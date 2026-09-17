"""Does one extractor read five authorities' different wording?

That is the only question worth asking of this layer. The fixtures below are written in the
styles these bodies actually use — not paraphrases of one another — and the *same*
implementation must read all of them. If a case needs a new pattern added just for it, the
layer has not generalised and the fixture has done its job by saying so.

There is deliberately no branching on authority anywhere in this file or in semantic.py.

Run: python -m tools.exam_builder.test_semantic
"""
from __future__ import annotations

from .evidence import EvidenceStatus
from .semantic import extract, extract_all

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def check_true(label: str, got) -> None:
    check(label, bool(got), True)


# --------------------------------------------------------------------------- fixtures
# Five authorities, five ways of saying the same things.

A_COMMISSION_STYLE = """
4. FEE: All the candidates (Except Female/SC/ST/Persons with Benchmark Disability Candidates
who are exempted from payment of fee) are required to pay fee of Rs. 100/- (Rupees One
Hundred only) by using Net Banking facility or by using Visa/Master/RuPay Credit/Debit Card
or UPI Payment.
(II) Age Limits: A candidate must have attained the age of 21 years and must not have
attained the age of 32 years on the 1st of August, 2026 i.e., the candidate must have been
born not earlier than 2nd August, 1994 and not later than 1st August, 2005.
(III) Minimum Educational Qualification: A candidate must hold a Graduate degree of any of
the Universities incorporated by an Act of the central or State Legislature in India.
(IV) Number of attempts: Every candidate appearing at the examination shall be permitted
six (6) attempts at the examination.
The number of vacancies to be filled through the examination is expected to be approximately
933 which include 33 Vacancies reserved for Persons with Benchmark Disability Category.
"""

B_STAFF_STYLE = """
Application Fee payable: Rs. 100/- (Rupees One Hundred only). Women candidates and
candidates belonging to Scheduled Caste, Scheduled Tribe and Ex-Servicemen eligible for
reservation are exempted from payment of fee. Fee can be paid through BHIM UPI, Net Banking
or by using Visa, Mastercard, Maestro, RuPay Credit or Debit cards.
Age Limit: 18-27 years as on 01-08-2026.
Educational Qualification: Bachelor's Degree from a recognized University or equivalent.
Tier-I will consist of 100 questions carrying 200 marks with a duration of 60 minutes.
There will be negative marking of 0.50 marks for each wrong answer in Tier-I.
Tentative vacancies: 17727 posts.
"""

C_BANKING_STYLE = """
Application Fees/ Intimation Charges (Payable from 01.08.2026 to 21.08.2026) (Online payment
including GST): Rs. 175/- for SC/ST/PWBD candidates and Rs. 850/- for all others.
Candidates should be not below 20 years and not above 30 years of age as on 01.08.2026.
A candidate must possess a Bachelor's Degree in any discipline from a University recognised
by the Government of India.
Number of vacancies: 4455.
The examination will be conducted online and will consist of Paper I Preliminary
Examination of 100 marks and Paper II Main Examination of 200 marks.
"""

D_CORPORATION_STYLE = """
Eligible candidates are required to pay an application fee of one hundred rupees. Persons
with Benchmark Disability are exempted.
The minimum age limit is 21 years and the maximum age limit is 30 years as on 01.09.2026.
There is no restriction on the number of attempts for this recruitment.
Candidates should hold a Bachelor's Degree from a recognised University.
Total number of posts: 300.
"""

E_STATE_COMMISSION_STYLE = """
Candidates are required to pay a non-refundable application processing fee of INR 250/-
through the online payment gateway. No fee is payable by candidates belonging to Scheduled
Caste, Scheduled Tribe and Persons with Benchmark Disabilities.
Age: The candidate should have attained the age of 18 years and must not have attained the
age of 42 years as on 01.07.2026.
Qualification: The applicant must possess a Degree of any University recognised by UGC.
Stage-I Screening Test carries 150 marks and Stage-II Main Examination carries 300 marks.
"""

FIXTURES = {
    'commission': A_COMMISSION_STYLE,
    'staff': B_STAFF_STYLE,
    'banking': C_BANKING_STYLE,
    'corporation': D_CORPORATION_STYLE,
    'state': E_STATE_COMMISSION_STYLE,
}


def _get(text: str, field: str, tag: str):
    return extract(field, text, source_url=f'https://example.invalid/{tag}',
                   document_title=f'{tag} notice')


