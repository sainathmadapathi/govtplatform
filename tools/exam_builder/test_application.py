"""Eight application styles, none of them any real authority's, and none needing a branch.

The extractor's whole premise is that the *document* supplies the steps. So the fixtures are
written to disagree with each other about what an application even is: one has eight numbered
steps, one has a single form, one splits registration from the exam-specific part, one makes
payment conditional, one varies the fee by category, one makes documents conditional, one
spreads the procedure across two documents, and one corrects itself.

If any of them needed special handling, the extractor would be recognising procedures rather
than reading them.

Every authority here is invented. No real exam's wording appears.

Run: python -m tools.exam_builder.test_application
"""
from __future__ import annotations

from .application import (extract_application_process, extract_fees, extract_portal,
                          extract_stages, merge_facts)
from .compat import application_simulator_spec
from .schema import Fact, ScopeKind, SourceDocument, SourceEvidence, SourceKind, Status

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def doc(doc_id: str = 'doc-1', url: str = 'https://authority.example/notice.pdf',
        kind: SourceKind = SourceKind.NOTIFICATION) -> SourceDocument:
    return SourceDocument(id=doc_id, url=url, kind=kind, title='Notice of Examination',
                          authority='Example Authority', accessed_at='2026-09-20',
                          exam_id='exam-x')


# ============================================================= A. multi-step online
A_MULTI_STEP = """
HOW TO APPLY. Candidates must apply online through the portal at
https://apply.authority.example/register. The application is completed in the following
steps.
Step 1 - Account Creation. Candidates shall create an account by entering the mobile number
and the email address. An account is created once in a lifetime.
Step 2 - Registration. Candidates must provide the name and the father's name exactly as in
the matriculation certificate. Enter the date of birth in the format DD/MM/YYYY.
Step 3 - Educational Details. Candidates shall furnish the qualification and the year of
passing. Select the board from the list.
Step 4 - Photograph and Signature. Candidates must upload the scanned photograph in JPEG
format. Candidates must upload the scanned signature in black ink.
Step 5 - Examination Centre. Candidates shall indicate the centre preference. Centres are
allotted on a first apply first allot basis.
Step 6 - Fee Payment. Candidates are required to pay a fee of Rs. 100/- through net banking
or debit card. Female candidates are exempted from payment of fee.
Step 7 - Final Submission. Candidates must submit the application before the last date. No
change or correction shall be permitted after final submission.
"""


def test_a_multi_step_application() -> None:
    d = doc()
    stages = extract_stages(d, A_MULTI_STEP)
    check('A: seven steps, because the document has seven', len(stages), 7)
    check('A: order is the document’s order',
          [s.order for s in stages], [1, 2, 3, 4, 5, 6, 7])
    check('A: the authority’s own titles survive verbatim',
          [s.title for s in stages],
          ['Account Creation', 'Registration', 'Educational Details',
           'Photograph and Signature', 'Examination Centre', 'Fee Payment',
           'Final Submission'])
    check('A: every stage carries verified evidence',
          all(s.evidence and s.evidence[0].is_verbatim for s in stages), True)
    check('A: and every stage is VERIFIED',
          {s.status for s in stages}, {Status.VERIFIED})

    fields = [f for s in stages for f in s.fields]
    check('A: fields were read from the sentences that ask for them',
          any(f.label.lower().startswith('date of birth') for f in fields), True)
    check('A: a stated format is captured as a constraint',
          any('DD/MM/YYYY' in c.upper() for f in fields for c in f.constraints), True)
    check('A: every field carries verified evidence',
          all(f.evidence and f.evidence[0].is_verbatim for f in fields), True)

    docs = [x for s in stages for x in s.documents]
    check('A: uploads are documents, not form fields',
          sorted({x.name.lower() for x in docs if 'photograph' in x.name.lower()
                  or 'signature' in x.name.lower()}),
          ['scanned photograph', 'scanned signature'])
    check('A: a document records only the specification that was printed',
          any('JPEG' in s.upper() for x in docs for s in x.specifications), True)


