"""Read an exam's examination pattern from whatever its authority published.

Four captured notices lay their scheme out four different ways (see PATTERN_AUDIT.md §8):
a clause-numbered heading over a flattened table whose duration cell spans every row; two
lettered headings over tables with a totals row; a phase heading with the penalty stated in
prose and the minimum marks split across category columns; and one with no table at all,
just labelled lines under the headings "Qualifying Papers" and "Papers to be counted for
merit". A reader built for any one of them reads none of the others, so nothing here keys
off an authority, an exam or a stage name.

What it does key off is structure and vocabulary that authorities share:

  * a heading that says a scheme, structure or pattern of examination follows;
  * a stage named by a label and an ordinal -- Tier-I, Phase II, Paper-A, Session-II -- or
    by the ordinary English words for an examination phase;
  * a table whose own header says what its columns hold, in the authority's order;
  * rows delimited by their own label, because a flattened PDF has no row boundaries;
  * rules stated in prose beside the table they govern.

Three rules run through all of it. A value is only a value if its span is verbatim in the
document. A number the authority printed and a number we computed from its numbers are
different things, and `Fact.derived_from` keeps them apart. And a row that does not fit its
columns is kept as NEEDS_REVIEW with its raw text, never dropped and never guessed at --
"we could not read this" and "the authority did not publish this" are different claims.
"""
from __future__ import annotations

import re

from .evidence import Evidence, EvidenceStatus
from .schema import (CategoryMinimum, DurationVariant, ExamPattern, Fact, NegativeMarking,
                     PatternLevel, PatternNode, QualifyingRule, SourceDocument,
                     SourceEvidence, Status)
from .tables import ColumnKind, _columns_in

# ==================================================================== vocabulary
#: Words for a level of an examination, and the label an authority writes beside an ordinal.
#: Structural vocabulary, not exam names: every one of these is ordinary English used by
#: many authorities, and which of them an exam uses is read from the document.
_LEVEL_WORDS: tuple[tuple[str, PatternLevel], ...] = (
    ('tier', PatternLevel.STAGE),
    ('phase', PatternLevel.STAGE),
    ('stage', PatternLevel.STAGE),
    ('round', PatternLevel.STAGE),
    ('paper', PatternLevel.PAPER),
    ('session', PatternLevel.PART),
    ('part', PatternLevel.PART),
    ('section', PatternLevel.SECTION),
    ('subject', PatternLevel.SUBJECT),
    ('module', PatternLevel.SECTION),
)

#: A heading announcing that the examination's structure follows.
_SCHEME_HEADING = re.compile(
    r'\b(?:scheme|structure|pattern|plan|design|composition|syllabus\s+and\s+scheme)\b'
    r'[^.\n]{0,40}?\b(?:exam\w*|test|selection|paper|recruitment|written)\b|'
    r'\b(?:exam\w*|test|written|selection)\b[^.\n]{0,20}?\b(?:scheme|structure|pattern)\b',
    re.I)

#: A stage of an examination, named by a label and an ordinal.
_STAGE_LABELLED = re.compile(
    r'\b(?P<label>tier|phase|stage|round|paper)\s*[-–—:\s]?\s*'
    r'(?P<ord>[IVXL]{1,4}|\d{1,2}|[A-H])\b', re.I)

#: A stage named by what it is rather than by a number. These are the ordinary English
#: words for a phase of a selection -- an authority that writes "Preliminary Examination"
#: and one that writes "Phase I" are describing the same thing, and neither spelling is
#: specific to any exam.
_STAGE_NAMED = re.compile(
    r'\b(?P<name>preliminary|prelims?|main|mains|final|screening|written|objective|'
    r'descriptive|interview|personality\s+test|viva[\s-]?voce|skill\s+test|typing\s+test|'
    r'physical\s+(?:test|standard|efficiency)|medical\s+(?:test|examination)|'
    r'computer\s+(?:proficiency|knowledge)\s+test|document\s+verification)\b'
    r'[\s\-–—]*(?P<kind>exam\w*|test|round)?', re.I)

#: A word that belongs to a table's header rather than to its contents. Used to tell a
#: category sub-heading from the header line above it.
_HEADER_WORD = re.compile(
    r'(?:of|the|and|for|no\.?|name|names|marks?|questions?|duration|time|medium|exam\w*|'
    r'test|tests|section|sections|paper|papers|subject|subjects|minimum|qualifying|'
    r'maximum|max\.?|total|sr\.?|sl\.?|serial|allotted|allowed|each)', re.I)


#: A heading that points at a part of the scheme from elsewhere rather than naming it:
#: "Section-III of Paper-I", "Part A of Section-I of Paper-I".
_CROSS_REFERENCE = re.compile(
    r'\b(?:of|in|for|from|under|within|i\.e\.|viz\.?)\b', re.I)

#: What else a notice heads with a heading. Every one of these is a real heading of a real
#: list, and none of them is the examination's structure.
_NOT_THE_SCHEME = re.compile(
    r'\b(?:syllabus|syllabi|curriculum|schedule|timetable|centres?|centers?|venue|'
    r'list|lists|annexure|appendix|index|instructions?|guidelines?|certificate|'
    r'format|pro\s*forma|undertaking|declaration|fee|fees|eligibility|vacanc\w+|'
    r'reservation|relaxation|qualifications?)\b', re.I)


#: How an authority marks a heading: a clause number, a lettered item, a colon, or
#: capitals. Every scheme heading read so far carries at least one of these, and the lines
#: that merely read like headings carry none.
_MARKED_HEADING = re.compile(
    r'^\s*(?:\d+(?:\.\d+)*[.)]?\s+\S|\(?[A-Za-z]\)?[.)]\s+\S)|[:：]')


def _is_marked(line: str) -> bool:
    text = (line or '').strip()
    if _MARKED_HEADING.search(text):
        return True
    letters = [c for c in text if c.isalpha()]
    return bool(letters) and sum(1 for c in letters if c.isupper()) / len(letters) > 0.8


#: The line a table's totals sit on.
_TOTAL_ROW = re.compile(r'^\s*(?:grand\s+)?total\b', re.I)

#: Page furniture, which sits in the middle of a table in a flattened PDF.
_FURNITURE = re.compile(
    r'^\s*(?:page\s+\d+\s+of\s+\d+|go\s+to\s+index\s*\d*|\d+\s*\|\s*page|'
    r'contd\.?|continued|annexure[\s-]*[ivxl\d]*)\s*$', re.I)

#: A clause number opening a line -- "13.8.2", "(iv)", "C." -- used to spot a prose rule
#: sitting under a table rather than another row of it.
_CLAUSE_PROSE = re.compile(r'^\s*(?:\d+(?:\.\d+)+|\([ivxlmcd]+\)|\([a-z]\))\s+\S')


# ================================================================== row labels
#: How a row of a flattened scheme table announces itself. Any of these begins a new row;
#: everything until the next one belongs to this one.
_ROW_LABEL = re.compile(
    r"""^\s*(?:
        \(?(?P<num>\d{1,3})\s*[.)]?\s+(?=\S)                      # 1 English Language
      | (?P<letter>[A-H])\s*[.):]\s*(?=\S|$)                      # A. General Intelligence
      | (?P<label>section|paper|part|phase|session|tier|stage|module|group)
        \s*[-–—:\s]?\s*(?P<ord>[IVXL]{1,4}|\d{1,2}|[A-H])\b
      | (?P<total>(?:grand\s+)?total)\b(?!\s*[=:])       # "Total =" is a cell, and
                                                          # the figure it sums may
                                                          # wrap to the next line
    )""",
    re.X | re.I)

#: A bare ordinal on its own line: the first column of a row whose cell spans the table.
_BARE_ORDINAL = re.compile(r'^\s*\(?\s*(?:\d{1,3}|[IVXL]{1,5}|[A-H])\s*[.)]?\s*$')


# ===================================================================== numbers
#: Marks written as their own arithmetic: "60*3 = 180" states 3 marks a question outright.
_MARKS_PRODUCT = re.compile(r'\b(\d{1,3})\s*[*x×]\s*(\d{1,3})\s*=\s*(\d{1,4})\b')
#: "Total = 60" inside a cell, where a merged row sums its own parts.
_CELL_TOTAL = re.compile(r'\btotal\s*=\s*(\d{1,4})\b', re.I)
_INTEGER = re.compile(r'(?<![\d.*/=-])(\d{1,4})(?:\*\*)?(?![\d.]|\s*[*×]\s*\d)')

