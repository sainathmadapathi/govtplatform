# Design: a validation & evidence layer between Tavily and GovOS

**Status: proposal for approval. No code has been changed.**

This designs the layer your brief asks for — Tavily → extraction → rule-based validation →
source+evidence storage → (human) → GovOS — corrected to the architecture that is actually in
the repo. Two corrections first, because they shape everything:

1. **There is no Firebase.** `firebase` appears only as an unused transitive entry in
   `package-lock.json`; it is not in `package.json` dependencies, not imported in any source
   file, and there is no `firebase.json`/`.firebaserc`/`firestore.rules`. The datastore is
   **SQLite** (`govos.db`) behind Flask. This design stores in SQLite, as you chose.
2. **Tavily results are not directly added to GovOS today.** `research_search` already
   classifies by domain, drops non-official results under OFFICIAL scope, and stores each
   result in `research_findings` with `review_status = 'PENDING_REVIEW'`. Nothing writes to
   the GovOS register (`data.ts`) automatically; the only route to a candidate is a human
   PROMOTE → "Add to Resource Library". So the safeguard you want largely exists. **This
   design does not change that flow — it adds a layer beside it.**

## 1. What is missing, precisely

The current pipeline stores findings as **whole web documents** (title / url / snippet /
trust / score). It never turns a finding into a **typed field-level fact**
(`{exam, field, value, evidence, status}`), so there is no per-field validation, no
cross-source conflict detection, and no field-level status. Tasks 4–10 of the brief are this
missing layer.

The model for it already exists offline in `tools/exam_builder/schema.py` — `Fact[T]` (value
+ evidence + four-state `Status`), `SourceEvidence` (verbatim-span check), domain trust
tiers, and a merge with CONFIRM / SUPERSEDE / CONFLICT. This layer brings that same
discipline to Tavily findings, in SQLite, feeding the existing human gate. **No LLM.**

## 2. The smallest safe change

- **Do not touch** `research_search`, `research_extract`, `research_finding_status`,
  `research_runs`, `research_findings`, `researchService`, or the Trust Panel's existing
  behaviour. They keep working exactly as now.
- **Add** one SQLite table (`research_facts`), one extraction+validation module, three new
  read/act endpoints, and one Trust-Panel sub-view. Extraction runs **on demand** (a button
  in the Trust Panel / a new endpoint), never silently inside search, so the existing path is
  untouched and the new one is opt-in.

```
existing:  Tavily → research_search → research_findings (PENDING_REVIEW)      ← unchanged
new:                                        │
                                            ▼  (on demand, per finding/run)
                              extract typed facts (rule-based, no LLM)
                                            ▼
                              validate (required/url/date/dup/conflict/reachable)
                                            ▼
                              research_facts  (status: pending|validated|conflicting|rejected)
                                            ▼  (human, in Trust Panel)
                                        approved / rejected
                                            ▼  (only approved, only via the EXISTING
                                               promote → resource_additions gate)
                                          GovOS
```

## 3. The structured fact (task 4)

One row of `research_facts` = one candidate value for one field of one exam, from one source:

```json
{
  "id": 91,
  "finding_id": 42,                     // FK → research_findings (the source document)
  "run_id": 7,                          // FK → research_runs (the query)
  "exam_id": "exam-ssc-cgl-2026",       // resolved against the register, or null if unresolved
  "exam_name": "SSC CGL",               // as the search targeted it
  "field": "application_last_date",      // canonical key from the field registry (§5)
  "raw_value": "15 July 2026",           // the span as it appeared
  "value": "2026-07-15",                 // normalized (ISO date / trimmed text / integer)
  "value_type": "DATE",                  // DATE | URL | TEXT | INTEGER | ENUM
  "source_url": "https://ssc.gov.in/...",
  "source_title": "SSC CGL 2026 Notice",
  "source_type": "OFFICIAL",             // OFFICIAL | HIGH | MEDIUM | LOW  (§6)
  "evidence": "...last date for applying is 15 July 2026...",  // verbatim snippet
  "extraction_rule": "date_near_label:application_last_date",   // which rule fired
  "confidence": 0.6,                     // from cues that fired; never a substitute for review
  "retrieved_at": "2026-09-23T10:11:00Z",
  "status": "pending",                   // pending|validated|conflicting|rejected|approved (§8)
  "validation_notes": ["date parsed", "source reachable"],
  "conflict_group": "exam-ssc-cgl-2026:application_last_date"  // set when ≥2 values disagree
}
```

Evidence is retained verbatim (task 9): `source_url`, `source_title`, `source_type`,
`retrieved_at`, `evidence` snippet, `raw_value` and normalized `value` all persist on the row.
The original finding is never mutated — the fact points at it by `finding_id`.

