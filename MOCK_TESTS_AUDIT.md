# Mock Tests: audit

Audit only. No code changed. Git HEAD: `bae7003`. Working tree clean at audit time.

## Verdict

**Already implemented and complete — missing only Qwen verification of official-PYQ questions.**
The routing, the per-exam engines, the scoring from verified pattern, the attempt storage, the
question-type distinction and the deterministic generator all exist. Generation is **deterministic
and uses no LLM**, and per the repo's standing rule it must stay that way. The only additive gap —
this phase's Qwen role, kept narrow — is verifying that a question presented as an official past
question truly belongs to its exact exam/cycle/paper and is supported by its source evidence.
**Do not rebuild the engine and do not wire the generator to a model.**

## Answers to the audit questions

1. **Already implemented?** Yes.
2. **Files.** `ui.tsx` — `ExamPracticeRouter`, `PRACTICE_ENGINES`, `PracticeEngine` (SSC),
   `UPSCPracticeEngine`, `IBPSPracticeEngine`, `APPSCGroup1/2PracticeEngine`,
   `UnavailablePracticeEngine`, `assertExamMatches`, the CBT clock/scoring/palette, the
   deterministic AI test creator (`generateCustomMockTest`, `parseTestRequest`,
   `planPracticeRequest`). `types.ts` — `PracticeQuestion` (`questionType`),
   `OfficialPaperQuestion`. `data.ts` — the SSC authored bank (35 templates + generators),
   `UPSC_OFFICIAL_QUESTIONS`, `officialQuestionsForExam`, `PRACTICE_BANK_EXAM_ID`. `app.py` —
   `mock_attempts` (`details_json`), `/api/sqlite/mock-attempts`, `sync-all`, the legacy-id
   migration. `services.ts` — `getMockAttempts(examId)`.
3. **Commits.** `04ebb2c`, `1c3ee1d` (one engine per exam), `3cd0f1f` (route by exam id +
   scope history), `6929fec` (UPSC engine), `299a0de` (legacy-id attempt migration),
   `0a97488` (real CSE 2026 Essay paper), `67daada`, `b473776`, `e34ea7c`.
4. **Exams with mock support.** SSC CGL (full authored bank + generators + PYQ shift papers),
   UPSC CSE (previous-year papers + the real Essay paper as attemptable questions), IBPS /
   APPSC ×2 (their own engines with honest empty states where the authority publishes no
   items), LIC (no engine → `UnavailablePracticeEngine`).
5. **Question sources.** `questionType`: **OFFICIAL_PYQ**, **GOVOS_CREATED**, **AI_GENERATED**,
   **CUSTOM_AI_GENERATED** (the "AI" ones are the deterministic generators, not a model), and
   `OfficialPaperQuestion` for real papers. The distinction is enforced: authored/generated
   items render as "GovOS practice question", never as official. The real OFFICIAL_PYQ data is
   the 8 UPSC CSE 2026 Essay topics, OCR-read, `UNDER_VERIFICATION`, `officialAnswerKey: null`
   (never guessed).
6. **Attempt storage.** `mock_attempts` with `details_json` holding `userAnswers` + the whole
   `paperData`; `getMockAttempts(examId)` and `GET …?exam_id=` filter per exam; a missing
   `exam_id` is a 400; legacy short ids were migrated once to the canonical `exam-ssc-cgl-2026`.
   No second attempt DB is needed.
7. **Scoring.** SSC Tier-1 is +2 / −0.5; every stage's `negativeMarking`, `totalQuestions`,
   `totalMarks`, `durationMinutes`, `mode` are read from `exam.stages`, not hard-coded across
   exams. A descriptive paper (the Essay) is not machine-scored — the record says so, and no
   score is invented.
8. **Negative marking.** Per-stage from the record (`stage.negativeMarking`), never one universal
   value; a descriptive paper carries none.
9. **Identity enforcement.** `ExamPracticeRouter` keys engines by exam id and remounts on switch
   (`key={exam.id}`); `assertExamMatches` refuses the wrong exam; `officialQuestionsForExam(id)`
   filters on the exact id; `OfficialPaperQuestion.examId` is stored, never inferred. There is no
   fallback to SSC.
10. **Does it generate questions with an LLM?** **No.** The generator is deterministic (procedural
    generators + curated sets); "No model call anywhere." This must be preserved.
11. **Genuinely missing.** Only Qwen semantic verification of an **official-PYQ** question — "does
    this evidence establish that this question belongs to the CSE 2026 Essay paper?" — useful
    precisely because those items were OCR-read and could be misread, and because it guards
    against a cross-exam or generated question ever being labelled official.

## Proposed change (minimal, additive)

- Add `claim_from_question(...)` to `verification/adapters.py` — a generic OfficialPaperQuestion →
  `Claim` adapter (no exam-specific branch): identity/cycle/paper from the question's own fields
  (wrong exam/cycle/paper rejected before Qwen), evidence from the question's provenance, and the
  question text as the value the model checks against the source.
- Add `test_mock_verification.py` — the sixteen required cases over the real UPSC Essay PYQ and the
  question-type/identity invariants. Routing, scoring and attempt storage are pre-existing TS/app
  behaviour and are asserted at the data-invariant level, not re-implemented.
- Demonstrate live: a real UPSC Essay question verified through Qwen, and isolation.
- **No change** to the engines, the generator, `OfficialPaperQuestion`, the authored questions,
  `mock_attempts`, or the UI. **No LLM generation is added.**

Nothing is published or overwritten; no production record, attempt store, or UI is touched.