_DURATION = re.compile(
    r'\b(?:(?P<h>\d{1,2})\s*(?:hours?|hrs?|hr)\b'
    r'(?:\s*(?:and|&)?\s*(?P<hm>\d{1,3})\s*(?:minutes?|mins?|min)\b)?'
    r'|(?P<m>\d{1,3})\s*(?:minutes?|mins?|min)\b)', re.I)

#: Who a second duration is for, in the authority's words.
_DURATION_GROUP = re.compile(
    r'\bfor\s+(?:the\s+)?candidates?\s+[^)\n]{0,90}|\bfor\s+(?:the\s+)?'
    r'(?:visually|hearing|physically)[^)\n]{0,60}', re.I)


def _minutes(text: str) -> int | None:
    m = _DURATION.search(text or '')
    if not m:
        return None
    if m.group('m'):
        return int(m.group('m'))
    total = int(m.group('h')) * 60
    if m.group('hm'):
        total += int(m.group('hm'))
    return total


# ============================================================ negative marking
_NEG_NONE = re.compile(
    r'\b(?:there\s+(?:will|shall)\s+be\s+)?no\s+negative\s+mark\w*|'
    r'\bnegative\s+mark\w*\s*[:\-]?\s*(?:nil|none|not\s+applicable|no)\b|'
    r'\bno\s+penalty\s+for\s+(?:wrong|incorrect)\b|'
    r'\bmarks?\s+(?:will|shall)\s+not\s+be\s+deducted\b', re.I)

_NEG_FLAT = re.compile(
    r'\bnegative\s+mark\w*\s*(?:of|will\s+be|:)?\s*(?:₹)?\s*(\d+(?:\.\d+)?)\s*marks?\b|'
    r'\b(\d+(?:\.\d+)?)\s*marks?\s+(?:will|shall)\s+be\s+deducted\b|'
    r'\bdeduction\s+of\s+(\d+(?:\.\d+)?)\s*marks?\b|'
    r'\bpenalty\s+of\s+(\d+(?:\.\d+)?)\s*marks?\b', re.I)

#: "one-third of the marks assigned to that question", "1/4th of the marks", "0.25 of the
#: marks" -- a share of the question's own marks rather than a flat figure.
_FRACTION_WORDS = {'half': 0.5, 'one-half': 0.5, 'one half': 0.5,
                   'one-third': 1 / 3, 'one third': 1 / 3, 'third': 1 / 3,
                   'one-fourth': 0.25, 'one fourth': 0.25, 'fourth': 0.25,
                   'one-quarter': 0.25, 'one quarter': 0.25, 'quarter': 0.25,
                   'one-fifth': 0.2, 'one fifth': 0.2}
_NEG_FRACTION = re.compile(
    r'\b(?P<word>one[\s-]?(?:third|fourth|quarter|fifth|half)|half|third|quarter)\b'
    r'(?:\s*\((?P<paren>\d*\.?\d+)\))?[^.\n]{0,60}?\bmarks?\b|'
    r'\b(?P<num>\d)\s*/\s*(?P<den>\d)\s*(?:th|rd|st|nd)?[^.\n]{0,40}?\bmarks?\b', re.I)

_NEG_CUE = re.compile(r'\bnegative\s+mark\w*|\bpenalty\b|\bdeduct\w*\b', re.I)


def read_negative_marking(passage: str) -> NegativeMarking | None:
    """The penalty an authority states, or None where it states nothing.

    None is not "no penalty": an authority that says nothing and an authority that says
    "there will be NO negative marks" are recorded differently, because a candidate who
    guesses freely on the strength of our silence is being misled by us.
    """
    text = ' '.join((passage or '').split())
    if not text:
        return None

    none_hit = _NEG_NONE.search(text)
    if none_hit:
        return NegativeMarking(as_printed=_sentence_around(text, none_hit.start()),
                               deducted_per_wrong=0.0)

    if not _NEG_CUE.search(text):
        return None

    flat = _NEG_FLAT.search(text)
    if flat:
        value = next(g for g in flat.groups() if g)
        return NegativeMarking(as_printed=_sentence_around(text, flat.start()),
                               deducted_per_wrong=float(value))

    share = _NEG_FRACTION.search(text)
    if share:
        if share.group('word'):
            key = share.group('word').lower().replace('-', ' ')
            fraction = _FRACTION_WORDS.get(key) or _FRACTION_WORDS.get(key.replace(' ', '-'))
            if share.group('paren'):
                fraction = float(share.group('paren'))
        else:
            fraction = int(share.group('num')) / int(share.group('den'))
        if fraction:
            return NegativeMarking(as_printed=_sentence_around(text, share.start()),
                                   fraction_of_marks=round(fraction, 4))

    # The cue fired and no shape matched. The wording is kept so a person can read it; no
    # number is invented, because the usual fraction of some other exam is not evidence.
    return NegativeMarking(as_printed=_sentence_around(text, _NEG_CUE.search(text).start()))


def _sentence_around(text: str, index: int, width: int = 220) -> str:
    start = max((text.rfind(c, 0, index) for c in '.;'), default=-1)
    end = text.find('.', index)
    out = text[start + 1: end + 1 if end != -1 else min(len(text), index + width)]
    return out.strip()[:300]


# ================================================================== qualifying
_QUALIFYING_ONLY = re.compile(
    r'\b(?:will|shall)\s+be\s+(?:a\s+)?qualifying\b|\bof\s+qualifying\s+nature\b|'
    r'\bqualifying\s+(?:paper|test|nature|in\s+nature)\b|'
    r'\bmarks?\s+there\s?of\s+will\s+not\s+be\s+counted\b|'
    r'\bwill\s+not\s+be\s+counted\s+for\s+(?:ranking|merit)\b|'
    r'\bnot\s+be\s+added\s+for\s+preparing\s+the\s+final\s+merit\b|'
    r'\bmarks?\s+obtained\s+[^.]{0,60}will\s+not\s+be\s+(?:counted|added)\b', re.I)
_MERIT_HEADING = re.compile(r'\b(?:papers?|tests?)\s+to\s+be\s+counted\s+for\s+merit\b|'
                            r'\bcounted\s+for\s+(?:the\s+)?merit\b', re.I)
_QUALIFYING_HEADING = re.compile(r'^\s*qualifying\s+(?:papers?|tests?)\s*:?\s*$', re.I)
_MIN_PERCENT = re.compile(
    r'\bminimum\s+qualifying\s+marks?\s+(?:fixed\s+)?(?:at|of)?\s*(\d{1,3}(?:\.\d+)?)\s*%|'
    r'\bqualify\w*\s+(?:marks?\s+)?(?:at|of)\s*(\d{1,3}(?:\.\d+)?)\s*%|'
    r'\b(\d{1,3}(?:\.\d+)?)\s*%\s*(?:minimum\s+)?qualifying\b', re.I)
_MIN_MARKS = re.compile(
    r'\bminimum\s+(?:qualifying\s+)?marks?\s+(?:fixed\s+)?(?:at|of)?\s*(\d{1,4})\b(?!\s*%)',
    re.I)


def read_qualifying(passage: str) -> QualifyingRule | None:
    """Whether a node counts towards the merit, and what clearing it takes."""
    text = ' '.join((passage or '').split())
    if not text:
        return None
    rule = QualifyingRule()
    only = _QUALIFYING_ONLY.search(text)
    if only:
        rule.is_qualifying_only = True
        rule.counts_towards_merit = False
        rule.as_printed = _sentence_around(text, only.start())
    percent = _MIN_PERCENT.search(text)
    if percent:
        rule.minimum_percent = float(next(g for g in percent.groups() if g))
        rule.as_printed = rule.as_printed or _sentence_around(text, percent.start())
    marks = _MIN_MARKS.search(text)
    if marks:
        rule.minimum_marks = float(marks.group(1))
        rule.as_printed = rule.as_printed or _sentence_around(text, marks.start())
    merit = _MERIT_HEADING.search(text)
    if merit and rule.counts_towards_merit is None:
        rule.counts_towards_merit = True
        rule.as_printed = rule.as_printed or _sentence_around(text, merit.start())
    return rule if (rule.as_printed or rule.minimum_marks is not None
                    or rule.minimum_percent is not None) else None


# =================================================== language, mode, question type
#: A medium cell says which languages a paper is set in. The languages themselves are not
#: listed here -- whatever the authority names is kept as it wrote it -- only the shapes
#: that mark a cell as being about language at all.
_LANGUAGE_CELL = re.compile(
    r'\b(?:english|hindi|urdu|bilingual|both\s+(?:the\s+)?languages?|'
    r'regional|vernacular|local\s+language|mother\s+tongue|'
    r'[a-z]{4,12}\s+(?:and|&|/)\s+[a-z]{4,12})\b', re.I)
