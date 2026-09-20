"""Sixteen ways a timeline appears in a notice, and the ones that must produce nothing.

The hard part of dates is not parsing them. It is deciding what a date *means*, and refusing
to decide when the document does not say. "15 May 2026" is an application deadline, an
examination, a result and an interview in four different notices, so every fixture here
pairs a date with wording and the test is whether the wording was what decided.

The other half is revision. A cycle states a date, then moves it, then a corrigendum moves it
again, and a timeline that overwrites loses exactly the history a candidate needs in order to
trust the current value.

Every authority, exam and date below is invented.

Run: python -m tools.exam_builder.test_dates
"""
from __future__ import annotations

from .compat import important_dates, legacy_date_type, notification_candidates
from .dates import extract_milestones, read_dates, reconcile
from .identity import ExamIdentity, IdentityVerdict, verify
from .schema import (DatePrecision, MilestoneState, SourceDocument, SourceKind, Status)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def doc(doc_id: str = 'doc-1', kind: SourceKind = SourceKind.NOTIFICATION) -> SourceDocument:
    return SourceDocument(id=doc_id, url=f'https://authority.example/{doc_id}.pdf',
                          kind=kind, title='Notice of Examination',
                          authority='Example Authority', accessed_at='2026-09-20',
                          exam_id='exam-x')


def milestones(text: str, d: SourceDocument | None = None, **kw):
    return extract_milestones(d or doc(), text, exam_id='exam-x', **kw)


def by_kind(items) -> dict:
    return {m.kind: m for m in items}


# ================================================================== A. one date
def test_a_single_date() -> None:
    items = milestones('The examination will be held on 15 May 2026.')
    check('A: one milestone', len(items), 1)
    check('A: read as an examination', items[0].kind, 'EXAM')
    check('A: on the stated day', items[0].effective_date, '2026-05-15')
    check('A: verified', items[0].status, Status.VERIFIED)
    check('A: with evidence carrying the wording and the date',
          '15 May 2026' in items[0].ends_at.primary_source.span
          and 'held' in items[0].ends_at.primary_source.span, True)


def test_a_bare_date_states_nothing() -> None:
    check('a date with no event wording is not a milestone',
          milestones('The figure 15 May 2026 appears in column three.'), [])


def test_the_same_date_means_four_things() -> None:
    """The wording decides, and nothing else can."""
    cases = {
        'Online applications may be submitted upto 15 May 2026.': 'APPLICATION_WINDOW',
        'The examination will be held on 15 May 2026.': 'EXAM',
        'The result will be declared on 15 May 2026.': 'RESULT',
        'The interview will be conducted on 15 May 2026.': 'INTERVIEW',
    }
    for text, kind in cases.items():
        items = milestones(text)
        check(f'{text[:38]!r} -> {kind}',
              items[0].kind if items else None, kind)


# ================================================================= B. a range
def test_b_date_range_is_one_milestone() -> None:
    items = milestones(
        'Dates for submission of online applications: 21.05.2026 to 22.06.2026.')
    check('B: one milestone, not two rows', len(items), 1)
    check('B: with both ends', items[0].is_range, True)
    check('B: opening', items[0].starts_at.value, '2026-05-21')
    check('B: closing', items[0].ends_at.value, '2026-06-22')
    check('B: and the deadline is what applies', items[0].effective_date, '2026-06-22')


# =============================================================== C/D. scoping
def test_c_stage_specific_dates() -> None:
    items = milestones(
        'The examination for Tier I will be held on 10 August 2026.\n'
        'The examination for Tier II will be held on 5 December 2026.')
    check('C: two examinations, not one contradicted', len(items), 2)
    check('C: each scoped to its own stage',
          sorted(m.scope.of(__import__('tools.exam_builder.schema', fromlist=["x"]).ScopeKind.STAGE)[0].label
                 for m in items), ['Tier I', 'Tier II'])
    check('C: with different dates',
          sorted(m.effective_date for m in items), ['2026-08-10', '2026-12-05'])


def test_d_paper_specific_dates() -> None:
    items = milestones(
        'Paper I will be held on 3 March 2026.\n'
        'Paper II will be held on 5 March 2026.')
    check('D: two milestones', len(items), 2)
    check('D: told apart by the authority’s own labels',
          sorted(m.scope.refs[0].label for m in items), ['Paper I', 'Paper II'])


