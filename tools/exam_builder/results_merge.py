"""Merge result declarations — and never overwrite a result's history.

The four operations again — ADDED, CONFIRMED, SUPERSEDED, CONFLICTED — with the identity that
decides them: **exam, cycle, kind, stage, and post**. Two declarations are the same
declaration only when all of those agree, which is what keeps a Preliminary written result
apart from a Final result, a 2025 result apart from a 2026 one, and one authority's result
apart from another's.

The one thing this merge does that the admit-card merge does not is carry a *lifecycle*. A
result can be revised or cancelled, and §13/§16 forbid a silent overwrite: an official
revision SUPERSEDES the earlier declaration and keeps it, marking the earlier one SUPERSEDED
and the later one REVISED, with the relationship addressable through `supersedes`. A
cancellation is a revision whose later state is CANCELLED. Where two declarations disagree
with no revision stated between them, both are kept and neither is settled — the newest
timestamp does not win, because a result is exactly the kind of fact where a later scrape of
a stale mirror must not overturn an earlier authoritative read.
"""
from __future__ import annotations

from .merge import MergeAction
from .schema import ResultDeclaration, ResultKind, ResultLifecycle, Status


class ResultDecision:
    """What the merge decided about one declaration, and why."""

    def __init__(self, action: MergeAction, label: str, result_id: str = '',
                 reason: str = '', superseded: str = '') -> None:
        self.action = action
        self.label = label
        self.result_id = result_id
        self.reason = reason
        self.superseded = superseded

    def describe(self) -> str:
        bits = [f'{self.action.value}: {self.label}']
        if self.superseded:
            bits.append(f'supersedes {self.superseded}')
        if self.reason:
            bits.append(self.reason)
        return ' · '.join(bits)


class ResultMergeReport:
    def __init__(self) -> None:
        self.decisions: list[ResultDecision] = []
        self.results: list[ResultDeclaration] = []

    def of(self, action: MergeAction) -> list:
        return [d for d in self.decisions if d.action is action]

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out


def _stage_key(event: ResultDeclaration) -> str:
    refs = [r for r in event.scope.refs if r.kind.value == 'STAGE']
    return (refs[0].ref or refs[0].label).lower() if refs else ''


def _post_key(event: ResultDeclaration) -> str:
    refs = [r for r in event.scope.refs if r.kind.value == 'POST']
    return (refs[0].ref or refs[0].label).lower() if refs else ''


import re as _re


def _doc_variant(event: ResultDeclaration) -> str:
    """A document's own basename with dates stripped, or ''.

    UPSC's Preliminary written result is published as a roll-number list and then a name
    list -- two distinct official documents of one result. Keyed without this they collided
    and the second was mislabelled a conflict. With it, two different documents are both
    added and a re-read of the *same* document still confirms. A declaration with no document
    (an SSC board notice) has '' here, so notices merge and conflict on stage and cycle
    exactly as before.
    """
    url = event.document_url.value or ''
    if not url:
        return ''
    base = url.rsplit('/', 1)[-1].lower()
    return _re.sub(r'\d+', '', base)


def identity_key(event: ResultDeclaration, exam_id: str) -> tuple:
    """The things that have to agree before two declarations are one declaration."""
    return (exam_id, (event.cycle or '').strip(), event.kind.value,
            _stage_key(event), _post_key(event), _doc_variant(event))


def same_result(a: ResultDeclaration, b: ResultDeclaration, *, exam_id: str) -> bool:
    return identity_key(a, exam_id) == identity_key(b, exam_id)


def _value(event: ResultDeclaration) -> str:
    return event.published_at.value or event.expected_at.value or ''


def _cancels(event: ResultDeclaration) -> bool:
    return bool(event.note and 'cancel' in event.note.lower()) \
        or event.lifecycle is ResultLifecycle.CANCELLED


def _revises(incoming: ResultDeclaration, existing: ResultDeclaration) -> bool:
    """Does the incoming declaration say it replaces this one?

    Either it names it outright (`supersedes`), or it is marked REVISED/CANCELLED, or its
    source document is later than the existing one's. A later *reading* of the same document
    is not a revision — that CONFIRMs.
    """
    if incoming.supersedes and incoming.supersedes == existing.id:
        return True
    if incoming.lifecycle in (ResultLifecycle.REVISED, ResultLifecycle.CANCELLED):
        return True
    later = [e.published_at for e in incoming.evidence if e.published_at]
    earlier = [e.published_at for e in existing.evidence if e.published_at]
    return bool(later and earlier and max(later) > max(earlier))


def _absorb(keeper: ResultDeclaration, other: ResultDeclaration) -> None:
    seen = {(e.source_id, e.span_digest) for e in keeper.evidence}
    for ev in other.evidence:
        if (ev.source_id, ev.span_digest) not in seen:
            keeper.evidence.append(ev)
    if not keeper.label and other.label:
        keeper.label = other.label


def merge_results(existing: list, incoming: list, *, exam_id: str) -> ResultMergeReport:
    """Fold newly read declarations into a record's own, never overwriting authored history.

    An incoming declaration that matches an authored one CONFIRMs it; one that genuinely
    revises or cancels it SUPERSEDEs it and the earlier one is kept and marked; one whose
    identity matches nothing is ADDED; and two that disagree with no revision between them are
    CONFLICTED, which keeps both and settles neither.
    """
    report = ResultMergeReport()
    out = list(existing)

    for event in incoming:
        label = f'{event.kind.value} {event.label or ""}'.strip()
        if event.status is Status.NOT_EXTRACTED:
            report.decisions.append(ResultDecision(
                MergeAction.CONFLICTED, label, event.id,
                'nothing was extracted for this declaration; a gap in GovOS is not a fact'))
            continue
        twins = [e for e in out if same_result(e, event, exam_id=exam_id)]
        if not twins:
            out.append(event)
            report.decisions.append(ResultDecision(MergeAction.ADDED, label, event.id))
            continue
        twin = twins[0]
        if _value(twin) == _value(event) and not _cancels(event):
            _absorb(twin, event)
            report.decisions.append(ResultDecision(
                MergeAction.CONFIRMED, label, twin.id,
                'a second source states the same declaration'))
            continue
        if _revises(event, twin):
            twin.lifecycle = ResultLifecycle.SUPERSEDED
            twin.status = Status.NEEDS_REVIEW
            action = 'cancelled' if _cancels(event) else 'revised'
            twin.note = (twin.note + ' ' if twin.note else '') + (
                f'{action} by {event.id}: the authority published a later declaration')
            event.supersedes = twin.id
            event.lifecycle = (ResultLifecycle.CANCELLED if _cancels(event)
                               else ResultLifecycle.REVISED)
            out.append(event)
            report.decisions.append(ResultDecision(
                MergeAction.SUPERSEDED, label, event.id, superseded=twin.id,
                reason=f'{_value(twin) or twin.lifecycle.value} → '
                       f'{_value(event) or event.lifecycle.value}'))
            continue
        event.status = Status.NEEDS_REVIEW
        event.note = (f'this conflicts with {twin.id}, which states {_value(twin)}; neither '
                      f'document claims to revise the other, so both are kept and neither is '
                      f'shown as settled')
        out.append(event)
        report.decisions.append(ResultDecision(
            MergeAction.CONFLICTED, label, event.id,
            f'conflicts with {twin.id} and neither revises the other'))

    report.results = out
    return report
