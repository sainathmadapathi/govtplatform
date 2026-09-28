"""Universal Exam Materialization Engine — Phase 3.

Governed by GOVOS_MASTER_SPEC.md. Closes the gap that Phase 1 (overlays) and Phase 2
(acquisition + completeness) left open: an acquired exam could be built, verified and gated,
but could not become a first-class *runtime* Exam, because the only full-Exam producer was the
compile-time TypeScript emitter and the frontend's universe was frozen to `src/data.ts`.

This module adds exactly three things, all universal and all built on the accepted engine:

    materialize_exam(record)   ExamRecord -> runtime Exam dict   (a JSON twin of emit.render_exam:
                               only sourced values, NEEDS_REVIEW -> UNDER_VERIFICATION, honest
                               empties, a DataProvenance on every value, completeness states kept)
    ExamRegistry               the persistent runtime home for machine-acquired exams (SQLite),
                               identity-scoped by (exam_id, cycle), gate-mandatory, contract-
                               validated, versioned, retirable. Never a JSON bucket.
    build_exam(query, year)    the single generic entry point: the existing orchestrator
                               (resolve -> discover -> identity -> extract -> verify -> gate),
                               then materialize -> validate -> register. Fails safely with a
                               distinct state and a reason; never fabricates, never writes data.ts.

Rules that are structural here, not habits:
- Only a record whose existing publication gate returned PASS may be registered as published.
- A registry record can never carry an id that lives in the authored register (data.ts):
  authored exams stay authored, and the registry never overwrites or duplicates them.
- A missing / unpublished / not-found section stays an honest empty with its completeness state
  attached; it is never filled from another exam, another year, or a guess.
- No branch names an exam or an authority.
"""
from __future__ import annotations

import io
import json
import re
import sqlite3
import time
from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Any, Callable, Optional

from ..exam_authoring.emit import _GROUP_TAIL_RX, classification_of
from ..exam_authoring.record import ExamRecord, Field, Status
from . import publish as P
from .completeness import ExamCompletenessReport
from .gate import GateReport
from .orchestrate import OrchestrationResult, OrchestrationState, orchestrate
from .overlay import get_exam_cycle
from .render import target_in_register

MATERIALIZER_VERSION = 'materialize-1'

# ------------------------------------------------------------------ the runtime Exam contract
#: The frontend `Exam` interface's 21 required fields and the JSON type each must carry. A
#: materialized exam is validated against this before it may enter the registry, so the
#: registry can never hold an untyped payload the UI cannot consume.
RUNTIME_EXAM_REQUIRED: dict[str, type] = {
    'id': str, 'code': str, 'title': str, 'authorityName': str, 'officialDomain': str,
    'crucialEligibilityDate': str, 'isGoldenJourney': bool, 'isDemoData': bool,
    'overviewDescription': str,
    'posts': list, 'dates': list, 'globalRuleGroup': dict, 'stages': list, 'syllabus': list,
    'practiceQuestions': list, 'corrigendums': list, 'cutoffsHistory': list, 'resources': list,
    'faqs': list, 'applicationGuide': dict, 'roadmapTracks': list,
}

_DATE_TYPES = {'NOTIFICATION', 'APPLICATION_OPEN', 'APPLICATION_CLOSE', 'CORRECTION_WINDOW',
               'ADMIT_CARD', 'EXAM_TIER1', 'EXAM_TIER2', 'ANSWER_KEY', 'RESULT', 'INTERVIEW'}


def validate_runtime_exam(exam: Any) -> list[str]:
    """Every way a materialized exam can fail the frontend contract, as a list of reasons.

    An empty list means the payload is a valid runtime Exam. Structural only: it checks shape and
    identity convention, never a fact's truth (that is the gate's job, already done).
    """
    errors: list[str] = []
    if not isinstance(exam, dict):
        return ['runtime exam must be an object']
    for key, typ in RUNTIME_EXAM_REQUIRED.items():
        if key not in exam:
            errors.append(f'missing required field {key!r}')
        elif not isinstance(exam[key], typ) or (typ is not bool and isinstance(exam[key], bool)):
            errors.append(f'field {key!r} must be {typ.__name__}, got {type(exam[key]).__name__}')
    exam_id = exam.get('id')
    if isinstance(exam_id, str) and not exam_id.startswith('exam-'):
        errors.append(f"id {exam_id!r} must follow the canonical 'exam-' convention")
    for d in (exam.get('dates') or []):
        if not isinstance(d, dict):
            errors.append('every date must be an object')
            continue
        for k in ('id', 'type', 'label', 'dateTimeStr', 'status', 'provenance'):
            if k not in d:
                errors.append(f'date {d.get("id", "?")!r} is missing {k!r}')
        if d.get('type') not in _DATE_TYPES:
            errors.append(f'date {d.get("id", "?")!r} has a type outside the frontend union: {d.get("type")!r}')
    for p in (exam.get('posts') or []):
        if not isinstance(p, dict) or not p.get('postName') or not p.get('classification'):
            errors.append('every post must carry postName and a printed classification')
    rg = exam.get('globalRuleGroup')
    if isinstance(rg, dict):
        if rg.get('operator') not in ('AND', 'OR') or not isinstance(rg.get('rules'), list) or not rg.get('id'):
            errors.append('globalRuleGroup must carry id, operator AND|OR, and rules[]')
    ag = exam.get('applicationGuide')
    if isinstance(ag, dict):
        for k in ('officialPortal', 'otrSteps', 'photoRules', 'signatureRules', 'certificateRules', 'rejectionPitfalls'):
            if k not in ag:
                errors.append(f'applicationGuide is missing {k!r}')
    return errors


