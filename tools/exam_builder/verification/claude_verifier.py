"""Run one semantic verification through the Claude gateway and return a strictly validated result.

Every failure mode -- disabled, CLI missing, not signed in, busy, timeout, malformed reply, wrong
shape -- becomes a `VerificationResult.error(...)` carrying the gateway's infrastructure status.
None of them can be read as SUPPORTED, so Claude can never publish by failing.
"""
from __future__ import annotations

from tools.claude_cli import Operation, get_gateway

from .schemas import Claim, ENGINE, VerificationResult


def claim_payload(claim: Claim) -> dict:
    """The schema fields of one VERIFY_CLAIM call. Only what the judgement needs: the claim, the
    source's public identity and the quoted evidence -- never the whole source text."""
    return {
        'exam': claim.official_name or claim.exam_id, 'cycle': claim.cycle, 'field': claim.field,
        'value': claim.value, 'source_title': claim.source_title, 'source_url': claim.source_url,
        'authority': claim.authority, 'evidence': claim.evidence_span.strip(),
    }


def run_claude(claim: Claim, gateway=None) -> VerificationResult:
    gateway = gateway or get_gateway()
    result = gateway.run(Operation.VERIFY_CLAIM, claim_payload(claim))
    if not result.ok:
        return VerificationResult.error(result.status, result.message, ENGINE)
    return VerificationResult.from_claude_output(result.output, engine=ENGINE)
