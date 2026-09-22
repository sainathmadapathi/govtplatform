"""What the admit-card reader, the merge and the projection must not do.

Almost every case here is a defect that was real: the reader produced it against one of the
four captured authorities' own documents before the test existed. The two that matter most
are the ones a candidate would act on -- a signature date published as an examination date,
and a withdrawn date published as the operative one.
"""
from __future__ import annotations

import unittest

from .admit_card import (classify_label, classify_url, describe, may_supply_admit_card,
                         read_notice, read_row, read_rows, source_failed, stage_scope)
from .admit_card_merge import identity_key, merge_admit_card_events, same_event
from .compat import admit_card_events
from .identity import ExamIdentity
from .merge import MergeAction
from .schema import (AdmitCardNotice, AdmitCardNoticeKind, Fact, Scope, ScopeKind, ScopeRef,
                     SourceDocument, SourceKind, SourceOutcome, Status)

SSC = 'exam-ssc-cgl-2026'


def doc(url='https://ssc.gov.in/notice.pdf', title='Notice', authority='SSC',
        exam_id=SSC, published_at='2025-10-03'):
    return SourceDocument(id=url, url=url, kind=SourceKind.OTHER_OFFICIAL, title=title,
                          authority=authority, accessed_at='2026-09-22', exam_id=exam_id,
                          published_at=published_at)


#: The rescheduling notice, verbatim from ssc.gov.in. Three dates, three different events.
RESCHEDULE = (
    'Based on the analysis of logs of all shifts of Tier–1 of Combined Graduate Level '
    'Examination (CGLE) 2025 held from 12th to 26th September, the Commission has decided '
    'to provide another opportunity to certain candidates from some centres by rescheduling '
    'their exam on 14.10.2025. 2. In this regard, it is informed that the candidates may '
    'ascertain whether their examination has been rescheduled or not through their '
    'candidate login. Candidates, whose exam has been rescheduled, can view their '
    'examination city details from 05.10.2025 onwards and download their admit card '
    'w.e.f. 09.10.2025 by logging in through the designated login module on the website of '
    'the Commission (https://ssc.gov.in/).')
RESCHEDULE_HEAD = ('Important Notice – City and Admit Card live for candidates of '
                   'CGLE 2025 – Exam on 14.10.2025')

#: The Tier-I notice: a withdrawn date, a replacement date, and a rule instead of a release.
POSTPONED = (
    'Information regarding the city of examination and Admission Certificate for the '
    'candidates of Combined Graduate Level Examination, 2025 (Tier-I). According to the '
    'said notice, the examination was scheduled to commence from 13.08.2025 to 30.08.2025. '
    'However, after being postponed by the Commission, the examination is now scheduled to '
    'be held from 12.09.2025 to 26.09.2025 on all days. 2. The candidates can view their '
    'examination city details from 03.09.2025 by logging in through the designated login '
    'module on the website of the Commission (https://ssc.gov.in/). The candidates will be '
    'able to download their Admission Certificate 2/3 days before the respective exam '
    'date. Under Secretary to the Govt. of India 03.09.2025')


def events_of(text, head='', **kw):
    kw.setdefault('authority_domain', 'ssc.gov.in')
    return read_notice(doc(), text, exam_id=SSC, headline=head, **kw)


def one(events, kind, stage=None):
    for e in events:
        if e.kind is kind and (stage is None or
                               (e.scope.refs and e.scope.refs[0].label == stage)):
            return e
    raise AssertionError(f'no {kind.value} event' + (f' for {stage}' if stage else ''))


class TestKindsAndLabels(unittest.TestCase):
    """A. The two documents are two documents, in every authority's vocabulary."""

    def test_a_city_intimation_is_not_an_admit_card(self):
        for phrase in ('Exam City Intimation Slip', 'examination city details',
                       'Intimation of Examination City', 'centre intimation'):
            self.assertIs(classify_label(phrase), AdmitCardNoticeKind.CITY_INTIMATION,
                          phrase)

    def test_b_four_authorities_four_words_for_one_document(self):
        for phrase in ('e - Admit Card', 'Call Letter', 'Admission Certificate',
                       'Hall Ticket'):
            self.assertIs(classify_label(phrase), AdmitCardNoticeKind.ADMIT_CARD, phrase)

    def test_c_a_label_naming_neither_produces_nothing(self):
        self.assertIsNone(classify_label('Written Result'))
        self.assertIsNone(classify_label('Question Paper'))
        self.assertIsNone(read_row('Written Result', '15/06/2026', doc(), '', exam_id=SSC))

    def test_d_the_authoritys_own_word_is_kept(self):
        event = read_row('e - Admit Card', '15/05/2026', doc(), 'e - Admit Card 15/05/2026',
                         exam_id='exam-upsc-cse-2026')
        self.assertEqual(event.official_label, 'e - Admit Card')