# ------------------------------------------------------------------ ExamRecord -> runtime Exam
def _prov(rec: ExamRecord, f: Field, suffix: str) -> Optional[dict]:
    if not f.citation:
        return None
    return f.citation.to_provenance(prov_id=f'prov-{rec.exam_id}-{suffix}', level=f.verification_level)


def _dates(rec: ExamRecord) -> list[dict]:
    f = rec.get('dates')
    out: list[dict] = []
    if f and f.usable and isinstance(f.value, list):
        prov = _prov(rec, f, 'date')
        # A row whose label matched no known milestone is not emitted: the union has no OTHER,
        # and forcing it into the nearest member would invent a milestone (same rule as emit).
        for i, d in enumerate(x for x in f.value if isinstance(x, dict) and x.get('type') in _DATE_TYPES):
            out.append({
                'id': str(d.get('id') or f'date-{rec.exam_id}-{i}'), 'type': d['type'],
                'label': d.get('label', d['type']),
                'dateTimeStr': d.get('dateTimeStr', ''), 'timezone': d.get('timezone') or 'Asia/Kolkata (IST)',
                'isTentative': bool(d.get('isTentative', False)),
                'status': d.get('status') if d.get('status') in ('AVAILABLE', 'SUPERSEDED') else 'AVAILABLE',
                # A reconciled date carries the provenance of the document it was read from;
                # keep it, and fall back to the field's citation only where a row has none.
                'provenance': (d.get('provenance') if isinstance(d.get('provenance'), dict) and d['provenance']
                               else (prov or {})),
            })
    sup = rec.get('lastDateSuperseded')
    if sup and sup.usable and isinstance(sup.value, dict):
        out.append({
            'id': f'date-{rec.exam_id}-close-superseded', 'type': 'APPLICATION_CLOSE',
            'label': 'Last date printed in the notice (superseded)',
            'dateTimeStr': sup.value.get('noticeDate', ''), 'timezone': 'Asia/Kolkata (IST)',
            'isTentative': False, 'status': 'SUPERSEDED',
            'provenance': _prov(rec, sup, 'lastdate-superseded') or {},
        })
    return out


def _corrigendums(rec: ExamRecord) -> list[dict]:
    out: list[dict] = []
    # Corrigenda read by the corrigenda reader: one CorrigendumNotice per official revision,
    # each carrying the authority's own words and the old/new values it stated.
    corr = rec.get('corrigenda')
    if corr and corr.usable and isinstance(corr.value, list):
        for i, c in enumerate(corr.value):
            if not isinstance(c, dict):
                continue
            old, new = c.get('oldValue', ''), c.get('newValue', '')
            out.append({
                'id': str(c.get('id') or f'corr-{rec.exam_id}-{i}'),
                'title': str(c.get('title') or f"Corrigendum: {c.get('affectedField', 'revision')}"),
                'noticeNumber': str(c.get('sourceTitle') or c.get('noticeNumber') or ''),
                'publishedDate': str(c.get('publishedDate') or c.get('effectiveDate') or '')[:10],
                'effectiveDate': str(c.get('effectiveDate') or '')[:10],
                'summary': str(c.get('evidenceSpan') or c.get('note') or ''),
                'pdfUrl': str(c.get('sourceUrl') or ''),
                'status': 'SUPERSEDED' if str(c.get('status', '')).upper() == 'SUPERSEDED' else 'ACTIVE',
                'diffSummary': (f"{c.get('affectedField', 'value')}: {old} → {new}" if (old or new)
                                else str(c.get('note') or '')),
            })
    sup = rec.get('lastDateSuperseded')
    if not (sup and sup.usable and isinstance(sup.value, dict)):
        return out
    v = sup.value
    return out + [{
        'id': f'corr-{rec.exam_id}-lastdate',
        'title': f"Last date changed from {str(v.get('noticeDate', ''))[:10]} to {str(v.get('pageDate', ''))[:10]}",
        'noticeNumber': f'{rec.authority_name} — examination page for this exam',
        'publishedDate': str(v.get('pageDate', ''))[:10], 'effectiveDate': str(v.get('noticeDate', ''))[:10],
        'summary': (f"The notice prints \"{v.get('noticeExcerpt', '')}\" The authority's own examination page "
                    f"records {str(v.get('pageDate', ''))[:10]} as the last date; the page is the later "
                    f"statement, so it is operative and the notice's date is kept struck through."),
        'pdfUrl': sup.citation.url if sup.citation else '', 'status': 'ACTIVE',
        'diffSummary': f"Last date: {str(v.get('noticeDate', ''))[:10]} (notice) → {str(v.get('pageDate', ''))[:10]} (examination page).",
    }]


