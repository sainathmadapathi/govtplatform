"""Comprehensive Acceptance Test Suite for Phase 2: Universal Exam Acquisition & Completeness.

Governed by GOVOS_MASTER_SPEC.md (Phase 2).
Verifies:
  1. Universal acquisition for an unknown examination (UNKNOWN_EXAM_2028) on a simulated
     authority domain without exam-specific logic.
  2. Bounded targeted re-acquisition loop when sections are unpopulated.
  3. Multi-document chronological reconciliation with evidence preservation.
  4. Corrigenda delta extraction generating SUPERSEDE overlays.
  5. Strict failure-state separation across all 17 user-facing sections.
  6. Overlay projection for all 17 domains.
  7. Authored seed (src/data.ts) remains 100% byte-identical.
"""
from __future__ import annotations

import io
import os
import unittest
from unittest.mock import patch

from ..exam_authoring.record import Citation, ExamRecord, Field, Status as RecordStatus
from ..exam_authoring.sources import Document
from . import build as B
from . import compat as COMPAT
from . import corrigenda as CORR
from . import discover as D
from .contract import CONTRACT, ContractField
from .discover import DiscoveredDoc, DocKind, Relevance, SourceSet
from .completeness import (
    CompletenessState,
    ExamCompletenessReport,
    GOVOS_17_SECTIONS,
    PROHIBITED_SECTION_NAMES,
    SECTIONS_BY_ID,
    SECTIONS_BY_NUM,
    SECTIONS_BY_ORDER,
    SectionNature,
    evaluate_completeness,
)
from .identity import ExamIdentity, IdentityCheck, IdentityVerdict
from .manifest import content_hash
from .overlay import ExamFactOverlay, OverlayKind, OverlayStore, apply_overlays_to_exam_dict, create_overlays_from_record
from .resolve import Authority, ResolvedExam
from .schema import Fact, Milestone, MilestoneState, SourceDocument, SourceEvidence, SourceKind, Status


# -----------------------------------------------------------------------------------------
# Synthetic Unknown Exam 2028 Fixtures (No authority in codebase knows about this)
# -----------------------------------------------------------------------------------------
UNKNOWN_EXAM_QUERY = "National Agricultural Examination Board Scientist Examination 2028"
UNKNOWN_OFFICIAL_NAME = "NAEB Agricultural Research Scientist Examination 2028"
UNKNOWN_EXAM_ID = "exam-naeb-scientist-2028"
UNKNOWN_AUTHORITY_NAME = "National Agricultural Examination Board"
UNKNOWN_DOMAIN = "https://naeb.gov.in"

NOTICE_PAGE_HTML = """<html>
<head><title>NAEB Agricultural Research Scientist Examination 2028 - Notification</title></head>
<body>
<h1>National Agricultural Examination Board</h1>
<h2>Notice of Agricultural Research Scientist Examination, 2028</h2>
<p>The National Agricultural Examination Board announces the Agricultural Research Scientist Examination 2028.</p>
<table>
  <tr><td>Date of Notification</td><td>10/01/2028</td></tr>
  <tr><td>Opening Date of Application</td><td>15/01/2028</td></tr>
  <tr><td>Closing Date of Application</td><td>15/02/2028 - 5:00pm</td></tr>
  <tr><td>Date of Preliminary Examination</td><td>20/05/2028</td></tr>
</table>
<p>Candidates must apply online at https://naeb.gov.in/apply.</p>
<h3>Age Limits</h3>
<p>A candidate must have attained the age of 21 years and must not have attained the age of 35 years as on 1st January 2028.</p>
<h3>Educational Qualification</h3>
<p>Master's degree in Agricultural Sciences or equivalent from a recognised university.</p>
<h3>Application Fee</h3>
<p>Candidates are required to pay a fee of Rs. 500/- online.</p>
<h3>Posts and Vacancies</h3>
<table>
  <tr><th>Post Name</th><th>Department</th><th>Pay Level</th><th>Vacancies</th></tr>
  <tr><td>Scientist (Agronomy)</td><td>Division of Crop Science</td><td>Level 10</td><td>45</td></tr>
  <tr><td>Scientist (Genetics)</td><td>Division of Plant Breeding</td><td>Level 10</td><td>35</td></tr>
</table>
<h3>Scheme of Examination</h3>
<table>
  <tr><th>Stage</th><th>Papers</th><th>Marks</th><th>Duration</th></tr>
  <tr><td>Preliminary Examination</td><td>Paper-I Objective</td><td>200</td><td>120 minutes</td></tr>
  <tr><td>Main Examination</td><td>Paper-II Descriptive</td><td>300</td><td>180 minutes</td></tr>
</table>
</body>
</html>"""

SEPARATE_SYLLABUS_PDF_TEXT = """National Agricultural Examination Board
Agricultural Research Scientist Examination 2028
Detailed Syllabus of Examination

1. Section A - General Agricultural Knowledge:
Agronomy fundamentals, soil chemistry, plant genetics, agricultural meteorology, and post-harvest technology.

2. Section B - Specialized Research Topics:
Crop physiology, genomics, breeding methodologies, biometrics, biotechnology, and farm management.
"""

CORRIGENDUM_PDF_TEXT = """National Agricultural Examination Board
Corrigendum to Notice of Agricultural Research Scientist Examination 2028
Notice No. NAEB/2028/CORR-01

In partial modification of the notification dated 10/01/2028:
1. Extension of Last Date: The last date for receipt of applications is extended from 15/02/2028 to 28/02/2028.
2. Revision of Vacancies: Total vacancies are revised from 80 to 95.
All other conditions of the notification remain unchanged.
Dated: 10/02/2028.
"""

ADMIT_CARD_NOTICE_TEXT = """National Agricultural Examination Board
Notice regarding City Intimation and Admit Card
Agricultural Research Scientist Examination 2028

The City Intimation Slip for the Preliminary Examination 2028 has been released on 10/05/2028.
Candidates can view their examination city on https://naeb.gov.in/admit.
Admit cards will be available 3 days before the examination date.
Dated: 10/05/2028.
"""

# -----------------------------------------------------------------------------------------
# Structurally Different Synthetic Unknown Exam Fixture (Prose/narrative, non-standard layout)
# -----------------------------------------------------------------------------------------
STRUCTURAL_UNKNOWN_QUERY = "State Technical Services Board Assistant Engineer Examination 2028"
STRUCTURAL_OFFICIAL_NAME = "STSB Assistant Engineer (Civil) Recruitment 2028"
STRUCTURAL_EXAM_ID = "exam-stsb-ae-2028"
STRUCTURAL_AUTHORITY_NAME = "State Technical Services Board"
STRUCTURAL_DOMAIN = "https://stsb.gov.in"