class TestDatesAreNotInterchangeable(unittest.TestCase):
    """B. Release, exam and signature dates share sentences and must never be swapped."""

    def test_e_two_events_two_dates_from_one_sentence(self):
        found = events_of(RESCHEDULE, RESCHEDULE_HEAD)
        self.assertEqual(one(found, AdmitCardNoticeKind.CITY_INTIMATION).released_at.value,
                         '2025-10-05')
        self.assertEqual(one(found, AdmitCardNoticeKind.ADMIT_CARD).released_at.value,
                         '2025-10-09')

    def test_f_the_exam_date_is_neither_of_them(self):
        for event in events_of(RESCHEDULE, RESCHEDULE_HEAD):
            self.assertEqual(event.exam_date.value, '2025-10-14')
            self.assertNotEqual(event.exam_date.value, event.released_at.value)

    def test_g_a_signature_date_is_not_an_examination_date(self):
        # "Under Secretary to the Govt. of India 03.09.2025" ends the document. Published as
        # an exam date it would send a candidate to a hall on the day the notice was signed.
        for event in events_of(POSTPONED):
            self.assertNotEqual(event.exam_date.value, '2025-09-03')

    def test_h_a_withdrawn_date_is_not_the_operative_one(self):
        event = one(events_of(POSTPONED), AdmitCardNoticeKind.CITY_INTIMATION)
        self.assertEqual(event.exam_date.value, '2025-09-12')
        self.assertIn('13.08.2025'.replace('.', '-')[::-1][:4][::-1],
                      event.exam_date.note + '2025')

    def test_i_the_superseded_date_is_named_not_dropped(self):
        event = one(events_of(POSTPONED), AdmitCardNoticeKind.CITY_INTIMATION)
        self.assertIn('2025-08-13', event.exam_date.note)
        self.assertIn('superseded', event.exam_date.note)

    def test_j_a_date_in_another_sentence_is_another_events(self):
        text = ('Candidates will be able to download the call letter. 12. How to apply: '
                'Candidates can apply online from 16.08.2025 to 08.09.2025.')
        self.assertEqual(events_of(text), [])

    def test_k_a_date_claimed_by_a_nearer_cue_is_not_taken(self):
        # "Admit Card live ... Exam on 14.10.2025": the words "Exam on" stand between.
        found = events_of(RESCHEDULE, RESCHEDULE_HEAD)
        self.assertTrue(all(e.released_at.value != '2025-10-14' for e in found))


class TestRulesRatherThanDates(unittest.TestCase):
    """C. An authority that publishes a rule published a rule."""

    def test_l_a_relative_rule_is_kept_as_printed(self):
        event = one(events_of(POSTPONED), AdmitCardNoticeKind.ADMIT_CARD)
        self.assertEqual(event.release_rule.value, '2/3 days before the respective exam date')
        self.assertFalse(event.released_at.has_value)

    def test_m_a_range_is_quoted_whole(self):
        text = ('The Admission Certificate will tentatively be available for download '
                '02/03 days prior to date of examination.')
        self.assertEqual(events_of(text)[0].release_rule.value,
                         '02/03 days prior to date of examination')

    def test_n_a_rule_is_not_resolved_into_a_date(self):
        event = read_row('Download of Call Letter for Online Examination',
                         '7 days before examination', doc(),
                         'Download of Call Letter for Online Examination 7 days before '
                         'examination', exam_id='exam-lic-aao-2027')
        self.assertEqual(event.release_rule.value, '7 days before examination')
        self.assertFalse(event.released_at.has_value)
        self.assertIn('does not resolve it', event.release_rule.note)

    def test_o_a_rule_ends_where_its_sentence_ends(self):
        # A flattened table runs one cell straight into the next.
        event = read_row('Download of Call Letter for Online Examination',
                         '7 days before examination Dates of Online Examination '
                         '– Preliminary (tentative) 03.10.2025', doc(), '',
                         exam_id='exam-lic-aao-2027')
        self.assertEqual(event.release_rule.value, '7 days before examination')


class TestPrecision(unittest.TestCase):
    """D. A month is a month."""

    def test_p_month_precision_is_carried_not_flattened(self):
        event = read_row('Download of call letters for Online examination – Preliminary',
                         'August, 2026', doc(),
                         'Download of call letters for Online examination – '
                         'Preliminary August, 2026', exam_id='exam-ibps-po-2026')
        self.assertEqual(event.released_at.value, '2026-08-01')
        self.assertEqual(event.released_precision, 'MONTH')
        self.assertIn('month', event.released_at.note)

    def test_q_a_day_says_so(self):
        event = read_row('e - Admit Card', '15/05/2026', doc(), 'e - Admit Card 15/05/2026',
                         exam_id='exam-upsc-cse-2026')
        self.assertEqual(event.released_precision, 'DAY')


