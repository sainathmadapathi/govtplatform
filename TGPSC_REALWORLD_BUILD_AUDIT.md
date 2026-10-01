> **ARCHIVAL NOTE (2026-10-01).** This document records what was true when it was written and is kept as history, not rewritten. Where it mentions a local model (Qwen, llama.cpp, a GGUF file, a local OpenAI-compatible endpoint), `GOVOS_LLM_*` variables, `LLM_*` states or the Tavily search provider, that system has since been removed: GovOS now uses only the installed Claude CLI, server-side. The current architecture is in `CLAUDE_CLI_INTEGRATION.md`.

# Real-world universal build test — TGPSC Group-I Services (Notification 02/2024)

Date: 2026-09-28. Engine: the universal exam acquisition → verification → materialization
pipeline as committed at `7add6a9`, run unchanged in structure against a recruitment it had
never seen. This document records what the engine did on its own, where a person had to step
in, what could not be established, and which *generic* capabilities were found missing and
added. Nothing TGPSC-specific was written: no branch, adapter, parser, URL, selector or field
mapping names this authority or this recruitment (§ Repository search).

## Final answer (evidence only)

> *If I give GovOS a specific unseen government recruitment name, can the existing universal
> engine discover, verify, build, materialize and register that recruitment with zero manual
> data-entry, while requesting human intervention only when evidence/identity/extraction
> genuinely requires it?*

**Yes for the chain, with three qualifications the test itself produced.**

1. **Zero manual data entry — held.** No value of the registered record was typed by a person.
   Every published field cites the authority's own document, page and verbatim span. The three
   human decisions were all *withholds* (do not publish this reading); none supplied a value.
2. **Human intervention only where required — held, and it was required four times:**
   `AMBIGUOUS_IDENTITY` (two official Group-I cycles exist; a person chose 02/2024) and three
   `SOURCE_REQUIRES_REVIEW` decisions on fields the readers had read wrongly or could not read
   into the record's shape (post-scoped age limits, a documents list read as posts, a garbled
   scheme table). The machine flagged one of these itself (NEEDS_REVIEW); the other two it had
   published as FOUND and a person caught them by reading the evidence spans. That is the honest
   limit today: **extraction fidelity on an unseen layout is not yet trustworthy enough to
   publish without a person reading the cited spans of the scalar fields.**
3. **The engine as checked out at the start of the test could not do it.** The first live run
   never reached the exam's own notification (blocked, nothing registered — failure-safe, but
   useless). Seven generic capabilities were missing (§ Generic gaps). With them added, the
   *same* code path resolves, discovers, isolates, extracts, gates, materializes and registers
   the recruitment, and the checkpoint's own fixtures (NAEB, STSB, Zeta) still pass on it.

## TARGET

| | |
|---|---|
| Query supplied | `TGPSC Group-I Services` (no year) |
| Authority resolved | Telangana Public Service Commission, `https://websitenew.tgpsc.gov.in` (confidence 0.77–0.81 across runs; rival `tgpsc.gov.in` recognised as the same body) |
| Candidate cycles found on the authority's own notifications page | `02/2024 - GROUP-I SERVICES` (notification dated 19/02/2024; applications 23/02–14/03/2024) and `04/2022 - Group - I Services` |
| Human selection | 02/2024 (AMBIGUOUS_IDENTITY → the smallest possible choice; the test then ran unattended) |
| Exact identity | `exam-websitenew-tgpsc-group-i-2024`, cycle `2024`, notification NO. 02/2024 dated 19/02/2024, "GROUP-I SERVICES (GENERAL RECRUITMENT)" |
| Stages named by the notice | Preliminary Test (objective, May/June 2024), Main Examination (conventional/descriptive, September/October 2024) |

## SOURCES

Discovered on the authority's estate (crawl of the resolver's seeds, the site's listing pages
one level down, and domain-restricted search): **80 documents; 4 kept, 76 rejected** (run 5,
the last live run; the replays re-fetch exactly those 4 and re-validate them).

Kept, with the content-identity verdict each earned from its own text:

| Document | Kind | Identity | Contributed |
|---|---|---|---|
| `02/2024 - GROUP-I SERVICES` — 50-page notification PDF served behind `/preview/<token>` | NOTIFICATION | **MATCH** (title block names this exam; 18 other examinations mentioned in the body) | every published field |
| `04/2022 - Group - I Services` — the previous cycle's notification | NOTIFICATION | **MISMATCH** (names this examination for 2022, not 2024) | nothing; retained for audit |
| `Know Your TGPSC ID` — site page | NOTIFICATION (by link text) | MISMATCH (names 3 examinations, none this one) | nothing |
| `TGPSC - SYLLABUS CHANGE FOR VARIOUS RECRUITMENTS` — web note | SYLLABUS | AMBIGUOUS (names no examination) | nothing (no span attributable) |

Rejected, by reason: 73 documents named another recruitment or none (other notifications
`01/OG/PC/2026 … 33/2022`, Group-II/III/IV scheme-and-syllabus files, results and keys pages,
FAQ, regulations, departmental tests, a 2018 timetable); 3 re-acquired documents judged
MISMATCH by content (`/keys`, `/FAQ.jsp`, the home page). A search-result title was never
treated as content: every kept document was fetched, read, and asked to name itself.

The 2022 notification is the important rejection: it is the *same recruitment, previous
cycle*, its title block carries the year only in its notice number and dateline, and before
the fix it passed as MATCH and supplied `posts` and `feeExemptions` to the 2024 record.

## AUTOMATED (no human input beyond the cycle choice)

Read from the 02/2024 notification with a cited page and verbatim span — **12 fields FOUND,
12/12 with citation and excerpt (100 % provenance on published facts)**:

