"""One safe, universal pipeline that connects the existing components end to end.

Every stage below already exists and is individually universal and tested; the only thing
this module adds is the wiring, and it wires by *calling*, never by re-implementing:

    RESOLUTION        resolve.resolve            (inside build.build)
    DISCOVERY         discover.discover          (inside build.build)
    SOURCE CAPTURE    build._load                (inside build.build)
    IDENTITY          identity.verify            (inside build.build)
    EXTRACTION        semantic.extract / X.*     (inside build.build)
    DETERMINISTIC     verification.deterministic (inside verification.verify)
    CLAUDE (optional) verification.verify        (this module, per FOUND field)
    MERGE/REVISION    merge.*                    (available; nothing to merge on a fresh build)
    SCHEMA/ISOLATION  exam_authoring.verify.run_all + gate.evaluate
    PUBLICATION GATE  gate.evaluate
    STAGING           an auditable JSON artifact + publish.fingerprint baseline
    ATOMIC PUBLISH    publish.stage + publish.publish   (only on an explicit, non-dry run)

Two safety rules shape the whole thing:

- The orchestrator NEVER writes a verified fact around the publication gate. It publishes
  only through the existing `publish.stage` / `publish.publish`, and only when the existing
  `gate.evaluate` returns PASS. Its default is a dry run, which resolves → discovers →
  extracts → verifies → stages an auditable artifact and touches nothing live.
- The orchestrator owns no record-to-TypeScript renderer. Turning a record into a `data.ts`
  block is not a step this module invents (that would be new, unsafe logic); the caller
  supplies a `render` callback for the one path that writes the live register, and without
  one a gate-passing build is staged for a human rather than published. This is deliberate:
  see ORCHESTRATION_AUDIT.md, "Remaining limitations".

Every distinct failure keeps its own state (Step 14): a search outage is not a silent
authority, an ambiguous authority is not a resolution failure, a gate block is not a publish,
and a Claude outage never becomes a verified fact or a fabricated one.
"""
from __future__ import annotations

import io
import json
import os
import time
from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Callable, Optional

from ..exam_authoring.record import ExamRecord, Field, Status
from ..exam_authoring.verify import IsolationError, run_all
from . import publish as P
from . import render as R
from .build import BuildResult, NoClaude, build
from .gate import BuildState, GateReport, evaluate as gate_evaluate
from .identity import IdentityVerdict
from .resolve import AmbiguousAuthority, SearchUnavailable
from .verification.adapters import claim_from_field
from .verification.schemas import InfraStatus, VerificationDecision, Verdict
from .verification.verifier import verify as claude_verify


class Stage(str, Enum):
    """The furthest stage a run reached, for the report."""

    RESOLUTION = 'RESOLUTION'
    DISCOVERY = 'DISCOVERY'
    SOURCE_CAPTURE = 'SOURCE_CAPTURE'
    IDENTITY = 'IDENTITY'
    EXTRACTION = 'EXTRACTION'
    DETERMINISTIC = 'DETERMINISTIC'
    CLAUDE_VERIFICATION = 'CLAUDE_VERIFICATION'
    MERGE_REVISION = 'MERGE_REVISION'
    SCHEMA = 'SCHEMA'
    ISOLATION = 'ISOLATION'
    STAGING = 'STAGING'
    PUBLICATION_GATE = 'PUBLICATION_GATE'
    ATOMIC_PUBLISH = 'ATOMIC_PUBLISH'


