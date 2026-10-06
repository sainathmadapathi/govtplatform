"""Generic capabilities a real, previously unseen recruitment site exposed as missing.

Every fixture here is the *shape* of what a real authority's site did, not that authority:
anchors written `href ="preview/…"` with a relative path, PDFs served behind extension-less
viewer routes, sibling exams told apart only by an ordinal ("Group-I" / "Group-II"), the
exam's documents linked from a site-wide listing page rather than from any seed, a link whose
text is only the recruitment's name, and a home-page title that is the authority's own name.
No authority, exam or domain from the real run is named; the code under test has no branch
for any of them.

Run: python -m unittest tools.exam_builder.test_realworld_generic
"""
from __future__ import annotations

import unittest
from unittest.mock import patch

from ..exam_authoring import sources as S
from ..exam_authoring.record import Field, Status
from ..exam_authoring.sources import Document
from . import build as B
from . import discover as D
from .discover import DiscoveredDoc, DocKind, Relevance, gate
from .identity import ExamIdentity, IdentityVerdict, verify
from .resolve import Authority, ResolvedExam, alias_in, exam_aliases, ordinal_compounds


class TestLinkParsing(unittest.TestCase):
    def test_href_with_space_and_relative_path(self):
        doc = Document(url='https://board.example.gov.in/notifications', kind='HTML', fetched_at='x', text='')
        doc.html = ('<a target="_blank" href ="preview/AbC=="><i class="fa"></i>&nbsp;02/2024 - GROUP-I SERVICES</a>'
                    "<a href='/Results'>Results</a>"
                    '<a href="#">skip</a><a href="javascript:void(0)">skip</a>'
                    '<a href="https://otr.example.gov.in/login">Apply</a>')
        links = S.html_links(doc)
        self.assertEqual(links[0], ('02/2024 - GROUP-I SERVICES', 'https://board.example.gov.in/preview/AbC=='))
        self.assertEqual(links[1], ('Results', 'https://board.example.gov.in/Results'))
        self.assertEqual([u for _, u in links][2:], ['https://otr.example.gov.in/login'])


class TestDocumentSniffing(unittest.TestCase):
    """The bytes are fetched once and the PDF magic decides how they are parsed -- the parsers take the
    bytes, never the URL (`load_pdf`/`load_html` used to be called here, and fetched it again)."""

    def sniff(self, data):
        calls = []
        with patch.object(S, 'fetch', side_effect=lambda u, **k: calls.append(('fetch', u)) or data) as fetched, \
             patch.object(S, 'pdf_document', side_effect=lambda u, b: calls.append(('pdf', u, b))), \
             patch.object(S, 'html_document', side_effect=lambda u, b: calls.append(('html', u, b))), \
             patch.object(S, 'load_pdf', side_effect=AssertionError('fetched again')), \
             patch.object(S, 'load_html', side_effect=AssertionError('fetched again')):
            S.load_document('https://board.example.gov.in/preview/token')
        self.assertEqual(fetched.call_count, 1)
        return calls

    def test_pdf_bytes_behind_extensionless_url_load_as_pdf(self):
        url = 'https://board.example.gov.in/preview/token'
        self.assertEqual(self.sniff(b'%PDF-1.4 ...'), [('fetch', url), ('pdf', url, b'%PDF-1.4 ...')])

    def test_html_bytes_load_as_html(self):
        calls = self.sniff(b'<html><title>x</title></html>')
        self.assertEqual([c[0] for c in calls], ['fetch', 'html'])


class TestOrdinalAliases(unittest.TestCase):
    def test_compound_replaces_bare_head(self):
        self.assertEqual(ordinal_compounds('Board Group-I Services'), ['group i'])
        aliases = exam_aliases('XBRD Group-I Services')
        self.assertIn('group i', aliases)
        self.assertNotIn('group', aliases)
        # an acronym is not split into a head and an ordinal
        self.assertEqual(ordinal_compounds('XBRDC clerk'), [])
        # structural heads stay out ("paper", "level" are every exam's words)
        self.assertEqual(ordinal_compounds('Paper-II Level 4'), [])

    def test_boundary_matching(self):
        self.assertTrue(alias_in('group i', '02/2024 - group-i services'))
        self.assertTrue(alias_in('group i', 'group – i services (hons. degree standard)'))
        self.assertFalse(alias_in('group i', 'group-ii services'))
        self.assertFalse(alias_in('group i', 'group iii services'))
        self.assertFalse(alias_in('group i', 'group iv'))
        self.assertTrue(alias_in('cgl', 'cgl 2026 notice'))          # plain aliases unchanged

    def test_gate_tells_siblings_apart(self):
        words = exam_aliases('XBRD Group-I Services')
        rel, matched, _ = gate('02/2024 - GROUP-I SERVICES', '/preview/a', exam_words=words, page_is_exam_specific=False)
        self.assertEqual((rel, matched), (Relevance.DIRECT, ['group i']))
        rel, _, _ = gate('03/2024 - GROUP-II SERVICES', '/preview/b', exam_words=words, page_is_exam_specific=False)
        self.assertEqual(rel, Relevance.REJECTED)
        rel, _, _ = gate('Group-IV Services', '/preview/c', exam_words=words, page_is_exam_specific=False)
        self.assertEqual(rel, Relevance.REJECTED)


