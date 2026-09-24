"""The production renderer + preservation-safe publish: the mandatory renderer cases.

The renderer itself (`exam_authoring.emit.render_exam`) is reused as-is — status-aware, honest
empties, provenance on every value, no exam branch. These tests prove the two things this phase
adds: (1) it is preservation-first — a partial build never overwrites an existing record, and an
existing populated array is left byte-identical; (2) a NEW exam publishes atomically through the
existing gate + publisher with every other exam byte-identical. Everything is offline; publish
tests write to a temp register (never the live one), typecheck disabled for speed.
"""
from __future__ import annotations

import io
import os
import tempfile
import unittest

from . import orchestrate as O
from . import publish as P
from . import render as R
from .gate import BuildState
from .test_orchestrate import _build, _rec, _temp_register, patch_build
from ..exam_authoring.emit import render_exam
from ..exam_authoring.record import Citation, ExamRecord, Field, Status


# --------------------------------------------------------------------------- render fixtures
def _renderable(exam_id='exam-newauth-clerk-2027', title='Newauth Clerk Examination',
                authority='Newauth Public Commission', domain='https://newauth.gov.in',
                dates_status=Status.FOUND):
    """A build record the emitter can render: identity + dates (+ an age band)."""
    rec = ExamRecord(exam_id=exam_id, code=exam_id.replace('exam-', '').upper().replace('-', '_'),
                     title=title, authority_name=authority, official_domain=domain)
    cit = Citation(document_title=f'{title}, 2027 — Notice', url=domain + '/notice', page=1,
                   excerpt=f'{title}, 2027. Applications are invited online.', verified_date='2027-01-01')
    rec.set(Field.found('officialName', title, cit))
    rec.set(Field.found('authority', authority, cit))
    rec.set(Field.found('applicationPortal', domain, cit))
    dates_val = [{'type': 'APPLICATION_CLOSE', 'label': 'Last date to apply',
                  'dateTimeStr': '2027-02-11 18:00', 'rawLabel': 'Last Date', 'rawValue': '11/02/2027'}]
    if dates_status is Status.NEEDS_REVIEW:
        rec.set(Field.needs_review('dates', dates_val, 'read from prose', cit))
    else:
        rec.set(Field.found('dates', dates_val, cit))
    rec.set(Field.found('ageLimits', {'minAge': 21, 'maxAge': 30, 'asOn': '2027-08-01'}, cit))
    return rec


