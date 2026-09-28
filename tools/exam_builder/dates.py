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


#: The words that make a date part of a document reference: "Notification No. 02/2024,
#: Dt. 19/02/2024", "G.O.Ms.No.29, dated 08-02-2024", "vide Memo No. 12 dated ...". Such a
#: date says when a document was issued, not when anything happens.
_CITATION_BEFORE = re.compile(
    r'(?:notification|notice|advt|advertisement|g\.?\s?o\.?(?:\s*\(?\w+\)?)?|memo|letter|circular|'
    r'order|proceedings?|rc|lr)\.?\s*(?:ms\.?\s*|rt\.?\s*)?(?:no|number)\.?\s*[:.]?\s*[\w/()\-]{1,20}'
    r'[\s,]*(?:\(?\s*dated|dt)\.?\s*[:.\-]?\s*$', re.I)


#: An earlier document's issue date, named in reference to it: "In continuation to the
#: notification of certificates verification issued on 09/04/2031". Without the reference
#: marker, "Notification published on X" is the event itself and is not a citation.
_ISSUED_BEFORE = re.compile(r'(?:in\s+continuation|with\s+reference|further\s+to|\bvide\b|\bas\s+per\b|'
                            r'\breferred)[^.]{0,90}\b(?:issued|published|released)\s+(?:on|dated)\s*$',
                            re.I)


def _cited(text: str, start: int) -> bool:
    before = text[max(0, start - 70):start]
    if re.search(r'(?:^|[\s(,])(?:dt|dated)\.?\s*[:.\-]?\s*$', before, re.I):
        # "Dt. 19/02/2031", "dated 08-02-2031": the date a document carries, not an event.
        return True
    return bool(_CITATION_BEFORE.search(before)
                or _ISSUED_BEFORE.search(text[max(0, start - 180):start]))


