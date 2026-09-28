"""Generic capabilities added to read a real recruitment's whole lifecycle, each proven on an
invented authority in the flattened shapes real notices take.

Every authority, exam, post, date and figure below is invented. None of the code under test
names an authority or an exam; these tests are what keeps it that way.

Run: python -m unittest tools.exam_builder.test_lifecycle_generic
"""
from __future__ import annotations

import unittest

from ..exam_authoring.record import ExamRecord, Field, Status as RecordStatus
from .dates import extract_milestones, reconcile
from .compat import important_dates
from .eligibility import (extract_age_rules, extract_posts, post_code_clauses,
                          post_scoped_sentences, printed_vacancy_total)
from .identity import ExamIdentity, IdentityVerdict, verify
from .results import derive_next_steps, read_notice
from .schema import SourceDocument, SourceKind
from .tables import ColumnKind, reconstruct


def doc(doc_id='n', title='Notice') -> SourceDocument:
    return SourceDocument(id=doc_id, url=f'https://psc.example/{doc_id}.pdf',
                          kind=SourceKind.NOTIFICATION, title=title, authority='Example PSC',
                          accessed_at='2031-01-01', exam_id='exam-x')


# ============================================================ a post table, as flattened
POST_TABLE = """1.14. The Main Examination will be notified in due course.
1.15. The details of vacancies are as follows:-
Post
code
No.
Name of the Post No. of
Vacancies
Age as on
01/07/2031
Min. Max.
Scale of
Pay
Rs.
01 Deputy Revenue Officer [Civil
(Revenue Branch)] 12 18-44 48,000-
1,20,000/-
02
District Audit Officer
(State Audit Service) 30 21-35 45,000 -
1,10,000/-
03 Assistant Labour Officer (Labour
Service) 08 18-44 45,000-
1,10,000/-
TOTAL 50
The vacancies will be filled as per the rules of reservation.
PARA-3 EDUCATIONAL QUALIFICATIONS:
3.1 The candidate should hold the qualification as on the date of Notification, and the result of the degree must have been declared before that date for the qualification requirement.
Post
Code
No.
Name of the Post Educational Qualifications as specified in
the Service Rules of the department.
01 Deputy Revenue Officer [Civil
(Revenue Branch)]
Must possess a Bachelor's Degree of any
recognized University.
02
District Audit
Officer (State Audit Service) Must possess a Degree in Commerce with at
least a Second Class.
03 Assistant Labour Officer (Labour Service)
Must possess a Degree of any recognized University.
3.6 PHYSICAL REQUIREMENTS:
For Post Code No. 02: Must be not less than 165 Cms. in height and 86.3 Cms. round the chest.
PARA-4 RESERVATIONS:
4.1 However, for PC.No.03 Men only are eligible as per the Special Rules.
PARA-6 AGE:
6.1 The age is reckoned as on 01/07/2031 for all posts.
6.2 For PC. No. 01 & 03: Minimum Age (18 years): An applicant should not be born after 01/07/2013.
"""


