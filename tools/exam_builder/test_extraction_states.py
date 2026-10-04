"""A document that could not be read stays visibly unreadable; it is never relabelled as absent.

Three situations must stay apart for every section a candidate sees, including the sections GovOS
derives from others (Study Roadmap, Mock Tests):

  * the document was read and the value extracted          -> VERIFIED / SUPPORTED
  * the document exists but the reader or OCR failed on it  -> EXTRACTION_FAILED / SOURCE_UNREADABLE
  * no document is available                                 -> SOURCE_NOT_FOUND_AFTER_SEARCH (or an outage)

and only the authority's own listing showing none is NOT_YET_PUBLISHED. The derived sections used to
read NOT_YET_PUBLISHED ("will activate once the exam pattern is officially released") whenever the pattern
was not FOUND -- including a pattern that was found and could not be read -- and `nextSteps` was
NOT_YET_PUBLISHED whenever absent.

Run: python -m pytest tools/exam_builder/test_extraction_states.py -q
"""
from __future__ import annotations

import unittest

from . import discover as D
from .completeness import CompletenessState as S, evaluate_completeness
from .test_materialize import _passing_record
from ..exam_authoring.record import Field

URL = 'https://zeta.gov.in/notice'


def report(rec, *, unreadable=False, infra=False, searched=frozenset()):
    sources = D.SourceSet(exam_id=rec.exam_id, authority_domain=rec.official_domain)
    sources.has_unreadable_docs = unreadable
    sources.infrastructure_failed = infra
    return evaluate_completeness(rec, sources, searched_not_found=searched)


class DerivedSectionsKeepTheirInputsState(unittest.TestCase):

    def test_extraction_succeeds(self):
        rec = _passing_record()                                    # examPattern FOUND
        self.assertIs(report(rec).get_section('mock-tests').state, S.SUPPORTED_AND_PROJECTED)

    def test_document_exists_but_the_reader_fails(self):
        rec = _passing_record()
        rec.set(Field.not_extracted('examPattern', URL, 'scheme'))
        rec.note(f'scheme_tables failed on {URL}: ValueError("merged cell")')
        r = report(rec)
        self.assertIs(r.get_section('mock-tests').state, S.EXTRACTION_FAILED)
        self.assertNotEqual(r.get_section('mock-tests').state, S.NOT_YET_PUBLISHED)
        self.assertNotIn('officially released', r.get_section('mock-tests').student_status_summary)

    def test_document_downloaded_but_unreadable(self):
        rec = _passing_record()
        rec.set(Field.not_extracted('examPattern', URL, 'scheme'))
        r = report(rec, unreadable=True)
        self.assertIs(r.get_section('mock-tests').state, S.SOURCE_UNREADABLE)
        self.assertIn('could not be read', r.get_section('mock-tests').student_status_summary)

    def test_reader_failure_is_not_relabelled_unreadable_by_another_document(self):
        rec = _passing_record()
        rec.set(Field.not_extracted('examPattern', URL, 'scheme'))
        rec.note(f'scheme_tables failed on {URL}: ValueError("merged cell")')
        # some other document of the build was a scan; this field's own document had text to fail on
        self.assertEqual(report(rec, unreadable=True).get_section('pattern').fields['examPattern'], 'EXTRACTION_FAILED')

    def test_document_unavailable(self):
        rec = _passing_record()
        del rec.fields['examPattern']
        r = report(rec)
        self.assertIs(r.get_section('mock-tests').state, S.SOURCE_NOT_FOUND_AFTER_SEARCH)
        self.assertIs(report(rec, infra=True).get_section('mock-tests').state, S.INFRASTRUCTURE_FAILURE)

    def test_only_the_authoritys_listing_makes_it_not_yet_published(self):
        rec = _passing_record()
        rec.set(Field.not_published('examPattern', 'Zeta Recruitment Board lists no scheme for 2028'))
        self.assertIs(report(rec).get_section('mock-tests').state, S.NOT_YET_PUBLISHED)

    def test_roadmap_takes_its_weakest_input(self):
        rec = _passing_record()                                     # syllabus NOT_PUBLISHED by the listing
        rec.set(Field.not_extracted('examPattern', URL, 'scheme'))
        rec.note(f'scheme_tables failed on {URL}: ValueError("merged cell")')
        self.assertIs(report(rec).get_section('roadmap').state, S.EXTRACTION_FAILED)

    def test_absent_next_steps_are_not_called_unpublished(self):
        rec = _passing_record()
        del rec.fields['nextSteps']
        r = report(rec)
        states = {sec.section_id: sec for sec in r.sections}
        holders = [s for s in states.values() if 'nextSteps' in s.fields]
        self.assertTrue(holders)
        for sec in holders:
            self.assertEqual(sec.fields['nextSteps'], 'SOURCE_NOT_FOUND_AFTER_SEARCH')


if __name__ == '__main__':
    unittest.main()
