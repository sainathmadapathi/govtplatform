"""Reading a timeline out of a notice, without deciding in advance what a timeline contains.

A date on its own says nothing. "15 May 2026" could be the last day to apply, the day of the
examination, the day the result comes out, or the day the fee window shuts, and the only
thing that distinguishes them is the wording around it. So nothing here starts from a date:
every milestone starts from a *statement* — a passage that says what happens — and the date
is read out of that statement, never the other way round.

That ordering is what makes the extractor universal. An authority that publishes three dates
produces three milestones; one that publishes twelve produces twelve; one that says the
examination will be notified later produces an AWAITED milestone with no date, which is a
real thing to tell a candidate and not an absence.

Four rules the whole module obeys:

  * **the wording names the event.** Cue sets, in the manner of `semantic.py` — the idea of
    applying, the idea of an examination being held — never one authority's phrasing.
  * **the span carries both.** A milestone's evidence must contain the event wording *and*
    the date, so a date can never be attached to a statement it did not appear in.
  * **precision is the authority's.** "In June 2026" is a month, and recording a day would
    be inventing one.
  * **a revision is a relationship, not an overwrite.** A postponement produces a second
    milestone that points at the first; both are kept and the old one stops being effective.

Nothing here names an authority, an exam, a stage or a month-specific format.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from datetime import date as _date

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .schema import (DatePrecision, Fact, Milestone, MilestoneState, Scope, ScopeKind,
                     ScopeRef, SourceDocument, SourceEvidence, Status)

# ==================================================================== dates
_MONTHS = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}
_MONTH_WORD = (r'jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
               r'jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|'
               r'dec(?:ember)?')

#: Numeric: 21.05.2026, 21-05-2026, 21/05/2026. Day first, which is the convention these
#: documents are written in; an ambiguous pair is reported rather than guessed (see below).
_NUMERIC = re.compile(r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})\b')

#: Worded: "21 May 2026", "21st May, 2026", "May 21, 2026".
_WORDED = re.compile(
    rf'\b(\d{{1,2}})\s*(?:st|nd|rd|th)?\s*[-,.]?\s*({_MONTH_WORD})\s*[-,.]?\s*(\d{{4}})\b',
    re.I)
_WORDED_MONTH_FIRST = re.compile(
    rf'\b({_MONTH_WORD})\s+(\d{{1,2}})\s*(?:st|nd|rd|th)?\s*,?\s*(\d{{4}})\b', re.I)

#: Month only: "in June 2026". A month is what was said, and a day would be invented.
_MONTH_ONLY = re.compile(rf'\b({_MONTH_WORD})[,\s]+(\d{{4}})\b', re.I)

#: A clock time beside a date: "(23:00 hours)", "upto 6:00 PM", "till 11.59 p.m.".
_TIME = re.compile(r'\b(\d{1,2})[:.](\d{2})\s*(a\.?m\.?|p\.?m\.?|hours|hrs)?', re.I)


@dataclass
class ReadDate:
    """One date as the document stated it."""

    iso: str
    precision: DatePrecision
    start: int
    end: int
    text: str

    @property
    def sort_key(self) -> str:
        return self.iso


def _iso(day: int, month: int, year: int) -> str | None:
    if year < 100:
        year += 2000
    try:
        return _date(year, month, day).isoformat()
    except ValueError:
        return None


def read_dates(text: str) -> list[ReadDate]:
    """Every date in a passage, with the precision the authority actually used."""
    out: list[ReadDate] = []
    taken: list[tuple[int, int]] = []

    def free(a: int, b: int) -> bool:
        return not any(a < y and x < b for x, y in taken)

    for m in _WORDED.finditer(text):
        day, month, year = int(m.group(1)), _MONTHS[m.group(2)[:3].lower()], int(m.group(3))
        iso = _iso(day, month, year)
        if iso and free(*m.span()):
            out.append(ReadDate(iso, DatePrecision.DAY, m.start(), m.end(), m.group(0)))
            taken.append(m.span())

    for m in _WORDED_MONTH_FIRST.finditer(text):
        month, day, year = _MONTHS[m.group(1)[:3].lower()], int(m.group(2)), int(m.group(3))
        iso = _iso(day, month, year)
        if iso and free(*m.span()):
            out.append(ReadDate(iso, DatePrecision.DAY, m.start(), m.end(), m.group(0)))
            taken.append(m.span())

    for m in _NUMERIC.finditer(text):
        a, b, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if b > 12:
            # Only one reading is possible, so take it whichever order it is written in.
            a, b = b, a
        iso = _iso(a, b, year)
        if iso and free(*m.span()):
            out.append(ReadDate(iso, DatePrecision.DAY, m.start(), m.end(), m.group(0)))
            taken.append(m.span())

    for m in _MONTH_ONLY.finditer(text):
        if not free(*m.span()):
            continue
        month, year = _MONTHS[m.group(1)[:3].lower()], int(m.group(2))
        iso = _iso(1, month, year)
        if iso:
            out.append(ReadDate(iso, DatePrecision.MONTH, m.start(), m.end(), m.group(0)))
            taken.append(m.span())

    out.sort(key=lambda d: d.start)
    return out


# ===================================================================== events
@dataclass(frozen=True)
class EventCue:
    """What an authority says when it means a particular event.

    `anchors` are the ideas; one must be present. `against` are the ideas that mean the
    passage is about something adjacent -- a rule about admit cards inside a paragraph on
    conduct, say -- and they veto the reading rather than merely lowering it.
    """

    kind: str
    anchors: tuple[str, ...]
    against: tuple[str, ...] = ()
    #: Where the date sits relative to the statement, when the authority gives a window.
    range_role: str = ''

    def matches(self, passage: str) -> bool:
        low = passage.lower()
        if any(re.search(a, low) for a in self.against):
            return False
        return any(re.search(a, low) for a in self.anchors)


#: The vocabulary of a recruitment timeline, as ideas. Order matters only in that the first
#: match wins for a passage, so the more specific events come first.
EVENT_CUES: tuple[EventCue, ...] = (
    EventCue('CORRECTION_WINDOW',
             (r'correction\s+window', r'window\s+for\s+(?:application\s+form\s+)?correction',
              r'edit(?:ing)?\s+(?:of\s+)?(?:the\s+)?application',
              r'modif\w+\s+(?:of\s+)?(?:the\s+)?application')),
    EventCue('FEE_PAYMENT_END',
             (r'(?:last\s+date|closing\s+date)[^.]{0,40}\b(?:fee|payment)\b',
              r'\bfee\s+payment\b[^.]{0,30}\b(?:last|upto|up\s+to|till)\b',
              r'payment\s+of\s+(?:the\s+)?(?:application\s+|examination\s+)?fee[^.]{0,30}'
              r'\b(?:last|upto|up\s+to|till|by)\b')),
    EventCue('APPLICATION_WINDOW',
             (r'(?:submission|receipt|filing)\s+of\s+(?:the\s+)?(?:online\s+)?applications?',
              r'online\s+applications?\s+(?:can|may|shall|will)\s+be\s+(?:submitted|filled)',
              r'applications?\s+(?:are|is|may|can)\s+(?:to\s+be\s+)?(?:submitted|filled|made)',
              r'dates?\s+for\s+(?:submission|filing|applying)',
              r'apply\s+online\b', r'registration\s+(?:opens?|begins?|starts?)',
              # The active voice, which the rest of this set was missing:
              # "Candidates may submit online applications from X to Y".
              r'submit\w*\s+(?:the\s+)?(?:online\s+)?applications?\b',
              r'\bfil(?:l|ing)\w*\s+(?:up\s+)?(?:the\s+)?(?:online\s+)?applications?\b',
              r'last\s+date[^.]{0,40}\bapplication', r'closing\s+date[^.]{0,30}\bapplication'),
             against=(r'\bfee\b.{0,20}\bpayment\b',)),
    EventCue('ADMIT_CARD',
             (r'(?:e-?\s?)?admit\s+cards?', r'call\s+letters?', r'hall\s+tickets?'),
             against=(r'\bcity\s+intimation\b',)),
    EventCue('CITY_INTIMATION',
             (r'city\s+intimation', r'intimation\s+of\s+(?:exam\w*\s+)?city',
              r'exam(?:ination)?\s+city\s+(?:slip|intimation|details)')),
    EventCue('ANSWER_KEY',
             (r'answer\s+keys?', r'tentative\s+keys?', r'provisional\s+keys?')),
    EventCue('RESULT',
             (r'\bresults?\b', r'declaration\s+of\s+result', r'merit\s+list')),
    EventCue('INTERVIEW',
             (r'\binterviews?\b', r'personality\s+test', r'viva[\s-]?voce')),
    EventCue('SKILL_TEST',
             (r'skill\s+test', r'typing\s+test', r'proficiency\s+test',
              r'computer\s+(?:knowledge|proficiency)\s+test', r'\bdest\b')),
    EventCue('PHYSICAL_TEST',
             (r'physical\s+(?:efficiency|standard|measurement)\s+test',
              r'\bpet\b', r'\bpst\b', r'physical\s+test')),
    EventCue('DOCUMENT_VERIFICATION',
             (r'document\s+verification', r'verification\s+of\s+documents?',
              r'scrutiny\s+of\s+documents?')),
    EventCue('EXAM',
             # A bounded gap: an authority names *which* examination before saying
             # what happens to it -- "the examination for Tier I will be held".
             (r'exam(?:ination)?[^.\n]{0,40}?\b(?:is|are|will\s+be|shall\s+be|scheduled|to\s+be)\s+'
              r'(?:held|conducted|scheduled|notified|organised|organized)',
              r'dates?\s+of\s+(?:the\s+)?(?:written\s+)?exam(?:ination)?',
              r'exam(?:ination)?\s+dates?', r'date\s+of\s+(?:tier|paper|phase|stage)',
              # Once a notice has named its papers it stops repeating the noun:
              # "Paper I will be held on X" is an examination date.
              r'(?:tier|paper|phase|stage|session|shift)\s*[-–—:]?\s*(?:[ivxIVX]{1,4}|\d{1,2}|[A-Z])\b[^.\n]{0,30}?\b(?:is|are|will\s+be|shall\s+be|to\s+be)\s+(?:held|conducted|scheduled)',
              r'schedule\s+of\s+(?:the\s+)?exam(?:ination)?',
              r'conduct\s+of\s+(?:the\s+)?exam(?:ination)?',
              # An examination being moved is still an examination. Without these the
              # lifecycle wording carried the event and the cue set did not recognise it.
              r'exam(?:ination)?\s+scheduled\s+(?:for|on|to\s+be\s+held)',
              r'exam(?:ination)?[^.]{0,60}\b(?:has|have|stands?)\s+been\s+'
              r'(?:postponed|cancell?ed|rescheduled|deferred|preponed)',
              r'exam(?:ination)?[^.]{0,40}\bwill\s+now\s+be\s+held'),
             against=(r'\badmit\s+card\b', r'\banswer\s+key\b', r'\bresult\b',
                      r'\bfee\b', r'\bapplication\s+form\b')),
    EventCue('NOTIFICATION',
             (r'notification\s+(?:is|was|shall\s+be|will\s+be)?\s*'
              r'(?:published|issued|released|dated)',
              r'date\s+of\s+(?:the\s+)?(?:notification|advertisement|notice)',
              r'advertisement\s+(?:is|was)\s+(?:published|issued)')),
)

#: Words that say a stated date is not final. An authority's own hedge, not our doubt.
_TENTATIVE = re.compile(
    r'\btentativ\w+\b|\bprovisional\w*\b|\blikely\b|\bexpected\b|\bsubject\s+to\s+change\b|'
    r'\bmay\s+(?:be\s+)?(?:change|vary)\b|\bindicative\b', re.I)

#: What an authority says when it moves or drops an event.
_LIFECYCLE = (
    (MilestoneState.CANCELLED,
     re.compile(r'\bcancell?ed\b|\bstands?\s+cancell?ed\b|\bwithdrawn\b|\bannull?ed\b', re.I)),
    (MilestoneState.POSTPONED,
     re.compile(r'\bpostponed\b|\bdeferred\b|\bput\s+off\b|\bheld\s+in\s+abeyance\b', re.I)),
    (MilestoneState.RESCHEDULED,
     re.compile(r'\brescheduled\b|\brevised\b|\bpreponed\b|\bnew\s+date\b|'
                r'\brevised\s+schedule\b|\bin\s+supersession\b|\bnow\s+be\s+held\b', re.I)),
)

#: Stated as existing, with no date. A real thing to show, and not an absence.
_AWAITED = re.compile(
    r'\bwill\s+be\s+(?:announced|notified|intimated|informed|communicated)\b|'
    r'\bto\s+be\s+(?:announced|notified|intimated|decided)\b|'
    r'\bin\s+due\s+course\b|\bshall\s+be\s+notified\s+(?:later|separately|in\s+due)\b|'
    r'\bseparately\s+(?:notified|announced)\b', re.I)

#: Page furniture. An official page carries its footer beside its content, and the footer
#: has a date in it: "Last Updated", "SiteMap", "visit help page" all became milestones.
_FURNITURE = re.compile(
    r'\blast\s+updated\b|\bsite\s?map\b|\bhelp\s+page\b|\bscreen\s+reader\b|'
    r'\bskip\s+to\s+main\b|\bprivacy\s+policy\b|\bterms\s+of\s+use\b|'
    r'\bcopyright\b|\bvisitor\s+count\b|\bfeedback\b|\bdisclaimer\b|'
    r'\bhits?\s*:\s*\d|\bpage\s+\d+\s+of\s+\d+\b', re.I)


def _is_a_label(text: str) -> bool:
    """Two words or more, so a clause-number tail like "26." is not a milestone name."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", text or '') if len(w) > 2]
    return len(words) >= 2


