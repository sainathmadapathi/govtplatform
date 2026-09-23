"""Deterministic verification -- the authoritative checks that run before the LLM.

These reuse the engine's own identity and evidence discipline: `identity.verify` (exam and
cycle, MATCH/AMBIGUOUS/MISMATCH) and verbatim span membership (`normalise_ws`). Nothing here
calls a model. A cross-exam or cross-cycle source fails here and the LLM is never consulted,
so the model can neither see nor override an identity failure.
"""
from __future__ import annotations

from ..identity import ExamIdentity, IdentityVerdict, verify as identity_verify
from ..schema import normalise_ws
from .schemas import Claim, DeterministicResult

_TITLE_BLOCK = 3000


def run_deterministic(claim: Claim) -> DeterministicResult:
    r = DeterministicResult()

    r.source_ok = bool((claim.source_url or '').strip())
    if not r.source_ok:
        r.reasons.append('no source URL')

    span = (claim.evidence_span or '').strip()
    r.span_present = bool(span)
    if not r.span_present:
        r.reasons.append('no evidence span')

    # The span must belong to the fetched source. When no source text was supplied the span
    # cannot be confirmed to come from the document -- a snippet is not evidence by itself.
    if claim.source_text and r.span_present:
        r.span_in_source = normalise_ws(span) in normalise_ws(claim.source_text)
        if not r.span_in_source:
            r.reasons.append('evidence span not found verbatim in the source document')
    elif r.span_present and not claim.source_text:
        r.span_in_source = False
        r.reasons.append('no source document supplied to confirm the evidence span')

    r.value_present = (not claim.requires_value) or bool(str(claim.value or '').strip())
    if not r.value_present:
        r.reasons.append('the claim requires a value and none is present')

    # Exam and cycle identity, from the source text (or the span if that is all there is).
    text = claim.source_text or claim.evidence_span or ''
    target = ExamIdentity(exam_id=claim.exam_id,
                          query=claim.official_name or claim.exam_id,
                          official_name=claim.official_name,
                          year=claim.cycle, authority_name=claim.authority)
    check = identity_verify(text, target)
    if check.verdict is IdentityVerdict.MISMATCH:
        r.identity_ok = False
        r.cross_exam_ok = False
        r.reasons.append('identity mismatch: ' + (check.reasons[0] if check.reasons
                                                  else 'the source belongs to another exam/cycle'))
    elif check.verdict is IdentityVerdict.MATCH:
        r.identity_ok = True
        r.cross_exam_ok = True
    else:  # AMBIGUOUS -- accept only if the source's own title block names this exam
        opening = identity_verify(text[:_TITLE_BLOCK], target)
        r.identity_ok = opening.verdict is IdentityVerdict.MATCH or bool(opening.matched)
        r.cross_exam_ok = r.identity_ok
        if not r.identity_ok:
            r.reasons.append('the source mentions this exam among others but does not '
                             'identify itself as belonging to it')

    # Cycle: identity already refuses a wrong year for the same exam. Where a cycle is claimed
    # and the source names a *different* four-digit year beside the exam with none matching,
    # identity returns MISMATCH above; here we only record the positive when identity held.
    r.cycle_ok = r.identity_ok and (not claim.cycle or _cycle_present(text, claim.cycle))
    if claim.cycle and not r.cycle_ok:
        r.reasons.append(f'the source does not establish cycle {claim.cycle}')

    return r


def _cycle_present(text: str, cycle: str) -> bool:
    """A conservative positive: the claimed cycle appears in the source. Identity has already
    refused a source that names a conflicting year, so this only confirms the match."""
    c = (cycle or '').strip()
    if not c:
        return True
    return c in text
