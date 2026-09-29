"""Evidence on every published fact, on an invented authority ("Example Recruitment Board").

The runtime_evidence module names no exam and no authority. These tests hold its rules:
evidence identity follows what is cited, a replaced statement and its replacement are linked
both ways, a derived figure names its inputs, and nothing without a source claims to be
officially verified. The extraction fixes found while building it are held here too.

Run: python -m unittest tools.exam_builder.test_runtime_evidence
"""
from __future__ import annotations

import copy
import unittest

from .runtime_evidence import (derive_pattern_evidence, evidence_id, evidence_problems, link_revisions,
                               stamp, stamp_exam, strip_evidence_metadata)


def prov(pid='p1', url='https://erb.gov.in/notice.pdf', page=3, clause='Vacancies', excerpt='TOTAL 120',
         level='OFFICIALLY_VERIFIED'):
    return {'id': pid, 'documentTitle': 'ERB Notice', 'officialUrl': url, 'pageNumber': page,
            'clauseNumber': clause, 'publishedDate': '', 'verifiedDate': '2031-01-01',
            'verifiedBy': 'GovOS exam builder', 'taxonomyType': 'FACT', 'verificationLevel': level,
            'excerptText': excerpt}


class TestIdentity(unittest.TestCase):

    def test_the_same_citation_keeps_one_identity_and_another_gets_its_own(self):
        a, b = prov('a'), prov('b')                       # same words, same page, different ids
        self.assertEqual(evidence_id(a), evidence_id(b))
        self.assertNotEqual(evidence_id(a), evidence_id(prov(excerpt='TOTAL 121')))
        self.assertNotEqual(evidence_id(a), evidence_id(prov(page=4)))

    def test_stamping_names_the_authority_and_the_kind(self):
        p = stamp(prov(), 'Example Recruitment Board')
        self.assertEqual((p['authorityName'], p['evidenceType']), ('Example Recruitment Board', 'DIRECT'))
        self.assertEqual(p['evidenceId'], evidence_id(p))

    def test_nothing_without_a_source_is_presented_as_verified(self):
        for bare in (prov(url=''), prov(page=None, excerpt='')):
            p = stamp(bare, 'Example Recruitment Board')
            self.assertEqual(p['verificationLevel'], 'UNDER_VERIFICATION')
        exam = {'authorityName': 'X', 'posts': [{'provenance': prov(url='')}]}
        exam['posts'][0]['provenance']['evidenceType'] = 'DIRECT'
        exam['posts'][0]['provenance']['evidenceId'] = evidence_id(exam['posts'][0]['provenance'])
        self.assertTrue(any('officially verified' in e for e in evidence_problems(exam)))


class TestReconciled(unittest.TestCase):

    def test_a_replaced_statement_and_its_replacement_are_linked_both_ways(self):
        shared = prov('shared')                            # a fallback provenance two rows share
        rows = [{'id': 'old', 'provenance': dict(prov('o', excerpt='Last date 14/03/2031'))},
                {'id': 'new', 'provenance': dict(prov('n', url='https://erb.gov.in/list', excerpt='Last date 16/03/2031'))},
                {'id': 'other', 'provenance': shared}]
        link_revisions(rows, {'old': 'new'})
        old, new = rows[0], rows[1]
        self.assertEqual(old['supersededBy'], 'new')
        self.assertEqual(old['provenance']['supersededBy']['excerptText'], 'Last date 16/03/2031')
        self.assertEqual([p['excerptText'] for p in new['provenance']['supersedes']], ['Last date 14/03/2031'])
        self.assertEqual({old['provenance']['evidenceType'], new['provenance']['evidenceType']}, {'RECONCILED'})
        self.assertIsNot(rows[2]['provenance'].get('supersedes'), new['provenance']['supersedes'],
                         'a shared provenance is copied, never changed in place')
        self.assertNotIn('supersedes', shared)


