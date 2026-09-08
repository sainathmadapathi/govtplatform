# GovOS — India's Exam & Career Navigation Platform

Single-page React app (dark "glassmorphism" UI) that turns fragmented Indian government
recruitment notifications into a verified, provenance-cited, personalized exam journey.
SSC CGL 2026 is the fully-built "Golden Journey" reference exam; UPSC CSE and IBPS PO are
thinner secondary datasets.

## Commands

```bash
npm run dev                # Vite dev server on :3000, proxies /api -> 127.0.0.1:5000
npm run build              # vite build -> dist/index.html (single self-contained file)
python app.py              # Flask API + static server on :5000 (override with PORT)
python generate_official_pdfs.py   # regenerates public/resources/*.pdf (needs reportlab)
npx tsc --noEmit           # type check (NOT part of build — currently clean, keep it so)
```

**Ports:** the Vite dev server runs on 3000 and proxies `/api` to Flask on 5000, which is
`app.py`'s default. Run both (`npm run dev` + `python app.py`) for a full dev stack. In
production, `npm run build` then `python app.py` serves `dist/index.html` and the API
together on 5000.

## Architecture

Two independent halves joined only by `fetch('/api/...')` calls in one service file.

```
Browser (React SPA)                     Flask (app.py)              SQLite (govos.db)
  components/*  ──uses──> data/*.ts
       │                                                                  ▲
       └──> services/storageService.ts ──> localStorage (source of truth) │
                        └──> fetch /api/sqlite/* ──> app.py ──────────────┘
```

### Frontend (`src/`)

- `main.tsx` → `App.tsx`. **No router.** Navigation is a single `activeTab` string in
  `App.tsx` state: `FINDER | ELIGIBILITY | EXAM_DETAIL | PLANNER | PRACTICE | COMPARE |
  CALENDAR | AI_ASSISTANT | ADMIN`. `App.tsx` also owns the two global modals
  (provenance citation, report-an-error) and the two notification modals.
- **All styling is CSS variables + inline `style={{}}` objects.** `src/index.css` holds the
  design tokens (`--primary` indigo, `--emerald`, `--amber`, `--rose`, `--bg-dark`) plus
  utility classes: `.glass-card`, `.glass-pill`, `.btn` / `.btn-primary|emerald|secondary|
  outline`, `.badge-verified|changed|superseded|demo`, `.taxonomy-*`, `.modal-overlay`,
  `.animate-fade-in`, `.trick-card-animated`. No Tailwind, no CSS modules.
- Icons: `lucide-react` only. `firebase` is a dependency but **unused** — no imports anywhere
  (`.env.local` holds unused `VITE_FIREBASE_*` keys).

### The trust/provenance model (the product's core idea)

Nearly every data object carries a `DataProvenance` (`src/types/exam.ts`): source document
title, official URL, page number, clause number, published/verified dates, verifier name,
a `taxonomyType` (`FACT | INTERPRETATION | EXPLANATION | RECOMMENDATION`), a
`verificationLevel` (`OFFICIALLY_VERIFIED | UNDER_VERIFICATION | SUPERSEDED`), and a quoted
`excerptText`. UI surfaces it as a "Sourced Clause" button that calls
`onOpenProvenanceModal(provenance)` — the handler lives in `App.tsx` and is threaded down as
a prop through every view. Superseded dates render struck-through with a corrigendum badge.

### Component map