#: A window: two dates joined by the authority. "from X to Y", "X to Y", "between X and Y".
_RANGE = re.compile(r'\b(?:from|between|w\.e\.f\.?)\b|\bto\b|\btill\b|\bupto\b|\bup\s+to\b',
                    re.I)

#: Words naming a stage or paper, so a date can be scoped to one. The *words* are generic;
#: the value beside them is whatever the authority wrote.
_STAGE_REF = re.compile(
    r'\b((?:tier|phase|stage|paper|part|session|shift)\s*[-–—:]?\s*'
    r'(?:[ivxIVX]{1,4}|\d{1,2}|[A-Z])\b)', re.I)

#: A cycle label the authority attaches to an event, so two cycles in one document stay apart.
_CYCLE = re.compile(r'\b(20\d{2})(?:\s*[-–—/]\s*(\d{2,4}))?\b')


# ================================================================= passages
def statements(text: str) -> list[str]:
    """Passages that could each state one event.

    Split on sentence ends, on clause numbers and on line breaks, because a notice's
    timeline is as often a table of rows as it is prose. A row is a statement.
    """
    flat = (text or '').replace('\r', '')
    flat = re.sub(r'(?<=[.;])\s+(?=\d{1,2}\.\d{1,2}\s)', '\n', flat)
    parts: list[str] = []
    for line in flat.split('\n'):
        line = line.strip()
        if not line:
            continue
        for piece in re.split(r'(?<=[.;])\s+(?=[A-Z(])', line):
            piece = piece.strip()
            if piece:
                parts.append(piece)
    return parts


