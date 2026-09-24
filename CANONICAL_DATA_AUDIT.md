# Canonical Exam-Data Ownership & Fidelity — architecture audit

Audit only. No data migrated, no DB/UI/deployment/`data.ts` changed. The single code artifact is
`tools/exam_builder/test_fidelity.py` — a preservation test that *proves* the findings (Step 7).
Resolves the P1 in `PRODUCTION_RENDERER_AUDIT.md`: how to let a machine field-level-merge into
existing hand-authored records without losing fidelity. Git HEAD before this phase: `dde05ef`.

**Headline:** the codebase already contains a safe, non-destructive, provenance-carrying,
runtime **overlay** mechanism (`syllabus_revisions`, `resource_additions` in `govos.db`, merged
over the `data.ts` seed by `applySyllabusRevisions` / `additionToResource`). It solves the
fidelity problem for two domains today and is the pattern to generalise. The recommendation
(Step 10) needs **no migration of `data.ts` and no new database**.

---

## Step 1 — Who owns each fact?

`data.ts` is authored TypeScript, consumed **only** by the frontend build (imported in
`main.tsx`/`ui.tsx`, compiled by Vite into the single-file `dist/index.html`). **No backend reads
it** (grep: only the offline `tools/exam_builder`/`exam_authoring` touch it). The only writer is
the offline `publish.py`. So authored exam facts live in source code, not in a database.

| Domain | Source | Notes |
|---|---|---|
| identity (id/code/title/authority/domain) | **AUTHOR** | data.ts; also emittable by `emit.render_exam` for new exams |
| dates / timeline | **AUTHOR** (+ machine-capable) | data.ts; a superseded date is kept struck-through |
| eligibility | **AUTHOR** | data.ts (`globalRuleGroup`, `eligibilityHighlights`, `ageRelaxations`) |
| posts | **AUTHOR** | data.ts (`PostRequirement[]`) |
| application | **AUTHOR** | data.ts (`ApplicationGuideData`, simulator spec) |
| exam pattern | **AUTHOR** | data.ts (`stages`, `patternTree`) |
| syllabus | **MIXED** | AUTHOR seed (`syllabus`) **+ MACHINE/verifier overlay** (`syllabus_revisions`) merged at runtime by `applySyllabusRevisions` |
| PYQs / practice bank | **MIXED** | AUTHOR SSC bank + **DERIVED** generated drills (`GOVOS_AUTHORED`); UPSC official papers AUTHOR |
| answer keys | **AUTHOR** | data.ts; mostly `null`/absent by design |
| admit card | **AUTHOR** | data.ts (`admitCardEvents`); + **DERIVED** live board feeds (cached) |
| exam day | **AUTHOR** (none authored yet) | data.ts optional; honest empty for all five |
| results | **AUTHOR** | data.ts (`resultDeclarations`); self-assessment is candidate input |
| FAQs | **AUTHOR** | data.ts |
| resources | **MIXED** | AUTHOR seed + **verifier overlay** (`resource_additions`) + **DERIVED** live feeds/link-health (cached in `govos.db`) |
| portals / official links | **AUTHOR** | data.ts (`officialLinks`) |
| corrigenda | **AUTHOR** | data.ts |
| cutoffs | **AUTHOR** | data.ts (`cutoffsHistory`) |
| roadmap | **AUTHOR** | data.ts (`roadmapTracks`) |
| mock tests | **DERIVED** | generated at runtime from `TOPIC_CATALOG`; never stored |
| — candidate data (profile, attempts, bookmarks, notifications, tracked) | n/a exam fact | `govos.db` + `localStorage`; not exam facts |

**Two domains are already MIXED via a runtime overlay** — the precedent this audit builds on.

## Step 2 — Source of truth

