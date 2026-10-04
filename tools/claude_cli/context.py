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
# ------------------------------------------------------------------- is one fact verified?
# The same rule the page applies when it opens a value's Evidence (src/ui.tsx: provenanceIsVerified,
# withClaim, claimInQuote), so an answer's badge and the Evidence panel can never disagree. Both are held
# to one table of cases, tools/claude_cli/fact_verification_cases.json -- change the rule in both or neither.
#
#   VERIFIED            OFFICIALLY_VERIFIED, a source to open (an http(s) URL) and a place in it (a page or
#                       the quoted words), and the quoted words state this fact's own claim
#   UNSUPPORTED         the source is official, but the words it quotes do not state this claim
#   UNDER_VERIFICATION  a source is recorded, but the record has not verified it
#   SUPERSEDED          a later official statement replaced it
#   UNVERIFIED          no source at all, or one with no address or place to check
VERIFIED, UNSUPPORTED, UNDER_VERIFICATION, SUPERSEDED, UNVERIFIED = (
    'VERIFIED', 'UNSUPPORTED', 'UNDER_VERIFICATION', 'SUPERSEDED', 'UNVERIFIED')
#: An answer: every fact it cites verified, some of them, or none (or it cites none).
ANSWER_VERIFIED, ANSWER_PARTLY_VERIFIED, ANSWER_NOT_VERIFIED = 'VERIFIED', 'PARTLY_VERIFIED', 'NOT_VERIFIED'

_MONTHS = ('january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october',
           'november', 'december')
_QUOTE_STOP = frozenset(('the', 'and', 'for', 'with', 'from', 'into', 'cum'))
_HTTP = re.compile(r'^https?://')


def _quote_text(s: str) -> str:
    return re.sub(r'\s+', ' ', re.sub('[\u2010-\u2015\u2212]', '-', s.lower()))


def _date_forms(y: str, mo: str, d: str) -> list:
    """Every way a notice prints one calendar date: 21.05.2026, 21/5/2026, 21st May 2026, May 21, 2026, 2026-05-21."""
    dd, mm, mon = f'0?{int(d)}', f'0?{int(mo)}', _MONTHS[int(mo) - 1]
    mon3 = mon[:3]
    return [re.compile(p, re.ASCII) for p in (
        rf'(?<!\d){dd}\s*[./-]\s*{mm}\s*[./-]\s*{y}(?!\d)',
        rf'(?<!\d){dd}(?:st|nd|rd|th)?\s*(?:of\s+)?(?:{mon}|{mon3}\.?)\s*,?\s*{y}',
        rf'(?:{mon}|{mon3}\.?)\s+{dd}(?:st|nd|rd|th)?\s*,?\s*{y}',
        rf'(?<!\d){y}\s*-\s*{mo}\s*-\s*{d}(?!\d)')]


def _one_in_quote(p: dict, value: str) -> bool:
    quote = _quote_text(str(p.get('excerptText') or ''))
    if not quote.strip():
        return False
    v = value.strip()
    iso = re.match(r'^(\d{4})-(\d{2})-(\d{2})(?:[ T]\d{2}:\d{2}(?::\d{2})?)?$', v, re.ASCII)
    if iso:
        return any(rx.search(quote) for rx in _date_forms(*iso.groups()))
    num = re.match(r'^\s*(\d[\d,]*)\b', v, re.ASCII)
    if num and re.fullmatch(r'\s*\d[\d,]*(?:\s*\(.*\))?\s*', v, re.ASCII):
        digits = num.group(1).replace(',', '')
        return bool(re.search(r'(?<![\d,])' + ',?'.join(digits) + r'(?!\d)', re.sub(r'\s', ' ', quote), re.ASCII))
    if _quote_text(v) in quote:
        return True
    words = [w for w in re.findall(r'[a-z0-9]+', _quote_text(re.sub(r'\([^)]*\)|\[[^\]]*\]', ' ', v)))
             if len(w) > 2 and w not in _QUOTE_STOP]
    if not words:
        return False
    quoted = set(re.findall(r'[a-z0-9]+', quote))
    return all(w in quoted for w in words)


def claim_in_quote(p: dict, claim: list) -> bool:
    """Do the words this provenance quotes state the claim (any one of its printed forms)?"""
    alts = [str(v) for v in (claim or []) if v is not None and str(v).strip()]
    if not alts:
        return True
    return any(_one_in_quote(p, v) for v in alts)


def fact_verification(p: Optional[dict], claim: list) -> str:
    """The state of one fact, from its provenance and the claim it makes. Nothing else counts: not the
    question, not Claude, not a source that merely looks official."""
    if not isinstance(p, dict) or not (_HTTP.match(str(p.get('officialUrl') or '')) or str(p.get('excerptText') or '').strip()):
        return UNVERIFIED
    level = p.get('verificationLevel')
    if p.get('claimNotInQuote'):
        return UNSUPPORTED
    if level == 'SUPERSEDED' or p.get('supersededBy'):
        return SUPERSEDED
    if level != 'OFFICIALLY_VERIFIED':
        return UNDER_VERIFICATION
    if not (_HTTP.match(str(p.get('officialUrl') or '')) and (p.get('pageNumber') or str(p.get('excerptText') or '').strip())):
        return UNVERIFIED
    return VERIFIED if claim_in_quote(p, claim) else UNSUPPORTED