_LANGUAGE_PROSE = re.compile(
    r'\b(?:questions?\s+papers?|papers?|questions?|test)\s+(?:will|shall|are|is)\s+'
    r'(?:be\s+)?(?:set|available|printed)\s+(?:both\s+)?in\s+([^.;\n]{4,120})|'
    r'\bmedium\s+of\s+(?:the\s+)?(?:exam\w*|test|paper)\s*(?:will\s+be|is|:)?\s*'
    r'([^.;\n]{3,80})|'
    r'\b(?:will|shall)\s+be\s+(?:set|conducted)\s+in\s+((?:english|hindi)[^.;\n]{0,80})',
    re.I)
_MODE = re.compile(
    r'\b(?:computer[\s-]based(?:\s+(?:test|exam\w*|mode))?|online|offline|'
    r'pen[\s-]and[\s-]paper|omr|written|paper[\s-]pencil|cbt)\b', re.I)
_QUESTION_TYPE = re.compile(
    r'\b(?:objective\s+type|objective|multiple\s+choice(?:\s+questions?)?|mcq|'
    r'descriptive|conventional(?:\s+essay[\s-]type)?|essay[\s-]type|'
    r'short\s+answer|practical|data\s+entry|typing)\b', re.I)
_SECTIONAL_TIMING = re.compile(
    r'\bsectional\s+tim\w*|\bseparately\s+timed\b|\bseparate\s+tim\w*\s+for\s+each\b|'
    r'\bwith\s+separate\s+timings?\s+for\s+each\b', re.I)


def _first(pattern: re.Pattern, text: str) -> str:
    m = pattern.search(text or '')
    if not m:
        return ''
    groups = [g for g in m.groups() if g] if m.groups() else []
    return (groups[0] if groups else m.group(0)).strip(' .,;:')[:160]


# ================================================================== extraction
def _evidence(span: str, doc: SourceDocument, text: str, *, reading: str,
              page: int | None = None) -> SourceEvidence | None:
    """Evidence whose span is verbatim in the document, or nothing at all."""
    ev = Evidence(span=span[:900], source_url=doc.url, document_title=doc.title,
                  page=page or 1, reading=reading)
    if ev.verify(text) is not EvidenceStatus.VERIFIED:
        return None
    out = SourceEvidence.from_evidence(ev, source=doc, source_id=doc.id)
    out.section = 'pattern'
    return out


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')[:44] or 'x'


def _fact(value, span: str, doc: SourceDocument, text: str, *, reading: str):
    ev = _evidence(span, doc, text, reading=reading)
    if ev is None:
        return Fact.needs_review(
            value, 'the value was read but its span could not be found verbatim in the '
                   'document, so it is not publishable as the authority’s own')
    return Fact.verified(value, ev)


class _Cursor:
    """Lines, with the small amount of state a walk over them needs."""

    def __init__(self, text: str) -> None:
        self.text = text
        self.lines = (text or '').split('\n')

    def joined(self, start: int, end: int) -> str:
        return ' '.join(l.strip() for l in self.lines[start:end] if l.strip())


# --------------------------------------------------------------- table reading
def _numeric_columns(columns: list) -> list:
    order = {ColumnKind.QUESTIONS: 0, ColumnKind.MARKS: 1, ColumnKind.QUALIFYING_MARKS: 2}
    return [c for c in columns if c.kind in order]


def _row_numbers(raw: str, *,
                 label: str = '') -> tuple[list[float], float | None, float | None, str]:
    """The numbers a row states, with the two shapes that carry their own arithmetic.

    "60*3 = 180" is a marks cell stating three marks a question, and "Total = 60" is a
    merged row summing its own parts. Both are consumed first so their parts are not
    counted again as separate figures.
    """
    working = raw
    # The row's own serial is a column, not a figure. Counting it made every row of one
    # table read as having one, two or three questions -- its serial number.
    if label and working.strip().startswith(label.strip()):
        working = working.strip()[len(label.strip()):]
    per_question: float | None = None
    product_total: float | None = None
    product = _MARKS_PRODUCT.search(working)
    if product:
        count, each, total = (int(product.group(1)), int(product.group(2)),
                              int(product.group(3)))
        if count * each == total:
            per_question, product_total = float(each), float(total)
            working = working.replace(product.group(0), ' ', 1)

    stated_total: float | None = None
    cell_total = _CELL_TOTAL.search(working)
    if cell_total:
        stated_total = float(cell_total.group(1))
        working = working.replace(cell_total.group(0), ' ', 1)

    # Durations are numbers too, and they belong to the duration column, not the marks one.
    working = _DURATION.sub(' ', working)
    numbers = [float(m.group(1)) for m in _INTEGER.finditer(working)]
    if stated_total is not None:
        numbers = [n for n in numbers if n != stated_total]
    return numbers, per_question, product_total, working


def _durations(raw: str) -> tuple[int | None, str, list[DurationVariant]]:
    """The row's duration, and any extra duration printed for a named group.

    One notice prints the ordinary time and, in the same cell, a longer time "for the
    candidates eligible for scribe". Taking the first figure and stopping would lose a
    concession a candidate may be entitled to; taking the longest would state the wrong
    time for everyone else.
    """
    matches = list(_DURATION.finditer(raw or ''))
    if not matches:
        return None, '', []
    main = matches[0]
    minutes = _minutes(main.group(0))
    variants: list[DurationVariant] = []
    for extra in matches[1:]:
        # Forward only: a concession follows the time it applies to. Searching backwards
        # as well let "sectional timer of 15 minutes for each subject" claim the scribe
        # concession printed above it in the same cell.
        tail = raw[extra.end(): extra.end() + 140]
        who = _DURATION_GROUP.search(tail)
        # And it has to be this figure's qualifier: anything past the next figure belongs
        # to that one.
        next_figure = _DURATION.search(tail)
        if not who or (next_figure and next_figure.start() < who.start()):
            continue
        value = _minutes(extra.group(0))
        if value is None or any(v.minutes == value for v in variants):
            continue
        variants.append(DurationVariant(minutes=value, as_printed=extra.group(0).strip(),
                                        applies_to=' '.join(who.group(0).split())[:120]))
    return minutes, main.group(0).strip(), variants



def _medium_text(raw: str) -> str:
    """The medium cell's own words: what is left of a row after its name and its figures.

    Read positionally rather than by a list of languages, for two reasons. Which languages
    an authority sets its papers in is its own business and cannot be enumerated in
    advance, and matching language-shaped text anywhere in the row picked words out of the
    subject name -- one row's medium came out as "Awareness / Digital" from "General/
    Economy/ Banking Awareness / Digital/ Financial Awareness".
    """
    text = _MARKS_PRODUCT.sub(' ', raw or '')
    first = re.search(r'\s\d', text)
    if not first:
        return ''
    tail = _DURATION.sub(' ', text[first.start():])
    tail = re.sub(r'\b\d+(?:\.\d+)?\b|\btotal\s*=\s*', ' ', tail)
    tail = re.sub(r'\s+', ' ', tail).strip(' .,;:*-')
    # A medium cell is short. Anything long is the row's own prose, not its medium.
    return tail[:60] if len(tail) <= 60 else ''


def _row_name(raw: str, label: str) -> str:
    """The row's own name: what is left once its label, numbers and times are taken out."""
    body = raw[len(label):] if label and raw.lower().startswith(label.lower()) else raw
    body = _MARKS_PRODUCT.sub(' ', body)
    body = _DURATION.sub(' ', body)
    body = re.sub(r'\([^)]*\)', ' ', body)
    cut = re.search(r'\s\d', body)
    if cut:
        body = body[:cut.start()]
    body = re.sub(r'\s+', ' ', body).strip(' .,;:-–—')
    return body[:120]


def _ordinal_value(label: str) -> tuple[str, int] | None:
    """A row label's place in its sequence: ('num', 2), ('alpha', 3), or None."""
    text = (label or '').strip().strip('.):-–— ')
    # "Paper-II" and "Section-III" carry their ordinal after the level word, so the
    # label is split on its separators and not on spaces alone. Without this a
    # labelled row left the sequence unset, and the next line beginning with a figure
    # -- "2 hours (2 hours and 40 minutes for ...)" -- opened a row called "hours".
    parts = [part for part in re.split(r'[^A-Za-z0-9]+', text) if part]
    tail = parts[-1] if parts else ''
    if tail.isdigit():
        return ('num', int(tail))
    roman = {'i': 1, 'ii': 2, 'iii': 3, 'iv': 4, 'v': 5, 'vi': 6, 'vii': 7, 'viii': 8,
             'ix': 9, 'x': 10}
    if tail.lower() in roman:
        return ('roman', roman[tail.lower()])
    if len(tail) == 1 and tail.isalpha():
        return ('alpha', ord(tail.upper()) - 64)
    return None


