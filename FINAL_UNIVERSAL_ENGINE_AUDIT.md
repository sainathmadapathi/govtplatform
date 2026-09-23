# GovOS — Final Universal Engine Audit

Audit only. Git HEAD at audit time: `14771c9`. Working tree clean. **No production code was
changed in this phase** — the fix-gate (below) is not met by any finding, so this is a report.

Method: the pipeline and verification code were read directly; three parallel sweeps mapped
exam-specific logic, the build-pipeline stages, and 17-section data coverage; and two claims were
proved empirically by running code — content isolation (`test_contamination`) and data isolation +
unknown-authority universality (a live `publish.stage` of a never-seen synthetic exam). Prior-phase
`*_AUDIT.md` reports were **not** trusted; every load-bearing claim was re-verified against source.

---

## 1. Overall architecture verdict

**GovOS is a genuinely universal engine, not an SSC platform with exams bolted on — with two real
caveats.** The core safety machinery (identity, evidence, state semantics, isolation, the LLM and
Tavily paths) is authority-agnostic, enforced by invariants the code states about itself and by
self-tests that fail if an authority name or `if exam ==` branch appears in a generic module. Facts
are never shared between exams: content isolation drops a sibling exam's document before extraction,
and data isolation proves byte-for-byte that building one exam changes no other.

The two caveats are **completeness**, not safety:

1. **The offline pipeline is not wired end-to-end into one command.** Discovery → identity →
   extraction → evidence → semantic → isolation-check → report runs as one CLI; the publication
   **gate**, **merge/revision**, universal-**schema** projection, **atomic publish**, and the **Qwen
   verification** layer are implemented, individually universal, and tested, but invoked only by
   their own tests, not by the orchestrator. Publishing to `data.ts` remains a deliberate staged
   human step (by design across every prior phase).
2. **One UI section misrepresents absence as official** (§12 Exam Day) and a second synthesizes a
   fallback (§16 Official Links). These are the only places the UI's honesty discipline lapses.

Nothing unsafe is auto-published, because nothing is auto-published at all.

---

## 2. Universal pipeline audit (Step 2)

Each stage exists as a single-responsibility, authority-agnostic module. "Wired" = invoked by the
runnable CLI (`python -m tools.exam_builder "<exam>"`).

| Stage | Location | Output / states | Universal | Wired into CLI |
|---|---|---|---|---|
| DISCOVERY (authority resolution) | `resolve.py` `resolve()`, `search.py` | `ResolvedExam` / `SearchUnavailable`, `LookupError` | yes | ✅ |
| IDENTITY-A (authority ambiguity) | `ambiguity.py` `decide()` | `RESOLVED / AMBIGUOUS_AUTHORITY / INFRASTRUCTURE_FAILURE / UNRESOLVED` | yes | ✅ |
| IDENTITY-B (content identity) | `identity.py` `verify()` | `MATCH / MISMATCH / AMBIGUOUS` | yes | ✅ (`build.py:203`) |
| EXTRACTION + EVIDENCE | `evidence.py`, `semantic.py` | `Extracted`; `EvidenceStatus VERIFIED/NOT_IN_SOURCE/UNCHECKED` | yes | ✅ |
| SEMANTIC | `semantic.py` `extract()` | cue-scored `Extracted \| None` | yes | ✅ |
| COVERAGE (gate precondition) | `contract.py` `coverage_from()` | `INTRINSIC / CAN_ANSWER_FROM / NO_SOURCE` | yes | ✅ |
| PUBLICATION GATE | `gate.py` `evaluate()` | `PASS / BLOCK`; `BuildState COMPLETE/PAUSED_INFRASTRUCTURE/FAILED` | yes | ⚠️ tested only |
| CONFLICT / REVISION | `merge.py` | `ADDED/CONFIRMED/SUPERSEDED/CONFLICTED/UNCHANGED` | yes | ⚠️ tested only |
| SCHEMA (universal model) | `schema.py` `UniversalExam`, `Fact` | `Status VERIFIED/NEEDS_REVIEW/NOT_PUBLISHED/NOT_EXTRACTED` | yes | ⚠️ tested only |
| EXAM ISOLATION + ATOMIC PUBLISH | `publish.py` `stage()/publish()` | `IsolationViolation` on any foreign byte change | yes | ⚠️ tested only |
| PROJECTION to UI | `compat.py` | per-section projectors; drops foreign `exam_id` rows | yes | ⚠️ tested only |
| SEMANTIC VERIFICATION (Qwen) | `verification/verifier.py` `verify()` | `VERIFIED / NEEDS_REVIEW` + `InfraStatus` | yes | ⚠️ adapters+tests only |

