"""The publication gate: what reaches production and what is stopped.

The asymmetry under test is the product rule: an absence the *authority* created is
publishable, an absence *we* created is not. A candidate cannot tell them apart on screen,
so the gate has to.

Run: python -m tools.exam_builder.test_gate
"""
from __future__ import annotations

from ..exam_authoring.record import Citation, ExamRecord, Field
from .gate import BuildState, GateDecision, evaluate
from .identity import IdentityVerdict

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def _cite() -> Citation:
    return Citation(document_title='notice', url='https://x.invalid/n.pdf', page=1,
                    excerpt='...', verified_date='2026-09-17')


def _record(**fields) -> ExamRecord:
    """A record with every required field satisfied, then overridden by the caller."""
    rec = ExamRecord(exam_id='exam-x-y-2026', code='X_Y', title='X Y 2026',
                     authority_name='X', official_domain='https://x.invalid')
    for name in ('officialName', 'authority', 'applicationPortal', 'dates'):
        rec.set(Field.found(name, 'value', _cite()))
    for name, f in fields.items():
        rec.set(f)
    return rec


def _blocked_on(report, field: str) -> bool:
    return any(b.field == field for b in report.blockers)


# ------------------------------------------------------------------------------ tests
def test_a_clean_build_publishes() -> None:
    r = evaluate(_record())
    check('a build with every required field verified passes',
          r.decision, GateDecision.PASS)


def test_unpublished_is_allowed() -> None:
    """The authority has not released an answer key. That is information, not a defect."""
    rec = _record(answerKeys=Field.not_published('answerKeys', 'no key published'),
                  results=Field.not_published('results', 'no result yet'))
    r = evaluate(rec)
    check('genuinely unpublished fields do not block', r.decision, GateDecision.PASS)
    check('and they are reported as allowed', sorted(r.allowed), ['answerKeys', 'results'])


def test_not_extracted_blocks() -> None:
    """A source exists and we failed to read it. Publishing would show a gap they did not leave."""
    rec = _record(fee=Field.not_extracted('fee', 'https://x.invalid', 'fee clause'))
    r = evaluate(rec)
    check('an unread field blocks publication', r.decision, GateDecision.BLOCK)
    check('and the blocker names it', _blocked_on(r, 'fee'), True)


def test_needs_review_blocks_its_field() -> None:
    rec = _record(ageLimits=Field.needs_review('ageLimits', {'minAge': 18},
                                               'only one cue fired'))
    r = evaluate(rec)
    check('an unconfident reading blocks', r.decision, GateDecision.BLOCK)
    check('and names the field', _blocked_on(r, 'ageLimits'), True)


def test_mismatched_source_blocks() -> None:
    r = evaluate(_record(), identity_by_source={
        'https://x.invalid/other-exam.pdf': IdentityVerdict.MISMATCH})
    check('a source belonging to another exam blocks', r.decision, GateDecision.BLOCK)
    check('and is named', any('another exam' in b.reason for b in r.blockers), True)


def test_infrastructure_failure_blocks_and_is_not_a_finding() -> None:
    """The rule that matters most: an outage must never look like an authority's silence."""
    r = evaluate(_record(), build_state=BuildState.PAUSED_INFRASTRUCTURE)
    check('a paused build cannot publish', r.decision, GateDecision.BLOCK)
    check('and says the silence is ours, not theirs',
          any('not published' in b.detail for b in r.blockers), True)


def test_conflicts_block() -> None:
    r = evaluate(_record(), conflicts=['applicationEnd: 10 June vs 15 June'])
    check('an unresolved contradiction blocks', r.decision, GateDecision.BLOCK)


def test_schema_typecheck_isolation_block() -> None:
    check('a schema failure blocks',
          evaluate(_record(), schema_ok=False).decision, GateDecision.BLOCK)
    check('a typecheck failure blocks',
          evaluate(_record(), typecheck_ok=False).decision, GateDecision.BLOCK)
    check('an isolation failure blocks',
          evaluate(_record(), isolation_ok=False).decision, GateDecision.BLOCK)


def test_a_required_field_may_not_be_merely_unpublished() -> None:
    """An exam with no application portal on record cannot be offered at all."""
    rec = _record(applicationPortal=Field.not_published('applicationPortal', 'none found'))
    r = evaluate(rec)
    check('a required field being unpublished still blocks', r.decision, GateDecision.BLOCK)
    check('and explains why', _blocked_on(r, 'applicationPortal'), True)


def test_the_asymmetry_holds_in_one_comparison() -> None:
    """Same shape of hole, opposite verdicts, decided only by whose hole it is."""
    theirs = evaluate(_record(cutoffs=Field.not_published('cutoffs', 'not yet declared')))
    ours = evaluate(_record(cutoffs=Field.not_extracted('cutoffs', 'https://x.invalid',
                                                        'cut-off table')))
    check('their gap publishes', theirs.decision, GateDecision.PASS)
    check('our gap does not', ours.decision, GateDecision.BLOCK)


def main() -> int:
    test_a_clean_build_publishes()
    test_unpublished_is_allowed()
    test_not_extracted_blocks()
    test_needs_review_blocks_its_field()
    test_mismatched_source_blocks()
    test_infrastructure_failure_blocks_and_is_not_a_finding()
    test_conflicts_block()
    test_schema_typecheck_isolation_block()
    test_a_required_field_may_not_be_merely_unpublished()
    test_the_asymmetry_holds_in_one_comparison()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('publication gate: all checks pass')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
