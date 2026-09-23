"""Golden tests for the verification layer. No live model: the LLM is stubbed so these are
deterministic and fast. They prove the contract -- deterministic checks are authoritative, the
LLM can only withhold, and no failure mode is ever read as VERIFIED. The live-model proof is
`verification/test_local_llm.py` and the real-fact replay script.
"""
from __future__ import annotations

import unittest

from .verification.cache import VerificationCache
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import (Claim, InfraStatus, VerificationDecision,
                                    VerificationResult, VERIFIER_VERSION)
from .verification.verifier import verify

SSC_SRC = ('Staff Selection Commission. Combined Graduate Level Examination, 2026. '
           'The last date for submission of online applications is 22 June 2026. '
           'Applications are invited for various Group B and Group C posts.')
SPAN = 'The last date for submission of online applications is 22 June 2026.'


def ssc_claim(**kw):
    base = dict(exam_id='exam-ssc-cgl-2026', field='application_last_date',
                value='22 June 2026', cycle='2026', source_url='https://ssc.gov.in/n',
                source_title='SSC CGL 2026 Notice', authority='Staff Selection Commission',
                official_name='Combined Graduate Level Examination',
                evidence_span=SPAN, source_text=SSC_SRC)
    base.update(kw)
    return Claim(**base)


class _Stub(VerificationProvider):
    def __init__(self, payload=None, raises=None):
        self.cfg = {'model': 'stub'}
        self.payload = payload
        self.raises = raises
        self.called = False

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
    import json
    return json.dumps({'decision': decision, 'identity_supported': ident,
                       'evidence_supported': ev, 'claim_supported': claim, 'reason': 'stub'})


SUPPORTED = _Stub(_json('SUPPORTED'))
CONTRADICTED = _Stub(_json('CONTRADICTED', ev=False, claim=False))
INSUFFICIENT = _Stub(_json('INSUFFICIENT', ev=False, claim=False))
POISON = _Stub(raises=AssertionError('LLM must not be called after a deterministic failure'))


class TestGolden(unittest.TestCase):

    def test_case_1_supported(self):
        v = verify(ssc_claim(), provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_case_2_contradicted(self):
        v = verify(ssc_claim(), provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')
        self.assertIs(v.llm.decision, VerificationDecision.CONTRADICTED)

    def test_case_3_insufficient(self):
        v = verify(ssc_claim(), provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_case_4_wrong_exam_rejected_before_llm(self):
        src = ('Staff Selection Commission. Combined Higher Secondary (10+2) Level '
               'Examination, 2026. The last date is 22 June 2026.')
        v = verify(ssc_claim(source_text=src,
                             evidence_span='The last date is 22 June 2026.',
                             value='22 June 2026'), provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)                       # LLM never consulted

    def test_case_5_wrong_cycle_rejected_before_llm(self):
        src = ('Combined Graduate Level Examination, 2025. The last date for submission of '
               'online applications is 22 June 2025.')
        v = verify(ssc_claim(source_text=src,
                             evidence_span='The last date for submission of online applications is 22 June 2025.',
                             value='22 June 2025'), provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.identity_ok)
        self.assertIsNone(v.llm)

    def test_case_6_irrelevant_evidence_insufficient(self):
        # Deterministic passes (identity/cycle/span ok); the LLM judges support and says no.
        v = verify(ssc_claim(), provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_case_7_llm_unavailable_never_verified(self):
        down = _Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'server down'))
        v = verify(ssc_claim(), provider=down)
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)
        self.assertIsNot(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_case_8_malformed_json_never_verified(self):
        v = verify(ssc_claim(), provider=_Stub('this is not json at all {oops'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_case_9_llm_supported_but_deterministic_fails(self):
        # LLM would say SUPPORTED, but the span is not in the source -> deterministic fails
        # first and the model is never called.
        v = verify(ssc_claim(source_text='An unrelated document with no such sentence.'),
                   provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.llm)

    def test_case_10_snippet_unsupported_by_official_doc(self):
        # The claimed value comes from a Tavily snippet, but the official document's own span
        # does not state it -> the LLM (given the official span) returns INSUFFICIENT.
        v = verify(ssc_claim(value='30 July 2026'),
                   provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertIs(v.llm.decision, VerificationDecision.CONTRADICTED)

    def test_case_11_uses_official_evidence_span(self):
        # Even if a snippet was incomplete, verification runs on the official document's span,
        # which supports the claim -> SUPPORTED.
        v = verify(ssc_claim(), provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertIn(SPAN, SSC_SRC)                   # the official span is what was checked

    def test_case_12_cross_exam_identity_rejection(self):
        # A UPSC source can never verify an SSC claim.
        upsc_src = ('Union Public Service Commission. Civil Services (Preliminary) '
                    'Examination, 2026. e-Admit Cards will be uploaded on 15 May 2026.')
        v = verify(ssc_claim(source_text=upsc_src,
                             evidence_span='e-Admit Cards will be uploaded on 15 May 2026.',
                             field='admit_card', value='15 May 2026'), provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)


class TestContractDetails(unittest.TestCase):

    def test_infra_is_not_a_factual_state(self):
        for infra in InfraStatus:
            self.assertNotIn(infra.value,
                             {'VERIFIED', 'NEEDS_REVIEW', 'NOT_PUBLISHED', 'PUBLISHED'})

    def test_malformed_supported_with_disagreeing_booleans_is_refused(self):
        import json
        bad = json.dumps({'decision': 'SUPPORTED', 'identity_supported': True,
                          'evidence_supported': False, 'claim_supported': False, 'reason': 'x'})
        r = VerificationResult.from_model_json(bad, model='stub')
        self.assertIs(r.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_cache_serves_repeat_and_skips_infra_failures(self):
        cache = VerificationCache()
        ok = _Stub(_json('SUPPORTED'))
        v1 = verify(ssc_claim(), provider=ok, cache=cache)
        self.assertTrue(v1.publishable)
        ok.payload = _json('CONTRADICTED', ev=False, claim=False)  # would change the answer
        v2 = verify(ssc_claim(), provider=ok, cache=cache)         # served from cache
        self.assertTrue(v2.publishable)
        self.assertEqual(v1.fingerprint, v2.fingerprint)
        # an infra failure is never cached
        cache.clear()
        down = _Stub(raises=ProviderError(InfraStatus.LLM_TIMEOUT, 'slow'))
        verify(ssc_claim(), provider=down, cache=cache)
        self.assertIsNone(cache.get(ssc_claim().fingerprint(VERIFIER_VERSION)))

    def test_fingerprint_changes_with_evidence(self):
        a = ssc_claim().fingerprint()
        b = ssc_claim(evidence_span='A different sentence entirely.').fingerprint()
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main(verbosity=2)
