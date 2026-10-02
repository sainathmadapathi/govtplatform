"""The orchestrator: deterministic checks first, then -- only if they pass -- the Claude
semantic check, then a deterministic publication decision.

The publication rule is fixed and never keyed on a numeric confidence:

    VERIFIED  ==  deterministic.passed  AND  claude.decision == SUPPORTED

Anything else is NEEDS_REVIEW: a deterministic failure (identity, cycle, span, contradiction),
a CONTRADICTED or INSUFFICIENT decision, or any infrastructure failure (disabled, CLI missing,
not signed in, busy, timeout, malformed reply). Claude can only withhold; it can never turn a
deterministic failure into a pass, and an unavailable Claude is never VERIFIED and never
NOT_PUBLISHED.
"""
from __future__ import annotations

from .cache import VerificationCache
from tools.claude_cli import get_gateway
from .deterministic import run_deterministic
from .claude_verifier import run_claude
from .schemas import (Claim, InfraStatus, VerificationDecision, VerificationResult,
                      Verdict, VERIFIER_VERSION)


def verify(claim: Claim, *, gateway=None,
           cache: VerificationCache | None = None) -> Verdict:
    """Produce a publication verdict for one candidate fact."""
    fp = claim.fingerprint(VERIFIER_VERSION)
    det = run_deterministic(claim)

    # Deterministic failure is authoritative and Claude is never consulted -- it cannot see, let
    # alone override, an identity or evidence failure.
    if not det.passed:
        return Verdict(publishable=False, status='NEEDS_REVIEW', deterministic=det, claude=None,
                       infra=InfraStatus.OK, fingerprint=fp,
                       reason='deterministic checks failed: ' + '; '.join(det.reasons))

    gateway = gateway or get_gateway()
    verdict = cache.get(fp) if cache else None
    if verdict is None:
        verdict = run_claude(claim, gateway)
        if cache:
            cache.put(fp, verdict)
    claude = verdict

    if claude.infra is not InfraStatus.OK:
        # Infrastructure failure: explicit state, never VERIFIED, never NOT_PUBLISHED.
        return Verdict(publishable=False, status='NEEDS_REVIEW', deterministic=det, claude=claude,
                       infra=claude.infra, fingerprint=fp,
                       reason=f'Claude verification unavailable ({claude.infra.value}); '
                              f'not published')

    if claude.decision is VerificationDecision.SUPPORTED:
        return Verdict(publishable=True, status='VERIFIED', deterministic=det, claude=claude,
                       infra=InfraStatus.OK, fingerprint=fp,
                       reason='deterministic checks passed and the evidence supports the claim')

    return Verdict(publishable=False, status='NEEDS_REVIEW', deterministic=det, claude=claude,
                   infra=InfraStatus.OK, fingerprint=fp,
                   reason=f'the evidence does not support the claim ({claude.decision.value})')
