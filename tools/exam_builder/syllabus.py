"""Read an exam's syllabus from whatever its authority published, at whatever depth.

Two of the four captured notices publish a syllabus and they publish it two ways (see
SYLLABUS_AUDIT.md §7). One numbers every clause -- `13.10 Indicative Syllabus (Tier-I):`,
`13.11.1 Part A of Section-I of Paper-I (Mathematical Abilities):`, `13.11.1.1 Number
Systems: …` -- so the numbering *is* the hierarchy and its depth is the count of its parts.
The other writes headings and bullets: `Part A—Preliminary Examination`, `Paper I - (200
marks)`, then seven bullets, each of which is a syllabus entry belonging to that paper.

The other two publish none, and that is a finding rather than a gap in this reader.

Three rules run through all of it, the same three the pattern reader follows:

  * **Hierarchy is read, never assumed.** A node's parent is the clause that numbers it or
    the heading it sits under. Where neither establishes a parent, the node is kept at the
    level it was found and marked NEEDS_REVIEW rather than attached to a plausible one.
  * **A title is not its contents.** An authority that names "General Studies" and does not
    list its topics gets a VERIFIED node with no children -- never invented ones.
  * **A value is only a value if its span is verbatim in the document.** Titles are checked
    against the source before they are published, and a title that cannot be found is kept
    for review rather than asserted.
"""
from __future__ import annotations

import re

from .evidence import normalise_ws
from .pattern import (_Cursor, _evidence, _IS_STATEMENT, _is_marked, _slug,
                      may_supply_pattern)
from .schema import (Fact, Scope, ScopeKind, ScopeRef, SourceDocument, Status, Syllabus,
                     SyllabusNode)

# ================================================================= where it starts
#: A heading that says a syllabus follows. "Indicative Syllabus", "SYLLABI FOR THE
#: EXAMINATION", "Scheme and Syllabus", "Detailed Syllabus" -- all of them ordinary
#: English, none of them any authority's private word.
_SYLLABUS_HEADING = re.compile(
    r'\b(?:syllabus|syllabi|curriculum|course\s+content|scope\s+of\s+the\s+(?:exam\w*|'
    r'paper|test)|subjects?\s+for\s+the\s+exam\w*)\b', re.I)

#: Where a syllabus stops. Deliberately narrow: a heading *inside* a syllabus -- "Part
#: A-Preliminary Examination", "Paper I", "Section-I" -- is part of it, and treating those
#: as the end left one authority's whole syllabus unread.
#:
#: A syllabus ends where the notice turns to something else: the next section at the level
#: the syllabus itself opened in, an annexure of its own, or one of the things a notice
#: does by name.
_SECTION_HEADING = re.compile(r'^\s*(?:section|chapter)\s*[-\u2013]?\s*[IVXL0-9]+\b', re.I)
_ANNEXURE_HEADING = re.compile(r'^\s*(?:annexure|appendix)\b[-\s]*[IVXL0-9]*\s*[:.]?\s*$',
                               re.I)
_NAMED_SECTION = re.compile(
    r'^\s*(?:how\s+to\s+apply|application\s+fees?|mode\s+of\s+payment|important\s+dates|'
    r'instructions?\s+to\s+(?:the\s+)?candidates?|general\s+instructions|declaration|'
    r'acknowledgement|list\s+of\s+(?:exam\w*\s+)?centres?)\b', re.I)


def _ends_syllabus(line: str, *, opened_in_section: bool) -> bool:
    if _SYLLABUS_HEADING.search(line):
        return False
    if _NAMED_SECTION.match(line) or _ANNEXURE_HEADING.match(line):
        return True
    # Only where the syllabus was itself opened by a section heading does another section
    # heading end it; otherwise a syllabus printed inside a section would end at its own.
    return bool(opened_in_section and _SECTION_HEADING.match(line))


#: A clause number opening a line: "13.11.1.1", "2.3", "1.". Its depth is its part count.
_CLAUSE = re.compile(r'^\s*(?P<number>\d{1,2}(?:\.\d{1,3}){0,5})\.?\s+(?P<rest>\S.*)$')

#: A bullet, in the shapes PDFs leave behind once the glyph is extracted.
_BULLET = re.compile(r'^\s*(?:[•●▪◦·⁃\-–—*]|'
                     r'\(?[ivxl]{1,4}\)|\([a-z]\))\s+(?P<rest>\S.*)$', re.I)

#: A heading naming a level of the exam, with or without an ordinal: "Paper I", "Part B—Main
#: Examination", "Section-I", "Unit III". The label is the authority's own word for it.
_LEVEL_HEADING = re.compile(
    r'^\s*(?P<label>paper|part|section|unit|module|group|subject|topic|stage|tier|phase)'
    r'\s*[-–—:\s]?\s*(?P<ord>[IVXL]{1,4}|\d{1,2}|[A-H])?\b\s*'
    r'[-–—:.]?\s*(?P<rest>.*)$', re.I)

