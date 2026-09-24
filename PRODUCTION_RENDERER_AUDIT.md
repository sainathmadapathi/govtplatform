# Universal Production Renderer & Safe Atomic Publish — audit & report

Closes the bounded P1 from `ORCHESTRATION_AUDIT.md`: the orchestrator could resolve → … →
stage but not safely publish live, because it owned no record → production representation. This
phase adds that bridge **safely**, by reusing the renderer that already exists and adding the one
decision it lacks (whether publishing is safe). Git HEAD before this phase: `88cae1a`.

Headline: a full preservation-*merge* into the hand-authored records is **not** safely
achievable and is left as a documented P1 (the HARD STOP boundary). Everything short of that —
a universal, status-aware, provenance-preserving renderer and a **preservation-first atomic
publish for a new exam** — is implemented, tsc-validated against the real interface, and proven.

---

## 1. Existing production representation (Step 1)

- **The renderer already exists.** `tools/exam_authoring/emit.py · render_exam(rec: ExamRecord)
  -> str` emits a complete `export const CODE_EXAM: Exam = {…}` block. It is already:
  *status-aware* (only `usable` fields; `NEEDS_REVIEW` → `UNDER_VERIFICATION`; `NOT_EXTRACTED`
  / `NOT_PUBLISHED` → honest empty arrays, never invented), *provenance-preserving* (a
  `DataProvenance` on every value via `Citation.to_provenance`), *complete* (all 21 required
  `Exam` fields — arrays `[]`, `globalRuleGroup`/`applicationGuide` as valid minimals), and
  *universal* (no exam/authority branch).
- **The Exam interface** (`src/types.ts`): 38 fields, **21 required** (10 arrays satisfiable
  with `[]`, 2 small nested objects, 9 scalars). A complete valid Exam is machine-emittable, and
  `render_exam` emits one.
- **The publisher** (`publish.py`) treats a record as an **opaque TS slice**: `stage` replaces
  an exam's whole `export const … = {…};` block (or appends a new one) and `publish` re-proves
  isolation and runs `npx tsc --noEmit` with rollback. It never parses the object internals.
- **Two record models, no bridge.** `build.py` produces an `exam_authoring.record.ExamRecord`
  (flat `dict[str,Field]`); `schema.py`'s `UniversalExam`/`Fact` is a separate, richer model that
  `compat.py` projects per-section to the UI. **Nothing converts `ExamRecord` → `UniversalExam`**,
  and `compat.py` never assembles a whole `Exam`. So the build → `data.ts` route is
  `render_exam`, not `compat`. (Reaching `compat`'s rich projections would need an
  `ExamRecord → UniversalExam` bridge — a separate concern, not this phase.)

### The decisive finding: byte-fidelity round-trip is impossible

Authored `data.ts` records **reference shared `const`s** (`...sscSyllabusSource`,
`upscNotice(...)`, `officialSource(...)`) declared above the records, and **contain inline
comments** inside the object literal. Since `publish.stage` replaces the whole slice, updating a
hand-authored record from a machine build would have to re-emit it — which **inlines the shared
provenance consts and drops the comments** (fidelity lost), and, for a *partial* build, would
**erase the authored arrays** (`syllabus`, `resources`, `cutoffsHistory`, …) the build never
extracted. Neither is acceptable.

### Compatibility mapping

| Build field | Maps to | How |
|---|---|---|
| officialName / authority / applicationPortal | `title` / `authorityName` / `applicationGuide.officialPortal` | direct |
| dates (list of `{type,label,dateTimeStr}`) | `dates: ImportantDate[]` | projected (+id/timezone/status/provenance) |
| ageLimits / vacancies / fee / attempts / qualification | `eligibilityHighlights[]`, `crucialEligibilityDate` | projected where the value is typed |
| posts (with printed Group) | `posts: PostRequirement[]` | projected; posts without a printed Group are named in the header, not faked |
| notice / officialPapers | `resources[]` (links only) | projected |
| syllabus / stages / practiceQuestions / cutoffs / faqs / roadmap | `[]` | **honest empty** — not extracted by this pipeline |

**Fields that cannot safely be projected** are emitted as honest empties, never invented — the
existing renderer's rule, preserved.

---

## 2. Preservation semantics (Steps 2, 7)