## 4. Table schema (task 11 — SQLite, additive, compatible)

```sql
CREATE TABLE IF NOT EXISTS research_facts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    finding_id      INTEGER NOT NULL,
    run_id          INTEGER,
    exam_id         TEXT,
    exam_name       TEXT,
    field           TEXT NOT NULL,
    raw_value       TEXT,
    value           TEXT,
    value_type      TEXT NOT NULL DEFAULT 'TEXT',
    source_url      TEXT NOT NULL,
    source_title    TEXT,
    source_type     TEXT NOT NULL DEFAULT 'LOW',
    evidence        TEXT,
    extraction_rule TEXT,
    confidence      REAL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'pending',
    validation_notes TEXT,               -- JSON array
    conflict_group  TEXT,
    retrieved_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reviewed_at     TIMESTAMP,
    FOREIGN KEY (finding_id) REFERENCES research_findings(id),
    FOREIGN KEY (run_id)     REFERENCES research_runs(id)
);
CREATE INDEX IF NOT EXISTS idx_research_facts_conflict ON research_facts(conflict_group);
CREATE INDEX IF NOT EXISTS idx_research_facts_status   ON research_facts(status);
```

Added in `init_database()` alongside the other `CREATE TABLE IF NOT EXISTS` blocks — no
existing table is altered, so no migration and no risk to current data. The row maps 1:1 to a
future Firestore document (`research_facts/{id}`) if Firebase is ever adopted, so this choice
does not close that door.

## 5. GovOS field registry (task 5)

A single table `FIELD_REGISTRY` (Python constant) defines each field once — its canonical key,
value type, and the label cues an extractor looks for. Covers every field you listed:

| key | type | label cues (examples) |
|---|---|---|
| `exam_name` | TEXT | name of exam |
| `conducting_authority` | TEXT | conducted by, authority, commission, board |
| `official_website` | URL | official website, apply online at |
| `notification` | URL | notification, advertisement no. |
| `eligibility` | TEXT | eligibility, eligible candidates |
| `age_limit` | TEXT | age limit, minimum/maximum age, as on |
| `qualification` | TEXT | educational qualification, must hold |
| `vacancies` | INTEGER | vacancies, number of posts, tentative vacancies |
| `application_start_date` | DATE | applications open, from, start date |
| `application_last_date` | DATE | last date, closing date, up to |
| `correction_window` | DATE | correction window, edit/modify |
| `exam_date` | DATE | date of examination, exam scheduled |
| `admit_card` | DATE/URL | admit card, call letter, hall ticket |
| `result` | DATE/URL | result, declared on |
| `syllabus` | TEXT/URL | syllabus, scheme of examination |
| `exam_pattern` | TEXT | pattern, scheme, marking |
| `application_fee` | TEXT/INTEGER | fee, application fee, ₹ |
| `previous_papers` | URL | previous year, question paper |

Types drive validation (a DATE is parsed; a URL is format- and reachability-checked). Unknown
labels are not guessed — no fact is emitted for a field whose cues did not fire.

## 6. Source classification (task 6)

Reuse the existing `_classify_trust(url)` and map its three tiers onto your four, so there is
one source of truth for what "official" means:

- **OFFICIAL** — `*.gov.in`, `*.nic.in`, and the statutory hosts already in `OFFICIAL_HOSTS`
  (UPSC, SSC, IBPS, RBI, …). Highest priority.
- **HIGH** — `*.ac.in`, `*.edu`, PRS and the `TRUSTED_PUBLIC_HOSTS` set.
- **MEDIUM** — recognised mainstream news domains (a short, explicit allowlist).
- **LOW** — everything else (coaching sites, blogs, aggregators, unknown hosts).

A fact's `source_type` is its finding's tier. **Priority affects ordering and conflict
resolution eligibility, never auto-verification** (§8): an OFFICIAL source still enters as
`pending`.

## 7. Rule-based validation (task 7 — no LLM)

Each fact runs through ordered checks; each appends to `validation_notes`:

1. **Required fields** — `field`, `source_url`, and a non-empty `value` must be present, else
   `rejected` (a fact with no value is not a fact).
2. **Valid URL** — `source_url` (and any URL-typed `value`) must parse as `http(s)://host/…`.
3. **Valid date** — DATE values must parse to a real calendar date; implausible dates (e.g. a
   `result` before the `exam_date` for the same exam, where both are known) are flagged, not
   silently kept.
4. **Missing value** — a cue fired but no value was extractable → not stored (a gap here is
   not a fact).
