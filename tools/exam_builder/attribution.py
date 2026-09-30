"""Fact attribution: identity MATCH is not attribution.

A document that belongs to the right recruitment still holds sentences, clauses and table
cells that state other things -- a row's serial number, an age-relaxation clause, a category
column, a mark shared by two papers, a certificate rule in the list item after an exemption.
The readers find values by the words around them; this module asks, of the evidence each
reading cites, whether that evidence plays the *role* the field needs and whether the value
is in the *scope* of the statement that carries it.

Five field families, one test each, all stated in the language every recruitment notice uses
and none naming an authority, exam, post or category of any one of them:

    vacancies      COUNT BINDING   the number is bound to the count noun ("12,256 vacancies",
                                   "Total: 563"), not merely printed after it with other
                                   labels between ("Vacancies GEN/UR ... D 1 Officers") or
                                   bound to another noun ("related to 22 offices")
    qualification  REQUIREMENT     the statement requires a qualification; one that relaxes an
                                   age limit, exempts, or disqualifies is not a requirement
    fee / feeExemptions
                   CLAUSE SCOPE    an exemption reaches only the groups named in the clause
                                   that grants it, or in the list that clause introduces --
                                   never the next, sibling list item
    posts          DESIGNATION     every post name is a designation: not a reservation-category
                                   label, a serial number, a footnote, or markup residue
    examPattern    PAPER BINDING   a paper's name is a name, not a fragment of prose, and its
                                   marks are not shared with another paper named beside them

A reading that fails is not published: an exemption group out of scope is set aside (each is
its own fact; the precedent is `build._vet_posts` removing document names), and any other
failure holds the whole field as NEEDS_REVIEW with the reading and the reason -- which the
publication gate already refuses to publish until a person decides.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .evidence import normalise_ws


@dataclass
class Attribution:
    """The verdict on one reading's evidence."""

    ok: bool
    role: str = ''
    reasons: list[str] = field(default_factory=list)
    #: Exemption groups found out of scope, to be set aside (the rest stand).
    out_of_scope: list[str] = field(default_factory=list)


# ================================================================================ vacancies
_COUNT_NOUN = re.compile(r'\b(?:vacanc\w+|total|posts?)\b', re.I)
#: Words that may stand between a count noun and its number without changing what the number
#: counts: "vacancies: 12", "Total No. of vacancies - 563", "vacancies (tentative) 40".
_CONNECTORS = frozenset({
    'of', 'is', 'are', 'the', 'total', 'approx', 'approximately', 'about', 'tentative',
    'tentatively', 'number', 'no', 'nos', 'to', 'be', 'filled', 'including', 'notified',
    'vacancies', 'vacancy', 'posts', 'post', 'there', 'will', 'as', 'under', 'this',
    'notification', 'advertisement', 'in', 'all', 'overall', 'grand', 'likely'})


def _number_forms(value: int) -> list[str]:
    plain = str(value)
    grouped = f'{value:,}'
    # Indian grouping: 1,23,456
    s = plain
    indian = s if len(s) <= 3 else f'{s[:-3]}'
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        indian = ','.join(parts + [tail])
    padded = [f'{value:02d}', f'{value:03d}'] if value < 100 else []     # "05 vacancies"
    return list(dict.fromkeys([grouped, indian, plain] + padded))


#: A share of the total, stated as a share: "including 06 vacancies for NCC", "of which 12 ...".
_COMPONENT_BEFORE = re.compile(
    r'\b(?:including|of\s+which|out\s+of\s+which|out\s+of\s+these|among\s+which|among\s+these)'
    r'\s*[:\-]?\s*$', re.I)
_COMPONENT_AFTER = re.compile(r'\s*(?:vacanc\w+|posts?)\s+(?:are\s+|is\s+)?reserved\b', re.I)


