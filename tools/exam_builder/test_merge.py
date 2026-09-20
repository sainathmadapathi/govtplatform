"""Four operations. The fourth is the one that matters.

A merge engine that resolves disagreements will eventually resolve one wrongly and quietly,
and a candidate cannot tell a confident wrong date from a right one. So most of these check
that it refuses.

The fixtures are invented; the two shapes they are drawn from are not. Both came out of the
first real run: a record storing the two ends of a window as separate rows while an
extractor reads it as one milestone, and an authority stating an event it has not yet dated.

Run: python -m tools.exam_builder.test_merge
"""
from __future__ import annotations

from .merge import MergeAction, comparable_values, matches, merge_milestones
from .schema import (Fact, Milestone, Post, MilestoneState, Scope, ScopeKind, ScopeRef,
                     SourceDocument, SourceEvidence, SourceKind, Status)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def ev(source_id: str, span: str = 'a span') -> SourceEvidence:
    from .evidence import EvidenceStatus
    return SourceEvidence(source_id=source_id, span=span,
                          span_status=EvidenceStatus.VERIFIED)


def milestone(kind: str, *, end: str = '', start: str = '', source: str = 'doc',
              state: MilestoneState = MilestoneState.ANNOUNCED, scope: Scope | None = None,
              mid: str = '', cycle: str = '2026') -> Milestone:
    return Milestone(
        id=mid or f'm-{kind}-{end or start}',
        label=kind.replace('_', ' ').title(), kind=kind, cycle=cycle,
        scope=scope or Scope(),
        starts_at=Fact.verified(start, ev(source)) if start else Fact(),
        ends_at=Fact.verified(end, ev(source)) if end else Fact(),
        state=state, status=Status.VERIFIED)


CORRIGENDUM = SourceDocument(id='doc-corr', url='https://a.example/c.pdf',
                             kind=SourceKind.CORRIGENDUM, title='Corrigendum')
NOTICE = SourceDocument(id='doc-notice', url='https://a.example/n.pdf',
                        kind=SourceKind.NOTIFICATION, title='Notice')


# ===================================================================== 1. MATCH
def test_match_needs_the_same_subject() -> None:
    a = milestone('APPLICATION_END', end='2026-06-22')
    check('the same event matches itself',
          matches(a, milestone('APPLICATION_END', end='2026-06-30')), True)
    check('a different event does not',
          matches(a, milestone('EXAM', end='2026-06-22')), False)
    check('nor does the same event in a different cycle',
          matches(a, milestone('APPLICATION_END', end='2027-06-22', cycle='2027')), False)


def test_two_papers_are_two_events_not_a_contradiction() -> None:
    paper_one = milestone('EXAM', end='2026-03-03', mid='m1',
                          scope=Scope([ScopeRef(ScopeKind.STAGE, 'p1', 'Paper I')]))
    paper_two = milestone('EXAM', end='2026-03-05', mid='m2',
                          scope=Scope([ScopeRef(ScopeKind.STAGE, 'p2', 'Paper II')]))
    check('scoped events do not match each other', matches(paper_one, paper_two), False)
    report = merge_milestones([paper_one], [paper_two])
    check('so neither is a conflict', report.has_conflicts, False)
    check('and both survive', len(report.milestones), 2)


def test_a_window_is_compared_end_for_end() -> None:
    """From the first real run: a closing date was compared against an opening date."""
    record_open = milestone('APPLICATION_START', start='2026-05-21')
    extracted = milestone('APPLICATION_WINDOW', start='2026-05-21', end='2026-06-22')
    check('a window matches one of its ends', matches(record_open, extracted), True)
    check('and the opening is compared against the opening',
          comparable_values(record_open, extracted), ('2026-05-21', '2026-05-21'))

    record_close = milestone('APPLICATION_END', end='2026-06-22')
    check('the closing against the closing',
          comparable_values(record_close, extracted), ('2026-06-22', '2026-06-22'))


# =================================================================== 2. CONFIRM
def test_agreement_makes_one_fact_with_two_sources() -> None:
    existing = milestone('APPLICATION_END', end='2026-06-22', source='record')
    incoming = milestone('APPLICATION_END', end='2026-06-22', source='doc-notice')
    report = merge_milestones([existing], [incoming], source=NOTICE)
    check('agreement is CONFIRMED',
          [d.action for d in report.decisions], [MergeAction.CONFIRMED])
    check('one fact, not two', len(report.milestones), 1)
    check('with both sources behind it',
          sorted(e.source_id for e in report.milestones[0].ends_at.evidence),
          ['doc-notice', 'record'])
    check('and it stays verified', report.milestones[0].status, Status.VERIFIED)


