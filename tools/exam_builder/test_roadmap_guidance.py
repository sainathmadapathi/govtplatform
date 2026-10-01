"""Study-roadmap guidance: the thirteen required cases. Real syllabus topic *content* (names
from the register) with stubbed providers so the tests are deterministic. The live-model proof
is the roadmap replay.

The guidance is GOVOS_GUIDANCE, built only from verified topics, and the model may only reorder
them; anything it invents is rejected and the deterministic order stands. Nothing is written to
an exam record.
"""
from __future__ import annotations

import json
import unittest

from tools.claude_cli.testing import FakeClaude
from .verification.roadmap_guidance import (GUIDANCE_LABEL, RoadmapGuidance,
                                            deterministic_sequence, generate)
from .verification.schemas import InfraStatus

# --- real topic content per exam (names from data.ts; ids are internal) -----------------
UPSC = [
    {'id': 'u-hist', 'topicName': 'History of India and the Indian National Movement',
     'subject': 'GS-I', 'weightagePercentage': 16, 'isHighYield': True},
    {'id': 'u-geo', 'topicName': 'Indian and World Geography', 'subject': 'GS-I',
     'weightagePercentage': 14, 'isHighYield': True},
    {'id': 'u-pol', 'topicName': 'Indian Polity and Governance', 'subject': 'GS-I',
     'weightagePercentage': 18, 'isHighYield': True},
    {'id': 'u-csat', 'topicName': 'CSAT — Comprehension and Reasoning', 'subject': 'CSAT',
     'weightagePercentage': 8, 'isHighYield': False},
]
SSC = [
    {'id': 's-arith', 'topicName': 'Arithmetic: Percentage, Profit & Loss, Ratio',
     'subject': 'Quantitative Aptitude', 'weightagePercentage': 20, 'isHighYield': True},
    {'id': 's-geo', 'topicName': 'Geometry & Mensuration (2D & 3D)',
     'subject': 'Quantitative Aptitude', 'weightagePercentage': 12, 'isHighYield': True},
    {'id': 's-eng', 'topicName': 'English Comprehension & Grammar', 'subject': 'English',
     'weightagePercentage': 15, 'isHighYield': True},
]
IBPS = [
    {'id': 'i-di', 'topicName': 'Data Interpretation & Caselets', 'subject': 'Quant',
     'weightagePercentage': 25, 'isHighYield': True},
    {'id': 'i-puz', 'topicName': 'Puzzles & Seating Arrangements', 'subject': 'Reasoning',
     'weightagePercentage': 22, 'isHighYield': True},
]


def _Stub(payload=None, raises=None):
    """A scripted Claude gateway: the real gateway over a fake CLI process. `payload` is a
    structured reply (or a raw string for a malformed one); `raises` is the failure to simulate."""
    if raises is not None:
        return FakeClaude(fail=raises)
    return FakeClaude(payload)


def _order(ids):
    return {'order': [{'id': i, 'why': 'sequencing reason'} for i in ids]}


