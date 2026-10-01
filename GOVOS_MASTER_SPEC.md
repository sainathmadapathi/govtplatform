# GOVOS MASTER SPECIFICATION — The North Star

> Authoritative product specification for GovOS. Read this before making any change.
> It records BOTH the product vision (the required future state) and the actual current state
> of the repository, and keeps them clearly distinguished. It is not a changelog and not a
> notes file — see **Change Control**.

- **Status legend used throughout:**
  `VISION` (required future state) · `IMPLEMENTED` · `PARTIAL` · `NOT YET` · `LIMITATION`.
- **Repository state captured at:** git HEAD `82a3940` (this document adds nothing to the code).
- **Source of truth for current state:** the repository itself, verified by inspection — not
  prior history. Where this document says IMPLEMENTED it names the file that proves it.

---

## 0. Reading order

1. **Product Vision** (what GovOS is for).
2. **Non-Negotiable Requirements** (rules that may never be traded away).
3. **Architecture Principles** (how the system must be built to honour the rules).
4. **The 17-Section Workspace** (the user-facing contract).
5. **Current Implementation** (what actually exists today, with evidence).
6. **Current Gaps** (P0–P3, ranked by vision impact).
7. **Future Roadmap** (7 outcome-phases).
8. **Acceptance Tests** (how success is judged).
9. **Development Rules**, **Change Control**.
10. **North-Star Check** & **When Asked to Implement a Feature** (run before every change).
11. **North Star** (the closing statement).

---

# PART A — PRODUCT VISION

## A.1 What GovOS is

GovOS exists so that **a completely naive student** — no direction, no knowledge of government
examinations, knowing only *"I want to write a government exam"* — can enter and receive a
**clear, simple, trustworthy path**.

It must take a student from *"I don't know anything about government exams"* to *"I understand my
options, I understand the exam I selected, I know what to do now, I know what happens next, and
GovOS will keep me informed throughout the exam lifecycle."*

GovOS is specifically a **government-exam discovery, guidance, information, preparation, tracking,
and next-step platform**. It is **not** a generic productivity app, education platform, AI
assistant, career platform, or exam database, and must never be reinterpreted as one.

## A.2 The core product promise (the lifecycle)

```
DISCOVERY → UNDERSTANDING → ELIGIBILITY → EXAM SELECTION → APPLICATION →
PREPARATION → PRACTICE → EXAM → ADMIT CARD / CITY INTIMATION → ANSWER KEY →
RESULT → NEXT STAGE → FINAL OUTCOME → NEXT STEP / NEXT OPPORTUNITY
```

The user should need no prior knowledge of the exam ecosystem. The experience must be simple,
clear, guided, trustworthy, low-complexity, evidence-backed, exam-specific, and continuously
useful across the whole lifecycle.

## A.3 What a student must be able to learn

Which exams exist; which are relevant and **why**; required qualification; whether they are
eligible; posts; what the exam is about; the recruitment process; when/how to apply; documents;
fee; pattern; syllabus; how to prepare; resources; how to practice; previous-year papers; mock
tests; city intimation/admit card; exam-day conduct; answer key; result; cutoff/history where
officially available; what happens after the result; the next stage; what to do next; and future
opportunities.

---

# PART B — NON-NEGOTIABLE REQUIREMENTS

These are constitutional. A task that conflicts with any of them must stop and surface the
conflict (see Development Rules) rather than proceed.

## B.1 Zero AI-generated factual data — **NO EVIDENCE = NO FACT**

- **0% AI-generated factual examination data.** Claude (the installed Claude CLI, reached only
  through the gateway in `tools/claude_cli/`; see `CLAUDE_CLI_INTEGRATION.md`) may be internal
  machinery (discovering candidate sources, classification, extraction proposals that carry exact
  quotations, structure detection, semantic comparison, evidence verification, contradiction
  detection, completeness judgement, converting *already-supported* information into structured
  fields, and clearly labelled GovOS guidance). Claude is **never** the factual authority.
- Claude must **never invent** exam dates, eligibility, age limits, vacancies, posts,
  qualifications, fees, procedures, patterns, syllabus, cutoffs, results, admit-card dates, answer
  keys, official links, stages, rules, or clauses.
- If a claim cannot be supported by a source, it must not become published factual information.

## B.2 Source authenticity

- Core facts come from **official primary sources**, in priority order: authority website →
  recruitment portal → notification → official PDF/document → corrigendum/revision →
  result/answer-key/admit-card portal → other official systems of the responsible authority →
  trusted secondary sources only when necessary and **clearly labelled**.
- Every user-facing factual item should carry an **evidence trail** and be able to answer: where
  it came from, which official source supports it, which exam/cycle the source belongs to, the
  exact supporting evidence, when it was verified, and whether it has been superseded.