def test_a_portal_comes_from_a_sentence_about_applying() -> None:
    portal = extract_portal(doc(), A_MULTI_STEP)
    check('A: the apply address is found', portal.value,
          'https://apply.authority.example/register')
    check('A: and it is evidenced verbatim', portal.is_publishable, True)


# ====================================================== B. one form with instructions
B_SINGLE_FORM = """
APPLICATION. There is a single application form. Candidates shall fill in the application
form available on the website https://authority.example/form and submit it. Candidates must
provide the roll number. The form must be submitted before the closing date.
"""


def test_b_single_form_yields_no_invented_steps() -> None:
    stages = extract_stages(doc(), B_SINGLE_FORM)
    check('B: a document with no enumeration yields no steps', stages, [])
    outcome = extract_application_process([(doc(), B_SINGLE_FORM)], exam_id='exam-x')
    check('B: and the absence is reported as our gap',
          any('extraction gap' in line for line in outcome.log), True)
    check('B: never as the authority publishing none',
          any('publishes none' in line and 'not evidence' not in line
              for line in outcome.log), False)
    check('B: the portal is still read', outcome.process.portal.value,
          'https://authority.example/form')


# ============================================== C. registration + exam-specific part
C_TWO_PART = """
PROCEDURE FOR APPLYING. The process has two parts.
Part 1 - One Time Profile. Candidates shall create the profile by entering the name and the
address. The profile is created once and reused.
Part 2 - Examination Application. Candidates must select the examination and provide the
centre preference. Candidates shall submit the examination application separately.
"""


def test_c_registration_and_exam_specific_parts() -> None:
    stages = extract_stages(doc(), C_TWO_PART)
    check('C: two parts', len(stages), 2)
    check('C: the authority calls them Parts, and they stay Parts',
          [s.title for s in stages], ['One Time Profile', 'Examination Application'])
    check('C: nothing renamed a profile step into "Account Creation"',
          any('account creation' in s.title.lower() for s in stages), False)


# =================================================== D. payment optional/conditional
D_CONDITIONAL_PAYMENT = """
HOW TO APPLY. Candidates apply online.
Step 1 - Registration. Candidates must provide the name.
Step 2 - Payment. Candidates may pay the fee of Rs. 250/- by credit card. Candidates
claiming exemption are not required to pay. Ex-servicemen candidates are exempted from
payment of fee.
"""


def test_d_conditional_payment() -> None:
    d = doc()
    stages = extract_stages(d, D_CONDITIONAL_PAYMENT)
    payment = next(s for s in stages if s.title.lower() == 'payment')
    check('D: an optional step is not marked required',
          [f.required for f in payment.fields if f.required is True], [])

    fees = extract_fees(d, D_CONDITIONAL_PAYMENT)
    amounts = [f for f in fees if f.amount.has_value]
    exempt = [f for f in fees if f.is_exempt.value is True]
    check('D: the amount is read', [f.amount.value for f in amounts], [250.0])
    check('D: and a stated exemption is scoped to the group that was named',
          [r.label for f in exempt for r in f.scope.of(ScopeKind.CATEGORY)],
          ['ex-servicemen'])
    check('D: a stated mode is captured',
          'credit card' in (amounts[0].accepted_modes.value or []), True)


# ====================================================== E. category-dependent fee
E_CATEGORY_FEE = """
FEE. The application fee is Rs. 500/- for all candidates. A fee of Rs. 250/- is payable by
candidates belonging to Other Backward Classes. Scheduled Caste candidates are exempted from
payment of fee. Women candidates are exempted from payment of fee.
"""