def _uncited_dates(text: str) -> list[ReadDate]:
    # A date listed with a cited one ("issued on 09/04/2031, 24/04/2031 & 06/06/2031") is
    # cited too: the list is one reference.
    out: list[ReadDate] = []
    previous: ReadDate | None = None
    previous_cited = False
    for d in read_dates(text):
        joined = previous is not None and re.fullmatch(
            r'[\s,&]*(?:and\s*)?', text[previous.end:d.start], re.I)
        cited = _cited(text, d.start) or bool(joined and previous_cited)
        if not cited:
            out.append(d)
        previous, previous_cited = d, cited
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
              r'modif\w+\s+(?:of\s+)?(?:the\s+)?application',
              # The noun first: "Application Edit Option From X To Y".
              r'application\s+(?:form\s+)?(?:edit|correction|modification)\w*')),
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
              r'last\s+date[^.]{0,40}\bapplication', r'closing\s+date[^.]{0,30}\bapplication',
              # A window stated as a pair of ends rather than as an act of applying:
              # "Applications From X To Y", "Apply online from X to Y", "Applications are
              # invited from X up to Y", "Online application starts X and closes Y".
              r'\bapplications?\s*(?:are\s+|will\s+be\s+)?(?:invited\s+|accepted\s+|received\s+)?'
              r'(?:online\s+)?(?:from|between)\b',
              r'\bapply\s+(?:online\s+)?(?:from|between)\b',
              r'\b(?:online\s+)?applications?\s+(?:window\s+|process\s+|portal\s+)?'
              r'(?:starts?|opens?|begins?|commences?|closes?|ends?)\b',
              r'\b(?:submission|registration)\s+(?:window\s+)?(?:starts?|opens?|begins?|commences?|ends?|closes?)\b',
              # A recruitment listing's row: "Start Date: X End Date Y". Only the pair, and
              # only bare: a lone "end date" says nothing about what ends.
              r'\bstart\s+date\b\s*:?\s*[^\n]{0,40}?\bend\s+date\b'),
             against=(r'\bfee\b.{0,20}\bpayment\b',
                      r'\b(?:start|end)\s+date\s+of\s+(?:the\s+)?(?:exam\w*|test|fee|payment)\b')),
    EventCue('ADMIT_CARD',
             # "Hall Ticket Numbers" is how candidates are listed, not an admit-card event.
             (r'(?:e-?\s?)?admit\s+cards?', r'call\s+letters?',
              r'hall\s+tickets?(?!\s+(?:no|nos|numbers?)\b)'),
             against=(r'\bcity\s+intimation\b',)),
    EventCue('CITY_INTIMATION',
             (r'city\s+intimation', r'intimation\s+of\s+(?:exam\w*\s+)?city',
              r'exam(?:ination)?\s+city\s+(?:slip|intimation|details)')),
    EventCue('ANSWER_KEY',
             (r'answer\s+keys?', r'tentative\s+keys?', r'provisional\s+keys?')),
    EventCue('RESULT',
             (r'\bresults?\b', r'declaration\s+of\s+result', r'merit\s+list',
              r'(?:general\s+)?ranking\s+list', r'\brank\s+list')),
    # Choosing posts and zones after the written stage: "web options", "option entry",
    # "exercise of options". A milestone of its own, not a verification and not a result.
    EventCue('OPTION_ENTRY',
             (r'\bweb[\s-]*options?\b', r'\boption\s+entry\b', r'\bexercis\w*\s+(?:of\s+)?options?\b',
              r'\bchoice\s+filling\b')),
    EventCue('INTERVIEW',
             (r'\binterviews?\b', r'personality\s+test', r'viva[\s-]?voce')),
    EventCue('SKILL_TEST',
             (r'skill\s+test', r'typing\s+test', r'proficiency\s+test',
              r'computer\s+(?:knowledge|proficiency)\s+test', r'\bdest\b')),
    EventCue('PHYSICAL_TEST',
             (r'physical\s+(?:efficiency|standard|measurement)\s+test',
              r'\bpet\b', r'\bpst\b', r'physical\s+test',
              r'medical\s+(?:examination|board|test)\b')),
    EventCue('DOCUMENT_VERIFICATION',
             (r'document\s+verification', r'verification\s+of\s+documents?',
              r'scrutiny\s+of\s+documents?', r'verification\s+of\s+certificates?',
              r'certificates?\s+verification')),
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
              # "Schedule of Main Examination", "Schedule of Preliminary Test": the
              # authority names the stage between "schedule of" and the noun.
              r'schedule\s+of\s+(?:the\s+)?(?:[\w()]+\s+){0,3}?(?:exam(?:ination)?|test)\b',
              r'conduct\s+of\s+(?:the\s+)?exam(?:ination)?',
              # An examination being moved is still an examination. Without these the
              # lifecycle wording carried the event and the cue set did not recognise it.
              r'exam(?:ination)?\s+scheduled\s+(?:for|on|to\s+be\s+held)',
              r'exam(?:ination)?[^.]{0,60}\b(?:has|have|stands?)\s+been\s+'
              r'(?:postponed|cancell?ed|rescheduled|deferred|preponed)',
              r'exam(?:ination)?[^.]{0,40}\bwill\s+now\s+be\s+held',
              # What already happened: "on the basis of Mains examinations held from X to Y".
              r'exam(?:ination)?s?\s+(?:was\s+|were\s+)?held\s+(?:from|on|between)\b'),
             against=(r'\badmit\s+card\b', r'\banswer\s+key\b', r'\bresult\b',
                      r'\bfee\b', r'\bapplication\s+form\b')),
    EventCue('NOTIFICATION',
             (r'notification\s+(?:is|was|shall\s+be|will\s+be)?\s*'
              r'(?:published|issued|released|dated)',
              r'date\s+of\s+(?:the\s+)?(?:notification|advertisement|notice)',
              r'advertisement\s+(?:is|was)\s+(?:published|issued)')),
)

#: Words that say a stated date is not final. An authority's own hedge, not our doubt.
#: "Provisional" hedges a date only where it qualifies one ("provisional schedule", "dates are
#: provisional"); a "PROVISIONAL LIST OF HALL TICKET NUMBERS" beside a date says the list may
#: change, not the day.
_TENTATIVE = re.compile(
    r'\btentativ\w+\b|\bprovisional(?:ly)?\s+(?:date|dates|schedule|scheduled|calendar|time\s*table)\b|'
    r'\b(?:date|dates|schedule)\s+(?:is|are)\s+provisional\b|\blikely\b|\bexpected\b|'
    r'\bsubject\s+to\s+change\b|\bmay\s+(?:be\s+)?(?:change|vary)\b|\bindicative\b', re.I)

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

