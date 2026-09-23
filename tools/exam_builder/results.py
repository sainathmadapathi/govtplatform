"""Read an exam's result declarations out of whatever its authority published.

RESULTS_AUDIT.md §4 records what four real authorities publish, and it is not one shape:
UPSC declares a Preliminary written result as two rows in its exam page's document table,
each a dated PDF; SSC declares a result as a board notice ("Declaration of Result of Tier-I
for short-listing ..."); IBPS does not declare a result at all in the captured sources, only
*schedules* one ("Result of Online examination -- Preliminary September, 2026"), at month
precision.

So this reads *declarations*, and keeps three things straight that a naive reader confuses:

  * **A declared result is not a scheduled one.** IBPS's "September, 2026" is a date a result
    is expected, not a result. It is carried as `SCHEDULED` with `expected_at`, never with a
    `published_at`, so it can never render as a declaration a candidate could act on.
  * **"Qualified for the next stage" is not "selected".** A shortlist for the Mains does not
    make anyone a selected candidate, and the qualification state is read only where the
    source states it -- otherwise `UNSTATED`.
  * **A result is scoped to its stage and cycle, never to a fixed progression.** There is no
    Prelims -> Mains -> Final built in; the stage is the authority's own word, and the cycle
    the source names is what keeps SSC CGL 2025's many result notices out of the 2026 record.

Candidate-level data is never fabricated: where an authority publishes a roll-number or merit
list, this links to it and transcribes no individual (§12).

Most of the reading machinery is the admit-card reader's, imported rather than copied: the
same authorities lay results and admit cards out the same two ways (a page/table row, a prose
notice), and the lessons -- a cell seam ends a value in a flattened table, a date belongs to
the cue beside it, a homepage is not a document link -- are the same lessons.
"""
from __future__ import annotations

import re

from .admit_card import (_CELL_SEAM, _SIGNATURE, _URL, _YEAR, _near, classify_url,
                         source_failed, stage_scope)
from .dates import read_dates
from .pattern import _evidence, _slug
from .schema import (DatePrecision, Fact, QualificationState, ResultDeclaration, ResultKind,
                     ResultLifecycle, Scope, ScopeKind, ScopeRef, SourceDocument,
                     SourceOutcome, Status, normalise_ws)

__all__ = ['read_notice', 'read_row', 'read_rows', 'classify_label', 'may_supply_results',
           'source_failed', 'describe', 'ResultKind']

# ===================================================================== vocabulary
#: What an authority calls a result, longest and most specific idea first, because "final
#: result" and "written result" both contain "result" and the specific one must win its span.
#: Every phrase is ordinary result vocabulary; which an authority uses is read, not assumed.
_KIND_CUES: tuple[tuple[ResultKind, re.Pattern], ...] = (
    (ResultKind.DV_SHORTLIST, re.compile(
        r'\bdocument\s+verification\b[^.;]{0,30}\b(?:short[\s\-]?list|list|call)\w*'
        r'|\bshort[\s\-]?listed\b[^.;]{0,30}\bdocument\s+verification\b', re.I)),
    (ResultKind.INTERVIEW_SHORTLIST, re.compile(
        r'\b(?:interview|personality\s+test)\b[^.;]{0,30}\bshort[\s\-]?list\w*'
        r'|\bshort[\s\-]?listed\b[^.;]{0,30}\b(?:interview|personality\s+test)\b', re.I)),
    (ResultKind.MERIT_LIST, re.compile(r'\bmerit\s+list\b', re.I)),
    (ResultKind.WAITLIST, re.compile(r'\bwait[\s\-]?list\w*\b|\breserve\s+list\b', re.I)),
    (ResultKind.RECOMMENDATION, re.compile(
        r'\brecommend(?:ation|ed)\b|\bcandidates?\s+recommended\b', re.I)),
    (ResultKind.SELECTION, re.compile(
        r'\bselection\s+list\b|\bselected\s+candidates?\b|\bfinal\s+selection\b'
        r'|\bappointment\b', re.I)),
    (ResultKind.SCORECARD, re.compile(
        r'\bscore\s*cards?\b|\bresponse\s+sheets?\b', re.I)),
    (ResultKind.MARKS, re.compile(
        r'\b(?:uploading|declaration)\s+of\s+marks\b|\bmarks\s+of\s+candidates?\b', re.I)),
    (ResultKind.FINAL_RESULT, re.compile(r'\bfinal\s+result\b', re.I)),
    (ResultKind.WRITTEN_RESULT, re.compile(r'\bwritten\s+result\b', re.I)),
    (ResultKind.SHORTLIST, re.compile(
        r'\bshort[\s\-]?list\w*\b|\bfor\s+short[\s\-]?listing\b', re.I)),
    (ResultKind.QUALIFIED_LIST, re.compile(
        r'\bqualified\s+candidates?\b|\blist\s+of\s+qualified\b', re.I)),
    (ResultKind.STAGE_RESULT, re.compile(
        r'\bresult\s+of\s+(?:tier|phase|stage|prelims?|preliminary|mains?)\b', re.I)),
    (ResultKind.RESULT, re.compile(
        r'\bdeclaration\s+of\s+result\b|\bresults?\s+declared\b|\bresult\b', re.I)),
)