`applicationPortal` (https://www.tspsc.gov.in as printed, p.1) · `howToApply` (7.1 "How to
upload the application form") · `requiredDocuments` · `photoSignatureGuidelines` · `fee`
(Rs. 200 online application processing fee, 8.1) · `qualification` ("Must possess a
Bachelor's Degree of any recognized University in India …", p.4) · `dates` (notification
19/02/2024; applications close 14/03/2024; Preliminary Test May/June 2024 and Main
Examination September/October 2024 at month precision, marked tentative) · `syllabus`
(Annexure-II: Group-I subject list, 124 entries under two roots) · `admitCard` ("Hall
Tickets" rule) · `examDayChecklist` (one instruction, p.16) · `officialName` · `authority`.

Machine-established absences: `corrigenda`, `officialPapers`, `answerKeys`, `results`,
`cutoffs`, `nextSteps`, `feeExemptions` → NOT_PUBLISHED (searched the authority's domain and
its listing pages; no document of that kind for this recruitment). `attempts`, `faqs` →
NOT_EXTRACTED / SOURCE_NOT_FOUND_AFTER_SEARCH in the live run (`faqs` reads
EXTRACTION_FAILED in the replays, which perform no search — a replay artefact, recorded as
such). `vacancies` → NOT_EXTRACTED (the notice's total was not read; it was *not* invented).

Materialized and registered: `exam-websitenew-tgpsc-group-i-2024`, cycle 2024, registry
version 1, `origin: MACHINE_ACQUIRED`, 30 top-level keys, 4 dates, 2 eligibility highlights,
syllabus tree, 1 exam-day item, 1 official link, section states for all 17 sections.

## HUMAN REVIEW (exactly what required intervention)

| Point | Kind | What the person did | Why the machine could not |
|---|---|---|---|
| Cycle | `AMBIGUOUS_IDENTITY` | chose 02/2024 over 04/2022 | two official cycles of one recruitment; no evidence chooses |
| `ageLimits` | `SOURCE_REQUIRES_REVIEW` (machine-flagged NEEDS_REVIEW) | **withheld** | the notice states post-scoped limits (min 18 / 21, max 46 / 35 by post code); the record has no per-post rules to hold them and one band would misstate some posts |
| `posts` | `SOURCE_REQUIRES_REVIEW` (person-flagged; machine had FOUND) | **withheld** | the reader took the "documents to be produced" list (p.44) for the posts list; the posts table (p.4, "Name of the Post") was not read |
| `examPattern` | `SOURCE_REQUIRES_REVIEW` (person-flagged; machine had FOUND with a NEEDS_REVIEW child) | **withheld** | the flattened scheme table produced a stage with marks 27 / questions 900 from a merged "2 ½ 150" cell and a subject named "½" |

The review mechanism (`tools/exam_builder/review.py`) allows only APPROVE (publish the cited
reading, optionally with a corrected value under the same citation, reviewer named) and
WITHHOLD (the field becomes NOT_EXTRACTED with the reviewer's reason — a gap a person chose,
never NOT_PUBLISHED). It cannot create a fact with no citation and cannot mark anything
"not published". Reviews are applied before the gate; the gate is unchanged. A withheld
field's section reads NEEDS_REVIEW, not "failed" and not "absent".

## FAILED / UNAVAILABLE (and why)

- **Search quota.** Tavily returned HTTP 432 ("exceeds your plan's set usage limit") from
  run 6 onward. Run 6 ended `SOURCE_FETCH_FAILURE` and run 7 `INFRASTRUCTURE_FAILURE`; in
  both, every unread field was NOT_EXTRACTED with the infrastructure note, none became
  NOT_PUBLISHED, and nothing registered. The final builds (runs 8–11) used the engine's
  existing **replay** path: the run-5 discovery manifest fixes *which* documents are used;
  every document is re-fetched from tgpsc.gov.in and re-validated; no search is made. A
  `replay` pass-through was added to `build_exam` for this.
- **Vacancies** (the notice's total), **attempts**, **FAQs**: not read; recorded as ours.
- **Posts, age limits, exam pattern**: read wrongly or un-holdably; withheld (above).
- **The application window extension.** The authority's `directRecruitment` listing shows
  "End Date 16/03/2024 05:00 PM" while the notification prints 14/03/2024. The listing row's
  dates are not read as facts (listing pages are crawled for links, never for content), so
  the record carries 14/03 with no corrigendum. Per this repo's own rule the examination page
  outranks the notice; reading listing-row facts is a genuine generic capability still missing.
- **Main Examination typed EXAM_TIER1**: the month-precision milestone carries no stage
  label the legacy union can map, so it is not distinguished from the Preliminary Test.
- **Roadmap / Mock Tests read NOT_YET_PUBLISHED** once the pattern is withheld — the derived
  sections lack their input, which is not the authority's silence; the label is imprecise.

## 17 SECTIONS (final registered record, run 11)

| # | Section | State | Fields | Populated |
|---|---|---|---|---|
| 1 | Overview | VERIFIED_AVAILABLE | officialName, authority ✓; vacancies EXTRACTION_FAILED | title, authority, overview sentence |
| 2 | Dates & Timeline | VERIFIED_AVAILABLE | dates ✓ | 4 milestones, each with provenance |
| 3 | Eligibility & Posts | NEEDS_REVIEW | qualification ✓; ageLimits, posts withheld; attempts EXTRACTION_FAILED | 1 highlight (qualification); posts [] |
| 4 | Application & Documents | VERIFIED_AVAILABLE | portal, howToApply, requiredDocuments, photo/signature, fee ✓; feeExemptions NOT_YET_PUBLISHED | applicationGuide (6 parts), fee highlight |
| 5 | Exam Pattern | NEEDS_REVIEW | examPattern withheld | patternTree [] |
| 6 | Syllabus | VERIFIED_AVAILABLE | syllabus ✓ | syllabusTree (2 roots, 124 entries) |
| 7 | Study Roadmap | NOT_YET_PUBLISHED (derived; input withheld) | — | — |
| 8 | Resources | VERIFIED_AVAILABLE | officialSources ✓ | 0 link entries materialized (limitation) |
| 9 | Practice & PYQs | NOT_YET_PUBLISHED | officialPapers | honest empty state |
| 17 | Mock Tests | NOT_YET_PUBLISHED (derived; input withheld) | — | — |
| 14 | Admit Card | VERIFIED_AVAILABLE | admitCard ✓ | rule event ("Hall Tickets") |
| 15 | Exam Day | VERIFIED_AVAILABLE | examDayChecklist ✓ | 1 instruction |
| 16 | Results & Next Steps | NOT_YET_PUBLISHED | results, nextSteps | honest empty state |
| 11 | FAQs & Official Clauses | EXTRACTION_FAILED (replay) / SOURCE_NOT_FOUND_AFTER_SEARCH (live) | faqs | — |
| 13 | Corrigenda Log | NOT_YET_PUBLISHED | corrigenda | — |
| 12 | Official Portals & Links | VERIFIED_AVAILABLE | officialSources, applicationPortal ✓ | 1 link |
| 10 | Cutoff History | NOT_YET_PUBLISHED | cutoffs | — |

No section is marked complete because its UI exists; 8 of 17 carry verified content, 6 are
the authority's absences, 2 are under review, 1 is ours.

## MATERIALIZATION / REGISTRY

`GET /api/exams` → `[("exam-websitenew-tgpsc-group-i-2024", "2024")]` ·
`GET /api/exams/exam-websitenew-tgpsc-group-i-2024` → the full record (30 keys) ·
`?cycle=2022` → **404** ("no published runtime exam with that id for cycle 2022") ·
`?cycle=2024` → 200 · `ExamRegistry.get(id, "2022")` → None. Verified through the real Flask
app (`app.test_client()`) against the run's registry file.

## PROVENANCE

12 of 12 published factual fields carry document, URL, page and verbatim excerpt (the two
intrinsic fields cite the authority resolution). Every materialized date, syllabus node,
exam-day item and highlight carries a `DataProvenance` naming `02/2024 - GROUP-I SERVICES`.
No value came from an LLM (Qwen was not enabled); no value was typed.

## ISOLATION

`src/data.ts` SHA-256 before = after in every run; per-exam fingerprints (SSC CGL, UPSC CSE,
IBPS PO, APPSC Group-I, APPSC Group-II) identical before/after; orchestration
`isolation_ok = True`; `git diff --quiet src/data.ts` clean (blob `31339b78…`). The runtime
registry used in the test is a scratch SQLite file, not `govos.db`. No cross-exam id or
cross-cycle fact reached the record (the 2022 notice is MISMATCH; the seventy-odd sibling
notifications are rejected).

## Repository search (§ NO EXAM-SPECIFIC BRANCHES)

`TGPSC | TSPSC | Telangana Public Service Commission | Group-I | Group-II | Group 1 | Group 2`:
no branch, fixture, parser, URL, selector or field mapping for this recruitment exists. Hits
are APPSC Group-I/II authored data in `src/data.ts`, their practice engines in `src/ui.tsx`,
the string `'TSPSC Group I 2026'` in `test_build.py`'s id-distinctness list, and prose in
audits. The universal code names none of them; `test_realworld_generic.py` uses fictitious
authorities and asserts on shapes only.

## Generic gaps found and fixed (each was a real cause of failure in a live run)

| # | Missing capability | Symptom on the real site | Fix (generic) |
|---|---|---|---|
| 1 | Tolerant link parsing | anchors written `href ="preview/…"` with a relative path were invisible; the exam's own notification link on a crawled page was never seen | `html_links`: any quoting/spacing, `urljoin` for relative paths |
| 2 | Document type by content | PDFs served at extension-less `/preview/<token>` routes were read as HTML (no text → "names no examination") | `load_document` sniffs `%PDF-`; `_load` uses it |
| 3 | Ordinal-distinguished siblings | "Group-I" and "Group-II" shared the alias `group`; Group-II/III/IV files were DIRECT matches | `exam_aliases` keeps the compound `group i` and drops the bare head; `alias_in` matches on a boundary; identity uses the same |
| 4 | Official name ≠ authority name | the home-page title "Telangana Public Service Commission - TGPSC" became the exam's official name, making every site page "exam-specific" | a title whose distinctive words are all the authority's (name, initials, host labels) is not the exam's name |
| 5 | Listing pages one level down | a site's Notifications/Results pages are reached from navigation, never from a seed; only 4 pages were crawled | on-estate listing links are crawled (bounded); links found there still pass the gate; a link whose text is only the recruitment's name inherits the listing's kind |
| 6 | Read the most specific documents first | with an 8-document cap, listing pages and other recruitments' notices were read and the exam's own notification was not (every FOUND field cited another recruitment's notice) | `_load_order`: compound-alias matches, DIRECT, known kind first |
| 7 | Gate: MISMATCH blocks only when cited | any site whose navigation pages name other exams was unpublishable although those pages supplied nothing | a MISMATCH source that no field cites is retained for audit and noted; a cited one still blocks |
| 8 | One authority, several hosts | `otr.tgpsc.gov.in` (apply portal) tripped the single-authority isolation check | `estate_of`/`same_estate`: sibling hosts on one registered domain are one estate (verify, discover, re-acquisition) |
| 9 | Identity: year before the title; body mentions | the 2022 notice passed as MATCH (year only in "NO. 04/2022, DATED: 26/04/2022"); the 2024 notice was AMBIGUOUS because its body mentions other examinations | nearest year on either side of the title; the title block decides — rivals named only in the body are recorded, not disqualifying; "Recruitment **for** the post of" is a title |
| 10 | Age-limit readers | "raised the maximum age limit from 44 years to 46 years" read as a 44–46 band; "Minimum Age (18 years)" label form unread; several post-scoped clauses collapsed into one band | a change narrative is not a band; bracketed figures read; disagreeing minima/maxima → NEEDS_REVIEW, never one band |
| 11 | Vacancy counter | "13.1 Vacancies:" read as 1 vacancy | a figure preceded by a digit or dot is a clause number; several figures → NEEDS_REVIEW, never summed |
| 12 | Dates beside their label | "Schedule of Main Examination … September/October 2024" typed as an application deadline (the cue after it won) | the cue whose wording ends nearest before the date line labels it; "Schedule of Main Examination" is an EXAM cue; identical (type, date) rows de-duplicated |
| 13 | Human review | no way to approve or withhold a field without editing data | `review.py` + `reviews=` on `orchestrate`/`build_exam`; recorded in the staging artifact; completeness re-evaluated after review |
| 14 | `Status` NameError in the portal dispatch | `extract_portal failed … NameError('Status')` on every build | schema `Status` imported under its own name |

Also: `replay=` pass-through on `build_exam`; fee highlight printed as text rather than a dict.

## TESTS

- New: `tools/exam_builder/test_realworld_generic.py` — **22 tests** (link parsing, PDF
  sniffing, ordinal aliases and boundary matching, gate on siblings, identity with ordinals /
  dashed titles / previous cycle / body mentions, second-level listing crawl, content-based
  kind, offline end-to-end build reading a notification found only by its content,
  authority-name guard, estate rule, isolation with sibling hosts, load order, human review
  ×4). Existing tests updated for the precise MISMATCH rule: `test_gate`,
  `test_materialize`, `test_orchestrate`.
- Full regression: `python -m unittest discover -s tools/exam_builder` **345 tests, OK**;
  `test_research_facts` 15/15; standalone modules 21/23 — the two failures
  (`test_build` fee `[100.0]` vs `['100']`, `test_contamination` fee-format) are the
  pre-existing Phase-2 regressions recorded before this test, unchanged by it.
- TypeScript: `npx tsc --noEmit` clean. Build: `dist/index.html` 2,548 kB.
- `src/data.ts`: byte-identical (git blob unchanged).

## What the test did NOT do

It did not run Qwen verification (not enabled); it did not read the listing row's extended
last date; it did not author a study roadmap or mock questions (none exist for this exam and
none were generated); it did not commit any runtime record, manifest, cache or database;
it did not add a TGPSC adapter, fixture or branch.