| Component | Role |
|---|---|
| `Header` | Top nav, tracked-exam count, notification bell + unread badge |
| `ExamFinder` | Landing/discovery. Qualification + career-field selects and text search all filter `ALL_EXAMS`; exams lacking discovery metadata are never hidden. Track toggle |
| `EligibilityCalculator` | Profile form → `evaluateEligibility` → per-post verdict cards with filters. Hardcoded to `SSC_CGL_EXAM` |
| `ExamDetailView` | **The hub.** 16 numbered sections + a 9-step lifecycle stepper. Hosts/embeds most other components |
| `ApplicationGuide` | Section 4. Two modes: the simulator, or OTR steps / photo+signature specs / certificate validity checker / rejection pitfalls |
| `PracticeApplicationSimulator` | 6-step fake SSC application form. Real file uploads are measured client-side (photo 20–50 KB & portrait aspect; signature 10–20 KB) and scored against SSC rules; also has "preset trap" mode (glasses/cap/block-capitals). Saves result as a mock attempt |
| `PostStudyPathEngine` | Section 6 default view. Per-target-post module checklist, incl. an explicit "you DON'T need to study" list. Persists via `storageService` |
| `PreparationPlanner` | Section 7 (also the `PLANNER` tab). Roadmap track selector, daily timetable, expandable phases/weeks. Goal checkboxes persist per exam via `storageService` |
| `PracticeEngine` | Section 9 (also the `PRACTICE` tab). Full CBT engine — see below |
| `ResourceReaderModal` | In-app chapter reader, embedded `youtube-nocookie` player, direct PDF iframe, print/download |
| `ResourceAIAssistant` | Keyword→resource matcher styled as chat (Section 8) |
| `AIAssistant` | `AI_ASSISTANT` tab. Keyword branches over eligibility/dates/negative-marking; falls back to "no verified source found" |
| `AdminVerificationPanel` | `ADMIN` tab, 4 views: SHA-256 source-health monitor, corrigendum & conflict queue, candidate accuracy reports (live from `/api/reports`), PDF-extraction sample |
| `ExamCalendar` | `CALENDAR` tab. "My Timeline" (tracked exams) vs "All Exams Calendar" (flattened `exam.dates`, month filter) |
| `ExamCompare` | Two-exam matrix, every row derived from the exam records (age range, pay levels, stages, physical standards, latest cut-off, next date, career fields) |
| `NotificationCenterModal` / `NotificationPreferencesModal` | Inbox with filters; channel toggles, real `Notification.requestPermission()`, simulated OTP for WhatsApp, test-alert dispatch |
| `AdmitCardSection` / `ExamDayChecklistSection` / `ResultNextStepsSection` | Sections 14/15/16 |

**`ExamDetailView` section numbers are the app's deep-link vocabulary.** Notification
`actionPayload: { section: N }` and the `initialSection` prop refer to them:
1 Overview/Posts · 2 Dates · 3 Eligibility · 4 Application · 5 Pattern · 6 Study Plan+Syllabus ·
7 Roadmap · 8 Resources · 9 Practice · 10 Cutoffs · 11 FAQs · 12 Links · 13 Corrigenda ·
14 Admit Card · 15 Exam-Day Checklist · 16 Result Next Steps.

### PracticeEngine (largest component, ~2000 lines)

Six views via `activePracticeTab`: `PAPERS_LIST`, `SUBJECT_TESTS`, `TOPIC_DRILLS`,
`AI_CHAT_ASSISTANT`, `ACTIVE_TEST`, `PAST_ANALYTICS`.

- Real CBT mechanics: countdown timer (auto-submits at 0), pause, question palette with
  answered/marked-for-review states, section jump tabs, clear response.
- Scoring is hardcoded SSC Tier-1: **+2 correct, −0.5 incorrect**.
- On submit → weak (<50%) / medium (50–75%) / strong (>75%) topic classification, a
  derived "daily study hours" plan that grows with weak areas, and a solutions view with
  five layers per question: plain-English explanation, technical-terms glossary,
  step-by-step method, animated shortcut-trick card, crucial takeaway.
- The "AI chat" is a **keyword parser**, not a model: it regex-matches subjects, a question
  count, and difficulty, then calls `generateCustomMockTest`.
- "Sync Latest Sourced Papers" is a `setTimeout(1200)` that merges the local
  `NEW_DISCOVERED_PAPERS` array — no network call.
- `handleReviewPastAttempt` reconstructs an old attempt through a 7-step fallback chain
  (embedded `paperData` → id → exact title → fuzzy title → regenerate → a hardcoded
  application-sim paper → `OFFICIAL_10_MOCK_PAPERS[0]`) so review never crashes.

### Data layer (`src/data/`)

- `examsData.ts` (~2600 lines) — `SSC_CGL_EXAM` (18 posts, 9 dates incl. one superseded,
  3 stages, ~21 syllabus topics, 3 roadmap tracks, ~14 resources, 6 FAQs, full application
  guide), `UPSC_CSE_EXAM`, `IBPS_PO_EXAM`, and `ALL_EXAMS`.