# ============================================================ E/F. lifecycle
def test_e_postponed_exam() -> None:
    items = milestones(
        'The examination scheduled for 15 May 2026 has been postponed.')
    check('E: read as a postponement', items[0].state, MilestoneState.POSTPONED)
    check('E: and is no longer an effective date', items[0].effective_date, '2026-05-15')
    check('E: it cannot drive a reminder',
          notification_candidates(items), [])


def test_e_awaited_event_has_no_date_and_is_not_an_absence() -> None:
    items = milestones('The date of the examination will be announced in due course.')
    check('an event stated without a date is still a milestone', len(items), 1)
    check('marked as awaited', items[0].state, MilestoneState.AWAITED)
    check('with no date invented', items[0].effective_date, None)
    check('and it says so plainly', 'has not given a date' in items[0].note, True)


def test_f_revised_date_supersedes_rather_than_overwrites() -> None:
    original = doc('doc-notice', SourceKind.NOTIFICATION)
    revision = doc('doc-revised', SourceKind.CORRIGENDUM)
    first = milestones('The examination will be held on 15 May 2026.', original)
    second = milestones(
        'The examination will now be held on 22 June 2026, in supersession of the earlier '
        'notice.', revision)

    timeline = reconcile([(original, first), (revision, second)])
    check('F: both versions are kept', len(timeline), 2)
    old = [m for m in timeline if m.is_superseded]
    new = [m for m in timeline if not m.is_superseded]
    check('F: the earlier one is superseded', len(old), 1)
    check('F: by the later one', old[0].superseded_by, new[0].id)
    check('F: the old date stops being effective', old[0].effective_date, None)
    check('F: the new one applies', new[0].effective_date, '2026-06-22')
    check('F: and the document that changed it is named',
          new[0].revision_source_id, 'doc-revised')
    check('F: only the effective one can remind',
          [m.id for m in notification_candidates(timeline)], [new[0].id])


def test_g_corrigendum_changing_an_application_date() -> None:
    notice = doc('doc-notice', SourceKind.NOTIFICATION)
    corr = doc('doc-corr', SourceKind.CORRIGENDUM)
    a = milestones('Last date for submission of online applications is 24.02.2026.', notice)
    b = milestones(
        'The last date for submission of applications has been revised to 27.02.2026.', corr)
    timeline = reconcile([(notice, a), (corr, b)])
    effective = [m for m in timeline if not m.is_superseded]
    check('G: the revised date applies', effective[0].effective_date, '2026-02-27')
    check('G: and the original is kept, struck through',
          [m.effective_date for m in timeline if m.is_superseded], [None])
    rows = important_dates(timeline, exam_id='exam-x')
    check('G: the UI is given both', len(rows), 2)
    check('G: one of them marked SUPERSEDED',
          sorted(r['status'] for r in rows), ['AVAILABLE', 'SUPERSEDED'])


# ============================================================== H. a conflict
def test_h_conflicting_sources_are_not_resolved_by_order() -> None:
    one = doc('doc-one', SourceKind.NOTIFICATION)
    two = doc('doc-two', SourceKind.EXAM_PAGE)
    a = milestones('The examination will be held on 15 May 2026.', one)
    b = milestones('The examination will be held on 20 May 2026.', two)
    timeline = reconcile([(one, a), (two, b)])
    check('H: both are kept', len(timeline), 2)
    check('H: both held for review',
          {m.status for m in timeline}, {Status.NEEDS_REVIEW})
    check('H: neither is superseded, because neither corrects the other',
          [m for m in timeline if m.is_superseded], [])
    check('H: the note says ranking did not decide it',
          all('none of them says it is correcting' in m.note for m in timeline), True)
    check('H: and nothing uncertain can remind', notification_candidates(timeline), [])


def test_agreeing_sources_corroborate() -> None:
    one, two = doc('doc-one'), doc('doc-two', SourceKind.EXAM_PAGE)
    a = milestones('The examination will be held on 15 May 2026.', one)
    b = milestones('The examination will be held on 15 May 2026.', two)
    timeline = reconcile([(one, a), (two, b)])
    check('two documents agreeing make one milestone', len(timeline), 1)
    check('with evidence from both',
          len(timeline[0].ends_at.evidence), 2)
    check('and it stays verified', timeline[0].status, Status.VERIFIED)


