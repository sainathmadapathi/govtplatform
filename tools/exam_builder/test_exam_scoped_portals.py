"""A registration or application service reaches an exam's page only when it is that exam's, or the
authority's own service for every recruitment -- never for its role alone.

Found on TGPSC's live site: a recruitments table whose row reads "Notification No: 04/2026  Web note
StartDate ... EndDate ...  Online application". The "Web note" names nothing itself, so its role was read
from the row ("Online application" -> APPLICATION_PORTAL), and the portal list, which chose by role,
offered a departmental test's notice to Group-I as its application portal. These tests rebuild that shape
on the invented commission of authority_fixture_site.py; nothing here names a real authority or exam.
"""
from __future__ import annotations

import unittest

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.exam_fixtures import NoNetwork
from tools.claude_cli.testing import ForbiddenClaude, use_gateway

from .authority_discovery import discover_authority, project_for_exam
from .authority_fixture_site import APPLY, AUTHORITY, HOME, OTR, ROOT, FakeSite
from .discover import DocKind
from .source_graph import EdgeKind, NodeStatus
from .source_trust import TrustRegistry

RECRUITMENTS = 'https://www.epsc.gov.in/recruitments.jsp'
DEPT_WEB_NOTE = 'https://www.epsc.gov.in/preview/RFQtMDQtMjAyNi1XTg'
GROUP_I_WEB_NOTE = 'https://www.epsc.gov.in/preview/RzEtMDUtMjAyNi1XTg'
BARE_WEB_NOTE = 'https://www.epsc.gov.in/preview/WFgtV04'
AE_PORTAL = 'https://apply.epsc.gov.in/ae-2026'
GROUP_II_PORTAL = 'https://apply.epsc.gov.in/group-ii-2026'

#: One table of the authority's recruitments. Every row has the same shape; only its words say whose it is.
LISTING = '''<html><head><title>Recruitments</title></head><body><h3>Recruitment Notifications</h3><table>
<tr><th>Notification</th><th>Documents</th><th>Dates</th><th>Apply</th></tr>
<tr><td>Notification No: 04/2026 - DEPARTMENTAL TESTS NOVEMBER 2026 SESSION</td>
    <td><a href="/preview/RFQtMDQtMjAyNi1XTg">Web note</a></td>
    <td>StartDate: 26/09/2026 EndDate: 17/10/2026</td><td>Online application</td></tr>
<tr><td>05/2026 - GROUP-I SERVICES</td>
    <td><a href="/preview/RzEtMDUtMjAyNi1XTg">Web note</a></td>
    <td>StartDate: 01/09/2026 EndDate: 30/09/2026</td><td>Online application</td></tr>
<tr><td>07/2026 - ASSISTANT ENGINEERS</td><td>Notice</td>
    <td>StartDate: 05/10/2026 EndDate: 25/10/2026</td>
    <td><a href="https://apply.epsc.gov.in/ae-2026">Submit Online Application</a></td></tr>
<tr><td><a href="/preview/WFgtV04">Webnote</a></td><td>Online application</td></tr>
</table></body></html>'''

#: The home page as it is, plus the link to that table and a home-page box for another recruitment.
HOME_PLUS = HOME.replace('<h3>Latest News</h3>', '''<h3>Recruitments</h3>
<ul><li><a href="/recruitments.jsp">Recruitments</a></li></ul>
<h3>Group-II Services 2026</h3>
<ul><li><a href="https://apply.epsc.gov.in/group-ii-2026">Submit Online Application</a></li></ul>
<h3>Latest News</h3>''')

EXAM = dict(authority_name=AUTHORITY, authority_domain=ROOT, cycle='2026')
GROUP_I = dict(EXAM, exam_id='exam-epsc-group-i-2026', title='Group-I Services')
AE = dict(EXAM, exam_id='exam-epsc-ae-2026', title='Assistant Engineers')
DEPT = dict(EXAM, exam_id='exam-epsc-departmental-tests-2026', title='Departmental Tests')

SERVICE_ROLES = ('OTR_PORTAL', 'APPLICATION_PORTAL')


class ExamScopedPortalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with NoNetwork() as net, use_gateway(ForbiddenClaude('portal scoping never calls Claude')):
            cls.site = FakeSite(extra={ROOT: HOME_PLUS, RECRUITMENTS: LISTING})
            cls.walked = discover_authority([ROOT], authority_name=AUTHORITY, fetch=cls.site, registry=TrustRegistry())
        assert net.attempts == [], net.attempts

    def portals(self, exam, **kw):
        return {x['url']: x for x in project_for_exam(self.walked, **exam, **kw)['portals']}

    def application(self, exam, **kw):
        """What section 04 (Application & Documents) is handed: the registration and application services."""
        return {u: x for u, x in self.portals(exam, **kw).items() if x['role'] in SERVICE_ROLES}

    def test_the_fixture_reproduces_the_live_shape(self):
        node = self.walked.graph.get(DEPT_WEB_NOTE)
        self.assertIs(node.role, DocKind.APPLICATION_PORTAL, node.role_reason)
        self.assertTrue(node.role_reason.startswith('listed under'), 'its role is read from its row, not its words')
        self.assertEqual({e.kind for e in self.walked.graph.parents(node.id)}, {EdgeKind.REPOSITORY_ITEM})
        self.assertIn('Notification No: 04/2026', node.context)

    def test_1_a_departmental_test_web_note_is_not_group_is_application_portal(self):
        self.assertNotIn(DEPT_WEB_NOTE, self.portals(GROUP_I))
        self.assertNotIn(DEPT_WEB_NOTE, self.portals(GROUP_I, sibling_words=['group-ii']))
        p = project_for_exam(self.walked, **GROUP_I)
        self.assertNotIn(DEPT_WEB_NOTE, [i['url'] for r in p['repositories'] for i in r['items']])
        self.assertNotIn(DEPT_WEB_NOTE, [i['url'] for i in p['practicalGuidance'] + p['learning']])

    def test_2_genuine_application_services_still_reach_group_i(self):
        app = self.application(GROUP_I)
        # The authority's own "Apply Online" serves every recruitment.
        self.assertEqual(app[APPLY]['role'], 'APPLICATION_PORTAL')
        self.assertEqual(app[APPLY]['sourceLabel'], 'Official source')
        # Group-I's own row's document is Group-I's, read by the same row mechanism.
        self.assertIn(GROUP_I_WEB_NOTE, app)
        self.assertEqual(app[GROUP_I_WEB_NOTE]['relation'], 'THIS_EXAM')

    def test_3_the_registration_portal_still_reaches_every_exam(self):
        for exam in (GROUP_I, AE, DEPT):
            with self.subTest(exam=exam['title']):
                app = self.application(exam)
                self.assertEqual(app[OTR]['role'], 'OTR_PORTAL')
                self.assertEqual(app[OTR]['section'], 'APPLICATION')

    def test_4_another_recruitments_portal_on_the_same_page_is_not_offered(self):
        self.assertNotIn(AE_PORTAL, self.portals(GROUP_I), 'its own words make it a portal; its row makes it AE\'s')
        # The same on the home page, and without being told the sibling's name: its box names a cycle.
        self.assertNotIn(GROUP_II_PORTAL, self.portals(GROUP_I))
        self.assertNotIn(GROUP_II_PORTAL, self.portals(GROUP_I, sibling_words=['group-ii']))
        self.assertNotIn(GROUP_II_PORTAL, self.portals(AE))

    def test_5_a_service_whose_owner_nothing_shows_is_left_out_not_guessed(self):
        node = self.walked.graph.get(BARE_WEB_NOTE)
        self.assertIs(node.role, DocKind.APPLICATION_PORTAL, 'read from its row, which names no recruitment')
        for exam in (GROUP_I, AE, DEPT):
            with self.subTest(exam=exam['title']):
                self.assertNotIn(BARE_WEB_NOTE, self.portals(exam))

    def test_6_the_same_rows_give_each_exam_its_own_service_and_no_other(self):
        dept, ae, g1 = self.application(DEPT), self.application(AE), self.application(GROUP_I)
        self.assertIn(DEPT_WEB_NOTE, dept)
        self.assertEqual(dept[DEPT_WEB_NOTE]['relation'], 'THIS_EXAM')
        self.assertNotIn(GROUP_I_WEB_NOTE, dept)
        self.assertIn(AE_PORTAL, ae)
        self.assertNotIn(DEPT_WEB_NOTE, ae)
        self.assertNotIn(GROUP_I_WEB_NOTE, ae)
        self.assertIn(GROUP_I_WEB_NOTE, g1)
        self.assertNotIn(AE_PORTAL, g1)
        for app in (dept, ae, g1):
            self.assertIn(OTR, app)
            self.assertIn(APPLY, app)

    def test_7_left_out_is_not_relabelled_and_stays_in_the_run(self):
        for url in (DEPT_WEB_NOTE, AE_PORTAL, BARE_WEB_NOTE, GROUP_II_PORTAL):
            with self.subTest(url=url):
                node = self.walked.graph.get(url)
                self.assertIsNotNone(node, 'the run keeps it for the audit')
                self.assertIs(node.status, NodeStatus.DISCOVERED, 'a service is recorded, never fetched')
                self.assertIs(node.role, DocKind.APPLICATION_PORTAL, 'no other role is made up for it')
        relation = {x['url']: x['relation'] for r in project_for_exam(self.walked, **GROUP_I)['repositories']
                    for x in r['items']}
        self.assertNotEqual(relation.get(DEPT_WEB_NOTE), 'THIS_EXAM')

    def test_8_the_plain_fixture_offers_what_it_always_did(self):
        with NoNetwork(), use_gateway(ForbiddenClaude('no Claude')):
            plain = discover_authority([ROOT], authority_name=AUTHORITY, fetch=FakeSite(), registry=TrustRegistry())
        for exam in (GROUP_I, AE):
            with self.subTest(exam=exam['title']):
                titles = sorted(x['title'] for x in project_for_exam(plain, **exam)['portals'])
                self.assertEqual(titles, ['Apply Online', 'Know Your EPSC ID', 'One Time Registration'])


if __name__ == '__main__':
    unittest.main()