def answer_verification(cited: list) -> str:
    """VERIFIED only when every fact the answer cites is; PARTLY_VERIFIED when some are; else NOT_VERIFIED."""
    states = [c.get('verification') for c in cited]
    if states and all(s == VERIFIED for s in states):
        return ANSWER_VERIFIED
    return ANSWER_PARTLY_VERIFIED if VERIFIED in states else ANSWER_NOT_VERIFIED


@dataclass
class Fact:
    id: str
    section: str
    label: str
    text: str
    provenance: Optional[dict] = None
    #: What this fact asserts, in the forms its evidence may print it: a date's printed form and its day, a
    #: figure, or -- for anything composite -- the fact as stated, every word of which must be quoted.
    claim: list = field(default_factory=list)

    @property
    def verification(self) -> str:
        return fact_verification(self.provenance, self.claim)

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
    """Every fact the exam record supports, in a fixed order. (section, label, text, provenance, claim).

    The claim is what the fact's evidence must print for the fact to be presented as verified: the value of
    a single-value fact (a date as printed and its day, a figure), or the whole fact as stated -- a post with
    its age band and pay, a stage with its marks -- so a quotation of the post's name alone cannot vouch for
    an age band it does not print. With no claim given, the fact's own text is the claim."""
    out: list = []

    def add(sec, label, text, prov=None, claim=None):
        if str(text).strip():
            out.append((sec, label, str(text), prov, [str(v) for v in (claim if claim is not None else [text]) if v]))

    add('OVERVIEW', 'Exam', f"{exam.get('title')} — {exam.get('authorityName')}")
    if exam.get('cycle'):
        add('OVERVIEW', 'Cycle', exam['cycle'], None, [exam['cycle']])
    if exam.get('vacanciesTotal'):
        add('OVERVIEW', 'Total vacancies', exam['vacanciesTotal'], (exam.get('factEvidence') or {}).get('vacanciesTotal'),
            [exam['vacanciesTotal']])
    if exam.get('crucialEligibilityDate'):
        add('ELIGIBILITY', 'Age is reckoned on', exam['crucialEligibilityDate'],
            (exam.get('factEvidence') or {}).get('crucialEligibilityDate'), [exam['crucialEligibilityDate']])
    if exam.get('overviewDescription'):
        add('OVERVIEW', 'About', _short(exam['overviewDescription'], 500), None, [exam['overviewDescription']])

    for d in exam.get('dates') or []:
        state = []
        if d.get('isTentative'):
            state.append('tentative')
        if d.get('status') == 'SUPERSEDED':
            state.append('superseded — no longer the governing date')
        # A date's claim is the page's own (dateClaim in ui.tsx): as printed, and its day.
        add('DATES', str(d.get('label') or d.get('type')),
            _when(d) + (f" ({', '.join(state)})" if state else ''), d.get('provenance'),
            [d.get('displayWhen') or '', str(d.get('dateTimeStr') or '').split(' ')[0]])

    for h in exam.get('eligibilityHighlights') or []:
        add('ELIGIBILITY', str(h.get('title')), _short(h.get('body'), 600), h.get('provenance'), [h.get('body')])
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
        add('FAQS', str(f.get('question')), _short(f.get('answer'), FAQ_ANSWER_CONTEXT_CHARS), f.get('provenance'),
            [f.get('answer')])
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
    section, label, text = fact[0], fact[1], fact[2]
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
        section, label, text, prov, claim = cands[i]
        sheet.facts.append(Fact(id=f'F{n}', section=section, label=label, text=text,
                                provenance=prov if isinstance(prov, dict) else None, claim=claim))
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


_CLOCK = re.compile(r'\b([01]?\d|2[0-3]):[0-5]\d\b')
#: A time written on the 12-hour clock in an answer: "6 PM", "6:00 p.m.".
_TWELVE_HOUR = re.compile(r'\b(\d{1,2})(?::(\d{2}))?\s*([ap])\.?\s*m\b\.?', re.I)
#: A number at a line's start followed by "." or ")" and a space: a list marker *or* a figure.
_LINE_NUMBER = re.compile(r'(?m)^[ \t]*(\d{1,3})[.)](?=[ \t])')


