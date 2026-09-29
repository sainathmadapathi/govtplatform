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


# ================================================ Q. windows, openings, stages
def _rows(text: str):
    return important_dates(milestones(text), exam_id='exam-x')


def _by_type(rows) -> dict:
    out: dict = {}
    for r in rows:
        out.setdefault(r['type'], []).append(r)
    return out


def test_q_a_window_yields_its_opening_and_its_closing() -> None:
    for text in ('Date of Submission of Online\nApplications From: 03/03/2031 To:24/03/2031',
                 'Apply online from 03.03.2031 to 24.03.2031.',
                 'Applications are invited from 03 March 2031 up to 24 March 2031.',
                 'Online application starts on 03/03/2031 and closes on 24/03/2031.',
                 'Online registration begins 03.03.2031 and ends 24.03.2031.'):
        got = _by_type(_rows(text))
        check(f'Q: opening read from "{text[:40]}"',
              [r['dateTimeStr'][:10] for r in got.get('APPLICATION_OPEN', [])], ['2031-03-03'])
        check(f'Q: closing read from "{text[:40]}"',
              [r['dateTimeStr'][:10] for r in got.get('APPLICATION_CLOSE', [])], ['2031-03-24'])
        opened = (got.get('APPLICATION_OPEN') or [{}])[0]
        check(f'Q: the opening cites a span carrying its own date ("{text[:30]}")',
              '03' in (opened.get('provenance') or {}).get('excerptText', ''), True)


def test_q_a_single_opening_is_not_a_deadline() -> None:
    got = _by_type(_rows('Online application starts on 03/03/2031.'))
    check('Q: an opening stated alone is the opening',
          [r['dateTimeStr'][:10] for r in got.get('APPLICATION_OPEN', [])], ['2031-03-03'])
    check('Q: and never the closing date', got.get('APPLICATION_CLOSE'), None)
    got = _by_type(_rows('Last date for submission of online applications is 24.03.2031.'))
    check('Q: a deadline stated alone is still the closing', len(got.get('APPLICATION_CLOSE', [])), 1)
    check('Q: with no opening invented', got.get('APPLICATION_OPEN'), None)


def test_q_the_notification_date_is_its_own_row() -> None:
    got = _by_type(_rows('Date of Notification 19/02/2031.\n'
                         'Applications From: 23/02/2031 To:14/03/2031'))
    check('Q: notification kept', [r['dateTimeStr'][:10] for r in got['NOTIFICATION']], ['2031-02-19'])
    check('Q: never standing in for the opening',
          [r['dateTimeStr'][:10] for r in got['APPLICATION_OPEN']], ['2031-02-23'])


def test_q_named_stages_keep_their_identity() -> None:
    text = ('Schedule of Preliminary Test\n(Objective Type) May/June 2031\n'
            'Schedule of Main Examination\n(Conventional Type) September/October 2031.')
    rows = _rows(text)
    exams = [r for r in rows if r['type'] in ('EXAM_TIER1', 'EXAM_TIER2')]
    check('Q: two examination dates', len(exams), 2)
    by = {r['type']: r for r in exams}
    check('Q: the preliminary is the first stage', by.get('EXAM_TIER1', {}).get('dateTimeStr', '')[:7], '2031-06')
    check('Q: the main examination is a later stage, not the first',
          by.get('EXAM_TIER2', {}).get('dateTimeStr', '')[:7], '2031-10')
    check('Q: both stated by their own evidence',
          sorted(r.get('stageAssociation') for r in exams), ['STATED', 'STATED'])
    check('Q: the stage words are inside the evidence span',
          'Main Examination' in by['EXAM_TIER2']['provenance']['excerptText'], True)
    check('Q: month-only dates stay tentative', all(r['isTentative'] for r in exams), True)


def test_q_an_unnamed_stage_is_held_for_review() -> None:
    rows = _rows('The examination will be held on 15 May 2031.')
    check('Q: one exam row', len(rows), 1)
    check('Q: kept in the historical bucket', rows[0]['type'], 'EXAM_TIER1')
    check('Q: but its stage is not claimed', rows[0].get('stageAssociation'), 'NEEDS_REVIEW')
    check('Q: a later stage is never mapped to the first by being an exam date',
          legacy_date_type('EXAM', stage_label='Main Examination'), 'EXAM_TIER2')
    check('Q: a third tier is a later stage', legacy_date_type('EXAM', stage_label='Tier III'), 'EXAM_TIER2')
    check('Q: the preliminary is the first', legacy_date_type('EXAM', stage_label='Preliminary Test'), 'EXAM_TIER1')
    tent = _rows('The examination is tentatively scheduled to be held on 15 May 2031.')
    check('Q: a hedged date is tentative', tent[0]['isTentative'], True)
    check('Q: rows that are not examinations carry no stage association',
          [r.get('stageAssociation') for r in _rows('Date of Notification 19/02/2031.')], [None])