def _posts(rec: ExamRecord) -> tuple[list[dict], list[str]]:
    """Posts whose Group the authority printed; the rest are returned by name, never faked."""
    f = rec.get('posts')
    if not (f and f.usable and isinstance(f.value, list)):
        return [], []
    age = rec.value('ageLimits') or {}
    rows, skipped = [], []
    prov = _prov(rec, f, 'posts')
    for i, item in enumerate(f.value[:60]):
        if isinstance(item, dict):
            name = str(item.get('postName') or item.get('name') or '').strip()
            cls = str(item.get('classification') or '') or classification_of(name)
            department = str(item.get('department') or rec.authority_name)
            pay_level = str(item.get('payLevel') or '')
        else:
            name = str(item).strip()
            cls, department, pay_level = classification_of(name), rec.authority_name, ''
        if not name:
            continue
        if not cls:
            skipped.append(name)
            continue
        rows.append({
            'id': f'post-{rec.exam_id}-{i}', 'postName': re.sub(_GROUP_TAIL_RX, '', name).strip(),
            'department': department,
            'payLevel': pay_level, 'payScale': '', 'classification': cls,
            'minAge': age.get('minAge', 0) if isinstance(age, dict) else 0,
            'maxAge': age.get('maxAge', 0) if isinstance(age, dict) else 0,
            'provenance': prov or {},
        })
    return rows, skipped


def _eligibility_highlights(rec: ExamRecord) -> list[dict]:
    cards = []
    for name, title in (('ageLimits', 'Age limits'), ('qualification', 'Educational qualification'),
                        ('attempts', 'Number of attempts'), ('fee', 'Fee')):
        f = rec.get(name)
        if not (f and f.usable and f.citation):
            continue
        v = f.value
        if name == 'ageLimits' and isinstance(v, dict):
            body = (f"{v.get('minAge')} to {v.get('maxAge')} years"
                    + (f" as on {v['asOn']}" if v.get('asOn') else '')
                    + (f"; born on or after {v['bornNotEarlierThan']} and on or before {v['bornNotLaterThan']}."
                       if v.get('bornNotEarlierThan') else '.'))
        elif isinstance(v, dict) and v.get('text'):
            body = str(v['text'])[:400]
        elif name == 'fee' and isinstance(v, dict) and (v.get('amounts') or v.get('amount')):
            # The fee as the notice printed it; the reader's structure is not a sentence.
            amounts = [str(a) for a in (v.get('amounts') or [v.get('amount')]) if a not in (None, '')]
            body = 'Rs. ' + ' / Rs. '.join(dict.fromkeys(amounts)) + ' as printed in the notice; the evidence span carries the wording.'
        elif isinstance(v, dict):
            body = str(f.citation.excerpt or '')[:400] if f.citation and getattr(f.citation, 'excerpt', '') else str(v)[:400]
        else:
            body = str(v)[:400]
        cards.append({'title': title, 'body': body, 'provenance': _prov(rec, f, name.lower()) or {}})
    return cards


def _resources(rec: ExamRecord) -> list[dict]:
    """Links only — the content policy forbids storing anything."""
    items = []
    notice = rec.get('notice')
    if notice and notice.usable and notice.citation:
        url = notice.value['url'] if isinstance(notice.value, dict) else notice.value
        items.append({
            'id': f'res-{rec.exam_id}-notice', 'title': f'{rec.title} — Examination Notice (official PDF)',
            'subject': 'Official Gazette', 'author': rec.authority_name, 'type': 'OFFICIAL_PDF',
            'resourceFormat': 'DIRECT_PDF', 'url': url, 'directPdfUrl': url,
            'officialTag': f'{rec.code} — OFFICIAL NOTICE',
            'recommendedFor': 'The rules themselves, from the authority that wrote them.',
            'description': 'The examination notice this record was read from.',
            'linkVerifiedDate': notice.citation.verified_date, 'provenance': _prov(rec, notice, 'notice') or {},
        })
    papers = rec.get('officialPapers')
    if papers and papers.usable and isinstance(papers.value, dict):
        for i, (label, url) in enumerate(sorted(papers.value.items())[:12]):
            items.append({
                'id': f'res-{rec.exam_id}-paper-{i}', 'title': str(label).split('::', 1)[-1],
                'subject': 'Previous Year Papers', 'author': rec.authority_name, 'type': 'OFFICIAL_PDF',
                'resourceFormat': 'DIRECT_PDF', 'url': url, 'directPdfUrl': url,
                'officialTag': f'{rec.code} — OFFICIAL QUESTION PAPER',
                'recommendedFor': 'The real paper, as the authority published it.',
                'description': 'Published by the authority on this exam’s own page.',
                'linkVerifiedDate': papers.citation.verified_date if papers.citation else '',
                'provenance': _prov(rec, papers, f'paper-{i}') or {},
            })
    return items


def _application_guide(rec: ExamRecord) -> dict:
    portal = rec.value('applicationPortal') or rec.official_domain
    how = rec.get('howToApply')
    steps: list[dict] = []
    if how and how.usable:
        # Kept whole, as one cited step: splitting an authority's prose into invented sub-steps
        # would be GovOS writing the process rather than quoting it (same rule as emit).
        steps.append({'stepNumber': 1, 'title': 'How to Apply — as the notice states it',
                      'portalUrl': portal, 'instructions': [str(how.value)[:1200]],
                      'mandatoryFields': [], 'commonMistakesToAvoid': []})
    spec = {'documentType': 'As stated on the portal’s upload screen', 'dimensions': '',
            'fileFormat': '', 'fileSize': '', 'rules': [], 'sampleDescription': ''}
    return {'officialPortal': portal, 'otrSteps': steps, 'photoRules': dict(spec),
            'signatureRules': dict(spec), 'certificateRules': [], 'rejectionPitfalls': []}