class TestIdentityWithOrdinal(unittest.TestCase):
    TARGET = ExamIdentity(exam_id='exam-xbrd-group-i-2024', query='XBRD Group-I Services',
                          official_name='XBRD Group-I Services', year='2024', authority_name='Example Board')

    def test_own_notification_matches(self):
        text = ('EXAMPLE STATE BOARD: CAPITAL NOTIFICATION NO. 02/2024, DATED: 19/02/2024 '
                'GROUP-I SERVICES (GENERAL RECRUITMENT) PARA-1: 1.1. Applications are invited Online.')
        self.assertEqual(verify(text, self.TARGET).verdict, IdentityVerdict.MATCH)

    def test_sibling_notification_mismatches(self):
        text = ('EXAMPLE STATE BOARD: CAPITAL NOTIFICATION NO. 03/2024, DATED: 21/02/2024 '
                'GROUP-II SERVICES (GENERAL RECRUITMENT) PARA-1: 1.1. Applications are invited Online.')
        self.assertEqual(verify(text, self.TARGET).verdict, IdentityVerdict.MISMATCH)

    def test_previous_cycle_notice_is_another_exam(self):
        """The year sits in the notice number and dateline *before* the title. A 2022 notice
        for the same recruitment must not supply facts to the 2024 cycle."""
        text = ('EXAMPLE STATE BOARD: CAPITAL NOTIFICATION NO. 04/2022, DATED: 26/04/2022 '
                'GROUP-I SERVICES (GENERAL RECRUITMENT) PARA-1: 1.1. Applications are invited Online.')
        check = verify(text, self.TARGET)
        self.assertEqual(check.verdict, IdentityVerdict.MISMATCH)
        self.assertTrue(any('2022' in r for r in check.reasons), check.reasons)

    def test_body_mentions_do_not_make_a_notice_ambiguous(self):
        text = ('EXAMPLE STATE BOARD NOTIFICATION NO. 02/2024, DATED: 19/02/2024 GROUP-I SERVICES (GENERAL RECRUITMENT). '
                'Applications are invited. ' + 'Filler sentence about the scheme of the examination. ' * 40 +
                'The candidate must have passed the Seventh Class Examination with Telugu as a subject. '
                'Centres for the Preliminary Test and Written Examination will be announced.')
        check = verify(text, self.TARGET)
        self.assertEqual(check.verdict, IdentityVerdict.MATCH, check.reasons)
        self.assertIn('title block', check.reasons[0])

    def test_dashed_ordinal_in_title_phrase(self):
        text = 'SCHEME AND SYLLABUS FOR RECRUITMENT TO THE POSTS OF GROUP – I SERVICES (HONS. DEGREE STANDARD)'
        self.assertEqual(verify(text, self.TARGET).verdict, IdentityVerdict.MATCH)