class TestProductionRenderer(unittest.TestCase):

    # --- the reused renderer is status-aware and complete -----------------------------------
    def test_1_renderer_emits_all_required_exam_fields(self):
        ts = render_exam(_renderable())
        for field in ('id:', 'code:', 'title:', 'authorityName:', 'officialDomain:',
                      'crucialEligibilityDate:', 'isGoldenJourney:', 'isDemoData:',
                      'overviewDescription:', 'posts:', 'dates:', 'globalRuleGroup:', 'stages:',
                      'syllabus:', 'practiceQuestions:', 'corrigendums:', 'cutoffsHistory:',
                      'resources:', 'faqs:', 'applicationGuide:', 'roadmapTracks:'):
            self.assertIn(field, ts, f'missing required Exam field {field}')

    def test_2_verified_field_is_officially_verified(self):
        ts = render_exam(_renderable(dates_status=Status.FOUND))
        self.assertIn("'OFFICIALLY_VERIFIED'", ts)          # a FOUND field's provenance

    def test_3_needs_review_field_is_under_verification(self):
        # A NEEDS_REVIEW date must be badged UNDER_VERIFICATION, never official.
        ts = render_exam(_renderable(dates_status=Status.NEEDS_REVIEW))
        self.assertIn("'UNDER_VERIFICATION'", ts)

    def test_4_not_extracted_section_is_empty_not_invented(self):
        # syllabus/cutoffs/faqs were never extracted -> honest empty arrays, not fabricated.
        ts = render_exam(_renderable())
        self.assertIn('syllabus: []', ts)
        self.assertIn('cutoffsHistory: []', ts)
        self.assertIn('faqs: []', ts)

    def test_5_unknown_authority_renders_from_the_record(self):
        # A never-seen authority renders from its own record, no exam-specific branch.
        ts = render_exam(_renderable(exam_id='exam-zeta-clerk-2031', title='Zeta Clerk Examination',
                                     authority='Zeta Recruitment Board', domain='https://zeta.gov.in'))
        self.assertIn("id: 'exam-zeta-clerk-2031'", ts)
        self.assertIn('Zeta Recruitment Board', ts)

    def test_6_render_module_has_no_exam_specific_branch(self):
        import re
        with io.open(os.path.join(os.path.dirname(__file__), 'render.py'), encoding='utf-8') as fh:
            code = '\n'.join(l for l in fh.read().splitlines() if not l.strip().startswith('#'))
        for pat in (r"if\s+exam\s*==", r"if\s+authority\s*==", r"==\s*['\"]exam-",
                    r"['\"]SSC['\"]", r"['\"]UPSC['\"]", r"['\"]IBPS['\"]", r"['\"]APPSC['\"]"):
            self.assertIsNone(re.search(pat, code), f'forbidden branch {pat!r} in render.py')

    # --- preservation-first: never overwrite an existing record -----------------------------
    def test_7_partial_build_does_not_overwrite_existing(self):
        # Step 13: an existing exam with populated authored arrays; a partial build for the same
        # id must NOT overwrite it. The register is left byte-identical.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'data.ts')
            existing = (
                "export const SSC_EXAM: Exam = {\n"
                "  id: 'exam-ssc-cgl-2026',\n"
                "  title: 'SSC',\n"
                "  syllabus: [{ id: 'topic-1', label: 'Quant' }],\n"
                "  resources: [{ id: 'res-1', title: 'Notice' }],\n"
                "  cutoffsHistory: [{ id: 'cut-1' }],\n"
                "};\n\n"
                "export const ALL_EXAMS: Exam[] = [\n  SSC_EXAM\n];\n")
            io.open(path, 'w', encoding='utf-8', newline='').write(existing)
            before = io.open(path, encoding='utf-8').read()
            patch_build(self, lambda *a, **k: _build(_rec('exam-ssc-cgl-2026')))
            r = O.orchestrate('SSC CGL 2026', dry_run=False, data_ts=path, typecheck=False)
            self.assertEqual(r.state, O.OrchestrationState.PRESERVATION_BLOCKED)
            self.assertFalse(r.published)
            self.assertEqual(io.open(path, encoding='utf-8').read(), before)   # byte-identical

    def test_8_populated_array_survives_a_partial_build(self):
        # Step 7/14: the existing populated syllabus array is intact after a partial build.
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'data.ts')
            io.open(path, 'w', encoding='utf-8', newline='').write(
                "export const SSC_EXAM: Exam = {\n  id: 'exam-ssc-cgl-2026',\n"
                "  syllabus: [{ id: 'topic-1', label: 'Quant' }, { id: 'topic-2', label: 'Reasoning' }],\n};\n\n"
                "export const ALL_EXAMS: Exam[] = [\n  SSC_EXAM\n];\n")
            patch_build(self, lambda *a, **k: _build(_rec('exam-ssc-cgl-2026')))
            O.orchestrate('SSC CGL 2026', dry_run=False, data_ts=path, typecheck=False)
            after = io.open(path, encoding='utf-8').read()
            self.assertIn("topic-1", after)
            self.assertIn("topic-2", after)                 # not emptied

    def test_9_new_exam_publishes_atomically(self):
        # Step 12 (safe publish): a NEW exam id is appended and published atomically.
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026')])
            before = P.fingerprint(io.open(reg, encoding='utf-8').read())
            patch_build(self, lambda *a, **k: _build(_renderable('exam-newauth-clerk-2027',
                        'Newauth Clerk Examination', 'Newauth Public Commission', 'https://newauth.gov.in'),
                        year='2027'))
            r = O.orchestrate('Newauth Clerk 2027', year='2027', dry_run=False, data_ts=reg, typecheck=False)
            self.assertEqual(r.state, O.OrchestrationState.PUBLISHED)
            self.assertTrue(r.published)
            after = P.fingerprint(io.open(reg, encoding='utf-8').read())
            self.assertIn('exam-newauth-clerk-2027', after)          # appended
            for other in ('exam-ssc-cgl-2026', 'exam-upsc-cse-2026'):
                self.assertEqual(before[other], after[other])        # byte-identical

    def test_10_cross_exam_isolation_on_new_publish(self):
        # Step 15: publishing a new exam mutates no existing exam across all five.
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026'),
                                     ('IBPS_EXAM', 'exam-ibps-po-2026'), ('LIC_EXAM', 'exam-lic-aao-2027'),
                                     ('APPSC_EXAM', 'exam-appsc-group1-2026')])
            before = P.fingerprint(io.open(reg, encoding='utf-8').read())
            patch_build(self, lambda *a, **k: _build(_renderable(), year='2027'))
            r = O.orchestrate('Newauth Clerk 2027', year='2027', dry_run=False, data_ts=reg, typecheck=False)
            self.assertEqual(r.state, O.OrchestrationState.PUBLISHED)
            after = P.fingerprint(io.open(reg, encoding='utf-8').read())
            for e in before:
                self.assertEqual(before[e], after[e], f'{e} changed')

    # --- failure safety ---------------------------------------------------------------------
    def test_11_gate_block_never_publishes(self):
        # A NOT_EXTRACTED required field blocks; nothing is written even to a new id.
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('X_EXAM', 'exam-other-1')])
            before = io.open(reg, encoding='utf-8').read()
            patch_build(self, lambda *a, **k: _build(_rec('exam-newauth-clerk-2027',
                        statuses={'dates': Status.NOT_EXTRACTED})))
            r = O.orchestrate('Newauth 2027', dry_run=False, data_ts=reg, typecheck=False)
            self.assertEqual(r.state, O.OrchestrationState.BLOCKED_BY_GATE)
            self.assertEqual(io.open(reg, encoding='utf-8').read(), before)

    def test_12_isolation_violation_never_publishes(self):
        # An (explicit-overwrite) render that would ALSO add another exam is refused by the
        # publisher's isolation proof; the register is left byte-identical.
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026'), ('UPSC_EXAM', 'exam-upsc-cse-2026')])
            before = io.open(reg, encoding='utf-8').read()
            evil = lambda rec: ("export const SSC_EXAM: Exam = {\n  id: 'exam-ssc-cgl-2026',\n};\n\n"
                                "export const SNEAK_EXAM: Exam = {\n  id: 'exam-sneak-9',\n};")
            patch_build(self, lambda *a, **k: _build(_rec('exam-ssc-cgl-2026')))
            r = O.orchestrate('SSC CGL 2026', dry_run=False, data_ts=reg, typecheck=False,
                              allow_overwrite=True, render=evil)
            self.assertEqual(r.state, O.OrchestrationState.ISOLATION_VIOLATION)
            self.assertFalse(r.published)
            self.assertEqual(io.open(reg, encoding='utf-8').read(), before)

    def test_13_dry_run_never_publishes_a_new_exam(self):
        with tempfile.TemporaryDirectory() as d:
            reg = _temp_register(d, [('SSC_EXAM', 'exam-ssc-cgl-2026')])
            before = io.open(reg, encoding='utf-8').read()
            patch_build(self, lambda *a, **k: _build(_renderable(), year='2027'))
            r = O.orchestrate('Newauth Clerk 2027', year='2027', dry_run=True, data_ts=reg)
            self.assertEqual(r.state, O.OrchestrationState.STAGED)
            self.assertEqual(io.open(reg, encoding='utf-8').read(), before)


if __name__ == '__main__':
    unittest.main(verbosity=2)
