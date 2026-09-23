# Corrigenda & Revisions: audit

Audit only. No code changed. Git HEAD: `bb0e584`. Working tree clean at audit time.

## Verdict

**Already implemented and complete as a feature — missing only Qwen semantic verification.**
The model preserves old and new values, the revision and effective dates, the exact evidence
and source, and the exam/cycle identity; the UI shows what changed and which document caused
it; superseded values stay visible struck through. The only additive gap — and what this
phase asks for — is routing a revision's *new value* through the deterministic + Qwen verifier.
**Do not rebuild the model or the UI.**

## Answers to the audit questions

1. **Already implemented?** Yes.
2. **Files.** Frontend model `CorrigendumNotice` (`types.ts:21`) and `Exam.corrigendums`
   (`types.ts:1064`); `VerificationLevel` includes `SUPERSEDED`; `ImportantDate`/milestones
   carry a `SUPERSEDED` status; result declarations carry `lifecycle: ORIGINAL | REVISED |
   CANCELLED | SUPERSEDED`; admit-card events carry `supersedes`. Builder model `Revision`
   (`schema.py`) — an addressable change with `field_path`, `previous_value`, `revised_value`,
   `published_at`, `effective_from`, `evidence`, `supersedes_source_id`. Per-domain
   SUPERSEDE/revision semantics in `merge.py`, `results_merge.py`, `admit_card_merge.py`,
   `pattern_merge.py`, `syllabus_merge.py`, `pyq_merge.py`, `dates.py`. UI: section 13
   Corrigenda log, the corrigendum bar in `ExamDetailView`, struck-through superseded dates,
   the chat's section-13 deep link (`ui.tsx:3826`), and the Trust Panel's Corrigendum &
   Conflict Queue (`ui.tsx:5177`).
3. **Commits.** The base authored records; `2aff782` (syllabus revisions on the tree map); the
   Admit Card and Results phases added the `supersedes`/`lifecycle` revision semantics.
4. **Exams with revision data.**
   - **UPSC CSE 2026 — 2 corrigenda:** `corr-upsc-02` (last date 24 Feb → **27 Feb 2026**,
     the Commission extended the window after the notice) and `corr-upsc-01` (vacancies approx.
     933 → **1,016**).
   - **SSC CGL 2026 — 2 corrigenda:** `corr-cgl-01` (PwBD scribe clarification), `corr-cgl-02`
     (application-window & fee extension).
   - **IBPS PO 2026, APPSC Group 1/2 — 0** (`corrigendums: []`; NOT_PUBLISHED, correct).
5. **Official sources.** UPSC's examination page (the 27 Feb last date) and its 18.06.2026
   result press note (1,016 vacancies); SSC's own corrigendum notices. Real, captured.
6. **Old and new values preserved?** Yes — `diffSummary` ("24-02-2026 → 27-02-2026",
   "approx. 933 → 1,016") on the frontend, and `previous_value`/`revised_value` addressably in
   the builder `Revision`.
7. **Revision/effective date preserved?** Yes — `publishedDate` + `effectiveDate`
   (`published_at` + `effective_from` in the builder).
8. **Exact evidence preserved?** Yes — `pdfUrl` / provenance on the notice; `evidence` spans
   on the builder `Revision`. The superseded original is kept, never deleted (a `SUPERSEDED`
   date renders struck through beside the corrigendum that replaced it).
9. **Correction vs withdrawal/postponement/rescheduling distinguished?** Partially. The
   *result* and *admit-card* lifecycles distinguish REVISED / CANCELLED / SUPERSEDED
   explicitly; a `CorrigendumNotice` carries the distinction in prose (title/summary) rather
   than a closed `type` enum. Per this phase's rule ("only classify when evidence supports
   it"), that is acceptable, and Qwen can read the relationship semantically where useful.
10. **Genuinely missing.** Only Qwen semantic verification of a revision fact — "does this
    document actually establish the claimed new value for this exam and cycle?" — exactly the
    additive step Results and Cut-off received.

## Proposed change (minimal, additive)

- Add `claim_from_revision(...)` to `verification/adapters.py` — a generic revision → `Claim`
  adapter (no exam-specific branch): the claim's value is the revision's **new** value, its
  evidence is the revision source's own span, its identity/cycle come from the exam record. So
  a revision runs through the authoritative deterministic gate (wrong exam/cycle/field rejected
  first) and then the local Qwen check on whether the evidence supports the new value.
- Add `test_corrigenda_verification.py` — the ten required cases over the real UPSC
  `corr-upsc-02` (24 → 27 February) evidence.
- Demonstrate the real revision live through Qwen.
- **No change** to `CorrigendumNotice`, `Revision`, section 13, the corrigendum bar, or any
  authored `corrigendums`.

Nothing is published or overwritten; no production record is touched.