class TestListingCrawl(unittest.TestCase):
    """The exam's documents are linked from a site-wide listing page, one level below the seed,
    with anchors whose text is only the recruitment's name."""

    HOME = ('<html><head><title>Example State Board</title></head><body>'
            '<a href="/notifications">Notifications</a><a href="/Results">Results</a>'
            '<a href="/contact">Contact Us</a></body></html>')
    LISTING = ('<html><head><title>Example State Board</title></head><body><table>'
               '<tr><td><a target="_blank" href ="preview/AAA"><i class="fa"></i>&nbsp;02/2024 - GROUP-I SERVICES</a></td></tr>'
               '<tr><td><a target="_blank" href ="preview/BBB"><i class="fa"></i>&nbsp;03/2024 - GROUP-II SERVICES</a></td></tr>'
               '<tr><td><a target="_blank" href ="preview/CCC">Corrigendum to Group-I Services notification</a></td></tr>'
               '</table></body></html>')
    RESULTS = ('<html><head><title>Results</title></head><body>'
               '<a href="preview/RRR">Group-I Services Preliminary Test Result</a></body></html>')

    def _site(self, url, **kw):
        page = {'https://xbrd.example.gov.in/home': self.HOME,
                'https://xbrd.example.gov.in/notifications': self.LISTING,
                'https://xbrd.example.gov.in/Results': self.RESULTS}.get(url)
        if page is None:
            raise S.FetchError(url)
        d = Document(url=url, kind='HTML', fetched_at='x', text='')
        d.html = page
        return d

    def test_listing_pages_are_crawled_and_gated(self):
        resolved = ResolvedExam(query='XBRD Group-I Services', official_name='XBRD Group-I Services', year='2024',
                                authority=Authority(name='Example State Board', domain='https://xbrd.example.gov.in', confidence=0.9),
                                seed_urls=['https://xbrd.example.gov.in/home'])
        with patch.object(D, 'load_html', side_effect=self._site), \
             patch.object(D, '_search_for_missing_kinds', lambda *a, **k: None):
            out = D.discover(resolved, exam_id='exam-xbrd-group-i-2024')
        by_url = {d.url: d for d in out.docs}
        self.assertIn('https://xbrd.example.gov.in/preview/AAA', by_url, out.log)
        own = by_url['https://xbrd.example.gov.in/preview/AAA']
        self.assertEqual(own.relevance, Relevance.DIRECT)
        self.assertEqual(own.kind, DocKind.NOTIFICATION)            # inherited from the listing's own kind
        self.assertEqual(by_url['https://xbrd.example.gov.in/preview/CCC'].kind, DocKind.CORRIGENDUM)
        self.assertEqual(by_url['https://xbrd.example.gov.in/preview/RRR'].kind, DocKind.RESULT)
        self.assertNotIn('https://xbrd.example.gov.in/preview/BBB', by_url)  # the sibling's notification
        self.assertFalse(any(u.endswith('/contact') for u in by_url))


class TestContentKind(unittest.TestCase):
    def test_unknown_link_classified_from_its_own_text(self):
        from ..exam_authoring.record import ExamRecord
        rec = ExamRecord(exam_id='exam-x-2024', code='X', title='X', authority_name='X', official_domain='https://x.gov.in')
        doc = DiscoveredDoc(url='https://x.gov.in/preview/AAA', kind=DocKind.UNKNOWN, title='02/2024 - GROUP-I SERVICES',
                            relevance=Relevance.DIRECT)
        pdf = Document(url=doc.url, kind='PDF', fetched_at='x', pages=['NOTIFICATION NO. 02/2024, DATED: 19/02/2024 GROUP-I SERVICES'])
        B._reclassify_from_content(doc, pdf, rec)
        self.assertEqual(doc.kind, DocKind.NOTIFICATION)
        known = DiscoveredDoc(url='u', kind=DocKind.SYLLABUS, title='t', relevance=Relevance.DIRECT)
        B._reclassify_from_content(known, pdf, rec)
        self.assertEqual(known.kind, DocKind.SYLLABUS)               # a known kind is never rewritten

    def test_build_reads_notification_found_only_by_content(self):
        """End to end, offline: the notification's link says only the recruitment's name, its URL
        has no extension, and its text carries the age clause — the field is read from it."""
        notice = ('EXAMPLE STATE BOARD NOTIFICATION NO. 02/2024, DATED: 19/02/2024 GROUP-I SERVICES (GENERAL RECRUITMENT). '
                  'Applications are invited Online through https://otr.example.gov.in. '
                  '2. Age Limits: A candidate must have attained the age of 18 years and must not have attained the age '
                  'of 44 years as on 01/07/2024.')
        listing = ('<html><head><title>Example State Board</title></head><body>'
                   '<a href ="preview/AAA">02/2024 - GROUP-I SERVICES</a></body></html>')

        def fake_resolve(query, year=''):
            return ResolvedExam(query='XBRD Group-I Services', official_name='XBRD Group-I Services', year='2024',
                                authority=Authority(name='Example State Board', domain='https://xbrd.example.gov.in', confidence=0.9),
                                seed_urls=['https://xbrd.example.gov.in/notifications'])

        def fake_load_html(url, **kw):
            d = Document(url=url, kind='HTML', fetched_at='x', text='')
            d.html = listing
            return d

        def fake_load(doc):
            if doc.url.endswith('/preview/AAA'):
                return Document(url=doc.url, kind='PDF', fetched_at='x', pages=[notice])
            return fake_load_html(doc.url)

        with patch.object(B, 'resolve', fake_resolve), patch.object(D, 'load_html', fake_load_html), \
             patch.object(B, '_load', fake_load), patch.object(D, '_search_for_missing_kinds', lambda *a, **k: None):
            result = B.build('XBRD Group-I Services', year='2024')
        rec = result.record
        kinds = {d.url: d.kind for d in result.sources.docs}
        self.assertEqual(kinds.get('https://xbrd.example.gov.in/preview/AAA'), DocKind.NOTIFICATION)
        age = rec.fields.get('ageLimits')
        self.assertIsNotNone(age)
        self.assertIn(age.status, (Status.FOUND, Status.NEEDS_REVIEW), age.note)
        self.assertEqual((age.value['minAge'], age.value['maxAge']), (18, 44))