#: A title followed by its own description: "Number Systems: Computation of Whole Number…".
#: The part before the colon is what the syllabus calls the entry; the rest is its scope.
_TITLED = re.compile(r'^(?P<title>[^:]{3,90}?)\s*:\s*(?P<body>\S.*)$')

#: Page furniture inside a syllabus, which a flattened PDF scatters through it.
_FURNITURE = re.compile(
    r'^\s*(?:page\s+\d+\s+of\s+\d+|go\s+to\s+index\s*\d*|\d+\s*\|\s*page|contd\.?)\s*$',
    re.I)

#: A note about the syllabus rather than a part of it.
_NOTE_LINE = re.compile(r'^\s*(?:note\s*[-:\d]|n\.b\.)', re.I)


# ==================================================================== scope
#: Words that bind a syllabus entry to a stage or a paper when its heading names one.
_SCOPE_WORDS: tuple[tuple[str, ScopeKind], ...] = (
    ('paper', ScopeKind.PAPER),
    ('tier', ScopeKind.STAGE),
    ('phase', ScopeKind.STAGE),
    ('stage', ScopeKind.STAGE),
    ('part', ScopeKind.SECTION),
    ('section', ScopeKind.SECTION),
)


def _scope_of(title: str, inherited: Scope) -> Scope:
    """What this heading binds its entries to, on top of whatever it inherited.

    "Part A of Section-I of Paper-I (Mathematical Abilities)" names three levels at once,
    and all three are kept: the entry belongs to Paper-I, to Section-I within it, and to
    Part A within that. A heading that names none inherits its parent's scope unchanged --
    which is what makes a bullet under "Paper I" belong to Paper I.
    """
    refs = list(inherited.refs)
    seen = {(r.kind, r.ref) for r in refs}
    for word, kind in _SCOPE_WORDS:
        for match in re.finditer(
                rf'\b{word}\s*[-–—\s]?\s*([IVXL]{{1,4}}|\d{{1,2}}|[A-H])\b',
                title or '', re.I):
            label = f'{word.title()}-{match.group(1).upper()}'
            ref = _slug(label)
            if (kind, ref) not in seen:
                seen.add((kind, ref))
                refs.append(ScopeRef(kind, ref, label))
    return Scope(refs)


# ================================================================= the regions
def _syllabus_regions(cur: _Cursor) -> list[tuple[int, int, str]]:
    """Every stretch of the document that is a syllabus, with the heading that opens it.

    A notice may publish more than one -- one per stage, or one per paper -- so this
    returns all of them rather than the first.
    """
    regions: list[tuple[int, int, str]] = []
    for index, raw in enumerate(cur.lines):
        line = raw.strip()
        if not line or len(line) > 120:
            continue
        if not _SYLLABUS_HEADING.search(line):
            continue
        if _in_annexure_list(cur.lines, index):
            # "Annexure-II Scheme and Syllabus." between "Annexure-I Breakup of Vacancies."
            # and "Annexure-III List of Communities." is a table of contents naming the
            # syllabus, not the syllabus; read as one, the headings after it became a root.
            continue
        # A heading is marked, numbered, or simply a short line whose subject is the
        # syllabus. The third case is a real one -- "Syllabus for the Examination" carries
        # no colon, no number and no capitals, and it is still the heading.
        short_title = len(line.split()) <= 8 and line[:1].isupper()
        if not (_is_marked(line) or _CLAUSE.match(line) or short_title):
            continue
        if _IS_STATEMENT.search(line) and not _CLAUSE.match(line):
            continue
        # A sentence advising candidates to read the syllabus is not the syllabus.
        if len(line.split()) > 12:
            continue
        own_clause = _CLAUSE.match(line)
        end = _region_end(cur, index + 1,
                          opening_depth=_depth_of(own_clause.group('number'))
                          if own_clause else 0,
                          opened_in_section=bool(_SECTION_HEADING.match(line)))
        if end - index > 2:
            regions.append((index, end, line))

    # A region wholly inside another is that one's subsection, not a region of its own --
    # except under a "Scheme and Syllabus" heading, which prints the scheme first (a table of
    # papers, durations and marks) and then the syllabus under its own heading. There the
    # syllabus starts at the inner heading: read from the outer one, the scheme table's rows
    # ("3 150" / "Paper-II – History, Culture and Geography") became syllabus topics.
    out: list[tuple[int, int, str]] = []
    for region in regions:
        outer = next((o for o in regions if o[0] < region[0] and region[1] <= o[1]), None)
        if outer is not None and not (_SCHEME.search(outer[2]) and _BARE_SYLLABUS.match(region[2])):
            continue
        inner = [r for r in regions if region[0] < r[0] and r[1] <= region[1]]
        if _SCHEME.search(region[2]) and any(_BARE_SYLLABUS.match(r[2]) for r in inner):
            continue
        out.append(region)
    return out


