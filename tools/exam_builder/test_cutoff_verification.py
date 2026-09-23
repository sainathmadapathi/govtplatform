"""The verification layer applied to CUT-OFF facts: the thirteen required cases over the real
UPSC CSE 2025 minimum-qualifying-marks sheet (authored in the register with a verbatim excerpt
and the official PDF URL). The LLM is stubbed for determinism; the live-model proof is the
cut-off replay script.

Additive only: no cut-off model, UI, or authored `cutoffsHistory` is changed. This verifies
that a published cut-off, routed through the deterministic + Qwen gate, behaves correctly and
stays isolated by exam and cycle.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_cutoff
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured cut-off evidence: UPSC CSE 2025 official sheet ------------------------
UPSC_2025_EXCERPT = ('CS(Prelim)* 92.66 (General) 89.34 (EWS) 92.00 (OBC) 84.00 (SC) '
                     '82.66 (ST) … CS(Main)# 739 706 717 700 694 … CS(Final) 963 926 931 '
                     '905 902. *Cut off marks on the basis of GS Paper-I only. GS Paper-II '
                     'is of qualifying nature with 33% marks.')
UPSC_2025_TITLE = ('UPSC — Civil Services Examination, 2025: minimum qualifying marks '
                   '(official sheet)')
UPSC_2025_URL = ('https://www.upsc.gov.in/sites/default/files/'
                 'CSE_2025_Cut-OffMks_Eng_09032026.pdf')


def upsc_entry(category='General', tier1=92.66, tier2=739, year=2025):
    return {'year': year, 'category': category, 'tier1Cutoff': tier1, 'tier2Cutoff': tier2,
            'postsEligible': 'Final cut-off 963 / 2025',
            'provenance': {'documentTitle': UPSC_2025_TITLE, 'officialUrl': UPSC_2025_URL,
                           'excerptText': UPSC_2025_EXCERPT}}


UPSC_CTX = dict(exam_id='exam-upsc-cse-2026',
                official_name='Civil Services (Preliminary) Examination',
                authority='Union Public Service Commission')


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


class TestCutoffVerification(unittest.TestCase):

    def test_1_valid_cutoff_matching_evidence(self):
        c = claim_from_cutoff(upsc_entry(), **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.deterministic.passed)
        self.assertIn('92.66', c.evidence_span)

    def test_2_valid_cutoff_qwen_supported_verified(self):
        c = claim_from_cutoff(upsc_entry(), **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_3_contradictory_cutoff_evidence(self):
        c = claim_from_cutoff(upsc_entry(), **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_4_insufficient_cutoff_evidence(self):
        c = claim_from_cutoff(upsc_entry(), **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)

    def test_5_wrong_exam_rejected_before_llm(self):
        # UPSC sheet, but the claim says it is SSC CGL's cut-off.
        c = claim_from_cutoff(upsc_entry(), exam_id='exam-ssc-cgl-2026',
                              official_name='Combined Graduate Level Examination',
                              authority='Staff Selection Commission')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_6_wrong_cycle_rejected_before_llm(self):
        # The 2025 sheet, but the claim asserts cycle 2026.
        c = claim_from_cutoff(upsc_entry(year=2026), **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    def test_7_wrong_stage_is_semantic_needs_review(self):
        # Claim: this is a Mains cut-off of 92.66. 92.66 is a Prelim mark; the model, given
        # the sheet, must not support a Mains reading. Scope correctness is semantic.
        c = claim_from_cutoff(upsc_entry(), tier='mains', **UPSC_CTX)
        # value for tier='mains' is 739; re-point the claim's value to a prelim mark to model
        # a wrong-stage assertion, then the model contradicts.
        c.value = '92.66'
        c.field = 'cutoff:mains:General'
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)     # deterministic can't tell; Qwen does

    def test_8_wrong_category_scope_is_semantic_needs_review(self):
        # Claim: OBC prelim cut-off is 92.66. 92.66 is General; OBC is 92.00. The value is in
        # the sheet, so only the model catches the wrong category.
        entry = upsc_entry(category='OBC', tier1=92.66)
        c = claim_from_cutoff(entry, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_9_llm_unavailable_never_verified(self):
        c = claim_from_cutoff(upsc_entry(), **UPSC_CTX)
        v = verify(c, provider=_Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'down')))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)

    def test_10_malformed_llm_never_verified(self):
        c = claim_from_cutoff(upsc_entry(), **UPSC_CTX)
        v = verify(c, provider=_Stub('{not valid json'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_11_historical_cutoff_isolated_from_current_cycle(self):
        # A 2025 cut-off verifies as a 2025 fact; the same evidence cannot verify a 2026 claim.
        ok = verify(claim_from_cutoff(upsc_entry(year=2025), **UPSC_CTX),
                    provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(ok.deterministic.cycle_ok)
        bad = verify(claim_from_cutoff(upsc_entry(year=2026), **UPSC_CTX), provider=POISON)
        self.assertFalse(bad.deterministic.cycle_ok)
        self.assertIsNone(bad.llm)

    def test_12_cross_exam_isolation(self):
        ssc_src = ('Staff Selection Commission. Combined Graduate Level Examination, 2024. '
                   'Category-wise cut-off marks: UR 145.50, OBC 140.25.')
        entry = {'year': 2024, 'category': 'UR', 'tier1Cutoff': 145.50,
                 'provenance': {'documentTitle': 'SSC CGL 2024 cut-off',
                                'officialUrl': 'https://ssc.gov.in/c',
                                'excerptText': 'UR 145.50, OBC 140.25.'}}
        # A UPSC claim can never be verified by the SSC source.
        c = claim_from_cutoff(entry, exam_id='exam-upsc-cse-2026',
                              official_name='Civil Services (Preliminary) Examination',
                              authority='Union Public Service Commission', source_text=ssc_src)
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_13_no_fallback_from_missing_cutoff(self):
        # An exam with no cut-off evidence produces a claim with no source text -> the span
        # cannot be confirmed and it is NEEDS_REVIEW; nothing is borrowed from another exam.
        empty = {'year': 2026, 'category': 'General', 'tier1Cutoff': None,
                 'provenance': {}}
        c = claim_from_cutoff(empty, exam_id='exam-appsc-group1-2026',
                              official_name='APPSC Group-I Services Examination',
                              authority='Andhra Pradesh Public Service Commission')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertIsNone(v.llm)                    # never reaches the model
        self.assertNotEqual(v.status, 'VERIFIED')


if __name__ == '__main__':
    unittest.main(verbosity=2)
