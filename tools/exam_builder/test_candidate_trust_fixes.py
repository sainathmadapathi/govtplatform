"""Regression tests for the five candidate-trust fixes found by the source-discovery audit:

1. "Not found after search" only when every relevant discovered listing and item was read; a node
   skipped for any reason (file/page/item budget, depth, script, fetch failure) makes it incomplete.
2. Official status comes from owning the host, never from being linked by an official page.
3. A link in a table row keeps that row as its context ("Addendum" in the row of its notification).
4. One placement model (role -> section), shared by the backend and the candidate pages.
5. The trusted-secondary command-line output says what it is: TRUSTED_SECONDARY / COMMAND_LINE_ONLY /
   NOT_PUBLISHED.

Everything runs over the in-memory fixture sites; nothing reaches the network or Claude.
"""
from __future__ import annotations

import io
import json
import os
import unittest

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.exam_fixtures import NoNetwork
from tools.claude_cli.testing import ForbiddenClaude, use_gateway

from . import secondary_ingestion as SI
from .authority_discovery import admit_for_exam, discover_authority, exam_words_for, extract_links, project_for_exam
from .authority_fixture_site import AUTHORITY, ROOT, FakeSite
from .discover import DocKind
from .resource_roles import LEARNING_ROLES, SECTION_FOR_ROLE
from .secondary_fixture_site import EXAM as SECONDARY_EXAM, PROFILE, SecondarySite
from .source_graph import (DiscoveryLimits, NodeStatus, SearchState, SkipReason, SourceClass, coverage_report)
from .source_trust import TrustRegistry, classify_source, source_ownership
from tools.exam_authoring.sources import estate_of, same_estate

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GROUP_I = dict(exam_id='exam-epsc-group-i-2026', title='Group-I Services', authority_name=AUTHORITY,
               authority_domain=ROOT, cycle='2026', sibling_words=['group-ii'])
RESULTS = 'https://www.epsc.gov.in/results.jsp'
KEYS = 'https://www.epsc.gov.in/keys'
OLD_PAPERS = 'https://www.epsc.gov.in/oldquestionp.jsp'
NOTICES = 'https://www.epsc.gov.in/notifications.jsp'


def html(title: str, body: str) -> str:
    return f'<html><head><title>{title}</title></head><body>{body}</body></html>'


#: The authority's results area as a real listing, linking a keys listing that holds this exam's paper.
RESULTS_WITH_KEYS = {
    RESULTS: html('Results, Keys & OMR Downloads', '''<h3>Results, Keys &amp; OMR Downloads</h3><ul>
      <li><a href="/res/g2-2025.pdf">Group-II Results 2025</a></li>
      <li><a href="/res/ae-2024.pdf">AE Results 2024</a></li>
      <li><a href="/keys">Keys</a></li></ul>'''),
    KEYS: html('Keys', '''<h3>Keys</h3><ul>
      <li><a href="/keys/g1-2026-qp.pdf">Group-I 2026 Preliminary Question Paper</a></li>
      <li><a href="/keys/g1-2026-key.pdf">Group-I 2026 Preliminary Answer Key</a></li>
      <li><a href="/keys/ae-2024.pdf">AE 2024 Key</a></li></ul>'''),
}
#: The same results area with nothing of this exam's, and no further listing.
RESULTS_ALL_OTHER = {
    RESULTS: html('Results, Keys & OMR Downloads', '''<h3>Results, Keys &amp; OMR Downloads</h3><ul>
      <li><a href="/res/g2-2025.pdf">Group-II Results 2025</a></li>
      <li><a href="/res/ae-2024.pdf">AE Results 2024</a></li>
      <li><a href="/res/tpbo-2023.pdf">TPBO Results 2023</a></li></ul>'''),
}