The CLI additionally runs `exam_authoring/verify.py run_all()` (id consistency + single-authority)
and aborts with "ISOLATION CHECK FAILED — nothing emitted" on violation.

**Verdict:** the pipeline exists and every stage is universal; it is **partially orchestrated**. The
discovery→report half is one command; the gate→merge→schema→publish→project→Qwen half is a tested
library a human drives. **P1 (architectural completeness), not a safety gap.**

---

## 3. Exam-specific logic audit (Step 3)

Generic `tools/exam_builder/*.py` is **clean**: authority literals (`SSC/UPSC/IBPS/LIC/APPSC`) appear
only in comments, docstrings and test fixtures — never a code branch. `publish.py, merge.py, gate.py,
compat.py, evidence.py, sources_compat.py` contain no authority token at all; `semantic.py` and
others carry them only in comments that warn *against* branching. Self-tests (`test_pyq.py`,
`test_syllabus.py`, `test_pattern.py`) read the reader source and assert no authority token / no
`if exam ==` / `== 'exam-'` / `.startswith('exam-')` branch. `eligibility.py` documents that the old
hard-coded "OBC +3 / SC,ST +5 / PwBD +10" table was **removed** in favour of source extraction.

Classification of every non-comment occurrence:

- **A — legitimate authored data:** the five `data.ts` exam records and their children; authored
  portal/notice URLs; notification-id strings.
- **B — authority adapters (meant to know one authority):** `tools/exam_authoring/adapters/upsc.py`;
  the per-exam UI engines `UPSCPracticeEngine`, `IBPSPracticeEngine`, `APPSCGroup1/2PracticeEngine`.
- **C — generic resolver knowledge:** `LEGACY_EXAM_ID_ALIASES` / `canonicalExamId` (one legacy id);
  `resolve.py` national-portal allowlist; `search.py` `_OFFICIAL_SUFFIXES = ('.gov.in','.nic.in')`.
- **D — dangerous exam-specific business logic in generic infrastructure:** **none in the pipeline.**
  The only D-class items are app/UI **defaults to `exam-ssc-cgl-2026`** (see §17 P2 list). The one
  historically-dangerous default — a missing attempt `exam_id` silently filed under SSC — was already
  fixed to a hard `400` (`app.py:551-553`) and a `sync-all` skip.
- **E — UI compatibility gating (legitimate):** `PRACTICE_BANK_EXAM_ID` gating (SSC-only bank shown
  only for SSC; others get an empty shelf); `PRACTICE_ENGINES` registry + `ExamPracticeRouter` keyed
  by exam id **with no default** (`UnavailablePracticeEngine` fallback).

---

## 4. 17-section coverage matrix (Step 4 + Step 13)

**Only 5 of the 6 named exams exist.** `LIC AAO 2027` has **no record in `data.ts`** and is absent
from `ALL_EXAMS`; it exists only as captured evidence in the offline verification tests. It is a
data gap ("not authored"), not an engine limitation.

Legend: **WP** present-with-provenance · **NP** present-no-provenance · **∅** empty/absent.

