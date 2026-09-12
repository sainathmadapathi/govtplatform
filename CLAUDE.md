# GovOS — India's Exam & Career Navigation Platform

Single-page React app (dark "glassmorphism" UI) that turns fragmented Indian government
recruitment notifications into a verified, provenance-cited, personalized exam journey.
SSC CGL 2026 is the "Golden Journey" reference exam and UPSC CSE 2026 is authored to the
same depth from UPSC's own documents; IBPS PO and the two APPSC exams are thin skeletons.

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

├── .env / .gitignore          # .env holds TAVILY_API_KEY (never committed)

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

```

For development run both servers. For production, `npm run build` then `python app.py`
serves the built frontend and the API together on 5000.

## Content policy: link, don't store

GovOS stores **no study material**. Every PDF and video in the Resource Library is a link
to the publisher's own server (ssc.gov.in, legislative.gov.in, ncert.nic.in, YouTube), so
nothing is redistributed and nothing goes stale in the repo. `public/` and
`generate_official_pdfs.py` were removed along with 48 MB of stored PDFs; there is no
`/resources/<file>` route any more.

The **only** content GovOS holds is the practice question bank, and each question carries a
`QuestionSource` naming the official document it was written from. `provenanceForSource()`
turns that into the question's `DataProvenance`, and every solution card shows
"Written from the official source: …" with an **Open source** link to the real document.

Two kinds of question exist, and the UI distinguishes them:

- **Sourced** (`OFFICIAL_EXERCISE` / `OFFICIAL_DOCUMENT`) — written by reading the official
  PDF. 15 quantitative questions come from NCERT Exemplar Class 10 Maths (Triangles
  `jeep206.pdf`, Trigonometry `jeep208.pdf`, Surface Areas & Volumes `jeep212.pdf`), and 14
  general-awareness questions from the Constitution of India official text plus the SSC CGL
  2026 notice. Every numeric answer was verified computationally before being committed.
- **GovOS-authored** (`GOVOS_AUTHORED`) — reasoning, English and computer questions written
  to the official syllabus and paper pattern, not taken from a past paper. These render as
  "GovOS practice question" and carry `UNDER_VERIFICATION`, never official authority.

When adding questions, read the official source and cite it; never copy a paper wholesale,
and never label an authored question as officially sourced.


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
  3 roadmap tracks, 38 resources, 6 FAQs, admit-card details, full application guide),
  `UPSC_CSE_EXAM`, `IBPS_PO_EXAM`, `APPSC_*`, `ALL_EXAMS`. **SSC CGL and UPSC CSE are the
  two authored exams**; IBPS and APPSC are skeletons. Never fill a thin exam with material
  derived from another exam — author it from that authority's own documents, as UPSC was.
- **`UPSC_CSE_EXAM` was read from UPSC's own documents on 2026-09-12**, every one fetched
  from upsc.gov.in and named in a provenance: Examination Notice No. 05/2026-CSE (4 Feb
  2026, the 159-page PDF: services, eligibility, attempts, fee, scheme, syllabi, centres),
  the e-Admit Card press note (15 May), the Preliminary result press notes (15 and 18 June:
  13,343 shortlisted, Mains window 19-28 June, Rs 200 fee, **1,016 vacancies against the
  approx. 933 in the notice** — recorded as the exam's corrigendum), the Main Examination
  press note (19 Aug: 21-23 and 29-30 Aug, QPReP 31 Aug-4 Sep), the Calendar for 2027 (the
  next cycle's dates: 13 Jan / 2 Feb / 23 May / 20 Aug 2027, all `isTentative`), and the
  minimum-qualifying-marks sheets for 2021, 2022, 2023 and 2025 (2024's sheet was not on
  UPSC's cut-off page, so it is absent rather than guessed). The 2026 question booklets are
  scanned; the item counts (GS-I 100, CSAT 80) were read from their back covers with the
  app's own OCR. 23 services with the notice's Group A/B classification; pay is **not** in
  the notice, so `upscPayProvenance` is INTERPRETATION / UNDER_VERIFICATION and says so.
  Topic weightage is GovOS's count of the official papers, marked the same way. 30 resources
  — the notice, the portal, the 2026 Prelims and Mains papers as official PDFs, the cut-off
  and calendar sheets, PIB, PRS, Economic Survey, RBI, NITI, MEA, Sansad, India Code, the
  Constitution, NCERT on DIKSHA, e-Gazette, Sansad TV (official) and six coaching channels
  whose identity and subscriber count were read from each channel page (`/channel/UC...`
  URLs from the page's canonical link) — all HTTP 200 through the app's checker that day.
- **Resource library (SSC CGL only), links only.** `officialSource()` / `pendingSource()` build
  `DataProvenance` for external links. Every `OFFICIAL_PORTAL` entry was HTTP-checked on 2026-09-09 and carries
  `linkVerifiedDate`; `ncert.nic.in` timed out from the authoring machine so it is marked
  `UNDER_VERIFICATION` ("Link check pending") rather than claimed verified. `isEssential`
  pins a resource to the "Start here" shelf. Sources are government/regulator domains only
  (SSC portal, PIB, e-Gazette, Legislative Dept, NDLI, SWAYAM, NIOS, MoSPI, Census,
  National Portal, NCERT, India Code, Sansad, RBI, NPTEL). **38 entries, all answering HTTP 200
  on 2026-09-09**: 3 direct PDFs, 20 official portals, 6 single video lessons, 8 YouTube
  channels, 1 practice tool.
- **Coaching content is listed, and labelled as such.** The eight most-followed free SSC
  YouTube channels (Adda247 SSC, Gagan Pratap, Rakesh Yadav, Rankers Gurukul, SSC Wallah,
  Parmar SSC, Piyush Varshney, English With Rani Mam) are in the library because candidates
  actually use them, but they are not government sources. `communitySource()` records them as
  `RECOMMENDATION` / `UNDER_VERIFICATION`, with the subscriber count and check date as the
  stated basis, an explicit "GovOS does not endorse this and has not fact-checked its
  lessons", and the rule that the SSC notice governs where they disagree. Channel identity
  was confirmed by fetching each channel page, not assumed from memory. PRS Legislative
  Research is listed the same way: useful, widely cited, not official.
- **The library is not static.** Four things refresh on the server without a code edit
  (see `app.py` → "Live resources"):
  1. **SSC's own notice board**, read from the portal's public API
     (`ssc.gov.in/api/general-website/portal/notice-boards` with the site's own attribute list;
     attachments become `ssc.gov.in/api/attachment/<path>` links). Shown as a "Latest from SSC's
     notice board" shelf at the top of the SSC library, CGL-filtered by headline with an
     "All SSC notices" toggle. Official by construction — it is SSC's board — so it carries a
     LIVE · OFFICIAL badge and the fetch time. Cached 6 h.
  2. **Channel uploads** from each YouTube channel's public Atom feed
     (`youtube.com/feeds/videos.xml?channel_id=UC…`, no API key). The three newest appear on
     the channel card with the fetch time. Cached 6 h per channel.
  3. **Link health on a schedule.** The library registers its URLs on load
     (`POST /api/resources/health/sync`); a daemon thread re-checks anything older than 12 h and
     stores results in `resource_link_health`, so badges are current without clicking. New
     URLs are checked in the background and the page re-polls once after 15 s. "Verify all
     links now" forces a sweep (`/health/recheck`) and stores it for the next visitor.
  4. **Verifier additions.** A PROMOTED research finding gets "Add to Resource Library" in the
     Trust Panel (`POST /api/resources/additions`). It appears in the library immediately via
     `additionToResource()`, labelled "ADDED <date> · VERIFIER-APPROVED FROM LIVE SOURCE
     RESEARCH" with provenance naming the finding, and its link joins the health schedule.
     `…/retire` hides it again. This is the only path by which research reaches candidates,
     and it is a deliberate second click after Promote.
  The background loop wakes hourly and refreshes only what is past its own interval, so
  upstream sites are not hammered; a failed refresh keeps serving the last good copy and says
  so (`stale`/`error`). Everything lives in three tables: `resource_link_health`,
  `live_feed_cache`, `resource_additions`. The static list in `data.ts` remains the seed and
  the fallback when the server is down.
- **`YOUTUBE_CHANNEL` vs `YOUTUBE_COURSE`.** A channel has no single video to embed, so it
  opens on YouTube; only a `YOUTUBE_COURSE` with a real `youtubeEmbedId` plays in the reader.
  The player used to fall back to a hardcoded video id when the field was missing, which
  silently showed the wrong lesson; it now renders only with a real id.
- `ALL_POST_STUDY_PATHS` + `getPostStudyPath(id)` — resolves current, legacy and
  equivalent post ids to an authored study path.
- Mock repository: `OFFICIAL_10_MOCK_PAPERS`, `NEW_DISCOVERED_PAPERS`, `SUBJECT_MOCK_TESTS`,
  `TOPIC_DRILL_TESTS`, `generateCustomMockTest(config)`.

**Full-shift papers are template-cycled.** 35 `*_TEMPLATES` entries exist (4 reasoning,
14 GA, 15 quant, 1 English, 1 computer); `buildFullPaperQuestions()` cycles them with
`i % len` to fill each "100-question" paper, so all papers share the same underlying items.
Adding real past-paper questions means extending those arrays.

**Custom tests are topic-scoped, not template-cycled.** `TOPIC_CATALOG` lists 47 topics (34 in-syllabus, 13 recognised as out-of-syllabus) —
key, label, subject, recognition aliases, `inSyllabus`, and an optional `generate()`. Asking
for "12 questions on calculus" must produce twelve calculus questions, so:

- `parseTestRequest(query)` turns a chat message into `{subjects, topics, numQuestions,
  difficulty, durationMinutes?, focusGoal, unrecognised}`. Aliases match on **word
  boundaries** (plural-tolerant): substring matching read "quantum physics" as Quantitative
  Aptitude, "Framework" as Time & Work and "Similar Triangles" as Simple Interest. The count
  comes from a number attached to a question-word, never from "in 10 minutes". `simple` and
  `speed` are topic words, so they are not read as difficulty.
- `generateCustomMockTest` draws per requested topic: matching bank questions first, then
  the topic's generator. Each bank question belongs to exactly **one** topic — the one whose
  longest alias its name contains (`ownerOf`) — so a trigonometry question never fills a
  speed-and-distance drill.
- **Question sources.** 12 procedural generators (calculus, percentage, ratio, average,
  SI/CI, profit & loss, time & work, speed-time-distance, algebra, number series,
  coding-decoding, direction sense) build questions from seeded random values and compute
  the answer, the distractors and the worked steps. 5 curated sets (synonyms/antonyms,
  idioms, error spotting, active-to-passive voice, computer basics — 58 items) are written
  and checked by hand, because language and factual items cannot be generated safely. All of
  it is `GOVOS_AUTHORED` and renders as "GovOS practice question"; never label it official.
- **A topic with nothing to serve is refused, not substituted.** `topicHasSupply()` is true
  when the bank or a generator can supply it. If every named topic lacks supply, the chat
  says "X is in the SSC CGL syllabus, but GovOS has no questions on it yet", lists what it
  can build in that subject, and builds nothing — "history 10 questions" must not quietly
  become a polity test. Subject fills (`suppliersForSubject`) exclude off-syllabus topics,
  so a mixed Tier-1 test never opens on calculus, and `rotateStart` varies the opening topic.
  A request with no recognisable topic in any phrasing ("cooking recipes 10 questions")
  strips request grammar and reports the leftover words as unrecognised.
- **Scarcity is stated, never hidden.** If a topic runs out the test widens to the rest of
  that subject, then to the other Tier-1 sections, and finally stops short — a question is
  never repeated inside one paper. Every decision lands in `generationNotes[]`, which the
  chat prints back, plus `requestSummary` and the count of questions actually on the
  requested topic in `description`.
- **Typos are forgiven, and said so.** Exact alias matching runs first; only if it finds no
  topic does `containsAliasFuzzy` retry, accepting a word once repeated letters collapse
  ("workk") or within one edit for 5+ letters, two for 9+. Words under four letters stay
  exact, so "si"/"ci" cannot drift. Every correction lands in `corrections[]` and the chat
  prints "(I read "workk" as "work".)" — a silent correction would hide a wrong guess.
- **Out of syllabus is named, not guessed around.** `TOPIC_CATALOG` carries thirteen
  `inSyllabus: false` topics with no generator (matrices, vectors, complex numbers,
  differential equations, programming, ML, essay writing, Hindi, foreign languages, law,
  accounting, medical, engineering) purely so the chat can say "X is not part of the SSC CGL
  syllabus" and list the nearest in-syllabus topics, instead of "could not match". Calculus
  keeps its generator and is still built with a syllabus note, because the user asked for
  that. A request matching nothing at all produces no test; the chat says it may be spelled
  differently or be outside the syllabus, and offers examples.
- Pace words are stripped before topic matching, so a "speed drill on Indian Polity" is not
  read as speed-time-distance. Watch for aliases that belong to two topics: "articles" means
  constitutional articles here, so grammar claims "article usage" instead.
- **"Test my weak areas"** (the fourth quick-prompt pill) reads `pastAttempts`, tallies
  answered questions by catalogue topic via `matchTopicByName`, and drills the four topics
  below 60%, naming each with its accuracy. With no answered questions on record it says so
  and gives a mixed test instead of pretending to personalise.

A harness that re-derives every generated answer from the question text lives in the
session scratchpad (`gen_test.ts`); the last run checked 1090 answers with 0 mismatches.
Re-run it after touching a generator: copy it to `src/`, `npx esbuild src/__gen_test.ts
--bundle --platform=node --format=cjs --outfile=<tmp>.cjs`, `node <tmp>.cjs`, then delete it
(the repo keeps 5 source files).

### Two exams, one page: nothing SSC-shaped is baked into a section
`ExamDetailView` renders every section from the record. Prose the components used to carry
for SSC moved into the SSC record, and the UPSC record supplies its own:
- Section 03 maps `exam.eligibilityHighlights` (title, body, provenance) — four cards for
  UPSC (age, attempts, degree, fee), three for SSC; with none it lists `globalRuleGroup`.
- Section 06 names `exam.syllabusSourceNote`; the Post Study Plan view appears only where
  `examHasStudyPaths(exam)` — SSC's posts differ in papers, UPSC's services are all selected
  by the same papers, so UPSC gets a sentence saying so rather than the ASO path.
- Section 10's heading and column labels come from the exam's cut-off years and stages, so
  UPSC reads "Preliminary ... (General Studies Paper-I, of 200)" and "Main ... (of 1750)".
- Section 12 maps `exam.officialLinks` (six for UPSC, SSC's three).
- `ApplicationGuide` names the guide's own portal; the SSC form simulator and the ssc.nic.in
  notice show only for an `ssc.gov.in` portal (`isSscPortal`), with a sentence for others.
- `EligibilityCalculator` takes `exam` (main passes `liveExam`); the JSO and physical
  checks appear only where the exam has such posts.
- **The practice bank belongs to one exam.** `PRACTICE_BANK_EXAM_ID` in `data.ts` is SSC
  CGL; `PracticeEngine` offers the shift papers, sectionals and drills only there and shows
  an honest empty state pointing other exams at their official papers in Resources. The test
  creator still builds aptitude drills for any exam and names the exam it judges syllabus
  membership for (`syllabusName` in `planPracticeRequest`).
- The unions in `types.ts` widened rather than loosened: `SyllabusSubject` (SSC's six plus
  UPSC's areas), `ExamStage.tier` and `ImportantDate.type` gained `INTERVIEW`, and
  `ResourceItem.subject` gained the UPSC library's groups.

**UPSC has a live board as SSC does.** upsc.gov.in's RSS is empty, so `app.py` reads the
What's New page (`_fetch_upsc_whatsnew`: 44 "Kind: Exam" rows with links and **no dates**),
records the date GovOS first saw each item (`firstSeen`, carried across refreshes), caches it
six hours as `upsc-whatsnew`, refreshes it in the hourly loop, and serves it at
`GET /api/resources/live/upsc-notices?scope=cse|all`. The Resource Library shows a "Latest
from UPSC's What's New — Civil Services" shelf for a UPSC exam, with an honest empty state
when none of the latest items concern the CSE, and the syllabus watch judges UPSC items by
first sighting and says so in its `note`.

### Conversation context — one model, three chats
Every chat answers from the same context, assembled per message by `buildChatContext(exam,
channel)` in `services.ts`: the active exam, the target post (`storageService.getTargetPost()`
resolved against `exam.posts`), the saved `UserProfile`, the journey stage, and the recent
turns for that chat. Priority is the platform's: the message, then the thread, then the
selected exam/post, then the candidate's own data, then the register.

- **Every chat is scoped to the exam in hand, visibly.** `AIAssistant` shows a "current exam
  context" strip naming the exam and saying that naming another exam switches it;
  `ResourceAIAssistant` names the library it is searching. `namedResourceAnswer`, `dateOfType`
  and the live official-domain search all take the exam from context instead of reading
  `SSC_CGL_EXAM`. One guard matters: the navigator weights a term by how few entries carry
  it, which means nothing in a library of one or two — every word is then "rare" and the
  single entry answers everything — so `namedResourceAnswer` refuses to claim the candidate
  named a document when the exam's library holds fewer than 5 entries.
- `conversationService` keeps up to 12 turns per channel (`ASSISTANT` | `PRACTICE` |
  `RESOURCES`) in `govos_chat_history`. A turn records what the assistant took it to be
  about (`subject`), and for the practice chat what it built (`topics`, `count`,
  `difficulty`) — that is what makes "make it harder" and "20 more" work.
- `deriveCandidateStage(exam)` reads the exam's own dates — never a guess — to give
  BEFORE_NOTIFICATION / APPLICATION_OPEN / APPLICATION_CLOSED / PRE_EXAM / POST_EXAM, and
  `daysToApplicationClose` supplies the countdown. This is what "what should I do next?"
  answers from.
- **Inheriting a subject is deliberate, not automatic.** `needsInheritedSubject()` is true
  only when a message names nothing of its own ("when is it?", "what about that?");
  `resolveWithHistory()` then prepends the thread's subject. A message that does name
  something ("am I eligible?") never inherits, or it would answer the previous question
  again. The reply says "Taking that as a follow-up about …" so a wrong inheritance is
  visible. The navigator applies the same test on its own reading: a query naming a format
  but no subject ("any video on that?", "pdf instead") inherits.
- **Switching exam is detected and announced.** `examNamedIn()` spots another exam from
  `ALL_EXAMS` in the message; the answer is given for that exam with a one-line note. The
  components clear their channel's history when `exam.id` changes, because "it" no longer
  refers to the same thing.
- **Context changes the answer, not just the wording.** Eligibility runs the candidate's
  saved profile through `evaluateCandidateEligibility` and names their target post's age
  band; with no profile it asks for date of birth, degree and category rather than answering
  in general. Pay lists the target post first when no post is named. "What should I study?"
  names the target post and its special qualification, or asks the candidate to choose one.
- **An answer about one entry hands over the entry.** `AssistantReply.resourceLink` carries
  the title, URL and a label matched to the kind ("Launch the tool", "Open the PDF", "Watch
  the video"), and the chat renders it as a direct button. `namedResourceAnswer()` sets it,
  and any section answer whose action points at Resources picks it up too — describing which
  tab to open, when the thing itself is one click away, is not an answer.
- **Four kinds of claim, four badges.** `AssistantReply.sourceKind` is OFFICIAL (from the
  register, cited), PLATFORM (how GovOS works), GUIDANCE (derived advice — "not an official
  rule"), CLARIFY (a question back) or UNVERIFIED (not in the register; live search offered).
  The chat renders each differently. Nothing from a live search is ever badged as official.
- The scratchpad `conv_test.tsx` drives multi-turn threads across all three chats with a
  stubbed `localStorage`; it is the fastest way to see whether context still holds.

### The syllabus is watched, and revised only by a verifier
The register's syllabus is the seed and carries the date it was verified. It changes at
runtime through the same two-step rule as resource additions, never from a scrape:

1. **Watch.** `GET /api/syllabus/watch?exam_id=&since=` reads the cached SSC notice board
   for the notices that can change a syllabus (the exam's own notice, and any corrigendum,
   addendum or revision to it) dated after the syllabus's `verifiedDate`. The Syllabus
   section shows them in an amber banner with the notice link and says plainly that the
   syllabus below is the last verified version; with nothing newer it says so in green, with
   the fetch time. Exams without a wired board get an honest "no live board yet". A notice
   is a reason to check, not a change.
2. **Revise.** The Trust Panel's Corrigendum tab shows the same list with "Use as basis"
   and a form to ADD, AMEND or RETIRE a topic citing the notice (`POST
   /api/syllabus/revisions`, table `syllabus_revisions`, `…/<id>/retire` to undo). The server
   refuses a revision with neither a notice URL nor a note. `applySyllabusRevisions(exam,
   revisions)` in `services.ts` merges active revisions over the seed; `main.tsx` fetches
   them per exam (and again on entering the exam page) and hands the merged `liveExam` to
   the exam page, practice engine, planner, library and assistant, so the syllabus count in
   a chat answer and the weights in the practice analysis agree with the Syllabus section.
   A revised topic carries a REVISED / ADDED badge linking the notice and provenance naming
   the verifier; a revision with a notice URL is `OFFICIALLY_VERIFIED`, one on a note alone
   `UNDER_VERIFICATION`. `applySyllabusRevisions` returns the same object when there is
   nothing to apply, so nothing re-renders for no reason.

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
- `conversationService` / `buildChatContext` / `deriveCandidateStage` / `daysToApplicationClose`
  — the shared conversation context described above.
- `syllabusLiveService` — `watch`, `revisions`, `addRevision`, `retireRevision`; plus the pure
  `applySyllabusRevisions(exam, revisions)`.
- `resourceLiveService` — `healthSync`, `recheck`, `sscNotices`, `channelUploads`, `additions`,
  `addResource`, `retireResource`, `status`. Every call swallows network errors and returns
  null/empty, so the library degrades to its static seed when the server is down.

### `src/ui.tsx`
All 20 components, ordered leaves-first so composites can reference them:

`Header` · `ExamFinder` · `EligibilityCalculator` · `ExamCompare` · `ExamCalendar` ·
`AIAssistant` · `AdminVerificationPanel` · `NotificationCenterModal` ·
`NotificationPreferencesModal` · `ResourceReaderModal` · `ResourceAIAssistant` ·
`PreparationPlanner` · `PostStudyPathEngine` · `PracticeEngine` ·
`PracticeApplicationSimulator` · `ApplicationGuide` · `AdmitCardSection` ·
`ExamDayChecklistSection` · `ResultNextStepsSection` · `ResourceLibrary` · `ExamDetailView`

**The assistant answers, it does not deflect.** `AIAssistant` used to have three hardcoded
branches, so "where should I check my eligibility in this platform" hit the fallback.
`answerCandidateQuery(query)` now returns `{text, verified, citation?, action?}`:

- `asksLocation()` detects "where / which tab / how do I / take me", and `PLATFORM_MAP`
  answers it — 20 entries covering eligibility, resources, practice, the application
  simulator, past attempts, saved items, target post, calendar, syllabus, application,
  admit card, cutoffs, roadmap, compare, trust/report, results, exam day, corrigenda, FAQs
  and posts. Each carries an `AssistantAction` that `main.tsx` turns into a working button,
  including a guide section number where relevant.
- **Intents are scored, never first-match.** `bestMatch()` picks the highest-scoring entry
  in `PLATFORM_MAP` and in `FACT_INTENTS`; `scoreKey()` gives a multi-word key roughly four
  times a single word's weight, and its words need not be adjacent. This is what makes
  "where is application mock practice" reach the Application Practice Simulator instead of
  Practice & Mocks: taking the first entry containing any keyword meant a generic
  "practice" beat a specific "application practice". Navigation wins when the question asks
  where something is, or when a multi-word phrase scores 6+ and beats the factual match;
  otherwise the winning `FACT_INTENTS` id selects the branch, so where a branch sits in the
  file no longer decides what it answers. **Add keys as phrases, not lone words** — a lone
  word competes badly and drags unrelated questions in.
- Factual intents read `SSC_CGL_EXAM` at answer time — age bands computed across all posts,
  the non-superseded dates, the real stage/section tables, pay by post, syllabus counts,
  resource counts by format — and cite the provenance of the record they came from. Nothing
  is retyped into the answer text, so the answers cannot drift from the register.
- The fallback still exists and still offers the live official-domain search, but it now
  lists what the assistant *can* answer instead of dead-ending. Application fee deliberately
  answers `verified: false`: the register has no fee field.
- Starter-question chips under the input make the scope visible. `renderAssistantText`
  turns `**bold**` into real bold runs; message bubbles are `pre-wrap`.
- Greetings and thanks get a human reply, not "not in the register". A post named in a pay
  question ("tax assistant") is listed first.
- **Spelling is repaired before anything is matched.** `correctAssistantQuery()` maps each
  word of four letters or more onto `assistantVocab()` (every key word, plus whole-word
  expansions of the stems, plus resource titles) when it is within a typo's distance and
  starts with the same letter; the reply opens with "(I read "whree" as "where".)".
  Without this, "whree is thr typing test tool" never registered as a "where" question and
  `asksLocation()` never fired. `bestMatch(…, loose=true)` is still the second chance for
  words the corrector left alone.
- **Each word of a question scores once.** `scoreKeys` credits keys highest-first and skips
  any that covers no new word — listing both "channel" and "channels" used to score one word
  twice and push a weak, generic match past the confidence gate.
- **A weak match is not an answer.** When the best score is under 3 and the question has two
  or more content words, the assistant looks for a resource the candidate named instead of
  replying with a generic section blurb: one stray word ("test") must not produce a
  confident Practice & Mocks answer for a question about the typing tool.
- **Naming an item beats naming a section.** `namedResourceAnswer()` runs the navigator's
  ranking over the library; a score of 10+ answers with the item itself ("The Constitution
  of India — Official Full Text (PDF)") even for a "where" question, 6+ is used on the weak
  path and once more before refusing.

**All three chats are testable headlessly.** `answerCandidateQuery`, `planPracticeRequest`
(the test creator's whole decision: BUILT / OFF_SYLLABUS / NO_MATCH, pulled out of the
component so it can be exercised) and `rankResourcesForQuery` are pure exports. The
scratchpad `all_bots_test.tsx` runs ~130 phrasings across them — typos, Hinglish, filler
words, off-topic — and prints destination/kind/top results; copy it into `src/`, bundle with
esbuild (`--jsx=automatic`), run, delete. Every behavioural fix in this area came from
reading that output, and it is the fastest way to see a regression.

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

`ResourceLibrary` is both **its own top-level tab** (the candidate-facing entry point — the
user could not find it when it was only a guide sub-section) and guide section 08. Pass
`showSectionNumber={false}` for the tab, which drops the "08 —" prefix and adds the
link-don't-store note. Either way `onOpenResource` opens `ResourceReaderModal`, so the tab
needs that modal mounted in `main.tsx` too. Contents: "Start here" essentials shelf, search, type-group and
subject chips derived from the exam's own resources (so UPSC/IBPS never show empty SSC
filters), results grouped by subject, one primary action per card chosen by
`resourceFormat`, bookmark toggle, per-card link-status badge, and a "Verify all links now"
button that shows live HTTP results. The old `ResourceAIAssistant` sits inside it, collapsed.

`ExamCalendar` is **time-aware and self-updating**. `relativeWhen(dateTimeStr, now)` turns a
milestone into "in 16 days" / "today" / "3 days ago", and a one-minute interval re-reads the
clock, so a deadline moves from tomorrow to today to done with the page open. My Exam
Timeline shows only what is still ahead, with a NEXT banner and countdown on the nearest
milestone and completed ones behind a "Show N completed" toggle; when everything has passed
it says the cycle is complete rather than showing a wall of old dates. All Exams Calendar
defaults to Upcoming (All and Completed are one click away), and the month chips are derived
from the events actually present — the old hardcoded `['FEB','MAR',…]` list with a "2026"
label could not survive the year turning.

## The exam is the unit of navigation

Everything that belongs to one exam lives inside that exam. Resources, Practice, Mocks, the
Timeline, the Application guide and both chats read the **current exam** and show only its
content; a candidate inside UPSC never meets SSC material.

`ExamDetailView` is that page: the exam's **13 parts** as the section row, then a quieter
"Also in this exam" row for the four reference sections. That is the **only** navigation on
the page. A 9-stage "candidate lifecycle" card grid used to sit above it and repeated the
same stages under different names; it was removed as a duplicate visual layer, and nothing
it pointed at went with it — every section, jump button and feature is reached from the row.

```
<exam>
├── Overview            ├── Resources
├── Dates & Timeline    ├── Practice & PYQs
├── Eligibility & Posts ├── Mock Tests
├── Application & Docs  ├── Admit Card
├── Exam Pattern        ├── Exam Day
├── Syllabus            └── Results & Next Steps
└── Study Roadmap
   also in this exam: FAQs · Corrigenda · Official Links · Cutoff History