def _overview(rec: ExamRecord) -> str:
    bits = [f'{rec.title}, conducted by {rec.authority_name}.']
    if rec.value('vacancies'):
        bits.append(f"The notice states approximately {rec.value('vacancies')} vacancies.")
    close = next((d for d in (rec.value('dates') or []) if isinstance(d, dict) and d.get('type') == 'APPLICATION_CLOSE'), None)
    if close:
        bits.append(f"Applications close {close.get('dateTimeStr', '')}.")
    bits.append('Read from the authority’s own documents by the GovOS universal engine; sections with '
                'no sourced data are shown as unauthored rather than filled in.')
    return ' '.join(bits)


def _faqs(rec: ExamRecord) -> list[dict]:
    f = rec.get('faqs')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    prov = _prov(rec, f, 'faqs') or {}
    out = []
    for i, q in enumerate(f.value):
        if not isinstance(q, dict) or not q.get('question') or not q.get('answer'):
            continue
        item_prov = dict(prov)
        item_prov['id'] = f'{prov.get("id", "prov")}-{i}'
        if q.get('excerpt'):
            item_prov['excerptText'] = str(q['excerpt'])[:600]
        out.append({'id': f'faq-{rec.exam_id}-{i}', 'question': str(q['question']),
                    'answer': str(q['answer']), 'officialClause': str(q.get('officialClause') or 'Official clause'),
                    'provenance': item_prov})
    return out


_EXAM_DAY_CATEGORIES = {'DOCUMENTS', 'TIMING', 'ITEMS_ALLOWED', 'ITEMS_PROHIBITED', 'CENTRE_INSTRUCTIONS'}


def _exam_day(rec: ExamRecord) -> list[dict]:
    f = rec.get('examDayChecklist')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    prov = _prov(rec, f, 'examday') or {}
    out = []
    for i, it in enumerate(f.value):
        if not isinstance(it, dict) or not it.get('description'):
            continue
        item_prov = dict(prov)
        item_prov['id'] = f'{prov.get("id", "prov")}-{i}'
        if it.get('excerpt'):
            item_prov['excerptText'] = str(it['excerpt'])[:600]
        cat = str(it.get('category') or 'CENTRE_INSTRUCTIONS')
        out.append({'id': f'examday-{rec.exam_id}-{i}',
                    'category': cat if cat in _EXAM_DAY_CATEGORIES else 'CENTRE_INSTRUCTIONS',
                    'title': str(it.get('title') or it['description'])[:120],
                    'description': str(it['description']), 'isMandatory': bool(it.get('isMandatory', False)),
                    'provenance': item_prov})
    return out


_PATTERN_LEVELS = {'STAGE', 'PAPER', 'SUBJECT', 'SECTION', 'PART'}
_MINUTES_RX = re.compile(r'(\d+)\s*(?:min|minute)', re.I)
_HOURS_RX = re.compile(r'(\d+(?:\.\d+)?)\s*(?:hr|hour)', re.I)


def _minutes(text) -> Optional[int]:
    s = str(text or '')
    m = _MINUTES_RX.search(s)
    if m:
        return int(m.group(1))
    h = _HOURS_RX.search(s)
    if h:
        return int(round(float(h.group(1)) * 60))
    return None


def _pattern_node(n: dict, prov: dict) -> dict:
    """One extracted pattern node -> ExamPatternNode. Only what the reader printed is carried;
    a value it did not read is omitted, not guessed."""
    label = str(n.get('levelLabel') or n.get('level') or '')
    level = label.upper() if label.upper() in _PATTERN_LEVELS else 'OTHER'
    node: dict = {'id': str(n.get('id') or ''), 'level': level, 'levelLabel': label or None,
                  'name': str(n.get('name') or n.get('title') or ''), 'status': str(n.get('status') or 'VERIFIED'),
                  'provenance': n.get('provenance') or prov}
    if n.get('code'):
        node['code'] = str(n['code'])
    if n.get('order') is not None:
        node['order'] = n['order']
    marks = n.get('marks', n.get('totalMarks'))
    if isinstance(marks, (int, float)):
        node['marks'] = marks
    qs = n.get('questions', n.get('totalQuestions'))
    if isinstance(qs, (int, float)):
        node['questions'] = qs
    dur = n.get('durationMinutes')
    if not isinstance(dur, (int, float)):
        dur = _minutes(n.get('duration'))
    if isinstance(dur, (int, float)):
        node['durationMinutes'] = int(dur)
    if n.get('negativeMarking'):
        node['negativeMarking'] = str(n['negativeMarking'])
    if n.get('mode'):
        node['mode'] = str(n['mode'])
    if n.get('note'):
        node['note'] = str(n['note'])
    children = n.get('children')
    if isinstance(children, list) and children:
        node['children'] = [_pattern_node(c, prov) for c in children if isinstance(c, dict)]
    return {k: v for k, v in node.items() if v is not None}


def _pattern_tree(rec: ExamRecord) -> list[dict]:
    f = rec.get('examPattern')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    prov = _prov(rec, f, 'pattern') or {}
    return [_pattern_node(n, prov) for n in f.value if isinstance(n, dict)]


def _syllabus_tree(rec: ExamRecord) -> list[dict]:
    """The syllabus reader already emits ExamSyllabusNode-shaped nodes (id, title, levelLabel,
    order, status, provenance, children); they are carried through as read."""
    f = rec.get('syllabus')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    return json.loads(json.dumps([n for n in f.value if isinstance(n, dict) and n.get('title')], default=str))


