# Exam authoring pipeline

Name an exam; the pipeline reads **that authority's own documents** and produces a
`data.ts`-shaped `Exam` record in which every value cites the document and page it came
from.

```bash
python -m tools.exam_authoring "Civil Services"                 # list matches
python -m tools.exam_authoring "Civil Services Preliminary 2026" --pick 0 \
       --emit out.ts --json out.json
```

## What it guarantees, and what it does not

It **cannot** guarantee that every field of every exam gets filled, and no tool can: some
notices are scanned images with no text layer, some authorities publish no answer keys at
all, and every authority formats its notice differently. What it does guarantee is the
property that actually matters — **it never states something it did not read.**

Every field lands in exactly one of four states, and they are kept distinct on purpose:

| state | meaning |
|---|---|
| `FOUND` | sourced, with document, page and the words it was read from |
| `NEEDS_REVIEW` | read but not confidently (or read from a scan); emitted as `UNDER_VERIFICATION`, never badged official |
| `NOT_PUBLISHED` | the authority genuinely does not publish it — established from its own listing |
| `NOT_EXTRACTED` | the document was read but no pattern matched. **A gap in this tool, not a fact about the authority** |

Collapsing the last two is the single most dangerous thing this pipeline could do: "UPSC
publishes no answer key" is a finding a candidate can rely on, while "our regex missed the
age clause in the CDS notice" is a to-do for us. They are reported separately and worded
differently.

There is deliberately no state for "guessed". A field nobody could source is emitted as an
empty array, and the app already renders honest empty states for those.

## Isolation

`verify.py` runs before anything is emitted and **stops emission** if it fails:

* every URL read must belong to the exam's own authority (`assert_single_authority`)
* the exam id must be well-formed and unique to this record
* a mention of another authority inside an extracted value is *reported* for a person to
  judge, not silently stripped — a state notice may legitimately cite a central rule

One record holds one exam. Adapters never import each other.

## Layout

```
sources.py    fetch + cache + PDF/HTML text, keeping the URL and page with the text
record.py     Field / ExamRecord — the four states above, enforced structurally
extract.py    field extractors; each returns a Field, so a miss is recorded as a miss
emit.py       ExamRecord -> TypeScript `Exam` literal with provenance on every value
verify.py     isolation + coverage checks
registry.py   exam name -> authority adapter (the only place this mapping lives)
adapters/     one file per authority
```

## Adding an authority

Write `adapters/<authority>.py` with `discover(query)` and `gather(target)`, add one line to
`registry.py`. Touch nothing else. An authority with no adapter is reported as unsupported
rather than guessed at.

## Two rules learned the hard way, now encoded

1. **A notice PDF is not the last word on a date.** UPSC extended CSE 2026's last date by
   three days *after* publishing its notice, so the PDF says 24 February and the
   Commission's examination page says 27 February. The pipeline reads the page for dates,
   the PDF for rules, and when they disagree it keeps both — the page operative, the notice
   superseded, with a corrigendum explaining the move. It reproduces that specific
   correction automatically.
2. **A scanned PDF is unreadable, not empty.** Reporting "no rules found" for a document we
   could not read would claim the authority is silent when it is not.

## Verifying a generated record

The emitted file is plain TypeScript. Typecheck it against the real interface before using
it:

```bash
{ echo "import { Exam } from './types';"; sed -n '/^export const/,$p' out.ts; } > src/__gen_check.ts
npx tsc --noEmit && rm src/__gen_check.ts
```

This is how the `ImportantDate` union mismatch and the required-`classification` problem
were both caught; do not skip it.

## Cache

Fetched documents are cached in `.exam_cache/` (gitignored) so a re-run does not hammer a
government host. Study material is never committed — the content policy is links-only.