- Search/discovery (Claude's web discovery, search engines, coaching sites, YouTube, etc.) **find**
  sources; they are **not** factual authorities. `Claude-proposed source → VERIFIED FACT` must never
  exist: every URL Claude proposes is only a candidate until deterministic checks (syntax, public
  address, reachability, redirects, authority ownership, document and exam/cycle identity) and a human
  have judged it, and it is never official because Claude said so.

## B.3 Trust & evidence chain

```
SOURCE → SOURCE IDENTITY → EXAM/CYCLE IDENTITY → RELEVANT EVIDENCE →
EXTRACTION → VALIDATION → VERIFICATION → PUBLICATION
```

A fact must never be published because Claude said it, a search result said it, a secondary site
said it, the value "looks right," another exam has the same rule, or an older cycle had the value.

## B.4 Isolation

Cross-exam contamination is prohibited. SSC data must never appear under UPSC; one cycle's data
must never silently become another's; one recruitment/post/stage/paper's data must never silently
become another's.

## B.5 State semantics never collapsed

`NOT_PUBLISHED ≠ NOT_EXTRACTED ≠ SOURCE_UNAVAILABLE ≠ FETCH_FAILURE ≠ EXTRACTION_FAILURE ≠
VERIFICATION_FAILURE`. Infrastructure failures (`NETWORK_UNAVAILABLE`, `SOURCE_FETCH_FAILURE`,
`CLAUDE_DISABLED`, `CLAUDE_CLI_NOT_INSTALLED`, `CLAUDE_CLI_NOT_AUTHENTICATED`, `CLAUDE_CLI_BUSY`,
`CLAUDE_CLI_TIMEOUT`, `CLAUDE_CLI_FAILED`, `CLAUDE_INVALID_OUTPUT`, `CLAUDE_SCHEMA_REJECTED`,
`PARSER_FAILURE`, `BUILD_FAILURE`) must
never become "official information does not exist," never become `NOT_PUBLISHED`, `NOT_APPLICABLE`,
or `NOT_RELEASED`. Engineering states stay internal; users see plain language
("Not released yet by the authority").

## B.6 Failure safety & Claude safety

Deterministic validation runs **before** semantic (Claude) validation. Claude receives only the
claim, the exact evidence, and source metadata, each inside a delimited data block, never outside
knowledge, and every reply is validated against a strict schema and re-checked by code that does not
trust it (a proposed value is kept only if its quotation is printed verbatim in the source text GovOS
fetched itself). Claude failures fail safely (NEEDS_REVIEW, never VERIFIED, never a fabricated fact,
never `NOT_PUBLISHED`). Claude can **never directly publish**, and its job results wait for a human or
the publication gate.

## B.7 Preservation

Missing information must never overwrite existing information with empty values. A partial machine
build must never erase human-authored content, comments, provenance, or shared structures.
Existing exam records remain isolated. Historical truth is never silently overwritten — old/new
values and effective dates are preserved.

## B.8 Security / trust

Never expose API keys; never commit `.env` or model files; never trust external/lookalike domains
without validation; never allow cross-exam contamination; never publish unsupported facts; never
silently modify historical facts.

## B.9 Scope discipline

A feature must directly support the government-exam journey. GovOS must never become a generic
chatbot, productivity app, social network, LMS, career platform, news aggregator, or content
platform.

## B.10 Naive-student-first & clear direction

GovOS is designed for a student who begins with **almost no knowledge** of the government-exam
ecosystem. The product must:
- explain things in **plain language**, guide rather than assume prior knowledge, and reduce
  ambiguity at every step — telling the user what exams exist, which they can consider, **why** an
  exam is relevant, what to do **now**, and what happens **next**;
- make every screen answer *"What does this mean for me?"* and, where appropriate, *"What should
  I do next?"*;
- stay simple, clear, consistent and low-complexity, using progressive disclosure and clear next
  actions, with source/evidence available on demand;
- **never expose engineering/system states to naive students** (see B.5); avoid unnecessary
  jargon, unexplained abbreviations, confusing dashboards, configuration burden, and information
  overload.

## B.11 Completeness, and no false completeness

- **Completeness is a product requirement, not just a schema.** Every applicable section must be
  populated with **actual official information whenever it exists**. When a fact is missing, the
  system must **widen its search across legitimate official sources** (exam page → notification →
  official syllabus/document → recruitment portal → linked official documents → relevant PDFs),
  then extract and verify it. It may conclude "genuinely unavailable" **only after** those paths
  are exhausted.
- `NOT_EXTRACTED` is **never** an acceptable final state when the information exists and can
  reasonably be acquired.
- **Completeness must never be faked.** No generic filler, no other exam's information, no prior
  year's value without proving applicability, no Claude knowledge, no assumptions, no guessed values,
  ever — to make a section look complete.

## B.12 Full lifecycle & next-step guidance

- GovOS must cover the **whole exam lifecycle** where applicable — Notification → Application →
  Correction → City Intimation → Admit Card → Exam → Answer Key → Result → Cutoff → Next Stage →
  Final Result → Next Step — and must not stop at preparation.
- After a result it must explain **what happens next**, based on official recruitment information,
  and must clearly distinguish an **OFFICIAL NEXT STEP** (sourced) from **GENERAL PREPARATION
  GUIDANCE**. Career advice must never be presented as an official recruitment instruction; every
  next-step *claim* must be sourced.

---

# PART C — ARCHITECTURE PRINCIPLES

**Architecture exists to serve the product vision (Parts A–B); the goal is never to demonstrate
architecture.** Every principle below is a means to authentic, complete, clear, automatic
government-exam guidance for a naive student — not an end in itself.

## C.1 Universal engine, not per-exam code

**Universal** means the infrastructure can represent different government examinations **without
exam-specific business logic**. It does **not** mean every exam has identical rules/stages/fields.
The model must support differences in authorities, recruitment types, posts, stages, papers,
subjects, languages, scoring, negative marking, eligibility, age/qualification rules, application,
documents, timelines, admit-card systems, result stages, cutoffs, and portals. **The source
defines the fact.**

Prohibited: `if exam == "SSC"` / `if authority == …` branches in generic infrastructure; per-exam
modules like `rrb_ntpc.py`; assuming Tier-1/Tier-2, interviews, negative marking, fixed age
relaxation, uniform qualification/application/admit-card/cutoff/answer-key/paper structures. A
documented, unavoidable external-system **adapter** is the only exception, and it must not replace
the universal engine or become a manually authored exam database.

**A generic schema alone does not make GovOS universal.** Neither does a generic renderer, nor a
collection of adapters. GovOS is universal **only when a previously unsupported government exam can
be given to the system and the system automatically discovers, acquires, verifies, structures and
publishes its information without exam-specific business logic** (Acceptance Test 2, the primary
engineering acceptance test). Universality is **proven by onboarding an unknown exam**, never
asserted from the shape of the schema.

## C.2 The automatic acquisition pipeline

```
EXAM QUERY → RESOLUTION → OFFICIAL SOURCE DISCOVERY → SOURCE COLLECTION →
SOURCE IDENTITY → DOCUMENT UNDERSTANDING → UNIVERSAL EXTRACTION →
DETERMINISTIC VALIDATION → EVIDENCE VERIFICATION → CONFLICT/REVISION DETECTION →
CANONICAL EXAM RECORD → COMPLETENESS CHECK → PUBLICATION GATE → SAFE PUBLISH → UI →
CONTINUOUS MONITORING
```

Normal exam onboarding must not depend on manually entering every fact. Human intervention is an
exception mechanism for genuine failures.

## C.3 Canonical data & ownership

There must be a canonical representation of an examination supporting identity, authority, cycle,
posts, vacancies, eligibility, application, fees, dates, pattern, syllabus, PYQs, answer keys,
admit cards, results, cutoff, corrigenda/revisions, portals, resources, FAQs, exam-day, next
steps, source evidence, provenance, status/confidence, and historical revisions. It must support
**partial updates** without erasing existing data, keep records **isolated**, and represent
**human vs machine ownership/provenance**. Machine data must not overwrite verified human-authored
information without a valid evidence-based merge.

> **The overlay model is a means, not the goal.** The canonical-ownership approach the audit
> identified — an authored seed **plus** additive, provenance-carrying, reversible machine
> overlays with revision history and a safe merge (`CANONICAL_DATA_AUDIT.md`) — is an
> *implementation* means to this requirement. It must never be mistaken for the product vision.
> The vision stays: automatic, authentic, complete, clear government-exam guidance; the overlay
> architecture exists only to update facts safely without destroying authored content.

## C.4 Completeness is a goal, not a schema

Having 17 sections in a schema is not the objective. For every exam, GovOS should find and populate
all applicable information actually available from authoritative sources, continuing to search
legitimate official sources (exam page → notification → syllabus document → linked docs → portal →
relevant PDFs) before concluding information is genuinely unavailable. `NOT_EXTRACTED` is not an
acceptable final state when the official information exists and can reasonably be acquired. (This
is also the non-negotiable B.11.)

## C.5 Definition of "complete" (from the student's perspective)

An exam is **not** "complete" merely because a record exists, the schema validates, the renderer
works, some sections contain data, or the tests pass. **An exam is complete when the student
receives the meaningful official information needed for the applicable stages of that exam's
lifecycle** — and the system has exhausted reasonable official-source discovery before declaring
anything unavailable. Completeness is judged from the student's perspective, never the engineer's.

---

# PART D — THE 17-SECTION WORKSPACE (user-facing contract)

The 17 sections are a **user-experience** structure, not 17 hardcoded data systems; one universal,
data-driven engine feeds them. For each: **Purpose · Authoritative sources · Evidence requirement ·
When unpublished · Never fabricate · Student experience.** (Stable deep-link ids in parentheses;
UI order differs from the numbering below — see `EXAM_SECTIONS`/`REFERENCE_SECTIONS` in `ui.tsx`.)

1. **Overview** (1) — what the exam is, authority, level, vacancies, selection process. Sources:
   notification/portal. Unpublished → say so. Never fabricate the authority or vacancy count.
2. **Dates & Timeline** (2) — every milestone with date, tentativeness, supersession. Sources:
   notification + authority examination page (the page outranks the PDF for extendable dates).
   Unpublished → "not announced yet." Never invent or un-strike a superseded date.
3. **Eligibility & Posts** (3) — age, qualification, category relaxations, posts, pay. Sources:
   notification. Evidence: per rule/post provenance. Never invent an age band or a post's group.
4. **Application & Documents** (4) — how to apply, portal, fields, documents, fee, pitfalls, an
   exam-specific mock form where authored. Sources: notification + portal. Never invent a fee or
   a procedure; never point one exam at another's form.
5. **Exam Pattern** (5) — stages/papers/sections at the authority's own depth and vocabulary,
   marks, negative marking, timing. Sources: scheme in the notification. Never assume Tier-1/2.
6. **Syllabus** (6) — topics at the authority's depth, weightage where derivable (marked as
   derived), tree + flat list + map. Sources: syllabus document/notification. Never fabricate a
   topic; a verifier revision overlays the seed with provenance.
