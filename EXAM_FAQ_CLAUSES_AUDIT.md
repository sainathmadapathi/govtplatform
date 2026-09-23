# FAQs & Official Clauses: audit

Audit only. No code changed. Git HEAD: `a4fe183`. Working tree clean at audit time.

## Verdict

**Already implemented and complete — missing only Qwen verification.** Every FAQ is exam-scoped,
carries the official clause it comes from, and carries provenance (an official URL + a verbatim
excerpt). The additive gap — this phase's Qwen role — is verifying that a FAQ's answer is actually
supported by its cited clause before it could be treated as VERIFIED. **Do not rebuild the model,
data, or UI.**

## What already exists / what is missing

- **Model** — `FAQItem` (`types.ts`): `id`, `question`, `answer`, **`officialClause`** (the clause
  it comes from), **`provenance: DataProvenance`** (document title, official URL, verbatim
  `excerptText`, `verificationLevel`). `Exam.faqs: FAQItem[]`.
- **Data** — FAQs authored per exam with clause + provenance for **all five** exams: SSC 6, UPSC 8,
  IBPS 1, APPSC Group-1 1, APPSC Group-2 1. Real, verbatim clauses — e.g. the UPSC age FAQ cites
  *"A candidate must have attained the age of 21 years and must not have attained the age of 32
  years on the 1st of August, 2026 …"* (notice p.14), and the fee FAQ cites *"required to pay fee
  of Rs. 100/- … a further fee of Rs. 200/- …"* (p.3).
- **UI** — section 11 FAQs, each FAQ rendered with its `officialClause` and a Sourced-Clause
  provenance button; the chat's section-11 deep link.
- **Missing** — no semantic verification that a FAQ's *answer* is supported by its *clause*. That
  is the additive step every other section received.

## Answers to the audit questions

- **Universal?** Yes — `exam.faqs` per exam; no SSC-only schema; the same `FAQItem` shape serves
  every exam.
- **Exam-scoped?** Yes — FAQs live on each exam's own array.
- **Official clauses source-backed?** Yes — `officialClause` names the clause; `provenance` carries
  the official URL and a verbatim excerpt.
- **Provenance preserved?** Yes, on every FAQ.
- **Verified vs unverified distinguishable?** Yes — `provenance.verificationLevel`
  (OFFICIALLY_VERIFIED / UNDER_VERIFICATION / SUPERSEDED).
- **Generic/hard-coded facts across unrelated exams?** No — each exam's FAQs are its own, cited to
  its own notice.
- **Missing data treated as published?** No — the thin exams (IBPS/APPSC) carry only their own real
  FAQ, not a generic set.
- **Smallest additive change** — a Qwen FAQ verifier adapter + tests + a live demo. No schema, data,
  or UI change.

## Real evidence available (captured, verbatim, not fabricated)

UPSC's notice provides verbatim clauses for the age band (p.14), the fee (p.3), the scheme (p.25),
the syllabus (p.33), how to apply (p.1), the admit card (p.3) and the vacancy statement (p.2) —
each already the `excerptText` of a FAQ's provenance. SSC's, IBPS's and APPSC's FAQs likewise cite
their own clauses. **No fact is assumed common across exams** — a FAQ exists only where that exam's
own clause supports it.

## Proposed change (minimal, additive)

- Add `claim_from_faq(...)` to `verification/adapters.py` — a generic FAQ → `Claim` adapter (no
  exam-specific branch): the FAQ answer as the value, the clause's provenance excerpt as the
  evidence, identity/cycle from the exam record, so a wrong-exam or wrong-cycle FAQ is rejected
  before Qwen.
- Add `test_faq_verification.py` — the sixteen required cases over the real UPSC age/fee FAQs.
- Demonstrate live: a real UPSC FAQ verified through Qwen, and isolation.
- **No change** to `FAQItem`, section 11, or any authored `faqs`.

Nothing is published or overwritten; no production record or UI is touched.
