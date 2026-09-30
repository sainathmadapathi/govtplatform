"""Designation identity: the second way a document can name an exam, beside the alias model.

The alias model (identity.py) identifies an exam by its distinctive words. Some recruitments
have none: "Officers in Grade 'B' (DR)" is built entirely of words every notice uses, and the
alias model -- which drops generic words, peels leading words off titles and ignores bracketed
tails -- cannot tell it from "Legal Officer in Grade 'B'" or "Officers in Grade 'B'
(Information Technology)". Their identity is an *ordered* designation, a qualifier, and a
cycle.

This mode is additive and switched on only where the alias model has nothing exam-level to go
on (`identity.designation_mode`). Every exam the alias model can identify stays on it.

    CANONICAL   read once, from the authority's own recruitment NOTIFICATION -- never from a
                result page, scorecard, admit card, handout, listing row or arbitrary page.
                A local model may help locate the designation and the components the notice
                declares, but every string it returns must be printed verbatim in that
                notice, and the decomposition of each string is done here, deterministically.
    JUDGE       per document, deterministic: the designation in its title block, read from
                recruitment wording ("Recruitment of X", "Recruitment for the Posts of X",
                "Selection to the post of X"), compared whole and in order with the canonical
                one, with its qualifier, its components and its cycle.

Verdicts:

    MATCH      same ordered core, a qualifier word shared with the notice, every qualifier and
               component word declared by the notice, the target cycle, no rival in the title
               block
    MISMATCH   a different designation, a qualifier sharing nothing with the notice, or the same
               designation for another cycle
    AMBIGUOUS  everything else: no canonical designation, the same designation saying more than
               the notice declares, two recruitments in one title block, no cycle beside it

Nothing here names an authority, an exam, a post or a cadre.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Callable, Optional

from .evidence import normalise_ws

#: How much of a document is its title block, for designation purposes. The same figure the
#: alias model uses (identity._TITLE_BLOCK_CHARS), repeated here to avoid an import cycle.
TITLE_BLOCK_CHARS = 1500

_QUOTES = '‘’\'"“”`'
#: The wording an authority names a recruitment with. The designation follows it.
_INTRO = re.compile(
    r'\b(?:recruitment|selection)\s+(?:for|of|to)\s+(?:the\s+)?'
    r'(?:posts?\s+(?:of|for)\s+(?:the\s+)?)?', re.I)
#: Where a designation's statement ends: a colon, a sentence end, a date clause, a result word.
_STOP = re.compile(r'\s*[:;]|\.\s|\bheld\s+on\b|\bdated\b|\bresults?\b|\bexamination\b', re.I)
_YEAR = re.compile(r'\b(20\d{2})\b')
_FULL_DATE = re.compile(r'\b\d{1,2}[./-]\d{1,2}[./-](?:19|20)\d{2}\b'
                        r'|\b[A-Z][a-z]{2,8}\.? \d{1,2}, 20\d\d\b')
#: A designation longer than this is a sentence, not a name.
_MAX_CORE = 10


def tokens(text: str) -> list[str]:
    """Words, lower-cased, with only the transformations shown safe: quote style dropped,
    punctuation as a separator, and a plural 's' removed from words of four letters or more
    ("Officers" / "Officer", "Cadres" / "Cadre"). No synonyms."""
    s = (text or '').lower()
    for q in _QUOTES:
        s = s.replace(q, ' ')
    out = []
    for w in re.split(r'[^a-z0-9]+', s):
        if not w:
            continue
        if len(w) > 3 and w.endswith('s') and not w.endswith('ss'):
            w = w[:-1]
        out.append(w)
    return out


def _context_words() -> frozenset[str]:
    """Words that label a stage, a cycle or a paper beside a designation, never a different
    recruitment: the alias model's own structural vocabulary, plus cycle labels, connectors
    and ordinals. Read from identity.py so the two modes share one notion of 'structural'."""
    from .identity import _STRUCTURAL
    base = set(tokens(' '.join(sorted(_STRUCTURAL))))
    base |= {'panel', 'year', 'py', 'cycle', 'batch', 'session', 'held', 'on', 'of', 'the',
             'and', 'for', 'in', 'to', 'i', 'ii', 'iii', 'iv', 'v', 'a', 'b', 'c', 'd'}
    return frozenset(base)


@dataclass(frozen=True)
class Designation:
    """One designation as a document prints it."""

    core: tuple[str, ...]
    qualifiers: frozenset[str]          # every bracketed word
    components: frozenset[str]          # words after the designation, before its cycle
    year: str
    text: str                           # as printed (whitespace-normalised)
    at: int = 0                         # position in the whitespace-normalised document


@dataclass(frozen=True)
class CanonicalDesignation:
    """The recruitment's own designation, read from its notification, with its declared
    vocabulary. Carried on ExamIdentity; every judgement in designation mode is against it."""

    core: tuple[str, ...]
    qualifiers: frozenset[str]
    components: frozenset[str]
    year: str
    text: str
    source_url: str
    #: 'deterministic' | 'deterministic+qwen' | 'qwen-located'
    basis: str
    evidence: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()

    def as_dict(self) -> dict:
        return {'designation': self.text, 'core': list(self.core),
                'qualifiers': sorted(self.qualifiers), 'components': sorted(self.components),
                'cycle': self.year, 'sourceUrl': self.source_url, 'basis': self.basis,
                'evidence': list(self.evidence), 'notes': list(self.notes)}


# =================================================================== reading a designation
def _read_at(flat: str, start: int, authority_name: str = '') -> Optional[Designation]:
    """The designation that begins at `start` in whitespace-normalised text."""
    rest = flat[start:start + 260]
    if authority_name:
        # "... Cadres - Panel Year - 2026 in <the authority>" -- the authority is not the post.
        rest = re.split(r'\s+in\s+(?:the\s+)?' + re.escape(authority_name), rest, flags=re.I)[0]
    masked = _FULL_DATE.sub(lambda m: ' ' * len(m.group(0)), rest)
    year = _YEAR.search(masked)
    stop = _STOP.search(rest)
    ends = [p for p in (year.start() if year else None, stop.start() if stop else None)
            if p is not None]
    end = min(ends) if ends else len(rest)
    span = rest[:end]
    cut = re.search(r'\(|\s[-–—]\s', span)
    core_text = span[:cut.start()] if cut else span
    after = span[cut.start():] if cut else ''
    quals: set[str] = set()
    for q in re.findall(r'\(([^)]*)\)?', after):
        quals |= set(tokens(q))
    context = _context_words()
    components = set(tokens(re.sub(r'\([^)]*\)?', ' ', after))) - context
    core = tuple(tokens(core_text))
    if not core or len(core) > _MAX_CORE or not (set(core) - context):
        return None
    return Designation(core=core, qualifiers=frozenset(quals), components=frozenset(components),
                       year=year.group(1) if year else '',
                       text=normalise_ws(flat[start:start + end]).strip(' -–—'), at=start)


def read_designations(text: str, *, authority_name: str = '') -> list[Designation]:
    """Every designation the text names in recruitment wording, in order."""
    flat = normalise_ws(text)
    out = []
    for m in _INTRO.finditer(flat):
        d = _read_at(flat, m.end(), authority_name)
        if d is not None:
            out.append(Designation(d.core, d.qualifiers, d.components, d.year, d.text, m.start()))
    return out


def parse_designation(printed: str, *, authority_name: str = '') -> Optional[Designation]:
    """A designation string on its own (a query, or a string a model located in a notice)."""
    flat = normalise_ws(printed)
    m = _INTRO.search(flat)
    return _read_at(flat, m.end() if m else 0, authority_name)


def query_designation(query: str, official_name: str, authority_aliases: set[str],
                      authority_name: str = '') -> Optional[Designation]:
    """What the person asked for, as a designation: the authority's own tokens removed."""
    name = official_name or query
    words = [w for w in normalise_ws(name).split()
             if w.lower().strip(_QUOTES + '()') not in authority_aliases]
    return parse_designation(' '.join(words), authority_name=authority_name)


