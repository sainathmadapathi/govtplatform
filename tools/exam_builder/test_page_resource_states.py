"""An exam's resource reached as a page, not a file, and pages the walk went no further than.

Found in the pre-merge review of the source-discovery work: when this exam's question paper sat behind its
own HTML page on the paper listing, the search state said NOT_FOUND_AFTER_DISCOVERY -- "every listing and
item GovOS found was read, and none is for this exam" -- while the same projection listed that page as this
exam's paper, and the PDF behind it had never been fetched. A page was never counted as a found item, and a
page whose links were not followed counted as a listing read in full. Also: an item expected to be a file
that turned out to be a page was read without the page limit.

Everything runs over the invented commission of authority_fixture_site.py; nothing reaches the network.
"""
from __future__ import annotations

import io
import os
import unittest

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.exam_fixtures import NoNetwork
from tools.claude_cli.testing import ForbiddenClaude, use_gateway

from .authority_discovery import discover_authority, project_for_exam
from .authority_fixture_site import AUTHORITY, ROOT, FakeSite
from .source_graph import DiscoveryLimits, NodeStatus, NodeType, SearchState, SkipReason, coverage_report
from .source_trust import TrustRegistry

HERE = os.path.dirname(os.path.abspath(__file__))
OLD_PAPERS = 'https://www.epsc.gov.in/oldquestionp.jsp'
RESULTS = 'https://www.epsc.gov.in/results.jsp'
PAPER_PAGE = 'https://www.epsc.gov.in/g1-2026-papers.jsp'
PAPER_PDF = 'https://www.epsc.gov.in/files/x91.pdf'
OFF_SITE_PAGE = 'https://papers.example.gov.in/epsc/g1-2026.html'
OFF_SITE_PDF = 'https://papers.example.gov.in/epsc/g1-2026-gs.pdf'
GROUP_I = dict(exam_id='exam-epsc-group-i-2026', title='Group-I Services', authority_name=AUTHORITY,
               authority_domain=ROOT, cycle='2026', sibling_words=['group-ii'])
#: What a "not found" says: never while a relevant page was not followed, or while this exam's page is listed.
NOT_FOUND_CLAIMS = ('every relevant listing', 'names something other than this exam')


def html(title: str, body: str) -> str:
    return f'<html><head><title>{title}</title></head><body>{body}</body></html>'


def old_papers(third: str) -> str:
    """The authority's old-papers listing: two papers of another recruitment, and a third item."""
    return html('Old Question Papers', f'''<h3>Old Question Papers:</h3><ul>
      <li><a href="/qp/ae-civil.pdf">1.AE-CIVIL.</a></li>
      <li><a href="/qp/ae-gs.pdf">2.AE-GS.</a></li>
      <li>{third}</li></ul>''')


#: The fixture's results page is built by script; here it is readable, so nothing else is left unread and
#: any "not found" would be the run's whole answer.
READABLE_RESULTS = html('Results', '''<h3>Results</h3><ul>
  <li><a href="/res/g2-2025.pdf">Group-II Results 2025</a></li>
  <li><a href="/res/ae-2024.pdf">AE Results 2024</a></li>
  <li><a href="/res/tpbo-2023.pdf">TPBO Results 2023</a></li></ul>''')
def results_with(fourth: str) -> str:
    """The readable results listing with a fourth item. Its heading names no archive, so a page off the
    authority's site listed on it is recorded and not followed (an old-papers heading would let the walk
    read one off-site archive)."""
    return READABLE_RESULTS.replace('</ul>', f'<li>{fourth}</li></ul>')


#: A paper's own page, which links to its file with words that name nothing.
PAPER_PAGE_HTML = html('Papers', '<p><a href="/files/x91.pdf">Click here</a></p>')
OFF_SITE_HTML = html('Papers', '<p><a href="g1-2026-gs.pdf">General Studies</a></p>')


class Walked(unittest.TestCase):
    def setUp(self):
        self.net = NoNetwork().__enter__()
        gw = use_gateway(ForbiddenClaude('search states never call Claude'))
        gw.__enter__()
        self.addCleanup(gw.__exit__, None, None, None)
        self.addCleanup(self._no_network)

    def _no_network(self):
        self.net.__exit__(None, None, None)
        self.assertEqual(self.net.attempts, [], 'the test reached for the network')

    def walk(self, pages: dict, limits=None):
        self.site = FakeSite(extra={RESULTS: READABLE_RESULTS, **pages})
        run = discover_authority([ROOT], authority_name=AUTHORITY, fetch=self.site, registry=TrustRegistry(),
                                 limits=limits)
        return run, project_for_exam(run, **GROUP_I)

    def assertNeverClaimsNotFound(self, state: dict):
        self.assertNotEqual(state['state'], SearchState.NOT_FOUND_AFTER_DISCOVERY.value, state['reason'])
        for claim in NOT_FOUND_CLAIMS:
            self.assertNotIn(claim, state['reason'])

    def mine(self, projection: dict) -> dict:
        return {i['url']: i['relation'] for r in projection['repositories'] for i in r['items']}