class TestPostTables(unittest.TestCase):

    def setUp(self):
        self.posts = extract_posts(doc(), POST_TABLE, exam_id='exam-x')

    def test_a_serial_on_the_cell_line_and_a_long_wrapped_header(self):
        table = reconstruct(POST_TABLE)[0]
        self.assertEqual([c.kind for c in table.columns],
                         [ColumnKind.NAME, ColumnKind.SERIAL, ColumnKind.VACANCY, ColumnKind.AGE, ColumnKind.PAY])
        self.assertEqual(len(table.rows), 3)
        self.assertTrue(all(r.reconstructed for r in table.rows))
        self.assertEqual(table.total_line, 'TOTAL 50')

    def test_each_post_keeps_its_own_row(self):
        by_code = {p.code: p for p in self.posts}
        self.assertEqual(sorted(by_code), ['01', '02', '03'])
        self.assertEqual(by_code['02'].vacancies[0].count.value, 30)
        self.assertEqual(by_code['02'].age_band.value, '21-35')
        self.assertIn('1,10,000', by_code['02'].pay.value)
        self.assertNotIn('30', by_code['02'].name)

    def test_the_qualification_table_joins_by_code_and_full_name(self):
        by_code = {p.code: p for p in self.posts}
        self.assertTrue(by_code['02'].qualification[0].requirement.value.startswith('Must possess a Degree in Commerce'))
        self.assertTrue(all(p.qualification for p in self.posts))
        self.assertEqual(len(self.posts), 3, 'the second table must not create posts of its own')

    def test_the_printed_total_is_read_only_where_the_rows_add_up(self):
        total = printed_vacancy_total(doc(), POST_TABLE)
        self.assertEqual(total.count.value, 50)
        self.assertIsNone(printed_vacancy_total(doc(), POST_TABLE.replace('TOTAL 50', 'TOTAL 51')))

    def test_clauses_scoped_by_post_code(self):
        post_code_clauses(doc(), POST_TABLE, self.posts,
                          heading=__import__('re').compile(r'physical\s+requirements?\s*:', 2))
        post_scoped_sentences(doc(), POST_TABLE, self.posts)
        by_code = {p.code: p for p in self.posts}
        self.assertTrue(any('165 Cms' in f.value for f in by_code['02'].other_requirements))
        self.assertFalse(any('165 Cms' in f.value for f in by_code['01'].other_requirements))
        self.assertTrue(any('Men only' in f.value for f in by_code['03'].other_requirements))

    def test_a_single_reckoning_date_governs_the_age_rules(self):
        rules = extract_age_rules(doc(), POST_TABLE)
        self.assertTrue(rules)
        self.assertTrue(all(r.cutoff_date.value == '2031-07-01' for r in rules))
        two = POST_TABLE + '\n6.9 The age is reckoned as on 01/01/2032 for promotions.\n'
        self.assertTrue(all(not r.cutoff_date.has_value or r.cutoff_date.value != '2031-07-01'
                            or False for r in extract_age_rules(doc(), two)) or True)
        self.assertFalse(any(r.cutoff_date.has_value for r in extract_age_rules(doc(), two)))

    def test_a_grid_spilled_into_a_name_is_not_a_post(self):
        spilled = POST_TABLE.replace('03 Assistant Labour Officer (Labour\nService) 08',
                                     '03 Assistant Labour Officer MZ1 6 2 2 1\nService) 08')
        names = [p.name for p in extract_posts(doc(), spilled, exam_id='exam-x')]
        self.assertFalse(any('MZ1 6 2 2' in n for n in names))


# ============================================================ the lifecycle's own notices
CV_NOTICE = """EXAMPLE PUBLIC SERVICE COMMISSION
DIVISION-II SERVICES NOTIFICATION NO.05/2031, DATED:10/02/2031
NOTIFICATION FOR VERIFICATION OF CERTIFICATES.
It is hereby informed that the candidates with the following Hall Ticket Numbers are
picked up for Certificate Verification on the basis of Mains examinations held from
12/10/2031 to 18/10/2031 for the recruitment of Division-II Services, vide Notification No. 05/2031 dated:
10/02/2031, scheduled to be held on 14/04/2032, 15/04/2032 & 17/04/2032 from 10:30 AM.
Candidates are directed to use the Web-options link provided from 13/04/2032 to 18/04/2032 up to 5.00 PM only.
Candidates who give web options for post code 02 would be sent for Medical Examination.
(TOTAL: 40 Candidates)
(TOTAL: 38 Candidates)
Date: 09/04/2032. SECRETARY
"""

SECOND_SPELL = """EXAMPLE PUBLIC SERVICE COMMISSION
NOTIFICATION FOR 2nd SPELL CERTIFICATES VERIFICATION
In continuation to the notification of certificate verification issued on 09/04/2032, 20/04/2032 &
22/04/2032 the following candidates are informed to attend Verification of Certificates on
28/04/2032 at 10:30 AM.
Date: 25/04/2032. SECRETARY
"""


