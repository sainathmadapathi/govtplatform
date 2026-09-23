# Resources: audit

Audit only. No code changed. Git HEAD: `24974a9`. Working tree clean at audit time.

## Verdict

**Already implemented and complete — missing only Qwen semantic verification.** The resource
model, the per-exam authored data with provenance, the official/unofficial classification, the
server-side link health, the Tavily→findings→human-promote gate, and the Resource Library UI
all exist. The only additive gap — this phase's Qwen role — is verifying that a resource's
evidence actually matches its claimed exam/cycle and type. **Do not rebuild the engine.**

## Answers to the audit questions

1. **Already implemented?** Yes.
2. **Files.** `types.ts` (`ResourceItem`, `ResourceLinkStatus`); `data.ts` (authored
   `resources` per exam + `officialSource` / `communitySource` / `pendingSource` provenance
   builders); `ui.tsx` (`ResourceLibrary` — its own tab and section 8 — `ResourceReaderModal`,
   `ResourceAIAssistant` navigator); `services.ts` (`resourceLiveService`, `verifyResourceLinks`,
   bookmark storage); `app.py` (`/api/resources/verify-links`, `resource_link_health`,
   `live/ssc-notices`, `channel-uploads`, `additions`, and the research pipeline).
3. **Commits.** `04ebb2c`, `16a0da1`, `4758f8b` (link-don't-store), `511c3e6` (own tab),
   `f238a36` (self-refreshing), `41c9abc` (ranked navigator), `874daf1`, `a8d3ba2`, `48cde61`.
4. **Resource types.** `type`: OFFICIAL_PDF, OFFICIAL_PORTAL, SIMPLIFIED_GUIDE, RECOMMENDED_BOOK,
   VIDEO_LECTURE, ONLINE_TOOL. `resourceFormat`: DIRECT_PDF, YOUTUBE_COURSE, YOUTUBE_CHANNEL,
   INTERACTIVE_HANDBOOK, ONLINE_TOOL, OFFICIAL_PORTAL. Real counts: SSC 38, UPSC 32 (with
   provenance), IBPS/APPSC thin.
5. **Exam/cycle scope.** Resources live on `exam.resources` — a per-exam array — so a resource
   is scoped to its exam by construction; the library's filters are derived from that exam's own
   resources (UPSC never shows empty SSC filters). Nothing crosses exams.
6. **Official vs unofficial.** Domain identity via `_classify_trust` (OFFICIAL / TRUSTED_PUBLIC /
   UNVERIFIED) and the resource `type`; `communitySource()` records coaching channels as
   RECOMMENDATION / UNDER_VERIFICATION with an explicit "GovOS does not endorse this and has not
   fact-checked its lessons." Officiality is never inferred from a snippet or a professional look.
7. **Dead/broken links.** `/api/resources/verify-links` (server-side, GET trusted) classifies
   HEALTHY / REDIRECT / BLOCKED / BROKEN / UNREACHABLE, cached in `resource_link_health` (12 h).
   The UI marks anything it cannot reach **amber "open to confirm"**, never red; red is reserved
   for a real HTTP error on GET. A fetch failure is infrastructure, **not** NOT_PUBLISHED.
8. **Provenance.** `ResourceItem.provenance?: DataProvenance` + `linkVerifiedDate`; built by
   `officialSource` / `communitySource` / `pendingSource`.
9. **Can Tavily directly publish a resource?** **No.** Tavily results are stored as
   `research_findings` (PENDING_REVIEW); reaching the library requires a human PROMOTE and a
   second click ("Add to Resource Library" → `resource_additions`), and the entry is labelled
   "VERIFIER-APPROVED FROM LIVE SOURCE RESEARCH". There is no Tavily → verified-resource
   shortcut. (Confirmed in earlier phases: `test_research_facts.py`.)
10. **Genuinely missing.** Only Qwen semantic verification of a resource fact — "does this
    evidence establish that this is a `<type>` resource for `<exam>` `<cycle>`?" — the additive
    step Results, Cut-off and Corrigenda each received.

## Resource content vs resource link (already respected)

A resource URL is not verified content: `linkVerifiedDate` records that the *link* answered
HTTP 200, not that its contents were read; official PDFs are linked, not transcribed; a
login-required portal is linked as official (by domain) without any claim about its gated
contents. The new verifier keeps this: it verifies the resource's *scope/type* against the
evidence given, and a login-gated or unfetchable resource whose content cannot be confirmed
stays NEEDS_REVIEW rather than VERIFIED — never NOT_PUBLISHED.

## Proposed change (minimal, additive)

- Add `claim_from_resource(...)` and `resource_officiality(...)` to `verification/adapters.py`
  — a generic resource → `Claim` adapter (no exam-specific branch) plus a deterministic
  domain-officiality check. A resource runs through the authoritative deterministic gate
  (wrong exam/cycle/no-source rejected first) and then the Qwen check on whether the evidence
  supports the resource's claimed exam/cycle and type. Officiality is deterministic (domain),
  never from the model.
- Add `test_resources_verification.py` — the twelve required cases over the real UPSC notice
  resource.
- Demonstrate live: the real UPSC official-notice resource verified through Qwen, and isolation.
- **No change** to `ResourceItem`, the authored `resources`, the Resource Library UI, or the
  link-health/promote pipeline.

Nothing is published or overwritten; no production record or UI is touched.
