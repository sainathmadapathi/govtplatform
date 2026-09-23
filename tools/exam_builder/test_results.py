"""What the result reader, the merge and the projection must not do.

Every case here is either a real document's shape (UPSC's exam-page written-result rows, an
SSC Tier-I short-listing notice, IBPS's scheduled result row) or a rule the brief names. The
two that matter most: a scheduled date is never a declaration, and a shortlist is never a
selection.
"""
from __future__ import annotations

import unittest

from .compat import result_declarations
from .identity import ExamIdentity
from .merge import MergeAction
from .results import (classify_label, describe, may_supply_results, read_notice, read_row,
                      read_rows, source_failed)
from .results_merge import identity_key, merge_results, same_result
from .schema import (Fact, QualificationState, ResultDeclaration, ResultKind,
                     ResultLifecycle, Scope, ScopeKind, ScopeRef, SourceDocument,
                     SourceEvidence, SourceKind, SourceOutcome, Status)

SSC = 'exam-ssc-cgl-2026'
UPSC = 'exam-upsc-cse-2026'


def doc(url='https://ssc.gov.in/result.pdf', title='Result notice', authority='SSC',
        exam_id=SSC, published_at='2026-01-09'):
    return SourceDocument(id=url, url=url, kind=SourceKind.OTHER_OFFICIAL, title=title,
                          authority=authority, accessed_at='2026-09-23', exam_id=exam_id,
                          published_at=published_at)


#: An SSC Tier-I short-listing notice, in the Commission's own wording (from a real CHSL one
#: of the same form), for the CGL 2025 cycle.
SSC_TIER1 = (
    'Combined Graduate Level Examination (CGLE), 2025 - Declaration of result of Tier-I to '
    'shortlist candidates for appearing in Tier-II. Staff Selection Commission conducted '
    'Tier-I of the Combined Graduate Level Examination (CGLE), 2025 from 12.09.2025 to '
    '26.09.2025 in the Computer Based Mode. On the basis of the performance, 1,50,000 '
    'candidates have been shortlisted for appearing in Tier-II. The result was declared on '
    '09.01.2026.')
SSC_TIER1_HEAD = ('Combined Graduate Level Examination, 2025 (Tier-I) – Declaration of '
                  'Result of Tier-I for short-listing candidates for Tier-II')


def notice(text, head='', exam_id=SSC, **kw):
    return read_notice(doc(exam_id=exam_id), text, exam_id=exam_id, headline=head, **kw)


def one(events, kind=None):
    for e in events:
        if kind is None or e.kind is kind:
            return e
    raise AssertionError(f'no {kind} event in {[e.kind for e in events]}')


class TestKinds(unittest.TestCase):
    """A–H, J–L. Every result type the label names, distinctly."""

    def test_a_basic_result_declaration(self):
        self.assertIs(classify_label('Declaration of Result'), ResultKind.RESULT)

    def test_b_stage_result(self):
        self.assertIs(classify_label('Result of Tier-I'), ResultKind.STAGE_RESULT)

    def test_c_final_result(self):
        self.assertIs(classify_label('Declaration of Final Result'), ResultKind.FINAL_RESULT)

    def test_d_shortlist(self):
        self.assertIs(classify_label('Short-listing candidates for Tier-II'),
                      ResultKind.SHORTLIST)

    def test_e_qualified_candidates(self):
        self.assertIs(classify_label('List of qualified candidates'),
                      ResultKind.QUALIFIED_LIST)

    def test_f_selected_candidates(self):
        self.assertIs(classify_label('Selection list of candidates'), ResultKind.SELECTION)

    def test_g_recommended(self):
        self.assertIs(classify_label('Candidates recommended for appointment'),
                      ResultKind.RECOMMENDATION)

    def test_h_waiting_list(self):
        self.assertIs(classify_label('Reserve list of candidates'), ResultKind.WAITLIST)

    def test_i_scorecard(self):
        self.assertIs(classify_label('Uploading of Response Sheets'), ResultKind.SCORECARD)

    def test_j_marks(self):
        self.assertIs(classify_label('Uploading of Marks of candidates'), ResultKind.MARKS)

    def test_k_merit_list(self):
        self.assertIs(classify_label('Final Merit List'), ResultKind.MERIT_LIST)

    def test_l_dv_and_interview_shortlists_are_distinct(self):
        self.assertIs(classify_label('Document Verification short-list'),
                      ResultKind.DV_SHORTLIST)
        self.assertIs(classify_label('Interview short-list'),
                      ResultKind.INTERVIEW_SHORTLIST)

    def test_m_a_label_naming_none_produces_nothing(self):
        self.assertIsNone(classify_label('Exam City Intimation Slip'))
        self.assertIsNone(read_row('Question Paper', 'GS-I', doc(), '', exam_id=SSC))


