# Application data — what is sourced, what is hand-written, and where the boundary runs

Read against `src/types.ts` (`ApplicationSimulatorSpec` and friends), `src/data.ts`
(`UPSC_APPLICATION_SIMULATOR`), `src/ui.tsx` (`ExamApplicationSimulator`,
`PracticeApplicationSimulator`), `tools/exam_authoring/extract.py`
(`application_portal`, `how_to_apply`), `tools/exam_builder/contract.py` and
`tools/exam_builder/schema.py`.

No factual exam content is reproduced here.

## What exists today

| piece | where | how it is produced | sourced? |
|---|---|---|---|
| `ApplicationSimulatorSpec` | `types.ts:547` | hand-written | shape only |
| one exam's simulator | `data.ts:2540` | **read by a person from the notice** | yes — 19 `noticeReference`s |
| a second exam's simulator | `ui.tsx:10887` | **hard-coded React component** | partly |
| `ExamApplicationSimulator` | `ui.tsx:12057` | renders whatever spec it is handed | n/a |
| `applicationGuide.officialPortal` | `data.ts` | hand-written string | no |
| `otrSteps`, `photoRules`, `signatureRules`, `certificateRules`, `rejectionPitfalls` | `types.ts:563` | hand-written | no |
| builder `applicationPortal` | `extract.py:374` | one regex | yes, thinly |
| builder `howToApply` | `extract.py:385` | one regex for a heading, 300–6000 chars | yes, as a blob |
| `ApplicationProcess` | `schema.py` | **Phase F shapes, nothing fills them** | — |

## Hard-coded vs sourced, precisely

**Sourced, and genuinely so.** The authored simulator's traps each quote a clause and name
where it sits (`officialClause` + `noticeReference`), and the record was corrected twice when
the source was re-read. That is the standard the extractor has to meet, not replace.

**Sourced but shapeless.** `howToApply` captures a heading and the next few thousand
characters as one string. Nothing inside it is addressable: the steps, the fields and the
uploads are all in there and none can be pointed at, revised or rendered separately. It is
evidence without structure.

**Hard-coded, and invisible as such.** `ApplicationGuideData` carries `otrSteps`,
`photoRules`, `signatureRules`, `certificateRules` and `rejectionPitfalls` as plain data with
no provenance field at all. A reader cannot tell which of these an authority printed.
`PracticeApplicationSimulator` is an entire second form written in TSX — deliberately, because
it validates real image uploads against published pixel specifications that the other
authority's notice does not print — but it is a component, not data, so nothing can check it
against a source.

**Not extracted at all.** Fees exist in the builder as a single blob
(`{amounts, exemptions, modes}`) with no scope, so a per-category or per-post amount cannot be
represented on the extraction side even though `schema.FeeRule` can now hold one.

## Migration boundary

The line this phase draws, and does not cross:

```
          official documents
                  ↓
    identity + officiality validation        (existing, unchanged)
                  ↓
    ApplicationProcess extraction            <- THIS PHASE
                  ↓
    ApplicationProcess (schema.py)           <- new source of truth
                  ↓
    compat.application_simulator_spec()      <- projection, added here
                  ↓
    ApplicationSimulatorSpec                 (existing shape, unchanged)
                  ↓
    ExamApplicationSimulator                 (existing UI, untouched)
```

**Above the projection** everything is new and evidence-backed. **Below it** nothing changes
in this phase: the two authored simulators keep working exactly as they do, `data.ts` is not
touched, and no component is edited.

The projection is deliberately partial and says so. It can build modules and fields from
extracted stages, because those are structural. It **cannot** invent traps: a trap asserts
that a specific mistake is fatal, which is a reading of a clause, and manufacturing those from
extracted text would be exactly the invention this phase forbids. So a projected spec carries
the stages it found and an empty trap list, and the authored specs remain the richer ones
until a later phase extracts rules with the same rigour.

## What the extractor must not inherit

- The step names in the authored spec are one portal's. Nothing may normalise another
  authority's wording onto them.
- `photoRules` / `signatureRules` exist as required top-level fields. The extractor must not
  produce them unless a document states them, and must not fill in dimensions from the
  general knowledge that such rules usually exist.
- `otrSteps` presumes a one-time-registration model. Some authorities have one; the extractor
  may not assume it.