class TestRoadmapGuidance(unittest.TestCase):

    def test_1_universal_generation(self):
        g = generate('exam-upsc-cse-2026', UPSC, gateway=_Stub(_order(['u-pol', 'u-hist', 'u-geo', 'u-csat'])))
        self.assertTrue(g.available)
        self.assertEqual(g.generated_by, 'claude')
        self.assertEqual(len(g.steps), len(UPSC))
        self.assertEqual(g.steps[0].topic_id, 'u-pol')      # the model's order was honoured

    def test_2_ssc_isolation(self):
        g = generate('exam-ssc-cgl-2026', SSC, gateway=_Stub(_order(['s-arith', 's-eng', 's-geo'])))
        ids = {s.topic_id for s in g.steps}
        self.assertEqual(ids, {'s-arith', 's-geo', 's-eng'})
        self.assertFalse(ids & {'u-hist', 'u-pol', 'i-di'})  # no UPSC/IBPS topic

    def test_3_upsc_isolation(self):
        g = generate('exam-upsc-cse-2026', UPSC, gateway=_Stub(_order(['u-hist', 'u-geo', 'u-pol', 'u-csat'])))
        self.assertTrue(all(s.topic_id.startswith('u-') for s in g.steps))

    def test_4_ibps_isolation(self):
        g = generate('exam-ibps-po-2026', IBPS, gateway=_Stub(_order(['i-di', 'i-puz'])))
        self.assertTrue(all(s.topic_id.startswith('i-') for s in g.steps))

    def test_5_missing_syllabus_unavailable(self):
        g = generate('exam-appsc-group1-2026', [], gateway=_Stub(_order([])))
        self.assertFalse(g.available)
        self.assertIn('NOT_EXTRACTED', g.unavailable_reason)
        self.assertEqual(g.steps, [])                        # nothing fabricated

    def test_6_missing_progress_still_works(self):
        # The generator needs no candidate progress; guidance is built from the syllabus alone.
        g = generate('exam-ssc-cgl-2026', SSC, gateway=_Stub(_order(['s-arith', 's-geo', 's-eng'])))
        self.assertTrue(g.available)

    def test_7_verified_topics_only(self):
        g = generate('exam-upsc-cse-2026', UPSC, gateway=_Stub(_order(['u-pol', 'u-hist', 'u-geo', 'u-csat'])))
        input_ids = {t['id'] for t in UPSC}
        self.assertTrue({s.topic_id for s in g.steps} <= input_ids)

    def test_8_guidance_labelled_not_official(self):
        g = generate('exam-upsc-cse-2026', UPSC, gateway=_Stub(_order(['u-hist', 'u-geo', 'u-pol', 'u-csat'])))
        self.assertEqual(g.source, GUIDANCE_LABEL)
        self.assertIn('not an official recommendation', g.disclaimer)

    def test_9_claude_unavailable_deterministic_fallback(self):
        g = generate('exam-upsc-cse-2026', UPSC,
                     gateway=_Stub(raises=InfraStatus.CLAUDE_CLI_FAILED))
        self.assertTrue(g.available)                         # roadmap does not vanish
        self.assertEqual(g.generated_by, 'deterministic')
        self.assertEqual(g.infra, InfraStatus.CLAUDE_CLI_FAILED.value)
        self.assertEqual({s.topic_id for s in g.steps}, {t['id'] for t in UPSC})

    def test_10_malformed_claude_deterministic_fallback(self):
        g = generate('exam-upsc-cse-2026', UPSC, gateway=_Stub('not json at all'))
        self.assertEqual(g.generated_by, 'deterministic')
        self.assertEqual(g.infra, InfraStatus.CLAUDE_INVALID_OUTPUT.value)

    def test_11_no_invented_topic_enters(self):
        # The model returns an id that was never supplied -> the whole order is rejected.
        g = generate('exam-upsc-cse-2026', UPSC,
                     gateway=_Stub(_order(['u-hist', 'u-INVENTED', 'u-geo', 'u-pol', 'u-csat'])))
        self.assertEqual(g.generated_by, 'deterministic')
        self.assertNotIn('u-INVENTED', {s.topic_id for s in g.steps})

    def test_12_cross_exam_contamination_rejected(self):
        # A UPSC generation whose model tries to inject an SSC topic id -> rejected.
        g = generate('exam-upsc-cse-2026', UPSC,
                     gateway=_Stub(_order(['u-hist', 's-arith', 'u-geo', 'u-pol', 'u-csat'])))
        self.assertEqual(g.generated_by, 'deterministic')
        self.assertTrue(all(s.topic_id.startswith('u-') for s in g.steps))

    def test_13_deterministic_order_is_sensible(self):
        seq = deterministic_sequence(UPSC)
        self.assertEqual({s.topic_id for s in seq}, {t['id'] for t in UPSC})
        # high-yield topics precede the non-high-yield CSAT
        self.assertEqual(seq[-1].topic_id, 'u-csat')


if __name__ == '__main__':
    unittest.main(verbosity=2)