def _split_rows(cur: _Cursor, start: int, limit: int) -> list[tuple[str, list[str], int]]:
    """A flattened table's rows, delimited by the labels the rows themselves carry.

    A PDF gives no row boundaries: one cell's wrapping is several lines and one row's cells
    are several more. What survives is that every row in a scheme table names itself -- an
    ordinal, a letter, or a level word and an ordinal.

    The label alone is not enough, though, because the *middle* of a row begins with a
    number too: "35 30 English and" is Quantitative Aptitude's counts, not row 35. So a
    numbered or lettered label counts as a boundary only where it continues the sequence,
    which is how a row of figures is told from a row of its own.
    """
    rows: list[tuple[str, list[str], int]] = []
    current: list[str] | None = None
    label = ''
    row_start = start
    index = start
    sequence: tuple[str, int] | None = None

    def begin(new_label: str, line: str, at: int) -> None:
        nonlocal current, label, row_start
        if current is not None:
            rows.append((label, current, row_start))
        label, current, row_start = new_label, [line], at

    while index < min(limit, len(cur.lines)):
        line = cur.lines[index].strip()
        index += 1
        if not line or _FURNITURE.match(line):
            continue
        if _CLAUSE_PROSE.match(line) and len(line) > 60:
            break                                  # a rule under the table, not a row
        if len(line) > 90 and not line[:8].strip()[:1].isdigit():
            break                                  # a sentence, not a cell

        hit = _ROW_LABEL.match(line)
        if hit and not _BARE_ORDINAL.match(line):
            found = hit.group(0).strip()
            if hit.group('total'):
                # The sequence is deliberately kept: one notice prints its totals row in
                # the middle of the table and continues with row 5 after a page break.
                begin(found, line, index - 1)
                continue
            if hit.group('label'):
                # "Section-II", "Paper-III": a level word with its ordinal is unambiguous.
                begin(found, line, index - 1)
                sequence = _ordinal_value(found)
                continue
            place = _ordinal_value(found)
            expected = (sequence[1] + 1) if sequence else 1
            if place and (place[1] == expected
                          or (sequence is None and place[1] <= 2)):
                begin(found, line, index - 1)
                sequence = place
                continue
            # A number that does not continue the sequence belongs to the row in hand.
            if current is not None:
                current.append(line)
            continue

        if _BARE_ORDINAL.match(line) and current is None:
            continue                               # the stage's own ordinal cell
        if current is not None:
            current.append(line)
    if current is not None:
        rows.append((label, current, row_start))
    return rows


def _node_level(columns: list, label: str) -> tuple[PatternLevel, str]:
    """What the rows of this table are, from the column that names them."""
    for column in columns:
        if column.kind is ColumnKind.PAPER:
            return PatternLevel.PAPER, column.label
        if column.kind is ColumnKind.SECTION:
            return PatternLevel.SECTION, column.label
        if column.kind is ColumnKind.SUBJECT:
            return PatternLevel.SUBJECT, column.label
    for word, level in _LEVEL_WORDS:
        if re.match(rf'\s*{word}\b', label or '', re.I):
            return level, word.title()
    return PatternLevel.SECTION, ''


def _read_table_rows(cur: _Cursor, doc: SourceDocument, columns: list, start: int,
                     limit: int, *, prefix: str) -> tuple[list[PatternNode], dict]:
    """The nodes a scheme table's rows describe, plus the totals row if it has one."""
    nodes: list[PatternNode] = []
    totals: dict = {}
    numeric = _numeric_columns(columns)
    has_language = any(c.kind is ColumnKind.LANGUAGE for c in columns)
    level, level_label = _node_level(columns, '')

    for order, (label, block, at) in enumerate(_split_rows(cur, start, limit), start=1):
        raw = ' '.join(block)
        span = ' '.join(l.strip() for l in block if l.strip())
        numbers, per_question, product_total, residue = _row_numbers(raw, label=label)
        minutes, duration_text, variants = _durations(raw)

        if _TOTAL_ROW.match(label or ''):
            if not _CELL_TOTAL.search(raw):
                totals = {'numbers': numbers, 'minutes': minutes, 'span': span}
            continue

        name = _row_name(raw, label)
        node_level, node_label = (level, level_label)
        by_label = _node_level(columns, label)
        if by_label[0] is not level and label:
            node_level, node_label = by_label
        node = PatternNode(
            id=f'{prefix}-{_slug(name or label or str(order))}',
            level=node_level, level_label=node_label, name=name or label.strip(': '),
            code=label.strip(' .:)') if label and not label.strip().isdigit() else '',
            order=order)
        ev = _evidence(span, doc, cur.text, reading=f'a row of the scheme table: {name}')
        if ev:
            node.evidence = [ev]
            node.status = Status.VERIFIED
        else:
            node.status = Status.NEEDS_REVIEW

        # The numbers are paired with the numeric columns the header declared, in the
        # authority's own order. Nothing is assumed about which column comes first.
        pairs: list[tuple[ColumnKind, float]] = []
        category_values: list[float] = []
        qualifying_column = next(
            (c for c in numeric if c.kind is ColumnKind.QUALIFYING_MARKS), None)
        expected = len(numeric)
        if product_total is not None:
            numbers = numbers + [product_total]
        if _CELL_TOTAL.search(raw):
            # The row sums itself across parts the table does not separate, so which
            # figure belongs to which part is not established by the document.
            node.status = Status.NEEDS_REVIEW
            node.remarks = Fact.needs_review(
                span[:240],
                'the row states a total across parts its table does not separate, so no '
                'figure in it can be attributed to this part on its own')
            nodes.append(node)
            continue
        if len(numbers) == expected:
            pairs = list(zip([c.kind for c in numeric], numbers))
        elif qualifying_column is not None and len(numbers) == expected + 1:
            # The qualifying column is split into category sub-columns, so it holds one
            # figure more than the header's column count suggests.
            plain = [c.kind for c in numeric if c.kind is not ColumnKind.QUALIFYING_MARKS]
            pairs = list(zip(plain, numbers[:len(plain)]))
            category_values = numbers[len(plain):]
        elif numbers:
            pairs = list(zip([c.kind for c in numeric], numbers))
            node.status = Status.NEEDS_REVIEW
            node.remarks = Fact.needs_review(
                residue.strip()[:200],
                f'the row states {len(numbers)} figures where its table declares '
                f'{expected} numeric columns, so the pairing is not established')

        for kind, value in pairs:
            if kind is ColumnKind.QUESTIONS:
                node.questions = _fact(int(value), span, doc, cur.text,
                                       reading=f'{name}: {int(value)} questions')
            elif kind is ColumnKind.MARKS:
                node.marks = _fact(value, span, doc, cur.text,
                                   reading=f'{name}: {value} marks')
            elif kind is ColumnKind.QUALIFYING_MARKS:
                node.qualifying = _fact(
                    QualifyingRule(as_printed=span[:200], minimum_marks=value),
                    span, doc, cur.text, reading=f'{name}: minimum {value} marks')

        if category_values and qualifying_column is not None:
            labels = _category_labels(cur, start, qualifying_column, len(category_values))
            rule = QualifyingRule(
                as_printed=span[:200],
                by_category=[CategoryMinimum(label=lab, minimum_marks=val)
                             for lab, val in zip(labels, category_values)])
            node.qualifying = _fact(rule, span, doc, cur.text,
                                    reading=f'{name}: minimum marks by category')

        if per_question is not None:
            node.marks_per_question = _fact(
                per_question, span, doc, cur.text,
                reading=f'{name}: the cell states {per_question} marks a question')
        elif node.questions.has_value and node.marks.has_value and node.questions.value:
            each = node.marks.value / node.questions.value
            if abs(each - round(each, 2)) < 1e-9:
                node.marks_per_question = Fact.derived(
                    round(each, 4), ['marks', 'questions'],
                    node.marks.evidence,
                    'computed from the marks and the question count this table states')

        if minutes is not None:
            node.duration_minutes = _fact(minutes, span, doc, cur.text,
                                          reading=f'{name}: {duration_text}')
            node.duration_variants = variants
        if has_language:
            # The cell itself is the value. Matching a language word inside it would keep
            # only the first of them, and "English and Hindi" is two languages.
            medium = _medium_text(raw)
            if medium and _LANGUAGE_CELL.search(medium):
                node.languages = _fact([m.strip() for m in re.split(r'\s*(?:and|&|/|,)\s*',
                                                                    medium) if m.strip()],
                                       span, doc, cur.text,
                                       reading=f'{name}: medium of examination {medium}')
        kind_text = _first(_QUESTION_TYPE, raw)
        if kind_text:
            node.question_type = _fact(kind_text, span, doc, cur.text,
                                       reading=f'{name}: {kind_text}')
        nodes.append(node)
    return nodes, totals


