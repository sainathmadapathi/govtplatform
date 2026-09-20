# Why post extraction returns zero, and what the documents actually look like

## 1. The failure shape

`eligibility.extract_posts` looks for `_POST_ROW = (?:^|\n)[ \t]*([^\n|]{0,60}\|[^\n]{4,300})`
— a row is a line containing a pipe. Neither document contains one. Both publish their post
tables as PDF tables, and PDF text extraction flattens a table into **one cell per line**,
with a cell's own wrapping producing several lines of its own. The reader therefore matches
nothing, returns `[]`, and everything downstream that needs a post — post-scoped age,
post-scoped qualification, per-post vacancies — has nothing to attach to.

It is a total miss rather than a partial one, which is why the count is exactly zero and not
merely low.

## 2. What the real structure is

```
 0  'Name of Post Ministry/Department/Office/\r'    <- header, wrapped
 1  'Cadre\r'
 2  'Classification of \r'
 3  'Post Age Limit\r'
 4  '1\r'                                           <- row boundary: a bare ordinal
 5  'Assistant Audit \r'                            <- name, wrapped
 6  'Officer\r'
 7  '(Central\r'
 8  'Cadre)\r'
 9  'Indian Audit & Accounts \r'                    <- department, wrapped
10  'Department under O/o \r'
11  'Comptroller and Auditor \r'
12  'General of India (C&AG)\r'
13  'Group ?B? \r'                                  <- classification, wrapped
14  'Gazetted (Non-Ministerial)\r'
15  '18-30 years\r'                                 <- age
16  '2.\r'                                          <- next row
```

Four observations that the algorithm is built on:

1. **The header is itself wrapped**, so column labels have to be recovered from the joined
   text of several lines rather than from one.
2. **Rows are delimited by a bare ordinal on its own line** — `1`, `2.`, `01`, `(i)`.
3. **A cell spans a variable number of lines**, so the count of lines in a row is not the
   count of columns.
4. **A wrapped line keeps its trailing space** (`'Assistant Audit '`) while the last line of
   a cell does not (`'Officer'`). Combined with bracket balance this separates cells without
   knowing anything about their contents — see §3.

There is also a **pay level in the section heading above the table**
(`2.1 Pay Level-8 (₹ 47600 to 151100):`) rather than in a column, so a value can govern every
row of a table without appearing in any of them.

## 3. The separation signal

A cell continues while any of these holds, and ends otherwise:

- the line ends with whitespace — it was wrapped mid-cell
- brackets are unbalanced so far — `(Central` is waiting for `Cadre)`
- the next line opens with `(` — `Officer` followed by `(Central Cadre)`

Checked against the rows above this yields exactly four cells for four columns, for a name
with a bracketed suffix on one line (`Officer (State Cadre)`) and across two (`Officer` /
`(Central Cadre)`). Where it does not produce one cell per column, the row is refused rather
than guessed — that is the honest failure and it is what §13 of the brief asks for.

## 4. Current contract

`schema.Post` is already open: `id`, `name`, then `department`, `classification`, `pay` as
`Fact`s, `vacancies`, `qualification`, `other_requirements`, `evidence`, `status`. Nothing
required beyond a name, and `classification` is a `Fact[str]`, not an enum.

**The closed union is on the frontend**: `PostRequirement.classification` is required and
admits four values.

*Correction to an earlier report.* I previously wrote that the UPSC record carries 0 posts.
It does not — it carries **23**, built through a helper (`upscGroupA`) rather than as
literals, which a `postName:` grep did not see. Every record has posts: 18, 23, 1, 3, 3.

What is genuinely zero is *extraction*: the builder produced no posts from any document, and
the records' posts are all hand-authored. That is the gap this phase closes.

The closed union still costs something, and the cost is visible in that helper: it assigns
`Group A (Gazetted)` to every post it builds, including three services whose Group the
notice does not print. The type left no third option between omitting the post and asserting
a classification the document never stated. Its provenance is marked UNDER_VERIFICATION, so
the product is not claiming it as official — but extraction now supplies the real answer for
the services whose Group *is* printed, and correctly nothing for the three.

## 5. Existing extractors and how they are affected

| extractor | state | effect of zero posts |
|---|---|---|
| `extract_age_rules` | works — **46 bands found on one notice** | all unscoped, because `posts=[]`; they are the per-post bands from this very table |
| `extract_qualifications` | noisy — matches sentences *mentioning* qualification | nothing to scope to |
| `extract_vacancies` | works | counts cannot be attached to a post |
| `extract_relaxations` | works, table-aware | unaffected — relaxation is exam-wide here |

The 46 age bands are the clearest evidence that the table is being read *around* rather than
*into*: the bands are the `Age Limit` column of the rows this reader cannot see.

## 6. UI consumers

`ui.tsx` reads `exam.posts` for the post list, the filters (`physicalRequired`), the target
post, pay answers and the eligibility verdicts; `services.ts` maps `exam.posts` in
`evaluateEligibility`. All of them tolerate an empty array, and all five records populate it,
so the section renders for every exam today. What none of them can show is a post the
*builder* found, because until now it found none.

## 7. What the merge decided, on the real records

Extraction is only half the job: the records already hold hand-authored posts worth more
than a re-extraction of them. So the merge settles identity once per post and then decides
each field on its own, because rejecting a whole post over one contested field would throw
away a correct name, department and pay scale.

| exam | authored | extracted | confirmed | unchanged | contested | added |
|---|---|---|---|---|---|---|
| SSC CGL | 18 | 16 | 4 | 14 | 0 | 13 |
| UPSC CSE | 23 | 20 | 14 | 4 | 5 | 2 |
| IBPS PO | 1 | 0 | 0 | 1 | 0 | 0 |

The five contested UPSC posts are the interesting result, and they are all the same field:
the record says `Group A (Gazetted)` and the notice does not print a Group for those
services. That is **not** the notice contradicting the record — the services almost
certainly are Group A — it is the record asserting something no document in hand supports.
The merge therefore holds the field (`UNDER_REVIEW`), keeps the value, keeps every other
field, and refuses to delete anything.

Nothing is written into an exam's record by this pass. What ships is
`CLASSIFICATION_CONFIRMED` in `data.ts`: **17 posts whose Group an official document
actually prints**, each citing the document and quoting the row it was read from. The UI
marks a post outside that map with an asterisk explaining that GovOS has no published source
for its classification. One SSC post the merge confirmed is deliberately absent — its span
could not be traced back to a page, and a citation nobody can check is worth less than the
caveat.

Two refusals are load-bearing and tested: a post no extracted post matches is left exactly
as it is, and a post two extractions match equally well merges nothing at all rather than
risk merging the wrong pair.
