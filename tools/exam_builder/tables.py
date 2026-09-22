"""Putting a table back together after a PDF has taken it apart.

A PDF does not store a table. It stores text in positions, and an extractor flattens that
into one cell per line — with each cell's own wrapping producing several lines of its own.
So a four-column row arrives as anywhere between four and a dozen lines, the header is
wrapped across several more, and nothing marks where one cell ends and the next begins.

Three structural facts make it recoverable without knowing what the table is about:

    a row begins with a bare ordinal on its own line
    a wrapped line keeps its trailing space; the last line of a cell does not
    brackets balance at the end of a cell and not in the middle of one

The third matters more than it looks. A name followed by a bracketed qualifier on the
next line is one cell in two parts, and only the unclosed bracket says so.

Where these do not yield one cell per column, the row is **refused** rather than guessed. A
table read wrongly produces posts that do not exist, with ages and vacancies attached to
them, and a candidate may apply for one.

Nothing here knows what any column contains. Columns are identified from the words in the
header the authority wrote, and from the shape of the values underneath.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from enum import Enum


class ColumnKind(str, Enum):
    """What a column holds, recognised from the words in its own header."""

    SERIAL = 'SERIAL'
    NAME = 'NAME'
    DEPARTMENT = 'DEPARTMENT'
    CLASSIFICATION = 'CLASSIFICATION'
    PAY = 'PAY'
    AGE = 'AGE'
    VACANCY = 'VACANCY'
    QUALIFICATION = 'QUALIFICATION'
    # --- a scheme table's columns. Structural like the rest: no authority's stage names.
    STAGE = 'STAGE'
    PAPER = 'PAPER'
    SECTION = 'SECTION'
    SUBJECT = 'SUBJECT'
    QUESTIONS = 'QUESTIONS'
    MARKS = 'MARKS'
    DURATION = 'DURATION'
    LANGUAGE = 'LANGUAGE'
    QUALIFYING_MARKS = 'QUALIFYING_MARKS'
    OTHER = 'OTHER'


#: Header wordings, as ideas. An authority writes "Name of Post", "Name of the Post",
#: "Designation" or "Post"; all of them name the same column. Longest first so that
#: "Educational Qualification" is not read as the generic "Qualification".
_HEADER_CUES: tuple[tuple[ColumnKind, str], ...] = (
    # -- scheme columns, most specific first ------------------------------------------
    (ColumnKind.QUALIFYING_MARKS, r'\b(?:minimum|min\.?)\s+qualifying\s+marks?\b|'
                                  r'\bqualifying\s+marks?\b|\bcut[\s-]?off\s+marks?\b|'
                                  r'\bpassing\s+marks?\b'),
    (ColumnKind.QUESTIONS, r'\b(?:no\.?|number|nos\.?)\s*of\s+(?:questions?|items?|'
                           r'ques\.?)\b|\bquestions?\b(?!\s*paper)|\bno\.?\s*of\s+qs?\b'),
    (ColumnKind.MARKS, r'\b(?:maximum|max\.?|total)\s+marks?\b|\bmarks?\s+allotted\b|'
                       r'\bmarks?\b'),
    (ColumnKind.DURATION, r'\b(?:time|duration)\s+(?:allowed|allotted|permitted)\b|'
                          r'\bduration\b|\btime\s+allowed\b|\btime\s+allotted\b|'
                          r'\btiming\b|\btime\s+limit\b'),
    (ColumnKind.LANGUAGE, r'\bmedium\s+of\s+(?:exam\w*|test|paper)\b|\bmedium\b|'
                          r'\blanguage\s+of\s+(?:exam\w*|paper|test)\b'),
    (ColumnKind.SUBJECT, r'\bname\s+of\s+(?:the\s+)?(?:tests?|papers?|subjects?)\b|'
                         r'\bsubjects?\b|\bname\s+of\s+the\s+test\b'),
    (ColumnKind.PAPER, r'\bpapers?\b'),
    (ColumnKind.SECTION, r'\bsections?\b|\bparts?\b'),
    (ColumnKind.STAGE, r'\btiers?\b|\bstages?\b|\bphases?\b|\bsessions?\b'),
    # "No." alone is a serial column, unless "of" follows it -- "No. of Vacancies"
    # is a count, and matching the serial cue first made that column disappear.
    (ColumnKind.SERIAL, r'\bs\.?\s*no\.?(?!\s*of\b)|\bsl\.?\s*no\.?(?!\s*of\b)|\bserial\b|'
                        r'\bsr\.?\s*no\.?(?!\s*of\b)|\bcode\s*no\.?\b|'
                        r'\bno\.(?!\s*of\b)'),
    (ColumnKind.QUALIFICATION, r'\b(?:educational|essential|minimum|academic)\s+'
                               r'qualification\b|\bqualification\b|\beligibility\b'),
    (ColumnKind.CLASSIFICATION, r'\bclassification\b|\bgroup\s+of\s+post\b|\bpost\s+group\b|'
                                r'\bcategory\s+of\s+post\b'),
    # Specific before generic: "Name of Service" names the post, and the department
    # cue's bare "service" claimed it first.
    (ColumnKind.NAME, r'\bname\s+of\s+(?:the\s+)?(?:post|service|cadre)\b|\bdesignation\b'),
    (ColumnKind.DEPARTMENT, r'\bministry\b|\bdepartment\b|\boffice\b|\bcadre\b|'
                            r'\borganisation\b|\borganization\b|\bservice\b'),
    (ColumnKind.VACANCY, r'\bvacanc\w+\b|\bno\.?\s*of\s+posts?\b|\bnumber\s+of\s+posts?\b|'
                         r'\bno\.?\s*of\s+vacanc\w+\b'),
    (ColumnKind.AGE, r'\bage\b'),
    (ColumnKind.PAY, r'\bpay\s*(?:level|scale|band|matrix)?\b|\bscale\s+of\s+pay\b|'
                     r'\blevel\b|\bsalary\b|\bremuneration\b'),
    (ColumnKind.NAME, r'\bname\s+of\s+(?:the\s+)?post\b|\bname\s+of\s+(?:the\s+)?service\b|'
                      r'\bdesignation\b|\bpost\b'),
)

#: Value shapes, for the columns whose contents are recognisable on sight. These confirm an
#: assignment; they never create one on their own.
_VALUE_SHAPES: dict[ColumnKind, re.Pattern] = {
    ColumnKind.QUESTIONS: re.compile(r'^\s*\d{1,3}\s*$'),
    # "60*3 = 180" is a marks cell that shows its own arithmetic.
    ColumnKind.MARKS: re.compile(r'^\s*\d{1,4}(?:\s*\*\s*\d{1,3}\s*=\s*\d{1,4})?\s*$'),
    ColumnKind.DURATION: re.compile(r'\b\d{1,3}\s*(?:min\w*|hour|hrs?|hours?)\b', re.I),
    ColumnKind.AGE: re.compile(r'\b\d{1,2}\s*(?:[-–—]|to)\s*\d{1,2}\s*(?:years?|yrs?)?\b|'
                               r'\bnot\s+exceeding\s+\d{1,2}\b', re.I),
    ColumnKind.PAY: re.compile(r'\b(?:pay\s+)?level[\s-]*\d{1,2}\b|₹\s*[\d,]+|'
                               r'\brs\.?\s*[\d,]+', re.I),
    ColumnKind.VACANCY: re.compile(r'^\s*\d{1,5}\s*$'),
    ColumnKind.CLASSIFICATION: re.compile(
        r'\bgroup\s*[-–—]?\s*[\'"‘’“”]?[a-d][\'"‘’“”]?|\bgazetted\b|'
        r'\bnon[- ]?ministerial\b|\bministerial\b', re.I),
}

#: A numbered section heading: "2.1 Pay Level-8 (Rs 47600 to 151100):". It introduces a
#: table and states something about it, but names none of its columns.
_SECTION_HEADING = re.compile(r'^\s*\d+(?:\.\d+)*\s+\S.*[:：]\s*$')

#: A line that is only an ordinal: "1", "2.", "01", "(i)", "iii.".
_ORDINAL = re.compile(r'^\s*\(?\s*(?:\d{1,3}|[ivxlIVXL]{1,5})\s*[.)]?\s*$')

#: Page furniture inside a table. A running footer is not a row.
_FURNITURE = re.compile(
    r'^\s*(?:page\s*\d+\s*(?:of\s*\d+)?|contd\.?|continued|annexure[\s\S]{0,12}|'
    r'[-–—\s]*)\s*$', re.I)


@dataclass
class Column:
    kind: ColumnKind
    label: str
    order: int


@dataclass
class Row:
    """One reconstructed row, or one that could not be reconstructed."""

    cells: dict[ColumnKind, str] = dc_field(default_factory=dict)
    #: The lines this row was built from, so the evidence span is the row itself.
    span: str = ''
    ordinal: str = ''
    #: False where the line runs did not match the columns. The row is kept, unassigned.
    reconstructed: bool = True
    note: str = ''
    raw_cells: list = dc_field(default_factory=list)


@dataclass
class Table:
    columns: list[Column] = dc_field(default_factory=list)
    rows: list[Row] = dc_field(default_factory=list)
    #: A value stated in the heading above the table that governs every row, such as a pay
    #: level the column does not repeat.
    heading: str = ''
    heading_values: dict = dc_field(default_factory=dict)

    @property
    def kinds(self) -> list[ColumnKind]:
        return [c.kind for c in self.columns]


#: An ordinal and its text on one line, repeated: "(i) Something", "1. Something".
_LIST_ITEM = re.compile(
    r'^\s*\(?\s*(?P<ordinal>\d{1,3}|[ivxlIVXL]{1,5})\s*[.)]\s+(?P<text>\S.{2,160})$')

#: How many items before a run of ordinals is a list rather than a coincidence.
_LIST_MINIMUM = 3

#: What is being listed, and a word pointing at the list. Both are needed: a paragraph that
#: mentions posts is not an introduction to a list of them.
_LISTS_POSTS = re.compile(
    r'\b(?:services?|posts?|cadres?|designations?|vacanc\w+)\b[^.]{0,120}?'
    r'\b(?:below|following|as\s+under|namely|as\s+follows)\b|'
    r'\b(?:below|following|as\s+under|namely|as\s+follows)\b[^.]{0,120}?'
    r'\b(?:services?|posts?|cadres?|designations?)\b', re.I)

#: How far above a list its introduction may sit. A wrapped sentence is several lines.
_INTRODUCTION_LINES = 8


def _introduces_posts(lines: list[str], first_item: int) -> bool:
    """Does anything just above this list say that it lists posts?"""
    above: list[str] = []
    for k in range(first_item - 1, -1, -1):
        if lines[k].strip():
            above.append(lines[k].strip())
        if len(above) >= _INTRODUCTION_LINES:
            break
    return bool(_LISTS_POSTS.search(' '.join(reversed(above))))


def reconstruct_lists(text: str, *, max_lists: int = 12) -> list[Table]:
    """Runs of numbered items, each naming one thing.

    A value recognisable on sight inside an item -- a classification, a pay level -- is
    split out as its own column. Everything before it is the name. An item with no such
    value yields a name and nothing else, which is a complete answer rather than a gap.
    """
    lines = (text or '').split('\n')
    out: list[Table] = []
    # The raw line is kept with each item: the evidence span has to be what the document
    # actually contains, and "(i) Something" rebuilt from its parts is not.
    run: list[tuple[str, str, str]] = []
    run_start = [0]

    def names_a_thing(item: str) -> bool:
        """Is this item a name, or a piece of a sentence?

        A post is named with a noun phrase: it begins with a capital and does not end with
        a full stop or a conjunction. The items this rejects are clauses from other lists —
        "offering illegal gratification to; or", "Short Essays." — which are enumerated
        the same way and are not posts.
        """
        text = item.strip()
        if len(text) < 4 or not text[0].isupper():
            return False
        if text.endswith(('.', ';', ':', ',')) or re.search(r'\b(?:or|and)\s*$', text, re.I):
            return False
        return True

    def flush() -> None:
        if len(run) < _LIST_MINIMUM or not _introduces_posts(lines, run_start[0]):
            run.clear()
            return
        named = [t for t in run if names_a_thing(t[1])]
        if len(named) < _LIST_MINIMUM:
            run.clear()
            return
        run[:] = named
        columns = [Column(ColumnKind.SERIAL, 'ordinal', 0),
                   Column(ColumnKind.NAME, 'item', 1)]
        rows: list[Row] = []
        typed_seen = False
        for ordinal, item, raw in run:
            cells = {}
            name = item.strip()
            for kind, shape in _VALUE_SHAPES.items():
                if kind is ColumnKind.VACANCY:
                    continue           # a bare number inside an item is not a count
                m = shape.search(item)
                if m:
                    cells[kind] = item[m.start():m.end()].strip()
                    name = item[:m.start()].strip(' ,;-')
                    typed_seen = True
                    break
            cells[ColumnKind.NAME] = name
            rows.append(Row(cells=cells, span=raw.strip()[:900],
                            ordinal=ordinal, reconstructed=bool(name),
                            raw_cells=[name]))
        if typed_seen:
            columns.append(Column(ColumnKind.CLASSIFICATION, 'inline', 2))
        out.append(Table(columns=columns, rows=rows))
        run.clear()

    for index, line in enumerate(lines):
        m = _LIST_ITEM.match(line.rstrip())
        if m:
            if not run:
                run_start[0] = index
            run.append((m.group('ordinal'), m.group('text').strip(), line.strip()))
            continue
        if line.strip():
            flush()
            if len(out) >= max_lists:
                return out
    flush()
    return out[:max_lists]


# ------------------------------------------------------------------ headers
def _columns_in(text: str) -> list[Column]:
    """The columns a header line names, in the order it names them.

    Matched on position so that "Name of Post Ministry/Department" yields the post column
    before the department one — the order is what lets cells be assigned by walking left to
    right.
    """
    found: list[tuple[int, ColumnKind, str]] = []
    taken: list[tuple[int, int]] = []
    for kind, pattern in _HEADER_CUES:
        for m in re.finditer(pattern, text, re.I):
            if any(m.start() < end and start < m.end() for start, end in taken):
                continue
            taken.append(m.span())
            found.append((m.start(), kind, m.group(0).strip()))
            break
    found.sort()
    # One column per kind. A specific cue and a generic one for the same column both match
    # -- "Name of Post" and the bare "post" after it -- and two NAME columns means every
    # cell after the first lands one place to the left.
    out: list[Column] = []
    claimed: set = set()
    for _pos, kind, label in found:
        if kind in claimed:
            continue
        claimed.add(kind)
        out.append(Column(kind=kind, label=label, order=len(out)))
    return out


def find_header(lines: list[str], *, start: int = 0,
                lookahead: int = 6) -> tuple[int, list[Column]] | None:
    """The first header block, and the columns it declares.

    A header is wrapped like any other cell, so consecutive lines are joined until enough
    column words appear together. Two is the minimum: one word is a sentence mentioning a
    post, two in a row is a table saying what its columns are.
    """
    for i in range(start, len(lines)):
        if _SECTION_HEADING.match(lines[i].strip()):
            # A heading states a value for the table below it; it does not name columns,
            # and joining from one read its "Pay Level" as a column of its own.
            continue
        joined = ''
        best: tuple[int, list[Column]] | None = None
        for j in range(i, min(i + lookahead, len(lines))):
            if _SECTION_HEADING.match(lines[j].strip()):
                # A heading interrupts a header rather than continuing it. Joining across
                # one read the heading's "Pay Level" as the table's first column.
                joined = ''
                continue
            joined = (joined + ' ' + lines[j]).strip()
            columns = _columns_in(joined)
            if len(columns) >= 2 and (best is None or len(columns) > len(best[1])):
                best = (j, columns)
            # Rows have begun; the header cannot still be growing.
            if _ORDINAL.match(lines[j].strip()) and best is not None:
                break
        if best is None:
            continue
        # A header is followed by its first row. Without this, a paragraph that happens to
        # mention posts and ministries was read as a two-column header.
        nxt = next((lines[k].strip() for k in range(best[0] + 1, len(lines))
                    if lines[k].strip()), '')
        if not _ORDINAL.match(nxt):
            continue
        return best
    return None


# --------------------------------------------------------------------- cells
def split_cells(lines: list[str]) -> list[str]:
    """Group a row's lines into cells, using how the PDF wrapped them.

    A cell continues while its line was wrapped (trailing whitespace), while its brackets
    are still open, or while the next line begins with an opening bracket. Nothing here
    looks at what the text says.
    """
    cells: list[str] = []
    current: list[str] = []

    def balanced(parts: list[str]) -> bool:
        text = ' '.join(parts)
        return (text.count('(') == text.count(')')
                and text.count('[') == text.count(']'))

    for index, raw in enumerate(lines):
        line = raw.rstrip('\r\n')
        if not line.strip():
            continue
        current.append(line.strip())

        wrapped = line != line.rstrip()
        next_line = ''
        for k in range(index + 1, len(lines)):
            if lines[k].strip():
                next_line = lines[k].strip()
                break
        continues = (wrapped
                     or not balanced(current)
                     or next_line.startswith('('))
        if not continues:
            cells.append(' '.join(current).strip())
            current = []
    if current:
        cells.append(' '.join(current).strip())
    return [c for c in cells if c]


# ---------------------------------------------------------------------- rows
def _row_blocks(lines: list[str], start: int, header_lines: list | None = None) -> tuple[list, int]:
    """Split the lines after a header into rows, on the ordinals that begin them.

    Collection stops at the next section heading: a table ends where the next one is
    introduced, and running on produced rows made of two tables' cells.
    """
    blocks: list[tuple[str, list[str]]] = []
    current_ordinal = ''
    current: list[str] = []
    index = start
    expected: int | None = None

    def ordinal_value(token: str) -> int | None:
        digits = re.sub(r'[^\d]', '', token)
        if digits:
            return int(digits)
        roman = re.sub(r'[^ivxlIVXL]', '', token).lower()
        if not roman:
            return None
        values = {'i': 1, 'v': 5, 'x': 10, 'l': 50}
        total = previous = 0
        for char in reversed(roman):
            value = values.get(char, 0)
            total += -value if value < previous else value
            previous = max(previous, value)
        return total or None

    def continues_the_sequence(token: str) -> bool:
        """Does this ordinal follow the last one?

        A count in a cell is a bare number too, and treating it as a row boundary split the
        row that contained it. The sequence is what tells them apart.
        """
        nonlocal expected
        value = ordinal_value(token)
        if value is None:
            return False
        if expected is None:
            # The first ordinal establishes the run. Tables start at 1, occasionally at 0;
            # allowing any starting value let stray numbers open rows and cost real posts.
            if value > 2:
                return False
            expected = value
            return True
        if value == expected + 1:
            expected = value
            return True
        return False
    for index in range(start, len(lines)):
        stripped = lines[index].strip()
        if _SECTION_HEADING.match(stripped):
            break
        # The header appearing again ends this table's rows. Recognised by its own text:
        # searching for a header instead found the next one far below, and anchoring on a
        # found header's end cut a row short.
        if current_ordinal and stripped and stripped in (header_lines or ()):
            # The fragment a wrapped header leaves above its main line belongs to the
            # header, not to the row it interrupted.
            while current and len(current[-1].strip()) <= 4:
                current.pop()
            break
        if _FURNITURE.match(stripped):
            continue
        if _ORDINAL.match(stripped) and continues_the_sequence(stripped):
            if current_ordinal:
                blocks.append((current_ordinal, current))
            current_ordinal, current = stripped, []
            continue
        if current_ordinal:
            current.append(lines[index])
    else:
        index = len(lines)
    if current_ordinal:
        blocks.append((current_ordinal, current))
    # The line where collection stopped, so the caller resumes exactly there. Counting
    # block lengths under-counted, because blank and furniture lines are skipped, and the
    # cursor then landed inside the table it had just read.
    return blocks, index


def _assign(cells: list[str], columns: list[Column]) -> tuple[dict, bool, str]:
    """Map cells onto columns, or say that they could not be mapped.

    Three attempts, weakest last. Positional assignment where the counts match; then
    placing the recognisable values and giving the rest to a single remaining column; then
    cutting a run-together row at the values themselves. What none of them will do is
    distribute text between columns on a guess.
    """
    data_columns = [c for c in columns if c.kind is not ColumnKind.SERIAL]
    if not data_columns:
        return {}, False, 'the header declared no data columns'

    if len(cells) == len(data_columns):
        assigned = {c.kind: cells[i] for i, c in enumerate(data_columns)}
        # A recognisable value sitting in the wrong column means the reading is wrong,
        # whatever the counts say.
        for kind, shape in _VALUE_SHAPES.items():
            if kind not in assigned:
                continue
            misplaced = [c for k, c in assigned.items()
                         if k is not kind and shape.match(c)]
            if shape.search(assigned[kind]) is None and misplaced:
                return {}, False, (
                    f'the {kind.value.lower()} column does not hold a '
                    f'{kind.value.lower()} value, but another column does')
        return assigned, True, ''

    # Counts differ. Where every recognisable value can be placed and exactly one
    # unrecognisable column remains, the rest of the text belongs to it.
    typed = [c for c in data_columns if c.kind in _VALUE_SHAPES]
    untyped = [c for c in data_columns if c.kind not in _VALUE_SHAPES]
    matched: dict = {}
    leftovers = list(cells)
    for column in typed:
        shape = _VALUE_SHAPES[column.kind]
        hit = next((c for c in leftovers if shape.search(c)), None)
        if hit is None:
            break
        matched[column.kind] = hit
        leftovers.remove(hit)
    if typed and len(matched) == len(typed) and len(untyped) == 1 and leftovers:
        matched[untyped[0].kind] = ' '.join(leftovers)
        return matched, True, ''

    # Nothing in the line structure separated the cells. The values still can.
    by_value, note = _split_on_values(' '.join(cells), data_columns)
    if by_value:
        return by_value, True, note

    return {}, False, (
        f'{len(cells)} cell(s) were recovered for {len(data_columns)} column(s), and the '
        f'values do not identify which is which; the row is kept unassigned rather than '
        f'guessed')


def _split_on_values(joined: str, data_columns: list[Column]) -> tuple[dict, str]:
    """Cut a run-together row at the values that can be recognised on sight.

    Returns the assignment and a note, or an empty assignment where too little could be
    placed to be worth keeping. The note is non-empty when two untyped columns had to share
    one run of text, which is what marks the row for review.
    """
    typed = [c for c in data_columns if c.kind in _VALUE_SHAPES]
    if not typed or not joined.strip():
        return {}, ''

    cuts: list[tuple[int, int, Column]] = []
    cursor = 0
    for column in typed:
        m = _VALUE_SHAPES[column.kind].search(joined, cursor)
        if m is None:
            continue
        cuts.append((m.start(), m.end(), column))
        cursor = m.end()
    if not cuts:
        return {}, ''

    assigned: dict = {}
    note = ''
    position = 0
    remaining = list(data_columns)

    for start, end, column in cuts:
        before = joined[position:start].strip()
        preceding = []
        while remaining and remaining[0].kind is not column.kind:
            preceding.append(remaining.pop(0))
        if remaining:
            remaining.pop(0)

        if preceding:
            if len(preceding) == 1:
                assigned[preceding[0].kind] = before
            elif before:
                # Several columns, one run of text, nothing to divide it on.
                assigned[preceding[0].kind] = before
                note = (f'{len(preceding)} columns shared one run of text '
                        f'({", ".join(c.kind.value.lower() for c in preceding)}) and '
                        f'nothing in the row separates them, so it is held for review')
        assigned[column.kind] = joined[start:end].strip()
        position = end

    tail = joined[position:].strip()
    if tail and remaining:
        assigned[remaining[0].kind] = tail

    # A row that yielded only its age is not a row worth keeping.
    if len([v for v in assigned.values() if v]) < 2:
        return {}, ''
    return assigned, note


#: A value stated in a heading that governs the table below it, such as a pay level the
#: rows do not repeat.
_HEADING_VALUE = (
    (ColumnKind.PAY, re.compile(r'\bpay\s+level[\s-]*\d{1,2}\b[^:\n]{0,40}', re.I)),
)


def _next_nonblank(lines: list[str], index: int) -> tuple[int, str]:
    for k in range(index, len(lines)):
        if lines[k].strip():
            return k, lines[k].strip()
    return len(lines), ''


def _heading_values(above: str, columns: list[Column]) -> dict:
    out: dict = {}
    declared = [c.kind for c in columns]
    for kind, pattern in _HEADING_VALUE:
        m = pattern.search(above)
        if m and kind not in declared:
            out[kind] = m.group(0).strip()
    return out


def reconstruct(text: str, *, max_tables: int = 40) -> list[Table]:
    """Every table this document contains, as far as the structure can be recovered.

    A document states a header once and may then run several sections under it, each with
    its own heading. Those are separate tables sharing a column layout, not one table with
    a confusing middle -- so they are returned separately, each carrying the value its own
    heading states.
    """
    lines = (text or '').split('\n')
    tables: list[Table] = []
    cursor = 0
    columns: list[Column] = []
    header_text: list[str] = []

    while cursor < len(lines) and len(tables) < max_tables:
        index, first = _next_nonblank(lines, cursor)
        if not first:
            break

        heading = ''
        if _SECTION_HEADING.match(first):
            heading = first
            index, first = _next_nonblank(lines, index + 1)

        if _ORDINAL.match(first) and columns:
            # A section continuing the table above it: rows, no header of its own.
            start = index
        else:
            header = find_header(lines, start=cursor)
            if header is None:
                break
            header_end, columns = header
            start = header_end + 1
            # The lines the header occupies, so a repeat of it can be recognised later.
            header_text = [l.strip() for l in lines[max(0, header_end - 5):header_end + 1]
                           if len(l.strip()) > 4]
            above = ' '.join(l.strip() for l in lines[max(0, header_end - 6):header_end])
            heading = heading or above
            index = header_end

        table = Table(columns=columns, heading=heading)
        table.heading_values = _heading_values(heading, columns)

        blocks, stopped = _row_blocks(lines, start, header_text)
        if not blocks:
            cursor = max(start, index + 1, stopped)
            continue

        for ordinal, block in blocks:
            cells = split_cells(block)
            assigned, ok, note = _assign(cells, columns)
            span = ' '.join(l.strip() for l in [ordinal] + block if l.strip())
            table.rows.append(Row(cells=assigned, span=span[:900], ordinal=ordinal,
                                  reconstructed=ok, note=note, raw_cells=cells))

        tables.append(table)
        cursor = max(stopped, index + 1)

    return tables
