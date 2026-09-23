# Exam Day: audit

Audit only. No code changed. Git HEAD: `10f1ea6`. Working tree clean at audit time.

## Verdict

**Partially implemented.** The section, the type and the UI exist, but there is **no per-exam
authored exam-day data and no provenance** — section 15 shows generic CBT content for every
exam. The additive, safe piece this phase asks for is the **Qwen-verification path for exam-day
instructions**: a way to check a candidate instruction against its exact exam/cycle's official
evidence before it could ever be published. Authoring per-exam `examDayChecklist` data with
provenance is a separate, larger data task and is **not** done here (it would touch production
records and the UI); this phase adds the verification capability and demonstrates it on real
captured evidence.

## Answers to the audit questions

1. **Already implemented?** Partially — type + UI section, no sourced per-exam data.
2. **Files.** `types.ts` — `ExamDayChecklistItem` (`category`, `title`, `description`,
   `isMandatory`) and `Exam.examDayChecklist?`. `ui.tsx` — `ExamDayChecklistSection`
   (section 15, `CheckSquare`). The admit-card reader (`admit_card.py`) already reads real
   exam-day *documents required* clauses (`_DOCUMENT_CUES`) from the same notices.
3. **Commits.** The base platform (`04ebb2c`) added the section and type; no dedicated exam-day
   commit since.
4. **Exams with exam-day info.** None have authored `examDayChecklist` — the section renders
   generic CBT content for all. (CLAUDE.md, Known issues: "the generic CBT content shows for
   every exam.")
5. **Instruction categories.** The type supports DOCUMENTS / TIMING / ITEMS_ALLOWED /
   ITEMS_PROHIBITED / CENTRE_INSTRUCTIONS. It carries no provenance field.
6. **Provenance.** **None** on `ExamDayChecklistItem` — unlike every other sourced section.
   This is the gap that makes the current content generic rather than sourced.
7. **Identity enforcement.** None at the exam-day layer today (the content is component-local,
   not per-exam). The engine's `identity.py` (exam + cycle) is what a verified exam-day
   instruction *would* be gated by — which is what this phase adds.
8. **Genuinely missing.** (a) a verification path so an exam-day instruction is checked against
   its exact exam/cycle's official evidence (added here); (b) authored per-exam `examDayChecklist`
   data with provenance (a separate data task, not done here — the generic content stays, and the
   verification layer is what would gate any authored instruction).

## Real exam-day evidence available (captured, not fabricated)

LIC's AAO notification carries explicit, real exam-day instructions:

- *"Candidates reporting late i.e. after the reporting time specified on the call letter for
  examination will not be permitted to take the examination."* (TIMING)
- *"Photo Identity proof (as specified) in original bearing the same name as it appears on the
  call letter …"* (IDENTITY / DOCUMENTS)
- *"Valid Call letter for the respective date and session of Examination with a photograph
  affixed on it."* (DOCUMENTS)

SSC's admit-card notices carry sitting/city/scribe instructions. These are real, cycle-specific
clauses a Qwen check can be run against. **No instruction is assumed common across exams** — a
rule like "calculator prohibited" is not stated for any exam unless that exam's own evidence
supports it.

## Proposed change (minimal, additive)

- Add `claim_from_exam_day(...)` to `verification/adapters.py` — a generic exam-day instruction
  → `Claim` adapter (no exam-specific branch): the instruction category and text as the claim,
  the official clause as the evidence, and identity/cycle/stage from the exam record, so a
  wrong-exam or wrong-cycle instruction is rejected before Qwen.
- Add `test_examday_verification.py` — the ten required cases over the real LIC exam-day clauses.
- Demonstrate live: a real LIC instruction verified through Qwen, and isolation.
- **No change** to `ExamDayChecklistItem`, section 15, or any record. **No exam-day rule is
  authored or published** — this is the verification gate, demonstrated.

Nothing is published or overwritten; no production record or UI is touched.
