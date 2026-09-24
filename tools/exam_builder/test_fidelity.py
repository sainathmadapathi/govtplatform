"""The preservation test the canonical-data audit is built on (CANONICAL_DATA_AUDIT.md, Step 7).

It proves two things about the *current* representation, with no migration and no change to any
production file:

  1. WHOLE-SLICE REPLACEMENT LOSES FIDELITY. Re-emitting an exam's `data.ts` block from a partial
     machine build — the only way publish.stage can update an existing record — deletes authored
     arrays, drops inline comments, inlines shared `const` provenance, and loses authored ids.
     The test detects each loss explicitly.

  2. AN ADDITIVE OVERLAY PRESERVES EVERYTHING. Recording the machine's new fact in a separate
     overlay (the shape `syllabus_revisions` / `resource_additions` already use) leaves the
     authored block byte-identical and mutates no other exam, while still carrying the new value
     with its provenance and status. This is the pattern the audit recommends generalising.

Nothing here migrates data or writes a production file; it operates on in-memory strings and
reuses `publish.fingerprint` so "the authored record is unchanged" means what it means at publish
time. It is documentation-as-a-test for the audit, not an implementation of the future store.
"""
from __future__ import annotations

import unittest

from .publish import fingerprint, slice_exams

# An authored register slice, in the real shape: a shared-const spread, inline comments, and
# populated authored arrays with their own ids — exactly the fidelity the audit says is at risk.
AUTHORED = """export const SSC_EXAM: Exam = {
  id: 'exam-ssc-cgl-2026',
  title: 'SSC CGL 2026',
  // Authored by hand from the notice; see CLAUDE.md on the provenance chain.
  dates: [
    { id: 'date-1', type: 'APPLICATION_CLOSE', dateTimeStr: '2026-06-22', provenance: { ...sscNoticeProv, id: 'p-d1' } }
  ],
  syllabus: [
    { id: 'topic-1', topicName: 'Quantitative Aptitude', officialProvenance: { ...sscSyllabusSource, id: 'p-s1' } },
    { id: 'topic-2', topicName: 'Reasoning', officialProvenance: { ...sscSyllabusSource, id: 'p-s2' } }
  ],
  resources: [ { id: 'res-1', title: 'Official Notice', provenance: { ...sscNoticeProv, id: 'p-r1' } } ],
  cutoffsHistory: [ { id: 'cut-2024', category: 'General', tier1Cutoff: 145 } ]
};

export const UPSC_EXAM: Exam = {
  id: 'exam-upsc-cse-2026',
  title: 'UPSC CSE 2026',
  syllabus: [ { id: 'gs-1', topicName: 'Polity' } ]
};

export const ALL_EXAMS: Exam[] = [
  SSC_EXAM,
  UPSC_EXAM
];
"""

# What a partial machine build re-emits for the SAME exam (emit.render_exam-style): only the
# fields it extracted, honest-empty arrays for everything it did not, no comments, no shared
# const — the provenance is inlined per value.
MACHINE_REEMIT_SSC = """export const SSC_CGL_2026_EXAM: Exam = {
  id: 'exam-ssc-cgl-2026',
  title: 'SSC CGL 2026',
  dates: [
    { id: 'date-ssc-0', type: 'APPLICATION_CLOSE', dateTimeStr: '2026-06-27', provenance: { id: 'prov-ssc-date-0', documentTitle: 'Notice', verificationLevel: 'OFFICIALLY_VERIFIED' } }
  ],
  syllabus: [],
  resources: [],
  cutoffsHistory: []
};"""


def _slice_text(register: str, exam_id: str) -> str:
    for s in slice_exams(register):
        if s.exam_id == exam_id:
            return s.text
    return ''


def _whole_slice_replace(register: str, exam_id: str, new_block: str) -> str:
    """What publish.stage does: swap an exam's whole slice for the new block."""
    s = next(x for x in slice_exams(register) if x.exam_id == exam_id)
    return register[:s.start] + new_block.rstrip() + '\n' + register[s.end:]


