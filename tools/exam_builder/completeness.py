"""Semantic 17-Section Completeness Evaluation for GovOS.

Governed by GOVOS_MASTER_SPEC.md (Phase 2 & Part D Workspace Contract).
Evaluates the student-facing completeness across the 17 authoritative GovOS sections:
  1. Overview (deep-link: 1)
  2. Dates & Timeline (deep-link: 2)
  3. Eligibility & Posts (deep-link: 3)
  4. Application & Documents (deep-link: 4)
  5. Exam Pattern (deep-link: 5)
  6. Syllabus (deep-link: 6)
  7. Study Roadmap (deep-link: 7) - RUNTIME_DERIVED
  8. Resources (deep-link: 8)
  9. Practice & PYQs (deep-link: 9)
 10. Mock Tests (deep-link: 17) - RUNTIME_DERIVED
 11. Admit Card (deep-link: 14)
 12. Exam Day (deep-link: 15)
 13. Results & Next Steps (deep-link: 16)
 14. FAQs & Official Clauses (deep-link: 11)
 15. Corrigenda Log (deep-link: 13)
 16. Official Portals & Links (deep-link: 12)
 17. Cutoff History (deep-link: 10)

Strict failure-state separation is enforced:
  - VERIFIED_AVAILABLE: Real official facts with verbatim citation.
  - SUPPORTED_AND_PROJECTED: Runtime capability successfully configured from verified inputs.
  - RUNTIME_DERIVED: Derived guidance/roadmap synthesized from verified pattern & syllabus.
  - NOT_YET_PUBLISHED: Official authority has not published for this cycle yet.
  - NOT_APPLICABLE: Section does not apply to this examination's structure.
  - SOURCE_NOT_FOUND_AFTER_SEARCH: Bounded official search returned zero matches.
  - SOURCE_UNREADABLE: Document fetched but corrupted / unparseable / scanned image without text.
  - EXTRACTION_FAILED: Document text verified for identity, but extractor missed schema.
  - NEEDS_REVIEW: Ambiguous facts, conflicting sources, or low confidence.
  - INFRASTRUCTURE_FAILURE: Network / DNS / HTTP outage / search provider failure.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from ..exam_authoring.record import ExamRecord, Status as RecordStatus


class CompletenessState(str, Enum):
    """The distinct user-facing completeness states for each of the 17 sections."""
    VERIFIED_AVAILABLE = 'VERIFIED_AVAILABLE'
    SUPPORTED_AND_PROJECTED = 'SUPPORTED_AND_PROJECTED'
    RUNTIME_DERIVED = 'RUNTIME_DERIVED'
    NOT_YET_PUBLISHED = 'NOT_YET_PUBLISHED'
    NOT_APPLICABLE = 'NOT_APPLICABLE'
    SOURCE_NOT_FOUND_AFTER_SEARCH = 'SOURCE_NOT_FOUND_AFTER_SEARCH'
    SOURCE_UNREADABLE = 'SOURCE_UNREADABLE'
    EXTRACTION_FAILED = 'EXTRACTION_FAILED'
    NEEDS_REVIEW = 'NEEDS_REVIEW'
    INFRASTRUCTURE_FAILURE = 'INFRASTRUCTURE_FAILURE'


class SectionNature(str, Enum):
    """Distinguishes direct official factual extractions from runtime derived capabilities."""
    FACTUAL_EXTRACTION = 'FACTUAL_EXTRACTION'
    RUNTIME_DERIVED = 'RUNTIME_DERIVED'


FACTUAL_SUPPORTED_STATES: frozenset[CompletenessState] = frozenset({
    CompletenessState.VERIFIED_AVAILABLE,
    CompletenessState.NOT_YET_PUBLISHED,
    CompletenessState.NOT_APPLICABLE,
    CompletenessState.SOURCE_NOT_FOUND_AFTER_SEARCH,
    CompletenessState.SOURCE_UNREADABLE,
    CompletenessState.EXTRACTION_FAILED,
    CompletenessState.NEEDS_REVIEW,
    CompletenessState.INFRASTRUCTURE_FAILURE,
})

DERIVED_SUPPORTED_STATES: frozenset[CompletenessState] = frozenset({
    CompletenessState.SUPPORTED_AND_PROJECTED,
    CompletenessState.RUNTIME_DERIVED,
    CompletenessState.NOT_APPLICABLE,
    CompletenessState.NOT_YET_PUBLISHED,
    CompletenessState.EXTRACTION_FAILED,
    CompletenessState.NEEDS_REVIEW,
    CompletenessState.INFRASTRUCTURE_FAILURE,
})


@dataclass(frozen=True)
class GovOSSectionDefinition:
    """Definition and contract for one of the 17 authoritative GovOS sections."""
    order: int                          # 1 to 17 order in GOVOS_MASTER_SPEC.md Part D
    num: int                            # UI deep-link number matching src/ui.tsx
    id: str                             # Stable kebab-case section identifier
    title: str                          # Official product section title
    nature: SectionNature               # FACTUAL_EXTRACTION or RUNTIME_DERIVED
    canonical_domain: str               # Corresponding canonical overlay domain
    canonical_fields: tuple[str, ...]   # Underlying record fields evaluated
    preferred_sources: tuple[str, ...]  # Preferred primary source document kinds
    lifecycle_stage: str                # Lifecycle category: PRE_EXAM, APPLICATION, CONDUCT, POST_EXAM, CONTINUOUS
    student_purpose: str                # Student-centric explanation of what this section answers
    target_group: str = 'JOURNEY'       # JOURNEY (sections 1..13) or REFERENCE (sections 14..17)
    verification_requirement: str = ''  # Verifiable rule required to certify state
    supported_states: frozenset[CompletenessState] = FACTUAL_SUPPORTED_STATES

    @property
    def sources_required(self) -> tuple[str, ...]:
        """Backward-compatible alias for preferred_sources."""
        return self.preferred_sources


#: The authoritative 17 GovOS sections as defined in GOVOS_MASTER_SPEC.md Part D and src/ui.tsx
GOVOS_17_SECTIONS: tuple[GovOSSectionDefinition, ...] = (
    GovOSSectionDefinition(
        order=1, num=1, id='overview', title='Overview',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='overview',
        canonical_fields=('officialName', 'authority', 'vacancies'),
        preferred_sources=('NOTIFICATION', 'EXAM_PAGE'),
        lifecycle_stage='CONTINUOUS',
        student_purpose='What the examination is, conducting authority, vacancy count, and selection overview.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation required for official name, authority, or vacancies.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=2, num=2, id='dates', title='Dates & Timeline',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='dates',
        canonical_fields=('dates',),
        preferred_sources=('NOTIFICATION', 'EXAM_PAGE', 'CALENDAR'),
        lifecycle_stage='CONTINUOUS',
        student_purpose='Every milestone date, application window, admit card date, exam dates, status, and supersessions.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation with milestone label, date, and document provenance.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=3, num=3, id='eligibility', title='Eligibility & Posts',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='eligibility',
        canonical_fields=('posts', 'ageLimits', 'qualification', 'attempts'),
        preferred_sources=('NOTIFICATION',),
        lifecycle_stage='PRE_EXAM',
        student_purpose='Whether the student may apply (age limits, qualifications, category relaxations) and posts offered.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation for posts, age limits, educational qualification, or attempts.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=4, num=4, id='application', title='Application & Documents',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='application',
        canonical_fields=('applicationPortal', 'howToApply', 'requiredDocuments',
                          'photoSignatureGuidelines', 'fee', 'feeExemptions'),
        preferred_sources=('NOTIFICATION', 'APPLICATION_PORTAL'),
        lifecycle_stage='APPLICATION',
        student_purpose='How to apply online, portal link, required documents, photo/signature guidelines, fee structure, and category exemptions.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation for application procedure, portal link, document uploads, photo/sig rules, fee, or exemptions.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=5, num=5, id='pattern', title='Exam Pattern',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='pattern',
        canonical_fields=('examPattern',),
        preferred_sources=('NOTIFICATION', 'EXAM_PATTERN'),
        lifecycle_stage='PRE_EXAM',
        student_purpose='Examination stages, tiers, papers, marks, duration, question types, and negative marking.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation for exam stages, papers, marks, and duration.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=6, num=6, id='syllabus', title='Syllabus',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='syllabus',
        canonical_fields=('syllabus',),
        preferred_sources=('NOTIFICATION', 'SYLLABUS'),
        lifecycle_stage='PRE_EXAM',
        student_purpose='Detailed topics and subjects at the authority\'s own depth, sections, and weightage where derivable.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation for syllabus topics and subjects.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=7, num=7, id='roadmap', title='Study Roadmap',
        nature=SectionNature.RUNTIME_DERIVED,
        canonical_domain='roadmapTracks',
        canonical_fields=('examPattern', 'syllabus'),
        preferred_sources=(),
        lifecycle_stage='PRE_EXAM',
        student_purpose='Structured preparation strategy derived from verified pattern and syllabus topics (clearly guidance, not official instruction).',
        target_group='JOURNEY',
        verification_requirement='Runtime derived from verified exam pattern and syllabus topics (no manual authoring).',
        supported_states=DERIVED_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=8, num=8, id='resources', title='Resources',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='resources',
        canonical_fields=('officialSources',),
        preferred_sources=('NOTIFICATION', 'EXAM_PAGE'),
        lifecycle_stage='CONTINUOUS',
        student_purpose='Curated official links and trusted reference sources with strict officiality tiers; no stored material.',
        target_group='JOURNEY',
        verification_requirement='Verified official sources or vetted trusted reference sources with active provenance; unvetted blocked.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=9, num=9, id='pyqs', title='Practice & PYQs',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='officialPapers',
        canonical_fields=('officialPapers',),
        preferred_sources=('QUESTION_PAPER', 'NOTIFICATION'),
        lifecycle_stage='PRE_EXAM',
        student_purpose='Official previous year question papers catalogued with exact identity, plus official answer keys.',
        target_group='JOURNEY',
        verification_requirement='Verified official question papers or answer keys with exact document identity.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=10, num=17, id='mock-tests', title='Mock Tests',
        nature=SectionNature.RUNTIME_DERIVED,
        canonical_domain='mockTests',
        canonical_fields=('examPattern', 'syllabus'),
        preferred_sources=(),
        lifecycle_stage='PRE_EXAM',
        student_purpose='Runtime interactive exam practice simulator driven by verified pattern and question schemes.',
        target_group='JOURNEY',
        verification_requirement='Runtime simulator derived from verified exam pattern stages, question schemes, and marks.',
        supported_states=DERIVED_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=11, num=14, id='admit-card', title='Admit Card',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='admitCard',
        canonical_fields=('admitCard',),
        preferred_sources=('ADMIT_CARD', 'NOTIFICATION'),
        lifecycle_stage='CONDUCT',
        student_purpose='City intimation and admit card release dates, download instructions, and official candidate portal.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation for admit card / city intimation event, date, or portal.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=12, num=15, id='exam-day', title='Exam Day',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='examDayChecklist',
        canonical_fields=('examDayChecklist',),
        preferred_sources=('NOTIFICATION', 'ADMIT_CARD'),
        lifecycle_stage='CONDUCT',
        student_purpose='Official examination day conduct instructions, permitted/prohibited items, and reporting timings.',
        target_group='JOURNEY',
        verification_requirement='Verified primary source citation for exam day instructions, reporting time, or permitted items.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=13, num=16, id='results', title='Results & Next Steps',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='results',
        canonical_fields=('results', 'nextSteps'),
        preferred_sources=('RESULT', 'NOTIFICATION'),
        lifecycle_stage='POST_EXAM',
        student_purpose='Official result declarations (written results, shortlists, merit lists) plus structured next-step guidance derived from verified exam lifecycle.',
        target_group='JOURNEY',
        verification_requirement='Verified official result declaration facts; next-step guidance cleanly derived from verified lifecycle.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=14, num=11, id='faqs', title='FAQs & Official Clauses',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='faqs',
        canonical_fields=('faqs',),
        preferred_sources=('NOTIFICATION', 'EXAM_PAGE'),
        lifecycle_stage='CONTINUOUS',
        student_purpose='Direct answers to common questions tied directly to official notice clauses and citations.',
        target_group='REFERENCE',
        verification_requirement='Verified official FAQ document or notification clauses cited verbatim.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=15, num=13, id='corrigenda', title='Corrigenda Log',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='corrigendums',
        canonical_fields=('corrigenda',),
        preferred_sources=('CORRIGENDUM',),
        lifecycle_stage='CONTINUOUS',
        student_purpose='Chronological log of official corrigenda, date extensions, vacancy revisions, and addenda.',
        target_group='REFERENCE',
        verification_requirement='Verified official corrigendum notices with structured revision deltas and superseded links.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=16, num=12, id='official-links', title='Official Portals & Links',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='officialLinks',
        canonical_fields=('officialSources', 'applicationPortal'),
        preferred_sources=('EXAM_PAGE', 'NOTIFICATION'),
        lifecycle_stage='CONTINUOUS',
        student_purpose='Verified official web links, recruitment portals, and notification documents with domain verification.',
        target_group='REFERENCE',
        verification_requirement='Verified official authority domain or application portal URLs.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
    GovOSSectionDefinition(
        order=17, num=10, id='cutoffs', title='Cutoff History',
        nature=SectionNature.FACTUAL_EXTRACTION,
        canonical_domain='cutoffsHistory',
        canonical_fields=('cutoffs',),
        preferred_sources=('CUTOFF', 'RESULT'),
        lifecycle_stage='POST_EXAM',
        student_purpose='Official qualifying and cutoff marks by category and post across recent cycles.',
        target_group='REFERENCE',
        verification_requirement='Verified official qualifying or cutoff marks by category from official result/cutoff publications.',
        supported_states=FACTUAL_SUPPORTED_STATES
    ),
)

#: Fast lookup tables by order (1..17), UI number (1..17 deep links), and string id
SECTIONS_BY_ORDER: dict[int, GovOSSectionDefinition] = {s.order: s for s in GOVOS_17_SECTIONS}
SECTIONS_BY_NUM: dict[int, GovOSSectionDefinition] = {s.num: s for s in GOVOS_17_SECTIONS}
SECTIONS_BY_ID: dict[str, GovOSSectionDefinition] = {s.id: s for s in GOVOS_17_SECTIONS}

#: Internal canonical fields/features that must NEVER replace or masquerade as user-facing sections
PROHIBITED_SECTION_NAMES: frozenset[str] = frozenset({
    'vacancies', 'age-calculator', 'age calculator', 'ageCalculator', 'salary',
    'papers', 'answer-keys', 'answerKeys', 'officialSources', 'dates_list',
})


@dataclass
class SectionCompleteness:
    """Completeness state for one user-facing section."""
    section_order: int
    section_num: int
    section_id: str
    section_title: str
    nature: SectionNature
    state: CompletenessState
    is_applicable: bool = True
    evidence_count: int = 0
    student_status_summary: str = ''
    technical_note: str = ''
    fields: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'sectionOrder': self.section_order,
            'sectionNum': self.section_num,
            'sectionId': self.section_id,
            'sectionTitle': self.section_title,
            'nature': self.nature.value,
            'state': self.state.value,
            'isApplicable': self.is_applicable,
            'evidenceCount': self.evidence_count,
            'studentStatusSummary': self.student_status_summary,
            'technicalNote': self.technical_note,
            'fields': self.fields,
        }


@dataclass
class ExamCompletenessReport:
    """Full 17-section evaluation report for an examination."""
    exam_id: str
    cycle: str
    total_sections: int = 17
    verified_count: int = 0
    derived_count: int = 0
    not_yet_published_count: int = 0
    not_applicable_count: int = 0
    needs_review_count: int = 0
    failure_count: int = 0
    #: Sections whose readers and a domain search found nothing -- kept apart from "not yet
    #: published", which is a statement about the authority this state does not make.
    source_not_found_count: int = 0
    sections: list[SectionCompleteness] = field(default_factory=list)
    reacquisition_performed: bool = False
    reacquisition_attempts: int = 0

    @property
    def completeness_percentage(self) -> float:
        applicable = self.total_sections - self.not_applicable_count
        if applicable <= 0:
            return 100.0
        # Verified factual sections plus verified-derived sections count toward complete student experience
        usable = self.verified_count + self.derived_count
        return round((usable / applicable) * 100.0, 1)

    def get_section(self, section_id_or_num: str | int) -> Optional[SectionCompleteness]:
        for s in self.sections:
            if s.section_id == section_id_or_num or s.section_num == section_id_or_num or s.section_order == section_id_or_num:
                return s
        return None

    def to_dict(self) -> dict:
        return {
            'examId': self.exam_id,
            'cycle': self.cycle,
            'totalSections': self.total_sections,
            'verifiedCount': self.verified_count,
            'derivedCount': self.derived_count,
            'notYetPublishedCount': self.not_yet_published_count,
            'notApplicableCount': self.not_applicable_count,
            'needsReviewCount': self.needs_review_count,
            'failureCount': self.failure_count,
            'sourceNotFoundCount': self.source_not_found_count,
            'completenessPercentage': self.completeness_percentage,
            'reacquisitionPerformed': self.reacquisition_performed,
            'reacquisitionAttempts': self.reacquisition_attempts,
            'sections': [s.to_dict() for s in self.sections],
        }


def _extractor_for(field_name: str) -> str:
    from .contract import CONTRACT
    for cf in CONTRACT:
        if cf.name == field_name:
            return cf.extractor or ''
    return ''


def _reader_raised(rec: ExamRecord, field_name: str) -> bool:
    """True when this field's reader threw on a document it was handed -- positive evidence
    that content was present and we failed on it, which is what EXTRACTION_FAILED means."""
    name = _extractor_for(field_name)
    if not name:
        return False
    marker = f'{name} failed on '
    return any(marker in line for line in getattr(rec, 'log', []))


def _classify_field_status(rec: ExamRecord, field_name: str,
                           infra_failed: bool, unreadable_docs: bool,
                           searched_not_found: frozenset = frozenset(),
                           not_applicable: dict | None = None) -> tuple[CompletenessState, str]:
    """The distinct state of one record field. The record's own status is never rewritten;
    this reads the evidence around it and names which of the six situations it is:

      VERIFIED_AVAILABLE              present and verified
      NOT_YET_PUBLISHED               the authority publishes none (its own listing shows so)
      NOT_APPLICABLE                  does not apply to this exam, on cited evidence
      EXTRACTION_FAILED               the reader raised on content it was handed
      SOURCE_NOT_FOUND_AFTER_SEARCH   readers ran and the domain was searched; nothing found
      INFRASTRUCTURE_FAILURE          we could not finish looking
    A NOT_EXTRACTED field that was never searched for stays EXTRACTION_FAILED: absence is not
    claimed until the engine has actually looked.
    """
    if not_applicable and field_name in not_applicable:
        return CompletenessState.NOT_APPLICABLE, not_applicable[field_name] or 'Not applicable on cited evidence'

    f = rec.fields.get(field_name)
    if f is None:
        if infra_failed:
            return CompletenessState.INFRASTRUCTURE_FAILURE, 'Search or fetch infrastructure failed'
        return CompletenessState.SOURCE_NOT_FOUND_AFTER_SEARCH, 'No source discovered'

    status = f.status
    st_val = status.value if hasattr(status, 'value') else str(status)

    if st_val == 'FOUND':
        return CompletenessState.VERIFIED_AVAILABLE, 'Verified from official document'
    if st_val == 'NEEDS_REVIEW':
        return CompletenessState.NEEDS_REVIEW, f.note or 'Requires verification review'
    if st_val == 'NOT_PUBLISHED':
        if infra_failed:
            return CompletenessState.INFRASTRUCTURE_FAILURE, 'Pipeline could not finish search'
        return CompletenessState.NOT_YET_PUBLISHED, f.note or 'Not published by authority'
    if st_val == 'NOT_EXTRACTED':
        # A reading a person withheld (review.py) is held back, not failed and not absent:
        # the section stays under review, and the note says who held it and why.
        if 'withheld by reviewer' in (f.note or ''):
            return CompletenessState.NEEDS_REVIEW, f.note
        if infra_failed:
            return CompletenessState.INFRASTRUCTURE_FAILURE, 'Infrastructure failure during build'
        if unreadable_docs:
            return CompletenessState.SOURCE_UNREADABLE, 'Source document text was unreadable'
        if _reader_raised(rec, field_name):
            return CompletenessState.EXTRACTION_FAILED, 'Reader failed on a document that carries this section'
        if field_name in searched_not_found:
            return (CompletenessState.SOURCE_NOT_FOUND_AFTER_SEARCH,
                    'Readers found no such clause and a search of the authority domain found no document for it')
        return CompletenessState.EXTRACTION_FAILED, f.note or 'Extractor found nothing and no search was made'

    return CompletenessState.EXTRACTION_FAILED, 'Unknown field state'


def evaluate_completeness(rec: ExamRecord, sources: Any,
                          build_result: Any = None,
                          reacquisition_attempts: int = 0,
                          searched_not_found: frozenset = frozenset(),
                          not_applicable: dict | None = None) -> ExamCompletenessReport:
    """Evaluates user-centric completeness across all 17 authoritative GovOS sections.

    Answers from the student's perspective:
      'Which of the 17 workspace areas have verified useful information,
       which are derived from verified facts, which are legitimately not yet published,
       and which encountered extraction/infrastructure gaps?'
    """
    infra_failed = bool(getattr(sources, 'infrastructure_failed', False))
    unreadable_docs = bool(getattr(sources, 'has_unreadable_docs', False))

    sections: list[SectionCompleteness] = []
    verified_cnt = 0
    derived_cnt = 0
    not_yet_published_cnt = 0
    not_applicable_cnt = 0
    needs_review_cnt = 0
    failure_cnt = 0
    source_not_found_cnt = 0

    cycle = getattr(rec, 'cycle', '') or (rec.exam_id.split('-')[-1] if '-' in rec.exam_id else '2026')

    for s_def in GOVOS_17_SECTIONS:
        field_states: dict[str, str] = {}
        states_list: list[CompletenessState] = []
        ev_count = 0
        notes: list[str] = []

        # -------------------------------------------------------------
        # Case A: RUNTIME_DERIVED sections (Study Roadmap, Mock Tests)
        # -------------------------------------------------------------
        if s_def.nature is SectionNature.RUNTIME_DERIVED:
            # Check availability of prerequisite verified factual inputs
            pat_f = rec.fields.get('examPattern')
            syl_f = rec.fields.get('syllabus')

            pat_ok = pat_f and getattr(pat_f, 'status', None) == RecordStatus.FOUND
            syl_ok = syl_f and getattr(syl_f, 'status', None) == RecordStatus.FOUND

            if s_def.id == 'roadmap':
                if pat_ok and syl_ok:
                    final_state = CompletenessState.SUPPORTED_AND_PROJECTED
                    student_summary = 'Study roadmap derived from verified pattern and syllabus topics'
                    tech_note = 'Generated dynamically from verified examPattern and syllabus trees'
                    derived_cnt += 1
                elif infra_failed:
                    final_state = CompletenessState.INFRASTRUCTURE_FAILURE
                    student_summary = 'Connection error during official document acquisition'
                    tech_note = 'Infrastructure failure prevented acquiring syllabus/pattern'
                    failure_cnt += 1
                else:
                    final_state = CompletenessState.NOT_YET_PUBLISHED
                    student_summary = 'Awaiting verified syllabus and pattern to generate roadmap'
                    tech_note = 'Prerequisite factual fields not yet verified'
                    not_yet_published_cnt += 1

            elif s_def.id == 'mock-tests':
                if pat_ok:
                    final_state = CompletenessState.SUPPORTED_AND_PROJECTED
                    student_summary = 'Interactive mock simulator configured from verified exam pattern'
                    tech_note = 'Runtime simulator ready with verified stages/marking scheme'
                    derived_cnt += 1
                elif infra_failed:
                    final_state = CompletenessState.INFRASTRUCTURE_FAILURE
                    student_summary = 'Connection error during official document acquisition'
                    tech_note = 'Infrastructure failure prevented acquiring exam pattern'
                    failure_cnt += 1
                else:
                    final_state = CompletenessState.NOT_YET_PUBLISHED
                    student_summary = 'Mock test simulator will activate once exam pattern is officially released'
                    tech_note = 'Awaiting verified examPattern'
                    not_yet_published_cnt += 1
            else:
                final_state = CompletenessState.NOT_YET_PUBLISHED
                student_summary = 'Runtime derived capability'
                tech_note = ''

            field_states['pattern'] = 'FOUND' if pat_ok else 'MISSING'
            field_states['syllabus'] = 'FOUND' if syl_ok else 'MISSING'

            sec = SectionCompleteness(
                section_order=s_def.order,
                section_num=s_def.num,
                section_id=s_def.id,
                section_title=s_def.title,
                nature=s_def.nature,
                state=final_state,
                is_applicable=True,
                evidence_count=1 if final_state is CompletenessState.SUPPORTED_AND_PROJECTED else 0,
                student_status_summary=student_summary,
                technical_note=tech_note,
                fields=field_states,
            )
            sections.append(sec)
            continue

        # -------------------------------------------------------------
        # Case B: FACTUAL_EXTRACTION sections
        # -------------------------------------------------------------
        for fn in s_def.canonical_fields:
            if fn == 'officialSources':
                if rec.sources_read:
                    field_states[fn] = 'FOUND'
                    states_list.append(CompletenessState.VERIFIED_AVAILABLE)
                    ev_count += len(rec.sources_read)
                elif infra_failed:
                    field_states[fn] = 'INFRASTRUCTURE_FAILURE'
                    states_list.append(CompletenessState.INFRASTRUCTURE_FAILURE)
                else:
                    field_states[fn] = 'SOURCE_NOT_FOUND_AFTER_SEARCH'
                    states_list.append(CompletenessState.SOURCE_NOT_FOUND_AFTER_SEARCH)
                continue

            # examDayChecklist and faqs are read by their own readers and classified like every
            # other field. They used to be labelled NOT_YET_PUBLISHED whenever absent, which
            # asserted something about the authority that no source had said.

            if fn == 'nextSteps':
                f = rec.fields.get('nextSteps')
                if f and f.ok and getattr(f, 'value', None):
                    field_states[fn] = 'FOUND'
                    states_list.append(CompletenessState.VERIFIED_AVAILABLE)
                    ev_count += 1
                else:
                    field_states[fn] = 'NOT_YET_PUBLISHED'
                    states_list.append(CompletenessState.NOT_YET_PUBLISHED)
                continue

            state, note = _classify_field_status(rec, fn, infra_failed, unreadable_docs,
                                                 searched_not_found, not_applicable)
            field_states[fn] = state.value
            states_list.append(state)
            if note:
                notes.append(note)

            f = rec.fields.get(fn)
            if f and getattr(f, 'citation', None):
                ev_count += 1

        # Synthesize overall section state from its field states
        if CompletenessState.INFRASTRUCTURE_FAILURE in states_list:
            final_state = CompletenessState.INFRASTRUCTURE_FAILURE
            student_summary = 'Network or search connection error while retrieving official documents'
            failure_cnt += 1
        elif CompletenessState.SOURCE_UNREADABLE in states_list:
            final_state = CompletenessState.SOURCE_UNREADABLE
            student_summary = 'Official document was found but could not be parsed as text (scanned image)'
            failure_cnt += 1
        elif any(s is CompletenessState.VERIFIED_AVAILABLE for s in states_list):
            if any(s is CompletenessState.NEEDS_REVIEW for s in states_list):
                final_state = CompletenessState.NEEDS_REVIEW
                student_summary = 'Official information extracted but undergoing evidence verification'
                needs_review_cnt += 1
            else:
                final_state = CompletenessState.VERIFIED_AVAILABLE
                student_summary = 'Verified from official government source with evidence'
                verified_cnt += 1
        elif CompletenessState.EXTRACTION_FAILED in states_list:
            final_state = CompletenessState.EXTRACTION_FAILED
            student_summary = 'Document found, but detailed section could not be extracted'
            failure_cnt += 1
        elif CompletenessState.NEEDS_REVIEW in states_list:
            final_state = CompletenessState.NEEDS_REVIEW
            student_summary = 'Information requires human verification review'
            needs_review_cnt += 1
        elif CompletenessState.NOT_YET_PUBLISHED in states_list:
            final_state = CompletenessState.NOT_YET_PUBLISHED
            student_summary = 'Not yet released or announced by the authority for this cycle'
            not_yet_published_cnt += 1
        elif CompletenessState.NOT_APPLICABLE in states_list:
            final_state = CompletenessState.NOT_APPLICABLE
            student_summary = 'Not applicable to this examination'
            not_applicable_cnt += 1
        else:
            # Every remaining state is SOURCE_NOT_FOUND_AFTER_SEARCH: the readers and a search
            # of the authority's own domain found nothing. That is not a claim the authority
            # published nothing -- the wording says so, and it is counted on its own.
            final_state = CompletenessState.SOURCE_NOT_FOUND_AFTER_SEARCH
            student_summary = ('GovOS searched the official sources it found and could not locate '
                               'this yet; it may still be published elsewhere')
            source_not_found_cnt += 1

        sec = SectionCompleteness(
            section_order=s_def.order,
            section_num=s_def.num,
            section_id=s_def.id,
            section_title=s_def.title,
            nature=s_def.nature,
            state=final_state,
            is_applicable=True,
            evidence_count=ev_count,
            student_status_summary=student_summary,
            technical_note='; '.join(notes)[:240] if notes else '',
            fields=field_states,
        )
        sections.append(sec)

    return ExamCompletenessReport(
        exam_id=rec.exam_id,
        cycle=cycle,
        total_sections=len(sections),
        verified_count=verified_cnt,
        derived_count=derived_cnt,
        not_yet_published_count=not_yet_published_cnt,
        not_applicable_count=not_applicable_cnt,
        needs_review_count=needs_review_cnt,
        failure_count=failure_cnt,
        source_not_found_count=source_not_found_cnt,
        sections=sections,
        reacquisition_performed=reacquisition_attempts > 0,
        reacquisition_attempts=reacquisition_attempts,
    )
