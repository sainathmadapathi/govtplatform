# Cut-off History: audit

Audit only. No code changed. Git HEAD: `62741ae`. Working tree clean at audit time.

## Verdict

**C — already implemented, but with no Qwen semantic verification.** Cut-off History has a
data model, a universal UI, and real authored data with provenance for every exam that
publishes one. The only genuinely missing piece — and the one this phase asks for — is
routing cut-off facts through the existing deterministic + Qwen verifier. **The model and UI
must not be rebuilt.**

## What already exists, and where

- **Frontend model** — `CutoffEntry` (`src/types.ts:318`): `year, category, tier1Cutoff,
  tier2Cutoff?, postsEligible?, provenance`. `Exam.cutoffsHistory: CutoffEntry[]`
  (`types.ts:1065`).
- **Builder model** — `CutoffMark` (`schema.py`): `scope` (open, so stage/post/paper/region/
  category are all expressible), `marks: Fact[float]`, `basis` ("out of 200", "aggregate").
  `ResultDeclaration.cutoffs: list[CutoffMark]` and `compat.py` already projects cutoffs.
- **UI** — Section 10 "Cutoffs" renders `exam.cutoffsHistory` by category, year and post; the
  chat answers cut-off questions from the same array with category/year and the exam's own
  stage labels (`ui.tsx` ~2616, ~4356, and the section-10 deep-link at 3796). It reads the
  qualifying-vs-ranked distinction from the record, and says "No published cut-off in
  register" where there is none — an explicit empty state, not a fallback.
- **No dedicated `cutoff.py` reader/merge module.** There is none, and none is needed: the
  values are authored from each authority's own sheet with provenance, exactly like the other
  reference sections. `CutoffMark` already covers the builder-side shape.

## Real authored data and its evidence (per exam)

| exam | entries | cycles | provenance |
|---|---|---|---|
| SSC CGL 2026 | 16 | 2022, 2023, 2024 | authored, cited to SSC sheets |
| UPSC CSE 2026 | 24 | 2021, 2022, 2023, 2025 | **verbatim excerpt + official PDF URL per year** |
| IBPS PO 2026 | 2 | 2023, 2024 | authored |
| APPSC Group 1 | 1 | 2024 | authored |
| APPSC Group 2 | 1 | 2024 | authored |

UPSC's are the strongest: each year's entries share a `DataProvenance` built by the `upscCutoff`
helper, carrying the official sheet URL, the publication date, and a **verbatim excerpt** — e.g.
2025: *"CS(Prelim)\* 92.66 (General) 89.34 (EWS) 92.00 (OBC) 84.00 (SC) 82.66 (ST) … CS(Main)#
739 706 717 700 694 … CS(Final) 963 926 931 905 902. \*Cut off marks on the basis of GS Paper-I
only. GS Paper-II is of qualifying nature with 33% marks."* This is real captured evidence a
Qwen check can be run against.

**Cut-offs are already cycle-specific.** Every entry carries its own `year`, and the register
holds past cycles (2021–2025) distinctly; nothing overwrites the current cycle. There is **no
2026 cut-off for any exam** — none has been published yet — which is correct, not a gap.

## Identity, cycle, isolation

The identity engine (`identity.py`) is exam- and cycle-aware and is what the verification layer
already uses. A cut-off claim can therefore be rejected deterministically for the wrong exam or
the wrong cycle before Qwen is consulted, exactly as result claims are. Category/stage/post
*scope* correctness (e.g. is 92.66 the General prelim mark or the SC one?) is inherently
semantic — the value alone appears in several rows — which is precisely where Qwen is useful
(this phase's §6).

## Missing capability

Only one: **no cut-off fact is currently routed through the deterministic + Qwen verifier.**
The Results phase gained a `claim_from_result` adapter and result-verification tests; Cut-off
History has the analogous gap.

## Proposed change (minimal, additive)

- Add `claim_from_cutoff(...)` to `verification/adapters.py` — a generic cut-off-row → `Claim`
  adapter (no exam-specific branch), building the claim's value from the entry, its evidence
  from the entry's own provenance excerpt, and its identity/cycle from the exam record.
- Add `test_cutoff_verification.py` — the 13 required cases over the real UPSC 2025 evidence.
- Demonstrate one real cut-off fact live through Qwen.
- **No change** to `CutoffEntry`, `CutoffMark`, section 10, or any authored `cutoffsHistory`.

Nothing is published or overwritten; no production record is touched.