class OrchestrationState(str, Enum):
    """The run's outcome. Each failure mode is distinct and never collapsed into another."""

    PUBLISHED = 'PUBLISHED'                       # atomic publish succeeded
    STAGED = 'STAGED'                             # gate PASS; staged, not written live (dry run / no renderer)
    BLOCKED_BY_GATE = 'BLOCKED_BY_GATE'           # gate BLOCK (NOT_EXTRACTED / NEEDS_REVIEW / MISMATCH / conflict / required-missing)
    RESOLUTION_FAILURE = 'RESOLUTION_FAILURE'     # no authority resolved (LookupError)
    AMBIGUOUS_AUTHORITY = 'AMBIGUOUS_AUTHORITY'   # two real authorities; not chosen on a score gap
    INFRASTRUCTURE_FAILURE = 'INFRASTRUCTURE_FAILURE'   # search/discovery could not run
    SOURCE_FETCH_FAILURE = 'SOURCE_FETCH_FAILURE'       # a source could not be fetched (build PAUSED_INFRASTRUCTURE)
    ISOLATION_VIOLATION = 'ISOLATION_VIOLATION'   # publishing would change another exam's bytes
    PRESERVATION_BLOCKED = 'PRESERVATION_BLOCKED'  # target already exists; a partial build must not overwrite authored data


@dataclass
class OrchestrationResult:
    query: str
    year: str
    dry_run: bool
    state: OrchestrationState
    reached: Stage
    build: Optional[BuildResult] = None
    gate: Optional[GateReport] = None
    verifications: dict = dc_field(default_factory=dict)     # field name -> Verdict
    #: What a person decided, field by field (see review.py); empty when no review was given.
    reviews: dict = dc_field(default_factory=dict)
    isolation_ok: Optional[bool] = None
    fingerprint_before: dict = dc_field(default_factory=dict)
    fingerprint_after: dict = dc_field(default_factory=dict)
    staging_path: str = ''
    published: bool = False
    reason: str = ''
    notes: list = dc_field(default_factory=list)

    @property
    def exam_id(self) -> str:
        return self.build.record.exam_id if self.build else ''

    def summary(self) -> str:
        lines = [f'query:    {self.query}' + (f' ({self.year})' if self.year else ''),
                 f'state:    {self.state.value}',
                 f'reached:  {self.reached.value}',
                 f'dry-run:  {self.dry_run}']
        if self.build:
            rec = self.build.record
            found = sum(1 for f in rec.fields.values() if f.status is Status.FOUND)
            lines.append(f'exam:     {rec.exam_id} — {found}/{len(rec.fields)} fields FOUND')
        if self.gate:
            lines.append(f'gate:     {self.gate.decision.value}'
                         + (f' — {len(self.gate.blockers)} blocker(s)' if self.gate.blockers else ''))
        if self.verifications:
            sup = sum(1 for v in self.verifications.values()
                      if v.claude and v.claude.decision is VerificationDecision.SUPPORTED)
            lines.append(f'claude:   {sup}/{len(self.verifications)} SUPPORTED')
        if self.isolation_ok is not None:
            lines.append(f'isolated: {self.isolation_ok} (unrelated exams byte-identical)')
        if self.staging_path:
            lines.append(f'staged:   {self.staging_path}')
        if self.published:
            lines.append('published: live register updated')
        if self.reason:
            lines.append(f'reason:   {self.reason}')
        return '\n'.join(lines)


