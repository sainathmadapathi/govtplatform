"""The syllabus outline, the study roadmap's inputs and the practice form, on an invented authority.

Found by looking at one machine-read exam as a candidate would: its syllabus had come out as 124
siblings under "SCHEME AND SYLLABUS FOR RECRUITMENT TO THE POSTS OF" (the scheme table's rows
among them), so its tree map was one branch and its study order a wall of text, and it had no
practice application form at all. Every rule below is generic; nothing names an exam.

Run: python -m unittest tools.exam_builder.test_candidate_features
"""
from __future__ import annotations

import unittest

from .schema import SourceDocument, SourceKind

NOTICE = """PARA-14 ANNEXURES:
Annexure-I Breakup of Vacancies.
Annexure-II Scheme and Syllabus.
Annexure-III List of Communities.
PARA-15 MEMORANDUM OF MARKS:
15.1 The marks secured in the Preliminary Test will not be counted.
ANNEXURE-II
SCHEME AND SYLLABUS FOR RECRUITMENT TO THE POSTS OF
EXAMPLE SERVICES
SCHEME OF EXAMINATION
SUBJECT DURATION MAXIMUM MARKS
Preliminary Test
General Studies (Objective Type) 2 150
Paper-I General Essay
1. Social issues.
2. Economic growth.
3 150
TOTAL MARKS: 450
17
SYLLABUS
EXAMPLE SERVICES
GENERAL STUDIES AND MENTAL ABILITY
(PRELIMINARY TEST)
1. Current Affairs – Regional and National.
2. General Science.
3. Logical Reasoning.
Written Examination (Main)
General English (Qualifying Test)
(X CLASS STANDARD)
1. Spotting Errors
2. Comprehension
PAPER-I: GENERAL ESSAY
(Candidate should write two Essays, one from each
Section. Each Essay carries 50 marks.)
Section-I
1. Social issues.
2. Economic growth.
Section-II
1. Politics.
PAPER-II: HISTORY AND GEOGRAPHY
I. History of the Region, with special reference to the Modern Period (1757
to 1947 A.D.)
1. Early civilisations of the region and their art and architecture.
2. The colonial period.
II. Geography of the Region.
1. Physical setting.
10.Urbanisation of the region.
ANNEXURE-III
List of communities
"""


def doc():
    return SourceDocument(id='n', url='https://erb.gov.in/n.pdf', kind=SourceKind.NOTIFICATION, title='Notice',
                          authority='Example Recruitment Board', exam_id='exam-x')


class TestSyllabusOutline(unittest.TestCase):

    def setUp(self):
        from .syllabus import extract_syllabus
        self.syl = extract_syllabus(doc(), NOTICE, exam_id='exam-x')

    def tree(self, nodes=None, depth=0):
        out = []
        for n in (self.syl.roots if nodes is None else nodes):
            out.append(('  ' * depth) + f'{n.level_label}: {n.title}')
            out += self.tree(n.children, depth + 1)
        return out

    def test_a_table_of_contents_line_opens_no_syllabus(self):
        self.assertEqual([r.title for r in self.syl.roots], ['SYLLABUS'])

    def test_the_scheme_table_before_the_syllabus_is_not_read_as_topics(self):
        titles = '\n'.join(self.tree())
        self.assertNotIn('150', titles)
        self.assertNotIn('TOTAL MARKS', titles)

    def test_papers_sections_and_numbered_lists_keep_their_hierarchy(self):
        tree = self.tree()
        self.assertIn('  Subject: GENERAL STUDIES AND MENTAL ABILITY (PRELIMINARY TEST)', tree)
        self.assertIn('  Stage: Written Examination (Main)', tree)
        self.assertIn('    Paper: PAPER-I: GENERAL ESSAY', tree)
        self.assertIn('      Section: Section-I', tree)
        self.assertIn('        Topic: Social issues', tree)
        # A Roman-numbered heading keeps its wrapped title whole.
        self.assertIn('      Subject: History of the Region, with special reference to the Modern Period '
                      '(1757 to 1947 A.D.)', tree)

    def test_a_wrapped_bracketed_note_is_a_note_not_a_heading(self):
        self.assertFalse(any('Each Essay carries' in line for line in self.tree()))

    def test_numbering_restarts_under_each_heading_and_needs_no_space(self):
        geography = next(n for r in self.syl.roots for n in r.walk() if n.title.startswith('Geography of the Region'))
        # "10.Urbanisation" does not continue 1, so it is text of entry 1, never entry 10.
        self.assertEqual(len(geography.children), 1)
        self.assertTrue(geography.children[0].title.startswith('Physical setting'))
        self.assertIn('10.Urbanisation', geography.children[0].title)
        prelim = self.syl.roots[0].children[0]
        self.assertEqual([c.title for c in prelim.children], ['Current Affairs', 'General Science', 'Logical Reasoning'])


