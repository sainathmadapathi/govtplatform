"""Offline checks for the discovery gate — the point where cross-exam leakage would start.

These need no network. They are written against the exact confusions these authorities
actually create: one site hosting many exams, notices that cross-link to each other, and
file names that share every generic word.

Run: python -m tools.exam_builder.test_discover
"""
from __future__ import annotations

from .discover import (DocKind, Relevance, classify_kind, exam_aliases, gate,
                       page_is_specific_to)

# Built the way the engine builds them, not hand-written, so the test exercises the real
# alias set — including the acronym the authority actually uses in its link text.
CGL = exam_aliases('SSC CGL 2026', 'SSC Combined Graduate Level Examination 2026')
CHSL_WORDS = exam_aliases('SSC CHSL 2026', 'SSC Combined Higher Secondary Level Examination 2026')

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def test_kinds() -> None:
    cases = [
        ('Answer Key for CGL Tier-I', DocKind.ANSWER_KEY),
        ('Corrigendum to Notice of Examination', DocKind.CORRIGENDUM),
        ('Revised Notice', DocKind.CORRIGENDUM),
        ('e-Admit Card', DocKind.ADMIT_CARD),
        ('Call Letter download', DocKind.ADMIT_CARD),
        ('Cut-off marks 2026', DocKind.CUTOFF),
        ('Previous Year Question Paper', DocKind.QUESTION_PAPER),
        ('Written Result (with name)', DocKind.RESULT),
        ('Syllabus and Scheme of Examination', DocKind.SYLLABUS),
        ('Calendar of Examinations 2027', DocKind.CALENDAR),
        ('Apply Online', DocKind.APPLICATION_PORTAL),
        ('One Time Registration', DocKind.APPLICATION_PORTAL),
        ('Notice of Examination', DocKind.NOTIFICATION),
        ('Advertisement No. 12/2026', DocKind.NOTIFICATION),
        ('Home', DocKind.UNKNOWN),
        ('Contact Us', DocKind.UNKNOWN),
    ]
    for text, want in cases:
        check(f'classify_kind({text!r})', classify_kind(text), want)

    # A corrigendum *to* a notification is a corrigendum, not the notification.
    check("specificity: 'Corrigendum to Notification'",
          classify_kind('Corrigendum to Notification'), DocKind.CORRIGENDUM)
    # An answer key is not a generic result.
    check("specificity: 'Answer Key'", classify_kind('Answer Key'), DocKind.ANSWER_KEY)


def test_gate() -> None:
    # 1. The link names this exam -> DIRECT, wherever it was found. Note it matches on the
    #    acronym: the authority's link says "CGL" while its page title spells out "Combined
    #    Graduate Level", and an expansion-only gate rejected the exam's own documents.
    rel, matched, _ = gate('CGL 2026 Notice', '/cgl-notice.pdf',
                           exam_words=CGL, page_is_exam_specific=False)
    check('direct match via acronym', (rel, 'cgl' in matched), (Relevance.DIRECT, True))

    # 1b. And the spelled-out form matches just as well.
    rel, matched, _ = gate('Combined Graduate Level Examination notice', '/x.pdf',
                           exam_words=CGL, page_is_exam_specific=False)
    check('direct match via expansion', (rel, 'combined' in matched), (Relevance.DIRECT, True))

    # 2. A bare "Syllabus" link on the exam's own page inherits.
    rel, _, _ = gate('Syllabus', '/syllabus.pdf', exam_words=CGL, page_is_exam_specific=True)
    check('inherits from an exam page', rel, Relevance.INHERITED)

    # 3. The same link on a general page does not.
    rel, _, _ = gate('Syllabus', '/syllabus.pdf', exam_words=CGL, page_is_exam_specific=False)
    check('no inheritance from a general page', rel, Relevance.REJECTED)

    # 4. THE ONE THAT MATTERS: another exam's document, sitting on this exam's page.
    #    Authorities cross-link constantly; inheriting here files CHSL's rules under CGL.
    rel, _, foreign = gate('CHSL Tier-I Answer Key', '/chsl-key.pdf',
                           exam_words=CGL, page_is_exam_specific=True,
                           sibling_exam_words=CHSL_WORDS)
    check('sibling exam rejected on our own page', rel, Relevance.REJECTED)
    check('sibling exam names the intruder', bool(foreign), True)

    # 5. A link naming both stays with us — it is genuinely about this exam too.
    rel, _, _ = gate('CGL and CHSL combined notice', '/x.pdf',
                     exam_words=CGL, page_is_exam_specific=True,
                     sibling_exam_words=CHSL_WORDS)
    check('shared notice kept', rel, Relevance.DIRECT)


