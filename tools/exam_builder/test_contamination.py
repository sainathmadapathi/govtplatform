"""Content isolation and data isolation are different protections.

This is the test that justifies building the first one. It constructs a build in which a
sibling exam's document reaches the extractor, and shows that:

    * the DATA isolation proof passes — only the target exam's record was written
    * and yet, without the CONTENT gate, the record would carry the sibling's fee

So a green isolation proof is not evidence that the data is right. The content gate is what
makes it right, and it is verified here by running the real builder twice over the same
documents: once with the gate and once with it disabled.

Run: python -m tools.exam_builder.test_contamination
"""
from __future__ import annotations

from ..exam_authoring.record import Status
from ..exam_authoring.sources import Document
from . import build as B
from . import discover as D
from .identity import IdentityVerdict
from .publish import fingerprint
from .resolve import Authority, ResolvedExam

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


# Deliberately silent on the fee. The only fee anywhere in this build belongs to the
# sibling exam, so if it appears in the record the contamination is unambiguous.
TARGET_NOTICE = """
Staff Selection Commission. Notice of Examination.
Combined Graduate Level Examination, 2026.
Applications are invited for the Combined Graduate Level Examination, 2026 for filling up
various Group B and Group C posts in Ministries and Departments.
"""

#: The same authority, the same year, a different exam — and a different fee.
SIBLING_NOTICE = """
Staff Selection Commission. Notice of Examination.
Combined Higher Secondary Level Examination, 2026.
Applications are invited for the Combined Higher Secondary Level Examination, 2026.
FEE: Candidates are required to pay a fee of Rs. 777/- (Rupees Seven Hundred Seventy Seven
only) for this recruitment.
"""

PAGE_HTML = """<html><head><title>Combined Graduate Level Examination 2026</title></head>
<body><table>
<tr><td>Date of Notification</td><td>05/06/2026</td></tr>
<tr><td>Last Date for Receipt of Applications</td><td>30/06/2026 - 11:00pm</td></tr>
</table>
<a href="/pdf/cgl-2026-notice.pdf">Combined Graduate Level Examination 2026 Notice</a>
<a href="/pdf/chsl-2026-notice.pdf">Notice of Examination</a>
</body></html>"""


def _run(*, content_gate: bool):
    """Run the real builder over both documents, with the content gate on or off."""
    page_url = 'https://ssc.gov.in/cgl-2026'

    def fake_resolve(query, year=''):
        return ResolvedExam(
            query='SSC CGL 2026',
            official_name='SSC Combined Graduate Level Examination 2026',
            year='2026',
            authority=Authority(name='Staff Selection Commission',
                                domain='https://ssc.gov.in', confidence=0.9),
            seed_urls=[page_url])

    def fake_load_html(url, **kw):
        doc = Document(url=url, kind='HTML', fetched_at='2026-09-17', text='')
        doc.html = PAGE_HTML
        return doc

    def fake_load(doc):
        if doc.url.endswith('chsl-2026-notice.pdf'):
            return Document(url=doc.url, kind='PDF', fetched_at='2026-09-17',
                            pages=[SIBLING_NOTICE])
        if doc.is_pdf:
            return Document(url=doc.url, kind='PDF', fetched_at='2026-09-17',
                            pages=[TARGET_NOTICE])
        return fake_load_html(doc.url)

    def no_search(out, resolved, words, host, siblings):
        out.log.append('targeted search skipped (offline fixture)')

    real_verify = B.verify_identity
    if not content_gate:
        # Disable only the content gate, changing nothing else, so the comparison isolates
        # exactly what it buys.
        from .identity import IdentityCheck
        B.verify_identity = lambda *a, **k: IdentityCheck(IdentityVerdict.MATCH)

    saved = (B.resolve, D.load_html, B._load, D._search_for_missing_kinds)
    B.resolve, D.load_html, B._load, D._search_for_missing_kinds = (
        fake_resolve, fake_load_html, fake_load, no_search)
    try:
        return B.build('SSC CGL 2026')
    finally:
        B.resolve, D.load_html, B._load, D._search_for_missing_kinds = saved
        B.verify_identity = real_verify


# ------------------------------------------------------------------------------ tests
def test_without_the_content_gate_the_sibling_contaminates() -> None:
    result = _run(content_gate=False)
    fee = result.record.fields.get('fee')
    got = fee.value['amounts'] if (fee and fee.usable) else None
    # The target says nothing about a fee. 777 can only have come from the sibling exam.
    check('without the gate, the sibling document supplies a fee the target never states',
          got is not None and '777' in got, True)


def test_with_the_content_gate_the_sibling_is_excluded() -> None:
    result = _run(content_gate=True)

    verdicts = {url: c.verdict for url, c in result.identity.items()}
    sibling = [u for u in verdicts if u.endswith('chsl-2026-notice.pdf')]
    check('the sibling document was seen', bool(sibling), True)
    if sibling:
        check('and judged MISMATCH on its own content',
              verdicts[sibling[0]], IdentityVerdict.MISMATCH)

    fee = result.record.fields.get('fee')
    # The target states no fee, so the honest outcome is that none was read — never the
    # sibling's. An unread field is a gap we own; a borrowed one is a lie about this exam.
    check('the sibling’s fee does not reach this record',
          bool(fee and fee.usable and '777' in (fee.value or {}).get('amounts', [])), False)
    check('and the field is reported as unread rather than filled',
          fee.status if fee else None, Status.NOT_EXTRACTED)


def test_data_isolation_passes_either_way() -> None:
    """The point of the whole file: the isolation proof cannot detect this problem."""
    register = ("export const A_EXAM: Exam = {\n  id: 'exam-other-1',\n};\n\n"
                "export const B_EXAM: Exam = {\n  id: 'exam-ssc-ssc-cgl-2026',\n};\n")
    before = fingerprint(register)
    # A rebuild of the target that writes the *wrong* fee still touches only the target.
    after_ok = fingerprint(register.replace("id: 'exam-ssc-ssc-cgl-2026',",
                                            "id: 'exam-ssc-ssc-cgl-2026', fee: '100',"))
    after_bad = fingerprint(register.replace("id: 'exam-ssc-ssc-cgl-2026',",
                                             "id: 'exam-ssc-ssc-cgl-2026', fee: '777',"))
    check('the neighbour is untouched when the data is right',
          before['exam-other-1'] == after_ok['exam-other-1'], True)
    check('the neighbour is untouched when the data is WRONG too',
          before['exam-other-1'] == after_bad['exam-other-1'], True)
    check('so data isolation alone cannot tell the two apart',
          after_ok['exam-other-1'] == after_bad['exam-other-1'], True)


def main() -> int:
    test_without_the_content_gate_the_sibling_contaminates()
    test_with_the_content_gate_the_sibling_is_excluded()
    test_data_isolation_passes_either_way()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('contamination: content isolation and data isolation shown to be different')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
