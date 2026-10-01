"""Semantic units: where a quoted value ends in its source, and whether a stored value is whole.

A candidate-facing value that quotes a document -- a qualification, an application step, an
exam-day rule, an FAQ clause, an official clause -- is a *unit* of that document: one sentence,
one numbered clause, one numbered step. It ends where the document ends it, never at a character
count. A fixed-length slice ("text[:600]") cuts wherever the count runs out, and the cut value is
still a verbatim substring of the document, so no later verbatim check can see that anything is
missing ("District Centres once chos", "Provincial Act or a").

This module finds those ends deterministically and checks a value against its source. It never
completes a value: a span whose end it cannot find is reported incomplete, and the caller keeps it
out of publication (NEEDS_REVIEW / NOT_EXTRACTED) rather than filling it in.

Vocabulary only: sentence punctuation, clause numbering, list markers, section headings. No exam,
authority or state.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .evidence import normalise_ws

#: A word before a full stop that does not end a sentence. Lower-cased, without the stop.
_ABBREVIATIONS = frozenset({
    'rs', 'no', 'nos', 'sl', 'sr', 's.no', 'viz', 'i.e', 'e.g', 'approx', 'dt', 'dated',
    'govt', 'dept', 'dr', 'mr', 'mrs', 'ms', 'smt', 'sri', 'shri', 'st', 'prof', 'vol', 'art',
    'sec', 'cl', 'para', 'ref', 'fig', 'p', 'pp', 'g.o', 'g.o.ms', 'ms.no', 'rt', 'rt.no', 'm.s',
    'b.a', 'b.sc', 'b.com', 'b.e', 'b.tech', 'm.a', 'm.sc', 'm.com', 'm.tech', 'ph.d', 'll.b',
    'ph', 'hon', 'jr', 'ltd', 'co', 'u.s', 'a.p', 'm.p', 'u.p', 'h.p', 'j&k', 'vs', 'v',
})

#: A higher-level heading: a new part of the document begins, so every unit above it has ended.
#: Set in capitals, as a heading is. The same word in a sentence ("enclosed at Annexure-VI",
#: "State Gazette No. 35, Part-IV-B") is a cross-reference, and `_is_heading` also refuses a
#: capitalised one that continues a sentence.
STRUCTURAL_HEADING = re.compile(
    r'(?:(?<=\s)|^)(?:PARA|SECTION|CHAPTER|PART|ANNEXURE|ANNEXE|APPENDIX)\s*[-–—.:]?\s*'
    r'(?:\d{1,2}|[IVXLC]{1,6})\b(?:\s*[:.\-–—])?')
#: The signature block that closes an order or notice ("Sd/- Place: ... SECRETARY"). Whatever
#: follows it is the signatory, not the last clause.
SIGNATURE = re.compile(r'(?:(?<=\s)|^)Sd\s*/-?', re.I)
#: A numbered clause beginning ("10.3 If the ...", "16.6 ANY ..."): the previous clause has ended.
CLAUSE_NUMBER = re.compile(r'(?:(?<=\s)|^)\d{1,2}\.\d{1,2}(?:\.\d{1,2})?\s+(?=[A-Z(“"‘\'])')

_TERMINAL = re.compile(r'[.?!](?:[)\]”"’\']{0,2})(?=\s|$)')
#: What may follow a sentence end: a capital, a digit (a new clause), a bracket or quote, a list
#: marker, or the end of the text.
_NEXT_OPENS = re.compile(r'\s*(?:$|[A-Z0-9(\[“"‘\'••–—-])')


def _word_before(flat: str, stop: int) -> str:
    """The token ending at `stop` (exclusive), without surrounding brackets."""
    i = stop
    while i > 0 and not flat[i - 1].isspace():
        i -= 1
    return flat[i:stop].strip('([{“"‘\'').lower()


def _is_sentence_end(flat: str, at: int) -> bool:
    """Is the punctuation at `at` the end of a sentence (not an abbreviation or a number)?"""
    ch = flat[at]
    if ch in '?!':
        return True
    word = _word_before(flat, at)
    if not word:
        return False
    if word in _ABBREVIATIONS or word.rstrip('.') in _ABBREVIATIONS:
        return False
    # A dotted abbreviation ("G.O.Ms.No.", "U.G.C.", "p.m.") carries its own stops.
    if '.' in word.strip('.'):
        return False
    # "01." / "5." as a serial, "A." as an initial.
    if re.fullmatch(r'\d{1,3}|[a-z]', word):
        return False
    return bool(_NEXT_OPENS.match(flat, at + 1))


def sentence_end(flat: str, start: int, limit: int | None = None) -> int | None:
    """The index just past the sentence that runs from `start`, or None when no sentence end is
    found before `limit` (default: the end of the text). A structural boundary before any
    sentence end is not a sentence end: the unit was cut, or it never ended in a sentence."""
    stop = len(flat) if limit is None else min(limit, len(flat))
    for m in _TERMINAL.finditer(flat, start, stop):
        if _is_sentence_end(flat, m.start()):
            return m.end()
    return None


def _is_heading(flat: str, at: int) -> bool:
    """A heading does not continue a sentence: the text before it ends a sentence or stands on
    its own (a page number, a closing bracket), rather than ending in a lower-case word or a comma."""
    before = flat[:at].rstrip()
    return not before or not (before[-1].islower() or before[-1] in ',;(“"‘')


#: Words a figure follows inside a sentence ("not less than 86.3", "a minimum of 5.0").
#: Only words that practically always introduce a figure: "above" or "and" also end or join
#: clauses ("... the cases mentioned above 12.3 In case ..."), so a unit after the figure is what
#: identifies most measurements.
_BEFORE_FIGURE = frozenset({'than', 'upto', 'least', 'minimum', 'maximum', 'rs', 'rs.', 'about',
                            'approx', 'approx.', 'nearly', 'exceeding'})
#: Units a figure is followed by ("86.3 Cms", "45.5 Kgs", "2.5 hours").
_UNIT_AFTER = re.compile(r'\s*(?:cms?|kgs?|mm|m|metres?|meters?|ft|feet|inch(?:es)?|%|per\s*cent|'
                         r'marks?|years?|yrs?|hours?|hrs?|minutes?|mins?|lakhs?|crores?|km|kms)\b\.?', re.I)


def _is_figure(flat: str, m: re.Match) -> bool:
    """Is this clause-number-shaped match a figure in a sentence rather than a clause number?"""
    before = flat[:m.start()].rstrip().rsplit(' ', 1)[-1].lower().strip('(,')
    number_end = m.start() + len(m.group(0).rstrip())
    return before in _BEFORE_FIGURE or bool(_UNIT_AFTER.match(flat, number_end))


def next_structural_boundary(flat: str, start: int, *, clauses: bool = True) -> int:
    """The first clause number or higher-level heading at or after `start` (or the text's end)."""
    ends = [len(flat)]
    for rx in (STRUCTURAL_HEADING, SIGNATURE):
        for h in rx.finditer(flat, start):
            # A capitalised heading followed by its own capitalised title ("PARA-6 AGE:") is a
            # heading even straight after an unfinished sentence; otherwise the words before it
            # decide (a heading does not continue a sentence).
            titled = rx is STRUCTURAL_HEADING and re.match(r'\s*[A-Z][A-Z]{2,}\b', flat[h.end():])
            if titled or _is_heading(flat, h.start()):
                ends.append(h.start())
                break
    if clauses:
        # A figure inside a sentence ("not less than 86.3 Cms. round the chest") has the shape of
        # a clause number; only one that does not continue a sentence begins a clause.
        for c in CLAUSE_NUMBER.finditer(flat, start):
            if not _is_figure(flat, c):
                ends.append(c.start())
                break
    return min(ends)


def sentence_start(flat: str, pos: int) -> int:
    """Where the sentence containing `pos` begins: just after the previous sentence end, clause
    number or heading -- whichever is nearest -- or the start of the text."""
    begin = 0
    for m in _TERMINAL.finditer(flat, 0, pos):
        if _is_sentence_end(flat, m.start()):
            begin = m.end()
    for rx in (STRUCTURAL_HEADING, CLAUSE_NUMBER):
        for m in rx.finditer(flat, begin, pos):
            if rx is STRUCTURAL_HEADING or not _is_figure(flat, m):
                begin = max(begin, m.end() if rx is CLAUSE_NUMBER else _heading_end(flat, m))
    while begin < pos and flat[begin].isspace():
        begin += 1
    return begin


def _heading_end(flat: str, m: re.Match) -> int:
    """The end of a heading's own capitalised title ("PARA-5 EDUCATIONAL QUALIFICATIONS:")."""
    title = re.match(r'(?:\s*[A-Z][A-Z&/,()\-]*\b)+\s*[:.\-–—]?', flat[m.end():])
    return m.end() + (title.end() if title else 0)


def unit_end(flat: str, start: int, stop: int | None = None, *, clauses: bool = True) -> int | None:
    """Where a quoted unit that begins at `start` ends: the last sentence end before the next
    structural boundary (or `stop`, when the caller already knows where the unit's container ends).
    `clauses=False` for a unit that holds numbered clauses of its own (a section under a heading):
    only a heading, an annexure or a signature ends it.
    None when the text up to that boundary holds no sentence end -- the unit is not complete in
    what was read, and nothing is to be supplied for it."""
    bound = next_structural_boundary(flat, start + 1, clauses=clauses)
    if stop is not None:
        bound = min(bound, stop)
    last = None
    pos = start
    while True:
        end = sentence_end(flat, pos, bound)
        if end is None:
            break
        last, pos = end, end
    return last


# ----------------------------------------------------------------- the fields that quote units

#: Candidate-facing fields whose value quotes whole units of a document.
UNIT_FIELDS = ('qualification', 'howToApply', 'examDayChecklist', 'faqs', 'syllabus')


def units_of(field_name: str, value) -> list[tuple[str, str]]:
    """(label, quoted text) for every unit a field's value publishes. Labels name the item for
    a reviewer; nothing here reads or changes the text."""
    out: list[tuple[str, str]] = []
    if field_name == 'qualification':
        text = value.get('text') if isinstance(value, dict) else value
        if isinstance(text, str) and text.strip():
            out.append(('qualification', text))
    elif field_name == 'howToApply':
        if isinstance(value, str) and value.strip():
            out.append(('how to apply', value))
        for i, step in enumerate(value if isinstance(value, list) else [], start=1):
            if isinstance(step, dict) and str(step.get('description') or '').strip():
                out.append((f'step {i} ({str(step.get("title") or "")[:40]})', str(step['description'])))
    elif field_name == 'examDayChecklist':
        for i, item in enumerate(value if isinstance(value, list) else [], start=1):
            if not isinstance(item, dict):
                continue
            for key in ('title', 'description'):
                if str(item.get(key) or '').strip():
                    out.append((f'item {i} {key}', str(item[key])))
    elif field_name == 'syllabus':
        # A syllabus entry's unit is the entry as printed: its evidence quotation.
        for node in _syllabus_nodes(value):
            quoted = str((node.get('provenance') or {}).get('excerptText') or '')
            if node.get('status', 'VERIFIED') == 'VERIFIED' and quoted.strip():
                out.append((f'syllabus entry {str(node.get("title") or "")[:40]!r}', quoted))
    elif field_name == 'faqs':
        for i, q in enumerate(value if isinstance(value, list) else [], start=1):
            if isinstance(q, dict) and str(q.get('answer') or '').strip():
                out.append((f'clause {i} ({str(q.get("officialClause") or "")[:30]})', str(q['answer'])))
    return out


def _syllabus_nodes(tree) -> list[dict]:
    out: list[dict] = []

    def walk(node):
        if isinstance(node, dict):
            out.append(node)
            for child in node.get('children') or []:
                walk(child)
    for root in tree if isinstance(tree, list) else []:
        walk(root)
    return out


def _within(value: str, quoted: str) -> bool:
    """Is `value` printed inside `quoted`, allowing a page number printed between its words?"""
    v, q = normalise_ws(value).strip(' .;,:'), normalise_ws(quoted)
    if not v or v in q:
        return True
    # Words compared without their trailing punctuation: a title is stored without the full stop
    # the entry printed after its last word.
    want = [w.rstrip('.,;:') for w in v.split()]
    have = [w.rstrip('.,;:') for w in q.split()]
    for start, word in enumerate(have):
        if word != want[0]:
            continue
        i, j = 1, start + 1
        while i < len(want) and j < len(have):
            if have[j] == want[i]:
                i += 1
            elif not re.fullmatch(r'\d{1,3}', have[j]):
                break
            j += 1
        if i == len(want):
            return True
    return False


def syllabus_problems(tree, document_text: str) -> list[str]:
    """Why a syllabus tree is not publishable as whole units, or []. A verified entry's title and
    note must lie inside its own quotation (the evidence covers the value), and that quotation must
    not be cut -- stopping inside a word, or carrying a cut marker. Entries the reader already held
    for review are not re-judged here."""
    doc = normalise_ws(_markup_as_boundaries(document_text))
    problems: list[str] = []
    for node in _syllabus_nodes(tree):
        if node.get('status', 'VERIFIED') != 'VERIFIED':
            continue
        quoted = str((node.get('provenance') or {}).get('excerptText') or '')
        label = repr(str(node.get('title') or '')[:40])
        for key in ('title', 'note'):
            value = str(node.get(key) or '')
            if value and not _within(value, quoted):
                problems.append(f'{label}: its {key} is not inside the words its evidence quotes')
        q = normalise_ws(quoted).rstrip()
        if q.endswith('…'):
            problems.append(f'{label}: its quotation carries a cut marker')
            continue
        at = _locate(q, doc) if q else -1
        if at >= 0 and at + len(q) < len(doc) and doc[at + len(q)].isalnum() and q[-1:].isalnum():
            problems.append(f'{label}: its quotation stops inside a word')
    return problems


# ------------------------------------------------------------------- checking a stored value

@dataclass(frozen=True)
class Completeness:
    #: True: a whole unit. False: demonstrably cut -- it stops inside a word or a sentence that the
    #: document continues, or carries a cut marker. None: it cannot be checked (the reader cleaned
    #: the words, so they are not printed verbatim); other checks decide such a value.
    complete: bool | None
    reason: str

    @property
    def cut(self) -> bool:
        return self.complete is False


#: Stands where a page's markup closed a block (a heading, a paragraph, a cell, a list item):
#: a structural boundary that whitespace normalisation must not erase. A private-use character,
#: so it cannot collide with printed text.
_BLOCK = ''
_BLOCK_TAG = re.compile(r'</?(?:h[1-6]|p|div|li|ul|ol|td|th|tr|table|br|section|article|dd|dt)\b[^>]*>', re.I)
_ANY_TAG = re.compile(r'<[^>]+>')


def _markup_as_boundaries(text: str) -> str:
    """An HTML page's text with its block tags as boundaries and its inline tags removed."""
    if '<' not in text or not _ANY_TAG.search(text):
        return text
    return _ANY_TAG.sub('', _BLOCK_TAG.sub(f' {_BLOCK} ', text))


def _locate(value_flat: str, doc_flat: str) -> int:
    """Where the value is printed in the document, compared without whitespace differences."""
    at = doc_flat.find(value_flat)
    if at >= 0:
        return at
    # Case and quote style can differ between a reader's cleaning and the page text.
    return doc_flat.lower().find(value_flat.lower())


def check_value(value: str, document_text: str) -> Completeness:
    """Is this quoted value a whole unit of its document?

    Whole means: printed verbatim; it neither begins nor ends inside a word; and it ends either
    at a sentence end or immediately before a structural boundary (the next clause number, the
    next heading, a list marker, the end of the text). A value that stops mid-sentence with the
    sentence continuing in the document is incomplete -- the check says so and names where it
    stops; it does not say what is missing.
    """
    v = normalise_ws(value).rstrip()
    doc = normalise_ws(_markup_as_boundaries(document_text))
    if not v:
        return Completeness(False, 'empty value')
    at = _locate(v, doc)
    if at < 0:
        if v.endswith('…'):
            return Completeness(False, f'the value was cut and marked with an ellipsis: …{v[-40:]!r}')
        return Completeness(None, 'the value is not printed verbatim in the document, so its '
                                  'boundaries cannot be checked here')
    end = at + len(v)
    if at > 0 and doc[at - 1].isalnum() and v[0].isalnum():
        return Completeness(False, f'begins inside a word: {doc[max(0, at - 12):at + 12]!r}')
    if end < len(doc) and doc[end].isalnum() and v[-1].isalnum():
        return Completeness(False, f'ends inside a word: {doc[max(0, end - 20):end + 12]!r}')
    crossed = next_structural_boundary(doc, at + 1, clauses=False)
    if crossed < end:
        return Completeness(False, f'runs past a heading into another part of the document: '
                                   f'{doc[crossed:crossed + 40]!r}')
    if _TERMINAL.search(v[-4:]) and _is_sentence_end(doc, at + len(v.rstrip('”"’\')]')) - 1):
        return Completeness(True, 'ends at a sentence end')
    rest = doc[end:]
    if not rest.strip():
        return Completeness(True, 'ends with the document')
    if rest.lstrip().startswith(_BLOCK):
        return Completeness(True, 'ends where the page closes its block')
    nb = next_structural_boundary(doc, end)
    if not doc[end:nb].strip():
        return Completeness(True, 'ends at the next clause or heading')
    if re.match(r'\s*(?:\(?[ivx]{1,4}\)|\(?[a-z]\)|\d{1,2}\)|[••])\s', rest):
        return Completeness(True, 'ends at the next list item')
    if v[-1] in ':;,' or not v[-1] in '.?!)]”"’\'':
        return Completeness(False, f'stops mid-sentence; the document continues: '
                                   f'{doc[max(0, end - 30):end]!r} | {doc[end:end + 30]!r}')
    return Completeness(False, f'stops before the unit ends: {doc[end:end + 30]!r}')


# --------------------------------------------------------- completing a stored value from source

@dataclass(frozen=True)
class Completion:
    #: The whole unit as the document prints it, or None when it cannot be established.
    text: str | None
    #: 'unchanged' | 'extended' (the stored value was cut) | 'ended' (the stored value ran past its
    #: unit into the next part of the document) | 'unchecked' (not a verbatim quotation, so there is
    #: no unit to complete) | 'unresolved' (a cut value whose unit could not be established)
    kind: str
    reason: str


def complete_from_source(value: str, document_text: str, unit: str) -> Completion:
    """The whole unit a stored quotation was cut from, read from the same document.

    Used to repair a stored record whose readers cut units at a character count. The stored words
    are found verbatim in the document; the unit then runs to its own end -- `unit='sentence'` to
    the sentence end, `unit='clause'` to the next clause number or heading -- and the result is
    the document's own text between those points. It is accepted only when it continues the stored
    words exactly (the stored value was cut) or when the stored words ran on past a heading and
    the unit ends before it. Nothing is ever composed: where the stored words cannot be found, or
    the unit's end cannot be found, the result is `unresolved` and the value stays as it was, for
    the caller to hold for review.
    """
    stored = normalise_ws(value).rstrip()
    core = re.sub(r'\s*…$', '', stored).rstrip()
    doc = normalise_ws(_markup_as_boundaries(document_text))
    state = check_value(stored, document_text)
    if state.complete is True:
        return Completion(stored, 'unchanged', state.reason)
    if state.complete is None and not stored.endswith('…'):
        # Not a verbatim quotation (a reader's or a reviewer's own wording): nothing to complete.
        return Completion(stored, 'unchecked', state.reason)
    at = _locate(core, doc)
    if at < 0:
        return Completion(None, 'unresolved', 'the stored words are not printed verbatim in the document')
    if at > 0 and doc[at - 1].isalnum() and core[0].isalnum():
        return Completion(None, 'unresolved', 'the stored words begin inside a word')
    bound = next_structural_boundary(doc, at + 1)
    if unit == 'sentence':
        end = sentence_end(doc, at, bound)
    elif unit == 'clause':
        end = bound
        while end > at and doc[end - 1].isspace():
            end -= 1
    else:
        raise ValueError(f'unknown unit {unit!r}')
    if end is None or end <= at:
        return Completion(None, 'unresolved', f'no end of the {unit} is printed before the next boundary')
    whole = doc[at:end].strip()
    if whole == core:
        return Completion(None, 'unresolved', f'the stored words already end where the {unit} ends, '
                                              f'but the check found them cut: {state.reason}')
    if whole.startswith(core):
        return Completion(whole, 'extended', f'the {unit} continues past the stored words to its own end')
    if core.startswith(whole) and next_structural_boundary(doc, at + 1, clauses=False) <= at + len(core):
        return Completion(whole, 'ended', f'the stored words ran past the {unit}\'s end into the next '
                                          f'part of the document')
    return Completion(None, 'unresolved', f'the {unit} read from the document does not continue the stored words')