def _without_list_numbering(text: str) -> str:
    """`text` with the numbering of its numbered lists blanked, and nothing else.

    A list's own numbering is layout ("1. Apply online" / "2. Pay the fee"): only line-start numbers
    that count 1, 2, 3 ... in order (a list may start again at 1) are treated as markers. Any other
    number at a line's start -- "32. Relaxations apply" -- is a figure and is checked like every
    other; stripping every line-start number used to let such a figure through unchecked."""
    out, last, expected = [], 0, 1
    for m in _LINE_NUMBER.finditer(text):
        n = int(m.group(1))
        if n != expected and n != 1:
            continue
        out.append(text[last:m.start(1)])
        out.append(' ' * len(m.group(1)))
        last = m.end(1)
        expected = n + 1
    out.append(text[last:])
    return ''.join(out)


def _norm_url(url: str) -> str:
    return url.rstrip('.,;:!?\'"').rstrip('/').lower()


def _url_in(url: str, trusted: list) -> bool:
    """Is `url` one of the trusted URLs, or a trusted URL's own site or parent path? Matched on URL
    boundaries ("/", "?", "#"), never as a substring: "https://ssc.gov" is another host than
    "https://ssc.gov.in", and the substring test used to accept it."""
    u = _norm_url(url)
    return any(t == u or (t.startswith(u) and t[len(u)] in '/?#') for t in trusted)


def _clock_forms(text: str) -> set:
    """A 24-hour time may be said on the 12-hour clock: "18:00" allows 6 (PM), "00:30" allows 12."""
    out = set()
    for hour in _CLOCK.findall(text):
        h = int(hour)
        if h > 12:
            out.add(str(h - 12))
        elif h == 0:
            out.add('12')
    return out


def validate_answer(output: dict, sheet: FactSheet, question: str, other_exam_names: list) -> list:
    """Reasons the answer must be refused, or []. Deterministic; Claude has no say in it.

    Three inputs, one of them trusted: the candidate's `question` is untrusted input and Claude's
    `output` is untrusted output; only `sheet` -- facts GovOS built from this exam's own record -- may
    vouch for a link or a figure in the answer. `question` is accepted for the callers and is never
    used as evidence."""
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
    # What may vouch for a link or a figure is GovOS's own record of this exam: the supplied facts, the
    # title and the authority. The candidate's question is input, and the answer is Claude's output;
    # neither establishes anything. The question used to count as allowed text, so a link or a figure
    # the candidate typed ("is https://... the portal?", "is the fee 750?") could be echoed back as an
    # answer that passed the checks.
    allowed_text = sheet.corpus().lower()
    trusted_urls = [_norm_url(u) for u in _URL.findall(allowed_text)]
    for url in _URL.findall(answer):
        if not _url_in(url, trusted_urls):
            problems.append('mentions a link that is not in the supplied facts')
            break
    if basis == 'VERIFIED_DATA':
        # A verified answer is held to the facts it cites: every figure in it, a single digit
        # too, must be printed in one of those facts or in the exam's title or authority. The
        # question does not count, or "is the fee 750?" could be answered "yes, 750" whatever the
        # fee is. It used to be enough for a figure of two digits or more to appear anywhere on
        # the sheet, so "6 attempts" passed under "verified" against a fact that says 4.
        cited_text = ' '.join(f'{ids[c].label} {ids[c].text}' for c in cited if c in ids)
        scope = f'{cited_text} {sheet.title} {sheet.authority}'.lower()
        allowed_groups, min_len, where = _figure_groups(scope), 1, 'the facts it cites'
    else:
        scope = allowed_text
        allowed_groups, min_len, where = _figure_groups(scope), 2, 'the supplied facts'
    # A link was checked whole against the record above (and refused if it is not there), so the digits
    # inside it -- ".../07-2031.pdf" -- are part of that link, not figures of their own.
    figures = _without_list_numbering(_URL.sub(' ', answer))
    # A 24-hour time in the facts may be said on the 12-hour clock -- but only as a time, so the
    # "18" of 18:00 lets "6 PM" through and never a bare "6".
    hours = allowed_groups | _clock_forms(scope)
    for m in _TWELVE_HOUR.finditer(figures):
        hour, minutes = _norm_group(m.group(1)), m.group(2)
        if hour not in hours or (minutes and _norm_group(minutes) not in allowed_groups):
            problems.append(f'states a time ({m.group(0).strip()}) that is not in {where}')
            break
    for token in _NUMBER_TOKEN.findall(_TWELVE_HOUR.sub(' ', figures)):
        for group in re.findall(r'\d+', token):
            if len(group) >= min_len and _norm_group(group) not in allowed_groups:
                problems.append(f'states a figure ({group}) that is not in {where}')
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
    """The cited facts with their own provenance, for the page to open as Evidence -- each with its own
    verification state and the claim that state was judged on, so the page shows each fact for what it is
    and opens its Evidence against the same claim."""
    by_id = sheet.by_id
    out = []
    for fid in output.get('cited_fact_ids') or []:
        f = by_id.get(fid)
        if f is not None:
            out.append({'id': f.id, 'section': f.section, 'label': f.label, 'text': f.text,
                        'provenance': f.provenance, 'claim': list(f.claim), 'verification': f.verification})
    return out