#: What the source says happened to the candidates. Read only where present; the whole point
#: of §5 is that a shortlist is not a selection, so these do not overlap by inference.
_QUALIFICATION_CUES: tuple[tuple[QualificationState, re.Pattern], ...] = (
    (QualificationState.RECOMMENDED, re.compile(r'\brecommend(?:ed|ation)\b', re.I)),
    (QualificationState.SELECTED, re.compile(
        r'\bselected\s+candidates?\b|\bfinal(?:ly)?\s+selected\b|\bfor\s+appointment\b', re.I)),
    (QualificationState.WAITLISTED, re.compile(r'\bwait[\s\-]?listed\b|\breserve\s+list\b', re.I)),
    (QualificationState.SHORTLISTED, re.compile(
        r'\bshort[\s\-]?listed\b|\bfor\s+short[\s\-]?listing\b', re.I)),
    (QualificationState.QUALIFIED, re.compile(
        r'\bqualified\b|\bdeclared\s+(?:to\s+have\s+)?qualified\b', re.I)),
)

#: The stage a cleared candidate advances to: "short-listing for Tier-II", "qualified for the
#: Main Examination". The stage it *names as the destination* is the next stage.
_NEXT_STAGE_CUE = re.compile(
    r'\b(?:short[\s\-]?list\w*|qualif\w+|admission|appear\w+)\b[^.;]{0,40}?'
    r'\b(?:for|to|in)\s+(?:appearing\s+in\s+|the\s+)?'
    r'((?:tier|phase|stage)[\s\-]*[IVX0-9]+|main\w*|interview|personality\s+test'
    r'|document\s+verification|skill\s+test)', re.I)

#: A count of those who cleared: "13,343 candidates", "declaration of final result of 219".
_COUNT_CUE = re.compile(
    r'\b(\d[\d,]{1,12})\s+candidates?\b|\bresult\s+of\s+(\d[\d,]{1,12})\b'
    r'|\bshort[\s\-]?listed?\s+(\d[\d,]{1,12})\b', re.I)

#: A future/expected date rather than a declaration: "Result ... September, 2026".
_SCHEDULE_CUE = re.compile(
    r'\bresult\b[^.;]{0,60}\b(?:January|February|March|April|May|June|July|August'
    r'|September|October|November|December)[,\s]+20\d{2}', re.I)

#: A cue that a nearby date is the declaration date: "declared on", "result dated".
_DECLARED_CUE = re.compile(
    r'\bdeclared\s+on\b|\bdeclaration\b[^.;]{0,20}?\bon\b|\bresult\s+dated\b'
    r'|\bresult\s+(?:was\s+)?declared\b[^.;]{0,20}?\bon\b|\buploaded\s+on\b', re.I)

_STAGE_WORDS = re.compile(
    r'\b(?:tier|phase|stage|prelims?|preliminary|mains?|interview)\b', re.I)
_DATE_WINDOW = 120


# ====================================================================== helpers
def classify_label(label: str) -> ResultKind | None:
    """Which result the label names, in the authority's own words, or None."""
    for kind, pattern in _KIND_CUES:
        if pattern.search(label or ''):
            return kind
    return None


