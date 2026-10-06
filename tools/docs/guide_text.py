"""The hand-written, plain-language half of docs/GovOS_Guide.html.

Each topic is told twice: **simple** -- for someone who has never programmed -- and **tech** -- the exact
mechanism, naming the functions, files, tables and limits involved. Markup, rendered by build_guide.rich():

* `code`, **bold**, *italic*, [text](url) as in Markdown; a blank line starts a paragraph; "- " starts a list item
* [[name]]        a link to that declaration's entry in the reference (warned about if no such declaration)
* {{doc:Heading}} a link to that heading of CLAUDE.md, rendered in chapter 12 (warned about if no such heading)

Edit this file when how something works changes; the reference chapters are regenerated from the code.
"""

# ------------------------------------------------------------------------------------------------ the story
STORY = [
    # ======================================================================== the idea
    ('What GovOS is', 'idea', """
Every year lakhs of people in India prepare for government jobs: SSC, UPSC, bank exams, state commissions.
The information they need is scattered. A notice PDF on one website, a date change on another page, a
syllabus in a 130-page document, a result in a press note. People end up trusting coaching sites and
WhatsApp forwards, which are often wrong.

GovOS puts all of it for one exam in one place, in order: find an exam, check whether you are eligible,
see the dates, learn how to apply, study the syllabus, practise, get your admit card, sit the exam and
read your result.

The one big rule: **every fact can show where it came from.** Next to a date or a number there is an
**Evidence** button. It opens the exact words from the official document, with the page number and a
link. If GovOS does not have that proof, it says so instead of pretending.""",
     """GovOS is a single-page React app (`src/`) and a Flask server (`app.py`) with a SQLite database
(`govos.db`). Its core data type is the exam record, `Exam` in `src/types.ts`. Nearly every value in it
carries a [[DataProvenance]]: source document, official URL, page, clause, quoted excerpt, verification
level, and evidence type (DIRECT, RECONCILED or DERIVED). The candidate sees this through
[[EvidenceButton]] and [[EvidencePanel]]. Whether something may be called verified is decided by one rule,
[[factVerification]]; the server applies the same rule (`tools/claude_cli/context.py`), and both are held
to `tools/claude_cli/fact_verification_cases.json`. See {{doc:Evidence: "where did GovOS get this?", the same way for every fact}}."""),

    ('The pieces, and how they talk', 'pieces', """
Think of GovOS as a shop with a front counter and a back office.

- **The front counter is the web page** you see in the browser. It holds all the screens, and it already
  carries the exam information inside it, so it opens fast and works even without the internet.
- **Your own notebook is the browser's storage.** Whatever you save (exams you track, your profile, your
  test scores) is written there first, so nothing is lost if the server is down.
- **The back office is the server.** It keeps a copy of your saved things in a database, fetches the
  latest notices from official websites, checks that links still open, and reads uploaded scorecards.
- **Claude, an AI, is a helper in the back office.** It is switched off unless the owner turns it on, and it
  is never trusted on its own word. Everything it says is checked against official text first.""",
     """The browser half: `main.tsx` (the shell: tabs, modals, the root), `ui.tsx` (every component, ordered
leaves-first), `services.ts` (storage, eligibility, every API call), and `data.ts` + `types.ts` (the exam
register and every type). `npm run build` (Vite with `vite-plugin-singlefile`) inlines everything into one
`dist/index.html`.

The server half: `app.py` creates its tables at import (`init_database`), serves `dist/index.html` at `/`
with an SPA fallback, and exposes the `/api/*` routes. A daemon thread refreshes feeds and link health
hourly. Claude lives behind `tools/claude_cli` (gateway, job queue, fixed templates). The two halves meet
only through `fetch('/api/…')` calls, all inside `services.ts`. localStorage is written first; the SQLite
write is fire-and-forget inside `try/catch` ([[storageService]]). See Figure 1 in chapter 4."""),

    ('Which exams it knows', 'exams', """
GovOS holds a small set of exams, and it is honest about how deep each one goes:

- **SSC CGL 2026** and **UPSC Civil Services 2026** were written by hand from the commissions' own
  documents. Every date, post, rule and syllabus topic was read from the official PDF or exam page.
- **IBPS PO 2026** and **APPSC Group-I and Group-II** are thinner. The features work for them, but where
  something has not been read yet, the screen says exactly what is missing.
- **TGPSC Group-I** was read by GovOS's own machine reader from the commission's website and stored in the
  database. It is a "machine-read" exam.
- **TG TET 2026-II** (the Special Teacher Eligibility Test for in-service teachers in Telangana) was written by
  hand from the Department of School Education's own notification, bulletin, press note and syllabus files. It
  is an *eligibility test*, not a recruitment: passing it fills no post, so it has no vacancies, pay or age
  band, and GovOS says so instead of printing "0 posts".
- **JEE (Main) 2026** (the National Testing Agency's engineering, architecture and planning entrance test) was
  written by hand from NTA's own information bulletin, syllabus, FAQ and result press release. It is an
  *admission test*: its scores decide admission to institutions, so it too has no posts. Its 2026 cycle is over
  (the Paper 1 result was declared on 20 April 2026); NTA had published nothing for 2027 when it was read.

GovOS never fills a thin exam with another exam's material. A UPSC page never shows SSC content.""",
     """Authored records are constants in `data.ts` ([[SSC_CGL_EXAM]], [[UPSC_CSE_EXAM]], [[IBPS_PO_EXAM]],
`APPSC_*`, [[TG_TET_INSERVICE_2026_II_EXAM]], [[JEE_MAIN_2026_EXAM]]), collected in [[ALL_EXAMS]]. `Exam.examNature`
marks an `ELIGIBILITY_TEST` or an `ADMISSION_TEST`; the assistant answers their post-shaped questions with
[[noPostsReply]], and a question one of the exam's own FAQs answers with [[faqAnswerFor]]. Machine-read exams are rows in the `exam_registry` table, published by
`tools/exam_builder` and served by `GET /api/exams`. The frontend loads them through `examRegistryService`
(newest load wins; a failed load keeps the last good list). Exam ids are stable (`exam-ssc-cgl-2026`); the
legacy short id is mapped once by `canonicalExamId` / `LEGACY_EXAM_ID_ALIASES`. See {{doc:Adding an exam is adding data, never a branch}}."""),

    # ======================================================================== the screens
    ('The home page', 'home', """
The home page is the welcome screen, top to bottom:

- **A short intro** the first time you open GovOS in a session: the GovOS mark pops in and a ribbon sweeps
  away.
- **The hero:** a big headline, a search box, quick buttons and an animated scene. A student with a
  backpack walks along a road at dawn toward a government building. Four signposts light up as he passes
  them: Discover, Apply, Exam, Result. It is the journey GovOS guides you through.
- **A fanned deck of exam cards**, one per popular exam, each in its commission's colour with a simple line
  drawing of its world (a bank, a railway, a state office). Point at a card and it grows and straightens.
- **"Choose from":** a list of every exam and career field. The page pauses while you scroll through it
  line by line, so you can read each one.
- A colour band, the **eligibility finder**, a short story of how GovOS works, **recommended exams**, a
  **FAQ**, and the footer.""",
     """Rendered by [[ExamFinder]]: [[ClubIntro]] (once per session via sessionStorage, skipped under
reduced motion), [[ClubHero]] with [[ClubSkyline]]. The skyline animation runs on one requestAnimationFrame
clock: [[journeyAt]] maps time `t` (loop `LOOP_S` = 17 s) to walk progress, camera push, road fill and stage,
written to `data-stage` / `data-walking`. It runs only while the hero is on screen. Then come
[[ExamPassRail]] with [[AuthoritySketch]] (CSS flex-grow accordion on hover / focus-within),
[[ClubCategories]] (a pinned sticky stage of `100svh + lines × 34svh`; it honours `data-scroll-rate="0.55"` in
[[installSmoothWheel]] and settles to a line 220 ms after scrolling stops), [[ClubBand]],
[[ExamDiscovery]], [[JourneyStory]], [[ClubFAQ]] and [[ClubFooter]]. See {{doc:Motion and type (presentation only)}}."""),

    ('The top bar', 'topbar', """
The bar along the top is how you move around: **Home**, **Exam Finder**, **My Exams** (the exams you
track or opened last), **Compare Exams**, **Ask GovOS AI**, **My Timeline** (your exams' dates), and the
**Trust Panel** (the owner's tools). Then the bell for alerts and your profile picture.

When you are inside an exam, its name shows as the highlighted button. The bar quietly changes colour
to match whatever is behind it as you scroll.""",
     """[[Header]]. There is no router: `main.tsx` keeps one `activeTab` string (`GovOSTab`). Every button,
alert and assistant action goes through one function, `navigate(tab, section?, examId?)` inside [[App]].
`PRACTICE` / `RESOURCES` / `PLANNER` are translated into the exam page at sections 9 / 8 / 7. The bar
samples the colour under its bottom edge (about 10 times a second while scrolling) into `--bar-rgb` and
`data-surface`, and condenses once scrolled (`data-scrolled`). See Figure 3 in chapter 5."""),

    ('The exam page', 'exampage', """
Click an exam and you get its own page. Everything about that exam lives here and nowhere else.

On the left (or along the top, on a phone) is the list of the exam's **13 parts**, in the order a
candidate meets them, plus four **reference** parts (FAQs, Corrigenda, Official Links, Cut-off History).
The top of the page shows the exam's name, its commission, a "next on record" date, and its stages as a
line of stops. Each part has "previous" and "next" buttons at the bottom, like turning pages in a book.

Switching to another exam starts that exam's page fresh, so nothing from the previous exam leaks in:
not a ticked box, not a half-finished test, not a chat message.""",
     """[[ExamDetailView]], keyed by `exam.id` in `main.tsx`, so a switch remounts it. The structure is two
arrays, [[EXAM_SECTIONS]] and [[REFERENCE_SECTIONS]]. A part's `num` is its stable deep-link id, not its
position (Mock Tests is 17). Notifications, assistant actions and `initialSection` target these numbers.
Section changes replay `section-enter` through [[useReplayOnChange]] without remounting. Exam-scoped state
(open panels, checklist ticks under `examChecklistKey`, the Ask AI thread) resets during render on a switch.
See {{doc:The exam is the unit of navigation}}."""),

    ('Part 1 — Overview', 'p1', """
The summary of the exam: what it is, who conducts it, how many vacancies, the most important date, quick
facts (posts, level, selection stages, official website) and the latest updates. Each fact has its
Evidence button. The "About" paragraph is labelled as GovOS's own summary, not a quote.""",
     """Section 1 of [[ExamDetailView]]. Headline facts cite `Exam.factEvidence` (`vacanciesTotal`,
`crucialEligibilityDate`), never `posts[0]`. Post cards list `postName`, department, ministry, a neutral
`pay-tag` for `payLevel` and the pay scale. [[ExamVerifiedBadge]] says "Officially verified" only when every
date and post is VERIFIED, otherwise "N of M facts officially verified". Latest Updates sorts corrigenda and
dates by publication, then upcoming dates by nearness."""),

    ('Part 2 — Dates & Timeline', 'p2', """
Every important date of this exam: notification, last date to apply, fee date, exam dates, admit card,
results. What is still ahead is shown first, with a countdown on the next one ("in 16 days"). Dates
already passed are tucked behind a "show completed" button.

If a date was changed by a later notice, the old one stays visible but **struck through**, with the
reason. It is never counted down to. A date printed without a day ("May/June") is shown as printed and
never counted down to either.""",
     """Reads `exam.dates` against a clock that re-reads itself every minute. A `SUPERSEDED` date is never the
NEXT milestone. `ImportantDate.displayWhen` is shown verbatim (`shownWhen()`), and `dateTimeStr` then holds
the range's last day for ordering only. `isTentative` dates are badged. The cross-exam view is
[[ExamCalendar]] (`relativeWhen`, month chips derived from the events present)."""),

    ('Part 3 — Eligibility & Posts', 'p3', """
Can you apply? Enter your date of birth, category (General, OBC, SC, ST, PwBD…) and qualification, and
GovOS checks you against **every post** of the exam: the age limit with your category's relaxation, the
degree or subject each post needs, and physical standards where they exist.

Each post gets one of three answers: **eligible**, **not eligible** (with the reason), or **not
determined**, when the notice states a rule your profile can't answer. GovOS never guesses a yes or a no.""",
     """[[EligibilityCalculator]] (takes `exam`) over [[evaluateEligibility]] / [[evaluatePostEligibility]].
Age: `maxAge` + relaxation from [[getCategoryAgeRelaxation]] (OBC +3, SC/ST +5, PwBD +10) on the crucial date.
Qualification: [[evaluateQualification]] reads the post's `ruleGroup`, else `exam.globalRuleGroup`; there is
no default degree. Rules: `DEGREE_REQUIRED` (as a level), `BRANCH_SPECIALIZATION`, `PERCENTAGE_MIN`,
`APPEARING_ALLOWED`, `STATED_CONDITION`. Unanswerable means `qualStatus: 'UNKNOWN'`, which the verdict shows
as NOT DETERMINED. The overall result is ELIGIBLE, CONDITIONAL, INELIGIBLE or NOT_EVALUABLE.
`eligibilityHighlights` render as numbered rule cards."""),

    ('Part 4 — Application & Documents', 'p4', """
How to apply, step by step: the portal, the fields, the fee, the documents, the rules that trip people
up. There is a **practice application form**: a safe copy of the real form where you can make mistakes.
It warns you the way the real rules would ("your signature must be in black ink, three times") and quotes
the notice for each warning.

Each exam's form is its own, built from its own notice. UPSC's follows UPSC's four steps; SSC's checks
photo and signature sizes against SSC's published specifications.""",
     """[[ApplicationGuide]]. Preference order: the exam's own `ApplicationSimulatorSpec` rendered by
[[ExamApplicationSimulator]] (traps fire on declarative rules: `VALUE_IN`, `VALUE_IN_ALL`, `DATE_OUTSIDE`, each
quoting its clause and page), then SSC's bespoke [[PracticeApplicationSimulator]] (real image-upload
validation), then an honest "not authored yet". For machine-read exams the spec is built by
`runtime_simulator.build_simulator`. Portal links come from `ApplicationSourcesPanel`, offered only when they
serve this exam (`_serves_exam`). See {{doc:Two exams, one page: nothing SSC-shaped is baked into a section}}."""),

    ('Part 5 — Exam Pattern', 'p5', """
How the exam is built: its stages (Prelims, Mains, Interview, or Tier-I and Tier-II), the papers in each,
how many questions, marks, time, and the penalty for wrong answers. GovOS uses the commission's own words
for each level. Where it worked out a number itself (say, a total), it marks it "(computed)".""",
     """Section 5 renders `exam.stages` and, where present, `Exam.patternTree`: a recursive projection of
`tools/exam_builder/pattern.py`'s `PatternNode`, with `level_label` holding the authority's own word.
[[stageBadge]] shows that label, never the internal `TIER_1`. Derived figures carry
`Fact.derived_from`. See {{doc:The exam pattern is read from the authority's own scheme}}."""),

    ('Part 6 — Syllabus', 'p6', """
What to study, in three views:

- **Post Study Plan:** for exams whose posts need different papers (SSC), the subjects for the post you
  chose.
- **Official Syllabus:** the commission's syllabus, topic by topic, with a tick box per topic to track your
  progress, and how often each topic tends to appear.
- **Tree Map:** the same syllabus as a zoomable map, from exam to subjects to topics. Drag to move, pinch
  or ctrl+scroll to zoom, and full screen for a big view.

If the commission changes the syllabus, an amber banner shows the notice, and a verifier updates the topic.
The topic then carries a small NEW or REV badge.""",
     """Views are chosen by `defaultSyllabusView`. Study paths exist only where [[examHasStudyPaths]];
otherwise the page opens on the official syllabus. `Exam.syllabusTree` (recursive `SyllabusNode` from
`syllabus.py`) is keyed by `syllabusNodeKeys` because UPSC's tree repeats ids. [[SyllabusTreeMap]] reads the
merged `exam.syllabus` (the topic count must equal the list's anchors). Gestures: pointer drag, two-pointer
pinch (linear with span), ctrl/meta+wheel at 1.08 per notch, all through `zoomAbout`. The fit runs only for a
new canvas. The live watch is `GET /api/syllabus/watch` with six states (`syllabusWatchState`); revisions are
merged by [[applySyllabusRevisions]]. See {{doc:The syllabus, also as a map}}."""),

    ('Part 7 — Study Roadmap', 'p7', """
A study plan for the exam: phases, goals you can tick off, and progress. For machine-read exams the
roadmap follows the exam's own stages and papers, with each paper's topics as a checklist. GovOS does not
invent "study 3 hours a day" numbers. Where a plan has no phases yet, it says what is missing.""",
     """[[PreparationPlanner]] for authored roadmap tracks (goals in `govos_roadmap_goals`), [[SyllabusRoadmap]]
for a machine exam's study guidance: stages, each with its official schedule in the authority's words, papers
as cards with topic checklists. There are no durations, because none are published."""),

    ('Part 8 — Resources', 'p8', """
A library of study material: official PDFs (NCERT books, the Constitution), official portals, single
video lessons and popular YouTube channels. GovOS **stores no study material**. Every item is a link to
the publisher's own website.

Coaching channels are listed because students use them, but they are clearly labelled "not official, not
fact-checked". A small badge on each card tells you whether the link opened when it was last checked.
Notices and question papers are not in the library; each goes to the part of the exam page where you would
look for it.""",
     """[[ResourceLibrary]] (also its own top-level tab, with `showSectionNumber={false}`). Only
`STUDY_MATERIAL`, `LECTURE_VIDEO` and `PRACTICE_TOOL` are listed ([[resourceRoleOf]]). Every other role goes to
its section through [[RESOURCE_SECTION]], mirrored by `resource_roles.SECTION_FOR_ROLE` and both pinned to
`resource_role_cases.json`. Link health: `POST /api/resources/health/sync` registers URLs, and a daemon
re-checks anything older than 12 h into `resource_link_health`. Live shelves: SSC's notice board, UPSC What's
New, and channel Atom feeds, cached 6 h in `live_feed_cache`. The search is [[ResourceAIAssistant]] over
[[rankResourcesForQuery]] (rarity-weighted terms). See {{doc:Content policy: link, don't store}}."""),

    ('Part 9 — Practice & PYQs, and Part 17 — Mock Tests', 'p9', """
Practice questions and full tests. For SSC CGL there is a question bank, sectional tests, topic drills
and a **test creator**: type "12 questions on percentages, medium" and it builds exactly that. Tests run
like the real computer-based test: a clock, a question palette, and the exam's real marking (for example
+2 right, −0.5 wrong). Afterwards you get scores, weak topics and worked solutions.

Every question says where it came from. Some are written from official books and documents. Others are
GovOS's own practice questions, labelled that way, and never presented as real past-paper questions.

Each exam has its own practice engine, so a UPSC candidate never gets SSC questions. Where a commission
publishes no papers or answer keys, GovOS says so instead of making answers up.""",
     """[[ExamPracticeRouter]] picks the engine by exact id from [[PRACTICE_ENGINES]]; an exam with no entry
gets [[UnavailablePracticeEngine]], never a fallback. `assertExamMatches()` refuses a wrong exam. SSC uses
[[PracticeEngine]] with a `scope` (PRACTICE, MOCKS or ALL), views `PAPERS_LIST` … `PAST_ANALYTICS`, and a CBT
clock that auto-submits at zero. Each paper's marking comes from `MockPaper.marking`. Custom tests:
[[parseTestRequest]] → [[planPracticeRequest]] → [[generateCustomMockTest]] over [[TOPIC_CATALOG]] (47 topics, 12
generators, 5 curated sets). A topic with no supply is refused, not substituted. Attempts are saved by
`saveMockAttempt` under the exam id and filtered by exam in SQL. Official papers and keys are listed by
`OfficialPaperCatalogue` / `AnswerKeyPanel`. See {{doc:The exam chooses its practice engine}}."""),

    ('Part 14 — Admit Card', 'p14', """
When and where the admit card (hall ticket) comes out. GovOS keeps two things apart that people often
mix up: the **city slip**, which tells you the city of your exam, and the **admit card** itself. It also
separates the date the card is released from the date of the exam.

Some commissions publish a rule ("7 days before the exam") instead of a date, and GovOS shows the rule.
The download always happens on the commission's own login page, which GovOS links to as a portal. It
cannot see your personal login, and says so.""",
     """[[AdmitCardSection]] renders `Exam.admitCardEvents` (from `tools/exam_builder/admit_card.py` via
`compat.admit_card_events()`), one card per document, with `AdmitCardNoticeKind`, release date or rule,
precision, and a portal link. There are four states, including "GovOS has not read this exam's sources". The
sample hall ticket prints field names only. See {{doc:The admit card is read as events, never as one card per exam}}."""),

    ('Part 15 — Exam Day', 'p15', """
A checklist for the day of the exam: what to carry, what not to carry, reporting time and the rules in
the hall. You can tick items off. Ticks are saved per exam, so your UPSC list and SSC list stay separate.""",
     """[[ExamDayChecklistSection]]. Ticks are stored under `examChecklistKey(exam)` and re-keyed during
render on an exam switch. `examDayChecklist` is an optional field on `Exam`; until it is authored, generic CBT
content shows."""),

    ('Part 16 — Results & Next Steps', 'p16', """
Two things live here. First, the **official results**: what the commission has actually declared, with a
link to the document. A result that is only *scheduled* is shown as expected, never as declared.

Second, **your own result**: type your marks or upload your scorecard (a PDF or a photo). GovOS reads the
marks, compares them with past cut-offs **for your category**, says which year that cut-off is from, and
shows the next steps for the stages that follow, such as a skill test, documents or a medical exam. The
uploaded file is read in memory and **never stored**.""",
     """[[ResultNextStepsSection]] renders `Exam.resultDeclarations` (`results.py` / `results_merge.py`
lifecycle: ORIGINAL → REVISED → CANCELLED → SUPERSEDED, or CONFLICTED) and the self-assessment. The scorecard
goes to `POST /api/results/parse` ([[parse_result_document]]), protected by the limits in Figure 7, with OCR
optional. Cut-offs come from [[matchCutoffRow]] (exact category or a shared `CATEGORY_WORDINGS` code, else a
named "not available" state). Pathways are built from the record by `resultPathway`; skill tests come from
`ExamStage.skillTest`. See {{doc:Results are read as declarations, not a self-assessment}}."""),

    ('The four reference parts', 'refs', """
- **FAQs:** common questions about this exam, answered from its record.
- **Corrigenda Log:** every official correction (a date moved, vacancies changed), with what changed and
  the notice that changed it.
- **Official Links:** the commission's own pages and notices, plus a live feed of its latest notices
  where one is available.
- **Cut-off History:** the minimum marks of past years, by category, each from the commission's own
  sheet.""",
     """Sections 11, 13, 12 and 10 of [[ExamDetailView]]. Official Links maps `exam.officialLinks` and
`OfficialNoticeBoards` (`/api/resources/live/ssc-notices`, `/api/resources/live/upsc-notices`). Cut-off
column labels come from the exam's own stages. Authority-discovery items are placed by role through
`SectionSourcesPanel` / `OfficialDocumentsPanel`."""),

    ('My Exams, Compare, My Timeline, alerts', 'personal', """
- **My Exams:** a shelf of the exams you track, bookmarked or opened last. Nothing is tracked until you
  choose.
- **Compare Exams:** two exams side by side: eligibility, stages, dates, vacancies.
- **My Timeline:** the dates of all your tracked exams on one line, plus a month-by-month calendar of every
  exam. Each date says how sure GovOS is of it ("Officially verified", "Verification pending" and so on).
- **Alerts (the bell):** reminders like "3 days left to apply". Each reminder shows only during its own
  window. A reminder for a deadline that has passed never appears, and "result declared" appears only
  after a firm date has actually passed.""",
     """`MyExams`, [[ExamCompare]], [[ExamCalendar]], `NotificationCenterModal`. Alerts come from
[[StorageService.generatePersonalizedNotificationsForTrackedExams]] with stable ids (`notif-<examId>-deadline-3d`). The windows:
7d (7 → 3 days before), 3d (3 → 1), 1d (last 24 h), last day. Each is stamped when it fell due, and `isRead`
is preserved by id. [[StorageService.getTrackedExams]] returns `[]` when nothing is tracked. An alert for an exam GovOS does not
hold opens nothing (`notificationDestination`). See {{doc:Nothing stronger than the evidence (the evidence boundary)}}."""),

    ('Ask GovOS AI', 'ask', """
A chat assistant for the exam you're looking at. Ask "what's the last date?", "am I eligible?", "where do
I practise?" or "what's the fee for OBC?". It:

- **fixes typos** and tells you ("I read 'whree' as 'where'");
- answers **"where is…" questions** with a button that takes you there;
- answers **fact questions from the exam's record**, with the source;
- understands **follow-ups** ("and for OBC?", "and for UPSC?").

Each answer wears a badge: official, how-GovOS-works, guidance, or not verified. Only for a question the
record can't answer, and only if the owner has turned Claude on, does it ask Claude. Claude must answer
from that exam's checked facts, and the screen re-checks every fact before calling it verified.""",
     """[[AIAssistant]] → [[answerCandidateQuery]]: [[correctAssistantQuery]] (typo repair over `assistantVocab`),
`ASSISTANT_PARAPHRASES`, `questionFocus`, refinement re-entry, then scored matching over [[PLATFORM_MAP]] and
`FACT_INTENTS` (`bestMatch` / `scoreKeys`; a multi-word key weighs about four words). Context comes from
[[buildChatContext]] (exam, target post, profile, stage from [[deriveCandidateStage]], last 12 turns via
[[conversationService]]). Actions carry `examId` (`actionForExam`). The Claude fallback is
`POST /api/claude/ask` (8 per minute per client), queued as a job; facts are re-derived on the page
(`citationVerification`). See Figure 6 and {{doc:Conversation context — one model, three chats}}."""),

    # ======================================================================== where facts come from
    ('Where the information comes from', 'sources', """
Facts reach GovOS in four ways, and each one is labelled:

- **Hand-written from official documents:** a person read the notice PDF and the exam page and typed the
  facts in, with the page and the exact words. This is SSC CGL and UPSC CSE.
- **Machine-read:** GovOS's reader visits the commission's website, finds the right documents and pulls
  out dates, the pattern, the syllabus, admit-card and result notices. Each fact keeps the words it was
  read from. Nothing is published unless it passes the checks. This is TGPSC.
- **Live feeds:** the server re-reads SSC's notice board, UPSC's "What's New" page and YouTube channel
  feeds every few hours, and checks the library's links twice a day.
- **A verifier's approved change:** the owner can add a resource or revise a syllabus topic from the Trust
  Panel, always citing the notice. Such changes stay marked "verification pending".""",
     """Authored: `data.ts`, built with `officialSource()` / `sscNotice()` / `sscDocument()` / `sscReplaced()`.
Machine-read: `tools/exam_builder` (discover → readers → evidence → completeness → `publish`) into
`exam_registry`, plus `tools/exam_authoring` for data.ts-shaped records. Live:
`_start_background_refresh()` (hourly loop; each feed refreshes past its own interval, `_feed_cached` never
makes a request wait, `_public_link` on every redirect hop). Verifier: `syllabus_revisions` and
`resource_additions`, behind `admin_required`. See Figure 2 and {{doc:Architecture}}."""),

    ('The machine reader, step by step', 'pipeline', """
How GovOS reads an exam from a commission's website by itself:

- **Look around the commission's site first:** its menus, its lists of notifications, old papers and
  results, its application portal. It writes down everything it finds and where it found it. It reads a
  limited number of pages, and if it couldn't read everything it says "search incomplete", not "not
  found".
- **Decide which documents belong to this exam and this year.** A document for another exam or another
  year supplies nothing.
- **Read each part with its own reader:** dates, the pattern, the syllabus, past papers and keys, admit
  cards, results. Every value keeps the exact words and page it came from.
- **Check:** is every value backed by official words? Is anything missing? A value from a non-official
  site can only agree with an official one; it can never become the fact.
- **Publish** only what passed.""",
     """`authority_discovery.py` builds a source graph (`source_graph.py`: `SourceNode`, `SourceEdge`,
`DiscoveryRun`). Limits: 2 links deep, 25 pages, 40 files, 600 nodes. Search states come from
`role_search_state` (FOUND_VERIFIED, FOUND_AMBIGUOUS, FOUND_UNREADABLE, NOT_FOUND_AFTER_DISCOVERY,
SEARCH_INCOMPLETE, NOT_SEARCHED). Gates: `discover.gate()`, `may_supply_pattern` / `may_supply_syllabus` /
`may_supply_admit_card`. Readers: `pattern.py`, `syllabus.py`, `pyq.py`, `admit_card.py`, `results.py`,
`dates.py`. Claims: `claims.reconcile` (official governs, secondary corroborates or conflicts). Ownership:
`source_trust.classify_source`. Failures are `SourceOutcome`, never a `Status`. See
{{doc:Authority source discovery: the authority first, then the exam}}."""),

    ('Trust: what "verified" means', 'trust', """
GovOS uses a few honest labels instead of a simple yes or no:

- **Officially verified:** there is an official link, a page or quote, *and* the quoted words actually
  contain the value.
- **Verification pending:** the source is known, but nobody has checked the value against it yet.
- **Not in its quoted source:** a source is cited, but its words don't contain the value.
- **Superseded:** a later official notice replaced it. It stays visible, struck through.
- **No official source on record:** GovOS has nothing to show for it.

And two that must never be confused: "the commission publishes no such thing" versus "our reader
couldn't find it". The second is GovOS's gap, not a fact about the commission.""",
     """[[factVerification]] (Figure 4) over `verificationLevel` (OFFICIALLY_VERIFIED / UNDER_VERIFICATION /
SUPERSEDED), `evidenceType`, `supersededBy`, URL, page and excerpt. The builder downgrades "verified without a
source". `validate_runtime_exam` refuses unidentified or untyped evidence. `evidenceId` is the hash of (URL,
page, clause, excerpt), stamped by `runtime_evidence.py` and rendered as `data-evidence-id`. Builder states:
FOUND, NEEDS_REVIEW, NOT_PUBLISHED, NOT_EXTRACTED. See {{doc:Nothing stronger than the evidence (the evidence boundary)}}."""),

    # ======================================================================== under the hood
    ('Saving your data', 'saving', """
Everything you do is saved **in your browser first**: exams you track, your profile, ticked topics,
test attempts, bookmarks, alert settings. Then a copy goes to the server in the background. If the
server is off, GovOS still works; if saving in the browser fails, the screen tells you "not kept" rather
than "saved".

The server copy is never allowed to quietly overwrite what you chose in the browser. A test attempt can
be added to, but never erased by a later half-empty save.""",
     """[[storageService]] writes keys such as `govos_tracked_exams`, `govos_candidate_profile`,
`govos_mock_attempts` (capped at 50), `govos_completed_syllabus_topics` and `govos_roadmap_goals` (all listed in
chapter 10), then calls `/api/sqlite/*`. Server rules: `_merge_attempt` (present values only; an id under
another exam returns 409), `_upsert_profile` (only the fields sent), and the browser's tracked list stands.
`readStoredJson` keeps unreadable JSON aside as `<key>__corrupt`. `syncAllToSQLite` is single-flight. See
Figure 5 and {{doc:Persistence: nothing the candidate saved is silently lost}}."""),

    ('Claude, the AI helper — and its limits', 'claude', """
Claude is an AI model installed on the computer running the server. GovOS uses it **like a careful
assistant, never like a source of truth**. It may suggest where to look for documents, sort links into
kinds, pull out values *with their exact quotes*, write practice questions, or answer a question from
facts GovOS has already checked.

It may never publish anything, and nothing becomes true because Claude said it. Every quote it gives is
checked against text GovOS fetched itself, and every practice answer is checked by a second, independent
Claude call. If Claude is off, slow or wrong, the feature falls back to its normal behaviour and says so.
It is **off by default** and uses no API key.""",
     """Every call goes through `ClaudeGateway.run(Operation, payload)` (`tools/claude_cli/gateway.py`). The
payload is schema fields only: no caller supplies a prompt, flag, tool, model or path. `runner.py` is the only
place a process is spawned (array args, no shell, prompt on stdin, narrow env, process-tree kill). Output is
strict-schema validated, reasoning-like keys are stripped, and quotations are re-checked. Slow work runs as a
`claude_jobs` row ([[JobQueue]]), and audit goes to `claude_invocations` (never prompt or output text).
Enabled only with `GOVOS_CLAUDE_ENABLED=1`. Tests use `FakeClaude`. See
{{doc:AI: the installed Claude CLI, and nothing else}} and `CLAUDE_CLI_INTEGRATION.md`."""),

    ('The Trust Panel (owner tools)', 'admin', """
A back room for the person running GovOS. It holds: error reports sent by candidates; **live source
research** (ask Claude to suggest official pages, which the server then checks itself); **authority
discovery** (let the machine reader walk a commission's site); **syllabus revisions**; adding a checked
link to an exam's library; and a list of Claude's background jobs. Every change here cites a notice and
can be undone.""",
     """[[AdminVerificationPanel]]. Writes go through `admin_required` (`tools/claude_cli/routes.py` →
`security.admin_check`): the `GOVOS_CLAUDE_ADMIN_TOKEN` header, or a loopback request with no proxy headers and
no foreign Origin. That is a local guard, not production authentication. Research runs as `DISCOVER_SOURCES`
jobs into `research_runs` / `research_findings`, and discovery as `DISCOVER_AUTHORITY` into
`source_discovery_runs`. The admin token sits in sessionStorage (`adminHeaders()`)."""),

    ('Safety and security', 'security', """
- **No secrets in the code:** there is no API key anywhere; settings live in a private `.env` file.
- **The owner's tools only answer the owner:** from the same computer, or with a secret token.
- **The server only visits public websites**, on every redirect too, so nobody can use it to reach
  private machines.
- **Rate limits:** a single visitor can't flood the link checker, the uploader or the AI (for example, at
  most 10 scorecard uploads a minute).
- **Uploads are boxed in:** size limits, checks before any heavy work, a separate process with a memory
  cap and a time limit, and the file is never stored.
- **No raw HTML** from chats or feeds is ever put into the page, so nothing can sneak code into it.""",
     """`LINK_RATE` in `app.py` (verify 10, recheck 4, sync 20, channels 30, scorecard 10 per minute), and
`LIMITER.allow` for ask (8) and practice (4). `MAX_UPLOAD_BYTES` = 8 MB. `tools/scorecard_decode.py` caps PDF
streams (`MAX_PDF_STREAMS` = 2000, 48 MB each, 96 MB together, failed decodes counted). CORS is limited to
localhost origins. `_load_dotenv` reads only `GOVOS_*` and `PORT`. A frontend check refuses
`dangerouslySetInnerHTML` / `innerHTML` / `insertAdjacentHTML` / `outerHTML` in ui.tsx and main.tsx, and chat text
is rendered by [[renderAssistantText]] as React text. See Figure 7."""),

    ('How it looks and moves', 'look', """
GovOS's look is called "Dawn": a navy sky, a saffron sun, marigold hills, cream paper. It stands for the
morning of a better day. Cards, stickers with outlines, and wavy section edges.

Things move gently: cards rise as they scroll into view, pages wipe in with a saffron ribbon, and the
hero scene plays its journey. Decoration only animates while you can see it. If your computer is set to
**reduce motion**, all of it turns off. Every text colour passes the readability standard against its
background, and every screen works on a phone without sideways scrolling.""",
     """All CSS is in `index.html` (blocks CLUB, DAWN, SUNRISE, THE JOURNEY, THE DECK, CHOOSE FROM PINNED), with
tokens on `:root` and one easing family (`--ease-osmo`, `--ease-energy`, `--ease-elastic`). Reveals:
[[installRevealObserver]]. The wheel lerp is [[installSmoothWheel]] (mouse notches only; touchpads stay
native). Then `PageWipe`, [[SplitWords]], and `prefers-reduced-motion` disables everything. WCAG AA contrast
is checked by compositing the background stack, and the overflow sweep runs at 375 / 768 / 1024 / 1440. See
{{doc:Styling}}."""),

    ('How the code is checked', 'checks', """
GovOS has thousands of automatic checks that run in seconds. They prove things like: an SSC fact never
appears on a UPSC page; a date that was replaced is never counted down to; a coaching link is never
labelled official; a half-empty save never erases a test attempt; an upload over the limits is refused.

Before any change is merged, all of them must pass, along with a type check of the whole frontend and a
full build. The real AI is never called by the tests; a stand-in plays its part.""",
     """`python -m pytest tools test_*.py -q` (2,375 test functions; the root `conftest.py` forbids the real CLI),
`npm run check:frontend` (`tools/frontend_checks/run.mjs`: evidence boundary, exam isolation, future exam,
persistence, results, assistant actions and more), `npx tsc --noEmit` (must stay at 0 errors) and
`npm run build`. Chapter 11 lists every test and check by name."""),

    ('Running it, and how this guide stays current', 'running', """
To run GovOS on a computer: install its parts once, then start the server. It opens on
`http://127.0.0.1:5000`. Developers run a second, live-reloading server while they work.

This guide rebuilds itself. Whenever Claude Code finishes a piece of work in this project, and whenever
the app is built, the guide is regenerated from the current code. If a function changes after its
plain-English explanation was written, the guide marks that explanation "may be out of date" instead of
silently describing old code.""",
     """`npm install`, `pip install -r requirements.txt`, `npm run build`, then `python app.py` (one server, port
5000, `PORT` to override). For development, `npm run dev` (Vite on :3000, proxying `/api` to :5000). This guide:
`tools/docs/build_guide.py` (reference, generated) + `tools/docs/guide_text.py` (this chapter) +
`tools/docs/plain.json` (per-declaration explanations with code fingerprints). It runs via `npm run docs`,
`prebuild` and the Stop hook in `.claude/settings.json`; `--stale` lists explanations whose code changed."""),
]