# ================================================================== the model's contribution
#: The only keys a model's designation extraction may carry.
EXTRACTION_KEYS = ('designation_core', 'qualifiers', 'cycle', 'declared_components',
                   'evidence_spans', 'confidence', 'ambiguities')


@dataclass
class ValidatedExtraction:
    """What survives deterministic validation of a model's extraction. `ok` False means the
    output is refused whole; `reasons` says why."""

    ok: bool
    designations: list[Designation] = field(default_factory=list)
    components: list[Designation] = field(default_factory=list)
    qualifier_words: frozenset[str] = frozenset()
    cycle: str = ''
    evidence: list[str] = field(default_factory=list)
    confidence: str = ''
    reasons: list[str] = field(default_factory=list)


def validate_extraction(raw, notification_text: str, *,
                        authority_name: str = '') -> ValidatedExtraction:
    """Every string the model returns must be printed in the notification and sit inside one
    of its own verbatim evidence spans; each is then decomposed here. Anything else -- a
    malformed object, an invented span, an invented component, a declared ambiguity, or
    designations that disagree -- refuses the whole output."""
    bad = lambda why: ValidatedExtraction(ok=False, reasons=[why])
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except (ValueError, TypeError):
            return bad('model output was not valid JSON')
    if not isinstance(raw, dict):
        return bad('model output was not a JSON object')
    extra = set(raw) - set(EXTRACTION_KEYS)
    if extra:
        return bad(f'model output carried fields outside the contract: {sorted(extra)}')
    for key in ('designation_core', 'qualifiers', 'declared_components', 'evidence_spans',
                'ambiguities'):
        v = raw.get(key, [])
        if not isinstance(v, list) or not all(isinstance(x, str) for x in v):
            return bad(f'{key} must be a list of strings')
    if not isinstance(raw.get('cycle', ''), str) or not isinstance(raw.get('confidence', ''), str):
        return bad('cycle and confidence must be strings')

    doc = normalise_ws(notification_text)
    spans = [normalise_ws(s) for s in raw.get('evidence_spans', []) if normalise_ws(s)]
    if not spans:
        return bad('no evidence span: nothing the model said can be checked')
    for s in spans:
        if s not in doc:
            return bad(f'evidence span not printed in the notification: {s[:80]!r}')
    if [a for a in raw.get('ambiguities', []) if normalise_ws(a)]:
        return bad('the model reported the designation as ambiguous: '
                   + '; '.join(normalise_ws(a) for a in raw['ambiguities'])[:200])

    # Every string is printed in the notification, verbatim -- that is what makes an invented
    # designation, qualifier or component impossible. Each such string is its own evidence.
    for key in ('designation_core', 'qualifiers', 'declared_components'):
        for item in raw.get(key, []):
            if normalise_ws(item) and normalise_ws(item) not in doc:
                return bad(f'{key} item not printed in the notification: '
                           f'{normalise_ws(item)[:80]!r}')
    spans = spans + [normalise_ws(x) for key in ('designation_core', 'declared_components')
                     for x in raw.get(key, []) if normalise_ws(x) and
                     not any(normalise_ws(x) in s for s in spans)]

    designations = [d for d in (parse_designation(x, authority_name=authority_name)
                                for x in raw.get('designation_core', [])) if d is not None]
    if not designations:
        return bad('no designation the notice prints could be read from the model output')
    cores = {d.core for d in designations}
    if len(cores) > 1:
        return bad('the model returned designations that disagree: '
                   + ' / '.join(' '.join(c) for c in sorted(cores)))

    # A component is this designation's own only where it is printed *with* the designation
    # (same ordered core). A printed string that does not carry it -- a table heading, a
    # reservation-category column -- is set aside: dropping it can only narrow what may match.
    # (Anything *not printed* was refused above, whole.)
    components, set_aside = [], []
    for x in raw.get('declared_components', []):
        c = parse_designation(x, authority_name=authority_name)
        if c is not None and c.core == designations[0].core:
            components.append(c)
        elif normalise_ws(x):
            set_aside.append(normalise_ws(x))

    cycle = normalise_ws(raw.get('cycle', ''))
    year = _YEAR.search(cycle)
    if cycle and (not year or not any(year.group(1) in s for s in spans)):
        return bad(f'cycle {cycle!r} is not printed in the model\'s evidence')

    # A qualifier qualifies *this* designation only where the notice prints it in the same
    # statement: a bracketed word anywhere else in the notice is not the designation's own.
    core = designations[0].core
    own_spans = [s for s in spans
                 if any(d.core == core for d in read_designations(s, authority_name=authority_name))
                 or any(normalise_ws(x) in s for x in raw.get('designation_core', [])
                        if (p := parse_designation(x, authority_name=authority_name)) is not None
                        and p.core == core)]
    qwords = set()
    for q in raw.get('qualifiers', []):
        if not normalise_ws(q):
            continue
        if not any(normalise_ws(q) in s for s in own_spans):
            return bad(f'qualifier {normalise_ws(q)[:60]!r} is not printed in the same statement '
                       f'as the designation')
        # A qualifier is its bracketed words (all of it when the model copied it unbracketed);
        # the designation's own words are never qualifiers.
        inside = re.findall(r'\(([^)]*)\)?', q)
        qwords |= set(tokens(' '.join(inside) if inside else q)) - set(core)
    spans = [s for s in spans if s in own_spans or any(
        c.core == core for c in (parse_designation(s, authority_name=authority_name),) if c)]
    return ValidatedExtraction(ok=True, designations=designations, components=components,
                               qualifier_words=frozenset(qwords),
                               cycle=year.group(1) if year else '', evidence=spans,
                               confidence=normalise_ws(raw.get('confidence', ''))[:20],
                               reasons=([f'set aside {len(set_aside)} printed item(s) that do not '
                                         f'carry the designation: {set_aside[:6]}']
                                        if set_aside else []))