#: A stage the authority names rather than numbers: "Schedule of Preliminary Test", "Main
#: Examination". Only the stage *words* are listed; which stage of which exam they belong to is
#: whatever the document says. "Preliminary" alone is not a stage ("preliminary key"), so the
#: noun of an examination has to follow it.
_STAGE_NAME = re.compile(
    r'\b(preliminary\s+(?:written\s+)?(?:test|exam(?:ination)?|stage)|prelims?\b(?:\s+exam(?:ination)?)?|'
    r'screening\s+test|main\s*\(?\s*(?:written\s*|conventional\s*)?\)?\s*(?:exam(?:ination)?|test|stage)|mains\b|'
    # The noun first: "Dates of Online Examination – Preliminary (tentative)".
    r'(?:exam(?:ination)?|test)\s*[-–—:(]\s*(?:preliminary|prelims?|mains?)\b)', re.I)

#: The two ends of a window, stated with verbs rather than with "from ... to".
_OPENS = re.compile(r'\b(?:starts?|opens?|begins?|commences?|opening\s+date|start\s+date|from)\b', re.I)
_CLOSES = re.compile(r'\b(?:closes?|ends?|last\s+date|closing\s+date|deadline|up\s*to|upto|till|to)\b', re.I)
_OPEN_THEN_CLOSE = re.compile(
    r'\b(?:starts?|opens?|begins?|commences?)\b.{0,80}?\b(?:closes?|ends?|last\s+date)\b', re.I)

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
    #: True where a single application date is stated as the *opening* of the window.
    opens_only: bool = False


def _label_for(passage: str, kind: str) -> str:
    """The authority's own wording for this event, trimmed to a label.

    Taken from the passage rather than composed, so the timeline reads in the authority's
    words. Where the passage is a table row the label is the part before the date.
    """
    text = normalise_ws(passage)
    dates = read_dates(text)
    if dates:
        head = text[:dates[0].start].strip(' :|-–—\t')
        if re.search(rf'\b(?:{_MONTH_WORD})\s*/\s*$', head, re.I):
            # "May/June 2024": the authority gave alternative months, and cutting the label
            # at the date read would leave "May/" and hide that the month is not settled.
            head = text[:dates[0].end].strip(' :|-–—\t')
        head = re.sub(r'^\d{1,2}(?:\.\d{1,2})*\s*[.)]?\s*', '', head).strip()
        if '|' in head:
            # A listing row: the first cells name the recruitment, the last one labels the
            # date. "02/2024 - GROUP-I SERVICES | Start Date" labels nothing as a whole.
            head = head.split('|')[-1].strip(' :-–—')
            if re.fullmatch(r'start\s+date', head, re.I) and re.search(r'\bend\s+date\b', text, re.I):
                # The row's two labels, as it prints them: the window's rows carry both.
                head = 'Start Date / End Date'
        # "Applications From: X To: Y" labels a window, and the window's two rows (opening,
        # closing) each carry the label; a dangling "From" would describe only one of them.
        bare = re.sub(r'\s*\b(?:from|between)\s*[:\-–—]?\s*$', '', head, flags=re.I).strip()
        head = bare if _is_a_label(bare) else head
        if 3 <= len(head) <= 90:
            return head
    trimmed = re.sub(r'^\d{1,2}(?:\.\d{1,2})*\s*[.)]?\s*', '', text).strip()
    return (trimmed[:90] or kind.replace('_', ' ').title()).strip()


def _nearest_cue(context: str, passage: str) -> EventCue | None:
    """The cue a date sits beside, when the date's own line carries no cue.

    A schedule lays its label and its date on separate lines, and the neighbourhood of a
    date line holds *both* the label above it ("Schedule of Main Examination") and whatever
    comes after it ("Submission of online applications is mandatory ..."). Taking the first
    cue in list order read a main-examination month as an application deadline. The cue
    whose wording ends nearest *before* the date line is the label of that line; only where
    no cue precedes it does the first match anywhere in the neighbourhood stand.
    """
    low = context.lower()
    at = low.find(normalise_ws(passage).lower()[:40])
    end = at + len(normalise_ws(passage)) if at >= 0 else -1
    best: tuple[int, EventCue] | None = None
    overlapping: EventCue | None = None
    fallback: EventCue | None = None
    for cue in EVENT_CUES:
        if not cue.matches(context):
            continue
        fallback = fallback or cue
        if at < 0:
            continue
        for anchor in cue.anchors:
            for m in re.finditer(anchor, low):
                if m.end() <= at:
                    gap = at - m.end()
                    if best is None or gap < best[0]:
                        best = (gap, cue)
                elif overlapping is None and m.start() < end:
                    # A label split across the line break ("Last Date & Time for receipt of"
                    # / "Online Applications 14/03/2024") reaches into the date line. It is
                    # still this line's label, and it outranks a cue on the line *after*.
                    overlapping = cue
    if best or overlapping:
        return best[1] if best else overlapping
    # Only a cue *after* the date line. That is a table whose label sits below its date --
    # unless the line above never finished its sentence, in which case the date belongs to
    # that sentence and the sentence pass reads it with its grammar.
    return None if _mid_sentence(context, at) else fallback