def _window(parts: list[str], index: int, before: int = 1, after: int = 1) -> str:
    """A statement plus its neighbours.

    A table puts the label on one line and the date on the next often enough that reading a
    row in isolation loses half of it.
    """
    lo = max(0, index - before)
    hi = min(len(parts), index + after + 1)
    return ' '.join(parts[lo:hi])


# ================================================================= the reader
@dataclass
class DateReading:
    """One event as a passage stated it, before it becomes a Milestone."""

    kind: str
    label: str
    span: str
    dates: list[ReadDate] = dc_field(default_factory=list)
    is_range: bool = False
    tentative: bool = False
    state: MilestoneState = MilestoneState.ANNOUNCED
    stage_ref: str = ''
    cycle: str = ''
    precision: DatePrecision = DatePrecision.DAY


def _label_for(passage: str, kind: str) -> str:
    """The authority's own wording for this event, trimmed to a label.

    Taken from the passage rather than composed, so the timeline reads in the authority's
    words. Where the passage is a table row the label is the part before the date.
    """
    text = normalise_ws(passage)
    dates = read_dates(text)
    if dates:
        head = text[:dates[0].start].strip(' :|-–—\t')
        head = re.sub(r'^\d{1,2}(?:\.\d{1,2})*\s*[.)]?\s*', '', head).strip()
        if 3 <= len(head) <= 90:
            return head
    trimmed = re.sub(r'^\d{1,2}(?:\.\d{1,2})*\s*[.)]?\s*', '', text).strip()
    return (trimmed[:90] or kind.replace('_', ' ').title()).strip()