class Guarded(unittest.TestCase):
    def setUp(self):
        self.net = NoNetwork().__enter__()
        gw = use_gateway(ForbiddenClaude('these fixes never call Claude'))
        gw.__enter__()
        self.addCleanup(gw.__exit__, None, None, None)
        self.addCleanup(self._no_network)

    def _no_network(self):
        self.net.__exit__(None, None, None)
        self.assertEqual(self.net.attempts, [], 'the test reached for the network')

    def walk(self, extra=None, limits=None, registry=None):
        site = FakeSite(extra=extra or {})
        run = discover_authority([ROOT], authority_name=AUTHORITY, fetch=site, registry=registry or TrustRegistry(),
                                 limits=limits)
        return run, site


# ============================================================ 1. search completeness
class SearchCompletenessTests(Guarded):
    def test_a_listing_skipped_for_the_file_budget_makes_the_search_incomplete_never_not_found(self):
        run, site = self.walk(RESULTS_WITH_KEYS, limits=DiscoveryLimits(max_documents=2))
        keys = run.graph.get(KEYS)
        self.assertEqual((keys.status, keys.skipped), (NodeStatus.SKIPPED_LIMIT, SkipReason.FILE_BUDGET.value))
        self.assertNotIn(KEYS, site.calls, 'the keys listing was never read')
        self.assertIn(KEYS, [f['url'] for f in run.frontier if f.get('skip') == 'FILE_BUDGET'],
                      'a file-budget skip is recorded as unexplored')
        p = project_for_exam(run, **GROUP_I)
        qp = p['searchStates']['QUESTION_PAPER']
        self.assertEqual(qp['state'], SearchState.SEARCH_INCOMPLETE.value)
        self.assertNotEqual(qp['state'], SearchState.NOT_FOUND_AFTER_DISCOVERY.value)
        self.assertGreaterEqual(qp['notRead'].get('skipped_due_to_file_budget', 0), 1)
        self.assertIn('file budget', qp['reason'])
        # The paper was not found among what happened to be fetched -- and that is not "not found".
        adm = admit_for_exam(run, exam_id=GROUP_I['exam_id'], exam_words=exam_words_for(
            'Group-I Services', 'Group-I Services', authority_name=AUTHORITY, authority_domain=ROOT), exam_cycle='2026')
        found = [n for n in run.graph.nodes.values()
                 if n.role is DocKind.QUESTION_PAPER and adm.relation.get(n.id) == 'THIS_EXAM']
        self.assertEqual(found, [])
        cov = coverage_report(run)
        self.assertGreaterEqual(cov['skipped'].get('skipped_due_to_file_budget', 0), 1)
        self.assertFalse(cov['exhaustive'])

    def test_with_the_budget_to_read_it_the_same_listing_yields_the_paper(self):
        run, site = self.walk(RESULTS_WITH_KEYS)
        self.assertIn(KEYS, site.calls)
        p = project_for_exam(run, **GROUP_I)
        self.assertEqual(p['searchStates']['QUESTION_PAPER']['state'], SearchState.FOUND_VERIFIED.value)

    def test_not_found_is_allowed_only_when_every_relevant_place_was_read(self):
        run, _ = self.walk(RESULTS_ALL_OTHER)
        p = project_for_exam(run, **GROUP_I)
        qp = p['searchStates']['QUESTION_PAPER']
        self.assertEqual(qp['state'], SearchState.NOT_FOUND_AFTER_DISCOVERY.value, qp['reason'])
        self.assertNotIn('notRead', qp)

    def test_a_script_built_listing_or_a_tiny_page_budget_also_forbids_not_found(self):
        run, _ = self.walk()                                      # the fixture's results page is built by script
        st = project_for_exam(run, **GROUP_I)['searchStates']['QUESTION_PAPER']
        self.assertEqual((st['state'], st['notRead']), ('SEARCH_INCOMPLETE', {'skipped_due_to_script_rendering': 1}))
        # Read with every page: nothing of this exam's, and everything was read.
        run, _ = self.walk(RESULTS_ALL_OTHER)
        self.assertEqual(project_for_exam(run, **GROUP_I)['searchStates']['QUESTION_PAPER']['state'],
                         'NOT_FOUND_AFTER_DISCOVERY')
        # The same site with a two-page budget: the results listing goes unread, so never "not found".
        run, _ = self.walk(RESULTS_ALL_OTHER, limits=DiscoveryLimits(max_pages=2))
        self.assertEqual(run.graph.get(RESULTS).skipped, SkipReason.PAGE_BUDGET.value)
        st = project_for_exam(run, **GROUP_I)['searchStates']['QUESTION_PAPER']
        self.assertNotEqual(st['state'], SearchState.NOT_FOUND_AFTER_DISCOVERY.value, st['reason'])
        self.assertIn('skipped_due_to_page_budget', coverage_report(run)['skipped'])

    def test_every_skip_is_explicit_and_counted(self):
        seen = {}
        for limits in (DiscoveryLimits(), DiscoveryLimits(max_documents=3), DiscoveryLimits(max_pages=2)):
            run, _ = self.walk(limits=limits)
            cov = coverage_report(run)
            seen.update(cov['skipped'])
            self.assertFalse(cov['exhaustive'])
            for n in run.graph.nodes.values():
                if n.status in (NodeStatus.SKIPPED_LIMIT, NodeStatus.FETCH_FAILED):
                    self.assertIn(n.skipped, {r.value for r in SkipReason}, n.url)
        for key in ('skipped_due_to_file_budget', 'skipped_due_to_page_budget', 'skipped_due_to_depth',
                    'skipped_due_to_script_rendering', 'skipped_due_to_fetch_failed'):
            self.assertIn(key, seen, key)

    def test_an_item_ruled_out_by_its_own_words_is_not_a_gap_but_a_listing_never_is(self):
        # The old papers are named for other recruitments: unread or not, they cannot be this exam's.
        run, _ = self.walk(RESULTS_ALL_OTHER, limits=DiscoveryLimits(max_documents=1))
        p = project_for_exam(run, **GROUP_I)
        qp = p['searchStates']['QUESTION_PAPER']
        # Some of the results items were skipped, but each names another recruitment: still complete.
        self.assertEqual(qp['state'], SearchState.NOT_FOUND_AFTER_DISCOVERY.value, qp['reason'])
        # A "Keys" link (a listing) skipped for the budget is never ruled out by its title.
        run, _ = self.walk(RESULTS_WITH_KEYS, limits=DiscoveryLimits(max_documents=1))
        self.assertEqual(project_for_exam(run, **GROUP_I)['searchStates']['QUESTION_PAPER']['state'], 'SEARCH_INCOMPLETE')


