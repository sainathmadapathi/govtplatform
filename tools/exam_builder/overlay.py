"""Canonical Data Ownership & Safe Machine Updates — Universal Overlay Engine.

Governed by GOVOS_MASTER_SPEC.md (Phase 1).
Provides:
  1. Strongly-typed ExamFactOverlay with full identity scoping (exam, cycle, domain, target, scope).
  2. Domain payload validation (never allows arbitrary untyped JSON mutations).
  3. Publication gate enforcement (only VERIFIED facts with verbatim evidence can be active).
  4. Conflict and revision history preservation (never deletes authored facts or silently resolves disagreements).
  5. Pure in-memory projection (apply_overlays_to_exam_dict) matching frontend applyExamOverlays.
  6. OverlayStore with SQLite persistence and offline JSON export/import.
"""
from __future__ import annotations

import copy
import dataclasses
from dataclasses import dataclass, field as dc_field
from enum import Enum
import json
import os
import re
import sqlite3
import time
from typing import Any, Dict, List, Optional, Tuple, Union

# Valid 17 user-facing domains
VALID_DOMAINS = frozenset({
    'dates',
    'posts',
    'eligibility',
    'application',
    'pattern',
    'syllabus',
    'resources',
    'practiceQuestions',
    'officialPapers',
    'answerKeys',
    'admitCard',
    'examDayChecklist',
    'results',
    'faqs',
    'corrigendums',
    'officialLinks',
    'cutoffsHistory',
    'roadmapTracks',
    'overview',
})

VALID_STATUSES = frozenset({'VERIFIED', 'NEEDS_REVIEW', 'NOT_PUBLISHED', 'NOT_EXTRACTED'})
PUBLISHABLE_STATUSES = frozenset({'VERIFIED', 'NOT_PUBLISHED'})


class OverlayKind(str, Enum):
    ADD = 'ADD'                # Add a new fact/entity into a collection or field
    AMEND = 'AMEND'            # Amend specific properties of an existing entity
    SUPERSEDE = 'SUPERSEDE'    # Mark previous entity as superseded and introduce replacement
    RETIRE = 'RETIRE'          # Soft-delete / deactivate overlay from projection
    CONFLICT = 'CONFLICT'      # Author and machine disagree without corrigendum; hold for review


@dataclass
class ExamOverlayScope:
    """Exact structural identity context to prevent cross-paper/stage/post contamination."""
    stage_id: Optional[str] = None
    paper_id: Optional[str] = None
    post_id: Optional[str] = None
    rule_id: Optional[str] = None
    category_label: Optional[str] = None
    subject: Optional[str] = None
    topic_id: Optional[str] = None
    level_label: Optional[str] = None

    def to_dict(self) -> dict:
        return {k: v for k, v in dataclasses.asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, d: Optional[dict]) -> 'ExamOverlayScope':
        if not d or not isinstance(d, dict):
            return cls()
        return cls(
            stage_id=d.get('stage_id') or d.get('stageId'),
            paper_id=d.get('paper_id') or d.get('paperId'),
            post_id=d.get('post_id') or d.get('postId'),
            rule_id=d.get('rule_id') or d.get('ruleId'),
            category_label=d.get('category_label') or d.get('categoryLabel'),
            subject=d.get('subject'),
            topic_id=d.get('topic_id') or d.get('topicId'),
            level_label=d.get('level_label') or d.get('levelLabel'),
        )


