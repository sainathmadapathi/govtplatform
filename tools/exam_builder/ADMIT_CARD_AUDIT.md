# Admit cards: what exists, what it assumes, and what four authorities actually publish

Audit only. No production data was changed while writing this.

## 1. The existing contract

`AdmitCardDetails` in `src/types.ts` is the whole of the frontend's model, and `Exam` holds
exactly one of them:

```ts
export interface AdmitCardDetails {
  status: 'AVAILABLE' | 'NOT_YET_ANNOUNCED' | 'EXPIRED';   // closed union
  releaseDateStr: string;                                   // one date
  officialPortalUrl: string;                                // one URL
  loginCredentialsRequired: string[];                       // free strings
  instructions: string[];                                   // free strings
  cityIntimationAvailable: boolean;                         // a boolean
  cityIntimationUrl?: string;
  regionPortals?: { regionName; regionCode; statesCovered; portalUrl; status }[];
}
```

**One exam, one admit card, one URL, one date.** There is no stage, no paper, no cycle, no
authority label, no evidence and no provenance anywhere in it — the only admit-card type in
the product with no `DataProvenance` field at all.

The builder side already has the right shape from the Phase F contract
(`schema.py`): `AdmitCardNotice` with `kind` (ADMIT_CARD / CITY_INTIMATION /
EXAM_INTIMATION / OTHER — already separate concepts), a `Scope` binding it to a stage or
paper, `released_at`, `available_until`, `download_url`, `credentials_required`,
`instructions`, `alternate_portals`, `status` and `evidence`. **No producer exists**, and
nothing in the frontend can render it.

## 2. What the records hold

| exam | `admitCardDetails` | ADMIT_CARD milestone |
|---|---|---|
| SSC CGL | status NOT_YET_ANNOUNCED, release 2026-10-18, portal ssc.gov.in, city `true`, 4 region portals | 1 — **"Tier 1 City Intimation Slip & Admit Card Release"** |
| UPSC CSE | status EXPIRED, release 2026-05-15, portal upsconline.nic.in, city `false` | 1 — "Preliminary e-Admit Cards uploaded on upsconline.nic.in" |
| IBPS PO | none | 1 — "Online Preliminary Exam Call Letter Download" |
| APPSC ×2 | none | none |

The SSC milestone label is the clearest statement of the problem: **one milestone named for
both the city intimation slip and the admit card**, which are two events on two dates. IBPS
carries a milestone with no details record, so the section renders from a date alone.

## 3. Hard-coded assumptions

1. **One admit card per exam.** An exam with a Prelims call letter and a Mains call letter —
   which is most of them — cannot express the second.
2. **One URL per exam**, and it is not even used: the section's download button is
   `href={exam.officialDomain}`, i.e. **the authority's homepage presented as the "Official
   Download Portal"** for every exam, whether or not an admit card exists. This is the §13
   violation already shipping.
3. **`status` has three values and none of them is "we do not know".** An exam whose sources
   were never read is `NOT_YET_ANNOUNCED`, which is a candidate-facing factual claim about
   the authority. There is no NOT_EXTRACTED, and no way at all to say a fetch failed.
4. **`cityIntimationAvailable: boolean`** — `false` asserts the authority issues no city
   slip, when the truth is usually that GovOS has not read one.
5. **The heading is hardcoded** "e-Admit Card & Exam City Intimation Slip" for every exam,
   and the status badge reads "🟡 CITY INTIMATION RELEASED — ADMIT CARD SOON" whenever any
   release date exists — asserting a slip that may not exist for that exam.
6. **No stage or paper binding**, so a Tier-II call letter and a Tier-I one are the same
   record, and `exam.dates.find(d => d.type === 'ADMIT_CARD')` takes whichever comes first.
7. **`cityIntimationDate` is computed as** `d.label.includes('city') || d.type === 'ADMIT_CARD'`
   — so any admit-card milestone doubles as the city-intimation date.
8. **`instructions` and `loginCredentialsRequired` are free strings with no source.** They
   are candidate instructions with nothing behind them.
9. **`regionPortals`** is record-driven (good) but shaped by one authority's four regions.

## 4. Fallback and state

There is no cross-exam fallback — the section reads only `exam.admitCardDetails` and
`exam.dates` — and `AdmitCardSection` takes the exam as a prop, so switching exams re-renders
it. What is wrong is not fallback but **state**: a missing record and an unread source are
the same thing to this model, and both render as a claim about the authority.

## 5. What the four authorities actually publish

Read from the captured board, the notifications, and the authorities' own pages on
2026-09-23. All four publish something, and no two publish it the same way.

**SSC — one notice carrying two events, two dates and an exam date.**
The board's only admit-card item for this exam is
*"Important Notice – City and Admit Card live for candidates of CGLE 2025 – Exam on
14.10.2025"* (03.10.2025). Its body:

