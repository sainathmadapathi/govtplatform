"""Offline end-to-end check of the orchestrator's routing.

The decision this verifies is the one the whole pipeline is built around: a contract field
with no discovered source must come out NOT_PUBLISHED (a claim about the authority), while a
field whose source *was* found but whose extractor found nothing must come out NOT_EXTRACTED
(a claim about us). Getting these the wrong way round would tell a candidate an authority is
silent when the fault is ours.

No network: the resolver and the document loader are both replaced with fixtures.

Run: python -m tools.exam_builder.test_build
"""
from __future__ import annotations

import re

from ..exam_authoring.record import Status
from ..exam_authoring.sources import Document
from . import build as B
from . import discover as D
from .resolve import Authority, ResolvedExam

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


#: A notice carrying an age clause and a fee clause, and nothing else the contract wants.
#: It names its examination, as every real notice does. (Changed 2026-09-29: it used to name
#: none, which only worked while a document that could not be identified still supplied
#: exam-specific facts. It no longer can -- an unnamed corrigendum supplied one exam's
#: deadline to another -- so a notice naming no exam now supplies no age, fee or date.
#: test_an_unnamed_notice_supplies_no_exam_fact below holds that rule.)
NOTICE_TEXT = """
NOTICE OF EXAMINATION: Combined Graduate Level Examination, 2026.
Candidates are required to apply online by using the website
https://ssconline.gov.in.
2. Age Limits: A candidate must have attained the age of 18 years and must not have attained
the age of 32 years on the 1st of August, 2026 i.e., the candidate must have been born not
earlier than 2nd August, 1994 and not later than 1st August, 2008.
4. FEE: All the candidates (Except Female/SC/ST/Persons with Benchmark Disability Candidates
who are exempted from payment of fee) are required to pay fee of Rs. 100/- by using Net
Banking or UPI Payment.
"""

EXAM_PAGE_HTML = """<html><head><title>SSC Combined Graduate Level Examination 2026</title></head>
<body><table>
<tr><td>Date of Notification</td><td>04/06/2026</td></tr>
<tr><td>Last Date for Receipt of Applications</td><td>30/06/2026 - 11:00pm</td></tr>
</table>
<a href="/pdf/cgl-2026-notice.pdf">CGL 2026 Notice of Examination</a>
</body></html>"""


def _fixtures():
    page_url = 'https://ssc.gov.in/cgl-2026'
    notice_url = 'https://ssc.gov.in/pdf/cgl-2026-notice.pdf'

    def fake_resolve(query, year=''):
        return ResolvedExam(
            query='SSC CGL 2026',
            official_name='SSC Combined Graduate Level Examination 2026',
            year='2026',
            authority=Authority(name='Staff Selection Commission',
                                domain='https://ssc.gov.in', confidence=0.83),
            seed_urls=[page_url])

    def fake_load_html(url, **kw):
        # The page's text is its rendered HTML, as sources.load_html gives it. (It was '',
        # which no real load produces, and which left the page with nothing to identify it by.)
        text = ' '.join(re.sub(r'<[^>]+>', ' ', EXAM_PAGE_HTML).split())
        doc = Document(url=url, kind='HTML', fetched_at='2026-09-17', text=text)
        doc.html = EXAM_PAGE_HTML
        return doc

    def fake_load(doc):
        if doc.is_pdf:
            return Document(url=doc.url, kind='PDF', fetched_at='2026-09-17',
                            pages=[NOTICE_TEXT])
        return fake_load_html(doc.url)

    def no_search(out, resolved, words, host, siblings):
        out.log.append('targeted search skipped (offline fixture)')

    return page_url, notice_url, fake_resolve, fake_load_html, fake_load, no_search


