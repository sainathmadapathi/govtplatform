"""Engine weaknesses found by running a second real exam through the same universal pipeline.

Each case below is a generic defect the second build exposed and the first never exercised,
tested on an invented authority ("Example Recruitment Board", ERB). None of the code under
test names an authority or an exam.

Run: python -m unittest tools.exam_builder.test_universal_validation
"""
from __future__ import annotations

import unittest

from .compat import important_dates
from .dates import extract_milestones, reconcile
from .identity import ExamIdentity, IdentityVerdict, verify
from .schema import SourceDocument, SourceKind

TARGET = ExamIdentity(exam_id='exam-erb-cgl-2031', query='ERB CGL 2031', official_name='ERB CGL 2031',
                      year='2031', authority_name='Example Recruitment Board',
                      authority_domain='https://erb.gov.in')


def doc(doc_id='n', kind=SourceKind.NOTIFICATION) -> SourceDocument:
    return SourceDocument(id=doc_id, url=f'https://erb.gov.in/{doc_id}.pdf', kind=kind,
                          title='Notice', authority='Example Recruitment Board', exam_id='exam-x')


class TestIdentity(unittest.TestCase):

    def test_the_authority_s_own_name_identifies_none_of_its_exams(self):
        # A sibling exam's notice mentions "ERB Examination"; the authority's acronym is in
        # every one of its notices, so it cannot say which exam a document is about.
        sibling = ('Subject - Combined Higher Secondary (10+2) Level Examination (CHSLE), 2030 - '
                   'Declaration of result. Candidates who appeared in the ERB Examination are informed.')
        self.assertNotEqual(verify(sibling, TARGET).verdict, IdentityVerdict.MATCH)
        self.assertEqual(TARGET.authority_aliases, {'erb'})

    def test_the_exam_s_own_name_still_identifies_it(self):
        own = 'NOTICE Combined Graduate Level Examination, 2031. Applications are invited.'
        self.assertEqual(verify(own, TARGET).verdict, IdentityVerdict.MATCH)

    def test_a_bracketed_plus_does_not_truncate_a_title(self):
        from .identity import exam_references
        refs = [r.text for r in exam_references('Combined Higher Secondary (10+2) Level Examination, 2030')]
        # The longest reading is the whole title; "+" used to end it at "(10".
        self.assertEqual(refs[0], 'Combined Higher Secondary (10+2) Level Examination, 2030')


class TestAgeBands(unittest.TestCase):

    def test_a_debarment_period_is_not_an_age_band(self):
        from .eligibility import extract_age_rules
        text = ('The age limit for the post is 18-27 years as on 01/08/2031.\n'
                '21 Candidate acting as scribe in same examination. 03-05 years\n'
                '28 Peeking in the computer of other candidate(s). 01-03 years\n')
        rules = extract_age_rules(doc(), text)
        bands = sorted((r.minimum_age.value, r.maximum_age.value) for r in rules
                       if r.minimum_age.has_value and r.maximum_age.has_value)
        self.assertEqual(bands, [(18.0, 27.0)])