| Domain group | Current source of truth | Producer | Consumer | Mutable? | Provenance? |
|---|---|---|---|---|---|
| Authored exam facts (17 domains) | **`data.ts`** (source code) | offline `publish.py` (whole-slice) / humans | frontend build → `dist/index.html` | only via offline publish; **not** at runtime | yes (`DataProvenance`, often shared consts) |
| Syllabus revisions | `govos.db · syllabus_revisions` | verifier (Trust Panel API) | frontend at runtime (`applySyllabusRevisions`) | yes (add/retire) | yes (built per revision) |
| Resource additions | `govos.db · resource_additions` | verifier API | frontend at runtime (`additionToResource`) | yes (add/retire) | yes |
| Live feeds / link health | `govos.db · live_feed_cache`, `resource_link_health` | Flask background refresh (external) | frontend at runtime | yes (cache) | derived, dated |
| Candidate state | **`localStorage`** (effective) + `govos.db` (best-effort) | the SPA (`services.ts` writes localStorage first, SQLite fire-and-forget) | the SPA | yes | n/a |
| Research findings | `govos.db · research_runs/findings/facts` | Tavily + human review | Trust Panel | yes (PENDING→reviewed) | classified, never VERIFIED without a human |

- **Is `data.ts` canonical?** Yes — for authored exam facts. It is source code, not a runtime store.
- **Is `govos.db` canonical?** Yes — for candidate state, the two exam-fact overlays, feed caches and research. **It holds no authored exam register.**
- **Firebase?** **None** — no `firebase`/`firestore` anywhere in `src/`, `app.py`, or `package.json`.
- **localStorage?** Canonical for candidate runtime state (SQLite is a best-effort mirror).
- **Some domains authored in code, others persisted elsewhere?** Yes — 17 authored in `data.ts`; syllabus & resources also carry runtime overlays in `govos.db`.
- **UI consumes:** compiled `data.ts` **merged at runtime** with `govos.db` overlays (the `liveExam` handed down by `main.tsx`) and `localStorage`.
- **Builder consumes/produces:** an `ExamRecord` offline; writes `data.ts` via `publish`.
- **Publisher:** whole-slice textual replacement of `data.ts` (`publish.stage`).

## Step 3 — Fidelity requirements & why TS cannot be field-patched

Everything a future machine merge must not destroy: **inline comments; shared `const` provenance
spreads** (`...sscSyllabusSource`, `upscNotice(...)`); **formatting & ordering; authored ids;
provenance (including shared); verification state; revision history; authored values; machine
values; unknown/frontend-only fields** (`careerFields`, `categoryTag`, `isGoldenJourney`,
`eligibilityHighlights`, …); **populated arrays; hand-curated content.**

**The current TS source format cannot support safe field-level patching — proven, not asserted**
(`test_fidelity.py`, Part 1): `publish.stage` replaces an exam's whole slice, and the only way to
update an existing record is to re-emit it. A partial re-emit **deletes authored arrays**
(`syllabus`/`resources`/`cutoffs` → `[]`), **drops inline comments**, **inlines shared-const
provenance**, and **loses authored ids** — each detected explicitly, and the change is a hash
change. A TS parser/emitter cannot fix this: comments and the shared-const *structure* are not
recoverable from a parsed object, and publish.py deliberately never parses TS. **TS source is
unsuitable as a machine-patchable store.**

## Step 4 — Ownership conflicts

Domains where an author value and a machine-verified value can touch the same field: **dates,
vacancies, eligibility, posts, syllabus, resources, cutoffs.** Required semantics when both exist
(no winner chosen here — these are the *rules*, and every one already has infrastructure):

| Situation | Semantic | Existing support |
|---|---|---|
| Author value, machine agrees | **CONFIRM** | `merge.MergeAction.CONFIRMED` |
| Machine value, nothing authored | **MERGE / ADD** | `MergeAction.ADDED`; `syllabus_revisions` ADD |
| Machine value with a notice that revises the authored one | **SUPERSEDE** (keep old, struck) | `Revision` lifecycle; already done for dates |
| Author & machine disagree, no stated relation | **CONFLICT** → hold for review, keep both | `MergeAction.CONFLICTED` → `NEEDS_REVIEW` |
| Machine value unconfident | **REVIEW** (never official) | `Status.NEEDS_REVIEW` / `verificationLevel: UNDER_VERIFICATION` |
| Authored value, machine silent | **PRESERVE** | overlay simply carries nothing |
| Computed value | **DERIVED** (marked) | `Fact.derived_from` |

