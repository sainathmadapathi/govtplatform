"""Content isolation: does a document's own text belong to the target exam?

This is a different question from the one publish.py answers. The isolation proof shows a
build wrote only to SSC; these checks show that what it wrote *is* SSC. A pipeline can pass
the first and fail the second, and the result is a perfectly isolated record full of another
exam's rules.

Every fixture below is a document from the *right authority* — that is the whole point. A
correct domain is not identity evidence.

Run: python -m tools.exam_builder.test_identity
"""
from __future__ import annotations

from .identity import (ExamIdentity, IdentityVerdict, exam_references,
                       field_is_attributable, verify)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


TARGET = ExamIdentity(
    exam_id='exam-ssc-ssc-cgl-2026',
    query='SSC CGL 2026',
    official_name='SSC Combined Graduate Level Examination 2026',
    year='2026',
    authority_name='Staff Selection Commission')

# --------------------------------------------------------------------------- fixtures
OWN_NOTICE = """
Staff Selection Commission
Notice of Examination
Combined Graduate Level Examination, 2026
Applications are invited for the Combined Graduate Level Examination, 2026 for filling up
various Group B and Group C posts. Candidates are required to pay a fee of Rs. 100/-.
"""

SIBLING_NOTICE = """
Staff Selection Commission
Notice of Examination
Combined Higher Secondary Level Examination, 2026
Applications are invited for the Combined Higher Secondary Level Examination, 2026 for
filling up posts of Lower Division Clerk. The fee is Rs. 100/-.
"""

WRONG_YEAR = """
Staff Selection Commission
Combined Graduate Level Examination, 2024
The Combined Graduate Level Examination, 2024 was conducted in September 2024.
Cut-off marks for the Combined Graduate Level Examination, 2024 are given below.
"""

MULTI_EXAM_CALENDAR = """
Staff Selection Commission — Annual Calendar
Combined Graduate Level Examination, 2026 — date of advertisement 05.06.2026.
Combined Higher Secondary Level Examination, 2026 — date of advertisement 20.06.2026.
Multi Tasking Staff Examination, 2026 — date of advertisement 26.06.2026.
"""

NO_EXAM_NAMED = """
Staff Selection Commission
The Commission has decided to revise the timings of its regional offices with effect from
the first of next month. Officers are requested to take note.
"""


# ------------------------------------------------------------------------------ tests
def test_own_document_matches() -> None:
    c = verify(OWN_NOTICE, TARGET, source_url='https://ssc.gov.in/a.pdf')
    check('the exam’s own notice MATCHes', c.verdict, IdentityVerdict.MATCH)
    check('and may supply facts', c.may_supply_facts, True)
    check('identity evidence is verified verbatim',
          c.evidence is not None and c.evidence.span in ' '.join(OWN_NOTICE.split()), True)


def test_sibling_exam_is_rejected() -> None:
    """The case that matters: same authority, same year, different exam."""
    c = verify(SIBLING_NOTICE, TARGET, source_url='https://ssc.gov.in/b.pdf')
    check('a sibling exam’s notice MISMATCHes', c.verdict, IdentityVerdict.MISMATCH)
    check('and may NOT supply facts', c.may_supply_facts, False)
    check('the intruder is named', bool(c.competing), True)


def test_wrong_year_is_rejected() -> None:
    c = verify(WRONG_YEAR, TARGET, source_url='https://ssc.gov.in/c.pdf')
    check('the right exam in the wrong year MISMATCHes', c.verdict, IdentityVerdict.MISMATCH)
    check('and may NOT supply facts', c.may_supply_facts, False)


def test_multi_exam_page_is_ambiguous() -> None:
    c = verify(MULTI_EXAM_CALENDAR, TARGET, source_url='https://ssc.gov.in/cal.pdf')
    check('a calendar listing several exams is AMBIGUOUS',
          c.verdict, IdentityVerdict.AMBIGUOUS)
    check('AMBIGUOUS is not a soft MATCH', c.may_supply_facts, False)
    check('it names the target among others', bool(c.matched), True)
    check('and names the others', len(c.competing) >= 2, True)


def test_ambiguous_can_still_attribute_a_specific_span() -> None:
    """A multi-exam document may supply a fact where the fact's own span names the exam."""
    ours = ('Combined Graduate Level Examination, 2026 — date of advertisement 05.06.2026.')
    theirs = ('Combined Higher Secondary Level Examination, 2026 — date of advertisement '
              '20.06.2026.')
    check('a span naming this exam is attributable',
          field_is_attributable(MULTI_EXAM_CALENDAR, TARGET, ours), True)
    check('a span naming another exam is not',
          field_is_attributable(MULTI_EXAM_CALENDAR, TARGET, theirs), False)


def test_document_naming_no_exam_is_ambiguous() -> None:
    c = verify(NO_EXAM_NAMED, TARGET, source_url='https://ssc.gov.in/d.pdf')
    check('a document that names no exam cannot vouch for itself',
          c.verdict, IdentityVerdict.AMBIGUOUS)
    check('and may not supply facts', c.may_supply_facts, False)


def test_domain_is_not_identity() -> None:
    """Every fixture above is on the authority's own domain; three of five still fail."""
    verdicts = [verify(t, TARGET, source_url='https://ssc.gov.in/x').verdict
                for t in (OWN_NOTICE, SIBLING_NOTICE, WRONG_YEAR,
                          MULTI_EXAM_CALENDAR, NO_EXAM_NAMED)]
    check('being on the right domain does not make a document the right exam',
          verdicts.count(IdentityVerdict.MATCH), 1)


def test_reference_extraction_is_authority_neutral() -> None:
    """The same primitive must read other authorities' title styles."""
    cases = [
        ('Civil Services (Preliminary) Examination, 2026', 'Civil Services'),
        ('Common Recruitment Process for Probationary Officers Recruitment 2026', 'Recruitment'),
        ('Group-I Services Examination 2026 notification', 'Services Examination'),
    ]
    for text, needle in cases:
        refs = exam_references(text)
        check(f'a reference is found in {needle!r}', bool(refs), True)


def main() -> int:
    test_own_document_matches()
    test_sibling_exam_is_rejected()
    test_wrong_year_is_rejected()
    test_multi_exam_page_is_ambiguous()
    test_ambiguous_can_still_attribute_a_specific_span()
    test_document_naming_no_exam_is_ambiguous()
    test_domain_is_not_identity()
    test_reference_extraction_is_authority_neutral()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('content identity: all checks pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