def _category_labels(cur: _Cursor, header_end: int, column, count: int) -> list[str]:
    """The authority's own names for the groups a qualifying column is split across.

    Read from the sub-heading line under the header -- "SC/ST/PWBD Others" -- rather than
    assumed, because which groups an authority distinguishes is its own choice. The search
    runs forward only: looking backwards as well found the header's own "Medium of Exam"
    and labelled the two columns "of" and "Exam".
    """
    looked = 0
    for index in range(header_end, min(header_end + 6, len(cur.lines))):
        line = cur.lines[index].strip()
        if not line:
            continue
        looked += 1
        if looked > 3 or any(ch.isdigit() for ch in line):
            break
        parts = [p.strip() for p in re.split(r'\s{2,}|\s(?=[A-Z][a-zA-Z/]*\b)|\t', line)
                 if p.strip()]
        if len(parts) != count or any(len(p) > 24 for p in parts):
            continue
        if any(_HEADER_WORD.fullmatch(p) for p in parts):
            continue                       # still inside the header, not the sub-heading
        return [' '.join(p.split()) for p in parts]
    return [f'{column.label} {i + 1}' for i in range(count)]


# ---------------------------------------------------------------- prose papers
#: "Paper-A", "Paper II", "Part III". Deliberately not "Section": a disability
#: certificate’s "Section 2 of the RPwD Act" is not a paper of the examination, and a
#: scheme that numbers its parts as sections says so in a table, not in a list.
_PROSE_PAPER = re.compile(
    r'^\s*(?P<label>(?:paper|part)\s*[-–—]?\s*'
    r'(?:[IVXL]{1,4}|\d{1,2}|[A-H]))\b\s*[:.\-–]?\s*(?P<rest>.*)$', re.I)
_PROSE_MARKS = re.compile(r'\b(\d{2,4})\s*marks?\b', re.I)


def _read_prose_papers(cur: _Cursor, doc: SourceDocument, start: int, limit: int, *,
                       prefix: str) -> list[PatternNode]:
    """Papers listed as labelled lines, with the heading above them setting the rule.

    One authority publishes no scheme table at all: it lists its papers under two headings
    that are themselves the qualifying distinction. The heading is therefore read as a fact
    about the papers beneath it, which is exactly how a candidate reads it.
    """
    nodes: list[PatternNode] = []
    qualifying_group: bool | None = None
    order = 0
    index = start
    pending: list[str] = []
    label = name = ''
    heading_span = ''

    def flush() -> None:
        nonlocal label, name, pending, order
        if not label:
            pending = []
            return
        order += 1
        raw = ' '.join([label] + pending)
        span = ' '.join(x.strip() for x in [label] + pending if x.strip())
        node = PatternNode(id=f'{prefix}-{_slug(label)}', level=PatternLevel.PAPER,
                           level_label=re.split(r'[-\s]', label)[0].title(),
                           name=name or label, code=label.strip(' .:'), order=order)
        ev = _evidence(span, doc, cur.text, reading=f'a listed paper: {name or label}')
        if ev:
            node.evidence = [ev]
            node.status = Status.VERIFIED
        marks = _PROSE_MARKS.search(raw)
        if marks:
            node.marks = _fact(float(marks.group(1)), span, doc, cur.text,
                               reading=f'{name or label}: {marks.group(1)} marks')
        if qualifying_group is not None:
            rule = QualifyingRule(as_printed=heading_span[:200],
                                  is_qualifying_only=qualifying_group,
                                  counts_towards_merit=not qualifying_group)
            node.qualifying = _fact(rule, heading_span, doc, cur.text,
                                    reading=f'{label} sits under "{heading_span[:60]}"')
        kind_text = _first(_QUESTION_TYPE, raw)
        if kind_text:
            node.question_type = _fact(kind_text, span, doc, cur.text,
                                       reading=f'{label}: {kind_text}')
        nodes.append(node)
        label = name = ''
        pending = []

    while index < min(limit, len(cur.lines)):
        line = cur.lines[index].strip()
        index += 1
        if not line or _FURNITURE.match(line):
            continue
        if _QUALIFYING_HEADING.match(line):
            flush()
            qualifying_group, heading_span = True, line
            continue
        if _MERIT_HEADING.search(line) and len(line) < 80:
            flush()
            qualifying_group, heading_span = False, line
            continue
        hit = _PROSE_PAPER.match(line)
        if hit and _IS_STATEMENT.search(hit.group('rest') or ''):
            # "Paper-VII ) and Marks obtained in Interview/Personality Test will be
            # considered ..." is a rule about a paper, not the paper's own entry.
            hit = None
        if hit:
            flush()
            label = hit.group('label').strip()
            rest = hit.group('rest').strip()
            name = _row_name(rest, '') or rest[:120]
            pending = [rest] if rest else []
            continue
        if label and len(line) < 200:
            pending.append(line)
            if not name:
                name = _row_name(line, '')
            continue
    flush()
    # One labelled line proves nothing -- a pro forma, an annexure or a citation is
    # labelled the same way. A list of papers is two or more, and an authority that lists
    # its papers states what at least one of them is worth.
    if len(nodes) < 2 or not any(n.marks.has_value for n in nodes):
        return []
    return nodes


# ================================================================ stage finding
#: A statement rather than a name. In a flattened PDF no line ends in a full stop, so
#: punctuation cannot tell a heading from the middle of a sentence -- but a heading has no
#: verb. This is what stops "Tier-II will consist of Paper-I, Paper-II and" from being read
#: as a stage of the examination.
_IS_STATEMENT = re.compile(
    r'\b(?:will|shall|may|must|should|would|can|could|is|are|was|were|be|been|being|'
    r'has|have|had|consist|consists|include|includes|comprise|comprises|means|'
    r'conducted|awarded|deducted|allowed|given|based|required|eligible|applicable)\b',
    re.I)


def _is_heading(line: str) -> bool:
    text = line.strip()
    if not text or len(text) > 110:
        return False
    if text.endswith((';', ',')):
        return False
    # A wrapped sentence's first line ends wherever the column ran out -- "(i) Civil
    # Services (Preliminary) Examination (Objective Type) for the". No heading does.
    if re.search(r'\b(?:for|of|in|to|and|or|the|a|an|with|by|from|as|on|at|is|are)\s*$',
                 text, re.I):
        return False
    if _IS_STATEMENT.search(text):
        return False
    words = text.split()
    return len(words) <= 14


def _stage_regions(cur: _Cursor) -> list[tuple[int, str, str]]:
    """Every line that announces a stage, with what it called it.

    A scheme heading is taken as a stage boundary too: an exam with one stage says "Scheme
    of Examination" and nothing more, and refusing to read that would lose every
    single-stage exam.
    """
    found: list[tuple[int, str, str]] = []
    for index, raw in enumerate(cur.lines):
        line = raw.strip()
        if not _is_heading(line):
            continue
        labelled = _STAGE_LABELLED.search(line)
        named = _STAGE_NAMED.search(line)
        scheme = _SCHEME_HEADING.search(line)
        if not (labelled or named or scheme):
            continue
        # A heading names its subject at the start; prose mentions it anywhere. Without
        # this, "list of Examination centres for the Online Preliminary Examination" was
        # read as a stage of the examination.
        opening = re.sub(r'^\s*(?:\d+(?:\.\d+)*|\([a-z]\)|[a-z]\.|[A-H]\.)\s*', '',
                         line).lstrip()
        if opening[:1].islower():
            continue
        first = min((m.start() for m in (labelled, named, scheme) if m), default=99)
        if first > 40:
            continue
        if not _is_marked(line):
            continue
        if named and not (labelled or scheme):
            # "Interview" alone in a sentence is not a heading announcing a stage; the
            # line has to read like a title of one.
            if not re.search(r'\b(?:exam\w*|test|round|paper|phase|stage|tier)\b',
                             line, re.I):
                continue
        found.append((index, line, 'labelled' if labelled else
                      ('named' if named else 'scheme')))
    return found


def _stage_name(line: str) -> tuple[str, str, str]:
    """The stage's name, its level label and its code, as the heading writes them."""
    text = re.sub(r'^\s*(?:\d+(?:\.\d+)*|\([a-z]\)|[a-z]\.|[A-H]\.)\s*', '', line.strip())
    text = text.strip(' :.–—-')
    labelled = _STAGE_LABELLED.search(text)
    if labelled:
        return text[:110], labelled.group('label').title(), labelled.group(0).strip()
    named = _STAGE_NAMED.search(text)
    if named:
        return text[:110], 'Stage', ''
    return text[:110], 'Stage', ''