def test_q_a_correction_window_named_noun_first() -> None:
    found = by_kind(milestones('Application Edit Option From: 23/03/2031 at 10:00 A.M.\n'
                               'To: 27/03/2031 at 5:00 P.M.'))
    check('Q: read as a correction window', 'CORRECTION_WINDOW' in found, True)
    check('Q: not as the application window', 'APPLICATION_WINDOW' in found, False)


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
        test_q_a_window_yields_its_opening_and_its_closing,
        test_q_a_single_opening_is_not_a_deadline,
        test_q_the_notification_date_is_its_own_row,
        test_q_named_stages_keep_their_identity,
        test_q_an_unnamed_stage_is_held_for_review,
        test_q_a_correction_window_named_noun_first,
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


import unittest as _unittest


class TestFlattenedTwoColumnSchedule(_unittest.TestCase):
    """A two-column schedule that extraction printed column by column: every label, then every
    date. The dates are the rows' in order; they must not all go to the last label."""

    TEXT = ('The tentative Schedule for the conduct of Examinations for the above posts is as under:-\n'
            '(i) Preliminary Examination\n'
            '(ii) Main Written Examination\n'
            '(iii) Personality Test/ Viva- Voce\n'
            '- 26.04.2031\n'
            '- 27.06.2031 to 29.06.2031\n'
            '- August / September,2031\n'
            'In case of a change, the schedule will be notified on the website.\n')

    def test_each_label_takes_its_own_row(self):
        items = milestones(self.TEXT, cycle='2031')
        got = sorted((m.kind, m.starts_at.value or m.ends_at.value) for m in items)
        self.assertEqual(got, [('EXAM', '2031-04-26'), ('EXAM', '2031-06-27'), ('INTERVIEW', '2031-09-01')])
        interview = next(m for m in items if m.kind == 'INTERVIEW')
        self.assertIsNone(interview.ends_at.value if interview.starts_at.has_value else None)
        self.assertEqual(interview.precision, DatePrecision.MONTH)
        # The table's heading says it is tentative; every row carries that.
        self.assertTrue(all(m.is_tentative for m in items))

    def test_the_evidence_is_the_table_as_printed(self):
        for m in milestones(self.TEXT, cycle='2031'):
            ev = (m.starts_at.evidence or m.ends_at.evidence)[0]
            self.assertTrue(ev.is_verbatim)
            self.assertIn('(i) Preliminary Examination', ev.span)
            self.assertIn('- August / September,2031', ev.span)

    def test_an_unequal_run_is_left_alone(self):
        from .dates import pair_label_columns
        parts = ['(i) Preliminary Examination', '(ii) Main Examination', '- 26.04.2031']
        self.assertEqual(pair_label_columns(parts), parts)


class TestARestatedRowIsNotReadAgain(_unittest.TestCase):
    """A notice states its opening date twice. The second statement is dropped as a repeat by
    the line reader -- and must not then be read again, without its reading, as a closing date."""

    def test_an_opening_stated_twice_never_becomes_a_close(self):
        text = ('a) Opening date for submission of online applications: 06.02.2031\n'
                'b) Closing date for the submission of online applications: 26.02.2031 upto 05:00 PM\n'
                'Some other clause.\n'
                'Item (s) Timeline\n'
                'Date of publication 30.01.2031\n'
                'Opening date for submission of online applications 06.02.2031\n'
                'Closing date for submission of online applications 26.02.2031\n'
                '(upto 05:00 PM)\n'
                'Category wise break-up of the posts are as under:-\n')
        items = milestones(text, cycle='2031')
        closes = sorted({m.ends_at.value for m in items
                         if m.kind in ('APPLICATION_WINDOW',) and m.ends_at.has_value})
        self.assertEqual(closes, ['2031-02-26'])
