# GovOS — India's Exam & Career Navigation Platform

Single-page React app (dark "glassmorphism" UI) that turns fragmented Indian government
recruitment notifications into a verified, provenance-cited, personalized exam journey.
SSC CGL 2026 is the fully-built "Golden Journey" reference exam; UPSC CSE and IBPS PO are
thinner secondary datasets.

## Project layout

```
govt-platform/
├── app.py                     # Flask API + SQLite schema + static serving + Tavily research pipeline
├── index.html                 # HTML shell + all global CSS
├── govos.db                   # SQLite database
├── requirements.txt           # Flask, flask-cors
├── package.json               # React, lucide-react, Vite
├── vite.config.ts             # dev proxy + single-file build
├── tsconfig.json
├── generate_official_pdfs.py  # one-off authoring script for public/resources PDFs
├── .env / .gitignore          # .env holds TAVILY_API_KEY (never committed)
├── public/resources/          # 6 official PDFs served at /resources/<name>
└── src/
    ├── main.tsx               # App shell, global modals, React root
    ├── types.ts               # every interface and union
    ├── data.ts                # exam register + verified resource library + mock papers + study paths
    ├── services.ts            # storage, eligibility engine, profile maths
    └── ui.tsx                 # all 20 components, in dependency order
```

Five frontend source files, one backend file. The build inlines everything into a single
self-contained `dist/index.html` with no runtime CDN dependencies (Google Fonts aside).

## Commands

```bash
npm run dev                # Vite dev server on :3000, proxies /api -> :5000
python app.py              # Flask API + static server on :5000 (override with PORT)
npm run build              # -> dist/index.html, fully self-contained
npx tsc --noEmit           # type check (NOT part of build — currently clean, keep it so)
python generate_official_pdfs.py   # regenerate public/resources PDFs (needs reportlab)
```

For development run both servers. For production, `npm run build` then `python app.py`
serves the built frontend and the API together on 5000.

## Architecture

Two halves joined only by `fetch('/api/...')` calls, all of which live in `services.ts`.

```
Browser (React SPA)                       Flask (app.py)            SQLite (govos.db)
  ui.tsx ──uses──> data.ts, types.ts
     │                                                                     ▲
     └──> services.ts ──> localStorage (source of truth)                   │
                    └──> fetch /api/sqlite/* ──> app.py ───────────────────┘
```

### `src/types.ts`
Every interface and union. The core one is `DataProvenance` — source document, official URL,
page, clause, published/verified dates, verifier, `taxonomyType`
(`FACT | INTERPRETATION | EXPLANATION | RECOMMENDATION`), `verificationLevel`
(`OFFICIALLY_VERIFIED | UNDER_VERIFICATION | SUPERSEDED`) and a quoted excerpt. Nearly every
data object carries one; the UI surfaces it as a "Sourced Clause" button wired to
`onOpenProvenanceModal`, threaded down from `main.tsx`. Superseded dates render
struck-through with a corrigendum badge. **This provenance chain is the product's core idea.**

### `src/data.ts`
- `SSC_CGL_EXAM` (18 posts, 9 dates incl. one superseded, 3 stages, ~21 syllabus topics,
  3 roadmap tracks, 25 resources, 6 FAQs, admit-card details, full application guide),
  `UPSC_CSE_EXAM`, `IBPS_PO_EXAM`, `ALL_EXAMS`. **Only SSC CGL has real, authored
  content**; UPSC and IBPS are skeletons (3/1 posts, one resource each). Do not extend
  them with SSC-derived material — treat SSC CGL as the sole content exam until told
  otherwise.
- **Resource library (SSC CGL only).** `officialSource()` / `pendingSource()` build
  `DataProvenance` for external links. Every `OFFICIAL_PORTAL` entry was HTTP-checked on 2026-09-09 and carries
  `linkVerifiedDate`; `ncert.nic.in` timed out from the authoring machine so it is marked
  `UNDER_VERIFICATION` ("Link check pending") rather than claimed verified. `isEssential`
  pins a resource to the "Start here" shelf. Sources are government/regulator domains only
  (SSC portal, PIB, e-Gazette, Legislative Dept, NDLI, SWAYAM, NIOS, MoSPI, Census,
  National Portal, NCERT).
- `ALL_POST_STUDY_PATHS` + `getPostStudyPath(id)` — resolves current, legacy and
  equivalent post ids to an authored study path.
- Mock repository: `OFFICIAL_10_MOCK_PAPERS`, `NEW_DISCOVERED_PAPERS`, `SUBJECT_MOCK_TESTS`,
  `TOPIC_DRILL_TESTS`, `generateCustomMockTest(config)`.

**Question content is template-cycled.** Only 11 `*_TEMPLATES` entries exist (4 reasoning,
3 quant, 2 GA, 1 English, 1 computer); `buildFullPaperQuestions()` cycles them with
`i % len` to fill each "100-question" paper, so all papers share the same underlying items.
Adding real questions means extending those arrays.