def test_page_specificity() -> None:
    check('exam page recognised',
          page_is_specific_to('SSC Combined Graduate Level Examination 2026',
                              '/cgl-2026', CGL), True)
    # One shared word must not qualify: "Combined" is in CGL, CHSL and CDS alike.
    check('one generic word is not specificity',
          page_is_specific_to('Combined Examinations', '/exams', CGL), False)
    check('home page rejected',
          page_is_specific_to('Staff Selection Commission', '/', CGL), False)


def test_discover_end_to_end() -> None:
    """Run the real crawl over a fabricated SSC-shaped page, with no network.

    The page is built to contain the exact trap: an exam-specific CGL page that also links
    to CHSL's documents, which is how every one of these sites is actually laid out.
    """
    from . import discover as D
    from ..exam_authoring.sources import Document
    from .resolve import Authority, ResolvedExam

    page_url = 'https://ssc.gov.in/cgl-2026'
    html = """<html><head><title>SSC Combined Graduate Level Examination 2026</title></head>
    <body>
      <a href="/pdf/CGL-2026-Notice.pdf">CGL 2026 Notice of Examination</a>
      <a href="/pdf/syllabus.pdf">Syllabus</a>
      <a href="/pdf/CHSL-2026-key.pdf">CHSL Tier-I Answer Key</a>
      <a href="/pdf/cgl-corrigendum.pdf">Corrigendum to CGL Notice</a>
      <a href="/">Home</a>
      <a href="/contact">Contact Us</a>
      <a href="https://ssc.gov.in/apply">Apply Online</a>
    </body></html>"""

    def fake_load_html(url, **kw):
        doc = Document(url=url, kind='HTML', fetched_at='2026-09-17', text='')
        doc.html = html
        return doc

    real = D.load_html
    D.load_html = fake_load_html
    try:
        resolved = ResolvedExam(
            query='SSC CGL 2026',
            official_name='SSC Combined Graduate Level Examination 2026',
            year='2026',
            authority=Authority(name='Staff Selection Commission',
                                domain='https://ssc.gov.in', confidence=0.83),
            seed_urls=[page_url])
        chsl = exam_aliases('SSC CHSL 2026',
                            'SSC Combined Higher Secondary Level Examination 2026')
        # Only the words unique to CHSL count as a sibling signal; the two exams share
        # "ssc" and "combined", and treating those as foreign would reject our own pages.
        chsl_only = [w for w in chsl if w not in CGL]
        out = D.discover(resolved, exam_id='exam-ssc-ssc-cgl-2026',
                         sibling_exam_words=chsl_only)
    finally:
        D.load_html = real

    kept = {d.url.rsplit('/', 1)[-1]: d for d in out.docs}
    dropped = {d.url.rsplit('/', 1)[-1] for d in out.rejected}

    check('exam page kept', 'cgl-2026' in kept, True)
    check('own notice kept', 'CGL-2026-Notice.pdf' in kept, True)
    check('own corrigendum kept', 'cgl-corrigendum.pdf' in kept, True)
    check('bare syllabus inherited', 'syllabus.pdf' in kept, True)
    check("sibling exam's key NOT kept", 'CHSL-2026-key.pdf' in kept, False)
    check("sibling exam's key recorded as rejected", 'CHSL-2026-key.pdf' in dropped, True)

    if 'CGL-2026-Notice.pdf' in kept:
        check('notice classified', kept['CGL-2026-Notice.pdf'].kind, DocKind.NOTIFICATION)
    if 'cgl-corrigendum.pdf' in kept:
        check('corrigendum classified', kept['cgl-corrigendum.pdf'].kind, DocKind.CORRIGENDUM)
    if 'syllabus.pdf' in kept:
        check('syllabus inherited, not direct',
              kept['syllabus.pdf'].relevance, Relevance.INHERITED)
    check('navigation chrome not collected',
          any(k in kept for k in ('', 'contact')), False)


def main() -> int:
    test_kinds()
    test_gate()
    test_page_specificity()
    test_discover_end_to_end()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('discovery gate: all checks pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