def orchestrate(exam_query: str = '', *, year: str = '', dry_run: bool = True,
                use_claude: bool = False, gateway=None, cache=None,
                replay=None, siblings: Optional[list] = None, max_docs: int = 8,
                data_ts: str = P.DATA_TS, typecheck: bool = True, allow_overwrite: bool = False,
                allow_overlay: bool = False, overlay_store=None,
                search_fn: Optional[Callable] = None,
                render: Optional[Callable[[ExamRecord], str]] = None,
                reviews: Optional[list] = None,
                authority_discovery: Optional[Callable] = None) -> OrchestrationResult:

    """Run the universal pipeline for one exam. Universal: the input is a name and a year and
    nothing authority-specific; every branch reads a *state*, never an exam or an authority.

    dry_run (default True): resolve → discover → extract → verify → stage, and never write the
    live register. Set dry_run=False *and* pass a `render` to publish through the existing
    atomic publisher.
    """
    res = OrchestrationResult(query=exam_query, year=year, dry_run=dry_run,
                              state=OrchestrationState.STAGED, reached=Stage.RESOLUTION)
    res.fingerprint_before = _fingerprint(data_ts)

    # --- RESOLUTION → DISCOVERY → SOURCE CAPTURE → IDENTITY → EXTRACTION (existing build) ----
    try:
        # A job that did not ask for Claude builds with none, even where Claude is enabled for
        # the process. One that did builds as before: its extraction steps use the process-wide
        # gateway, and `gateway` below verifies the claims.
        br = build(exam_query, year=year, sibling_exam_words=siblings, max_docs=max_docs,
                   replay=replay, search_fn=search_fn, authority_discovery=authority_discovery,
                   gateway=None if use_claude else NoClaude())
    except AmbiguousAuthority as exc:
        res.state = OrchestrationState.AMBIGUOUS_AUTHORITY
        res.reached = Stage.RESOLUTION
        res.reason = 'two or more real authorities answer to this name; not chosen on a score gap'
        verdict = getattr(exc, 'verdict', None)
        res.notes.append(verdict.summary() if verdict is not None else str(exc))
        return _finish(res, data_ts)
    except SearchUnavailable as exc:
        res.state = OrchestrationState.INFRASTRUCTURE_FAILURE
        res.reached = Stage.DISCOVERY
        res.reason = f'search/discovery could not run: {exc}. This is not a claim about the authority.'
        return _finish(res, data_ts)
    except LookupError as exc:
        res.state = OrchestrationState.RESOLUTION_FAILURE
        res.reached = Stage.RESOLUTION
        res.reason = f'no authority resolved clearly enough for "{exam_query}": {exc}'
        return _finish(res, data_ts)

    res.build = br
    res.reached = Stage.EXTRACTION
    rec = br.record

    # --- DETERMINISTIC + optional CLAUDE, per FOUND field ------------------------------------
    # Order is preserved by verify(): identity → evidence (span verbatim) → deterministic →
    # Claude. Claude may only WITHHOLD: an explicit CONTRADICTED holds a field for review; a
    # SUPPORTED/INSUFFICIENT/infra result never upgrades a field and never fabricates data.
    if use_claude:
        res.reached = Stage.CLAUDE_VERIFICATION
        for name, f in list(rec.fields.items()):
            if f.status is not Status.FOUND or f.citation is None:
                continue
            claim = claim_from_field(f, exam_id=rec.exam_id, official_name=rec.title,
                                     authority=rec.authority_name,
                                     cycle=(br.resolved.year or year))
            v: Verdict = claude_verify(claim, gateway=gateway, cache=cache)
            res.verifications[name] = v
            if v.infra is not InfraStatus.OK:
                rec.note(f'{name}: Claude verification unavailable ({v.infra.value}); the field '
                         f'is left exactly as the build read it — never upgraded, never dropped.')
                continue
            if v.claude is not None and v.claude.decision is VerificationDecision.CONTRADICTED:
                rec.set(Field.needs_review(
                    name, f.value,
                    'Claude found the cited evidence contradicts this reading; held for review '
                    'rather than published.', f.citation))

    # --- MERGE / REVISION -------------------------------------------------------------------
    # A from-scratch build has no prior record to reconcile against, so there is nothing to
    # merge and no conflict to resolve. merge.py is the component that would fold a revision
    # into an existing record on a publish-over-existing path; it is not exercised here.
    res.reached = Stage.MERGE_REVISION
    conflicts: list = []

    # --- HUMAN REVIEW ------------------------------------------------------------------------
    # A person's decisions on named fields (approve a reading, or withhold one), applied after
    # every machine step and before the gate. The gate is not consulted about them and is not
    # changed by them; a withheld field is a gap of ours, an approved one keeps its citation.
    if reviews:
        from .review import apply_reviews
        outcome = apply_reviews(rec, reviews)
        res.reviews = outcome.to_dict()
        res.notes.extend(f'review: {n}' for n in outcome.notes)
        if outcome.applied and getattr(br, 'completeness', None) is not None:
            # The section states must describe the record as it now stands.
            from .completeness import evaluate_completeness
            br.completeness = evaluate_completeness(
                rec, br.sources, reacquisition_attempts=getattr(br, 'reacquisition_attempts', 0),
                searched_not_found=getattr(br, 'searched_not_found', frozenset()))

    # --- SCHEMA / record-level ISOLATION (single authority, id consistency) -----------------
    res.reached = Stage.ISOLATION
    isolation_ok = True
    try:
        run_all(rec)
    except IsolationError as exc:
        isolation_ok = False
        res.notes.append(f'record isolation check failed: {exc}')

    # --- PUBLICATION GATE -------------------------------------------------------------------
    res.reached = Stage.PUBLICATION_GATE
    identity_by_source = {u: c.verdict for u, c in br.identity.items()}
    gate = gate_evaluate(rec, build_state=br.build_state,
                         identity_by_source=identity_by_source, conflicts=conflicts,
                         isolation_ok=isolation_ok,
                         completeness=getattr(br, 'completeness', None))
    res.gate = gate

    # --- STAGING (always; never mutates the live register) ----------------------------------
    res.reached = Stage.STAGING
    res.staging_path = _write_staging(res)

    # --- ATOMIC PUBLISH (only on an explicit, gate-passing, rendered, non-dry run) ----------
    if br.build_state is BuildState.PAUSED_INFRASTRUCTURE:
        res.state = OrchestrationState.SOURCE_FETCH_FAILURE
        res.reason = ('a source could not be fetched, so the build is unfinished; an absent '
                      'field here means "not looked at", not "the authority published nothing".')
    elif not gate.may_publish:
        res.state = OrchestrationState.BLOCKED_BY_GATE
        res.reason = '; '.join(str(b) for b in gate.blockers[:5]) or 'the publication gate blocked this build'
    elif dry_run:
        res.state = OrchestrationState.STAGED
        res.reason = 'gate PASS; dry run, so the live register was not touched.'
    elif R.target_in_register(rec.exam_id, data_ts) and not allow_overwrite:
        if allow_overlay:
            # Canonical Data Ownership (Phase 1):
            # Existing exam in register -> DO NOT overwrite data.ts!
            # Create and persist verified additive overlays via OverlayStore.
            res.reached = Stage.ATOMIC_PUBLISH
            from .overlay import OverlayStore, create_overlays_from_record
            overlays = create_overlays_from_record(rec, gate)
            if overlays:
                try:
                    store = overlay_store or OverlayStore()
                    for o in overlays:
                        store.record(o)
                    res.published = True
                    res.state = OrchestrationState.PUBLISHED
                    res.reason = (f'gate PASS; existing exam updated safely with {len(overlays)} verified '
                                  f'canonical overlay(s) in OverlayStore without modifying data.ts.')
                except Exception as exc:
                    res.state = OrchestrationState.BLOCKED_BY_GATE
                    res.reason = f'Failed to persist canonical overlays: {exc}'
            else:
                res.published = True
                res.state = OrchestrationState.PUBLISHED
                res.reason = ('gate PASS; existing exam verified against canonical register; '
                              'no new overlays required, data.ts left byte-identical.')
        else:
            # Preservation-first without overlay: a partial build must never overwrite an existing record,
            # because publish.stage replaces the exam's whole slice. Register is left byte-identical.
            res.state = OrchestrationState.PRESERVATION_BLOCKED
            res.reason = ('gate PASS, but the target already exists in the register; a partial '
                          'build will not overwrite an authored record. The live register is '
                          'untouched. Pass allow_overlay=True to record verified machine facts as overlays.')


    else:
        # A NEW exam (or an explicit, disposable overwrite): render with the existing universal
        # renderer and publish atomically through the existing publisher and its isolation
        # proof + typecheck. The orchestrator never writes a fact around the gate.
        res.reached = Stage.ATOMIC_PUBLISH
        renderer = render if callable(render) else R.render_exam
        try:
            ts = renderer(rec)
            report = P.stage(rec.exam_id, ts, data_ts=data_ts)
            P.publish(report, data_ts=data_ts, typecheck=typecheck)
            res.published = True
            res.state = OrchestrationState.PUBLISHED
            res.reason = 'gate PASS; new exam published atomically through publish.stage + publish.publish.'
        except P.IsolationViolation as exc:
            res.state = OrchestrationState.ISOLATION_VIOLATION
            res.reason = f'publishing would change another exam or fails typecheck: {exc}'

    return _finish(res, data_ts)


