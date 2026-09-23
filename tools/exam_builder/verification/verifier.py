"""The orchestrator: deterministic checks first, then -- only if they pass -- the local Qwen
semantic check, then a deterministic publication decision.

The publication rule is fixed and never keyed on a numeric confidence:

    VERIFIED  ==  deterministic.passed  AND  llm.decision == SUPPORTED

Anything else is NEEDS_REVIEW: a deterministic failure (identity, cycle, span, contradiction),
a CONTRADICTED or INSUFFICIENT decision, or any infrastructure failure (disabled, unreachable,
timeout, malformed). The LLM can only withhold; it can never turn a deterministic failure into
a pass, and an unavailable model is never VERIFIED and never NOT_PUBLISHED.
"""
from __future__ import annotations

from .cache import VerificationCache
from .client import VerificationProvider, get_provider
from .deterministic import run_deterministic
from .llm_verifier import run_llm
from .schemas import (Claim, InfraStatus, VerificationDecision, VerificationResult,
                      Verdict, VERIFIER_VERSION)


def verify(claim: Claim, *, provider: VerificationProvider | None = None,
           cache: VerificationCache | None = None) -> Verdict:
    """Produce a publication verdict for one candidate fact."""
    fp = claim.fingerprint(VERIFIER_VERSION)
    det = run_deterministic(claim)

    # Deterministic failure is authoritative and the model is never consulted -- it cannot
    # see, let alone override, an identity or evidence failure.
    if not det.passed:
        return Verdict(publishable=False, status='NEEDS_REVIEW', deterministic=det, llm=None,
                       infra=InfraStatus.OK, fingerprint=fp,
                       reason='deterministic checks failed: ' + '; '.join(det.reasons))

    provider = provider or get_provider()
    llm = cache.get(fp) if cache else None
    if llm is None:
        llm = run_llm(claim, provider)
        if cache:
            cache.put(fp, llm)

    if llm.infra is not InfraStatus.OK:
        # Infrastructure failure: explicit state, never VERIFIED, never NOT_PUBLISHED.
        return Verdict(publishable=False, status='NEEDS_REVIEW', deterministic=det, llm=llm,
                       infra=llm.infra, fingerprint=fp,
                       reason=f'local LLM verification unavailable ({llm.infra.value}); '
                              f'not published')

    if llm.decision is VerificationDecision.SUPPORTED:
        return Verdict(publishable=True, status='VERIFIED', deterministic=det, llm=llm,
                       infra=InfraStatus.OK, fingerprint=fp,
                       reason='deterministic checks passed and the evidence supports the claim')

    return Verdict(publishable=False, status='NEEDS_REVIEW', deterministic=det, llm=llm,
                   infra=InfraStatus.OK, fingerprint=fp,
                   reason=f'the evidence does not support the claim ({llm.decision.value})')