class TestEstateAndLoadOrder(unittest.TestCase):
    def test_sibling_hosts_are_one_authority(self):
        self.assertEqual(S.estate_of('otr.xbrd.gov.in'), 'xbrd.gov.in')
        self.assertEqual(S.estate_of('websitenew.xbrd.gov.in'), 'xbrd.gov.in')
        self.assertEqual(S.estate_of('www.ibps.in'), 'ibps.in')
        self.assertTrue(S.same_estate('otr.xbrd.gov.in', 'websitenew.xbrd.gov.in'))
        self.assertFalse(S.same_estate('other.gov.in', 'websitenew.xbrd.gov.in'))
        self.assertFalse(S.same_estate('xbrd.gov.in.evil.example', 'xbrd.gov.in'))

    def test_isolation_accepts_the_authoritys_own_portal_and_refuses_others(self):
        from ..exam_authoring.record import ExamRecord
        from ..exam_authoring.verify import IsolationError, assert_single_authority
        rec = ExamRecord(exam_id='exam-x-2024', code='X', title='X', authority_name='X',
                         official_domain='https://websitenew.xbrd.gov.in')
        rec.sources_read += ['https://websitenew.xbrd.gov.in/notifications', 'https://otr.xbrd.gov.in/login']
        assert_single_authority(rec)                                      # no raise
        rec.sources_read.append('https://coaching.example.com/xbrd')
        with self.assertRaises(IsolationError):
            assert_single_authority(rec)

    def test_most_specific_documents_are_read_first(self):
        docs = [DiscoveredDoc(url='u1', kind=DocKind.EXAM_PAGE, title='site', relevance=Relevance.DIRECT, matched=['xbrd']),
                DiscoveredDoc(url='u2', kind=DocKind.NOTIFICATION, title='other', relevance=Relevance.INHERITED, matched=[]),
                DiscoveredDoc(url='u3', kind=DocKind.NOTIFICATION, title='own', relevance=Relevance.DIRECT, matched=['group i']),
                DiscoveredDoc(url='u4', kind=DocKind.UNKNOWN, title='x', relevance=Relevance.DIRECT, matched=['xbrd'])]
        self.assertEqual([d.url for d in B._load_order(docs)], ['u3', 'u1', 'u4', 'u2'])