| # Section | Backing type carries provenance? | SSC | UPSC | IBPS | APPSC-1 | APPSC-2 |
|---|---|---|---|---|---|---|
| 1 Overview | thin (string) | NP | NP | NP | NP | NP |
| 2 Dates | **yes (req)** | WP 11 | WP 14 | WP 9 | WP 4 | WP 4 |
| 3 Eligibility & Posts | **yes (req)** | WP 18 | WP 23 | WP 1 | WP 3 | WP 3 |
| 4 Application & Docs | mixed (simulator only) | NP | WP | WP | NP | NP (0 steps) |
| 5 Exam Pattern | **yes** | WP +tree | WP +tree | WP +tree | WP no tree | WP no tree |
| 6 Syllabus | **yes (req)** | WP 22 +tree | WP 18 +tree | WP 2 | WP 3 | WP 2 |
| 7 Study Roadmap | thin | NP 8ph | NP 9ph | NP 0ph | NP 0ph | NP 0ph |
| 8 Resources | yes (opt) | WP 38 | WP 32 | NP 1 | NP 1 | NP 1 |
| 9 Practice & PYQs | **yes** | WP 6 +key | WP 8 +paper | WP 1 | WP 1 | WP 1 |
| 10 Mock Tests | inherits §9 | engine | empty(honest) | empty | empty | empty |
| 11 Admit Card | mixed | NP(0 events) | WP 1 | WP 2 | ∅ | ∅ |
| 12 Exam Day | thin | ∅ | ∅ | ∅ | ∅ | ∅ |
| 13 Results & Next Steps | mixed | ∅ | WP 2 | WP 2 | ∅ | ∅ |
| 14 FAQs & Clauses | **yes (req)** | WP 6 | WP 8 | WP 1 | WP 1 | WP 1 |
| 15 Corrigenda | thin | NP 2 | NP 2 | ∅ | ∅ | ∅ |
| 16 Official Portals | thin (inline) | NP 3 | NP 6 | ∅→synth | ∅→synth | ∅→synth |
| 17 Cutoff History | **yes (req)** | WP 16 | WP 24 | WP 2 | WP 1 | WP 1 |

**Engine-cannot-support: none.** Every section has a type and a renderer. `examDayChecklist` (§12)
and `resultNextSteps` (§13) are authored for **0/5** exams. Both APPSC records are single-element
stubs (~300 lines each vs UPSC ~13,600) — thin because extraction hasn't been done, not because the
engine can't hold it. This is the correct "engine supports it / evidence not extracted" distinction,
except where the UI hides it (§14 below).

---

## 5. State-semantics audit (Step 5)

Correct and not conflated, in code:

- `schema.Status` = `VERIFIED / NEEDS_REVIEW / NOT_PUBLISHED / NOT_EXTRACTED`, with the greppable
  invariant `INFRASTRUCTURE_IS_NOT_A_STATUS = True` and the comment "NOT_PUBLISHED is a finding about
  the authority, NOT_EXTRACTED is a to-do about us."
- `gate.evaluate` is asymmetric on purpose: `NOT_PUBLISHED` allowed; `NOT_EXTRACTED / NEEDS_REVIEW /
  MISMATCH / AMBIGUOUS / conflict / schema / typecheck / isolation` all **BLOCK**; a
  `PAUSED_INFRASTRUCTURE` build is **never** rewritten as `NOT_PUBLISHED`.
- Verification `InfraStatus` (`OK / LLM_DISABLED / LLM_UNAVAILABLE / LLM_TIMEOUT / LLM_ERROR /
  LLM_INVALID_RESPONSE`) is deliberately not a factual state; an infra failure is `NEEDS_REVIEW`,
  never `VERIFIED`, never `NOT_PUBLISHED`. Infra failures are **not cached** (`cache.put` stores only
  `InfraStatus.OK`), so a transient outage never sticks as a verdict.

A failed fetch does not become `NOT_PUBLISHED`; an unavailable LLM does not become `VERIFIED`; missing
extraction is not fabricated; insufficient evidence is not `VERIFIED`. **Pass.**

---

## 6. Identity-safety audit (Step 6)

- `identity.verify` → `MATCH / MISMATCH / AMBIGUOUS`; `IdentityCheck.may_supply_facts` is true **only**
  on MATCH ("AMBIGUOUS is not a weak yes"). MISMATCH documents are dropped before extraction; an
  AMBIGUOUS multi-exam document may supply a field only where `field_is_attributable()` confirms the
  span itself names the target. Identity evidence is verified verbatim like any other claim.