#: A heading that announces the scheme of examination before its syllabus.
_SCHEME = re.compile(r'\bscheme\b', re.I)
#: A heading that is the syllabus and nothing else: "SYLLABUS", "Detailed Syllabus", "Syllabi".
_BARE_SYLLABUS = re.compile(r'^\s*(?:detailed\s+)?(?:syllabus|syllabi)\s*[:.]?\s*$', re.I)
#: A reference to an annexure by number and title, as a list of annexures prints it.
_ANNEXURE_REFERENCE = re.compile(r'^\s*(?:annexure|appendix)\s*[-–]?\s*[IVXL0-9]+\b\s*[-–:.]?\s*\S', re.I)


def _in_annexure_list(lines: list[str], index: int) -> bool:
    """Is this line one entry of a list of annexures (a table of contents)?"""
    if not _ANNEXURE_REFERENCE.match(lines[index]):
        return False
    neighbours = []
    for step in (-1, 1):
        k = index + step
        while 0 <= k < len(lines) and not lines[k].strip():
            k += step
        if 0 <= k < len(lines):
            neighbours.append(lines[k])
    return any(_ANNEXURE_REFERENCE.match(n) for n in neighbours)


def _region_end(cur: _Cursor, start: int, *, opening_depth: int = 0,
                opened_in_section: bool = False) -> int:
    """Where a syllabus stops.

    Either the next section of the notice that is not a syllabus, or another syllabus at
    the same level. One notice publishes "13.10 Indicative Syllabus (Tier-I)" and "13.11
    Indicative Syllabus (Tier-II)" as siblings; without the second test the first ran to
    the end and swallowed the second as one of its own subjects.
    """
    for index in range(start, len(cur.lines)):
        line = cur.lines[index].strip()
        if not line:
            continue
        if _ends_syllabus(line, opened_in_section=opened_in_section):
            return index
        if opening_depth and _SYLLABUS_HEADING.search(line):
            clause = _CLAUSE.match(line)
            if clause and _depth_of(clause.group('number')) <= opening_depth:
                return index
    return len(cur.lines)


# ================================================================= clause reading
def _depth_of(number: str) -> int:
    return len([p for p in (number or '').split('.') if p])


def _only_page_numbers_between(printed: str, entry: str) -> bool:
    """Is `printed` the entry's own words, in order, with nothing added but bare page numbers
    (the footer a PDF prints where an entry runs over a page)?"""
    p, e = normalise_ws(printed).split(), normalise_ws(entry).split()
    i = 0
    for word in p:
        if i < len(e) and word == e[i]:
            i += 1
        elif not re.fullmatch(r'\d{1,3}', word):
            return False
    return i == len(e)


def _covers(ev, span: str) -> bool:
    """Does this evidence quote the whole span (whitespace, and a page number printed inside a
    wrapped entry, aside)?"""
    return ev is not None and (normalise_ws(ev.span) == normalise_ws(span)
                               or _only_page_numbers_between(ev.span, span))


def _entry_evidence(entry_text: str, first_line: str, doc: SourceDocument, text: str, *,
                    reading: str):
    """Evidence for a syllabus entry: the whole entry as printed, across every line it wrapped
    onto, so the quotation covers the title and note it publishes. An entry that runs over a
    page has the page's number printed between its lines; the quotation is then the printed
    span itself, number and all, which is verbatim. Where neither is found, its first line is
    the evidence, and the caller holds the node for review instead of calling it covered."""
    entry = entry_text.strip()
    whole = _evidence(entry, doc, text, reading=reading) if entry else None
    if whole is None and entry:
        flat, head, tail = normalise_ws(text), normalise_ws(first_line), normalise_ws(entry)[-40:]
        at = flat.find(head)
        end = flat.find(tail, at) if at >= 0 else -1
        if at >= 0 and end >= 0:
            printed = flat[at:end + len(tail)]
            if _only_page_numbers_between(printed, entry):
                whole = _evidence(printed, doc, text, reading=reading)
    return whole or _evidence(first_line, doc, text, reading=reading)


def _split_title(text: str) -> tuple[str, str]:
    """An entry's own name, and the description the authority wrote after it.

    A colon separates them where there is one. Where there is not, a dash often does --
    "Measures of Central Tendency- Common measures of central tendency, mean median and
    mode" -- and reading the whole run-on sentence as the entry's name makes a syllabus
    nobody can scan. Neither separator is invented: the text is split where the authority
    punctuated it, and if it punctuated nowhere the whole line stays the title.
    """
    cleaned = (text or '').strip()
    titled = _TITLED.match(cleaned)
    if titled:
        return titled.group('title').strip(' .;,:'), titled.group('body').strip()
    dashed = re.match(r'^(?P<title>[^–—-]{3,70}?)\s*[–—-]\s+(?P<body>\S.*)$',
                      cleaned)
    if dashed:
        return dashed.group('title').strip(' .;,:'), dashed.group('body').strip()
    return cleaned.strip(' .;,:'), ''


