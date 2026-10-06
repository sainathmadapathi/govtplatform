# The GovOS information pipeline

How a fact gets from an authority's own website to a candidate's screen, what can go wrong at each
step, and what was found and fixed on 2026-10-03 (branch `fix/pipeline-bottlenecks`).

```
 COLLECT (build time, tools/)                 STORE (SQLite)            SERVE (app.py)               SHOW (src/)
 ───────────────────────────                  ──────────────            ──────────────               ──────────
 exam name + year
   │ resolve the authority                                                                           services.ts
   │ walk the authority's site (opt-in) ────► source_discovery_runs ──► /api/sources/exam/<id> ──┐   (one shared
   │ discover this exam's documents                                                              │    read per exam)
   │ fetch + identity-check them                                                                 │        │
   │ read each contract field                                                                    │    main.tsx
   │ vet (dates, units, attribution)                                                             │    liveExam =
   │ re-acquire what is missing                                                                  │    record
   │ completeness → 17 section states                                                            │    + revisions
   │ verify (optional Claude) + gate                                                             │    + overlays
   ▼ materialize → runtime Exam ──────────► exam_registry ───────────► /api/exams ──────────────►├──► ExamDetailView
                                                                                                 │    17 sections,
 hand-authored records: src/data.ts ─────────────────────────────────────────────────────────────┤    Evidence panel,
                                                                                                 │    banners
 LIVE (background + admin)                                                                       │
   notice boards, channel feeds ──────────► live_feed_cache ─────────► /api/resources/live/* ────┤    Ask GovOS AI,
   link health ───────────────────────────► resource_link_health ────► /api/resources/health/* ──┤    test creator,
   research → promote → add ──────────────► resource_additions ──────► /api/resources/additions ─┤    resource navigator
   verifier revisions / overlays ─────────► syllabus_revisions, overlays ► /api/syllabus/*, ... ─┘
   Claude jobs (gateway → runner) ────────► claude_jobs, audit tables
```

Two rules run through every stage. **Officiality is ownership**: only the authority's own estate is
official, and nothing becomes official because Claude, a coaching site or a link said so. **Absence
is a claim**: `NOT_PUBLISHED` (the authority published none, shown by its own material) and
`NOT_EXTRACTED` (GovOS could not read it) must never be merged, because the first is a statement
about the authority and the second is a gap in GovOS.

---

## 1. Collect — build time (`tools/exam_builder`, `tools/exam_authoring`)

Entry points: the Trust Panel's **Build** (`POST /api/exams/build` → a `BUILD_EXAM` job →
`materialize.build_exam`), or the CLI `python -m tools.exam_builder.materialize`. Both run
`orchestrate()` as a **dry run** (it never writes `src/data.ts`), then materialize and register.
`orchestrate --publish` on the command line is the only path that writes `data.ts`.