#: (title_block) -> (raw model output or None, infra status value, detail)
Extractor = Callable[[str], tuple]


# ======================================================================== the canonical one
def _admits(d: Designation, want: Designation, year: str) -> bool:
    """A notification designation that could be the one asked for."""
    if d.core != want.core or d.year != year:
        return False
    return not want.qualifiers or bool(want.qualifiers & d.qualifiers)


def establish_canonical(want: Designation, year: str,
                        notifications: list[tuple[str, str]], *,
                        authority_name: str = '',
                        extractor: Optional[Extractor] = None,
                        llm_enabled: bool = False) -> tuple[Optional[CanonicalDesignation], list[str]]:
    """The recruitment's canonical designation, from its own notification(s), or None.

    `notifications` are (url, text) of documents the builder classified as the authority's
    recruitment notification -- the caller never passes a result page or a listing. With a
    model enabled, it must be reachable and its output must validate, or there is no canonical
    designation: an interpretation that cannot be checked is not used, and not bypassed.
    """
    notes: list[str] = []
    found: list[CanonicalDesignation] = []
    for url, text in notifications:
        flat = normalise_ws(text)
        block = flat[:TITLE_BLOCK_CHARS]
        det = [d for d in read_designations(block, authority_name=authority_name)
               if _admits(d, want, year)]
        qwen: Optional[ValidatedExtraction] = None
        if llm_enabled:
            if extractor is None:
                notes.append(f'{url}: a model is enabled but no extractor was supplied')
                return None, notes
            raw, infra, detail = extractor(block)
            if infra != 'OK':
                notes.append(f'{url}: model unavailable ({infra}: {detail}); no canonical '
                             f'designation without it')
                return None, notes
            qwen = validate_extraction(raw, flat, authority_name=authority_name)
            if not qwen.ok:
                notes.append(f'{url}: model extraction refused: {"; ".join(qwen.reasons)}')
                return None, notes
            notes.extend(f'{url}: {r}' for r in qwen.reasons)
            if qwen.cycle and qwen.cycle != year:
                notes.append(f'{url}: the model read cycle {qwen.cycle}, not {year}')
                continue

        if det:
            anchor = det[0]
            if qwen is not None and qwen.designations[0].core != anchor.core:
                notes.append(f'{url}: the model and the notice\'s own wording disagree on the '
                             f'designation ({" ".join(qwen.designations[0].core)} vs '
                             f'{" ".join(anchor.core)})')
                return None, notes
            basis = 'deterministic+qwen' if qwen is not None else 'deterministic'
        elif qwen is not None:
            # The notice's wording was not in the recruitment grammar; the model located a
            # designation the notice prints in its title block, which the checks confirmed.
            located = [d for d in qwen.designations if _admits(
                Designation(d.core, d.qualifiers, d.components, qwen.cycle or d.year, d.text),
                want, year) and normalise_ws(d.text) in block]
            if not located:
                continue
            anchor = Designation(located[0].core, located[0].qualifiers, located[0].components,
                                 year, located[0].text)
            basis = 'qwen-located'
        else:
            continue

        qualifiers = set(anchor.qualifiers)
        components = set(anchor.components)
        evidence = [anchor.text]
        if qwen is not None:
            # A component counts only when the notice prints it as this designation's own
            # (same ordered core) -- the model locates it, the parse decides it. Qualifier
            # strings were checked to be printed inside the model's verbatim evidence; their
            # cycle labels and numbers are not qualifiers.
            for c in qwen.components:
                qualifiers |= c.qualifiers
                components |= c.components
            qualifiers |= {w for w in qwen.qualifier_words
                           if w not in _context_words() and not w.isdigit()}
            evidence += [s for s in qwen.evidence if s not in evidence]
        found.append(CanonicalDesignation(
            core=anchor.core, qualifiers=frozenset(qualifiers),
            components=frozenset(components), year=year, text=anchor.text, source_url=url,
            basis=basis, evidence=tuple(evidence)))

    if not found:
        notes.append('no recruitment notification names this designation for this cycle')
        return None, notes
    first = found[0]
    for other in found[1:]:
        if other.core != first.core or not (other.qualifiers & first.qualifiers
                                            or not (other.qualifiers or first.qualifiers)):
            notes.append(f'two notifications name different recruitments ({first.text} / '
                         f'{other.text}); no canonical designation')
            return None, notes
    # The same recruitment's notice in two formats: one vocabulary.
    merged = CanonicalDesignation(
        core=first.core,
        qualifiers=frozenset().union(*(f.qualifiers for f in found)),
        components=frozenset().union(*(f.components for f in found)),
        year=year, text=first.text, source_url=first.source_url,
        basis=first.basis if all(f.basis == first.basis for f in found) else 'mixed:' + '+'.join(
            sorted({f.basis for f in found})),
        evidence=tuple(dict.fromkeys(e for f in found for e in f.evidence)),
        notes=tuple(notes))
    return merged, notes