def test_e_category_dependent_fee() -> None:
    fees = extract_fees(doc(), E_CATEGORY_FEE)
    globals_ = [f for f in fees if f.scope.is_global and f.amount.has_value]
    scoped = [f for f in fees if not f.scope.is_global and f.amount.has_value]
    exempt = [f for f in fees if f.is_exempt.value is True]

    check('E: a general amount is global', [f.amount.value for f in globals_], [500.0])
    check('E: a group-specific amount is scoped to that group',
          [(f.amount.value, f.scope.of(ScopeKind.CATEGORY)[0].label) for f in scoped],
          [(250.0, 'other backward classes')])
    check('E: two stated exemptions, each scoped',
          # The group's label is the wording the document printed, not an acronym we
          # normalised it onto — the same rule that keeps a step called "Registration".
          sorted(r.label for f in exempt for r in f.scope.of(ScopeKind.CATEGORY)),
          ['scheduled caste', 'women'])
    check('E: every fee rule is evidenced',
          all(f.amount.is_publishable for f in globals_ + scoped), True)
    check('E: and no exemption was added because such exemptions are common',
          len(exempt), 2)


def test_e_no_fee_is_proved_not_assumed() -> None:
    stated = 'FEE. There is no application fee for this recruitment.'
    fees = extract_fees(doc(), stated)
    check('a stated absence is NOT_PUBLISHED', fees[0].amount.status, Status.NOT_PUBLISHED)
    check('and it cites the sentence that states it',
          bool(fees[0].amount.evidence), True)

    silent = 'HOW TO APPLY. Candidates apply online at https://authority.example/x.'
    check('a document that never mentions a fee yields no fee rule at all',
          extract_fees(doc(), silent), [])


# ======================================================== F. conditional documents
F_CONDITIONAL_DOCS = """
HOW TO APPLY.
Step 1 - Upload. Candidates must upload the photograph. Candidates claiming age relaxation
shall upload the category certificate, if applicable. Candidates must upload the signature.
Step 2 - Submit. Candidates shall submit the form.
"""


def test_f_conditional_documents() -> None:
    stages = extract_stages(doc(), F_CONDITIONAL_DOCS)
    docs = {x.name.lower(): x for s in stages for x in s.documents}
    check('F: an unconditional upload is required',
          docs['photograph'].required, True)
    check('F: a conditional one is not asserted as required',
          docs['category certificate'].required, None)
    check('F: and the condition itself is kept, in the source’s words',
          any('applicable' in s.lower()
              for s in docs['category certificate'].specifications), True)
    check('F: no document was added because other exams commonly require it',
          sorted(docs), ['category certificate', 'photograph', 'signature'])


# ============================================ G. process across two official documents
G_NOTICE = """
HOW TO APPLY. Candidates apply online at https://apply.authority.example/go.
Step 1 - Registration. Candidates must provide the name.
Step 2 - Submission. Candidates shall submit the form.
"""

G_INSTRUCTIONS = """
INSTRUCTIONS FOR FILLING THE APPLICATION. Candidates apply online at
https://apply.authority.example/go. A fee of Rs. 300/- is payable by net banking.
"""


def test_g_two_documents_combine_after_validation() -> None:
    d1 = doc('doc-1', 'https://authority.example/notice.pdf')
    d2 = doc('doc-2', 'https://authority.example/instructions.pdf',
             SourceKind.APPLICATION_PAGE)
    outcome = extract_application_process(
        [(d1, G_NOTICE), (d2, G_INSTRUCTIONS)], exam_id='exam-x')

    check('G: steps come from the document that enumerated them',
          [s.title for s in outcome.process.stages], ['Registration', 'Submission'])
    check('G: the fee comes from the other document',
          [f.amount.value for f in outcome.process.fees if f.amount.has_value], [300.0])
    check('G: the portal agreed, so it is corroborated rather than contested',
          outcome.process.portal.status, Status.VERIFIED)
    check('G: and carries evidence from both documents',
          sorted({e.source_id for e in outcome.process.portal.evidence}),
          ['doc-1', 'doc-2'])
    check('G: no conflict was raised', outcome.conflicts, [])


