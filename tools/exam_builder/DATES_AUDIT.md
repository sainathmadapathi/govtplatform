# Dates & Timeline — what exists, who makes it, who reads it

Read against `src/types.ts` (`ImportantDate`), `src/data.ts` (five exam records),
`src/ui.tsx` (section 02 and nine other readers), `src/services.ts` (notifications),
`tools/exam_builder/schema.py` (`Milestone`) and `tools/exam_authoring/extract.py`.

## 1. Current contract

```ts
ImportantDate {
  id, label, dateTimeStr, timezone, isTentative
  type: 'NOTIFICATION' | 'APPLICATION_OPEN' | 'APPLICATION_CLOSE' | 'CORRECTION_WINDOW'
      | 'ADMIT_CARD' | 'EXAM_TIER1' | 'EXAM_TIER2' | 'ANSWER_KEY' | 'RESULT' | 'INTERVIEW'
  status: 'AVAILABLE' | 'NOT_YET_ANNOUNCED' | 'SUPERSEDED'
  provenance: DataProvenance            // required
}
```

`Milestone` (schema.py, Phase F) is already the universal side: open `kind`, a `Scope`,
`starts_at`/`ends_at` as `Fact`s, `superseded_by`, four-state `status`.

## 2. Current producers

| producer | what it makes | how |
|---|---|---|
| `src/data.ts` | **15 date entries across 5 exams** | hand-authored, each with provenance |
| `extract.py: dates_from_rows` | `Field` of label/date pairs | one regex over table rows |
| `Milestone` | — | **nothing fills it** |

There is no path from a document to `exam.dates`. That is the gap this phase closes.

## 3. Current consumers

| where | use |
|---|---|
| `ui.tsx:17679` | **section 02** — maps `exam.dates`, sorts, splits on the clock, `SUPERSEDED` shown struck through and never announced as next |
| `ui.tsx:766` | next milestone for the exam header |
| `ui.tsx:2772` | all-exam calendar, flattens `ALL_EXAMS` |
| `ui.tsx:2904` | My Exams timeline per tracked exam |
| `ui.tsx:3673` | `dateOfType(type, exam = SSC_CGL_EXAM)` |
| `ui.tsx:4049,4158,4171,4284` | chat answers about dates, deadlines, admit card |
| `ui.tsx:12962-12964` | admit-card section |
| `services.ts:915` | notification generation, per `type` |
| `services.ts:2387` | chat context |

**Section 02 is already generic.** It renders whatever milestones the record holds, in date
order, with no exam-specific branch. Requirement 9 is therefore mostly a *producer* problem,
not a UI one.

## 4. Hard-coded assumptions

1. **`EXAM_TIER1` / `EXAM_TIER2` in the universal union.** One authority's vocabulary. An
   exam with a third written stage cannot express it, and an exam whose stages are called
   something else is mislabelled.
2. **`ui.tsx:12964`** — `d.type === 'EXAM_TIER1' || d.type === 'EXAM_TIER2'` to find "the
   exam date".
3. **`ui.tsx:12963`** — city intimation found by `label.toLowerCase().includes('city')`.
4. **`dateOfType(type, exam = SSC_CGL_EXAM)`** — defaults to one exam.
5. **`services.ts:915`** — notifications switch on `APPLICATION_OPEN` / `APPLICATION_CLOSE` /
   `ADMIT_CARD` / `RESULT` literals.
6. **`status` has no absence states.** `NOT_PUBLISHED` and `NOT_EXTRACTED` cannot be
   expressed, so "the authority has not announced this" and "we could not read it" both
   collapse into the date being missing.

## 5. Missing universal fields

- **no cycle** — a record holds one year implicitly
- **no range** — `dateTimeStr` is a single instant, so "21.05.2026 to 22.06.2026" is two
  unrelated rows
- **no stage or paper scope** — a paper-specific date has nowhere to go
- **no revision relationship** — `SUPERSEDED` says a date was replaced, not *by what*
- **no postponement or cancellation** — an exam deferred without a new date cannot be shown
- **no alternatives** — an authority offering two dates cannot state both
- **no partial dates** — "in June 2026", where the authority itself is imprecise

## 6. Existing reusable infrastructure

Most of what this phase needs already exists and is not rebuilt:

- `Milestone`, `Scope`, `Fact`, `SourceEvidence`, `Revision` — the contract
- `evidence.Evidence.verify` — verbatim span checking
- `identity.verify` / `field_is_attributable` — is this document, and this span, this exam's
- `stages.procedure_regions` and the `CueSet` pattern — locating a passage by meaning
- `manifest` — replayable captured sources, four already captured
- `compat` — the projection boundary to the frontend shapes
- section 02 itself — already renders milestones generically