def read_statement(passage: str, *, context: str = '') -> DateReading | None:
    """What event, if any, this passage states — and the date it gives for it."""
    # The passage first: a table row names its own event, and classifying it by its
    # neighbours read "Date of examination" as an application window because the row above
    # it mentioned applications.
    cue = next((c for c in EVENT_CUES if c.matches(passage)), None)
    haystack = passage
    if cue is None and context:
        # Only now the neighbourhood, for a row whose label and date are on separate lines.
        haystack = context
        cue = next((c for c in EVENT_CUES if c.matches(context)), None)
    if cue is None:
        return None
    # Hedging and lifecycle are read from the wider text either way, because "the above
    # dates stand postponed" is a statement about its neighbours by design.
    wider = context or passage

    dates = read_dates(passage) or read_dates(haystack)
    state = MilestoneState.ANNOUNCED
    for candidate_state, pattern in _LIFECYCLE:
        if pattern.search(wider):
            state = candidate_state
            break
    if not dates:
        if state is MilestoneState.ANNOUNCED and not _AWAITED.search(wider):
            return None
        if state is MilestoneState.ANNOUNCED:
            state = MilestoneState.AWAITED

    stage = _STAGE_REF.search(passage)
    cycle_match = _CYCLE.search(passage) or _CYCLE.search(haystack)
    precision = dates[0].precision if dates else DatePrecision.UNSPECIFIED

    return DateReading(
        kind=cue.kind,
        label=_label_for(passage, cue.kind),
        span=normalise_ws(passage),
        dates=dates,
        is_range=bool(len(dates) >= 2 and _RANGE.search(passage)),
        tentative=bool(_TENTATIVE.search(wider)),
        state=state,
        stage_ref=normalise_ws(stage.group(1)) if stage else '',
        cycle=cycle_match.group(1) if cycle_match else '',
        precision=precision)