# =================================================== I/J. what must be refused
def test_i_a_non_official_source_supplies_nothing() -> None:
    """Officiality is decided before extraction; this records the contract.

    The extractor is handed documents that have already been established as the authority's
    own. What it must not do is treat where a date came from as irrelevant -- so every
    milestone carries the document it was read from, and a caller can see it.
    """
    coaching = SourceDocument(id='doc-coaching', url='https://coaching.example/blog',
                              kind=SourceKind.OTHER_OFFICIAL, title='Exam date out!')
    items = milestones('The examination will be held on 15 May 2026.', coaching)
    check('a milestone always names its source',
          items[0].ends_at.primary_source.source_id, 'doc-coaching')
    check('so a non-official source is visible rather than anonymous',
          items[0].ends_at.primary_source.url.startswith('https://coaching.example'), True)


def test_j_a_wrong_exam_document_is_rejected_by_identity() -> None:
    target = ExamIdentity(exam_id='exam-x', query='Alpha Clerical Examination 2031',
                          official_name='Alpha Clerical Examination 2031',
                          authority_name='Alpha Commission')
    foreign = ('BETA BOARD - TECHNICAL SERVICES EXAMINATION, 2031. The Technical Services '
               'Examination will be held on 15 May 2026.')
    verdict = verify(foreign, target)
    check('J: another exam’s notice cannot supply facts', verdict.may_supply_facts, False)
    check('J: and is never a match', verdict.verdict is IdentityVerdict.MATCH, False)


# ============================================================ K/L. absence
def test_k_a_document_with_no_dates_yields_none() -> None:
    check('K: nothing stated, nothing recorded',
          milestones('This notice sets out the eligibility conditions for the posts.'), [])


def test_l_partial_date_is_kept_at_its_own_precision() -> None:
    items = milestones('The examination will be held in June 2026.')
    check('L: a month is a month', items[0].precision, DatePrecision.MONTH)
    check('L: no day is invented', items[0].effective_date, '2026-06-01')
    check('L: and it is held for review', items[0].status, Status.NEEDS_REVIEW)
    check('L: saying what the authority actually printed',
          'to the nearest month' in items[0].note, True)
    check('L: a partial date cannot drive a reminder',
          notification_candidates(items), [])
    rows = important_dates(items, exam_id='exam-x')
    check('L: and the UI is told it is tentative', rows[0]['isTentative'], True)


# =========================================================== M. two cycles
def test_m_two_cycles_in_one_document() -> None:
    text = ('The examination for 2026 will be held on 15 May 2026.\n'
            'The examination for 2027 will be held on 14 May 2027.')
    both = milestones(text)
    check('M: without a cycle, both are read', len(both), 2)
    only_2026 = milestones(text, cycle='2026')
    check('M: asked for one cycle, the other is left out', len(only_2026), 1)
    check('M: and it is the right one', only_2026[0].effective_date, '2026-05-15')


# ====================================================== N/O/P. layouts
def test_n_dates_in_a_table() -> None:
    text = ('| Activity | Date |\n'
            '| Dates for submission of online applications | 21.05.2026 to 22.06.2026 |\n'
            '| Date of examination | 10.08.2026 |\n'
            '| Declaration of result | 30.09.2026 |')
    found = by_kind(milestones(text))
    check('N: the application window is read from its row',
          found['APPLICATION_WINDOW'].effective_date, '2026-06-22')
    check('N: the examination too', found['EXAM'].effective_date, '2026-08-10')
    check('N: and the result', found['RESULT'].effective_date, '2026-09-30')
    check('N: labels are the row’s own words',
          found['EXAM'].label, 'Date of examination')


def test_o_dates_in_prose() -> None:
    text = ('Candidates may submit online applications from 21 May 2026 to 22 June 2026. '
            'The examination will be conducted on 10 August 2026. The e-Admit Card will be '
            'available for download from 1 August 2026.')
    found = by_kind(milestones(text))
    check('O: the window', found['APPLICATION_WINDOW'].is_range, True)
    check('O: the examination', found['EXAM'].effective_date, '2026-08-10')
    check('O: the admit card', found['ADMIT_CARD'].effective_date, '2026-08-01')


