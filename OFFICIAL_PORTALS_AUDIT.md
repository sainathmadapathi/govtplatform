# Official Portals & Links: audit

Audit only. No code changed. Git HEAD: `024a82e`. Working tree clean at audit time.

## Verdict

**Partially implemented.** Section 12 renders per-exam `officialLinks`, but the records are thin
(`{title, url, note}` only) — **no provenance, no purpose enum, no per-link officiality or
verification**, and IBPS/APPSC have none. The additive, safe piece this phase asks for is the
**Qwen portal-purpose verifier plus a deterministic officiality check** (not `.gov.in`-only), so a
link's claimed purpose is checked against official evidence and its officiality is decided by
domain — before anything could be treated as VERIFIED. Authoring richer per-exam link records with
provenance is a separate, larger data+type task and is **not** done here; this phase adds the gate
and demonstrates it. **Do not rebuild the type, data, or UI.**

## Answers to the audit questions

- **Already implemented?** Partially — type + UI + some data; no provenance/verification.
- **Exams with records.** SSC 3 (ssc.gov.in, ncbc.nic.in, digilocker.gov.in), UPSC 6 (upsc.gov.in,
  upsconline.nic.in). IBPS/APPSC ×2 have **none**.
- **Exam-scoped?** Yes — `officialLinks` is per-exam.
- **URLs source-backed?** **No** — the inline type has no `provenance` field; links carry only a
  free-text `note`.
- **Officiality deterministic?** Not modelled per link today. It *can* be, by domain — and it must
  not be `.gov.in`-only: IBPS uses `ibps.in`, LIC uses `licindia.in`. The engine's
  `resource_officiality(url, authority_domain)` already checks a host against the authority's own
  domain and handles those non-`.gov.in` cases.
- **Authority identity validated?** Not at the link layer today; `identity.py` (exam + cycle) is
  what a verified link *would* be gated by — added here.
- **Tied to the correct exam/cycle?** Scoped to the exam; no per-link cycle field.
- **Stale vs current links distinguishable?** Not modelled per link.
- **Homepages incorrectly treated as application/download links?** The current notes describe
  purpose in prose but nothing *validates* that a URL's purpose matches the evidence — which is
  exactly the risk this phase names (a homepage becoming "Download Admit Card").
- **Dead vs NOT_PUBLISHED?** The Resource Library's link-health (`/api/resources/verify-links`,
  HEALTHY/REDIRECT/BLOCKED/BROKEN/UNREACHABLE) exists and is reused; a dead link is infrastructure,
  never NOT_PUBLISHED.
- **What is missing?** (a) a verifier that a link's *purpose* is supported by official evidence and
  a deterministic officiality check (added here); (b) richer per-link records with provenance (a
  separate data task, not done here).

## Real evidence available (captured, verbatim, not fabricated)

UPSC's notice ties URLs to purposes in its own words:

- **Application** — *"Applicants are required to apply online by using the website
  https://upsconline.nic.in."* (p.1)
- **Admit card** — *"The e-Admit Card will be made available on the website
  [https://upsconline.nic.in] for downloading by the candidates. No Admit Card will be sent by
  post or Email."* (p.3)

SSC's notices name `ssc.gov.in` as the portal. IBPS (`ibps.in`) and LIC (`licindia.in`) are the
non-`.gov.in` official domains the phase calls out. **No purpose is assumed** — a homepage is not
called an application or download portal unless the evidence says so.

## Proposed change (minimal, additive)

- Add `claim_from_portal(...)` and `portal_officiality(...)` to `verification/adapters.py` — a
  generic portal → `Claim` adapter (no exam-specific branch) that verifies a link's *purpose*
  against the evidence, plus a deterministic domain-officiality check that reuses
  `resource_officiality` (so `ibps.in` / `licindia.in` count as official). Identity/cycle come from
  the exam record, so a wrong-exam or wrong-cycle link is rejected before Qwen; officiality is
  deterministic, never the model's.
- Add `test_portals_verification.py` — the twenty required cases over the real UPSC portal evidence.
- Demonstrate live: a real UPSC portal purpose verified through Qwen, and isolation.
- **No change** to the `officialLinks` type, section 12, or any authored links.

Nothing is published or overwritten; no production record or UI is touched.
