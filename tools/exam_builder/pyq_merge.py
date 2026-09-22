"""Merge papers, questions and answer keys — and refuse anything whose paper is not exact.

The four operations again, with one difference that matters more here than anywhere else in
this pipeline: **identity is the paper, not the item**. Two shifts of one day both have a
question 47 and both have an answer for it, and the only thing standing between a candidate
and the wrong answer is that the paper identities do not match.

So nothing in this module compares question numbers, question text or answers before it has
compared `PaperIdentity`. Where the papers differ, the items are different items and no
amount of similarity in their text makes them one.

A revised or final key supersedes the earlier key for *the same paper* and keeps it. Two
keys that disagree with no revision between them are refused, and both are kept for a person
to look at.
"""
from __future__ import annotations

import re

from .merge import FieldDecision, FieldOutcome, MergeAction
from .schema import (AnswerEntry, AnswerKey, AnswerKeyKind, AnswerStatus, OfficialQuestion,
                     PaperIdentity, SourceStatus)

#: The order in which an authority's keys supersede one another.
_KEY_ORDER = {AnswerKeyKind.PROVISIONAL: 0, AnswerKeyKind.UNSPECIFIED: 1,
              AnswerKeyKind.REVISED: 2, AnswerKeyKind.FINAL: 3}


class ItemDecision:
    """What the merge decided about one paper, question or key."""

    def __init__(self, action: MergeAction, label: str, item_id: str = '',
                 fields: list | None = None, reason: str = '',
                 superseded: str = '') -> None:
        self.action = action
        self.label = label
        self.item_id = item_id
        self.fields = fields or []
        self.reason = reason
        self.superseded = superseded

    def field(self, name: str):
        return next((f for f in self.fields if f.field == name), None)


class PyqMergeReport:
    def __init__(self) -> None:
        self.decisions: list[ItemDecision] = []

    def of(self, action: MergeAction) -> list:
        return [d for d in self.decisions if d.action is action]

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out


def same_paper(left: PaperIdentity, right: PaperIdentity) -> bool:
    """Is this the same paper, exactly?

    `PaperIdentity.matches` allows either side to be silent about a part it never printed,
    which is right: one document may name the shift and another may not. What it never
    allows is two different stated values for the same part, and that is the whole defence
    against a Shift 1 key reaching Shift 2.
    """
    return left.matches(right)


def merge_questions(existing: list, incoming: list) -> PyqMergeReport:
    """Fold extracted questions into the ones a record already holds.

    Matching is on the paper *and* the number, never the number alone. A question whose
    paper the record does not hold is added; one the record holds with different text is
    contested, because a question paper does not change and two readings that disagree mean
    one of them is wrong.
    """
    report = PyqMergeReport()
    by_key = {}
    for question in incoming:
        by_key.setdefault(question.identity_key(), []).append(question)
    used: set = set()

    for row in existing:
        identity = row['paper'] if isinstance(row.get('paper'), PaperIdentity) else None
        number = str(row.get('number') or row.get('questionNumber') or '')
        if identity is None or not number:
            report.decisions.append(ItemDecision(
                MergeAction.UNCHANGED, row.get('id', number), row.get('id', ''),
                reason='the record does not identify this question’s exact paper, so '
                       'nothing may be matched against it'))
            continue

        candidates = [q for group in by_key.values() for q in group
                      if same_paper(identity, q.paper)
                      and q.number.strip().lower() == number.strip().lower()]
        if not candidates:
            report.decisions.append(ItemDecision(
                MergeAction.UNCHANGED, f'{identity.describe()} Q{number}', row.get('id', ''),
                reason='no extracted question is of this paper and this number; the record '
                       'is left exactly as it is'))
            continue
        if len(candidates) > 1:
            report.decisions.append(ItemDecision(
                MergeAction.CONFLICTED, f'{identity.describe()} Q{number}',
                row.get('id', ''),
                reason=f'{len(candidates)} extracted questions claim this paper and number, '
                       f'so which is which is not established; nothing is merged'))
            continue

        match = candidates[0]
        used.add(id(match))
        text = (row.get('text') or row.get('promptEnglish') or '').strip()
        fields = [FieldDecision('paper', FieldOutcome.KEPT, identity.describe(),
                                match.paper.describe(),
                                'the same paper, exactly')]
        if text and _normalised(text) != _normalised(match.text):
            fields.append(FieldDecision(
                'text', FieldOutcome.UNDER_REVIEW, text, match.text,
                'the record and this reading of the paper word the question differently; a '
                'question paper does not change, so one of the two is a misreading and '
                'neither is published over the other'))
            report.decisions.append(ItemDecision(
                MergeAction.CONFLICTED, f'{identity.describe()} Q{number}',
                row.get('id', ''), fields=fields, reason='the wording is contested'))
            continue
        fields.append(FieldDecision('text', FieldOutcome.CONFIRMED, text, match.text,
                                    'both readings of the paper agree'))
        report.decisions.append(ItemDecision(
            MergeAction.CONFIRMED, f'{identity.describe()} Q{number}', row.get('id', ''),
            fields=fields, reason='the paper confirms this question'))

    for question in incoming:
        if id(question) in used:
            continue
        report.decisions.append(ItemDecision(
            MergeAction.ADDED, f'{question.paper.describe()} Q{question.number}',
            question.identity_key(),
            reason='the paper contains this question and the record does not hold it'))
    return report


