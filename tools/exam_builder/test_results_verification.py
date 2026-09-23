"""The verification layer applied to RESULT facts: the eight required cases, over real
captured result evidence (UPSC's exam page, IBPS's notification). The LLM is stubbed so these
are deterministic and fast; the live-model proof is the results replay script.

This adds no production data and touches no completed phase -- it verifies that a published
result declaration, routed through the deterministic + Qwen gate, behaves correctly.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_result
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured result evidence -------------------------------------------------------
UPSC_SRC = ('Union Public Service Commission. Civil Services (Preliminary) Examination, 2026. '
            'Written Result WR-CSP-2026-RollList-Engl-150626.pdf 15/06/2026.')
UPSC_ROW = {
    'examId': 'exam-upsc-cse-2026', 'kind': 'WRITTEN_RESULT', 'label': 'Written Result',
    'cycle': '2026', 'stageLabel': 'Preliminary', 'declaredAt': '2026-06-15',
    'provenance': {'officialUrl': 'https://upsc.gov.in/examinations',
                   'documentTitle': 'Civil Services (Preliminary) Examination, 2026',
                   'excerptText': 'Written Result WR-CSP-2026-RollList-Engl-150626.pdf 15/06/2026'},
}
UPSC_CTX = dict(official_name='Civil Services (Preliminary) Examination',
                authority='Union Public Service Commission')

IBPS_SRC = ('Institute of Banking Personnel Selection. Common Recruitment Process for '
            'Probationary Officers (CRP PO/MT-XVI), 2026. Result of Online examination '
            'Preliminary September, 2026.')
IBPS_ROW = {
    'examId': 'exam-ibps-po-2026', 'kind': 'SCHEDULED', 'label': 'Result', 'cycle': '2026',
    'stageLabel': 'Preliminary', 'expectedAt': '2026-09-01',
    'provenance': {'officialUrl': 'https://www.ibps.in/notification',
                   'documentTitle': 'CRP PO/MT-XVI notification',
                   'excerptText': 'Result of Online examination Preliminary September, 2026'},
}
IBPS_CTX = dict(official_name='Common Recruitment Process for Probationary Officers',
                authority='Institute of Banking Personnel Selection')


class _Stub(VerificationProvider):
    def __init__(self, payload=None, raises=None):
        self.cfg = {'model': 'stub'}
        self.payload, self.raises, self.called = payload, raises, False

    def is_enabled(self):
        return True

    def health(self):
        return {'enabled': True, 'reachable': True}

    def complete(self, messages, *, max_tokens=320):
        self.called = True
        if self.raises:
            raise self.raises
        return self.payload


def _json(decision, ident=True, ev=True, claim=True):
    return json.dumps({'decision': decision, 'identity_supported': ident,
                       'evidence_supported': ev, 'claim_supported': claim, 'reason': 'stub'})


SUPPORTED = lambda: _Stub(_json('SUPPORTED'))
POISON = _Stub(raises=AssertionError('LLM must not be called after a deterministic failure'))


class TestResultVerification(unittest.TestCase):

    def test_1_correct_real_result_supported(self):
        c = claim_from_result(UPSC_ROW, source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_2_contradictory_result_evidence(self):
        c = claim_from_result(UPSC_ROW, source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_3_insufficient_result_evidence(self):
        c = claim_from_result(IBPS_ROW, source_text=IBPS_SRC, **IBPS_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)   # deterministic ok; the LLM withheld

    def test_4_wrong_exam_rejected_before_llm(self):
        # UPSC evidence, but the claim says the result is SSC CGL's.
        row = dict(UPSC_ROW, examId='exam-ssc-cgl-2026')
        c = claim_from_result(row, source_text=UPSC_SRC,
                              official_name='Combined Graduate Level Examination',
                              authority='Staff Selection Commission')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_5_wrong_cycle_rejected_before_llm(self):
        src = ('Union Public Service Commission. Civil Services (Preliminary) Examination, '
               '2025. Written Result WR-CSP-2025.pdf 12/06/2025.')
        row = dict(UPSC_ROW, cycle='2026',
                   provenance=dict(UPSC_ROW['provenance'],
                                   excerptText='Written Result WR-CSP-2025.pdf 12/06/2025'),
                   declaredAt='2025-06-12')
        c = claim_from_result(row, source_text=src, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.identity_ok)
        self.assertIsNone(v.llm)

    def test_6_llm_unavailable_never_verified(self):
        c = claim_from_result(UPSC_ROW, source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'down')))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)
        self.assertIsNot(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_7_malformed_llm_never_verified(self):
        c = claim_from_result(UPSC_ROW, source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub('not json {'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_8_cross_exam_isolation(self):
        # An IBPS result document can never verify a UPSC result claim.
        row = dict(UPSC_ROW)  # UPSC claim
        c = claim_from_result(row, source_text=IBPS_SRC, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_adapter_scheduled_row_has_value_and_field(self):
        c = claim_from_result(IBPS_ROW, source_text=IBPS_SRC, **IBPS_CTX)
        self.assertEqual(c.field, 'result:scheduled')
        self.assertEqual(c.value, '2026-09-01')
        self.assertIn('September', c.evidence_span)


if __name__ == '__main__':
    unittest.main(verbosity=2)
