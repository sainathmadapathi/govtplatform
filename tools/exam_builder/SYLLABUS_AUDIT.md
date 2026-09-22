# Syllabus: what exists, what it assumes, and what four real authorities actually publish

Audit only. No production data was changed while writing this.

## 1. The existing contract

`SyllabusTopic` in `src/types.ts` (lines 132-158) is the whole of the frontend's syllabus
model, and `Exam.syllabus: SyllabusTopic[]` is a **flat array**:

```ts
export type SyllabusSubject =
  | 'Quantitative Aptitude' | 'Reasoning & General Intelligence' | 'English Comprehension'
  | 'General Awareness' | 'Computer Proficiency' | 'Statistics'
  | 'History & Culture' | … | 'Indian Language & English (Qualifying)';   // 19 literals

export interface SyllabusTopic {
  id: string;
  subject: SyllabusSubject;          // closed union
  tier: 'TIER_1' | 'TIER_2' | 'BOTH';// closed union
  topicName: string;
  parentId?: string;                 // declared, used by nothing
  subtopics?: string[];              // plain strings: no id, no evidence, no children
  weightagePercentage: number;       // required
  avgQuestions: number;              // required
  isHighYield: boolean;
  officialProvenance: DataProvenance;
  weightageProvenance?: DataProvenance;
  revision?: { … };
}
```

Three levels at most, and the third is a bare string. There is no paper level, no stage
level that is not one of two tiers, and no way to say "the authority names this subject and
does not publish its topics".

The builder side already has the right model, from the Phase F contract
(`schema.py`, `SyllabusNode` / `Syllabus`): recursive `children`, `level_label` carrying the
authority's own word for the level, `scope` binding a node to a stage or paper, per-node
`evidence` and `status`, and `derived` kept apart from what was read. **What does not exist
is any producer, any projector, or any UI that can render it** — exactly the position the
pattern phase started from.

## 2. Existing producers

None. Every `SyllabusTopic` in `data.ts` is hand-authored. The only runtime writer is
`applySyllabusRevisions()` in `services.ts` (line 2182), which merges a verifier's ADD /
AMEND / RETIRE over the authored seed; it neither reads a document nor produces one.

## 3. Existing consumers

25 references in `ui.tsx`, 2 in `services.ts`:

| place | what it reads | assumes |
|---|---|---|
| section 06 list (18248) | the flat array | subject and tier are printable strings; every topic has a weightage |
| `SyllabusTreeMap` (16922) | the same array | builds Subject → Topic → Subtopic by grouping on `t.subject`; **depth fixed at 3** |
| tree-map node meta (16940) | `t.tier` | prints `T1+T2` / `T1` / `T2` for every exam |
| list badge (18275) | `weightagePercentage`, `avgQuestions` | prints "Weightage: ~X% (~Y Qs/Shift)" — **"Qs/Shift" is SSC's vocabulary**, shown to every exam |
| Trust Panel revisions (5393) | `syllabusExam.syllabus` | topic dropdown is `subject — topicName`, one level |
| chat (4300) | groups by `t.subject` | counts topics per subject |
| study roadmap (18167) | `exam.syllabus.length` | "N topics are on record" |
| `services.applySyllabusRevisions` | the flat array | a revision targets one topic id |

All of them tolerate an empty array. None of them can render a fourth level, a paper, or a
node whose topics the authority has not published.

## 4. Hard-coded assumptions

1. **Depth is three, and the last level is a string.** `subtopics?: string[]`.
2. **A closed subject union of 19 literals**, six of them SSC's sections and the rest
   UPSC's. Adding an exam whose authority names a subject outside that list means editing a
   type.
3. **A closed tier union**, `TIER_1 | TIER_2 | BOTH`, and it is *displayed*.
4. **Weightage and average questions are required numbers**, so "not published" has to be
   written as `0` — and one UPSC topic already carries `weightagePercentage: 0`.
5. **No paper level.** UPSC's syllabus is published *per paper* (Paper I, Paper II, Papers
   A, B and I-VII); those are flattened into subject strings.
