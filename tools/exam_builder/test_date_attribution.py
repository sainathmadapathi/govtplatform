"""A date publishes only with an event role its own evidence establishes.

A table-row reader takes a row's first cell as a label and the first date anywhere in the rest
as that row's date. On a notice whose rules are printed as a numbered table, that turned clause
numbers into labels and the dates *inside* rule text into milestones: a 1962 cut-off in a
nationality clause, a 2018 office-memorandum date, a 2012 pension-scheme date, the age
reference date. Nothing about those is an event of the recruitment. The fixtures below are
written for an invented authority; the failures are shapes, not one authority's.

Run: python -m unittest tools.exam_builder.test_date_attribution
"""
from __future__ import annotations

import json
import unittest

from ..exam_authoring.record import Status
from .attribution import check_dates
from .test_attribution import FakeProvider, published, read

CYCLE = '2031'


def row(label: str, value: str, kind: str = 'OTHER', iso: str = '') -> dict:
    """One item as the table-row reader emits it."""
    from ..exam_authoring.extract import parse_date
    iso = iso or parse_date(value) or ''
    return {'type': kind, 'label': label, 'dateTimeStr': f'{iso} 00:00:00', 'rawLabel': label,
            'rawValue': value}


def milestone(kind: str, label: str, iso: str, excerpt: str, status: str = 'AVAILABLE',
              tentative: bool = False) -> dict:
    """One item as the milestone reader emits it (via the runtime projection)."""
    return {'type': kind, 'label': label, 'dateTimeStr': f'{iso} 00:00:00', 'status': status,
            'isTentative': tentative, 'provenance': {'excerptText': excerpt}}


def verdict(items, text=''):
    text = text or ' '.join(f"{i.get('rawLabel', i.get('label'))} {i.get('rawValue', '')} "
                            f"{(i.get('provenance') or {}).get('excerptText', '')}" for i in items)
    return check_dates(items, text, CYCLE)


def kept(items, text=''):
    return [i['dateTimeStr'][:10] for i in verdict(items, text).kept]


def table(*rows_: tuple[str, str]) -> str:
    return '<table>' + ''.join(f'<tr><td>{a}</td><td>{b}</td></tr>' for a, b in rows_) + '</table>'


def text_of(*rows_: tuple[str, str]) -> str:
    return ' '.join(f'{a} {b}' for a, b in rows_)