- Cycle/year: a document naming the exam for a different year returns MISMATCH; the deterministic
  verifier's `cycle_ok` requires the claimed cycle present and identity held.
- **Authority ambiguity (the APPSC case) is handled correctly:** `ambiguity.decide` returns
  `AMBIGUOUS_AUTHORITY` when two real bodies (Andhra vs Arunachal PSC) are both plausible and the
  supplied name distinguishes neither; the score margin is explicitly **never** used to break the tie
  ("a score gap is a fact about today's search results rather than about which authority was meant").
- `PaperIdentity` is exam · cycle · stage · paper · shift · language; `OfficialQuestion.identity_key`
  is paper **and** number. Exam+cycle is a *cycle*, never a paper identity.

**Pass**, including the APPSC ambiguity the brief called out.

---

## 7. Evidence-safety audit (Step 7)

`deterministic.run_deterministic` requires, before any model call: a source URL, a non-empty span,
the span present **verbatim** in the supplied source text (`normalise_ws(span) in normalise_ws(source)`),
a value when required, and identity+cycle from the source. A snippet with no source document fails
(`span_in_source=False`). A claim whose own text is not in the source is rejected pre-Qwen — verified
in tests (e.g. an "Aadhaar mandatory" FAQ answer absent from the cited clause fails
`span_in_source`). `schema.Fact.is_publishable` requires `VERIFIED` + a value + verbatim evidence, and
`UniversalExam.unsourced_facts()` exists to prove no assertion lacks a source. **No path publishes a
fact without evidence.**

---

## 8. Qwen / LLM safety audit (Step 8)

Path is `deterministic → (only if passed) Qwen semantic → fixed publication rule`, never Qwen →
publish. `verifier.verify`: `VERIFIED == deterministic.passed AND llm.decision == SUPPORTED`; never
keyed on a numeric confidence. A deterministic failure short-circuits — the model is **never
consulted** (proved by `POISON` provider tests across every adapter). Verified properties:

- No outside knowledge / no browsing: the system prompt forbids prior knowledge and inference; the
  template names no authority or exam (universal).
- Strict JSON: `VerificationResult.from_model_json` rejects non-JSON, wrong shape, or a `SUPPORTED`
  whose booleans disagree → `LLM_INVALID_RESPONSE`. `<think>…</think>` stripped before parsing;
  `/no_think` sent.
- Infra failures never cached as success; model-unavailable and malformed both yield `NEEDS_REVIEW`.
- Cross-exam / cross-cycle rejected **before** Qwen (deterministic identity).
- **One framework only:** the entire `verification/` package is imported solely by its own adapters,
  tests and demos — there is no second LLM framework, and no generic pipeline module imports it.

**Pass.** Live replays across phases (results, cutoff, corrigenda, resources, mock, exam-day, faq,
portals) show real evidence → VERIFIED and mismatches → NEEDS_REVIEW, LLM never called on a
deterministic failure.

---

## 9. Tavily / research safety audit (Step 9)

Two Tavily surfaces, both safe:

- `app.py research_search`: `include_domains` is treated as advisory; OFFICIAL scope is **enforced
  server-side** (only `_classify_trust == OFFICIAL` kept, `filteredOut` reported). Findings are stored
  `PENDING_REVIEW` with a `trust_level` (OFFICIAL / TRUSTED_PUBLIC / UNVERIFIED) — **never VERIFIED**.
  Snippets are never treated as official evidence; promotion is a human decision, and reaching
  candidates is a separate deliberate `data.ts` edit.
- `test_research_facts.py` (root, 15 tests, green): a Tavily finding → candidate fact → validate
  (parsed, but "source not reachable" ⇒ **pending**, not verified) → classify → store `status=pending`.
  Unreachable source stays pending; invalid URL rejected; duplicate skipped.

No `Tavily → VERIFIED` path exists. **Pass.**

---

## 10. Revision / conflict audit (Step 10)

