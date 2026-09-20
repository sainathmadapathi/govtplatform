"""Getting newly extracted facts into an exam's record without damaging what is there.

This is the gap between a builder that can read documents and a product that shows anything.
It does four things and deliberately no more:

    MATCH      is the extracted fact about the same thing as one already in the record?
    CONFIRM    same answer -> one fact, more sources behind it
    SUPERSEDE  a later official document says it is changing this -> both kept, old inert
    REFUSE     two answers, neither claiming to correct the other -> NEEDS_REVIEW, both kept

The fourth is the one that matters. A merge engine that resolves disagreements is a merge
engine that will eventually resolve one wrongly and quietly, and a candidate cannot tell a
confident wrong date from a right one. So this refuses, loudly, and leaves the record as it
was until a person looks.

What it never does: delete an existing fact, prefer a value because it is newer, or prefer
one because it was extracted rather than authored. A hand-authored record carries a person's
reading of a document, which is at least as good as ours.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum

from .schema import Milestone, MilestoneState, SourceDocument, SourceKind, Status


class MergeAction(str, Enum):
    ADDED = 'ADDED'                #: nothing in the record covered this
    CONFIRMED = 'CONFIRMED'        #: the record already said this; more evidence now
    SUPERSEDED = 'SUPERSEDED'      #: a later official document changed it
    CONFLICTED = 'CONFLICTED'      #: two answers, no stated relationship between them
    UNCHANGED = 'UNCHANGED'        #: nothing incoming touched this


@dataclass
class MergeDecision:
    """One decision, with enough of its reasoning to be argued with."""

    action: MergeAction
    kind: str
    existing: Milestone | None = None
    incoming: Milestone | None = None
    reason: str = ''

    def describe(self) -> str:
        # The values that were actually compared, not each side's effective date -- for a
        # window against one of its ends those are different, and printing the wrong one
        # makes a correct decision look like a mistake.
        if self.existing is not None and self.incoming is not None:
            left, right = comparable_values(self.existing, self.incoming)
        else:
            left = self.existing.effective_date if self.existing else None
            right = self.incoming.effective_date if self.incoming else None
        return (f'{self.action.value:11} {self.kind:22} '
                f'{left or "—"!s:12} -> {right or "—"!s:12}')


@dataclass
class MergeReport:
    """The merged record, and every decision that produced it."""

    milestones: list[Milestone] = dc_field(default_factory=list)
    decisions: list[MergeDecision] = dc_field(default_factory=list)

    def of(self, action: MergeAction) -> list[MergeDecision]:
        return [d for d in self.decisions if d.action is action]

    @property
    def has_conflicts(self) -> bool:
        return bool(self.of(MergeAction.CONFLICTED))

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out


# ------------------------------------------------------------------- 1. MATCH
#: A window states both ends; a record often stores each end separately. These are the
#: same subject matter at different granularity, so they are allowed to match -- and the
#: comparison below is careful to put the right end against the right end.
_WINDOW_ENDS = {
    'APPLICATION_WINDOW': ('APPLICATION_START', 'APPLICATION_END'),
    'CORRECTION_WINDOW': ('CORRECTION_START', 'CORRECTION_END'),
}


def _kinds_align(a_kind: str, b_kind: str) -> bool:
    if a_kind == b_kind:
        return True
    for window, ends in _WINDOW_ENDS.items():
        if a_kind == window and b_kind in ends:
            return True
        if b_kind == window and a_kind in ends:
            return True
    return False


def comparable_values(a: Milestone, b: Milestone) -> tuple:
    """The two moments to weigh against each other.

    Where one side is a window and the other names a single end, the window's matching end
    is used. Comparing a closing date against an opening date is how the first real merge
    manufactured a disagreement between two values that were never about the same moment.
    """
    for window, (start_kind, end_kind) in _WINDOW_ENDS.items():
        for left, right in ((a, b), (b, a)):
            # Both sides fall back the same way. A window that states only one end still
            # has a moment, and asking one side for a value it does not carry while the
            # other falls back manufactured a difference out of an identical date.
            if left.kind == window and right.kind == start_kind:
                pair = (left.starts_at.value or left.ends_at.value,
                        right.starts_at.value or right.ends_at.value)
                return pair if left is a else tuple(reversed(pair))
            if left.kind == window and right.kind == end_kind:
                pair = (left.ends_at.value or left.starts_at.value,
                        right.ends_at.value or right.starts_at.value)
                return pair if left is a else tuple(reversed(pair))
    return a.effective_date, b.effective_date


def matches(a: Milestone, b: Milestone) -> bool:
    """Are these about the same thing?

    Same kind, same scope, same cycle. Scope is what keeps "Tier II examination" from
    matching "application end" -- and, just as importantly, keeps "Paper I on the 3rd" from
    looking like a contradiction of "Paper II on the 5th". They are two events.
    """
    if not _kinds_align(a.kind, b.kind):
        return False
    if str(a.scope) != str(b.scope):
        return False
    a_cycle, b_cycle = (a.cycle or ''), (b.cycle or '')
    if a_cycle and b_cycle and a_cycle != b_cycle:
        return False
    return True


# ----------------------------------------------------------------- 2/3/4
def _claims_to_revise(incoming: Milestone, source: SourceDocument | None) -> bool:
    """Does this document say it is changing something, rather than merely differing?

    Two ways an authority says so: the wording of the statement itself -- postponed,
    rescheduled, in supersession -- or the document being a corrigendum, which is a document
    whose entire purpose is to correct an earlier one.

    Differing is not revising. A second notice that simply prints a different date is a
    disagreement until something says which came later.
    """
    if incoming.state in (MilestoneState.RESCHEDULED, MilestoneState.POSTPONED,
                          MilestoneState.CANCELLED):
        return True
    return bool(source is not None and source.kind is SourceKind.CORRIGENDUM)


def _same_value(a: Milestone, b: Milestone) -> bool:
    """Do these point at the same moment?

    Only the moments being compared -- not every field. Requiring both ends to agree made a
    record row that stores one end differ from an extracted window that states both, though
    they said exactly the same thing about the end in question.
    """
    left, right = comparable_values(a, b)
    return left == right and left is not None


def _absorb_evidence(keeper: Milestone, other: Milestone) -> None:
    """Add the other reading's evidence, keyed on document as well as wording."""
    for field_name in ('starts_at', 'ends_at'):
        target = getattr(keeper, field_name)
        known = {(e.source_id, e.span_digest) for e in target.evidence}
        for ev in getattr(other, field_name).evidence:
            if (ev.source_id, ev.span_digest) not in known:
                target.evidence.append(ev)


