# Universal Exam-Build Orchestration — audit & report

Addresses the P1 orchestration gap in `FINAL_UNIVERSAL_ENGINE_AUDIT.md`: the universal stages
existed and were individually tested, but no single command ran discovery → … → publish. This
phase adds the wiring only, by **calling** existing components — no new extraction, no new
models, no exam sections, no redesign. Git HEAD before this phase: `09b4c1d`.

---

## 1. Existing components discovered (Step 1)

Interfaces confirmed by reading each module. "Safe to call" = pure/deterministic given its
inputs, or its side effects are staged/guarded.

| Component | Module · callable | Input → Output | Failure states | Safe to call |
|---|---|---|---|---|
| Resolve + discover + capture + identity + extract | `build.py · build(query, *, year, sibling_exam_words, max_docs, replay)` → `BuildResult` | exam name → record + identity + manifest | raises `AmbiguousAuthority`, `SearchUnavailable`, `LookupError`; `build_state=PAUSED_INFRASTRUCTURE` on a fetch failure | yes — it already runs the first half in order |
| Authority resolve | `resolve.py · resolve(query, *, year)` → `ResolvedExam` | name → authority+seeds | `SearchUnavailable`, `LookupError`, `AmbiguousAuthority(verdict)` | yes (called inside build) |
| Authority ambiguity | `ambiguity.py · decide()` | candidates → `AuthorityVerdict` (`RESOLVED/AMBIGUOUS_AUTHORITY/…`) | — | yes (inside resolve) |
| Content identity | `identity.py · verify(text, target)` → `IdentityCheck` | doc text → `MATCH/MISMATCH/AMBIGUOUS` | — | yes (inside build; MISMATCH dropped pre-extraction) |
| Evidence | `evidence.py · Evidence.verify()`; `verified_or_none()` | value+span+doc → `Extracted\|None`; `VERIFIED/NOT_IN_SOURCE/UNCHECKED` | — | yes (inside semantic) |
| Semantic extract | `semantic.py · extract(field, text, …)` | field+text → `Extracted\|None` | `None` = not read | yes (inside build) |
| Deterministic validation | `verification/deterministic.py · run_deterministic(claim)` → `DeterministicResult` | claim → pass/fail booleans | — | yes (inside verify) |
| Qwen semantic verify | `verification/verifier.py · verify(claim, *, provider, cache)` → `Verdict` | claim → `VERIFIED/NEEDS_REVIEW` + `InfraStatus` | `LLM_UNAVAILABLE/ERROR/INVALID` never publishable | yes — deterministic-first, model can only withhold |
| Verification adapters | `verification/adapters.py · claim_from_*` | record/dict → `Claim` | — | yes (pure) |
| Qwen provider | `verification/client.py · get_provider()` / `ProviderError` | — | infra errors | yes |
| Merge / revision | `merge.py · merge_milestones/merge_posts` → `MergeReport` (`ADDED/CONFIRMED/SUPERSEDED/CONFLICTED/UNCHANGED`) | existing+incoming → reconciled | refuses (→NEEDS_REVIEW) rather than guesses | yes; only meaningful on publish-over-existing |
| Record-level isolation | `exam_authoring/verify.py · run_all(rec)` → report; raises `IsolationError` | record → id/single-authority checks | `IsolationError` | yes |
| Publication gate | `gate.py · evaluate(record, *, build_state, identity_by_source, conflicts, schema_ok, typecheck_ok, isolation_ok)` → `GateReport` (`PASS/BLOCK`) | record+context → decision | blockers list | yes (pure) |
| Data isolation + atomic publish | `publish.py · fingerprint()`, `stage(exam_id, ts)`, `publish(report, *, typecheck)`; `IsolationViolation` | rendered TS → staged/published | `IsolationViolation`; typecheck rollback | yes — staging never touches live; publish is atomic |

**Missing integration point found and added:** there was no generic bridge from a record
`Field` to a verification `Claim` (existing `claim_from_*` adapters take projected UI dicts, not
build records). Added `claim_from_field(field, *, exam_id, official_name, authority, cycle)` in
`adapters.py` — additive, duck-typed, no exam branch — so the orchestrator can run the existing
Qwen gate over whatever a build read.

---

## 2. Orchestration entry point (Step 2/15)

`tools/exam_builder/orchestrate.py · orchestrate(exam_query, *, year='', dry_run=True,
use_llm=False, provider=None, cache=None, replay=None, siblings=None, max_docs=8,
data_ts=…, typecheck=True, render=None) -> OrchestrationResult`, plus a CLI:

```bash
python -m tools.exam_builder.orchestrate "UPSC CSE 2026"          # dry run
python -m tools.exam_builder.orchestrate "UPSC CSE 2026" --llm    # + optional Qwen
```

The input is a **name and a year** — nothing SSC/UPSC/IBPS/LIC-specific. Every branch reads a
*state*, never an exam or authority (proved by `test_22`). The default is a **dry run**.