#: A colon that introduces a value rather than ending a sentence: "... dated:" / "19/02/2031".
_VALUE_COLON = re.compile(r'\b(?:dated|dt|on|from|to|no|nos|number|date|w\.e\.f)\.?\s*:\s*$', re.I)


def _ends_sentence(text: str) -> bool:
    text = (text or '').rstrip()
    if _VALUE_COLON.search(text):
        return False
    return bool(re.search(r'[.:;!?)]\s*$', text))


def _mid_sentence(context: str, at: int) -> bool:
    before = context[:at].rstrip() if at > 0 else ''
    return bool(before) and not _ends_sentence(before)


def _without_dates(text: str) -> str:
    out = text or ''
    for d in sorted(read_dates(out), key=lambda d: -d.start):
        out = out[:d.start] + ' ' + out[d.end:]
    return out


def _cue_beside_dates(passage: str) -> EventCue | None:
    """The event this passage's dates belong to.

    A passage may carry two events' words -- "picked up for Certificate Verification on the
    basis of Mains examinations held from X to Y" -- and the dates belong to the one whose
    wording ends nearest before them. Where no cue precedes the first date, list order
    decides, as before.
    """
    matching = [c for c in EVENT_CUES if c.matches(passage)]
    if len(matching) < 2:
        return matching[0] if matching else None
    low = passage.lower()
    firsts = [d for d in read_dates(passage) if not _cited(passage, d.start)]
    if not firsts:
        return matching[0]
    at = firsts[0].start
    best: tuple[int, int, EventCue] | None = None
    for rank, cue in enumerate(matching):
        for anchor in cue.anchors:
            for m in re.finditer(anchor, low):
                if m.end() <= at + 1:
                    key = (at - m.end(), rank)
                    if best is None or key < best[:2]:
                        best = (key[0], key[1], cue)
    return best[2] if best else matching[0]


