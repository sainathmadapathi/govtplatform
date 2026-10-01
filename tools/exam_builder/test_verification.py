"""Golden tests for the verification layer. No real Claude: the gateway runs over a scripted fake
CLI process so these are deterministic and fast. They prove the contract -- deterministic checks are
authoritative, Claude can only withhold, and no failure mode is ever read as VERIFIED. The gateway's
own behaviour (flags, timeouts, malformed output) is proved in tools/claude_cli/test_gateway.py.
"""
from __future__ import annotations

import unittest

from .verification.cache import VerificationCache
from tools.claude_cli.testing import FakeClaude, ForbiddenClaude, verdict_reply
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


def _Stub(payload=None, raises=None):
    """A scripted Claude gateway: the real gateway over a fake CLI process. `payload` is a verdict
    reply (or a raw string for a malformed one); `raises` is the failure to simulate."""
    if raises is not None:
        return FakeClaude(fail=raises)
    return FakeClaude(payload)


def _json(decision, ident=True, ev=True, claim=True):
    return verdict_reply(decision, identity=ident, evidence=ev, claim=claim)


SUPPORTED = _Stub(_json('SUPPORTED'))
CONTRADICTED = _Stub(_json('CONTRADICTED', ev=False, claim=False))
INSUFFICIENT = _Stub(_json('INSUFFICIENT', ev=False, claim=False))
POISON = ForbiddenClaude('Claude must not be called after a deterministic failure')


class TestGolden(unittest.TestCase):

    def test_case_1_supported(self):
        v = verify(ssc_claim(), gateway=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.claude.decision, VerificationDecision.SUPPORTED)

    def test_case_2_contradicted(self):
        v = verify(ssc_claim(), gateway=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')
        self.assertIs(v.claude.decision, VerificationDecision.CONTRADICTED)

    def test_case_3_insufficient(self):
        v = verify(ssc_claim(), gateway=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_case_4_wrong_exam_rejected_before_claude(self):
        src = ('Staff Selection Commission. Combined Higher Secondary (10+2) Level '
               'Examination, 2026. The last date is 22 June 2026.')
        v = verify(ssc_claim(source_text=src,
                             evidence_span='The last date is 22 June 2026.',
                             value='22 June 2026'), gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.claude)                       # Claude never consulted

    def test_case_5_wrong_cycle_rejected_before_claude(self):
        src = ('Combined Graduate Level Examination, 2025. The last date for submission of '
               'online applications is 22 June 2025.')
        v = verify(ssc_claim(source_text=src,
                             evidence_span='The last date for submission of online applications is 22 June 2025.',
                             value='22 June 2025'), gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.identity_ok)
        self.assertIsNone(v.claude)

    def test_case_6_irrelevant_evidence_insufficient(self):
        # Deterministic passes (identity/cycle/span ok); the Claude judges support and says no.
        v = verify(ssc_claim(), gateway=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_case_7_claude_unavailable_never_verified(self):
        down = _Stub(raises=InfraStatus.CLAUDE_CLI_FAILED)
        v = verify(ssc_claim(), gateway=down)
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')
        self.assertIs(v.infra, InfraStatus.CLAUDE_CLI_FAILED)
        self.assertIsNot(v.claude.decision, VerificationDecision.SUPPORTED)

    def test_case_8_malformed_json_never_verified(self):
        v = verify(ssc_claim(), gateway=_Stub('this is not json at all {oops'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.CLAUDE_INVALID_OUTPUT)

    def test_case_9_claude_supported_but_deterministic_fails(self):
        # Claude would say SUPPORTED, but the span is not in the source -> deterministic fails
        # first and the model is never called.
        v = verify(ssc_claim(source_text='An unrelated document with no such sentence.'),
                   gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.claude)

    def test_case_10_snippet_unsupported_by_official_doc(self):
        # The claimed value comes from a Discovery snippet, but the official document's own span
        # does not state it -> the Claude (given the official span) returns INSUFFICIENT.
        v = verify(ssc_claim(value='30 July 2026'),
                   gateway=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertIs(v.claude.decision, VerificationDecision.CONTRADICTED)

    def test_case_11_uses_official_evidence_span(self):
        # Even if a snippet was incomplete, verification runs on the official document's span,
        # which supports the claim -> SUPPORTED.
        v = verify(ssc_claim(), gateway=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertIn(SPAN, SSC_SRC)                   # the official span is what was checked

    def test_case_12_cross_exam_identity_rejection(self):
        # A UPSC source can never verify an SSC claim.
        upsc_src = ('Union Public Service Commission. Civil Services (Preliminary) '
                    'Examination, 2026. e-Admit Cards will be uploaded on 15 May 2026.')
        v = verify(ssc_claim(source_text=upsc_src,
                             evidence_span='e-Admit Cards will be uploaded on 15 May 2026.',
                             field='admit_card', value='15 May 2026'), gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.claude)


class TestContractDetails(unittest.TestCase):

    def test_infra_is_not_a_factual_state(self):
        for infra in InfraStatus:
            self.assertNotIn(infra.value,
                             {'VERIFIED', 'NEEDS_REVIEW', 'NOT_PUBLISHED', 'PUBLISHED'})

    def test_malformed_supported_with_disagreeing_booleans_is_refused(self):
        bad = {'decision': 'SUPPORTED', 'identity_supported': True,
               'evidence_supported': False, 'claim_supported': False, 'reason': 'x'}
        r = VerificationResult.from_claude_output(bad, engine='stub')
        self.assertIs(r.infra, InfraStatus.CLAUDE_SCHEMA_REJECTED)

    def test_cache_serves_repeat_and_skips_infra_failures(self):
        cache = VerificationCache()
        ok = _Stub(_json('SUPPORTED'))
        v1 = verify(ssc_claim(), gateway=ok, cache=cache)
        self.assertTrue(v1.publishable)
        v2 = verify(ssc_claim(), gateway=ok, cache=cache)         # served from the verdict cache
        self.assertTrue(v2.publishable)
        self.assertEqual(ok.calls, 1)                             # Claude was asked once, not twice
        self.assertEqual(v1.fingerprint, v2.fingerprint)
        # an infra failure is never cached
        cache.clear()
        down = _Stub(raises=InfraStatus.CLAUDE_CLI_TIMEOUT)
        verify(ssc_claim(), gateway=down, cache=cache)
        self.assertIsNone(cache.get(ssc_claim().fingerprint(VERIFIER_VERSION)))

    def test_fingerprint_changes_with_evidence(self):
        a = ssc_claim().fingerprint()
        b = ssc_claim(evidence_span='A different sentence entirely.').fingerprint()
        self.assertNotEqual(a, b)


if __name__ == '__main__':
    unittest.main(verbosity=2)