def test_routing() -> None:
    page_url, notice_url, fake_resolve, fake_load_html, fake_load, no_search = _fixtures()

    saved = (B.resolve, D.load_html, B._load, D._search_for_missing_kinds)
    B.resolve, D.load_html, B._load, D._search_for_missing_kinds = (
        fake_resolve, fake_load_html, fake_load, no_search)
    try:
        result = B.build('SSC CGL 2026')
    finally:
        B.resolve, D.load_html, B._load, D._search_for_missing_kinds = saved

    rec = result.record
    check('exam id from the exam, not a table', rec.exam_id, 'exam-ssc-ssc-cgl-2026')
    check('authority carried through', rec.authority_name, 'Staff Selection Commission')

    # --- sourced from the notice
    age = rec.fields.get('ageLimits')
    # FOUND or NEEDS_REVIEW are both real readings with verified evidence; they differ only
    # in how strongly the wording supported it.
    check('ageLimits read', age.status in (Status.FOUND, Status.NEEDS_REVIEW) if age else False, True)
    if age and age.usable:
        # The semantic reader returns the band plus the crucial date it is reckoned on.
        check('age band read correctly',
              (age.value['minAge'], age.value['maxAge'], age.value['asOn']),
              (18, 32, '2026-08-01'))
        check('age cites the document it came from', bool(age.citation.url), True)

    fee = rec.fields.get('fee')
    check('fee read', fee.status in (Status.FOUND, Status.NEEDS_REVIEW) if fee else False, True)
    if fee and fee.usable:
        check('fee amount read', fee.value['amounts'][:1], ['100'])

    # --- sourced from the exam page's table
    dates = rec.fields.get('dates')
    check('dates found from the page table', dates.status if dates else None, Status.FOUND)
    if dates and dates.ok:
        kinds = {d['type'] for d in dates.value}
        check('close date recognised', 'APPLICATION_CLOSE' in kinds, True)

    # --- THE ROUTING THAT MATTERS ------------------------------------------------------
    # Nothing discovered could answer these, so they are a statement about the authority.
    keys = rec.fields.get('answerKeys')
    check('answerKeys -> NOT_PUBLISHED (no such document found)',
          keys.status if keys else None, Status.NOT_PUBLISHED)
    check('and it names what was looked for',
          'ANSWER_KEY' in (keys.note if keys else ''), True)

    results = rec.fields.get('results')
    check('results -> NOT_PUBLISHED', results.status if results else None,
          Status.NOT_PUBLISHED)

    # The notice WAS found and read, but no attempts clause is in it -> our gap, not theirs.
    attempts = rec.fields.get('attempts')
    check('attempts -> NOT_EXTRACTED (document read, clause absent)',
          attempts.status if attempts else None, Status.NOT_EXTRACTED)
    check('and it says so in our own terms',
          'do not assume the authority is silent' in (attempts.note if attempts else ''), True)

    # A field whose source exists but which has no reader written is also ours to own.
    syl = rec.fields.get('syllabus')
    check('syllabus -> NOT_EXTRACTED (source present, no extractor yet)',
          syl.status if syl else None, Status.NOT_EXTRACTED)


def test_an_unnamed_notice_supplies_no_exam_fact() -> None:
    """A document whose content names no examination cannot say whose ages it states."""
    global NOTICE_TEXT
    page_url, notice_url, fake_resolve, fake_load_html, fake_load, no_search = _fixtures()
    named, NOTICE_TEXT = NOTICE_TEXT, NOTICE_TEXT.replace(
        'NOTICE OF EXAMINATION: Combined Graduate Level Examination, 2026.', 'NOTICE OF EXAMINATION.')
    saved = (B.resolve, D.load_html, B._load, D._search_for_missing_kinds)
    B.resolve, D.load_html, B._load, D._search_for_missing_kinds = (
        fake_resolve, fake_load_html, fake_load, no_search)
    try:
        rec = B.build('SSC CGL 2026').record
    finally:
        B.resolve, D.load_html, B._load, D._search_for_missing_kinds = saved
        NOTICE_TEXT = named
    for name in ('ageLimits', 'fee'):
        f = rec.fields.get(name)
        check(f'{name} not taken from an unnamed notice', bool(f and f.usable), False)
    # The page does name the exam, so its own table still dates it.
    dates = rec.fields.get('dates')
    check('the exam page still supplies its dates', dates.status if dates else None, Status.FOUND)