class TestFlatProjection(unittest.TestCase):

    def test_a_bare_syllabus_root_gives_its_papers_as_subjects(self):
        from .materialize import flat_syllabus_from_tree
        leaf = lambda t: {'id': t, 'title': t, 'levelLabel': 'Topic', 'children': []}
        tree = [{'id': 'r', 'title': 'SYLLABUS', 'levelLabel': 'Syllabus', 'children': [
            {'id': 'p', 'title': 'GENERAL STUDIES (PRELIMINARY TEST)', 'levelLabel': 'Subject',
             'children': [leaf('Current Affairs'), leaf('Reasoning')]},
            {'id': 'm', 'title': 'Written Examination (Main)', 'levelLabel': 'Stage', 'children': [
                {'id': 'p1', 'title': 'PAPER-I: GENERAL ESSAY', 'levelLabel': 'Paper', 'children': [
                    {'id': 's1', 'title': 'Section-I', 'levelLabel': 'Section', 'children': [leaf('Social issues')]}]}]}]}]
        flat = flat_syllabus_from_tree(tree)
        self.assertEqual([(t['subject'], t['topicName']) for t in flat], [
            ('GENERAL STUDIES (PRELIMINARY TEST)', 'Current Affairs'),
            ('GENERAL STUDIES (PRELIMINARY TEST)', 'Reasoning'),
            ('PAPER-I: GENERAL ESSAY', 'Section-I')])
        self.assertEqual(flat[2]['subtopics'], ['Social issues'])

    def test_a_named_root_is_still_the_subject(self):
        from .materialize import flat_syllabus_from_tree
        flat = flat_syllabus_from_tree([{'id': 'r', 'title': 'Indicative Syllabus (Stage-I)', 'children': [
            {'id': 'a', 'title': 'Reasoning', 'children': []}]}])
        self.assertEqual(flat[0]['subject'], 'Indicative Syllabus (Stage-I)')


class TestStudyOrderReason(unittest.TestCase):

    def test_no_weightage_means_no_claim_of_one(self):
        from .verification.roadmap_guidance import deterministic_sequence
        steps = deterministic_sequence([{'id': 'a', 'topicName': 'A', 'subject': 'S', 'weightagePercentage': 0},
                                        {'id': 'b', 'topicName': 'B', 'subject': 'S', 'weightagePercentage': 12}])
        reasons = {s.topic_id: s.rationale for s in steps}
        self.assertEqual(reasons['a'], 'In the order the official syllabus lists it.')
        self.assertEqual(reasons['b'], 'Scheduled by weightage within its subject.')


def _prov(excerpt, page=1):
    return {'id': 'p', 'documentTitle': 'ERB Notice', 'officialUrl': 'https://erb.gov.in/n.pdf', 'pageNumber': page,
            'clauseNumber': 'c', 'publishedDate': '', 'verifiedDate': '', 'verifiedBy': '', 'taxonomyType': 'FACT',
            'verificationLevel': 'OFFICIALLY_VERIFIED', 'excerptText': excerpt}