def _normalised(text: str) -> str:
    return re.sub(r'\s+', ' ', (text or '')).strip().lower()


def merge_answer_keys(existing: list, incoming: list) -> PyqMergeReport:
    """Fold extracted answer keys into the ones a record holds, by exact paper.

    A key for a paper the record does not hold is added. A key of a different kind for a
    paper it does hold supersedes the earlier one and keeps it, because a candidate who
    challenged an answer needs both. A key of the *same* kind that disagrees is refused.
    """
    report = PyqMergeReport()
    used: set = set()

    for row in existing:
        identity = row.get('paper')
        if not isinstance(identity, PaperIdentity) or not identity.is_paper_level:
            report.decisions.append(ItemDecision(
                MergeAction.UNCHANGED, str(row.get('id', '')), str(row.get('id', '')),
                reason='the record does not identify this key’s exact paper, so it is '
                       'left alone and never attached to the nearest-looking paper'))
            continue
        kind = row.get('kind')
        candidates = [k for k in incoming if same_paper(identity, k.paper)]
        if not candidates:
            report.decisions.append(ItemDecision(
                MergeAction.UNCHANGED, identity.describe(), str(row.get('id', '')),
                reason='no extracted key is for this exact paper'))
            continue

        same_kind = [k for k in candidates if k.kind == kind]
        later = [k for k in candidates
                 if _KEY_ORDER.get(k.kind, 1) > _KEY_ORDER.get(kind, 1)]
        if later:
            newest = max(later, key=lambda k: _KEY_ORDER.get(k.kind, 1))
            used.add(id(newest))
            report.decisions.append(ItemDecision(
                MergeAction.SUPERSEDED, f'{identity.describe()} — {newest.kind.value}',
                newest.id, superseded=str(row.get('id', '')),
                reason=f'the authority has since published a {newest.kind.value.lower()} '
                       f'key for this paper; the earlier one is kept as superseded'))
            continue
        if same_kind:
            used.add(id(same_kind[0]))
            report.decisions.append(ItemDecision(
                MergeAction.CONFIRMED, identity.describe(), str(row.get('id', '')),
                reason='the same key, for the same paper'))
            continue
        report.decisions.append(ItemDecision(
            MergeAction.UNCHANGED, identity.describe(), str(row.get('id', '')),
            reason='an earlier kind of key was extracted for this paper; the record keeps '
                   'the later one'))

    for key in incoming:
        if id(key) in used:
            continue
        report.decisions.append(ItemDecision(
            MergeAction.ADDED, f'{key.paper.describe()} — {key.kind.value}', key.id,
            reason='the authority published this key and the record does not hold it'))
    return report


def merge_answers(existing: AnswerKey, incoming: AnswerKey) -> list:
    """Per-question answers of two keys for the same paper.

    Refuses outright if the papers differ: a key is a list of answers *to a paper*, and
    applying one paper's answers to another's questions is the single worst thing this
    module could do.
    """
    if not same_paper(existing.paper, incoming.paper):
        raise ValueError('answer keys for different papers are never merged')
    revises = _KEY_ORDER.get(incoming.kind, 1) > _KEY_ORDER.get(existing.kind, 1)
    by_number = {e.question_number: e for e in existing.entries}
    out: list[AnswerEntry] = []
    for entry in incoming.entries:
        earlier = by_number.get(entry.question_number)
        if earlier is None:
            out.append(entry)
            continue
        if sorted(earlier.accepted) == sorted(entry.accepted) and \
                earlier.value == entry.value:
            out.append(earlier)
            continue
        if not revises:
            held = AnswerEntry(question_number=entry.question_number, paper=entry.paper,
                               status=AnswerStatus.UNKNOWN, evidence=list(entry.evidence),
                               note='two keys of the same standing give different answers '
                                    'for this question and neither revises the other; '
                                    'no answer is published')
            out.append(held)
            continue
        entry.supersedes = earlier
        entry.status = (AnswerStatus.REVISED if entry.accepted or entry.value
                        else entry.status)
        out.append(entry)
    for number, earlier in by_number.items():
        if not any(e.question_number == number for e in out):
            out.append(earlier)
    return out