def _keeps(stage: PatternNode, line: str) -> bool:
    """Is this heading a stage of the examination, now that we have read what it says?

    Three ways to qualify, in order of strength:

      * its rows state figures -- a scheme table was read under it;
      * it states a measurable fact of its own, which is how an authority that puts its
        papers elsewhere still publishes the stage's duration, languages and penalty;
      * it is a plain labelled heading naming nothing else, which is all an interview
        stage ever gets: "Phase-III: Interview" and not one figure anywhere.

    Everything else is a heading that reads like a stage: a cross-reference to part of the
    scheme, a heading over some other list, or a fragment of a sentence.
    """
    measurable = ('questions', 'marks', 'duration_minutes', 'negative_marking',
                  'qualifying', 'languages')
    bare = re.sub(r'^\s*(?:\d+(?:\.\d+)*|\([a-z]\)|[a-z]\.|[A-H]\.)\s*', '', line).strip()
    if _NOT_THE_SCHEME.search(bare):
        # A heading over a list, a syllabus, the instructions or the fee. It heads real
        # content and none of it is the examination's structure.
        return False
    if stage.children:
        return any(child.questions.has_value or child.marks.has_value
                   or child.duration_minutes.has_value for child in stage.children)
    if _SCHEME_HEADING.search(line):
        # "STRUCTURE OF EXAMINATION", "Scheme of the Examination" -- it introduces the
        # stages that follow. Where it also carries their table it was kept by the branch
        # above; on its own it is a heading, not a stage, whatever rule follows it.
        return False
    if any(getattr(stage, field).has_value for field in measurable):
        return True
    if _CROSS_REFERENCE.search(bare):
        return False
    # Nothing countable, no rows: it has to be named like a stage rather than like a part
    # of one. A phase, a tier, a round, or one of the words an authority uses for a phase
    # of its selection -- which is all an interview stage ever gets.
    stage_word = re.search(r'\b(?:tier|phase|stage|round)\b', bare, re.I)
    if not (stage_word or _STAGE_NAMED.search(bare)):
        return False
    return len(bare.split()) <= 6


def extract_pattern(doc: SourceDocument, text: str, *, exam_id: str,
                    cycle: str = '') -> ExamPattern:
    """The examination pattern this document publishes, for this exam and no other.

    The exam id is carried, never inferred: a scheme page that serves several exams must
    not contribute its facts to whichever one happens to be selected, and the caller is the
    only thing that knows which exam it asked about.
    """
    pattern = ExamPattern(exam_id=exam_id, cycle=cycle)
    if not text or not exam_id:
        return pattern

    cur = _Cursor(text)
    regions = _stage_regions(cur)
    if not regions:
        return pattern

    bounds = [r[0] for r in regions] + [len(cur.lines)]
    seen: set[str] = set()
    consumed = 0
    for position, (line_no, line, _kind) in enumerate(regions):
        end = bounds[position + 1]
        if end - line_no < 2 or line_no < consumed:
            # Inside a stage already read. A heading there is part of that stage's
            # structure, not the start of another one -- and re-reading it produced the
            # same nine papers under twelve different stages.
            continue
        name, level_label, code = _stage_name(line)
        stage_id = f'stage-{_slug(name)}'
        if stage_id in seen:
            continue

        # A row of the table can read as a heading on its own line, and stopping there
        # cut the table short. The row reader is given the lines through any following
        # heading that is itself row-shaped, and decides what they are.
        header = _find_scheme_header(cur, line_no + 1, end)
        if header is not None:
            # A table's rows read like headings, so its reading runs past them. A prose
            # list has no such problem, and extending for one made the first stage
            # swallow the next stage's papers.
            end = _extend_past_rows(cur, regions, position, bounds)
        passage = cur.joined(line_no, min(end, line_no + 60))
        children: list[PatternNode] = []
        totals: dict = {}
        if header is not None:
            header_end, columns = header
            children, totals = _read_table_rows(cur, doc, columns, header_end + 1, end,
                                                prefix=stage_id)
        if not children:
            children = _read_prose_papers(cur, doc, line_no + 1, end, prefix=stage_id)
        stage = PatternNode(id=stage_id, level=PatternLevel.STAGE,
                            level_label=level_label, name=name, code=code,
                            order=len(pattern.stages) + 1, children=children)
        evidence = _evidence(line.strip(), doc, text,
                             reading=f'a stage of the examination: {name}')
        if evidence:
            stage.evidence = [evidence]
            stage.status = Status.VERIFIED
        else:
            stage.status = Status.NEEDS_REVIEW
        _apply_stage_rules(stage, passage, doc, text, totals)

        if not _keeps(stage, line):
            continue
        pattern.stages.append(stage)
        seen.add(stage_id)
        if children:
            consumed = end

    _fold_restated_stages(pattern)
    _apply_merit_statements(pattern, doc, text)
    _push_down_stage_rules(pattern)
    return pattern


#: A sentence saying what a stage's or a paper's marks count for. Read from the whole
#: document: an authority states this where it explains the selection, which is often
#: pages away from the table it governs.
_MERIT_SENTENCE = re.compile(r'[^.\n]{0,300}?(?:' + _QUALIFYING_ONLY.pattern +
                             r')[^.\n]{0,200}\.', re.I)


#: Words that appear in half the headings an authority writes and so distinguish nothing.
_GENERIC_NODE_WORDS = frozenset({
    'exam', 'exams', 'examination', 'examinations', 'test', 'tests', 'paper', 'papers',
    'phase', 'tier', 'stage', 'part', 'parts', 'section', 'sections', 'session',
    'online', 'offline', 'objective', 'written', 'round',
})


def _trim_to_statement(passage: str, cue: re.Pattern) -> str:
    """Drop whatever table the statement was printed under."""
    text = ' '.join((passage or '').split())
    hit = cue.search(text)
    if not hit:
        return text.strip()
    head = text[:hit.start()]
    cut = max((m.end() for m in re.finditer(r'\d', head)), default=0)
    # The sentence may open before the cue with a word or two ("The marks obtained in the
    # Preliminary Examination (Phase-I) will NOT be added ..."), so the trim keeps
    # everything after the last figure rather than starting at the cue itself.
    return text[cut:].strip(' *.,;:')


def _distance_in(flat: str, node, where: int) -> int:
    """How far the node's own span is from this sentence, in the flattened document."""
    for evidence in (node.evidence or []):
        span = ' '.join((evidence.span or '').split())[:120]
        if not span:
            continue
        at = flat.find(span)
        if at >= 0:
            return abs(at - where)
    return 10 ** 9


def _apply_merit_statements(pattern: ExamPattern, doc: SourceDocument, text: str) -> None:
    """Attach each merit statement to the node it names, by that node's own words.

    A sentence that names no node is left alone. It is real and it is about something, but
    guessing which paper it governs would be inventing the most consequential field in the
    pattern -- whether the marks count.
    """
    flat = ' '.join((text or '').split())
    nodes = list(pattern.walk())
    for match in _MERIT_SENTENCE.finditer(flat):
        sentence = _trim_to_statement(match.group(0), _QUALIFYING_ONLY)
        if not sentence or len(sentence) > 420:
            continue
        if len(re.findall(r'(?<![\w.])\d{1,4}(?![\w.])', sentence)) >= 3:
            # A run of table cells, not a statement: "Grand Total 2025 Marks ... 250 ...".
            continue
        lowered = sentence.lower()
        # If the sentence names a stage, it is about something in that stage.
        named_stage = None
        for candidate in pattern.stages:
            marks = {w for w in re.split(r'[^a-z]+', (candidate.name or '').lower())
                     if len(w) > 3 and w not in _GENERIC_NODE_WORDS}
            if marks and marks <= set(re.split(r'[^a-z]+', lowered)):
                named_stage = candidate
                break
        allowed = set()
        if named_stage is not None:
            allowed = {id(n) for n in named_stage.walk()}
        where = match.start()
        best, score, distance = None, 0, 10 ** 9
        for node in nodes:
            # Only the node's *distinguishing* words count. Matching on level vocabulary
            # let "Candidates qualifying in earlier phase only will be called" attach to
            # whichever stage had "Phase" in its heading, which is all of them.
            words = {w for w in re.split(r'[^a-z]+', (node.name or '').lower())
                     if len(w) > 3 and w not in _GENERIC_NODE_WORDS}
            hits = sum(1 for w in words if w in lowered)
            # A coded node is claimed only by a sentence naming its code. Without this,
            # a rule about the Preliminary stage's Paper-II attached to the Main
            # Examination's General Studies papers, marking 250 merit marks as qualifying.
            parts = [part for part in re.split(r'[^a-z0-9]+', (node.code or '').lower())
                     if part]
            if parts and sum(len(part) for part in parts) > 1:
                spelled = r'\b' + r'\W*'.join(re.escape(part) for part in parts) + r'\b'
                if not re.search(spelled, lowered):
                    continue
                hits += 1
            if allowed and id(node) not in allowed:
                continue
            if not hits:
                continue
            gap = _distance_in(flat, node, where)
            # A deeper node wins a tie -- a footnote about one test is about that test and
            # not about the stage containing it -- and between two equally deep ones, the
            # one printed nearer the sentence.
            better = (hits > score
                      or (hits == score and not node.children and best is not None
                          and best.children)
                      or (hits == score and gap < distance))
            if better:
                best, score, distance = node, hits, gap
        if best is None or score < 1:
            continue
        existing = best.qualifying.value if best.qualifying.has_value else None
        rule = QualifyingRule(
            as_printed=sentence[:300], is_qualifying_only=True, counts_towards_merit=False,
            minimum_marks=existing.minimum_marks if existing else None,
            minimum_percent=existing.minimum_percent if existing else None,
            by_category=list(existing.by_category) if existing else [])
        best.qualifying = _fact(rule, sentence, doc, text,
                                reading=f'{best.name}: the authority states its marks are '
                                        f'not counted towards the merit')