`merge.py` refuses rather than resolves: two undated disagreeing readings both become `NEEDS_REVIEW`;
newer is not preferred over older, extracted not over authored; supersession happens only when a
document **says** it revises (RESCHEDULED/POSTPONED/CANCELLED or CORRIGENDUM). `results_merge`
carries ORIGINAL → REVISED → CANCELLED → SUPERSEDED and **keeps** the superseded declaration; two
disagreeing declarations with no revision between are CONFLICTED (neither wins on timestamp).
`syllabus_revisions` and `cutoffsHistory` preserve old values; the UI struck-through + corrigendum
badge shows superseded dates without ever making one the "next" milestone. **Pass** — old/new remain
traceable.

---

## 11. Isolation proof (Step 11)

Two independent layers, both proved by running code:

- **Content isolation** (`test_contamination.py`, run this phase — green): the real builder is run over
  a target notice plus a *sibling* exam's notice (same authority, same year, a different fee). With the
  content gate the sibling is judged `MISMATCH` on its own text and its fee never reaches the record
  (the field is honestly `NOT_EXTRACTED`); with the gate disabled the sibling's fee contaminates —
  demonstrating the gate is load-bearing and that data-isolation alone cannot detect the problem.
- **Data isolation + atomic publish** (`publish.py`, run this phase): fingerprint every exam →
  `stage()` writes only to `.exam_staging`, never live → `assert_only_this_exam_changed` raises
  `IsolationViolation` on any foreign add/remove/byte-change → `publish()` re-checks against live-now
  and typechecks with rollback. Empirical run: staging a brand-new synthetic exam left **all 5**
  existing exam hashes byte-identical and added only the new id.

No cross-exam ids, evidence, or citations; `compat` projectors drop any row whose `exam_id` ≠ the
requested exam; `key={exam.id}` remounts practice engines so no question/timer/score survives a switch.
Runtime records are exam-scoped in SQL (`mock-attempts?exam_id=`), and a mismatched row is dropped and
logged, not relabelled. **Pass.**

---

## 12. Unknown-authority universality test (Step 12)

Demonstrated, not asserted: a synthetic never-seen exam (`exam-zpsc-clerk-2027`) staged cleanly through
`publish.stage` with **no code branch added**, adding only its own id and touching no other exam. The
resolver is tested against fictional authorities (`test_ambiguity.py` uses `zpsc.gov.in` / `zrb.gov.in`).
A new authority needs: resolver/configuration, source discovery, official-domain evidence, extracted
source data — **not** an `if exam == NEW` branch. The one caveat is `exam_authoring/verify.py`'s
`_FOREIGN_EXAM_TOKENS`, which enumerates four exam families for a *report-only* cross-mention check; a
fifth family degrades to no-op (not to wrong behaviour). **Pass**, with that report-only seam noted (P2).

---

## 13. Six-exam real-data matrix (Step 13)

See §4. Summary: SSC and UPSC are deeply authored; IBPS is a thin-but-real record; both APPSC records
are single-element stubs; **LIC AAO 2027 is not authored at all.** These are extraction/authoring
gaps, correctly distinguishable from "engine cannot support" — every section has a type and renderer.
`examDayChecklist` and `resultNextSteps` are authored for no exam.

---

## 14. UI / data-consistency audit (Step 14)

Most sections honour the honesty rule — §4, §6, §7, §9, §10, §11, §13, §15 render explicit
"GovOS has not read / not authored" empty states, and `compat.verification_level_for` grants the
`OFFICIALLY_VERIFIED` badge **only** to `Status.VERIFIED` (everything else → `UNDER_VERIFICATION`,
superseded → `SUPERSEDED`). Two lapses:

- **§12 Exam Day — `ExamDayChecklistSection` (`ui.tsx:13624`). P1.** The component never reads
  `exam.examDayChecklist`; it always renders a hardcoded generic CBT checklist ("e-Admit Card",
  "biometric iris/thumb scan", "Computer Lab & CBT Protocols", "3–5 year debarment") under a
  `badge-verified` **"OFFICIAL EXAM-DAY PROTOCOL"** + `{exam.code}` (`:13797-13802`). Since the field
  is empty for all five exams, every exam shows the identical generic content **as if official and
  exam-specific** — and it is factually wrong for UPSC CSE Mains (offline descriptive; no CBT lab) and
  the APPSC descriptive papers. This is the one place the UI implies OFFICIAL over a `NOT_EXTRACTED`/
  absent field — squarely the Step-5/Step-14 red line.