def _bound_count(span: str, value: int) -> bool:
    """Is some occurrence of `value` in `span` bound to a count noun?

    Bound forward: "12,256 vacancies", "40 posts". Bound backward: the nearest count noun
    before it with only connectors between ("Total: 563", "vacancies (tentative) 40") -- and
    the number does not open a noun phrase of its own: "22 offices" counts offices, and
    "... D 1 Officers" is a row's serial number opening the row's name.
    """
    flat = normalise_ws(span)
    for form in _number_forms(value):
        for m in re.finditer(r'(?<![\d,])(?<!\d\.)' + re.escape(form) + r'(?![\d,])', flat):
            after = flat[m.end():m.end() + 40]
            if _COMPONENT_BEFORE.search(flat[max(0, m.start() - 40):m.start()]) or \
                    _COMPONENT_AFTER.match(after):
                continue                                   # a share of the total, not the total
            if re.match(r'\s*(?:\([^)]{0,30}\)\s*)?(?:vacanc\w+|posts?)(?![a-z])', after, re.I):
                return True
            before = flat[max(0, m.start() - 90):m.start()]
            nouns = list(_COUNT_NOUN.finditer(before))
            if not nouns:
                continue
            between = re.sub(r'\([^)]*\)', ' ', before[nouns[-1].end():])
            if not all(w.lower() in _CONNECTORS for w in re.findall(r'[A-Za-z]+', between)):
                continue
            # Another figure between the noun and this one: this is not the noun's figure.
            if re.search(r'\d', between):
                continue
            # A figure followed by more figures is one cell of a row ("Total 24 6 14 ... 60"):
            # which column it is cannot be told from flattened text.
            if re.match(r'\s*[-–]?\s*\d', after):
                continue
            opens = re.match(r'\s+([A-Za-z]+)', after)           # a word, no punctuation first
            if opens and opens.group(1).lower() not in _CONNECTORS:
                continue
            return True
    return False


def _vacancy_value(value: Any) -> Optional[int]:
    if isinstance(value, dict):
        value = value.get('count')
    try:
        return int(str(value).replace(',', ''))
    except (TypeError, ValueError):
        return None


def check_vacancies(value: Any, excerpt: str, source_text: str) -> Attribution:
    n = _vacancy_value(value)
    if n is None:
        return Attribution(True, 'unreadable-value')
    span = normalise_ws(excerpt)
    # A figure the builder derived (a table column's sum) is cited by its own label rather than
    # a printed span; whether derived totals should publish at all is a separate question, left
    # as it is. The binding test below still applies to that label.
    if not _bound_count(span, n):
        return Attribution(False, 'unbound-number', [
            f'{n} is not stated as a vacancy count in its evidence: it is not bound to the count '
            f'noun (it is printed after other labels, or counts something else) -- '
            f'{span[:160]!r}'])
    return Attribution(True, 'vacancy-count')


# =========================================================================== qualification
_RELAXES = re.compile(
    r'\brelax\w*|\bupper\s+age\b|\bage[\s-]+limit|\bexempt\w*|\b(?:shall|will)\s+not\s+be\s+'
    r'eligible\b|\bnot\s+(?:be\s+)?eligible\b|\bdisqualif\w*|\bineligible\b|\bdebarred\b', re.I)
#: What a qualification is made of. A statement with none of these states no qualification.
_EDUCATION = re.compile(
    r'\b(?:degree|graduat\w*|diploma|bachelor\w*|master\w*|post[\s-]?graduat\w*|doctorate|ph\.?\s?d|'
    r'certificate|matricul\w*|10\+2|intermediate|higher\s+secondary|qualification\w*)\b', re.I)
