"""Content-level exam identity: does this document's *text* belong to the target exam?

Discovery already gates links — it decides whether a URL looks like it belongs to this exam.
That is not the same question. A link can pass and the document behind it still be about a
different exam the same authority runs, and the isolation proof would happily report "I
modified only SSC" while SSC's record filled with CHSL's rules.

    CONTENT ISOLATION   does this document belong to this exam?      <- this module
    DATA ISOLATION      did this build modify only this exam?        <- publish.py

The method is universal and uses no authority's name. Indian recruitment documents identify
themselves the same way regardless of who publishes them: a capitalised title phrase ending
in "Examination" / "Recruitment" / "Exam", usually carrying a year. So the document is asked
to say which exams it is about, and those self-declarations are compared with the target.

Three verdicts, and the middle one is not a soft MATCH:

    MATCH      the document declares the target exam and no rival dominates it
    MISMATCH   it declares an exam that is not the target — never contributes any fact
    AMBIGUOUS  it declares several exams, or none clearly — may inform discovery, but
               never supplies a required field until a person resolves it

A document on the right domain is not evidence. A search-result title is not evidence. Only
the document's own words are, and the span carrying them is verified verbatim like any other.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from enum import Enum

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .resolve import distinctive_words, exam_aliases


class IdentityVerdict(str, Enum):
    MATCH = 'MATCH'
    MISMATCH = 'MISMATCH'
    AMBIGUOUS = 'AMBIGUOUS'


@dataclass(frozen=True)
class ExamIdentity:
    """Who we are looking for. Built from the resolver, never hand-written."""

    exam_id: str
    query: str
    official_name: str = ''
    year: str = ''
    authority_name: str = ''
    stage: str = ''
    paper: str = ''

    @property
    def aliases(self) -> list[str]:
        return exam_aliases(self.query, self.official_name)


@dataclass
class ExamReference:
    """One exam the document names, as the document names it."""

    text: str
    year: str = ''
    #: Alias tokens this reference carries.
    tokens: list[str] = dc_field(default_factory=list)
    #: Which title phrase this came from. Suffixes of one phrase share a group, so the
    #: variants this module generates are never mistaken for rival exams.
    group: int = 0


@dataclass
class IdentityCheck:
    verdict: IdentityVerdict
    evidence: Evidence | None = None
    matched: list[str] = dc_field(default_factory=list)
    competing: list[str] = dc_field(default_factory=list)
    reasons: list[str] = dc_field(default_factory=list)

    @property
    def may_supply_facts(self) -> bool:
        """Only a MATCH may contribute factual data. AMBIGUOUS is not a weak yes."""
        return self.verdict is IdentityVerdict.MATCH


#: How these documents title themselves. Capitalised run, then the noun that makes it an
#: examination or a recruitment, optionally followed by a year. Nothing authority-specific.
_TITLE_RX = re.compile(
    # The trailing form -- "Combined Graduate Level Examination, 2026" -- and the leading
    # one, "Recruitment of Assistant Administrative Officers (AAO)". An authority uses
    # whichever reads better in its own language; both name the same thing.
    r'((?:[A-Z][\w&().\'-]*\s+){1,9}'
    r'(?i:Examination|Exam|Recruitment|Test|Services\s+Examination)'
    # ... but not where the anchor is the *start* of the leading form. Without
    # this, "Mumbai-400021 Recruitment" consumed the word that
    # "Recruitment of Assistant Administrative Officers (AAO)" needed, and an
    # authority whose notice is titled that way could not name itself at all.
    r'(?!\s+(?i:of|to)\s)'  # the anchor word may be in capitals: many notices print their
    # own title that way, and a case-sensitive anchor made every one of
    # those titles invisible -- the document could not name itself at all.
    r'(?:\s*[,\-–]?\s*(?:20\d{2}))?'
    r'|(?i:Recruitment|Selection)\s+(?i:of|to)\s+(?i:the\s+)?'
    r'(?:[A-Z][\w&().\'-]*[\s/]+){1,8}[A-Z][\w&().\'-]*'
    r'(?:\s*[,\-–]?\s*(?:20\d{2}))?)')

#: A year written beside an exam name, in any of the usual shapes.
_YEAR_RX = re.compile(r'\b(20\d{2})\b')

#: Words that make a phrase a section heading rather than an exam's name.
_NOT_A_TITLE = re.compile(
    r'^(the|this|that|such|any|each|every|all|no)\b|'
    r'\b(scheme|syllabus|instructions?|guidelines?|annexure|appendix|note)\s+(?:of|for|to)\b',
    re.I)


def exam_references(text: str, *, limit: int = 400) -> list[ExamReference]:
    """Every exam the document names about itself, in its own words."""
    flat = normalise_ws(text)
    seen: dict[str, ExamReference] = {}
    group = 0
    for m in _TITLE_RX.finditer(flat):
        group += 1
        phrase = normalise_ws(m.group(1))
        if len(phrase) < 12 or _NOT_A_TITLE.search(phrase):
            continue
        year = ''
        ym = _YEAR_RX.search(phrase)
        if ym:
            year = ym.group(1)
        else:
            # A title often carries its year a few words later ("... Examination, 2026").
            tail = flat[m.end():m.end() + 24]
            ym2 = _YEAR_RX.search(tail)
            if ym2:
                year = ym2.group(1)
        # A run of capitalised words before the noun may include text that is not part of
        # the title — "Annual Calendar Combined Graduate Level Examination" is a heading
        # followed by a title. Emitting every suffix lets the real title surface without
        # this function needing to know which exam is being looked for.
        words = phrase.split()
        for start in range(0, max(1, len(words) - 1)):
            candidate = ' '.join(words[start:])
            if len(candidate) < 12:
                break
            key = candidate.lower()
            if key not in seen:
                seen[key] = ExamReference(text=candidate, year=year,
                                          tokens=distinctive_words(candidate), group=group)
            if len(seen) >= limit:
                return list(seen.values())
    return list(seen.values())


#: Words that describe a *part* of an exam rather than a different exam. "Combined Graduate
#: Level Examination (Tier-II)" is still the same exam; the stage lives on ExamIdentity.
_STRUCTURAL = frozenset({
    'tier', 'phase', 'stage', 'paper', 'papers', 'prelim', 'prelims', 'preliminary',
    'main', 'mains', 'part', 'session', 'shift', 'advt', 'notice', 'notification',
    'computer', 'based', 'written', 'descriptive', 'objective', 'interview',
    # The words an authority uses for the process itself and for the kinds of test inside
    # it. A notice is full of these, and every one of them was being counted as a rival
    # examination: "Common Recruitment", "Annexure I. Recruitment", "Personality Test",
    # "Objective Test", "Result- Main Examination". They name this recruitment's own
    # parts, so a phrase built only from them is not evidence of another exam.
    'recruitment', 'common', 'process', 'annexure', 'appendix', 'result', 'results',
    'online', 'offline', 'personality', 'test', 'tests', 'examination', 'exam',
    'skill', 'typing', 'proficiency', 'document', 'verification', 'medical',
    'physical', 'efficiency', 'final', 'merit', 'list', 'schedule', 'round',
    'screening', 'qualifying', 'language', 'optional', 'compulsory', 'general',
})


_ACRONYM_SKIP = frozenset({'of', 'and', 'the', 'for', 'to', 'in'})


def _acronyms_of(phrase: str) -> set[str]:
    """Initials of a phrase's words, as prefixes: "Combined Graduate Level" -> cg, cgl.

    This is the direction that was missing. Aliases already contain acronyms derived
    from an expanded name; without the reverse, a document that spells the exam out
    could not be recognised when the user typed the acronym.
    """
    words = [w for w in re.findall(r"[A-Za-z]+", phrase)
             if w.lower() not in _ACRONYM_SKIP]
    initials = ''.join(w[0].lower() for w in words)
    return {initials[:k] for k in range(2, min(len(initials), 6) + 1)}


def _is_generic_phrase(ref: 'ExamReference') -> bool:
    """"Computer Based Examination" names a mode, not a different exam."""
    return not (set(ref.tokens) - _STRUCTURAL)


def _identifies(ref: ExamReference, target: ExamIdentity) -> bool:
    """Does this reference name the target exam?

    Sharing a word is not naming the same exam. "Combined Graduate Level" and "Combined
    Higher Secondary Level" share "combined", and accepting one shared token let a sibling
    exam's notice pass as the target's own — the precise contamination this module exists
    to stop.

    So the test is two-sided: the reference must carry one of the target's aliases **and**
    contribute no words of its own that the target's name lacks. Words that merely name a
    stage or a paper are not "its own words" in that sense, since they describe a part of
    an exam rather than a different one.
    """
    alias_set = set(target.aliases)
    ref_tokens = set(ref.tokens)

    # Symmetric match: the reference's own initials against the target's aliases. This is
    # what lets "Combined Graduate Level Examination" answer to "CGL".
    if _acronyms_of(ref.text) & alias_set:
        return True

    overlap = alias_set & ref_tokens
    if not overlap:
        # The acronym form may sit inside a single token ("CGLE", "CGL-2026").
        joined = ' '.join(ref.tokens)
        return any(a in joined for a in alias_set if len(a) >= 4)

    foreign = ref_tokens - alias_set - _STRUCTURAL
    if not foreign:
        return True
    # An explicit acronym match outweighs surrounding description: a reference containing
    # "CGL" is about CGL whatever else it says.
    return bool({a for a in overlap if len(a) <= 5 and a not in target.official_name.lower()})


def _year_conflicts(ref: ExamReference, target: ExamIdentity) -> bool:
    return bool(target.year and ref.year and ref.year != target.year)


def verify(text: str, target: ExamIdentity, *, source_url: str = '',
           document_title: str = '') -> IdentityCheck:
    """Decide whether a document's content belongs to the target exam."""
    if not normalise_ws(text):
        return IdentityCheck(IdentityVerdict.AMBIGUOUS,
                             reasons=['the document has no readable text; identity cannot '
                                      'be established from it'])

    refs = exam_references(text)
    if not refs:
        return IdentityCheck(
            IdentityVerdict.AMBIGUOUS,
            reasons=['the document names no examination, so it cannot vouch for itself; '
                     'being on the authority’s domain is not identity evidence'])

    # Collapse by group: the suffixes of one title are one reference, not several. Counting
    # them separately made a document's own title look like a crowd of rival exams.
    groups: dict[int, list[ExamReference]] = {}
    for r in refs:
        groups.setdefault(r.group, []).append(r)

    matching, wrong_year, other = [], [], []
    for members in groups.values():
        hits = [r for r in members if _identifies(r, target)]
        if not hits:
            # A phrase made only of structural words ("Computer Based Examination") names a
            # mode of examination, not another one. Counting it as a rival pushed clean
            # documents to AMBIGUOUS and blocked their facts.
            if all(_is_generic_phrase(r) for r in members):
                continue
            # The longest form is the readable one for a report.
            other.append(max(members, key=lambda r: len(r.text)))
            continue
        clean = [r for r in hits if not _year_conflicts(r, target)]
        if clean:
            matching.append(min(clean, key=lambda r: len(r.text)))
        else:
            wrong_year.append(min(hits, key=lambda r: len(r.text)))

    reasons: list[str] = []
    ev: Evidence | None = None
    if matching:
        best = max(matching, key=lambda r: (bool(r.year), len(r.tokens)))
        ev = Evidence(span=best.text, source_url=source_url,
                      document_title=document_title,
                      reading=f'names {target.exam_id}')
        ev.verify(text)
        if ev.status is not EvidenceStatus.VERIFIED:
            # Identity evidence is held to the same standard as any other claim.
            return IdentityCheck(
                IdentityVerdict.AMBIGUOUS, evidence=ev,
                reasons=['the phrase that would establish identity could not be verified '
                         'verbatim in the document'])

    if matching and not other:
        return IdentityCheck(IdentityVerdict.MATCH, evidence=ev,
                             matched=[r.text for r in matching[:3]],
                             reasons=['the document names this exam and no other'])

    if matching and other:
        # A calendar or a combined notice listing several exams. It is real evidence of
        # *something*, but not of a fact belonging to this exam in particular.
        return IdentityCheck(
            IdentityVerdict.AMBIGUOUS, evidence=ev,
            matched=[r.text for r in matching[:3]],
            competing=[r.text for r in other[:5]],
            reasons=[f'the document names this exam and {len(other)} other examination(s); '
                     f'a fact in it cannot be attributed to this exam without a reference '
                     f'that is specific to it'])

    if wrong_year:
        return IdentityCheck(
            IdentityVerdict.MISMATCH,
            competing=[r.text for r in wrong_year[:3]],
            reasons=[f'the document names this examination for '
                     f'{", ".join(sorted({r.year for r in wrong_year}))}, not '
                     f'{target.year or "the requested year"}'])

    if not other:
        # Nothing matched and nothing rivals it either: every phrase the document names is
        # built from process vocabulary. That is a document we cannot place, which is not
        # the same as one that belongs elsewhere.
        return IdentityCheck(
            IdentityVerdict.AMBIGUOUS,
            reasons=['the document names no examination distinctively — every phrase '
                     'in it is built from process vocabulary — so its identity cannot '
                     'be established from its content'])

    return IdentityCheck(
        IdentityVerdict.MISMATCH,
        competing=[r.text for r in other[:5]],
        reasons=[f'the document names {len(other)} examination(s), none of them this one'])


def field_is_attributable(text: str, target: ExamIdentity, evidence_span: str) -> bool:
    """For an AMBIGUOUS document, may *this particular* fact still be attributed?

    A multi-exam calendar can still legitimately supply a fact when the sentence carrying
    it names the target itself. This is what keeps AMBIGUOUS from being either uselessly
    strict or quietly permissive: the document stays ambiguous, but a span that identifies
    the exam on its own terms is attributable.
    """
    window = normalise_ws(evidence_span)
    if not window:
        return False
    refs = exam_references(window)
    if not refs:
        return False
    return any(_identifies(r, target) and not _year_conflicts(r, target) for r in refs)