def _clause_blocks(cur: _Cursor, start: int, end: int) -> list[tuple[str, str, int]]:
    """Each numbered clause as one piece of text, however many lines it was printed on.

    A flattened PDF breaks a heading wherever the column ran out, so the colon that ends a
    title is regularly on the next line: "Part B of Section-I of Paper-I (Reasoning and
    General" / "Intelligence):". Reading a clause rather than a line is what keeps those
    titles whole.
    """
    blocks: list[tuple[str, str, int]] = []
    number, buffer, at = '', [], start
    for index in range(start, min(end, len(cur.lines))):
        line = cur.lines[index].strip()
        if not line or _FURNITURE.match(line):
            continue
        clause = _CLAUSE.match(line)
        if clause:
            if number:
                blocks.append((number, ' '.join(buffer), at))
            number, buffer, at = clause.group('number'), [clause.group('rest').strip()], index
            continue
        if number:
            buffer.append(line)
    if number:
        blocks.append((number, ' '.join(buffer), at))
    return blocks


def _read_clauses(cur: _Cursor, doc: SourceDocument, start: int, end: int, *,
                  prefix: str, root_scope: Scope) -> list[SyllabusNode]:
    """A syllabus whose hierarchy is its own clause numbering.

    "13.11.1.1" is a child of "13.11.1" is a child of "13.11". Nothing about the depth is
    assumed: it is the number of parts the authority wrote, and an authority that numbers
    two levels gets two.
    """
    roots: list[SyllabusNode] = []
    stack: list[tuple[int, SyllabusNode]] = []
    opening_depth: int | None = None

    for number, body_text, index in _clause_blocks(cur, start, end):
        depth = _depth_of(number)
        if opening_depth is None:
            opening_depth = depth

        title, body = _split_title(body_text)
        # A clause whose title is a whole sentence is a rule about the syllabus rather than
        # an entry in it. Its words are kept on the node above rather than made a node.
        if not title or (_IS_STATEMENT.search(title) and len(title.split()) > 8):
            if stack:
                node = stack[-1][1]
                node.note = (node.note + ' ' + body_text).strip()
            continue

        node = SyllabusNode(
            id=f'{prefix}-{_slug(number)}',
            title=title,
            level_label=_level_label(title, depth - (opening_depth or 1)),
            order=1)
        if body:
            node.note = body

        evidence = _entry_evidence(body_text, cur.lines[index].strip(), doc, cur.text,
                                   reading=f'a syllabus entry: {title[:60]}')
        if evidence:
            node.evidence = [evidence]
            node.status = Status.VERIFIED if _covers(evidence, body_text) else Status.NEEDS_REVIEW
        else:
            node.status = Status.NEEDS_REVIEW
            node.note = (node.note + ' [span not verbatim in the source]').strip()

        while stack and stack[-1][0] >= depth:
            stack.pop()
        parent = stack[-1][1] if stack else None
        node.scope = _scope_of(title, parent.scope if parent else root_scope)
        if parent is None:
            node.order = len(roots) + 1
            roots.append(node)
        else:
            node.order = len(parent.children) + 1
            parent.children.append(node)
        stack.append((depth, node))
    return roots


def _level_label(title: str, relative_depth: int) -> str:
    """The authority's own word for this level, where its heading uses one."""
    head = _LEVEL_HEADING.match(title or '')
    if head and head.group('label'):
        return head.group('label').title()
    return ['Subject', 'Topic', 'Subtopic', 'Detail'][min(max(relative_depth, 0), 3)]


