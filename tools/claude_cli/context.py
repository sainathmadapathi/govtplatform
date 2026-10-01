"""The bounded, server-built factual context behind the candidate-facing assistant.

A candidate's question never carries facts. The server loads the selected exam's own record (the
registry's runtime exam, or the authored register exported at build time), turns it into a short
list of numbered FACTS, each tied to the provenance it already has, and gives Claude only that
list plus the question and a few turns of conversation. Claude may cite fact ids; the server
checks every id it cites exists in the list it supplied (`validate_answer`), that no figure,
link or other exam appears in the answer that is not in the supplied facts, and only then
returns the answer. Anything else is refused and the candidate gets the deterministic assistant.

Nothing here sends the database, the candidate's profile, a file, or another exam to Claude.
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
import threading
from dataclasses import dataclass, field
from typing import Optional

from .schemas import NAVIGATION_TARGETS

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_AUTHORED_PATH = os.path.join(REPO_ROOT, 'exam_data', 'authored_exams.json')

MAX_FACT_CHARS = 20_000
MAX_QUESTION_CHARS = 600
FAQ_ANSWER_CONTEXT_CHARS = 500

_CONTROL = re.compile(r'[\x00-\x08\x0b-\x1f\x7f]')


def clean_text(text: object, limit: int) -> str:
    """Candidate-supplied text, reduced to printable characters and a length limit."""
    s = _CONTROL.sub(' ', str(text or ''))
    return re.sub(r'[ \t]+', ' ', s).strip()[:limit]


# ------------------------------------------------------------------------------ exam store
class ExamStore:
    """Finds an exam record by id: the runtime registry first, then the authored register."""

    def __init__(self, db_path: str, authored_path: Optional[str] = None) -> None:
        self.db_path = db_path
        self.authored_path = authored_path or DEFAULT_AUTHORED_PATH
        self._lock = threading.Lock()
        self._authored: dict = {}
        self._authored_mtime = -1.0

    def _authored_exams(self) -> dict:
        try:
            mtime = os.path.getmtime(self.authored_path)
        except OSError:
            return {}
        with self._lock:
            if mtime != self._authored_mtime:
                try:
                    with open(self.authored_path, encoding='utf-8') as fh:
                        data = json.load(fh)
                    self._authored = {e['id']: e for e in data if isinstance(e, dict) and e.get('id')}
                except (OSError, ValueError):
                    self._authored = {}
                self._authored_mtime = mtime
            return self._authored

    def _registry_exam(self, exam_id: str) -> Optional[dict]:
        try:
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True, timeout=10)
        except sqlite3.Error:
            return None
        try:
            row = conn.execute('SELECT exam_json FROM exam_registry WHERE exam_id=? AND published=1 AND retired=0 '
                               'ORDER BY version DESC LIMIT 1', (exam_id,)).fetchone()
        except sqlite3.Error:
            return None
        finally:
            conn.close()
        if not row:
            return None
        try:
            return json.loads(row[0])
        except (TypeError, ValueError):
            return None

    def get(self, exam_id: str) -> Optional[dict]:
        exam_id = (exam_id or '').strip()
        if not exam_id:
            return None
        return self._registry_exam(exam_id) or self._authored_exams().get(exam_id)

    def other_exam_names(self, exam_id: str) -> list:
        """Distinctive names of every OTHER exam the server knows, for the cross-exam check."""
        names: list = []
        pool = dict(self._authored_exams())
        try:
            conn = sqlite3.connect(f'file:{self.db_path}?mode=ro', uri=True, timeout=10)
            try:
                for (blob,) in conn.execute('SELECT exam_json FROM exam_registry WHERE published=1 AND retired=0'):
                    try:
                        e = json.loads(blob)
                        pool[e['id']] = e
                    except (ValueError, KeyError, TypeError):
                        continue
            finally:
                conn.close()
        except sqlite3.Error:
            pass
        for eid, e in pool.items():
            if eid == exam_id:
                continue
            for n in (e.get('title'), (e.get('code') or '').replace('_', ' ')):
                if n and len(n) >= 6:
                    names.append(str(n))
        return names


# --------------------------------------------------------------------------------- facts
@dataclass
class Fact:
    id: str
    section: str
    label: str
    text: str
    provenance: Optional[dict] = None

    def as_prompt(self) -> dict:
        return {'id': self.id, 'section': self.section, 'label': self.label, 'text': self.text}


@dataclass
class FactSheet:
    exam_id: str
    title: str
    authority: str
    facts: list = field(default_factory=list)
    truncated: bool = False

    @property
    def by_id(self) -> dict:
        return {f.id: f for f in self.facts}

    def corpus(self) -> str:
        """Every word the answer may legitimately use: the facts, the title, the authority."""
        return ' '.join([self.title, self.authority] + [f'{f.label} {f.text}' for f in self.facts])


def _when(d: dict) -> str:
    if d.get('displayWhen'):
        return str(d['displayWhen'])
    raw = str(d.get('dateTimeStr') or '')
    day, _, time_ = raw.partition(' ')
    return day if not time_ or time_.startswith('00:00') else f'{day} {time_[:5]}'


def _short(text: object, limit: int) -> str:
    s = re.sub(r'\s+', ' ', str(text or '')).strip()
    return s if len(s) <= limit else s[:limit].rstrip() + ' […continues in the exam page]'


def _candidates(exam: dict) -> list:
    """Every fact the exam record supports, in a fixed order. (section, label, text, provenance)."""
    out: list = []
    add = lambda sec, label, text, prov=None: out.append((sec, label, str(text), prov)) if str(text).strip() else None

    add('OVERVIEW', 'Exam', f"{exam.get('title')} — {exam.get('authorityName')}")
    if exam.get('cycle'):
        add('OVERVIEW', 'Cycle', exam['cycle'], None)
    if exam.get('vacanciesTotal'):
        add('OVERVIEW', 'Total vacancies', exam['vacanciesTotal'], (exam.get('factEvidence') or {}).get('vacanciesTotal'))
    if exam.get('crucialEligibilityDate'):
        add('ELIGIBILITY', 'Age is reckoned on', exam['crucialEligibilityDate'],
            (exam.get('factEvidence') or {}).get('crucialEligibilityDate'))
    if exam.get('overviewDescription'):
        add('OVERVIEW', 'About', _short(exam['overviewDescription'], 500))

    for d in exam.get('dates') or []:
        state = []
        if d.get('isTentative'):
            state.append('tentative')
        if d.get('status') == 'SUPERSEDED':
            state.append('superseded — no longer the governing date')
        add('DATES', str(d.get('label') or d.get('type')),
            _when(d) + (f" ({', '.join(state)})" if state else ''), d.get('provenance'))

    for h in exam.get('eligibilityHighlights') or []:
        add('ELIGIBILITY', str(h.get('title')), _short(h.get('body'), 600), h.get('provenance'))
    for p in exam.get('posts') or []:
        bits = [str(p.get('postName') or '')]
        if p.get('minAge') is not None and p.get('maxAge') is not None:
            bits.append(f"age {p['minAge']}–{p['maxAge']}")
        if p.get('payScale') or p.get('payLevel'):
            bits.append(f"pay {p.get('payScale') or p.get('payLevel')}")
        if p.get('classification'):
            bits.append(str(p['classification']))
        if p.get('specialQualification'):
            bits.append(_short(p['specialQualification'], 200))
        add('ELIGIBILITY', 'Post', '; '.join(b for b in bits if b), p.get('provenance'))

    fee = (exam.get('applicationGuide') or {}).get('fee') or {}
    for r in fee.get('rules') or []:
        add('APPLICATION', 'Fee', _short(r.get('statedAs') or r.get('scope'), 400),
            r.get('provenance') or fee.get('provenance'))
    if fee.get('acceptedModes'):
        add('APPLICATION', 'Fee payment modes', ', '.join(map(str, fee['acceptedModes'])), fee.get('provenance'))
    portal = (exam.get('applicationGuide') or {}).get('officialPortal')
    if portal:
        add('APPLICATION', 'Official application portal', portal)

    for s in exam.get('stages') or []:
        bits = [str(s.get('stageName') or '')]
        if s.get('totalMarks'):
            bits.append(f"{s['totalMarks']} marks")
        if s.get('durationMinutes'):
            bits.append(f"{s['durationMinutes']} minutes")
        if s.get('negativeMarking'):
            bits.append(f"negative marking: {_short(s['negativeMarking'], 120)}")
        add('PATTERN', 'Stage', '; '.join(b for b in bits if b), s.get('provenance'))

    by_subject: dict = {}
    for t in exam.get('syllabus') or []:
        by_subject.setdefault(t.get('subject') or 'Syllabus', []).append(t)
    for subject, topics in by_subject.items():
        add('SYLLABUS', f'Syllabus: {subject}', _short('; '.join(str(t.get('topicName')) for t in topics), 700),
            (topics[0] or {}).get('officialProvenance'))

    for f in exam.get('faqs') or []:
        add('FAQS', str(f.get('question')), _short(f.get('answer'), FAQ_ANSWER_CONTEXT_CHARS), f.get('provenance'))
    for c in exam.get('corrigendums') or []:
        add('CORRIGENDA', str(c.get('title') or 'Corrigendum'), _short(c.get('diffSummary') or c.get('summary'), 400),
            c.get('provenance'))
    for e in exam.get('admitCardEvents') or []:
        add('ADMIT_CARD', str(e.get('officialLabel') or 'Admit card'),
            _short(e.get('releaseRule') or e.get('releaseRuleNote') or e.get('status'), 300), e.get('provenance'))
    for r in exam.get('resultDeclarations') or []:
        add('RESULTS', str(r.get('label') or r.get('kind')),
            _short(' · '.join(str(x) for x in (r.get('stageLabel'), r.get('nextStep')) if x), 300), r.get('provenance'))
    for i in exam.get('examDayChecklist') or []:
        add('EXAM_DAY', str(i.get('title')), _short(i.get('description'), 400), i.get('provenance'))
    for l in exam.get('officialLinks') or []:
        add('PORTALS', str(l.get('title')), f"{l.get('url')} — {_short(l.get('note'), 160)}")
    cut = exam.get('cutoffsHistory') or []
    if cut:
        add('CUTOFFS', 'Cut-offs on record', f'{len(cut)} published cut-off rows', None)
    return out


_SECTION_CUES = {
    'DATES': ('date', 'when', 'last', 'deadline', 'schedule', 'open', 'close', 'start', 'month'),
    'ELIGIBILITY': ('eligib', 'age', 'qualif', 'degree', 'attempt', 'post', 'relax', 'limit', 'vacanc'),
    'APPLICATION': ('apply', 'application', 'fee', 'document', 'form', 'portal', 'payment'),
    'PATTERN': ('pattern', 'marks', 'paper', 'stage', 'negative', 'duration', 'scheme', 'tier', 'prelim', 'main'),
    'SYLLABUS': ('syllabus', 'topic', 'subject', 'study'),
    'ADMIT_CARD': ('admit', 'hall', 'ticket', 'call letter'),
    'EXAM_DAY': ('exam day', 'carry', 'allowed', 'prohibited', 'rules', 'phone', 'gadget'),
    'RESULTS': ('result', 'merit', 'selected', 'shortlist'),
    'FAQS': ('faq', 'clause', 'objection', 'key', 'debar', 'procedure'),
    'CORRIGENDA': ('corrigendum', 'changed', 'extended', 'revised', 'update'),
    'PORTALS': ('website', 'portal', 'link', 'official site', 'url'),
}
_STOP = frozenset('the and for with what when how who why can are this that have does from about tell give please '
                  'which where will would should could into your you its any exam examination'.split())


def _score(question_words: set, question: str, fact: tuple) -> int:
    section, label, text, _ = fact
    words = set(re.findall(r'[a-z0-9]{3,}', f'{label} {text}'.lower())) - _STOP
    s = len(question_words & words)
    q = question.lower()
    if any(c in q for c in _SECTION_CUES.get(section, ())):
        s += 3
    return s


def build_fact_sheet(exam: dict, question: str = '', *, max_chars: int = MAX_FACT_CHARS) -> FactSheet:
    """The numbered facts Claude may use. Deterministic: the same exam and question always give
    the same sheet. The exam's own core facts are always included; the rest are ranked by their
    relevance to the question and trimmed to the budget."""
    sheet = FactSheet(exam_id=str(exam.get('id') or ''), title=str(exam.get('title') or ''),
                      authority=str(exam.get('authorityName') or ''))
    cands = _candidates(exam)
    qwords = set(re.findall(r'[a-z0-9]{3,}', (question or '').lower())) - _STOP
    core = [i for i, c in enumerate(cands) if c[0] == 'OVERVIEW'][:6]
    ranked = sorted(range(len(cands)), key=lambda i: (i not in core, -_score(qwords, question or '', cands[i]), i))
    chosen: list = []
    used = 0
    for i in ranked:
        cost = len(cands[i][1]) + len(cands[i][2]) + 24
        if used + cost > max_chars:
            sheet.truncated = True
            continue
        chosen.append(i)
        used += cost
    for n, i in enumerate(sorted(chosen), start=1):          # keep the record's own order
        section, label, text, prov = cands[i]
        sheet.facts.append(Fact(id=f'F{n}', section=section, label=label, text=text,
                                provenance=prov if isinstance(prov, dict) else None))
    return sheet


def syllabus_topics(exam: dict) -> list:
    """The verified syllabus topic names of an exam (empty when it has no syllabus)."""
    seen, out = set(), []
    for t in exam.get('syllabus') or []:
        name = re.sub(r'\s+', ' ', str(t.get('topicName') or '')).strip()
        if name and name not in seen:
            seen.add(name)
            out.append(name)
    return out


# ---------------------------------------------------------------------------- validation
_URL = re.compile(r'''https?://[^\s<>"')\]]+''', re.I)
_NUMBER_TOKEN = re.compile(r'\d+(?:[.,]\d+)*')


def _norm_group(group: str) -> str:
    return group.lstrip('0') or '0'


def _figure_groups(text: str) -> set:
    """Every run of digits in `text`, without leading zeros: "2024-03-16" -> {2024, 3, 16}."""
    return {_norm_group(g) for g in re.findall(r'\d+', text)}


def validate_answer(output: dict, sheet: FactSheet, question: str, other_exam_names: list) -> list:
    """Reasons the answer must be refused, or []. Deterministic; Claude has no say in it."""
    problems: list = []
    ids = sheet.by_id
    cited = output.get('cited_fact_ids') or []
    unknown = [c for c in cited if c not in ids]
    if unknown:
        problems.append(f'cites facts that were not supplied: {", ".join(unknown[:4])}')
    if len(set(cited)) != len(cited):
        problems.append('cites the same fact twice')
    basis = output.get('basis')
    if basis == 'VERIFIED_DATA' and not cited:
        problems.append('claims a verified answer but cites no fact')
    if basis == 'NOT_IN_RECORD' and output.get('uncertainty') == 'NONE':
        problems.append('says the record has no answer yet reports no uncertainty')
    if output.get('navigate_to', 'NONE') not in NAVIGATION_TARGETS:
        problems.append('points at a section that does not exist')
    answer = str(output.get('answer') or '')
    if not answer.strip():
        problems.append('the answer is empty')
    answer += ' ' + str(output.get('follow_up') or '')      # the follow-up is shown too: same rules
    allowed_text = (sheet.corpus() + ' ' + question).lower()
    for url in _URL.findall(answer):
        if url.rstrip('.,;').lower() not in allowed_text:
            problems.append('mentions a link that is not in the supplied facts')
            break
    allowed_groups = _figure_groups(allowed_text)
    for token in _NUMBER_TOKEN.findall(answer):
        for group in re.findall(r'\d+', token):
            if len(group) >= 2 and _norm_group(group) not in allowed_groups:
                problems.append(f'states a figure ({group}) that is not in the supplied facts')
                break
        else:
            continue
        break
    low = answer.lower()
    own = sheet.corpus().lower()
    for name in other_exam_names:
        n = name.lower()
        if n in low and n not in own:
            problems.append('mentions another exam')
            break
    return problems


def citations(output: dict, sheet: FactSheet) -> list:
    """The cited facts with their own provenance, for the page to open as Evidence."""
    by_id = sheet.by_id
    out = []
    for fid in output.get('cited_fact_ids') or []:
        f = by_id.get(fid)
        if f is not None:
            out.append({'id': f.id, 'section': f.section, 'label': f.label, 'text': f.text,
                        'provenance': f.provenance})
    return out
