"""A reader that matched nothing is not the authority publishing nothing.

The photograph/signature and required-documents readers used to record NOT_PUBLISHED ("No distinct
photograph/signature guidelines published") whenever their patterns found nothing in a readable
notice -- GovOS's gap reported as the authority's silence. Where the notice speaks of the thing at
all, the field is NOT_EXTRACTED; only a notice that never mentions it says none was published.

Run: python -m unittest tools.exam_builder.test_reader_gaps
"""
from __future__ import annotations

import unittest

from ..exam_authoring.record import Status
from .test_attribution import read

SILENT = 'The examination will be held in two stages at district centres.'


class ReaderGapTests(unittest.TestCase):

    def test_a_notice_that_mentions_photographs_is_not_said_to_publish_none(self):
        got = read('photoSignatureGuidelines', 'The specifications for the photograph and signature are given on the portal.')
        self.assertIs(got.status, Status.NOT_EXTRACTED, got.note)
        self.assertIn('not a statement that the authority published none', got.note)

    def test_a_notice_that_mentions_uploads_is_not_said_to_publish_none(self):
        got = read('requiredDocuments', 'All documents to be uploaded are listed in the portal help section.')
        self.assertIs(got.status, Status.NOT_EXTRACTED, got.note)

    def test_a_notice_that_never_mentions_them_still_reads_as_none_published(self):
        self.assertIs(read('photoSignatureGuidelines', SILENT).status, Status.NOT_PUBLISHED)
        self.assertIs(read('requiredDocuments', SILENT).status, Status.NOT_PUBLISHED)

    def test_what_the_reader_can_structure_is_still_found(self):
        got = read('photoSignatureGuidelines', 'Candidates must upload a recent photograph and signature in the online application.')
        self.assertIs(got.status, Status.FOUND)


if __name__ == '__main__':
    unittest.main()