# ============================================================ 2. ownership, not linking
REVIEWED = TrustRegistry([dict(PROFILE)])
SECONDARY_FILE = 'https://www.studyportal.example.in/pdf/epsc-group-1-2022-master.pdf'
COACHING_FILE = 'https://files.coach.example.com/papers/epsc-g1.pdf'


class OwnershipTests(Guarded):
    def linked(self, url, role=DocKind.QUESTION_PAPER, is_document=True, registry=REVIEWED):
        from .source_graph import EdgeKind
        cls, why = classify_source(url, estates=['epsc.gov.in'], via=EdgeKind.REPOSITORY_ITEM,
                                   parent_class=SourceClass.PRIMARY_OFFICIAL, role=role, is_document=is_document,
                                   registry=registry, authority=AUTHORITY)
        owner, relationship = source_ownership(url, estates=['epsc.gov.in'], via=EdgeKind.REPOSITORY_ITEM,
                                               parent_class=SourceClass.PRIMARY_OFFICIAL)
        return cls, relationship, owner, why

    def test_a_file_on_a_reviewed_secondary_site_linked_from_an_official_page_stays_trusted_secondary(self):
        cls, relationship, owner, why = self.linked(SECONDARY_FILE)
        self.assertEqual((cls, relationship, owner),
                         (SourceClass.TRUSTED_SECONDARY, 'LINKED_FROM_OFFICIAL', estate_of('www.studyportal.example.in')))
        self.assertIn('does not make it the authority', why)

    def test_no_third_party_url_becomes_official_by_being_linked_whatever_it_is(self):
        cases = [(COACHING_FILE, DocKind.QUESTION_PAPER, True), ('https://files.coach.example.com/p', DocKind.NOTIFICATION, False),
                 ('https://drive.example.com/file/d/abc', DocKind.CORRIGENDUM, False),
                 (SECONDARY_FILE, DocKind.STUDY_MATERIAL, True),          # a reviewed site, outside its reviewed roles
                 ('https://www.youtube.com/@epsc', DocKind.LECTURE_VIDEO, False),
                 ('https://x.com/epsc_official', DocKind.DISCOVERY_SIGNAL, False)]
        for url, role, is_doc in cases:
            with self.subTest(url=url):
                cls, relationship, _, _ = self.linked(url, role, is_doc)
                self.assertNotEqual(cls, SourceClass.PRIMARY_OFFICIAL)
                self.assertEqual(relationship, 'LINKED_FROM_OFFICIAL')
        self.assertIs(self.linked('https://x.com/epsc_official', DocKind.DISCOVERY_SIGNAL, False)[0], SourceClass.DISCOVERY_ONLY)

    def test_official_detection_by_ownership_is_not_weakened(self):
        self.assertEqual(self.linked('https://otr.epsc.gov.in/login', DocKind.OTR_PORTAL, False)[:2],
                         (SourceClass.PRIMARY_OFFICIAL, 'OWNED_BY_AUTHORITY'))
        self.assertEqual(self.linked('http://old.expsc.gov.in/a.pdf')[:2], (SourceClass.PRIMARY_OFFICIAL, 'GOVERNMENT_HOST'),
                         'a retired government domain the authority links to stays official')
        cls, _ = classify_source('https://www.telangana.gov.in/x', estates=['epsc.gov.in'])
        self.assertIs(cls, SourceClass.SECONDARY, 'a government site nobody linked is not this authority\'s')

    def test_in_a_walk_a_third_party_file_on_an_official_listing_is_never_official_or_fetched(self):
        listing = html('Old Question Papers', f'''<h3>Old Question Papers:</h3><ul>
          <li><a href="/preview/ae-civil.pdf">1.AE-CIVIL.</a></li>
          <li><a href="/preview/ae-gs.pdf">2.AE-GS.</a></li>
          <li><a href="{SECONDARY_FILE}">3.EPSC Group-1 2022 Master Paper and Key</a></li>
          <li><a href="{COACHING_FILE}">4.EPSC Group-1 Paper (mirror)</a></li></ul>''')
        run, site = self.walk({OLD_PAPERS: listing}, registry=REVIEWED)
        secondary, coaching = run.graph.get(SECONDARY_FILE), run.graph.get(COACHING_FILE)
        self.assertEqual((secondary.source_class, secondary.relationship),
                         (SourceClass.TRUSTED_SECONDARY, 'LINKED_FROM_OFFICIAL'))
        self.assertEqual((coaching.source_class, coaching.relationship), (SourceClass.SECONDARY, 'LINKED_FROM_OFFICIAL'))
        self.assertNotIn(SECONDARY_FILE, site.calls)
        self.assertNotIn(COACHING_FILE, site.calls)
        for n in run.graph.nodes.values():
            if n.source_class is SourceClass.PRIMARY_OFFICIAL:
                self.assertIn(n.relationship, ('OWNED_BY_AUTHORITY', 'GOVERNMENT_HOST'), n.url)
        p = project_for_exam(run, **GROUP_I)
        shown = [i for r in p['repositories'] for i in r['items']]
        for item in shown:
            if item['url'] in (SECONDARY_FILE, COACHING_FILE):
                self.assertNotEqual(item['sourceLabel'], 'Official source', item['url'])
                self.assertEqual(item['relationship'], 'LINKED_FROM_OFFICIAL')