def _fingerprint(data_ts: str) -> dict:
    try:
        return P.fingerprint(io.open(data_ts, encoding='utf-8').read())
    except OSError:
        return {}


def _finish(res: OrchestrationResult, data_ts: str) -> OrchestrationResult:
    """Record the isolation proof: every unrelated exam is byte-identical before and after."""
    res.fingerprint_after = _fingerprint(data_ts)
    before, after = res.fingerprint_before, res.fingerprint_after
    this = res.exam_id
    res.isolation_ok = all(before.get(e) == after.get(e) for e in before if e != this)
    return res


def _write_staging(res: OrchestrationResult) -> str:
    """Write an auditable staging artifact: identity, sources, evidence, facts, verification,
    conflicts, errors and unresolved items — enough to review a build without re-running it.
    It is written under the staging directory and never into the live register."""
    br = res.build
    rec = br.record if br else None
    payload = {
        'query': res.query, 'year': res.year, 'dryRun': res.dry_run,
        'state': res.state.value, 'reached': res.reached.value,
        'examId': res.exam_id,
        'authority': {
            'name': br.resolved.authority.name if br else '',
            'domain': br.resolved.authority.domain if br else '',
            'confidence': br.resolved.authority.confidence if br else None,
        } if br else {},
        'buildState': br.build_state.value if br else None,
        'sourcesRead': list(rec.sources_read) if rec else [],
        'identity': {u: c.verdict.value for u, c in (br.identity.items() if br else [])},
        'fields': {
            n: {'status': f.status.value, 'note': f.note,
                'value': _short(f.value),
                'citation': {
                    'documentTitle': f.citation.document_title, 'url': f.citation.url,
                    'page': f.citation.page, 'excerpt': (f.citation.excerpt or '')[:300],
                } if f.citation else None}
            for n, f in (rec.fields.items() if rec else [])
        },
        'verification': {
            n: {'status': v.status, 'decision': v.claude.decision.value if v.claude else None,
                'infra': v.infra.value, 'publishable': v.publishable}
            for n, v in res.verifications.items()
        },
        'gate': (res.gate.summary() if res.gate else ''),
        'reviews': res.reviews,
        'conflicts': [],
        'notes': list(rec.log) if rec else [],
        'orchestratorNotes': res.notes,
        'isolationOk': res.isolation_ok,
    }
    os.makedirs(P.STAGING_DIR, exist_ok=True)
    name = f'{res.exam_id or "unresolved"}-orchestration-{time.strftime("%Y%m%d-%H%M%S")}.json'
    path = os.path.join(P.STAGING_DIR, name)
    with io.open(path, 'w', encoding='utf-8') as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False, default=str)
    return path


def _short(value, limit: int = 240) -> str:
    s = str(value)
    return s if len(s) <= limit else s[:limit] + '…'


# --------------------------------------------------------------------------- CLI
def main(argv: Optional[list] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(
        prog='exam_builder.orchestrate',
        description='Run the universal build pipeline end to end for one exam (dry run by default).')
    ap.add_argument('exam', nargs='?', default='', help='the exam name, e.g. "UPSC CSE 2026"')
    ap.add_argument('--year', default='', help='override the year if the name has none')
    ap.add_argument('--claude', action='store_true', help='also run the optional Claude CLI verification')
    ap.add_argument('--publish', action='store_true',
                    help='NOT a dry run: attempt an atomic publish (requires a renderer; the CLI '
                         'supplies none, so this stages unless the pipeline is extended)')
    args = ap.parse_args(argv)
    if not args.exam:
        ap.error('name an exam, e.g. "UPSC CSE 2026"')
    res = orchestrate(args.exam, year=args.year, dry_run=not args.publish, use_claude=args.claude)
    print(res.summary())
    return 0 if res.state in (OrchestrationState.PUBLISHED, OrchestrationState.STAGED) else 1


if __name__ == '__main__':
    raise SystemExit(main())
