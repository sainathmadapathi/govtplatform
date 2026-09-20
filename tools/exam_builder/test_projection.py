"""One exam's application never contains another's, and the projection invents nothing.

Two things are proved here.

**Isolation.** Four invented authorities, four procedures, built in one run from one shared
pool of documents. Each record must contain only its own, and a document belonging to
another exam must be refused by content identity even when somebody has written it into the
manifest — because a manifest names documents and never vouches for them.

**Projection.** The extracted process is turned into the shape the existing simulator UI
already renders. The projection is a translation and not an author: where the process has
nothing to say, the spec says nothing rather than filling the gap.

Every authority, exam and document below is invented. The behaviour is structural.

Run: python -m tools.exam_builder.test_projection
"""
from __future__ import annotations

from .application import extract_application_process
from .compat import application_simulator_spec
from .identity import ExamIdentity, IdentityVerdict, verify
from .schema import SourceDocument, SourceKind, Status

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


# Four authorities, four procedures, deliberately using different words for the same ideas
# so that a leak between them would be visible rather than plausible.
DOCS = {
    'exam-alpha': ("""
ALPHA COMMISSION - COMBINED CLERICAL EXAMINATION, 2031
HOW TO APPLY
Step 1 - Alpha Profile
Candidates shall create the Alpha Profile and enter the alpha reference number.
Step 2 - Alpha Submission
Candidates must submit the Combined Clerical Examination form and pay Rs. 111/-.
""", 'Alpha Commission', 'Combined Clerical Examination 2031'),

    'exam-beta': ("""
BETA BOARD - TECHNICAL SERVICES EXAMINATION, 2031
PROCEDURE FOR APPLYING
Step 1 - Beta Enrolment
Candidates shall complete the Beta Enrolment and provide the beta identifier.
Step 2 - Beta Payment
Candidates must pay Rs. 222/- for the Technical Services Examination and submit it.
""", 'Beta Board', 'Technical Services Examination 2031'),

    'exam-gamma': ("""
GAMMA AUTHORITY - FIELD OFFICER EXAMINATION, 2031
APPLICATION PROCEDURE
Step 1 - Gamma Registration
Candidates shall register with Gamma Authority and enter the gamma code.
Step 2 - Gamma Upload
Candidates must upload the gamma declaration and pay Rs. 333/- to apply.
""", 'Gamma Authority', 'Field Officer Examination 2031'),

    'exam-delta': ("""
DELTA CORPORATION - ANALYST EXAMINATION, 2031
HOW TO APPLY
Step 1 - Delta Account
Candidates shall open the Delta Account and enter the delta membership number.
Step 2 - Delta Confirmation
Candidates must confirm the Analyst Examination entry and pay Rs. 444/- to submit.
""", 'Delta Corporation', 'Analyst Examination 2031'),
}

#: The token that belongs to exactly one exam, used to detect a leak.
MARKERS = {'exam-alpha': 'alpha', 'exam-beta': 'beta',
           'exam-gamma': 'gamma', 'exam-delta': 'delta'}

AMOUNTS = {'exam-alpha': 111.0, 'exam-beta': 222.0,
           'exam-gamma': 333.0, 'exam-delta': 444.0}


def doc_for(exam_id: str) -> SourceDocument:
    _text, authority, _name = DOCS[exam_id]
    return SourceDocument(id=f'{exam_id}-doc', url=f'https://{exam_id}.example/notice.pdf',
                          kind=SourceKind.NOTIFICATION, title=f'{authority} Notice',
                          authority=authority, accessed_at='2026-09-20', exam_id=exam_id)


def build(exam_id: str, extra=None):
    text, authority, _name = DOCS[exam_id]
    sources = [(doc_for(exam_id), text)] + list(extra or [])
    return extract_application_process(sources, exam_id=exam_id, authority=authority)


def all_text(process) -> str:
    """Every string the process holds, so a leak anywhere is visible."""
    bits = [process.portal.value or '']
    for s in process.stages:
        bits += [s.title, s.description, s.note]
        bits += [f.label + ' ' + f.help_text for f in s.fields]
        bits += [d.name for d in s.documents]
        bits += [str(i.value) for i in s.instructions]
        bits += [e.span for e in s.evidence]
    for f in process.fees:
        bits += [e.span for e in f.amount.evidence + f.is_exempt.evidence]
    return ' '.join(bits).lower()