class TestDerived(unittest.TestCase):

    TREE = [{'id': 's', 'name': 'Stage-I', 'questions': 50, 'marks': 100, 'derived': ['questions', 'marks'],
             'negativeMarking': 'There will be negative marking of 0.25 marks.', 'provenance': prov('s', excerpt='negative marking of 0.25 marks'),
             'children': [
                 {'id': 'a', 'name': 'Part A', 'questions': 25, 'marks': 50, 'marksPerQuestion': 2.0,
                  'negativeMarking': 'There will be negative marking of 0.25 marks.',
                  'derived': ['marksPerQuestion', 'negativeMarking'], 'provenance': prov('a', excerpt='A 25 50')},
                 {'id': 'b', 'name': 'Part B', 'questions': 25, 'marks': 50, 'provenance': prov('b', excerpt='B 25 50')}]}]

    def setUp(self):
        self.tree = copy.deepcopy(self.TREE)
        derive_pattern_evidence(self.tree)
        stamp_exam({'authorityName': 'ERB', 'patternTree': self.tree})

    def inputs(self, node, key):
        return [p['excerptText'] for p in node['derivedEvidence'][key]['derivation']['inputs']]

    def test_a_quotient_names_the_row_it_divides(self):
        part = self.tree[0]['children'][0]
        self.assertEqual(part['derivedEvidence']['marksPerQuestion']['evidenceType'], 'DERIVED')
        self.assertEqual(self.inputs(part, 'marksPerQuestion'), ['A 25 50'])

    def test_a_sum_names_every_part_it_adds(self):
        self.assertEqual(self.inputs(self.tree[0], 'questions'), ['A 25 50', 'B 25 50'])

    def test_a_stage_rule_carried_down_names_the_stage(self):
        self.assertEqual(self.inputs(self.tree[0]['children'][0], 'negativeMarking'), ['negative marking of 0.25 marks'])

    def test_the_contract_holds(self):
        self.assertEqual(evidence_problems({'patternTree': self.tree}), [])

    def test_removing_the_metadata_gives_back_the_facts(self):
        self.assertEqual(strip_evidence_metadata(self.tree), strip_evidence_metadata(copy.deepcopy(self.TREE)))


class TestFiguresBehindEvidence(unittest.TestCase):

    def test_a_figure_computed_from_withheld_figures_is_withheld(self):
        from .materialize import _pattern_node
        held: list = []
        node = _pattern_node({'id': 'n', 'name': 'Part A', 'status': 'NEEDS_REVIEW', 'marks': 50, 'questions': 25,
                              'marksPerQuestion': 2.0, 'derived': ['marksPerQuestion']}, prov(), held)
        self.assertNotIn('marksPerQuestion', node)
        self.assertNotIn('derived', node)
        self.assertTrue(any(h['fields'] == ['marksPerQuestion'] for h in held))

    def test_a_sentence_is_not_cut_at_a_clause_number_or_a_decimal(self):
        from .pattern import read_negative_marking
        text = ('Questions are set in English. 13.8.2 There will be negative marking of 0.50 marks for each '
                'wrong answer. 13.9 Scheme of Stage-II')
        self.assertEqual(read_negative_marking(text).as_printed,
                         'There will be negative marking of 0.50 marks for each wrong answer.')
        self.assertEqual(read_negative_marking('Page 9 of 40 7.2.1 There will be negative marking of 1 mark for '
                                               'each wrong answer.').as_printed,
                         'There will be negative marking of 1 mark for each wrong answer.')
        self.assertEqual(read_negative_marking('Note. 0.25 marks will be deducted for each wrong answer.').as_printed,
                         '0.25 marks will be deducted for each wrong answer.')

    def test_a_document_name_starts_on_a_word_and_names_a_document(self):
        from .application import extract_required_documents
        from .schema import SourceDocument, SourceKind
        text = ('6.1 Candidates who seek age-relaxation must submit requisite certificate from the competent '
                'authority in the prescribed format. Candidates are advised to submit online application much '
                'before the closing date. Candidates must submit details of the own scribe at the time of examination.')
        d = SourceDocument(id='n', url='https://erb.gov.in/n.pdf', kind=SourceKind.NOTIFICATION, title='Notice',
                           authority='Example Recruitment Board', exam_id='exam-x')
        names = [x['name'] for x in extract_required_documents(d, text)]
        self.assertEqual(names, ['requisite certificate from the competent authority'])


if __name__ == '__main__':
    unittest.main()
