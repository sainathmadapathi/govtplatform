"""Finding the steps of a procedure, whatever shape the authority gave them.

The first version of this looked for "Step 1", "Step 2". Against a real notice it found
nothing, and the reason is worth stating precisely rather than patching around: that notice
writes its procedure as

    PROCEDURE FOR FILLING ONLINE APPLICATION
    The process ... consists of two parts:
    Part-A (One-Time Registration):
    1. ...
    Part-B (Online Application Form):
    1. ...

The parts are lettered, not numbered, and the numbered items beneath them are instructions
*within* a part rather than parts themselves. Two different mistakes were available: find no
stages at all, or find eleven by promoting every numbered instruction. Both are wrong, and
the second is worse, because it produces a confident wrong answer.

So structure is read at several strengths, strongest first, and the first one that actually
fits the document wins:

    explicit marker   "Step 3 - Payment", "Part-A (One-Time Registration)"
    table row         a row whose first cell is an ordinal
    heading           a short title line followed by real prose, twice or more
    lettered list     (A) ... (B) ..., (i) ... (ii) ...
    numbered clause   9.1 ... 9.2 ...
    bullet            - ... - ...

Two guards keep this from inventing:

  * a candidate must sit inside a region that is *about* applying, and its own text must
    describe an application action. A heading that merely contains the word "registration"
    is not a stage; a heading whose body tells a candidate to register is.
  * a structure must produce at least two candidates. One marker is a coincidence.

Line breaks are preserved throughout, because a heading is a line and flattening the text
first is what made headings invisible. Evidence spans are matched with whitespace
normalised, so keeping the newlines costs nothing downstream.

Nothing here names an authority, an exam or a document. There is no list of expected stages.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .semantic import CueSet


class Structure(str, Enum):
    """How the authority laid its procedure out. Reported so a reader can judge it."""

    EXPLICIT_MARKER = 'EXPLICIT_MARKER'
    TABLE_ROW = 'TABLE_ROW'
    HEADING = 'HEADING'
    LETTERED_LIST = 'LETTERED_LIST'
    NUMBERED_CLAUSE = 'NUMBERED_CLAUSE'
    BULLET = 'BULLET'


@dataclass
class StageCandidate:
    """One step the document appears to describe, with what makes us think so."""

    title: str
    body: str
    structure: Structure
    order: int = 0
    #: Offset within the document, so two candidates can be ordered and located.
    offset: int = 0
    #: The action cues found in the body. Empty means this is not a procedural step.
    action_cues: list[str] = None

    def __post_init__(self) -> None:
        if self.action_cues is None:
            self.action_cues = []

    @property
    def confidence(self) -> float:
        """Structural strength, plus how clearly the body describes an action."""
        base = {
            Structure.EXPLICIT_MARKER: 0.9,
            Structure.TABLE_ROW: 0.8,
            Structure.HEADING: 0.7,
            Structure.LETTERED_LIST: 0.7,
            Structure.NUMBERED_CLAUSE: 0.6,
            Structure.BULLET: 0.5,
        }[self.structure]
        return round(min(1.0, base + 0.05 * min(len(self.action_cues), 2)), 3)


# ------------------------------------------------------------------ the region
#: A region that describes *how to apply*, rather than mentioning that one must.
PROCEDURE = CueSet(
    anchors=(r'how to apply', r'application proc(?:edure|ess)',
             r'procedure for (?:applying|submission|filling|filling up)',
             r'instructions? for (?:filling|submission|applying)',
             r'process of (?:filling|applying|registration)',
             r'steps? (?:to|for) apply', r'mode of (?:application|submission)',
             r'filling (?:up )?(?:the )?online application',
             r'applications? (?:are|is|must|should) (?:to )?be (?:submitted|filled|made)'),
    supporting=(r'\bonline\b', r'\bwebsite\b', r'\bportal\b', r'\bregistration\b',
                r'\bcandidates?\b', r'\bform\b', r'\bsubmit\b', r'\bupload\b'),
    against=(r'\bsyllabus\b', r'\bscheme of examination\b'))

#: What makes a passage an *action* a candidate performs, rather than a topic.
#:
#: Verbs only. The noun "application" used to be here and it appears in every paragraph of a
#: recruitment notice, which promoted a policy banner to an application stage. A passage
#: that mentions an application is not a step; one that tells somebody to submit one is.
_ACTION = (
    r'\bregister\w*\b', r'\bappl(?:y|ies|ying)\b', r'\bsubmit\w*\b',
    r'\bupload\w*\b', r'\bfill\w*\b', r'\benter\w*\b', r'\bprovide\b', r'\bselect\w*\b',
    r'\bpay(?:s|ing|ment)?\b', r'\bgenerat\w*\b', r'\bcreat\w*\b', r'\bchoose\b',
    r'\bindicat\w*\b', r'\bfurnish\w*\b', r'\bspecif\w*\b',
    r'\blog\s?in\b', r'\bclick\b', r'\bverif\w*\b', r'\battach\w*\b',
)

#: A page marker, a running header, a bare folio. These are lines in a PDF and they are
#: not content; the first multi-structure run promoted three of them to application stages.
_FURNITURE = re.compile(
    r'^\s*(?:page\s*\d+\s*(?:of\s*\d+)?|\d{1,4}|[ivxlc]{1,6}|(?:annexure|appendix|schedule|enclosure|attachment)\s*-?\s*[ivxa-z\d]*|'
    r'contd\.?|continued|table\s*\d*)\s*$', re.I)


def _is_furniture(line: str) -> bool:
    return bool(_FURNITURE.match(line.strip()))


def _has_words(text: str) -> bool:
    """A title is made of words. "Hours)]" is a fragment of one."""
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", text) if len(w) > 2]
    return len(words) >= 2 or (len(words) == 1 and len(words[0]) >= 5)


#: Page furniture and site navigation. A menu is not a procedure.
_NAVIGATION = re.compile(
    r'\b(home|sitemap|contact us|feedback|screen reader|skip to main|'
    r'accessibility|privacy policy|terms of use|copyright|last updated|'
    r'visitor count|font size|toggle navigation)\b', re.I)

#: Markup and script. A URL or a word inside one is not the authority addressing anybody.
_MARKUP = re.compile(
    r'<[a-z!/][^>]*>|\bfunction\s*\(|\bvar\s+\w+\s*=|\bdocument\.\w|\.createElement\b|'
    r'\bwindow\.\w|gtag\(|dataLayer|googletagmanager', re.I)

REGION_LENGTH = 9000


def procedure_regions(text: str) -> list[tuple[int, str]]:
    """Passages about how to apply, anchored where the document says so, best first.

    Anchored at the cue match rather than taken as sliding windows. The window version
    scored a passage about educational qualifications above the actual procedure, because a
    long enough window around anything in a recruitment notice contains the supporting
    words.
    """
    if not text:
        return []
    found: list[tuple[float, int, str]] = []
    for anchor in PROCEDURE.anchors:
        for m in re.finditer(anchor, text, re.I):
            region = text[m.start():m.start() + REGION_LENGTH]
            score, cues = PROCEDURE.score(region)
            if score <= 0:
                continue
            # A heading standing on its own line is a stronger claim to be the start of a
            # section than the same words inside a sentence.
            line_start = text.rfind('\n', 0, m.start()) + 1
            if text[line_start:m.start()].strip() == '':
                score += 1.5
            found.append((score, m.start(), region))
    found.sort(key=lambda t: (-t[0], t[1]))
    seen: list[int] = []
    out: list[tuple[int, str]] = []
    for _score, start, region in found:
        if any(abs(start - s) < REGION_LENGTH // 3 for s in seen):
            continue
        seen.append(start)
        out.append((start, region))
    return out


# ------------------------------------------------------------------ segmenters
_MARKER = re.compile(
    # The enumerator may be a number, a roman numeral or a letter. Letters were missing,
    # and "Part-A (One-Time Registration)" is exactly how a real notice labels its parts.
    # A step label *begins a line*. Allowing it mid-sentence read "(Part-III and Part-IV)"
    # and "Section 2(s) of the Act" as the two stages of an application.
    r'(?:^|\n)[ \t]*(?P<marker>(?:step|stage|part|phase|section)\s*[-–—:.]?\s*'
    # The letter alternative is case-sensitive even though the rest of the pattern is not.
    # Under re.I, [A-Z] matched the "s" of the word "steps", so the sentence "completed in
    # the following steps." was itself read as the first step.
    r'(?P<num>\d{1,2}|[ivxIVX]{1,4}|(?-i:[A-Z]))\b)\s*[-–—:.)]?\s*'
    r'(?P<title>\(?[^\n.;:]{3,80}\)?)', re.I)

_LETTERED = re.compile(r'(?:^|\n)\s*(?P<marker>\((?P<num>[A-Za-z]|[ivx]{1,4})\))\s*'
                       r'(?P<title>[^\n.;:]{3,80})')

_CLAUSE = re.compile(r'(?:^|\n)\s*(?P<marker>(?P<num>\d{1,2}\.\d{1,2}))\s+'
                     r'(?P<title>[^\n]{10,140})')

_BULLET = re.compile(r'(?:^|\n)\s*(?P<marker>[-•*•●])\s+(?P<title>[^\n]{6,100})')

# The leading cell may be empty, because a table row usually opens with its separator.
_TABLE_ROW = re.compile(r'(?:^|\n)[ \t]*(?P<cells>[^\n|]{0,60}\|[^\n]{4,300})')

#: A heading: a short line, not ending in a full stop, not a sentence of prose.
_HEADING_LINE = re.compile(r'^[ \t]*(?P<title>(?!\d)[^\n]{3,70})[ \t]*$')


#: A sentence that tells somebody to do something, rather than describing that something
#: exists. Either a person with a modal, or an imperative opening a line or a list item.
_DIRECTED = re.compile(
    r'(?:candidate|applicant)s?\b[^.\n]{0,80}?\b'
    r'(?:shall|must|should|may|will|are|is|has to|have to|required to|advised to)\b',
    re.I)

_IMPERATIVE = re.compile(
    r'(?:^|\n)[ \t]*(?:[-•*\u2022]|\(?[a-z0-9]{1,3}[.)])?[ \t]*'
    r'(?:please\s+)?(?:enter|fill|upload|select|click|register|pay|submit|provide|create|'
    r'choose|verify|attach|log\s?in|read|keep|ensure)\b', re.I)


def _directing_sentences(body: str) -> list[str]:
    """The sentences of this passage that ask somebody to act."""
    out = []
    for part in re.split(r'(?<=[.;])\s+|\n', body):
        if not part.strip():
            continue
        if _DIRECTED.search(part) or _IMPERATIVE.search('\n' + part):
            out.append(part)
    return out


def _actions_in(body: str) -> list[str]:
    """Action verbs, counted only where the passage is telling somebody to act.

    Counting every occurrence read a glossary as a procedure: "definitions apply to this
    notice" and "the register of candidates" carry the verbs without asking for anything.
    """
    if not _directing_sentences(body):
        # Nothing here asks anybody to do anything. A glossary entry carries the verbs
        # without instructing: "definitions apply to this notice", "the register of
        # candidates".
        return []
    low = body.lower()
    return [a for a in _ACTION if re.search(a, low)]


def _looks_like_prose(line: str) -> bool:
    return len(line) > 70 or line.rstrip().endswith(('.', ';'))


def _is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 70 or len(stripped) < 3:
        return False
    if stripped.endswith(('.', ';', ',')):
        return False
    if _NAVIGATION.search(stripped) or _MARKUP.search(stripped):
        return False
    if _is_furniture(stripped) or not _has_words(stripped):
        return False
    # A fragment of a wrapped sentence, not a title: unbalanced brackets, or a line that
    # picks up where the previous one left off.
    if stripped.count(')') != stripped.count('(') or stripped.count(']') != stripped.count('['):
        return False
    words = stripped.split()
    if len(words) > 10:
        return False
    letters = [c for c in stripped if c.isalpha()]
    if not letters:
        return False
    # A title is capitalised, whether in title case or in capitals.
    upper_ratio = sum(1 for c in letters if c.isupper()) / len(letters)
    starts_capital = stripped[0].isupper() or stripped[0] in '([('
    return starts_capital and (upper_ratio > 0.55 or _title_case(words))


def _title_case(words: list[str]) -> bool:
    significant = [w for w in words if len(w) > 3]
    if not significant:
        return False
    capped = sum(1 for w in significant if w[0].isupper())
    return capped / len(significant) >= 0.6


def _by_marker(region: str, pattern: re.Pattern,
               structure: Structure) -> list[StageCandidate]:
    marks = list(pattern.finditer(region))
    if len(marks) < 2:
        return []
    out: list[StageCandidate] = []
    for i, m in enumerate(marks):
        end = marks[i + 1].start() if i + 1 < len(marks) else len(region)
        title = _clean_title(m.group('title'))
        body = region[m.start():end].strip()
        if not _valid_title(title) or len(body) < 25:
            continue
        out.append(StageCandidate(title=title, body=body, structure=structure,
                                  offset=m.start(), action_cues=_actions_in(body)))
    return out


def _by_heading(region: str) -> list[StageCandidate]:
    """Headings that introduce real content, which is what makes them section titles."""
    lines = region.split('\n')
    starts: list[tuple[int, str, int]] = []      # (line index, title, char offset)
    offset = 0
    offsets: list[int] = []
    for line in lines:
        offsets.append(offset)
        offset += len(line) + 1
    for i, line in enumerate(lines):
        if i == 0:
            # The region opens at its own anchor, so line 0 is the heading that *names* the
            # procedure. It is the title of the section, not a step within it.
            continue
        if not _is_heading(line):
            continue
        # A heading starts something. In a PDF the line before it therefore ends a
        # sentence, ends a section, or is blank -- a wrapped line does none of those.
        previous = lines[i - 1].strip() if i > 0 else ''
        if previous and not previous.endswith(('.', ':', ';', '?')) \
                and not _is_furniture(previous):
            continue
        # A heading has something under it. A run of short lines is a menu, not a section.
        following = '\n'.join(lines[i + 1:i + 6])
        # Enough text under it to be a section. A menu's items are a dozen characters
        # each, while the shortest real section here is a sentence or two.
        if len(following.strip()) < 80 or not any(_looks_like_prose(l)
                                                   for l in lines[i + 1:i + 6]):
            continue
        starts.append((i, _clean_title(line), offsets[i]))
    if len(starts) < 2:
        return []
    out: list[StageCandidate] = []
    for n, (line_index, title, char_offset) in enumerate(starts):
        end_line = starts[n + 1][0] if n + 1 < len(starts) else len(lines)
        body = '\n'.join(lines[line_index:end_line]).strip()
        if len(body) < 60:
            continue
        out.append(StageCandidate(title=title, body=body, structure=Structure.HEADING,
                                  offset=char_offset, action_cues=_actions_in(body)))
    return out


def _by_table(region: str) -> list[StageCandidate]:
    """Rows of a table whose first cell is an ordinal and whose rest is an activity.

    No column name is assumed. What identifies the table is that its rows are ordered and
    that the remaining cells describe something to do.
    """
    rows = [m.group('cells') for m in _TABLE_ROW.finditer(region)]
    if len(rows) < 2:
        return []
    out: list[StageCandidate] = []
    for row in rows:
        cells = [c.strip() for c in row.split('|') if c.strip()]
        if len(cells) < 2:
            continue
        first = cells[0]
        # An ordinal: a bare number, a roman numeral, a letter, or "Step 2".
        if not re.fullmatch(r'(?:step|stage|part)?\s*[-–—:]?\s*(?:\d{1,2}|[ivxIVX]{1,4}|[A-Z])\.?',
                            first, re.I):
            continue
        title = _clean_title(cells[1])
        body = ' '.join(cells)
        if not title:
            continue
        out.append(StageCandidate(title=title, body=body, structure=Structure.TABLE_ROW,
                                  offset=region.find(row), action_cues=_actions_in(body)))
    return out if len(out) >= 2 else []


def _valid_title(title: str) -> bool:
    """A title, not a fragment of the sentence it was cut out of."""
    if not title or _is_furniture(title) or not _has_words(title):
        return False
    if title[0].islower() or title[0] in ')]},.;':
        return False
    return title.count('(') == title.count(')') and title.count('[') == title.count(']')


def _clean_title(text: str) -> str:
    out = ' '.join((text or '').split()).strip(' -–—:.;,')
    # Balanced brackets the authority wrote around its own label are part of the label;
    # an unbalanced one is a fragment of the sentence the title was cut out of.
    if out.startswith('(') and out.endswith(')'):
        out = out[1:-1].strip()
    elif out.count('(') != out.count(')'):
        out = out.rstrip(')').rstrip('(').strip()
    return out


#: Strongest first. The first structure that fits the document is the one it used.
_SEGMENTERS = (
    (Structure.EXPLICIT_MARKER, lambda r: _by_marker(r, _MARKER, Structure.EXPLICIT_MARKER)),
    (Structure.TABLE_ROW, _by_table),
    (Structure.HEADING, _by_heading),
    (Structure.LETTERED_LIST, lambda r: _by_marker(r, _LETTERED, Structure.LETTERED_LIST)),
    (Structure.NUMBERED_CLAUSE, lambda r: _by_marker(r, _CLAUSE, Structure.NUMBERED_CLAUSE)),
    (Structure.BULLET, lambda r: _by_marker(r, _BULLET, Structure.BULLET)),
)

#: How many of a structure's candidates must actually describe an action before the
#: structure is believed. A procedure whose steps mostly do nothing is not a procedure.
_ACTION_RATIO = 0.5


def _support(candidates: list[StageCandidate]) -> float:
    """How well-supported a set of candidates is, for choosing between regions.

    Structural strength dominates, then how many steps were found, then how clearly they
    describe actions. A long document mentions applying in several places and only one of
    them sets out the procedure; taking the first was how a passing mention beat the
    annexure that actually contained it.
    """
    if not candidates:
        return 0.0
    strength = candidates[0].confidence
    acting = sum(1 for c in candidates if c.action_cues) / len(candidates)
    return strength + 0.15 * min(len(candidates), 8) / 8 + 0.25 * acting


def discover_stages(text: str) -> list[StageCandidate]:
    """The steps this document describes, or none.

    None is a real answer and the preferred one: a document whose procedure is unstructured
    prose yields nothing, because splitting prose on guesswork produces stages the authority
    never wrote -- and four invented stages are worse than no stages, because they look
    like an answer.
    """
    best: list[StageCandidate] = []
    best_support = 0.0
    for _offset, region in procedure_regions(text)[:6]:
        if _MARKUP.search(region[:400]):
            continue
        for _structure, segment in _SEGMENTERS:
            candidates = segment(region)
            if len(candidates) < 2:
                continue
            acting = [c for c in candidates if c.action_cues]
            # Two, not one. A procedure has more than one step, and a lone survivor is
            # half an extraction rather than a finding about the document.
            if len(acting) < 2 or len(acting) / len(candidates) < _ACTION_RATIO:
                # The structure is there but it is not describing an application. A
                # numbered list of certificates is not a list of steps.
                continue
            support = _support(acting)
            if support > best_support:
                acting.sort(key=lambda c: c.offset)
                best, best_support = acting, support
            break          # the strongest structure this region actually used
    for order, candidate in enumerate(best, start=1):
        candidate.order = order
    return best
