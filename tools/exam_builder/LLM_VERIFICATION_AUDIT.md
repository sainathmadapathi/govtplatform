# LLM verification layer: audit of the current fact/evidence/publication path

Audit only. No behaviour was changed while writing this. Git HEAD at audit time: `9cde204`.

## 1. Where Tavily is called, and what it returns

Tavily is called in **one** place: `app.py` → `research_search()` (`_tavily_post('/search', …)`).
It returns web results — `{title, url, content (snippet), score, published_date}` and an
`answer` string. That is **source discovery**, nothing more.

## 2. What happens to a Tavily result

`research_search()` classifies each result's URL by domain (`_classify_trust` → OFFICIAL /
TRUSTED_PUBLIC / UNVERIFIED), drops non-official results under OFFICIAL scope, and stores each
in the `research_findings` table with `review_status = 'PENDING_REVIEW'`. The snippet is kept
as text; **no fact is extracted and nothing is published**. `research_extract()` may add the
page's full text to a finding. `research_finding_status()` lets a human set PENDING_REVIEW /
REVIEWED / PROMOTED / REJECTED.

The field-level layer added last phase (`research_facts`, RESEARCH_VALIDATION_DESIGN.md) turns
a stored finding into typed candidate facts with `status ∈ {pending, validated, conflicting,
rejected, approved}`. It is rule-based, evidence-kept, and **writes nothing to the exam
record** — `approved` only marks a fact eligible for the human promote gate.

## 3. Where source URLs, documents, text and facts live in the *builder*

The universal engine (`tools/exam_builder/`) is a separate, **offline** pipeline that does not
call Tavily at runtime:

- **Source capture / fetch** — `tools/exam_authoring/sources.py` (`fetch`, `load_pdf`,
  `load_html`), with an on-disk cache (`.exam_cache/`).
- **Content identity** — `identity.py` (`verify(text, ExamIdentity) → MATCH / AMBIGUOUS /
  MISMATCH`, cycle-year aware). Gate: `may_supply_pattern()` (reused as
  `may_supply_syllabus` / `may_supply_results`, etc.).
- **Extraction** — `pattern.py`, `syllabus.py`, `pyq.py`, `admit_card.py`, `results.py`. Each
  produces typed values carried as `Fact[T]` with a `SourceEvidence` whose `span` is verified
  **verbatim** against the source (`SourceEvidence.is_verbatim`, `EvidenceStatus.VERIFIED`).
- **Merge / revision** — `*_merge.py` (MATCH / CONFIRM / SUPERSEDE / CONFLICT, revision
  lifecycle).
- **Publication gate** — `Fact.is_publishable` (VERIFIED **and** a verbatim span) and each
  reader's `is_publishable` (VERIFIED, scoped, verbatim). Projection to the record
  (`compat.*`) drops anything not publishable and anything whose `examId` is not this exam.
- **The actual write to the record** is a **deliberate publisher script** that asserts the
  edit is purely additive (strips exactly what it inserted → reproduces the file). There is
  **no runtime path** from a network source to `data.ts`.

## 4. The mandatory question

> "Can a Tavily result currently reach the final candidate-facing record without evidence
> verification?"

**No.** There are two independent barriers, and both are already in place:

1. **The research pipeline never auto-publishes.** A Tavily finding is stored as
   `PENDING_REVIEW`; reaching a candidate requires a human `PROMOTE` and then a second human
   click ("Add to Resource Library"), and even then it appears as a *labelled resource link*,
   never as a verified fact in the exam record. (Proven by `test_research_facts.py`:
   extraction touches neither `review_status` nor `resource_additions`.)
2. **The builder never publishes an unverified fact.** A value with no verbatim evidence span
   is not `is_publishable`; a document that fails `identity.verify` (wrong exam or wrong cycle)
   `may_supply` nothing; and the write itself is an offline, additive, human-run script.

So the flow is already `Tavily → CandidateSource → (human review) …` and
`source → fetch → extract → Fact+Evidence → deterministic gate → deliberate publish`. There is
**no `Tavily → record` edge** to remove.

## 5. Where a fact becomes publishable (the exact points)

- Builder: `schema.Fact.is_publishable` and each reader's `is_publishable`; enforced again at
  projection time in `compat.*` (drops non-publishable and cross-exam rows). The value is only
  *written* by a publisher script that a human runs.
- Research pipeline: a fact/finding becomes candidate-visible only via human `PROMOTE` →
  `resource_additions` (a resource link, not a record fact).

## 6. What this phase adds, and where it sits

A **semantic verification layer** (`tools/exam_builder/verification/`) that inserts a local
Qwen check **between deterministic verification and the publication decision**, for facts that
are routed through it (e.g. web-discovered candidate facts). It is:

- **universal** — no exam-specific branches; every input comes from the claim's own fields;
- **subordinate** — deterministic checks (source, identity, cycle, verbatim span,
  contradiction) run first and are authoritative; the LLM is consulted only when they pass;
- **withholding-only** — the LLM can move a fact to `NEEDS_REVIEW`, never fabricate `VERIFIED`;
  an unavailable/erroring/malformed model yields an **infrastructure** result
  (`LLM_UNAVAILABLE` / `LLM_ERROR` / `LLM_INVALID_RESPONSE`), never `VERIFIED` and never
  `NOT_PUBLISHED`;
- **out of the offline build's critical path** — the completed publishers are not rewired to
  require a running model, so the build and production (which cannot reach `127.0.0.1:8080`)
  behave exactly as before; the verifier is invoked on candidate facts and demonstrated on
  real captured evidence.

Nothing in §1–§5 is replaced. The Evidence model, `Fact`, identity validation, the merge, the
publication gate, the source manifests, Tavily discovery and the existing extractors are all
unchanged.