```

`EXAM_SECTIONS` and `REFERENCE_SECTIONS` (top of the ExamDetailView block in `ui.tsx`) are
the whole structure; add a part by adding an entry and a render block, not by renumbering.

**Section numbers are the app's deep-link vocabulary** (notification `actionPayload:
{section: N}`, `AssistantAction.section` and the `initialSection` prop target them), so a
section's `num` is its **stable id, not its position**. The ids therefore keep their
historical values and Mock Tests took a fresh number rather than pushing the others along:
1 Overview · 2 Dates & Timeline · 3 Eligibility & Posts · 4 Application & Documents ·
5 Exam Pattern · 6 Syllabus · 7 Study Roadmap · 8 Resources · 9 Practice & PYQs ·
**17 Mock Tests** · 14 Admit Card · 15 Exam Day · 16 Results & Next Steps, with reference
sections 10 Cutoffs · 11 FAQs · 12 Official Links · 13 Corrigenda.

**Global navigation is what genuinely spans exams.** The header's first row is the platform
(Find Exam · the current exam · Ask GovOS AI · Trust Panel · the notification bell); the
second, quieter row is "across all exams" (Am I Eligible? · Compare Exams · All-Exam
Calendar). Practice, Resources and the Study Roadmap used to be top-level tabs **as well as**
sections of the exam they describe, so a candidate met the same feature twice under two
names; they are now only inside the exam.

**Nothing was renamed away.** `GovOSTab` still carries `PRACTICE`, `RESOURCES` and `PLANNER`,
and `navigate(tab, section?)` in `main.tsx` — the single entry point every button, assistant
action and notification goes through — translates them into `EXAM_DETAIL` at sections 9, 8
and 7. `main.tsx` still renders those three tabs as a safety net for any path that sets the
tab directly. When you move a feature, update `EXAM_SCOPED_TABS` and `PLATFORM_MAP` in the
same edit.

**One engine, two doors.** `PracticeEngine` takes `scope`: `PRACTICE` offers PYQ shift
papers, subject sectionals and topic drills; `MOCKS` opens on the AI test creator; `ALL` is
the untouched original. Both always keep `ACTIVE_TEST` and `PAST_ANALYTICS`, so a test
started in either can be sat, submitted and reviewed, and one Past Tests History serves both.
The question bank, the CBT clock, the scoring, the attempt records and the review chain are
literally the same code — only the tab row differs.

**Section 02 is the exam's own timeline**, not a copy of the calendar: it reads `exam.dates`
against a clock that re-reads itself every minute, puts what is still ahead first with a NEXT
banner, and hides completed milestones behind a toggle. A **`SUPERSEDED` date is never the
"next" milestone** — it is still listed, struck through, because the corrigendum that
replaced it is part of the record, but announcing it would send the candidate at a deadline
that no longer exists. The cross-exam view (`ExamCalendar`, the All-Exam Calendar button)
still covers every exam at once; that is the one timeline that cannot belong to a single exam.

**The current exam is stored** (`storageService.getCurrentExamId()` /
`setCurrentExamId()`, key `govos_current_exam_id`), so reopening GovOS lands where the
candidate left off, and `handleSelectExam` resets the open section to the new exam's
Overview.

`PracticeEngine` is the largest component: six views (`PAPERS_LIST`, `SUBJECT_TESTS`,
`TOPIC_DRILLS`, `AI_CHAT_ASSISTANT`, `ACTIVE_TEST`, `PAST_ANALYTICS`), a real CBT clock that
auto-submits at zero, a question palette, SSC Tier-1 scoring (**+2 correct, −0.5 incorrect**),
weak/medium/strong topic diagnosis, a derived daily-study-hours plan, and five-layer
solutions. `handleReviewPastAttempt` reconstructs old attempts through a 7-step fallback
chain so review never crashes.

### `src/main.tsx`
The `App` shell: one `activeTab` string for all ten views (three of which are now reached through `navigate()` inside the exam page rather than from the header) (`FINDER | ELIGIBILITY |
EXAM_DETAIL | PLANNER | PRACTICE | RESOURCES | COMPARE | CALENDAR | AI_ASSISTANT | ADMIN`,
exported from `ui.tsx` as `GovOSTab`) — **no router** — plus `examSection`, which lets
anything deep-link into an Exam Guide section, the resource reader modal, the provenance
modal, the report-error modal, the two notification modals, and the React root.
`handleAssistantNavigate(tab, section?)` is what the assistant's "take me there" buttons
call.

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

Syllabus (`/api/syllabus/*`): `GET watch?exam_id=&since=` · `GET|POST revisions?exam_id=` ·
`POST revisions/<id>/retire`. Table `syllabus_revisions`.

Live resources (`/api/resources/*`): `POST health/sync {urls}` (register + current health,
background-checks new URLs) · `POST health/recheck {urls}` (immediate sweep, stored) ·
`GET live/ssc-notices?scope=cgl|all&limit=N` · `GET live/upsc-notices?scope=cse|all&limit=N` ·
`GET live/channel-uploads?ids=UC…,UC…` ·
`GET live/status` · `GET|POST additions` · `POST additions/<id>/retire`. Feeds are cached in
`live_feed_cache` for 6 h, health in `resource_link_health` for 12 h; `_start_background_refresh()`
runs the hourly daemon from `__main__`.

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

Tables: `users`, `study_progress`, `research_runs`, `research_findings`, `resource_link_health`,
`live_feed_cache`, `resource_additions`, `mock_attempts` (with `details_json` holding
`userAnswers` + the whole `paperData`), `bookmarked_resources`, `candidate_notes`,
`audit_reports`, `tracked_exams`, `notification_preferences`, `candidate_notifications`.
`candidate_notes` has a schema but no endpoints and no frontend writers — harmless, but
nothing reads it. `bookmarked_resources` backs the Resource Library's Saved shelf.

## Known issues

`npx tsc --noEmit` is **clean (0 errors)** — keep it that way; the build does not typecheck,
so run it yourself.

Remaining by design, not defects:

- **Chats are context-aware but still deterministic.** They read the thread, the selected
  exam and post, the profile and the stage — there is no model call and no generation. When
  you add an intent, give it a `FACT_SUBJECTS` phrase too, or follow-ups after it will have
  nothing to inherit.
- **Authored data yes, invented personalisation no.** The register (dates, posts, syllabus,
  resources, question bank) is authored on purpose and carries provenance — that is the
  product. What must never be hardcoded is anything presented as *the candidate's*:
  - Daily study hours come from an input in the practice analysis
    (`storageService.getDailyStudyHours()`, null until they answer). The split across
    sections uses the Tier-1 marks from `exam.stages` and is boosted by the *share* of the
    candidate's weak topics in each section, capped at double — counting weak topics
    outright let one quant drill swallow three quarters of the day.
  - Weak-area cards state what was measured ("0 right, 0 wrong, 1 not attempted out of 1")
    and the topic's real weight from `exam.syllabus` (`weightagePercentage`, `avgQuestions`,
    `isHighYield`). They used to assert a cause GovOS cannot know ("prone to sign errors")
    and an invented weight ("3-4 Qs guaranteed in TCS exam pattern").
  - `getTargetPost()` returns `''` when the candidate has not chosen, never `post-aso-css`.
    Labels say "not chosen yet" and point at section 01; the statistics slice appears when
    the chosen post actually needs statistics, read from the post, not from its id.
  - The application simulator records real elapsed time and a score of passed checks over
    checks run; both were constants (120 seconds, 100 − 25 × mistakes).
  - Counts inside answer text are placeholders (`{posts}`, `{resources}`, `{syllabus}`,
    `{exam}`) filled by `fillCounts()` from the register, so "25 verified links" cannot
    survive the library growing to 38.
- **The "AI" features are deterministic local logic.** `ResourceAIAssistant` is a ranked
  search (`rankResourcesForQuery`: `readNavigatorQuery` extracts a format — pdf / video /
  channel / portal / tool — plus subjects from its own word lists and topics via
  `parseTestRequest`, then scores every resource on title, author, tag, subject and blurb,
  keeps only results in the same league as the best, and shows nothing when nothing fits —
  it used to substring-match the whole sentence and dump the first three entries on a miss,
  with an invented 4.9/5 on every card). Terms are weighted by rarity — a word in one or two
  entries ("exemplar", "prs", "sansad") identifies the item, a word in half the library
  ("ncert", "ssc") barely narrows it — and an exact format match outranks a near one, so
  "english grammar video" returns the video above the channel; `AIAssistant` is an intent engine over `PLATFORM_MAP` + `SSC_CGL_EXAM`
  (`answerCandidateQuery`); the PracticeEngine chat is a written parser over
  `TOPIC_CATALOG`; the admin SHA-256 monitor and the PDF extraction sample are fixtures.
  No model call anywhere. Preserve the framing; don't wire them to a model unasked.
  When you add a view or move a feature, update `PLATFORM_MAP` in the same edit — a stale
  map sends candidates to the wrong tab, which is worse than no answer.
- **The past-paper corpus is 35 templates** (see `data.ts` above). Custom tests are not
  limited to it — they generate per topic — but full shift papers still cycle these.
- **IBPS and APPSC datasets are thin** next to SSC CGL and UPSC CSE. Views degrade
  gracefully (the roadmap shows "0 of 0 milestones", practice shows its empty state), but
  the data, not the code, is the limit. UPSC's Result & Next Steps and Exam-Day sections
  still use the component-local, Tier-shaped content (see the Section 15/16 notes) — the
  `resultNextSteps` / `examDayChecklist` record fields exist but nothing reads them yet.
- **YouTube's Atom feed refused this machine while UPSC's channels were added** (404/500 on
  known-good IDs too), so their upload shelves were not seen live; the ids are the channel
  pages' canonical ids and the library already tolerates a failed refresh.
- **Section 16 reads the candidate's result instead of asking them to classify themselves.**
  They type their Tier-1 marks and category, or upload the scorecard: `POST /api/results/parse`
  pulls the text out of a generated PDF with `zlib` and regexes — no OCR engine, no new
  dependency — and returns marks, category, roll number and any printed "qualified"
  declaration for the candidate to confirm. **The file is parsed in memory and never stored**,
  in line with the content policy. Text in SSC PDFs is laid out character by character, so
  every match tolerates spaces inside words (`_loose()`) and split digits are rejoined
  (`_join_numbers()`); a number found next to a "marks obtained" label is HIGH confidence, a
  bare decimal is LOW and is offered as a list to pick from. **A photo or a scanned PDF is
  read by OCR**: RapidOCR (ONNX models, `pip install rapidocr-onnxruntime`, no system binary)
  reads a JPEG/PNG directly, and pypdfium2 rasterises the first three pages of a PDF with no
  text layer at ~160 dpi first. Small photos are upscaled to 1400 px wide before recognition,
  and lines are re-ordered top-to-bottom, left-to-right so the same `_parse_scorecard` runs
  over both paths. The response carries `method: TEXT_LAYER | OCR`; an OCR read adds the note
  that a digit can be misread and the UI shows "Read from your scan by OCR — CHECK THE
  DIGITS". The four OCR libraries are optional (listed in `requirements.txt`): without them
  the route answers `OCR_NOT_INSTALLED` with the install hint and the candidate types the
  marks, so the app never depends on them to start. The marks
  are then compared against `cutoffsHistory` for that category and the **year is stated**,
  because this cycle's cutoff does not exist yet; a declaration printed on the scorecard
  outranks the comparison — but only while the marks are the ones it was read with. The
  declaration is stored on the applied entry, not held in the live parse result, so typing a
  different number over an upload drops it; keeping it there once let an old "qualified"
  override 120 typed marks. The panels state their basis rather than asserting a result:
  the Tier-2 panel reads "your scorecard says you are through", "on last year's bar, X
  clears Tier-1", or "the Tier-2 plan, if you are shortlisted" when opened by hand.
- **Section 15** uses component-local content. `ExamDayChecklistItem` and
  `ResultNextStepStage` exist on `Exam` as optional fields for when per-exam data is
  authored; until then the generic CBT content shows for every exam.
- **SSC CGL 2026 dates in `data.ts` contradict the official record.** A live research run on
  2026-09-09 surfaced SSC's real notice (`ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/`
  `CGLE_Reopen_23062026.pdf`): notification published 21.05.2026, applications 21.05–22.06.2026
  (28 lakh+ applicants), then a reopening. The platform shows a 10-08-2026 notification, an
  Aug–Sept window and a corrigendum to 27-09-2026. Not changed — the user decides; use the Trust
  Panel's Live Source Research quick check to re-verify before editing.
- **Government hosts are intermittent from Indian networks; links must open for the candidate.**
  `ncert.nic.in` timed out in the user's own browser (ERR_CONNECTION_TIMED_OUT) even though it
  answered Tavily, so every NCERT link now points at a host that answers: the question
  sources and the Exemplar entry use NCERT's own upload on the Internet Archive
  (`archive.org/download/ncert-jeep2/jeepNNN.pdf`, creator NCERT, collection ncert-textbooks —
  identical file codes), and the textbook-portal entry uses DIKSHA (`diksha.gov.in/ncert`,
  Ministry of Education). Census likewise links to the data.gov.in census catalogue with
  censusindia.gov.in named as canonical. `egazette.gov.in` occasionally exceeds the checker's
  10 s timeout but answers in under a second on retry, so it stays. Rule going forward: a link
  that fails from the candidate's network is replaced or removed, never kept on the strength
  of working elsewhere. The UI marks anything it cannot reach amber "open to confirm", never
  red; red is reserved for a real HTTP error on GET.
