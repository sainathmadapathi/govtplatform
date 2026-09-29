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
from .runtime_simulator import build_simulator
from .runtime_evidence import (derive_pattern_evidence, evidence_problems, fact_provenance,
                               is_provenance, link_revisions, stamp_exam)

MATERIALIZER_VERSION = 'materialize-2'


# ------------------------------------------------------------------ the projection map
#: Every canonical contract field that has a runtime representation, and where it lands.
#:
#: This table is the materializer's contract with the canonical record, and it is enforced:
#: `validate_projection` checks, for every canonical field that is FOUND, that the runtime
#: paths below exist and carry content -- or that the materialization ledger records an
#: explicit, reasoned disposition for it (held for review, withheld as unreliable). A FOUND
#: field that reaches neither is a *silent loss*, and publication fails on it.
#:
#: Authoritative runtime representation for a machine-acquired exam, and its compatibility
#: projections (derived deterministically from the authoritative one, never independently):
#:
#:   patternTree      authoritative   ->  stages          (one ExamStage per STAGE root node)
#:   syllabusTree     authoritative   ->  syllabus        (flat topics for map / list / checklist)
#:   admitCardEvents  authoritative   ->  (admitCardDetails is not derived: collapsing a list of
#:                                         events into one card would invent a status)
#:   officialPapers / answerKeys / resultDeclarations / cutoffsHistory / ageRelaxations /
#:   resultNextSteps / applicationGuide   carried as read; no competing representation.
PROJECTION_MAP: dict[str, tuple[str, ...]] = {
    'officialName': ('title',),
    'authority': ('authorityName',),
    'applicationPortal': ('applicationGuide.officialPortal',),
    'howToApply': ('applicationGuide.otrSteps',),
    'requiredDocuments': ('applicationGuide.requiredDocuments',),
    'photoSignatureGuidelines': ('applicationGuide.photoRules.rules|applicationGuide.signatureRules.rules',),
    'fee': ('applicationGuide.fee',),
    'feeExemptions': ('applicationGuide.fee.exemptions',),
    'posts': ('posts',),
    'vacancies': ('vacanciesTotal',),
    'ageLimits': ('eligibilityHighlights[Age limits]',),
    'qualification': ('eligibilityHighlights[Educational qualification]',),
    'attempts': ('eligibilityHighlights[Number of attempts]',),
    'dates': ('dates',),
    'corrigenda': ('corrigendums',),
    'examPattern': ('patternTree',),
    'syllabus': ('syllabusTree', 'syllabus'),
    'officialPapers': ('officialPapers',),
    'answerKeys': ('answerKeys',),
    'admitCard': ('admitCardEvents',),
    'results': ('resultDeclarations',),
    'nextSteps': ('resultNextSteps',),
    'cutoffs': ('cutoffsHistory',),
    'examDayChecklist': ('examDayChecklist',),
    'faqs': ('faqs',),
    'vacancyBreakup': ('vacancyBreakups',),
}


class MaterializationLoss(ValueError):
    """A canonical FOUND field that did not survive materialization, with no recorded reason."""

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

#: The frontend ImportantDate.type union. OTHER carries a milestone the notice printed with a
#: label no specific member names ("Date of upload"); forcing it into the nearest member would
#: invent a milestone, and dropping it would lose a printed date.
_DATE_TYPES = {'NOTIFICATION', 'APPLICATION_OPEN', 'APPLICATION_CLOSE', 'CORRECTION_WINDOW',
               'ADMIT_CARD', 'EXAM_TIER1', 'EXAM_TIER2', 'ANSWER_KEY', 'RESULT', 'INTERVIEW', 'OTHER'}


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
        # A post needs its name; its Group is carried only where the authority printed one, so
        # an empty classification is the honest value, never a gap to be filled in.
        if not isinstance(p, dict) or not p.get('postName') or not isinstance(p.get('classification'), str):
            errors.append('every post must carry postName and a classification string (empty where none was printed)')
    # The UI keys every card on its id; two items sharing one are one item to it, and the later
    # may silently not render. That is a loss after the projection check, so it is refused here.
    for key in ('dates', 'posts', 'resultDeclarations', 'admitCardEvents', 'syllabusTree',
                'vacancyBreakups'):
        ids: list = []
        stack = list(exam.get(key) or [])
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                if item.get('id'):
                    ids.append(item['id'])
                stack.extend(item.get('children') or [])
        repeated = sorted({i for i in ids if ids.count(i) > 1})
        if repeated:
            errors.append(f'{key} carries repeated ids {repeated[:5]}; every item must be addressable on its own')
    rg = exam.get('globalRuleGroup')
    if isinstance(rg, dict):
        if rg.get('operator') not in ('AND', 'OR') or not isinstance(rg.get('rules'), list) or not rg.get('id'):
            errors.append('globalRuleGroup must carry id, operator AND|OR, and rules[]')
    ag = exam.get('applicationGuide')
    if isinstance(ag, dict):
        for k in ('officialPortal', 'otrSteps', 'photoRules', 'signatureRules', 'certificateRules', 'rejectionPitfalls'):
            if k not in ag:
                errors.append(f'applicationGuide is missing {k!r}')
    # Every piece of evidence the exam carries must identify itself, say what kind it is, and
    # never claim official verification without a source a candidate can open.
    errors += evidence_problems(exam)[:20]
    return errors


def _path_has_content(exam: dict, path: str) -> bool:
    """Does the runtime exam carry content at `path`?

    `a.b.c` walks objects; `x|y` is satisfied by either; `highlights[Title]` asks for a card of
    that title in a list of {title, body} cards."""
    if '|' in path:
        return any(_path_has_content(exam, p) for p in path.split('|'))
    m = re.match(r'^(\w+)\[(.+)\]$', path)
    if m:
        cards = exam.get(m.group(1)) or []
        return any(isinstance(c, dict) and c.get('title') == m.group(2) and c.get('body') for c in cards)
    node: Any = exam
    for part in path.split('.'):
        if not isinstance(node, dict) or part not in node:
            return False
        node = node[part]
    return node not in (None, '', [], {})


#: Canonical list fields whose items must each reach runtime (no silent partial drop).
_ITEM_PRESERVING = (('dates', 'dates'), ('admitCard', 'admitCardEvents'), ('answerKeys', 'answerKeys'),
                    ('results', 'resultDeclarations'), ('officialPapers', 'officialPapers'),
                    ('cutoffs', 'cutoffsHistory'), ('corrigenda', 'corrigendums'),
                    ('vacancyBreakup', 'vacancyBreakups'))

#: Runtime collections of official facts; every item must carry provenance.
_PROVENANCED = ('dates', 'admitCardEvents', 'officialPapers', 'answerKeys', 'resultDeclarations',
                'cutoffsHistory', 'examDayChecklist', 'faqs', 'eligibilityHighlights', 'ageRelaxations',
                'vacancyBreakups')


def validate_projection(rec: ExamRecord, exam: dict) -> list[str]:
    """Every canonical FOUND fact that did not survive into the runtime exam, as reasons.

    The canonical gate judges the record; it cannot see what materialization then does to it.
    This is the second layer: a FOUND field must reach the runtime paths PROJECTION_MAP names,
    or be listed in the ledger (`materialization.heldForReview`) with a reason. A list field
    must not lose items, and every official item must keep its provenance. An empty result
    means nothing was lost silently."""
    losses: list[str] = []
    held = ((exam.get('materialization') or {}).get('heldForReview') or {}) if isinstance(exam, dict) else {}
    for name, paths in PROJECTION_MAP.items():
        f = rec.get(name)
        if not (f and f.status is Status.FOUND and f.value not in (None, '', [], {})):
            continue
        if name in held and not held[name].get('partial'):
            continue                      # accounted for: held for review, with its reason
        for p in paths:
            if not _path_has_content(exam, p):
                losses.append(f'{name}: FOUND in the canonical record, but runtime {p} is empty '
                              f'and no reason is recorded')
    for name, coll in _ITEM_PRESERVING:
        f = rec.get(name)
        if not (f and f.status is Status.FOUND and isinstance(f.value, list)):
            continue
        n_canonical = sum(1 for x in f.value if isinstance(x, dict))
        n_runtime = len(exam.get(coll) or [])
        if name == 'dates':
            # The superseded-last-date row comes from a different field; it is not one of these.
            n_runtime = sum(1 for d in exam.get('dates') or []
                            if not str(d.get('id', '')).endswith('-close-superseded'))
        if n_runtime < n_canonical:
            losses.append(f'{name}: {n_canonical} canonical item(s) but only {n_runtime} reached runtime {coll}')
    tree = exam.get('patternTree') or []
    if any(isinstance(n, dict) and n.get('level') == 'STAGE' for n in tree) and not exam.get('stages'):
        losses.append('examPattern: the pattern tree names stages, but the stages projection is empty')
    for coll in _PROVENANCED:
        for item in exam.get(coll) or []:
            if isinstance(item, dict) and not (isinstance(item.get('provenance'), dict) and item['provenance']):
                losses.append(f'{coll}: item {item.get("id") or item.get("title") or "?"} carries no provenance')
    return losses


# ------------------------------------------------------------------ ExamRecord -> runtime Exam
def _prov(rec: ExamRecord, f: Field, suffix: str) -> Optional[dict]:
    if not f.citation:
        return None
    return f.citation.to_provenance(prov_id=f'prov-{rec.exam_id}-{suffix}', level=f.verification_level)


def _vacancy_count(value) -> tuple[str, bool]:
    """(the count as a candidate reads it, whether the source called it approximate).

    A vacancy figure arrives as a bare number from a printed total, or as {count,
    isApproximate} from a sentence ("There are approx. 12,256 vacancies"). Stringifying the
    second put "{'count': '12256', ...}" in front of candidates, and the overview called every
    figure "approximately", including one read from a table's printed TOTAL."""
    if isinstance(value, dict):
        count = str(value.get('count') or '').replace(',', '').strip()
        return (count if count.isdigit() else '', bool(value.get('isApproximate')))
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(int(value)), False
    text = str(value or '').replace(',', '').strip()
    return (text if text.isdigit() else '', False)