def _document_name(label: str) -> str:
    """The document's own name -- the phrase that identified its kind, not the whole row.

    The admit-card lesson: "Download of call letters for Online examination -- Preliminary"
    names an activity; the document is a "call letter". Here a schedule row reads "Result of
    Online examination -- Preliminary September, 2026" and the thing is a "Result".
    """
    named = next((m.group(0) for _, pattern in _KIND_CUES
                  for m in [pattern.search(label or '')] if m), '')
    return normalise_ws(named).strip(' -–') or normalise_ws(label)


def _qualification(text: str) -> QualificationState:
    for state, pattern in _QUALIFICATION_CUES:
        if pattern.search(text):
            return state
    return QualificationState.UNSTATED


def _next_stage(text: str, doc: SourceDocument):
    m = _NEXT_STAGE_CUE.search(text)
    if not m:
        return Fact.not_extracted('the source states no next stage'), ''
    phrase = normalise_ws(m.group(0))
    stage = stage_scope(m.group(1))
    ref = stage.refs[0].ref if stage.refs else _slug(m.group(1))
    ev = _evidence(_near(text, m.start(), 220), doc, text, reading=f'next stage: {phrase}')
    fact = Fact.verified(phrase, ev, confidence=0.85) if ev else Fact.needs_review(
        phrase, 'the next stage was read but its span could not be verified verbatim')
    return fact, ref


def _count(text: str, doc: SourceDocument):
    m = _COUNT_CUE.search(text)
    if not m:
        return Fact.not_extracted('the source states no count of cleared candidates')
    raw = next(g for g in m.groups() if g)
    try:
        value = int(raw.replace(',', ''))
    except ValueError:
        return Fact.not_extracted('a count was seen but could not be read as a number')
    ev = _evidence(_near(text, m.start(), 200), doc, text, reading=f'{value} candidates')
    return (Fact.verified(value, ev, confidence=0.8) if ev
            else Fact.needs_review(value, 'the count could not be verified verbatim'))


def _dated(reading: str, at: int, text: str, doc: SourceDocument = None, *, dates,
           window=_DATE_WINDOW):
    """The date nearest after a cue, within a window, verbatim -- or nothing."""
    for d in dates:
        if d.start < at or d.start - at > window:
            continue
        span = _near(text, d.start, 240)
        ev = _evidence(span, doc, text, reading=reading)
        note = ('' if d.precision is DatePrecision.DAY
                else 'the authority published a month, not a day; shown as the month it '
                     'printed rather than a date it did not')
        if ev is None:
            return Fact.needs_review(d.iso, 'the date could not be verified verbatim'), d
        fact = Fact.verified(d.iso, ev, confidence=0.9 if not note else 0.7)
        fact.note = note
        return fact, d
    return None, None


def _cycle_in(text: str, fallback: str = '') -> str:
    m = _YEAR.search(text or '')
    return m.group(1) if m else fallback


def _new(exam_id: str, kind: ResultKind, scope: Scope, cycle: str, key: str) -> ResultDeclaration:
    stage = scope.refs[0].label if scope.refs else 'exam'
    return ResultDeclaration(
        id=f'{exam_id}-result-{kind.value.lower().replace("_", "-")}-{_slug(stage)}-{key}',
        kind=kind, scope=scope, cycle=cycle,
        published_at=Fact.not_extracted('no declaration date was read'),
        expected_at=Fact.not_extracted('no scheduled date was read'),
        document_url=Fact.not_extracted(
            'the authority publishes no direct file link, or none appears here'),
        portal_url=Fact.not_extracted('no portal link appears here'),
        qualified_count=Fact.not_extracted('no count of cleared candidates was read'),
        next_step=Fact.not_extracted('the source states no next stage'),
        status=Status.VERIFIED)


# =============================================================== prose notices
def _declaration_date(body: str, dates: list, doc: SourceDocument):
    """The date the notice says the result was declared, found from its own cue.

    "The result was declared on 09.01.2026" -- the date follows a declaration cue, which is
    where to look, rather than near whichever synonym for "result" happened to appear first.
    """
    for m in _DECLARED_CUE.finditer(body):
        for d in dates:
            if 0 <= d.start - m.end() <= 25:
                return _dated('result declared', d.start - 1, body, dates=[d], doc=doc,
                              window=3)
    return None, None


