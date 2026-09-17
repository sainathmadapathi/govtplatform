"""The checks that must pass before anything reaches `data.ts`.

The isolation rule in CLAUDE.md is absolute: no exam's information may interfere with
another's. A pipeline that writes records automatically is the most likely place to break
it, so the checks here run on every extraction and a failure stops emission rather than
producing a record someone has to notice is wrong.
"""
from __future__ import annotations

import re
from urllib.parse import urlparse

from .record import ExamRecord, Status


class IsolationError(RuntimeError):
    """Raised when a record contains something that does not belong to its own exam."""


def assert_single_authority(rec: ExamRecord) -> None:
    """Every URL read must belong to the exam's own authority."""
    own = urlparse(rec.official_domain).netloc.replace('www.', '')
    if not own:
        raise IsolationError(f'{rec.exam_id}: no official domain set')
    foreign = []
    for url in rec.sources_read:
        host = urlparse(url).netloc.replace('www.', '')
        if host and host != own and not host.endswith('.' + own):
            foreign.append(url)
    if foreign:
        raise IsolationError(
            f'{rec.exam_id}: read {len(foreign)} URL(s) outside {own} — {foreign[:3]}')


#: Tokens that name a *different* exam family. A record that mentions one has almost
#: certainly picked up another exam's page, which is the failure this catches.
_FOREIGN_EXAM_TOKENS = {
    'exam-upsc': (r'\bSSC\b', r'\bIBPS\b', r'\bAPPSC\b'),
    'exam-ssc': (r'\bUPSC\b', r'\bIBPS\b', r'\bAPPSC\b'),
    'exam-ibps': (r'\bUPSC\b', r'\bSSC\b', r'\bAPPSC\b'),
    'exam-appsc': (r'\bUPSC\b', r'\bSSC\b', r'\bIBPS\b'),
}


def foreign_exam_mentions(rec: ExamRecord) -> list[str]:
    """Report, don't raise: a notice may legitimately name another body in passing.

    UPSC's own notice mentions the Staff Selection Commission nowhere, but an APPSC notice
    can cite a UPSC rule. The pipeline surfaces these for a person rather than deciding.
    """
    prefix = next((p for p in _FOREIGN_EXAM_TOKENS if rec.exam_id.startswith(p)), None)
    if not prefix:
        return []
    hits = []
    for name, f in rec.fields.items():
        if not f.usable:
            continue
        text = str(f.value)
        for rx in _FOREIGN_EXAM_TOKENS[prefix]:
            if re.search(rx, text):
                hits.append(f'{name}: matches {rx}')
    return hits


def assert_ids_consistent(rec: ExamRecord) -> None:
    if not rec.exam_id.startswith('exam-'):
        raise IsolationError(f'{rec.exam_id}: exam id must start with "exam-"')
    if not rec.code or not rec.title:
        raise IsolationError(f'{rec.exam_id}: code and title are required')


def report(rec: ExamRecord) -> dict:
    """A human-readable account of what this run can and cannot claim."""
    s = rec.summary()
    scanned = [n for n, f in rec.fields.items()
               if f.status is Status.NEEDS_REVIEW and 'no text layer' in (f.note or '')]
    # A run that extracted almost nothing is a broken run, not a thin exam. Saying so keeps
    # an adapter failure from looking like an authority that publishes nothing.
    total = len(rec.fields) or 1
    extracted = sum(1 for f in rec.fields.values() if f.status is Status.FOUND)
    return {
        **s,
        'foreignMentions': foreign_exam_mentions(rec),
        'unreadableSources': scanned,
        'coverage': f'{extracted}/{total} fields sourced',
        'lowCoverage': extracted < max(3, total // 3),
        'log': rec.log,
    }


def run_all(rec: ExamRecord) -> dict:
    assert_ids_consistent(rec)
    assert_single_authority(rec)
    return report(rec)