# ================================================================= each rule, alone
class TestEachRule(unittest.TestCase):

    def test_a_numbered_rule_citation_is_not_a_date(self):
        # Clause 8's text cites an office memorandum by its date.
        it = row('8', 'For Persons with Benchmark Disabilities: As per OM No. 36035/02/2017 dated '
                      'January 15, 2031 issued by the Department, the categories of disability are')
        self.assertEqual(kept([it]), [])

    def test_a_serial_number_label_names_no_event(self):
        it = row('22', 'April 01, 2031')
        self.assertEqual(kept([it]), [])
        self.assertTrue(verdict([it]).unresolved)

    def test_a_historical_date_is_not_this_cycles(self):
        it = row('Nationality', 'a person who came over to India before 1st January, 1962')
        self.assertEqual(kept([it]), [])

    def test_a_reference_date_is_not_an_event(self):
        it = row('Age Limit', 'as on August 01, 2031', kind='OTHER')
        self.assertEqual(kept([it]), [])

    def test_a_date_inside_a_clause_of_text_is_not_the_rows_value(self):
        it = row('Mode of Application', 'Candidates are required to apply online only through the '
                 "website. No other mode of submission is available. Brief instructions are given in "
                 'the appendix, and the closing date of receipt of applications is May 20, 2031.')
        self.assertEqual(kept([it]), [])

    def test_a_footnote_is_not_a_milestone(self):
        it = row('Note', 'The examination of the previous panel was held on March 12, 2031.')
        self.assertEqual(kept([it]), [])

    def test_a_malformed_date_is_not_a_date(self):
        it = row('Last date for online application', '31.02.2031', kind='APPLICATION_CLOSE')
        self.assertEqual(kept([it]), [])

    def test_a_date_stated_for_another_event_in_the_same_row(self):
        it = row('Phase-I Examination', 'Admit card will be available from June 01, 2031; the '
                 'examination follows', kind='EXAM_TIER1')
        self.assertEqual(kept([it]), [])

    def test_conflicting_dates_for_one_single_event(self):
        a = row('Last date for online application', 'May 20, 2031', kind='APPLICATION_CLOSE')
        b = row('Closing date of application', 'May 27, 2031', kind='APPLICATION_CLOSE')
        v = verdict([a, b])
        self.assertTrue(v.conflicts)
        self.assertEqual([i['dateTimeStr'][:10] for i in v.kept], [])

    def test_a_publication_date_after_a_citation_is_an_event(self):
        # "... vide Notification No. 14/2030 - (Published on 28/08/2031)": the citation names
        # which recruitment; the date is when its result was published.
        it = milestone('RESULT', 'Results', '2031-08-28',
                       'Results for the post of Deputy Officer vide Notification No. 14/2030 - '
                       '(Published on 28/08/2031) - Click Here')
        self.assertEqual(kept([it]), ['2031-08-28'])

    def test_a_notices_own_dateline_is_its_date(self):
        # "DATED:" cites nothing here: it dates the notification itself.
        it = milestone('NOTIFICATION', 'Notification published', '2031-02-19',
                       'NOTIFICATION NO. 02/2031, DATED: 19/02/2031')
        self.assertEqual(kept([it]), ['2031-02-19'])

    # ---- the same rules, on dates that DO name an event, so no other rule can hide them
    def dropped(self, item):
        return [i for i, _ in verdict([item]).dropped]

    def test_alone_another_cycle(self):
        self.assertTrue(self.dropped(row('Last date for online application', '20.05.2018',
                                         kind='APPLICATION_CLOSE')))

    def test_alone_a_cited_date(self):
        self.assertTrue(self.dropped(row('Last date for online application',
                                         'as per the circular dated 20.05.2031', kind='APPLICATION_CLOSE')))

    def test_alone_a_footnote(self):
        self.assertTrue(self.dropped(row('Note', '20.05.2031', kind='APPLICATION_CLOSE')))

    def test_alone_a_date_inside_a_clause(self):
        self.assertTrue(self.dropped(row(
            'Last date for online application', 'Candidates are required to apply online only '
            'through the website and no other mode of submission is available; brief instructions '
            'for filling the form are given in the appendix, and applications close on 20.05.2031.',
            kind='APPLICATION_CLOSE')))

    def test_a_superseded_date_is_not_a_conflict(self):
        a = milestone('APPLICATION_CLOSE', 'Last date', '2031-05-27', 'Last date extended to May 27, 2031')
        b = milestone('APPLICATION_CLOSE', 'Last date', '2031-05-20', 'Last date May 20, 2031',
                      status='SUPERSEDED')
        self.assertFalse(verdict([a, b]).conflicts)


# ========================================================== genuine dates keep publishing
class TestGenuineDates(unittest.TestCase):

    def test_a_genuine_event_date(self):
        self.assertEqual(kept([row('Last date for online application', 'May 20, 2031',
                                   kind='APPLICATION_CLOSE')]), ['2031-05-20'])

    def test_a_date_range(self):
        self.assertEqual(kept([row('Online application', '21.04.2031 to 20.05.2031',
                                   kind='APPLICATION_OPEN')]), ['2031-04-21'])

    def test_a_correction_window(self):
        self.assertEqual(kept([row('Application Edit Option', '27.05.2031 to 29.05.2031',
                                   kind='CORRECTION_WINDOW')]), ['2031-05-27'])

    def test_a_fee_deadline(self):
        self.assertEqual(kept([row('Last date for payment of fee', '22.05.2031')]), ['2031-05-22'])

    def test_a_row_naming_a_stage(self):
        self.assertEqual(kept([row('Phase-II: Paper-I, II & III Online Examination', 'July 25, 2031')]),
                         ['2031-07-25'])

    def test_the_same_date_for_two_stated_events(self):
        a = row('Last date for online application', 'May 20, 2031', kind='APPLICATION_CLOSE')
        b = row('Last date for payment of fee', 'May 20, 2031')
        self.assertEqual(kept([a, b]), ['2031-05-20', '2031-05-20'])

    def test_milestones_the_reader_already_bound_to_a_cue(self):
        items = [milestone('OTHER', 'Certificate verification', '2031-04-16',
                           'Certificate verification of the candidates on 16.04.2031'),
                 milestone('OTHER', 'Web options (post preference) close', '2031-04-22',
                           'web options will be available up to 22.04.2031'),
                 milestone('EXAM_TIER2', 'Main Examination', '2031-10-01',
                           'Schedule of Main Examination September/October 2031', tentative=True),
                 milestone('EXAM_TIER2', 'Main Examination', '2031-10-21',
                           'Main Examination held from 21.10.2031 to 27.10.2031')]
        self.assertEqual(len(kept(items)), 4)

    def test_a_month_only_schedule_is_not_refused(self):
        items = [milestone('INTERVIEW', 'Personality Test', '2031-09-01',
                           '(iii) Personality Test/ Viva-Voce - August / September, 2031')]
        self.assertEqual(kept(items), ['2031-09-01'])


