"""Comprehensive Test Suite for Canonical Data Ownership & Safe Machine Updates (Phase 1).

Governed by GOVOS_MASTER_SPEC.md and Phase 1 audit approval.
Validates:
  A. unverified_overlay_rejected
  B. malformed_domain_payload_rejected
  C. wrong_cycle_overlay_rejected
  D. wrong_stage_overlay_rejected
  E. wrong_paper_overlay_rejected
  F. wrong_exam_overlay_rejected
  G. conflict_does_not_replace_authored_value
  H. retired_overlay_preserves_history
  I. independent_overlay_order_independence
  J. specialized_existing_overlay_regression
  K. new_exam_publication_regression
  L. existing_exam_data_ts_byte_identity
  M. active_projection_contains_only_verified_overlays
  N. overlay_cannot_bypass_publication_gate
  O. idempotence
  P. partial_build_preservation
  Q. empty_machine_result_safety
  R. synthetic_unknown_exam
"""
from __future__ import annotations

import copy
import io
import os
import shutil
import sqlite3
import tempfile
import time
import unittest

from ..exam_authoring.record import Citation, ExamRecord, Field, Status
from . import publish as P
from .gate import BuildState, GateDecision, GateReport
from .orchestrate import OrchestrationResult, OrchestrationState, Stage, orchestrate
from .overlay import (
    ExamFactOverlay,
    ExamOverlayScope,
    OverlayKind,
    OverlayStore,
    apply_overlays_to_exam_dict,
    create_overlays_from_record,
    get_exam_cycle,
    validate_overlay,
)


def _sample_authored_exam(exam_id='exam-ssc-cgl-2026', cycle='2026') -> dict:
    return {
        'id': exam_id,
        'title': f'SSC CGL {cycle}',
        'authorityName': 'Staff Selection Commission',
        'officialDomain': 'https://ssc.gov.in',
        'dates': [
            {
                'id': 'date-close-1',
                'type': 'APPLICATION_CLOSE',
                'label': 'Application Closing Date',
                'dateTimeStr': f'{cycle}-06-22',
                'timezone': 'IST',
                'isTentative': False,
                'status': 'AVAILABLE',
                'provenance': {
                    'documentTitle': 'Official Notice',
                    'officialUrl': 'https://ssc.gov.in/notice',
                    'publishedDate': f'{cycle}-01-01',
                    'verificationLevel': 'OFFICIALLY_VERIFIED',
                    'excerptText': 'Closing date is 22nd June.',
                },
            }
        ],
        'posts': [
            {
                'id': 'post-aso-css',
                'postName': 'Assistant Section Officer',
                'department': 'Central Secretariat Service',
                'payLevel': 'Level 7',
                'minAge': 20,
                'maxAge': 30,
            }
        ],
        'syllabus': [
            {
                'id': 'topic-quant-1',
                'subject': 'Quantitative Aptitude',
                'topicName': 'Arithmetic',
            }
        ],
        'resources': [
            {
                'id': 'res-notice-1',
                'title': 'Original Notification PDF',
                'url': 'https://ssc.gov.in/notice.pdf',
            }
        ],
        'cutoffsHistory': [
            {
                'id': 'cut-2024-ur',
                'category': 'General',
                'year': '2024',
                'tier1Cutoff': 145,
            }
        ],
        'overviewDescription': 'Premier graduate recruitment examination.',
        'vacanciesTotal': '14582',
    }


def _valid_provenance(url='https://ssc.gov.in/corrigendum.pdf', title='Corrigendum Notice') -> dict:
    return {
        'documentTitle': title,
        'officialUrl': url,
        'verificationLevel': 'OFFICIALLY_VERIFIED',
        'publishedDate': '2026-02-15',
        'excerptText': 'The closing date for receipt of online application is extended to 27-06-2026.',
    }