7. **Study Roadmap** (7) — a preparation plan derived from the exam's own pattern/syllabus and the
   candidate's inputs. Clearly **guidance**, not an official instruction. Never present as official.
8. **Resources** (8) — links only (no stored material), official sources first, coaching content
   clearly labelled non-official, live feeds/link-health. Never store material; never badge
   coaching as official.
9. **Practice & PYQs** (9) — the authority's own previous papers (identity-exact) and, separately,
   clearly-labelled GovOS-authored practice. Never present authored questions as past papers;
   never produce an answer from another year's/shift's key.
10. **Mock Tests** (17) — full/section/topic practice built from the exam's own scope; GovOS-authored,
    labelled as such. Never label generated items official.
11. **Admit Card** (14) — city-intimation vs admit-card vs exam date kept distinct; release as a
    date or a rule; portal (not a homepage as a download link). Never claim availability GovOS
    cannot see behind a login.
12. **Exam Day** (15) — the authority's own exam-day instructions with provenance. When none are
    extracted, an **honest empty state** ("not yet extracted … a gap here, not a claim the
    authority published none"). Never present generic content as this exam's official protocol.
13. **Results & Next Steps** (16) — official result declarations (sourced) + a candidate
    self-assessment; official next step distinguished from general guidance. Never fabricate a
    next step or read a candidate's login.
14. **FAQs & Official Clauses** (11) — answers each tied to an official clause + provenance.
    Never answer beyond what a clause supports.
15. **Corrigenda Log** (13) — official revisions with old/new and effective date. Never hide or
    silently apply a change.
16. **Official Portals & Links** (12) — official links tied to exam/cycle/authority/purpose, with
    officiality decided **deterministically by domain** (not `.gov.in`-only; IBPS/LIC use
    non-`.gov.in`). Never label a homepage as a download/application link; never fabricate a URL.
17. **Cutoff History** (10) — official cut-offs by category/year with the year stated. Never
    present a prior year's cut-off as the current cycle's.

---

# PART E — CURRENT IMPLEMENTATION (repository state, with evidence)

## E.1 Shape of the system

- **Frontend:** a single React 18 + TypeScript SPA — five source files (`src/main.tsx`,
  `types.ts`, `data.ts`, `services.ts`, `ui.tsx`) plus one hero image — built by Vite
  (`vite-plugin-singlefile`) into one self-contained `dist/index.html`. `IMPLEMENTED`.
- **Backend:** `app.py` (Flask + SQLite `govos.db`), no ORM, no auth, single-user by design
  (`default-candidate`). Serves `dist/index.html` + the API on one port. `IMPLEMENTED`.
- **Persistence:** `localStorage` is the effective source of truth for candidate state; SQLite is a
  committed seed **and** runtime store (candidate data, two exam-fact overlays, feed caches,
  research). **No Firebase.** `IMPLEMENTED` (see `CANONICAL_DATA_AUDIT.md`).
- **Deployment:** no `vercel.json`/`Procfile`/CI. `npm run build` → static single-file; `python
  app.py` serves it. `PARTIAL` (no configured production/serverless deploy; SQLite writes are not
  serverless-safe).
- **Offline exam-builder pipeline:** `tools/exam_builder/` (resolve, discover, search, identity,
  ambiguity, evidence, semantic, contract, gate, merge, schema, publish, compat, orchestrate,
  render, + per-domain readers: dates, eligibility, pattern, syllabus, pyq, results, admit_card,
  application, stages, tables) and `tools/exam_authoring/` (adapters, extract, emit, verify).
  `IMPLEMENTED` as a library; `PARTIAL` as an end-to-end automatic onboarding tool (see gaps).
- **Claude verification:** `tools/exam_builder/verification/` (deterministic → claude_verifier →
  verifier, adapters, cache) over the single gateway `tools/claude_cli/` (the installed Claude CLI,
  non-interactive, server-side, behind a persistent job queue). Deterministic-first; VERIFIED ==
  det.pass AND SUPPORTED; infra failures never VERIFIED/never cached. `IMPLEMENTED` as a library
  and wired into the build through `use_claude`.

## E.2 The exam register (authored data)

- **5 exams in `ALL_EXAMS`** (`data.ts`): `SSC_CGL_2026` (deep), `UPSC_CSE_2026` (deep),
  `IBPS_PO_2026` (thin but real), `APPSC_GROUP1_2026` and `APPSC_GROUP2_2026` (single-element
  stubs). **LIC AAO 2027 is NOT in the register** — it exists only as evidence in verification
  tests. `IMPLEMENTED` (authored, hand-written, provenance-carrying).
- **All authored facts are human-authored TypeScript**, cited with `DataProvenance`. **No machine
  build has published to `data.ts`.** This satisfies B.1 today by construction.

## E.3 The 17-section workspace

- All 17 sections exist with types, renderers, and honest empty states for most
  (`EXAM_SECTIONS`/`REFERENCE_SECTIONS` in `ui.tsx`; section ids are stable deep-link vocabulary).
  `IMPLEMENTED` (UI + types + per-exam data for SSC/UPSC; thin for IBPS/APPSC).
- **Provenance-backed domains:** dates, eligibility/posts, pattern, syllabus, resources (optional),
  practice/PYQs, FAQs, cutoffs, and the sourced halves of admit-card/results. **Thin (no
  provenance) domains:** overview, roadmap, exam-day, corrigenda, official-links.
- **Exam-Day** now renders honestly (verified this session): authored checklist when present, else
  an honest "not yet extracted" state; the false "OFFICIAL EXAM-DAY PROTOCOL" badge was removed.
  `IMPLEMENTED`.

## E.4 Naive-user discovery & guidance

- `ExamFinder` (hero + search + popular chips), a deterministic recommendation engine
  (`computePersonalizedRecommendations` with explained "why"), and `EligibilityCalculator`
  (per-post age/qualification/category, explained). `IMPLEMENTED` — but only over the **5 authored
  exams** (`PARTIAL` against the vision of the whole ecosystem).
- All candidate-facing "AI" (the three chats, the resource navigator, recommendations) is
  **deterministic local logic — no model calls.** `IMPLEMENTED` and consistent with B.1.

## E.5 Lifecycle tracking & updates

- Time-aware timeline (`ExamCalendar`, section 2) with supersession; personalized notifications
  (`generatePersonalizedNotificationsForTrackedExams`); live official boards (SSC notice board,
  UPSC What's New), channel feeds, and scheduled link-health in `app.py`. `IMPLEMENTED` for the
  authored exams.
- **Runtime exam-fact overlays exist:** `syllabus_revisions` and `resource_additions` (govos.db)
  are merged over the seed at runtime by `applySyllabusRevisions` / `additionToResource` —
  non-destructive, provenance-carrying, reversible. `IMPLEMENTED` (the precedent for safe merge).

## E.6 The offline universal pipeline & verification

- **Orchestrated end-to-end** (`orchestrate.py`): resolve → discover → identity → extract →
  (optional Claude) → gate → staging → atomic publish, dry-run by default, distinct failure states,
  no exam-specific branch. `IMPLEMENTED` (see `ORCHESTRATION_AUDIT.md`).
- **Identity & isolation:** content identity (`identity.py`, MATCH/MISMATCH/AMBIGUOUS, drops
  MISMATCH before extraction), authority ambiguity (`ambiguity.py`, e.g. Andhra vs Arunachal PSC →
  AMBIGUOUS_AUTHORITY, never a margin guess), data isolation (`publish.py`, byte-fingerprints every
  exam, refuses foreign change). `IMPLEMENTED`.
- **Publication gate** (`gate.py`): NOT_PUBLISHED allowed; NOT_EXTRACTED/NEEDS_REVIEW/MISMATCH/
  conflict/infra all BLOCK; infra never rewritten as NOT_PUBLISHED. `IMPLEMENTED`.
- **Renderer & safe publish** (`render.py` + `exam_authoring/emit.py`): a complete, status-aware,
  provenance-carrying `Exam` block; preservation guard appends NEW exams and **refuses to overwrite
  authored records**. tsc-validated against the real interface this session. `IMPLEMENTED` for new
  exams.
- **Claude discovery** (`app.py` + `tools/claude_cli/discovery.py`): discovery only, as a background
  job. Claude proposes candidate URLs; the server checks each deterministically and enforces the
  OFFICIAL scope; findings are stored `PENDING_REVIEW` with a server-computed trust level, **never
  VERIFIED**; a manifest records everything proposed and everything rejected; `research_facts`
  validation stays pending when a source is unreachable. Claude's fact reading keeps a value only with
  a quotation found verbatim in the fetched page. `IMPLEMENTED` and consistent with B.2/B.6. The earlier
  search provider is removed; its stored runs remain, labelled `LEGACY_SEARCH`.
- **Tests:** 260 exam_builder unittest + 15 research-facts + 23 standalone modules pass; `tsc
  --noEmit` clean; `npm run build` succeeds. **No frontend test harness.** `IMPLEMENTED` (backend/
  pipeline) / `LIMITATION` (frontend untested by automation).

## E.7 Current-state matrix (Part 25)

| AREA | REQUIRED BY VISION | CURRENT STATUS | EVIDENCE IN REPO | GAP | PRIORITY |
|---|---|---|---|---|---|
| Exam discovery (naive) | Yes | PARTIAL | `ExamFinder`, recommendation engine in `ui.tsx`/`services.ts` | Only 5 authored exams; not the ecosystem | P1 |
| Candidate guidance / eligibility | Yes | IMPLEMENTED | `EligibilityCalculator`, `evaluateEligibility` | Guidance limited to authored posts | P2 |
| Exam resolution | Yes | IMPLEMENTED | `resolve.py`, `ambiguity.py` | Needs Claude discovery (signed-in CLI) to run live | P1 |
| Official source discovery | Yes | PARTIAL | `discover.py`, `search.py` (Claude discovery adapter), `tools/claude_cli/discovery.py` | Not run live; needs a signed-in Claude CLI with web tools | P1 |
| Source identity | Yes | IMPLEMENTED | `identity.py` (MATCH/MISMATCH/AMBIGUOUS) | — | — |
| Extraction | Yes | PARTIAL | `semantic.py`, `exam_authoring/extract.py`, per-domain readers | Coverage limited; many fields NOT_EXTRACTED by current readers | P1 |
| Evidence verification | Yes | IMPLEMENTED | `verification/` (deterministic + Claude) | A step in the build when `use_claude` is set; otherwise fields are held, never upgraded | P2 |
| Completeness (search until found) | Yes | NOT YET | `contract.py`/`coverage_from` compute coverage but do not re-search on gaps | No automatic multi-source re-acquisition loop | P0 |
| Canonical data | Yes | PARTIAL | `schema.py` `UniversalExam` (Fact/evidence/revisions) | No types for resources/portals/FAQs/exam-day/roadmap; `ExamRecord→UniversalExam` bridge missing | P1 |
| 17 sections | Yes | IMPLEMENTED | `ui.tsx` sections + `types.ts` | Thin data for IBPS/APPSC; some thin (no-provenance) types | P2 |
| Application & documents | Yes | IMPLEMENTED (SSC/UPSC) | `ApplicationGuide`, simulator specs | Authored only for SSC/UPSC | P2 |
| Dates | Yes | IMPLEMENTED | `dates.py`, `ImportantDate`, timeline | Live extraction not run for new exams | P1 |
| Eligibility | Yes | IMPLEMENTED | `eligibility.py`, `evaluateEligibility` | — | — |
| Posts | Yes | IMPLEMENTED | `PostRequirement`, `_posts` in emit | Group classification only where printed | P2 |
| Exam pattern | Yes | IMPLEMENTED | `pattern.py`, `patternTree` | — | — |
| Syllabus | Yes | IMPLEMENTED | `syllabus.py`, tree/map, revisions overlay | Coverage per authored exam | P2 |
| PYQs | Yes | PARTIAL | `pyq.py`, UPSC official papers | Most authorities publish scans; limited items | P2 |
| Answer keys | Yes | IMPLEMENTED (model) | `AnswerKey`, `answer_keys()` | Few published; served per login | P3 |
| Study roadmap | Yes | IMPLEMENTED | `PreparationPlanner`, `roadmapTracks` | Thin (no provenance); guidance-only | P2 |
| Resources | Yes | IMPLEMENTED | `ResourceLibrary`, additions overlay, live feeds | Links-only by policy | — |
| Mock tests | Yes | IMPLEMENTED | `PracticeEngine`, generators | SSC bank only; others honest-empty | P2 |
| Admit card | Yes | IMPLEMENTED | `AdmitCardSection`, `admit_card.py` | Authored for SSC/UPSC | P2 |
| Exam day | Yes | IMPLEMENTED (honest) | `ExamDayChecklistSection` | No exam authors data yet | P2 |
| Results | Yes | IMPLEMENTED | `ResultNextStepsSection`, `results.py` | `resultNextSteps` authored for none | P2 |
| Next steps | Yes | PARTIAL | section 16 | Official-vs-guidance modelled; data thin | P2 |
| Corrigenda | Yes | IMPLEMENTED | `corrigendums`, merge supersession | Thin type (no full provenance) | P3 |
| Official portals | Yes | IMPLEMENTED | section 12, `portal_officiality` | Thin type; provenance not per-link in `data.ts` | P2 |
| Cutoff | Yes | IMPLEMENTED | `CutoffEntry`, cutoff panels | Per authored exam | P2 |
| Continuous updates | Yes | PARTIAL | live boards, link-health, notifications | Monitoring for authored exams; not a general watcher | P1 |
| Notifications | Yes | IMPLEMENTED | `generatePersonalizedNotifications…` | — | — |
| Exam isolation | Yes (B.4) | IMPLEMENTED | `identity.py`, `publish.py`, `key={exam.id}` | — | — |
| Automation (unknown exam onboarding) | Yes (Part 24) | NOT YET | pipeline exists but stops at report/staging; needs live discovery + full extraction + safe merge | The primary engineering acceptance test is unmet end-to-end | P0 |
| Publication | Yes | IMPLEMENTED (new exams) | `gate.py`, `publish.py`, `render.py` | Field-level merge into authored records blocked (fidelity) | P1 |
| UI / UX | Yes | IMPLEMENTED | light card SPA, WCAG-swept, responsive | No automated UI tests | P2 |
| Deployment | Yes | PARTIAL | Vite build + Flask serve | No configured prod/serverless; SQLite not serverless-safe | P1 |

---

# PART F — CURRENT GAPS (ranked by vision impact)

**P0 — blocks the core vision**
- **G-P0-1 Automatic unknown-exam onboarding is not achieved end-to-end (Part 24).** The pipeline
  is orchestrated and safe, but normal onboarding cannot yet produce a populated workspace from a
  bare exam name without a live search key, broader extractor coverage, and a completeness loop.
- **G-P0-2 No completeness re-acquisition loop (Part 6/9).** The system computes coverage but does
  not automatically widen the search across official documents when a section is missing;
  `NOT_EXTRACTED` can be a de-facto final state for authored-but-unread sections.

**P1 — major limitations**
- **G-P1-1 Canonical model incomplete.** `UniversalExam` lacks types for resources, portals, FAQs,
  exam-day, roadmap; cutoffs only nested in results; no `ExamRecord→UniversalExam` bridge, so the
  build cannot reach the rich `compat` projections.
- **G-P1-2 Field-level merge into authored records is unsafe (fidelity).** `data.ts` cannot be
  losslessly re-emitted (shared consts, comments); whole-slice replace erases authored arrays. The
  safe path (append new exams) works; updating authored exams needs the overlay store from
  `CANONICAL_DATA_AUDIT.md`.
- **G-P1-3 Extraction coverage is narrow.** Current readers reliably source identity/dates/
  eligibility/pattern-ish; many domains come back NOT_EXTRACTED on a real notice.
- **G-P1-4 Deployment is not production-configured.** Static frontend is deployable; the Flask API
  + SQLite writes are not serverless-safe and no host is configured.
- **G-P1-5 Ecosystem breadth.** Only 5 exams are authored; the vision needs many more, acquired
  automatically rather than hand-authored.

**P2 — important improvements**
- Thin (no-provenance) types for overview/roadmap/exam-day/corrigenda/official-links.
- Verifier not wired as a mandatory step in the automated build (only via orchestrator/tests).
- IBPS/APPSC data are stubs; no frontend test harness.

**P3 — refinements**
- Answer-key coverage; per-link provenance in `officialLinks`; richer corrigenda provenance.

---

# PART G — FUTURE ROADMAP (outcome-phases; no dates)

### PHASE 1 — Lock the product contract & canonical data ownership
- **Objective:** freeze this spec; adopt the canonical ownership model from `CANONICAL_DATA_AUDIT.md`
  (authored seed + additive, provenance-carrying, reversible overlays), generalising the existing
  `syllabus_revisions`/`resource_additions` pattern.
- **Why:** every later phase depends on being able to update facts without erasing authored data.
- **Prerequisites:** none (design exists).
- **Areas:** an `exam_fact_overlay` store; per-domain runtime merge; `Status`/`Revision` mapping.
- **Acceptance:** `test_fidelity` green for every exam; an overlay leaves the authored record
  byte-identical and mutates no other exam.
- **Must NOT:** rewrite `data.ts`; introduce a new database; implement merge before Phase 1's model.

### PHASE 2 — Complete the universal automatic acquisition pipeline
- **Objective:** run resolve → discover → extract → verify → gate → publish for real, with a live
  discovery source and broadened universal extractors, driven by one command.
- **Why:** Part 24 is the primary engineering acceptance test.
- **Prerequisites:** Phase 1; a configured discovery key handled per B.8.
- **Areas:** `discover`/`search`, per-domain readers, `verifier` as a pipeline step, orchestrator.
- **Acceptance:** for a captured official source set, the pipeline populates the applicable
  sections with verified, provenance-backed facts and passes the gate; failures keep distinct
  states.
- **Must NOT:** add exam-specific logic; let search/Claude output become VERIFIED without evidence.

### PHASE 3 — Reliably populate the 17 sections from verified official data
- **Objective:** the completeness loop (Part 6) — widen search across official documents before
  concluding "unavailable"; fill the canonical-model gaps (resources/portals/FAQs/exam-day/roadmap).
- **Why:** completeness is the product, not the schema.
- **Prerequisites:** Phases 1–2.
- **Acceptance:** on a real exam with published data, no applicable section is falsely NOT_EXTRACTED
  once legitimate acquisition paths are exhausted; every populated field carries evidence.
- **Must NOT:** fabricate to fill a section; collapse failure states.

### PHASE 4 — Naive-user exam discovery & guidance
- **Objective:** guided discovery from candidate facts (qualification, age, preferences, state),
  explaining why each exam appears, deterministic and evidence-backed.
- **Prerequisites:** a broader acquired exam set (Phases 2–3).
- **Acceptance:** Acceptance Test 1 & 9 pass with a growing exam set; suitability is never fabricated.
- **Must NOT:** invent eligibility; expose engineering states.

### PHASE 5 — Full lifecycle tracking & automatic updates
- **Objective:** detect official corrigenda/new documents, update current state while preserving
  history and effective dates, notify affected candidates.
- **Prerequisites:** Phase 1 (overlays), Phase 2 (acquisition).
- **Acceptance:** Acceptance Test 7 (revision) & 8 (failure safety); old values preserved.
- **Must NOT:** silently overwrite historical truth.

### PHASE 6 — Validate unknown-exam onboarding
- **Objective:** onboard a previously unconfigured exam (e.g. "RRB NTPC 2027") with no
  exam-specific code and no manual fact entry.
- **Prerequisites:** Phases 1–5.
- **Acceptance:** Acceptance Test 2; a synthetic unknown authority progresses through the generic
  pipeline; isolation holds.
- **Must NOT:** declare universality from a generic schema alone — prove it by onboarding.

### PHASE 7 — Production hardening & scale
- **Objective:** a real deployment target for the stateful API + a durable store; monitoring,
  rollback, backups; retire unsafe whole-record replacement (append-only for new exams).
- **Prerequisites:** Phases 1–6.
- **Acceptance:** secrets never exposed; rollback proven; isolation and failure-safety hold at scale.
- **Must NOT:** migrate data without the phased plan and rollback criteria in `CANONICAL_DATA_AUDIT.md`.

---

# PART H — ACCEPTANCE TESTS

| # | Test | What it proves | Current result |
|---|---|---|---|
| 1 | **Naive student** — a user with no exam knowledge can understand what to do | UX clarity | PARTIAL (works for the 5 authored exams) |
| 2 | **Unknown exam** — a previously unsupported exam onboarded without exam-specific logic | universality | NOT YET (pipeline safe but not end-to-end live) |
| 3 | **Authenticity** — every published factual claim has valid evidence | B.1/B.2 | IMPLEMENTED for authored data (provenance on facts) |
| 4 | **Zero AI fact creation** — Claude cannot introduce unsupported facts | B.1/B.6 | IMPLEMENTED (deterministic-first; every proposed value needs a verbatim quotation; Claude never publishes) |
| 5 | **Completeness** — legitimate official sources searched before "unavailable" | Part 6 | NOT YET (no re-acquisition loop) |
| 6 | **Isolation** — no exam receives another's information | B.4 | IMPLEMENTED (content + data isolation, tested) |
| 7 | **Revision** — corrigenda update current info while preserving history | B.7 | IMPLEMENTED (dates supersession; merge refuses to overwrite) |
| 8 | **Failure safety** — network/Claude/parser failures never become false facts | B.5/B.6 | IMPLEMENTED (distinct infra states; not cached) |
| 9 | **User clarity** — a naive student understands a page without technical knowledge | UX | PARTIAL (honest empty states; engineering states hidden) |
| 10 | **Full journey** — discovery → result → next step | A.2 | PARTIAL (all sections exist; data deep only for SSC/UPSC) |

---

# PART I — DEVELOPMENT RULES (for Claude / AI coding agents)

1. Read this file before making changes; treat it as authoritative for product vision.
2. Inspect the existing implementation before changing architecture.
3. Never create exam-specific logic where a universal solution is required.
4. Never generate factual exam data (B.1).
5. Never weaken verification to make the UI look complete.
6. Never use another exam as a fallback.
7. Never expose internal failure states as factual information.
8. Never add unrelated features (B.9).
9. Preserve existing working functionality (B.7).
10. Prefer minimal changes that move the project toward the vision.
11. Update this spec only when the actual product requirements change (see Change Control).
12. Never silently redefine the vision.
13. If a task conflicts with this document, explain the conflict before coding.
14. Every major implementation must name the requirement/acceptance criterion it satisfies.
15. Test unknown-exam behaviour, not only known exams.
16. Never declare the system "universal" from a generic schema — prove it by onboarding an unknown exam.
17. Do not modify `data.ts`, the DB, UI, deployment, or config outside the requested scope.
18. Keep secrets out of the repo; validate external domains; never allow cross-exam contamination.

---

# PART J — CHANGE CONTROL

This specification is a constitution, not a scratchpad. Update the **vision/requirements** only for
an intentional product decision, preserving original intent; never weaken a requirement because it
is hard. Implementation details belong in technical docs; historical work belongs in the audit
reports (`FINAL_UNIVERSAL_ENGINE_AUDIT.md`, `ORCHESTRATION_AUDIT.md`, `PRODUCTION_RENDERER_AUDIT.md`,
`CANONICAL_DATA_AUDIT.md`, and the per-section `*_AUDIT.md`). Refresh **Part E/F** (current state and
gaps) as the code changes, keeping VISION and CURRENT STATE clearly separated.

---

# PART K — NORTH-STAR CHECK (run before implementing anything)

Before adding or changing anything, answer these. If a proposed change does not clearly support
the vision, it must **not** be added merely because it is technically interesting.

1. Does this help a naive government-exam aspirant?
2. Does this reduce ambiguity?
3. Does this provide or enable authentic information?
4. Does this preserve the zero-AI-factual-data rule (NO EVIDENCE = NO FACT)?
5. Does this work for previously unsupported exams?
6. Does this avoid exam-specific hardcoding?
7. Does this improve completeness?
8. Does this preserve evidence?
9. Does this preserve exam isolation?
10. Does this move the student toward the next step?

---

# PART L — WHEN ASKED TO IMPLEMENT A FEATURE (pre-coding checklist)

1. **Read `GOVOS_MASTER_SPEC.md`** first.
2. Identify the **exact product requirement** being addressed (cite it, e.g. B.11, C.1).
3. Identify the **acceptance criterion** it satisfies (Part H).
4. **Inspect the existing implementation** before changing architecture.
5. Determine whether the change can be implemented **generically** (universal engine).
6. **Reject exam-specific workarounds** unless genuinely required by an external authority system,
   and even then keep them to a documented adapter, never a manual exam database.
7. **Never invent factual data** (B.1).
8. **Never weaken evidence requirements** (B.2/B.3).
9. **Preserve existing functionality** (B.7).
10. **Test against a previously unsupported/synthetic exam** where possible (Dev Rule 15/16).
11. **Report which master-spec requirement was fulfilled.**

If the task conflicts with any non-negotiable requirement, **stop and surface the conflict before
coding** (Dev Rule 13).

---

# PART M — NORTH STAR

> GovOS exists to remove the confusion surrounding government examinations for ordinary students.
>
> A student should not need to already understand the government-exam ecosystem in order to use
> GovOS.
>
> GovOS should discover the relevant path, explain the examination clearly, provide authentic
> evidence-backed information, guide the student through the complete lifecycle, track what changes,
> and explain what to do next.
>
> The platform should do this automatically, universally, clearly, and without generating factual
> examination information with AI.
