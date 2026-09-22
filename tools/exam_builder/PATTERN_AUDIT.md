# Exam Pattern: what exists, what it assumes, and what four real authorities actually print

Audit only. No production data was changed while writing this.

## 1. The existing contract

`ExamStage` in `src/types.ts` (lines 155-179) is the whole of the frontend's pattern model:

```ts
export interface ExamStage {
  id: string; stageNumber: number; stageName: string;
  tier: 'TIER_1' | 'TIER_2' | 'INTERVIEW';
  durationMinutes: number; totalQuestions: number; totalMarks: number;
  negativeMarking: string; mode: string; qualifyingNature: string;
  sections: { sectionName: string; modules: string[]; questions: number;
              marks: number; durationMinutes: number; negativeMarking: string }[];
  provenance: DataProvenance;
}
```

`Exam.stages: ExamStage[]` is the only place an exam's structure lives. Two levels, fixed:
a stage and its sections. Every measurable is a **required number**, so "the authority did
not print this" has no representation — it has to be written as `0`, which renders as a
zero. One `provenance` covers the whole stage, so a duration read from a table and a
negative-marking rule read from a clause six pages away cite the same thing.

The builder side already has the right model, from the Phase F contract
(`tools/exam_builder/schema.py`, lines 375-486): `PatternLevel` (STAGE / PAPER / SUBJECT /
SECTION / PART / OTHER, structural, no TIER_1), `PatternNode` (recursive, `level_label`
carrying the authority's own word, every measurable a `Fact`), `NegativeMarking`
(`as_printed` plus optional numbers), `QualifyingRule` (`is_qualifying_only`,
`minimum_marks`, `minimum_percent`, `counts_towards_merit`) and `ExamPattern`. **What does
not exist is any producer or projector for it.**

## 2. Existing producers

None. Every `ExamStage` in `data.ts` is hand-authored. The builder has extractors for dates,
posts, eligibility, application stages and fees, and nothing for pattern:

| module | produces |
|---|---|
| `dates.py` | `Milestone` |
| `eligibility.py` | `AgeRule`, `Post`, `QualificationRule`, `VacancyCount` |
| `application.py` | `ApplicationProcess`, `ApplicationStage`, `FeeRule` |
| `stages.py` | *application* procedure stages, not examination stages |
| `compat.py` | `important_dates()`, application simulator spec — **no pattern projection** |
| `tables.py` | generic flattened-table reconstruction, column kinds for posts only |

`stages.py` is a near-miss trap for a reader: it reads "Step 1: register" procedures, not
examination structure. The two must not be confused.

## 3. Existing consumers

27 references to `exam.stages` in `ui.tsx`, none in `services.ts`. The ones that matter:

| place | what it reads | breaks how |
|---|---|---|
| section 05 (line 17923) | the whole stage tree | heading hardcodes **"Complete 2-Tier Exam Pattern & Scheme"**; badge prints `stage.tier` raw, so every exam shows `TIER_1` |
| `ExamPatternPanel` (16085) | stage name, marks, duration, negative marking, section pills | tolerant of empty sections; prints `0 marks` for an unknown total |
| `hasSkillStage` (13661) | stage and section names | regex on names — generic enough |
| cut-off table (18210) | `stages[0]`, `stages[1]`, their sections | positional, and one branch is SSC-only by exam id |
| chat: negative marking (4228) | `st.tier !== 'INTERVIEW'` | filters by the closed union |
| chat: qualifying (4336) | regex over `qualifyingNature` prose | a string search for `33%` |
| practice engines (16434-16553) | `ExamPatternPanel` | shared renderer, already exam-agnostic |
| `PostStudyPath.tier1/tier2` | two fixed keys | SSC-shaped by design, out of scope here |

## 4. Hard-coded assumptions

1. **Exactly two written levels.** Stage → Section. No paper.
2. **A closed stage union.** `TIER_1 | TIER_2 | INTERVIEW`, and it is *displayed*.
3. **Everything is a number.** `durationMinutes: 0` is the only way to say "not published".
4. **Negative marking always exists**, as a required string on both stage and section.
5. **One provenance per stage**, for facts that come from different pages.
6. **No qualifying marks field.** UPSC's 33% and LIC's per-category minima live in prose
   inside `qualifyingNature`, where only a regex can find them.
7. **No language field.** IBPS's and LIC's "Medium of Exam" column has nowhere to go.
8. **No question-type, paper code, or sectional-timing flag.**
9. **No marks-per-question.** SSC prints `60*3 = 180`; the record keeps only 180.
10. **Section 05's heading asserts two tiers** for an exam that may have one or five.
11. **Positional stage reads** (`stages[0]`, `stages[1]`) in the cut-off header.

The shape has already been strained by real data. UPSC's Mains is nine *papers*, and with no
paper level they were authored as `sections`, with `totalQuestions: 0` standing in for "not
applicable" and the two qualifying language papers sitting among the merit papers with no
field to distinguish them.

## 5. Existing provenance

`DataProvenance` is per stage, not per fact: document title, URL, page, clause, published
and verified dates, verifier, taxonomy type, verification level, excerpt. The builder's
`Fact[T]` is per field and carries its own `SourceEvidence` with a verbatim span and status
— strictly richer. `compat.to_legacy_provenance()` already converts one `Fact` into one
`DataProvenance`, which is the bridge this phase needs for pattern.

## 6. Missing universal concepts

Against the brief: paper level, paper code, section-level language, question type, mode per
node, marks per question, negative marking per node with its printed wording, qualifying-only
status, qualifying marks and percentage, **per-category qualifying marks**, sectional timing,
per-candidate-group duration, breaks, totals as stated vs totals derived, and a source-vs-
derived distinction on every number.

Two of those are not hypothetical. SSC prints a second duration **for candidates eligible for
a scribe** ("1 hour and 20 minutes … for the candidates eligible for scribe as per Para-7.1"),
and LIC prints minimum qualifying marks in two columns, `SC/ST/PWBD` and `Others`.

## 7. What can be reused

- **`PatternNode` / `ExamPattern` / `NegativeMarking` / `QualifyingRule`** — the model is
  already universal and already tested (`test_schema.py`). This phase writes the producer.
- **`tables.py`** — `find_header`, `split_cells`, `_row_blocks`, `reconstruct`. It needs new
  `ColumnKind`s (questions, marks, duration, language, qualifying marks, section name) and
  their header cues; the row/cell machinery itself is content-blind and needs no change.
- **`evidence.py`** — verbatim span verification, unchanged.
- **`identity.py`** — content identity, which is what rejects a wrong-exam scheme page.
- **`merge.py`** — MATCH / CONFIRM / SUPERSEDE / REFUSE, and the field-level post merge is
  the template for a field-level pattern merge.
- **`compat.py`** — `to_legacy_provenance`, and the projection pattern established by
  `important_dates()`.

## 8. What the four captured authorities actually print

No Tavily call is needed: all four notices are already in the manifests, and all four carry
their scheme. They are structured four different ways, which is the real requirement.

**SSC CGL — numbered clause heading, flattened table, four levels, prose rules.**
`13.8 Scheme of Tier-I Examination:` then a table `Tier | Subject | Number of Questions |
Maximum Marks | Time allowed`, where the duration cell spans all four rows and contains a
second duration for scribe-eligible candidates. Negative marking is a separate clause
(`13.8.2 There will be negative marking of 0.50 marks for each wrong answer`). Tier-II is
`Tier | Paper | Session | Subject | …` — **Tier → Paper → Session → Section → Subject**, five
levels — with marks printed as `60*3 = 180` and a Data Entry Speed Test whose marks cell is
`-` and whose count is `One Data Entry Task`.

**IBPS PO — lettered headings and two tables.** `D. STRUCTURE OF EXAMINATION`, then
`a. Preliminary Examination (Objective Test)` and `b. Main Examination (Objective and
Descriptive)`, each a table `Sr. No. | Name of Tests | No. of Questions | Maximum Marks |
Medium of Exam | Time allotted for each test (Separately timed)` with a `Total` row. Marks
are **not** equal to questions: English 30/30, Quantitative Aptitude 35/**30**, Reasoning
35/**40**.

**LIC AAO — phase headings, prose rules, per-category qualifying marks.**
`Phase I: Preliminary Examination:` with `There will be NO negative marks` stated in prose,
then a table carrying `Minimum Qualifying Marks` split across two columns, `SC/ST/PWBD` and
`Others`, and a footnote `**English Language test will be of qualifying nature and the marks
thereof will not be counted for ranking`.

**UPSC CSE — prose and a labelled list, no table at all.**
`A. PRELIMINARY EXAMINATION: The Examination shall comprise of two compulsory Papers of 200
marks each`, notes giving the duration (`two hours`), the qualifying rule (`General Studies
Paper-II … qualifying paper with minimum qualifying marks fixed at 33%`) and the languages
(`set both in Hindi and English`). The Mains is a list under two headings that are themselves
the qualifying distinction: `Qualifying Papers: Paper-A … 300 Marks / Paper-B English 300
Marks` and `Papers to be counted for merit: Paper-I Essay 250 Marks …`.

So the extractor must read: a flattened table under a heading, a table with a merged cell
spanning rows, a table with a totals row, a table with per-category sub-columns, a prose
sentence carrying a count and marks, a labelled list, and clause-numbered rules sitting
outside the table they govern. No two of those four exams share a layout, which is the point:
a reader built for any one of them is a reader for none of the others.

## 9. What the reader actually produced

Run against the captured notices only — no Tavily call was needed, because all four carry
their scheme (§8). Every figure below was read from the authority's own document and
verified verbatim in it.

| exam | stages | papers / sections | figures read | what is held for review |
|---|---|---|---|---|
| SSC CGL | 2 (Tier-I, Tier-II) | 4 subjects + 7 papers | 25/50 per Tier-I subject, penalty 0.50, bilingual except English Comprehension, sectional timing, the scribe concession | the two Tier-II rows whose cells are summed across parts |
| UPSC CSE | 3 (Prelims, Mains, Interview) | 9 papers | Paper-A/B 300 qualifying, Papers I–VII 250 for merit, 33% on the qualifying paper, penalty one third of the marks | — |
| IBPS PO | 2 (Prelims, Mains) | 8 tests | every count, mark, medium and sectional time, both totals rows | — |
| LIC AAO | 4 (Phase I, Phase-II, Interview, Medical) | 8 sections | every count, mark and time; **no negative marks** as stated; minimum qualifying marks per category | — |

Four things worth singling out, because the old shape could not hold any of them:

* **Marks are not the question count.** IBPS prints 35 questions for 30 marks in one test
  and 35 for 40 in the next. The marks a question carries is computed where the table
  states both figures and marked as computed; where the notice prints its own arithmetic
  (`60*3 = 180`, `100*2 = 200`), the figure is the authority's and is not marked.
* **A penalty is read or it is absent.** 0.50 flat, one third of the marks, and an explicit
  "there will be NO negative marks" are three different findings, and a notice that says
  nothing produces none of them. Nothing is ever assumed from what other exams do.
* **Qualifying is attached to what the sentence names.** Seven such statements were found
  across the four notices and every one landed on the node it names — a stage whose marks
  are not added to the merit, a section that qualifies only, a paper with a 33% minimum —
  because a coded node is claimed only by a sentence that says its code, and ties are
  broken by which of two same-named nodes the sentence was printed beside.
* **Merged cells are refused.** One table states 30 and 30 questions for two parts and a
  single total of 180 marks across both. Which part is worth what is not established by the
  document, so both rows are NEEDS_REVIEW with their raw text kept, and nothing is shown as
  read.

Nothing here overwrites authored data. The merge matched by the authority's own labels and
produced, across the three exams with records, `UNCHANGED` for every authored stage it could
not establish as the same stage, one `CONFIRMED`, one `CONFLICTED` (IBPS: the record's
combined "Main Examination & English Descriptive" states different totals from the notice,
so all three figures are held), and `ADDED` for the stages the documents set out. The
published `patternTree` sits beside `stages`, so the section shows the authority's structure
and the record's own, and says which is which.
