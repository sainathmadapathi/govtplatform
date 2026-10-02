"""Guards for two mistakes that were made twice while this package was written.

1. A `\\b` word boundary written in an ordinary (non-raw) string, or pushed through a shell/patch
   script, becomes a BACKSPACE byte (0x08). The regular expression then silently matches nothing: the
   "claims an official origin" check and the "401 means not signed in" check both looked fine, compiled,
   and did nothing. No source file may contain a control byte.
2. The two patterns that were affected are exercised here on real strings, so a regression shows up as a
   failing assertion and not as a quietly absent check.

Run: python -m unittest tools.claude_cli.test_source_hygiene
"""
from __future__ import annotations

import os
import unittest

from .client import _AUTH_PATTERNS
from .handlers import _OFFICIAL_CLAIM

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PACKAGE_DIR))
SCANNED = (PACKAGE_DIR, os.path.join(REPO_ROOT, 'tools', 'exam_builder'), os.path.join(REPO_ROOT, 'app.py'))


def _files():
    for target in SCANNED:
        if os.path.isfile(target):
            yield target
            continue
        for root, dirs, names in os.walk(target):
            dirs[:] = [d for d in dirs if d not in ('__pycache__', 'fixtures')]
            for name in names:
                if name.endswith(('.py', '.mjs', '.ts', '.tsx')):
                    yield os.path.join(root, name)


class TestNoControlBytes(unittest.TestCase):

    def test_no_source_file_contains_a_control_byte(self):
        offenders = []
        for path in _files():
            with open(path, 'rb') as fh:
                data = fh.read()
            bad = sorted({c for c in data if c < 32 and c not in (9, 10, 13)})
            if bad:
                offenders.append(f'{os.path.relpath(path, REPO_ROOT)}: {[hex(c) for c in bad]}')
        self.assertEqual(offenders, [], 'control bytes (a "\\b" that became a backspace?) in source files')


class TestOfficialOriginCheck(unittest.TestCase):

    def test_a_question_that_dates_itself_to_an_examination_is_caught(self):
        for text in ('Example Commission 2030 paper', 'a question from the paper of 2023', 'Tier-I exam in 2022',
                     'a 2030 shift question', 'SSC CGL 2023', 'asked in the previous year', 'a past paper item',
                     'see https://example.gov.in/q', 'www.example.org', 'actual exam question'):
            with self.subTest(text=text):
                self.assertIsNotNone(_OFFICIAL_CLAIM.search(text))

    def test_ordinary_practice_wording_is_not_caught(self):
        for text in ('In 2023 a shop sold 40 items', 'What is 20% of 50?', 'the examination hall rules',
                     'A train covers 120 km in 2 hours', 'Which of these is a paperless method?'):
            with self.subTest(text=text):
                self.assertIsNone(_OFFICIAL_CLAIM.search(text))


class TestNotSignedInDetection(unittest.TestCase):

    def test_a_401_is_a_login_problem(self):
        for text in ('API Error: 401 unauthorized', 'HTTP 401', 'oauth token has expired', 'Not logged in'):
            with self.subTest(text=text):
                self.assertIsNotNone(_AUTH_PATTERNS.search(text))

    def test_digits_that_merely_contain_401_are_not(self):
        for text in ('failed after 14012 ms', 'pid 40123 exited', 'code 4010'):
            with self.subTest(text=text):
                self.assertIsNone(_AUTH_PATTERNS.search(text))


if __name__ == '__main__':
    unittest.main()