The governing rule from `merge.py` holds: **never delete an authored fact, never prefer a value
because it is newer or because it was extracted rather than authored; refuse and keep both.**

## Step 5 — Can `UniversalExam` be the canonical model?

`UniversalExam` (`schema.py`) is `Fact[T]`-based with `SourceEvidence`, `Status`, `Revision`,
`ExamIdentity`, `PaperIdentity`, nested `ExamPattern`/`Syllabus` trees, `OfficialPaper`,
`AnswerKey`, `AdmitCardNotice`, `ResultDeclaration` (with nested `CutoffMark`). It covers:
identity, dates (milestones), eligibility, posts, application, pattern, syllabus, PYQs, answer
keys, admit cards, results, revisions — with provenance and status throughout.

**Information that cannot survive a `UniversalExam` round-trip today:**
- **No schema types for five domains:** `resources`, `officialLinks` (portals), `faqs`,
  `examDayChecklist`, `roadmapTracks`. These would be lost.
- **`cutoffsHistory`** exists only as `CutoffMark` nested in a result declaration, not as the
  standalone domain the frontend renders.
- **Frontend-only presentation fields** have no `UniversalExam` home: `isGoldenJourney`,
  `isDemoData`, `categoryTag`, `careerFields`, `minimumQualification`, `vacanciesTotal`,
  `eligibilityHighlights`, `syllabusSourceNote`, the application simulator's authored traps.
- **The `ExamRecord → UniversalExam` bridge does not exist**, so the build cannot even populate a
  `UniversalExam` yet.

**Conclusion:** `UniversalExam` is the right *shape* (evidence-first, scoped, revision-aware) and
already canonical-quality for ~12 of 19 domains, but it is **not yet a complete canonical model** —
five domains and several presentation fields have no representation. It can become the machine-side
canonical model **after** those types are added; it should not replace `data.ts` wholesale.

## Step 6 — Storage options

Evaluated against field-level updates · provenance · revisions · atomic writes · isolation ·
human editing · deployment/Vercel · existing UI · Flask · repo workflow · offline dev · migration
cost · rollback · auditability.

- **A. `data.ts` stays canonical (status quo).** Human editing ✓, provenance ✓, UI ✓, offline ✓,
  auditable via git ✓. **Fails field-level machine updates** (Step 3). *Keep as the authored seed,
  not as the machine target.*
- **B. Structured JSON exam records.** Field-level ✓, machine-mergeable ✓. But migrating all
  authored records loses the TS authoring ergonomics, comments and shared consts; the UI needs a
  loader; large migration. High fidelity for machine, poor for human authoring.
- **C. SQLite canonical.** The SPA is a **static single-file** build — it cannot read a DB at build
  time, and the current deploy has no runtime exam-fact API. Making the DB canonical forces the
  frontend to fetch every exam fact at runtime (architecture change) and is hostile to offline dev
  and the single-file deploy. **Rejected.**
- **D. Firebase canonical.** None exists; adds a dependency, cost, auth surface, and breaks offline
  dev and the static build. **Rejected.**
- **E. Hybrid: authored seed + machine overlay store.** `data.ts` stays the authored canonical
  seed; machine/verifier facts are **additive, provenance-carrying, status-aware, reversible
  overlays**, merged at runtime — **exactly the existing `syllabus_revisions`/`resource_additions`
  pattern**, generalised to all domains. No `data.ts` migration, no new DB, reuses `Fact`/
  `Revision`/`merge` semantics, UI already merges overlays, rollback via a `retired` flag,
  isolation via per-exam-keyed rows, new exams via the safe `emit.render_exam` append. **Recommended.**
- **F. E-variant: build-time overlay files.** Per-exam JSON overlays committed beside `data.ts`
  and merged at **build** time (not via a runtime API). Keeps the static single-file deploy fully
  self-contained (good if the app must deploy as static to Vercel/Netlify), at the cost of a build
  step to fold overlays in. A viable variant of E where no runtime API is available.