# ================================================================= 3. SUPERSEDE
def test_a_corrigendum_supersedes_and_keeps_the_old_value() -> None:
    existing = milestone('APPLICATION_END', end='2026-06-21', mid='old', source='record')
    incoming = milestone('APPLICATION_END', end='2026-06-22', mid='new', source='doc-corr')
    report = merge_milestones([existing], [incoming], source=CORRIGENDUM)

    check('a corrigendum supersedes',
          [d.action for d in report.decisions], [MergeAction.SUPERSEDED])
    check('both versions are kept', len(report.milestones), 2)
    old = next(m for m in report.milestones if m.id == 'old')
    new = next(m for m in report.milestones if m.id == 'new')
    check('the old one points at what replaced it', old.superseded_by, 'new')
    check('the new one points back', new.supersedes, 'old')
    check('the old value stops applying', old.effective_date, None)
    check('the new one applies', new.effective_date, '2026-06-22')
    check('and the document that changed it is named',
          new.revision_source_id, 'doc-corr')


def test_revision_wording_supersedes_without_a_corrigendum() -> None:
    existing = milestone('EXAM', end='2026-05-15', mid='old')
    incoming = milestone('EXAM', end='2026-06-22', mid='new',
                         state=MilestoneState.RESCHEDULED)
    report = merge_milestones([existing], [incoming], source=NOTICE)
    check('a statement that it is rescheduling supersedes too',
          [d.action for d in report.decisions], [MergeAction.SUPERSEDED])


# ==================================================================== 4. REFUSE
def test_two_readings_with_no_stated_relationship_are_refused() -> None:
    existing = milestone('APPLICATION_END', end='2026-06-21', mid='old', source='record')
    incoming = milestone('APPLICATION_END', end='2026-06-22', mid='new', source='doc-notice')
    report = merge_milestones([existing], [incoming], source=NOTICE)

    check('a plain difference is CONFLICTED',
          [d.action for d in report.decisions], [MergeAction.CONFLICTED])
    check('both are kept', len(report.milestones), 2)
    check('both held for review',
          {m.status for m in report.milestones}, {Status.NEEDS_REVIEW})
    check('neither is superseded, because neither claims to correct the other',
          [m for m in report.milestones if m.is_superseded], [])
    check('and the note says so',
          all('neither says it is correcting' in m.note for m in report.milestones), True)


def test_a_newer_document_does_not_win_by_being_newer() -> None:
    """The engine has no notion of "later" beyond what a document says about itself."""
    existing = milestone('EXAM', end='2026-05-15', mid='old')
    incoming = milestone('EXAM', end='2026-06-22', mid='new')
    report = merge_milestones([existing], [incoming], source=NOTICE)
    check('a second notice with a different date does not overwrite',
          report.of(MergeAction.CONFLICTED) != [], True)
    check('and the record keeps its value, unpublished rather than replaced',
          next(m for m in report.milestones if m.id == 'old').effective_date, '2026-05-15')


# ================================================================ housekeeping
def test_an_undated_statement_changes_nothing() -> None:
    """From the first real run: an awaited event conflicted with a dated record entry."""
    existing = milestone('EXAM', end='2026-11-05')
    awaited = Milestone(id='m-awaited', label='Examination', kind='EXAM', cycle='2026',
                        state=MilestoneState.AWAITED, status=Status.VERIFIED)
    report = merge_milestones([existing], [awaited])
    check('silence is not disagreement',
          [d.action for d in report.decisions], [MergeAction.UNCHANGED])
    check('and the record is untouched',
          report.milestones[0].effective_date, '2026-11-05')


def test_new_information_is_added() -> None:
    existing = milestone('APPLICATION_END', end='2026-06-22')
    incoming = milestone('FEE_PAYMENT_END', end='2026-06-23')
    report = merge_milestones([existing], [incoming], source=NOTICE)
    check('an event the record lacked is ADDED',
          sorted(d.action.value for d in report.decisions), ['ADDED', 'UNCHANGED'])
    check('and both are in the result', len(report.milestones), 2)