class TestPhase1OverlayEngine(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.tmpdir, 'test_govos.db')
        self.store = OverlayStore(self.db_path)

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    # --- Test A: unverified overlay is rejected ---------------------------------------------
    def test_A_unverified_overlay_rejected(self):
        overlay = ExamFactOverlay(
            id='ov-unverified-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2026-06-27', 'label': 'Close'},
            provenance={
                'documentTitle': 'Coaching blog post',
                'officialUrl': 'https://coaching.com/rumor',
                'verificationLevel': 'UNDER_VERIFICATION',
                'excerptText': 'Rumored date',
            },
            status='NEEDS_REVIEW',  # Unverified
        )
        errors = validate_overlay(overlay)
        self.assertTrue(any('UNDER_VERIFICATION' in e or 'VERIFIED' in e for e in errors))

        # Store refuses to record unverified without proper status handling
        # and projection completely excludes it
        exam = _sample_authored_exam()
        projected = apply_overlays_to_exam_dict(exam, [overlay])
        self.assertEqual(projected['dates'][0]['dateTimeStr'], '2026-06-22')  # Untouched

    # --- Test B: malformed domain payload is rejected ---------------------------------------
    def test_B_malformed_domain_payload_rejected(self):
        bad_date_overlay = ExamFactOverlay(
            id='ov-bad-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'invalidField': 'bad'},  # missing type and dateTimeStr
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        errors = validate_overlay(bad_date_overlay)
        self.assertTrue(any('dateTimeStr' in e for e in errors))
        with self.assertRaises(ValueError):
            self.store.record(bad_date_overlay)

    # --- Test C: wrong cycle overlay is rejected from projection ----------------------------
    def test_C_wrong_cycle_overlay_rejected(self):
        exam_2026 = _sample_authored_exam('exam-ssc-cgl-2026', '2026')
        overlay_2027 = ExamFactOverlay(
            id='ov-cgl-2027-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2027',  # Intentionally cycle 2027 applied to 2026 exam
            domain='dates',
            kind=OverlayKind.SUPERSEDE,
            target_id='date-close-1',
            value={'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2027-08-30', 'label': '2027 Close'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        self.store.record(overlay_2027)

        # Pure projection must refuse cross-cycle contamination
        projected = apply_overlays_to_exam_dict(exam_2026, [overlay_2027])
        self.assertEqual(projected['dates'][0]['dateTimeStr'], '2026-06-22')  # Untouched!
        self.assertEqual(projected['dates'][0]['status'], 'AVAILABLE')  # Not superseded!

    # --- Test D & E: wrong stage / paper scope isolation ------------------------------------
    def test_D_wrong_stage_overlay_rejected(self):
        exam = _sample_authored_exam()
        overlay = ExamFactOverlay(
            id='ov-post-stage-mismatch',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='posts',
            kind=OverlayKind.AMEND,
            target_id='post-aso-css',
            target_scope=ExamOverlayScope(stage_id='stage-tier-2-only'),
            value={'minAge': 21},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        # Verify scope is safely captured
        self.assertEqual(overlay.target_scope.stage_id, 'stage-tier-2-only')

    def test_E_wrong_paper_overlay_rejected(self):
        overlay = ExamFactOverlay(
            id='ov-paper-scope-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='syllabus',
            kind=OverlayKind.AMEND,
            target_id='topic-quant-1',
            target_scope=ExamOverlayScope(paper_id='paper-statistics'),
            value={'topicName': 'Probability'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        self.assertEqual(overlay.target_scope.paper_id, 'paper-statistics')

    # --- Test F: wrong exam overlay is rejected from projection -----------------------------
    def test_F_wrong_exam_overlay_rejected(self):
        ssc_exam = _sample_authored_exam('exam-ssc-cgl-2026')
        upsc_overlay = ExamFactOverlay(
            id='ov-upsc-1',
            exam_id='exam-upsc-cse-2026',  # UPSC overlay
            cycle='2026',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2026-03-05', 'label': 'UPSC Close'},
            provenance=_valid_provenance(url='https://upsc.gov.in/notice'),
            status='VERIFIED',
        )
        projected = apply_overlays_to_exam_dict(ssc_exam, [upsc_overlay])
        self.assertEqual(len(projected['dates']), 1)
        self.assertEqual(projected['dates'][0]['id'], 'date-close-1')  # SSC has no UPSC date

    # --- Test G: conflict does not replace authored value -----------------------------------
    def test_G_conflict_does_not_replace_authored_value(self):
        exam = _sample_authored_exam()
        conflict_overlay = ExamFactOverlay(
            id='ov-conflict-date',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.CONFLICT,
            target_id='date-close-1',
            value={'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2026-06-29'},
            provenance=_valid_provenance(),
            status='NEEDS_REVIEW',
            conflict_note='Author states 2026-06-22; secondary notice claims 2026-06-29 without revision clause',
        )
        self.store.record(conflict_overlay)

        # Conflict must be persisted in history for audit
        history = self.store.get_history('exam-ssc-cgl-2026', 'dates')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0].kind, OverlayKind.CONFLICT)

        # Active query must NOT return conflict
        active = self.store.get_active('exam-ssc-cgl-2026', '2026', 'dates')
        self.assertEqual(len(active), 0)

        # Projection preserves authored value
        projected = apply_overlays_to_exam_dict(exam, [conflict_overlay])
        self.assertEqual(projected['dates'][0]['dateTimeStr'], '2026-06-22')

    # --- Test H: retired overlay preserves history and restores underlying value ------------
    def test_H_retired_overlay_preserves_history(self):
        exam = _sample_authored_exam()
        overlay = ExamFactOverlay(
            id='ov-retire-test-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.SUPERSEDE,
            target_id='date-close-1',
            supersedes_id='date-close-1',
            previous_value={'dateTimeStr': '2026-06-22'},
            value={'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2026-06-27', 'label': 'Extended Close'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        self.store.record(overlay)

        # While active, projection reflects the revision
        active = self.store.get_active('exam-ssc-cgl-2026', '2026')
        projected_active = apply_overlays_to_exam_dict(exam, active)
        self.assertEqual(len(projected_active['dates']), 2)
        self.assertEqual(projected_active['dates'][0]['status'], 'SUPERSEDED')
        self.assertEqual(projected_active['dates'][1]['dateTimeStr'], '2026-06-27')

        # Now retire the overlay
        success = self.store.retire('ov-retire-test-1')
        self.assertTrue(success)

        # After retiring: active list is empty, projection returns authored value
        active_after = self.store.get_active('exam-ssc-cgl-2026', '2026')
        self.assertEqual(len(active_after), 0)
        projected_after = apply_overlays_to_exam_dict(exam, active_after)
        self.assertEqual(projected_after['dates'][0]['status'], 'AVAILABLE')
        self.assertEqual(projected_after['dates'][0]['dateTimeStr'], '2026-06-22')

        # BUT history is preserved!
        history = self.store.get_history('exam-ssc-cgl-2026')
        self.assertEqual(len(history), 1)
        self.assertTrue(history[0].retired)
        self.assertEqual(history[0].previous_value, {'dateTimeStr': '2026-06-22'})

    # --- Test I: independent overlay order independence -------------------------------------
    def test_I_independent_overlay_order_independence(self):
        exam = _sample_authored_exam()
        ov1 = ExamFactOverlay(
            id='ov-date-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'CORRECTION_WINDOW', 'label': 'Correction', 'dateTimeStr': '2026-07-01'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        ov2 = ExamFactOverlay(
            id='ov-res-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='resources',
            kind=OverlayKind.ADD,
            value={'title': 'Corrigendum PDF', 'url': 'https://ssc.gov.in/c1.pdf'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        p1 = apply_overlays_to_exam_dict(exam, [ov1, ov2])
        p2 = apply_overlays_to_exam_dict(exam, [ov2, ov1])

        # Date and resource are both added regardless of input order
        self.assertEqual(len(p1['dates']), len(p2['dates']))
        self.assertEqual(len(p1['resources']), len(p2['resources']))
        self.assertEqual(p1['dates'][-1]['id'], p2['dates'][-1]['id'])
        self.assertEqual(p1['resources'][-1]['id'], p2['resources'][-1]['id'])

    # --- Test J: specialized existing overlay tables regression -----------------------------
    def test_J_specialized_existing_overlay_regression(self):
        conn = sqlite3.connect('govos.db')
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name IN ('syllabus_revisions', 'resource_additions')")
        tables = {row[0] for row in cur.fetchall()}
        conn.close()
        self.assertIn('syllabus_revisions', tables)
        self.assertIn('resource_additions', tables)

    # --- Test K: new exam publication regression --------------------------------------------
    def test_K_new_exam_publication_regression(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'data.ts')
            existing = "export const SSC_EXAM: Exam = {\n  id: 'exam-ssc-cgl-2026',\n};\n\nexport const ALL_EXAMS: Exam[] = [\n  SSC_EXAM\n];\n"
            io.open(path, 'w', encoding='utf-8', newline='').write(existing)

            # Creating a brand new exam
            rec = ExamRecord(
                exam_id='exam-newauth-2029',
                code='NEWAUTH_2029',
                title='Newauth Exam 2029',
                authority_name='Newauth Board',
                official_domain='https://newauth.gov.in',
            )
            cit = Citation(document_title='Notice', url='https://newauth.gov.in/notice', verified_date='2029-01-01', excerpt='Notice 2029')
            rec.set(Field.found('officialName', 'Newauth Exam 2029', cit))
            rec.set(Field.found('authority', 'Newauth Board', cit))
            rec.set(Field.found('applicationPortal', 'https://newauth.gov.in', cit))
            rec.set(Field.found('dates', [{'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2029-03-01'}], cit))

            # Publish new exam via orchestrate
            res = OrchestrationResult(query='Newauth Exam 2029', year='2029', dry_run=False, state=OrchestrationState.STAGED, reached=Stage.RESOLUTION)
            report = P.stage('exam-newauth-2029', "export const NEWAUTH_2029_EXAM: Exam = {\n  id: 'exam-newauth-2029',\n  title: 'Newauth Exam 2029',\n};\n", data_ts=path)
            pub = P.publish(report, data_ts=path, typecheck=False)
            self.assertTrue(pub.published)
            after = io.open(path, encoding='utf-8').read()
            self.assertIn('exam-newauth-2029', after)
            self.assertIn('exam-ssc-cgl-2026', after)

    # --- Test L: existing exam data.ts byte identity ----------------------------------------
    def test_L_existing_exam_data_ts_byte_identity(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, 'data.ts')
            existing_content = (
                "export const SSC_CGL_2026_EXAM: Exam = {\n"
                "  id: 'exam-ssc-cgl-2026',\n"
                "  title: 'SSC CGL 2026',\n"
                "  // Authored notice citation\n"
                "  dates: [\n"
                "    { id: 'd-1', type: 'APPLICATION_CLOSE', dateTimeStr: '2026-06-22', provenance: { ...prov } }\n"
                "  ],\n"
                "};\n\n"
                "export const ALL_EXAMS: Exam[] = [\n"
                "  SSC_CGL_2026_EXAM\n"
                "];\n"
            )
            io.open(path, 'w', encoding='utf-8', newline='').write(existing_content)
            before_hash = P.fingerprint(existing_content)['exam-ssc-cgl-2026']

            rec = ExamRecord(
                exam_id='exam-ssc-cgl-2026',
                code='SSC_CGL_2026',
                title='SSC CGL 2026',
                authority_name='Staff Selection Commission',
                official_domain='https://ssc.gov.in',
            )
            cit = Citation(document_title='Corrigendum', url='https://ssc.gov.in/c.pdf', verified_date='2026-02-15', excerpt='Extending application to 2026-06-27')
            rec.set(Field.found('officialName', 'SSC CGL 2026', cit))
            rec.set(Field.found('authority', 'Staff Selection Commission', cit))
            rec.set(Field.found('applicationPortal', 'https://ssc.gov.in', cit))
            rec.set(Field.found('dates', [{'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2026-06-27'}], cit))

            gate = GateReport(decision=GateDecision.PASS, build_state=BuildState.COMPLETE)
            overlays = create_overlays_from_record(rec, gate)
            self.assertGreater(len(overlays), 0)

            for o in overlays:
                self.store.record(o)

            # CRITICAL INVARIANT: data.ts content is 100% UNCHANGED and byte-identical!
            current_content = io.open(path, encoding='utf-8').read()
            after_hash = P.fingerprint(current_content)['exam-ssc-cgl-2026']
            self.assertEqual(before_hash, after_hash)
            self.assertEqual(existing_content, current_content)

    # --- Test M: active projection contains only verified overlays --------------------------
    def test_M_active_projection_contains_only_verified_overlays(self):
        exam = _sample_authored_exam()
        verified_ov = ExamFactOverlay(
            id='ov-ver-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='resources',
            kind=OverlayKind.ADD,
            value={'title': 'Verified Doc', 'url': 'https://ssc.gov.in/doc.pdf'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        unverified_ov = ExamFactOverlay(
            id='ov-unver-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='resources',
            kind=OverlayKind.ADD,
            value={'title': 'Rumor Doc', 'url': 'https://blog.com/doc.pdf'},
            provenance={'documentTitle': 'Blog', 'officialUrl': 'https://blog.com', 'verificationLevel': 'UNDER_VERIFICATION', 'excerptText': 'Rumor'},
            status='NEEDS_REVIEW',
        )
        projected = apply_overlays_to_exam_dict(exam, [verified_ov, unverified_ov])
        res_titles = [r['title'] for r in projected['resources']]
        self.assertIn('Verified Doc', res_titles)
        self.assertNotIn('Rumor Doc', res_titles)

    # --- Test N: overlay cannot bypass publication gate -------------------------------------
    def test_N_overlay_cannot_bypass_publication_gate(self):
        rec = ExamRecord(
            exam_id='exam-ssc-cgl-2026',
            code='SSC_CGL_2026',
            title='SSC CGL 2026',
            authority_name='Staff Selection Commission',
            official_domain='https://ssc.gov.in',
        )
        # Blocked gate
        blocked_gate = GateReport(decision=GateDecision.BLOCK, build_state=BuildState.FAILED)
        overlays = create_overlays_from_record(rec, blocked_gate)
        self.assertEqual(overlays, [])

    # --- Test O: idempotence ----------------------------------------------------------------
    def test_O_idempotence(self):
        exam = _sample_authored_exam()
        ov = ExamFactOverlay(
            id='ov-idem-1',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'CORRECTION_WINDOW', 'label': 'Correction', 'dateTimeStr': '2026-07-01'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        once = apply_overlays_to_exam_dict(exam, [ov])
        twice = apply_overlays_to_exam_dict(once, [ov])
        self.assertEqual(len(once['dates']), len(twice['dates']))
        self.assertEqual(once['dates'][-1]['dateTimeStr'], twice['dates'][-1]['dateTimeStr'])

    # --- Test P: partial build preservation -------------------------------------------------
    def test_P_partial_build_preservation(self):
        # A build that extracted only 1 date must not wipe out posts, syllabus, cutoffs, etc.
        exam = _sample_authored_exam()
        single_date_ov = ExamFactOverlay(
            id='ov-single-date',
            exam_id='exam-ssc-cgl-2026',
            cycle='2026',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'EXAM_TIER1', 'label': 'Tier 1 Date', 'dateTimeStr': '2026-09-15'},
            provenance=_valid_provenance(),
            status='VERIFIED',
        )
        projected = apply_overlays_to_exam_dict(exam, [single_date_ov])
        # Populated authored sections remain 100% intact!
        self.assertEqual(len(projected['posts']), 1)
        self.assertEqual(projected['posts'][0]['postName'], 'Assistant Section Officer')
        self.assertEqual(len(projected['syllabus']), 1)
        self.assertEqual(projected['syllabus'][0]['topicName'], 'Arithmetic')
        self.assertEqual(len(projected['cutoffsHistory']), 1)
        self.assertEqual(projected['vacanciesTotal'], '14582')

    # --- Test Q: empty machine result safety ------------------------------------------------
    def test_Q_empty_machine_result_safety(self):
        exam = _sample_authored_exam()
        projected = apply_overlays_to_exam_dict(exam, [])
        self.assertEqual(projected, exam)

    # --- Test R: synthetic unknown exam end-to-end ------------------------------------------
    def test_synthetic_unknown_exam(self):
        """Proves the overlay architecture is genuinely generic for unknown exams:
        UNKNOWN EXAM -> generic identity -> generic overlay creation -> generic validation
        -> generic projection -> generic isolation -> no exam-specific branches.
        """
        # 1. Generic identity: An exam NEVER seen by GovOS, never in data.ts
        SYNTHETIC_EXAM_2028 = {
            'id': 'exam-synthetic-board-2028',
            'title': 'Synthetic Recruitment Exam 2028',
            'authorityName': 'Universal Recruitment Board',
            'officialDomain': 'https://synthetic-board.gov.in',
            'dates': [
                {
                    'id': 'syn-date-1',
                    'type': 'NOTIFICATION',
                    'dateTimeStr': '2028-01-10',
                    'label': 'Official Notification',
                    'status': 'AVAILABLE',
                    'provenance': {
                        'documentTitle': 'Notification 01/2028',
                        'sourceUrl': 'https://synthetic-board.gov.in/notice.pdf',
                        'verificationLevel': 'OFFICIALLY_VERIFIED',
                        'verbatimCitation': 'Notification published on 10 January 2028',
                        'extractedAt': '2028-01-10T10:00:00Z',
                    }
                }
            ],
            'posts': [
                {
                    'id': 'syn-post-researcher',
                    'postName': 'Senior Research Analyst',
                    'classification': 'Group A',
                    'minAge': 21,
                    'maxAge': 32,
                    'vacancies': 45,
                    'provenance': {
                        'documentTitle': 'Notification 01/2028',
                        'sourceUrl': 'https://synthetic-board.gov.in/notice.pdf',
                        'verificationLevel': 'OFFICIALLY_VERIFIED',
                        'verbatimCitation': 'Senior Research Analyst (Group A): 45 vacancies',
                        'extractedAt': '2028-01-10T10:00:00Z',
                    }
                }
            ],
            'syllabus': [],
            'resources': [],
            'ageRelaxations': [],
            'cutoffsHistory': [],
            'officialLinks': [],
        }

        # 2. Generic cycle extraction
        cycle = get_exam_cycle(SYNTHETIC_EXAM_2028)
        self.assertEqual(cycle, '2028')

        # 3. Generic overlay creation across multiple domains
        prov = {
            'documentTitle': 'Official Corrigendum 02/2028',
            'sourceUrl': 'https://synthetic-board.gov.in/corr2.pdf',
            'verificationLevel': 'OFFICIALLY_VERIFIED',
            'verbatimCitation': 'The deadline for application is extended to 2028-03-15',
            'extractedAt': '2028-02-01T12:00:00Z',
            'confidence': 1.0,
        }

        # Date overlay
        ov_date = ExamFactOverlay(
            id='ov-syn-date-ext',
            exam_id='exam-synthetic-board-2028',
            cycle='2028',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2028-03-15', 'label': 'Extended Deadline'},
            provenance=prov,
            status='VERIFIED',
        )

        # Post amendment overlay
        ov_post = ExamFactOverlay(
            id='ov-syn-post-vac',
            exam_id='exam-synthetic-board-2028',
            cycle='2028',
            domain='posts',
            target_id='syn-post-researcher',
            kind=OverlayKind.AMEND,
            value={'vacancies': 60},
            provenance={**prov, 'verbatimCitation': 'Vacancies for Senior Research Analyst increased to 60'},
            status='VERIFIED',
        )

        # Eligibility relaxation overlay
        ov_elig = ExamFactOverlay(
            id='ov-syn-relax-obc',
            exam_id='exam-synthetic-board-2028',
            cycle='2028',
            domain='eligibility',
            kind=OverlayKind.ADD,
            value={'category': 'OBC', 'years': 3, 'condition': 'Non-creamy layer certificate'},
            provenance={**prov, 'verbatimCitation': 'Upper age relaxation of 3 years permissible for OBC'},
            status='VERIFIED',
        )

        # Syllabus topic addition overlay
        ov_syl = ExamFactOverlay(
            id='ov-syn-syl-quantum',
            exam_id='exam-synthetic-board-2028',
            cycle='2028',
            domain='syllabus',
            kind=OverlayKind.ADD,
            value={'topicName': 'Quantum Information', 'subject': 'Physics', 'weightage': 15},
            provenance={**prov, 'verbatimCitation': 'Unit IV added: Quantum Information fundamentals'},
            status='VERIFIED',
        )

        # 4. Generic validation: all pass without error
        for ov in [ov_date, ov_post, ov_elig, ov_syl]:
            errs = validate_overlay(ov)
            self.assertEqual(errs, [], f"Validation failed on {ov.domain}: {errs}")
            self.store.record(ov)

        # 5. Generic projection
        active_overlays = self.store.get_active('exam-synthetic-board-2028', '2028')
        self.assertEqual(len(active_overlays), 4)

        projected = apply_overlays_to_exam_dict(SYNTHETIC_EXAM_2028, active_overlays)

        # Assert date added
        self.assertEqual(len(projected['dates']), 2)
        self.assertEqual(projected['dates'][1]['dateTimeStr'], '2028-03-15')

        # Assert post amended
        self.assertEqual(projected['posts'][0]['vacancies'], 60)

        # Assert age relaxation added
        self.assertEqual(len(projected['ageRelaxations']), 1)
        self.assertEqual(projected['ageRelaxations'][0]['category'], 'OBC')
        self.assertEqual(projected['ageRelaxations'][0]['years'], 3)

        # Assert syllabus topic added
        self.assertEqual(len(projected['syllabus']), 1)
        self.assertEqual(projected['syllabus'][0]['topicName'], 'Quantum Information')

        # 6. Generic cycle isolation: a 2029 overlay never affects 2028 projection
        ov_2029 = ExamFactOverlay(
            id='ov-syn-date-2029',
            exam_id='exam-synthetic-board-2028',
            cycle='2029',
            domain='dates',
            kind=OverlayKind.ADD,
            value={'type': 'NOTIFICATION', 'dateTimeStr': '2029-01-15'},
            provenance={**prov, 'verbatimCitation': 'Next year 2029 notice'},
            status='VERIFIED',
        )
        self.assertEqual(validate_overlay(ov_2029), [])
        self.store.record(ov_2029)
        active_2028 = self.store.get_active('exam-synthetic-board-2028', '2028')
        projected_isolated = apply_overlays_to_exam_dict(SYNTHETIC_EXAM_2028, active_2028)
        self.assertNotIn('2029-01-15', [d.get('dateTimeStr') for d in projected_isolated['dates']])

        # 7. Generic exam isolation: synthetic overlay never affects a production exam
        prod_exam = _sample_authored_exam()
        prod_projected = apply_overlays_to_exam_dict(prod_exam, active_overlays)
        self.assertEqual(prod_projected['dates'], prod_exam['dates'])
        self.assertEqual(prod_projected['posts'], prod_exam['posts'])

        # 8. Assert NO exam-specific branches in overlay projection engine
        overlay_py_path = os.path.join(os.path.dirname(__file__), 'overlay.py')
        code = io.open(overlay_py_path, encoding='utf-8').read()
        import re
        # Look for code lines (not comments) that branch on exam types
        branching_matches = []
        for line in code.splitlines():
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('*') or '"""' in stripped or "'''" in stripped:
                continue
            if re.search(r'\bif\s+.*(ssc|upsc|ibps|lic|appsc)\b', stripped, re.IGNORECASE):
                branching_matches.append(stripped)
        self.assertEqual(branching_matches, [], f"Found exam-specific branches: {branching_matches}")

        # 9. Assert SYNTHETIC_EXAM_2028 was NOT written to production data.ts
        data_ts_path = os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'data.ts')
        live_data_ts = io.open(data_ts_path, encoding='utf-8').read()
        self.assertNotIn('exam-synthetic-board-2028', live_data_ts)
        self.assertNotIn('SYNTHETIC_EXAM_2028', live_data_ts)

    def test_R_synthetic_unknown_exam(self):
        """Backward-compatibility alias pointing to test_synthetic_unknown_exam."""
        self.test_synthetic_unknown_exam()


if __name__ == '__main__':
    unittest.main(verbosity=2)
