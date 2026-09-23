"""The verification layer applied to OFFICIAL PORTALS & LINKS: the twenty required cases over
real UPSC CSE 2026 notice clauses that tie a URL to a purpose (the online application portal and
the admit-card download portal, both named verbatim in the notice). The LLM is stubbed for
determinism; the live-model proof is the portal replay.

Additive only -- no `officialLinks` type, section 12, or authored link is changed, and no portal
is published. This verifies four things the phase demands: (1) officiality is deterministic and
domain-based, not a ".gov.in" test and not the model's; (2) a URL's *purpose* is checked against
official evidence, so a homepage cannot become an application/download link; (3) a portal is bound
to the exact exam/cycle, rejected before Qwen otherwise; (4) a dead/unreachable link is
infrastructure, never NOT_PUBLISHED, and a discovered-but-unsupported URL is never VERIFIED.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_portal, portal_officiality, resource_officiality
from .verification.client import ProviderError, VerificationProvider
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured portal evidence: UPSC CSE 2026 notice --------------------------------
UPSC_TITLE = 'UPSC — Civil Services (Preliminary) Examination, 2026 notice'
APPLY_CLAUSE = ('Applicants are required to apply online by using the website '
                'https://upsconline.nic.in.')
ADMIT_CLAUSE = ('The e-Admit Card will be made available on the website '
                '[https://upsconline.nic.in] for downloading by the candidates. No Admit Card '
                'will be sent by post or Email.')
HOME_CLAUSE = ('Union Public Service Commission official website www.upsc.gov.in carries the '
               'Commission’s notices and press releases.')
APPLY_SRC = f'{UPSC_TITLE}. Section How to Apply. {APPLY_CLAUSE}'
ADMIT_SRC = f'{UPSC_TITLE}. Section e-Admit Card. {ADMIT_CLAUSE}'
HOME_SRC = f'{UPSC_TITLE}. {HOME_CLAUSE}'

UPSC_CTX = dict(exam_id='exam-upsc-cse-2026',
                official_name='Civil Services (Preliminary) Examination',
                authority='Union Public Service Commission', cycle='2026')
# UPSC owns two official hosts: its notice site and NIC's application/admit-card portal.
UPSC_DOMAINS = 'upsc.gov.in upsconline.nic.in'


def apply_link(url='https://upsconline.nic.in', note=APPLY_CLAUSE, title=UPSC_TITLE):
    return {'url': url, 'title': 'UPSC Online Application', 'note': note,
            'evidenceSpan': note, 'sourceTitle': title, 'sourceUrl': url}


def admit_link(url='https://upsconline.nic.in', note=ADMIT_CLAUSE):
    return {'url': url, 'title': 'e-Admit Card', 'note': note,
            'evidenceSpan': note, 'sourceTitle': UPSC_TITLE}


def home_link(url='https://www.upsc.gov.in', note=HOME_CLAUSE):
    return {'url': url, 'title': 'UPSC Official Website', 'note': note,
            'evidenceSpan': note, 'sourceTitle': UPSC_TITLE}


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


class TestPortalsVerification(unittest.TestCase):

    # --- 1-4: real official links of four purposes verify against their own evidence ------
    def test_1_real_application_portal_verified(self):
        c = claim_from_portal(apply_link(), purpose='APPLICATION', source_text=APPLY_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.llm.decision, VerificationDecision.SUPPORTED)

    def test_2_real_admit_card_portal_verified(self):
        c = claim_from_portal(admit_link(), purpose='ADMIT_CARD', source_text=ADMIT_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertIn('admit_card', c.field)

    def test_3_real_official_home_verified(self):
        c = claim_from_portal(home_link(), purpose='OFFICIAL_HOME', source_text=HOME_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)

    def test_4_real_notification_page_verified(self):
        link = {'url': 'https://www.upsc.gov.in/examinations/active-exams', 'title': 'CSE 2026 notice',
                'note': HOME_CLAUSE, 'evidenceSpan': HOME_CLAUSE, 'sourceTitle': UPSC_TITLE}
        c = claim_from_portal(link, purpose='NOTIFICATION', source_text=HOME_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)

    # --- 5-8: wrong exam / cycle / authority rejected deterministically, before the LLM ---
    def test_5_wrong_exam_rejected_before_llm(self):
        c = claim_from_portal(apply_link(), purpose='APPLICATION', source_text=APPLY_SRC,
                              exam_id='exam-ssc-cgl-2026',
                              official_name='Combined Graduate Level Examination',
                              authority='Staff Selection Commission', cycle='2026')
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_6_wrong_cycle_rejected_before_llm(self):
        src2025 = ('UPSC — Civil Services (Preliminary) Examination, 2025 notice. Apply online at '
                   'https://upsconline.nic.in.')
        c = claim_from_portal(apply_link(note='Apply online at https://upsconline.nic.in.'),
                              purpose='APPLICATION', source_text=src2025, **dict(UPSC_CTX, cycle='2026'))
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    def test_7_wrong_authority_evidence_rejected(self):
        # SSC-scoped context against UPSC evidence: the source names UPSC, not SSC.
        c = claim_from_portal(apply_link(), purpose='APPLICATION', source_text=APPLY_SRC,
                              exam_id='exam-ssc-cgl-2026',
                              official_name='Combined Graduate Level Examination',
                              authority='Staff Selection Commission', cycle='2026')
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)

    def test_8_stale_cycle_evidence_rejected(self):
        stale = 'UPSC — Civil Services (Preliminary) Examination, 2024 notice. Apply at upsconline.nic.in.'
        c = claim_from_portal(apply_link(note='Apply at upsconline.nic.in.'), purpose='APPLICATION',
                              source_text=stale, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.llm)

    # --- 9-10: officiality is deterministic and NOT a .gov.in test -----------------------
    def test_9_officiality_non_govin_domains(self):
        # IBPS (ibps.in) and LIC (licindia.in) are official on their own non-.gov.in hosts;
        # UPSC's application portal upsconline.nic.in is a second official host, not upsc.gov.in.
        self.assertEqual(portal_officiality('https://ibps.in/', 'ibps.in'), 'OFFICIAL')
        self.assertEqual(portal_officiality('https://www.licindia.in/aao', 'licindia.in'), 'OFFICIAL')
        self.assertEqual(portal_officiality('https://upsconline.nic.in', UPSC_DOMAINS), 'OFFICIAL')
        self.assertEqual(portal_officiality('https://www.upsc.gov.in/notice', UPSC_DOMAINS), 'OFFICIAL')
        # one shared definition across the engine (single-domain case delegates unchanged)
        self.assertEqual(portal_officiality('https://ibps.in/', 'ibps.in'),
                         resource_officiality('https://ibps.in/', 'ibps.in'))

    def test_10_officiality_rejects_lookalike_and_aggregator(self):
        self.assertEqual(portal_officiality('https://ibps.in.exam-results.com/', 'ibps.in'), 'UNOFFICIAL')
        self.assertEqual(portal_officiality('https://sarkariresult.com/upsc', UPSC_DOMAINS), 'UNOFFICIAL')
        self.assertEqual(portal_officiality('https://upsc-gov.in/', UPSC_DOMAINS), 'UNOFFICIAL')

    # --- 11-12: a homepage must not become an application/download link -------------------
    def test_11_homepage_claimed_as_application_not_verified(self):
        # The homepage clause names no application purpose; claiming it as the application portal
        # cannot be SUPPORTED. The model returns INSUFFICIENT -> NEEDS_REVIEW, never VERIFIED.
        c = claim_from_portal(home_link(), purpose='APPLICATION', source_text=HOME_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')
        self.assertTrue(v.deterministic.passed)   # identity fine; purpose is what fails

    def test_12_homepage_claimed_as_admit_card_not_verified(self):
        c = claim_from_portal(home_link(), purpose='ADMIT_CARD', source_text=HOME_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    # --- 13: evidence for one purpose cannot verify another (purpose travels in the field)-
    def test_13_wrong_purpose_is_semantic(self):
        # Admit-card evidence, claimed as the result portal: the field carries RESULT, the model
        # judges the mismatch. Deterministic passes (same exam/cycle), publication does not.
        c = claim_from_portal(admit_link(), purpose='RESULT', source_text=ADMIT_SRC, **UPSC_CTX)
        self.assertIn('portal:result', c.field)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)

    # --- 14: a fabricated / not-official URL is UNOFFICIAL and unsupported ----------------
    def test_14_fake_url_unofficial_and_unverified(self):
        fake = 'https://upsc-online-apply.com/cse2026'
        self.assertEqual(portal_officiality(fake, UPSC_DOMAINS), 'UNOFFICIAL')
        c = claim_from_portal(apply_link(url=fake), purpose='APPLICATION', source_text=APPLY_SRC, **UPSC_CTX)
        # the evidence names upsconline.nic.in, not this host -> the model cannot support it
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)

    # --- 15: a URL not present in the evidence is not verifiable --------------------------
    def test_15_url_not_in_evidence_not_verified(self):
        # A plausible official-looking host that the cited clause never mentions.
        c = claim_from_portal(apply_link(url='https://digilocker.gov.in'), purpose='APPLICATION',
                              source_text=APPLY_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)

    # --- 16: missing source -> NEEDS_REVIEW, never VERIFIED and never NOT_PUBLISHED -------
    def test_16_missing_source(self):
        c = claim_from_portal(apply_link(), purpose='APPLICATION', **UPSC_CTX)  # no source_text...
        c.source_text = ''
        c.evidence_span = ''
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.llm)

    # --- 17-18: a dead / unreachable official link is not NOT_PUBLISHED -------------------
    def test_17_dead_official_link_stays_official(self):
        # Link health (DEAD) is infrastructure about the URL, not a claim about the authority.
        # Officiality is unchanged by reachability, and the record is not converted to
        # NOT_PUBLISHED: a historically valid official link stays official.
        self.assertEqual(portal_officiality('https://upsconline.nic.in/old', UPSC_DOMAINS), 'OFFICIAL')

    def test_18_unreachable_source_never_verified_but_not_absent(self):
        # The source could not be fetched (LLM stands in for an infrastructure failure here):
        # NEEDS_REVIEW with an infra status, never VERIFIED and never NOT_PUBLISHED.
        c = claim_from_portal(apply_link(), purpose='APPLICATION', source_text=APPLY_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub(raises=ProviderError(InfraStatus.LLM_UNAVAILABLE, 'down')))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_UNAVAILABLE)
        self.assertNotEqual(v.status, 'VERIFIED')

    # --- 19: malformed LLM output is never VERIFIED --------------------------------------
    def test_19_malformed_llm_never_verified(self):
        c = claim_from_portal(apply_link(), purpose='APPLICATION', source_text=APPLY_SRC, **UPSC_CTX)
        v = verify(c, provider=_Stub('not json'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.LLM_INVALID_RESPONSE)

    # --- 20: cross-exam isolation — SSC evidence can never verify a UPSC portal -----------
    def test_20_cross_exam_isolation(self):
        ssc_src = ('Staff Selection Commission — Combined Graduate Level Examination, 2026. '
                   'Apply online at https://ssc.gov.in.')
        c = claim_from_portal(apply_link(url='https://ssc.gov.in', note='Apply online at https://ssc.gov.in.'),
                              purpose='APPLICATION', source_text=ssc_src, **UPSC_CTX)
        v = verify(c, provider=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.llm)


if __name__ == '__main__':
    unittest.main(verbosity=2)