# ================================================================ heading + bullets
def _read_headings_and_bullets(cur: _Cursor, doc: SourceDocument, start: int, end: int, *,
                               prefix: str, root_scope: Scope) -> list[SyllabusNode]:
    """A syllabus written as headings with bullets under them.

    The heading is the thing the bullets belong to -- a paper, a part, a subject -- and its
    own wording says which. A bullet is one entry of that thing's syllabus, and it is kept
    whole: "Indian Polity and Governance-Constitution, Political System, Panchayati Raj,
    Public Policy, Rights Issues, etc." is one entry the authority wrote, not six.
    """
    roots: list[SyllabusNode] = []
    stack: list[tuple[int, SyllabusNode]] = []
    pending: list[str] = []

    def rank(label: str) -> int:
        order = {'part': 0, 'section': 1, 'paper': 2, 'unit': 3, 'module': 3,
                 'group': 3, 'subject': 4, 'topic': 5}
        return order.get((label or '').lower(), 4)

    def flush_bullet(text: str, index: int) -> None:
        if not stack:
            return
        parent = stack[-1][1]
        title, entry_body = _split_title(text)
        node = SyllabusNode(
            id=f'{prefix}-{_slug(parent.title)[:18]}-{len(parent.children) + 1}',
            title=title,
            level_label='Topic',
            order=len(parent.children) + 1,
            scope=parent.scope)
        if entry_body:
            node.note = entry_body
        evidence = _entry_evidence(text, cur.lines[index].strip(), doc, cur.text,
                                   reading=f'a syllabus entry under {parent.title[:40]}')
        if evidence:
            node.evidence = [evidence]
            node.status = Status.VERIFIED if _covers(evidence, text) else Status.NEEDS_REVIEW
        else:
            node.status = Status.NEEDS_REVIEW
        parent.children.append(node)

    index = start
    while index < min(end, len(cur.lines)):
        line = cur.lines[index].strip()
        index += 1
        if not line or _FURNITURE.match(line):
            continue
        if _NOTE_LINE.match(line):
            if stack:
                stack[-1][1].note = (stack[-1][1].note + ' ' + line).strip()
            continue

        bullet = _BULLET.match(line)
        if bullet:
            if pending:
                flush_bullet(' '.join(pending), index - 2)
                pending = []
            pending = [bullet.group('rest').strip()]
            continue

        head = _LEVEL_HEADING.match(line)
        # A heading names a level *and* numbers it, or is marked as a heading in its own
        # right. Without the ordinal, the wrapped tail of a bullet -- "...that do not
        # require" / "subject specialization." -- was read as a heading called "subject".
        is_heading = (head and head.group('label') and len(line) < 110
                      and (head.group('ord') or _is_marked(line))
                      and not _IS_STATEMENT.search(line[:60]))
        if is_heading:
            if pending:
                flush_bullet(' '.join(pending), index - 2)
                pending = []
            label = head.group('label').title()
            ordinal = (head.group('ord') or '').upper()
            trailing = (head.group('rest') or '').strip(' -–—:')
            title = f'{label} {ordinal}'.strip()
            if trailing and len(trailing) < 80:
                title = f'{title} — {trailing}' if ordinal else trailing
            node = SyllabusNode(id=f'{prefix}-{_slug(title)}', title=title,
                                level_label=label, order=1)
            evidence = _evidence(line, doc, cur.text,
                                 reading=f'a syllabus heading: {title[:50]}')
            if evidence:
                node.evidence = [evidence]
                node.status = Status.VERIFIED
            else:
                node.status = Status.NEEDS_REVIEW
            level = rank(label)
            while stack and rank(stack[-1][1].level_label) >= level:
                stack.pop()
            parent = stack[-1][1] if stack else None
            node.scope = _scope_of(title, parent.scope if parent else root_scope)
            if parent is None:
                node.order = len(roots) + 1
                roots.append(node)
            else:
                node.order = len(parent.children) + 1
                parent.children.append(node)
            stack.append((level, node))
            continue

        if pending:
            # A bullet wrapped onto the next line.
            pending.append(line)
    if pending:
        flush_bullet(' '.join(pending), min(end, len(cur.lines)) - 1)
    return roots


# ===================================================================== outline
#: A numbered entry of a list: "1. Current Affairs", "10.Policies of Telangana State." (no
#: space after the stop, as printed). The entry starts with a letter or a bracket, so "13.10
#: Indicative Syllabus" -- a clause number -- is not read as entry 13.
_OUTLINE_ITEM = re.compile(r'^\s*(?P<n>\d{1,2})\s*\.\s*(?P<rest>[A-Za-z(“"\'‘].*)$')
#: A heading numbered in Roman: "I. History and Culture of India, with special reference to…".
_ROMAN_HEADING = re.compile(r'^\s*(?P<ord>[IVX]{1,4})\s*\.\s+(?P<rest>[A-Z].*)$')
#: A line that is only a page number.
_PAGE_NUMBER = re.compile(r'^\s*\d{1,3}\s*$')
#: A line in brackets under a heading: "(PRELIMINARY TEST)", "(X CLASS STANDARD)", or a
#: bracketed instruction such as "(Candidate should write three Essays …)".
_BRACKETED = re.compile(r'^\s*\(.*\)?\s*$')
#: Words naming a stage of the examination, in ordinary English.
_STAGE_WORDS = re.compile(r'\b(?:preliminary|prelims?|main|mains|written\s+examination|screening|'
                          r'interview|personality\s+test)\b', re.I)
_OUTLINE_LABELS = ('paper', 'section', 'part', 'unit', 'module')