def test_g_disagreeing_documents_become_needs_review() -> None:
    """Two official sources, two different portals. Neither wins on ranking."""
    d1 = doc('doc-1', 'https://authority.example/a.pdf')
    d2 = doc('doc-2', 'https://authority.example/b.pdf')
    other = G_INSTRUCTIONS.replace('https://apply.authority.example/go',
                                   'https://different.authority.example/go')
    outcome = extract_application_process([(d1, G_NOTICE), (d2, other)], exam_id='exam-x')

    check('conflicting portals are held for review',
          outcome.process.portal.status, Status.NEEDS_REVIEW)
    check('the conflict is reported', outcome.conflicts, ['portal'])
    check('both readings are preserved',
          len(outcome.process.portal.evidence) >= 2, True)
    check('and the field cannot be published while contested',
          outcome.process.portal.is_publishable, False)
    check('the note explains that ranking did not decide it',
          'ranked higher' in outcome.process.portal.note, True)


# ============================================== H. a corrigendum changing a step
H_ORIGINAL = """
HOW TO APPLY.
Step 1 - Registration. Candidates must provide the name.
Step 2 - Payment. Candidates shall pay a fee of Rs. 100/-.
"""

H_CORRIGENDUM = """
PROCEDURE FOR APPLYING - CORRIGENDUM.
Step 1 - Registration. Candidates must provide the name.
Step 2 - Payment. Candidates shall pay a fee of Rs. 100/-.
Step 3 - Verification. Candidates must verify the submitted details.
"""


def test_h_corrigendum_changing_the_procedure() -> None:
    d1 = doc('doc-1', 'https://authority.example/notice.pdf')
    d2 = doc('doc-2', 'https://authority.example/corrigendum.pdf', SourceKind.CORRIGENDUM)
    outcome = extract_application_process(
        [(d1, H_ORIGINAL), (d2, H_CORRIGENDUM)], exam_id='exam-x')

    check('H: a second document describing a different procedure is a conflict',
          outcome.conflicts, ['stages'])
    check('H: the stages are held for review rather than merged',
          {s.status for s in outcome.process.stages}, {Status.NEEDS_REVIEW})
    check('H: and the other document’s evidence is preserved alongside',
          any(e.source_id == 'doc-2'
              for s in outcome.process.stages for e in s.evidence), True)
    check('H: nothing silently appended a step',
          len(outcome.process.stages), 2)


# ============================================================ the general rules
def test_no_invention_without_a_verbatim_span() -> None:
    """The structural guarantee: a value whose span is not in the source cannot exist."""
    d = doc()
    stages = extract_stages(d, A_MULTI_STEP)
    every = (
        [e for s in stages for e in s.evidence]
        + [e for s in stages for f in s.fields for e in f.evidence]
        + [e for s in stages for x in s.documents for e in x.evidence]
        + [e for s in stages for i in s.instructions for e in i.evidence])
    check('every span in the result was found verbatim in the source',
          all(e.is_verbatim for e in every), True)
    check('and there are plenty of them to check', len(every) > 20, True)


def test_an_unreadable_source_is_infrastructure() -> None:
    outcome = extract_application_process(
        [(doc(), '')], exam_id='exam-x', unreadable=['https://authority.example/down.pdf'])
    check('an empty read is infrastructure', outcome.infrastructure_failed, True)
    check('the unreadable sources are named',
          len(outcome.unreadable), 2)
    check('and no fact claims the authority publishes nothing',
          outcome.process.portal.status, Status.NOT_EXTRACTED)


def test_no_sources_at_all_is_not_a_claim_about_anyone() -> None:
    outcome = extract_application_process([], exam_id='exam-x')
    check('nothing read means nothing claimed',
          outcome.process.portal.status, Status.NOT_EXTRACTED)
    check('and it is said out loud',
          any('says nothing about what the authority publishes' in l
              for l in outcome.log), True)


