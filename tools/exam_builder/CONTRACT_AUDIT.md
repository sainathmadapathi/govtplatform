# Contract audit — what the current shapes can and cannot say

Read against `src/types.ts` (the frontend's `Exam` and its 40-odd interfaces),
`tools/exam_builder/contract.py` (the builder's 20 asked-for fields),
`tools/exam_authoring/record.py` (`Field`/`Status`/`Citation`) and
`tools/exam_builder/evidence.py` (`Evidence`/`Extracted`).

No factual exam data appears here. This is about shapes.

## Legend

`mult` multiple values possible · `rev` corrigendum-capable · scopes: `stg` stage ·
`ppr` paper · `sub` subject · `sec` section · `pst` post · `cat` category

---

## identity

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `Exam.id` | string | yes | no | — | no | none | implemented |
| `Exam.code` / `title` | string | yes | no | — | no | none | implemented |
| `authorityName` / `officialDomain` | string | yes | no | — | no | **none** | implemented |
| `categoryTag`, `careerFields`, `minimumQualification` | closed unions | no | `careerFields` yes | — | no | none | implemented, hand-set |

**Problem.** Identity carries no provenance at all, while the builder now resolves the
authority name *with* provenance (`CANONICAL_NAME_VERIFIED` / `INFERRED` / `NAME_UNRESOLVED`,
Phase 1). That distinction has nowhere to land. `careerFields` and `categoryTag` are closed
unions, so a new exam family means editing the type.

## application

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `applicationGuide` | `ApplicationGuideData` | yes | no | — | no | mixed | implemented |
| builder `applicationPortal` | string | yes | no | — | no | `Citation` | implemented |
| builder `howToApply` | string | no | no | — | no | `Citation` | implemented |
| builder `fee` | `{amounts, exemptions, modes}` | no | **yes** | should be `pst`/`cat` | yes | `Evidence` | implemented |

**Problem.** Fee is extracted as one blob though a notice states different amounts per
category and per post. There is no `ApplicationProcess` entity at all — the stages a
candidate actually walks through exist only inside `ApplicationSimulatorSpec`, which is
hand-authored per exam.

## mockApplication

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `ApplicationSimulatorSpec` | modules + fields + traps | no | — | — | no | per-trap clause | **hand-authored, 2 of 5 exams** |

**Problem.** The spec is well-shaped for *rendering* and has no extraction-side counterpart.
It is written by a person from the notice. Nothing connects a trap to an extracted rule.

## dates / timeline

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `ImportantDate.type` | **closed union of 10** | yes | yes | none | via `status` | `DataProvenance` | implemented |
| `ImportantDate.status` | AVAILABLE / NOT_YET_ANNOUNCED / SUPERSEDED | yes | — | — | yes | — | implemented |
| `crucialEligibilityDate` | **single string on `Exam`** | yes | **no** | — | no | none | implemented |

**Problems.** `type` includes `EXAM_TIER1` / `EXAM_TIER2` — one authority's vocabulary in a
universal enum; an exam with four written stages cannot express the third. A date cannot be
scoped to a stage or paper, so "Paper II admit card" has nowhere to go.
`crucialEligibilityDate` is **one** cutoff for the whole exam, which requirement 3D
contradicts directly.

## posts

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `PostRequirement` | flat object | yes | yes | `pst` | no | `DataProvenance` | implemented |
| `classification` | **closed union of 4** | **yes** | no | `pst` | no | — | implemented |
| `payLevel` / `payScale` / `gradePay` | string / number | yes | no | `pst` | no | shared | implemented |
| `vacanciesTotal` | **string on `Exam`** | no | no | — | no | none | implemented |

**Problems.** `classification` is required and closed, so a post whose Group the notice does
not print cannot be represented — this already forced the UPSC emitter to drop posts into a
file header rather than the record. Vacancies are one string for the exam, not per post, per
category or per cycle.

## eligibility — the worst shape in the contract

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `PostRequirement.minAge` / `maxAge` | **plain numbers** | yes | no | `pst` only | no | post's provenance | implemented |
| `EligibilityRule` | `{ruleType, operator, ruleValue, category}` | no | yes | `cat` | no | `DataProvenance` | implemented |
| `getCategoryAgeRelaxation()` | **hard-coded in `services.ts`** | — | — | `cat` | no | **none** | implemented |
| builder `ageLimits` | `{minimum, maximum}` | no | no | none | no | `Evidence` | implemented |

**Problems.**

1. Age is two integers on a post. There is no cutoff date on them — the exam's single
   `crucialEligibilityDate` is used for every post.
2. **Category relaxation is hard-coded** (`OBC +3, SC/ST +5, PwBD +10`) in `services.ts`,
   carrying no provenance. It is applied to every exam regardless of what that authority
   printed. This is the clearest violation of the product's own rule in the codebase.
3. A global age rule and a post-specific one cannot coexist — there is no global slot.
4. Two documents stating different age rules cannot both be held.
5. `EligibilityRule.category` is a closed union of six, so an authority using its own
   category vocabulary cannot be recorded.

## examPattern

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `ExamStage` | flat, one level of `sections[]` | yes | yes | `stg` | no | `DataProvenance` | implemented |
| `ExamStage.tier` | **`TIER_1` / `TIER_2` / `INTERVIEW`** | yes | — | — | — | — | implemented |
| `sections[]` | anonymous inline objects | no | yes | `sec` | no | **none** | implemented |
| `negativeMarking` | **free string** | yes | no | `stg`+`sec` | no | — | implemented |
| `qualifyingNature` | **free string** | yes | no | `stg` | no | — | implemented |
| languages | **absent** | — | — | — | — | — | missing |

**Problems.** Exactly two levels, and the middle level — **paper** — does not exist. An exam
whose stage contains papers, each with its own subjects and sections, must be flattened.
`tier` hard-codes one authority's naming into the universal type. Sections have no id, so
nothing can reference one. Negative marking and qualifying status are prose, not data.
Language is absent, though bilingual papers are near-universal.

## syllabus

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `SyllabusTopic.subject` | **closed union of 19 literals** | yes | — | `sub` | — | — | implemented |
| `SyllabusTopic.tier` | `TIER_1`/`TIER_2`/`BOTH` | yes | — | `stg` | — | — | implemented |
| `subtopics` | **`string[]`** | no | yes | — | no | **none** | implemented |
| `weightagePercentage` / `avgQuestions` / `isHighYield` | numbers / bool | yes | — | — | — | separate provenance | implemented |
| `revision` | inline object | no | — | — | **yes** | notice link | implemented |

**Problems.** The hierarchy is two levels (subject → topic) plus a bag of subtopic strings.
There is no paper level. `subject` being a closed union means adding an exam edits the type —
this is a structural blocker for a universal engine. Subtopics are bare strings and so can
carry neither evidence nor a revision. `tier` again hard-codes one vocabulary.

## pyqs

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `OfficialPaperQuestion` | per **question** | no | yes | `stg`,`ppr`,`sec` | no | `DataProvenance` | implemented |
| `stage` | **`PRELIMS` / `MAINS`** | yes | — | — | — | — | implemented |
| paper entity | **absent** | — | — | — | — | — | **missing** |
| language / medium / booklet set | **absent** | — | — | — | — | — | **missing** |

**Problems.** There is no paper-level object; identity lives on each question as
`examId + paperName + paperYear + stage`. `stage` is a two-value union that cannot express a
third written stage. Language is missing entirely, so two language versions of one paper are
indistinguishable — the exact failure requirement 6 names.

## answerKeys

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `officialAnswerKey` | **`string \| null` per question** | no | no | — | no | question's | implemented |
| key entity | **absent** | — | — | — | — | — | **missing** |

**Problems.** No answer-key entity exists. Provisional / final / revised cannot be
represented, a key has no source of its own, and a key cannot be attached to a paper because
there is no paper to attach it to. `null` correctly means "none published" and is never
guessed — that part is right and must be preserved.

## admitCard

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `AdmitCardDetails` | single object | no | **no** | none | no | **none** | implemented |
| `cityIntimationAvailable` | **boolean** | yes | — | — | — | — | implemented |
| `regionPortals` | array | no | yes | — | — | — | implemented |

**Problems.** One admit card for the whole exam, so a per-stage or per-paper call letter
cannot be held. City intimation is modelled as a boolean every exam answers, rather than as a
kind of notice that may simply not exist. `regionPortals` encodes one authority's regional
structure. The whole object carries no provenance.

## results

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `ResultNextStepStage.status` | closed union incl. `SKILL_TEST`, `DEST`-adjacent | no | yes | `stg` | no | none | implemented |
| `MultiTierResultEntry` | **per-exam branches** | — | — | — | — | — | implemented |

**Problem.** `MultiTierResultEntry` contains `examType: 'SSC_CGL' \| 'UPSC_CSE' \| 'IBPS_PO' \|
'APPSC' \| 'GENERIC'` and then per-exam fields — `tier1Marks`, `destMistakesPercent`,
`upscPrelimsGs1Marks`, `ibpsPrelimsMarks`. This is precisely the exam-specific branching the
universal engine forbids, sitting in the shared type file.

## cutoffs

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `CutoffEntry` | `{year, category, tier1Cutoff, tier2Cutoff?}` | no | yes | `cat` | no | `DataProvenance` | implemented |

**Problem.** Two named numeric slots. A third stage, a per-paper cutoff or a per-post cutoff
cannot be expressed; `category` is a free string here but a closed union elsewhere.

## corrigenda

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `CorrigendumNotice` | `{summary, diffSummary, status}` | no | yes | none | — | `pdfUrl` only | implemented |

**Problem.** `diffSummary` is prose. There is no machine-readable link from a corrigendum to
the field it changed, no previous value and no revised value, so nothing can decide whether a
field is superseded except a person reading the sentence. The date rule the repo already
follows (exam page outranks notice PDF, keep both, mark one `SUPERSEDED`) is applied by hand.

## sources

| field | shape | req | mult | scopes | rev | evidence | status |
|---|---|---|---|---|---|---|---|
| `ExamRecord.sources_read` | **`list[str]`** | yes | yes | — | — | — | implemented |
| `DataProvenance` | per value | yes | — | — | — | — | implemented |
| `SourceDocument` entity | **absent** | — | — | — | — | — | **missing** |

**Problem.** Sources are bare URLs. No document kind, no publication date, no fetch time, no
content hash — although `manifest.py` computes hashes and `discover.py` classifies kinds, so
the information exists and is discarded at the boundary.

---

## Cross-cutting

**Two evidence models, diverging.** `exam_authoring.Citation` (documentTitle, url, page,
clause, excerpt, verifiedDate) and `exam_builder.Evidence` (span, source_url, page, reading,
status, digest). Only the second verifies its span against the source. Requirement 2 asks for
one.

**Four states are not four states everywhere.** The builder has
`FOUND / NEEDS_REVIEW / NOT_PUBLISHED / NOT_EXTRACTED`; the frontend has
`OFFICIALLY_VERIFIED / UNDER_VERIFICATION / SUPERSEDED`. `NOT_PUBLISHED` and `NOT_EXTRACTED`
have no frontend representation, so the distinction the pipeline works hardest to preserve is
lost at the last step. The requested vocabulary renames `FOUND` to `VERIFIED`.

**No field-level status on the frontend at all.** A value is present or absent; there is no
way for the UI to say "the authority publishes none" as distinct from "we could not read it".

**Infrastructure.** `BuildState.PAUSED_INFRASTRUCTURE` exists in `gate.py` and correctly never
becomes `NOT_PUBLISHED`. It has no representation in either data contract.