def _section_states(report: Optional[ExamCompletenessReport]) -> dict:
    """The 17 completeness states, carried as metadata so the UI can tell an honest absence from
    an unpublished one — never rendered as raw enum text (that translation is a UI boundary)."""
    if report is None:
        return {}
    return {s.section_id: {'state': s.state.value, 'nature': s.nature.value,
                           'studentStatusSummary': s.student_status_summary,
                           'sectionNum': s.section_num, 'isApplicable': s.is_applicable}
            for s in report.sections}


def materialize_exam(rec: ExamRecord, *, cycle: str = '',
                     completeness: Optional[ExamCompletenessReport] = None,
                     gate: Optional[GateReport] = None) -> dict:
    """ExamRecord -> runtime Exam dict, the JSON twin of `emit.render_exam`.

    Only sourced values are written; a field the run could not source is an honest empty array
    or absent, exactly as the emitter does, so an absent field shows as absent rather than as a
    plausible invention. Every value carries a DataProvenance; NEEDS_REVIEW is badged
    UNDER_VERIFICATION. The completeness states ride along as metadata.
    """
    cycle = cycle or get_exam_cycle({'id': rec.exam_id, 'title': rec.title}) or ''
    admit = rec.get('admitCard')
    admit_details = None
    if admit and admit.usable and isinstance(admit.value, dict):
        admit_details = {'status': 'NOT_YET_ANNOUNCED', 'releaseDateStr': '',
                         'officialPortalUrl': admit.value.get('portalUrl') or rec.value('applicationPortal') or rec.official_domain,
                         'loginCredentialsRequired': [], 'instructions': [str(admit.value.get('text', ''))[:500]],
                         'cityIntimationAvailable': False}
    posts, skipped_posts = _posts(rec)
    age = rec.value('ageLimits') or {}
    exam: dict = {
        'id': rec.exam_id, 'code': rec.code, 'title': rec.title,
        'authorityName': rec.authority_name, 'officialDomain': rec.official_domain,
        'crucialEligibilityDate': str((age.get('asOn') if isinstance(age, dict) else '') or ''),
        'isGoldenJourney': False, 'isDemoData': False,
        'overviewDescription': _overview(rec),
        'vacanciesTotal': str(rec.value('vacancies') or ''),
        'posts': posts, 'dates': _dates(rec),
        'globalRuleGroup': {'id': f'rules-{rec.exam_id}', 'operator': 'AND', 'rules': []},
        # The flat, closed-union forms (stages, syllabus topics) need figures and vocabulary the
        # readers did not print, so they stay honest empties; the typed trees the UI renders
        # (patternTree, syllabusTree) carry exactly what was read, node by node, with provenance.
        'stages': [], 'syllabus': [], 'practiceQuestions': [],
        'corrigendums': _corrigendums(rec), 'cutoffsHistory': [],
        'resources': _resources(rec), 'faqs': _faqs(rec),
        'applicationGuide': _application_guide(rec), 'roadmapTracks': [],
        'eligibilityHighlights': _eligibility_highlights(rec),
        'officialLinks': [{'title': f'{rec.authority_name} — official website', 'url': rec.official_domain,
                           'note': 'The authority’s own site.'}],
        'origin': 'MACHINE_ACQUIRED',
        'cycle': cycle,
        'sectionStates': _section_states(completeness),
        'materialization': {'version': MATERIALIZER_VERSION,
                            'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                            'gateDecision': gate.decision.value if gate else None,
                            'postsWithoutPrintedGroup': skipped_posts},
    }
    if admit_details is not None:
        exam['admitCardDetails'] = admit_details
    pattern_tree = _pattern_tree(rec)
    if pattern_tree:
        exam['patternTree'] = pattern_tree
    syllabus_tree = _syllabus_tree(rec)
    if syllabus_tree:
        exam['syllabusTree'] = syllabus_tree
    exam_day = _exam_day(rec)
    if exam_day:
        exam['examDayChecklist'] = exam_day
    return exam


# ------------------------------------------------------------------ the runtime registry
class RegistryRejected(ValueError):
    """A record that must not enter the active registry, with the reason it was refused."""


@dataclass
class RegistryRecord:
    exam_id: str
    cycle: str
    authority_name: str
    authority_domain: str
    official_name: str
    version: int
    gate_decision: str
    published: bool
    exam: dict
    record: dict
    completeness: Optional[dict]
    created_at: str
    updated_at: str
    retired: bool = False

    def meta(self) -> dict:
        return {'examId': self.exam_id, 'cycle': self.cycle, 'authorityName': self.authority_name,
                'authorityDomain': self.authority_domain, 'officialName': self.official_name,
                'version': self.version, 'gateDecision': self.gate_decision, 'published': self.published,
                'createdAt': self.created_at, 'updatedAt': self.updated_at, 'retired': self.retired,
                'origin': 'MACHINE_ACQUIRED'}


def _record_snapshot(rec: ExamRecord) -> dict:
    """The canonical record as read: every field's status, value, note and citation, for audit."""
    out = {}
    for name, f in rec.fields.items():
        out[name] = {'status': f.status.value, 'note': f.note,
                     'value': json.loads(json.dumps(f.value, default=str)),
                     'citation': (f.citation.__dict__ if f.citation else None)}
    return {'examId': rec.exam_id, 'code': rec.code, 'title': rec.title,
            'authorityName': rec.authority_name, 'officialDomain': rec.official_domain,
            'sourcesRead': list(rec.sources_read), 'fields': out}