# ==================================================================== isolation
def test_each_exam_contains_only_its_own_facts() -> None:
    built = {exam_id: build(exam_id).process for exam_id in DOCS}

    for exam_id, process in built.items():
        text = all_text(process)
        check(f'{exam_id} carries its own marker', MARKERS[exam_id] in text, True)
        foreign = [other for other, token in MARKERS.items()
                   if other != exam_id and token in text]
        check(f'{exam_id} carries no other exam’s marker', foreign, [])

    for exam_id, process in built.items():
        amounts = [f.amount.value for f in process.fees if f.amount.has_value]
        check(f'{exam_id} has only its own fee', amounts, [AMOUNTS[exam_id]])

    titles = {exam_id: [s.title for s in p.stages] for exam_id, p in built.items()}
    check('no two exams share a stage title',
          len({t for ts in titles.values() for t in ts}),
          sum(len(ts) for ts in titles.values()))


def test_building_one_exam_does_not_disturb_another() -> None:
    """Order must not matter. A shared module holding state would show up here."""
    forward = [build(e).process for e in ('exam-alpha', 'exam-beta', 'exam-gamma', 'exam-delta')]
    backward = [build(e).process for e in ('exam-delta', 'exam-gamma', 'exam-beta', 'exam-alpha')]
    check('the same exam built in either order is the same',
          [all_text(p) for p in forward], [all_text(p) for p in reversed(backward)])


def test_a_foreign_document_is_refused_by_identity() -> None:
    """The manifest names documents. It never vouches for them.

    Somebody writes another exam's notice into this exam's manifest -- by mistake, or
    because a discovery run was wrong. Content identity is what catches it, and it has to
    catch it on the document's own text rather than on where the document came from.
    """
    for exam_id, (_text, authority, official_name) in DOCS.items():
        target = ExamIdentity(exam_id=exam_id, query=official_name,
                              official_name=official_name, authority_name=authority)
        own_verdict = verify(DOCS[exam_id][0], target)
        check(f'{exam_id} accepts its own notice',
              own_verdict.verdict is IdentityVerdict.MISMATCH, False)

        for other_id in DOCS:
            if other_id == exam_id:
                continue
            verdict = verify(DOCS[other_id][0], target)
            # The guarantee is that a foreign document cannot supply facts. Whether it is
            # refused outright or merely left undecided is the identity module's judgement;
            # asserting MISMATCH specifically would over-specify it, and AMBIGUOUS is an
            # equally safe answer because only MATCH may be attributed.
            check(f'{exam_id} will not take facts from {other_id}',
                  verdict.may_supply_facts, False)
            check(f'and it is never a MATCH for {other_id}',
                  verdict.verdict is IdentityVerdict.MATCH, False)
            check(f'and says why for {other_id}', bool(verdict.reasons), True)


def test_a_foreign_document_that_slipped_through_still_cannot_supply_facts() -> None:
    """Belt and braces: if identity were bypassed, the disagreement must surface."""
    alpha_doc = doc_for('exam-alpha')
    beta_doc = doc_for('exam-beta')
    outcome = extract_application_process(
        [(alpha_doc, DOCS['exam-alpha'][0]), (beta_doc, DOCS['exam-beta'][0])],
        exam_id='exam-alpha', authority='Alpha Commission')
    check('two different procedures are reported as a conflict',
          'stages' in outcome.conflicts, True)
    # Both exams' fees are present too, and two unscoped amounts is its own disagreement.
    check('and so are the two fees',
          'fee amount' in outcome.conflicts, True)
    check('and neither is published while contested',
          {s.status for s in outcome.process.stages}, {Status.NEEDS_REVIEW})


