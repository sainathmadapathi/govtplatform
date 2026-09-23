"""The verification layer applied to RESOURCE facts: the twelve required cases over the real
UPSC CSE 2026 official-notice resource (authored in the register with provenance on
upsc.gov.in). The LLM is stubbed for determinism; the live-model proof is the resources replay.

Additive only -- no resource model, UI, or authored `resources` is changed. This verifies that a
resource, routed through the deterministic + Qwen gate, is bound to the exact exam/cycle, that
officiality is decided deterministically by domain, and that Tavily cannot shortcut to VERIFIED.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_resource, resource_officiality
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured resource: UPSC CSE 2026 examination notice ---------------------------
UPSC_NOTICE = {
    'id': 'res-upsc-notice-2026', 'type': 'OFFICIAL_PDF', 'resourceFormat': 'DIRECT_PDF',
    'title': 'UPSC CSE 2026 — Examination Notice No. 05/2026-CSE (official PDF)',
    'url': 'https://www.upsc.gov.in/sites/default/files/Notif-CSP-2026-Engl-060226Rev.pdf',
    'description': ("The Commission's notice for the Civil Services (Preliminary) Examination, "
                    "2026, hosted on upsc.gov.in. Sections I-III carry the services, "
                    "eligibility, scheme and syllabi.")}
UPSC_CTX = dict(exam_id='exam-upsc-cse-2026',
                official_name='Civil Services (Preliminary) Examination',
                authority='Union Public Service Commission', cycle='2026')
UPSC_DOMAIN = 'upsc.gov.in'

# A real coaching video resource (useful, not official).
COACHING_VIDEO = {
    'id': 'res-adda-cse', 'type': 'VIDEO_LECTURE', 'resourceFormat': 'YOUTUBE_CHANNEL',
    'title': 'Adda247 — UPSC CSE 2026 strategy playlist',
    'url': 'https://www.youtube.com/@Adda247',
    'description': 'Free UPSC Civil Services (Preliminary) Examination, 2026 strategy videos.'}


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


class TestResourceVerification(unittest.TestCase):

    def test_1_valid_official_resource(self):
        c = claim_from_resource(UPSC_NOTICE, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertEqual(resource_officiality(UPSC_NOTICE['url'], UPSC_DOMAIN), 'OFFICIAL')

    def test_2_valid_unofficial_resource(self):
        # A coaching video verifies as a video resource for the exam, but is UNOFFICIAL by domain.
        c = claim_from_resource(COACHING_VIDEO, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)                       # it is a real video for this exam
        self.assertEqual(resource_officiality(COACHING_VIDEO['url'], UPSC_DOMAIN), 'UNOFFICIAL')
        self.assertEqual(c.field, 'resource:video_lecture')

    def test_3_wrong_exam_rejected_before_llm(self):
        c = claim_from_resource(UPSC_NOTICE, exam_id='exam-ssc-cgl-2026',
                                official_name='Combined Graduate Level Examination',
                                authority='Staff Selection Commission', cycle='2026')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_4_wrong_cycle_rejected_before_llm(self):
        res = dict(UPSC_NOTICE,
                   description="Civil Services (Preliminary) Examination, 2025 notice on upsc.gov.in.")
        c = claim_from_resource(res, **dict(UPSC_CTX, cycle='2026'))
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    def test_5_wrong_resource_type_is_semantic(self):
        # Claim: this is a VIDEO_LECTURE. The evidence describes an official PDF notice. The
        # model, given the evidence, must not support a video reading.
        res = dict(UPSC_NOTICE, type='VIDEO_LECTURE')
        c = claim_from_resource(res, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(c.field, 'resource:video_lecture')

    def test_6_irrelevant_evidence_insufficient(self):
        c = claim_from_resource(UPSC_NOTICE, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_7_tavily_candidate_cannot_shortcut(self):
        # A Tavily candidate with only a snippet and no official document text: the span cannot
        # be confirmed against a source, so it is NEEDS_REVIEW, never VERIFIED.
        candidate = {'id': 'cand', 'type': 'OFFICIAL_PDF',
                     'title': 'Some page a search returned',
                     'url': 'https://example.com/x', 'description': ''}
        c = claim_from_resource(candidate, **UPSC_CTX)
        c.source_text = ''                                   # nothing fetched/inspected yet
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertIsNone(v.llm)

    def test_8_llm_unavailable_never_verified(self):
        c = claim_from_resource(UPSC_NOTICE, **UPSC_CTX)
        v = verify(c, provider=_Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'down')))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)

    def test_9_malformed_llm_never_verified(self):
        c = claim_from_resource(UPSC_NOTICE, **UPSC_CTX)
        v = verify(c, provider=_Stub('definitely not json'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    def test_10_cross_exam_isolation(self):
        # SSC evidence, UPSC claim -> rejected before the model.
        ssc_res = dict(UPSC_NOTICE,
                       description='Staff Selection Commission Combined Graduate Level Examination, 2026 notice.')
        c = claim_from_resource(ssc_res, **UPSC_CTX)
        # identity target is UPSC; the SSC text names another exam -> mismatch
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_11_dead_link_is_infrastructure_not_not_published(self):
        # A resource whose document could not be fetched (no source text) is NEEDS_REVIEW; the
        # verdict never claims the resource does not exist.
        res = dict(UPSC_NOTICE)
        c = claim_from_resource(res, **UPSC_CTX)
        c.source_text = ''                                   # simulate a broken/unreachable link
        v = verify(c, provider=POISON)
        self.assertEqual(v.status, 'NEEDS_REVIEW')
        self.assertNotIn('NOT_PUBLISHED', (v.reason or '').upper())

    def test_12_login_required_official_portal(self):
        # A candidate-login portal is OFFICIAL by domain, but its gated contents cannot be
        # confirmed -> content verification is NEEDS_REVIEW, officiality preserved.
        portal = {'id': 'res-portal', 'type': 'OFFICIAL_PORTAL', 'resourceFormat': 'OFFICIAL_PORTAL',
                  'title': 'UPSC candidate login portal',
                  'url': 'https://upsconline.nic.in/', 'description': ''}
        self.assertEqual(resource_officiality(portal['url'], 'upsconline.nic.in'), 'OFFICIAL')
        c = claim_from_resource(portal, **UPSC_CTX)
        c.source_text = ''                                   # gated content, nothing to verify
        v = verify(c, provider=POISON)
        self.assertEqual(v.status, 'NEEDS_REVIEW')           # content unverified
        self.assertIsNone(v.llm)


if __name__ == '__main__':
    unittest.main(verbosity=2)
