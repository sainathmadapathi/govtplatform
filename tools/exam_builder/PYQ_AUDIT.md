# PYQs and answer keys: what exists, what it assumes, and what four authorities actually publish

Audit only. No production data was changed while writing this.

## 1. The existing contract

Three types carry questions today, and only one of them is about real papers.

**`OfficialPaperQuestion`** (`src/types.ts`) — a question from an authority's own paper:

```ts
export interface OfficialPaperQuestion {
  id: string; examId: string;
  paperName: string; paperYear: number;
  stage: 'PRELIMS' | 'MAINS';          // closed union
  section?: string; questionNumber: number;
  promptEnglish: string;                // English only, by name
  marks: number;                        // required
  answerFormat: 'DESCRIPTIVE' | 'MCQ';  // closed union
  options?: string[];                   // strings, no labels
  officialAnswerKey: string | null;     // one answer, or none
  officialAnswerKeyNote?: string;
  provenance: DataProvenance;
}
```

Three rules are already right and must survive this phase: `examId` is stored and never
inferred, `officialAnswerKey` is `null` where the authority published none, and `provenance`
names document and page.

**`PracticeQuestion`** — the authored practice bank. Carries `questionType: 'OFFICIAL_PYQ' |
'GOVOS_CREATED' | 'AI_GENERATED' | …`, a `tier: 'TIER_1' | 'TIER_2'`, a `shiftInfo` *string*,
`options: QuestionOption[]` and `correctOptionIndex: number`. It has no exam id at all — it
belongs to `PRACTICE_BANK_EXAM_ID`, which is SSC CGL, and the engine boundary is what keeps
it there.

**Builder side** (`schema.py`) already has the identity work from Phase F:
`PaperIdentity` (exam, cycle, stage, paper, subject, language, set_code, session, with
`key()`, `matches()` and `is_paper_level`), `OfficialPaper`, `AnswerKey` (with `kind`,
`revises`, `is_attached_to_a_paper`) and `AnswerKeyKind` (PROVISIONAL / FINAL / REVISED /
UNSPECIFIED). **What does not exist is a question entity on the builder side**, any producer
for papers or keys, and any per-question answer record.

## 2. Existing data

`UPSC_OFFICIAL_QUESTIONS` — 8 items, the CSE 2026 Main Essay paper's topics, read by OCR,
each `UNDER_VERIFICATION` with its page. `ALL_OFFICIAL_QUESTIONS` is that list and nothing
else; `officialQuestionsForExam(examId)` filters on the exact id and is the only accessor an
engine may use. That accessor is correct and stays.

The SSC practice bank is 35 `*_TEMPLATES` entries cycled by `buildFullPaperQuestions()` with
`i % len`, so every "100-question shift paper" repeats the same items. Those are
`GOVOS_AUTHORED`, and the UI says so — but `PracticeQuestion.questionType` includes
`'OFFICIAL_PYQ'`, and `shiftInfo` is free text like "Tier-1, 2023 Shift 2". **A bank item
labelled OFFICIAL_PYQ with a shift string is one careless edit away from claiming to be a
real paper's question**, with no paper identity behind it and no evidence.

## 3. Hard-coded assumptions found

1. **`stage: 'PRELIMS' | 'MAINS'`** — a closed union. An exam with Tiers, Phases or a single
   paper cannot be expressed.
2. **`paperName` + `paperYear` is the paper identity.** No shift, no session, no set code, no
   language, no date. Two shifts of one day collapse onto one identity.
3. **`marks: number` is required**, so a paper that does not print per-question marks has to
   claim a number.
4. **`options?: string[]`** — no option labels, so a paper labelled (a)/(b)/(c)/(d) and one
   labelled 1/2/3/4 are indistinguishable, and an answer can only be matched by position.
5. **`officialAnswerKey: string | null`** — exactly one answer. No multiple accepted answers,
   no dropped question, no revision, no key kind, no key provenance of its own.
6. **`promptEnglish`** — English by construction. A bilingual paper's Hindi side has nowhere
   to go, and a Hindi-only paper cannot be stored at all.
