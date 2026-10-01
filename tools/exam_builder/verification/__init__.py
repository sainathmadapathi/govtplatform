"""Claude semantic verification layer for GovOS candidate facts.

Deterministic checks run first and are authoritative; the Claude CLI (through the single gateway in
`tools/claude_cli`) then semantically verifies whether the supplied evidence supports the supplied
claim. Claude can only withhold (move a fact to NEEDS_REVIEW) -- it never fabricates VERIFIED, and an
unavailable or malformed Claude is an infrastructure result, never a factual one. See
CLAUDE_CLI_INTEGRATION.md.
"""
from tools.claude_cli.schemas import InfraStatus

from .schemas import (Claim, DeterministicResult, VerificationDecision, VerificationResult, Verdict,
                      VERIFIER_VERSION)
from .verifier import verify

__all__ = ['Claim', 'DeterministicResult', 'InfraStatus', 'VerificationDecision',
           'VerificationResult', 'Verdict', 'VERIFIER_VERSION', 'verify']