class TestHumanReview(unittest.TestCase):
    """The intervention model: a person approves a reading or withholds one; nothing else."""

    def _rec(self):
        from ..exam_authoring.record import Citation, ExamRecord
        rec = ExamRecord(exam_id='exam-x-2024', code='X', title='X', authority_name='X', official_domain='https://x.gov.in')
        cit = Citation(document_title='notice', url='https://x.gov.in/n', page=3, excerpt='Minimum Age (18 years)', verified_date='2024-01-01')
        rec.set(Field.needs_review('ageLimits', {'minAge': 18, 'maxAge': 46}, 'post-scoped limits', cit))
        rec.set(Field.found('vacancies', 1, cit))
        rec.set(Field.not_published('cutoffs', 'none'))
        return rec

    def test_approve_keeps_the_citation_and_names_the_reviewer(self):
        from .review import FieldReview, ReviewDecision, apply_reviews
        rec = self._rec()
        out = apply_reviews(rec, [FieldReview('ageLimits', ReviewDecision.APPROVE, 'reviewer A', 'band confirmed against p.3')])
        f = rec.fields['ageLimits']
        self.assertEqual((f.status, f.value['minAge']), (Status.FOUND, 18))
        self.assertEqual(f.citation.url, 'https://x.gov.in/n')
        self.assertIn('reviewer A', f.note)
        self.assertEqual(out.applied, ['ageLimits'])

    def test_withhold_is_our_gap_not_their_silence(self):
        from .review import FieldReview, ReviewDecision, apply_reviews
        rec = self._rec()
        apply_reviews(rec, [FieldReview('vacancies', ReviewDecision.WITHHOLD, 'reviewer A', 'a clause number, not a count')])
        f = rec.fields['vacancies']
        self.assertEqual(f.status, Status.NOT_EXTRACTED)
        self.assertIn('withheld by reviewer', f.note)

    def test_review_cannot_invent_or_unpublish(self):
        from .review import FieldReview, ReviewDecision, apply_reviews
        rec = self._rec()
        out = apply_reviews(rec, [
            FieldReview('cutoffs', ReviewDecision.APPROVE, 'reviewer A', value={'x': 1}),   # nothing cited to approve
            FieldReview('attempts', ReviewDecision.APPROVE, 'reviewer A', value=3),         # never read
            FieldReview('ageLimits', ReviewDecision.APPROVE, '', 'anonymous'),              # no reviewer
        ])
        self.assertEqual(out.applied, [])
        self.assertEqual(rec.fields['cutoffs'].status, Status.NOT_PUBLISHED)
        self.assertNotIn('attempts', rec.fields)
        self.assertEqual(rec.fields['ageLimits'].status, Status.NEEDS_REVIEW)

    def test_reviews_reach_the_gate_through_the_orchestrator(self):
        from . import orchestrate as O
        from .review import FieldReview, ReviewDecision
        from ..exam_authoring.record import Citation, ExamRecord
        from .gate import BuildState
        from .resolve import Authority, ResolvedExam
        from types import SimpleNamespace
        rec = ExamRecord(exam_id='exam-x-2026', code='X', title='X 2026', authority_name='X', official_domain='https://x.gov.in')
        cit = Citation(document_title='notice', url='https://x.gov.in/n', page=1, excerpt='...', verified_date='2026-01-01')
        for name in ('officialName', 'authority', 'applicationPortal', 'dates'):
            rec.set(Field.found(name, 'v', cit))
        rec.set(Field.needs_review('ageLimits', {'minAge': 18, 'maxAge': 30}, 'unconfident', cit))
        rec.sources_read.append('https://x.gov.in/n')
        resolved = ResolvedExam(query='X', official_name='X 2026', year='2026',
                                authority=Authority(name='X', domain='https://x.gov.in', confidence=0.9), seed_urls=[])
        fake = lambda *a, **k: SimpleNamespace(resolved=resolved, sources=SimpleNamespace(docs=[], rejected=[], log=[]),
                                               coverage=SimpleNamespace(supplied={}), record=rec,
                                               build_state=BuildState.COMPLETE, identity={}, completeness=None)
        real = O.build
        O.build = fake
        try:
            blocked = O.orchestrate('X', year='2026')
            self.assertEqual(blocked.state, O.OrchestrationState.BLOCKED_BY_GATE)
            rec.set(Field.needs_review('ageLimits', {'minAge': 18, 'maxAge': 30}, 'unconfident', cit))
            passed = O.orchestrate('X', year='2026', reviews=[FieldReview('ageLimits', ReviewDecision.APPROVE, 'reviewer A')])
        finally:
            O.build = real
        self.assertEqual(passed.state, O.OrchestrationState.STAGED, passed.reason)
        self.assertEqual(passed.reviews['applied'], ['ageLimits'])


class TestOfficialNameIsNotTheAuthority(unittest.TestCase):
    def test_home_page_title_does_not_become_the_exam_name(self):
        from .search import Hit
        from . import names as N
        hits = [Hit(title='Example State Board - XBRD', url='https://xbrd.example.gov.in/', content='XBRD Group-I services notification', trust='OFFICIAL'),
                Hit(title='Example State Board - XBRD', url='https://xbrd.example.gov.in/notifications', content='Group-I', trust='OFFICIAL')]

        class _Name:
            value = 'Example State Board'
            is_identity_evidence = True
            status = type('S', (), {'value': 'VERIFIED'})()
            source_url = 'https://xbrd.example.gov.in/'

        from . import resolve as R
        with patch.object(R, 'search', return_value=hits), patch.object(N, 'resolve_name', return_value=_Name()):
            resolved = R.resolve('XBRD Group-I Services', year='2024')
        self.assertEqual(resolved.official_name, 'XBRD Group-I Services')
        self.assertNotIn('example', exam_aliases(resolved.query, resolved.official_name))


if __name__ == '__main__':
    unittest.main()