# ------------------------------------------------------------------------------ tests
def test_fee_across_wordings() -> None:
    want = {
        'commission': ['100'],
        'staff': ['100'],
        'banking': ['175', '850'],
        'corporation': [],          # stated in words only
        'state': ['250'],
    }
    for tag, text in FIXTURES.items():
        got = _get(text, 'fee', tag)
        check_true(f'fee read from {tag}', got is not None)
        if got is None:
            continue
        check(f'fee amounts from {tag}', got.value['amounts'], want[tag])
        check(f'fee evidence verified in {tag}',
              got.evidence.status, EvidenceStatus.VERIFIED)
    # The one stated only in words must still be recognised as a fee.
    corp = _get(FIXTURES['corporation'], 'fee', 'corporation')
    check('a fee written in words is still a fee',
          corp.value['amountInWords'] if corp else None, True)
    # Exemptions are people-categories, however they are listed.
    for tag in ('commission', 'staff', 'state'):
        got = _get(FIXTURES[tag], 'fee', tag)
        check_true(f'{tag} exemptions found', got and got.value['exemptCategories'])


def test_age_across_wordings() -> None:
    want = {
        'commission': (21, 32),
        'staff': (18, 27),
        'banking': (20, 30),
        'corporation': (21, 30),
        'state': (18, 42),
    }
    for tag, text in FIXTURES.items():
        got = _get(text, 'ageLimits', tag)
        check_true(f'age read from {tag}', got is not None)
        if got is None:
            continue
        check(f'age band from {tag}', (got.value['minAge'], got.value['maxAge']), want[tag])
        check(f'age evidence verified in {tag}',
              got.evidence.status, EvidenceStatus.VERIFIED)


def test_attempts_including_the_absence_of_a_cap() -> None:
    a = _get(FIXTURES['commission'], 'attempts', 'commission')
    check('numbered attempts read', a.value if a else None, {'limited': True, 'count': 6})
    d = _get(FIXTURES['corporation'], 'attempts', 'corporation')
    check('"no restriction" is a real answer, not a miss',
          d.value if d else None, {'limited': False, 'count': None})


def test_qualification_across_wordings() -> None:
    for tag in FIXTURES:
        got = _get(FIXTURES[tag], 'qualification', tag)
        check_true(f'qualification read from {tag}', got is not None)
        if got:
            check_true(f'{tag} qualification names a level', got.value['levels'])


def test_vacancies_across_wordings() -> None:
    want = {'commission': '933', 'staff': '17727', 'banking': '4455', 'corporation': '300'}
    for tag, n in want.items():
        got = _get(FIXTURES[tag], 'vacancies', tag)
        check(f'vacancies from {tag}', got.value['count'] if got else None, n)
    approx = _get(FIXTURES['commission'], 'vacancies', 'commission')
    check('"approximately" is recorded, not dropped',
          approx.value['isApproximate'] if approx else None, True)


def test_pattern_across_wordings() -> None:
    for tag in ('staff', 'banking', 'state'):
        got = _get(FIXTURES[tag], 'examPattern', tag)
        check_true(f'pattern read from {tag}', got is not None)
        if got:
            check_true(f'{tag} pattern lists at least one paper', got.value['papers'])
    staff = _get(FIXTURES['staff'], 'examPattern', 'staff')
    check_true('negative marking captured where stated',
               staff and staff.value.get('negativeMarking'))


def test_evidence_must_exist_in_the_source() -> None:
    """The guard that makes everything above safe."""
    got = _get(FIXTURES['commission'], 'fee', 'commission')
    check('evidence verified against the real text',
          got.evidence.status, EvidenceStatus.VERIFIED)
    check('the span really is in the document',
          ' '.join(got.evidence.span.split()) in ' '.join(FIXTURES['commission'].split()), True)

    # A span that is not in the source must be refused, not downgraded.
    from .evidence import Evidence, Extracted, verified_or_none
    fake = Extracted(field='fee', value={'amounts': ['9999']},
                     evidence=Evidence(span='the fee is Rs. 9999 and nobody wrote this',
                                       source_url='x'))
    check('invented evidence is rejected outright',
          verified_or_none(fake, FIXTURES['commission']), None)


def test_no_field_is_read_from_a_silent_document() -> None:
    """Absence must stay absent: a document that says nothing must yield nothing."""
    silent = ('This notice concerns the revised timings of the departmental canteen and the '
              'allotment of parking spaces to officers of the Commission.')
    for name in ('fee', 'ageLimits', 'vacancies', 'attempts', 'examPattern'):
        got = extract(name, silent, source_url='https://example.invalid/x')
        check(f'{name} not invented from a silent document', got, None)


def test_extract_all() -> None:
    out = extract_all(FIXTURES['commission'], source_url='https://example.invalid/c')
    check_true('extract_all finds several fields at once', len(out) >= 5)
    check('every returned value carries verified evidence',
          all(e.evidence.status is EvidenceStatus.VERIFIED for e in out.values()), True)


def main() -> int:
    test_fee_across_wordings()
    test_age_across_wordings()
    test_attempts_including_the_absence_of_a_cap()
    test_qualification_across_wordings()
    test_vacancies_across_wordings()
    test_pattern_across_wordings()
    test_evidence_must_exist_in_the_source()
    test_no_field_is_read_from_a_silent_document()
    test_extract_all()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print(f'semantic extraction: all checks pass across {len(FIXTURES)} authority styles')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