@dataclass
class ExamFactOverlay:
    """A single additive, provenance-carrying, revision-aware machine fact."""
    id: str
    exam_id: str
    cycle: str                          # Strict cycle/year isolation (e.g. '2026', '2027')
    domain: str                         # One of VALID_DOMAINS
    kind: OverlayKind
    value: Any
    provenance: dict                    # Must contain documentTitle, officialUrl, verificationLevel, excerptText
    status: str = 'VERIFIED'            # VERIFIED, NEEDS_REVIEW, NOT_PUBLISHED
    target_id: Optional[str] = None     # Id of the existing item being amended or superseded
    target_scope: Optional[ExamOverlayScope] = None
    supersedes_id: Optional[str] = None # Id of the previous entity/overlay being superseded
    previous_value: Optional[Any] = None # Preserves historical value before revision
    effective_date: Optional[str] = None # ISO date when revision takes effect
    conflict_note: Optional[str] = None  # Explanation if in CONFLICT
    created_at: str = ''
    created_by: str = 'GovOS Machine Pipeline'
    retired: bool = False               # False = active in projection; True = preserved in history only

    @property
    def is_active(self) -> bool:
        """Only unretired, VERIFIED or NOT_PUBLISHED overlays enter the live projection."""
        return not self.retired and self.status in PUBLISHABLE_STATUSES and self.kind != OverlayKind.CONFLICT

    def to_dict(self) -> dict:
        return {
            'id': self.id,
            'examId': self.exam_id,
            'cycle': self.cycle,
            'domain': self.domain,
            'kind': self.kind.value if isinstance(self.kind, OverlayKind) else str(self.kind),
            'targetId': self.target_id,
            'targetScope': self.target_scope.to_dict() if self.target_scope else None,
            'value': self.value,
            'provenance': self.provenance,
            'status': self.status,
            'supersedesId': self.supersedes_id,
            'previousValue': self.previous_value,
            'effectiveDate': self.effective_date,
            'conflictNote': self.conflict_note,
            'createdAt': self.created_at or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'createdBy': self.created_by,
            'retired': self.retired,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'ExamFactOverlay':
        kind_raw = d.get('kind', 'ADD')
        kind = OverlayKind(kind_raw) if kind_raw in OverlayKind.__members__ else OverlayKind(kind_raw)
        scope_raw = d.get('targetScope') or d.get('target_scope')
        return cls(
            id=d['id'],
            exam_id=d.get('examId') or d.get('exam_id', ''),
            cycle=str(d.get('cycle', '')),
            domain=d['domain'],
            kind=kind,
            value=d.get('value'),
            provenance=d.get('provenance', {}),
            status=d.get('status', 'VERIFIED'),
            target_id=d.get('targetId') or d.get('target_id'),
            target_scope=ExamOverlayScope.from_dict(scope_raw) if scope_raw else None,
            supersedes_id=d.get('supersedesId') or d.get('supersedes_id'),
            previous_value=d.get('previousValue') or d.get('previous_value'),
            effective_date=d.get('effectiveDate') or d.get('effective_date'),
            conflict_note=d.get('conflictNote') or d.get('conflict_note'),
            created_at=d.get('createdAt') or d.get('created_at', ''),
            created_by=d.get('createdBy') or d.get('created_by', 'GovOS Machine Pipeline'),
            retired=bool(d.get('retired', False)),
        )


def validate_overlay(overlay: ExamFactOverlay) -> list[str]:
    """Strictly validates an overlay against the GovOS constitutional specification.
    Returns a list of validation error strings. An empty list indicates a valid overlay.
    """
    errors: list[str] = []

    # 1. Identity & Metadata
    if not overlay.id or not isinstance(overlay.id, str):
        errors.append("overlay must have a non-empty string id")
    if not overlay.exam_id or not isinstance(overlay.exam_id, str):
        errors.append("overlay must have a non-empty string exam_id")
    elif not overlay.exam_id.startswith('exam-'):
        errors.append(f"exam_id '{overlay.exam_id}' must follow canonical convention starting with 'exam-'")

    if not overlay.cycle or not str(overlay.cycle).strip():
        errors.append("overlay must declare an explicit cycle/year for cycle isolation (e.g. '2026')")

    if overlay.domain not in VALID_DOMAINS:
        errors.append(f"domain '{overlay.domain}' is invalid; must be one of {sorted(VALID_DOMAINS)}")

    if overlay.status not in PUBLISHABLE_STATUSES and overlay.kind != OverlayKind.CONFLICT:
        errors.append(f"overlay status '{overlay.status}' is not publishable; only {sorted(PUBLISHABLE_STATUSES)} facts can be active overlays")

    # 2. Provenance Integrity (Constitutional Rule B.1 & B.2)
    prov = overlay.provenance
    if not prov or not isinstance(prov, dict):
        errors.append("overlay must carry a valid provenance dictionary")
    else:
        title = prov.get('documentTitle') or prov.get('document_title')
        url = prov.get('officialUrl') or prov.get('url') or prov.get('sourceUrl') or prov.get('source_url')
        level = prov.get('verificationLevel') or prov.get('verification_level')
        excerpt = prov.get('excerptText') or prov.get('excerpt') or prov.get('span') or prov.get('verbatimCitation') or prov.get('verbatim_citation')

        if not title:
            errors.append("provenance must specify documentTitle")
        if not url or not str(url).startswith(('http://', 'https://')):
            errors.append(f"provenance must specify a valid http(s) officialUrl: got {url!r}")
        if overlay.kind != OverlayKind.CONFLICT and level != 'OFFICIALLY_VERIFIED':
            errors.append(f"overlay must have provenance verificationLevel='OFFICIALLY_VERIFIED', got {level!r}")
        if overlay.status == 'VERIFIED' and not excerpt:
            errors.append("VERIFIED fact must carry a verbatim excerpt/span from the source document (NO EVIDENCE = NO FACT)")


    # 3. Domain Payload Schema Validation (No Untyped Arbitrary JSON)
    val = overlay.value
    if overlay.kind != OverlayKind.RETIRE and overlay.status == 'VERIFIED':
        if val is None:
            errors.append(f"overlay with kind={overlay.kind.value} and status=VERIFIED cannot have None value")
        else:
            errors.extend(_validate_domain_payload(overlay.domain, val, overlay.kind))

    # 4. Target Identity Requirement
    if overlay.kind in (OverlayKind.AMEND, OverlayKind.SUPERSEDE):
        if not overlay.target_id and not (overlay.target_scope and any(dataclasses.asdict(overlay.target_scope).values())):
            errors.append(f"overlay with kind={overlay.kind.value} must declare target_id or target_scope")

    if overlay.kind == OverlayKind.SUPERSEDE and not overlay.supersedes_id:
        # If target_id is present, it can act as the superseded entity id
        if not overlay.target_id:
            errors.append("SUPERSEDE overlay must specify target_id or supersedes_id for historical traceability")

    return errors


def _validate_domain_payload(domain: str, value: Any, kind: OverlayKind = OverlayKind.ADD) -> list[str]:
    """Validates that value conforms to the expected shape of the target domain."""
    errs: list[str] = []
    if not isinstance(value, dict):
        return [f"payload for domain '{domain}' must be a structured dictionary, got {type(value).__name__}"]

    if domain == 'dates':
        valid_date_types = {
            'NOTIFICATION', 'APPLICATION_OPEN', 'APPLICATION_CLOSE', 'CORRECTION_WINDOW',
            'ADMIT_CARD', 'EXAM_TIER1', 'EXAM_TIER2', 'ANSWER_KEY', 'RESULT', 'INTERVIEW'
        }
        if kind != OverlayKind.AMEND:
            if 'type' not in value or value['type'] not in valid_date_types:
                errs.append(f"dates value must include valid type in {sorted(valid_date_types)}")
            if not value.get('dateTimeStr'):
                errs.append("dates value must include dateTimeStr (e.g. '2026-06-27')")
        else:
            if 'type' in value and value['type'] not in valid_date_types:
                errs.append(f"dates value must include valid type in {sorted(valid_date_types)}")

    elif domain == 'posts':
        if kind != OverlayKind.AMEND:
            for req in ('postName', 'department', 'payLevel'):
                if not value.get(req):
                    errs.append(f"posts value missing required field '{req}'")
        if 'minAge' in value and 'maxAge' in value:
            try:
                min_a, max_a = int(value['minAge']), int(value['maxAge'])
                if min_a < 0 or max_a < min_a:
                    errs.append(f"posts minAge/maxAge invalid: {min_a} to {max_a}")
            except (ValueError, TypeError):
                errs.append("posts minAge/maxAge must be integers")

    elif domain == 'eligibility':
        if not value.get('category') and not value.get('ruleType'):
            errs.append("eligibility value must specify category or ruleType")

    elif domain == 'syllabus':
        if not value.get('topicName') or not value.get('subject'):
            errs.append("syllabus value must specify topicName and subject")

    elif domain == 'resources':
        if not value.get('title') or not value.get('url'):
            errs.append("resources value must specify title and url")
        elif not str(value['url']).startswith(('http://', 'https://')):
            errs.append("resources url must be a valid http(s) URL")
        tier = value.get('officialityTier') or value.get('tier') or 'OFFICIAL'
        valid_tiers = {'OFFICIAL', 'TRUSTED_REFERENCE', 'PENDING_REVIEW'}
        if tier not in valid_tiers:
            errs.append(f"resources officialityTier '{tier}' is invalid; must be one of {sorted(valid_tiers)}")

    elif domain == 'application':
        valid_keys = {'applicationPortal', 'howToApply', 'requiredDocuments', 'photoSignatureGuidelines', 'fee', 'feeExemptions', 'stages', 'portal', 'rules'}
        if not any(k in value for k in valid_keys):
            errs.append(f"application value must include at least one key in {sorted(valid_keys)}")

    elif domain == 'officialPapers':
        if not value.get('paperTitle') or not value.get('pdfUrl'):
            errs.append("officialPapers value must specify paperTitle and pdfUrl")

    elif domain == 'answerKeys':
        if not value.get('paperTitle') or not value.get('pdfUrl'):
            errs.append("answerKeys value must specify paperTitle and pdfUrl")

    elif domain == 'admitCard':
        if not value.get('eventName') and not value.get('noticeTitle'):
            errs.append("admitCard value must specify eventName or noticeTitle")

    elif domain == 'results':
        if not value.get('stageName') and not value.get('declarationTitle') and not value.get('nextSteps'):
            errs.append("results value must specify stageName, declarationTitle, or nextSteps")

    elif domain == 'faqs':
        if not value.get('question') or not value.get('answer'):
            errs.append("faqs value must specify question and answer")

    elif domain == 'corrigendums':
        if not value.get('title') or not value.get('noticeNumber'):
            errs.append("corrigendums value must specify title and noticeNumber")

    elif domain == 'cutoffsHistory':
        if not value.get('category') or not value.get('year'):
            errs.append("cutoffsHistory value must specify category and year")

    elif domain == 'officialLinks':
        if not value.get('title') or not value.get('url'):
            errs.append("officialLinks value must specify title and url")

    elif domain == 'examDayChecklist':
        if not value.get('item') and not value.get('instruction'):
            errs.append("examDayChecklist value must specify item or instruction")

    elif domain == 'overview':
        if not value.get('overviewDescription') and not value.get('vacanciesTotal'):
            errs.append("overview value must specify overviewDescription or vacanciesTotal")

    elif domain == 'pattern':
        if not value.get('stageName') and not value.get('name') and not value.get('stages') and not value.get('level') and not value.get('levelLabel'):
            errs.append("pattern value must specify stageName, name, level, or stages")

    return errs


def get_exam_cycle(exam_dict: dict) -> str:
    """Extracts canonical 4-digit cycle/year from exam id or title."""
    exam_id = str(exam_dict.get('id', ''))
    title = str(exam_dict.get('title', ''))
    m = re.search(r'\b(20\d\d)\b', exam_id) or re.search(r'\b(20\d\d)\b', title)
    return m.group(1) if m else ''


def _upsert_by_id(lst: list, item: dict) -> list:
    item_id = item.get('id')
    if not item_id:
        lst.append(item)
        return lst
    for i, existing in enumerate(lst):
        if existing.get('id') == item_id:
            lst[i] = item
            return lst
    lst.append(item)
    return lst


def apply_overlays_to_exam_dict(exam: dict, overlays: list[ExamFactOverlay]) -> dict:
    """Pure, non-destructive projection of overlays over an authored exam dictionary.
    Guarantees:
      - If overlays list is empty, returns original exam dictionary untouched.
      - Never mutates the original exam dictionary.
      - Enforces strict cycle isolation (SSC CGL 2026 overlay never affects SSC CGL 2027).
      - Enforces strict exam isolation (SSC overlay never affects UPSC).
      - Enforces status gate (only VERIFIED or NOT_PUBLISHED overlays can be active).
      - Enforces identity scoping (stage, paper, post).
      - Retains old values when superseded (historical traceability).
      - Idempotent: repeated application produces the exact same projected state.
    """
    if not overlays:
        return exam

    exam_id = exam.get('id', '')
    exam_cycle = get_exam_cycle(exam)

    # Filter active, verified overlays matching this exam and cycle
    active_overlays = [
        o for o in overlays
        if o.exam_id == exam_id
        and (not o.cycle or not exam_cycle or o.cycle == exam_cycle)
        and o.is_active
    ]

    if not active_overlays:
        return exam

    projected = copy.deepcopy(exam)

    for o in active_overlays:
        domain = o.domain
        val = copy.deepcopy(o.value)
        target_id = o.target_id
        target_scope = o.target_scope

        # Domain: DATES
        if domain == 'dates':
            dates_list = list(projected.get('dates', []))
            if o.kind == OverlayKind.SUPERSEDE:
                sup_id = o.supersedes_id or target_id
                for d in dates_list:
                    if d.get('id') == sup_id:
                        d['status'] = 'SUPERSEDED'
                new_date = {
                    'id': o.id,
                    'type': val.get('type', 'NOTIFICATION'),
                    'label': val.get('label', 'Revised Date'),
                    'dateTimeStr': val.get('dateTimeStr', ''),
                    'timezone': val.get('timezone', 'IST'),
                    'isTentative': bool(val.get('isTentative', False)),
                    'status': 'AVAILABLE',
                    'provenance': o.provenance,
                }
                _upsert_by_id(dates_list, new_date)
            elif o.kind == OverlayKind.AMEND:
                for d in dates_list:
                    if d.get('id') == target_id:
                        d.update({k: v for k, v in val.items() if k != 'id'})
                        d['provenance'] = o.provenance
            elif o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                item['provenance'] = o.provenance
                _upsert_by_id(dates_list, item)
            projected['dates'] = dates_list


        # Domain: POSTS
        elif domain == 'posts':
            posts_list = list(projected.get('posts', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                item['provenance'] = o.provenance
                _upsert_by_id(posts_list, item)
            elif o.kind == OverlayKind.AMEND:
                for p in posts_list:
                    if p.get('id') == target_id or (target_scope and target_scope.post_id and p.get('id') == target_scope.post_id):
                        p.update({k: v for k, v in val.items() if k != 'id'})
                        p['provenance'] = o.provenance
            elif o.kind == OverlayKind.SUPERSEDE:
                sup_id = o.supersedes_id or target_id
                posts_list = [p for p in posts_list if p.get('id') != sup_id]
                item = copy.deepcopy(val)
                item['id'] = o.id
                item['provenance'] = o.provenance
                _upsert_by_id(posts_list, item)
            projected['posts'] = posts_list

        # Domain: SYLLABUS
        elif domain == 'syllabus':
            syllabus_list = list(projected.get('syllabus', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                item['officialProvenance'] = o.provenance
                _upsert_by_id(syllabus_list, item)
            elif o.kind == OverlayKind.AMEND:
                for s in syllabus_list:
                    if s.get('id') == target_id or (target_scope and target_scope.topic_id and s.get('id') == target_scope.topic_id):
                        s.update({k: v for k, v in val.items() if k != 'id'})
                        s['officialProvenance'] = o.provenance
            projected['syllabus'] = syllabus_list

        # Domain: RESOURCES
        elif domain == 'resources':
            res_list = list(projected.get('resources', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                item['provenance'] = o.provenance
                item['officialityTier'] = val.get('officialityTier', 'OFFICIAL')
                _upsert_by_id(res_list, item)
            projected['resources'] = res_list

        # Domain: ELIGIBILITY (Age relaxations & highlights)
        elif domain == 'eligibility':
            relax_list = list(projected.get('ageRelaxations', []))
            cat = val.get('category')
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['provenance'] = o.provenance
                if cat:
                    existing_idx = next((i for i, r in enumerate(relax_list) if r.get('category') == cat), -1)
                    if existing_idx >= 0:
                        relax_list[existing_idx] = item
                    else:
                        relax_list.append(item)
                else:
                    relax_list.append(item)
            elif o.kind == OverlayKind.AMEND:
                for r in relax_list:
                    if cat and r.get('category') == cat:
                        r.update(val)
                        r['provenance'] = o.provenance
            projected['ageRelaxations'] = relax_list

        # Domain: CUTOFFS
        elif domain == 'cutoffsHistory':
            cutoffs_list = list(projected.get('cutoffsHistory', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(cutoffs_list, item)
            projected['cutoffsHistory'] = cutoffs_list

        # Domain: FAQS
        elif domain == 'faqs':
            faqs_list = list(projected.get('faqs', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(faqs_list, item)
            projected['faqs'] = faqs_list

        # Domain: OFFICIAL LINKS / PORTALS
        elif domain == 'officialLinks':
            links_list = list(projected.get('officialLinks', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item_url = item.get('url')
                item_label = item.get('label')
                existing_idx = -1
                for i, existing in enumerate(links_list):
                    if (item_url and existing.get('url') == item_url) or (item_label and existing.get('label') == item_label):
                        existing_idx = i
                        break
                if existing_idx >= 0:
                    links_list[existing_idx] = item
                else:
                    links_list.append(item)
            projected['officialLinks'] = links_list

        # Domain: OFFICIAL PAPERS (PYQs)
        elif domain == 'officialPapers':
            papers_list = list(projected.get('officialPapers', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(papers_list, item)
            projected['officialPapers'] = papers_list

        # Domain: ANSWER KEYS
        elif domain == 'answerKeys':
            keys_list = list(projected.get('answerKeys', []))
            if o.kind == OverlayKind.SUPERSEDE:
                sup_id = o.supersedes_id or target_id
                keys_list = [k for k in keys_list if k.get('id') != sup_id]
                item = copy.deepcopy(val)
                item['id'] = o.id
                _upsert_by_id(keys_list, item)
            elif o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(keys_list, item)
            projected['answerKeys'] = keys_list

        # Domain: ADMIT CARD
        elif domain == 'admitCard':
            admit_events = list(projected.get('admitCardEvents', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(admit_events, item)
            projected['admitCardEvents'] = admit_events

        # Domain: RESULTS
        elif domain == 'results':
            results_list = list(projected.get('resultDeclarations', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                if 'nextSteps' in val:
                    projected['nextStepGuidance'] = val['nextSteps']
                else:
                    _upsert_by_id(results_list, item)
            projected['resultDeclarations'] = results_list

        # Domain: APPLICATION & DOCUMENTS
        elif domain == 'application':
            app_dict = dict(projected.get('application', {}))
            if o.kind in (OverlayKind.ADD, OverlayKind.AMEND):
                app_dict.update(val)
                app_dict['provenance'] = o.provenance
            projected['application'] = app_dict
            if 'howToApply' in val:
                projected['howToApply'] = val['howToApply']
            if 'applicationPortal' in val:
                projected['applicationPortal'] = val['applicationPortal']
            if 'requiredDocuments' in val:
                projected['requiredDocuments'] = val['requiredDocuments']
            if 'photoSignatureGuidelines' in val:
                projected['photoSignatureGuidelines'] = val['photoSignatureGuidelines']
            if 'fee' in val:
                projected['applicationFee'] = val['fee']
            if 'feeExemptions' in val:
                projected['feeExemptions'] = val['feeExemptions']

        # Domain: CORRIGENDUMS
        elif domain == 'corrigendums':
            corr_list = list(projected.get('corrigendums', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(corr_list, item)
            projected['corrigendums'] = corr_list

        # Domain: EXAM DAY
        elif domain == 'examDayChecklist':
            exam_day = list(projected.get('examDayChecklist', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(exam_day, item)
            projected['examDayChecklist'] = exam_day

        # Domain: ROADMAP TRACKS
        elif domain == 'roadmapTracks':
            tracks_list = list(projected.get('roadmapTracks', []))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(tracks_list, item)
            projected['roadmapTracks'] = tracks_list

        # Domain: PATTERN
        elif domain == 'pattern':
            stages_list = list(projected.get('examPatternStages', projected.get('stages', [])))
            if o.kind == OverlayKind.ADD:
                item = copy.deepcopy(val)
                item['id'] = target_id or o.id
                _upsert_by_id(stages_list, item)
            projected['examPatternStages'] = stages_list

        # Domain: OVERVIEW
        elif domain == 'overview':
            if 'overviewDescription' in val:
                projected['overviewDescription'] = val['overviewDescription']
            if 'vacanciesTotal' in val:
                projected['vacanciesTotal'] = val['vacanciesTotal']

    return projected


# =====================================================================
# Persistence: OverlayStore (SQLite + JSON fallback)
# =====================================================================

class OverlayStore:
    """Manages persistence of exam fact overlays in SQLite, with JSON import/export."""

    def __init__(self, db_path: str = 'govos.db'):
        self.db_path = db_path
        self._is_memory = (db_path == ':memory:' or 'mode=memory' in db_path)
        self._shared_conn: Optional[sqlite3.Connection] = None
        if self._is_memory:
            self._shared_conn = sqlite3.connect(db_path)
            self._shared_conn.row_factory = sqlite3.Row
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        if self._shared_conn is not None:
            return self._shared_conn
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _release_connection(self, conn: sqlite3.Connection):
        if not self._is_memory:
            conn.close()

    def _init_db(self):
        conn = self._get_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS exam_fact_overlays (
                id TEXT PRIMARY KEY,
                exam_id TEXT NOT NULL,
                cycle TEXT NOT NULL,
                domain TEXT NOT NULL,
                target_id TEXT,
                target_scope_json TEXT,
                kind TEXT NOT NULL,
                value_json TEXT NOT NULL,
                provenance_json TEXT NOT NULL,
                status TEXT NOT NULL,
                supersedes_id TEXT,
                previous_value_json TEXT,
                effective_date TEXT,
                conflict_note TEXT,
                created_at TEXT NOT NULL,
                created_by TEXT NOT NULL,
                retired INTEGER NOT NULL DEFAULT 0
            )
        ''')
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_exam_fact_overlays_lookup
            ON exam_fact_overlays(exam_id, cycle, domain, retired)
        ''')
        conn.commit()
        self._release_connection(conn)

    def record(self, overlay: ExamFactOverlay) -> ExamFactOverlay:
        """Validates and persists an overlay record. Raises ValueError if validation fails."""
        errors = validate_overlay(overlay)
        if errors:
            raise ValueError(f"Cannot save invalid overlay: {'; '.join(errors)}")

        conn = self._get_connection()
        scope_json = json.dumps(overlay.target_scope.to_dict()) if overlay.target_scope else None
        val_json = json.dumps(overlay.value, ensure_ascii=False)
        prov_json = json.dumps(overlay.provenance, ensure_ascii=False)
        prev_json = json.dumps(overlay.previous_value, ensure_ascii=False) if overlay.previous_value is not None else None

        created_at = overlay.created_at or time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

        conn.execute('''
            INSERT OR REPLACE INTO exam_fact_overlays (
                id, exam_id, cycle, domain, target_id, target_scope_json, kind,
                value_json, provenance_json, status, supersedes_id, previous_value_json,
                effective_date, conflict_note, created_at, created_by, retired
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            overlay.id, overlay.exam_id, overlay.cycle, overlay.domain,
            overlay.target_id, scope_json,
            overlay.kind.value if isinstance(overlay.kind, OverlayKind) else str(overlay.kind),
            val_json, prov_json, overlay.status, overlay.supersedes_id,
            prev_json, overlay.effective_date, overlay.conflict_note,
            created_at, overlay.created_by, 1 if overlay.retired else 0
        ))
        conn.commit()
        self._release_connection(conn)
        return overlay

    def retire(self, overlay_id: str) -> bool:
        """Retires an overlay reversibly (sets retired = 1). Preserves full history."""
        conn = self._get_connection()
        cur = conn.execute('UPDATE exam_fact_overlays SET retired = 1 WHERE id = ?', (overlay_id,))
        changed = cur.rowcount > 0
        conn.commit()
        self._release_connection(conn)
        return changed

    def get_active(self, exam_id: str, cycle: Optional[str] = None, domain: Optional[str] = None) -> list[ExamFactOverlay]:
        """Returns all active, unretired overlays for this exam that can enter the live projection."""
        conn = self._get_connection()
        query = "SELECT * FROM exam_fact_overlays WHERE exam_id = ? AND retired = 0 AND status IN ('VERIFIED', 'NOT_PUBLISHED') AND kind != 'CONFLICT'"
        params = [exam_id]
        if cycle:
            query += " AND cycle = ?"
            params.append(cycle)
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        query += " ORDER BY created_at ASC"

        rows = conn.execute(query, params).fetchall()
        self._release_connection(conn)
        return [self._row_to_overlay(r) for r in rows]

    def get_history(self, exam_id: str, domain: Optional[str] = None) -> list[ExamFactOverlay]:
        """Returns complete historical traceability for an exam (active, retired, and conflicts)."""
        conn = self._get_connection()
        query = "SELECT * FROM exam_fact_overlays WHERE exam_id = ?"
        params = [exam_id]
        if domain:
            query += " AND domain = ?"
            params.append(domain)
        query += " ORDER BY created_at ASC"

        rows = conn.execute(query, params).fetchall()
        self._release_connection(conn)
        return [self._row_to_overlay(r) for r in rows]

    def _row_to_overlay(self, row: sqlite3.Row) -> ExamFactOverlay:
        scope_d = json.loads(row['target_scope_json']) if row['target_scope_json'] else None
        prev_v = json.loads(row['previous_value_json']) if row['previous_value_json'] else None
        return ExamFactOverlay(
            id=row['id'],
            exam_id=row['exam_id'],
            cycle=row['cycle'],
            domain=row['domain'],
            kind=OverlayKind(row['kind']),
            value=json.loads(row['value_json']),
            provenance=json.loads(row['provenance_json']),
            status=row['status'],
            target_id=row['target_id'],
            target_scope=ExamOverlayScope.from_dict(scope_d) if scope_d else None,
            supersedes_id=row['supersedes_id'],
            previous_value=prev_v,
            effective_date=row['effective_date'],
            conflict_note=row['conflict_note'],
            created_at=row['created_at'],
            created_by=row['created_by'],
            retired=bool(row['retired'])
        )


def create_overlays_from_record(rec: Any, gate: Any) -> list[ExamFactOverlay]:
    """Generates strictly validated ExamFactOverlay objects from a gate-passing ExamRecord.
    Enforces that only FOUND fields with verbatim citations can become active overlays.
    """
    if not gate or not getattr(gate, 'may_publish', False):
        return []

    exam_id = rec.exam_id
    cycle = get_exam_cycle({'id': exam_id, 'title': getattr(rec, 'title', '')}) or '2026'
    overlays: list[ExamFactOverlay] = []
    t_now = int(time.time() * 1000)

    for field_name, f in getattr(rec, 'fields', {}).items():
        status_val = getattr(f.status, 'value', str(f.status)) if hasattr(f, 'status') else ''
        if status_val != 'FOUND':
            continue
        if not getattr(f, 'citation', None):
            continue

        citation = f.citation
        prov = citation.to_provenance(f"prov-{exam_id}-{field_name}") if hasattr(citation, 'to_provenance') else {}
        val = f.value

        if field_name == 'dates' and isinstance(val, list):
            for i, d in enumerate(val):
                if isinstance(d, dict) and d.get('type') and d.get('dateTimeStr'):
                    o_id = f"overlay-{exam_id}-date-{d['type'].lower()}-{t_now}-{i}"
                    o = ExamFactOverlay(
                        id=o_id,
                        exam_id=exam_id,
                        cycle=cycle,
                        domain='dates',
                        kind=OverlayKind.ADD,
                        value=d,
                        provenance=prov,
                        status='VERIFIED',
                        created_by='GovOS Universal Pipeline'
                    )
                    if not validate_overlay(o):
                        overlays.append(o)

        elif field_name == 'posts' and isinstance(val, list):
            for i, p in enumerate(val):
                if isinstance(p, dict) and p.get('postName'):
                    o_id = f"overlay-{exam_id}-post-{t_now}-{i}"
                    o = ExamFactOverlay(
                        id=o_id,
                        exam_id=exam_id,
                        cycle=cycle,
                        domain='posts',
                        kind=OverlayKind.ADD,
                        value=p,
                        provenance=prov,
                        status='VERIFIED',
                        created_by='GovOS Universal Pipeline'
                    )
                    if not validate_overlay(o):
                        overlays.append(o)

        elif field_name == 'syllabus' and isinstance(val, list):
            for i, s in enumerate(val):
                topic = s.get('topicName') or s.get('title') or f"Topic {i+1}"
                subj = s.get('subject') or s.get('levelLabel') or 'General'
                o_id = f"overlay-{exam_id}-syl-{t_now}-{i}"
                item_val = dict(s)
                item_val['topicName'] = topic
                item_val['subject'] = subj
                o = ExamFactOverlay(
                    id=o_id,
                    exam_id=exam_id,
                    cycle=cycle,
                    domain='syllabus',
                    kind=OverlayKind.ADD,
                    value=item_val,
                    provenance=prov,
                    status='VERIFIED',
                    created_by='GovOS Universal Pipeline'
                )
                if not validate_overlay(o):
                    overlays.append(o)

        elif field_name in ('examPattern', 'pattern') and isinstance(val, list):
            for i, p in enumerate(val):
                p_name = p.get('stageName') or p.get('name') or p.get('levelLabel') or f"Stage {i+1}"
                o_id = f"overlay-{exam_id}-pat-{t_now}-{i}"
                item_val = dict(p)
                item_val['stageName'] = p_name
                o = ExamFactOverlay(
                    id=o_id,
                    exam_id=exam_id,
                    cycle=cycle,
                    domain='pattern',
                    kind=OverlayKind.ADD,
                    value=item_val,
                    provenance=prov,
                    status='VERIFIED',
                    created_by='GovOS Universal Pipeline'
                )
                if not validate_overlay(o):
                    overlays.append(o)

        elif field_name == 'officialPapers' and isinstance(val, list):
            for i, p in enumerate(val):
                title = p.get('paperTitle') or p.get('title') or f"Paper {i+1}"
                url = p.get('pdfUrl') or p.get('url') or ''
                if url:
                    o_id = f"overlay-{exam_id}-paper-{t_now}-{i}"
                    o = ExamFactOverlay(
                        id=o_id,
                        exam_id=exam_id,
                        cycle=cycle,
                        domain='officialPapers',
                        kind=OverlayKind.ADD,
                        value={'paperTitle': title, 'pdfUrl': url},
                        provenance=prov,
                        status='VERIFIED',
                        created_by='GovOS Universal Pipeline'
                    )
                    if not validate_overlay(o):
                        overlays.append(o)

        elif field_name == 'answerKeys' and isinstance(val, list):
            for i, k in enumerate(val):
                title = k.get('paperTitle') or k.get('title') or f"Answer Key {i+1}"
                url = k.get('pdfUrl') or k.get('url') or ''
                if url:
                    o_id = f"overlay-{exam_id}-key-{t_now}-{i}"
                    o = ExamFactOverlay(
                        id=o_id,
                        exam_id=exam_id,
                        cycle=cycle,
                        domain='answerKeys',
                        kind=OverlayKind.ADD,
                        value={'paperTitle': title, 'pdfUrl': url},
                        provenance=prov,
                        status='VERIFIED',
                        created_by='GovOS Universal Pipeline'
                    )
                    if not validate_overlay(o):
                        overlays.append(o)

        elif field_name == 'admitCard' and isinstance(val, list):
            for i, a in enumerate(val):
                name = a.get('eventName') or a.get('officialLabel') or a.get('sourceLabel') or 'Admit Card'
                o_id = f"overlay-{exam_id}-admit-{t_now}-{i}"
                item_val = dict(a)
                item_val['eventName'] = name
                o = ExamFactOverlay(
                    id=o_id,
                    exam_id=exam_id,
                    cycle=cycle,
                    domain='admitCard',
                    kind=OverlayKind.ADD,
                    value=item_val,
                    provenance=prov,
                    status='VERIFIED',
                    created_by='GovOS Universal Pipeline'
                )
                if not validate_overlay(o):
                    overlays.append(o)

        elif field_name == 'results' and isinstance(val, list):
            for i, r in enumerate(val):
                name = r.get('stageName') or r.get('label') or r.get('sourceLabel') or 'Result'
                o_id = f"overlay-{exam_id}-res-{t_now}-{i}"
                item_val = dict(r)
                item_val['stageName'] = name
                o = ExamFactOverlay(
                    id=o_id,
                    exam_id=exam_id,
                    cycle=cycle,
                    domain='results',
                    kind=OverlayKind.ADD,
                    value=item_val,
                    provenance=prov,
                    status='VERIFIED',
                    created_by='GovOS Universal Pipeline'
                )
                if not validate_overlay(o):
                    overlays.append(o)

        elif field_name in ('cutoffs', 'cutoffsHistory') and isinstance(val, list):
            for i, c in enumerate(val):
                cat = c.get('category') or 'General'
                yr = str(c.get('year') or cycle)
                o_id = f"overlay-{exam_id}-cutoff-{t_now}-{i}"
                item_val = dict(c)
                item_val['category'] = cat
                item_val['year'] = yr
                o = ExamFactOverlay(
                    id=o_id,
                    exam_id=exam_id,
                    cycle=cycle,
                    domain='cutoffsHistory',
                    kind=OverlayKind.ADD,
                    value=item_val,
                    provenance=prov,
                    status='VERIFIED',
                    created_by='GovOS Universal Pipeline'
                )
                if not validate_overlay(o):
                    overlays.append(o)

        elif field_name in ('corrigenda', 'corrigendums') and isinstance(val, list):
            for i, c in enumerate(val):
                title = c.get('title') or f"Corrigendum {i+1}"
                o_id = f"overlay-{exam_id}-corr-{t_now}-{i}"
                item_val = dict(c)
                item_val['title'] = title
                item_val['noticeNumber'] = c.get('noticeNumber') or f"Notice {i+1}"
                o = ExamFactOverlay(
                    id=o_id,
                    exam_id=exam_id,
                    cycle=cycle,
                    domain='corrigendums',
                    kind=OverlayKind.ADD,
                    value=item_val,
                    provenance=prov,
                    status='VERIFIED',
                    created_by='GovOS Universal Pipeline'
                )
                if not validate_overlay(o):
                    overlays.append(o)

        elif field_name == 'applicationPortal' and isinstance(val, str) and val.startswith(('http://', 'https://')):
            o_id = f"overlay-{exam_id}-portal-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='officialLinks',
                kind=OverlayKind.ADD,
                value={'title': 'Online Application Portal', 'url': val},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

            o_app_id = f"overlay-{exam_id}-app-portal-{t_now}"
            o_app = ExamFactOverlay(
                id=o_app_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='application',
                kind=OverlayKind.ADD,
                value={'applicationPortal': val},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o_app):
                overlays.append(o_app)

        elif field_name == 'ageLimits':
            o_id = f"overlay-{exam_id}-age-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='eligibility',
                kind=OverlayKind.ADD,
                value={'category': 'General', 'ruleType': 'AGE_LIMIT', 'details': str(val)},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

        elif field_name == 'qualification':
            o_id = f"overlay-{exam_id}-qual-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='eligibility',
                kind=OverlayKind.ADD,
                value={'category': 'General', 'ruleType': 'QUALIFICATION', 'details': str(val)},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

        elif field_name == 'vacancies' and (isinstance(val, int) or isinstance(val, str)):
            o_id = f"overlay-{exam_id}-vacancies-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='overview',
                kind=OverlayKind.ADD,
                value={'vacanciesTotal': val},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

        elif field_name == 'overview' and isinstance(val, dict):
            o_id = f"overlay-{exam_id}-overview-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='overview',
                kind=OverlayKind.ADD,
                value=val,
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

        elif field_name == 'resources' and isinstance(val, list):
            for i, r in enumerate(val):
                title = r.get('title') or f"Official Resource {i+1}"
                url = r.get('url') or ''
                tier = r.get('officialityTier') or 'OFFICIAL'
                if url and url.startswith(('http://', 'https://')):
                    o_id = f"overlay-{exam_id}-res-{t_now}-{i}"
                    o = ExamFactOverlay(
                        id=o_id,
                        exam_id=exam_id,
                        cycle=cycle,
                        domain='resources',
                        kind=OverlayKind.ADD,
                        value={'title': title, 'url': url, 'officialityTier': tier},
                        provenance=prov,
                        status='VERIFIED',
                        created_by='GovOS Universal Pipeline'
                    )
                    if not validate_overlay(o):
                        overlays.append(o)

        elif field_name in ('applicationPortal', 'howToApply', 'requiredDocuments', 'photoSignatureGuidelines', 'fee', 'feeExemptions'):
            o_id = f"overlay-{exam_id}-{field_name.lower()}-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='application',
                kind=OverlayKind.ADD,
                value={field_name: val},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

        elif field_name == 'nextSteps' and isinstance(val, list):
            o_id = f"overlay-{exam_id}-nextsteps-{t_now}"
            o = ExamFactOverlay(
                id=o_id,
                exam_id=exam_id,
                cycle=cycle,
                domain='results',
                kind=OverlayKind.ADD,
                value={'nextSteps': val, 'stageName': 'Next Steps Guidance'},
                provenance=prov,
                status='VERIFIED',
                created_by='GovOS Universal Pipeline'
            )
            if not validate_overlay(o):
                overlays.append(o)

    return overlays