class ExamRegistry:
    """The runtime home for machine-acquired exams. One row per (exam_id, cycle).

    Not a replacement for `src/data.ts` — authored exams stay authored, and `register` refuses
    any id that already lives in the authored register. Only a gate-PASS, contract-valid runtime
    Exam may be published; a rejected record is refused with its reason, never stored as active.
    """

    DDL = '''
        CREATE TABLE IF NOT EXISTS exam_registry (
            exam_id TEXT NOT NULL,
            cycle TEXT NOT NULL,
            authority_name TEXT NOT NULL,
            authority_domain TEXT NOT NULL,
            official_name TEXT NOT NULL,
            version INTEGER NOT NULL DEFAULT 1,
            gate_decision TEXT NOT NULL,
            published INTEGER NOT NULL DEFAULT 0,
            exam_json TEXT NOT NULL,
            record_json TEXT NOT NULL,
            completeness_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            retired INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (exam_id, cycle)
        )'''

    def __init__(self, db_path: str = 'govos.db'):
        self.db_path = db_path
        self._is_memory = (db_path == ':memory:' or 'mode=memory' in db_path)
        self._shared: Optional[sqlite3.Connection] = None
        if self._is_memory:
            self._shared = sqlite3.connect(db_path)
            self._shared.row_factory = sqlite3.Row
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if self._shared is not None:
            return self._shared
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def _release(self, c: sqlite3.Connection) -> None:
        if not self._is_memory:
            c.close()

    def _init_db(self) -> None:
        c = self._conn()
        c.execute(self.DDL)
        c.commit()
        self._release(c)

    # -- write ------------------------------------------------------------------------------
    def register(self, rec: ExamRecord, *, gate: GateReport, exam: dict,
                 completeness: Optional[ExamCompletenessReport] = None,
                 cycle: str = '', data_ts: str = P.DATA_TS) -> RegistryRecord:
        """Publish a gate-passing, contract-valid runtime Exam. Raises RegistryRejected otherwise."""
        if gate is None or not getattr(gate, 'may_publish', False):
            blockers = '; '.join(str(b) for b in getattr(gate, 'blockers', [])[:5]) if gate else 'no gate report'
            raise RegistryRejected(f'the publication gate did not PASS: {blockers}')
        errors = validate_runtime_exam(exam)
        if errors:
            raise RegistryRejected('runtime exam fails the frontend contract: ' + '; '.join(errors[:6]))
        if exam.get('id') != rec.exam_id:
            raise RegistryRejected(f"identity mismatch: exam payload id {exam.get('id')!r} != record {rec.exam_id!r}")
        if target_in_register(rec.exam_id, data_ts):
            raise RegistryRejected(f'{rec.exam_id} is an authored exam in the register; the runtime '
                                   f'registry never overwrites or duplicates authored records')
        cycle = cycle or str(exam.get('cycle') or get_exam_cycle(exam) or '')
        if not cycle:
            raise RegistryRejected('a runtime exam must declare its cycle/year for cycle isolation')
        now = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        c = self._conn()
        row = c.execute('SELECT version, created_at FROM exam_registry WHERE exam_id = ? AND cycle = ?',
                        (rec.exam_id, cycle)).fetchone()
        version = (row['version'] + 1) if row else 1
        created = row['created_at'] if row else now
        c.execute('''INSERT OR REPLACE INTO exam_registry
                     (exam_id, cycle, authority_name, authority_domain, official_name, version,
                      gate_decision, published, exam_json, record_json, completeness_json,
                      created_at, updated_at, retired)
                     VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, 0)''',
                  (rec.exam_id, cycle, rec.authority_name, rec.official_domain, rec.title, version,
                   gate.decision.value, json.dumps(exam, ensure_ascii=False, default=str),
                   json.dumps(_record_snapshot(rec), ensure_ascii=False, default=str),
                   json.dumps(completeness.to_dict(), ensure_ascii=False) if completeness else None,
                   created, now))
        c.commit()
        self._release(c)
        return RegistryRecord(rec.exam_id, cycle, rec.authority_name, rec.official_domain, rec.title,
                              version, gate.decision.value, True, exam, _record_snapshot(rec),
                              completeness.to_dict() if completeness else None, created, now)

    def retire(self, exam_id: str, cycle: Optional[str] = None) -> bool:
        c = self._conn()
        if cycle:
            cur = c.execute('UPDATE exam_registry SET retired = 1 WHERE exam_id = ? AND cycle = ?', (exam_id, cycle))
        else:
            cur = c.execute('UPDATE exam_registry SET retired = 1 WHERE exam_id = ?', (exam_id,))
        changed = cur.rowcount > 0
        c.commit()
        self._release(c)
        return changed

    # -- read -------------------------------------------------------------------------------
    def _row(self, r: sqlite3.Row) -> RegistryRecord:
        return RegistryRecord(r['exam_id'], r['cycle'], r['authority_name'], r['authority_domain'],
                              r['official_name'], r['version'], r['gate_decision'], bool(r['published']),
                              json.loads(r['exam_json']), json.loads(r['record_json']),
                              json.loads(r['completeness_json']) if r['completeness_json'] else None,
                              r['created_at'], r['updated_at'], bool(r['retired']))

    def get(self, exam_id: str, cycle: Optional[str] = None) -> Optional[RegistryRecord]:
        """The published, unretired record for this exam — and, when given, exactly this cycle."""
        c = None
        try:
            c = self._conn()
            if cycle:
                r = c.execute('SELECT * FROM exam_registry WHERE exam_id = ? AND cycle = ? AND published = 1 AND retired = 0',
                              (exam_id, cycle)).fetchone()
            else:
                r = c.execute('SELECT * FROM exam_registry WHERE exam_id = ? AND published = 1 AND retired = 0 '
                              'ORDER BY cycle DESC LIMIT 1', (exam_id,)).fetchone()
        except sqlite3.Error:
            return None
        finally:
            # Released on every path: a corrupted store must not leave a handle open.
            if c is not None:
                self._release(c)
        return self._row(r) if r else None

    def list_published(self) -> list[RegistryRecord]:
        """Every published, unretired runtime exam. A broken store yields [] — never an error the
        frontend would read as 'there are no exams'; the authored register still stands."""
        c = None
        try:
            c = self._conn()
            rows = c.execute('SELECT * FROM exam_registry WHERE published = 1 AND retired = 0 '
                             'ORDER BY exam_id, cycle').fetchall()
        except sqlite3.Error:
            return []
        finally:
            if c is not None:
                self._release(c)
        return [self._row(r) for r in rows]


