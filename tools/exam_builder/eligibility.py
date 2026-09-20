"""Reading who may apply, out of the document that says so.

The thing this replaces is a function that returned 3 for OBC, 5 for SC and ST and 10 for
PwBD — for every exam in the country, with no source, no exam and no post. It was correct
for many notices and wrong for some, and nothing in the product could tell which. That is
the shape of error this whole builder exists to prevent, sitting in the path a candidate
actually reads.

So relaxation is extracted like any other fact: from a passage that states it, with the
authority's own category wording, its own number, and a span checked verbatim. Where a
notice publishes none, the answer is that it publishes none — not zero, and certainly not a
national default.

Four readers, all cue-based in the manner of `semantic.py`, none naming an authority:

    age            bands, date-of-birth windows, and the date age is reckoned on
    relaxation     per category, per post, in years or as an absolute ceiling
    qualification  whatever the authority requires, in its own words
    requirement    experience, nationality, domicile, physical, medical, licence, language

Two rules hold throughout. A value is recorded only if its span verifies verbatim. And an
authority's wording is never normalised onto anyone else's vocabulary — "Other Backward
Classes (Non-Creamy Layer)" stays that, rather than becoming OBC.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .schema import (AgeRelaxation, AgeRule, Eligibility, Fact, Post, QualificationRule,
                     Requirement, Scope, ScopeKind, ScopeRef, SourceDocument, SourceEvidence,
                     Status, VacancyCount)

# ===================================================================== helpers
_NUMBER_WORD = {
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6, 'seven': 7,
    'eight': 8, 'nine': 9, 'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fifteen': 15, 'twenty': 20,
}

#: A group an authority names when it states a rule about people. Longest first so the
#: fuller wording wins, and the *matched text* is kept rather than a code we mapped it to.
_CATEGORY = re.compile(
    r'\b(persons?\s+with\s+benchmark\s+disabilit(?:y|ies)|'
    r'other\s+backward\s+class(?:es)?(?:\s*\(?non[- ]creamy\s+layer\)?)?|'
    r'economically\s+weaker\s+sections?|scheduled\s+castes?|scheduled\s+tribes?|'
    r'ex-?servicemen|serving\s+defence\s+personnel|widows?|divorced\s+women|'
    r'departmental\s+candidates?|transgender|pwbd|pwd|obc|ews|esm|sc\s*/\s*st|sc|st)\b',
    re.I)

_YEARS = re.compile(r'\b(\d{1,2})\s*(?:\(\s*\w+\s*\))?\s*(?:years?|yrs?)\b', re.I)
_WORD_YEARS = re.compile(
    r'\b(' + '|'.join(_NUMBER_WORD) + r')\s*(?:\(\s*\d{1,2}\s*\))?\s*(?:years?|yrs?)\b',
    re.I)

_DATE = re.compile(
    r'\b(\d{1,2})[./-](\d{1,2})[./-](\d{4})\b|'
    r'\b(\d{1,2})\s*(?:st|nd|rd|th)?\s*(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|'
    r'may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t|tember)?|oct(?:ober)?|nov(?:ember)?|'
    r'dec(?:ember)?)\s*,?\s*(\d{4})\b', re.I)

_MONTHS = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6, 'jul': 7,
           'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}


def _iso_dates(text: str) -> list[str]:
    out = []
    for m in _DATE.finditer(text):
        try:
            if m.group(1):
                day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                day = int(m.group(4))
                month = _MONTHS[m.group(5)[:3].lower()]
                year = int(m.group(6))
            if month > 12:
                day, month = month, day
            out.append(f'{year:04d}-{month:02d}-{day:02d}')
        except (ValueError, KeyError):
            continue
    return out


def _years_in(text: str) -> list[int]:
    found = [int(n) for n in _YEARS.findall(text)]
    found += [_NUMBER_WORD[w.lower()] for w in _WORD_YEARS.findall(text)]
    return found


def statements(text: str) -> list[str]:
    """Passages that could each carry one rule. Rows count, because notices use tables."""
    flat = (text or '').replace('\r', '')
    flat = re.sub(r'(?<=[.;])\s+(?=\d{1,2}\.\d{1,2}\s)', '\n', flat)
    out = []
    for line in flat.split('\n'):
        line = line.strip()
        if not line:
            continue
        for piece in re.split(r'(?<=[.;])\s+(?=[A-Z(])', line):
            if piece.strip():
                out.append(piece.strip())
    return out


def _evidence(span: str, doc: SourceDocument, text: str, *,
              reading: str) -> SourceEvidence | None:
    ev = Evidence(span=span, source_url=doc.url, document_title=doc.title, page=1,
                  reading=reading)
    if ev.verify(text) is not EvidenceStatus.VERIFIED:
        return None
    out = SourceEvidence.from_evidence(ev, source=doc, source_id=doc.id)
    out.section = 'eligibility'
    return out


def _slug(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', (text or '').lower()).strip('-')[:40] or 'x'


# ========================================================================= age
_AGE_BAND = re.compile(
    r'\b(?:not\s+(?:be\s+)?(?:less|below|under)\s+than|minimum\s+(?:age\s+)?(?:of\s+)?|'
    r'at\s+least)\s*(\d{1,2})\s*(?:years?|yrs?)?', re.I)
_AGE_MAX = re.compile(
    r'\b(?:not\s+(?:be\s+)?(?:more|above|over|exceed(?:ing)?)\s+than|maximum\s+(?:age\s+)?'
    r'(?:of\s+)?|upper\s+age\s+limit\s*(?:is|of|:)?)\s*(\d{1,2})\s*(?:years?|yrs?)?', re.I)
# The second form is a table cell: "18-30 years", with none of the sentence wording.
_AGE_RANGE = re.compile(
    r'\b(?:between|from)\s*(\d{1,2})\s*(?:years?|yrs?)?\s*(?:and|to|-|–)\s*(\d{1,2})\s*'
    r'(?:years?|yrs?)\b|'
    r'\b(\d{1,2})\s*(?:[-–—]|to)\s*(\d{1,2})\s*(?:years?|yrs?)\b', re.I)

# The cue only; the date is read from what follows, because a tail that excluded dots
# stopped inside "02.08.1994".
_DOB_EARLIEST = re.compile(
    r'\bborn\s+(?:not\s+earlier\s+than|on\s+or\s+after)\b', re.I)
_DOB_LATEST = re.compile(
    r'\b(?:born\s+)?(?:not\s+later\s+than|on\s+or\s+before)\b', re.I)

# The cue only. The date is read from what follows it, because a date contains dots and
# a tail that excluded dots stopped inside "01.08.2026" and read "as on 01".
_CUTOFF = re.compile(
    r'\b(?:as\s+on|as\s+at|reckoned\s+(?:as\s+on|with\s+reference\s+to)|'
    r'crucial\s+date[^;]{0,30}?(?:is|:)|on\s+or\s+before|'
    r'cut[- ]?off\s+date[^;]{0,20}?(?:is|:))', re.I)

_IS_AGE = re.compile(r'\bage\b|\bborn\b|\bdate\s+of\s+birth\b|\bdob\b', re.I)
_NOT_AGE = re.compile(
    r'\bexperience\b|\bvalidity\b|\bcourse\b|\bduration\s+of\s+the\s+exam', re.I)


def extract_age_rules(doc: SourceDocument, text: str, *,
                      posts: list[Post] | None = None) -> list[AgeRule]:
    """Age bands, date-of-birth windows and the date age is reckoned on.

    A band and a window are both kept as printed. Converting one into the other needs a
    cutoff date and arithmetic the authority did not perform, and a derived birth date
    presented as the authority's would be exactly the invention this refuses.
    """
    rules: list[AgeRule] = []
    for passage in statements(text):
        if _NOT_AGE.search(passage):
            continue

        minimum = maximum = None
        band = _AGE_RANGE.search(passage)
        # A band *is* an age statement, whether or not the sentence says "age": "not less
        # than 21 years and not more than 30 years" says nothing else. Experience is
        # excluded above, which is what makes reading it this way safe.
        states_a_band = bool(band or (_AGE_BAND.search(passage) and _AGE_MAX.search(passage)))
        if not _IS_AGE.search(passage) and not states_a_band:
            continue
        if band:
            pair = ((band.group(1), band.group(2)) if band.group(1)
                    else (band.group(3), band.group(4)))
            minimum, maximum = int(pair[0]), int(pair[1])
        else:
            lo, hi = _AGE_BAND.search(passage), _AGE_MAX.search(passage)
            minimum = int(lo.group(1)) if lo else None
            maximum = int(hi.group(1)) if hi else None

        earliest = _DOB_EARLIEST.search(passage)
        latest = _DOB_LATEST.search(passage)
        cutoff = _CUTOFF.search(passage)

        if minimum is None and maximum is None and not earliest and not latest:
            continue

        ev = _evidence(passage, doc, text, reading='age rule')
        if ev is None:
            continue

        # A passage naming a post scopes the rule to it; otherwise it governs the exam.
        scope = Scope()
        for post in posts or []:
            if post.name and post.name.lower() in passage.lower():
                scope = Scope([ScopeRef(ScopeKind.POST, post.id, post.name)])
                break

        rule = AgeRule(id=f'age-{_slug(passage[:24])}', scope=scope)
        if minimum is not None:
            rule.minimum_age = Fact.verified(float(minimum), ev)
        if maximum is not None:
            rule.maximum_age = Fact.verified(float(maximum), ev)
        if earliest:
            dates = _iso_dates(passage[earliest.end():earliest.end() + 45])
            if dates:
                rule.born_not_earlier_than = Fact.verified(dates[0], ev)
        if latest:
            dates = _iso_dates(passage[latest.end():latest.end() + 45])
            if dates:
                rule.born_not_later_than = Fact.verified(dates[0], ev)
        if cutoff:
            dates = _iso_dates(passage[cutoff.end():cutoff.end() + 45])
            if dates:
                rule.cutoff_date = Fact.verified(dates[0], ev)
        # A rule with nothing in it is not a rule. This happened when a sentence about
        # birth dates matched the cue and its dates were lost to a pattern bug.
        if any(f.has_value for f in (rule.minimum_age, rule.maximum_age,
                                     rule.born_not_earlier_than, rule.born_not_later_than)):
            rules.append(rule)
    return rules


# ================================================================== relaxation
_RELAXES = re.compile(
    r'\brelaxa\w+\b|\brelaxable\b|\brelax(?:ed|es)?\b|\bage\s+concession\b|'
    r'\bupper\s+age\s+limit[^.;]{0,40}?\b(?:relax|raised|increased)\w*', re.I)

# Sixty, not forty: "for Persons with Benchmark Disabilities" is exactly forty
# characters, so the one phrasing this was written for was the one it could not match.
_ABSOLUTE_CEILING = re.compile(
    r'\bupper\s+age\s+limit\b[^.;]{0,60}?\bis\b[^.;]{0,15}?(\d{1,2})\s*(?:years?|yrs?)\b',
    re.I)

#: An increment on the limit, as against the limit itself. "Relaxable by five years"
#: cannot mean anything else, so it is tested first and vetoes the ceiling reading --
#: without which a five-year relaxation was recorded as a maximum age of five.
_INCREMENT = re.compile(
    r'\brelaxable\s+by\b|\brelaxed\s+by\b|\brelaxation\s+of\b|\brelaxation\s+up\s+to\b|'
    r'\bby\s+(?:a\s+(?:further|maximum)\s+)?(?:period\s+of\s+)?\d{1,2}\s*(?:years?|yrs?)\b|'
    r'\bage\s+concession\s+of\b|\bfurther\s+relaxa\w+\b', re.I)

_NO_RELAXATION = re.compile(
    r'\bno\s+(?:age\s+)?relaxa\w+\b|\brelaxa\w+\s+(?:is|shall)\s+not\s+be\s+(?:allowed|'
    r'admissible|available|granted)\b|\bnot\s+entitled\s+to\s+any\s+relaxa\w+', re.I)


#: A row of a relaxation table once the PDF has flattened it: an optional code, the
#: category exactly as printed, and the figure. The heading above supplies the meaning.
_RELAXATION_ROW = re.compile(
    r'(?:^|\n)\s*(?:(\d{1,2})\s+)?(?P<category>[A-Za-z][A-Za-z()/&.\- ]{1,44}?)\s+'
    r'(?P<years>\d{1,2})\s*(?:years?|yrs?)\b', re.I)

#: How wide a relaxation table can be before we stop trusting that we are still in it.
_RELAXATION_REGION = 1600


def _relaxation_regions(text: str) -> list[str]:
    """Passages that are *about* relaxation, anchored at the heading that says so."""
    out = []
    for m in _RELAXES.finditer(text):
        chunk = text[m.start():m.start() + _RELAXATION_REGION]
        if chunk.strip():
            out.append(chunk)
    return out[:6]


def extract_relaxation_rows(doc: SourceDocument, text: str) -> list[AgeRelaxation]:
    """Rows of a relaxation table, with the authority's own category wording.

    The category is whatever sits between the code and the figure. Taking it verbatim is
    what keeps "PwBD (OBC)" -- a combined category with its own figure -- from being read as
    two separate categories, which it is not.
    """
    out: list[AgeRelaxation] = []
    seen: set[str] = set()
    for region in _relaxation_regions(text):
        for m in _RELAXATION_ROW.finditer(region):
            category = normalise_ws(m.group('category')).strip(' .-')
            years = int(m.group('years'))
            if len(category) < 2 or not _CATEGORY.search(category):
                continue
            # A row is a short label plus a figure. A sentence that happens to end in
            # "N years" is not a row.
            if len(category.split()) > 6:
                continue
            key = f'{category.lower()}|{years}'
            if key in seen:
                continue
            row = normalise_ws(m.group(0))
            ev = _evidence(row, doc, text, reading=f'age relaxation: {category}')
            if ev is None:
                continue
            seen.add(key)
            out.append(AgeRelaxation(
                category_label=category,
                scope=Scope([ScopeRef(ScopeKind.CATEGORY, _slug(category), category)]),
                years=Fact.verified(float(years), ev)))
    return out


def extract_relaxations(doc: SourceDocument, text: str, *,
                        posts: list[Post] | None = None) -> list[AgeRelaxation]:
    """Per-category age relaxation, exactly as the authority states it.

    Both printed forms are kept, because authorities use both and converting between them
    needs the base limit plus arithmetic nobody published:

        "five years for Scheduled Castes"        -> years
        "the upper age limit for X is 40 years"  -> absolute_maximum

    A statement that a group gets *no* relaxation is a fact too, and is recorded as one.
    """
    # Tables first: that is how authorities actually publish this, and a row carries the
    # category and the figure together.
    out: list[AgeRelaxation] = extract_relaxation_rows(doc, text)
    seen: set[tuple[str, str]] = {(r.category_label.lower(),
                                   f'[{int(r.years.value)}]False') for r in out
                                  if r.years.has_value}

    for passage in statements(text):
        # A ceiling is a relaxation stated the other way round -- "the upper age limit for
        # X is 40 years" -- and never uses the word.
        if not (_RELAXES.search(passage) or _NO_RELAXATION.search(passage)
                or _ABSOLUTE_CEILING.search(passage)):
            continue
        categories = [normalise_ws(c) for c in _CATEGORY.findall(passage)]
        if not categories:
            continue

        ev = _evidence(passage, doc, text, reading='age relaxation')
        if ev is None:
            continue

        denied = bool(_NO_RELAXATION.search(passage))
        increment_match = _INCREMENT.search(passage)
        increment = bool(increment_match)
        # The figure attached to the increment, not the first figure in the sentence: a
        # band and a relaxation share a sentence often, and taking the first recorded a
        # four-year relaxation as twenty-seven.
        if increment_match:
            nearby = passage[increment_match.start():increment_match.end() + 30]
            years = _years_in(nearby) or _years_in(passage)
        else:
            years = _years_in(passage)
        ceiling = None if increment else _ABSOLUTE_CEILING.search(passage)

        scope_post = None
        for post in posts or []:
            if post.name and post.name.lower() in passage.lower():
                scope_post = post
                break

        # One passage may cover several groups with one number ("SC/ST — 5 years"), which is
        # the authority stating the same relaxation for each of them.
        for category in dict.fromkeys(categories):
            key = (category.lower(), str(years[:1]) + str(denied))
            if key in seen:
                continue
            seen.add(key)

            scope = Scope([ScopeRef(ScopeKind.CATEGORY, _slug(category), category)]
                          + ([ScopeRef(ScopeKind.POST, scope_post.id, scope_post.name)]
                             if scope_post else []))
            relaxation = AgeRelaxation(category_label=category, scope=scope)

            if denied:
                relaxation.years = Fact.not_published(
                    'the authority states that this group receives no age relaxation', ev)
            elif increment and years:
                relaxation.years = Fact.verified(float(years[0]), ev)
            elif ceiling:
                relaxation.absolute_maximum = Fact.verified(float(ceiling.group(1)), ev)
            elif years:
                relaxation.years = Fact.verified(float(years[0]), ev)
            else:
                # Relaxation mentioned without a number. Real, and not yet a value.
                relaxation.years = Fact.needs_review(
                    None, 'a relaxation is stated for this group but no number was printed '
                          'in the same passage', ev)

            condition = re.search(
                r'\b(subject\s+to[^.;]{0,90}|only\s+(?:for|if)[^.;]{0,90}|'
                r'provided\s+that[^.;]{0,90}|in\s+accordance\s+with[^.;]{0,90})',
                passage, re.I)
            if condition:
                relaxation.conditions = Fact.verified(
                    normalise_ws(condition.group(1)), ev)
            out.append(relaxation)
    return out


# =============================================================== qualification
_QUALIFIES = re.compile(
    r'\beducational\s+qualification\b|\bessential\s+qualification\b|'
    r'\bminimum\s+qualification\b|\bmust\s+(?:hold|possess|have)\b[^.;]{0,40}?\bdegree\b|'
    r'\bbachelor\w*\s+degree\b|\bmaster\w*\s+degree\b|\bgraduat\w+\b|'
    r'\bpassed\s+(?:the\s+)?(?:10th|12th|matriculation|intermediate|senior\s+secondary)\b|'
    r'\bdiploma\b|\bcertificate\s+course\b|\bprofessional\s+qualification\b', re.I)

_NOT_QUALIFICATION = re.compile(
    r'\bqualifying\s+(?:marks|paper|nature)\b|\bqualified\s+candidates\b|'
    r'\bqualifying\s+examination\s+result\b', re.I)

_AS_ON = re.compile(r'\b(?:as\s+on|on\s+or\s+before|by)\s+[^.;]{0,40}', re.I)


def extract_qualifications(doc: SourceDocument, text: str, *,
                           posts: list[Post] | None = None) -> list[QualificationRule]:
    """What the authority requires, in the authority's words.

    No closed vocabulary: the requirement is kept as printed, because "Bachelor's Degree in
    Engineering with 60% marks or equivalent" is not reducible to an enum member without
    losing the part a candidate needs.
    """
    out: list[QualificationRule] = []
    seen: set[str] = set()
    for passage in statements(text):
        if not _QUALIFIES.search(passage) or _NOT_QUALIFICATION.search(passage):
            continue
        if len(passage) < 25:
            continue
        ev = _evidence(passage, doc, text, reading='qualification')
        if ev is None:
            continue
        key = normalise_ws(passage)[:80].lower()
        if key in seen:
            continue
        seen.add(key)

        scope = Scope()
        for post in posts or []:
            if post.name and post.name.lower() in passage.lower():
                scope = Scope([ScopeRef(ScopeKind.POST, post.id, post.name)])
                break

        rule = QualificationRule(
            scope=scope,
            requirement=Fact.verified(normalise_ws(passage)[:400], ev),
            is_essential=True if re.search(r'\bessential\b|\bmust\b|\bshall\s+(?:hold|'
                                           r'possess|have)\b', passage, re.I) else None)
        as_on = _AS_ON.search(passage)
        if as_on:
            rule.as_on = Fact.verified(normalise_ws(as_on.group(0)), ev)
        out.append(rule)
    return out[:20]


# ================================================================ requirements
#: Conditions beyond age and qualification. The kinds are open; these are the ideas that
#: identify one, and the authority's sentence is what is stored.
_REQUIREMENT_CUES: tuple[tuple[str, re.Pattern], ...] = (
    ('NATIONALITY', re.compile(
        r'\bnationalit\w+\b|\bcitizen\w*\s+of\b|\bmust\s+be\s+(?:a\s+)?citizen\b|'
        r'\bsubject\s+of\s+nepal\b|\bperson\s+of\s+indian\s+origin\b', re.I)),
    ('DOMICILE', re.compile(
        r'\bdomicil\w+\b|\bresident\s+of\b|\bpermanent\s+resident\b|\bbona\s?fide\s+'
        r'resident\b', re.I)),
    ('EXPERIENCE', re.compile(
        r'\b(?:work(?:ing)?|professional|post[- ]qualification)\s+experience\b|'
        r'\bexperience\s+of\s+(?:not\s+less\s+than|at\s+least|minimum)\b|'
        r'\byears?\s+of\s+experience\b', re.I)),
    ('PHYSICAL', re.compile(
        r'\bphysical\s+(?:standard|efficiency|measurement|fitness)\b|\bheight\b[^.;]{0,30}'
        r'\bcm\b|\bchest\b[^.;]{0,30}\bcm\b|\bphysical\s+test\b', re.I)),
    ('MEDICAL', re.compile(
        r'\bmedical\s+(?:standard|fitness|examination|test)\b|\bvisual\s+standard\b|'
        r'\bcolou?r\s+blind\w*\b|\beye\s?sight\b', re.I)),
    ('LICENCE', re.compile(r'\bdriving\s+licen[cs]e\b|\bvalid\s+licen[cs]e\b', re.I)),
    ('LANGUAGE', re.compile(
        r'\bknowledge\s+of\s+[A-Z][a-z]+\b|\bproficiency\s+in\s+(?:the\s+)?\w+\s+language\b|'
        r'\bability\s+to\s+(?:read|write|speak)\b', re.I)),
    ('GENDER', re.compile(
        r'\bonly\s+(?:male|female|women|men)\s+candidates?\b|'
        r'\b(?:male|female)\s+candidates?\s+only\b', re.I)),
)


def extract_requirements(doc: SourceDocument, text: str, *,
                         posts: list[Post] | None = None) -> list[Requirement]:
    """Conditions the authority sets beyond age and qualification.

    Nothing is presumed to exist. An exam with no physical standard produces no physical
    requirement, rather than one marked absent -- the absence of a rule and a rule saying
    there is none are different claims, and only the second is a fact about the authority.
    """
    out: list[Requirement] = []
    seen: set[tuple[str, str]] = set()
    for passage in statements(text):
        if len(passage) < 25:
            continue
        for kind, pattern in _REQUIREMENT_CUES:
            if not pattern.search(passage):
                continue
            key = (kind, normalise_ws(passage)[:70].lower())
            if key in seen:
                continue
            ev = _evidence(passage, doc, text, reading=f'{kind.lower()} requirement')
            if ev is None:
                continue
            seen.add(key)

            scope = Scope()
            for post in posts or []:
                if post.name and post.name.lower() in passage.lower():
                    scope = Scope([ScopeRef(ScopeKind.POST, post.id, post.name)])
                    break

            out.append(Requirement(
                kind=kind, scope=scope,
                statement=Fact.verified(normalise_ws(passage)[:400], ev),
                is_essential=True if re.search(r'\bessential\b|\bmust\b|\bshall\b',
                                               passage, re.I) else None))
            break
    return out[:40]


# ==================================================================== vacancies
# Four and five figures are ordinary recruitment numbers. The old pattern capped the
# run at three digits before a word boundary, so 1200 could not match at all.
_VACANCY = re.compile(
    r'\b(?:number\s+of\s+vacanc\w+|vacanc\w+)\b[^.;\n]{0,60}?\b(\d[\d,]{0,8}\d|\d)\b|'
    r'\b(\d[\d,]{0,8}\d|\d)\s+vacanc\w+', re.I)

_TENTATIVE = re.compile(
    r'\btentativ\w+\b|\bprovisional\w*\b|\bapproximate\w*\b|\bliable\s+to\s+(?:change|'
    r'variation)\b|\bsubject\s+to\s+(?:change|variation)\b|\bmay\s+(?:vary|change)\b', re.I)

_NO_VACANCY = re.compile(
    r'\bvacanc\w+\s+(?:will|shall)\s+be\s+(?:notified|announced|intimated)\s+later\b|'
    r'\bnumber\s+of\s+vacanc\w+\s+(?:is|are)\s+not\s+(?:yet\s+)?(?:known|determined|fixed)\b',
    re.I)


def extract_vacancies(doc: SourceDocument, text: str, *,
                      posts: list[Post] | None = None) -> list[VacancyCount]:
    """Counts the authority published, with the qualifier it published them under.

    Never estimated, never summed from parts. "Tentative" is carried because a candidate
    planning around a number should know the authority reserved the right to change it.
    """
    out: list[VacancyCount] = []
    seen: set[int] = set()
    for passage in statements(text):
        if _NO_VACANCY.search(passage):
            ev = _evidence(passage, doc, text, reading='vacancies not yet announced')
            if ev is not None:
                out.append(VacancyCount(
                    count=Fact.not_published(
                        'the authority states the number of vacancies is not yet settled',
                        ev),
                    qualifier='to be announced'))
            continue
        m = _VACANCY.search(passage)
        if not m:
            continue
        raw = m.group(1) or m.group(2)
        if not raw:
            continue
        value = int(raw.replace(',', ''))
        if value in seen or value == 0:
            continue
        ev = _evidence(passage, doc, text, reading='vacancies')
        if ev is None:
            continue
        seen.add(value)

        scope = Scope()
        for post in posts or []:
            if post.name and post.name.lower() in passage.lower():
                scope = Scope([ScopeRef(ScopeKind.POST, post.id, post.name)])
                break
        category = _CATEGORY.search(passage)
        if category:
            scope.refs.append(ScopeRef(ScopeKind.CATEGORY,
                                       _slug(category.group(0)), normalise_ws(category.group(0))))

        out.append(VacancyCount(
            scope=scope,
            count=Fact.verified(value, ev),
            qualifier=normalise_ws(_TENTATIVE.search(passage).group(0)).lower()
            if _TENTATIVE.search(passage) else ''))
    return out[:30]


# ========================================================================= posts
_POST_ROW = re.compile(r'(?:^|\n)[ \t]*(?P<cells>[^\n|]{0,60}\|[^\n]{4,300})')

_POST_CUE = re.compile(
    r'\bname\s+of\s+(?:the\s+)?post\b|\bpost\s+code\b|\bname\s+of\s+(?:the\s+)?service\b|'
    r'\bpay\s+level\b|\bpay\s+scale\b|\bdepartment\b|\bministry\b|\bcadre\b', re.I)

_PAY_LEVEL = re.compile(r'\b(?:pay\s+level|level)\s*[-–—:]?\s*(\d{1,2})\b', re.I)


def extract_posts(doc: SourceDocument, text: str, *, exam_id: str) -> list[Post]:
    """Posts named in a table whose other cells describe a post.

    Deliberately narrow: a table row whose neighbours carry a pay level, a department or a
    post code is a post; a sentence that happens to contain the word "post" is not. A wrong
    post is worse than a missing one, because a candidate may apply for it.
    """
    out: list[Post] = []
    seen: set[str] = set()
    rows = [m.group('cells') for m in _POST_ROW.finditer(text)]
    if len(rows) < 2:
        return []

    for row in rows:
        cells = [c.strip() for c in row.split('|') if c.strip()]
        if len(cells) < 2:
            continue
        if not _POST_CUE.search(row):
            continue
        # The name is the first cell that is words rather than an ordinal or a number.
        name = next((c for c in cells
                     if re.search(r'[A-Za-z]{4}', c)
                     and not re.fullmatch(r'[\divxIVX.\s-]+', c)
                     and not _POST_CUE.fullmatch(c or '')), '')
        name = normalise_ws(name)
        if not name or len(name) < 4 or name.lower() in seen:
            continue
        if _POST_CUE.search(name) and len(name.split()) <= 3:
            continue                      # the header row
        ev = _evidence(row.strip(), doc, text, reading=f'post: {name}')
        if ev is None:
            continue
        seen.add(name.lower())

        post = Post(id=f'post-{exam_id}-{_slug(name)}', name=name,
                    evidence=[ev], status=Status.VERIFIED)
        level = _PAY_LEVEL.search(row)
        if level:
            post.pay = Fact.verified(f'Level {level.group(1)}', ev)
        out.append(post)
    return out[:60]


# ========================================================================= entry
@dataclass
class EligibilityOutcome:
    posts: list[Post]
    eligibility: Eligibility
    vacancies: list[VacancyCount]
    log: list[str]


def extract_eligibility(doc: SourceDocument, text: str, *,
                        exam_id: str) -> EligibilityOutcome:
    """Everything this document says about who may apply, and for what."""
    posts = extract_posts(doc, text, exam_id=exam_id)
    age_rules = extract_age_rules(doc, text, posts=posts)
    relaxations = extract_relaxations(doc, text, posts=posts)

    # A relaxation belongs to the rule it relaxes. With no post scope it modifies whichever
    # rule governs the exam; with one it attaches to that post's rule where there is one.
    if relaxations:
        target = next((r for r in age_rules if r.is_global), None)
        if target is None and age_rules:
            target = age_rules[0]
        if target is None:
            target = AgeRule(id=f'age-{exam_id}-relaxations')
            age_rules.append(target)
        target.relaxations.extend(relaxations)

    eligibility = Eligibility(
        age_rules=age_rules,
        qualifications=extract_qualifications(doc, text, posts=posts),
        requirements=extract_requirements(doc, text, posts=posts))
    eligibility.nationality = [r.statement for r in eligibility.requirements
                               if r.kind == 'NATIONALITY']

    vacancies = extract_vacancies(doc, text, posts=posts)
    for vacancy in vacancies:
        owners = [r.ref for r in vacancy.scope.of(ScopeKind.POST)]
        for post in posts:
            if post.id in owners:
                post.vacancies.append(vacancy)

    return EligibilityOutcome(
        posts=posts, eligibility=eligibility, vacancies=vacancies,
        log=[f'{len(posts)} post(s), {len(age_rules)} age rule(s), '
             f'{len(relaxations)} relaxation(s), '
             f'{len(eligibility.qualifications)} qualification(s), '
             f'{len(eligibility.requirements)} other requirement(s), '
             f'{len(vacancies)} vacancy statement(s)'])
