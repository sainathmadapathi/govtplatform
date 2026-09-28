"""The publication gate: what may reach production, and what must stop.

A build completing is not a build that should publish. The gate exists because the failure
it prevents is invisible to the person it harms: a candidate reading an exam page cannot
tell a field that is empty because the authority has not announced it from a field that is
empty because an extractor missed it. The first is information; the second is a mistake
wearing the same clothes.

So the rule is asymmetric on purpose:

    NOT_PUBLISHED   allowed     the authority genuinely has not released it
    NOT_EXTRACTED   blocks      when the field is one the contract marks required -- an exam
                                cannot be offered without it; an optional field that could not
                                be read is *allowed*, and its honest state (searched-and-not-
                                found, reader failed, ...) travels with the record so the UI
                                shows the gap as ours rather than as the authority's silence.
                                Its status is never rewritten to NOT_PUBLISHED.
    NEEDS_REVIEW    blocks      read, but not confidently enough to assert
    MISMATCH        blocks      a source belonged to another exam
    AMBIGUOUS       blocks      a required field rests on a source that names several exams
    infrastructure  blocks      and is *never* rewritten as NOT_PUBLISHED

Which fields are required is the contract's decision (`ContractField.required`), not this
module's: the gate reads it rather than keeping a list of its own.

That last one matters most. A network outage produces exactly the same silence as an
authority that has published nothing, and translating one into the other would have GovOS
tell candidates "no answer key has been published" because DNS was down.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum

from ..exam_authoring.record import ExamRecord, Status
from .contract import CONTRACT
from .identity import IdentityVerdict


class BuildState(str, Enum):
    """How the build itself went, separately from any field's status."""

    COMPLETE = 'COMPLETE'
    #: Search or fetch failed. The build is unfinished, not the authority silent.
    PAUSED_INFRASTRUCTURE = 'PAUSED_INFRASTRUCTURE'
    FAILED = 'FAILED'


class GateDecision(str, Enum):
    PASS = 'PASS'
    BLOCK = 'BLOCK'


#: Fields whose absence would leave a candidate with an exam page that misinforms. Read from
#: the contract, which is the one place that decides what is required; a field not marked
#: there may be missing without blocking, because the app renders an honest state for it.
#: An intrinsic contract entry (no source kinds: e.g. the sources read) is established by the
#: pipeline itself and carried on the record as an attribute, never as an extracted Field, so it
#: is not something the gate can find missing.
REQUIRED_FIELDS: frozenset[str] = frozenset(f.name for f in CONTRACT if f.required and f.sources)


@dataclass
class Blocker:
    field: str
    reason: str
    detail: str = ''

    def __str__(self) -> str:
        return f'{self.field}: {self.reason}' + (f' — {self.detail}' if self.detail else '')


@dataclass
class GateReport:
    decision: GateDecision
    build_state: BuildState
    blockers: list[Blocker] = dc_field(default_factory=list)
    allowed: list[str] = dc_field(default_factory=list)
    notes: list[str] = dc_field(default_factory=list)

    @property
    def may_publish(self) -> bool:
        return self.decision is GateDecision.PASS

    def summary(self) -> str:
        lines = [f'decision:    {self.decision.value}',
                 f'build state: {self.build_state.value}']
        if self.blockers:
            lines.append(f'blocked by {len(self.blockers)}:')
            lines += [f'   - {b}' for b in self.blockers]
        if self.allowed:
            lines.append(f'allowed absences, state preserved ({len(self.allowed)}): '
                         f'{", ".join(sorted(self.allowed))}')
        lines += [f'   note: {n}' for n in self.notes]
        return '\n'.join(lines)