def _fold_restated_stages(pattern: ExamPattern) -> None:
    """A heading that restates the one above it is the same stage, not another.

    One notice writes "Phase-II : Main Examination:" and then, immediately above the table,
    "Main Examination:". Read as two stages that is one stage with the rules and no rows
    and another with the rows and no rules, which is worse than either. The second's rows
    and facts are folded into the first, and its own name is kept as evidence.
    """
    folded: list[PatternNode] = []
    skip: set[int] = set()
    for index, stage in enumerate(pattern.stages):
        if index in skip:
            continue
        nxt = pattern.stages[index + 1] if index + 1 < len(pattern.stages) else None
        restates = (nxt is not None and not stage.children and nxt.children
                    and _restates(stage.name, nxt.name))
        if restates:
            stage.children = nxt.children
            for field in ('questions', 'marks', 'duration_minutes', 'negative_marking',
                          'qualifying', 'languages', 'mode', 'question_type',
                          'sectional_timing'):
                if not getattr(stage, field).has_value:
                    setattr(stage, field, getattr(nxt, field))
            stage.evidence = stage.evidence + nxt.evidence
            skip.add(index + 1)
        folded.append(stage)
        stage.order = len(folded)

    def code_of(node: PatternNode) -> str:
        return re.sub(r'[^a-z0-9]+', '', (node.code or '').lower())

    # A stage whose label another stage already carries -- a bare "Tier-II" pages before
    # the Tier-II scheme, or a "Paper-II Statistics" heading over the row that describes
    # it -- is that stage or that paper mentioned twice. Whatever it states of its own is
    # moved onto the node that has the substance, and the duplicate goes.
    def name_of(node: PatternNode) -> str:
        return ' '.join(re.sub(r'[^a-z ]+', ' ', (node.name or '').lower()).split())

    elsewhere: dict = {}
    by_name: list = []
    for node in folded:
        if not node.children:
            continue
        for inner in node.walk():
            if code_of(inner) and code_of(inner) not in elsewhere:
                elsewhere[code_of(inner)] = inner
            if name_of(inner) and inner is not node:
                by_name.append(inner)

    def twin_by_name(node: PatternNode):
        """A node elsewhere that this heading is another way of naming."""
        mine = name_of(node)
        if not mine:
            return None
        for other in by_name:
            theirs = name_of(other)
            if theirs and (mine == theirs or mine.endswith(' ' + theirs)):
                return other
        return None

    kept: list[PatternNode] = []
    for node in folded:
        twin = None
        if not node.children:
            twin = elsewhere.get(code_of(node)) or twin_by_name(node)
        if twin is not None and twin is not node:
            for field in ('questions', 'marks', 'duration_minutes', 'negative_marking',
                          'qualifying', 'languages', 'mode', 'question_type',
                          'sectional_timing'):
                if not getattr(twin, field).has_value and getattr(node, field).has_value:
                    setattr(twin, field, getattr(node, field))
            continue
        kept.append(node)
    kept = _merge_overlapping_stages(kept)
    for order, node in enumerate(kept, start=1):
        node.order = order
    pattern.stages = kept


def _merge_overlapping_stages(stages: list) -> list:
    """Two headings naming one stage, where neither has rows to tell them apart.

    One authority describes each stage twice: once in the plan of examination and once in
    the scheme, listing that stage's papers in neither place. Both headings are real and
    each carries part of the rules, so they are one stage with both halves -- the earlier
    heading keeps its name, and whatever only the later one stated is filled in.

    The test is on the distinguishing words: "preliminary" against "civil services
    preliminary objective". A subset is the same stage said shorter; an overlap is not.
    """
    def distinct(node) -> set:
        return {w for w in re.split(r'[^a-z]+', (node.name or '').lower())
                if len(w) > 3 and w not in _GENERIC_NODE_WORDS}

    out: list = []
    for stage in stages:
        if stage.children:
            out.append(stage)
            continue
        mine = distinct(stage)
        host = next((s for s in out
                     if not s.children and mine and distinct(s)
                     and (mine <= distinct(s) or distinct(s) <= mine)), None)
        if host is None:
            out.append(stage)
            continue
        for field in ('questions', 'marks', 'duration_minutes', 'negative_marking',
                      'qualifying', 'languages', 'mode', 'question_type',
                      'sectional_timing'):
            if not getattr(host, field).has_value and getattr(stage, field).has_value:
                setattr(host, field, getattr(stage, field))
        host.evidence = host.evidence + stage.evidence
    return out


def _restates(outer: str, inner: str) -> bool:
    """Is the second heading the first one again, without its label?"""
    def bare(text: str) -> str:
        text = _STAGE_LABELLED.sub(' ', text or '')
        return ' '.join(re.sub(r'[^a-z ]+', ' ', text.lower()).split())
    left, right = bare(outer), bare(inner)
    if left and right and left == right:
        return True
    # A bare label -- "Tier-II" on its own, before the notice reaches the scheme -- has no
    # name left once its label is removed, so it is compared by the label instead.
    outer_code = _STAGE_LABELLED.search(outer or '')
    inner_code = _STAGE_LABELLED.search(inner or '')
    if outer_code and inner_code and not left:
        return (outer_code.group(0).replace(' ', '').replace('-', '').lower()
                == inner_code.group(0).replace(' ', '').replace('-', '').lower())
    return False


#: A verb of statement. A table header has none: "Time allowed", "No. of Questions",
#: "Medium of Exam" name columns. A sentence does -- "The Civil Services (Preliminary)
#: Examination will consist of two papers of objective type (multiple choice questions)
#: and carry a maximum of 400 marks" declares paper, questions, marks and subject between
#: them, and was read as a five-column header.
_SENTENCE_VERB = re.compile(
    r"""(?:will|shall|may|must|should|would|can|could|is|are|was|were|be|been|being|
        has|have|had|consist|consists|include|includes|comprise|comprises|carry|carries|
        means|denotes|conducted)""", re.I | re.X)


def _extend_past_rows(cur: _Cursor, regions: list, position: int,
                      bounds: list) -> int:
    """How far this stage's table may be read: past every row-shaped heading after it."""
    end = bounds[position + 1]
    index = position + 1
    while index < len(regions):
        line = regions[index][1].strip()
        if not _ROW_LABEL.match(line):
            break
        # A row never has a scheme table under it. A stage heading does, and that is where
        # this stage's reading stops -- without it the first stage's table reading ran
        # through the next stage and took its table with it.
        if _find_scheme_header(cur, regions[index][0] + 1, bounds[index + 1]) is not None:
            break
        # Nor is a heading carrying a stage's own label ever a row of the table
        # above it: an interview has no table, and reading through it lost the
        # stage. Only the four stage words count here -- a row may perfectly well
        # be called "Computer Knowledge Test", and one is.
        if re.search(r'\b(?:tier|phase|stage|round)\b', line, re.I):
            break
        end = bounds[index + 1]
        index += 1
    return end


def _header_density(joined: str, columns: list) -> float:
    """What share of these lines is column names.

    A header is almost nothing but column names. A sentence that happens to mention
    papers, questions, marks and subjects spreads them across forty words of prose, and
    that is how "The Civil Services (Preliminary) Examination will consist of two papers
    of objective type (multiple choice questions) and carry a maximum of 400 marks in the
    subjects set out in Section II" was read as a five-column header.
    """
    words = [w for w in re.split(r'\s+', joined.strip()) if w]
    if not words:
        return 0.0
    named = sum(len(c.label.split()) for c in columns)
    return named / len(words)