#: A requirement governs an education term: "must possess a degree", "essential qualification".
#: "must have attained the age of 21" is an age requirement and does not count.
_REQUIRES = re.compile(
    r'\b(?:must|should|shall)\s+(?:hold|possess|have)\b(?![^.;]{0,40}\battain)(?=[^.;]{0,80}'
    r'\b(?:degree|graduat|diploma|bachelor|master|certificate|qualification|pass))|'
    r'\bessential\s+(?:educational\s+)?qualification|\bminimum\s+(?:educational\s+)?qualification|'
    r'\beducational\s+qualification|\bqualification\s+(?:required|prescribed)\b|'
    r'\bdoes\s+not\s+possess\b|\bpossess\w*\s+(?:a\s+|an\s+)?(?:bachelor|master|degree|graduat|diploma)',
    re.I)


def _statements(text: str) -> list[str]:
    """Sentences and list items: "x) For recruitment to ..." is a statement of its own."""
    out = []
    for sentence in re.split(r'(?<=[.;])\s+', normalise_ws(text)):
        out.extend(p for p in re.split(r'(?:^|\s)(?=\(?[a-zA-Z]{1,4}\)\s)', sentence) if p.strip())
    return [normalise_ws(s) for s in out]


def check_qualification(value: Any, excerpt: str, source_text: str) -> Attribution:
    text = value.get('text', '') if isinstance(value, dict) else str(value or '')
    # The statements the reading rests on: its own text, and the evidence sentence it cites.
    about = [s for s in _statements(f'{excerpt} {text}') if _EDUCATION.search(s)]
    if not about:
        return Attribution(False, 'no-qualification', [
            'the evidence names no degree, diploma, certificate or qualification -- '
            f'{normalise_ws(excerpt or text)[:160]!r}'])
    if not any(_REQUIRES.search(s) or not _RELAXES.search(s) for s in about):
        return Attribution(False, 'relaxation-or-exception', [
            'every statement in the evidence that names a qualification relaxes an age limit, '
            f'exempts, or disqualifies; none requires it -- {about[0][:180]!r}'])
    return Attribution(True, 'qualification-requirement')


# ====================================================================== exemption scope
from .application import _CATEGORY as _GROUP_WORDS, _sentences  # noqa: E402

_EXEMPTS = re.compile(r'\b(?:exempt\w*|remission|not\s+required\s+to\s+pay|waive\w*)\b', re.I)
#: A list item's own marker: "a)", "(b)", "iii)", "10)", "A)".
_ITEM = re.compile(r'(?:^|\s)(?:\(?[a-zA-Z]\)|\([ivxIVX]{1,4}\)|[ivxIVX]{1,4}\)|\d{1,2}\))\s')
#: A clause that introduces a list: "the following ... are exempted:", "... subject to following:".
_LEAD_IN = re.compile(r'\bfollowing\b|[:\-]\s*$', re.I)


def _clauses(sentence: str) -> list[str]:
    parts, last = [], 0
    for m in _ITEM.finditer(sentence):
        parts.append(sentence[last:m.start()])
        last = m.start()
    parts.append(sentence[last:])
    return [p.strip() for p in parts if p.strip()]


def _names_group(clause: str, group: str) -> bool:
    g = group.lower().split(':')[-1].replace('-', ' ').strip()
    low = clause.lower().replace('-', ' ')
    if re.search(r'\b' + re.escape(g) + r'\b', low):
        return True
    return g in {x.lower().replace('-', ' ') for x in _GROUP_WORDS.findall(clause)}


def exemption_in_scope(group: str, source_text: str) -> bool:
    """Does the document grant an exemption to `group` in a clause that names it?"""
    for sentence in _sentences(source_text):
        if not _EXEMPTS.search(sentence):
            continue
        clauses = _clauses(sentence)
        for i, clause in enumerate(clauses):
            if not _EXEMPTS.search(clause):
                continue
            if _names_group(clause, group):
                return True
            if _LEAD_IN.search(clause):
                # The list this clause introduces: its items, up to the next clause that is not
                # an item of it.
                for item in clauses[i + 1:]:
                    if _names_group(item, group):
                        return True
    return False