class TestWholeSliceReplacementLosesFidelity(unittest.TestCase):
    """Part 1: prove the loss the audit is about."""

    def setUp(self):
        self.after = _whole_slice_replace(AUTHORED, 'exam-ssc-cgl-2026', MACHINE_REEMIT_SSC)
        self.new_slice = _slice_text(self.after, 'exam-ssc-cgl-2026')

    def test_a_authored_arrays_are_deleted(self):
        # A partial build had no syllabus/resources/cutoffs, so re-emit empties them.
        self.assertIn('topic-1', AUTHORED)
        self.assertNotIn('topic-1', self.new_slice)          # syllabus erased
        self.assertNotIn('res-1', self.new_slice)            # resources erased
        self.assertNotIn('cut-2024', self.new_slice)         # cutoffs erased
        self.assertIn('syllabus: []', self.new_slice)

    def test_b_inline_comments_are_lost(self):
        self.assertIn('// Authored by hand', AUTHORED)
        self.assertNotIn('// Authored by hand', self.new_slice)

    def test_c_shared_const_provenance_is_lost(self):
        # The authored record shares `...sscSyllabusSource`; the re-emit inlines provenance.
        self.assertIn('...sscSyllabusSource', AUTHORED)
        self.assertNotIn('...sscSyllabusSource', self.new_slice)
        self.assertNotIn('...sscNoticeProv', self.new_slice)

    def test_d_authored_ids_are_lost(self):
        self.assertIn("id: 'p-s1'", AUTHORED)
        self.assertNotIn("id: 'p-s1'", self.new_slice)       # authored provenance ids gone

    def test_e_the_loss_is_detectable_as_a_hash_change(self):
        before = fingerprint(AUTHORED)['exam-ssc-cgl-2026']
        after = fingerprint(self.after)['exam-ssc-cgl-2026']
        self.assertNotEqual(before, after)                   # the record's bytes changed


class TestAdditiveOverlayPreservesEverything(unittest.TestCase):
    """Part 2: prove the recommended pattern is non-destructive (the shape the runtime overlay
    `syllabus_revisions` / `resource_additions` already uses)."""

    def _apply_overlay(self, register: str, exam_id: str, overlay: list) -> tuple[str, list]:
        # The authored register is NOT edited. The machine fact lives beside it, keyed by exam.
        # (At runtime the frontend merges it — applySyllabusRevisions / additionToResource — over
        # the seed; here we only assert the seed is untouched and the fact is carried.)
        return register, [o for o in overlay if o['examId'] == exam_id]

    def setUp(self):
        self.overlay = [{
            'examId': 'exam-ssc-cgl-2026', 'domain': 'dates', 'kind': 'SUPERSEDE',
            'value': {'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2026-06-27'},
            'provenance': {'officialUrl': 'https://ssc.gov.in/notice',
                           'verificationLevel': 'OFFICIALLY_VERIFIED'},
            'supersedes': 'date-1',
        }]
        self.register_after, self.applied = self._apply_overlay(
            AUTHORED, 'exam-ssc-cgl-2026', self.overlay)

    def test_a_authored_record_is_byte_identical(self):
        before = fingerprint(AUTHORED)
        after = fingerprint(self.register_after)
        self.assertEqual(before['exam-ssc-cgl-2026'], after['exam-ssc-cgl-2026'])

    def test_b_comments_consts_arrays_ids_all_survive(self):
        s = _slice_text(self.register_after, 'exam-ssc-cgl-2026')
        for token in ('// Authored by hand', '...sscSyllabusSource', 'topic-1', 'topic-2',
                      'res-1', 'cut-2024', "id: 'p-s1'"):
            self.assertIn(token, s, f'overlay must not disturb {token!r}')

    def test_c_no_other_exam_mutated(self):
        before = fingerprint(AUTHORED)
        after = fingerprint(self.register_after)
        self.assertEqual(before['exam-upsc-cse-2026'], after['exam-upsc-cse-2026'])

    def test_d_the_machine_fact_is_carried_with_provenance_and_supersession(self):
        self.assertEqual(len(self.applied), 1)
        fact = self.applied[0]
        self.assertEqual(fact['value']['dateTimeStr'], '2026-06-27')      # new value present
        self.assertEqual(fact['provenance']['verificationLevel'], 'OFFICIALLY_VERIFIED')
        self.assertEqual(fact['supersedes'], 'date-1')                    # revision preserved, old kept


if __name__ == '__main__':
    unittest.main(verbosity=2)