7. **`questionNumber: number` with no paper scoping in the id.** Ids are hand-written
   (`upsc-2026-essay-q1`), so uniqueness is a naming convention, not a constraint.
8. **`PracticeQuestion.tier`** is SSC's vocabulary, and `correctOptionIndex` assumes exactly
   one correct option always exists.
9. **No answer-key entity anywhere in the frontend.** The phrase "answer key" appears in
   chat answers and one results tab label; there is no record of a key, its kind, its date or
   what it revises.

## 4. Fallback behaviour

There is none, and that part is right. `officialQuestionsForExam` filters on the exact id;
`ExamPracticeRouter` keys engines by exam id and `assertExamMatches()` refuses to render for
the wrong exam; `UnavailablePracticeEngine` is the honest state and there is no default.
`getMockAttempts(examId)` and `GET /api/sqlite/mock-attempts?exam_id=` filter in the store
and in SQL. Nothing needs loosening here; the new work must fit inside it.

## 5. What the four authorities actually publish

Checked against the captured manifests and the authorities' own pages on 2026-09-22.

**UPSC — 365 Civil Services papers, every one a scan.**
`upsc.gov.in/examinations/previous-question-papers` carries 702 PDFs, of which 365 are Civil
Services (`QP-CSM-*` Main, `QP-CSP-*` Preliminary). The file names are structured and are
the identity: `QP-CSM-26-010926-GENERAL STUDIES PAPER - I.pdf`,
`QP-CSM-26-010926-Optional-AGRICULTURE_PAPER_I.pdf` — exam code, two-digit year, date of the
sitting, paper or optional subject. The other 337 belong to other UPSC examinations
(`IFSM` 90, `IES` 30, `CDSE` 12, `NDA` 6, `SO`, `CISF`, `GEOSM`…) and **must never enter the
CSE record**, which is the sharpest contamination risk in this phase.

Every CSE paper sampled — 2023, 2024, 2025 and 2026, Main and optional — extracts **zero
words**. They are image scans with no text layer. The Essay paper's eight topics are in the
record only because they were OCR'd and are marked `UNDER_VERIFICATION` for that reason.
UPSC publishes **no answer key** for CSE 2026; its Answer Keys page lists none.

**SSC — no public question papers, but nine official answer-key notices for this exam.**
SSC does not publish CGL question papers at all. It publishes *notices* that a key has been
uploaded, and the key itself is served to each candidate behind their own login. The cached
notice board holds 691 items, 85 of them about answer keys or question papers, and **nine of
those name the Combined Graduate Level Examination**:

| notice date | paper | kind |
|---|---|---|
| 2026-06-17 | CGL 2025 Tier-II | Final |
| 2026-01-30 | CGL 2025 Tier-II | Tentative |
| 2026-01-09 | CGL 2025 Tier-I | Final |
| 2025-10-18 | CGL 2025 Tier-I | Challenge window extended |
| 2025-10-16 | CGL 2025 Tier-I | Tentative |
| 2025-03-18 | CGL 2024 Tier-II | Final |
| 2025-01-21 | CGL 2024 Tier-II | Tentative |
| 2024-12-19 | CGL 2024 Tier-I | Final |
| 2024-10-03 | CGL 2024 Tier-I | Tentative |

Each is a PDF on ssc.gov.in stating the exact examination, the exact tier, the kind of key,
the date and time it was uploaded, and the window in which a candidate may view or challenge
it. The other 76 belong to other SSC examinations — Junior Engineer, Stenographers, Delhi
Police, the LDCEs — and are exactly what must not be attached to CGL.

These are **answer-key records without answer-key contents**, which is the case §7 of the
brief describes: the key exists, its paper is exactly identified, and its per-question
answers are not published to the public at all.

**IBPS and LIC — nothing.** Neither publishes question papers or answer keys. IBPS's
notification says its descriptive paper "may be broadly based on…" and nothing more; LIC's
names its sections and no items.

## 6. What this means for the phase

There is no exam among the four for which a public, machine-readable official question paper
exists. That is a fact about the authorities, not a gap in the reader, and the right output
is:

