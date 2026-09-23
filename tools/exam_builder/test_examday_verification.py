"""The verification layer applied to EXAM-DAY instructions: the ten required cases over real
LIC AAO notification clauses (late-reporting and identity-proof rules). The LLM is stubbed for
determinism; the live-model proof is the exam-day replay.

Additive only -- no exam-day model, section, or record is changed, and no exam-day rule is
authored or published. This verifies that an instruction, routed through the deterministic +
Qwen gate, is bound to the exact exam/cycle and its clause, and that a rule is never copied
between exams.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_exam_day
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured exam-day evidence: LIC AAO notification ------------------------------
LIC_SRC = ('Life Insurance Corporation of India — Recruitment of Assistant Administrative '
           'Officers (AAO), 2025. Candidates reporting late i.e. after the reporting time '
           'specified on the call letter for examination will not be permitted to take the '
           'examination. Photo Identity proof (as specified) in original bearing the same name '
           'as it appears on the call letter is required.')
LATE_CLAUSE = ('Candidates reporting late i.e. after the reporting time specified on the call '
               'letter for examination will not be permitted to take the examination.')
LIC_CTX = dict(exam_id='exam-lic-aao-2027',
               official_name='Recruitment of Assistant Administrative Officers',
               authority='Life Insurance Corporation of India', cycle='2025')


def lic_instruction(category='TIMING',
                    text='Late reporting after the time on the call letter is not permitted.',
                    span=LATE_CLAUSE):
    return {'category': category, 'text': text, 'evidenceSpan': span,
            'sourceUrl': 'https://licindia.in/aao', 'sourceTitle': 'AAO notification'}


class _Stub(VerificationProvider):
    def __init__(self, payload=None, raises=None):
        self.cfg = {'model': 'stub'}
        self.payload, self.raises = payload, raises

    def is_enabled(self):
        return True

    def health(self):
        return {'enabled': True, 'reachable': True}

    def complete(self, messages, *, max_tokens=320):
        if self.raises:
            raise self.raises
        return self.payload


def _json(decision, ident=True, ev=True, claim=True):
    return json.dumps({'decision': decision, 'identity_supported': ident,
                       'evidence_supported': ev, 'claim_supported': claim, 'reason': 'stub'})


POISON = _Stub(raises=AssertionError('LLM must not be called after a deterministic failure'))


class TestExamDayVerification(unittest.TestCase):

    def test_1_real_supported_instruction(self):
        c = claim_from_exam_day(lic_instruction(), source_text=LIC_SRC, **LIC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_2_contradictory_instruction(self):
        # The clause forbids late reporting; a claim that late candidates ARE permitted is contradicted.
        c = claim_from_exam_day(lic_instruction(text='Late candidates are permitted to sit.'),
                                source_text=LIC_SRC, **LIC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_3_insufficient_evidence(self):
        c = claim_from_exam_day(lic_instruction(), source_text=LIC_SRC, **LIC_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_4_wrong_exam_rejected_before_llm(self):
        c = claim_from_exam_day(lic_instruction(), source_text=LIC_SRC,
                                exam_id='exam-ssc-cgl-2026',
                                official_name='Combined Graduate Level Examination',
                                authority='Staff Selection Commission', cycle='2026')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_5_wrong_cycle_rejected_before_llm(self):
        src2024 = ('Life Insurance Corporation of India — Recruitment of Assistant '
                   'Administrative Officers (AAO), 2024. Candidates reporting late will not be '
                   'permitted.')
        c = claim_from_exam_day(lic_instruction(span='Candidates reporting late will not be permitted.'),
                                source_text=src2024, **dict(LIC_CTX, cycle='2025'))
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    def test_6_wrong_stage_is_semantic(self):
        # A Prelims-scoped claim verified against a general clause: the stage travels in the
        # field; deterministic passes, and the model judges scope.
        c = claim_from_exam_day(lic_instruction(), source_text=LIC_SRC, stage='Preliminary', **LIC_CTX)
        self.assertIn('preliminary', c.field)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)

    def test_7_llm_unavailable_never_verified(self):
        c = claim_from_exam_day(lic_instruction(), source_text=LIC_SRC, **LIC_CTX)
        v = verify(c, provider=_Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'down')))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)

    def test_8_malformed_llm_never_verified(self):
        c = claim_from_exam_day(lic_instruction(), source_text=LIC_SRC, **LIC_CTX)
        v = verify(c, provider=_Stub('not json'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_9_cross_exam_isolation(self):
        # SSC evidence can never verify a LIC instruction.
        ssc_src = ('Staff Selection Commission — Combined Graduate Level Examination, 2026. '
                   'Candidates must carry a printed admission certificate.')
        c = claim_from_exam_day(lic_instruction(text='Candidates must carry a printed admission certificate.',
                                                span='Candidates must carry a printed admission certificate.'),
                                source_text=ssc_src, **LIC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_10_missing_source_or_evidence(self):
        # No source document to confirm the clause -> deterministic cannot verify -> NEEDS_REVIEW,
        # never VERIFIED and never NOT_PUBLISHED, and the model is not asked to fill the gap.
        c = claim_from_exam_day(lic_instruction(), **LIC_CTX)   # no source_text
        c.source_text = ''
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.llm)


if __name__ == '__main__':
    unittest.main(verbosity=2)