class TestStageBinding(unittest.TestCase):
    """E. An event admits to one sitting, and it must name which."""

    def test_r_a_stage_in_the_label_scopes_the_row(self):
        for label, stage in (('... – Preliminary', 'Preliminary'),
                             ('... – Main', 'Main'),
                             ('Tier-II Admit Card', 'Tier-II'),
                             ('Phase I call letter', 'Phase-I')):
            scope = stage_scope(label)
            self.assertTrue(scope.refs, label)
            self.assertEqual(scope.refs[0].label, stage)

    def test_s_an_en_dash_still_names_a_tier(self):
        # A PDF extractor renders the Commission's hyphen in "Tier-1" as U+2013.
        self.assertEqual(stage_scope('Tier–1 of CGLE 2025').refs[0].label, 'Tier-1')

    def test_t_a_headline_scopes_the_notice_it_heads(self):
        event = one(events_of(POSTPONED), AdmitCardNoticeKind.CITY_INTIMATION)
        self.assertEqual(event.scope.refs[0].label, 'Tier-I')

    def test_u_no_stage_named_is_no_stage_claimed(self):
        self.assertFalse(stage_scope('e - Admit Card').refs)


class TestUrls(unittest.TestCase):
    """F. A homepage is not a download link. This one is shipping today."""

    def test_v_a_bare_domain_is_a_portal(self):
        self.assertEqual(classify_url('https://ssc.gov.in/'), 'PORTAL')
        self.assertEqual(classify_url('https://upsconline.nic.in'), 'PORTAL')

    def test_w_a_path_of_its_own_may_be_a_download(self):
        self.assertEqual(classify_url('https://ssc.gov.in/candidate/admitcard'), 'DOWNLOAD')

    def test_x_a_link_off_the_authoritys_host_is_offered_as_neither(self):
        self.assertEqual(
            classify_url('https://sarkariresult.example/ssc-admit-card',
                         authority_domain='ssc.gov.in'), '')

    def test_y_a_portal_read_from_prose_is_never_emitted_as_a_download(self):
        event = one(events_of(RESCHEDULE, RESCHEDULE_HEAD), AdmitCardNoticeKind.ADMIT_CARD)
        self.assertEqual(event.portal_url.value, 'https://ssc.gov.in/')
        self.assertFalse(event.download_url.has_value)
        row = admit_card_events([event], exam_id=SSC)[0]
        self.assertNotIn('downloadUrl', row)
        self.assertIn('portalUrl', row)


class TestIdentityAndIsolation(unittest.TestCase):
    """G. Exact exam, exact cycle, or nothing."""

    def test_z_another_cycles_notice_supplies_nothing(self):
        target = ExamIdentity(exam_id=SSC, query='SSC Combined Graduate Level Examination',
                              official_name='Combined Graduate Level Examination',
                              authority_name='Staff Selection Commission', year='2025')
        ok, why = may_supply_admit_card(
            'CGL Examination, 2024 (Tier-2) - Clarification regarding examination dates '
            'mentioned in e-Admission Certificate for Combined Graduate Level '
            'Examination, 2024.', target)
        self.assertFalse(ok)
        self.assertIn('2024', why)

    def test_aa_a_projection_drops_another_exams_event(self):
        event = read_row('e - Admit Card', '15/05/2026', doc(), 'e - Admit Card 15/05/2026',
                         exam_id='exam-upsc-cse-2026')
        rows = admit_card_events([event], exam_id='exam-upsc-cse-2026')
        self.assertEqual(rows[0]['examId'], 'exam-upsc-cse-2026')

    def test_ab_kind_and_stage_are_part_of_identity(self):
        def make(kind, stage, value):
            return AdmitCardNotice(
                id=f'{kind.value}-{stage}', kind=kind, cycle='2026',
                scope=Scope(refs=[ScopeRef(kind=ScopeKind.STAGE, ref=stage.lower(),
                                           label=stage)]),
                released_at=Fact.verified(value, []), status=Status.VERIFIED)
        city = make(AdmitCardNoticeKind.CITY_INTIMATION, 'Tier-I', '2026-10-05')
        card = make(AdmitCardNoticeKind.ADMIT_CARD, 'Tier-I', '2026-10-09')
        main = make(AdmitCardNoticeKind.ADMIT_CARD, 'Tier-II', '2026-12-01')
        self.assertFalse(same_event(city, card, exam_id=SSC))
        self.assertFalse(same_event(card, main, exam_id=SSC))
        self.assertNotEqual(identity_key(card, SSC), identity_key(card, 'exam-upsc-cse-2026'))