### `src/services.ts`
- `storageService` — the **only** place that talks to the API. localStorage is written
  first and is the effective source of truth; every SQLite call is fire-and-forget inside
  `try/catch`, so the app works fully offline. Keys: `govos_target_post_id`,
  `govos_completed_modules`, `govos_mock_attempts` (capped at 50), `govos_candidate_profile`,
  `govos_bookmarked_resources`, `govos_tracked_exams`, `govos_notification_preferences`,
  `govos_candidate_notifications`, `govos_completed_syllabus_topics`, `govos_roadmap_goals`,
  `govos_pending_reports`. `toggleResourceBookmark()` / `loadBookmarksFromSQLite()` back the
  library's Saved shelf; `verifyResourceLinks(urls)` asks the server to HTTP-check links
  (browsers can't, because of CORS). Also owns
  `generatePersonalizedNotificationsForTrackedExams()`, which walks each tracked exam's
  dates, emits notifications with stable ids (`notif-<examId>-deadline-3d`), honours
  `eventSubscriptions` + `reminderSchedule`, and preserves `isRead`/`createdAt` across
  regeneration by id.
- `evaluateEligibility` / `evaluatePostEligibility` — per-post age vs `maxAge + relaxation`,
  degree normalization, the JSO 60%-maths-or-statistics rule, Statistical Investigator rule,
  physical/colour-blindness restrictions; aggregates to `ELIGIBLE | CONDITIONAL | INELIGIBLE`.
- `calculateAge`, `calculateDetailedAge`, `getCategoryAgeRelaxation`
  (OBC +3, SC/ST +5, PwBD +10).
- `researchService` — `getStatus`, `search(query, mode, examId?)`, `extract(urls, findingId?)`,
  `history`, `getFinding`, `setFindingStatus`. Returns a `ResearchOutcome<T>` discriminated
  union so the UI can render the setup notice on 503 instead of a generic error.

### `src/ui.tsx`
All 20 components, ordered leaves-first so composites can reference them:

`Header` · `ExamFinder` · `EligibilityCalculator` · `ExamCompare` · `ExamCalendar` ·
`AIAssistant` · `AdminVerificationPanel` · `NotificationCenterModal` ·
`NotificationPreferencesModal` · `ResourceReaderModal` · `ResourceAIAssistant` ·
`PreparationPlanner` · `PostStudyPathEngine` · `PracticeEngine` ·
`PracticeApplicationSimulator` · `ApplicationGuide` · `AdmitCardSection` ·
`ExamDayChecklistSection` · `ResultNextStepsSection` · `ResourceLibrary` · `ExamDetailView`

**Live Source Research (Tavily).** The Admin Trust Panel's "Live Source Research" tab runs a
Tavily search (scope: official domains only / news / whole web), and every result is
classified by domain — `OFFICIAL` (`*.gov.in`, `*.nic.in`, statutory bodies), `TRUSTED_PUBLIC`
(`*.ac.in`, `*.edu`, PRS), or `UNVERIFIED` — stored in `research_runs` / `research_findings`,
and reviewed by a human (promote / reviewed / reject) with optional full-text extraction.
The `AIAssistant` offers a live official-domain search **only** on its fallback path, with
results badged "LIVE WEB RESULTS — NOT YET VERIFIED". Nothing from research reaches
candidates as verified; promoting a finding records the decision, and adding it to `data.ts`
with provenance remains a deliberate edit. Shared helpers: `researchTrustMeta`,
`ResearchSetupNotice` (shown when no key is configured).

`ResourceLibrary` (Section 08): "Start here" essentials shelf, search, type-group and
subject chips derived from the exam's own resources (so UPSC/IBPS never show empty SSC
filters), results grouped by subject, one primary action per card chosen by
`resourceFormat`, bookmark toggle, per-card link-status badge, and a "Verify all links now"
button that shows live HTTP results. The old `ResourceAIAssistant` sits inside it, collapsed.

`ExamDetailView` is the hub: a 9-stage **candidate lifecycle** as primary navigation, plus a
collapsible grouped index of **16 detail sections** as secondary reference. `sectionToStep`
keeps the lifecycle in sync with whichever section is open.