6. **The tree map groups on `t.subject`**, so two papers that share a subject name merge
   into one branch.
7. **`parentId` exists and nothing reads it** — the one field that could carry hierarchy.
8. **"Qs/Shift"** in the weightage badge is SSC's word for a shift-based CBT.
9. **No per-node evidence.** One `officialProvenance` covers a topic and all its subtopics,
   so a topic read from a notice and a subtopic inferred from it cite the same document.
10. **No state.** There is no way to distinguish a subject the authority published from one
    GovOS authored, nor a topic list that is genuinely complete from one that is partial.

## 5. What the records actually hold

| exam | topics | distinct subjects | with subtopics | weightage |
|---|---|---|---|---|
| SSC CGL | 22 | 5 | 22 | all non-zero |
| UPSC CSE | 18 | 13 | 18 | one is 0 |
| IBPS PO | 2 | 2 | 0 | 40% and 55% |
| APPSC Group-I | 3 | 2 | 0 | authored |
| APPSC Group-II | 2 | 1 | 0 | authored |

The IBPS entries are the clearest illustration of the problem this phase exists to fix.
They are two topics — "Data Interpretation & Caselets" at 40% and "Puzzles & Circular /
Linear Seating Arrangements" at 55% — carrying SSC's subject vocabulary and a provenance
pointing at `https://ibps.in` rather than at any document. **IBPS publishes no syllabus at
all** (see §7), so neither the topics nor the weightages have a source. They are not wrong
in the sense of being bad guesses; they are unsourced, which in this product is the same
thing.

## 6. Cross-exam fallback

There is no syllabus fallback — `exam.syllabus` is read directly and an exam with an empty
array renders an empty section. That is the one part of this area already correct.
`defaultSyllabusView` picks which of section 06's three views opens first, and
`examHasStudyPaths(exam)` decides whether the Post Study Plan view exists at all; neither
substitutes another exam's content. The Trust Panel's exam picker (4826) filters to exams
with a non-empty syllabus, which is honest.

## 7. What the four captured authorities actually publish

No Tavily call is needed; all four notices are already in the manifests. Two publish a
syllabus and two do not, and that asymmetry is the finding.

**SSC CGL — a numbered clause hierarchy, four levels deep.**
`13.10 Indicative Syllabus (Tier-I):` then `13.10.1 General Intelligence & Reasoning:`
followed by prose naming the topics, and `13.11 Indicative Syllabus (Tier-II):` then
`13.11.1 Part A of Section-I of Paper-I (Mathematical Abilities):` then `13.11.1.1 Number
Systems: Computation of Whole Number, Decimal and Fractions…`. The clause number *is* the
hierarchy: depth is the count of its dot-separated parts, and the heading names the paper,
the section and the part it belongs to.

**UPSC CSE — headings and bullet lists, per paper.**
`SECTION III: SYLLABI FOR THE EXAMINATION` → `Part A—Preliminary Examination` →
`Paper I - (200 marks) Duration: Two hours` → seven bullets → `Paper II-(200 marks)` → six
bullets → `Part B—Main Examination` → the nine papers. The bullets are the syllabus; the
paper heading is what they belong to.

**IBPS PO — no syllabus.** The notification's only statement about content is a footnote to
the descriptive paper: "May be broadly based on Economic and Social issues, emerging trends
in Banking and Technology, Current events, Ethics etc." That is one sentence about one
paper, and it is all there is. The honest result for IBPS is NOT_PUBLISHED.

**LIC AAO — no syllabus.** The notice names its sections in the scheme table (Reasoning
Ability, Quantitative Aptitude, English Language, General Knowledge & Current Affairs, Data
Analysis & Interpretation, Insurance and Financial Market Awareness) and publishes no
topics under any of them. A section named in a scheme table is a paper's name, not its
syllabus.

## 8. What can be reused

- **`SyllabusNode` / `Syllabus`** in `schema.py` — recursive, `level_label`, `scope`,
  per-node evidence and status. Already tested by `test_schema.py`.