def _find_scheme_header(cur: _Cursor, start: int, end: int) -> tuple[int, list] | None:
    """A scheme table's header inside this stage's region, and the columns it declares.

    Not the shared `find_header`: that one requires the header to be followed by a bare
    ordinal, which is true of a post table and false of every scheme table read so far --
    their rows put the ordinal and the name on one line.
    """
    best: tuple[int, list] | None = None
    for index in range(start, min(end, len(cur.lines))):
        joined = ''
        # A wrapped header runs deep: one real header spends fifteen lines on six columns,
        # splitting "Maximum Marks" across three of them.
        for offset in range(index, min(index + 16, end, len(cur.lines))):
            joined = (joined + ' ' + cur.lines[offset]).strip()
            if len(joined) > 400:
                break
            if _SENTENCE_VERB.search(joined):
                continue
            columns = _columns_in(joined)
            kinds = {c.kind for c in columns}
            # A header, not a sentence: it has to declare something countable and
            # something that names the rows.
            dense = _header_density(joined, columns) >= 0.55
            if ({ColumnKind.QUESTIONS, ColumnKind.MARKS} & kinds) and len(columns) >= 3                     and dense:
                if best is None or len(columns) > len(best[1]):
                    best = (offset, columns)
        if best is not None:
            return best
    return best


def _apply_stage_rules(stage: PatternNode, passage: str, doc: SourceDocument, text: str,
                       totals: dict) -> None:
    """The rules a stage states in prose, and the totals its table states in a row."""
    negative = read_negative_marking(passage)
    if negative:
        stage.negative_marking = _fact(negative, negative.as_printed, doc, text,
                                       reading='the penalty this stage states')
    qualifying = read_qualifying(passage)
    if qualifying and qualifying.is_qualifying_only:
        # Whether a whole stage counts towards the merit is decided only by a sentence
        # that names the stage, and that pass runs over the whole document
        # (`_apply_merit_statements`). Read from the region instead, the words "Minimum
        # Qualifying Marks" in a column header made a stage whose marks decide the merit
        # look like a screening test. The region keeps what it can say for itself: the
        # minimum a candidate must score.
        qualifying.is_qualifying_only = None
        qualifying.counts_towards_merit = None
        if not (qualifying.minimum_marks or qualifying.minimum_percent):
            qualifying = None
    if qualifying:
        stage.qualifying = _fact(qualifying, qualifying.as_printed, doc, text,
                                 reading='whether this stage counts towards the merit')
    mode = _first(_MODE, passage)
    if mode:
        stage.mode = _fact(mode, mode, doc, text, reading=f'conducted {mode}')
    kind_text = _first(_QUESTION_TYPE, passage)
    if kind_text:
        stage.question_type = _fact(kind_text, kind_text, doc, text, reading=kind_text)
    languages = _first(_LANGUAGE_PROSE, passage)
    # A statement about language names languages. One notice's header line -- "Medium of
    # Exam Minimum Qualifying Marks Duration SC" -- matched the medium wording and was
    # read as the languages the papers are set in.
    if languages and (any(ch.isdigit() for ch in languages)
                      or not _LANGUAGE_CELL.search(languages) or len(languages) > 70):
        languages = ''
    if languages:
        parts = [p.strip(' .') for p in re.split(r'\s*(?:and|&|/|,)\s*', languages)
                 if 2 < len(p.strip()) < 40]
        if parts:
            stage.languages = _fact(parts, languages, doc, text,
                                    reading=f'papers set in {languages}')
    if _SECTIONAL_TIMING.search(passage):
        span = _sentence_around(' '.join(passage.split()),
                                _SECTIONAL_TIMING.search(passage).start())
        stage.sectional_timing = _fact(True, span, doc, text,
                                       reading='each section is timed separately')

    if totals:
        numbers = totals.get('numbers') or []
        span = totals.get('span') or ''
        # A totals row states its figures in the same column order as the rows above it.
        if len(numbers) >= 1:
            stage.questions = _fact(int(numbers[0]), span, doc, text,
                                    reading=f'the total row states {int(numbers[0])}')
        if len(numbers) >= 2:
            stage.marks = _fact(numbers[1], span, doc, text,
                                reading=f'the total row states {numbers[1]} marks')
        if totals.get('minutes') is not None:
            stage.duration_minutes = _fact(totals['minutes'], span, doc, text,
                                           reading='the total row states the duration')

    if not stage.questions.has_value:
        counted = [c.questions.value for c in stage.children if c.questions.has_value]
        if counted and len(counted) == len(stage.children):
            stage.questions = Fact.derived(
                int(sum(counted)), ['children.questions'],
                [e for c in stage.children for e in c.questions.evidence][:2],
                'the sum of the question counts this stage’s own rows state')
    if not stage.marks.has_value:
        counted = [c.marks.value for c in stage.children if c.marks.has_value]
        if counted and len(counted) == len(stage.children):
            stage.marks = Fact.derived(
                float(sum(counted)), ['children.marks'],
                [e for c in stage.children for e in c.marks.evidence][:2],
                'the sum of the marks this stage’s own rows state')


def _push_down_stage_rules(pattern: ExamPattern) -> None:
    """A penalty stated once for a stage governs its rows, and is marked as inherited.

    The rule is the authority's; the attachment to a particular row is ours, so the child's
    fact records that it was inherited rather than printed against that row.
    """
    for stage in pattern.stages:
        if not stage.negative_marking.has_value:
            continue
        for child in stage.children:
            if child.negative_marking.has_value:
                continue
            child.negative_marking = Fact(
                value=stage.negative_marking.value, status=stage.negative_marking.status,
                evidence=list(stage.negative_marking.evidence),
                confidence=stage.negative_marking.confidence,
                derived_from=['stage.negative_marking'],
                note='stated once for the whole stage rather than against this row')


# ====================================================== may this document supply facts?
#: How much of a document's opening counts as its title block. A notice names what it is
#: about in its first page; a passing mention of another exam deep inside it does not make
#: the document that exam's.
_TITLE_BLOCK = 3000


def may_supply_pattern(text: str, target) -> tuple[bool, str]:
    """Whether this document's pattern facts belong to this exam.

    Content identity decides it, and the answer is deliberately conservative:

      * MATCH -- the document names this exam and no other. Publish.
      * AMBIGUOUS -- it names this exam among others, which is what a real notice looks
        like: one authority's notice for one exam names fourteen sibling examinations
        in its own rules. Facts
        are published only where the document's *own title block* names this exam, which
        is the target evidence a shared scheme page cannot supply.
      * MISMATCH -- it belongs to another exam. Nothing is taken from it, whatever it says
        about patterns.
    """
    from .identity import IdentityVerdict, verify

    check = verify(text, target)
    if check.verdict is IdentityVerdict.MATCH:
        return True, 'the document names this exam and no other'
    if check.verdict is IdentityVerdict.MISMATCH:
        return False, ('refused: ' + (check.reasons[0] if check.reasons
                                      else 'the document names another exam'))
    opening = verify(text[:_TITLE_BLOCK], target)
    if opening.verdict is IdentityVerdict.MATCH or opening.matched:
        return True, (f'the document names this exam in its own title block '
                      f'({opening.matched[0] if opening.matched else "named"}), '
                      f'among others later')
    return False, ('not published: the document mentions this exam but does not identify '
                   'itself as belonging to it, so a pattern fact in it cannot be '
                   'attributed to this exam')


# ======================================================================= report
def describe(pattern: ExamPattern) -> dict:
    """What was found, counted by what it is, for a build report."""
    nodes = list(pattern.walk())
    fields = ('questions', 'marks', 'duration_minutes', 'negative_marking', 'qualifying',
              'languages', 'mode', 'question_type', 'marks_per_question')
    counts: dict = {'stages': len(pattern.stages),
                    'papers': len(pattern.of_level(PatternLevel.PAPER)),
                    'sections': len(pattern.of_level(PatternLevel.SECTION)),
                    'subjects': len(pattern.of_level(PatternLevel.SUBJECT)),
                    'parts': len(pattern.of_level(PatternLevel.PART)),
                    'depth': pattern.max_depth()}
    for field in fields:
        states: dict = {}
        for node in nodes:
            fact = getattr(node, field)
            key = fact.status.value
            if fact.has_value and fact.is_derived:
                key = 'DERIVED'
            states[key] = states.get(key, 0) + 1
        counts[field] = states
    return counts