def read_notice(doc: SourceDocument, text: str, *, exam_id: str, headline: str = '',
                published_at: str = '', authority_domain: str = '',
                cycle: str = '') -> list[ResultDeclaration]:
    """Every result declaration a notice states, one per kind cue it carries.

    A board notice ("Declaration of Result of Tier-I for short-listing ... for Tier-II") is
    one declaration with a stage, a count where stated, and a next stage where named.
    """
    body = normalise_ws(f'{headline} {text}' if headline else text)
    if not body:
        return []
    dates = read_dates(body)
    sig = _SIGNATURE.search(body)
    live = [d for d in dates if sig is None or d.start < sig.start()]
    headline_scope = stage_scope(headline)
    # A stage named once by the document as a whole scopes a statement that names none itself.
    document_scope = Scope()
    if not headline_scope.refs:
        named = {r.refs[0].label for m in _STAGE_WORDS.finditer(body)
                 for r in [stage_scope(body[m.start():m.start() + 40])] if r.refs}
        if len(named) == 1:
            document_scope = stage_scope(named.pop())

    out: list[ResultDeclaration] = []
    seen: set = set()
    for kind, pattern in _KIND_CUES:
        m = pattern.search(body)
        if not m:
            continue
        scope = stage_scope(body[max(0, m.start() - 120):m.start() + 120]) \
            or headline_scope or document_scope
        if not scope.refs:
            scope = headline_scope if headline_scope.refs else document_scope
        declared, used = _declaration_date(body, live, doc)
        key = (kind, scope.refs[0].ref if scope.refs else '',
               declared.value if declared else '')
        if key in seen:
            continue
        seen.add(key)
        ev = None
        span = _near(body, m.start(), 260)
        ev = _evidence(span, doc, body, reading=f'{kind.value}: {normalise_ws(m.group(0))}')

        event = _new(exam_id, kind, scope, _cycle_in(headline or body[:200], cycle),
                     declared.value if declared else _slug(normalise_ws(m.group(0))))
        event.label = _document_name(normalise_ws(m.group(0)))
        event.source_label = normalise_ws(headline or m.group(0))[:160]
        if declared is not None:
            event.published_at = declared
            event.published_precision = (used.precision.value if used else 'DAY')
        event.qualification = _qualification(body)
        event.qualified_count = _count(body, doc)
        event.next_step, event.next_stage_ref = _next_stage(body, doc)
        event.evidence = [e for f in (declared, event.next_step) if f for e in f.evidence]
        if ev is not None and ev not in event.evidence:
            event.evidence.insert(0, ev)
        if not any(e.is_verbatim for e in event.evidence):
            event.status = Status.NEEDS_REVIEW
            event.note = ('no span of this declaration could be verified verbatim, so it is '
                          'not shown as the authority’s own')
        # Break after the first (most specific) kind that matched, so one notice is one
        # declaration rather than one per synonym it happens to contain.
        out.append(event)
        break
    return out