# ------------------------------------------------------------------ the generic entry point
class EngineState(str, Enum):
    """The one outcome of a build. Each failure keeps its own state; none is ever collapsed."""

    REGISTERED = 'REGISTERED'                       # gate PASS, contract-valid, published in the registry
    BLOCKED_BY_GATE = 'BLOCKED_BY_GATE'
    RESOLUTION_FAILURE = 'RESOLUTION_FAILURE'
    AMBIGUOUS_AUTHORITY = 'AMBIGUOUS_AUTHORITY'
    INFRASTRUCTURE_FAILURE = 'INFRASTRUCTURE_FAILURE'
    SOURCE_FETCH_FAILURE = 'SOURCE_FETCH_FAILURE'
    ISOLATION_VIOLATION = 'ISOLATION_VIOLATION'
    MATERIALIZATION_INVALID = 'MATERIALIZATION_INVALID'   # gate passed but the payload fails the contract
    REGISTRY_REJECTED = 'REGISTRY_REJECTED'               # e.g. an authored id, a missing cycle


_ORCH_TO_ENGINE = {
    OrchestrationState.BLOCKED_BY_GATE: EngineState.BLOCKED_BY_GATE,
    OrchestrationState.RESOLUTION_FAILURE: EngineState.RESOLUTION_FAILURE,
    OrchestrationState.AMBIGUOUS_AUTHORITY: EngineState.AMBIGUOUS_AUTHORITY,
    OrchestrationState.INFRASTRUCTURE_FAILURE: EngineState.INFRASTRUCTURE_FAILURE,
    OrchestrationState.SOURCE_FETCH_FAILURE: EngineState.SOURCE_FETCH_FAILURE,
    OrchestrationState.ISOLATION_VIOLATION: EngineState.ISOLATION_VIOLATION,
}


@dataclass
class EngineBuildResult:
    query: str
    year: str
    state: EngineState
    reason: str = ''
    resolution: dict = dc_field(default_factory=dict)
    identity: dict = dc_field(default_factory=dict)
    acquisition: dict = dc_field(default_factory=dict)
    verification: dict = dc_field(default_factory=dict)
    completeness: Optional[dict] = None
    gate: dict = dc_field(default_factory=dict)
    materialization: dict = dc_field(default_factory=dict)
    registry: dict = dc_field(default_factory=dict)
    #: A person's field-level decisions, when any were given (review.py).
    reviews: dict = dc_field(default_factory=dict)
    exam: Optional[dict] = None
    orchestration: Optional[OrchestrationResult] = None

    @property
    def registered(self) -> bool:
        return self.state is EngineState.REGISTERED

    def to_dict(self) -> dict:
        return {'query': self.query, 'year': self.year, 'state': self.state.value, 'reason': self.reason,
                'resolution': self.resolution, 'identity': self.identity, 'acquisition': self.acquisition,
                'verification': self.verification, 'completeness': self.completeness, 'gate': self.gate,
                'materialization': self.materialization, 'registry': self.registry,
                'examId': (self.exam or {}).get('id')}

    def summary(self) -> str:
        lines = [f'query:   {self.query}' + (f' ({self.year})' if self.year else ''),
                 f'state:   {self.state.value}']
        if self.resolution:
            lines.append(f"authority: {self.resolution.get('authorityName')} ({self.resolution.get('authorityDomain')})")
        if self.acquisition:
            lines.append(f"acquired:  {self.acquisition.get('fieldsFound')}/{self.acquisition.get('fieldsTotal')} fields, "
                         f"{self.acquisition.get('documentsKept')} document(s)")
        if self.completeness:
            lines.append(f"complete:  {self.completeness.get('completenessPercentage')}% of applicable sections")
        if self.gate:
            lines.append(f"gate:      {self.gate.get('decision')}")
        if self.registry:
            lines.append(f"registry:  {self.registry.get('status')} {self.registry.get('examId') or ''} v{self.registry.get('version') or ''}")
        if self.reason:
            lines.append(f'reason:    {self.reason}')
        return '\n'.join(lines)