5. **Duplicate** — same `exam_id` + `field` + normalized `value` + `source_url` already
   present → skip (idempotent re-runs).
6. **Conflict** — same `exam_id` + `field`, **different** normalized `value` from a different
   source → both marked `conflicting`, sharing a `conflict_group` (task 10). Never silently
   pick one.
7. **Source availability** — the `source_url` is HTTP-checked using the existing
   `/api/resources/verify-links` machinery (GET, browser headers). Unreachable → noted; the
   fact stays but cannot be `validated` until reachable.

A fact that passes 1–5 and 7 with no conflicting sibling becomes `validated`; a conflict makes
it `conflicting`; a hard failure (no value / bad URL) makes it `rejected`. **Passing
validation is not approval** — it means the value is well-formed and sourced, nothing more.

## 8. Status lifecycle (task 8) — never auto-"verified"

Fact statuses (distinct from the finding's PENDING_REVIEW/REVIEWED/PROMOTED/REJECTED):

```
pending      just extracted, not yet validated
   ├─ validated     passed all rules, no conflict, source reachable
   ├─ conflicting   another source disagrees on the same field (both kept)
   └─ rejected      failed a hard rule (missing value, invalid URL)
validated ──(human, Trust Panel)──▶ approved | rejected
conflicting ──(human resolves)────▶ approved(one) + rejected(other) | left conflicting
```

Only `approved` facts are eligible to reach GovOS, and only through the **existing** human
promote → `resource_additions` gate — this layer adds no new automatic write to `data.ts`.
Nothing is ever marked verified merely because Tavily returned it (task 13/14 honoured).

## 9. Endpoints (additive; existing routes untouched)

- `POST /api/research/facts/extract` — `{finding_id}` or `{run_id}`: extract + validate facts
  from stored findings, insert into `research_facts`, return them. (Does **not** call Tavily.)
- `GET  /api/research/facts?run_id=&status=&exam_id=` — list facts for the Trust Panel.
- `POST /api/research/facts/<id>/status` — `{status: approved|rejected|conflicting}` for human
  review, sets `reviewed_at`.

Frontend: three thin `researchService` methods and a "Structured facts" sub-view in the Trust
Panel showing each fact with its field, value, evidence snippet, source tier, status, and —
for a `conflict_group` — both values side by side. No redesign; it sits beside the existing
findings list.

## 10. Logging (task 12)

One tagged line per stage, greppable as `[research-fact]`:

```
[research-fact] extract finding=42 run=7 exam=exam-ssc-cgl-2026 → 4 candidate facts
[research-fact] field=application_last_date raw='15 July 2026' value=2026-07-15 rule=date_near_label
[research-fact] validate id=91 field=application_last_date result=validated notes=[date parsed, source reachable]
[research-fact] classify id=91 source=OFFICIAL url=ssc.gov.in
[research-fact] store id=91 status=validated table=research_facts
[research-fact] conflict group=exam-ssc-cgl-2026:application_last_date values=[2026-07-15, 2026-07-22] sources=2
```

## 11. Honest limits (stated, not hidden)

Rule-based (regex + label-proximity) extraction over a 1,200-char snippet is **lossy**: it
will miss values stated far from their label, in tables, or in prose it has no cue for, and it
can mis-associate a nearby date. That is why **every extracted fact enters as `pending`, never
`validated`-and-done**, why low confidence is recorded, and why a human still approves before
anything moves. This layer raises the floor (structured, validated, conflict-aware, evidenced)
without pretending regex is comprehension — the LLM verification layer you're deferring is
what would close that gap later, and this table is shaped to receive its judgements when it
arrives.

## 12. Deliverables the implementation will produce (your A–G)

A. **Files changed** — `app.py` (new table in `init_database`, new module `research_facts`
   logic, three routes), `src/services.ts` (three fetch wrappers), `src/ui.tsx` (Trust-Panel
   sub-view). No existing function's behaviour altered.
B. **Per-file changes** — enumerated in the PR.
C. **New store** — the `research_facts` table above (SQLite; Firestore-shaped for the future).
D. **Example Tavily input** — a real captured search (`SSC CGL 2026 last date`), replayed from
   cache, no credits spent.
E. **Example processed output** — the fact rows it yields, with statuses.
F. **Validation rules** — the seven in §7.
G. **How to test** — run a cached search → call `facts/extract` → inspect `research_facts` →
   see `validated` / `conflicting` / `rejected` → approve one in the Trust Panel → confirm it
   becomes eligible for the existing promote gate and that `data.ts` is untouched until a human
   promotes.

---

**Awaiting approval of this design before writing any code.** On approval I'll implement it as
the smallest safe change above and report A–G against the running app.