class ExamResourceAsAPageTests(Walked):
    def test_a_the_pdf_control_is_unchanged(self):
        _, p = self.walk({OLD_PAPERS: old_papers(
            '<a href="/qp/g1-2026-prelims.pdf">3.Group-I Services 2026 Preliminary Question Paper</a>')})
        self.assertEqual(p['searchStates']['QUESTION_PAPER'],
                         {'state': SearchState.FOUND_VERIFIED.value, 'reason': '1 identified as this exam'})

    def test_b_this_exams_paper_behind_its_own_page_is_found_never_not_found(self):
        run, p = self.walk({OLD_PAPERS: old_papers(
            '<a href="/g1-2026-papers.jsp">3.Group-I Services 2026 Preliminary Question Paper</a>'),
            PAPER_PAGE: PAPER_PAGE_HTML})
        page = run.graph.get(PAPER_PAGE)
        self.assertEqual((page.node_type, page.status), (NodeType.PAGE, NodeStatus.READ))
        # The file behind the page was not reached: never fetched, never recorded.
        self.assertNotIn(PAPER_PDF, self.site.calls)
        self.assertIsNone(run.graph.get(PAPER_PDF))
        state = p['searchStates']['QUESTION_PAPER']
        self.assertNeverClaimsNotFound(state)
        self.assertNotIn('nothing on them is this exam', state['reason'])
        self.assertEqual(state['state'], SearchState.FOUND_VERIFIED.value)
        self.assertIn('as a page', state['reason'])
        self.assertIn('did not reach the file', state['reason'])
        self.assertEqual(self.mine(p).get(PAPER_PAGE), 'THIS_EXAM', 'the panel and the state agree')

    def test_c_the_same_page_off_the_authoritys_site_is_found_and_its_links_are_not_followed(self):
        run, p = self.walk({RESULTS: results_with(
            f'<a href="{OFF_SITE_PAGE}">4.Group-I Services Results 2026</a>'), OFF_SITE_PAGE: OFF_SITE_HTML})
        page = run.graph.get(OFF_SITE_PAGE)
        self.assertIn(OFF_SITE_PAGE, self.site.calls)
        self.assertEqual((page.node_type, page.status, page.skipped),
                         (NodeType.PAGE, NodeStatus.READ, SkipReason.LINKS_NOT_FOLLOWED.value))
        self.assertNotIn(OFF_SITE_PDF, self.site.calls)
        state = p['searchStates']['RESULT']
        self.assertNeverClaimsNotFound(state)
        self.assertNotIn('nothing on them is this exam', state['reason'])
        self.assertEqual(state['state'], SearchState.FOUND_VERIFIED.value)
        self.assertIn('did not reach the file', state['reason'])
        self.assertEqual(coverage_report(run)['skipped'].get('skipped_due_to_links_not_followed'), 1)


class UnfollowedPagesTests(Walked):
    def test_d_an_unfollowed_page_that_names_nothing_never_supports_not_found(self):
        cases = (('a paper page read with nothing kept', 'QUESTION_PAPER',
                  {OLD_PAPERS: old_papers('<a href="/g1-2026-papers.jsp">3.Question Paper</a>'),
                   PAPER_PAGE: PAPER_PAGE_HTML}),
                 ('a results page off the site', 'RESULT',
                  {RESULTS: results_with(f'<a href="{OFF_SITE_PAGE}">4.Results</a>'), OFF_SITE_PAGE: OFF_SITE_HTML}))
        for where, role, pages in cases:
            with self.subTest(where=where):
                _, p = self.walk(pages)
                state = p['searchStates'][role]
                self.assertNeverClaimsNotFound(state)
                self.assertEqual(state['state'], SearchState.SEARCH_INCOMPLETE.value, state['reason'])
                self.assertEqual(state['notRead'], {'skipped_due_to_links_not_followed': 1})

    def test_e_a_page_is_not_this_exams_because_it_is_a_page(self):
        # Another recruitment's paper page: identity still decides, and its own words rule it out. With every
        # listing read, "not found" is then the honest answer -- the state model keeps that distinction.
        run, p = self.walk({OLD_PAPERS: old_papers(
            '<a href="/g1-2026-papers.jsp">3.Group-II Services 2025 Main Question Paper</a>'),
            PAPER_PAGE: PAPER_PAGE_HTML})
        self.assertNotIn(PAPER_PAGE, self.mine(p))
        state = p['searchStates']['QUESTION_PAPER']
        self.assertEqual(state['state'], SearchState.NOT_FOUND_AFTER_DISCOVERY.value, state['reason'])


class PageLimitTests(Walked):
    def test_f_a_listing_of_pages_that_look_like_files_cannot_read_past_the_page_limit(self):
        limits = DiscoveryLimits()
        items = ''.join(f'<li><a href="/qp/p{i}.pdf">Paper {i}</a></li>' for i in range(60))
        pages = {f'https://www.epsc.gov.in/qp/p{i}.pdf': html(f'Paper {i}', '<p>A page, not a file.</p>')
                 for i in range(60)}
        run, p = self.walk({OLD_PAPERS: html('Old Question Papers', f'<h3>Old Question Papers:</h3><ul>{items}</ul>'),
                            **pages}, limits=limits)
        self.assertLessEqual(run.pages_fetched, limits.max_pages)
        fetched = [u for u in self.site.calls if '/qp/p' in u]
        self.assertLessEqual(len(fetched), limits.max_pages + limits.max_documents)
        skipped = {n.skipped for n in run.graph.nodes.values() if '/qp/p' in n.url and n.skipped}
        self.assertIn(SkipReason.PAGE_BUDGET.value, skipped)
        self.assertNeverClaimsNotFound(p['searchStates']['QUESTION_PAPER'])


class CandidateWordsTests(unittest.TestCase):
    def test_every_reason_a_candidate_can_be_shown_has_words(self):
        with io.open(os.path.join(HERE, '..', '..', 'src', 'ui.tsx'), encoding='utf-8') as fh:
            ui = fh.read()
        for reason in SkipReason:
            self.assertIn(f'{reason.coverage_key}:', ui, reason.coverage_key)


if __name__ == '__main__':
    unittest.main()
