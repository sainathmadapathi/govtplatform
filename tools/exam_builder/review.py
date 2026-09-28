"""Human review of a build: the one place a person's decision enters the record.

The engine builds as much as it can establish; where it read something but not confidently
(NEEDS_REVIEW), or read something a person judges wrong, the build stops at the gate and
names the field. This module is how the person answers, and it is deliberately small:

    APPROVE    publish the field as read (or with a corrected value the reviewer supplies).
               The document citation is kept -- the evidence is still the authority's -- and
               the reviewer is named in the note. A value the reviewer types must still sit
               under the same citation; nothing here lets a fact in without a source.
    WITHHOLD   keep the field out of publication. It becomes NOT_EXTRACTED with the reviewer's
               reason: a gap a person established, which is ours, never the authority's
               silence (NOT_PUBLISHED is not available to a reviewer).

A review names a field; it never names an exam or an authority. Reviews are applied before
the publication gate and the gate itself is unchanged: an APPROVE of a required field the
reader did not find is not possible, because there is nothing to approve.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Any, Optional

from ..exam_authoring.record import ExamRecord, Field, Status


class ReviewDecision(str, Enum):
    APPROVE = 'APPROVE'
    WITHHOLD = 'WITHHOLD'


@dataclass
class FieldReview:
    field: str
    decision: ReviewDecision
    reviewer: str
    note: str = ''
    #: APPROVE only: a corrected value. None keeps the value the reader produced.
    value: Optional[Any] = None


@dataclass
class ReviewOutcome:
    applied: list[str] = dc_field(default_factory=list)
    skipped: list[str] = dc_field(default_factory=list)
    notes: list[str] = dc_field(default_factory=list)

    def to_dict(self) -> dict:
        return {'applied': list(self.applied), 'skipped': list(self.skipped), 'notes': list(self.notes)}


def apply_reviews(rec: ExamRecord, reviews: list[FieldReview] | None) -> ReviewOutcome:
    """Fold a person's decisions into the record, field by field, and say what happened."""
    out = ReviewOutcome()
    for rv in reviews or []:
        f = rec.fields.get(rv.field)
        if not rv.reviewer.strip():
            out.skipped.append(rv.field)
            out.notes.append(f'{rv.field}: review ignored — no reviewer named')
            continue
        if rv.decision is ReviewDecision.WITHHOLD:
            if f is None:
                out.skipped.append(rv.field)
                out.notes.append(f'{rv.field}: nothing to withhold; the field was never read')
                continue
            rec.set(Field.not_extracted(
                rv.field, (f.citation.url if f.citation else rec.official_domain),
                f'{rv.field} withheld by reviewer {rv.reviewer}: {rv.note or "no reason given"} '
                f'(read as {f.status.value}; this is a gap a person chose, not a fact about the authority)'))
            out.applied.append(rv.field)
            out.notes.append(f'{rv.field}: withheld by {rv.reviewer}')
            continue
        # APPROVE
        if f is None or f.citation is None or f.status not in (Status.NEEDS_REVIEW, Status.FOUND):
            out.skipped.append(rv.field)
            out.notes.append(f'{rv.field}: cannot approve — no cited reading exists to approve')
            continue
        value = f.value if rv.value is None else rv.value
        approved = Field.found(rv.field, value, f.citation)
        approved.note = (f'approved by reviewer {rv.reviewer}'
                         + (' with a corrected value' if rv.value is not None else '')
                         + (f': {rv.note}' if rv.note else '')
                         + (f' (reader note: {f.note})' if f.note else ''))
        rec.set(approved)
        rec.note(f'{rv.field}: {approved.note}')
        out.applied.append(rv.field)
        out.notes.append(f'{rv.field}: approved by {rv.reviewer}')
    return out