- **§16 Official Portals (`ui.tsx:19255-19257`). P2.** When `officialLinks` is empty (IBPS, both
  APPSC) the section synthesizes a one-card directory from `authorityName` + `officialDomain` instead
  of an honest empty state. The URL is the authority's real domain, so it is derived rather than false
  — a lesser offence than §12, beside an honestly-empty Corrigenda section.

No cross-exam leakage, fake counts, or stale hard-coded counts were found (answer-text counts are
`fillCounts()` placeholders from the register).

---

## 15. Persistence / deployment audit (Step 15)

- **No Firebase** — GovOS is SQLite (`govos.db`, committed as seed) + `localStorage` (effective source
  of truth); every SQLite call is fire-and-forget so the app works fully offline. The brief's Firebase
  question is **N/A**.
- Flask serves the single self-contained `dist/index.html` + API on one port (SPA fallback). Vercel
  note (not a blocker for the current single-user/local-model design): serverless SQLite writes are
  ephemeral/per-instance; the app is single-user by construction (`default-candidate`).
- Secrets/artifacts: `.gitignore` excludes `.env`, `.env.*`, `*.gguf`, `dist/`, `.exam_staging/`,
  `.exam_cache/`, `.exam_manifests/`, `*.pdf`, `node_modules/`. No `.env`, GGUF, or `node_modules`
  tracked. `TAVILY_API_KEY` and the Qwen GGUF are external and user-supplied.
- **`import app` mutates `govos.db`** (init adds a table) — restored with `git checkout -- govos.db`
  after every run this phase; a real operational footgun (P2) but not a code defect.

No migration or deployment redesign performed (out of scope).

---

## 16. Test coverage (Step 16)

Run this phase, all green:

- **exam_builder unittest modules (12):** 215 tests — resolver/discovery/identity/ambiguity/evidence/
  semantic/pattern/syllabus/pyq/admit-card/results + the 9 Qwen-verification suites (results, cutoff,
  corrigenda, resources, mock, exam-day, faq, portals, roadmap).
- **exam_builder standalone `main()` modules (23):** all pass — including `test_contamination`
  (isolation), `test_publish`, `test_gate`, `test_merge`, `test_schema`, `test_identity`,
  `test_ambiguity`.
- **`test_research_facts.py` (root):** 15 tests — the Tavily research-fact validation path.
- **`verification/test_local_llm.py`:** live-server smoke test, correctly skipped without a running
  Qwen (reports rather than false-passes).

Coverage by concern: resolver ✓, discovery ✓, identity ✓ (incl. ambiguity), extraction/evidence ✓,
Qwen ✓, publication gate ✓, isolation ✓ (content + data), persistence ✓ (research-facts).
**Untested by an automated harness: the frontend** — there is no UI/React test harness, so UI honesty
(e.g. §12) cannot be regression-proved in-repo. This is why the §12/§16 UI fixes fail the phase
fix-gate. The build pipeline is proven at the module level but has **no end-to-end orchestration test**
(because there is no end-to-end orchestrator).

---

## 17. P0 / P1 / P2 / P3 issue list (Step 17)

**P0 (release blocker / universal-safety violation): none.** No path shares facts between exams,
publishes without evidence, treats a fetch failure as NOT_PUBLISHED, or an unavailable LLM as VERIFIED.

**P1 (important architectural / correctness):**
- **P1-a — §12 Exam Day badges absent/generic content as "OFFICIAL EXAM-DAY PROTOCOL {exam.code}"**
  (`ui.tsx:13624`, `:13797`). Verified; UI implies OFFICIAL over a `NOT_EXTRACTED` field, identical
  and wrong across exams. *Recommended minimal fix (not applied — see gate):* render
  `exam.examDayChecklist` when authored; when absent, keep the generic guidance but relabel it
  honestly (e.g. "General CBT guidance — not {exam}-specific") and drop the `badge-verified` +
  `exam.code` badges, matching the honest empty states of §11/§13/§15.
