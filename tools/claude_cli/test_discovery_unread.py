"""A reachable candidate whose text the server did not read (a PDF, say) is labelled UNREAD, not guessed at.

Found with the real CLI: five official ssc.gov.in notice PDFs came back `NOT_MATCHED` / `WEAK` because the
hint was computed from the title alone. The files were reachable and plainly the right notices; the server
had simply not read them. An identity label must say what was checked.

Run: python -m unittest tools.claude_cli.test_discovery_unread
"""
from __future__ import annotations

import unittest

from .discovery import Candidate, FetchResult, _check, classify_url


def _fetch(text: str, ok: bool = True):
    def fetch(url):
        return FetchResult(ok=ok, status=200 if ok else 404, final_url=url, text=text, error='' if ok else 'HTTP 404')
    return fetch


class TestUnreadCandidates(unittest.TestCase):

    def _candidate(self):
        return Candidate(title='Notice of Examination 2026', url='https://ssc.gov.in/files/notice.pdf', trust='OFFICIAL')

    def test_a_reachable_file_with_no_text_is_unread_not_not_matched(self):
        c = _check(self._candidate(), 'SSC CGL 2026 notice of examination', _fetch(''), classify_url)
        self.assertTrue(c.reachable)
        self.assertEqual(c.identity, 'UNREAD')
        self.assertTrue(any('not read' in r for r in c.reasons), c.reasons)

    def test_a_page_with_text_still_gets_a_real_hint(self):
        c = _check(self._candidate(), 'SSC CGL 2026 notice of examination',
                   _fetch('Notice of Examination 2026 for the SSC CGL examination'), classify_url)
        self.assertIn(c.identity, ('MATCHED', 'WEAK'))

    def test_an_unreachable_candidate_is_still_unchecked(self):
        c = _check(self._candidate(), 'q', _fetch('', ok=False), classify_url)
        self.assertFalse(c.reachable)
        self.assertEqual(c.identity, 'UNCHECKED')


if __name__ == '__main__':
    unittest.main()