def _is_reservation_group(group: str) -> bool:
    """A reservation category (the vocabulary the readers collect sentence-wide, and so can
    carry across a clause). A free-text group -- "unemployed candidates" -- is captured as the
    subject of the exempting sentence itself and is in scope by construction."""
    g = group.split(':')[-1].strip()
    return bool(g) and bool(_GROUP_WORDS.fullmatch(g))


def _exempt_groups(field_name: str, value: Any) -> list[str]:
    out: list[str] = []
    if field_name == 'feeExemptions' and isinstance(value, list):
        out = [str(x.get('category', '')) for x in value
               if isinstance(x, dict) and x.get('isExempt') and x.get('category')]
    elif field_name == 'fee' and isinstance(value, dict):
        out = [str(r.get('scope', '')) for r in value.get('rules', [])
               if isinstance(r, dict) and r.get('isExempt') and ':' in str(r.get('scope', ''))]
        out += [str(c) for c in value.get('exemptCategories', []) or []]
    return [g for g in dict.fromkeys(out) if _is_reservation_group(g)]


def check_exemptions(field_name: str, value: Any, source_text: str) -> Attribution:
    groups = _exempt_groups(field_name, value)
    out = [g for g in groups if not exemption_in_scope(g, source_text)]
    if out:
        return Attribution(len(out) < len(groups), 'exemption-scope', [
            f'no clause granting an exemption names {", ".join(out)}; the exemption was read '
            f'from a neighbouring clause or list item'], out_of_scope=out)
    return Attribution(True, 'exemption-scope')


def without_groups(field_name: str, value: Any, groups: list[str]) -> Any:
    """The reading with out-of-scope exemption groups set aside."""
    drop = {g.lower() for g in groups}
    if field_name == 'feeExemptions':
        return [x for x in value if str(x.get('category', '')).lower() not in drop]
    v = dict(value)
    if 'rules' in v:
        v['rules'] = [r for r in v['rules'] if not (r.get('isExempt') and str(r.get('scope', '')).lower() in drop)]
        v['exemptions'] = ', '.join(str(r['scope']) for r in v['rules'] if r.get('isExempt'))
    if 'exemptCategories' in v:
        v['exemptCategories'] = [c for c in v['exemptCategories'] if str(c).lower() not in drop]
    return v


# ==================================================================================== posts
#: Reservation-category labels: the vocabulary of who a vacancy is reserved for, which every
#: recruitment table prints as column headings. A name made only of them names no post.
_CATEGORY_LABELS = frozenset({
    'gen', 'general', 'ur', 'unreserved', 'ews', 'obc', 'sc', 'st', 'pwbd', 'pwd', 'ph', 'esm',
    'bc', 'mbc', 'ebc', 'ncl', 'total', 'category', 'a', 'b', 'c', 'd', 'e', 'vh', 'hh', 'oh',
    'id', 'md', 'xsm', 'ex', 'servicemen', 'women', 'female', 'male'})


def _bad_post_name(name: str) -> str:
    n = normalise_ws(name)
    if re.search(r'&[a-z]+;|&#\d+;', n):
        return 'carries markup residue'
    words = re.findall(r'[A-Za-z]+', n)
    if not [w for w in words if len(w) >= 3]:
        return 'is not a name (a serial number, a letter, or blank)'
    if words and all(w.lower() in _CATEGORY_LABELS for w in words):
        return 'is a reservation-category label, not a post'
    if re.match(r'^(?:abbreviations?|note|notes|n\.?b\.?|\*|#|@|\$)\b', n, re.I):
        return 'is a footnote or an abbreviation key'
    # A sentence by its grammar, not its length: designations run long ("Assistant Treasury
    # Officer / Assistant Accounts Officer / ... (Treasuries and Accounts Service)"), but a
    # designation has no finite verb and no "Label: definition" shape.
    if (':' in n and len(words) > 8) or (len(words) > 6 and re.search(
            r'\b(?:is|are|was|were|shall|will|must|should|may|has|have|be)\b', n, re.I)):
        return 'is a sentence, not a designation'
    return ''


