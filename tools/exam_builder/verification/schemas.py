"""The strict, machine-validated contract for a verification. No free-form model text leaks
past `VerificationResult.from_model_json`, which rejects anything malformed."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

VERIFIER_VERSION = 'gov-verify-1'


class VerificationDecision(str, Enum):
    """The LLM's semantic decision about whether evidence supports the claim."""

    SUPPORTED = 'SUPPORTED'
    CONTRADICTED = 'CONTRADICTED'
    INSUFFICIENT = 'INSUFFICIENT'
    ERROR = 'ERROR'          # not a factual decision -- see `infra`


class InfraStatus(str, Enum):
    """What happened to the model call. Deliberately NOT a factual state: an infrastructure
    failure is never NOT_PUBLISHED and never VERIFIED."""

    OK = 'OK'
    LLM_DISABLED = 'LLM_DISABLED'
    LLM_UNAVAILABLE = 'LLM_UNAVAILABLE'
    LLM_TIMEOUT = 'LLM_TIMEOUT'
    LLM_ERROR = 'LLM_ERROR'
    LLM_INVALID_RESPONSE = 'LLM_INVALID_RESPONSE'


@dataclass
class Claim:
    """One extracted candidate fact, with the evidence and the identity it must be checked
    against. Universal: no field names an authority or exam type; everything is data."""

    exam_id: str
    field: str
    value: str
    evidence_span: str
    source_url: str = ''
    cycle: str = ''
    source_title: str = ''
    authority: str = ''
    official_name: str = ''
    #: The fetched official document text, used to confirm the span belongs to the source and
    #: to check exam/cycle identity. When empty, span membership cannot be confirmed.
    source_text: str = ''
    #: Some claims carry no scalar value (e.g. "this heading begins a syllabus section").
    requires_value: bool = True

    def fingerprint(self, verifier_version: str = VERIFIER_VERSION) -> str:
        """A stable id for (claim, evidence, source identity, verifier version). New evidence
        or a new verifier version yields a new fingerprint, so cache never validates stale
        evidence."""
        parts = [self.exam_id, self.cycle, self.field, self.value.strip(),
                 ' '.join(self.evidence_span.split()), self.source_url, verifier_version]
        return hashlib.sha256('␟'.join(parts).encode('utf-8')).hexdigest()


@dataclass
class DeterministicResult:
    """The Python checks that run before the LLM and are authoritative."""

    source_ok: bool = False
    span_present: bool = False
    span_in_source: bool = False
    identity_ok: bool = False
    cycle_ok: bool = False
    value_present: bool = False
    cross_exam_ok: bool = False
    reasons: list = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return (self.source_ok and self.span_present and self.span_in_source
                and self.identity_ok and self.cycle_ok and self.value_present
                and self.cross_exam_ok)


@dataclass
class VerificationResult:
    """The LLM verifier's structured, validated output."""

    decision: VerificationDecision
    identity_supported: bool
    evidence_supported: bool
    claim_supported: bool
    reason: str
    model: str
    verifier_version: str = VERIFIER_VERSION
    infra: InfraStatus = InfraStatus.OK

    @classmethod
    def error(cls, infra: InfraStatus, reason: str, model: str = '') -> 'VerificationResult':
        """A non-factual failure. Decision is ERROR and can never be read as SUPPORTED."""
        return cls(decision=VerificationDecision.ERROR, identity_supported=False,
                   evidence_supported=False, claim_supported=False, reason=reason,
                   model=model, infra=infra)

    @classmethod
    def from_model_json(cls, raw: Any, *, model: str) -> 'VerificationResult':
        """Parse and *validate* the model's JSON. Anything malformed is LLM_INVALID_RESPONSE
        -- never a publishable decision."""
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (ValueError, TypeError):
                return cls.error(InfraStatus.LLM_INVALID_RESPONSE,
                                 'model output was not valid JSON', model)
        if not isinstance(raw, dict):
            return cls.error(InfraStatus.LLM_INVALID_RESPONSE,
                             'model output was not a JSON object', model)
        dec = raw.get('decision')
        if dec not in (d.value for d in VerificationDecision) or dec == 'ERROR':
            return cls.error(InfraStatus.LLM_INVALID_RESPONSE,
                             f'missing or invalid decision: {dec!r}', model)
        for key in ('identity_supported', 'evidence_supported', 'claim_supported'):
            if not isinstance(raw.get(key), bool):
                return cls.error(InfraStatus.LLM_INVALID_RESPONSE,
                                 f'field {key} must be a boolean', model)
        reason = raw.get('reason')
        if not isinstance(reason, str):
            reason = ''
        # A SUPPORTED decision whose own booleans do not agree is internally inconsistent and
        # is refused rather than trusted -- the model does not get to both support and not.
        if dec == 'SUPPORTED' and not (raw['evidence_supported'] and raw['claim_supported']):
            return cls.error(InfraStatus.LLM_INVALID_RESPONSE,
                             'SUPPORTED but evidence/claim booleans disagree', model)
        return cls(decision=VerificationDecision(dec),
                   identity_supported=raw['identity_supported'],
                   evidence_supported=raw['evidence_supported'],
                   claim_supported=raw['claim_supported'], reason=reason[:600], model=model)

    def as_dict(self) -> dict:
        return {'decision': self.decision.value, 'identitySupported': self.identity_supported,
                'evidenceSupported': self.evidence_supported,
                'claimSupported': self.claim_supported, 'reason': self.reason,
                'model': self.model, 'verifierVersion': self.verifier_version,
                'infra': self.infra.value}


@dataclass
class Verdict:
    """The publication decision. `publishable` is VERIFIED; otherwise NEEDS_REVIEW.

    The rule is deterministic and never keyed on a numeric LLM confidence:
    VERIFIED  ==  deterministic.passed AND llm.decision == SUPPORTED.
    Everything else -- a deterministic failure, a CONTRADICTED/INSUFFICIENT decision, or any
    infrastructure failure -- is NEEDS_REVIEW.
    """

    publishable: bool
    status: str                        # 'VERIFIED' | 'NEEDS_REVIEW'
    deterministic: DeterministicResult
    llm: Optional[VerificationResult]
    infra: InfraStatus
    reason: str
    fingerprint: str = ''

    def as_dict(self) -> dict:
        return {'status': self.status, 'publishable': self.publishable, 'reason': self.reason,
                'infra': self.infra.value, 'fingerprint': self.fingerprint,
                'deterministic': {
                    'passed': self.deterministic.passed,
                    'sourceOk': self.deterministic.source_ok,
                    'spanPresent': self.deterministic.span_present,
                    'spanInSource': self.deterministic.span_in_source,
                    'identityOk': self.deterministic.identity_ok,
                    'cycleOk': self.deterministic.cycle_ok,
                    'valuePresent': self.deterministic.value_present,
                    'crossExamOk': self.deterministic.cross_exam_ok,
                    'reasons': self.deterministic.reasons},
                'llm': self.llm.as_dict() if self.llm else None}