def _vacancy_breakups(rec: ExamRecord) -> list[dict]:
    """Each verified break-up table, as the authority printed its columns, rows tied to posts.

    Counts stay split into fresh and carried-forward, as printed; the column labels are the
    table's own header paths. Every table names its document, its pages and the arithmetic it
    reconciled, so the section can say why the figures are trusted."""
    f = rec.get('vacancyBreakup')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    # Rows were joined to the canonical posts; the runtime names a post by its position in
    # that same list (see `_posts`), so the join is carried across by position.
    posts = rec.value('posts') if isinstance(rec.value('posts'), list) else []
    runtime_id = {str(p.get('id')): f'post-{rec.exam_id}-{i}'
                  for i, p in enumerate(posts[:80]) if isinstance(p, dict) and p.get('id')}
    out = []
    for i, t in enumerate(x for x in f.value if isinstance(x, dict)):
        prov = dict(_prov(rec, f, f'vacancy-breakup-{i}') or {},
                    documentTitle=t.get('documentTitle', ''), officialUrl=t.get('documentUrl', ''),
                    pageNumber=(t.get('pages') or [1])[0],
                    excerptText='; '.join(t.get('checks') or [])[:400])
        out.append({
            'id': f'vb-{rec.exam_id}-{i}',
            'documentTitle': t.get('documentTitle', ''), 'documentUrl': t.get('documentUrl', ''),
            'pages': list(t.get('pages') or []),
            'checks': list(t.get('checks') or []),
            'columns': [' / '.join(re.sub(r'\s+', ' ', p) for p in path) for path in t.get('columns') or []],
            'rows': [{'postId': runtime_id.get(str(r.get('postId', '')), ''), 'postCode': r.get('postCode', ''),
                      'printedName': r.get('printedName', ''), 'zone': r.get('zone', ''),
                      'counts': [{'fresh': c.get('fresh', 0), 'carriedForward': c.get('carriedForward', 0)}
                                 for c in r.get('counts') or []],
                      **({'postTotal': r['postTotal']} if r.get('postTotal') is not None else {}),
                      'page': r.get('page')}
                     for r in t.get('rows') or []],
            'tableTotal': t.get('tableTotal'),
            'provenance': prov,
        })
    return out