- `postStudyPathsData.ts` — reusable `StudyModuleRequirement` constants composed into
  `ALL_POST_STUDY_PATHS: Record<postId, PostStudyPath>` for 7 posts.
- `mockPapersData.ts` — `OFFICIAL_10_MOCK_PAPERS`, `NEW_DISCOVERED_PAPERS`,
  `SUBJECT_MOCK_TESTS`, `TOPIC_DRILL_TESTS`, and `generateCustomMockTest(config)`.

**Question content is template-cycled, not authored per question.** There are only 11 unique
question templates total (4 reasoning, 3 quant, 2 GA, 1 English, 1 computer).
`buildFullPaperQuestions()` builds each "100-question shift paper" as 25 reasoning + 25 GA +
25 quant + 25 English cycling those templates with `i % templates.length`, so every paper is
effectively the same 11 questions repeated and all 12 papers share identical content. Adding
real questions means extending the `*_TEMPLATES` arrays.

### Services (`src/services/`)

- `storageService.ts` — a singleton class, the **only** place that talks to the API.
  Dual persistence: localStorage is written first and is the effective source of truth;
  every SQLite call is fire-and-forget inside `try/catch` so the app works fully offline.
  Keys: `govos_target_post_id`, `govos_completed_modules`, `govos_mock_attempts` (capped at
  50), `govos_candidate_profile`, `govos_bookmarked_resources`, `govos_tracked_exams`,
  `govos_notification_preferences`, `govos_candidate_notifications`,
  `govos_completed_syllabus_topics`, `govos_roadmap_goals`, `govos_pending_reports`.
  Also owns `generatePersonalizedNotificationsForTrackedExams(allExams)` — a deterministic
  generator that walks each tracked exam's `dates`, emits notifications with stable ids
  (`notif-<examId>-deadline-3d`), respects `eventSubscriptions` + `reminderSchedule`,
  **preserves `isRead` and `createdAt` across regeneration by id**, keeps user test alerts
  (`notif-test-*`), sorts unread → priority → newest, and background-POSTs the batch.
  (`ExamDayChecklistSection` bypasses this service and uses `govos_checklist_<examId>` directly.)
- `eligibilityEngine.ts` — `evaluatePostEligibility` per post (age vs `maxAge + relaxation`,
  degree normalization, the JSO 60%-maths-or-statistics rule, the Statistical Investigator
  rule, physical/colour-blindness restrictions) and `evaluateEligibility` aggregating to
  `ELIGIBLE | CONDITIONAL | INELIGIBLE` with plain-English text and legal clauses.
- `profileUtils.ts` — `calculateAge`, `calculateDetailedAge` (y/m/d against the crucial
  date), `getCategoryAgeRelaxation` (OBC +3, SC/ST +5, PwBD +10, else 0).

### Backend (`app.py`, `database.py`)

Flask + `flask-cors`, no ORM, no auth. `database.py` creates 9 tables on import and seeds a
single `default-candidate` user tracking `exam-ssc-cgl-2026`. **Every endpoint takes
`user_id` from a query param defaulting to `'default-candidate'`** — single-user by design.

`/` and `/<path>` serve `dist/index.html` (SPA fallback); `/resources/<file>` serves the
generated PDFs. API: `/api/sqlite/status`, `/profile`, `/progress`, `/mock-attempts`,
`/sync-all`, `/tracked-exams`, `/notifications` (GET/POST/DELETE),
`/notifications/read`, `/notifications/preferences`, plus `/api/reports` (GET/POST) and
`/api/reports/<id>/status` (POST).

Tables: `users`, `study_progress`, `mock_attempts` (with `details_json` holding
`userAnswers` + the whole `paperData`), `bookmarked_resources`, `candidate_notes`,
`audit_reports`, `tracked_exams`, `notification_preferences`, `candidate_notifications`.
`bookmarked_resources` and `candidate_notes` have schemas but no endpoints and no frontend
writers — dead tables. `audit_reports` is written by `POST /api/reports` (from the Report
Error modal) and read/updated by `GET /api/reports` and `POST /api/reports/<id>/status`
(the admin Trust Panel).