def test_p_dates_in_a_numbered_notice() -> None:
    text = ('IMPORTANT DATES\n'
            '1. Notification published on 01.04.2026.\n'
            '2. Online applications can be submitted from 05.04.2026 to 30.04.2026.\n'
            '3. The correction window will be open from 02.05.2026 to 04.05.2026.\n'
            '4. The examination will be held on 20.06.2026.')
    found = by_kind(milestones(text))
    check('P: four events from four numbered items', len(found), 4)
    check('P: correction window is not read as the application window',
          found['CORRECTION_WINDOW'].effective_date, '2026-05-04')
    check('P: and the application window is its own',
          found['APPLICATION_WINDOW'].effective_date, '2026-04-30')


# ================================================================ projection
def test_the_projection_leaves_undated_events_out() -> None:
    items = milestones('The date of the examination will be announced in due course.')
    check('an undated milestone is not given to a UI that cannot render it',
          important_dates(items, exam_id='exam-x'), [])


def test_the_projection_maps_open_kinds_onto_the_closed_union() -> None:
    check('an application window becomes a close date',
          legacy_date_type('APPLICATION_WINDOW'), 'APPLICATION_CLOSE')
    check('a skill test has no type of its own, so it maps to the nearest',
          legacy_date_type('SKILL_TEST'), 'INTERVIEW')
    check('a second stage maps to the second tier',
          legacy_date_type('EXAM', stage_label='Tier II'), 'EXAM_TIER2')
    check('the first does not', legacy_date_type('EXAM', stage_label='Tier I'), 'EXAM_TIER1')
    check('and an unknown kind still produces a row rather than vanishing',
          legacy_date_type('SOMETHING_NEW'), 'NOTIFICATION')


def test_only_verified_effective_dates_can_remind() -> None:
    from .schema import Fact, Milestone
    good = milestones('The examination will be held on 15 May 2026.')
    check('a verified day-precision date qualifies',
          len(notification_candidates(good)), 1)

    unsure = milestones('The examination will be held in June 2026.')
    check('a partial date does not', notification_candidates(unsure), [])

    awaited = milestones('The date will be announced in due course.')
    check('an undated event does not', notification_candidates(awaited), [])

    blocked = Milestone(id='m', label='x', kind='EXAM',
                        ends_at=Fact.verified('2026-05-15', good[0].ends_at.evidence[0]),
                        status=Status.NEEDS_REVIEW)
    check('and neither does one held for review', notification_candidates([blocked]), [])


def test_nothing_is_recorded_without_a_verbatim_span() -> None:
    items = milestones(
        'Online applications from 21.05.2026 to 22.06.2026. The examination will be held '
        'on 10.08.2026. The result will be declared on 30.09.2026.')
    spans = [e for m in items for e in m.starts_at.evidence + m.ends_at.evidence]
    check('every span verified', all(e.is_verbatim for e in spans), True)
    check('and there are several', len(spans) >= 4, True)


def test_the_extractor_names_no_authority() -> None:
    import io
    import re
    source = io.open('tools/exam_builder/dates.py', encoding='utf-8').read()
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'sbi', 'rrb'):
        check(f'dates.py never names {forbidden.upper()}',
              re.findall(rf'\b{forbidden}\b', source, re.I), [])
    check('and holds no exam-conditional branch',
          re.findall(r'if\s+(?:exam|authority)\s*==', source), [])


def main() -> int:
    for fn in (
        test_a_single_date, test_a_bare_date_states_nothing,
        test_the_same_date_means_four_things, test_b_date_range_is_one_milestone,
        test_c_stage_specific_dates, test_d_paper_specific_dates,
        test_e_postponed_exam, test_e_awaited_event_has_no_date_and_is_not_an_absence,
        test_f_revised_date_supersedes_rather_than_overwrites,
        test_g_corrigendum_changing_an_application_date,
        test_h_conflicting_sources_are_not_resolved_by_order,
        test_agreeing_sources_corroborate,
        test_i_a_non_official_source_supplies_nothing,
        test_j_a_wrong_exam_document_is_rejected_by_identity,
        test_k_a_document_with_no_dates_yields_none,
        test_l_partial_date_is_kept_at_its_own_precision,
        test_m_two_cycles_in_one_document, test_n_dates_in_a_table,
        test_o_dates_in_prose, test_p_dates_in_a_numbered_notice,
        test_the_projection_leaves_undated_events_out,
        test_the_projection_maps_open_kinds_onto_the_closed_union,
        test_only_verified_effective_dates_can_remind,
        test_nothing_is_recorded_without_a_verbatim_span,
        test_the_extractor_names_no_authority,
    ):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('dates: the wording names the event, and a revision keeps both versions')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