# ============================================================ 3. table-row context
ROWS = html('Notifications', '''<h3>Direct Recruitment</h3><table>
  <tr><th>Notification</th><th>Dates</th><th>Documents</th></tr>
  <tr><td><a href="/pdf/n05-2026.pdf">05/2026 - GROUP-I SERVICES</a></td><td>Start Date: 10/01/2026</td><td><a href="/pdf/add-05.pdf">Addendum</a></td></tr>
  <tr><td><a href="/pdf/n06-2026.pdf">06/2026 - GROUP-II SERVICES</a></td><td>Start Date: 12/01/2026</td><td><a href="/pdf/add-06.pdf">Addendum</a></td></tr>
  <tr><td><a href="/pdf/n07-2026.pdf">07/2026 - ASSISTANT ENGINEERS</a></td><td>Start Date: 15/01/2026</td><td><a href="/pdf/add-07.pdf">Addendum</a></td></tr>
</table><ul><li><a href="/pdf/add-x.pdf">Addendum</a></li></ul>''')


class RowContextTests(Guarded):
    def test_links_with_the_same_text_keep_their_own_rows(self):
        links, _ = extract_links(ROWS, NOTICES)
        addenda = {l.url.rsplit('/', 1)[-1]: l for l in links if l.text == 'Addendum'}
        self.assertIn('05/2026 - GROUP-I SERVICES', addenda['add-05.pdf'].context)
        self.assertIn('06/2026 - GROUP-II SERVICES', addenda['add-06.pdf'].context)
        self.assertIn('07/2026 - ASSISTANT ENGINEERS', addenda['add-07.pdf'].context)
        self.assertEqual(len({l.context for l in addenda.values()}), 4, 'four different contexts')
        self.assertEqual(addenda['add-05.pdf'].table_heading, 'Direct Recruitment')
        self.assertEqual(addenda['add-x.pdf'].context, 'Direct Recruitment', 'outside a table: the list or heading, as before')
        self.assertEqual(addenda['add-x.pdf'].row, '')

    def test_layout_tables_and_navigation_rows_are_not_used_as_context(self):
        layout = '<table><tr><td>' + ('Long page text. ' * 60) + '<a href="/a.pdf">Addendum</a></td></tr></table>'
        nav = '<table><tr>' + ''.join(f'<td><a href="/m{i}">Menu {i}</a></td>' for i in range(10)) + '</tr></table>'
        links, _ = extract_links(f'<html><body><h3>Notices</h3>{layout}{nav}</body></html>', NOTICES)
        self.assertTrue(all(not l.row for l in links))

    def test_each_addendum_is_judged_by_its_row_and_an_untitled_one_is_unidentifiable(self):
        run, _ = self.walk({NOTICES: ROWS})
        words = exam_words_for('Group-I Services', 'Group-I Services', authority_name=AUTHORITY, authority_domain=ROOT)
        adm = admit_for_exam(run, exam_id=GROUP_I['exam_id'], exam_words=words, sibling_words=['group-ii'], exam_cycle='2026')
        rel = {n.url.rsplit('/', 1)[-1]: adm.relation.get(n.id) for n in run.graph.nodes.values() if 'add-' in n.url}
        self.assertEqual(rel, {'add-05.pdf': 'THIS_EXAM', 'add-06.pdf': 'OTHER_EXAM', 'add-07.pdf': 'NOT_THIS_EXAM',
                               'add-x.pdf': 'UNIDENTIFIABLE'})
        self.assertIs(run.graph.get('https://www.epsc.gov.in/pdf/add-05.pdf').role, DocKind.CORRIGENDUM)
        p = project_for_exam(run, **GROUP_I)
        self.assertEqual(p['searchStates']['CORRIGENDUM']['state'], SearchState.FOUND_VERIFIED.value)