def check_posts(value: Any) -> Attribution:
    if not isinstance(value, list):
        return Attribution(True, 'posts')
    bad = []
    for p in value:
        name = p.get('postName') or p.get('name') or '' if isinstance(p, dict) else str(p)
        why = _bad_post_name(str(name))
        if why:
            bad.append(f'"{normalise_ws(str(name))[:50]}" {why}')
    if bad:
        return Attribution(False, 'not-designations', [
            f'{len(bad)} of {len(value)} post name(s) are not designations -- the table was '
            f'read with a heading row, a label column or a footnote as data: ' + '; '.join(bad[:4])])
    return Attribution(True, 'post-designations')


# ============================================================================== exam pattern
_PAPER_LABEL = re.compile(r'\b(?:paper|tier|stage|phase)[\s\-]*(?:[ivxIVX]+|\d)\b', re.I)


def check_pattern(value: Any, excerpt: str) -> Attribution:
    # Only the flat reading ({"papers": [...]}); the pattern tree has its own discipline.
    if not isinstance(value, dict) or 'papers' not in value:
        return Attribution(True, 'pattern-tree')
    bad = []
    span = normalise_ws(excerpt)
    for row in value.get('papers') or []:
        name = normalise_ws(str(row.get('name', '')))
        label = normalise_ws(str(row.get('label', '')))
        if re.match(r'^(?:and|or|for|with|there|of|in|the|to|,)\b', name, re.I) or \
                re.search(r'\bthere\s+(?:will|shall)\s+be\b', name, re.I):
            bad.append(f'{label} "{name[:50]}" is a fragment of prose, not a paper name')
            continue
        if _PAPER_LABEL.search(name):
            bad.append(f'{label} "{name[:50]}" names another paper beside it; its marks may be '
                       f'that paper\'s or shared')
            continue
        # Marks printed for "both Paper-I and Paper-III" belong to neither alone.
        if label and re.search(re.escape(label) + r'\s+(?:and|&|or)\s+' + _PAPER_LABEL.pattern,
                               span, re.I):
            bad.append(f'{label}\'s marks are printed jointly with another paper')
    if bad:
        return Attribution(False, 'unbound-paper', bad[:4])
    return Attribution(True, 'paper-scheme')


# ======================================================================= the one entry point
FIELDS = ('vacancies', 'qualification', 'fee', 'feeExemptions', 'posts', 'examPattern')


def check(field_name: str, value: Any, excerpt: str, source_text: str) -> Optional[Attribution]:
    """The attribution verdict for one reading, or None where no test applies."""
    if field_name == 'vacancies':
        return check_vacancies(value, excerpt, source_text)
    if field_name == 'qualification':
        return check_qualification(value, excerpt, source_text)
    if field_name in ('fee', 'feeExemptions'):
        return check_exemptions(field_name, value, source_text)
    if field_name == 'posts':
        return check_posts(value)
    if field_name == 'examPattern':
        return check_pattern(value, excerpt)
    return None


# ==================================================================================== dates
# A date publishes only with an event role its own evidence establishes. Parsing as a date
# is not a role; neither is a label that happens to sit beside it. Every rule below is stated
# in the language all recruitment notices share; none names an authority or an exam.