class TestNumbersAreReadWhole(unittest.TestCase):

    def test_a_window_edge_never_cuts_a_number(self):
        from .semantic import passages
        # Slide the figure across every position, so some window edge lands inside it.
        for pad in range(0, 400, 3):
            text = ('word ' * (pad // 5)) + 'There are approx.12,256 vacancies. ' + ('word ' * 120)
            tokens = set(text.split())
            for _, chunk in passages(text):
                parts = chunk.split()
                self.assertIn(parts[0], tokens, f'window begins inside a token (pad {pad})')
                self.assertIn(parts[-1], tokens, f'window ends inside a token (pad {pad})')

    def test_the_count_is_the_number_bound_to_the_noun(self):
        from .semantic import _vacancies
        self.assertEqual(_vacancies('There are approx.12,256 vacancies.'),
                         {'count': '12256', 'isApproximate': True})
        self.assertEqual(_vacancies('approx. 1,20,000 posts')['count'], '120000')
        self.assertIsNone(_vacancies('filled as per the reservations under Rule-22 and 22(A). vacancies'))
        self.assertIsNone(_vacancies('3.1 Tentative vacancies: There'))
        # A total stated in words outranks a part of it named in the same sentence.
        self.assertEqual(_vacancies('The number of vacancies to be filled through the examination is expected '
                                    'to be approximately 933 which include 33 Vacancies reserved for PwBD.'),
                         {'count': '933', 'isApproximate': True})
        self.assertEqual(_vacancies('Total 450 posts, of which 45 posts are reserved.')['count'], '450')


class TestTableSections(unittest.TestCase):

    TABLE = """2.1 Pay Level-8 (Rs 47600 to 151100):
S.
No. Name of Post Ministry/Department Classification of
Post Age Limit
1
Audit Officer
Audit Department
Group 'B'
18-30 years
2.2 Pay Level-5 (Rs 29200 to 92300):
1 Auditor Audit Offices Group 'C' 18-27 years
2 Accountant Accounts Offices Group 'C' 18-27 years
"""

    def test_a_sibling_section_whose_rows_start_with_their_serial_continues(self):
        # 2.2 prints no header of its own, and its rows carry the serial on the cell line.
        # It used to be dropped whole: only a bare serial line counted as a continuation.
        from .tables import reconstruct
        tables = reconstruct(self.TABLE)
        self.assertEqual([len(t.rows) for t in tables], [1, 2])
        self.assertTrue(tables[1].heading.startswith('2.2'))

    def test_only_the_next_sibling_continues(self):
        from .tables import _is_next_sibling
        self.assertTrue(_is_next_sibling('2.4 Pay Level-5', '2.3 Pay Level-6'))
        self.assertFalse(_is_next_sibling('2.5 Pay Level-4', '2.3 Pay Level-6'))
        self.assertFalse(_is_next_sibling('3.1 Tentative vacancies', '2.3 Pay Level-6'))
        self.assertFalse(_is_next_sibling('2.4.1 Note', '2.3 Pay Level-6'))


class TestPostRows(unittest.TestCase):

    TABLE = """2.1 Pay Level-7 (Rs 44900 to 142400):
S.
No. Name of Post Ministry/Department Classification of
Post Age Limit
1
Assistant Officer
Other Ministries
Group 'B'
18-30 years
2
Inspector (Examiner)
3
Audit Officer
Audit Department
Group 'B'
18-30 years
2.2 Pay Level-6 (Rs 35400 to 112400):
1 Assistant Officer Other Ministries Group 'B' 18-30 years
"""

    def setUp(self):
        from .eligibility import extract_posts
        self.held = []
        self.posts = extract_posts(doc(), self.TABLE, exam_id='exam-x', held=self.held)

    def test_a_namesake_at_another_pay_level_is_another_post(self):
        pays = sorted(str(p.pay.value)[:13] for p in self.posts if p.name.startswith('Assistant Officer'))
        self.assertEqual(pays, ['Pay Level-6 (', 'Pay Level-7 ('])
        self.assertEqual(len({p.id for p in self.posts}), len(self.posts))

    def test_a_row_printing_only_its_name_is_reported_not_published(self):
        self.assertNotIn('Inspector (Examiner)', [p.name for p in self.posts])
        self.assertEqual([(o, n) for o, n, _ in self.held], [('2', 'Inspector (Examiner)')])


class TestLifecycle(unittest.TestCase):

    NOTICE = ('Dates for submission of online applications 21.05.2031 to 22.06.2031\n'
              'Last date and time for receipt of online applications 22.06.2031 (23:00 hours)\n'
              'An ex-serviceman must complete his engagement within the stipulated period of one year '
              'from the closing date for receipt of application i.e. 22-06-2032.\n')
    REOPEN = ('The online application window was kept open from 21.05.2031 to 22.06.2031.\n'
              '3. The Board has decided to re-open the window for submission of online applications for two '
              'days i.e. from 23.06.2031 (23:00\n'
              'hours) to 25.06.2031 (23:00 hours).\n')

    def rows(self, *groups):
        return important_dates(reconcile([(d, extract_milestones(d, t, exam_id='exam-x')) for d, t in groups]),
                               exam_id='exam-x')

    def test_the_end_of_a_period_is_not_the_event_it_is_counted_from(self):
        rows = self.rows((doc('notice'), self.NOTICE))
        self.assertFalse(any(r['dateTimeStr'].startswith('2032') for r in rows))

    def test_a_reopened_window_supersedes_the_printed_close(self):
        notice, reopen = doc('notice'), doc('reopen')
        # The same notice served under two names, as an authority sometimes does.
        twin = doc('notice-copy')
        rows = self.rows((notice, self.NOTICE), (twin, self.NOTICE), (reopen, self.REOPEN))
        closes = sorted((r['dateTimeStr'][:10], r['status']) for r in rows if r['type'] == 'APPLICATION_CLOSE')
        self.assertIn(('2031-06-25', 'AVAILABLE'), closes)
        self.assertTrue(all(s == 'SUPERSEDED' for d, s in closes if d == '2031-06-22'))
        ids = [r['id'] for r in rows]
        self.assertEqual(len(ids), len(set(ids)), 'a statement read from two copies is one row')

    def test_a_fee_deadline_is_not_the_application_close(self):
        rows = self.rows((doc('n'), 'Last date and time for making online fee payment: 23.06.2031 (23:00 hours)\n'))
        self.assertEqual({r['type'] for r in rows}, {'OTHER'})

    def test_a_deadline_for_registration_and_payment_together_is_the_close(self):
        rows = self.rows((doc('n'), 'Last date for Online Registration & Online Payment of Fee 08.09.2031\n'))
        self.assertEqual({r['type'] for r in rows}, {'APPLICATION_CLOSE'})


class TestAmendingNotices(unittest.TestCase):

    def test_a_notice_reopening_a_window_or_extending_a_date_amends_the_notice(self):
        from .discover import DocKind, classify_kind
        for title in ('Reopening of Online Applications Form Window for Example Examination, 2031',
                      'ERB_Reopen_23062031.pdf', 'Extension of last date for online application',
                      'Last date extended'):
            self.assertIs(classify_kind(title, ''), DocKind.CORRIGENDUM, title)
        self.assertIs(classify_kind('Notice of Examination', ''), DocKind.NOTIFICATION)

    def _revise(self, amending_text):
        from ..exam_authoring.record import Citation, ExamRecord, Field
        from .build import record_date_revisions
        from .discover import DiscoveredDoc, DocKind, Relevance, SourceSet

        class Loaded:
            def __init__(self, text): self.text = text
            def all_text(self): return self.text

        rows = [
            {'id': 'fee-new', 'type': 'OTHER', 'label': 'The last date for fee payment will be',
             'dateTimeStr': '2031-06-26 00:00:00', 'status': 'AVAILABLE',
             'provenance': {'documentTitle': 'Reopening', 'officialUrl': 'https://erb.gov.in/r.pdf',
                            'excerptText': 'will be 26.06.2031'}},
            {'id': 'fee-old', 'type': 'OTHER', 'label': 'Last date for making online fee payment',
             'dateTimeStr': '2031-06-23 00:00:00', 'status': 'SUPERSEDED', 'supersededBy': 'fee-new',
             'provenance': {'documentTitle': 'Notice', 'officialUrl': 'https://erb.gov.in/n.pdf',
                            'excerptText': '23.06.2031'}}]
        rec = ExamRecord(exam_id='exam-x', code='X', title='X', authority_name='Example Recruitment Board',
                         official_domain='https://erb.gov.in')
        rec.set(Field.found('dates', rows, Citation(document_title='t', url='u', page=1, clause='c',
                                                     excerpt='e', verified_date='2031-07-01')))
        sources = SourceSet(exam_id='exam-x', authority_domain='https://erb.gov.in', docs=[
            DiscoveredDoc(url='https://erb.gov.in/r.pdf', kind=DocKind.CORRIGENDUM, title='Reopening',
                          relevance=Relevance.DIRECT)])
        record_date_revisions(rec, sources, {'https://erb.gov.in/r.pdf': Loaded(amending_text)})
        return rec.fields['corrigenda'].value[0]

    def test_an_amending_notice_is_named_as_one_with_its_own_dateline(self):
        entry = self._revise('4. ... shall remain as in the Notice dated 21.05.2031.\nUnder Secretary\nDated: 23.06.2031\n')
        self.assertEqual(entry['publishedDate'], '2031-06-23')
        self.assertIn('later notice amending the schedule, dated 2031-06-23', entry['note'])
        # An untyped event is titled by the notice's own label for it.
        self.assertTrue(entry['title'].startswith('Last date for making online fee payment revised'))

    def test_a_body_reference_to_another_date_is_not_the_dateline(self):
        entry = self._revise('the Notice dated 21.05.2031 shall remain unchanged.\n')
        self.assertEqual(entry['publishedDate'], '')
        self.assertIn('prints no date of its own', entry['note'])


class TestReadersTakeFactsOnlyFromTheExamsOwnDocuments(unittest.TestCase):

    def test_an_ambiguous_document_supplies_no_exam_specific_fact(self):
        from .build import _facts_view
        from .identity import IdentityCheck
        loaded = {'own': object(), 'unnamed': object()}
        identity = {'own': IdentityCheck(IdentityVerdict.MATCH), 'unnamed': IdentityCheck(IdentityVerdict.AMBIGUOUS)}
        self.assertEqual(set(_facts_view('corrigenda', loaded, identity)), {'own'})
        self.assertEqual(set(_facts_view('dates', loaded, identity)), {'own'})
        # The authority's portal is the authority's, whichever exam asks.
        self.assertEqual(set(_facts_view('applicationPortal', loaded, identity)), {'own', 'unnamed'})

    def test_a_pattern_reading_with_no_paper_does_not_preempt_the_scheme_reader(self):
        from .build import _states_something
        self.assertFalse(_states_something('examPattern', {'papers': [], 'negativeMarking': '0.50 mark'}))
        self.assertTrue(_states_something('examPattern', {'papers': [{'name': 'Paper I'}]}))


class TestSchemeTableRows(unittest.TestCase):
    """A flattened scheme table whose first row reads "II Paper-I:", then "Session-I (2 hours".

    Found when restoring the extractor's hyphens made "Paper-I" and "Session-I" readable:
    the row was taken for a new stage and cut the stage's table in two, "(2 hours" opened a
    row called "hours", and a session was filed as a paper because the column said Paper.
    """

    TEXT = ('9.1 Scheme of Stage-II Examination:\n\nStage Paper Session Subject\n\nNumber \n\nof \n\n'
            'Questions\n\nMaximum \n\nMarks Time allowed\n\nII Paper-I: \n\nSession-I\n\n(2 hours \n\n'
            'and 15 \n\nminutes)\n\nSection-I:\n\nComputer \n\nKnowledge \n\nTest\n\n20 20*3\n\n= 60\n\n'
            '15 Minutes\n\nPaper-II Statistics\n\n100\n\n100*2\n\n= 200\n\n2 hours\n\n'
            '9.1.1 Paper-I is compulsory for all the posts.\n')

    def setUp(self):
        from .pattern import extract_pattern
        self.pattern = extract_pattern(doc(), self.TEXT, exam_id='exam-x')
        self.nodes = [(n.level.value, n.name) for s in self.pattern.stages for n in s.walk()]

    def test_a_row_opening_on_the_previous_column_s_ordinal_is_not_a_stage(self):
        stages = [name for level, name in self.nodes if level == 'STAGE']
        self.assertEqual(len(stages), 1, self.nodes)
        self.assertIn('Statistics', [name for _, name in self.nodes])

    def test_a_duration_never_opens_a_row(self):
        self.assertFalse(any('hours' in name.lower() for _, name in self.nodes), self.nodes)

    def test_a_row_naming_its_own_level_keeps_it(self):
        self.assertIn(('PART', 'Session-I'), self.nodes)


class TestPdfText(unittest.TestCase):

    def test_the_extractor_s_line_break_hyphen_is_printed_as_a_hyphen(self):
        from ..exam_authoring.sources import pdf_text
        self.assertEqual(pdf_text('De\ufffeindustrialization; Inter\u00adState disputes'),
                         'De-industrialization; Inter-State disputes')


class TestMaterialization(unittest.TestCase):

    def test_a_vacancy_figure_is_shown_as_a_number(self):
        from .materialize import _vacancy_count
        self.assertEqual(_vacancy_count({'count': '12256', 'isApproximate': True}), ('12256', True))
        self.assertEqual(_vacancy_count(563), ('563', False))
        self.assertEqual(_vacancy_count('1,234'), ('1234', False))

    def test_the_structural_level_decides_a_node_not_the_authority_s_word(self):
        from .materialize import _pattern_node
        node = _pattern_node({'level': 'STAGE', 'levelLabel': 'Tier', 'name': 'Scheme of Tier-I Examination',
                              'status': 'VERIFIED'}, {})
        self.assertEqual((node['level'], node['levelLabel']), ('STAGE', 'Tier'))


if __name__ == '__main__':
    unittest.main()