- **P1-b — the offline pipeline is not orchestrated end-to-end** (gate/merge/schema/publish/compat/Qwen
  are tested libraries, not CLI-invoked). Fixing = building an orchestrator = redesign, out of scope
  for this phase. Publishing stays a deliberate human step, which is why nothing unsafe escapes.

**P2 (robustness / consistency):**
- SSC-default fallbacks in generic paths: `app.py:450` & `:604` (profile target → SSC), `app.py:48`
  (schema column default), `services.ts:737` (`getTrackedExams` → SSC), `main.tsx:449` (provenance
  link → `ssc.gov.in`). Product defaults toward the reference exam; they set a single user's
  preference and never share facts, so not P1. Recommend applying the attempts-endpoint discipline
  (explicit id or honest neutral) if made stricter later.
- §16 Official Links synthesized fallback card (`ui.tsx:19255`).
- `verify.py _FOREIGN_EXAM_TOKENS` enumerates four exam families (report-only).
- `import app` mutates the committed `govos.db`.

**P3 (future work):** author `examDayChecklist` / `resultNextSteps` per exam; author the LIC AAO 2027
record (the engine supports it); deepen IBPS/APPSC; wire the Qwen verifier and gate into a single
publish command; add a minimal frontend test harness so UI honesty is regression-testable.

---

## 18. Fixes made (Step 18 continued)

**None.** No finding satisfies the full fix-gate (clear evidence · small · no redesign · functionality
preserved · **regression-provable**): P1-a is UI-only and cannot be regression-proved without a
frontend harness this repo lacks; P1-b needs a redesign; the P2 items are not release-blocking. Per
the phase's explicit rule ("Only fix a P0/P1 issue if … regression tests can prove the fix"; "Do NOT
fix P2/P3"; "the UI must … only change if necessary"), the correct action is to report. This mirrors
the codebase's own precedent (the §12 generic content and the SSC-dates discrepancy were both
documented for the user to decide rather than silently changed).

---

## 19. Exact files changed

Only this report: `FINAL_UNIVERSAL_ENGINE_AUDIT.md` (new). No source, type, data, UI, `app.py`,
`govos.db`, `index.html`, or test file was modified.

## 20. Final test counts

215 exam_builder unittest tests + 15 research-facts tests = **230 automated tests pass**; **23**
standalone `main()` modules pass (incl. content-isolation and data-isolation proofs); 1 live-only LLM
smoke test correctly skipped. Empirical proofs run green: content contamination gate, and data
isolation + unknown-authority staging (5/5 hashes unchanged).

## 21. tsc result

`npx tsc --noEmit` — **clean, 0 errors.**

## 22. build result

`npm run build` — **success**, `dist/index.html` 2,529 kB (gzip 791 kB), self-contained.

## 23. Final commit hash

`<filled on commit>` — audit report only.

## 24. Push result

`<filled on push>`.

## 25. Remaining known limitations

- The universal engine is proven **stage-by-stage and isolation-wise**, but **not orchestrated
  end-to-end**; publishing is a deliberate human step (P1-b). This is a completeness limit, not a
  safety one — nothing is auto-published.
- **§12 Exam Day presents generic content as official/exam-specific** (P1-a) — the one UI honesty
  defect; a precise minimal fix is specified above, deferred because it is not regression-provable in
  this repo.
- **LIC AAO 2027 is not authored**; both APPSC records are single-element stubs; `examDayChecklist`
  and `resultNextSteps` are authored for no exam. All are extraction gaps the engine can hold, not
  engine limits.
- **No frontend test harness**, so UI honesty is outside automated regression coverage.
- Do not claim "100% universal": on the audit evidence, GovOS is **universal in its facts, identity,
  evidence, isolation and verification, and partially-orchestrated in its build pipeline**, with two
  bounded UI honesty exceptions. That is the accurate verdict.