---

## 3. Pipeline sequence (Steps 3–11)

```
orchestrate()
  fingerprint(live register)                                   # isolation baseline
  build(query, year)         -> RESOLUTION→DISCOVERY→CAPTURE→IDENTITY→EXTRACTION (existing)
     AmbiguousAuthority  -> AMBIGUOUS_AUTHORITY   (stop, nothing built)
     SearchUnavailable   -> INFRASTRUCTURE_FAILURE
     LookupError         -> RESOLUTION_FAILURE
  [use_llm] per FOUND field: claim_from_field -> verify()      # DETERMINISTIC then QWEN
     CONTRADICTED -> field downgraded to NEEDS_REVIEW; SUPPORTED/INSUFFICIENT/infra -> unchanged
  (merge/revision: nothing to merge on a fresh build; conflicts=[])
  run_all(record)                                              # SCHEMA / record isolation
  gate.evaluate(record, build_state, identity_by_source, …)    # PUBLICATION GATE
  write_staging(...)                                           # STAGING (auditable JSON, always)
  if PAUSED_INFRASTRUCTURE -> SOURCE_FETCH_FAILURE
  elif not gate.may_publish -> BLOCKED_BY_GATE
  elif dry_run or render is None -> STAGED
  else stage()+publish()     -> ATOMIC PUBLISH  (PUBLISHED, or ISOLATION_VIOLATION)
  fingerprint(live register)                                   # isolation proof
```

Order is preserved (Step 7): identity → evidence → schema/type → deterministic → Qwen → gate.
Identity and evidence are enforced inside `build` (a MISMATCH document is dropped before
extraction; a value is accepted only when its span is found verbatim). The deterministic layer
runs inside `verify()` **before** the model, so Qwen never sees, let alone overrides, a
deterministic failure.

---

## 4. Failure-state mapping (Step 14) — never collapsed

| Situation | State | Kept distinct from |
|---|---|---|
| No authority resolved (`LookupError`) | `RESOLUTION_FAILURE` | ambiguity, infra |
| Two real authorities (`AmbiguousAuthority`) | `AMBIGUOUS_AUTHORITY` | resolution failure |
| Search/discovery cannot run (`SearchUnavailable`) | `INFRASTRUCTURE_FAILURE` | "authority silent" |
| A document could not be fetched (`build_state=PAUSED`) | `SOURCE_FETCH_FAILURE` | `NOT_PUBLISHED` |
| Source belongs to another exam | gate `BLOCK` (identity MISMATCH) | valid source |
| Extractor missed a present source | field `NOT_EXTRACTED` → gate `BLOCK` | `NOT_PUBLISHED` |
| Authority publishes none | field `NOT_PUBLISHED` (allowed) | `NOT_EXTRACTED` |
| Read but unconfident / Qwen contradiction | field `NEEDS_REVIEW` → gate `BLOCK` | `VERIFIED` |
| Qwen down / malformed | `InfraStatus.LLM_UNAVAILABLE/ERROR/INVALID`; field unchanged | `VERIFIED`, fabricated |
| Gate blocks | `BLOCKED_BY_GATE` | published |
| Publishing would change a neighbour | `ISOLATION_VIOLATION` | published |

---

## 5. Staging design (Step 9)

`_write_staging` writes one auditable JSON per run under `.exam_staging/` (git-ignored),
carrying: exam identity, authority + confidence, build state, sources read, per-source identity
verdicts, every field's `{status, note, value, citation}`, per-field Qwen verdicts, the gate
summary, conflicts, notes, and the isolation result. It is written on **every** run (dry or
not) and **never** touches the live register. It is enough to review a build without re-running
it.

## 6. Publication-gate integration (Step 11)

The orchestrator publishes **only** through `publish.stage` + `publish.publish`, and **only**
when `gate.evaluate` returns `PASS`. It never writes a verified fact around the gate. `stage`
proves data isolation (every other exam byte-identical, else `IsolationViolation`); `publish`
re-proves it against the live file *as it is now* and typechecks with rollback. The orchestrator
adds its own before/after fingerprint of unrelated exams as a second, independent proof.

## 7. Dry-run behavior (Step 13)

Default. Runs resolve → discover → identity → extract → (optional Qwen) → gate → staging, and
writes nothing live. Verified: on a dry run the live register's bytes are identical before and
after (`isolation_ok == True`), and the only artifact produced is the staging JSON.

## 8. Unknown-authority result (Step 12)

The architecture is universal: the orchestrator holds no authority table and no exam branch
(`test_22` asserts the source contains no `if exam ==`, `if authority ==`, `== 'exam-…'`, or
`SSC/UPSC/IBPS/APPSC` literal branch). A synthetic never-seen exam progresses through the
generic path and stops at whichever real stage runs out of inputs — for "Zeta Board Clerk 2031"
the resolver finds no authority and the run ends `RESOLUTION_FAILURE`, with no code change
required (`test_6`). The prior phase additionally proved a never-seen exam stages cleanly into
the register with all existing exams byte-identical.