| # | Stage | Code | In → out | What it decides |
|---|---|---|---|---|
| 1 | Resolve the authority | `resolve.resolve` | name + year → `ResolvedExam` | Which commission conducts the exam, by a vote of hosts over search hits. Ambiguous → `AMBIGUOUS_AUTHORITY`; search unavailable → `INFRASTRUCTURE_FAILURE` (never "not published"). |
| 2 | Walk the authority's site (opt-in) | `authority_discovery.discover_authority`, `source_graph` | root URL → `DiscoveryRun` (source graph) | Bounded walk (2 links deep, 25 pages, 40 files). Every link gets a role (notification, paper, key, portal, …), an owner and a class; six search states per role, never merged. Stored whole in `source_discovery_runs`. |
| 3 | Discover this exam's documents | `discover.discover`, `discover.gate` | resolved exam (+ walk) → `SourceSet` | Crawls seeds and listings, admits the walk's THIS_EXAM items, then searches for kinds still missing. Each document is DIRECT, INHERITED or REJECTED for this exam. |
| 4 | Fetch and load | `exam_authoring.sources.fetch`, `load_pdf/html` | URL → `Document` (pages or HTML text) | 45 s timeout, 3 tries, 24 h disk cache. A fetch failure pauses the build as infrastructure. |
| 5 | Identity | `identity.verify`, `designation` | text → MATCH / AMBIGUOUS / MISMATCH | Is this document about *this* exam and *this* cycle? A mismatched document is dropped before anything is read from it. |
| 6 | Contract and coverage | `contract.CONTRACT`, `coverage_from` | document kinds → per-field coverage | Which fields this exam's documents can supply. A field with no source document at all becomes `NOT_PUBLISHED` "No document of kind …" (see fix 5 for how that is now shown). |
| 7 | Read each field | `build._dispatch_domain_extraction` → `dates`, `pattern`, `syllabus`, `eligibility`, `pyq`, `admit_card`, `results`, `application`, `corrigenda`, … | documents → `Field` | Each reader quotes the words it read the value from (`Citation`, `Evidence`). Default for a reader that matched nothing is `NOT_EXTRACTED`. |
| 8 | Vet | `_vet_dates`, `_vet_completeness`, `_vet_attribution`, `_vet_posts` | `Field` → `Field` | Deterministic checks first (a date must name its own event; a quoted unit must be whole). Claude, when enabled, may only **withhold** — except that it may give a role to a date whose evidence names none, and only with a cue in its own quoted evidence (fix 1). |
| 9 | Re-acquire | `_targeted_reacquire` | missing fields → more documents | One search per still-missing field; new documents are identity-checked and read again. |
| 10 | Completeness | `completeness.evaluate_completeness` | record → 17 section states | VERIFIED_AVAILABLE, NOT_YET_PUBLISHED, SOURCE_NOT_FOUND_AFTER_SEARCH, SOURCE_UNREADABLE, EXTRACTION_FAILED, NEEDS_REVIEW, INFRASTRUCTURE_FAILURE. These become the section banners. |
| 11 | Verify and gate | `orchestrate` (`VERIFY_CLAIM` when `useClaude`), `gate.evaluate` | record → PASS / BLOCK | NEEDS_REVIEW anywhere, a required field not read, infrastructure, or a cited mismatch blocks. Claude's CONTRADICTED only withholds. |
| 12 | Materialize and register | `materialize.materialize_exam`, `compat.*`, `runtime_evidence`, `ExamRegistry.register` | record → runtime `Exam` JSON | Projects the canonical record into the frontend's `Exam` shape, stamps every provenance with an `evidenceId`, validates it against the contract, and stores it in `exam_registry` (older versions kept in `exam_registry_history`). |

