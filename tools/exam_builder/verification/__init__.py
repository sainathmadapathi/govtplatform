"""Local-LLM semantic verification layer for GovOS candidate facts.

Deterministic checks run first and are authoritative; a local Qwen model then semantically
verifies whether the supplied evidence supports the supplied claim. The LLM can only withhold
(move a fact to NEEDS_REVIEW) -- it never fabricates VERIFIED, and an unavailable or malformed
model is an infrastructure result, never a factual one. See LLM_VERIFICATION_AUDIT.md.
"""
from .schemas import (Claim, DeterministicResult, InfraStatus, VerificationDecision,
                      VerificationResult, Verdict, VERIFIER_VERSION)
from .verifier import verify

__all__ = ['Claim', 'DeterministicResult', 'InfraStatus', 'VerificationDecision',
           'VerificationResult', 'Verdict', 'VERIFIER_VERSION', 'verify']
