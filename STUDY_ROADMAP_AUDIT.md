# Study Roadmap: audit

Audit only. No code changed. Git HEAD: `2644ab9`. Working tree clean at audit time.

## Verdict

**Already implemented — universal, personalized, and with official/guidance separation.** The
only additive, *optional* gap is Step 5's Qwen role: turning the verified syllabus into a
sensible learning *sequence* with rationale, clearly labelled GOVOS_GUIDANCE. The roadmap
tracks, the UI, the personalization signals and the official-fact/guidance split must not be
rebuilt.

## Answers to the audit questions

1. **Already implemented?** Yes.
2. **Files.** Types `PostStudyPath`, `RoadmapPhase`, `RoadmapTrack` and `Exam.roadmapTracks`
   (`types.ts:694/809/823/1069`). Authored `roadmapTracks` for **all five exams** (`data.ts`
   2671 SSC, 17685 UPSC, 19375 IBPS, 19697/19988 APPSC ×2) plus `ALL_POST_STUDY_PATHS` /
   `getPostStudyPath`. UI: `PreparationPlanner` (section 7 "Study Roadmap", `ui.tsx:7898`) and
   `PostStudyPathEngine` (`ui.tsx:8157`); the chat's section-7 deep link (`ui.tsx:3801`).
3. **Commits.** `04ebb2c` (post study engine + roadmap, initial), `16a0da1` (study sources).
4. **Static / dynamic / personalized?** Both authored and personalized. `roadmapTracks` are
   authored GovOS tracks (90-day / 180-day / working-professional), each with phases, weekly
   schedules and suggested daily hours. Personalization reads existing candidate signals —
   `getDailyStudyHours`, `getCompletedModules`, `getCompletedSyllabusTopics`,
   `getRoadmapGoals`, `getMockAttempts` — and the practice analysis derives weak areas and a
   daily-hours split. An exam whose track has no authored phases renders an honest empty panel
   naming the missing piece rather than "0 of 0".
5. **Syllabus data it can consume.** `Exam.syllabus: SyllabusTopic[]` — each topic carries
   `subject`, `topicName`, `weightagePercentage`, `avgQuestions`, `isHighYield`, and official
   provenance. Real counts: UPSC 16, SSC 16, IBPS 3, APPSC ×2 authored. This is verified
   official data and is the correct input for sequencing.
6. **Candidate-progress data.** Completed modules, completed syllabus topics, roadmap goals,
   mock attempts, daily study hours — all already stored per the storage keys above. Reuse
   these; do not duplicate.
7. **Mock/PYQ performance.** `getMockAttempts(examId)` (per-exam) feeds the practice analysis,
   which tallies answered questions by topic and names weak areas. Available to a roadmap.
8. **Genuinely missing.** Only the optional Step-5 capability: a Qwen-assisted *guidance*
   generator that sequences the verified syllabus topics into a learning order with a short
   rationale — strictly labelled GOVOS_GUIDANCE, using only verified topics, never inventing a
   topic or a fact, validated, and falling back to a deterministic order when Qwen is
   unavailable.

## Official facts vs GovOS guidance (already separated, and preserved here)

- **OFFICIAL_FACT** — syllabus topics, weightage, pattern, dates, cut-offs — come from the
  verified register and carry provenance.
- **CANDIDATE STATE** — completed topics, mock attempts — come from the candidate's own storage.
- **GOVOS_GUIDANCE** — the roadmap tracks, the suggested order — are GovOS's, never presented
  as an authority's recommendation.

The new generator sits entirely in the third category: it **reorders verified topics** and
attaches sequencing rationale; it never adds a topic, a mark, a date, or a rule, and its output
is stamped GOVOS_GUIDANCE with a disclaimer. If Qwen invents anything the validator rejects it
and the deterministic order is used. It writes nothing to any exam record.

## Proposed change (minimal, additive)

- Add `verification/roadmap_guidance.py` — a universal generator: a deterministic weight-and-
  high-yield ordering as the baseline and fallback, and an optional Qwen sequencing pass that
  may only reorder the supplied topics (any invented topic → reject → deterministic). No
  exam-specific branch; the structure is whatever the exam's own syllabus is.
- Add `test_roadmap_guidance.py` — the thirteen required cases over real UPSC/SSC/IBPS topics.
- Demonstrate live: real UPSC topics → Qwen-sequenced guidance (labelled), and isolation (a
  UPSC guidance contains no SSC topic).
- **No change** to `RoadmapTrack`, the authored `roadmapTracks`, section 7, or personalization.

Nothing is published or overwritten; no production record or UI is touched.
