"""Parsing official corrigenda notices and extracting verified revision deltas.

Governed by GOVOS_MASTER_SPEC.md (Phase 2).
When an authority issues a corrigendum, addendum, errata, or amendment notice, it does
not replace the original notification in the archive: it modifies specific clauses or facts
while the rest of the notification remains in force.

Three rules run through this module:
  1. A revision is an explicit relationship (SUPERSEDE / AMEND), never a silent deletion.
  2. The predecessor fact is preserved alongside the new fact.
  3. Evidence spans must verify verbatim in the corrigendum document.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .overlay import ExamFactOverlay, ExamOverlayScope, OverlayKind
from .schema import Fact, Scope, ScopeKind, ScopeRef, SourceDocument, SourceEvidence, Status

#: Phrases indicating a modification or correction
_CORRIGENDA_CUES = re.compile(
    r'\b(?:corrigend\w*|addend\w*|amend\w*|errat\w*|partial\s+modification|revised\s+notice|'
    r'extension\s+of\s+(?:last\s+)?date|reschedul\w*|postpon\w*)\b',
    re.I
)

#: Date extension patterns: "extended from <date> to <date>" or "extended up to <date>"
_DATE_EXTENSION = re.compile(
    r'(?:extended\s+(?:from\s+([^\n,;]+?)\s+)?(?:to|upto|up\s+to|till)\s+([^\n,;.]+)|'
    r'(?:last\s+date|closing\s+date|exam\w*\s+date|date\s+of\s+examination)\s+(?:is\s+)?(?:revised|extended|rescheduled)\s+(?:to|till|as)\s+([^\n,;.]+))',
    re.I
)

#: Vacancy revision patterns: "vacancies (are )?revised from X to Y" or "revised to Y vacancies"
_VACANCY_REVISION = re.compile(
    r'(?:vacanc\w*\s+(?:are\s+)?revised\s+(?:from\s+(\d+)\s+)?to\s+(\d+)|'
    r'revised\s+(?:total\s+)?vacanc\w*\s*[:–—\-]?\s*(\d+))',
    re.I
)


@dataclass
class CorrigendumNotice:
    """One official amendment extracted from a corrigendum document."""
    id: str
    exam_id: str
    cycle: str
    title: str
    affected_domain: str              # 'dates', 'posts', 'vacancies', 'eligibility', etc.
    affected_field: str               # 'application_close', 'exam_date', 'vacancies_total', etc.
    old_value: Optional[Any] = None   # What the previous document stated, if mentioned
    new_value: Any = None             # The new revised value
    effective_date: str = ''          # When the revision was issued / takes effect
    evidence_span: str = ''
    source_url: str = ''
    source_title: str = ''
    status: Status = Status.VERIFIED
    note: str = ''

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'examId': self.exam_id,
            'cycle': self.cycle,
            'title': self.title,
            'affectedDomain': self.affected_domain,
            'affectedField': self.affected_field,
            'oldValue': self.old_value,
            'newValue': self.new_value,
            'effectiveDate': self.effective_date,
            'evidenceSpan': self.evidence_span,
            'sourceUrl': self.source_url,
            'sourceTitle': self.source_title,
            'status': self.status.value if hasattr(self.status, 'value') else str(self.status),
            'note': self.note,
        }


def is_corrigendum_text(text: str) -> bool:
    """Whether the document identifies itself as a corrigendum or amendment."""
    return bool(_CORRIGENDA_CUES.search(text[:3000]))


def extract_corrigenda(doc: SourceDocument, text: str, *,
                       exam_id: str, cycle: str = '') -> list[CorrigendumNotice]:
    """Extracts all amendment statements from a corrigendum document with verbatim evidence."""
    notices: list[CorrigendumNotice] = []
    lines = [line.strip() for line in text.split('\n') if line.strip()]

    # Check date extensions
    for line in lines:
        m_date = _DATE_EXTENSION.search(line)
        if m_date:
            ev = Evidence(span=line, source_url=doc.url, document_title=doc.title, page=1,
                          reading='date extension/rescheduling statement')
            if ev.verify(text) is not EvidenceStatus.VERIFIED:
                continue

            # Parse out the revised date string
            groups = [g for g in m_date.groups() if g is not None]
            new_val = groups[-1].strip() if groups else ''
            old_val = groups[0].strip() if len(groups) > 1 and groups[0] else None

            # Determine whether this is application close or exam date
            low = line.lower()
            if any(k in low for k in ('exam', 'tier', 'prelim', 'written', 'conduct')):
                field_name = 'exam_date'
            else:
                field_name = 'application_close'

            c_id = f"corr-{exam_id}-date-{len(notices)+1}"
            notices.append(CorrigendumNotice(
                id=c_id,
                exam_id=exam_id,
                cycle=cycle or doc.published_at[:4],
                title=f"Corrigendum: Revision of {field_name.replace('_', ' ').title()}",
                affected_domain='dates',
                affected_field=field_name,
                old_value=old_val,
                new_value=new_val,
                effective_date=doc.published_at or doc.accessed_at,
                evidence_span=line,
                source_url=doc.url,
                source_title=doc.title,
                status=Status.VERIFIED,
                note=f"Revised from {old_val} to {new_val}" if old_val else f"Revised to {new_val}"
            ))

        # Check vacancy revisions
        m_vac = _VACANCY_REVISION.search(line)
        if m_vac:
            ev = Evidence(span=line, source_url=doc.url, document_title=doc.title, page=1,
                          reading='vacancy revision statement')
            if ev.verify(text) is not EvidenceStatus.VERIFIED:
                continue

            nums = [int(n) for n in m_vac.groups() if n is not None and n.isdigit()]
            if nums:
                new_cnt = nums[-1]
                old_cnt = nums[0] if len(nums) > 1 else None
                c_id = f"corr-{exam_id}-vac-{len(notices)+1}"
                notices.append(CorrigendumNotice(
                    id=c_id,
                    exam_id=exam_id,
                    cycle=cycle or doc.published_at[:4],
                    title="Corrigendum: Revision of Total Vacancies",
                    affected_domain='overview',
                    affected_field='vacanciesTotal',
                    old_value=old_cnt,
                    new_value=new_cnt,
                    effective_date=doc.published_at or doc.accessed_at,
                    evidence_span=line,
                    source_url=doc.url,
                    source_title=doc.title,
                    status=Status.VERIFIED,
                    note=f"Vacancies revised from {old_cnt} to {new_cnt}" if old_cnt else f"Vacancies revised to {new_cnt}"
                ))

    return notices


def notices_to_overlays(notices: list[CorrigendumNotice],
                        existing_overlays: list[ExamFactOverlay] | None = None) -> list[ExamFactOverlay]:
    """Converts extracted corrigenda into SUPERSEDE overlays linked to predecessor facts."""
    overlays: list[ExamFactOverlay] = []
    existing = existing_overlays or []

    for notice in notices:
        # Construct provenance dict
        prov = {
            'id': f"prov-{notice.id}",
            'documentTitle': notice.source_title,
            'officialUrl': notice.source_url,
            'pageNumber': 1,
            'clauseNumber': 'Corrigendum Notice',
            'publishedDate': notice.effective_date,
            'verifiedDate': notice.effective_date,
            'verifiedBy': 'GovOS Corrigenda Extraction Engine',
            'taxonomyType': 'REVISION',
            'verificationLevel': 'OFFICIALLY_VERIFIED',
            'excerptText': notice.evidence_span[:600]
        }

        # Look for matching predecessor overlay or entity
        target_overlay: Optional[ExamFactOverlay] = None
        for o in existing:
            if o.domain == notice.affected_domain:
                if notice.affected_domain == 'dates':
                    # Check if date type matches
                    v = o.value if isinstance(o.value, dict) else {}
                    t = str(v.get('type', '')).lower()
                    if ('close' in notice.affected_field and 'close' in t) or \
                       ('exam' in notice.affected_field and 'exam' in t):
                        target_overlay = o
                        break
                elif notice.affected_domain == 'overview' and notice.affected_field == 'vacanciesTotal':
                    target_overlay = o
                    break

        if notice.affected_domain == 'dates':
            d_val = {
                'id': f"date-{notice.exam_id}-{notice.affected_field}",
                'type': 'APPLICATION_CLOSE' if 'close' in notice.affected_field else 'EXAM_TIER1',
                'label': f"Revised {notice.affected_field.replace('_', ' ').title()}",
                'dateTimeStr': f"{notice.new_value} 00:00:00" if len(str(notice.new_value)) <= 10 else str(notice.new_value),
                'status': 'AVAILABLE',
                'provenance': prov
            }
            overlay = ExamFactOverlay(
                id=f"overlay-{notice.id}",
                exam_id=notice.exam_id,
                cycle=notice.cycle,
                domain='dates',
                kind=OverlayKind.SUPERSEDE if target_overlay else OverlayKind.ADD,
                value=d_val,
                provenance=prov,
                status='VERIFIED',
                target_id=target_overlay.id if target_overlay else None,
                supersedes_id=target_overlay.id if target_overlay else None,
                previous_value=target_overlay.value if target_overlay else notice.old_value,
                effective_date=notice.effective_date,
                created_by='GovOS Corrigenda Pipeline'
            )
            overlays.append(overlay)

        elif notice.affected_domain == 'overview':
            overlay = ExamFactOverlay(
                id=f"overlay-{notice.id}",
                exam_id=notice.exam_id,
                cycle=notice.cycle,
                domain='overview',
                kind=OverlayKind.SUPERSEDE if target_overlay else OverlayKind.ADD,
                value={'vacanciesTotal': notice.new_value},
                provenance=prov,
                status='VERIFIED',
                target_id=target_overlay.id if target_overlay else None,
                supersedes_id=target_overlay.id if target_overlay else None,
                previous_value={'vacanciesTotal': notice.old_value} if notice.old_value else None,
                effective_date=notice.effective_date,
                created_by='GovOS Corrigenda Pipeline'
            )
            overlays.append(overlay)

    return overlays