> candidates may ascertain whether their examination has been rescheduled … can view their
> examination **city details from 05.10.2025** onwards and **download their admit card
> w.e.f. 09.10.2025** by **logging in through the designated login module** on the website of
> the Commission (https://ssc.gov.in/)

That is a city-intimation event (05.10), an admit-card event (09.10), an exam date (14.10)
and a login requirement, in one document — §7 and §8 of the brief in a single paragraph. It
is also a **rescheduling** notice, so the exam date it carries supersedes an earlier one.

Note the cycle: CGL **2025**, not the 2026 record's own cycle.

**UPSC — a document row on the exam's own page.**
`upsc.gov.in/examinations/Civil Services (Preliminary) Examination, 2026` carries a
document table whose row reads `e - Admit Card | 15/05/2026`. The exam page *is* the exam's
identity, so the row needs no further disambiguation — but it gives a date and a label and
nothing else: no URL, no credentials, no instructions.

**IBPS — two call-letter events, one per stage.**
The notification's own schedule lists them separately: *"Download of call letters for Online
examination – Preliminary — August, 2026"* and *"Download of Call letter for Online
examination – Main — September, 2026"*. Both dates are **month-precision**, not days. The
notification also states requirements: a *"Valid Call Letter for the respective date and
session of Examination"*, and the Information Handout downloadable with the call letter.

**LIC — a rule instead of a date.**
*"Download of Call Letter for Online Examination — 7 days before examination"*. The
authority publishes a **relative** rule, not an absolute date, and a model that can only
hold a date has to either invent one or drop the fact. Its requirements are unusually
explicit: a valid call letter *with a photograph affixed on it*, photo identity proof in
original bearing the same name, a photocopy of that proof, and that candidates reporting
after the time printed on the call letter are not permitted.

**APPSC** remains blocked upstream by authority ambiguity and is not read at all.

## 6. One infrastructure finding

The SSC notice's own attachment URL contains a space —
`…/NoticeBoards/CGLE 14 Oct_Final.pdf` — and the fetcher raises `InvalidURL` on it. Read
naively, that exam has "no admit-card notice"; read correctly, the fetch failed and the
path needs percent-encoding. This is precisely the failure §16 exists for, and it is real
rather than hypothetical.

## 7. What can be reused

`AdmitCardNotice` / `AdmitCardNoticeKind` and `Scope` unchanged; `identity.py` for exact
exam and cycle identity; `merge.py` for MATCH / CONFIRM / SUPERSEDE / REFUSE; `dates.py`'s
milestone vocabulary for the exam date the notice mentions (which must stay a *milestone*,
not become the admit card's own date); `pattern.py`'s reading helpers and publication gate;
`compat.to_legacy_provenance` and the projection shape used by the last three phases.

## 8. What has to be built

A producer that reads a notice, a document table and a schedule table without knowing which
authority wrote any of them; a state model in which a fetch failure is not a claim; a merge
that never joins a city intimation to an admit card or one stage to another; and a section
that can show several events per exam, says which kind each is, and offers a download button
only where a verified official URL exists.

## 9. What the readers actually produced

Run against the captured board, the notifications and the authorities' own pages; no Tavily
call was made.

| exam | source | events | kinds | stage-bound | dated | rule only | download URL |
|---|---|---|---|---|---|---|---|
| SSC CGL | 4 notices (board) | **5** | 3 admit card, 2 city | 5 | 3 | 2 | 0 |
| UPSC CSE | the exam's own page | **1** | 1 admit card | 0 | 1 | 0 | 0 |
| IBPS PO | CRP PO/MT-XVI notification | **2** | 2 call letters | 2 | 2 (month) | 0 | 0 |
| LIC AAO | AAO notification | **1** | 1 call letter | 1 | 0 | 1 | 0 |
| APPSC ×2 | not read | — | — | — | — | — | — |

**Not one of the four publishes a direct download link.** Every one serves the document to
each candidate behind their own login, which is why `downloadUrl` is zero everywhere and why
the section offers a portal, labelled as a portal, instead of the homepage-as-download it
used to.

Six defects were found by running the readers against these documents rather than against
fixtures, and each is now a test:

1. **A signature date published as an examination date.** One notice ends "Under Secretary
   to the Govt. of India 03.09.2025", and a bare "exam date" cue reached it.
2. **A withdrawn date published as the operative one.** "the examination was scheduled to
   commence from 13.08.2025 ... However, after being postponed ... is now scheduled to be
   held from 12.09.2025": the first match won. The later statement now governs and the
   earlier is named in the fact's note.
3. **A range quoted as half of itself.** "2/3 days before the respective exam date" read as
   "3 days"; "02/03 days prior" as "03 days".
4. **An application date published as a call-letter release.** "... the call letter. 12. How
   to apply: Candidates can apply online from 16.08.2025" — a date in the next sentence.
5. **A rule quoted with the next table row attached**, because a flattened PDF has no cell
   boundaries: "7 days before examination Dates of Online Examination – Preliminary (tent".
6. **`Tier–1` with an en dash named no stage**, so two events came out unscoped while the
   document named their tier plainly.

## 10. What was published

`exam-upsc-cse-2026` gained 1 event and `exam-ibps-po-2026` gained 2. **SSC CGL 2026 gained
nothing, deliberately**: all four notices that pass its identity gate are for the **2025**
cycle, and a 2025 release date in a 2026 record is a wrong answer however it is labelled.
The two APPSC records were not read at all. The diff is purely additive, and the publisher
proves it — stripping exactly what it inserted reproduces `data.ts` byte for byte.

Four further defects were found by looking at the rendered page rather than the data:

- the banner asserted **"Your Call Letter and reporting schedule are live"** for SSC off a
  stale `status: 'AVAILABLE'` in an authored record that had never been re-read. Green now
  requires a read source *and* a published release date that has passed, and says plainly
  that GovOS cannot see the candidate's own login;
- a **schedule row's label became the document's name**, so the banner read "DOWNLOAD OF
  CALL LETTERS FOR ONLINE EXAMINATION – PRELIMINARY ACTIVE & DOWNLOADABLE". The document is
  a *call letter*; the row is kept and shown as the row it is;
- the **sample hall ticket printed a fabricated roll number, shift, gate time and centre**
  ("2201048291", "iON Digital Zone iDZ ... Lab 4, New Delhi") under an "illustrative" label.
  The layout is unchanged; the values are the names of the fields;
- **UPSC's own sign-in portal was refused** by the reader's domain guard, because
  `upsconline.nic.in` is not `upsc.gov.in`. That guard belongs to links read out of a
  document, not to a portal the record itself supplies.