# ============================================================================ the judgement
def _same(d: Designation, c: CanonicalDesignation, context: frozenset[str]) -> bool:
    vocab = c.qualifiers | c.components | context
    if d.core != c.core:
        return False
    if c.qualifiers and not (d.qualifiers & c.qualifiers):
        return False
    if not c.qualifiers and d.qualifiers:
        return False
    return d.qualifiers <= vocab and d.components <= vocab


def _related(d: Designation, c: CanonicalDesignation, context: frozenset[str]) -> bool:
    """The same designation saying more than the notice declares: not proof of another
    recruitment, and not proof of this one."""
    if d.core != c.core or _same(d, c, context):
        return False
    return not c.qualifiers or not d.qualifiers or bool(d.qualifiers & c.qualifiers)


@dataclass
class Judgement:
    verdict: str                        # 'MATCH' | 'MISMATCH' | 'AMBIGUOUS'
    evidence: str = ''
    matched: list[str] = field(default_factory=list)
    competing: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)


def judge(text: str, canonical: Optional[CanonicalDesignation], *, year: str,
          authority_name: str = '') -> Judgement:
    """The deterministic verdict for one document, against the canonical designation."""
    if canonical is None:
        return Judgement('AMBIGUOUS', reasons=[
            'the exam has no distinctive words and no canonical designation was established '
            'from its own notification, so no document can be identified as its own'])
    context = _context_words()
    found = read_designations(text, authority_name=authority_name)
    head = [d for d in found if d.at < TITLE_BLOCK_CHARS]
    own = [d for d in head if _same(d, canonical, context) and d.year == year]
    wrong_year = [d for d in head if _same(d, canonical, context) and d.year and d.year != year]
    unexplained = [d for d in head if _related(d, canonical, context)]
    rivals = [d for d in head if not _same(d, canonical, context)
              and not _related(d, canonical, context)]
    body_rivals = [d.text for d in found if d.at >= TITLE_BLOCK_CHARS
                   and not _same(d, canonical, context)][:5]
    if own and not rivals and not unexplained:
        return Judgement('MATCH', evidence=own[0].text, matched=[own[0].text],
                         competing=body_rivals,
                         reasons=['the title block names the recruitment by its canonical '
                                  f'designation for cycle {year}'
                                  + (f'; {len(body_rivals)} other designation(s) are mentioned '
                                     f'in the body' if body_rivals else '')])
    if own:
        return Judgement('AMBIGUOUS', evidence=own[0].text, matched=[own[0].text],
                         competing=[d.text for d in rivals + unexplained][:5],
                         reasons=['the title block names this recruitment and another '
                                  'designation beside it'])
    if unexplained:
        return Judgement('AMBIGUOUS', competing=[d.text for d in unexplained][:5],
                         reasons=[f'{unexplained[0].text!r} says more than the notification '
                                  'declares for this recruitment'])
    if wrong_year:
        return Judgement('MISMATCH', competing=[f'{d.text} ({d.year})' for d in wrong_year][:3],
                         reasons=[f'the title block names this designation for cycle '
                                  f'{wrong_year[0].year}, not {year}'])
    if rivals:
        return Judgement('MISMATCH', competing=[d.text for d in rivals][:5],
                         reasons=[f'the title block names a different recruitment: '
                                  f'{rivals[0].text!r}'])
    same_no_year = [d for d in head if _same(d, canonical, context) and not d.year]
    return Judgement('AMBIGUOUS', competing=body_rivals, reasons=[
        'the title block names this designation with no cycle beside it'
        if same_no_year else
        'the title block names no recruitment designation'])


def link_admission(link_text: str, want: Designation) -> Optional[bool]:
    """For discovery, before any canonical designation exists: True when a link's own text
    names the requested designation, False when it names a different one, None when it names
    none (the caller's usual rules then apply). Admission is not identity -- every admitted
    document is judged on its content afterwards."""
    found = read_designations(link_text)
    if not found:
        return None
    for d in found:
        if d.core == want.core and (not want.qualifiers or not d.qualifiers
                                    or bool(want.qualifiers & d.qualifiers)):
            return True
    return False