# =============================================================== milestones
def _evidence(span: str, doc: SourceDocument, text: str, *,
              reading: str) -> SourceEvidence | None:
    ev = Evidence(span=span, source_url=doc.url, document_title=doc.title, page=1,
                  reading=reading)
    if ev.verify(text) is not EvidenceStatus.VERIFIED:
        return None
    out = SourceEvidence.from_evidence(ev, source=doc, source_id=doc.id)
    out.section = 'timeline'
    return out


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')[:40] or 'x'


def extract_milestones(doc: SourceDocument, text: str, *, exam_id: str,
                       cycle: str = '') -> list[Milestone]:
    """Every dated event this document states, in the authority's own words.

    A statement with no date and no hedge is skipped rather than recorded as unknown: a
    notice mentions examinations constantly and only some of those mentions are milestones.
    """
    parts = statements(text)
    out: list[Milestone] = []
    seen: set[tuple[str, str, str]] = set()

    for index, passage in enumerate(parts):
        if not read_dates(passage) and not _AWAITED.search(passage):
            continue
        reading = read_statement(passage, context=_window(parts, index))
        if reading is None:
            continue
        if _FURNITURE.search(passage):
            # A footer is not a timeline, however many dates it carries.
            continue
        if not _is_a_label(reading.label):
            continue
        if cycle and reading.dates:
            # The *date* has to belong to the cycle, not merely the sentence. A notice
            # citing a rule from years earlier mentions both, and reading the sentence's
            # year let the rule's date through as a milestone.
            try:
                year = int(reading.dates[0].iso[:4])
                wanted = int(cycle)
            except (ValueError, TypeError):
                year = wanted = 0
            if wanted and not (wanted - 1 <= year <= wanted + 2):
                continue
        if cycle and reading.cycle and reading.cycle != cycle:
            # And the passage's own cycle label, where it gives one. The two checks catch
            # different things: the label separates two cycles set out in one document, the
            # date's year catches a rule citation that borrowed the cycle's number.
            continue

        ev = _evidence(reading.span, doc, text,
                       reading=f'{reading.kind}: {reading.label}')
        if ev is None:
            continue

        key = (reading.kind, reading.dates[0].iso if reading.dates else '',
               reading.stage_ref.lower())
        if key in seen:
            continue
        seen.add(key)

        scope = Scope()
        if reading.stage_ref:
            scope = Scope([ScopeRef(ScopeKind.STAGE, _slug(reading.stage_ref),
                                    reading.stage_ref)])

        starts = ends = Fact()
        if reading.is_range:
            starts = Fact.verified(reading.dates[0].iso, ev)
            ends = Fact.verified(reading.dates[1].iso, ev)
        elif reading.dates:
            ends = Fact.verified(reading.dates[0].iso, ev)
        alternatives = [Fact.verified(d.iso, ev) for d in reading.dates[2:4]] \
            if reading.is_range else [Fact.verified(d.iso, ev) for d in reading.dates[1:3]]

        status = Status.VERIFIED
        note = ''
        if reading.state is MilestoneState.AWAITED:
            status = Status.VERIFIED
            note = 'the authority states this event exists but has not given a date for it'
        elif reading.precision is not DatePrecision.DAY:
            status = Status.NEEDS_REVIEW
            note = (f'the authority stated this to the nearest '
                    f'{reading.precision.value.lower()}; no day was printed and none is '
                    f'inferred')

        out.append(Milestone(
            id=f'date-{exam_id}-{_slug(reading.kind)}-{_slug(reading.label)[:16]}',
            label=reading.label,
            kind=reading.kind,
            scope=scope,
            cycle=reading.cycle or cycle,
            starts_at=starts,
            ends_at=ends,
            precision=reading.precision,
            state=reading.state,
            is_tentative=reading.tentative or None,
            alternatives=alternatives,
            status=status,
            note=note))
    return out