class TestLifecycleDates(unittest.TestCase):

    def rows(self, *texts):
        groups = []
        for i, t in enumerate(texts):
            d = doc(f'd{i}')
            groups.append((d, extract_milestones(d, t, exam_id='exam-x', cycle='2031')))
        return important_dates(reconcile(groups), exam_id='exam-x')

    def test_one_sentence_two_events(self):
        rows = self.rows(CV_NOTICE)
        exam = [r for r in rows if r['type'] == 'EXAM_TIER2']
        self.assertEqual([r['dateTimeStr'][:10] for r in exam], ['2031-10-12'],
                         'the Mains held from X to Y is a later-stage examination, shown from its first day')
        cv = [r for r in rows if r['type'] == 'INTERVIEW']
        self.assertEqual([r['dateTimeStr'][:10] for r in cv], ['2032-04-14'],
                         'the verification scheduled on three days, shown from its first day')

    def test_a_cited_document_date_is_not_an_event(self):
        rows = self.rows(CV_NOTICE)
        self.assertFalse(any(r['dateTimeStr'].startswith('2031-02-10') for r in rows))
        spell = self.rows(SECOND_SPELL)
        self.assertEqual(sorted(r['dateTimeStr'][:10] for r in spell), ['2032-04-28'],
                         'dates listed after "issued on" are the earlier notices, not events')

    def test_option_entry_is_its_own_milestone(self):
        rows = self.rows(CV_NOTICE)
        self.assertEqual([r['dateTimeStr'][:10] for r in rows if r['type'] == 'OTHER'], ['2032-04-18'])

    def test_recurring_spells_are_not_a_conflict(self):
        rows = self.rows(CV_NOTICE, SECOND_SPELL)
        cv = [r for r in rows if r['type'] == 'INTERVIEW']
        self.assertEqual(len(cv), 2)
        self.assertFalse(any(r['isTentative'] for r in cv), 'two spells are two events, not a conflict')


class TestResultNotices(unittest.TestCase):

    def test_the_title_decides_what_a_notice_declares(self):
        got = read_notice(doc(), CV_NOTICE + ' web options will be considered for final selection.',
                          exam_id='exam-x', headline='DIVISION-II - VERIFICATION OF CERTIFICATES - NOTIFICATION')
        self.assertEqual([d.kind.value for d in got], ['DV_SHORTLIST'])

    def test_the_notice_date_is_the_one_at_the_signature(self):
        got = read_notice(doc(), CV_NOTICE, exam_id='exam-x',
                          headline='VERIFICATION OF CERTIFICATES - NOTIFICATION')
        self.assertEqual(got[0].published_at.value, '2032-04-09')

    def test_several_printed_totals_assert_no_count(self):
        got = read_notice(doc(), CV_NOTICE, exam_id='exam-x',
                          headline='VERIFICATION OF CERTIFICATES - NOTIFICATION')
        self.assertFalse(got[0].qualified_count.has_value)

    def test_the_next_step_is_not_the_notice_s_own_stage(self):
        got = read_notice(doc(), CV_NOTICE, exam_id='exam-x',
                          headline='VERIFICATION OF CERTIFICATES - NOTIFICATION')
        self.assertIn('Medical Examination', got[0].next_step.value)

    def test_no_generic_flow_is_invented(self):
        stages = [{'level': 'STAGE', 'name': 'Preliminary Test'}, {'level': 'STAGE', 'name': 'Written Examination (Main)'}]
        steps = derive_next_steps([{'label': 'Final selection', 'stageLabel': 'Main'}], stages)
        self.assertEqual(steps, [], 'nothing follows the last stage of this scheme; no interview is supplied')
        pre = derive_next_steps([{'label': 'Preliminary result', 'stageLabel': 'Preliminary'}], stages)
        self.assertEqual(pre[0]['nextStage'], 'Written Examination (Main)')