def _dates(rec: ExamRecord) -> list[dict]:
    f = rec.get('dates')
    out: list[dict] = []
    replaced: dict[str, str] = {}
    if f and f.usable and isinstance(f.value, list):
        prov = _prov(rec, f, 'date')
        # Which row replaced which, as reconciliation recorded it: the evidence of both sides
        # is linked below so the page can show the old statement beside the new.
        replaced = {str(d['id']): str(d['supersededBy']) for d in f.value
                    if isinstance(d, dict) and d.get('id') and d.get('supersededBy')}
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
                # Which stage an examination date belongs to, and whether its evidence said so.
                **{k: d[k] for k in ('stageAssociation', 'stageLabel') if d.get(k)},
                # A date the authority printed at month precision ("May/June 2024"), as printed.
                **({'displayWhen': str(d['displayWhen'])} if d.get('displayWhen') else {}),
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
        governing = [d for d in out if d['type'] == 'APPLICATION_CLOSE' and d['status'] == 'AVAILABLE']
        if len(governing) == 1:
            replaced[out[-1]['id']] = governing[0]['id']
    link_revisions(out, replaced)
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
            # The revision's own evidence: the statement that made the change, in the document
            # that made it. A revision recorded from reconciled dates is given the reconciled
            # date's evidence (old and new linked) once the dates exist; see _corrigendum_evidence.
            base = _prov(rec, corr, f'corr-{i}') or {}
            own = dict(base, **{k: v for k, v in (
                ('documentTitle', str(c.get('sourceTitle') or '')),
                ('officialUrl', str(c.get('sourceUrl') or '')),
                ('excerptText', _clean(c.get('evidenceSpan') or '', 600))) if v}) if base else {}
            if own and own.get('officialUrl') != base.get('officialUrl'):
                # The field's page is its first entry's; this entry cites another document.
                own['pageNumber'] = None
            out.append({
                'id': str(c.get('id') or f'corr-{rec.exam_id}-{i}'),
                **({'provenance': own} if own else {}),
                'title': str(c.get('title') or f"Corrigendum: {c.get('affectedField', 'revision')}"),
                'noticeNumber': str(c.get('sourceTitle') or c.get('noticeNumber') or ''),
                # A revision whose source prints no date of its own carries publishedDate ''
                # on purpose: its effective date is when the change applies, not when it was
                # announced, and reporting one as the other would date an announcement.
                'publishedDate': str(c['publishedDate'] if 'publishedDate' in c
                                     else c.get('effectiveDate') or '')[:10],
                'effectiveDate': str(c.get('effectiveDate') or '')[:10],
                # Both: the quoted statements, then what kind of record this is -- a revision
                # read from a later official statement must say it is not a corrigendum notice.
                'summary': ' '.join(p for p in (str(c.get('evidenceSpan') or ''), str(c.get('note') or ''))
                                    if p),
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


def _single_age_band(rec: ExamRecord) -> tuple[int, int]:
    """The exam-wide age band, only where the record states exactly one.

    A notice that prints different limits for different posts (`minima`/`maxima` that
    disagree) has no exam-wide band, and giving every post the widest one would tell some
    candidates they qualify for posts they do not. 0/0 is returned then -- the eligibility
    engine reads a 0 upper limit as "not published", never as a limit of zero."""
    f = rec.get('ageLimits')
    if not (f and f.ok and isinstance(f.value, dict)):
        return 0, 0
    v = f.value
    minima, maxima = v.get('minima'), v.get('maxima')
    if (isinstance(minima, list) and len(set(minima)) > 1) or (isinstance(maxima, list) and len(set(maxima)) > 1):
        return 0, 0
    lo, hi = v.get('minAge'), v.get('maxAge')
    return (int(lo) if isinstance(lo, (int, float)) else 0, int(hi) if isinstance(hi, (int, float)) else 0)


def _posts(rec: ExamRecord) -> tuple[list[dict], list[str], list[dict]]:
    """Posts as read: name always, Group only where printed (never inferred), age only where one
    exam-wide band exists. Returns (posts, names-without-printed-group, held-for-review).

    A candidate that is plainly a document or a certificate ("Hall Ticket", "Non-Creamy Layer
    Certificate") is not a post: a checklist of what to bring reconstructs like a list of what
    one is recruited to. Such candidates are never published as posts; they are held for
    review with their evidence, and the ledger says so."""
    from .eligibility import is_document_not_post

    f = rec.get('posts')
    if not (f and f.usable and isinstance(f.value, list)):
        return [], [], []
    lo, hi = _single_age_band(rec)
    rows, no_group, held = [], [], []
    prov = _prov(rec, f, 'posts') or {}
    for i, item in enumerate(f.value[:80]):
        if isinstance(item, dict):
            name = str(item.get('postName') or item.get('name') or '').strip()
            cls = str(item.get('classification') or '') or classification_of(name)
            department = str(item.get('department') or '')
            pay_level = str(item.get('payLevel') or '')
        else:
            name = str(item).strip()
            cls, department, pay_level = classification_of(name), '', ''
        if not name:
            continue
        if is_document_not_post(name):
            held.append({'candidate': name, 'reason': 'reads as a document or certificate, not a post'})
            continue
        if not cls:
            no_group.append(name)
        extra = item if isinstance(item, dict) else {}
        # A post's own row states its own age band; the exam-wide band applies only where
        # the notice prints one for every post.
        own_lo, own_hi = extra.get('minAge'), extra.get('maxAge')
        pay_text = pay_level
        is_scale = bool(re.search(r'\d[\d,]{3,}\s*[-–—]\s*\d[\d,]{3,}', pay_text))
        row = {
            'id': f'post-{rec.exam_id}-{i}', 'postName': re.sub(_GROUP_TAIL_RX, '', name).strip(),
            # The post's own department as read; never the recruiting authority's name, which
            # is not the department a candidate would serve in.
            'department': department,
            'payLevel': '' if is_scale else pay_level, 'payScale': pay_text if is_scale else '',
            'classification': cls,
            'minAge': int(own_lo) if isinstance(own_lo, (int, float)) else lo,
            'maxAge': int(own_hi) if isinstance(own_hi, (int, float)) else hi,
            # Each post cites the row it was read from; the field's citation is the fallback.
            'provenance': (dict(prov, id=f"{prov.get('id', 'prov')}-{i}",
                                excerptText=_clean(extra['evidenceSpan'], 600),
                                **({'pageNumber': extra['page']} if extra.get('page') else {}))
                           if extra.get('evidenceSpan') else prov),
        }
        if extra.get('postCode'):
            row['postCode'] = str(extra['postCode'])
        if isinstance(extra.get('vacancies'), int):
            row['vacancies'] = extra['vacancies']
        if extra.get('qualification'):
            row['specialQualification'] = _clean(extra['qualification'], 600)
        if extra.get('physicalRequirements'):
            row['physicalRequired'] = True
            row['physicalNote'] = _clean(' '.join(extra['physicalRequirements']), 900)
        if extra.get('conditions'):
            row['postConditions'] = [_clean(c, 320) for c in extra['conditions']]
        rows.append(row)
    return rows, no_group, held


def _eligibility_highlights(rec: ExamRecord) -> list[dict]:
    cards = []
    for name, title in (('ageLimits', 'Age limits'), ('qualification', 'Educational qualification'),
                        ('attempts', 'Number of attempts'), ('fee', 'Fee')):
        f = rec.get(name)
        if not (f and f.usable and f.citation):
            continue
        v = f.value
        if name == 'ageLimits' and isinstance(v, dict):
            minima, maxima = v.get('minima'), v.get('maxima')
            if isinstance(minima, list) and isinstance(maxima, list) and (len(set(minima)) > 1 or len(set(maxima)) > 1):
                # Post-scoped limits: the notice states a different band per post code. Stating
                # one band would misdescribe some posts, so the full spread is shown as read.
                lo = '/'.join(str(x) for x in sorted(set(minima)))
                hi = '/'.join(str(x) for x in sorted(set(maxima)))
                body = (f"{lo} to {hi} years, depending on the post"
                        + (f", as on {v['asOn']}" if v.get('asOn') else '')
                        + ". The exact band for each post is in the notice; GovOS did not "
                          "collapse them into one figure.")
            else:
                body = (f"{v.get('minAge')} to {v.get('maxAge')} years"
                        + (f" as on {v['asOn']}" if v.get('asOn') else '')
                        + (f"; born on or after {v['bornNotEarlierThan']} and on or before {v['bornNotLaterThan']}."
                           if v.get('bornNotEarlierThan') else '.'))
        elif isinstance(v, dict) and v.get('text'):
            body = str(v['text'])[:400]
        elif name == 'fee' and isinstance(v, dict) and v.get('components'):
            # Each fee under the name the notice gave it, never one merged figure.
            body = '; '.join(f"{c.get('label') or c.get('feeType')}: Rs. {c.get('amount'):g}"
                             for c in v['components'] if isinstance(c, dict) and isinstance(c.get('amount'), (int, float)))
            body += ' — as printed in the notice; exemptions, where stated, are listed with the application guide.'
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


def _notice_url(rec: ExamRecord) -> tuple[str, Optional[Field]]:
    """The document this record's facts were actually read from: the URL cited most often by
    the FOUND fields (the notification), and the field whose provenance to reuse. There is no
    separate `notice` field on a machine build -- the notification is a source, and its URL
    lives on every citation it produced."""
    counts: dict[str, int] = {}
    holder: dict[str, Field] = {}
    # Fields are visited by name, not in the order they were set: the same canonical record
    # must give the same runtime however it was serialized. Visiting in insertion order made
    # the notice's provenance whichever field a build happened to set first, and a record
    # re-saved with sorted keys changed what a candidate saw.
    for name in sorted(rec.fields):
        f = rec.fields[name]
        if name in ('officialName', 'authority'):
            continue
        if f.usable and f.citation and getattr(f.citation, 'url', ''):
            u = f.citation.url
            if '/preview/' in u or u.lower().split('?')[0].endswith('.pdf'):
                counts[u] = counts.get(u, 0) + 1
                holder.setdefault(u, f)
    if not counts:
        return '', None
    # The most-cited document; a tie goes to the address itself, never to visiting order.
    best = min(counts, key=lambda u: (-counts[u], u))
    return best, holder[best]


def _resources(rec: ExamRecord) -> list[dict]:
    """Links only — the content policy forbids storing anything. The authority's own notice
    and its application portal, each read from this build, so the library is never empty for
    an exam whose notice we read."""
    items = []
    notice_url, notice_field = _notice_url(rec)
    if notice_url and notice_field:
        items.append({
            'id': f'res-{rec.exam_id}-notice', 'title': f'{rec.title} — Examination Notice (official PDF)',
            'subject': 'Official Gazette', 'author': rec.authority_name, 'type': 'OFFICIAL_PDF',
            'resourceFormat': 'DIRECT_PDF', 'url': notice_url, 'directPdfUrl': notice_url,
            'officialTag': f'{rec.code} — OFFICIAL NOTICE', 'isEssential': True,
            'recommendedFor': 'The rules themselves, from the authority that wrote them.',
            'description': 'The examination notice this record was read from.',
            'linkVerifiedDate': notice_field.citation.verified_date,
            # The notice cited as a document, not through one fact read from it: another
            # field's excerpt ("Hall Tickets") says nothing about the notice as a whole.
            'provenance': dict(_prov(rec, notice_field, 'notice') or {},
                               documentTitle=notice_field.citation.document_title,
                               officialUrl=notice_url, pageNumber=1,
                               clauseNumber='Examination notice',
                               excerptText=notice_field.citation.document_title),
        })
    printed = rec.value('applicationPortal')
    portal, portal_note = _portal_link(rec)
    if printed and isinstance(printed, str) and printed.startswith('http'):
        items.append({
            'id': f'res-{rec.exam_id}-portal', 'title': f'{rec.authority_name} — Online Application Portal',
            'subject': 'Official Portal', 'author': rec.authority_name, 'type': 'OFFICIAL_PORTAL',
            'resourceFormat': 'EXTERNAL_PORTAL', 'url': portal, 'isEssential': True,
            'officialTag': f'{rec.code} — APPLY HERE',
            'recommendedFor': 'Where the authority takes the application.',
            'description': portal_note or 'The portal the notice sends candidates to.',
            'linkVerifiedDate': '', 'provenance': _prov(rec, rec.get('applicationPortal'), 'portal') or {},
        })
    # Every result or verification notice the record cites is an official document of this
    # recruitment, identity-checked when it was read. Listed as a link under the title the
    # authority gave it, newest first; nothing is stored.
    results = rec.get('results')
    if results and results.usable and isinstance(results.value, list):
        seen_urls = {i['url'] for i in items}
        notices = [r for r in results.value if isinstance(r, dict) and str(r.get('documentUrl') or '').startswith('http')]
        notices.sort(key=lambda r: str(r.get('declaredAt') or ''), reverse=True)
        for i, r in enumerate(notices[:20]):
            url = str(r['documentUrl'])
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = _clean(r.get('sourceLabel') or r.get('label') or 'Official notice', 200)
            when = str(r.get('declaredAt') or '')
            items.append({
                'id': f'res-{rec.exam_id}-notice-{i}', 'title': title,
                'subject': 'Official Notices', 'author': rec.authority_name, 'type': 'OFFICIAL_PDF',
                'resourceFormat': 'DIRECT_PDF', 'url': url, 'directPdfUrl': url,
                'officialTag': f'{rec.code} — OFFICIAL NOTICE' + (f' ({when})' if when else ''),
                'isEssential': r.get('kind') in ('SELECTION', 'FINAL_RESULT'),
                'recommendedFor': 'The authority’s own notice for this stage of the recruitment.',
                'description': 'Issued by the authority for this recruitment' + (f' on {when}.' if when else '.'),
                'linkVerifiedDate': results.citation.verified_date if results.citation else '',
                'provenance': dict(_prov(rec, results, f'result-notice-{i}') or {},
                                   officialUrl=url, documentTitle=title),
            })
    # Every other document of this recruitment the build read and identity-matched: a schedule
    # that fed only the timeline is still the authority's own notice a candidate may need.
    official = rec.get('officialSources')
    if official and official.usable and isinstance(official.value, list):
        seen_urls = {i['url'] for i in items}
        for i, s in enumerate(official.value):
            if not isinstance(s, dict) or s.get('identity') != 'MATCH':
                continue
            url = str(s.get('url') or '')
            if not url.startswith('http') or url in seen_urls:
                continue
            seen_urls.add(url)
            title = _clean(s.get('title') or 'Official notice', 200)
            # A document is a file; a service page (a hall-ticket lookup) is not, whatever
            # kind of source it was read as.
            is_pdf = s.get('kind') != 'EXAM_PAGE' and bool(re.search(r'\.pdf$|/preview/', url, re.I))
            items.append({
                'id': f'res-{rec.exam_id}-source-{i}', 'title': title,
                'subject': 'Official Notices', 'author': rec.authority_name,
                'type': 'OFFICIAL_PDF' if is_pdf else 'OFFICIAL_PORTAL',
                'resourceFormat': 'DIRECT_PDF' if is_pdf else 'EXTERNAL_PORTAL', 'url': url,
                **({'directPdfUrl': url} if is_pdf else {}),
                'officialTag': f'{rec.code} — OFFICIAL SOURCE',
                'recommendedFor': 'A document this record was read from.',
                'description': 'Issued by the authority for this recruitment; identity-checked when read.',
                'linkVerifiedDate': official.citation.verified_date if official.citation else '',
                'provenance': dict(_prov(rec, official, f'source-{i}') or {},
                                   officialUrl=url, documentTitle=title),
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


def _how_to_apply_lines(value: Any) -> list[str]:
    """Readable instruction lines from whatever the howToApply reader produced.

    The semantic reader returns a *list of stage dicts* (id, title, description); rendering
    the list with `str()` printed a raw Python repr into the UI. Each stage becomes one
    "Title — description" line here, in the authority's own words, nothing invented."""
    lines: list[str] = []
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                title = re.sub(r'\s+', ' ', str(item.get('title') or '').strip())
                desc = re.sub(r'\s+', ' ', str(item.get('description') or item.get('text') or '').strip())
                text = f'{title} — {desc}' if title and desc and title.lower() not in desc.lower() else (desc or title)
            else:
                text = re.sub(r'\s+', ' ', str(item).strip())
            if text:
                lines.append(text[:600])
    elif isinstance(value, dict):
        text = re.sub(r'\s+', ' ', str(value.get('text') or '').strip())
        if text:
            lines.append(text[:1200])
    elif value:
        lines.append(re.sub(r'\s+', ' ', str(value).strip())[:1200])
    return lines[:20]


def _clean(text: Any, limit: int = 600) -> str:
    return re.sub(r'\s+', ' ', str(text or '')).strip()[:limit]


def _upload_spec(kind: str, rules: list[str], prov: Optional[dict]) -> dict:
    """A DocumentSpecification carrying exactly what the notice said about this upload.

    `rules` are the notice's own sentences. The structured slots (dimensions, format, size)
    are left empty rather than filled with a plausible value: the notice's sentence is the
    fact, and the UI prints only slots that carry one."""
    spec = {'documentType': kind, 'dimensions': '', 'fileFormat': '', 'fileSize': '',
            'rules': [r for r in (_clean(x) for x in rules) if r][:20], 'sampleDescription': ''}
    if prov:
        spec['provenance'] = prov
    return spec


def _required_documents(rec: ExamRecord) -> list[dict]:
    f = rec.get('requiredDocuments')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    prov = _prov(rec, f, 'documents') or {}
    out = []
    for i, d in enumerate(f.value[:60]):
        if isinstance(d, dict):
            name = _clean(d.get('name'), 200)
            if not name or _garbage_name(name):
                continue
            item = {'id': str(d.get('id') or f'doc-{rec.exam_id}-{i}'), 'name': name,
                    'required': bool(d.get('required', True)),
                    'specifications': [_clean(s, 200) for s in (d.get('specifications') or []) if _clean(s)],
                    'provenance': dict(prov, id=f"{prov.get('id', 'prov')}-{i}",
                                       **({'excerptText': _clean(d.get('evidenceSpan'))} if d.get('evidenceSpan') else {}),
                                       **({'pageNumber': d['page']} if d.get('page') else {}))}
        else:
            name = _clean(d, 200)
            if not name or _garbage_name(name):
                continue
            item = {'id': f'doc-{rec.exam_id}-{i}', 'name': name, 'required': True,
                    'specifications': [], 'provenance': dict(prov, id=f"{prov.get('id', 'prov')}-{i}")}
        out.append(item)
    return out


def _fee_details(rec: ExamRecord) -> Optional[dict]:
    """The fee as the notice printed it, with the exemptions it stated -- no amount computed,
    no category assumed exempt."""
    fee = rec.get('fee')
    exf = rec.get('feeExemptions')
    has_fee = bool(fee and fee.usable)
    has_ex = bool(exf and exf.usable and isinstance(exf.value, list))
    if not (has_fee or has_ex):
        return None
    out: dict = {'amounts': [], 'rules': [], 'acceptedModes': [], 'exemptions': []}
    if has_fee:
        v = fee.value
        if isinstance(v, dict):
            amounts = v.get('amounts') or ([v['amount']] if v.get('amount') not in (None, '', 0) else [])
            out['amounts'] = [str(a) for a in dict.fromkeys(str(a) for a in amounts if str(a) not in ('', 'None'))]
            out['acceptedModes'] = [_clean(m, 80) for m in (v.get('acceptedModes') or v.get('paymentModes') or []) if _clean(m)]
            out['rules'] = [{'scope': _clean(r.get('scope'), 120), 'amount': (str(r['amount']) if r.get('amount') not in (None, '') else ''),
                             'isExempt': r.get('isExempt') is True}
                            for r in (v.get('rules') or []) if isinstance(r, dict)]
            # Named fee components (application processing, examination): each amount under
            # its own name, with the sentence it was printed in.
            for c in v.get('components') or []:
                if isinstance(c, dict) and isinstance(c.get('amount'), (int, float)):
                    amount = f"{c['amount']:g}"
                    out['rules'].append({'scope': _clean(c.get('label') or c.get('feeType'), 120),
                                         'amount': amount, 'isExempt': False,
                                         'feeType': c.get('feeType', ''), 'statedAs': _clean(c.get('evidenceSpan'))})
                    if amount not in out['amounts']:
                        out['amounts'].append(amount)
        else:
            out['amounts'] = [_clean(v, 80)]
        if fee.citation:
            out['statedAs'] = _clean(fee.citation.excerpt)
        out['provenance'] = _prov(rec, fee, 'fee') or {}
    if has_ex:
        ex_prov = _prov(rec, exf, 'fee-exemptions') or {}
        for i, e in enumerate(exf.value):
            if not isinstance(e, dict):
                continue
            item = {'category': _clean(e.get('category'), 160),
                    'statedAs': _clean(e.get('evidenceSpan')),
                    'provenance': dict(ex_prov, id=f"{ex_prov.get('id', 'prov')}-{i}")}
            if e.get('exemptedFeeType'):
                item['exemptedFeeType'] = e['exemptedFeeType']
            out['exemptions'].append(item)
    return out


def _portal_link(rec: ExamRecord) -> tuple[str, str]:
    """(the portal address to link, a note), with the notice's own address kept in the note.

    A notice prints the portal as it stood when the notice was issued. An authority that has
    since been renamed or moved leaves that address on another registered domain, where it may
    no longer answer -- a state commission's former domain stopped resolving after it was
    renamed. A link off the authority's own estate is
    therefore not published as its portal; the authority's own site is linked instead and the
    printed address is quoted, so nothing the notice said is hidden.
    """
    from urllib.parse import urlsplit
    from ..exam_authoring.sources import same_estate
    printed = rec.value('applicationPortal')
    own = rec.official_domain
    if not (isinstance(printed, str) and printed.startswith('http')):
        return own, ''
    if same_estate(urlsplit(printed).hostname or '', urlsplit(own).hostname or ''):
        return printed, ''
    return own, (f'The notice names {printed} as the application portal. That address is not on '
                 f'the authority’s current domain ({own}), so the authority’s own site is linked '
                 f'instead.')


def _application_guide(rec: ExamRecord) -> dict:
    portal = _portal_link(rec)[0]
    how = rec.get('howToApply')
    steps: list[dict] = []
    if how and how.usable:
        instructions = _how_to_apply_lines(how.value)
        if instructions:
            steps.append({'stepNumber': 1, 'title': 'How to apply — as the notice states it',
                          'portalUrl': portal, 'instructions': instructions,
                          'mandatoryFields': [], 'commonMistakesToAvoid': [],
                          'provenance': _prov(rec, how, 'how-to-apply') or {}})
    # Photo and signature: the notice's own sentences, from the canonical record. The blank
    # "as stated on the portal" placeholder that used to overwrite them is gone; where the
    # record has no guideline the spec is empty and the UI says the notice sets none.
    psg = rec.get('photoSignatureGuidelines')
    photo_rules: list[str] = []
    sig_rules: list[str] = []
    psg_prov = None
    if psg and psg.usable and isinstance(psg.value, dict):
        photo_rules = list(psg.value.get('photograph') or [])
        sig_rules = list(psg.value.get('signature') or [])
        psg_prov = _prov(rec, psg, 'photo-signature')
    guide: dict = {'officialPortal': portal, 'otrSteps': steps,
                   'photoRules': _upload_spec('Photograph', photo_rules, psg_prov),
                   'signatureRules': _upload_spec('Signature', sig_rules, psg_prov),
                   # No canonical field carries certificate-validity rules or rejection
                   # statistics; a document's *name* says nothing about its validity window,
                   # so nothing is inferred into these.
                   'certificateRules': [], 'rejectionPitfalls': []}
    docs = _required_documents(rec)
    if docs:
        guide['requiredDocuments'] = docs
    fee = _fee_details(rec)
    if fee:
        guide['fee'] = fee
    return guide


def _overview(rec: ExamRecord) -> str:
    bits = [f'{rec.title}, conducted by {rec.authority_name}.']
    count, approximate = _vacancy_count(rec.value('vacancies'))
    if count:
        bits.append(f"The notice states {'approximately ' if approximate else ''}{count} vacancies.")
    # The close that governs: never a superseded one, never one held for review.
    close = next((d for d in (rec.value('dates') or []) if isinstance(d, dict)
                  and d.get('type') == 'APPLICATION_CLOSE' and d.get('status') != 'SUPERSEDED'
                  and not d.get('isTentative')), None)
    if close:
        # A midnight time is where no time was read, not a time the authority printed.
        when = close.get('displayWhen') or re.sub(r'\s+00:00(?::00)?$', '', close.get('dateTimeStr', ''))
        bits.append(f"Applications close {when}.")
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
        if q.get('page'):
            item_prov['pageNumber'] = q['page']
            item_prov['clauseNumber'] = str(q.get('officialClause') or '')
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
        if it.get('page'):
            item_prov['pageNumber'] = it['page']
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


#: A node whose whole name is punctuation, a stray fraction or a bare number is a
#: cell-seam artefact of a flattened PDF ("½", "150", "-"), not a stage or a subject.
_GARBAGE_NODE_RX = re.compile(r'^[\W\d½¼¾⅓⅔⅛\s]*$')


def _garbage_name(name: str) -> bool:
    return not name or bool(_GARBAGE_NODE_RX.match(name))


#: No single stage, paper or section of an Indian recruitment exam sets more than this many
#: questions in one node. A larger count is a merged-cell artefact of a flattened PDF ("2 ½
#: 150" read as 900), so that node's whole numeric cell (its marks and its question count) is
#: withheld rather than published, while its name and structure are kept.
_IMPLAUSIBLE_QUESTIONS = 300


#: Structural pattern fields carried through exactly as the reader produced them.
_PATTERN_PASSTHROUGH = ('questionType', 'sectionalTiming', 'marksPerQuestion', 'negativeMarkPerWrong',
                        'negativeFractionOfMarks', 'durationVariants', 'derived', 'underReview')


#: Derived figures computed from the node's own printed figures (as opposed to a rule stated
#: for its stage and carried down to it).
_FROM_OWN_FIGURES = frozenset({'marksPerQuestion', 'negativeMarkPerWrong'})


def _pattern_node(n: dict, prov: dict, withheld: Optional[list] = None) -> Optional[dict]:
    """One extracted pattern node -> ExamPatternNode. Only what the reader printed is carried;
    a value it did not read is omitted, not guessed. A node whose name is only a cell seam
    ("½") is dropped, and an implausible question count -- the signature of a merged cell in a
    flattened table -- withholds that node's numbers instead of asserting them. Every
    withheld figure and dropped node is recorded in `withheld` (the materialization ledger),
    so nothing leaves the record without a stated reason."""
    name = str(n.get('name') or n.get('title') or '').strip()
    if _garbage_name(name):
        if withheld is not None:
            withheld.append({'node': name or '(blank)', 'fields': ['node'],
                             'reason': 'the node name is a cell seam of a flattened table, not a stage, paper or subject'})
        return None
    label = str(n.get('levelLabel') or n.get('level') or '')
    # The structural level decides what a node is; the label is only the authority's word for
    # it. Reading the level from the label made one authority's "Tier" stages OTHER, so its
    # exam had no stages at all -- because another authority happens to say "Stage".
    structural = str(n.get('level') or '').upper()
    level = (structural if structural in _PATTERN_LEVELS
             else label.upper() if label.upper() in _PATTERN_LEVELS else 'OTHER')
    node: dict = {'id': str(n.get('id') or ''), 'level': level, 'levelLabel': label or None,
                  'name': name, 'status': str(n.get('status') or 'VERIFIED'),
                  'provenance': n.get('provenance') or prov}
    if n.get('code'):
        node['code'] = str(n['code'])
    if n.get('order') is not None:
        node['order'] = n['order']
    marks = n.get('marks', n.get('totalMarks'))
    qs = n.get('questions', n.get('totalQuestions'))
    # A figure is withheld when the reader itself is unsure of it (the node is NEEDS_REVIEW,
    # e.g. "2 figures where the table declares 1 numeric column" -- which is how a year in a
    # subject's name, "1757", was read as 1757 marks), or when a question count is
    # impossibly large (the signature of a merged cell in a flattened table). The node, its
    # name and its structure are still carried; only the unreliable number is held back.
    implausible = isinstance(qs, (int, float)) and qs > _IMPLAUSIBLE_QUESTIONS
    unreliable = str(n.get('status') or 'VERIFIED') == 'NEEDS_REVIEW' or implausible
    dur = n.get('durationMinutes')
    if not isinstance(dur, (int, float)):
        dur = _minutes(n.get('duration'))
    figures = {'marks': marks, 'questions': qs, 'durationMinutes': dur}
    present = {k: v for k, v in figures.items() if isinstance(v, (int, float))}
    if unreliable and present and withheld is not None:
        withheld.append({'node': name, 'fields': sorted(present), 'values': present,
                         'reason': ('an impossibly large question count, the signature of a merged cell'
                                    if implausible else
                                    'the reader could not establish which column this figure belongs to')})
    if not unreliable:
        if 'marks' in present:
            node['marks'] = present['marks']
        if 'questions' in present:
            node['questions'] = present['questions']
        if 'durationMinutes' in present:
            node['durationMinutes'] = int(present['durationMinutes'])
    if n.get('negativeMarking'):
        node['negativeMarking'] = str(n['negativeMarking'])
    if n.get('mode'):
        node['mode'] = str(n['mode'])
    if isinstance(n.get('languages'), list) and n['languages']:
        node['languages'] = [str(x) for x in n['languages']][:8]
    q = n.get('qualifying')
    if isinstance(q, dict) and q:
        node['qualifying'] = {k: q[k] for k in ('asPrinted', 'qualifyingOnly', 'countsTowardsMerit',
                                                'minimumMarks', 'minimumPercent', 'byCategory') if k in q}
    for k in _PATTERN_PASSTHROUGH:
        if n.get(k) not in (None, '', [], {}):
            if unreliable and k in _FROM_OWN_FIGURES and k in (n.get('derived') or []):
                # Computed from this node's own figures, which were just withheld: a quotient of
                # two figures nobody could vouch for is not a figure either.
                if withheld is not None:
                    withheld.append({'node': name, 'fields': [k], 'values': {k: n[k]},
                                     'reason': 'computed from figures of this node that were withheld'})
                continue
            node[k] = n[k]
    if isinstance(node.get('derived'), list):
        # Name only the derived figures actually published on this node.
        kept = [k for k in node['derived'] if k in node]
        if kept:
            node['derived'] = kept
        else:
            node.pop('derived')
    if n.get('note'):
        node['note'] = str(n['note'])
    children = n.get('children')
    if isinstance(children, list) and children:
        kids = [k for k in (_pattern_node(c, prov, withheld) for c in children if isinstance(c, dict)) if k]
        if kids:
            node['children'] = kids
    return {k: v for k, v in node.items() if v is not None}


def _paper_row_node(row: dict, i: int, negative: str = '') -> dict:
    """A flat paper row ("Paper-I · Civil Engineering · 150 marks · 150 minutes") as a PAPER node.

    Two readers produce rows rather than a tree: the semantic reader (`{'papers': [...]}`) and
    the legacy prose reader (a list of `{paper, name, marks, duration}`). The row's own label is
    its code and part of its name; nothing is added that the row did not print."""
    label = _clean(row.get('label') or row.get('paper'), 40)
    name = _clean(row.get('name'), 160).rstrip(' (-:—–')
    node = {'id': f'paper-row-{i}', 'level': 'PAPER', 'levelLabel': 'Paper',
            'name': f'{label} — {name}' if label and name else (name or label),
            'code': label, 'status': str(row.get('status') or 'VERIFIED')}
    for key in ('marks', 'questions'):
        if isinstance(row.get(key), (int, float)):
            node[key] = row[key]
    if row.get('duration'):
        node['duration'] = row['duration']
    if negative:
        node['negativeMarking'] = negative
        node['derived'] = ['negativeMarking']      # stated once for the scheme, shown on each paper
    return node


def _pattern_input(value: Any) -> tuple[list[dict], Optional[str]]:
    """Every shape a pattern reader produces, as a list of nodes -- or a reason it has none.

    tree nodes (level / levelLabel / children)   carried as they are
    {'papers': [rows], 'negativeMarking': ...}  one PAPER node per row (semantic reader)
    [rows with 'paper' or 'label']              one PAPER node per row (legacy reader)"""
    if isinstance(value, dict):
        rows = [r for r in (value.get('papers') or []) if isinstance(r, dict)]
        negative = _clean(value.get('negativeMarking'), 200)
        if rows:
            return [_paper_row_node(r, i, negative) for i, r in enumerate(rows)], None
        return [], ('the scheme states a rule (' + negative + ') but no paper rows' if negative
                    else 'the reading carries no stage, paper or section to show')
    if isinstance(value, list):
        nodes = [n for n in value if isinstance(n, dict)]
        if nodes and all(('level' not in n and 'levelLabel' not in n and 'children' not in n)
                         and ('paper' in n or 'label' in n) for n in nodes):
            return [_paper_row_node(r, i) for i, r in enumerate(nodes)], None
        return nodes, None
    return [], 'the reading is not a pattern structure'


def _pattern_tree(rec: ExamRecord, withheld: Optional[list] = None, held: Optional[dict] = None) -> list[dict]:
    f = rec.get('examPattern')
    if not (f and f.usable):
        return []
    prov = _prov(rec, f, 'pattern') or {}
    nodes, why_none = _pattern_input(f.value)
    tree = [node for node in (_pattern_node(n, prov, withheld) for n in nodes) if node]
    if not tree and held is not None:
        held['examPattern'] = {'reason': why_none or 'every node read was a cell seam, not a stage or paper',
                               'items': [f.value]}
    return tree


def _syllabus_tree(rec: ExamRecord) -> list[dict]:
    """The syllabus reader already emits ExamSyllabusNode-shaped nodes (id, title, levelLabel,
    order, status, provenance, children); they are carried through as read."""
    f = rec.get('syllabus')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    tree = json.loads(json.dumps([n for n in f.value if isinstance(n, dict) and n.get('title')], default=str))
    _unique_node_ids(tree)
    return tree


def _unique_node_ids(tree: list[dict]) -> None:
    """Qualify a repeated node id by its parent's, as `syllabus._make_ids_unique` does.

    A record stored before extraction made ids unique can repeat one (each paper's clauses
    numbered from "1." again). The first node keeps its id; content is never touched."""
    seen: set = set()

    def visit(node: dict, parent_id: str) -> None:
        node_id = str(node.get('id') or '')
        if node_id and node_id in seen and parent_id:
            base = f'{parent_id}-{node_id.rsplit("-", 1)[-1]}'
            node_id, n = base, 2
            while node_id in seen:
                node_id, n = f'{base}-{n}', n + 1
            node['id'] = node_id
            if isinstance(node.get('provenance'), dict):
                node['provenance']['id'] = f'prov-{node_id}'
        seen.add(node_id)
        for child in node.get('children') or []:
            if isinstance(child, dict):
                visit(child, node_id)

    for root in tree:
        if isinstance(root, dict):
            visit(root, '')


def _slugify(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')[:48] or 'x'


def _subject_label(title: str) -> str:
    t = re.sub(r'\s+', ' ', (title or '').strip())
    return (t[:58] + '…') if len(t) > 60 else (t or 'Syllabus')


def flat_syllabus_from_tree(tree: list[dict]) -> list[dict]:
    """Project the syllabus tree into the flat SyllabusTopic[] the tree map, the topic
    checklist and the weightage view read (`exam.syllabus`). The tree stays the source of
    record (`exam.syllabusTree`); this is the same content in the shape those views need.

    Subject = the root heading it sits under; a node whose children are all leaves becomes a
    topic carrying those leaves as subtopics; a deeper branch recurses. Nothing is weighted,
    because the authority printed no weightage: weightagePercentage/avgQuestions are 0 and
    isHighYield is false -- honest zeros, never invented emphasis."""
    topics: list[dict] = []
    counter = [0]

    def add(node: dict, subject: str, subtopics: list[str]) -> None:
        title = re.sub(r'\s+', ' ', str(node.get('title') or '').strip())
        if _garbage_name(title):
            return
        counter[0] += 1
        subs = [re.sub(r'\s+', ' ', str(s).strip()) for s in subtopics]
        subs = [s for s in subs if s and not _garbage_name(s)][:40]
        topics.append({
            'id': f'syltopic-{counter[0]}-{_slugify(title)}',
            'subject': subject, 'tier': 'BOTH', 'topicName': title[:220],
            'subtopics': subs, 'weightagePercentage': 0, 'avgQuestions': 0,
            'isHighYield': False,
            'officialProvenance': node.get('provenance') or {},
        })

    def walk(node: dict, subject: str) -> None:
        children = [c for c in (node.get('children') or []) if isinstance(c, dict)]
        branches = [c for c in children if c.get('children')]
        leaves = [c for c in children if not c.get('children')]
        if not children:
            add(node, subject, [])
        elif not branches:
            add(node, subject, [str(c.get('title') or '') for c in leaves])
        else:
            for c in leaves:
                add(c, subject, [])
            for c in branches:
                walk(c, subject)

    for root in tree:
        if not isinstance(root, dict):
            continue
        children = [c for c in (root.get('children') or []) if isinstance(c, dict)]
        if children and _BARE_SYLLABUS_TITLE.match(str(root.get('title') or '')):
            # A root that is only the word "Syllabus" names no subject. Its parts do: each
            # paper, or each paper of a stage. Taking the root's word made every topic of one
            # exam's syllabus a topic of "SYLLABUS" -- one branch on the tree map, and bare
            # "Section-I" topics that had lost the paper they belong to.
            for part in children:
                grand = [g for g in (part.get('children') or []) if isinstance(g, dict)]
                papers = grand if part.get('levelLabel') == 'Stage' and grand else [part]
                for paper in papers:
                    subject = _subject_label(paper.get('title'))
                    kids = [k for k in (paper.get('children') or []) if isinstance(k, dict)]
                    if not kids:
                        add(paper, subject, [])
                    for k in kids:
                        walk(k, subject)
            continue
        subject = _subject_label(root.get('title'))
        if not children:
            add(root, subject, [])
        else:
            for c in children:
                walk(c, subject)
    return topics[:200]


#: A syllabus root whose title is only the word for a syllabus.
_BARE_SYLLABUS_TITLE = re.compile(r'^\s*(?:detailed\s+)?(?:syllabus|syllabi)\s*[:.]?\s*$', re.I)


# ------------------------------------------------------------------ lifecycle projections
def _event_list(rec: ExamRecord, name: str, suffix: str) -> list[dict]:
    """A canonical field whose value is already a list of frontend-shaped events (the readers
    project through `compat.*`). Each event keeps its own identity and provenance; one without
    provenance inherits the field's citation rather than going unsourced. Never collapsed."""
    f = rec.get(name)
    if not (f and f.usable):
        return []
    items = f.value if isinstance(f.value, list) else [f.value]
    field_prov = _prov(rec, f, suffix) or {}
    out = []
    for i, e in enumerate(items):
        if not isinstance(e, dict):
            continue
        item = json.loads(json.dumps(e, default=str))
        item.setdefault('id', f'{suffix}-{rec.exam_id}-{i}')
        if not isinstance(item.get('provenance'), dict) or not item['provenance']:
            item['provenance'] = dict(field_prov, id=f"{field_prov.get('id', 'prov')}-{i}")
        out.append(item)
    return out


def _admit_card_events(rec: ExamRecord) -> list[dict]:
    events = []
    for e in _event_list(rec, 'admitCard', 'admit'):
        # The event model is the authoritative shape; a legacy dict-shaped reading (one card
        # with a text) is carried as one event of kind OTHER, in its own words, never as a date.
        if 'kind' not in e or 'officialLabel' not in e:
            e = {'id': e['id'], 'examId': rec.exam_id, 'kind': 'OTHER',
                 'officialLabel': _clean(e.get('label') or e.get('title') or 'Admit card', 120),
                 'status': 'VERIFIED' if rec.get('admitCard').ok else 'NEEDS_REVIEW',
                 'instructions': [x for x in [_clean(e.get('text'))] if x],
                 'portalUrl': e.get('portalUrl') or '', 'provenance': e['provenance']}
        e.setdefault('examId', rec.exam_id)
        events.append(e)
    return events


def _official_papers(rec: ExamRecord) -> list[dict]:
    out = []
    for p in _event_list(rec, 'officialPapers', 'paper'):
        if 'identity' not in p or 'url' not in p:
            # A legacy {label: url} catalogue: each entry is a paper whose identity is its label.
            continue
        out.append(p)
    f = rec.get('officialPapers')
    if not out and f and f.usable and isinstance(f.value, dict):
        prov = _prov(rec, f, 'paper') or {}
        for i, (label, url) in enumerate(sorted(f.value.items())):
            title = str(label).split('::', 1)[-1]
            out.append({'id': f'paper-{rec.exam_id}-{i}', 'title': title, 'url': str(url),
                        'identity': {'examId': rec.exam_id, 'describe': title},
                        'status': 'VERIFIED' if f.ok else 'NEEDS_REVIEW',
                        'provenance': dict(prov, id=f"{prov.get('id', 'prov')}-{i}")})
    return out


def _answer_keys(rec: ExamRecord) -> list[dict]:
    return [k for k in _event_list(rec, 'answerKeys', 'key') if 'identity' in k and 'kind' in k]


def _result_declarations(rec: ExamRecord) -> list[dict]:
    return [r for r in _event_list(rec, 'results', 'result') if 'kind' in r and 'label' in r]


def _result_next_steps(rec: ExamRecord) -> list[dict]:
    """GovOS guidance derived from a declared result and the pattern -- never an official fact.

    Every stage carries `isGuidance: True` and the basis it was derived from, so the UI can
    keep it visibly apart from the authority's own declarations above it."""
    f = rec.get('nextSteps')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    prov = _prov(rec, f, 'next-steps') or {}
    if prov:
        prov = dict(prov, taxonomyType='RECOMMENDATION', verificationLevel='UNDER_VERIFICATION')
    out = []
    for g in f.value:
        if not isinstance(g, dict):
            continue
        headline = _clean(g.get('action') or g.get('headline'), 160)
        summary = _clean(g.get('guidance') or g.get('summary'))
        if not (headline or summary):
            continue
        if g.get('source') == 'OFFICIAL_RULE':
            # The authority's own sentence, quoted: an official statement with its own
            # provenance, never folded into the guidance below it.
            out.append({'status': 'AWAITING_RESULT', 'headline': headline or 'Next stage', 'summary': summary,
                        'actions': [], 'isGuidance': False,
                        'basis': f"Stated in {_clean(g.get('documentTitle'), 160)}.",
                        'fromStage': _clean(g.get('fromStage'), 80), 'nextStage': _clean(g.get('nextStage'), 80),
                        'provenance': dict(_prov(rec, f, 'next-steps-official') or {},
                                           documentTitle=g.get('documentTitle', ''),
                                           officialUrl=g.get('documentUrl', ''),
                                           pageNumber=g.get('page') or 1,
                                           excerptText=g.get('evidenceSpan', ''),
                                           taxonomyType='FACT', verificationLevel='OFFICIALLY_VERIFIED')})
            continue
        own = prov
        if prov and g.get('documentUrl'):
            # The declaration this step was derived from, not whatever the field cites first.
            own = dict(prov, documentTitle=g.get('documentTitle', ''), officialUrl=g.get('documentUrl', ''),
                       **({'pageNumber': g['basisPage'], 'clauseNumber': g.get('basisClause', ''),
                           'excerptText': g.get('basisExcerpt', '')} if g.get('basisPage') else {}))
        out.append({'status': 'AWAITING_RESULT', 'headline': headline or 'Next step', 'summary': summary,
                    'actions': [], 'isGuidance': True,
                    'basis': ('Derived by GovOS from '
                              + (f"the declared result for {_clean(g.get('fromStage'), 80)}" if g.get('fromStage')
                                 else 'the official lifecycle') + ' and the exam pattern; not an official statement.'),
                    'fromStage': _clean(g.get('fromStage'), 80), 'nextStage': _clean(g.get('nextStage'), 80),
                    'provenance': own})
    return out


class _NoModel:
    """Materialization never calls a model: the guidance it carries is the deterministic order
    over verified topics, so a registration cannot depend on, or be changed by, a model reply."""
    name = 'none'

    def is_enabled(self) -> bool:
        return False


def _study_guidance(rec: ExamRecord, syllabus: list[dict]) -> Optional[dict]:
    """GOVOS_GUIDANCE: a suggested order over the exam's verified syllabus topics, and nothing
    else -- no durations, no daily hours, no topic that is not in the syllabus. Absent where
    the syllabus is not verified."""
    f = rec.get('syllabus')
    if not (f and f.ok and syllabus):
        return None
    from .verification.roadmap_guidance import generate
    g = generate(rec.exam_id, syllabus, authority=rec.authority_name, exam_label=rec.title,
                 provider=_NoModel())
    if not g.available:
        return None
    out = g.as_dict()
    out['basis'] = ('Ordered from the ' + str(len(syllabus)) + ' syllabus topics read from '
                    + rec.authority_name + "'s own documents; no topic is added.")
    return out


def _cutoffs(rec: ExamRecord) -> list[dict]:
    """Cut-offs exactly as a reader recorded them: year, stage, category, post, value, type.

    `tier1Cutoff` is filled only where the record itself says the figure is the first stage's;
    otherwise the value travels in `value` with its own `stage`, because relabelling a Mains or
    a final cut-off as "Tier 1" would misstate it."""
    f = rec.get('cutoffs')
    if not (f and f.usable and isinstance(f.value, list)):
        return []
    prov = _prov(rec, f, 'cutoffs') or {}
    out = []
    for i, c in enumerate(f.value):
        if not isinstance(c, dict):
            continue
        raw = c.get('value', c.get('cutoffMarks', c.get('marks', c.get('tier1Cutoff'))))
        try:
            value = float(raw)
        except (TypeError, ValueError):
            continue
        try:
            year = int(str(c.get('year') or '')[:4])
        except ValueError:
            continue
        entry = {'year': year, 'category': _clean(c.get('category'), 80) or 'Not stated',
                 'value': value, 'stage': _clean(c.get('stage'), 80), 'post': _clean(c.get('post'), 160),
                 'cutoffType': _clean(c.get('cutoffType') or c.get('type'), 60),
                 'provenance': (c['provenance'] if isinstance(c.get('provenance'), dict) and c['provenance']
                                else dict(prov, id=f"{prov.get('id', 'prov')}-{i}"))}
        if 'tier1Cutoff' in c:
            entry['tier1Cutoff'] = float(c['tier1Cutoff'])
        if 'tier2Cutoff' in c:
            entry['tier2Cutoff'] = float(c['tier2Cutoff'])
        if c.get('postsEligible'):
            entry['postsEligible'] = _clean(c['postsEligible'], 200)
        out.append(entry)
    return out


def _age_relaxations(rec: ExamRecord) -> list[dict]:
    """Relaxations the notice itself printed, carried in the canonical ageLimits value.

    Nothing is supplied from a national default: no printed relaxation, no entry."""
    f = rec.get('ageLimits')
    if not (f and f.usable and isinstance(f.value, dict)):
        return []
    prov = _prov(rec, f, 'age-relaxation') or {}
    out = []
    for i, r in enumerate(f.value.get('relaxations') or []):
        if not isinstance(r, dict) or not _clean(r.get('category')):
            continue
        years, maximum = r.get('years'), r.get('maximumAge')
        if not isinstance(years, (int, float)) and not isinstance(maximum, (int, float))                 and not (r.get('status') == 'NEEDS_REVIEW' and r.get('condition')):
            continue      # a relaxation with no figure and no stated rule carries nothing
        # A rule with no figure, or a qualified figure, is shown as the notice's words and
        # held for review: the eligibility engine adds only VERIFIED figures to a limit.
        entry = {'category': _clean(r.get('category'), 160),
                 'status': 'VERIFIED' if (f.ok and r.get('status', 'VERIFIED') == 'VERIFIED') else 'NEEDS_REVIEW',
                 'provenance': dict(prov, id=f"{prov.get('id', 'prov')}-{i}",
                                    **({'excerptText': _clean(r.get('evidenceSpan'))} if r.get('evidenceSpan') else {}))}
        if isinstance(years, (int, float)):
            entry['years'] = years
        if isinstance(maximum, (int, float)):
            entry['maximumAge'] = maximum
        if r.get('condition'):
            entry['condition'] = _clean(r['condition'], 300)
        if r.get('appliesToPostId'):
            entry['appliesToPostId'] = str(r['appliesToPostId'])
        out.append(entry)
    return out


def stages_from_pattern(tree: list[dict]) -> list[dict]:
    """The legacy `stages` projection of an authoritative pattern tree.

    One ExamStage per root node the tree itself labels a STAGE -- none is guessed from a
    paper, a section or a heading. A stage's figures are carried only where the tree carries
    them; an unstated figure is 0 *and* named in `unstatedFields`, so a consumer that prints
    it can say "not stated" instead of "0 marks"."""
    stages = []
    for node in tree:
        if not isinstance(node, dict) or node.get('level') != 'STAGE':
            continue
        unstated = [k for k, src in (('durationMinutes', 'durationMinutes'), ('totalQuestions', 'questions'),
                                     ('totalMarks', 'marks')) if not isinstance(node.get(src), (int, float))]
        sections = []
        for ch in node.get('children') or []:
            if not isinstance(ch, dict) or not ch.get('name'):
                continue
            sections.append({'sectionName': ch['name'],
                             'modules': [g['name'] for g in (ch.get('children') or []) if isinstance(g, dict) and g.get('name')][:20],
                             'questions': ch.get('questions') if isinstance(ch.get('questions'), (int, float)) else 0,
                             'marks': ch.get('marks') if isinstance(ch.get('marks'), (int, float)) else 0,
                             'durationMinutes': ch.get('durationMinutes') if isinstance(ch.get('durationMinutes'), (int, float)) else 0,
                             'negativeMarking': ch.get('negativeMarking') or ''})
        qualifying = node.get('qualifying') or {}
        stages.append({
            'id': node.get('id') or f'stage-{len(stages) + 1}',
            'stageNumber': len(stages) + 1,
            'stageName': node['name'],
            'tier': node.get('code') or node.get('levelLabel') or f'Stage {len(stages) + 1}',
            'durationMinutes': node.get('durationMinutes') if isinstance(node.get('durationMinutes'), (int, float)) else 0,
            'totalQuestions': node.get('questions') if isinstance(node.get('questions'), (int, float)) else 0,
            'totalMarks': node.get('marks') if isinstance(node.get('marks'), (int, float)) else 0,
            'negativeMarking': node.get('negativeMarking') or '',
            'mode': node.get('mode') or '',
            'qualifyingNature': qualifying.get('asPrinted') or '',
            'sections': sections,
            'unstatedFields': unstated,
            'derivedFrom': 'patternTree',
            'provenance': node.get('provenance') or {},
        })
    return stages


#: Sections whose content GovOS would *derive* (guidance, practice), mapped to the runtime key that
#: would carry it. The canonical report can say such a section is derivable ("supported and
#: projected"); if the runtime carries nothing for it, the student must be told it has not been
#: generated -- never that it exists.
_DERIVED_SECTION_CONTENT = {'roadmap': ('roadmapTracks', 'studyGuidance'),
                            'mock-tests': ('practiceQuestions',)}


def _section_states(report: Optional[ExamCompletenessReport], held: Optional[dict] = None,
                    runtime: Optional[dict] = None) -> dict:
    """The 17 completeness states, carried as metadata so the UI can tell an honest absence from
    an unpublished one — never rendered as raw enum text (that translation is a UI boundary).

    The canonical report describes the record; materialization can hold a reading back (a
    document list that is not a list of posts). A section containing a wholly held field is
    reported as under review, so the runtime state describes what the student actually sees."""
    if report is None:
        return {}
    held = held or {}
    out = {}
    for s in report.sections:
        state, summary = s.state.value, s.student_status_summary
        fields = getattr(s, 'fields', {}) or {}
        wholly_held = [f for f in fields if f in held and not held[f].get('partial')]
        if wholly_held and state == 'VERIFIED_AVAILABLE':
            state = 'NEEDS_REVIEW'
            summary = ('Part of this section was read from the notice but is held for review before it '
                       'is shown: ' + ', '.join(wholly_held) + '.')
        key = _DERIVED_SECTION_CONTENT.get(s.section_id)
        # A derived section is GovOS's to generate, so it is never "not published by the
        # authority": with no content it is NOT_YET_GENERATED, and where its input (the pattern)
        # is not verified the summary says that is why.
        if key and runtime is not None and not any(runtime.get(k) for k in key) and state in (
                'SUPPORTED_AND_PROJECTED', 'RUNTIME_DERIVED', 'NOT_YET_PUBLISHED'):
            waiting = not runtime.get('patternTree')
            state = 'NOT_YET_GENERATED'
            summary = ('GovOS guidance for this section has not been generated yet. It would be GovOS '
                       'guidance built from the verified pattern and syllabus, never an official statement.'
                       + (' It needs a verified examination pattern first, and the pattern read from the '
                          'notice is under review.' if waiting else ''))
        out[s.section_id] = {'state': state, 'nature': s.nature.value, 'studentStatusSummary': summary,
                             'sectionNum': s.section_num, 'isApplicable': s.is_applicable}
    return out


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
    held: dict[str, dict] = {}                       # field -> reasoned disposition (the ledger)
    pattern_withheld: list[dict] = []

    posts, no_group, held_posts = _posts(rec)
    if held_posts:
        held['posts'] = {'reason': 'candidate(s) read as documents or certificates, not posts; held for review '
                                   'with their evidence rather than published as posts',
                         'items': held_posts, 'partial': bool(posts)}
    age = rec.value('ageLimits') or {}
    vac = rec.get('vacancies')
    vacancies_total = ''
    if vac and vac.ok and vac.value not in (None, ''):
        vacancies_total = _vacancy_count(vac.value)[0]
    elif vac and vac.status is Status.NEEDS_REVIEW and vac.value not in (None, ''):
        held['vacancies'] = {'reason': vac.note or 'the vacancy figure is not established', 'items': [vac.value]}

    pattern_tree = _pattern_tree(rec, pattern_withheld, held)
    syllabus_tree = _syllabus_tree(rec)
    exam: dict = {
        'id': rec.exam_id, 'code': rec.code, 'title': rec.title,
        'authorityName': rec.authority_name, 'officialDomain': rec.official_domain,
        # The date age is reckoned on, only as the notice printed it. Never a default: an
        # exam without one is shown as "not stated", and eligibility is not evaluated.
        'crucialEligibilityDate': str((age.get('asOn') if isinstance(age, dict) else '') or ''),
        'isGoldenJourney': False, 'isDemoData': False,
        'overviewDescription': _overview(rec),
        'vacanciesTotal': vacancies_total,
        'posts': posts, 'dates': _dates(rec),
        'globalRuleGroup': {'id': f'rules-{rec.exam_id}', 'operator': 'AND', 'rules': []},
        # Compatibility projections of the authoritative trees (see PROJECTION_MAP).
        'stages': stages_from_pattern(pattern_tree),
        'syllabus': flat_syllabus_from_tree(syllabus_tree) if syllabus_tree else [],
        # No canonical field supplies practice questions or an official roadmap. These stay
        # empty, and the sections say so; nothing is generated to fill them.
        'practiceQuestions': [], 'roadmapTracks': [],
        'corrigendums': _corrigendums(rec), 'cutoffsHistory': _cutoffs(rec),
        'resources': _resources(rec), 'faqs': _faqs(rec),
        'applicationGuide': _application_guide(rec),
        'eligibilityHighlights': _eligibility_highlights(rec),
        'officialLinks': _official_links(rec),
        'origin': 'MACHINE_ACQUIRED',
        'cycle': cycle,
    }
    guidance = _study_guidance(rec, exam['syllabus'])
    if guidance:
        exam['studyGuidance'] = guidance
    for key, value in (('patternTree', pattern_tree), ('syllabusTree', syllabus_tree),
                       ('examDayChecklist', _exam_day(rec)), ('admitCardEvents', _admit_card_events(rec)),
                       ('officialPapers', _official_papers(rec)), ('answerKeys', _answer_keys(rec)),
                       ('resultDeclarations', _result_declarations(rec)),
                       ('resultNextSteps', _result_next_steps(rec)),
                       ('ageRelaxations', _age_relaxations(rec)),
                       ('vacancyBreakups', _vacancy_breakups(rec))):
        if value:
            exam[key] = value
    if pattern_withheld and pattern_tree:
        held['examPattern'] = {'reason': 'figures the reader could not tie to a column were withheld; '
                                         'the stages, papers and subjects are published',
                               'items': pattern_withheld, 'partial': True}
    _attach_evidence(rec, exam, vac)
    exam['sectionStates'] = _section_states(completeness, held, exam)
    exam['materialization'] = {
        'version': MATERIALIZER_VERSION,
        'generatedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'gateDecision': gate.decision.value if gate else None,
        'postsWithoutPrintedGroup': no_group,
        'heldForReview': held,
    }
    return exam


def _attach_evidence(rec: ExamRecord, exam: dict, vac: Optional[Field]) -> None:
    """Evidence for every published fact that has a source (see runtime_evidence).

    Scalar facts get their field's citation under `factEvidence`; a revision recorded from
    reconciled dates carries that date's evidence, old and new linked; a derived pattern figure
    names its inputs; and every provenance is stamped with its identity, authority and type."""
    facts: dict = {}
    for name, present, field in (
            ('vacanciesTotal', bool(exam.get('vacanciesTotal')), vac),
            ('crucialEligibilityDate', bool(exam.get('crucialEligibilityDate')), rec.get('ageLimits'))):
        p = fact_provenance(present, _prov(rec, field, f'fact-{name}') if field and field.usable else None)
        if p:
            facts[name] = p
    if facts:
        exam['factEvidence'] = facts
    dates = {str(d.get('id')): d for d in exam.get('dates') or []}
    for c in exam.get('corrigendums') or []:
        newer = dates.get(str(c.get('id', ''))[len('rev-'):]) if str(c.get('id', '')).startswith('rev-') else None
        if newer and is_provenance(newer.get('provenance')):
            c['provenance'] = dict(newer['provenance'])
    derive_pattern_evidence(exam.get('patternTree') or [])
    # The practice form, from the same record: every check it runs is a fact above, cited.
    simulator = build_simulator(exam)
    if simulator and isinstance(exam.get('applicationGuide'), dict):
        exam['applicationGuide']['simulator'] = simulator
    stamp_exam(exam)


def _official_links(rec: ExamRecord) -> list[dict]:
    # The authority's own site is where it was resolved to, not a statement in a document, so it
    # carries no evidence record. A portal carries the notice clause that names it; an exam page
    # is its own evidence, identified as this exam by its own text.
    links = [{'title': f'{rec.authority_name} — official website', 'url': rec.official_domain,
              'note': 'The authority’s own site.'}]
    portal, portal_note = _portal_link(rec)
    portal_field = rec.get('applicationPortal')
    portal_prov = _prov(rec, portal_field, 'portal') if portal_field and portal_field.ok else None
    if portal.startswith('http') and portal.rstrip('/') != rec.official_domain.rstrip('/'):
        links.append({'title': 'Online application portal', 'url': portal,
                      'note': 'Where the notice sends candidates to apply.',
                      **({'provenance': portal_prov} if portal_prov else {})})
    elif portal_note:
        # The printed portal is off the authority's estate; the site link above serves, and
        # the notice's own address is still stated where a candidate will look for it.
        links.append({'title': 'Application portal named in the notice', 'url': portal,
                      'note': portal_note, **({'provenance': portal_prov} if portal_prov else {})})
    # The authority's own page for this recruitment, where the build found one and its own
    # text identified it as this exam (a listing page contributes only its matching row).
    official = rec.get('officialSources')
    if official and official.usable and isinstance(official.value, list):
        seen = {l['url'] for l in links}
        for s in official.value:
            url = str((s or {}).get('url') or '')
            if (isinstance(s, dict) and s.get('kind') in ('EXAM_PAGE', 'ADMIT_CARD')
                    and s.get('identity') == 'MATCH' and url.startswith('http') and url not in seen
                    and not re.search(r'\.pdf$|/preview/', url, re.I)):
                seen.add(url)
                note = ('The authority’s own page listing this recruitment and its dates.'
                        if s.get('kind') == 'EXAM_PAGE' else
                        'The authority’s own hall-ticket service; this recruitment is among those it serves. '
                        'Each candidate’s hall ticket is served through it, not published as a file.')
                title = _clean(s.get('title') or 'Examination page', 120)
                links.append({'title': title, 'url': url, 'note': note, 'provenance': {
                    'id': f'prov-{rec.exam_id}-link-{len(links)}', 'documentTitle': title,
                    'officialUrl': url, 'pageNumber': None,
                    'clauseNumber': 'The authority’s own page, identified as this recruitment by its own text',
                    'publishedDate': '', 'verifiedDate': official.citation.verified_date if official.citation else '',
                    'verifiedBy': 'GovOS exam builder — read from the source',
                    'taxonomyType': 'FACT', 'verificationLevel': 'OFFICIALLY_VERIFIED',
                    'excerptText': title}})
    return links


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

    #: Every version a re-registration replaced, kept whole: what candidates were shown, the
    #: canonical record it came from, and when it stopped being current. Nothing is deleted.
    HISTORY_DDL = '''
        CREATE TABLE IF NOT EXISTS exam_registry_history (
            exam_id TEXT NOT NULL,
            cycle TEXT NOT NULL,
            version INTEGER NOT NULL,
            gate_decision TEXT NOT NULL,
            exam_json TEXT NOT NULL,
            record_json TEXT NOT NULL,
            completeness_json TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            superseded_at TEXT NOT NULL,
            PRIMARY KEY (exam_id, cycle, version)
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
        c.execute(self.HISTORY_DDL)
        c.commit()
        self._release(c)

    # -- history ----------------------------------------------------------------------------
    def history(self, exam_id: str, cycle: str) -> list[dict]:
        """Every superseded version of one exam and cycle, oldest first."""
        c = self._conn()
        rows = c.execute('SELECT * FROM exam_registry_history WHERE exam_id = ? AND cycle = ? '
                         'ORDER BY version', (exam_id, cycle)).fetchall()
        self._release(c)
        return [{'version': r['version'], 'gateDecision': r['gate_decision'],
                 'exam': json.loads(r['exam_json']), 'record': json.loads(r['record_json']),
                 'completeness': json.loads(r['completeness_json']) if r['completeness_json'] else None,
                 'createdAt': r['created_at'], 'updatedAt': r['updated_at'],
                 'supersededAt': r['superseded_at']} for r in rows]

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
        # The second publication layer: a hollow runtime object never reaches candidates, on
        # any path into the registry, whatever the canonical gate said about the record.
        losses = validate_projection(rec, exam)
        if losses:
            raise MaterializationLoss('canonical facts were lost in materialization: ' + '; '.join(losses[:6]))
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
        row = c.execute('SELECT * FROM exam_registry WHERE exam_id = ? AND cycle = ?',
                        (rec.exam_id, cycle)).fetchone()
        version = (row['version'] + 1) if row else 1
        created = row['created_at'] if row else now
        if row is not None:
            # The version being replaced is archived first, in the same transaction, so a
            # re-registration can never lose what candidates were shown before.
            c.execute('''INSERT OR IGNORE INTO exam_registry_history
                         (exam_id, cycle, version, gate_decision, exam_json, record_json,
                          completeness_json, created_at, updated_at, superseded_at)
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                      (row['exam_id'], row['cycle'], row['version'], row['gate_decision'],
                       row['exam_json'], row['record_json'], row['completeness_json'],
                       row['created_at'], row['updated_at'], now))
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
    PROJECTION_LOSS = 'PROJECTION_LOSS'                   # a canonical FOUND fact did not survive into runtime
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

        build_exam("<an authored exam>", 2027)  ·  build_exam("Any Unknown Board Exam", 2028)

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
    return _materialize_and_publish(out, rec, gate=res.gate, completeness=getattr(br, 'completeness', None),
                                    cycle=cycle, registry=registry, data_ts=data_ts)


def _materialize_and_publish(out: EngineBuildResult, rec: ExamRecord, *, gate: GateReport,
                             completeness: Optional[ExamCompletenessReport], cycle: str,
                             registry: Optional[ExamRegistry], data_ts: str) -> EngineBuildResult:
    """canonical gate PASS -> materialize -> runtime contract -> projection -> register.

    Shared by a fresh build and by re-materializing a stored canonical record, so the two
    cannot drift: each failing layer keeps its own state and registers nothing."""
    exam = materialize_exam(rec, cycle=cycle, completeness=completeness, gate=gate)
    errors = validate_runtime_exam(exam)
    losses = validate_projection(rec, exam) if not errors else []
    out.materialization = {'ok': not errors and not losses, 'errors': errors, 'projectionLosses': losses,
                           'version': MATERIALIZER_VERSION,
                           'postsWithoutPrintedGroup': exam['materialization']['postsWithoutPrintedGroup'],
                           'heldForReview': exam['materialization']['heldForReview']}
    out.gate = dict(out.gate or {}, runtimeDecision='PASS' if not errors and not losses else 'BLOCK')
    if errors:
        out.state = EngineState.MATERIALIZATION_INVALID
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = 'gate PASS, but the materialized exam fails the frontend contract: ' + '; '.join(errors[:4])
        return out
    if losses:
        out.state = EngineState.PROJECTION_LOSS
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = ('gate PASS on the canonical record, but materialization lost verified facts, so '
                      'nothing was published: ' + '; '.join(losses[:4]))
        return out
    out.exam = exam

    registry = registry or ExamRegistry()
    try:
        rr = registry.register(rec, gate=gate, exam=exam, completeness=completeness,
                               cycle=cycle, data_ts=data_ts)
    except MaterializationLoss as exc:
        out.state = EngineState.PROJECTION_LOSS
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = str(exc)
        return out
    except RegistryRejected as exc:
        out.state = EngineState.REGISTRY_REJECTED
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = str(exc)
        return out
    out.state = EngineState.REGISTERED
    out.registry = {'status': 'REGISTERED', 'examId': rr.exam_id, 'cycle': rr.cycle, 'version': rr.version}
    out.reason = (f'gate PASS; {rec.exam_id} (cycle {cycle}) materialized, projection-validated and '
                  f'registered as a runtime exam, version {rr.version}. data.ts untouched.')
    return out


# ------------------------------------------------------------------ re-materialization
def record_from_snapshot(snapshot: dict) -> ExamRecord:
    """Rebuild the canonical ExamRecord a registry row stored (`_record_snapshot`). Exact: every
    field keeps its status, value, note and citation, so re-materializing changes nothing about
    what was read -- only how it is projected."""
    from ..exam_authoring.record import Citation
    rec = ExamRecord(exam_id=snapshot['examId'], code=snapshot['code'], title=snapshot['title'],
                     authority_name=snapshot['authorityName'], official_domain=snapshot['officialDomain'])
    rec.sources_read.extend(snapshot.get('sourcesRead') or [])
    for name, f in (snapshot.get('fields') or {}).items():
        c = f.get('citation')
        rec.set(Field(name=name, status=Status(f['status']), value=f.get('value'),
                      citation=Citation(**c) if isinstance(c, dict) else None, note=f.get('note') or ''))
    return rec


def rematerialize(registry: ExamRegistry, exam_id: str, cycle: Optional[str] = None, *,
                  reviews: Optional[list] = None, target: Optional[ExamRegistry] = None,
                  data_ts: str = P.DATA_TS) -> EngineBuildResult:
    """Re-project a stored canonical record through the current materializer. No acquisition,
    no network: the record is the one the registry already holds.

    Reviews (review.py) may be applied, exactly as on a fresh build. The canonical gate is run
    again over the record as it now stands, then the same runtime and projection layers as a
    fresh build. The completeness report is re-evaluated from the record, keeping the fields
    the original build had searched for and not found."""
    from .completeness import evaluate_completeness
    from .gate import evaluate as gate_evaluate
    from types import SimpleNamespace

    row = registry.get(exam_id, cycle)
    out = EngineBuildResult(query=exam_id, year=str(cycle or ''), state=EngineState.BLOCKED_BY_GATE)
    if row is None:
        out.reason = f'no published registry record for {exam_id}' + (f' cycle {cycle}' if cycle else '')
        out.registry = {'status': 'NOT_REGISTERED'}
        return out
    rec = record_from_snapshot(row.record)
    if reviews:
        from .review import apply_reviews
        out.reviews = apply_reviews(rec, reviews).to_dict()
    searched = frozenset(
        fname for sec in ((row.completeness or {}).get('sections') or [])
        for fname, st in (sec.get('fields') or {}).items() if st == 'SOURCE_NOT_FOUND_AFTER_SEARCH')
    completeness = evaluate_completeness(rec, SimpleNamespace(infrastructure_failed=False),
                                         searched_not_found=searched)
    gate = gate_evaluate(rec, completeness=completeness)
    out.gate = {'decision': gate.decision.value, 'blockers': [str(b) for b in gate.blockers],
                'allowedUnpublished': list(gate.allowed)}
    out.completeness = completeness.to_dict()
    out.resolution = {'examId': rec.exam_id, 'authorityName': rec.authority_name,
                      'authorityDomain': rec.official_domain, 'officialName': rec.title}
    if not gate.may_publish:
        out.registry = {'status': 'NOT_REGISTERED'}
        out.reason = 'the canonical gate did not PASS: ' + '; '.join(str(b) for b in gate.blockers[:4])
        return out
    return _materialize_and_publish(out, rec, gate=gate, completeness=completeness, cycle=row.cycle,
                                    registry=target or registry, data_ts=data_ts)


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