def build_exam(exam_query: str, year: str | int = '', *, registry: Optional[ExamRegistry] = None,
               search_fn: Optional[Callable] = None, use_llm: bool = False, provider=None, cache=None,
               siblings: Optional[list] = None, max_docs: int = 8,
               data_ts: str = P.DATA_TS, reviews: Optional[list] = None,
               replay=None) -> EngineBuildResult:
    """The single generic engine entry point: name + cycle in, a registered runtime Exam out.

        build_exam("SSC CGL", 2027)  ·  build_exam("RRB NTPC", 2027)  ·  build_exam("Any Unknown Board Exam", 2028)

    all take the same path: the existing orchestrator (resolve → discover → identity → extract →
    verify → gate, always a dry run — this engine never writes data.ts), then materialize →
    validate against the frontend contract → register. Any failure returns a distinct state with
    a reason and registers nothing. No branch reads an exam or an authority name.
    """
    year = str(year or '')
    res = orchestrate(exam_query, year=year, dry_run=True, use_llm=use_llm, provider=provider,
                      cache=cache, siblings=siblings, max_docs=max_docs, data_ts=data_ts,
                      search_fn=search_fn, reviews=reviews, replay=replay)
    out = EngineBuildResult(query=exam_query, year=year, state=EngineState.BLOCKED_BY_GATE,
                            reason=res.reason, orchestration=res)
    out.reviews = dict(res.reviews or {})

    if res.build is not None:
        br, rec = res.build, res.build.record
        out.resolution = {'query': br.resolved.query, 'officialName': br.resolved.official_name,
                          'year': br.resolved.year, 'authorityName': br.resolved.authority.name,
                          'authorityDomain': br.resolved.authority.domain,
                          'confidence': br.resolved.authority.confidence, 'examId': rec.exam_id}
        out.identity = {u: c.verdict.value for u, c in br.identity.items()}
        out.acquisition = {'documentsKept': len(br.sources.docs), 'documentsRejected': len(br.sources.rejected),
                           'fieldsTotal': len(rec.fields),
                           'fieldsFound': sum(1 for f in rec.fields.values() if f.status is Status.FOUND),
                           'fieldsNeedsReview': sum(1 for f in rec.fields.values() if f.status is Status.NEEDS_REVIEW),
                           'fieldsNotPublished': sum(1 for f in rec.fields.values() if f.status is Status.NOT_PUBLISHED),
                           'fieldsNotExtracted': sum(1 for f in rec.fields.values() if f.status is Status.NOT_EXTRACTED),
                           'buildState': br.build_state.value}
        out.verification = {n: {'status': v.status, 'infra': v.infra.value,
                                'decision': v.llm.decision.value if v.llm else None}
                            for n, v in res.verifications.items()}
        out.completeness = br.completeness.to_dict() if getattr(br, 'completeness', None) else None
    if res.gate is not None:
        out.gate = {'decision': res.gate.decision.value,
                    'blockers': [str(b) for b in res.gate.blockers], 'allowedUnpublished': list(res.gate.allowed)}

    # Every non-passing outcome keeps its own state and registers nothing.
    if res.state is not OrchestrationState.STAGED or res.build is None or res.gate is None or not res.gate.may_publish:
        out.state = _ORCH_TO_ENGINE.get(res.state, EngineState.BLOCKED_BY_GATE)
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = res.reason or 'the build did not reach a gate PASS, so nothing was materialized'
        return out

    br, rec = res.build, res.build.record
    cycle = str(br.resolved.year or year or get_exam_cycle({'id': rec.exam_id, 'title': rec.title}) or '')
    exam = materialize_exam(rec, cycle=cycle, completeness=getattr(br, 'completeness', None), gate=res.gate)
    errors = validate_runtime_exam(exam)
    out.materialization = {'ok': not errors, 'errors': errors, 'version': MATERIALIZER_VERSION,
                           'postsWithoutPrintedGroup': exam['materialization']['postsWithoutPrintedGroup']}
    if errors:
        out.state = EngineState.MATERIALIZATION_INVALID
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = 'gate PASS, but the materialized exam fails the frontend contract: ' + '; '.join(errors[:4])
        return out
    out.exam = exam

    registry = registry or ExamRegistry()
    try:
        rr = registry.register(rec, gate=res.gate, exam=exam, completeness=getattr(br, 'completeness', None),
                               cycle=cycle, data_ts=data_ts)
    except RegistryRejected as exc:
        out.state = EngineState.REGISTRY_REJECTED
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = str(exc)
        return out
    out.state = EngineState.REGISTERED
    out.registry = {'status': 'REGISTERED', 'examId': rr.exam_id, 'cycle': rr.cycle, 'version': rr.version}
    out.reason = (f'gate PASS; {rec.exam_id} (cycle {cycle}) materialized and registered as a runtime exam, '
                  f'version {rr.version}. data.ts untouched.')
    return out


# ------------------------------------------------------------------ CLI
def main(argv: Optional[list] = None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog='exam_builder.materialize',
                                 description='Build one exam through the universal engine into the runtime registry.')
    ap.add_argument('exam', help='the exam name, e.g. "RRB NTPC"')
    ap.add_argument('--year', default='', help='the cycle/year, e.g. 2027')
    ap.add_argument('--db', default='govos.db', help='registry SQLite file')
    ap.add_argument('--llm', action='store_true', help='also run optional Qwen verification')
    args = ap.parse_args(argv)
    res = build_exam(args.exam, args.year, registry=ExamRegistry(args.db), use_llm=args.llm)
    print(res.summary())
    return 0 if res.registered else 1


if __name__ == '__main__':
    raise SystemExit(main())