# =================================================================== projection
def test_the_projection_is_a_translation_not_an_author() -> None:
    process = build('exam-alpha').process
    spec = application_simulator_spec(process, exam_id='exam-alpha')

    check('a spec is produced', spec is not None, True)
    check('bound to one exam', spec['examId'], 'exam-alpha')
    check('one module per extracted stage',
          len(spec['modules']), len(process.stages))
    check('module names are the authority’s own',
          [m['cardName'] for m in spec['modules']],
          [s.title for s in process.stages])
    check('each module cites where it was read',
          all(m['noticeReference'] for m in spec['modules']), True)
    check('no trap is manufactured', spec['traps'], [])
    check('and the note says why', 'mistake-traps' in spec['modelledOnNote'], True)
    check('no field carries an invented default',
          {f['defaultValue'] for m in spec['modules'] for f in m['fields']} <= {''}, True)


def test_the_projection_names_no_exam_and_no_authority() -> None:
    """Checked mechanically: the projection must not know who it is projecting."""
    import io
    import re
    source = io.open('tools/exam_builder/compat.py', encoding='utf-8').read()
    start = source.index('def application_simulator_spec')
    body = source[start:]
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'sbi', 'rrb'):
        check(f'the projection never names {forbidden.upper()}',
              re.findall(rf'\b{forbidden}\b', body, re.I), [])
    check('and holds no exam-conditional branch',
          re.findall(r'if\s+(?:exam|authority|exam_id)\s*==', body), [])


def test_four_authorities_project_to_four_different_forms() -> None:
    """The same code, four documents, four forms. That is the whole claim."""
    specs = {e: application_simulator_spec(build(e).process, exam_id=e) for e in DOCS}
    check('each exam gets a form', sorted(k for k, v in specs.items() if v), sorted(DOCS))
    names = {e: [m['cardName'] for m in s['modules']] for e, s in specs.items()}
    check('and no two forms are alike', len({tuple(v) for v in names.values()}), 4)
    for exam_id, cards in names.items():
        check(f'{exam_id}’s cards are its own',
              all(MARKERS[exam_id] in c.lower() for c in cards), True)


def test_nothing_to_show_produces_no_form() -> None:
    process = extract_application_process(
        [(doc_for('exam-alpha'), 'A notice with no procedure in it at all.')],
        exam_id='exam-alpha').process
    check('an empty process yields no form, rather than an empty one',
          application_simulator_spec(process, exam_id='exam-alpha'), None)


def test_an_unrepresentable_field_is_left_out_not_invented() -> None:
    process = build('exam-alpha').process
    spec = application_simulator_spec(process, exam_id='exam-alpha')
    kinds = {f['kind'] for m in spec['modules'] for f in m['fields']}
    check('field kinds stay inside what the UI understands',
          kinds <= {'TEXT', 'DATE', 'SELECT', 'RADIO'}, True)
    check('and an option list is never fabricated',
          any('options' in f for m in spec['modules'] for f in m['fields']), False)


def test_a_reviewed_stage_is_carried_with_its_reason() -> None:
    """A step the authority did not title is shown, and says that it needs checking."""
    text = """
HOW TO APPLY
1.1 Candidates shall register on the portal and create a password for the account.
1.2 Candidates must submit the completed form and pay the prescribed fee online.
"""
    process = extract_application_process(
        [(doc_for('exam-alpha'), text)], exam_id='exam-alpha').process
    if process.stages:
        check('an untitled step is held for review',
              {s.status for s in process.stages}, {Status.NEEDS_REVIEW})
        check('and carries a reason a person can act on',
              all('did not give this step a title' in s.note for s in process.stages), True)


def main() -> int:
    test_each_exam_contains_only_its_own_facts()
    test_building_one_exam_does_not_disturb_another()
    test_a_foreign_document_is_refused_by_identity()
    test_a_foreign_document_that_slipped_through_still_cannot_supply_facts()
    test_the_projection_is_a_translation_not_an_author()
    test_the_projection_names_no_exam_and_no_authority()
    test_four_authorities_project_to_four_different_forms()
    test_nothing_to_show_produces_no_form()
    test_an_unrepresentable_field_is_left_out_not_invented()
    test_a_reviewed_stage_is_carried_with_its_reason()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('projection: four exams, four forms, no fact crossed between them')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