## Step 7 — Preservation test (delivered)

`tools/exam_builder/test_fidelity.py`, **9 cases, all passing**, on in-memory strings (no
migration, no production write):
- **Part 1 proves the loss:** whole-slice replacement deletes authored arrays, drops comments,
  inlines shared consts, loses ids, and is a hash change.
- **Part 2 proves the fix:** an additive overlay leaves the authored record **byte-identical**,
  mutates **no other exam**, and carries the machine fact with **provenance and supersession**.
It explicitly detects deleted arrays, lost provenance, lost comments, lost ids, and cross-exam
mutation — the future-proof preservation check the migration will run at every phase.

## Step 8 — Machine/human conflict model (design only)

| State | Meaning | Existing infrastructure (no new concept needed) |
|---|---|---|
| **AUTHORED** | a `data.ts` value with no overlay | seed record; `verificationLevel: OFFICIALLY_VERIFIED` |
| **MACHINE_VERIFIED** | overlay, deterministic+Qwen passed | `Status.VERIFIED`; overlay row `OFFICIALLY_VERIFIED` |
| **MACHINE_REVIEW** | overlay, read but unconfident | `Status.NEEDS_REVIEW` / `UNDER_VERIFICATION` |
| **CONFLICT** | author & machine disagree, no revision | `MergeAction.CONFLICTED` → both kept, `NEEDS_REVIEW` |
| **SUPERSEDED** | a later official doc revises it | `Revision` (ORIGINAL→REVISED→CANCELLED→SUPERSEDED); already live for dates |
| **DERIVED** | computed | `Fact.derived_from`; UI prints "(computed)" |

Every state maps to `Status`, `Revision`, `MergeAction`, or `DataProvenance.verificationLevel`
that already exist. **No duplicate concepts required.**

## Step 9 — Deployment reality

- **No deployment config exists** — no `vercel.json`, `Procfile`, `netlify.toml`, CI workflow.
  "Vercel" is not currently wired.
- **Build:** `npm run build` → Vite `vite-plugin-singlefile` → one self-contained
  `dist/index.html` (no runtime CDN). **Frontend is fully static.**
- **Backend:** `python app.py` (Flask) serves `dist/index.html` + the API on one port; not
  serverless.
- **SQLite (`govos.db`):** a **committed seed** (git-tracked) **and runtime-writable** by Flask
  (candidate data, the two overlays, feed caches, research). It is both dev and (single-instance)
  production store. On a serverless host its writes would be ephemeral/per-instance.
- **Firebase:** none.
- **Vercel implication:** only the static frontend is Vercel-ready today; the Flask API + SQLite
  writes need a stateful host. This is why **E (runtime overlay)** assumes the existing Flask+SQLite
  host, and **F (build-time overlay)** is the variant for a static-only deploy.

## Step 10 — Recommendation

**Adopt Option E: keep `data.ts` as the authored canonical seed, and store all machine/verifier
exam facts as additive, provenance-carrying, status-aware, reversible overlays in `govos.db`,
merged over the seed at runtime — generalising the mechanism the app already ships for syllabus
and resources.** No `data.ts` migration, no new database.

- **Solves fidelity:** the authored TS is never rewritten, so comments, shared consts, ordering,
  ids and populated arrays are untouched by construction (proven: `test_fidelity` Part 2). The
  unsafe whole-slice replacement is used **only for appending brand-new machine-owned exams**,
  where there is nothing to preserve.
- **Preserves authored records:** an overlay row is keyed by `(exam_id, domain, target_id)` and
  only *adds* or *supersedes*; it never deletes the seed. A missing machine value leaves the
  authored value showing.
- **Merges machine facts:** the orchestrator writes overlay rows (ADD/AMEND/SUPERSEDE/RETIRE)
  instead of re-emitting a slice; `merge.py` decides CONFIRM/SUPERSEDE/CONFLICT at the field level.
- **Provenance & revisions survive:** each overlay carries a `DataProvenance` and, for a change, a
  `Revision` link to what it supersedes; the old value is kept (as dates already do).