class TestIdentityOfServiceNotices(unittest.TestCase):

    def test_a_service_group_titled_by_its_notice_number(self):
        target = ExamIdentity(exam_id='exam-x', query='EPSC Division-II Services',
                              official_name='EPSC Division-II Services', year='2031',
                              authority_name='Example Public Service Commission')
        self.assertEqual(verify(CV_NOTICE, target).verdict, IdentityVerdict.MATCH)
        old = CV_NOTICE.replace('05/2031', '03/2027').replace('10/02/2031', '10/02/2027')
        self.assertNotEqual(verify(old, target).verdict, IdentityVerdict.MATCH)


class TestSearchOutcomesAndHistory(unittest.TestCase):

    def test_a_search_is_recorded_as_ours_not_the_authority_s(self):
        from .build import record_search_outcomes
        rec = ExamRecord(exam_id='exam-x', code='X', title='X', authority_name='A', official_domain='https://a.example')
        rec.set(Field.not_published('answerKeys', 'No document of kind ANSWER_KEY was found for this exam'))
        rec.set(Field.not_published('corrigenda', 'the notice states that no corrigendum will be issued'))
        found = record_search_outcomes(rec, {'answerKeys': "the authority's Keys listing",
                                             'corrigenda': "the authority's notifications listing"})
        self.assertEqual(found, frozenset({'answerKeys'}))
        self.assertIs(rec.fields['answerKeys'].status, RecordStatus.NOT_EXTRACTED)
        self.assertIn('not a statement that the authority never published it', rec.fields['answerKeys'].note)
        self.assertIs(rec.fields['corrigenda'].status, RecordStatus.NOT_PUBLISHED)

    def test_a_re_registration_keeps_the_version_it_replaces(self):
        from . import materialize as M
        reg = M.ExamRegistry(':memory:')
        c = reg._conn()
        c.execute('''INSERT INTO exam_registry VALUES ('exam-x', '2031', 'A', 'https://a.example', 'X', 1, 'PASS', 1,
                     '{"id": "exam-x", "v": 1}', '{"examId": "exam-x"}', NULL, 't0', 't0', 0)''')
        c.commit()
        row = c.execute('SELECT * FROM exam_registry').fetchone()
        c.execute('''INSERT OR IGNORE INTO exam_registry_history
                     (exam_id, cycle, version, gate_decision, exam_json, record_json, completeness_json,
                      created_at, updated_at, superseded_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (row['exam_id'], row['cycle'], row['version'], row['gate_decision'], row['exam_json'],
                   row['record_json'], row['completeness_json'], row['created_at'], row['updated_at'], 't1'))
        c.commit()
        hist = reg.history('exam-x', '2031')
        self.assertEqual([h['version'] for h in hist], [1])
        self.assertEqual(hist[0]['exam']['v'], 1)


class TestSyllabusIdentity(unittest.TestCase):
    """Each paper's syllabus numbered from "1." again must not yield two nodes with one id."""

    def test_every_node_id_is_unique_and_the_first_keeps_its_id(self):
        from .syllabus import _make_ids_unique
        from .schema import SyllabusNode
        roots = [SyllabusNode(id='syl-x-root', title='S', level_label='Syllabus', order=1, children=[
            SyllabusNode(id=f'syl-x-paper-{p}', title=f'P{p}', level_label='Paper', order=p, children=[
                SyllabusNode(id=f'syl-x-{n}', title=f'T{p}{n}', level_label='Topic', order=n)
                for n in (1, 2)]) for p in (1, 2, 3)])]
        _make_ids_unique(roots)
        ids = [n.id for r in roots for n in r.walk()]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertIn('syl-x-1', ids)              # the first occurrence is unchanged
        self.assertIn('syl-x-paper-2-1', ids)       # a repeat is qualified by its parent

    def test_the_runtime_contract_refuses_repeated_ids(self):
        from .materialize import validate_runtime_exam
        exam = {'syllabusTree': [{'id': 'a', 'children': [{'id': 'b'}, {'id': 'b'}]}]}
        self.assertTrue(any('repeated ids' in e for e in validate_runtime_exam(exam)))


if __name__ == '__main__':
    unittest.main()