#: Which event cues (dates.EVENT_CUES kinds) a milestone of each runtime type may carry.
_TYPE_CUES = {
    'APPLICATION_OPEN': {'APPLICATION_WINDOW', 'APPLICATION_START'},
    'APPLICATION_CLOSE': {'APPLICATION_WINDOW', 'FEE_PAYMENT_END'},
    'CORRECTION_WINDOW': {'CORRECTION_WINDOW', 'APPLICATION_WINDOW'},
    'EXAM_TIER1': {'EXAM', 'SKILL_TEST'}, 'EXAM_TIER2': {'EXAM', 'SKILL_TEST'}, 'EXAM': {'EXAM', 'SKILL_TEST'},
    'ADMIT_CARD': {'ADMIT_CARD', 'CITY_INTIMATION'},
    'RESULT': {'RESULT'}, 'ANSWER_KEY': {'ANSWER_KEY', 'RESULT'},
    'INTERVIEW': {'INTERVIEW', 'DOCUMENT_VERIFICATION', 'PHYSICAL_TEST'},
    'NOTIFICATION': {'NOTIFICATION'},
}
#: One event, one date -- unless a later statement superseded the earlier.
_SINGLE_EVENT = frozenset({'APPLICATION_OPEN', 'APPLICATION_CLOSE', 'NOTIFICATION'})
#: A date the text cites rather than schedules: a document's date, an age reference, a
#: service-rule threshold. Only the last cue before the date counts, and only where no event
#: word stands between the cue and the date.
_REFERENCE_CUE = re.compile(
    r'\b(?:dated|dt|vide|o\.?\s?m|office\s+memorandum|circular|g\.?\s?o|order\s+no|as\s+on|'
    r'as\s+of|born|w\.?\s?e\.?\s?f|with\s+effect\s+from|joining|came\s+over)\b', re.I)
_EVENT_WORD = re.compile(
    r'\b(?:last|closing|opening|start\w*|end|exam\w*|test|interview|result|admit|answer|'
    r'verification|fee|payment|apply|application\w*|registration|window|schedule|held|conducted|'
    r'release\w*|download\w*|publish\w*|declar\w*|announc\w*)\b', re.I)
#: A row label that names a stage is an examination date: "Phase-II: Paper-I ... Examination".
_STAGE_LABEL = re.compile(r'\b(?:exam\w*|test|interview|viva|phase|tier|paper)\b', re.I)
_NOT_A_STAGE = re.compile(r'\bage\b|\bfee\b|\bqualif\w*|\beligib\w*', re.I)
_FOOTNOTE = re.compile(r'^\s*(?:notes?\b|n\.?\s?b\.?\b|footnote\b|[*#@$†]+\s*$)', re.I)


@dataclass
class DateVerdict:
    kept: list[dict] = field(default_factory=list)
    #: Provably not an event of this recruitment: set aside, with the reason.
    dropped: list[tuple[dict, str]] = field(default_factory=list)
    #: A date with no event role its evidence establishes: held for review.
    unresolved: list[tuple[dict, str]] = field(default_factory=list)
    #: Two dates for one single event, neither superseded: held for review.
    conflicts: list[tuple[dict, str]] = field(default_factory=list)


def _date_evidence(item: dict) -> tuple[str, str]:
    """(label, the text the date was read from)."""
    if 'rawValue' in item:                      # the table-row reader
        return normalise_ws(item.get('rawLabel', '')), normalise_ws(item.get('rawValue', ''))
    prov = item.get('provenance') or {}
    return normalise_ws(item.get('label', '')), normalise_ws(prov.get('excerptText', '') or item.get('label', ''))


def _locate(iso: str, text: str):
    from .dates import read_dates
    for d in read_dates(text):
        if d.iso == iso or (d.iso[:7] == iso[:7] and d.precision.value != 'DAY'):
            return d
    return None


def _valid_day(iso: str) -> bool:
    from datetime import date
    try:
        date.fromisoformat(iso)
        return True
    except ValueError:
        return False


def _cue_kinds(text: str) -> set[str]:
    from .dates import EVENT_CUES
    return {c.kind for c in EVENT_CUES if c.matches(text)}


def _nearest_cue(prefix: str) -> str:
    """The event cue closest before a date, in the same statement."""
    from .dates import EVENT_CUES
    low, best, kind = prefix.lower(), -1, ''
    for cue in EVENT_CUES:
        for a in cue.anchors:
            for m in re.finditer(a, low):
                if m.end() > best:
                    best, kind = m.end(), cue.kind
    return kind