# ------------------------------------------------------------------------------------------------ diagrams
FIGURE_STEPS = {
    'architecture': """
**In simple words:** the left box is everything in your browser, the right box is the server and its
tools. Read it from the top-left: `main.tsx` draws the app, which uses `ui.tsx` for every screen and
`data.ts` for the exam facts. When you save something, `services.ts` writes it into your browser first
(localStorage), then sends a copy to the server (`app.py`), which keeps it in the database (`govos.db`). The
server also fetches official websites (public ones only) and, when asked, hands slow jobs to Claude
through one gateway. The machine reader (`exam_builder`) writes the exams it reads into the database.""",
    'pipeline': """
**In simple words:** four columns, left to right. **Collect:** read the commission's website, find this
exam's documents, read each part, check the quotes, and let through only what passed. **Store:** the
results land in one of five places (the hand-written register, the machine-read registry, the live-feed
cache, the verifier's changes, Claude's job list). **Serve:** the server hands each one out through its own
address. **Show:** each appears on its own screen.""",
    'navigation': """
**In simple words:** every way of moving (the top bar, an alert, a button in the chat, a card on the home
page) goes through one door, `navigate`. It works out which exam you mean. If GovOS doesn't hold that exam,
it opens nothing and tells you. Otherwise it opens either a general screen or that exam's page at the
right part.""",
    'evidence': """
**In simple words:** a fact goes through six questions, top to bottom, and the first "fail" decides its
label. No source at all? Not in its own quote? Replaced by a newer notice? Not marked official? Missing a
link or page? Only if it survives all of these, and its quoted words really contain the value, is it
"Officially verified".""",
    'persistence': """
**In simple words:** when you do something, it is written into your browser straight away, then a copy
goes to the server, which merges it carefully (it only ever adds what is present). If your browser
refuses to save, the screen tells you. When you open GovOS again it reads your browser first, and the
server's copy is laid over it without replacing your choices.""",
    'ask': """
**In simple words:** your question is spell-fixed, then: is it "where is…"? You get a button to that place.
Is it a known fact? You get the answer with its source. Neither? Only if Claude is switched on does it go to
Claude, as a background job. Claude's answer is checked against official text, and the page checks each fact
again before calling it verified. If Claude is off, you get GovOS's own best reply with a note.""",
    'upload': """
**In simple words:** an uploaded scorecard passes a series of gates before any heavy work: not too many
uploads a minute, not bigger than 8 MB, a real PDF or image, and for a PDF, no hidden bomb of compressed
data. Only then is it read, in a separate boxed process with a memory and time limit. GovOS reads the text,
or uses OCR on a scan, finds your marks, category and roll number, and sends them back for you to confirm.
The file itself is never kept.""",
}