- **UI stays stable:** the frontend already merges overlays (`applySyllabusRevisions`,
  `additionToResource`, `liveExam`); generalising means one merge function per domain over the same
  `Exam` shape the UI already consumes. No UI redesign.
- **Rollback:** every overlay has a `retired` flag; retiring it returns the exam to its seed value
  (already how syllabus revisions roll back).
- **Isolation:** overlay rows are per-exam; one exam's overlays can never touch another's seed
  (rows are filtered by `examId`, as `applySyllabusRevisions` does).
- **New exams:** added via the safe `emit.render_exam` + `publish.stage` append (built last phase);
  their later machine updates use the same overlay path.
- **Orchestrator use:** after the gate passes, instead of `render + whole-slice publish`, the
  orchestrator emits **overlay writes** for changed fields (through a new, thin `overlay_merge`
  that calls `merge.py` for the decision and writes rows) — additive, gated, reversible.

The machine-side canonical model for those overlays is `UniversalExam` **once** it gains the five
missing domain types (Step 5); until then overlays can carry the frontend field shape directly, as
`syllabus_revisions` already does.

## Step 11 — Staged migration plan (not executed)

Each phase is reversible and gated by the `test_fidelity` preservation check.

- **Phase A — Canonical ownership model.** Write the overlay schema (a generic `exam_fact_overlay`
  table: `exam_id, domain, target_id, kind, value_json, provenance_json, status, supersedes,
  retired`) and the `Status`/`Revision` mapping from Step 8. *Rollback:* it is additive DDL; drop
  the table. No reads yet.
- **Phase B — Read compatibility layer.** One pure `applyOverlays(exam, overlays)` per domain
  (generalising `applySyllabusRevisions`), returning a new `Exam`, seed unchanged when empty.
  *Rollback:* feature-flag off → identical to today.
- **Phase C — Dual-read verification.** Serve the merged exam behind a flag; assert the merged
  output equals the seed when no overlays exist, and that `test_fidelity` passes for every exam.
  *Rollback:* flag off. *Gate:* zero diff with empty overlays.
- **Phase D — One disposable/synthetic exam.** Apply a real overlay (e.g. a superseded date) to a
  synthetic exam; prove the seed is byte-identical and the value updates. *Rollback:* retire the
  overlay. *Gate:* `test_fidelity` + byte-identical seed.
- **Phase E — One real exam.** Move an already-live change (the SSC 27-09-2026 date, or the UPSC
  27→24 Feb supersession) from `data.ts` into an overlay; render identically. *Rollback:* retire
  the overlay (seed still carries the authored value). *Gate:* pixel/DOM parity + `test_fidelity`.
- **Phase F — Machine field-level merge.** Point the orchestrator's publish path at overlay writes
  (via `merge.py`) for existing exams, keeping whole-slice publish for brand-new exams only.
  *Rollback:* orchestrator flag back to "new exams only". *Gate:* no authored slice changes bytes.
- **Phase G — Retire unsafe whole-record replacement.** Once every domain merges via overlays,
  restrict `publish.stage` to append-only (new exams). *Rollback:* re-enable replace. *Gate:* all
  suites green; no exam-specific branch; `test_fidelity` green.

## Step 12 — Hard stop

Nothing was migrated, rewritten, or reconfigured: `data.ts`, `govos.db`, SQLite/Firebase, the UI,
and the deployment are untouched; no field-level merge was implemented; no production exam record
was altered. The only artifact besides this report is the audit-proving test `test_fidelity.py`.

**Does a safe canonical store already exist?** Partly — the `syllabus_revisions` /
`resource_additions` overlay is a working, non-destructive, provenance-carrying, reversible store
for two domains, usable today with **no migration**. The recommendation is to generalise that exact
mechanism rather than introduce a new database. Full coverage additionally needs the five missing
`UniversalExam` domain types (Step 5), which Phase A/B would add.

### Files
- `CANONICAL_DATA_AUDIT.md` — this report.
- `tools/exam_builder/test_fidelity.py` — the preservation proof (9 tests).
No source, data, DB, UI, or deployment file changed.