class TestDeclaredVsScheduled(unittest.TestCase):
    """I, W, AA. A schedule is never a declaration."""

    def test_n_a_declaration_has_a_declared_date_not_an_expected_one(self):
        e = one(notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025'))
        self.assertEqual(e.published_at.value, '2026-01-09')
        self.assertFalse(e.expected_at.has_value)
        self.assertTrue(e.is_declaration)

    def test_o_a_scheduled_row_has_an_expected_date_not_a_declared_one(self):
        e = read_row('Result of Online examination – Preliminary', 'September, 2026',
                     doc(exam_id='exam-ibps-po-2026'),
                     'Result of Online examination – Preliminary September, 2026',
                     exam_id='exam-ibps-po-2026')
        self.assertIs(e.kind, ResultKind.SCHEDULED)
        self.assertFalse(e.is_declaration)
        self.assertEqual(e.expected_at.value, '2026-09-01')
        self.assertEqual(e.expected_precision, 'MONTH')
        self.assertFalse(e.published_at.has_value)

    def test_p_a_declaration_carries_an_aggregate_count_not_candidate_rows(self):
        e = one(notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025'))
        self.assertEqual(e.qualified_count.value, 150000)


class TestNextStage(unittest.TestCase):
    """M, N. Next stage is read, never assumed."""

    def test_q_next_stage_is_read_where_the_source_names_it(self):
        e = one(notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025'))
        self.assertEqual(e.next_stage_ref, 'tier-ii')
        self.assertIn('Tier-II', e.next_step.value)

    def test_r_no_next_stage_is_claimed_where_none_is_named(self):
        e = read_row('e - Written Result', 'WR-CSP-2026.pdf 15/06/2026',
                     doc(exam_id=UPSC), 'e - Written Result WR-CSP-2026.pdf 15/06/2026',
                     exam_id=UPSC, authority_domain='upsc.gov.in')
        self.assertFalse(e.next_step.has_value)


class TestQualification(unittest.TestCase):
    """E, F, AI. Qualified is not selected, and neither is inferred."""

    def test_s_a_shortlist_is_shortlisted_not_selected(self):
        e = one(notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025'))
        self.assertIs(e.qualification, QualificationState.SHORTLISTED)
        self.assertIsNot(e.qualification, QualificationState.SELECTED)

    def test_t_selection_is_read_only_where_stated(self):
        e = one(notice('Declaration of Final Result. The following candidates have been '
                       'finally selected and recommended for appointment. Result declared '
                       'on 17.06.2026.', 'Declaration of Final Result', cycle='2025'))
        self.assertIn(e.qualification,
                      (QualificationState.SELECTED, QualificationState.RECOMMENDED))

    def test_u_no_qualification_is_invented(self):
        e = read_row('Written Result', 'WR-CSP-2026.pdf 15/06/2026', doc(exam_id=UPSC),
                     'Written Result WR-CSP-2026.pdf 15/06/2026', exam_id=UPSC,
                     authority_domain='upsc.gov.in')
        self.assertIs(e.qualification, QualificationState.UNSTATED)


class TestDocumentUrls(unittest.TestCase):
    """AH, and the no-fabricated-link rule."""

    def test_v_a_bare_filename_resolves_against_the_authority_host(self):
        e = read_row('Written Result', 'WR-CSP-2026-RollList-Engl-150626.pdf 15/06/2026',
                     doc(exam_id=UPSC),
                     'Written Result WR-CSP-2026-RollList-Engl-150626.pdf 15/06/2026',
                     exam_id=UPSC, authority_domain='upsc.gov.in')
        self.assertTrue(e.document_url.value.startswith('https://upsc.gov.in/'))
        self.assertTrue(e.document_url.value.endswith('.pdf'))

    def test_w_no_document_link_is_invented_where_none_exists(self):
        e = one(notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025'))
        self.assertFalse(e.document_url.is_publishable)
        row = result_declarations([e], exam_id=SSC)[0]
        self.assertNotIn('documentUrl', row)


class TestIdentityAndIsolation(unittest.TestCase):
    """O, P, Q, R, AE. Exact exam, cycle, stage — or nothing."""

    def test_x_another_cycles_result_supplies_nothing(self):
        target = ExamIdentity(exam_id=SSC, query='SSC Combined Graduate Level Examination',
                              official_name='Combined Graduate Level Examination',
                              authority_name='Staff Selection Commission', year='2025')
        ok, _ = may_supply_results(SSC_TIER1, target)
        self.assertTrue(ok)  # this fixture is the 2025 cycle, matching the target's year
        target26 = ExamIdentity(exam_id=SSC, query='SSC Combined Graduate Level Examination',
                                official_name='Combined Graduate Level Examination',
                                authority_name='Staff Selection Commission', year='2026')
        ok26, why = may_supply_results(SSC_TIER1, target26)
        self.assertFalse(ok26)
        self.assertIn('2025', why)

    def test_y_a_projection_drops_another_exams_declaration(self):
        e = read_row('Written Result', 'WR-CSP-2026.pdf 15/06/2026', doc(exam_id=UPSC),
                     'Written Result WR-CSP-2026.pdf 15/06/2026', exam_id=UPSC,
                     authority_domain='upsc.gov.in')
        rows = result_declarations([e], exam_id=UPSC)
        self.assertEqual(rows[0]['examId'], UPSC)

    def test_z_kind_cycle_stage_are_part_of_identity(self):
        def make(kind, stage, cycle):
            return ResultDeclaration(
                id=f'{kind.value}-{stage}-{cycle}', kind=kind, cycle=cycle,
                scope=Scope(refs=[ScopeRef(kind=ScopeKind.STAGE, ref=stage.lower(),
                                           label=stage)]),
                published_at=Fact.verified('2026-06-15', []), status=Status.VERIFIED)
        prelims = make(ResultKind.WRITTEN_RESULT, 'Preliminary', '2026')
        final = make(ResultKind.FINAL_RESULT, 'Preliminary', '2026')
        old = make(ResultKind.WRITTEN_RESULT, 'Preliminary', '2025')
        self.assertFalse(same_result(prelims, final, exam_id=UPSC))
        self.assertFalse(same_result(prelims, old, exam_id=UPSC))
        self.assertNotEqual(identity_key(prelims, UPSC), identity_key(prelims, SSC))


class TestMerge(unittest.TestCase):
    """S, T, U, AR. Revision never overwrites; conflict settles nothing."""

    def result(self, kind=ResultKind.WRITTEN_RESULT, stage='Preliminary', value='2026-06-15',
               rid='r1', published='2026-06-15', lifecycle=ResultLifecycle.ORIGINAL,
               note=''):
        return ResultDeclaration(
            id=rid, kind=kind, cycle='2026',
            scope=Scope(refs=[ScopeRef(kind=ScopeKind.STAGE, ref=stage.lower(),
                                       label=stage)]),
            published_at=Fact.verified(value, []), status=Status.VERIFIED,
            lifecycle=lifecycle, note=note,
            evidence=[SourceEvidence(source_id=rid, published_at=published)])

    def test_aa_an_unmatched_result_is_added(self):
        r = merge_results([], [self.result()], exam_id=UPSC)
        self.assertEqual(r.summary(), {'ADDED': 1})

    def test_ab_the_same_declaration_from_a_second_source_confirms(self):
        r = merge_results([self.result(rid='a')], [self.result(rid='b')], exam_id=UPSC)
        self.assertEqual(r.summary(), {'CONFIRMED': 1})
        self.assertEqual(len(r.results), 1)

    def test_ac_a_later_revision_supersedes_and_the_earlier_is_kept(self):
        first = self.result(rid='a', value='2026-06-15', published='2026-06-15')
        later = self.result(rid='b', value='2026-06-20', published='2026-06-19')
        r = merge_results([first], [later], exam_id=UPSC)
        self.assertEqual(r.summary(), {'SUPERSEDED': 1})
        self.assertEqual(len(r.results), 2)
        self.assertIs(first.lifecycle, ResultLifecycle.SUPERSEDED)
        self.assertIs(later.lifecycle, ResultLifecycle.REVISED)
        self.assertEqual(later.supersedes, 'a')

    def test_ad_a_cancellation_is_carried_not_overwritten(self):
        first = self.result(rid='a', published='2026-06-15')
        cancel = self.result(rid='b', value='2026-06-20', published='2026-06-19',
                             note='Result cancelled owing to a re-examination.')
        r = merge_results([first], [cancel], exam_id=UPSC)
        self.assertEqual(r.summary(), {'SUPERSEDED': 1})
        self.assertIs(cancel.lifecycle, ResultLifecycle.CANCELLED)
        self.assertIs(first.lifecycle, ResultLifecycle.SUPERSEDED)

    def test_ae_two_declarations_no_revision_settles_nothing(self):
        first = self.result(rid='a', value='2026-06-15', published='')
        rival = self.result(rid='b', value='2026-06-20', published='')
        r = merge_results([first], [rival], exam_id=UPSC)
        self.assertEqual(r.summary(), {'CONFLICTED': 1})
        self.assertEqual(len(r.results), 2)
        self.assertIs(rival.status, Status.NEEDS_REVIEW)
        self.assertIs(first.status, Status.VERIFIED)

    def test_af_a_final_result_never_merges_into_a_written_result(self):
        w = self.result(kind=ResultKind.WRITTEN_RESULT, rid='a')
        f = self.result(kind=ResultKind.FINAL_RESULT, rid='b', value='2026-08-01')
        r = merge_results([w], [f], exam_id=UPSC)
        self.assertEqual(r.summary(), {'ADDED': 1})
        self.assertEqual(len(r.results), 2)


class TestInfrastructureIsNotAStatus(unittest.TestCase):
    """V, W. A fetch failure is not "no result"."""

    def test_ag_a_failed_fetch_is_classified_as_infrastructure(self):
        outcome, _ = source_failed(OSError('The read operation timed out'))
        self.assertIs(outcome, SourceOutcome.NETWORK_UNAVAILABLE)
        outcome, _ = source_failed('<HTTPError 404: Not Found>')
        self.assertIs(outcome, SourceOutcome.SOURCE_FETCH_FAILURE)

    def test_ah_no_infrastructure_outcome_can_become_a_status(self):
        for outcome in SourceOutcome:
            self.assertNotIn(outcome.value, {s.value for s in Status})

    def test_ai_an_unread_source_yields_no_declaration(self):
        self.assertEqual(read_notice(doc(), '', exam_id=SSC), [])
        self.assertEqual(read_rows([], doc(), '', exam_id=SSC), [])


class TestExtractionShapes(unittest.TestCase):
    """AB, AC, AJ. Flattened notice, table row, scorecard vs marks."""

    def test_aj_a_flattened_notice_reads_one_declaration(self):
        events = notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025')
        self.assertEqual(len(events), 1)
        self.assertIn(events[0].kind, (ResultKind.SHORTLIST, ResultKind.STAGE_RESULT))

    def test_ak_a_scorecard_row_is_not_a_marks_row(self):
        sc = read_row('Uploading of Response Sheets', '', doc(), 'Uploading of Response '
                      'Sheets', exam_id=SSC)
        mk = read_row('Uploading of Marks of candidates', '', doc(), 'Uploading of Marks '
                      'of candidates', exam_id=SSC)
        self.assertIs(sc.kind, ResultKind.SCORECARD)
        self.assertIs(mk.kind, ResultKind.MARKS)

    def test_al_a_cell_seam_ends_a_scheduled_row_value(self):
        e = read_row('Result of Online examination – Preliminary',
                     'September, 2026 Online Examination – Main October, 2026',
                     doc(exam_id='exam-ibps-po-2026'), '', exam_id='exam-ibps-po-2026')
        self.assertEqual(e.expected_at.value, '2026-09-01')


class TestProvenanceAndPublishability(unittest.TestCase):
    """AD, and the publishability gate."""

    def test_am_a_declaration_with_no_verbatim_span_is_not_publishable(self):
        e = ResultDeclaration(id='x', cycle='2026',
                              published_at=Fact.needs_review('2026-01-01', 'unverified'),
                              status=Status.NEEDS_REVIEW)
        self.assertFalse(e.is_publishable)

    def test_an_a_real_declaration_is_publishable_and_carries_provenance(self):
        e = one(notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025'))
        self.assertTrue(e.is_publishable)
        row = result_declarations([e], exam_id=SSC)[0]
        self.assertIn('provenance', row)

    def test_ao_describe_counts_declared_and_scheduled_apart(self):
        decl = notice(SSC_TIER1, SSC_TIER1_HEAD, cycle='2025')
        sched = [read_row('Result of Online examination – Preliminary', 'September, 2026',
                          doc(exam_id='exam-ibps-po-2026'),
                          'Result of Online examination – Preliminary September, 2026',
                          exam_id='exam-ibps-po-2026')]
        d = describe(decl + sched)
        self.assertEqual(d['declared'], 1)
        self.assertEqual(d['scheduled'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
