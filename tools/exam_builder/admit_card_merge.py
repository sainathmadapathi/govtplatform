"""Merge admit-card events — and refuse anything whose identity is not exact.

The four operations -- ADDED, CONFIRMED, SUPERSEDED, CONFLICTED -- with the identity that
decides them stated first, because here it is four things and not one: **the exam, the
cycle, the kind, and the stage**. Two events are the same event only when all four agree.

That is not pedantry. The audit found the existing record naming one SSC milestone
"Tier 1 City Intimation Slip & Admit Card Release", which is two documents on two dates
merged into one label. A merge that treats the city intimation and the admit card as one
event reproduces that defect at the data layer, where it is much harder to see:

  * **a city intimation is never an admit card**, whatever dates they share;
  * **one stage's call letter is never another's** — a Preliminary call letter released in
    August says nothing about the Main call letter in September;
  * **one cycle's admit card is never another's**, which is the refusal that keeps a 2024
    notice out of a 2025 record;
  * and **two authorities' events never meet at all**.

Where identity does match, a later event supersedes an earlier one *and keeps it*, because a
rescheduled admit card is a corrigendum a candidate should be able to see rather than a
silent overwrite. Where two events with the same identity carry different dates and neither
claims to revise the other, both are kept and the merge refuses to choose.
"""
from __future__ import annotations

from .merge import MergeAction
from .schema import AdmitCardNotice, Status


class EventDecision:
    """What the merge decided about one admit-card event, and why."""

    def __init__(self, action: MergeAction, label: str, event_id: str = '',
                 reason: str = '', superseded: str = '') -> None:
        self.action = action
        self.label = label
        self.event_id = event_id
        self.reason = reason
        self.superseded = superseded

    def describe(self) -> str:
        bits = [f'{self.action.value}: {self.label}']
        if self.superseded:
            bits.append(f'supersedes {self.superseded}')
        if self.reason:
            bits.append(self.reason)
        return ' · '.join(bits)


class AdmitCardMergeReport:
    def __init__(self) -> None:
        self.decisions: list[EventDecision] = []
        self.events: list[AdmitCardNotice] = []

    def of(self, action: MergeAction) -> list:
        return [d for d in self.decisions if d.action is action]

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out


def _stage_key(event: AdmitCardNotice) -> str:
    refs = [r for r in event.scope.refs if r.kind.value == 'STAGE']
    return (refs[0].ref or refs[0].label).lower() if refs else ''


def identity_key(event: AdmitCardNotice, exam_id: str) -> tuple:
    """The four things that have to agree before two events are one event."""
    return (exam_id, (event.cycle or '').strip(), event.kind.value, _stage_key(event))


def same_event(left: AdmitCardNotice, right: AdmitCardNotice, *, exam_id: str) -> bool:
    return identity_key(left, exam_id) == identity_key(right, exam_id)


def _value(event: AdmitCardNotice) -> str:
    return event.released_at.value or event.release_rule.value or ''


def _revises(incoming: AdmitCardNotice, existing: AdmitCardNotice) -> bool:
    """Does the incoming event say it replaces this one?

    Either it names it outright, or its source is later and says so in its own words. A
    later *reading* of the same document is not a revision -- that is a re-run, and it
    CONFIRMs.
    """
    if incoming.supersedes and incoming.supersedes == existing.id:
        return True
    later = [e.published_at for e in incoming.evidence if e.published_at]
    earlier = [e.published_at for e in existing.evidence if e.published_at]
    return bool(later and earlier and max(later) > max(earlier))


def _absorb(keeper: AdmitCardNotice, other: AdmitCardNotice) -> None:
    """Keep the other document's evidence, so a corroborated event looks corroborated."""
    seen = {(e.source_id, e.span_digest) for e in keeper.evidence}
    for ev in other.evidence:
        if (ev.source_id, ev.span_digest) not in seen:
            keeper.evidence.append(ev)
    if not keeper.official_label and other.official_label:
        keeper.official_label = other.official_label


def merge_admit_card_events(existing: list, incoming: list, *,
                            exam_id: str) -> AdmitCardMergeReport:
    """Fold newly read events into a record's own, field by field where they agree.

    Nothing an authored record holds is overwritten by a reader. An incoming event that
    matches an authored one CONFIRMs it and lends it evidence; one that genuinely revises it
    SUPERSEDEs it and the superseded event is kept; one whose identity matches nothing is
    added; and two that disagree with no stated relationship are CONFLICTED, which keeps
    both and settles neither.
    """
    report = AdmitCardMergeReport()
    out = list(existing)

    for event in incoming:
        label = f'{event.kind.value} {event.official_label or ""}'.strip()
        if event.status is Status.NOT_EXTRACTED:
            report.decisions.append(EventDecision(
                MergeAction.CONFLICTED, label, event.id,
                'nothing was extracted for this event; a gap in GovOS is not a fact'))
            continue
        twins = [e for e in out if same_event(e, event, exam_id=exam_id)]
        if not twins:
            out.append(event)
            report.decisions.append(EventDecision(MergeAction.ADDED, label, event.id))
            continue
        twin = twins[0]
        if _value(twin) == _value(event):
            _absorb(twin, event)
            report.decisions.append(EventDecision(
                MergeAction.CONFIRMED, label, twin.id,
                'a second source states the same release'))
            continue
        if _revises(event, twin):
            twin.status = Status.NEEDS_REVIEW
            twin.note = (twin.note + ' ' if twin.note else '') + (
                f'superseded by {event.id}: the authority published '
                f'{_value(event)} in a later document')
            event.supersedes = twin.id
            out.append(event)
            report.decisions.append(EventDecision(
                MergeAction.SUPERSEDED, label, event.id, superseded=twin.id,
                reason=f'{_value(twin)} → {_value(event)}'))
            continue
        # Two documents, one identity, two different dates, and neither claims to revise the
        # other. GovOS cannot decide which the authority means, so it decides nothing and
        # keeps both for a person.
        event.status = Status.NEEDS_REVIEW
        event.note = (f'this conflicts with {twin.id}, which states {_value(twin)}; '
                      f'neither document claims to revise the other, so both are kept and '
                      f'neither is shown as settled')
        out.append(event)
        report.decisions.append(EventDecision(
            MergeAction.CONFLICTED, label, event.id,
            f'conflicts with {twin.id} ({_value(twin)} vs {_value(event)}) and neither '
            f'revises the other'))

    report.events = out
    return report
