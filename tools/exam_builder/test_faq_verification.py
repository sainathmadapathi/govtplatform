"""The verification layer applied to FAQ / official-clause facts: the sixteen required cases over
real UPSC CSE 2026 FAQ clauses (the age band and the fee, both cited verbatim in the record's
provenance). The LLM is stubbed for determinism; the live-model proof is the FAQ replay.

Additive only -- no FAQ model, section 11, or authored `faqs` is changed. This verifies that a
FAQ's answer is supported by its cited official clause, bound to the exact exam/cycle, and that
another exam's or cycle's clause can never verify it.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_faq
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured FAQ clauses: UPSC CSE 2026 notice ------------------------------------
AGE_EXCERPT = ('A candidate must have attained the age of 21 years and must not have attained '
               'the age of 32 years on the 1st of August, 2026 i.e., the candidate must have '
               'been born not earlier than 2nd August, 1994 and not later than 1st August, 2005.')
FEE_EXCERPT = ('All the candidates (Except Female/SC/ST/Persons with Benchmark Disability '
               'Candidates who are exempted from payment of fee) are required to pay fee of '
               'Rs. 100/-. Candidates admitted to the Civil Services (Main) Examination, 2026 '
               'will be required to pay a further fee of Rs. 200/-.')
UPSC_TITLE = 'UPSC — Civil Services (Preliminary) Examination, 2026 notice'
AGE_SRC = f'{UPSC_TITLE}. Section II Age Limits. {AGE_EXCERPT}'
FEE_SRC = f'{UPSC_TITLE}. Section FEE (para 4). {FEE_EXCERPT}'

UPSC_CTX = dict(exam_id='exam-upsc-cse-2026',
                official_name='Civil Services (Preliminary) Examination',
                authority='Union Public Service Commission', cycle='2026')


def age_faq(answer='The age limit is 21 to 32 years on 1 August 2026 (born 2 Aug 1994 to 1 Aug 2005).'):
    return {'question': 'What are the age limits for CSE 2026?', 'answer': answer,
            'officialClause': 'Section II (II) Age Limits',
            'provenance': {'documentTitle': UPSC_TITLE,
                           'officialUrl': 'https://www.upsc.gov.in/notice',
                           'excerptText': AGE_EXCERPT}}


def fee_faq(answer='The application fee is Rs. 100; Female/SC/ST/PwBD candidates are exempt.'):
    return {'question': 'What is the application fee?', 'answer': answer,
            'officialClause': 'Section FEE (para 4)',
            'provenance': {'documentTitle': UPSC_TITLE,
                           'officialUrl': 'https://www.upsc.gov.in/notice',
                           'excerptText': FEE_EXCERPT}}


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


class TestFaqVerification(unittest.TestCase):

    def test_1_real_faq_supported(self):
        c = claim_from_faq(age_faq(), source_text=AGE_SRC, **UPSC_CTX)
        self.assertTrue(run_det(c))

    def test_2_real_official_clause_verified(self):
        c = claim_from_faq(fee_faq(), source_text=FEE_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_3_contradictory_faq_answer(self):
        # The clause says fee Rs. 100; a claim of Rs. 500 is contradicted.
        c = claim_from_faq(fee_faq(answer='The application fee is Rs. 500 for all candidates.'),
                           source_text=FEE_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_4_insufficient_evidence(self):
        c = claim_from_faq(age_faq(), source_text=AGE_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_5_wrong_exam_rejected_before_llm(self):
        c = claim_from_faq(age_faq(), source_text=AGE_SRC, exam_id='exam-ssc-cgl-2026',
                           official_name='Combined Graduate Level Examination',
                           authority='Staff Selection Commission', cycle='2026')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_6_wrong_cycle_rejected_before_llm(self):
        src2025 = ('UPSC — Civil Services (Preliminary) Examination, 2025 notice. Age band as '
                   'on 1 August 2025.')
        c = claim_from_faq(age_faq(answer='Age 21 to 32 on 1 August 2025.'),
                           source_text=src2025, **dict(UPSC_CTX, cycle='2026'))
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    def test_7_wrong_authority_rejected(self):
        # An SSC-authority context against UPSC evidence: the source names UPSC, not SSC.
        c = claim_from_faq(age_faq(), source_text=AGE_SRC,
                           exam_id='exam-ssc-cgl-2026',
                           official_name='Combined Graduate Level Examination',
                           authority='Staff Selection Commission', cycle='2026')
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_8_wrong_stage_is_semantic(self):
        c = claim_from_faq(age_faq(), source_text=AGE_SRC, stage='Main', **UPSC_CTX)
        self.assertIn('main', c.field)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)

    def test_9_evidence_not_in_source(self):
        # The FAQ's own excerpt is not present in the supplied source document.
        faq = age_faq()
        faq['provenance']['excerptText'] = 'A completely different clause about centres.'
        c = claim_from_faq(faq, source_text=AGE_SRC, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.llm)

    def test_10_missing_source(self):
        c = claim_from_faq(age_faq(), **UPSC_CTX)   # no source_text
        c.source_text = ''
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertIsNone(v.llm)

    def test_11_llm_unavailable_never_verified(self):
        c = claim_from_faq(fee_faq(), source_text=FEE_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'down')))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)

    def test_12_malformed_llm_never_verified(self):
        c = claim_from_faq(fee_faq(), source_text=FEE_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub('not json'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_13_cross_exam_evidence(self):
        ssc_src = ('Staff Selection Commission — Combined Graduate Level Examination, 2026. '
                   'Age relaxation as per category.')
        c = claim_from_faq(age_faq(), source_text=ssc_src, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_14_cross_cycle_evidence(self):
        src2025 = 'UPSC — Civil Services (Preliminary) Examination, 2025 notice. Age band.'
        c = claim_from_faq(age_faq(), source_text=src2025, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    def test_15_unsupported_generic_claim(self):
        # A generic assertion ("Aadhaar is required") not stated in the official clause: its own
        # text is not in the source -> deterministic rejects it, and it can never be VERIFIED.
        faq = {'question': 'Is Aadhaar required?', 'answer': 'Aadhaar is mandatory for CSE 2026.',
               'officialClause': 'Section II', 'provenance': {
                   'documentTitle': UPSC_TITLE, 'officialUrl': 'https://www.upsc.gov.in/notice',
                   'excerptText': 'Aadhaar is mandatory for CSE 2026.'}}
        c = claim_from_faq(faq, source_text=AGE_SRC, **UPSC_CTX)   # AGE_SRC says nothing of Aadhaar
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.llm)

    def test_16_revision_supported(self):
        # A FAQ answer updated by a corrigendum verifies against the corrigendum evidence; the
        # revision relationship is carried by the corrigenda layer (claim_from_revision), and the
        # old answer is preserved there. Here the new answer is supported by the new clause.
        new_src = ('UPSC — Civil Services (Preliminary) Examination, 2026 notice, revised. '
                   'The last date for applications is 27 February 2026.')
        faq = {'question': 'What is the last date?', 'answer': 'The last date is 27 February 2026.',
               'officialClause': 'Examination page (extended)', 'provenance': {
                   'documentTitle': 'UPSC — Civil Services (Preliminary) Examination, 2026 notice',
                   'officialUrl': 'https://www.upsc.gov.in/examinations',
                   'excerptText': 'The last date for applications is 27 February 2026.'}}
        c = claim_from_faq(faq, source_text=new_src, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)


def run_det(claim):
    from .verification.deterministic import run_deterministic
    return run_deterministic(claim).passed


if __name__ == '__main__':
    unittest.main(verbosity=2)
