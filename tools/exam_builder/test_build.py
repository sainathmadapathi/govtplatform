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
NOTICE_TEXT = """
NOTICE OF EXAMINATION. Candidates are required to apply online by using the website
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
        doc = Document(url=url, kind='HTML', fetched_at='2026-09-17', text='')
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
    check('ageLimits found', age.status if age else None, Status.FOUND)
    if age and age.ok:
        check('age band read correctly',
              (age.value['minAge'], age.value['maxAge'], age.value['asOn']),
              (18, 32, '2026-08-01'))
        check('age cites the document it came from', bool(age.citation.url), True)

    fee = rec.fields.get('fee')
    check('fee found', fee.status if fee else None, Status.FOUND)
    if fee and fee.ok:
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


def main() -> int:
    test_routing()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('build routing: all checks pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