Hand-authored records (SSC CGL, UPSC CSE, IBPS PO, APPSC) live in `src/data.ts`, written from the
authority's own documents with a provenance on every value; `tools/exam_authoring` reads a UPSC exam
into a `data.ts`-shaped record for a person to merge. `npm run export:authored` writes
`exam_data/authored_exams.json` so the server (Ask AI's fact sheets, `/api/sources/exam`) can read them.

**Claude in the build** (only through `ClaudeGateway.run`): `DISCOVER_SOURCES` for search,
`EXTRACT_DESIGNATION` / `CONFIRM_RECRUITMENT` for identity, `CHECK_COMPLETENESS`,
`CLASSIFY_ATTRIBUTION`, `CLASSIFY_DATE`, and `VERIFY_CLAIM`. Every reply is schema-checked and every
quotation is re-found in text GovOS fetched itself.

## 2. Store — SQLite (`govos.db`)

`exam_registry` (machine-built exams), `source_discovery_runs` (walks, never overwritten),
`live_feed_cache`, `resource_link_health`, `resource_additions`, `syllabus_revisions`,
`exam_fact_overlays`, `research_runs` / `research_findings` / `research_facts`, `claude_jobs` and the
Claude audit tables, and the candidate's own rows (`mock_attempts`, bookmarks, notifications, …).
The browser's `localStorage` is the candidate's source of truth; the server copy is fire-and-forget.

## 3. Live flows — background and admin (`app.py`, `tools/claude_cli`)

- **Notice boards and channel feeds**: SSC's notice-board API, UPSC's What's New page and YouTube
  Atom feeds, cached 6 h in `live_feed_cache`, refreshed hourly by a daemon thread.
- **Link health**: every library URL registered on load, re-checked when older than 12 h.
- **Research → candidates**: Claude proposes candidate sources (`DISCOVER_SOURCES` job); the server
  checks each one itself; a person reviews, **promotes**, then — a second deliberate click — **adds** it
  to one exam's library. Read facts land as `pending`/`validated` research facts for review; none
  reaches a candidate except through a verifier's overlay.
- **Syllabus watch and revisions**: new notices since the syllabus was verified are shown as a reason
  to check; a verifier applies ADD / AMEND / RETIRE citing the notice.
- **Claude jobs**: a persistent queue (`claude_jobs`), two workers, one gateway, one process runner
  (array arguments, no shell, prompt on stdin, process-tree kill on timeout).

## 4. Serve — `app.py`

`/api/exams` (registry), `/api/sources/exam/<id>` (the latest walk projected onto one exam),
`/api/syllabus/*`, `/api/exams/<id>/overlays`, `/api/resources/*` (live feeds, health, additions),
`/api/claude/*` (health, jobs, Ask, practice), `/api/research/*` (admin), and the candidate's own
`/api/sqlite/*` rows. Admin and canonical-changing routes sit behind `admin_required`.

## 5. Show — `src/`

1. `services.ts` is the only place that calls the API; every call fails soft (offline means "not
   read here", never "not published").
2. `main.tsx` composes the exam every feature is handed:
   `liveExam = applyExamOverlays(applySyllabusRevisions(record, revisions), overlays)`, where the
   record is the authored one or the registry's runtime one (`getExamUniverse`).
3. `ExamDetailView` renders 13 parts plus 4 reference sections from that one record. A
   machine-built exam's section carries a banner from its completeness state, now read against the
   latest walk (fix 13). Each cited value has one **Evidence** button opening the provenance.
4. Section panels (`SectionSourcesPanel`, `QuestionPaperSourcesPanel`, …) place the walk's discovered
   documents by role; the Resource Library lists learning material only.
5. The chats (`answerCandidateQuery`, the test creator, the resource navigator) answer from the same
   record; Ask GovOS AI may ask Claude for a question the register cannot place, and that answer is
   checked figure by figure against the facts it cites (fix 3).

---

## 6. Bottlenecks found and fixed (2026-10-03)

"Bottleneck" here means a place where the pipeline does not do what it is meant to: a value that can
be published or shown wrongly, one exam's facts leaking into another's page, or work that blocks,
repeats or piles up. Every fix has a test that fails on `main` (`50dcdfe`) and passes on the branch.

### Collection and publication

| # | Where | What was wrong | Fix | Test |
|---|---|---|---|---|
| 1 | `build._vet_dates` rescue loop | **P0.** A held date — one whose evidence states it for another event, or whose role Claude disputed — could be published under the row's role once Claude named *any* role with a cue in its quote (the rescue validated with `need_role=None`, and a disputed date was simply asked again). An examination date could be published as the last date to apply. | Only a date whose evidence names no event may be rescued; a date with a role stays held. | `test_date_attribution`: `…cannot_overrule_a_role_mismatch`, `…disputed_role_is_not_undone…` |
| 2 | `build()` / `orchestrate()` | A job with `useClaude: false` still called Claude in identity, completeness and date checks whenever Claude was enabled for the process (they read the global gateway); signed out, it held fields as "Claude could not check". | `build(gateway=)` sets the run's gateway (a context variable read by every step); `orchestrate` passes `NoClaude()` when the job did not ask for Claude. Claude-enabled builds are unchanged. | `test_orchestrate` 23, 24 |
| 3 | `claude_cli.context.validate_answer` | **P1.** A "verified data" answer from Ask was checked only for figures of two or more digits, against the *whole* fact sheet and the candidate's own question: "6 attempts" against a fact saying 4 passed, and "is the fee 750?" could be answered "yes, 750". | A verified answer is held to the facts it cites — every figure, single digits included; the question no longer counts. List numbering is layout; a 24-hour time may be said as "6 PM" but a bare "6" may not. | `test_context`: three new cases |
| 4 | `build.py` photo/signature and required-documents readers | A reader that matched nothing in a readable notice recorded `NOT_PUBLISHED` ("No distinct photograph/signature guidelines published") — GovOS's gap reported as the authority's silence. | Where a readable document speaks of photographs/signatures or uploads, the field is `NOT_EXTRACTED` with that sentence; only a notice that never mentions them is `NOT_PUBLISHED` (the fee-exemption rule, applied to both). | `test_reader_gaps` (4) |
| 5 | `completeness.state_for_field` | A field for which discovery found no document at all (`NOT_PUBLISHED` "No document of kind …") was shown as **"Not published yet — the authority has not published this for this cycle"**. | That case is `SOURCE_NOT_FOUND_AFTER_SEARCH` ("searched, not found; may still be published"). A `NOT_PUBLISHED` read from the authority's own words is unchanged. | `test_materialize`, `test_phase3_completion` (expectations corrected) |
| 6 | `POST /api/resources/additions` | The research gate (only a **promoted** finding reaches candidates) was enforced only by hiding a button: the server accepted any `findingId`, or a promoted one's number with a different URL. | A `findingId` must name an existing, PROMOTED finding, and the addition must carry that finding's own link. An addition made without a finding no longer claims to come "from Live Source Research". | `test_resource_additions` (3) |

### Serving

| # | Where | What was wrong | Fix | Test |
|---|---|---|---|---|
| 7 | Live feeds (`_ssc_notices_cached`, `_upsc_whatsnew_cached`, `_channel_uploads_cached`) | A stale feed was fetched **inside the candidate's request** (up to 25 s; the syllabus watch did this on every exam page); concurrent requests each fetched upstream; while an upstream was down, every request retried it. | Stale-while-revalidate (serve the last copy at once, refresh behind it), one fetch per feed at a time, 15-minute back-off after a failure, forced refresh limited to once a minute. The hourly loop runs each step on its own (one failure used to skip the rest for the hour). | `test_live_resources` (6) |
| 8 | `_check_one_link` (behind `verify-links`, `health/sync`, `health/recheck` — open to any caller) | Fetched whatever URL it was given, following redirects, and returned the status: a probe of the server's own network (127.0.0.1, 10.x, 169.254.x). | Only http(s) addresses whose host resolves to public addresses, on the first hop and on every redirect. | `test_live_resources` (2) |
| 9 | `/api/sources/exam/<id>` | Loaded and re-projected the whole stored walk (~600 nodes) on every GET, and ran table DDL; every section switch asked for it. | Memoized per (database, exam, run id, the inputs the projection reads), with a cheap `latest_id` query; one store object per database. A new walk is a new run id, so it shows at once. Measured on the live TGPSC walk: 107 ms first read, 6–9 ms after. | `test_app_sources` (1) |
| 10 | `/api/research/facts/extract` and the Claude facts hook | Checked each source's reachability (up to 20 s) **inside** the write transaction, so every other writer waited and failed with "database is locked". | All reachability checks run first, in parallel; the transaction holds no network call. SQLite connections also wait 30 s for a lock instead of 5 s. | `test_research_facts` (1) |
| 11 | `ClaudeGateway.health()` | Runs inside candidate requests; when its cache expired, every concurrent request spawned its own `--help`, `--version` and `auth status` processes (up to ~50 s each). | One probe at a time; waiting requests reuse its answer. Six concurrent checks: 6+6 probes on `main`, 1+1 now. | `test_config` (1) |
| 12 | Request handling | No request-size cap (`sync-all`, `results/parse` read any size into memory); a non-numeric `limit` was a 500; `/api/exams` ran table DDL and a commit on every GET. | 16 MB cap (413 above it); tolerant `limit`; one registry object per database. | `test_live_resources` (2) |

### Display

| # | Where | What was wrong | Fix | Test |
|---|---|---|---|---|
| 13 | `SectionStateNote` | **P1.** A machine exam's banner came from the build-time state alone: TGPSC's Practice & PYQs and Cutoff History said **"Not found. GovOS searched…"** above a panel saying the search was incomplete. | `resolveSectionState` reads a build's "not found" against the latest walk, but only against the section's **own** evidence role (`SECTION_EVIDENCE_ROLE`, keyed by the build's section id: Practice & PYQs = question papers, not answer keys). "Found on the official site" needs a listed item of that role, official, tied to this exam in this cycle and openable; the walk's per-role state is authority-wide (any portal makes APPLICATION_PORTAL "found"), so it can withhold "not found" but never grant "found". Anything the walk did not rule out → "Search incomplete". NOT_YET_PUBLISHED, EXTRACTION_FAILED and the other document findings are never rewritten; another exam's projection is ignored. (A first version took any found role placed in the section — a sibling answer key, an authority-wide OTR portal, an unlinked item, even Dates from a CALENDAR — as "Found".) Verified live: TGPSC sections 09 and 10 say "Search incomplete"; 1, 2, 4, 5, 15 carry no banner. | `exam_display_check` (~40) |
| 14 | Section panels, `services.ts` | Every section switch fetched the discovery projection and the additions again (two requests per switch). | `sharedRead`: one in-flight read shared by all panels, kept 2 minutes, a failed read never kept, cleared on an admin add/retire; the Trust Panel always reads fresh. Verified live: six section switches, zero extra requests. | `exam_display_check` (5) |
| 15 | `main.tsx` revisions and overlays | A failed read set them to `[]`, silently putting the unrevised syllabus back on the page after a network blip. | A failed read keeps what was applied (both merges only ever apply the exam's own). | — |
| 16 | `ExamDetailView` | The minute clock re-rendered the whole exam page every minute on every section; only Dates & Timeline reads it. "Latest Updates" sorted displayed text ("May/June 2024") against an ISO date, so such dates sorted as still ahead. | Clock runs only on section 2; updates sort by ISO day and show the printed text. | — |
| 17 | Results & Next Steps (engine B) | IBPS PO and both APPSC exams were judged in SSC CGL's words: "Tier-1/Tier-2", a **298-mark** target no record holds, CKT/DEST thresholds, "Ministry allocation", "SSC CHSL" advice, "/ 200" and "/ 390" maxima, and "NOT ALLOCATED" for an allocation never entered. SSC's own Skill Test tab had silently stopped rendering ("Data Entry Speed Test" has no "DEST" in it). | Stage names and maxima from the exam's own stages; SSC clauses only for SSC; the skill card only where the record has a skill stage; "Not entered" for an allocation not entered. Verified live on IBPS PO: "Preliminary Examination 59.25 / 100", no SSC wording. | `exam_display_check` (~40) |
| 18 | Practice papers 9 and 12; the CKT sectional | Titled "Tier-2 Paper-I pattern" but built in the Tier-I format; the Tier-II computer module (3 marks a question, 1 off) was scored at Tier-I's +2/−0.5, so its 60 marks could never be reached. | Papers relabelled "(Tier-1 pattern)" like papers 1–8. Every full paper is the same template-cycled item set with the same mix (36 hard / 32 medium / 32 easy), so no paper-level difficulty is claimed: all twelve are `ADAPTIVE` (papers 9, 10, 11, 12 had said HARD/MEDIUM). Questions untouched. `MockPaper.marking` carries a paper's own marking and clause (Tier-I's by default); the test and review screens show it. | `practice_papers_check` (questions frozen against 50dcdfe) |
| 19 | Assistant answers | Typing: "DEST is Section III Module 2 of Tier-2" for every exam (wrong even for SSC: Section-IV) and "the link below" where no link exists. Syllabus: "Study Plan & Syllabus" and weightage for every exam; "0 topics:" for an empty syllabus. Practice: SSC's eight 2024–2025 answer-key **notices** (no answers; login-served) counted as "8 answer keys"; UPSC's OCR-read essay items not said to be under verification. Syllabus badge "(~N Qs/Shift)" and "~0%" on every exam. | Each answer is built from the exam's own record (`typingAnswerFor`, `syllabusAnswerFor`, `practiceAnswerFor`); the badge shows only a recorded weightage, "per paper". | `exam_display_check` (~30) |

## 7. Found, not changed — and why

| Where | Issue | Why not changed here / suggested next step |
|---|---|---|
| `sources.fetch` (build) | TLS verification is off. | Many government hosts serve broken certificate chains, so turning it on would stop builds; needs verify-first with a recorded fallback. |
| `build.record_search_outcomes` | Never called, so the walk's role search states never reach a build's completeness. | Needs the walk's per-role states passed into `build()`; fix 5 covers the worst symptom. |
| `build._raw` | A NEEDS_REVIEW semantic reading is discarded and the field ends NOT_EXTRACTED. | Safe direction (nothing published); keep the reading for reviewers next. |
| Build performance | Documents fetched serially; whole-document `normalise_ws` per evidence check; PDFs re-parsed by the ruled-table reader. | Build-time only; cache each document's normalised text first. |
| `search.search` | Search for resolution uses the process-wide gateway even in a `useClaude: false` build. | Search *is* the discovery mechanism; decide whether `useClaude` should cover it. |
| Job queue | No priority lanes: candidate Ask/practice jobs wait behind builds and walks. | Reserve a worker for candidate jobs. |
| Rate limiter | Keyed by `remote_addr`; behind a proxy every candidate shares one bucket. | Read a trusted forwarded address when deployed behind one. |
| SQLite | Rollback journal, no WAL; `mock_attempts` has no index on `(user_id, exam_id, attempted_at)`. | Both change `govos.db` itself; apply in a migration when the database can be touched. |
| `authority_discovery._item` | A link role assigned only by Claude reaches candidates unlabelled. | Emit `roleBy` and show it; treat a Claude-only role as FOUND_AMBIGUOUS. |
| Research facts | Claude-read facts can become `validated`, not `pending` as documented. | Product decision; cap at `pending` or change the docs. |
| `applyExamOverlays` | NOT_PUBLISHED overlays applied like VERIFIED ones; a vacancies overlay does not update its evidence. | Needs an overlay-semantics review. |
| `publish.py` | Second process spawn (`npx tsc`, shell on Windows, no timeout). | CLI-only; resolve `npx.cmd` and add a timeout. |
| `ExamDetailView` | No `key={exam.id}`, so local state survives an exam switch. | Minor. |

## 8. Validation (2026-10-03)

- Backend: `python -m pytest tools test_research_facts.py test_app_claude.py` — 2142 passed; root
  files `test_app_sources.py test_resource_additions.py test_live_resources.py` — 32 passed
  (2174 in all; `main` had 2149; the 25 more are the new tests).
- Frontend: `npm run check:frontend` — all five checks pass, including the new `exam_display_check`
  (119 assertions; 84 of them fail on `main`). `npx tsc --noEmit` clean. `npm run build` succeeds.
- Every new Python test fails on `main` (`50dcdfe`) and passes on the branch (23 tests).
- Live, on a scratch copy of the database with the real TGPSC walk: banners, request counts, the
  projection timing, IBPS results and the assistant were checked in the browser.
- `govos.db`, `.claude/launch.json` and `package-lock.json` were not modified.