`render.py` adds the missing decision and nothing else. The rule is asymmetric and
preservation-first:

```
NEW exam (no block in the register)   -> safe to append the rendered block
EXISTING exam in the register         -> refuse; a partial build must not overwrite it
```

`target_in_register(exam_id, data_ts)` reuses `publish.fingerprint`/`slice_exams` (a textual
slice — no TS parsed). The orchestrator refuses to publish over an existing record unless the
caller passes an explicit `allow_overwrite=True` (used only for disposable/machine-owned
targets in tests). **A missing section is never an empty section**: a partial build leaves the
existing record byte-identical. Merging new verified fields into an existing authored record is
the P1 below.

## 3. Renderer design (Step 3)

No second data model, no second renderer. `render.py` re-exports `emit.render_exam` verbatim and
adds `target_in_register`. The orchestrator's publish branch now: picks the renderer (`render`
override, else the default `render_exam`), applies the preservation guard, then publishes through
the existing `publish.stage` + `publish.publish`. ~40 lines of wiring; the renderer itself is
untouched.

## 4. Status-aware projection (Step 4)

Enforced by the reused renderer and proven (`test_render` 2–4): a `FOUND` field carries
`OFFICIALLY_VERIFIED`; a `NEEDS_REVIEW` field carries `UNDER_VERIFICATION` and is never official;
a `NOT_EXTRACTED`/`NOT_PUBLISHED` section is an honest empty array, never fabricated. Only
gate-passing (`FOUND`, evidence-backed) records reach publication at all.

## 5. Provenance (Step 5)

Every emitted value carries a `DataProvenance` (documentTitle, officialUrl, page, clause,
verified/published dates, verifier, `verificationLevel`, excerpt), built from the field's own
`Citation`. No provenance is fabricated for a field that lacks a citation. Verification status is
never silently dropped — it becomes the badge level.

## 6. Merge semantics (Step 6)

No second merge engine. Value-level conflict/revision arbitration belongs to `merge.py` (schema
level) and is unchanged. At the frontend-record level the renderer does not arbitrate "new vs
old" for an existing record at all — it **refuses to overwrite**, which is the safest possible
merge semantics for a representation that cannot be losslessly round-tripped.

## 7. Array safety (Step 7)

Proven (`test_render` 8): an existing populated `syllabus`/`resources`/`cutoffsHistory` array
survives a partial build byte-identical. The guard never replaces a populated existing array
with an empty one — because it never overwrites an existing record.

## 8. Schema validation & 9. Atomic publication (Steps 9, 10)

Rendering flows `record → render_exam → publish.stage (isolation proof) → publish.publish
(re-proof + `tsc --noEmit` + rollback)`, never `render → write file`. If the gate blocks,
isolation fails, or tsc fails, nothing is published and the live register is unchanged
(`test_render` 11–12; publish restores its backup on a tsc failure). Distinct failure states:
`BLOCKED_BY_GATE`, `PRESERVATION_BLOCKED`, `ISOLATION_VIOLATION`.

## 10. Dry-run behavior (Step 11)

Default `dry_run=True` is preserved: resolve → … → render candidate → stage, and **never**
writes live (`test_render` 13). The staging artifact reports target, per-field status/value,
projected vs honest-empty, review items, gate decision, and the isolation result.

## 11. Partial-build proof (Step 13)

`test_render` 7–8: an existing exam with populated `syllabus`/`resources`/`cutoffsHistory` +
a partial new build (identity/dates only) for the same id → `PRESERVATION_BLOCKED`, the register
**byte-identical**, the authored arrays intact. Preservation-first, proven.

## 12. Verified / review proof (Step 14)

`test_render` 2–4, 11: VERIFIED → `OFFICIALLY_VERIFIED`; NEEDS_REVIEW → `UNDER_VERIFICATION`;
NOT_EXTRACTED → honest empty + gate block, never verified content; NOT_PUBLISHED → not published
factual content; populated existing array + absent new array → preserved.

## 13. Cross-exam isolation (Step 15)

`test_render` 9–10: publishing a new exam leaves all five existing exams byte-identical; an
overwrite whose render would add a stray exam is refused by the publisher's isolation proof
(`test_render` 12). No exam-specific branch in `render.py` (`test_render` 6) or the orchestrator
(`test_orchestrate` 22).