def date_role(item: dict) -> str:
    """The event role the item's own evidence establishes, or ''."""
    kind = item.get('type', 'OTHER')
    if kind != 'OTHER':
        return kind
    label, text = _date_evidence(item)
    cues = _cue_kinds(label) or (_cue_kinds(text) if 'rawValue' not in item else set())
    if cues:
        return sorted(cues)[0]
    if 'rawValue' in item and _STAGE_LABEL.search(label) and not _NOT_A_STAGE.search(label):
        return 'EXAM'
    return ''


def _date_problem(item: dict, cycle: str) -> tuple[str, str]:
    """('drop' | 'unresolved' | '', reason) for one date item."""
    iso = (item.get('dateTimeStr') or '')[:10]
    label, text = _date_evidence(item)
    if not _valid_day(iso):
        return 'drop', f'{iso!r} is not a calendar date'
    if cycle and cycle.isdigit() and not (int(cycle) - 1 <= int(iso[:4]) <= int(cycle) + 2):
        return 'drop', f'{iso[:4]} lies outside the {cycle} cycle: a historical or other-cycle date'
    if _FOOTNOTE.search(label):
        return 'drop', 'the date is in a footnote, not a scheduled event'
    at = _locate(iso, text)
    if at is not None and item.get('type') != 'NOTIFICATION':
        prefix = text[max(0, at.start - 70):at.start]
        refs = list(_REFERENCE_CUE.finditer(prefix))
        if refs and not _EVENT_WORD.search(prefix[refs[-1].end():]):
            return 'drop', (f'the date is cited ("{refs[-1].group(0)} ..."), not scheduled -- a '
                            f'document date, an age reference or a rule threshold')
    if 'rawValue' in item and at is not None:
        prose = re.sub(r'\s+', ' ', text[:at.start] + ' ' + text[at.end:])
        if at.start > 40 and len(re.findall(r'[A-Za-z]+', prose)) > 25:
            return 'drop', 'the date sits inside a clause of text, not as the row\'s value'
        kind = item.get('type', 'OTHER')
        if kind in _TYPE_CUES:
            near = _nearest_cue(text[:at.start])
            if near and near not in _TYPE_CUES[kind]:
                return 'unresolved', f'the date is stated for {near}, not for this row\'s {kind}'
    if not date_role(item):
        return 'unresolved', f'no event is named for this date (label {label[:40]!r})'
    return '', ''


def check_dates(items: list[dict], source_text: str, cycle: str) -> DateVerdict:
    v = DateVerdict()
    for item in items or []:
        what, why = _date_problem(item, cycle)
        if what == 'drop':
            v.dropped.append((item, why))
        elif what == 'unresolved':
            v.unresolved.append((item, why))
        else:
            v.kept.append(item)
    # One event, one date: two live dates for a single event are a conflict nobody may settle
    # by picking one. A superseded or tentative date is not a rival.
    groups: dict[str, set] = {}
    for item in v.kept:
        if (item.get('type') in _SINGLE_EVENT and item.get('status') != 'SUPERSEDED'
                and not item.get('isTentative')):
            groups.setdefault(item['type'], set()).add(item['dateTimeStr'][:10])
    clash = {t for t, ds in groups.items() if len(ds) > 1}
    if clash:
        still = []
        for item in v.kept:
            if (item.get('type') in clash and item.get('status') != 'SUPERSEDED'
                    and not item.get('isTentative')):
                v.conflicts.append((item, f'two different live dates are stated for '
                                          f'{item["type"]}, and no statement supersedes either'))
            else:
                still.append(item)
        v.kept = still
    return v


