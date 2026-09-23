# Results & Next Steps: what exists, what it assumes, and what four authorities publish

Audit only. No production data was changed while writing this.

## 1. The two things called "result" today

There are two entirely separate result features in GovOS, and only one of them is about a
result an authority *declared*.

**(a) `ResultNextStepsSection` (ui.tsx, ~1,660 lines) is a candidate self-assessment tool.**
The candidate types their own marks and category, or uploads a scorecard parsed by
`POST /api/results/parse`, and the section compares those marks against `cutoffsHistory` and
tells them whether they cleared the bar and what to do next. Its state is
`MultiTierResultEntry` (types.ts), stored per exam in localStorage
(`storageService.getResultEntry(examId)`). This is the candidate's own data — it is not an
official result, and it is right that it lives outside the register. **It is out of scope for
this phase and must not be broken.**

Its one flaw for later note: the section body still branches on `isUPSC / isIBPS / isSSC`
computed from the exam's code/title, and `CandidateResultStatus` is a closed union of
SSC/UPSC/IBPS-shaped statuses. That is exam-specific *UI* logic for the candidate's own
what-next flow, not factual extraction, so §19 of the brief (no exam-specific logic in the
*generic builder*) does not forbid it — but it is why the section cannot represent an
arbitrary authority's progression, and the new engine must not inherit that shape.

**(b) There is no record of an official result declaration anywhere.** No `Exam` field holds
"the authority declared the Prelims result on 15 June 2026, roll list here." The word
"result" in the register appears only in `resultNextSteps?: ResultNextStepStage[]` — a
hand-authored what-next narrative, authored for *no* exam — and in `cutoffsHistory`. The
authority's own act of declaring a result is simply not modelled.

## 2. What the builder side already has

`schema.py` carries a `ResultDeclaration` skeleton from the Phase F contract:

```python
@dataclass
class ResultDeclaration:
    id: str
    label: str = ''            # the authority's own wording
    kind: str = ''
    scope: Scope = ...         # stage/paper/post, never a fixed union
    published_at: Fact[str]
    document_url: Fact[str]
    qualified_count: Fact[int]
    next_step: Fact[str]       # what happens to those who cleared, in the authority's words
    cutoffs: list[CutoffMark]
    status: Status = NOT_EXTRACTED
    evidence: list[SourceEvidence]
    note: str = ''
```

and a `CutoffMark` scoped to whatever the authority published it against. **No producer, no
merge, no projection, and nothing in the frontend can render it.** `Revision` (schema.py)
already models an addressable correction with `previous_value` / `revised_value` and a
`supersedes_source_id`, which is the revision spine this phase reuses.

`SourceOutcome` (added in the admit-card phase) already separates infrastructure failure
(SOURCE_FETCH_FAILURE / NETWORK_UNAVAILABLE / SOURCE_UNREADABLE / BUILD_PAUSED /
IDENTITY_REFUSED) from `Status`, so §15 ("SOURCE_FETCH_FAILURE must never become NO_RESULT")
is already enforceable and needs no new state.

## 3. What can be reused wholesale

- `identity.py` / `may_supply_pattern()` — the exact-exam-and-**cycle** gate. This is what
  keeps SSC CGL **2025**'s many result notices out of the 2026 record (§3, §18).
- `dates.py` `read_dates()` — dates at day and month precision, which a result row needs.
- `pattern.py` reading helpers (`_evidence`, `_slug`) and the verbatim-span rule.
- `admit_card.py`'s shape end to end: it solved the same problem one phase ago — events
  scoped to a stage, a kind vocabulary, a cell-seam splitter for flattened tables, a
  domain-guarded URL classifier, a `describe()` report, and a merge with
  ADDED/CONFIRMED/SUPERSEDED/CONFLICTED. Results parallels it rather than reinventing it.
- `compat.admit_card_events()` — the projection pattern (scope refs → stageLabel, provenance
  via `to_legacy_provenance`, drop-if-wrong-exam).

## 4. What the four authorities actually publish (captured sources, 2026-09-23; no Tavily)

**UPSC CSE 2026 — declared results on the exam's own page.** Two rows in the exam page's
document table, each a real declared result with a document and a date:

| row | document | date |
|---|---|---|
| Written Result | WR-CSP-2026-RollList-Engl-150626.pdf | 15/06/2026 |
| Written Result (with name) | WR-NameList-CSP-2026-Engl-18062026.pdf | 18/06/2026 |

These are the **Preliminary** written result (roll-number list, then name list). Cycle 2026,
stage Preliminary, with document links. The row does not print a qualified count or the next
step, so those stay NOT_EXTRACTED — the declaration is real; the count is simply not on it.

**SSC CGL 2026 — nothing.** SSC's board carries many CGL result notices — "Declaration of
Result of Tier-I for short-listing", "Declaration of Final Result", "Uploading of Marks" —
but every one of them names the **2025** or **2024** cycle. None is for 2026. The identity
gate refuses them, so SSC CGL 2026's declared-result state is **NOT_PUBLISHED**, exactly as
its admit card was.

**IBPS PO 2026 — scheduled, not declared.** The notification's activity schedule lists
"Result of Online examination – Preliminary — September, 2026" and "Declaration of Result-
Main Examination — November, 2026". These are **month-precision expected dates**, not
declarations: no result document, no qualified list, no marks. Honest treatment is a
**SCHEDULED** kind carrying the expected month, never presented as a declared result.

**LIC AAO 2027 — nothing found.** The notification's schedule does not carry a result row in
the captured document; declared-result state is **NOT_PUBLISHED**.