def _read_outline(cur: _Cursor, doc: SourceDocument, start: int, end: int, *,
                  prefix: str, root_scope: Scope) -> list[SyllabusNode]:
    """A syllabus written as headings with numbered lists that restart under each heading.

    The commonest shape of all, and neither of the other two readings: the numbers do not
    carry the hierarchy ("1." restarts under every paper), and the entries are numbered
    rather than bulleted. "GENERAL STUDIES AND MENTAL ABILITY (PRELIMINARY TEST)" / "1.
    Current Affairs …"; "Written Examination (Main)" / "PAPER-II: HISTORY, CULTURE AND
    GEOGRAPHY" / "I. History and Culture of India …" / "1. Early Indian Civilizations …".

    A heading is recognised by what it is, never by where it happens to fall:
      * a labelled level with an ordinal ("PAPER-II: …", "Section-I");
      * a Roman-numbered heading ("II. History and Cultural Heritage of Telangana.");
      * a short title line that a numbered list restarting at 1 follows, or that another
        heading follows -- the latter being a stage when its words name one.
    A heading's bracketed line is its note. A number that does not continue its list is
    part of the entry before it. Headings are ranked stage > paper > section > entry; a
    heading nothing sits under is dropped, since it headed nothing.
    """
    lines: list[tuple[int, str]] = []
    open_bracket = False
    for index in range(start, min(end, len(cur.lines))):
        line = cur.lines[index].strip()
        if not line or _FURNITURE.match(line) or _PAGE_NUMBER.match(line):
            continue
        if open_bracket and lines:
            # A bracketed note wrapped across lines ("(Candidate should write three Essays,
            # selecting one from each" / "Section contains three Questions …)") is one note;
            # its second line read as a heading and took the paper's sections from it.
            lines[-1] = (lines[-1][0], f'{lines[-1][1]} {line}')
        else:
            lines.append((index, line))
        opened = lines[-1][1]
        open_bracket = opened.startswith('(') and opened.count('(') > opened.count(')')

    def next_kind(k: int, depth: int = 0) -> str:
        """What the next non-bracketed line is: an entry starting a list, a heading, or text.
        A short title line that itself heads a list is a heading too, one level deep: "Written
        Examination (Main)" is followed by "General English (Qualifying Test)", which is
        followed by "1. Spotting Errors"."""
        for j in range(k + 1, min(k + 4, len(lines))):
            text = lines[j][1]
            if _BRACKETED.match(text) and text.startswith('('):
                continue
            item = _OUTLINE_ITEM.match(text)
            if item:
                return 'first' if item.group('n') == '1' else 'item'
            if _labelled(text) or _ROMAN_HEADING.match(text):
                return 'heading'
            if depth == 0 and _short_title(text) and next_kind(j, depth + 1) in ('first', 'heading'):
                return 'heading'
            return 'text'
        return 'end'

    def _short_title(text: str) -> bool:
        return (len(text.split()) <= 10 and text[:1].isupper() and not text.endswith((',', ';', '-', '–'))
                and not _IS_STATEMENT.search(text) and not _OUTLINE_ITEM.match(text))

    def _labelled(text: str):
        head = _LEVEL_HEADING.match(text)
        if (head and (head.group('label') or '').lower() in _OUTLINE_LABELS and head.group('ord')
                and len(text) < 110 and not _IS_STATEMENT.search(text[:60])):
            return head
        return None

    def title_line(k: int, previous: str) -> bool:
        text = lines[k][1]
        if len(text.split()) > 10 or text.endswith((',', ';', '-', '–')) or not text[:1].isupper():
            return False
        if _IS_STATEMENT.search(text) or _OUTLINE_ITEM.match(text):
            return False
        # The line before must have ended, or be a heading line itself (short, in capitals:
        # "GROUP-I SERVICES" above "GENERAL STUDIES AND MENTAL ABILITY"): an entry's wrapped
        # tail is not a heading.
        letters = [c for c in previous if c.isalpha()]
        above_is_heading = (bool(letters) and len(previous.split()) <= 8
                            and sum(c.isupper() for c in letters) / len(letters) > 0.8)
        if previous and not previous.endswith(('.', ':', ')')) and not _labelled(previous) \
                and not _BRACKETED.match(previous) and not title_before.get(k - 1) \
                and not above_is_heading:
            return False
        return next_kind(k) in ('first', 'heading')

    roots: list[SyllabusNode] = []
    stack: list[tuple[int, SyllabusNode]] = []   # (rank, node); rank 0 stage … 3 entry
    title_before: dict[int, bool] = {}
    expected: dict[int, int] = {}                # id(parent) -> next entry number
    entry: list = [None, [], [], 0]              # [node, lines, raw lines, first index]

    def evidence_for(node: SyllabusNode, index: int, reading: str) -> None:
        ev = _evidence(cur.lines[index].strip(), doc, cur.text, reading=reading)
        node.evidence = [ev] if ev else []
        node.status = Status.VERIFIED if ev else Status.NEEDS_REVIEW

    def close_entry() -> None:
        node, parts, raw, first = entry
        if node is not None:
            title, body = _split_title(' '.join(parts))
            node.title = title or node.title
            if body:
                node.note = body
            # The evidence is the whole entry as printed, across the lines it wrapped onto,
            # so it covers the title and note it publishes, not only their first line.
            ev = _entry_evidence(' '.join(raw), cur.lines[first].strip(), doc, cur.text,
                                 reading=f'a syllabus entry: {node.title[:60]}')
            node.evidence = [ev] if ev else []
            covered = bool(ev) and (len(raw) == 1 or _covers(ev, ' '.join(raw)))
            node.status = Status.VERIFIED if covered else Status.NEEDS_REVIEW
        entry[0], entry[1], entry[2], entry[3] = None, [], [], 0

    def attach(node: SyllabusNode, rank: int) -> None:
        while stack and stack[-1][0] >= rank:
            stack.pop()
        parent = stack[-1][1] if stack else None
        node.scope = _scope_of(node.title, parent.scope if parent else root_scope)
        siblings = parent.children if parent else roots
        node.order = len(siblings) + 1
        siblings.append(node)
        if rank < 3:
            stack.append((rank, node))

    k = 0
    while k < len(lines):
        index, text = lines[k]
        previous = lines[k - 1][1] if k else ''
        labelled = _labelled(text)
        roman = _ROMAN_HEADING.match(text)
        item = _OUTLINE_ITEM.match(text)
        parent = stack[-1][1] if stack else None

        if item and parent is not None and int(item.group('n')) == expected.get(id(parent), 1):
            close_entry()
            node = SyllabusNode(id=f'{prefix}-{_slug(parent.title)[:18]}-{item.group("n")}',
                                title=item.group('rest'), level_label='Topic', order=1)
            evidence_for(node, index, f'a syllabus entry under {parent.title[:40]}')
            attach(node, 3)
            expected[id(parent)] = int(item.group('n')) + 1
            entry[0], entry[1], entry[2], entry[3] = node, [item.group('rest')], [text], index
            k += 1
            continue

        if labelled or roman or title_line(k, previous):
            close_entry()
            # A heading may wrap: take the lines up to the list it heads.
            parts, j = [text], k + 1
            while j < len(lines) and not _OUTLINE_ITEM.match(lines[j][1]) \
                    and not _labelled(lines[j][1]) and not _ROMAN_HEADING.match(lines[j][1]) \
                    and not parts[-1].endswith(('.', ')')) and len(parts) < 3 \
                    and not (_BRACKETED.match(lines[j][1]) and lines[j][1].startswith('(')) \
                    and not (_short_title(lines[j][1]) and next_kind(j) in ('first', 'heading')):
                parts.append(lines[j][1])
                j += 1
            notes = []
            while j < len(lines) and lines[j][1].startswith('(') and _BRACKETED.match(lines[j][1]):
                notes.append(lines[j][1])
                j += 1
            heading = ' '.join(parts).strip(' .:')
            if labelled:
                label = labelled.group('label').title()
                rank = 1 if label == 'Paper' else 2
            elif roman:
                # The whole wrapped title, not its first line: "… Modern Period (1757" / "to
                # 1947 A.D.)".
                label, rank = 'Subject', 2
                heading = _ROMAN_HEADING.match(heading).group('rest').strip(' .:')
            else:
                is_stage = bool(_STAGE_WORDS.search(heading)) and next_kind(j - 1) == 'heading'
                label, rank = ('Stage', 0) if is_stage else ('Subject', 1)
                if notes and not is_stage:
                    heading = f'{heading} {notes[0]}' if len(notes[0]) < 40 else heading
            node = SyllabusNode(id=f'{prefix}-{_slug(heading)[:40]}', title=heading,
                                level_label=label, order=1)
            if notes:
                node.note = ' '.join(notes)
            printed = ' '.join(parts + notes)
            ev = _entry_evidence(printed, cur.lines[index].strip(), doc, cur.text,
                                 reading=f'a syllabus heading: {heading[:50]}')
            node.evidence = [ev] if ev else []
            node.status = Status.VERIFIED if _covers(ev, printed) or (ev and len(parts) + len(notes) == 1)                 else Status.NEEDS_REVIEW
            attach(node, rank)
            title_before[j - 1] = True
            k = j
            continue

        if entry[0] is not None:
            entry[1].append(text)          # an entry wrapped onto the next line
            entry[2].append(text)
        k += 1
    close_entry()

    # A heading nothing sits under headed nothing -- a service name printed above the
    # syllabus ("GROUP-I SERVICES") -- unless it is a labelled paper, whose empty syllabus
    # is itself a fact ("a title is not its contents").
    def prune(nodes: list) -> list:
        kept = []
        for n in nodes:
            n.children = prune(n.children)
            if n.children or n.level_label in ('Topic', 'Paper'):
                kept.append(n)
        for i, n in enumerate(kept, start=1):
            n.order = i
        return kept

    return prune(roots)