def test_nothing_is_ever_removed() -> None:
    existing = [milestone('EXAM', end='2026-11-05', mid='a'),
                milestone('RESULT', end='2026-12-15', mid='b'),
                milestone('ANSWER_KEY', end='2026-11-20', mid='c')]
    report = merge_milestones(existing, [milestone('EXAM', end='2026-12-01', mid='x')],
                              source=NOTICE)
    check('every existing fact survives a merge',
          {'a', 'b', 'c'} <= {m.id for m in report.milestones}, True)


def test_an_empty_extraction_leaves_the_record_alone() -> None:
    existing = [milestone('EXAM', end='2026-11-05', mid='a')]
    report = merge_milestones(existing, [])
    check('nothing extracted means nothing changed',
          [d.action for d in report.decisions], [MergeAction.UNCHANGED])
    check('and the record is returned as it was',
          [m.id for m in report.milestones], ['a'])


def test_the_engine_names_no_exam() -> None:
    import io
    import re
    source = io.open('tools/exam_builder/merge.py', encoding='utf-8').read()
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc'):
        check(f'merge.py never names {forbidden.upper()}',
              re.findall(rf'\b{forbidden}\b', source, re.I), [])


# ===================================================================== 5. POSTS
def post(name, *, classification='', pid=''):
    p = Post(id=pid or 'p-' + name.lower().replace(' ', '-'), name=name)
    if classification:
        p.classification = Fact.verified(classification, ev('doc'))
    return p


def authored(name, *, classification='', pid='', low=21, high=32, department='X'):
    """A record's post, in the shape data.ts stores it."""
    return {'id': pid or 'a-' + name.lower().replace(' ', '-'), 'postName': name,
            'classification': classification, 'minAge': low, 'maxAge': high,
            'department': department, 'payLevel': 'Level 10', 'payScale': 'Rs 56,100'}


def test_a_post_the_record_abbreviates_is_still_the_same_post() -> None:
    from .merge import post_identity
    check('an abbreviation does not hide a post',
          post_identity('Indian Administrative Service (IAS)',
                        'Indian Administrative Service') >= 0.85, True)
    check('two different services are not one post',
          post_identity('Indian Foreign Service', 'Indian Police Service'), 0.0)
    check('and sharing the common vocabulary proves nothing',
          post_identity('Assistant Section Officer', 'Assistant Audit Officer') < 0.85, True)


def test_a_matched_post_keeps_what_the_record_already_has() -> None:
    from .merge import FieldOutcome, merge_posts
    report = merge_posts([authored('Alpha Service (AS)', classification='Group B')],
                         [post('Alpha Service', classification='Group B')])
    decision = report.decisions[0]
    check('the post is confirmed', decision.action, MergeAction.CONFIRMED)
    check('its name is the record’s', decision.field('name').outcome, FieldOutcome.KEPT)
    check('so are its department and pay',
          [decision.field(f).outcome for f in ('department', 'payLevel', 'payScale')],
          [FieldOutcome.KEPT] * 3)
    check('and the classification is confirmed rather than replaced',
          decision.field('classification').outcome, FieldOutcome.CONFIRMED)


def test_the_record_asserting_what_the_document_omits_is_held() -> None:
    """The case this layer exists for: silence is not denial, nor is it support."""
    from .merge import FieldOutcome, merge_posts
    report = merge_posts(
        [authored('Alpha Service (AS)', classification='Group A (Gazetted)')],
        [post('Alpha Service')])
    decision = report.decisions[0]
    field = decision.field('classification')
    check('the post is contested', decision.action, MergeAction.CONFLICTED)
    check('the classification is held for review', field.outcome, FieldOutcome.UNDER_REVIEW)
    check('the record’s value is kept, not deleted', field.existing, 'Group A (Gazetted)')
    check('and the reason says the document is silent, not opposed',
          'silent rather than opposed' in field.reason, True)
    check('everything else about the post survives',
          [decision.field(f).outcome for f in ('name', 'department', 'payScale')],
          [FieldOutcome.KEPT] * 3)


def test_one_contested_field_does_not_reject_the_whole_post() -> None:
    from .merge import FieldOutcome, merge_posts
    report = merge_posts(
        [authored('Alpha Service (AS)', classification='Group A (Gazetted)')],
        [post('Alpha Service')])
    kept = {f.field for f in report.decisions[0].fields if f.outcome is FieldOutcome.KEPT}
    check('the useful fields are still kept',
          {'name', 'department', 'payLevel', 'payScale'} <= kept, True)