# ================================================================== through the builder
RULE_TABLE = table(
    ('Opening Date for Online Registration of Applications', 'April 29, 2031'),
    ('Closing Date for Online Registration of Applications', 'May 20, 2031 (6:00 PM)'),
    ('3', 'Nationality: a subject of Bhutan, or a Tibetan refugee who came over to India before '
          '1st January, 1962 with the intention of permanently settling in India'),
    ('4', 'Age Limit (As on April 01, 2031): a candidate must have attained the age of 21 years'),
    ('8', 'As per OM No.36035/02/2017-Estt (Res) dated January 15, 2018 issued by the Department'),
    ('22', 'Selected candidates will be governed by the scheme for all employees joining on or after '
           'January 01, 2012, in addition to gratuity'))


class TestThroughTheBuilder(unittest.TestCase):

    def test_rule_clauses_publish_no_dates(self):
        got = read('dates', text_of(('x', 'y')), html=RULE_TABLE)
        dates = [d['dateTimeStr'][:10] for d in (got.value or [])] if got else []
        for bad in ('1962-01-01', '2031-04-01', '2018-01-15', '2012-01-01'):
            self.assertNotIn(bad, dates if published(got) else [], (got.status, dates))
        self.assertIn('2031-05-20', dates)

    def test_multiple_dates_in_one_sentence(self):
        # Every date the reader took from a multi-date sentence keeps its role and publishes.
        got = read('dates', 'Online applications will be received from 21.04.2031 to 20.05.2031 '
                            'and the examination will be held on 13.06.2031.')
        dates = sorted(d['dateTimeStr'][:10] for d in (got.value or []))
        self.assertTrue(published(got), (got.status, got.note))
        self.assertEqual(dates[:2], ['2031-04-21', '2031-05-20'])