# ============================================================== reconciliation
def _same_event(a: Milestone, b: Milestone) -> bool:
    """Do these two milestones talk about the same thing?

    Same kind, same scope and same cycle. Scope is what keeps "Paper I on the 3rd" and
    "Paper II on the 5th" from looking like a contradiction -- they are two events, not one
    event stated twice.
    """
    return (a.kind == b.kind
            and str(a.scope) == str(b.scope)
            and (a.cycle or '') == (b.cycle or ''))


#: Source kinds that carry later news than a notification, in the order the brief sets out.
_AUTHORITY_ORDER = {
    'CORRIGENDUM': 0,
    'EXAM_PAGE': 1,
    'NOTIFICATION': 2,
    'APPLICATION_PAGE': 3,
    'OTHER_OFFICIAL': 4,
}


def reconcile(groups: list[tuple[SourceDocument, list[Milestone]]]) -> list[Milestone]:
    """One timeline from several documents, keeping every version of every event.

    A revision supersedes what it revises and says which document made the change. A plain
    disagreement -- two documents, two dates, neither claiming to correct the other -- is
    left as NEEDS_REVIEW on both, because choosing between two official documents on their
    order in a list is the failure this pipeline exists to avoid.
    """
    flat: list[tuple[SourceDocument, Milestone]] = [
        (doc, m) for doc, milestones in groups for m in milestones]

    buckets: list[list[tuple[SourceDocument, Milestone]]] = []
    for doc, milestone in flat:
        for bucket in buckets:
            if _same_event(bucket[0][1], milestone):
                bucket.append((doc, milestone))
                break
        else:
            buckets.append([(doc, milestone)])

    out: list[Milestone] = []
    for bucket in buckets:
        if len(bucket) == 1:
            out.append(bucket[0][1])
            continue

        # A document that says it is revising something is the later word by its own
        # account, not by where it happened to sit in the list.
        # A revision changes a date, so both sides need one. Without this, undated
        # statements of the same kind were superseded by whichever of them happened to
        # carry revision wording.
        revising = [(d, m) for d, m in bucket
                    if m.state in (MilestoneState.RESCHEDULED, MilestoneState.POSTPONED,
                                   MilestoneState.CANCELLED)
                    and m.effective_date is not None]
        dated = [m for _d, m in bucket if m.effective_date is not None]
        if len(dated) < 2:
            revising = []
        distinct = {m.effective_date for _d, m in bucket}

        if len(distinct) == 1:
            # Same answer from several documents. Corroboration, so keep one with all of
            # the evidence behind it.
            keeper = bucket[0][1]
            for _d, other in bucket[1:]:
                for fact_name in ('starts_at', 'ends_at'):
                    target = getattr(keeper, fact_name)
                    # Keyed on the document as well as the words. Two authorities' pages
                    # stating the same sentence are two sources agreeing, and collapsing
                    # them on the span alone discards exactly the corroboration that makes
                    # the value more trustworthy than a single reading.
                    known = {(e.source_id, e.span_digest) for e in target.evidence}
                    for ev in getattr(other, fact_name).evidence:
                        if (ev.source_id, ev.span_digest) not in known:
                            target.evidence.append(ev)
            out.append(keeper)
            continue

        if revising:
            newer_doc, newer = revising[0]
            for doc, older in bucket:
                if older is newer:
                    continue
                older.superseded_by = newer.id
                older.note = (older.note + ' ' if older.note else '') + (
                    f'replaced by a later official document that states this event was '
                    f'{newer.state.value.lower()}')
                out.append(older)
            newer.supersedes = bucket[0][1].id if bucket[0][1] is not newer else ''
            newer.revision_source_id = newer_doc.id
            out.append(newer)
            continue

        # Two official documents, two dates, neither correcting the other.
        listed = ', '.join(sorted(str(d) for d in distinct))
        for _doc, milestone in bucket:
            milestone.status = Status.NEEDS_REVIEW
            milestone.note = (
                f'{len(bucket)} official sources give different dates for this event '
                f'({listed}) and none of them says it is correcting the others. Both '
                f'readings are kept; the field is not published until the disagreement is '
                f'resolved against the documents.')
            out.append(milestone)

    out.sort(key=lambda m: (m.effective_date or '9999', m.kind))
    return out