def test_classifications_written_differently_still_agree() -> None:
    from .merge import FieldOutcome, merge_posts
    report = merge_posts(
        [authored('Alpha Service (AS)', classification='Group B (Non-Gazetted)')],
        [post('Alpha Service',
              classification='Group ‘B’ Gazetted (Non-Ministerial)')])
    check('both say B, so both agree',
          report.decisions[0].field('classification').outcome, FieldOutcome.CONFIRMED)


def test_an_unmatched_record_post_is_left_exactly_as_it_is() -> None:
    from .merge import merge_posts
    report = merge_posts([authored('Zeta Service')], [post('Alpha Service')])
    unchanged = report.of(MergeAction.UNCHANGED)
    check('a post the document does not name is untouched', len(unchanged), 1)
    check('and nothing is claimed about it', unchanged[0].fields, [])


def test_two_equally_good_matches_are_refused() -> None:
    from .merge import merge_posts
    report = merge_posts([authored('Alpha Service')],
                         [post('Alpha Service', pid='p1'), post('Alpha Service', pid='p2')])
    contested = report.of(MergeAction.CONFLICTED)
    check('an ambiguous match merges nothing', len(contested), 1)
    check('and says why', 'equally well' in contested[0].reason, True)
    check('no field is touched', contested[0].fields, [])


def test_a_post_only_the_document_names_is_added() -> None:
    from .merge import merge_posts
    report = merge_posts([authored('Alpha Service')], [post('Gamma Service')])
    check('the new post is ADDED',
          [d.name for d in report.of(MergeAction.ADDED)], ['Gamma Service'])


def test_ages_are_confirmed_against_the_post_that_states_them() -> None:
    from .merge import FieldOutcome, merge_posts
    from .schema import AgeRule
    target = post('Alpha Service', pid='p-alpha')
    rule = AgeRule(id='r1', scope=Scope([ScopeRef(ScopeKind.POST, 'p-alpha', 'Alpha')]),
                   minimum_age=Fact.verified(21.0, ev('doc')),
                   maximum_age=Fact.verified(32.0, ev('doc')))
    agreed = merge_posts([authored('Alpha Service (AS)', low=21, high=32)], [target],
                         age_rules=[rule])
    check('a matching band is confirmed',
          agreed.decisions[0].field('age').outcome, FieldOutcome.CONFIRMED)

    differing = merge_posts([authored('Alpha Service (AS)', low=18, high=30)], [target],
                            age_rules=[rule])
    field = differing.decisions[0].field('age')
    check('a differing band is held for review', field.outcome, FieldOutcome.UNDER_REVIEW)
    check('with both readings kept', (field.existing, field.incoming),
          ((18, 30), (21.0, 32.0)))


def test_only_the_posts_it_was_handed_are_decided() -> None:
    """Isolation is the caller's: the engine is given one record and one exam's
    extractions, and must invent no third post between them."""
    from .merge import merge_posts
    report = merge_posts([authored('Alpha Service')], [post('Beta Service')])
    check('every decision names a post one side actually holds',
          sorted(d.name for d in report.decisions), ['Alpha Service', 'Beta Service'])
    check('and the record post is untouched by the stranger',
          report.of(MergeAction.UNCHANGED)[0].name, 'Alpha Service')


def main() -> int:
    for fn in (test_match_needs_the_same_subject,
               test_two_papers_are_two_events_not_a_contradiction,
               test_a_window_is_compared_end_for_end,
               test_agreement_makes_one_fact_with_two_sources,
               test_a_corrigendum_supersedes_and_keeps_the_old_value,
               test_revision_wording_supersedes_without_a_corrigendum,
               test_two_readings_with_no_stated_relationship_are_refused,
               test_a_newer_document_does_not_win_by_being_newer,
               test_an_undated_statement_changes_nothing,
               test_new_information_is_added,
               test_nothing_is_ever_removed,
               test_an_empty_extraction_leaves_the_record_alone,
               test_the_engine_names_no_exam,
               test_a_post_the_record_abbreviates_is_still_the_same_post,
               test_a_matched_post_keeps_what_the_record_already_has,
               test_the_record_asserting_what_the_document_omits_is_held,
               test_one_contested_field_does_not_reject_the_whole_post,
               test_classifications_written_differently_still_agree,
               test_an_unmatched_record_post_is_left_exactly_as_it_is,
               test_two_equally_good_matches_are_refused,
               test_a_post_only_the_document_names_is_added,
               test_ages_are_confirmed_against_the_post_that_states_them,
               test_only_the_posts_it_was_handed_are_decided):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('merge: confirms, supersedes, refuses to choose — milestone and field')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