# ====================================================================== the model's part
class TestModelOnlyWithholdsDates(unittest.TestCase):
    """The model may classify a date's role; only deterministic checks let that stand."""

    SPAN = 'Closing Date for Online Registration of Applications May 20, 2031'
    ROWS = (('Closing Date for Online Registration of Applications', 'May 20, 2031'),)
    TABLE = table(*ROWS)

    def reply(self, **over):
        out = {'role': 'APPLICATION_CLOSE', 'supports_date': True, 'evidence_span': self.SPAN,
               'is_reference': False, 'confidence': 'high', 'conflicts': []}
        out.update(over)
        return out

    def run_with(self, reply):
        return read('dates', text_of(*self.ROWS), html=self.TABLE, provider=FakeProvider(reply))

    def test_a_supported_date_stays(self):
        got = self.run_with(self.reply())
        self.assertTrue(published(got), got.note)

    def test_an_unsupported_date_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(supports_date=False))))

    def test_a_wrong_scope_role_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(role='RESULT'))))

    def test_text_the_model_calls_no_date_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(role='NOT_A_DATE'))))
        # ... even where no established role would otherwise refuse it.
        from .verification.attribution_llm import validate_date
        item = row('Closing Date for Online Registration of Applications', 'May 20, 2031',
                   kind='APPLICATION_CLOSE')
        text = text_of(*self.ROWS)
        self.assertFalse(validate_date(item, self.reply(role='NOT_A_DATE'), text, lambda r: True)[0])

    def test_a_conflict_the_model_reports_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(conflicts=['a later notice extends it']))))

    def test_a_reference_date_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(is_reference=True))))

    def test_evidence_not_printed_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(
            evidence_span='The last date for applications is 20 May 2031.'))))

    def test_evidence_without_the_date_is_withheld(self):
        self.assertFalse(published(self.run_with(self.reply(
            evidence_span='Closing Date for Online Registration of Applications'))))

    def test_an_unreachable_model_withholds(self):
        got = read('dates', text_of(*self.ROWS), html=self.TABLE, provider=FakeProvider({}, fail='down'))
        self.assertFalse(published(got))
        self.assertIn('could not check', got.note)

    def test_the_model_cannot_rescue_a_dropped_date(self):
        # A historical date is dropped deterministically; the model is never asked about it.
        p = FakeProvider(self.reply(role='EXAM', evidence_span='before 1st January, 1962'))
        got = read('dates', text_of(('x', 'y')), html=RULE_TABLE, provider=p)
        dates = [d['dateTimeStr'][:10] for d in (got.value or [])]
        self.assertNotIn('1962-01-01', dates)

    def test_a_dateline_read_as_cited_still_dates_the_notification(self):
        from .attribution import model_role_fits
        from .verification.attribution_llm import validate_date
        item = milestone('NOTIFICATION', 'Notification published', '2031-02-19',
                         'NOTIFICATION NO. 02/2031, DATED: 19/02/2031')
        text = 'NOTIFICATION NO. 02/2031, DATED: 19/02/2031 GROUP-I SERVICES'
        reply = {'role': 'REFERENCE', 'supports_date': True, 'is_reference': True,
                 'confidence': 'high', 'conflicts': [],
                 'evidence_span': 'NOTIFICATION NO. 02/2031, DATED: 19/02/2031'}
        self.assertTrue(validate_date(item, reply, text, lambda r: model_role_fits(item, r))[0])
        # ... but a cited date on any other event is still withheld.
        other = milestone('RESULT', 'Result', '2031-02-19', 'result dated 19/02/2031')
        self.assertFalse(validate_date(other, dict(reply, evidence_span='result dated 19/02/2031'),
                                       'result dated 19/02/2031', lambda r: model_role_fits(other, r))[0])

    def test_the_model_shares_the_readers_event_vocabulary(self):
        from .attribution import model_role_fits
        board = milestone('OTHER', 'Medical board (uniform services posts)', '2031-04-21',
                          'Medical Board on 21/04/2031')
        options = milestone('OTHER', 'Web options close', '2031-04-22',
                            'web options will be available up to 22/04/2031')
        edit = milestone('CORRECTION_WINDOW', 'Application Edit Option', '2031-03-27',
                         'Application Edit Option From 23/03/2031 To 27/03/2031')
        self.assertTrue(model_role_fits(board, 'PHYSICAL_TEST'))
        self.assertTrue(model_role_fits(options, 'OPTION_ENTRY'))
        self.assertTrue(model_role_fits(edit, 'CORRECTION_WINDOW'))
        self.assertFalse(model_role_fits(board, 'RESULT'))

    def test_the_model_can_establish_a_role_only_with_a_cue_in_its_evidence(self):
        from .attribution import resolve_with_model_reply
        item = row('Officers in Grade II - Economics Stream', 'June 13, 2031')
        text = ('Tentative schedule of Phase-I Online Examination: Officers in Grade II - Economics '
                'Stream June 13, 2031')
        ok = {'role': 'EXAM', 'supports_date': True, 'is_reference': False, 'confidence': 'high',
              'conflicts': [], 'evidence_span': 'Phase-I Online Examination: Officers in Grade II - '
                                                 'Economics Stream June 13, 2031'}
        self.assertTrue(resolve_with_model_reply(item, ok, text)[0])
        no_cue = dict(ok, evidence_span='Officers in Grade II - Economics Stream June 13, 2031')
        self.assertFalse(resolve_with_model_reply(item, no_cue, text)[0])


if __name__ == '__main__':
    unittest.main()