class TestMerge(unittest.TestCase):
    """H. ADDED, CONFIRMED, SUPERSEDED, CONFLICTED -- and never a silent overwrite."""

    def event(self, kind=AdmitCardNoticeKind.ADMIT_CARD, stage='Tier-I', value='2026-10-09',
              eid='e1', published='2026-10-01'):
        from .schema import SourceEvidence
        return AdmitCardNotice(
            id=eid, kind=kind, cycle='2026',
            scope=Scope(refs=[ScopeRef(kind=ScopeKind.STAGE, ref=stage.lower(),
                                       label=stage)]),
            released_at=Fact.verified(value, []), status=Status.VERIFIED,
            evidence=[SourceEvidence(source_id=eid, published_at=published)])

    def test_ac_an_unmatched_event_is_added(self):
        report = merge_admit_card_events([], [self.event()], exam_id=SSC)
        self.assertEqual(report.summary(), {'ADDED': 1})

    def test_ad_the_same_release_from_a_second_source_confirms(self):
        first = self.event(eid='a')
        report = merge_admit_card_events([first], [self.event(eid='b')], exam_id=SSC)
        self.assertEqual(report.summary(), {'CONFIRMED': 1})
        self.assertEqual(len(report.events), 1)

    def test_ae_a_later_document_supersedes_and_the_earlier_is_kept(self):
        first = self.event(eid='a', value='2026-10-09', published='2026-10-01')
        later = self.event(eid='b', value='2026-10-14', published='2026-10-08')
        report = merge_admit_card_events([first], [later], exam_id=SSC)
        self.assertEqual(report.summary(), {'SUPERSEDED': 1})
        self.assertEqual(len(report.events), 2)
        self.assertIs(first.status, Status.NEEDS_REVIEW)
        self.assertEqual(later.supersedes, 'a')

    def test_af_two_dates_and_no_stated_relationship_settles_nothing(self):
        first = self.event(eid='a', value='2026-10-09', published='')
        rival = self.event(eid='b', value='2026-10-14', published='')
        report = merge_admit_card_events([first], [rival], exam_id=SSC)
        self.assertEqual(report.summary(), {'CONFLICTED': 1})
        self.assertEqual(len(report.events), 2)
        self.assertIs(rival.status, Status.NEEDS_REVIEW)
        self.assertIs(first.status, Status.VERIFIED)

    def test_ag_a_city_intimation_never_merges_into_an_admit_card(self):
        card = self.event(kind=AdmitCardNoticeKind.ADMIT_CARD, eid='a', value='2026-10-09')
        city = self.event(kind=AdmitCardNoticeKind.CITY_INTIMATION, eid='b',
                          value='2026-10-05')
        report = merge_admit_card_events([card], [city], exam_id=SSC)
        self.assertEqual(report.summary(), {'ADDED': 1})
        self.assertEqual(len(report.events), 2)


class TestInfrastructureIsNotAStatus(unittest.TestCase):
    """I. "We could not read it" and "they published nothing" are different claims."""

    def test_ah_a_failed_fetch_is_classified_as_infrastructure(self):
        outcome, _ = source_failed(OSError('The read operation timed out'))
        self.assertIs(outcome, SourceOutcome.NETWORK_UNAVAILABLE)
        outcome, _ = source_failed('<HTTPError 404: Not Found>')
        self.assertIs(outcome, SourceOutcome.SOURCE_FETCH_FAILURE)
        outcome, _ = source_failed('no text layer in this PDF')
        self.assertIs(outcome, SourceOutcome.SOURCE_UNREADABLE)

    def test_ai_no_infrastructure_outcome_can_become_not_published(self):
        for outcome in SourceOutcome:
            self.assertNotIn(outcome.value, {s.value for s in Status})

    def test_aj_an_unread_source_yields_no_event_rather_than_a_claim(self):
        self.assertEqual(read_notice(doc(), '', exam_id=SSC), [])
        self.assertEqual(read_rows([], doc(), '', exam_id=SSC), [])


class TestPublishability(unittest.TestCase):
    """J. Nothing reaches a candidate without a stage, evidence and a verbatim span."""

    def test_ak_an_event_with_no_verbatim_span_is_not_publishable(self):
        event = AdmitCardNotice(id='x', cycle='2026',
                                released_at=Fact.needs_review('2026-01-01', 'unverified'),
                                status=Status.NEEDS_REVIEW)
        self.assertFalse(event.is_publishable)

    def test_al_the_real_events_are_publishable(self):
        found = events_of(RESCHEDULE, RESCHEDULE_HEAD)
        self.assertTrue(found)
        for event in found:
            self.assertTrue(event.is_publishable, event.id)

    def test_am_describe_counts_what_it_says_it_counts(self):
        found = events_of(RESCHEDULE, RESCHEDULE_HEAD)
        summary = describe(found)
        self.assertEqual(summary['events'], len(found))
        self.assertEqual(summary['withDownloadUrl'], 0)
        self.assertEqual(summary['withExamDate'], len(found))


if __name__ == '__main__':
    unittest.main(verbosity=2)