## 9. Real end-to-end proof (Step 17)

Ran the **real** orchestrator over a captured offline UPSC CSE 2026 source set (only network I/O
injected, as `test_contamination` does; resolve, discovery, identity, extraction, the gate,
staging and the isolation proof all real), **dry run**, against the live `src/data.ts`:

- **Extraction** read the real notice: `officialName`, `authority`, `applicationPortal`
  (`upsconline.nic.in`), `ageLimits`, `dates` all **FOUND** with page citations (5/19 fields).
- Fields with no matching extractor in the minimal fixture came back **NOT_EXTRACTED**; genuine
  absences (`corrigenda`, `cutoffs`, `answerKeys`, `officialPapers`, `results`) came back
  **NOT_PUBLISHED** (allowed).
- **The gate BLOCKED** with 9 blockers — correctly refusing to publish a build with
  `NOT_EXTRACTED` fields ("publishing would show a gap the authority did not leave"). State:
  `BLOCKED_BY_GATE`.
- **Staging** wrote an auditable artifact; the **live register was byte-identical** before and
  after (`isolated: True`). Nothing was published, which is the right outcome for a partial
  extraction.

This exercises resolve → source selection → identity → extraction → validation → gate → staging
→ isolation on real inputs, safely (dry run, production untouched), exactly as Step 17 prefers.

## 10. Isolation proof (Step 10)

- Every dry run: unrelated exams byte-identical before/after (`test_17`, and the E2E above).
- Atomic publish into a temp register updates only the target; the neighbour is byte-identical
  (`test_19`).
- All required pairs (SSC+UPSC, UPSC+IBPS, IBPS+LIC, LIC+APPSC) unchanged when a target is
  published (`test_20`), and reverse-order builds each leave the other untouched (`test_21`).

## 11. Tests (Step 16)

`tools/exam_builder/test_orchestrate.py` — **23 cases** (the 22 required; case 9 split into
search-unavailable and source-fetch-failure), all offline: only `build` (network) and the Qwen
provider are stubbed; the real gate, publisher, record-isolation check and verifier run. Covers
resolution of SSC/UPSC/IBPS/LIC, APPSC ambiguity, unknown authority, identity mismatch, cycle
mismatch, source failure, extraction failure, deterministic-validation failure, Qwen
SUPPORTED/CONTRADICTED/INSUFFICIENT/unavailable, publication rejection, dry-run and staging
non-mutation, successful publication, cross-exam and reverse-order isolation, and "no
exam-specific branch". The suite depends on neither Tavily nor a live Qwen.

## 12. tsc

`npx tsc --noEmit` — clean, 0 errors (no frontend change).

## 13. build

`npm run build` — success, `dist/index.html` 2,525 kB (unchanged).

## 14. Exact files changed

- `tools/exam_builder/orchestrate.py` — **new**: the orchestrator, states, staging, CLI.
- `tools/exam_builder/test_orchestrate.py` — **new**: 23-case suite.
- `tools/exam_builder/verification/adapters.py` — **+34**: `claim_from_field` bridge (additive).
- `ORCHESTRATION_AUDIT.md` — **new**: this report.

No `src/`, `app.py`, `govos.db`, `index.html`, `dist/`, `.env`, or model file changed. No exam
data touched. No UI change. Full gate: 238 exam_builder unittest + 15 research-facts tests, 23
standalone modules, all pass; tsc clean; build ok.

## 15. Commit hash

`<filled on commit>`.

## 16. Push result

`<filled on push>`.

## 17. Remaining limitations

- **Atomic publish to the live register needs a record→TypeScript renderer, which the
  orchestrator deliberately does not own.** The existing `publish.stage/publish` operate on a
  rendered `export const …_EXAM: Exam = {…}` block; `build`/`compat` produce a Python record and
  a UI projection, not that TypeScript literal. Writing that emitter is real new logic (it must
  render every authored field shape safely), so per the phase's "do not force it" rule the
  orchestrator takes a `render` callback for the one live-write path and, without one, stages a
  gate-passing build for a human instead of publishing. This is a bounded **P1** follow-up
  (a safe record→TS emitter), not a safety hole: nothing is published around the gate, and the
  dry-run/staging path is complete and proven.
- **Merge/revision is wired but not exercised on a from-scratch build** — there is no prior
  record to reconcile, so `conflicts=[]`. It becomes active on a publish-over-existing path once
  the renderer above exists.
- **A live network build depends on a Tavily key and reachable authority sites**, absent here,
  so the real E2E proof uses a captured offline source set (the same technique the isolation
  tests use). This is a proof-environment limitation, not an orchestrator one.
- Qwen remains **optional** (`use_llm=False` by default) and, when enabled, can only withhold —
  it never upgrades a field and an outage never changes data.