def _depth(nodes: list) -> int:
    return 1 + max((_depth(n.children) for n in nodes), default=0) if nodes else 0


# ===================================================================== extraction
def extract_syllabus(doc: SourceDocument, text: str, *, exam_id: str,
                     cycle: str = '') -> Syllabus:
    """The syllabus this document publishes, for this exam and no other.

    The exam id is carried, never inferred. A syllabus page that serves several exams, or a
    previous cycle's syllabus, must not contribute to whichever exam happens to be open --
    the caller is the only thing that knows which exam it asked about, and
    `may_supply_syllabus` is what decides whether this document may answer for it.
    """
    syllabus = Syllabus()
    if not text or not exam_id:
        return syllabus

    cur = _Cursor(text)
    regions = _syllabus_regions(cur)
    if not regions:
        return syllabus

    for number, (start, end, heading) in enumerate(regions, start=1):
        prefix = f'syl-{_slug(heading)[:26]}'
        scope = _scope_of(heading, Scope())
        clause_nodes = _read_clauses(cur, doc, start + 1, end, prefix=prefix,
                                     root_scope=scope)
        bullet_nodes = _read_headings_and_bullets(cur, doc, start + 1, end, prefix=prefix,
                                                  root_scope=scope)
        # Whichever reading recovered more of the document's own structure. They are not
        # combined: a document numbers its clauses or it bullets them, and mixing two
        # readings of the same lines would double every entry.
        children = (clause_nodes
                    if _entry_count(clause_nodes) >= _entry_count(bullet_nodes)
                    else bullet_nodes)
        # The outline reading is preferred only where it holds the document's hierarchy the
        # others flattened, at the same coverage: deeper, and at least 90% of the entries.
        # One authority's syllabus -- papers, sections, numbered lists restarting under each
        # -- came out as 124 siblings, and its tree map and study order with it.
        outline = _read_outline(cur, doc, start + 1, end, prefix=prefix, root_scope=scope)
        if (outline and _depth(outline) > _depth(children)
                and _entry_count(outline) >= 0.9 * _entry_count(children)):
            children = outline
        if not children:
            continue

        root = SyllabusNode(
            id=f'{prefix}-root', title=_clean_heading(heading), level_label='Syllabus',
            order=number, children=children, scope=scope)
        evidence = _evidence(heading, doc, text,
                             reading=f'the heading of a published syllabus: {heading[:60]}')
        if evidence:
            root.evidence = [evidence]
            root.status = Status.VERIFIED
        else:
            root.status = Status.NEEDS_REVIEW
        syllabus.roots.append(root)

    _make_ids_unique(syllabus.roots)
    if syllabus.roots:
        note = ('read from the authority’s own document; hierarchy is the document’s '
                'own numbering or headings')
        syllabus.source_note = Fact.verified(note, syllabus.roots[0].evidence[0]) \
            if syllabus.roots[0].evidence else Fact.needs_review(note, 'no verbatim heading')
    return syllabus


