# Eligibility & Posts — what exists, and what it assumes about every exam

Read against `src/types.ts` (`PostRequirement`, `EligibilityRule`, `RuleGroup`),
`src/data.ts` (five records, 34 posts), `src/services.ts`
(`getCategoryAgeRelaxation`, `evaluatePostEligibility`, `evaluateEligibility`),
`src/ui.tsx` (`EligibilityCalculator`, section 03) and `tools/exam_builder/schema.py`
(`Post`, `AgeRule`, `AgeRelaxation`, `QualificationRule`, `Eligibility` — built in Phase F,
still unfilled).

## 1. Existing contracts

```ts
PostRequirement {
  id, postName, department, ministry?, payLevel, payScale, gradePay?
  classification: 'Group A (Gazetted)' | 'Group B (Gazetted)'
                | 'Group B (Non-Gazetted)' | 'Group C'        // REQUIRED, closed
  minAge: number; maxAge: number                               // REQUIRED, scalars
  specialQualification?, physicalRequired?, physicalNote?
  colorBlindnessAllowed?, natureOfWork?, ruleGroup?
  provenance: DataProvenance                                   // one for the whole post
}

EligibilityRule {
  ruleType: 'AGE_MIN'|'AGE_MAX'|'DOB_CUTOFF'|'DEGREE_REQUIRED'|'BRANCH_SPECIALIZATION'
          |'PERCENTAGE_MIN'|'NATIONALITY'|'CATEGORY_RELAXATION'   // closed
  operator: '>='|'<='|'='|'IN'|'BETWEEN'
  ruleValue: string | number | string[]
  category: 'GENERAL'|'OBC'|'SC'|'ST'|'PwBD'|'EWS'               // closed
  provenance: DataProvenance
}

Exam.crucialEligibilityDate: string        // ONE cutoff for the whole exam
Exam.globalRuleGroup: RuleGroup            // REQUIRED on every exam
Exam.eligibilityHighlights?: {title, body, provenance}[]   // prose cards
```

The universal side already exists and is empty: `Post`, `AgeRule` (scoped, with
`relaxations`, per-rule `cutoff_date`, `born_not_earlier_than`/`born_not_later_than`),
`AgeRelaxation` (`years` **and** `absolute_maximum`, its own scope and evidence),
`QualificationRule`, `VacancyCount`, `AttemptRule`.

## 2. Existing producers

| producer | output | how |
|---|---|---|
| `src/data.ts` | **34 posts across 5 exams** | hand-authored, each with provenance |
| `extract.py: services_list` | post names | one regex over list markers |
| `extract.py: age_limits`, `qualification` | `{minimum, maximum}`, a string | regex |
| `semantic.py: SPECS` | `ageLimits`, `qualification` | cue-based, **not wired to `Post`** |
| `schema.Eligibility` | — | **nothing fills it** |

`UPSC_CSE_EXAM` has **0 posts** — its 23 services were dropped because
`PostRequirement.classification` is required and closed, and the notice does not print a
Group for the IAS, IFS or IPS. The emitter names them in a file header instead. This is the
clearest cost of the current contract.

## 3. Existing consumers

| where | use |
|---|---|
| `services.ts:164` | `evaluatePostEligibility` — age, degree, JSO rule, physical |
| `services.ts:250` | `evaluateEligibility` — builds `legalClauses`, maps posts |
| `ui.tsx:2167` | `EligibilityCalculator` — relaxation shown to the candidate |
| `ui.tsx:17837` | section 03 — renders `eligibilityHighlights`, falls back to `globalRuleGroup.rules` |
| `ui.tsx:3997,4027,4255` | chat answers for age, attempts, fee |
| `ui.tsx:2170` | post filters, `physicalRequired` |

## 4. Hard-coded assumptions

**These five are factual claims made about every exam without reading that exam's documents.**

1. **`getCategoryAgeRelaxation()`** (`services.ts:120`) — `OBC +3`, `SC/ST +5`, `PwBD +10`,
   everything else `0`. No provenance, no exam, no post. Called from three places including
   the candidate-facing calculator. **This is the phase's main target.**
2. **`crucialDate = '2026-08-01'`** — one authority's cutoff, used as the default whenever an
   exam does not carry one, and as the *only* cutoff when it does.
3. **`legalClauses`** (`services.ts:254-258`) — three strings naming
   *"SSC CGL Notification Section 3.1"*, *"Section 3.2"*, *"Section 8.1"*, rendered for
   **every** exam. An APPSC candidate is shown an SSC clause number as the basis of their
   verdict.
4. **`post.id === 'post-jso'`** — a post-specific rule for one exam, inside the generic
   evaluator.
5. **`isBachelor`** — every post is assumed to need a bachelor's degree, so an exam
   recruiting at 10th or 12th pass disqualifies everyone who has one.

Structural, rather than factual, but still closed:

6. `classification` — required, four values, which is why UPSC has no posts.
7. `EligibilityRule.category` — six values; an authority's own category wording cannot be
   recorded.
8. `EligibilityRule.ruleType` — eight values; experience, domicile, medical standards,
   licences and language requirements have no representation at all.

## 5. Existing provenance

Good where it exists: every `PostRequirement` and every `EligibilityRule` carries a
`DataProvenance`, and `eligibilityHighlights` cards each carry one.

Absent exactly where the claims are strongest: `getCategoryAgeRelaxation` returns a bare
number, `crucialEligibilityDate` is a bare string, and `legalClauses` are bare strings. The
three least sourced things in the eligibility path are the three shown most prominently to a
candidate.

## 6. Missing scopes

- no **per-post cutoff date** — one date for the exam
- no **per-post relaxation** — relaxation is global and computed
- no **category vocabulary of the authority's own**
- no **experience**, **domicile**, **medical**, **licence** or **language** rule at all
- no **per-category vacancies** — `vacanciesTotal` is one string on the exam
- no **cycle** on a vacancy, so a revised count would overwrite the old

## 7. Extraction gaps

`semantic.py` already reads `ageLimits` and `qualification` cue-wise, but into a flat
`{minimum, maximum}` with no scope, no cutoff and no relaxations — so nothing it produces can
reach `Post` or `AgeRule`. There is no reader at all for posts as entities, vacancies,
experience, physical or medical standards.

## 8. Compatibility constraints

- `PostRequirement.minAge`/`maxAge` are **required numbers** and four components read them,
  so the universal shape has to project back into them.
- `classification` is **required**; projecting a post whose Group is unprinted needs a value,
  and inventing one is what this phase must not do.
- `globalRuleGroup` is **required** on `Exam`.
- `evaluatePostEligibility` is exported and used by the UI; its signature should survive.
- Removing `getCategoryAgeRelaxation` outright breaks three call sites and `ui.tsx`'s import.
  It has to be replaced by something that takes the exam's own rules and says so when it has
  none.