## 14. Unknown-authority result (Step 16)

`test_render` 5: a never-seen authority renders from its own record, no branch added. The prior
phase proved the same authority stages cleanly with all existing exams byte-identical.

## 15. Real orchestrator integration (Step 17)

The orchestrator now calls the renderer for the publish path; no stage is duplicated. The full
flow is: input → resolve → discovery → identity → extraction → deterministic → Qwen → (merge n/a
on a fresh build) → gate → render_exam → publish.stage (isolation) → publish.publish (schema/tsc)
→ atomic write, dry-run by default.

## 16. Real end-to-end proof (Step 12)

- **Dry run, real orchestrator, offline UPSC set**: resolve → extract (officialName, authority,
  applicationPortal, ageLimits, dates FOUND) → gate BLOCK on `NOT_EXTRACTED` fields → staged; the
  rendered candidate carried all 21 required fields; the live register stayed byte-identical.
- **tsc-validated publish, real register, synthetic exam**: a synthetic new exam (`exam-zeta-
  clerk-2031`) was rendered by `render_exam`, staged and **published atomically into the real
  `src/data.ts` with `typecheck=True` — `npx tsc --noEmit` passed**, proving the emitted Exam
  satisfies the real interface and integrates; the 5 existing exams were byte-identical. The
  register was then reverted, so **production `src/data.ts` is byte-identical to committed**.

## 17. Failure safety (Step 18)

Tested: gate block → no publish; preservation block → no overwrite; isolation violation → no
publish; renderer/publish failure → backup restored; source unavailable (`PAUSED`) →
`SOURCE_FETCH_FAILURE`, never a destructive replacement; `NOT_EXTRACTED` → honest empty, never a
destructive replacement; LLM unavailable → unverified facts never published (prior phase).

## 18. Test counts

**251** exam_builder unittest tests (238 + **13** new `test_render`), **23** standalone modules,
**15** research-facts tests — all pass. `test_orchestrate` extended (3 overwrite tests now pass
`allow_overwrite=True`).

## 19. tsc — `npx tsc --noEmit` clean, 0 errors (no frontend change).
## 20. build — `npm run build` success, `dist/index.html` 2,525 kB (unchanged).

## 21. Exact files changed

- `tools/exam_builder/render.py` — **new**: reuses `emit.render_exam`; adds `target_in_register`.
- `tools/exam_builder/orchestrate.py` — preservation guard + default renderer + `allow_overwrite`
  + `PRESERVATION_BLOCKED` state (~40 lines).
- `tools/exam_builder/test_render.py` — **new**: 13 renderer cases.
- `tools/exam_builder/test_orchestrate.py` — 3 overwrite tests pass `allow_overwrite=True`.
- `PRODUCTION_RENDERER_AUDIT.md` — **new**: this report.

No `src/`, `app.py`, `govos.db`, `index.html`, `dist/`, `.env`, or model file changed. No exam
data changed. No UI change.

## 22. Commit hash — `d691b75` (this §22/§23 record is a one-line follow-up commit).
## 23. Push result — Pushed to `origin/main`.

## 24. Remaining limitations (the HARD STOP boundary, classified P1)

- **Merging new verified fields into an existing hand-authored record is not implemented, by
  design.** The production representation cannot be losslessly round-tripped: authored records
  reference shared `const` provenance and carry inline comments, and `publish.stage` replaces the
  whole slice, so a re-emit would inline the consts, drop the comments, and — for a partial build
  — erase authored arrays. Doing it safely needs a **fidelity-preserving structured store** (or a
  TS-aware structural merge that publish.py deliberately avoids). Per the phase's HARD STOP rule,
  this is **not forced**; it is recorded as **P1**. The renderer therefore updates only **new /
  machine-owned** exams and **refuses** to overwrite authored ones, which is the safe outcome.
- **Rich typed projection of loosely-extracted fields** (e.g. eligibility → `RuleGroup`/`posts`
  beyond what `emit` already maps) would benefit from an `ExamRecord → UniversalExam → compat`
  path that does not exist yet — a separate bounded improvement, not a safety issue. Unmapped
  fields are honest empties, never fabricated.
- A live network build still depends on a Tavily key + reachable sites; the real proofs use a
  captured offline set and a synthetic exam, as the isolation tests do.