## Known issues

All issues previously listed here were fixed. `npx tsc --noEmit` is **clean (0 errors)** —
keep it that way; the build (`vite build`) still does not typecheck, so run it yourself.

Remaining by design, not defects:

- **Question content is thin.** The 11 `*_TEMPLATES` entries in `mockPapersData.ts` are
  still cycled to fill every "100-question" paper. Adding real questions means extending
  those arrays — the plumbing is correct, the corpus is small.
- **The "AI" features are deterministic local logic.** `AIAssistant`, `ResourceAIAssistant`
  and the PracticeEngine chat are keyword matchers; the admin SHA-256 monitor and the PDF
  extraction sample are fixtures. Preserve the framing; don't wire them to a model unasked.
- **`bookmarked_resources` and `candidate_notes`** exist in `database.py` with no endpoints
  and no frontend writers. Harmless, but nothing reads them.
- **UPSC and IBPS datasets are thin** next to SSC CGL — few posts, short syllabi, sparse
  roadmaps. Views degrade gracefully (e.g. the roadmap shows "0 of 0 milestones"), but the
  data, not the code, is the limit.
- **Sections 15 and 16** still use component-local content. `ExamDayChecklistItem` and
  `ResultNextStepStage` exist on `Exam` as optional fields for when per-exam data is
  authored; until then the generic CBT content is shown for every exam.

## Change log (2026-09-08)

Navigation hierarchy in `ExamDetailView`:
- Candidate Lifecycle promoted to primary nav ("What should I do next?"), 9 stage cards with
  icons, action lines and explicit `Open → Section NN` targets, plus a Current Stage panel.
- The 16 section tabs became a quiet, collapsible, grouped reference index.
- `sectionToStep` keeps the lifecycle in sync with whichever section is open; a context
  strip above each section shows the breadcrumb and related sections.

Correctness fixes:
- All 24 TypeScript errors resolved. `ArrowRight` was missing from `ExamDetailView`'s
  imports — Section 10 threw at render. `SourceHealthLog` added to `types/exam.ts`.
  `ShortcutTrick.trickSteps`, the extra `questionType` values, `PracticeQuestion.difficulty:
  'ADAPTIVE'`, `MockPaper.category: 'SECTIONAL_MOCK'` and optional `CustomTestConfig.focusGoal`
  now match the data that already existed. Four UPSC/IBPS posts got their missing `payScale`.
- Post ids aligned with `examsData.ts` (`post-si-cbi`, `post-tax-assistant-cbdt`,
  `post-auditor-cag`). New `getPostStudyPath()` resolves legacy ids and maps posts that share
  a preparation path, so the engine no longer silently falls back to ASO.
- "Report Error" now actually POSTs to `/api/reports`, queues locally when the server is
  down, and retries on next load. Empty descriptions are blocked; the confirmation says
  whether it was delivered or queued.
- Admin Trust Panel: the Corrigendum tab rendered a blank panel — it now shows the open
  conflict queue and the published corrigenda register. Added a Candidate Accuracy Reports
  tab with resolve/reject, backed by new `GET /api/reports` and
  `POST /api/reports/<id>/status`.
- Roadmap weekly goals and syllabus topic ticks now persist per exam via `storageService`
  (`govos_roadmap_goals`, `govos_completed_syllabus_topics`) instead of resetting on unmount.
- Exam Finder's qualification and field dropdowns now filter, driven by new optional
  `minimumQualification` / `careerFields` on `Exam`. Exams without metadata are never hidden;
  there's a "no matches" state and a Reset Filters control.
- Exam Compare's matrix is derived from the exam records (age range, pay levels, stages,
  physical standards, latest cut-off, next date, career fields) instead of hardcoded
  SSC-vs-UPSC text.
- `admitCardDetails` populated for SSC CGL and read by `AdmitCardSection`. SSC's nine zonal
  mirrors were previously rendered on the UPSC and IBPS pages too; the block now only appears
  for authorities that declare mirrors.
- Flask's default port moved 3000 → 5000 to match the Vite proxy and stop colliding with the
  dev server.
- Header nav label said "14-Section Guide" against 16 sections; now just "Exam Guide".