# ------------------------------------------------------------------------------------------------ words
TECH_WORDS = [
    ('React', 'The library the page is built with. The screen is made of small pieces called components that redraw themselves when their data changes.'),
    ('Component', 'One piece of the screen (a card, a button bar, a whole page), written as a function that returns what to draw. Names start with a capital letter, like `ExamDetailView`.'),
    ('State', 'Something a component remembers while it is on screen, such as which tab is open or what was typed. Changing it redraws that piece.'),
    ('Props', 'The inputs a component is given by the piece that draws it, for example the exam to show.'),
    ('Hook', 'A reusable piece of component behaviour; the names start with `use` (`useState`, `useEffect`, `useReplayOnChange`).'),
    ('Effect', 'Work a component does after it is drawn: start a timer, fetch data, listen for scrolling.'),
    ('TypeScript', 'JavaScript with types: every value declares its shape, so mistakes are caught before the app runs (`npx tsc --noEmit`).'),
    ('Type / interface', 'A description of the shape some data must have, for example that an `Exam` has `posts`, `dates` and `stages`.'),
    ('Vite / build', 'The tool that turns the five source files into one ready-to-open `dist/index.html`.'),
    ('Flask', 'The Python library the server is written with. It maps addresses such as `/api/exams` to Python functions.'),
    ('API / route / endpoint', 'An address on the server the page can call to get or send data, such as `GET /api/exams`. GET reads, POST sends.'),
    ('JSON', 'The text format data travels in between the page and the server: `{"examId": "exam-ssc-cgl-2026"}`.'),
    ('SQLite / table', 'The database: one file (`govos.db`) holding tables, which are like spreadsheets with named columns.'),
    ('localStorage', "A small store inside your browser, private to this site, where GovOS saves your choices first."),
    ('fetch', 'How the page calls the server.'),
    ('Provenance', 'Where a value came from: document, link, page, clause and exact words.'),
    ('Hash / fingerprint', 'A short code computed from some content; if one character changes, the code changes. Used to spot changed documents and changed code.'),
    ('Regex', 'A text pattern ("a date like 21-05-2026") used to find things in documents.'),
    ('OCR', 'Optical character recognition: reading text out of a picture or a scanned page. It can misread digits, so GovOS asks you to check them.'),
    ('PDF stream', 'A compressed block inside a PDF file. A malicious file can hide a huge amount of data in small streams, so GovOS counts and caps them.'),
    ('Subprocess', 'A separate program the server starts and controls, used for Claude and for reading uploads, so a failure there cannot take the server down.'),
    ('Job / queue', 'Slow work written down as a row and done in the background, so a web request never waits on it.'),
    ('Rate limit', 'A cap on how many requests one visitor may make per minute.'),
    ('CORS', 'A browser rule about which websites may call this server; GovOS allows only its own local addresses.'),
    ('Schema', 'The exact shape an answer must have; anything else is rejected.'),
    ('Loopback', 'The computer talking to itself (127.0.0.1); the owner tools trust only that, or a secret token.'),
    ('Fixture / fake', 'A made-up stand-in used by tests, such as an invented commission website or a fake Claude.'),
    ('Deterministic', 'Gives the same answer every time for the same input; no AI and no guessing.'),
    ('requestAnimationFrame', "The browser's once-per-screen-refresh callback, used to drive smooth animation."),
    ('Reduced motion', 'An operating-system setting asking apps not to animate; GovOS honours it everywhere.'),
]