def test_two_exams_never_share_an_id() -> None:
    """The id is what every isolation guarantee keys on, so a shared id is a shared record.

    `distinctive_words` drops tokens of two characters or fewer, which is correct for
    matching prose and wrong for naming an exam: "PO" and "SO" are the whole difference
    between two IBPS exams, and "I" and "II" between two APPSC ones. Under that rule
    IBPS PO and IBPS SO were literally the same id, and this repo already says Group-I and
    Group-II must never be pointed at each other.
    """
    from .resolve import stable_exam_id

    names = ['IBPS PO 2026', 'IBPS SO 2026', 'IBPS Clerk 2026',
             'SBI PO 2026', 'SBI SO 2026',
             'SSC CGL 2026', 'SSC CHSL 2026', 'SSC MTS 2026',
             'APPSC Group I 2026', 'APPSC Group II 2026', 'TSPSC Group I 2026',
             'UPSC CDS I 2026', 'UPSC CDS II 2026',
             'RRB Group C 2026', 'RRB Group D 2026', 'LIC AAO 2027']

    ids: dict[str, str] = {}
    for name in names:
        resolved = ResolvedExam(
            query=name, official_name=name, year='2026',
            authority=Authority(name='X', domain='https://example.in', confidence=1.0))
        ids[name] = stable_exam_id(resolved)

    collisions = {}
    for name, eid in ids.items():
        collisions.setdefault(eid, []).append(name)
    shared = {k: v for k, v in collisions.items() if len(v) > 1}
    check('no two exams share an id', shared, {})

    check('the post code survives into the id', 'po' in ids['IBPS PO 2026'].split('-'), True)
    check('and the group numeral does',
          ids['APPSC Group I 2026'] != ids['APPSC Group II 2026'], True)


import unittest as _unittest


class TestEvidencePagePlacement(_unittest.TestCase):
    """The pattern and syllabus readers see one joined text and cite page 1; the builder puts
    each span back on the page that prints it. A heading printed twice (in a scheme table and
    over its syllabus) goes where the rest of its own node is printed."""

    def test_spans_go_to_the_pages_that_print_them(self):
        from types import SimpleNamespace
        from .schema import SourceEvidence, SyllabusNode
        doc = SimpleNamespace(pages=[
            'Notice cover page. Paper-II History and Geography is one of the papers.',
            'Scheme table: Paper-II History and Geography 150 marks.',
            'SYLLABUS Paper-II History and Geography 1. Ancient India and its culture. 2. Rivers of the plateau.'])
        ev = lambda span: SourceEvidence(source_id='d', span=span, page=1)
        paper = SyllabusNode(id='p2', title='Paper-II', evidence=[ev('Paper-II History and Geography')],
                             children=[SyllabusNode(id='t1', title='t1', evidence=[ev('1. Ancient India and its culture.')]),
                                       SyllabusNode(id='t2', title='t2', evidence=[ev('2. Rivers of the plateau.')])])
        first = B._place_tree_pages([paper], doc)
        self.assertEqual([paper.evidence[0].page, paper.children[0].evidence[0].page,
                          paper.children[1].evidence[0].page], [3, 3, 3])
        self.assertEqual(first, 3)

    def test_a_span_found_nowhere_keeps_what_the_reader_gave(self):
        from types import SimpleNamespace
        from .schema import SourceEvidence, SyllabusNode
        doc = SimpleNamespace(pages=['first page text here', 'second page with Unit One Economics'])
        placed = SyllabusNode(id='a', title='a', evidence=[SourceEvidence(source_id='d', span='Unit One Economics', page=1)])
        missing = SyllabusNode(id='b', title='b', evidence=[SourceEvidence(source_id='d', span='Not printed anywhere at all', page=1)])
        B._place_tree_pages([placed, missing], doc)
        self.assertEqual((placed.evidence[0].page, missing.evidence[0].page), (2, 1))