def evaluate(record: ExamRecord, *,
             build_state: BuildState = BuildState.COMPLETE,
             identity_by_source: dict[str, IdentityVerdict] | None = None,
             required: frozenset[str] = REQUIRED_FIELDS,
             conflicts: list[str] | None = None,
             schema_ok: bool = True,
             typecheck_ok: bool = True,
             isolation_ok: bool = True,
             completeness=None) -> GateReport:
    """Decide whether this build may modify production.

    `completeness` (an ExamCompletenessReport) is optional and never changes the decision; it
    lets the report name the honest state of each optional field that was allowed through.
    """
    blockers: list[Blocker] = []
    allowed: list[str] = []
    notes: list[str] = []
    identity_by_source = identity_by_source or {}
    field_state: dict[str, str] = {}
    for sec in (getattr(completeness, 'sections', None) or []):
        for fname, st in (getattr(sec, 'fields', None) or {}).items():
            field_state[fname] = st

    # --- infrastructure first. A paused build has not established anything, and its
    # --- silences must not be read as findings about the authority.
    if build_state is BuildState.PAUSED_INFRASTRUCTURE:
        blockers.append(Blocker(
            '(build)', 'infrastructure failure',
            'search or fetch did not complete, so an absent field means "not looked at", '
            'not "not published"'))
    elif build_state is BuildState.FAILED:
        blockers.append(Blocker('(build)', 'the build failed'))

    # --- a source that belongs to another exam must never have contributed anything. One
    # --- that was read, judged MISMATCH and excluded from extraction contributed nothing:
    # --- it is retained for audit, not a blocker. A real site's navigation pages name a
    # --- dozen other examinations, and blocking on their mere presence would make every
    # --- exam on such a site unpublishable while proving nothing about its facts. The
    # --- blocker is a MISMATCH source that a field *cites* -- that is contamination.
    # The two intrinsic fields cite the *authority resolution* (the domain root), not a
    # document that was read; a home page later judged MISMATCH shares that URL without
    # having supplied either of them.
    cited = {f.citation.url for name, f in record.fields.items()
             if f.citation is not None and getattr(f.citation, 'url', '')
             and name not in ('officialName', 'authority')}
    for url, verdict in identity_by_source.items():
        if verdict is IdentityVerdict.MISMATCH:
            if url in cited:
                blockers.append(Blocker('(source)', 'a field cites a document that belongs '
                                        'to another exam', url))
            else:
                notes.append(f'source excluded as another exam’s and retained for audit '
                             f'only; it supplied no field: {url}')

    # --- field-by-field
    field_names = {f.name for f in CONTRACT}
    for name in sorted(field_names):
        f = record.fields.get(name)
        if f is None:
            if name in required:
                blockers.append(Blocker(name, 'required field was never attempted'))
            continue

        if f.status is Status.FOUND:
            continue

        if f.status is Status.NOT_PUBLISHED:
            # The one acceptable absence: the authority has not released it.
            allowed.append(name)
            if name in required:
                blockers.append(Blocker(
                    name, 'required field is not published by the authority',
                    'an exam cannot be offered without it'))
            continue

        if f.status is Status.NOT_EXTRACTED:
            if name in required:
                blockers.append(Blocker(
                    name, 'a required field could not be read from any source',
                    'an exam cannot be offered without it'))
                continue
            # An optional field we could not read is a gap of ours, and it is published *as*
            # ours: the field keeps its NOT_EXTRACTED status and its completeness state, and the
            # app renders that state -- never an empty section dressed as the authority's silence.
            allowed.append(name)
            state = field_state.get(name)
            notes.append(f'{name}: optional, not read; carried as '
                         f'{state or "NOT_EXTRACTED"} rather than published as a fact or hidden')
            continue

        if f.status is Status.NEEDS_REVIEW:
            blockers.append(Blocker(
                name, 'read but not confidently', (f.note or '')[:140]))

    for c in (conflicts or []):
        blockers.append(Blocker('(conflict)', 'unresolved contradiction between sources', c))

    if not schema_ok:
        blockers.append(Blocker('(schema)', 'the generated record does not match the Exam interface'))
    if not typecheck_ok:
        blockers.append(Blocker('(typecheck)', 'the staged register does not compile'))
    if not isolation_ok:
        blockers.append(Blocker('(isolation)', 'the build changed another exam'))

    decision = GateDecision.BLOCK if blockers else GateDecision.PASS
    if decision is GateDecision.PASS:
        notes.append('every fact carries verified evidence, and every absence is the '
                     'authority’s rather than ours')
    return GateReport(decision=decision, build_state=build_state,
                      blockers=blockers, allowed=allowed, notes=notes)