# ============================================================ 4. one placement model
class PlacementTests(unittest.TestCase):
    def test_the_backend_model_is_the_shared_table(self):
        with io.open(os.path.join(HERE, 'resource_role_cases.json'), encoding='utf-8') as fh:
            table = json.load(fh)['sectionForRole']
        self.assertEqual(table, {k.value: v for k, v in SECTION_FOR_ROLE.items()})

    def test_each_role_goes_where_a_candidate_would_look(self):
        want = {DocKind.QUESTION_PAPER: 'PRACTICE', DocKind.ANSWER_KEY: 'PRACTICE', DocKind.APPLICATION_PORTAL: 'APPLICATION',
                DocKind.OTR_PORTAL: 'APPLICATION', DocKind.NOTIFICATION: 'OFFICIAL_LINKS', DocKind.CORRIGENDUM: 'CORRIGENDA',
                DocKind.ADMIT_CARD: 'ADMIT_CARD', DocKind.RESULT: 'RESULTS', DocKind.SYLLABUS: 'SYLLABUS',
                DocKind.CUTOFF: 'CUTOFFS', DocKind.EXAM_DAY_INSTRUCTIONS: 'EXAM_DAY', DocKind.STUDY_MATERIAL: 'RESOURCES',
                DocKind.LECTURE_VIDEO: 'RESOURCES', DocKind.PRACTICE_TOOL: 'RESOURCES'}
        for role, section in want.items():
            self.assertEqual(SECTION_FOR_ROLE[role], section, role)
        self.assertEqual({r for r, s in SECTION_FOR_ROLE.items() if s == 'RESOURCES'}, set(LEARNING_ROLES))
        self.assertIsNone(SECTION_FOR_ROLE[DocKind.DISCOVERY_SIGNAL])


