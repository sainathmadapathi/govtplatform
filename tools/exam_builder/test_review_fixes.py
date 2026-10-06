"""Fixes found while documenting the builder, each held here so it stays fixed.

1. **A failing domain reader is EXTRACTION_FAILED, not silence.** `completeness._reader_raised` looked
   only for the contract extractor's log line ("<extractor> failed on …"), but `build.py` runs a domain
   reader first for most fields and logs under that reader's own name ("extract_pattern failed on …").
   Those failures went unseen. `DOMAIN_READERS` names them, and the drift test below re-reads build.py so
   a new reader cannot be added without it.
2. **A corrigendum line's checks are independent.** When a line read as a date extension but its quote
   did not verify, `extract_corrigenda` skipped the whole line, so the vacancy revision on that same line
   was never read.
3. **Evidence quotes the value it is evidence for.** `semantic._narrowest_span` kept the shortest sentence
   that yielded *any* value, so a shorter sentence stating another figure could become the quote.

Run: python -m pytest tools/exam_builder/test_review_fixes.py -q
"""
from __future__ import annotations

import os
import re
from unittest import mock

from ..exam_authoring.record import ExamRecord
from . import corrigenda
from .semantic import _narrowest_span
from .completeness import DOMAIN_READERS, _reader_raised
from .evidence import EvidenceStatus
from .schema import SourceDocument

BUILD = os.path.join(os.path.dirname(__file__), 'build.py')


def _record(*log: str) -> ExamRecord:
    rec = ExamRecord(exam_id='exam-x-y-2026', code='X_Y', title='X Y 2026', authority_name='X',
                     official_domain='https://x.invalid')
    for line in log:
        rec.note(line)
    return rec


def test_every_domain_reader_in_build_is_named_for_its_field():
    """Re-read build.py: every "<reader> failed on" note inside a `cf.name == '<field>'` block must be
    one of DOMAIN_READERS[<field>] (or that field's contract extractor, logged as {cf.extractor})."""
    field, missing = None, []
    for line in open(BUILD, encoding='utf-8'):
        m = re.search(r"cf\.name == '([A-Za-z]+)'", line)
        if m:
            field = m.group(1)
        n = re.search(r"rec\.note\(f'([A-Za-z_.() ]+) failed on ", line)
        if n and field and n.group(1) not in DOMAIN_READERS.get(field, ()):
            missing.append((field, n.group(1)))
    assert missing == [], f'readers build.py runs that completeness cannot see fail: {missing}'


def test_a_domain_reader_failure_is_seen():
    rec = _record("extract_pattern failed on https://x.invalid/n.pdf: ValueError('bad table')")
    assert _reader_raised(rec, 'examPattern') is True
    assert _reader_raised(rec, 'syllabus') is False, 'one field’s failure is not another’s'
    assert _reader_raised(_record(), 'examPattern') is False


def test_a_reader_named_with_a_qualifier_is_seen():
    rec = _record("extract_eligibility (qualification) failed on https://x.invalid/n.pdf: KeyError('x')")
    assert _reader_raised(rec, 'qualification') is True
    assert _reader_raised(rec, 'ageLimits') is False


def test_an_unverified_date_reading_does_not_hide_the_vacancy_revision_on_its_line():
    text = 'The last date is extended to 30 March 2026 and vacancies are revised from 100 to 120.'
    doc = SourceDocument(id='d', url='https://x.invalid/corr.pdf', title='Corrigendum',
                         published_at='2026-03-01')
    real_verify = corrigenda.Evidence.verify

    def verify(self, source_text):
        # The date reading fails its check; every other reading is checked for real.
        if self.reading.startswith('date'):
            return EvidenceStatus.NOT_IN_SOURCE
        return real_verify(self, source_text)

    with mock.patch.object(corrigenda.Evidence, 'verify', verify):
        notices = corrigenda.extract_corrigenda(doc, text, exam_id='exam-x-y-2026')
    assert [n.affected_field for n in notices] == ['vacanciesTotal']
    assert notices[0].old_value == 100 and notices[0].new_value == 120
    both = corrigenda.extract_corrigenda(doc, text, exam_id='exam-x-y-2026')
    assert sorted(n.affected_field for n in both) == ['application_close', 'vacanciesTotal']


def test_the_narrowest_quote_must_carry_the_same_value():
    class Spec:   # stands in for a FieldSpec: only normalise() is read
        @staticmethod
        def normalise(text):
            m = re.search(r'(\d+) vacancies', text)
            return int(m.group(1)) if m else None
    chunk = ('The Commission will fill 563 vacancies across all services this year. '
             'In 2022 there were 503 vacancies only.')
    span = _narrowest_span(chunk, Spec, 563)
    assert '563' in span and '503' not in span