def _make_ids_unique(roots: list) -> None:
    """Give every node an id no other node in the syllabus carries.

    A clause id is built from the clause's own number, and a document that numbers each
    paper's syllabus from "1." again produces the same number under every paper. Two nodes
    sharing an id are one node to anything keyed on it, so the later ones could be dropped
    on display. The first node keeps its id, so a syllabus whose ids were already unique is
    unchanged; a repeat is qualified by its parent's id, the position the document gave it.
    """
    seen: set = set()

    def visit(node, parent_id: str) -> None:
        if node.id in seen:
            base = f'{parent_id}-{node.id.rsplit("-", 1)[-1]}' if parent_id else node.id
            candidate, n = base, 2
            while candidate in seen:
                candidate, n = f'{base}-{n}', n + 1
            node.id = candidate
        seen.add(node.id)
        for child in node.children:
            visit(child, node.id)

    for root in roots:
        visit(root, '')


def _entry_count(nodes: list) -> int:
    return sum(1 for node in nodes for _ in node.walk())


def _clean_heading(line: str) -> str:
    return re.sub(r'^\s*(?:\d+(?:\.\d+)*\.?|\([a-z]\)|[A-Z]\.)\s*', '', line).strip(' :.')


# ================================================== may this document supply a syllabus?
def may_supply_syllabus(text: str, target) -> tuple[bool, str]:
    """Whether this document's syllabus belongs to this exam and this cycle.

    The same gate the pattern reader uses, and for the same reason: a syllabus is the part
    of a notice most likely to be republished, reprinted on a shared page, or carried over
    from a previous cycle. MISMATCH contributes nothing -- which includes a document that
    names this examination for another year, since identity checks the cycle too.
    """
    return may_supply_pattern(text, target)


# ========================================================================== report
def describe(syllabus: Syllabus) -> dict:
    """What was read, counted by what it is."""
    nodes = list(syllabus.walk())
    states: dict = {}
    for node in nodes:
        states[node.status.value] = states.get(node.status.value, 0) + 1
    return {
        'roots': len(syllabus.roots),
        'nodes': len(nodes),
        'leaves': sum(1 for n in nodes if not n.children),
        'maxDepth': syllabus.max_depth(),
        'levelLabels': syllabus.level_labels(),
        'withEvidence': sum(1 for n in nodes if n.evidence),
        'states': states,
        'scoped': sum(1 for n in nodes if n.scope.refs),
    }