# ================================================================= table rows
def read_row(label: str, value: str, doc: SourceDocument, text: str, *, exam_id: str,
             authority_domain: str = '', cycle: str = '', portal_url: str = '',
             default_stage: str = '') -> ResultDeclaration | None:
    """One row of a document or schedule table: a label and whatever sits beside it.

    UPSC declares results this way -- "Written Result | WR-CSP-2026-RollList-Engl-150626.pdf
    | 15/06/2026". IBPS schedules one this way -- "Result of Online examination -- Preliminary
    | September, 2026". The first is a declaration with a document; the second is a schedule.
    """
    kind = classify_label(label)
    if kind is None:
        return None
    # A flattened row runs into the next; the cell ends where its own sentence does.
    value = _CELL_SEAM.split(normalise_ws(value), 1)[0].strip() if value else value
    joined = normalise_ws(f'{label} {value}')
    dates = read_dates(joined)
    scheduled = bool(_SCHEDULE_CUE.search(joined)) and not re.search(
        r'https?://|\.pdf', f'{label} {value}', re.I)
    scope = stage_scope(label)
    if not scope.refs and default_stage:
        # The page's own title names the stage; every row on it inherits that stage, the way
        # a notice's headline scopes its body.
        scope = stage_scope(default_stage)
    the_date = _dated(f'{normalise_ws(label)}: {normalise_ws(value)}', 0, joined, doc,
                      dates=dates, window=len(joined))[0] if dates else None

    if scheduled:
        kind = ResultKind.SCHEDULED
    event = _new(exam_id, kind, scope, _cycle_in(joined, cycle),
                 (the_date.value if the_date else _slug(normalise_ws(label))))
    event.label = _document_name(label)
    event.source_label = normalise_ws(label)
    doc_url = ''
    for m in _URL.finditer(f'{label} {value}'):
        if classify_url(m.group(0).rstrip('.,;)'), authority_domain=authority_domain) == 'DOWNLOAD':
            doc_url = m.group(0).rstrip('.,;)')
            break
    # UPSC prints a bare file name in the cell, not a URL; resolve it against the page host.
    if not doc_url:
        fm = re.search(r'\b([\w\-]+\.pdf)\b', value or '', re.I)
        if fm and authority_domain:
            base = authority_domain if '//' in authority_domain else 'https://' + authority_domain
            doc_url = base.rstrip('/') + '/sites/default/files/' + fm.group(1)
    if the_date is not None:
        if scheduled:
            event.expected_at = the_date
            event.expected_precision = dates[0].precision.value if dates else 'DAY'
        else:
            event.published_at = the_date
            event.published_precision = dates[0].precision.value if dates else 'DAY'
    if doc_url:
        ev = _evidence(joined, doc, joined, reading=f'result document: {doc_url}')
        event.document_url = (Fact.verified(doc_url, ev, confidence=0.9) if ev
                              else Fact.needs_review(doc_url, 'span not verified verbatim'))
    if portal_url and _URL.fullmatch(portal_url.strip()):
        event.portal_url = Fact.needs_review(
            portal_url, 'the portal is the authority’s own page, named in this record '
                        'rather than in the row')
    event.qualification = _qualification(joined)
    src = event.published_at if event.published_at.has_value else (
        event.expected_at if event.expected_at.has_value else event.document_url)
    event.evidence = list(src.evidence)
    if not any(e.is_verbatim for e in event.evidence):
        ev = _evidence(joined, doc, joined, reading=f'{kind.value} row')
        if ev:
            event.evidence.append(ev)
    if not any(e.is_verbatim for e in event.evidence):
        event.status = Status.NEEDS_REVIEW
        event.note = 'the row was read but no span of it could be verified verbatim'
    return event


def read_rows(rows, doc: SourceDocument, text: str, *, exam_id: str,
              authority_domain: str = '', cycle: str = '', portal_url: str = '',
              default_stage: str = '') -> list[ResultDeclaration]:
    """Every result row in a table, and none of the rows that are about something else."""
    out = []
    for label, value in rows:
        event = read_row(label, value, doc, text, exam_id=exam_id,
                         authority_domain=authority_domain, cycle=cycle,
                         portal_url=portal_url, default_stage=default_stage)
        if event is not None:
            out.append(event)
    return out


# ================================================================= publication
def may_supply_results(text: str, target) -> tuple[bool, str]:
    """Whether this document's result facts belong to this exam -- the pattern gate.

    The same conservative rule the pattern, syllabus and admit-card readers use, and the one
    that matters most here: identity checks the *year*, so SSC CGL 2025's result notices --
    of which the board has many -- supply nothing to the 2026 record.
    """
    from .pattern import may_supply_pattern
    return may_supply_pattern(text, target)


# ====================================================================== report
def describe(events: list) -> dict:
    """What was found, counted by what it is, for a build report."""
    by_kind: dict = {}
    for e in events:
        by_kind[e.kind.value] = by_kind.get(e.kind.value, 0) + 1
    return {
        'events': len(events),
        'byKind': by_kind,
        'declared': sum(1 for e in events if e.is_declaration),
        'scheduled': sum(1 for e in events if e.kind is ResultKind.SCHEDULED),
        'publishable': sum(1 for e in events if e.is_publishable),
        'withStage': sum(1 for e in events if e.scope.refs),
        'withDocument': sum(1 for e in events if e.document_url.is_publishable),
        'withCount': sum(1 for e in events if e.qualified_count.has_value),
        'withNextStage': sum(1 for e in events if e.next_step.has_value),
        'rows': [
            {'kind': e.kind.value, 'label': e.label,
             'stage': e.scope.refs[0].label if e.scope.refs else '',
             'cycle': e.cycle,
             'declared': e.published_at.value, 'expected': e.expected_at.value,
             'qualification': e.qualification.value,
             'count': e.qualified_count.value, 'nextStage': e.next_stage_ref,
             'status': e.status.value}
            for e in events],
    }