**APPSC ×2 — not read.** Authority ambiguous upstream; not read at all.

## 5. The design that follows

A result is not one shape. UPSC declares a written result as a page row with a PDF; SSC
declares one as a board notice; IBPS announces an expected date in a schedule. So the reader
takes the same two doors the admit-card reader does — a **prose/notice** door and a
**table-row** door — and produces `ResultDeclaration` events, each:

- scoped to the stage (and post/paper where named), never to a fixed Prelims→Mains→Final
  union;
- carrying the authority's own label and a `kind` (RESULT / WRITTEN_RESULT / FINAL_RESULT /
  SHORTLIST / MERIT_LIST / SCORECARD / MARKS / SELECTION / WAITLIST / DV_SHORTLIST /
  INTERVIEW_SHORTLIST / SCHEDULED);
- distinguishing a **declared** result (a document exists, or the notice says a result *is*
  declared) from a **scheduled** one (only a future/expected date);
- with a `qualification` state and a `next_step` **only where the source states them** —
  never inferred, because "qualified for the next stage" is not "selected" (§5);
- with `published_at` for a declaration and `expected_at` for a schedule, kept apart so a
  schedule can never render as a declaration (§9, §17, §20);
- with a document URL offered only where the authority published one on its own host, and a
  portal otherwise — the admit-card URL rule (§20: no fabricated links).

Merge is the admit-card merge specialised: identity is exam · cycle · kind · stage · post,
and ORIGINAL → REVISED → CANCELLED → SUPERSEDED is carried, never overwritten (§13, §16).
Candidate-level rows (roll numbers, names, ranks, marks) are **never fabricated**; where the
authority publishes a list, GovOS links to it rather than transcribing individuals (§12).

## 6. What will be built

`results.py` (readers + gate + report), `results_merge.py` (the four operations + revision
lifecycle), `compat.result_declarations()` (projection), `types.ts`
`ExamResultDeclaration` + `Exam.resultDeclarations?`, a distinct panel in the Results
section that shows *declared* results with their evidence above the self-assessment tool, and
`test_results.py` covering A–AJ. Real replay publishes UPSC's two declared results and IBPS's
two scheduled ones; SSC CGL 2026 and LIC AAO 2027 publish nothing, honestly.

## 7. What the readers actually produced

Run against the captured board, notification and exam page; no Tavily call was made.

| exam | source | declarations | scheduled | publishable | document links |
|---|---|---|---|---|---|
| SSC CGL 2026 | board notices | **0** | 0 | 0 | 0 |
| UPSC CSE 2026 | the exam's own page | **2** (Prelims written result) | 0 | 2 | 2 |
| IBPS PO 2026 | CRP PO/MT-XVI notification | 0 declared | **2** (Prelims, Main) | 2 | 0 |
| LIC AAO 2027 | AAO notification | **0** | 0 | 0 | 0 |
| APPSC ×2 | not read | — | — | — | — |

Defects found by running the readers against the real documents, each now a test:

1. **A declaration date past the window from the kind cue.** "... to shortlist candidates ...
   The result was declared on 09.01.2026" — the date is a clause away from "shortlist". It is
   now found from its own cue ("declared on"), with its evidence span built around the date.
2. **Indian digit grouping truncated the count.** "1,50,000 candidates" read as 50,000.
3. **The next stage used "for appearing in".** "shortlist candidates for appearing in
   Tier-II" was not matched by a pattern that expected the stage right after the verb.
4. **The written result had no stage.** The exam page's rows name no tier, but the page *is*
   "Civil Services (Preliminary) …", so the page's own stage scopes every row on it.
5. **Two documents of one result collided as a conflict.** UPSC's roll-number list (15/06)
   and name list (18/06) are two distinct documents of the Preliminary written result; keyed
   only on exam/cycle/kind/stage the second was mislabelled a conflict. Identity now also
   carries the document's own basename, so both are ADDED while a re-read still CONFIRMs.
6. **A constructed URL is not a link.** The page prints a bare file name; resolving it against
   a guessed `/sites/default/files/` path risks a 404. The publisher takes the page's own
   `href` and emits a document URL only when it is a real on-host link.

## 8. What was published

`exam-upsc-cse-2026` gained **2** result declarations (Preliminary written result: roll list
15 Jun 2026, name list 18 Jun 2026), each with the page's own PDF href and provenance.
`exam-ibps-po-2026` gained **2** scheduled result rows (Preliminary Sep 2026, Main Nov 2026),
marked SCHEDULED so neither renders as a declaration. **SSC CGL 2026 and LIC AAO 2027 gained
nothing** — SSC's board carries only 2024/2025 result notices (refused by the cycle gate) and
LIC's notification carries no result row. The edit is purely additive; the publisher proves
it by stripping exactly what it inserted and reproducing data.ts byte for byte.

### Infrastructure completed vs verified data

- **Infrastructure completed:** the universal `ResultDeclaration` model (kind vocabulary,
  lifecycle, qualification state, scoped to stage/post, declared-vs-expected dates), the
  reader (`results.py`, notice + table-row doors), the merge with the revision lifecycle
  (`results_merge.py`), the projection (`compat.result_declarations`), the frontend type and
  the Results-section panel.
- **Actual verified declared-result data:** UPSC CSE 2026's two Preliminary written-result
  declarations. That is the whole of it.
- **Actual verified scheduled-result data:** IBPS PO 2026's two expected result dates.
- **Data not available / not verified:** every result for SSC CGL 2026 (only prior cycles
  declared), LIC AAO 2027 (none), and both APPSC exams (not read). No candidate-level data
  (roll numbers, names, ranks, marks) was published for any exam.