# ============================================================ 5. secondary status
class SecondaryStatusTests(Guarded):
    def test_the_command_line_output_says_it_is_not_application_data(self):
        sources, _ = SI.load_reviewed_sources(self._registry())
        out = SI.ingest_secondary(sources['studyportal.example.in'], SECONDARY_EXAM, fetch=SecondarySite()).as_dict()
        self.assertEqual({k: out['status'][k] for k in ('sourceClass', 'availability', 'publication')},
                         {'sourceClass': 'TRUSTED_SECONDARY', 'availability': 'COMMAND_LINE_ONLY', 'publication': 'NOT_PUBLISHED'})
        self.assertIn('nothing here is a candidate fact', out['status']['note'])
        self.assertTrue(out['claims'] and out['resolutions'])
        for row in out['claims'] + out['resolutions']:
            self.assertEqual((row['publication'], row['availability']), ('NOT_PUBLISHED', 'COMMAND_LINE_ONLY'))

    def test_nothing_in_the_application_reads_it(self):
        for rel in ('app.py', 'src/ui.tsx', 'src/services.ts', 'src/main.tsx', 'tools/claude_cli/handlers.py',
                    'tools/claude_cli/routes.py'):
            with io.open(os.path.join(REPO, rel), encoding='utf-8') as fh:
                text = fh.read()
            for needle in ('secondary_ingestion', 'exam_data/secondary', 'SecondaryIngestion'):
                self.assertNotIn(needle, text, f'{rel} reads trusted-secondary output')

    def _registry(self):
        import tempfile
        d = tempfile.mkdtemp(prefix='govos-status-')
        self.addCleanup(lambda: __import__('shutil').rmtree(d, True))
        path = os.path.join(d, 'profiles.json')
        with io.open(path, 'w', encoding='utf-8') as fh:
            json.dump({'profiles': [PROFILE]}, fh)
        return path


if __name__ == '__main__':
    unittest.main()