**Section numbers are the app's deep-link vocabulary** (notification `actionPayload:
{section: N}` and the `initialSection` prop target them):
1 Overview/Posts · 2 Dates · 3 Eligibility · 4 Application · 5 Pattern · 6 Study Plan+Syllabus ·
7 Roadmap · 8 Resources · 9 Practice · 10 Cutoffs · 11 FAQs · 12 Links · 13 Corrigenda ·
14 Admit Card · 15 Exam-Day Checklist · 16 Result Next Steps.

`PracticeEngine` is the largest component: six views (`PAPERS_LIST`, `SUBJECT_TESTS`,
`TOPIC_DRILLS`, `AI_CHAT_ASSISTANT`, `ACTIVE_TEST`, `PAST_ANALYTICS`), a real CBT clock that
auto-submits at zero, a question palette, SSC Tier-1 scoring (**+2 correct, −0.5 incorrect**),
weak/medium/strong topic diagnosis, a derived daily-study-hours plan, and five-layer
solutions. `handleReviewPastAttempt` reconstructs old attempts through a 7-step fallback
chain so review never crashes.

### `src/main.tsx`
The `App` shell: one `activeTab` string for all nine views (`FINDER | ELIGIBILITY |
EXAM_DETAIL | PLANNER | PRACTICE | COMPARE | CALENDAR | AI_ASSISTANT | ADMIN`) — **no
router** — plus the provenance modal, report-error modal and the two notification modals,
and the React root.

### Styling
All CSS lives in `index.html`'s `<style>` block: tokens (`--primary` indigo, `--emerald`,
`--amber`, `--rose`, `--bg-dark`) and utilities `.glass-card`, `.glass-pill`, `.btn` /
`.btn-primary|emerald|secondary|outline`, `.badge-verified|changed|superseded|demo|pending`,
`.taxonomy-*`, `.modal-overlay`, `.animate-fade-in`, `.trick-card-animated`. Components use
inline `style={{}}` objects for everything else. No Tailwind, no CSS modules.

### `app.py`
Flask + flask-cors, no ORM, no auth. Creates 9 tables on startup and seeds a single
`default-candidate` user tracking SSC CGL. **Every endpoint takes `user_id` from a query
param defaulting to `'default-candidate'`** — single-user by design.

`/` and `/<path>` serve `dist/index.html` (SPA fallback); `/resources/<file>` serves the
PDFs. API: `/api/sqlite/status`, `/profile`, `/progress`, `/mock-attempts`, `/sync-all`,
`/tracked-exams`, `/notifications` (GET/POST/DELETE), `/notifications/read`,
`/notifications/preferences`, `/api/sqlite/bookmarks` (GET/POST), `/api/reports`
(GET/POST), `/api/reports/<id>/status` (POST), and `/api/resources/verify-links`
(POST `{urls: []}` → HEAD-then-GET each with browser-like headers and a cookie jar, 8
threads, 10s timeout; classifies HEALTHY / REDIRECT / BLOCKED / BROKEN / UNREACHABLE.
Only GET results are trusted, because several portals answer HEAD with 404).

Research pipeline (`/api/research/*`): `GET status` (configured?, run/pending counts,
official domain list) · `POST search {query, mode, exam_id?, max_results?}` · `POST extract
{urls, finding_id?}` · `GET history?limit` · `GET findings/<id>` · `POST findings/<id>/status`.
Tavily is called with `urllib` (no SDK); the key is read from the environment or a minimal
`.env` loader (`_load_dotenv`, no python-dotenv dependency) and sent both as a bearer header
and in the body for API-version compatibility. `TAVILY_BASE_URL` can be overridden — the
scratchpad `mock_tavily.py` used for testing relies on that. Without a key every research
route returns 503 with a `setup` hint and the UI shows how to configure it.
**Tavily's `include_domains` is advisory in practice** — a live OFFICIAL-scope run returned five
coaching sites alongside one ssc.gov.in notice — so `research_search` enforces the scope
server-side (only OFFICIAL-classified results are kept/stored) and returns `filteredOut`.
The key lives in the gitignored `.env`; the user adds it themselves.

Tables: `users`, `study_progress`, `research_runs`, `research_findings`, `mock_attempts` (with `details_json` holding
`userAnswers` + the whole `paperData`), `bookmarked_resources`, `candidate_notes`,
`audit_reports`, `tracked_exams`, `notification_preferences`, `candidate_notifications`.
`candidate_notes` has a schema but no endpoints and no frontend writers — harmless, but
nothing reads it. `bookmarked_resources` backs the Resource Library's Saved shelf.

## Known issues

`npx tsc --noEmit` is **clean (0 errors)** — keep it that way; the build does not typecheck,
so run it yourself.

Remaining by design, not defects:

- **The "AI" features are deterministic local logic.** `AIAssistant`, `ResourceAIAssistant`
  and the PracticeEngine chat are keyword matchers; the admin SHA-256 monitor and the PDF
  extraction sample are fixtures. Preserve the framing; don't wire them to a model unasked.
- **Question corpus is 11 templates** (see `data.ts` above).
- **UPSC and IBPS datasets are thin** next to SSC CGL. Views degrade gracefully (the roadmap
  shows "0 of 0 milestones"), but the data, not the code, is the limit.
- **Sections 15 and 16** use component-local content. `ExamDayChecklistItem` and
  `ResultNextStepStage` exist on `Exam` as optional fields for when per-exam data is
  authored; until then the generic CBT content shows for every exam.
- **SSC CGL 2026 dates in `data.ts` contradict the official record.** A live research run on
  2026-09-09 surfaced SSC's real notice (`ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/`
  `CGLE_Reopen_23062026.pdf`): notification published 21.05.2026, applications 21.05–22.06.2026
  (28 lakh+ applicants), then a reopening. The platform shows a 10-08-2026 notification, an
  Aug–Sept window and a corrigendum to 27-09-2026. Not changed — the user decides; use the Trust
  Panel's Live Source Research quick check to re-verify before editing.
- **Automated link checks are conservative.** `ncert.nic.in` and `censusindia.gov.in`
  time out for `urllib` from some networks while opening fine in a browser; the UI labels
  these amber "Could not reach automatically · open to confirm", never red. Red is reserved
  for a real HTTP error on GET.
