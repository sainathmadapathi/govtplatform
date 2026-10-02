"""Authority discovery wired into what already exists: exam discovery's gate, the build entry point,
the job queue and its normaliser. Nothing reaches the network or the real Claude CLI.
"""
from __future__ import annotations

import unittest
from unittest import mock

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.exam_fixtures import ExamTestCase, NoNetwork, make_hooks, run_job
from tools.claude_cli.handlers import norm_authority, norm_build
from tools.claude_cli.testing import ForbiddenClaude

from . import authority_discovery as AD
from . import build as B
from . import discover as D
from . import search as S
from .authority_fixture_site import AUTHORITY, ROOT, FakeSite
from .discover import DocKind, Relevance, SourceSet
from .resolve import Authority, ResolvedExam
from .source_graph import SourceGraphStore
from .source_trust import TrustRegistry

EXAM_ID = 'exam-epsc-group-i-2026'


def resolved_group_i() -> ResolvedExam:
    return ResolvedExam(query='Group-I Services', official_name='Group-I Services', year='2026',
                        authority=Authority(name=AUTHORITY, domain=ROOT, confidence=1.0), seed_urls=[])


def fixture_run():
    return AD.discover_authority([ROOT], authority_name=AUTHORITY, fetch=FakeSite(), registry=TrustRegistry())


class ExamDiscoveryHookTests(unittest.TestCase):
    """Phase E: a run's official items reach an exam only through discover.gate()."""

    def setUp(self):
        self.net = NoNetwork().__enter__()
        self.addCleanup(lambda: (self.net.__exit__(None, None, None),
                                 self.assertEqual(self.net.attempts, [], 'the test reached for the network')))

    def discover(self, authority_run):
        asked = []

        def fake_search(query, **kw):
            asked.append(query)
            return []

        with mock.patch.object(S, 'search', fake_search):
            out = D.discover(resolved_group_i(), exam_id=EXAM_ID, sibling_exam_words=['group-ii'],
                             authority_run=authority_run)
        return out, asked

    def test_the_gate_admits_this_exams_documents_and_nothing_else(self):
        out, _ = self.discover(fixture_run())
        urls = {d.url: d for d in out.docs}
        self.assertIn('https://www.epsc.gov.in/pdf/n05-2026.pdf', urls)
        self.assertIn('https://www.epsc.gov.in/pdf/g1-syllabus.pdf', urls)
        self.assertIs(urls['https://www.epsc.gov.in/pdf/n05-2026.pdf'].kind, DocKind.NOTIFICATION)
        self.assertIs(urls['https://www.epsc.gov.in/pdf/n05-2026.pdf'].relevance, Relevance.DIRECT)
        for other in ('n04-2022.pdf', 'n06-2026.pdf', 'g2-syllabus.pdf', 'ae-civil.pdf', 'otr.epsc.gov.in'):
            self.assertFalse([u for u in urls if other in u], other)
        self.assertTrue(all('(authority discovery)' in d.found_on for d in out.docs))
        self.assertIn('authority discovery:', ' '.join(out.log))

    def test_kinds_the_walk_supplied_are_not_searched_for_again(self):
        _, without = self.discover(None)
        _, with_run = self.discover(fixture_run())
        self.assertEqual(len(without), 8, 'without a run every kind is searched for, as before')
        self.assertLess(len(with_run), len(without))
        searched = ' '.join(with_run)
        self.assertNotIn('notification notice of examination', searched)
        self.assertNotIn('syllabus scheme of examination', searched)

    def test_without_a_run_discovery_is_unchanged(self):
        out, _ = self.discover(None)
        self.assertEqual(out.docs, [])
        self.assertNotIn('authority discovery', ' '.join(out.log))

    def test_build_calls_the_walk_with_the_resolved_exam_only_when_asked(self):
        resolved = resolved_group_i()
        sources = SourceSet(exam_id=EXAM_ID, authority_domain=ROOT)
        walked = []
        with mock.patch.object(B, 'resolve', return_value=resolved), \
             mock.patch.object(B, 'discover', return_value=sources) as disc:
            B.build('Group-I Services', year='2026')
            self.assertIsNone(disc.call_args.kwargs['authority_run'])
            result = B.build('Group-I Services', year='2026',
                             authority_discovery=lambda r: walked.append(r) or 'RUN')
        self.assertEqual(walked, [resolved])
        self.assertEqual(disc.call_args.kwargs['authority_run'], 'RUN')
        self.assertEqual(result.authority_run, 'RUN')


class AuthorityJobTests(ExamTestCase):
    def setUp(self):
        super().setUp()
        self.env.put_authored([{'id': EXAM_ID, 'title': 'Group-I Services', 'authorityName': AUTHORITY,
                                'officialDomain': ROOT, 'resources': []},
                               {'id': 'exam-nowhere-2026', 'title': 'Nowhere', 'authorityName': 'Nobody',
                                'officialDomain': ''}])
        self.hooks = make_hooks(self.env, ForbiddenClaude('a walk without useClaude must not call Claude'))

    def test_the_normaliser_takes_an_exam_and_never_an_address(self):
        self.assertEqual(norm_authority({'examId': EXAM_ID, 'root': 'http://169.254.169.254/', 'url': 'x'}),
                         {'examId': EXAM_ID})
        self.assertEqual(norm_authority({'examId': EXAM_ID, 'useClaude': 'yes'}), {'examId': EXAM_ID, 'useClaude': True})
        with self.assertRaises(ValueError):
            norm_authority({'root': ROOT})

    def test_a_plain_build_input_is_unchanged_and_the_walk_is_opt_in(self):
        self.assertEqual(norm_build({'query': 'q', 'year': '2026'}), {'query': 'q', 'year': '2026', 'useClaude': False})
        self.assertTrue(norm_build({'query': 'q', 'authorityDiscovery': 'true'})['authorityDiscovery'])

    def test_the_job_walks_from_the_exams_own_address_and_stores_the_run(self):
        site = FakeSite()
        with mock.patch.object(AD, 'fetch_checked', lambda url, **kw: site(url)):
            job = run_job(self.env, 'DISCOVER_AUTHORITY', {'examId': EXAM_ID}, self.hooks, exam_id=EXAM_ID)
        self.assertEqual(job.status.value, 'SUCCEEDED', job.error_message)
        self.assertEqual(site.calls[0], ROOT)
        self.assertEqual(job.result['searchStates']['NOTIFICATION']['state'], 'FOUND_VERIFIED')
        # The fixture's Results page is built by script: papers cannot be called "not found".
        self.assertEqual(job.result['searchStates']['QUESTION_PAPER']['state'], 'SEARCH_INCOMPLETE')
        stored = SourceGraphStore(self.env.db_path).latest('epsc.gov.in')
        self.assertEqual(stored.id, job.result['runId'])
        self.assertEqual([l['kind'] for l in job.evidence_links], ['SOURCE_RUN'])

    def test_an_unknown_exam_or_one_without_an_address_fails_safely(self):
        job = run_job(self.env, 'DISCOVER_AUTHORITY', {'examId': 'exam-missing-2026'}, self.hooks)
        self.assertEqual((job.status.value, job.error_category), ('FAILED', 'EXAM_NOT_FOUND'))
        job = run_job(self.env, 'DISCOVER_AUTHORITY', {'examId': 'exam-nowhere-2026'}, self.hooks)
        self.assertEqual((job.status.value, job.error_category), ('FAILED', 'NO_OFFICIAL_ADDRESS'))


if __name__ == '__main__':
    unittest.main()