- **`pattern.py`'s reading layer** — `_Cursor`, the marked-heading test, `_IS_STATEMENT`,
  `_evidence()`, and `may_supply_pattern()`'s identity gate, which is the same gate a
  syllabus needs and for the same reason.
- **`tables.py`** — for any authority that publishes its syllabus as a table. Neither of the
  two that publish one does, so this is for the exams that come next.
- **`identity.py`** — content identity, including the year check that keeps a 2025 syllabus
  out of a 2026 record (§6 of the brief).
- **`merge.py`** — MATCH / CONFIRM / SUPERSEDE / REFUSE, and `pattern_merge.py` is the
  worked example of doing it field by field.
- **`compat.py`** — `to_legacy_provenance()`, and `pattern_tree()` as the projection
  pattern for a recursive node.

## 9. What has to be built

A producer (`syllabus.py`) that reads a numbered clause hierarchy and a heading-plus-bullet
list without knowing which authority wrote either; a node-level merge; a projection into a
recursive frontend type; and a section 06 that renders arbitrary depth with per-node state
and evidence. The contract on the builder side needs no change — which is what Phase F was
for.

## 10. What the reader actually produced

Run against the captured manifests only — no Tavily call was needed. Every node below was
read from the authority's own document and its span verified verbatim in it.

| exam | documents inspected / rejected on identity | roots | nodes | depth | level words the authority used | evidence |
|---|---|---|---|---|---|---|
| SSC CGL | 5 / 4 | 2 (Tier-I, Tier-II) | 102 | 5 | Syllabus, Subject, Part, Section, Paper, Topic | 102 VERIFIED |
| UPSC CSE | 6 / 5 | 1 (Section III) | 1013 | 5 | Syllabus, Part, Paper, Section, Unit, Group, Topic | 1013 VERIFIED |
| IBPS PO | 2 / 1 | — | 0 | — | — | NOT_PUBLISHED |
| LIC AAO | 4 / 3 | — | 0 | — | — | NOT_PUBLISHED |

Not one node is NEEDS_REVIEW or NOT_EXTRACTED, because a node whose span could not be found
verbatim is not published at all — the state exists for the cases where a title is read but
unconfirmed, and neither of these two documents produced one.

**The merge, against the records' authored topics:**

| exam | CONFIRMED | UNCHANGED | CONFLICTED | ADDED | topics the published syllabus does not word the same |
|---|---|---|---|---|---|
| SSC CGL | 0 | 20 | 2 | 84 | 20 |
| UPSC CSE | 5 | 10 | 3 | 892 | 10 |

Nothing authored was overwritten. `UNCHANGED` means the record's topic is not in the
published syllabus under that wording — for SSC that is most of them, because the record
holds a finer breakdown than the Commission's indicative syllabus prints. `CONFLICTED` is
where the two word a topic closely but not identically and no document establishes a
revision between them; those are held, with both wordings kept.

**One revision rule earned its keep during the replay.** The UPSC notice's file name ends
`Rev` and its first page carries a revision date, and on the first pass that was enough to
mark two topics SUPERSEDED. It should not have been: being a revised notice is not revising
a topic. A revision claim must now name the syllabus and sit in the syllabus's own region,
and with that the same run reports no supersession at all — which is correct, because that
notice publishes a syllabus rather than amending one.

**Two exams publish nothing, and that is the finding.** IBPS's notification says only that
its descriptive paper "may be broadly based on Economic and Social issues, emerging trends
in Banking and Technology, Current events, Ethics etc."; LIC's names its sections in the
scheme table and no topics under any of them. Both records keep their authored topics and
gain no tree, and the section says so in words rather than showing an empty shell.

**What did not change.** The two records that gained a `syllabusTree` gained nothing else:
the publisher strips exactly the blocks it inserted and checks the result is byte-for-byte
the file it started from, and the diff is 8,354 insertions and zero deletions. The three
records with no published syllabus are untouched, including both APPSC exams, which remain
blocked upstream by authority ambiguity.