def read_statement(passage: str, *, context: str = '', lead: str = '') -> DateReading | None:
    """What event, if any, this passage states — and the date it gives for it.

    `lead` is the statement immediately before the passage. Where the passage names no event
    and the lead does, the two are one row laid out on two lines ("Schedule of Main
    Examination" / "(Conventional Type) September/October 2024"): the lead supplies the event
    *and* the stage, and the evidence span is the two together, so the words that decided the
    reading are inside the evidence rather than beside it.
    """
    # The passage first: a table row names its own event, and classifying it by its
    # neighbours read "Date of examination" as an application window because the row above
    # it mentioned applications.
    cue = _cue_beside_dates(passage)
    haystack = passage
    stated = passage
    if cue is None and context:
        # Only now the neighbourhood, for a row whose label and date are on separate lines.
        haystack = context
        cue = _nearest_cue(context, passage)
        if (cue is not None and lead and not read_dates(lead)
                and (cue.matches(lead) or cue.matches(f'{lead} {passage}'))):
            # The label is the lead, or the lead and the date line together: "Last Date &
            # Time of submission of Online" / "Application 17/08/2031 at 5:00 PM".
            stated = f'{normalise_ws(lead)} {normalise_ws(passage)}'
    if cue is None:
        return None
    # Hedging and lifecycle are read from the wider text either way, because "the above
    # dates stand postponed" is a statement about its neighbours by design.
    wider = context or passage

    # Citations are judged with the end of the line above in view, and a list of dates is one
    # reference: "issued on 09/04/2031, 20/04/2031 &" / "22/04/2031 the following ...".
    tail = normalise_ws(lead)[-160:] + ' ' if lead else ''
    kept = {d.start - len(tail) for d in _uncited_dates(tail + passage) if d.start >= len(tail)}
    own = read_dates(passage)
    if own:
        # The line's own dates decide. Where every one of them is a citation, the line states
        # no event date, and the neighbours' dates are not borrowed to give it one.
        dates = [d for d in own if d.start in kept]
    else:
        dates = _uncited_dates(haystack)
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

    # A stage is read only from the statement itself (and its label line), never from a
    # neighbour after it: the line below a Preliminary schedule is often the Main one.
    stage = _STAGE_REF.search(stated) or _STAGE_NAME.search(stated)
    if not stage and lead and stated.lstrip().startswith('('):
        # "... on the basis of the Main" / "(Written) Examination held from X": the stage's
        # name began on the line above and its bracket continues it.
        stage = _STAGE_NAME.search(normalise_ws(lead)[-40:] + ' ' + stated[:80])
    # A cycle label is a year written as a label ("the examination for 2031"), never the year
    # inside a date: a notice for one cycle dates its later milestones in the next year.
    cycle_match = _CYCLE.search(_without_dates(passage)) or _CYCLE.search(_without_dates(haystack))
    precision = dates[0].precision if dates else DatePrecision.UNSPECIFIED
    is_range = bool(len(dates) >= 2 and (_RANGE.search(stated) or _OPEN_THEN_CLOSE.search(stated)))
    # One application date stated as the opening of the window is the opening, not the
    # deadline: "Online application starts on X" must not become the last date.
    opens_only = bool(cue.kind == 'APPLICATION_WINDOW' and len(dates) == 1
                      and _OPENS.search(stated) and not _CLOSES.search(stated))

    return DateReading(
        kind=cue.kind,
        label=_label_for(stated, cue.kind),
        span=normalise_ws(stated),
        dates=dates,
        is_range=is_range,
        tentative=bool(_TENTATIVE.search(wider)),
        state=state,
        stage_ref=normalise_ws(stage.group(1)) if stage else '',
        cycle=cycle_match.group(1) if cycle_match else '',
        precision=precision,
        opens_only=opens_only)


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

    consumed: set[int] = set()
    for index, passage in enumerate(parts):
        if index in consumed:
            continue
        if not read_dates(passage) and not _AWAITED.search(passage):
            continue
        nxt = parts[index + 1] if index + 1 < len(parts) else ''
        joins = (len(read_dates(passage)) == 1 and re.search(r'\bfrom\b', passage, re.I)
                 and ((not _CLOSES.search(passage[read_dates(passage)[0].end:])
                       and re.match(r'\s*(?:to|till|up\s*to|upto)\b', nxt, re.I))
                      # "... held from 21/10/2031 to" / "27/10/2031 for the recruitment ..."
                      or (re.search(r'\b(?:to|till|up\s*to|upto|and)\s*$', passage, re.I)
                          and read_dates(nxt) and read_dates(nxt)[0].start < 3))
                 and read_dates(nxt))
        if joins:
            # A window broken over two lines: "... From: 23/03/2031 at 10:00 A.M." /
            # "To: 27/03/2031 at 5:00 P.M." is one statement with two ends.
            passage = f'{passage} {nxt}'
            consumed.add(index + 1)
        reading = read_statement(passage, context=_window(parts, index),
                                 lead=parts[index - 1] if index else '')
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

        kind = 'APPLICATION_START' if reading.opens_only else reading.kind
        key = (kind, reading.dates[0].iso if reading.dates else '',
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
        elif reading.dates and reading.opens_only:
            starts = Fact.verified(reading.dates[0].iso, ev)
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
            # A recurring event (a verification spell, a medical board day) is one event per
            # date: its rows share a label, and an id without the date made two days one event
            # stated twice -- a conflict that was not there.
            id=(f'date-{exam_id}-{_slug(kind)}-{_slug(reading.label)[:16]}'
                + (f'-{reading.dates[0].iso}' if kind in _RECURRING_KINDS and reading.dates else '')),
            label=reading.label,
            kind=kind,
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
    taken = {(m.kind, m.effective_date or '') for m in out}
    taken |= {(m.kind, m.starts_at.value) for m in out if m.starts_at.has_value}
    taken |= {(m.kind, m.ends_at.value) for m in out if m.ends_at.has_value}
    taken |= {(m.kind, a.value) for m in out for a in m.alternatives if a.has_value}
    placed = [(f.value, f.evidence[0].span) for m in out
              for f in (m.starts_at, m.ends_at, *m.alternatives) if f.has_value and f.evidence]
    out.extend(_sentence_milestones(doc, text, exam_id=exam_id, cycle=cycle, taken=taken,
                                    placed=placed))
    return out


# ================================================================ sentences
_LIST_START = re.compile(r'^\s*(?:\(?\d{1,2}\)|\d{1,2}[.)]|\(?[ivx]{1,4}\)|[a-z]\))\s')
_NEW_PREDICATE = re.compile(r'\b(?:scheduled|to\s+be\s+held|will\s+be\s+held|would\s+be\s+held|'
                            r'held\s+on|shall\s+be\s+held)\b', re.I)
_FOLLOWING_DATE = re.compile(r'\b(?:on\s+the\s+)?(?:following|below|under)[\s-]*(?:mentioned\s+)?dates?\s*[.:]?\s*$', re.I)


def _paragraph_sentences(text: str) -> list[str]:
    """Sentences, rejoined across the line breaks a PDF puts inside them.

    A line is joined to the one before unless that one ended a sentence, the line opens a
    list item, or the line is a bare number (a roll of hall-ticket numbers is not prose).
    """
    paragraphs: list[str] = []
    current = ''
    for raw in (text or '').replace('\r', '').split('\n'):
        line = raw.strip()
        if not line or re.fullmatch(r'[\d\s]+', line):
            if current:
                paragraphs.append(current)
                current = ''
            continue
        if current and not _ends_sentence(current.rstrip(')')) and not _LIST_START.match(line):
            current = f'{current} {line}'
        else:
            if current:
                paragraphs.append(current)
            current = line
    if current:
        paragraphs.append(current)
    out: list[str] = []
    for para in paragraphs:
        out.extend(p.strip() for p in re.split(r'(?<=[.;])\s+(?=[A-Z(])', para) if p.strip())
    return out


def _sentence_milestones(doc: SourceDocument, text: str, *, exam_id: str, cycle: str,
                         taken: set, placed: list | None = None) -> list[Milestone]:
    """Milestones whose statement runs across lines, or that share a sentence with another.

    "... picked up for Certificate Verification on the basis of Mains examinations held
    from X to Y ..., scheduled to be held on A, B & C" is one sentence with two events.
    Each group of dates goes to the event whose words precede it; a new predicate
    ("scheduled to be held on") after an event already given its dates goes back to the
    sentence's first event still without dates -- the sentence's subject. Nothing already
    read by the line pass is read again.
    """
    sentences = _paragraph_sentences(text)
    single_lines = {normalise_ws(l) for l in (text or '').replace('\r', '').split('\n') if l.strip()}
    # The dates the line pass placed, with the statement it placed them from. A date is not
    # read again from a sentence containing that same statement; another event on the same
    # day, stated elsewhere, is still its own milestone.
    used = [(iso, normalise_ws(span)) for iso, span in (placed or [])]
    out: list[Milestone] = []
    for n, sentence in enumerate(sentences):
        kinds_here = {c.kind for c in EVENT_CUES if c.matches(sentence)}
        if normalise_ws(sentence) in single_lines and len(kinds_here) < 2:
            # One line, one event: the line pass has read it already.
            continue
        dates = _uncited_dates(sentence)
        if not dates and _FOLLOWING_DATE.search(sentence) and n + 1 < len(sentences):
            nxt = sentences[n + 1]
            nd = _uncited_dates(nxt)
            if nd and nd[0].start <= 2:
                sentence = f'{sentence} {nxt}'
                dates = _uncited_dates(sentence)
        # A running footer inside a sentence the PDF broke across a page is removed, not
        # read as a reason to drop the sentence.
        sentence = re.sub(r'\bpage\s*\d+\s*of\s*\d+\b', ' ', sentence, flags=re.I)
        dates = _uncited_dates(sentence)
        if not dates or _FURNITURE.search(sentence):
            continue
        low = sentence.lower()
        hits = []
        for cue in EVENT_CUES:
            if not cue.matches(sentence):
                continue
            for anchor in cue.anchors:
                for m in re.finditer(anchor, low):
                    hits.append((m.start(), m.end(), cue))
        if not hits:
            continue
        hits.sort(key=lambda h: (h[0], -h[1]))
        bound: dict[int, list[ReadDate]] = {}
        last_end: dict[int, int] = {}
        previous: tuple[ReadDate, int] | None = None
        for d in dates:
            if previous is not None and re.fullmatch(r'[\s,&]*(?:and\s*)?',
                                                     sentence[previous[0].end:d.start], re.I):
                # "14/04/2032, 15/04/2032 & 17/04/2032": a listed day of the same event.
                bound[previous[1]].append(d)
                last_end[previous[1]] = d.end
                previous = (d, previous[1])
                continue
            before = [i for i, h in enumerate(hits) if h[1] <= d.start]
            if not before:
                continue
            i = before[-1]
            if i in bound and _NEW_PREDICATE.search(sentence[last_end[i]:d.start]):
                # The new predicate's subject is the event the dated one qualifies: "picked up
                # for Certificate Verification on the basis of Mains examinations held from X
                # to Y, scheduled to be held on Z" -- the unbound event nearest before it.
                free = [j for j in before if j < i and j not in bound
                        and hits[j][2].kind != hits[i][2].kind]
                if not free:
                    continue
                i = free[-1]
            bound.setdefault(i, []).append(d)
            last_end[i] = d.end
            previous = (d, i)
        for i, ds in bound.items():
            start, end, cue = hits[i]
            if cycle:
                try:
                    wanted = int(cycle)
                    ds = [d for d in ds if wanted - 1 <= int(d.iso[:4]) <= wanted + 2]
                except ValueError:
                    pass
            # Additive only: a date the line pass already placed is not read again, under
            # any kind.
            flat_sentence = normalise_ws(sentence)
            ds = [d for d in ds if not any(iso == d.iso and span and span in flat_sentence
                                           for iso, span in used)]
            if not ds:
                continue
            key = (cue.kind, ds[0].iso)
            if key in taken:
                continue
            clause = sentence[start:ds[-1].end]
            span = normalise_ws(sentence) if len(sentence) <= 900 else normalise_ws(clause)
            ev = _evidence(span, doc, text, reading=f'{cue.kind}: {sentence[start:end]}')
            if ev is None and span != normalise_ws(clause):
                # The sentence as rejoined may not be verbatim (a footer removed from inside
                # it); the clause from the event's words to its date is.
                span = normalise_ws(clause)
                ev = _evidence(span, doc, text, reading=f'{cue.kind}: {sentence[start:end]}')
            if ev is None:
                continue
            taken.add(key)
            lead_words = ' '.join(sentence[:ds[0].start].split()[-5:])
            label = normalise_ws(f'{sentence[start:end].strip()} - {lead_words}')[:90]
            stage = _STAGE_REF.search(clause) or _STAGE_NAME.search(clause)
            stage_ref = normalise_ws(stage.group(1)) if stage else ''
            ranged = len(ds) >= 2 and re.search(r'\bfrom\b', sentence[start:ds[0].start], re.I) \
                and re.search(r'\b(?:to|till|up\s*to)\b', sentence[ds[0].end:ds[1].start], re.I)
            spread = len(ds) >= 2
            starts = Fact.verified(ds[0].iso, ev) if spread or ranged else Fact()
            ends = Fact.verified(ds[-1].iso, ev)
            precision = ds[0].precision
            status, note = Status.VERIFIED, ''
            if precision is not DatePrecision.DAY:
                status = Status.NEEDS_REVIEW
                note = (f'the authority stated this to the nearest {precision.value.lower()}; '
                        f'no day was printed and none is inferred')
            if spread and not ranged:
                note = (note + ' ' if note else '') + (
                    'held on the listed days ' + ', '.join(d.text for d in ds))
            out.append(Milestone(
                id=f'date-{exam_id}-{_slug(cue.kind)}-{ds[0].iso}',
                label=label, kind=cue.kind,
                scope=Scope([ScopeRef(ScopeKind.STAGE, _slug(stage_ref), stage_ref)]) if stage_ref else Scope(),
                cycle=cycle, starts_at=starts, ends_at=ends, precision=precision,
                state=MilestoneState.ANNOUNCED,
                # The event's own clause, not the sentence: "the provisional selection list is
                # drawn on ... and General Ranking List hosted on X" does not hedge X.
                is_tentative=bool(_TENTATIVE.search(clause)) or None,
                status=status, note=note))
    return out


# ============================================================== reconciliation
def _same_event(a: Milestone, b: Milestone) -> bool:
    """Do these two milestones talk about the same thing?

    Same kind, same scope and same cycle. Scope is what keeps "Paper I on the 3rd" and
    "Paper II on the 5th" from looking like a contradiction -- they are two events, not one
    event stated twice.
    """
    if a.kind in _RECURRING_KINDS and a.id != b.id:
        # Certificate verification, a medical board, an option round: an authority holds
        # these in spells, each announced in its own notice. Two spells on two dates are
        # two events, not one event stated twice -- only the same statement is the same event.
        return False
    # A statement with no cycle label belongs to the cycle of the record it was read into --
    # every document here passed the identity gate for one exam and one cycle. Two different
    # labels are two cycles; one label and none are one cycle stated twice. Requiring equality
    # kept a listing row ("07/2031 - …") and the notice it revises in separate buckets.
    return (a.kind == b.kind
            and str(a.scope) == str(b.scope)
            and (not a.cycle or not b.cycle or a.cycle == b.cycle))


#: Events an authority holds more than once in a cycle, each spell announced separately.
_RECURRING_KINDS = frozenset({'DOCUMENT_VERIFICATION', 'PHYSICAL_TEST', 'OPTION_ENTRY', 'INTERVIEW'})


#: Source kinds that carry later news than a notification, in the order the brief sets out.
_AUTHORITY_ORDER = {
    'CORRIGENDUM': 0,
    'EXAM_PAGE': 1,
    'NOTIFICATION': 2,
    'APPLICATION_PAGE': 3,
    'OTHER_OFFICIAL': 4,
}


#: Windows an authority extends after printing its notice. For these the authority's own
#: later page outranks the notice PDF -- but only as an extension. An examination date is
#: deliberately not here: two official documents naming two examination dates with neither
#: saying it corrects the other stay a disagreement (test H), and a rescheduling that says
#: so is already handled as a revision.
_EXTENDABLE_KINDS = frozenset({'APPLICATION_WINDOW', 'FEE_PAYMENT_END', 'CORRECTION_WINDOW'})


def _later_word(bucket):
    """The (document, milestone) that governs an extended window, or None.

    Only where the higher-ranked sources -- a corrigendum or the authority's examination
    page -- agree on one date among themselves, every other statement comes from a printed
    notice or below, and the higher-ranked date is *later* than each printed one: that is an
    extension. A page closing a window earlier than the notice is not how a window moves, so
    it stays a disagreement for a person to resolve, as does anything else.
    """
    if not bucket or bucket[0][1].kind not in _EXTENDABLE_KINDS:
        return None
    rank = lambda d: _AUTHORITY_ORDER.get(getattr(d.kind, 'value', str(d.kind)), 9)
    notice = _AUTHORITY_ORDER['NOTIFICATION']
    best = min(rank(d) for d, _m in bucket)
    if best >= notice:
        return None
    top = [(d, m) for d, m in bucket if rank(d) == best and m.effective_date is not None]
    if not top or len({m.effective_date for _d, m in top}) != 1:
        return None
    if any(notice > rank(d) > best for d, _m in bucket):
        return None
    governing = top[0][1].effective_date
    if any(m.effective_date and m.effective_date > governing for d, m in bucket if rank(d) > best):
        return None
    return top[0]


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

        governing = _later_word(bucket)
        if governing is not None:
            newer_doc, newer = governing
            for doc, older in bucket:
                if older is newer or older.effective_date == newer.effective_date:
                    continue
                printed = older.effective_date
                older.superseded_by = newer.id
                older.note = (older.note + ' ' if older.note else '') + (
                    f'the notice printed {printed}; the authority’s own '
                    f'{newer_doc.kind.value.replace("_", " ").lower()} states '
                    f'{newer.effective_date}, and that later word governs. The printed value '
                    f'is kept as superseded, not overwritten')
                newer.supersedes = older.id
                if (older.starts_at.has_value and newer.starts_at.has_value
                        and older.starts_at.value == newer.starts_at.value):
                    # The window was extended, not re-opened: the opening is still the
                    # notice's own statement, so it stays the primary source and the later
                    # page corroborates it.
                    known = {(e.source_id, e.span_digest) for e in older.starts_at.evidence}
                    newer.starts_at.evidence = list(older.starts_at.evidence) + [
                        e for e in newer.starts_at.evidence if (e.source_id, e.span_digest) not in known]
                out.append(older)
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