- a **universal question model** that can hold what the Essay already holds and much more
  (option labels, multiple accepted answers, dropped questions, numerical and descriptive
  answers, language, passage grouping, per-paper numbering) without forcing any of it;
- an **official-paper catalogue** for the exam whose authority publishes papers, with exact
  identity parsed from the authority's own naming and contents `NOT_EXTRACTED` for the
  stated reason "published as a scan with no text layer";
- **answer-key records** for the exam whose authority publishes key notices, with exact paper
  identity, kind, dates, the access route, and a *revision relationship* where a final key
  supersedes the tentative one for the same paper;
- and `NOT_PUBLISHED` for the two exams whose authorities publish neither.

Optimising for the number of questions extracted would mean OCR'ing 365 scans and publishing
the results as official PYQs. That is exactly what this product must not do: OCR of a scanned
booklet loses word spacing and misreads option labels — sampling one showed `(b)` read as
`(q)` — so the items would be wrong in ways a candidate cannot see.

## 7. What can be reused

`PaperIdentity` and `AnswerKey` (schema.py) unchanged; `identity.py` for content identity and
the cycle check; `merge.py` for MATCH / CONFIRM / SUPERSEDE / REFUSE; `pattern.py`'s reading
helpers (`_Cursor`, `_evidence`, `_slug`) and its publication gate; `compat.to_legacy_provenance`
and the projection shape used by `pattern_tree` / `syllabus_tree`;
`officialQuestionsForExam` and the practice router's exam-id boundary, which already enforce
§15 and need no change.

## 8. What the readers actually produced

Run against the captured manifests and the authorities' own pages; no Tavily call was made.

| exam | official papers found | catalogued | readable | answer keys | published |
|---|---|---|---|---|---|
| SSC CGL | none published | — | — | **8**, across 4 papers | 8 keys |
| UPSC CSE | 702 files on the listing, **424 carry this exam's codes** | 410 | **0** | none | 140 papers |
| IBPS PO | none | — | — | none | nothing |
| LIC AAO | none | — | — | none | nothing |

**The filtering is the work.** Of 702 files on one authority's listing, 278 carry no code of
this exam, 14 carry another examination's, and 410 of the remainder resolve to a paper-level
identity read from the file's own naming: `QP-CSM-26-010926-Optional-AGRICULTURE_PAPER_I.pdf`
is *2026 · Main · Paper-I · Agriculture*. Verified in the running app: every PDF link in the
published catalogue is a Civil Services paper and not one belongs to the Forest Service,
the Defence Services, the Engineering Services or the Academies.

**Every paper is a scan.** Papers sampled from 2023, 2024, 2025 and 2026 — Main, optional
and Preliminary — extract zero words. Each catalogued paper therefore carries its identity,
its link and the reason its questions are absent: published as an image with no text layer,
and OCR of a scanned booklet loses word spacing and misreads option labels. Nothing is
transcribed from them, and the section says so on every card rather than showing a paper
with no questions.

**The answer keys are real and exact.** Eight keys across four papers — CGL 2025 Tier-I and
Tier-II, CGL 2024 Tier-I, and the paper the authority itself labelled "(Paper-II) - 2024" —
each with the kind the notice calls it, the date it went up, the window in which it may be
viewed or challenged, and the route: served to each candidate through their own login, so
the per-question answers are not public. Three finals record the provisional key they
supersede, and both are kept.

Two refusals are worth naming. The notice labelled "(Paper-II) - 2024" is **not** linked to
the "2024 (Tier-II)" final key, because the authority worded the two differently and GovOS
cannot decide that they are the same paper. And a notice about an extension of the
Option-cum-Preference window, which the board filter caught by its headline, produced no key
at all: its body is about a preference form, and a key whose paper cannot be established is
not recorded.

## 9. What was published

`exam-ssc-cgl-2026` gained 8 `answerKeys`; `exam-upsc-cse-2026` gained 140 `officialPapers`
(the most recent cycles of 410 catalogued — a candidate-facing list, not an archive). The
three records whose authorities publish neither gained nothing. The diff is 4,258 insertions
and zero deletions, and the publisher proves it: stripping exactly what it inserted
reproduces the original file byte for byte.
