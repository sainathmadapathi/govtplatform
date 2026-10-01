"""The verification layer applied to CORRIGENDA / REVISION facts: the ten required cases over
the real UPSC CSE 2026 corrigendum (last date extended 24 -> 27 February 2026, recorded in the
register as `corr-upsc-02` and cited to the Commission's own examination page).

The Claude is stubbed for determinism; the live-model proof is the corrigenda replay. Additive
only -- no revision model, corrigenda UI, or authored `corrigendums` is changed. A revision is
verified on its NEW value; the old value is preserved in the record and is not re-verified
against the new source.
"""
from __future__ import annotations

import json
import unittest

from .verification.adapters import claim_from_revision
from tools.claude_cli.testing import FakeClaude, ForbiddenClaude, verdict_reply
from .verification.schemas import InfraStatus, VerificationDecision
from .verification.verifier import verify

# --- real captured revision evidence: UPSC CSE 2026 last-date extension ------------------
UPSC_SRC = ('Union Public Service Commission. Civil Services (Preliminary) Examination, 2026. '
            'Last Date for Receipt of Applications 27/02/2026 - 6:00pm.')
UPSC_CTX = dict(exam_id='exam-upsc-cse-2026',
                official_name='Civil Services (Preliminary) Examination',
                authority='Union Public Service Commission')


def upsc_rev(affected='application_last_date', new_value='27/02/2026',
             span='Last Date for Receipt of Applications 27/02/2026 - 6:00pm', cycle='2026'):
    return {'affected': affected, 'newValue': new_value, 'cycle': cycle, 'evidenceSpan': span,
            'sourceUrl': 'https://upsc.gov.in/examinations',
            'sourceTitle': 'Civil Services (Preliminary) Examination, 2026'}


def _Stub(payload=None, raises=None):
    """A scripted Claude gateway: the real gateway over a fake CLI process. `payload` is a verdict
    reply (or a raw string for a malformed one); `raises` is the infrastructure failure to simulate."""
    if raises is not None:
        return FakeClaude(fail=raises)
    return FakeClaude(payload)


def _json(decision, ident=True, ev=True, claim=True):
    return verdict_reply(decision, identity=ident, evidence=ev, claim=claim)


POISON = ForbiddenClaude('Claude must not be called after a deterministic failure')


class TestCorrigendaVerification(unittest.TestCase):

    def test_1_real_supported_revision(self):
        c = claim_from_revision(upsc_rev(), source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, gateway=_Stub(_json('SUPPORTED')))
        self.assertTrue(v.publishable)
        self.assertEqual(v.status, 'VERIFIED')
        self.assertIs(v.claude.decision, VerificationDecision.SUPPORTED)

    def test_2_contradictory_revision(self):
        # The revision source says 27 Feb; a claim that the new date is 30 March is contradicted.
        c = claim_from_revision(upsc_rev(new_value='30/03/2026'), source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, gateway=_Stub(_json('CONTRADICTED', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertEqual(v.status, 'NEEDS_REVIEW')

    def test_3_insufficient_evidence(self):
        c = claim_from_revision(upsc_rev(), source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, gateway=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)

    def test_4_wrong_exam_rejected_before_claude(self):
        c = claim_from_revision(upsc_rev(), source_text=UPSC_SRC, exam_id='exam-ssc-cgl-2026',
                                official_name='Combined Graduate Level Examination',
                                authority='Staff Selection Commission')
        v = verify(c, gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.claude)

    def test_5_wrong_cycle_rejected_before_claude(self):
        src = ('Union Public Service Commission. Civil Services (Preliminary) Examination, '
               '2025. Last Date for Receipt of Applications 20/02/2025.')
        c = claim_from_revision(upsc_rev(new_value='20/02/2025',
                                         span='Last Date for Receipt of Applications 20/02/2025',
                                         cycle='2026'), source_text=src, **UPSC_CTX)
        v = verify(c, gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cycle_ok)
        self.assertIsNone(v.claude)

    def test_6_wrong_affected_field_is_semantic(self):
        # The evidence revises the last date; a claim that it revises the EXAM date is a
        # different field. Deterministic passes (span/identity ok); the model must not support
        # a field the evidence does not establish.
        c = claim_from_revision(upsc_rev(affected='exam_date'), source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, gateway=_Stub(_json('INSUFFICIENT', ev=False, claim=False)))
        self.assertFalse(v.publishable)
        self.assertTrue(v.deterministic.passed)
        self.assertEqual(c.field, 'revision:exam_date')

    def test_7_claude_unavailable_never_verified(self):
        c = claim_from_revision(upsc_rev(), source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, gateway=_Stub(raises=InfraStatus.CLAUDE_CLI_FAILED))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.CLAUDE_CLI_FAILED)

    def test_8_malformed_claude_never_verified(self):
        c = claim_from_revision(upsc_rev(), source_text=UPSC_SRC, **UPSC_CTX)
        v = verify(c, gateway=_Stub('<<not json>>'))
        self.assertFalse(v.publishable)
        self.assertIs(v.infra, InfraStatus.CLAUDE_INVALID_OUTPUT)

    def test_9_revision_without_sufficient_evidence(self):
        # No source document to confirm the span -> deterministic cannot verify -> NEEDS_REVIEW,
        # never VERIFIED, and the model is never asked to fill the gap.
        c = claim_from_revision(upsc_rev(), source_text='', **UPSC_CTX)
        c.source_text = ''  # simulate a fetch that returned nothing
        v = verify(c, gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.span_in_source)
        self.assertIsNone(v.claude)

    def test_10_cross_exam_isolation(self):
        # An SSC corrigendum document can never verify a UPSC revision claim.
        ssc_src = ('Staff Selection Commission. Combined Graduate Level Examination, 2026. '
                   'Corrigendum-II: application window extended to 05/09/2026.')
        c = claim_from_revision(upsc_rev(new_value='05/09/2026',
                                         span='application window extended to 05/09/2026'),
                                source_text=ssc_src, **UPSC_CTX)
        v = verify(c, gateway=POISON)
        self.assertFalse(v.publishable)
        self.assertFalse(v.deterministic.cross_exam_ok)
        self.assertIsNone(v.claude)


if __name__ == '__main__':
    unittest.main(verbosity=2)