def resolve_with_model_reply(item: dict, reply, source_text: str) -> tuple[bool, str]:
    """May a model's role classification give an unresolved date its role? Only when the
    model's verbatim evidence contains the date and an event cue of the role it names."""
    from .verification.attribution_llm import validate_date
    ok, why = validate_date(item, reply, source_text, need_role=None)
    if not ok:
        return False, why
    span = normalise_ws(reply['evidence_span'])
    kinds = _cue_kinds(span)
    stage = bool(_STAGE_LABEL.search(span) and not _NOT_A_STAGE.search(span))
    wanted = _ROLE_CUES.get(reply['role'], set())
    if not (kinds & wanted or (stage and reply['role'] == 'EXAM')):
        return False, (f'the model names {reply["role"]}, but its evidence carries no cue for '
                       f'that event ({span[:100]!r})')
    return True, f'role {reply["role"]} established by the model and its evidence\'s own cue'


#: Model roles -> the event cues (dates.EVENT_CUES kinds) that may substantiate them. The model's
#: roles are the reader's own kinds, so most map to themselves.
_ROLE_CUES = {
    'APPLICATION_START': {'APPLICATION_WINDOW'}, 'APPLICATION_CLOSE': {'APPLICATION_WINDOW'},
    'FEE_PAYMENT_END': {'FEE_PAYMENT_END'}, 'CORRECTION_WINDOW': {'CORRECTION_WINDOW'},
    'EXAM': {'EXAM'}, 'SKILL_TEST': {'SKILL_TEST', 'EXAM'}, 'PHYSICAL_TEST': {'PHYSICAL_TEST'},
    'ADMIT_CARD': {'ADMIT_CARD'}, 'CITY_INTIMATION': {'CITY_INTIMATION', 'ADMIT_CARD'},
    'RESULT': {'RESULT'}, 'ANSWER_KEY': {'ANSWER_KEY'}, 'OPTION_ENTRY': {'OPTION_ENTRY'},
    'DOCUMENT_VERIFICATION': {'DOCUMENT_VERIFICATION'}, 'INTERVIEW': {'INTERVIEW'},
    'NOTIFICATION': {'NOTIFICATION'}, 'OTHER_EVENT': {'OPTION_ENTRY', 'PHYSICAL_TEST'},
}
#: The model roles that agree with each role the evidence can establish (a runtime type or a
#: cue kind). A notice's own date may be read as cited: its dateline is "dated" by nature.
_FITS = {
    'NOTIFICATION': {'NOTIFICATION', 'REFERENCE'},
    'APPLICATION_OPEN': {'APPLICATION_START'}, 'APPLICATION_START': {'APPLICATION_START'},
    'APPLICATION_CLOSE': {'APPLICATION_CLOSE', 'FEE_PAYMENT_END'},
    'APPLICATION_WINDOW': {'APPLICATION_START', 'APPLICATION_CLOSE'},
    'FEE_PAYMENT_END': {'FEE_PAYMENT_END', 'APPLICATION_CLOSE'},
    'CORRECTION_WINDOW': {'CORRECTION_WINDOW'},
    'EXAM_TIER1': {'EXAM', 'SKILL_TEST'}, 'EXAM_TIER2': {'EXAM', 'SKILL_TEST'}, 'EXAM': {'EXAM', 'SKILL_TEST'},
    'SKILL_TEST': {'SKILL_TEST', 'EXAM'}, 'PHYSICAL_TEST': {'PHYSICAL_TEST'},
    'ADMIT_CARD': {'ADMIT_CARD', 'CITY_INTIMATION'}, 'CITY_INTIMATION': {'CITY_INTIMATION', 'ADMIT_CARD'},
    'RESULT': {'RESULT'}, 'ANSWER_KEY': {'ANSWER_KEY'}, 'OPTION_ENTRY': {'OPTION_ENTRY', 'OTHER_EVENT'},
    'DOCUMENT_VERIFICATION': {'DOCUMENT_VERIFICATION'},
    'INTERVIEW': {'INTERVIEW', 'DOCUMENT_VERIFICATION', 'PHYSICAL_TEST'},
}


def model_role_fits(item: dict, role: str) -> bool:
    """Does a model's role agree with the role the evidence already established?"""
    own = date_role(item)
    return bool(own) and role in _FITS.get(own, {own})