def test_merge_corroborates_and_contests() -> None:
    def fact(value, source_id):
        return Fact.verified(value, SourceEvidence(source_id=source_id, span='x'))

    agree = merge_facts('portal', [fact('https://a.example/x', 'd1'),
                                   fact('https://a.example/x/', 'd2')])
    check('the same value from two sources is corroboration',
          agree.status, Status.VERIFIED)
    check('and confidence rises with it', agree.confidence > 0.6, True)

    contest = merge_facts('portal', [fact('https://a.example/x', 'd1'),
                                     fact('https://b.example/y', 'd2')])
    check('different values are contested', contest.status, Status.NEEDS_REVIEW)
    check('with both kept', len(contest.evidence), 2)

    nothing = merge_facts('portal', [Fact.not_extracted()])
    check('and nothing found stays nothing found', nothing.status, Status.NOT_EXTRACTED)


def test_the_extractor_names_no_authority() -> None:
    """The architectural guarantee, checked mechanically rather than by inspection."""
    import io
    import re as _re
    source = io.open('tools/exam_builder/application.py', encoding='utf-8').read()
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'tspsc', 'rrb', 'sbi'):
        hits = _re.findall(rf'\b{forbidden}\b', source, _re.I)
        check(f'the extractor never names {forbidden.upper()}', hits, [])
    check('and contains no exam-conditional branch',
          _re.findall(r'if\s+(?:exam|authority)\s*==', source), [])


# ======================================================= backward compatibility
def test_the_existing_simulator_shape_can_still_be_produced() -> None:
    outcome = extract_application_process([(doc(), A_MULTI_STEP)], exam_id='exam-x')
    spec = application_simulator_spec(outcome.process, exam_id='exam-x')
    check('a spec is produced', spec is not None, True)
    check('bound to the one exam it belongs to', spec['examId'], 'exam-x')
    check('one module per extracted stage', len(spec['modules']), 7)
    check('module numbering follows the document',
          [m['moduleNumber'] for m in spec['modules']], [1, 2, 3, 4, 5, 6, 7])
    check('card names are the authority’s own words',
          spec['modules'][0]['cardName'], 'Account Creation')
    check('each module points at where it was read from',
          all(m['noticeReference'] for m in spec['modules']), True)
    check('the portal is carried through', spec['portalUrl'],
          'https://apply.authority.example/register')
    check('traps are empty, because a trap is a reading and not a shape',
          spec['traps'], [])
    check('and the note says so', 'mistake-traps' in spec['modelledOnNote'], True)
    check('field kinds the document did not state fall back to text, not a guess',
          {f['kind'] for m in spec['modules'] for f in m['fields']} <= {'TEXT', 'SELECT', 'DATE'},
          True)


def test_no_spec_rather_than_an_empty_one() -> None:
    outcome = extract_application_process([(doc(), B_SINGLE_FORM)], exam_id='exam-x')
    check('with no extracted stages, no form is offered',
          application_simulator_spec(outcome.process, exam_id='exam-x'), None)


def main() -> int:
    test_a_multi_step_application()
    test_a_portal_comes_from_a_sentence_about_applying()
    test_b_single_form_yields_no_invented_steps()
    test_c_registration_and_exam_specific_parts()
    test_d_conditional_payment()
    test_e_category_dependent_fee()
    test_e_no_fee_is_proved_not_assumed()
    test_f_conditional_documents()
    test_g_two_documents_combine_after_validation()
    test_g_disagreeing_documents_become_needs_review()
    test_h_corrigendum_changing_the_procedure()
    test_no_invention_without_a_verbatim_span()
    test_an_unreadable_source_is_infrastructure()
    test_no_sources_at_all_is_not_a_claim_about_anyone()
    test_merge_corroborates_and_contests()
    test_the_extractor_names_no_authority()
    test_the_existing_simulator_shape_can_still_be_produced()
    test_no_spec_rather_than_an_empty_one()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('application: eight document styles, no authority named, every span verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