def main() -> int:
    test_routing()
    test_an_unnamed_notice_supplies_no_exam_fact()
    test_two_exams_never_share_an_id()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('build routing: all checks pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())


class TestUnreadableIsOurGap(_unittest.TestCase):
    """A document GovOS could not read says nothing about what the authority published."""

    def test_a_legacy_font_text_layer_is_treated_as_no_text(self):
        from ..exam_authoring.sources import unreadable_text
        # A non-Unicode font extracts as consonant runs; ordinary notice prose does not.
        garbage = ' '.join(['vk;ksx', 'jktLFkku', 'yksd', 'lsok', 'fnukad', 'HkrhZ', 'ijh{kk', 'fu;e'] * 8)
        prose = ('The Commission invites online applications from eligible candidates for recruitment '
                 'to the posts listed below. Candidates must read the instructions carefully before '
                 'applying, and the closing date for the submission of applications is final. ') * 3
        self.assertTrue(unreadable_text(garbage))
        self.assertFalse(unreadable_text(prose))
        self.assertFalse(unreadable_text('SSC CGL TIER-I PWBD OBC EWS ' * 20))   # acronyms are not garbage

    def test_nothing_readable_is_not_extracted_never_not_published(self):
        from types import SimpleNamespace
        scans = [SimpleNamespace(url='https://authority.example/a.pdf')]
        loaded = {'https://authority.example/a.pdf': SimpleNamespace(all_text=lambda: '  \n ')}
        got = B._unread_by_us('feeExemptions', scans, loaded)
        self.assertEqual(got.status, Status.NOT_EXTRACTED)
        self.assertIn('not a statement that the authority published none', got.note)
        loaded_text = {'https://authority.example/a.pdf': SimpleNamespace(all_text=lambda: 'Fee rules.')}
        self.assertIsNone(B._unread_by_us('feeExemptions', scans, loaded_text))

    def test_nothing_admitted_is_not_called_unreadable(self):
        # Every document refused by the identity check: they were readable, and the note
        # must not send a reviewer looking for scans.
        got = B._unread_by_us('feeExemptions', [], {})
        self.assertEqual(got.status, Status.NOT_EXTRACTED)
        self.assertNotIn('readable text', got.note)
        self.assertIn("established as this exam's own", got.note)


class TestNothingPrintedIsSupplied(_unittest.TestCase):

    def test_the_overview_states_no_time_that_was_not_read(self):
        from ..exam_authoring.record import Citation, ExamRecord, Field
        from . import materialize as M
        rec = ExamRecord(exam_id='exam-x-2031', code='X', title='Example Examination 2031',
                         authority_name='Example Commission', official_domain='https://authority.example')
        cite = Citation(document_title='Notice', url='https://authority.example/n.pdf', page=1,
                        clause='', excerpt='Closing date 26.02.2031', verified_date='2031-01-01')
        rec.set(Field.found('dates', [{'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2031-02-26 00:00:00'}], cite))
        text = M._overview(rec)
        self.assertIn('Applications close 2031-02-26.', text)
        self.assertNotIn('00:00', text)

    def test_a_damaged_address_is_not_offered_as_a_link(self):
        from ..exam_authoring import extract as X
        page = ('(ii) The e-Admit Card will be made available on the website http://hpsp.gov.inlen-us/ '
                'for downloading by the candidates. No Admit Card will be sent by post.')
        got = X.admit_card(Document(url='https://authority.example/n.pdf', kind='pdf', fetched_at='2031-01-01', text=page, pages=[page]), 'Notice')
        self.assertEqual(got.value['portalUrl'], '')
        self.assertIn('e-Admit Card will be made available', got.value['text'])
        # A well-formed address is kept (read under the clause heading, whose match does not stop
        # at the first full stop).
        good = ('ISSUANCE OF E-ADMIT CARD: The e-Admit Card will be made available on the website '
                'https://authority.example/admit for downloading by the candidates well before the examination.')
        got = X.admit_card(Document(url='https://authority.example/n.pdf', kind='pdf', fetched_at='2031-01-01', text=good, pages=[good]), 'Notice')
        self.assertEqual(got.value['portalUrl'], 'https://authority.example/admit')