def merge_milestones(existing: list[Milestone], incoming: list[Milestone], *,
                     source: SourceDocument | None = None) -> MergeReport:
    """Fold newly extracted milestones into a record's existing ones.

    The record is the starting point and stays the starting point: nothing is removed, and
    an existing fact that nothing incoming touches comes through untouched.
    """
    report = MergeReport()
    used: set[int] = set()

    for old in existing:
        partner = next((m for m in incoming
                        if id(m) not in used and matches(old, m)), None)
        if partner is None:
            report.milestones.append(old)
            report.decisions.append(MergeDecision(
                MergeAction.UNCHANGED, old.kind, existing=old,
                reason='nothing extracted concerns this'))
            continue
        used.add(id(partner))

        if partner.effective_date is None:
            # Silence is not disagreement. The authority has stated this event without
            # dating it, which adds nothing to a record that already has a date for it.
            report.milestones.append(old)
            report.decisions.append(MergeDecision(
                MergeAction.UNCHANGED, old.kind, existing=old, incoming=partner,
                reason='the official source names this event but gives no date for it, so '
                       'there is nothing to compare against what the record holds'))
            continue

        # 2. CONFIRM
        if _same_value(old, partner):
            _absorb_evidence(old, partner)
            if old.status is not Status.VERIFIED and partner.status is Status.VERIFIED:
                old.status = Status.VERIFIED
            report.milestones.append(old)
            report.decisions.append(MergeDecision(
                MergeAction.CONFIRMED, old.kind, existing=old, incoming=partner,
                reason='an official source states the same value; kept as one fact with '
                       'both sources behind it'))
            continue

        # 3. SUPERSEDE
        if _claims_to_revise(partner, source):
            old.superseded_by = partner.id
            old.note = (old.note + ' ' if old.note else '') + (
                'replaced by a later official document that states it is changing this')
            partner.supersedes = old.id
            if source is not None:
                partner.revision_source_id = source.id
            report.milestones.extend([old, partner])
            report.decisions.append(MergeDecision(
                MergeAction.SUPERSEDED, old.kind, existing=old, incoming=partner,
                reason='the incoming document says it revises this; the old value is kept '
                       'and marked superseded rather than deleted'))
            continue

        # 4. REFUSE
        note = (f'two official readings disagree — the record holds '
                f'{old.effective_date}, an official source states '
                f'{partner.effective_date}, and neither says it is correcting the other. '
                f'Both are kept and neither is published as effective until a person '
                f'resolves it against the documents.')
        old.status = Status.NEEDS_REVIEW
        old.note = (old.note + ' ' if old.note else '') + note
        partner.status = Status.NEEDS_REVIEW
        partner.note = (partner.note + ' ' if partner.note else '') + note
        report.milestones.extend([old, partner])
        report.decisions.append(MergeDecision(
            MergeAction.CONFLICTED, old.kind, existing=old, incoming=partner, reason=note))

    # 1. MATCH found nothing: genuinely new information.
    for new in incoming:
        if id(new) in used:
            continue
        report.milestones.append(new)
        report.decisions.append(MergeDecision(
            MergeAction.ADDED, new.kind, incoming=new,
            reason='the record held nothing about this event'))

    report.milestones.sort(key=lambda m: (m.effective_date or '9999', m.kind))
    return report