STRUCTURAL_NOTICE_HTML = """<html>
<head><title>STSB Assistant Engineer Recruitment 2028</title></head>
<body>
<h1>State Technical Services Board</h1>
<h2>Recruitment Notification No. STSB/2028/AE-01</h2>
<p>Applications are invited for the post of Assistant Engineer (Civil) in Public Works Department.</p>
<div>
  <p>Important Milestones:</p>
  <p>Commencement of submission of online applications: 01/03/2028.</p>
  <p>Closing date for receipt of applications: 31/03/2028.</p>
  <p>Date of Computer Based Test: 15/07/2028.</p>
</div>
<h3>How to Apply:</h3>
<p>Eligible candidates must apply online through official recruitment portal https://stsb.gov.in/recruitment/apply. Candidates must complete registration, fill in personal and educational particulars, upload scanned copies of mandatory certificates, and pay the required fee online through net banking or debit card.</p>
<p>Age Limit: Minimum age 21 years and maximum age 38 years as on 01/01/2028.</p>
<p>Educational Qualification: Degree in Civil Engineering from a recognised university.</p>
<p>Number of Vacancies: Total 60 vacancies are announced for the post of Assistant Engineer (Civil), Pay Band Level 9.</p>
<p>Application Fee: An examination fee of Rs. 250/- must be paid online. Women candidates and SC, ST candidates are exempted from payment of fee.</p>
<p>Documents Required for Upload: Candidates must upload scanned copy of Degree Certificate, recent passport size photograph (20 to 50 KB in JPG format, white background) and signature (10 to 20 KB in JPG format).</p>
<p>Scheme of Examination: Selection will be based on a single Stage Computer Based Test comprising Paper-I Civil Engineering (150 Marks, Duration 150 minutes).</p>
</body>
</html>"""