class TestPracticeForm(unittest.TestCase):

    EXAM = {
        'id': 'exam-erb-2031', 'authorityName': 'Example Recruitment Board', 'officialDomain': 'https://erb.gov.in',
        'crucialEligibilityDate': '2031-07-01',
        'factEvidence': {'crucialEligibilityDate': _prov('Age as on 01/07/2031: 18 to 44 years')},
        'posts': [{'id': 'p1', 'postName': 'Officer A', 'minAge': 18, 'maxAge': 35},
                  {'id': 'p2', 'postName': 'Officer B', 'minAge': 21, 'maxAge': 44}],
        'ageRelaxations': [{'category': 'SC/ST', 'years': 5, 'status': 'VERIFIED'}],
        'dates': [
            {'type': 'APPLICATION_OPEN', 'dateTimeStr': '2031-05-21 00:00:00', 'status': 'SUPERSEDED', 'provenance': _prov('from 21.05.2031')},
            {'type': 'APPLICATION_OPEN', 'dateTimeStr': '2031-06-23 00:00:00', 'status': 'AVAILABLE', 'provenance': _prov('re-open from 23.06.2031')},
            {'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2031-06-22 00:00:00', 'status': 'SUPERSEDED', 'provenance': _prov('to 22.06.2031')},
            {'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2031-06-25 00:00:00', 'status': 'AVAILABLE',
             'provenance': dict(_prov('re-open … to 25.06.2031'), supersedes=[_prov('to 22.06.2031')])}],
        'applicationGuide': {'officialPortal': 'https://erb.gov.in', 'fee': {'amounts': ['100'], 'exemptions': [
            {'category': 'CATEGORY:women', 'provenance': _prov('Women are exempted from fee', 9)},
            {'category': 'CATEGORY:scheduled castes', 'provenance': _prov('Women are exempted from fee', 9)},
            {'category': 'CATEGORY:sc', 'provenance': _prov('Women are exempted from fee', 9)}]}},
    }

    def setUp(self):
        from .runtime_simulator import build_simulator
        self.spec = build_simulator(self.EXAM)
        self.traps = {t['id']: t for t in self.spec['traps']}

    def test_the_window_runs_from_the_first_opening_to_the_governing_close(self):
        rule = self.traps['trap-window']['rule']
        # An application made in the original window was not late: a re-opening adds days.
        self.assertEqual((rule['earliest'], rule['latest']), ('2031-05-21', '2031-06-25'))
        self.assertIn('to 22.06.2031', self.traps['trap-window']['rememberRule'])

    def test_age_is_checked_against_every_post_at_once(self):
        self.assertEqual(self.traps['trap-too-young']['rule']['latest'], '2013-07-01')      # 18 on 2031-07-01
        self.assertEqual(self.traps['trap-over-age']['rule']['earliest'], '1986-07-02')     # older than 44
        self.assertEqual(self.traps['trap-over-age']['severity'], 'WARNING')
        self.assertIn('SC/ST (+5 years)', self.traps['trap-over-age']['whyItMatters'])

    def test_an_exempt_category_is_listed_once(self):
        fee = next(m for m in self.spec['modules'] if m['cardName'] == 'Fee')
        labels = [o['label'] for o in fee['fields'][0]['options']]
        self.assertEqual(labels[1:], ['Women', 'Scheduled castes'])

    def test_every_check_quotes_its_statement(self):
        self.assertTrue(all(t['officialClause'] and t['noticeReference'] for t in self.spec['traps']))
        self.assertEqual(self.spec['examId'], 'exam-erb-2031')

    def test_a_record_with_nothing_to_check_gets_no_form(self):
        from .runtime_simulator import build_simulator
        self.assertIsNone(build_simulator({'id': 'exam-y', 'posts': [], 'dates': [], 'applicationGuide': {}}))


if __name__ == '__main__':
    unittest.main()