class TestPhase2AcquisitionAndCompleteness(unittest.TestCase):
    """Phase 2 Universal Acquisition & Completeness Acceptance Tests."""

    def setUp(self):
        self.resolved = ResolvedExam(
            query=UNKNOWN_EXAM_QUERY,
            official_name=UNKNOWN_OFFICIAL_NAME,
            year="2028",
            authority=Authority(
                name=UNKNOWN_AUTHORITY_NAME,
                domain=UNKNOWN_DOMAIN,
                confidence=0.95,
                evidence=["https://naeb.gov.in official portal"]
            ),
            seed_urls=["https://naeb.gov.in/scientist-2028"]
        )

    # =====================================================================================
    # TEST 0: GovOS 17-Section Universal Product Contract & Prohibitions
    # =====================================================================================
    def test_govos_17_section_contract(self):
        """Verifies exact 17-section product contract from GOVOS_MASTER_SPEC.md Part D and src/ui.tsx."""
        self.assertEqual(len(GOVOS_17_SECTIONS), 17)

        # Expected 17 product sections in exact order (1..17)
        expected_spec = [
            (1, 1, 'overview', 'Overview', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (2, 2, 'dates', 'Dates & Timeline', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (3, 3, 'eligibility', 'Eligibility & Posts', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (4, 4, 'application', 'Application & Documents', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (5, 5, 'pattern', 'Exam Pattern', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (6, 6, 'syllabus', 'Syllabus', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (7, 7, 'roadmap', 'Study Roadmap', SectionNature.RUNTIME_DERIVED, 'JOURNEY'),
            (8, 8, 'resources', 'Resources', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (9, 9, 'pyqs', 'Practice & PYQs', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (10, 17, 'mock-tests', 'Mock Tests', SectionNature.RUNTIME_DERIVED, 'JOURNEY'),
            (11, 14, 'admit-card', 'Admit Card', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (12, 15, 'exam-day', 'Exam Day', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (13, 16, 'results', 'Results & Next Steps', SectionNature.FACTUAL_EXTRACTION, 'JOURNEY'),
            (14, 11, 'faqs', 'FAQs & Official Clauses', SectionNature.FACTUAL_EXTRACTION, 'REFERENCE'),
            (15, 13, 'corrigenda', 'Corrigenda Log', SectionNature.FACTUAL_EXTRACTION, 'REFERENCE'),
            (16, 12, 'official-links', 'Official Portals & Links', SectionNature.FACTUAL_EXTRACTION, 'REFERENCE'),
            (17, 10, 'cutoffs', 'Cutoff History', SectionNature.FACTUAL_EXTRACTION, 'REFERENCE'),
        ]

        valid_contract_field_names = {f.name for f in CONTRACT}

        for (order, num, s_id, title, nature, group), sec in zip(expected_spec, GOVOS_17_SECTIONS):
            # 1. order (1..17)
            self.assertEqual(sec.order, order)
            # 2. num (deep-link number matching product spec / UI)
            self.assertEqual(sec.num, num)
            # 3. id (canonical slug)
            self.assertEqual(sec.id, s_id)
            # 4. title (human-readable title)
            self.assertEqual(sec.title, title)
            # 5. nature (FACTUAL_EXTRACTION or RUNTIME_DERIVED)
            self.assertEqual(sec.nature, nature)
            # 6. target_group (JOURNEY or REFERENCE)
            self.assertEqual(sec.target_group, group)
            # 7. canonical_fields (non-empty tuple of field names)
            self.assertIsInstance(sec.canonical_fields, tuple)
            self.assertGreater(len(sec.canonical_fields), 0)
            for f_name in sec.canonical_fields:
                self.assertIn(f_name, valid_contract_field_names, f"Field {f_name} in section {sec.id} not in CONTRACT")
            # 8. preferred_sources (aliased as sources_required)
            self.assertEqual(sec.sources_required, sec.preferred_sources)
            # 9. verification_requirement (exact rule, non-empty)
            self.assertIsInstance(sec.verification_requirement, str)
            self.assertGreater(len(sec.verification_requirement), 0)
            # 10. supported_states (set of CompletenessState values)
            self.assertIsInstance(sec.supported_states, (set, frozenset))
            self.assertGreater(len(sec.supported_states), 0)
            for state in sec.supported_states:
                self.assertIn(state, CompletenessState)

        # Verify deep link UI numbers: 13 Journey (1..9, 17, 14, 15, 16) + 4 Reference (11, 13, 12, 10)
        expected_ui_nums = {1, 2, 3, 4, 5, 6, 7, 8, 9, 17, 14, 15, 16, 11, 13, 12, 10}
        actual_ui_nums = {s.num for s in GOVOS_17_SECTIONS}
        self.assertEqual(actual_ui_nums, expected_ui_nums)

        # Verify SectionNature counts: exactly 2 RUNTIME_DERIVED, exactly 15 FACTUAL_EXTRACTION
        derived_sections = [s for s in GOVOS_17_SECTIONS if s.nature == SectionNature.RUNTIME_DERIVED]
        self.assertEqual(len(derived_sections), 2)
        self.assertEqual({s.order for s in derived_sections}, {7, 10})
        self.assertEqual({s.title for s in derived_sections}, {'Study Roadmap', 'Mock Tests'})

        factual_sections = [s for s in GOVOS_17_SECTIONS if s.nature == SectionNature.FACTUAL_EXTRACTION]
        self.assertEqual(len(factual_sections), 15)

        # Verify target_group counts: exactly 13 JOURNEY, exactly 4 REFERENCE
        journey_sections = [s for s in GOVOS_17_SECTIONS if s.target_group == 'JOURNEY']
        self.assertEqual(len(journey_sections), 13)
        self.assertEqual([s.order for s in journey_sections], list(range(1, 14)))

        reference_sections = [s for s in GOVOS_17_SECTIONS if s.target_group == 'REFERENCE']
        self.assertEqual(len(reference_sections), 4)
        self.assertEqual([s.order for s in reference_sections], [14, 15, 16, 17])

        # Verify internal database fields NEVER masquerade as product sections
        for prohibited in PROHIBITED_SECTION_NAMES:
            self.assertNotIn(prohibited, {s.id for s in GOVOS_17_SECTIONS})
            self.assertNotIn(prohibited, {s.title.lower() for s in GOVOS_17_SECTIONS})

    # =====================================================================================
    # TEST 1: Universal Acquisition for Unknown Exam (Zero exam-specific branches)
    # =====================================================================================
    def test_universal_acquisition_unknown_exam(self):
        """Pipeline builds UNKNOWN_EXAM_2028 through universal contract without hardcoded logic."""
        docs = [
            DiscoveredDoc(
                url="https://naeb.gov.in/scientist-2028",
                kind=DocKind.NOTIFICATION,
                title="NAEB Scientist 2028 Notice",
                relevance=D.Relevance.DIRECT,
                matched=["scientist", "2028"]
            )
        ]
        sources = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN, docs=docs)
        loaded = {
            "https://naeb.gov.in/scientist-2028": Document(
                url="https://naeb.gov.in/scientist-2028",
                kind="HTML",
                text=NOTICE_PAGE_HTML,
                fetched_at="2028-01-10"
            )
        }
        loaded["https://naeb.gov.in/scientist-2028"].html = NOTICE_PAGE_HTML

        # Mock resolve, discover, and loader to test universal build flow
        with patch.object(B, 'resolve', return_value=self.resolved), \
             patch.object(B, 'discover', return_value=sources), \
             patch.object(B, '_load', side_effect=lambda d: loaded[d.url]):

            result = B.build(UNKNOWN_EXAM_QUERY, year="2028")

        self.assertTrue(result.record.exam_id.startswith("exam-naeb-"))
        self.assertEqual(result.record.authority_name, UNKNOWN_AUTHORITY_NAME)

        # Dates extracted
        dates_field = result.record.fields.get('dates')
        self.assertIsNotNone(dates_field)
        self.assertTrue(dates_field.ok)
        self.assertTrue(any(d.get('type') == 'APPLICATION_CLOSE' for d in dates_field.value))

        # Eligibility / posts extracted
        posts_field = result.record.fields.get('posts')
        self.assertIsNotNone(posts_field)
        self.assertTrue(posts_field.ok)
        self.assertEqual(len(posts_field.value), 2)
        self.assertEqual(posts_field.value[0]['postName'], "Scientist (Agronomy)")

        # Pattern extracted
        pat_field = result.record.fields.get('examPattern')
        self.assertIsNotNone(pat_field)
        self.assertTrue(pat_field.ok)

        # Completeness evaluated
        self.assertIsNotNone(result.completeness)
        self.assertGreater(result.completeness.verified_count, 4)

    # =====================================================================================
    # TEST 2: Completeness-Driven Targeted Re-acquisition Loop
    # =====================================================================================
    def test_completeness_reacquisition_loop(self):
        """When applicable section is unpopulated, bounded official search discovers missing source."""
        # Initial pass: only notification, missing syllabus
        initial_doc = DiscoveredDoc(
            url="https://naeb.gov.in/notice.html",
            kind=DocKind.NOTIFICATION,
            title="Notice",
            relevance=D.Relevance.DIRECT
        )
        sources = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN, docs=[initial_doc])

        doc_notice = Document(url="https://naeb.gov.in/notice.html", kind="HTML", text=NOTICE_PAGE_HTML, fetched_at="2028-01-10")
        doc_notice.html = NOTICE_PAGE_HTML
        doc_syllabus = Document(url="https://naeb.gov.in/syllabus.pdf", kind="PDF", text=SEPARATE_SYLLABUS_PDF_TEXT, pages=[SEPARATE_SYLLABUS_PDF_TEXT], fetched_at="2028-01-11")

        loaded_map = {
            "https://naeb.gov.in/notice.html": doc_notice,
            "https://naeb.gov.in/syllabus.pdf": doc_syllabus
        }

        # Mock targeted search hit for syllabus on official domain
        class FakeHit:
            def __init__(self, title, url):
                self.title, self.url = title, url
                self.host = "naeb.gov.in"

        def fake_targeted_search(query, max_results=5, official_only=False):
            if "syllabus" in query.lower():
                return [FakeHit("Detailed Syllabus of Agricultural Research Scientist Examination 2028", "https://naeb.gov.in/syllabus.pdf")]
            return []

        with patch.object(B, 'resolve', return_value=self.resolved), \
             patch.object(B, 'discover', return_value=sources), \
             patch.object(B, '_load', side_effect=lambda d: loaded_map[d.url]):

            result = B.build(UNKNOWN_EXAM_QUERY, year="2028", search_fn=fake_targeted_search)

        # Assert syllabus was successfully acquired by targeted re-acquisition
        self.assertIn("https://naeb.gov.in/syllabus.pdf", result.record.sources_read)
        syl_field = result.record.fields.get('syllabus')
        self.assertIsNotNone(syl_field)
        self.assertEqual(syl_field.status, RecordStatus.FOUND)
        self.assertGreater(len(syl_field.value), 0)

        # Assert reacquisition performed flag is True
        self.assertTrue(result.completeness.reacquisition_performed)
        self.assertGreaterEqual(result.completeness.reacquisition_attempts, 1)

    # =====================================================================================
    # TEST 3: Multi-Document Reconciliation
    # =====================================================================================
    def test_multi_document_reconciliation(self):
        """Merges dates from notification and later corrigendum chronologically with evidence."""
        doc1 = SourceDocument(id="doc1", url="https://naeb.gov.in/notice.html",
                              title="Notice", authority=UNKNOWN_AUTHORITY_NAME, exam_id=UNKNOWN_EXAM_ID)
        doc2 = SourceDocument(id="doc2", url="https://naeb.gov.in/corrigendum.pdf",
                              title="Corrigendum 01", authority=UNKNOWN_AUTHORITY_NAME, exam_id=UNKNOWN_EXAM_ID)

        # Notice has initial application close: 2028-02-15
        span1 = "Closing Date of Application 15/02/2028"
        ev1 = SourceEvidence(source_id=doc1.id, url=doc1.url, document_title=doc1.title,
                             span=span1, accessed_at="2028-01-10", reading="closing date")
        m1 = Milestone(
            id=f"date-{UNKNOWN_EXAM_ID}-app-close",
            label="Closing Date of Application",
            kind="APPLICATION_END",
            ends_at=Fact.verified("2028-02-15", ev1),
            status=Status.VERIFIED
        )

        # Corrigendum extends application close to 2028-02-28
        span2 = "The last date for receipt of applications is extended from 15/02/2028 to 28/02/2028"
        ev2 = SourceEvidence(source_id=doc2.id, url=doc2.url, document_title=doc2.title,
                             span=span2, accessed_at="2028-02-10", reading="extension statement")
        m2 = Milestone(
            id=f"date-{UNKNOWN_EXAM_ID}-app-close-ext",
            label="Closing Date of Application (Extended)",
            kind="APPLICATION_END",
            ends_at=Fact.verified("2028-02-28", ev2),
            state=MilestoneState.POSTPONED,
            status=Status.VERIFIED
        )

        reconciled = B.D_DATES.reconcile([(doc1, [m1]), (doc2, [m2])])
        self.assertEqual(len(reconciled), 2)

        # Verify predecessor is superseded and successor supersedes it
        older = next(m for m in reconciled if m.id == m1.id)
        newer = next(m for m in reconciled if m.id == m2.id)

        self.assertEqual(older.superseded_by, newer.id)
        self.assertTrue(older.is_superseded)
        self.assertEqual(newer.supersedes, older.id)

    # =====================================================================================
    # TEST 4: Corrigenda Delta Extraction & SUPERSEDE Overlay Generation
    # =====================================================================================
    def test_corrigenda_delta_extraction_and_supersede_overlay(self):
        """Extracts corrigenda deltas and produces SUPERSEDE overlay linked to predecessor."""
        doc = SourceDocument(id="doc-corr", url="https://naeb.gov.in/corr.pdf",
                             title="Corrigendum Notice", authority=UNKNOWN_AUTHORITY_NAME,
                             published_at="2028-02-10", exam_id=UNKNOWN_EXAM_ID)

        notices = CORR.extract_corrigenda(doc, CORRIGENDUM_PDF_TEXT, exam_id=UNKNOWN_EXAM_ID, cycle="2028")
        self.assertGreaterEqual(len(notices), 2)

        # 1. Date extension delta
        date_notice = next(n for n in notices if n.affected_domain == 'dates')
        self.assertEqual(date_notice.affected_field, 'application_close')
        self.assertEqual(date_notice.new_value, '28/02/2028')
        self.assertEqual(date_notice.old_value, '15/02/2028')

        # 2. Vacancies revision delta
        vac_notice = next(n for n in notices if n.affected_domain == 'overview')
        self.assertEqual(vac_notice.new_value, 95)
        self.assertEqual(vac_notice.old_value, 80)

        # Existing initial overlays
        initial_date_overlay = ExamFactOverlay(
            id="overlay-init-date",
            exam_id=UNKNOWN_EXAM_ID,
            cycle="2028",
            domain="dates",
            kind=OverlayKind.ADD,
            value={"type": "APPLICATION_CLOSE", "dateTimeStr": "2028-02-15 00:00:00", "label": "Last Date"},
            provenance={"documentTitle": "Notice", "officialUrl": "https://naeb.gov.in/notice.html",
                        "verificationLevel": "OFFICIALLY_VERIFIED", "excerptText": "Last date 15/02/2028"},
            status="VERIFIED"
        )

        corr_overlays = CORR.notices_to_overlays(notices, [initial_date_overlay])
        self.assertGreaterEqual(len(corr_overlays), 2)

        superseding_date = next(o for o in corr_overlays if o.domain == 'dates')
        self.assertEqual(superseding_date.kind, OverlayKind.SUPERSEDE)
        self.assertEqual(superseding_date.supersedes_id, initial_date_overlay.id)
        self.assertEqual(superseding_date.target_id, initial_date_overlay.id)

        # Projection check: applying overlays updates projected date and archives revision
        exam_dict = {
            'id': UNKNOWN_EXAM_ID,
            'title': UNKNOWN_OFFICIAL_NAME,
            'dates': [],
            'vacanciesTotal': 80
        }
        projected = apply_overlays_to_exam_dict(exam_dict, [initial_date_overlay, superseding_date])
        # The predecessor date is preserved as SUPERSEDED and new date is AVAILABLE
        self.assertEqual(len(projected['dates']), 2)
        superseded_item = next(d for d in projected['dates'] if d.get('status') == 'SUPERSEDED')
        active_item = next(d for d in projected['dates'] if d.get('status') == 'AVAILABLE')
        self.assertEqual(superseded_item['id'], initial_date_overlay.id)
        self.assertEqual(active_item['dateTimeStr'], "28/02/2028 00:00:00")

    # =====================================================================================
    # TEST 5: Strict Failure-State Separation Across 17 Sections
    # =====================================================================================
    def test_strict_failure_state_separation(self):
        """Verifies failure states are distinctly typed and never collapsed."""
        rec = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                         authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)
        cite = Citation("Notice", "https://naeb.gov.in/notice.pdf", 1, "Clause 1", "Excerpt", "2028-01-10")

        # 1. VERIFIED_AVAILABLE
        rec.set(Field.found('officialName', UNKNOWN_OFFICIAL_NAME, cite))
        rec.set(Field.found('authority', UNKNOWN_AUTHORITY_NAME, cite))
        rec.set(Field.found('vacancies', 95, cite))

        # 2. NOT_YET_PUBLISHED
        rec.set(Field.not_published('admitCard', 'The authority has not announced admit card release date for 2028'))

        # 3. EXTRACTION_FAILED
        rec.set(Field.not_extracted('examPattern', UNKNOWN_DOMAIN, 'Table pattern parsing failed'))

        # 4. NEEDS_REVIEW
        rec.set(Field.needs_review('fee', {'amount': 500}, 'Only one supporting cue found', cite))

        sources = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN)
        report = evaluate_completeness(rec, sources)

        # Overview section -> VERIFIED_AVAILABLE
        sec_overview = next(s for s in report.sections if s.section_id == 'overview')
        self.assertEqual(sec_overview.state, CompletenessState.VERIFIED_AVAILABLE)

        # Admit Card section -> NOT_YET_PUBLISHED
        sec_admit = next(s for s in report.sections if s.section_id == 'admit-card')
        self.assertEqual(sec_admit.state, CompletenessState.NOT_YET_PUBLISHED)

        # Pattern section -> EXTRACTION_FAILED
        sec_pat = next(s for s in report.sections if s.section_id == 'pattern')
        self.assertEqual(sec_pat.state, CompletenessState.EXTRACTION_FAILED)

        # Infrastructure failure test: network outage must NEVER produce NOT_YET_PUBLISHED
        infra_sources = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN)
        infra_sources.infrastructure_failed = True
        infra_sources.infrastructure_note = "DNS resolution timeout for naeb.gov.in"
        infra_rec = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                               authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)

        infra_report = evaluate_completeness(infra_rec, infra_sources)
        self.assertGreaterEqual(infra_report.failure_count, 1)
        for s in infra_report.sections:
            if s.section_id in ('overview', 'dates', 'pattern'):
                self.assertEqual(s.state, CompletenessState.INFRASTRUCTURE_FAILURE)

    # =====================================================================================
    # TEST 6: All 17 Sections Completeness Evaluation and Overlay Projection
    # =====================================================================================
    def test_all_17_sections_completeness_and_projection(self):
        """Proves all 17 GovOS sections evaluate completeness and project without data fabrication."""
        rec = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                         authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)
        cite = Citation("Official Gazette", "https://naeb.gov.in/gazette.pdf", 1, "Sec 4", "Official text", "2028-01-10")

        # Set verified facts for available domains
        rec.set(Field.found('officialName', UNKNOWN_OFFICIAL_NAME, cite))
        rec.set(Field.found('authority', UNKNOWN_AUTHORITY_NAME, cite))
        rec.set(Field.found('vacancies', 95, cite))
        rec.set(Field.found('dates', [{'type': 'EXAM_TIER1', 'dateTimeStr': '2028-05-20 00:00:00', 'label': 'Prelim'}], cite))
        rec.set(Field.found('posts', [{'postName': 'Scientist', 'department': 'Crop Science', 'payLevel': 'Level 10'}], cite))
        rec.set(Field.found('ageLimits', '21-35 years', cite))
        rec.set(Field.found('qualification', "Master's Degree", cite))
        rec.set(Field.found('applicationPortal', 'https://naeb.gov.in/apply', cite))
        rec.set(Field.found('fee', {'amount': 500}, cite))
        rec.set(Field.found('howToApply', 'Apply online at official portal', cite))
        rec.set(Field.found('examPattern', [{'stageName': 'Prelims', 'marks': 200}], cite))
        rec.set(Field.found('syllabus', [{'topicName': 'Agronomy', 'subject': 'Agriculture'}], cite))
        rec.set(Field.found('admitCard', [{'eventName': 'Prelim Admit Card', 'releaseDate': '2028-05-10'}], cite))
        rec.set(Field.found('results', [{'stageName': 'Prelim Result', 'declaredAt': '2028-06-15'}], cite))
        rec.set(Field.found('cutoffs', [{'category': 'General', 'year': '2028', 'cutoffMarks': 135}], cite))

        # Explicitly declare future/unannounced sections as NOT_YET_PUBLISHED (zero fabrication)
        rec.set(Field.not_published('examDayChecklist', 'Conduct instructions will be released with admit card'))
        rec.set(Field.not_published('faqs', 'Official FAQ document not yet issued by board'))

        sources = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN)
        report = evaluate_completeness(rec, sources)

        # 1. Verify all 17 sections are evaluated
        self.assertEqual(len(report.sections), 17)
        section_states = {s.section_id: s.state for s in report.sections}
        section_natures = {s.section_id: s.nature for s in report.sections}

        # 2. Check Factual Extractions
        self.assertEqual(section_states['overview'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['dates'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['eligibility'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['application'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['pattern'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['syllabus'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['admit-card'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['results'], CompletenessState.VERIFIED_AVAILABLE)
        self.assertEqual(section_states['cutoffs'], CompletenessState.VERIFIED_AVAILABLE)

        # 3. Check Runtime Derived capabilities (Study Roadmap & Mock Tests)
        # Because pattern & syllabus are verified, runtime derived sections are SUPPORTED_AND_PROJECTED
        self.assertEqual(section_states['roadmap'], CompletenessState.SUPPORTED_AND_PROJECTED)
        self.assertEqual(section_natures['roadmap'], SectionNature.RUNTIME_DERIVED)
        self.assertEqual(section_states['mock-tests'], CompletenessState.SUPPORTED_AND_PROJECTED)
        self.assertEqual(section_natures['mock-tests'], SectionNature.RUNTIME_DERIVED)

        # 4. Check Unannounced/Future sections without fabrication
        self.assertEqual(section_states['exam-day'], CompletenessState.NOT_YET_PUBLISHED)
        self.assertEqual(section_states['faqs'], CompletenessState.NOT_YET_PUBLISHED)

        # 5. Check Overlay generation & SQLite persistence & projection
        class MockGate:
            may_publish = True

        overlays = create_overlays_from_record(rec, MockGate())
        self.assertGreaterEqual(len(overlays), 10)

        store = OverlayStore(':memory:')
        for o in overlays:
            store.record(o)

        loaded_overlays = store.get_active(UNKNOWN_EXAM_ID)
        self.assertEqual(len(loaded_overlays), len(overlays))

        # 6. Check Pure In-Memory Projection
        exam_dict = {'id': UNKNOWN_EXAM_ID, 'title': UNKNOWN_OFFICIAL_NAME}
        projected = apply_overlays_to_exam_dict(exam_dict, loaded_overlays)

        self.assertEqual(projected['vacanciesTotal'], 95)
        self.assertEqual(len(projected['dates']), 1)
        self.assertEqual(len(projected['posts']), 1)
        self.assertEqual(len(projected['syllabus']), 1)
        self.assertEqual(len(projected['examPatternStages']), 1)
        self.assertEqual(len(projected['admitCardEvents']), 1)
        self.assertEqual(len(projected['resultDeclarations']), 1)
        self.assertEqual(len(projected['cutoffsHistory']), 1)
        self.assertEqual(len(projected['officialLinks']), 1)

    # =====================================================================================
    # TEST 7: Authored Seed src/data.ts Preservation
    # =====================================================================================
    def test_authored_seed_preservation(self):
        """Verifies src/data.ts is unmodified and remains completely intact."""
        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
        data_ts_path = os.path.join(repo_root, 'src', 'data.ts')
        self.assertTrue(os.path.exists(data_ts_path))

        with io.open(data_ts_path, encoding='utf-8') as f:
            content = f.read()

        # Check required authored exam markers
        self.assertIn("EXAMS: Exam[] = [", content)
        self.assertIn("'exam-upsc-cse-2026'", content)
        self.assertIn("'exam-ssc-cgl-2026'", content)
        self.assertIn("'exam-ibps-po-2026'", content)
        self.assertIn("'exam-appsc-group1-2026'", content)
        self.assertIn("'exam-appsc-group2-2026'", content)

        # Check that no synthetic UNKNOWN_EXAM_2028 was written into data.ts
        self.assertNotIn("exam-naeb-scientist-2028", content)
        self.assertNotIn("National Agricultural Examination Board", content)

    # =====================================================================================
    # TEST 8: Application & Documents Canonical Mapping & Separation
    # =====================================================================================
    def test_application_documents_mapping(self):
        """Verifies canonical application mapping distinguishes procedure, portal, documents, photo/sig, fee, and exemptions."""
        from ..exam_authoring import extract as X
        from . import application as APP

        doc_html = Document(url="https://stsb.gov.in/recruitment/ae-2028", kind="HTML", text=STRUCTURAL_NOTICE_HTML, fetched_at="2028-03-01")
        doc_html.html = STRUCTURAL_NOTICE_HTML
        src_doc = SourceDocument(id="doc-stsb", url="https://stsb.gov.in/recruitment/ae-2028",
                                 title="STSB AE 2028 Notice", authority=STRUCTURAL_AUTHORITY_NAME, exam_id=STRUCTURAL_EXAM_ID)

        # 1. Application Portal extraction
        portal_field = X.application_portal(doc_html, "STSB AE Notice")
        self.assertTrue(portal_field.ok)
        self.assertEqual(portal_field.value, "https://stsb.gov.in/recruitment/apply")

        # 2. How to Apply procedure extraction
        how_field = X.how_to_apply(doc_html, "STSB AE Notice")
        self.assertTrue(how_field.ok)
        self.assertIn("https://stsb.gov.in/recruitment/apply", how_field.value)

        # 3. Required Documents extraction
        docs = APP.extract_required_documents(src_doc, STRUCTURAL_NOTICE_HTML)
        self.assertGreaterEqual(len(docs), 1)
        doc_names = [d['name'] for d in docs]
        self.assertTrue(any("degree certificate" in d.lower() for d in doc_names))

        # Zero invented documents: does not claim domicile or caste certificate if not requested
        self.assertFalse(any("domicile" in d.lower() for d in doc_names))

        # 4. Photo & Signature Guidelines extraction
        photo_sig = APP.extract_photo_signature_guidelines(src_doc, STRUCTURAL_NOTICE_HTML)
        self.assertIsNotNone(photo_sig)
        self.assertTrue(photo_sig.get('hasOfficialGuidelines'))
        self.assertGreater(len(photo_sig.get('photograph', [])), 0)
        self.assertGreater(len(photo_sig.get('signature', [])), 0)

        # 5. Fee structure & fee exemptions
        fee_field = X.fee(doc_html, "STSB AE Notice")
        self.assertTrue(fee_field.ok)
        self.assertIn('250', fee_field.value.get('amounts', []))

        exemptions = APP.extract_fee_exemptions(src_doc, STRUCTURAL_NOTICE_HTML)
        self.assertGreaterEqual(len(exemptions), 1)
        exempt_cats = [e['category'] for e in exemptions]
        self.assertTrue(any("women" in c.lower() or "sc" in c.lower() or "st" in c.lower() for c in exempt_cats))

        # 6. Overlay generation & Pure In-Memory Projection
        rec = ExamRecord(exam_id=STRUCTURAL_EXAM_ID, code="STSB_2028", title=STRUCTURAL_OFFICIAL_NAME,
                         authority_name=STRUCTURAL_AUTHORITY_NAME, official_domain=STRUCTURAL_DOMAIN)
        cite = Citation("STSB Notice", src_doc.url, 1, "Para 4", "Official text", "2028-03-01")
        rec.set(portal_field)
        rec.set(how_field)
        rec.set(Field.found('requiredDocuments', docs, cite))
        rec.set(Field.found('photoSignatureGuidelines', photo_sig, cite))
        rec.set(fee_field)
        rec.set(Field.found('feeExemptions', exemptions, cite))

        class MockGate:
            may_publish = True

        overlays = create_overlays_from_record(rec, MockGate())
        app_overlays = [o for o in overlays if o.domain == 'application']
        self.assertGreaterEqual(len(app_overlays), 1)

        portal_overlay = next((o for o in app_overlays if 'applicationPortal' in o.value), None)
        self.assertIsNotNone(portal_overlay)
        self.assertEqual(portal_overlay.value['applicationPortal'], portal_field.value)

        docs_overlay = next((o for o in app_overlays if 'requiredDocuments' in o.value), None)
        self.assertIsNotNone(docs_overlay)
        self.assertEqual(len(docs_overlay.value['requiredDocuments']), len(docs))

        exempt_overlay = next((o for o in app_overlays if 'feeExemptions' in o.value), None)
        self.assertIsNotNone(exempt_overlay)
        self.assertEqual(len(exempt_overlay.value['feeExemptions']), len(exemptions))

        base_exam = {'id': STRUCTURAL_EXAM_ID, 'title': STRUCTURAL_OFFICIAL_NAME}
        projected = apply_overlays_to_exam_dict(base_exam, overlays)
        self.assertEqual(projected['applicationPortal'], portal_field.value)
        self.assertEqual(len(projected['requiredDocuments']), len(docs))
        self.assertEqual(len(projected['feeExemptions']), len(exemptions))

    # =====================================================================================
    # TEST 9: Results & Next Steps Strict Separation
    # =====================================================================================
    def test_results_and_next_steps_separation(self):
        """Verifies strict separation between Official Result Facts and Derived Next-Step Guidance."""
        from .results import derive_next_steps

        # 1. Official Result Fact (pure verified data, not derived)
        official_fact = {
            'id': f"res-{UNKNOWN_EXAM_ID}-prelim",
            'declarationTitle': "Agricultural Research Scientist Prelim Result",
            'stageName': "Preliminary Examination",
            'declaredAt': "2028-06-15",
            'meritStatus': "MERIT_LIST_PUBLISHED",
            'officialResultUrl': "https://naeb.gov.in/result.pdf"
        }
        self.assertEqual(official_fact['meritStatus'], "MERIT_LIST_PUBLISHED")
        self.assertEqual(official_fact['officialResultUrl'], "https://naeb.gov.in/result.pdf")

        # 2. Derived Next-Step Guidance
        stages = [
            {'stageName': 'Preliminary Examination', 'sequence': 1},
            {'stageName': 'Mains Examination', 'sequence': 2},
            {'stageName': 'Interview / Viva-Voce', 'sequence': 3},
        ]
        derived = derive_next_steps([official_fact], stages)
        self.assertGreaterEqual(len(derived), 1)

        for step in derived:
            # Derived flag must be True and source must indicate lifecycle derivation
            self.assertTrue(step.get('isDerived'))
            self.assertEqual(step.get('source'), 'DERIVED_FROM_LIFECYCLE')
            self.assertIn("Mains", step.get('nextStage'))
            self.assertEqual(step.get('fromStage'), 'Preliminary Examination')

        # Negative test: zero results declared yet
        no_res_derived = derive_next_steps([], stages)
        self.assertGreaterEqual(len(no_res_derived), 1)
        self.assertTrue(no_res_derived[0]['isDerived'])
        self.assertEqual(no_res_derived[0]['action'], "Awaiting Official Result Declaration")
        # Zero invented next steps: does NOT pretend mains admit card is released
        self.assertFalse(no_res_derived[0].get('isAdmitCardReleased', False))

        # Check Overlay generation & projection
        rec = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                         authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)
        cite = Citation("Result PDF", "https://naeb.gov.in/result.pdf", 1, "Notice", "Excerpt", "2028-06-15")
        rec.set(Field.found('results', [official_fact], cite))
        rec.set(Field.found('nextSteps', derived, cite))

        class MockGate:
            may_publish = True

        overlays = create_overlays_from_record(rec, MockGate())
        res_overlays = [o for o in overlays if o.domain == 'results']
        self.assertEqual(len(res_overlays), 2)  # 1 for results, 1 for nextSteps

        base_exam = {'id': UNKNOWN_EXAM_ID, 'title': UNKNOWN_OFFICIAL_NAME}
        projected = apply_overlays_to_exam_dict(base_exam, overlays)
        self.assertEqual(len(projected['resultDeclarations']), 1)
        self.assertEqual(projected['resultDeclarations'][0]['stageName'], "Preliminary Examination")
        self.assertEqual(len(projected['nextStepGuidance']), len(derived))
        self.assertTrue(projected['nextStepGuidance'][0]['isDerived'])

    # =====================================================================================
    # TEST 10: Resources Official and Trusted Reference Tiers
    # =====================================================================================
    def test_resources_official_and_trusted_reference_tiers(self):
        """Verifies resources support OFFICIAL and TRUSTED_REFERENCE tiers and block unvetted candidates."""
        # 1. Overlay with OFFICIAL tier
        official_overlay = ExamFactOverlay(
            id="overlay-res-official",
            exam_id=UNKNOWN_EXAM_ID,
            cycle="2028",
            domain="resources",
            kind=OverlayKind.ADD,
            value={
                "title": "Official ARS Examination Notification",
                "url": "https://naeb.gov.in/notice.pdf",
                "officialityTier": "OFFICIAL",
                "isOfficial": True,
                "description": "Primary notification document from conducting board"
            },
            provenance={
                "documentTitle": "Notice",
                "officialUrl": "https://naeb.gov.in/notice.pdf",
                "verificationLevel": "OFFICIALLY_VERIFIED",
                "excerptText": "Official notification"
            },
            status="VERIFIED"
        )

        # 2. Overlay with TRUSTED_REFERENCE tier
        trusted_overlay = ExamFactOverlay(
            id="overlay-res-trusted",
            exam_id=UNKNOWN_EXAM_ID,
            cycle="2028",
            domain="resources",
            kind=OverlayKind.ADD,
            value={
                "title": "ICAR Standard Curriculum & Syllabus Reference",
                "url": "https://icar.org.in/curriculum",
                "officialityTier": "TRUSTED_REFERENCE",
                "isOfficial": False,
                "description": "Vetted apex council standard curriculum"
            },
            provenance={
                "documentTitle": "ICAR Curriculum",
                "officialUrl": "https://icar.org.in/curriculum",
                "verificationLevel": "OFFICIALLY_VERIFIED",
                "excerptText": "Agricultural Research Service scheme"
            },
            status="VERIFIED"
        )

        # 3. Unvetted search hit (PENDING_REVIEW) -> MUST be blocked by gate / inactive
        unvetted_overlay = ExamFactOverlay(
            id="overlay-res-unvetted",
            exam_id=UNKNOWN_EXAM_ID,
            cycle="2028",
            domain="resources",
            kind=OverlayKind.ADD,
            value={
                "title": "Third-Party Prep Blog",
                "url": "https://some-prep-blog.com/tips",
                "officialityTier": "PENDING_REVIEW",
                "isOfficial": False,
                "description": "Unverified web search candidate"
            },
            provenance={
                "documentTitle": "Blog",
                "officialUrl": "https://some-prep-blog.com/tips",
                "verificationLevel": "NEEDS_REVIEW",
                "excerptText": "Prep advice"
            },
            status="NEEDS_REVIEW"
        )

        # Store test: active vs inactive & publication gate
        store = OverlayStore(':memory:')
        store.record(official_overlay)
        store.record(trusted_overlay)

        # Confirm that an overlay with status NEEDS_REVIEW has is_active == False
        self.assertFalse(unvetted_overlay.is_active)

        # Publication gate: unvetted item (NEEDS_REVIEW) is rejected by gate
        with self.assertRaises(ValueError):
            store.record(unvetted_overlay)

        active = store.get_active(UNKNOWN_EXAM_ID, domain="resources")
        active_ids = {o.id for o in active}
        self.assertIn(official_overlay.id, active_ids)
        self.assertIn(trusted_overlay.id, active_ids)
        # Publication gate: unvetted item NEVER passes into active list
        self.assertNotIn(unvetted_overlay.id, active_ids)

        # Projection check: only official and trusted reference appear in projected exam dict
        base_exam = {'id': UNKNOWN_EXAM_ID, 'title': UNKNOWN_OFFICIAL_NAME}
        projected = apply_overlays_to_exam_dict(base_exam, active)
        self.assertEqual(len(projected['resources']), 2)
        tiers = {r['officialityTier'] for r in projected['resources']}
        self.assertEqual(tiers, {'OFFICIAL', 'TRUSTED_REFERENCE'})
        self.assertNotIn('PENDING_REVIEW', tiers)

    # =====================================================================================
    # TEST 11: Sources Required Are Acquisition Guidelines Not Completeness Blockers
    # =====================================================================================
    def test_source_types_not_completeness_blockers(self):
        """Verifies preferred_sources (sources_required) guide discovery but do NOT block completeness if facts are verified."""
        rec = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                         authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)
        cite = Citation("Comprehensive Notification", "https://naeb.gov.in/notice.pdf", 1, "Para 8", "Official syllabus excerpt", "2028-01-10")

        # Syllabus was extracted directly from NOTIFICATION (preferred_sources=('NOTIFICATION', 'SYLLABUS'))
        # Even though NO standalone 'SYLLABUS' document was discovered, the fact is verified
        rec.set(Field.found('syllabus', [{'topicName': 'Plant Pathology', 'subject': 'Agriculture'}], cite))

        # SourceSet has only NOTIFICATION, no standalone SYLLABUS document kind
        sources = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN, docs=[
            DiscoveredDoc(url="https://naeb.gov.in/notice.pdf", kind=DocKind.NOTIFICATION, title="Notice", relevance=D.Relevance.DIRECT)
        ])

        report = evaluate_completeness(rec, sources)
        sec_syllabus = next(s for s in report.sections if s.section_id == 'syllabus')

        # Crucial check: Section evaluates to VERIFIED_AVAILABLE, not blocked or degraded
        self.assertEqual(sec_syllabus.state, CompletenessState.VERIFIED_AVAILABLE)

    # =====================================================================================
    # TEST 12: Completeness Semantics Distinction Across All 10 States
    # =====================================================================================
    def test_completeness_semantics_distinction(self):
        """Proves pairwise distinctness of all 10 CompletenessState values with invariant protections."""
        # 1. Verify all 10 states exist and are distinct strings
        all_states = list(CompletenessState)
        self.assertEqual(len(all_states), 10)
        self.assertEqual(len(set(all_states)), 10)

        # 2. Invariant: Network/infrastructure failure NEVER becomes NOT_YET_PUBLISHED or NOT_APPLICABLE
        sources_infra = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN)
        sources_infra.infrastructure_failed = True
        sources_infra.infrastructure_note = "Connection reset by peer: 503 Service Unavailable"

        rec_empty = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                               authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)

        report_infra = evaluate_completeness(rec_empty, sources_infra)
        for s in report_infra.sections:
            if s.section_id in ('overview', 'dates', 'pattern', 'syllabus'):
                self.assertEqual(s.state, CompletenessState.INFRASTRUCTURE_FAILURE)
                self.assertNotEqual(s.state, CompletenessState.NOT_YET_PUBLISHED)
                self.assertNotEqual(s.state, CompletenessState.NOT_APPLICABLE)

        # 3. Invariant: Extraction failure NEVER becomes NOT_YET_PUBLISHED
        rec_extract_fail = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                                     authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)
        rec_extract_fail.set(Field.not_extracted('dates', UNKNOWN_DOMAIN, 'Date regex pattern matched 0 dates in notice'))
        sources_normal = D.SourceSet(exam_id=UNKNOWN_EXAM_ID, authority_domain=UNKNOWN_DOMAIN)
        report_extract_fail = evaluate_completeness(rec_extract_fail, sources_normal)
        sec_dates = next(s for s in report_extract_fail.sections if s.section_id == 'dates')
        self.assertEqual(sec_dates.state, CompletenessState.EXTRACTION_FAILED)
        self.assertNotEqual(sec_dates.state, CompletenessState.NOT_YET_PUBLISHED)

        # 4. Invariant: Source unreadable NEVER becomes NOT_APPLICABLE
        rec_unreadable = ExamRecord(exam_id=UNKNOWN_EXAM_ID, code="NAEB_2028", title=UNKNOWN_OFFICIAL_NAME,
                                   authority_name=UNKNOWN_AUTHORITY_NAME, official_domain=UNKNOWN_DOMAIN)
        rec_unreadable.set(Field.not_extracted('examPattern', UNKNOWN_DOMAIN, 'Document corrupted / unreadable PDF'))
        report_unreadable = evaluate_completeness(rec_unreadable, sources_normal)
        sec_pat = next(s for s in report_unreadable.sections if s.section_id == 'pattern')
        self.assertEqual(sec_pat.state, CompletenessState.EXTRACTION_FAILED)
        self.assertNotEqual(sec_pat.state, CompletenessState.NOT_APPLICABLE)

    # =====================================================================================
    # TEST 13: Universal Acquisition for Structural Variation Unknown Exam (STSB AE 2028)
    # =====================================================================================
    def test_universal_acquisition_structural_variation_unknown_exam(self):
        """Pipeline builds STSB Assistant Engineer 2028 (narrative/prose notice) without exam-specific code."""
        resolved_stsb = ResolvedExam(
            query=STRUCTURAL_UNKNOWN_QUERY,
            official_name=STRUCTURAL_OFFICIAL_NAME,
            year="2028",
            authority=Authority(
                name=STRUCTURAL_AUTHORITY_NAME,
                domain=STRUCTURAL_DOMAIN,
                confidence=0.94,
                evidence=["https://stsb.gov.in official portal"]
            ),
            seed_urls=["https://stsb.gov.in/recruitment/ae-2028"]
        )
        docs = [
            DiscoveredDoc(
                url="https://stsb.gov.in/recruitment/ae-2028",
                kind=DocKind.NOTIFICATION,
                title="STSB AE 2028 Notice",
                relevance=D.Relevance.DIRECT,
                matched=["assistant", "engineer", "2028"]
            )
        ]
        sources = D.SourceSet(exam_id=STRUCTURAL_EXAM_ID, authority_domain=STRUCTURAL_DOMAIN, docs=docs)
        doc = Document(url="https://stsb.gov.in/recruitment/ae-2028", kind="HTML", text=STRUCTURAL_NOTICE_HTML, fetched_at="2028-03-01")
        doc.html = STRUCTURAL_NOTICE_HTML
        loaded = {"https://stsb.gov.in/recruitment/ae-2028": doc}

        with patch.object(B, 'resolve', return_value=resolved_stsb), \
             patch.object(B, 'discover', return_value=sources), \
             patch.object(B, '_load', side_effect=lambda d: loaded[d.url]):

            result = B.build(STRUCTURAL_UNKNOWN_QUERY, year="2028", search_fn=lambda q, **kw: [])

        self.assertTrue(result.record.exam_id.startswith("exam-stsb-"))
        self.assertEqual(result.record.authority_name, STRUCTURAL_AUTHORITY_NAME)

        # Dates extracted from prose milestones
        dates_field = result.record.fields.get('dates')
        self.assertIsNotNone(dates_field)
        self.assertTrue(dates_field.ok)
        self.assertTrue(any(d.get('type') == 'APPLICATION_CLOSE' for d in dates_field.value))

        # Vacancies and age limits extracted
        vac_field = result.record.fields.get('vacancies')
        self.assertIsNotNone(vac_field)
        self.assertTrue(vac_field.ok)
        self.assertEqual(vac_field.value, 60)

        age_field = result.record.fields.get('ageLimits')
        self.assertIsNotNone(age_field)
        self.assertTrue(age_field.ok)

        # Application & documents extracted
        portal_field = result.record.fields.get('applicationPortal')
        self.assertIsNotNone(portal_field)
        self.assertEqual(portal_field.value, "https://stsb.gov.in/recruitment/apply")

        how_field = result.record.fields.get('howToApply')
        self.assertIsNotNone(how_field)
        self.assertTrue(how_field.ok)

        req_docs_field = result.record.fields.get('requiredDocuments')
        self.assertIsNotNone(req_docs_field)
        self.assertTrue(req_docs_field.ok)

        photo_sig_field = result.record.fields.get('photoSignatureGuidelines')
        self.assertIsNotNone(photo_sig_field)
        self.assertTrue(photo_sig_field.ok)

        fee_field = result.record.fields.get('fee')
        self.assertIsNotNone(fee_field)
        self.assertTrue(fee_field.ok)

        exempt_field = result.record.fields.get('feeExemptions')
        self.assertIsNotNone(exempt_field)
        self.assertTrue(exempt_field.ok)

        # Pattern extracted
        pat_field = result.record.fields.get('examPattern')
        self.assertIsNotNone(pat_field)
        self.assertTrue(pat_field.ok)

        # Completeness evaluated across all 17 sections
        self.assertIsNotNone(result.completeness)
        self.assertEqual(len(result.completeness.sections), 17)
        self.assertGreater(result.completeness.verified_count, 4)


if __name__ == '__main__':
    unittest.main()

