"""Semantic field extraction — reading a fact however the authority happened to word it.

The extractors this replaces were pattern-shaped: each looked for one authority's sentence,
so SSC's notice yielded 6 of 19 fields while UPSC's yielded 13, even though both documents
state the same things. Adding `if authority == 'SSC'` would have rebuilt the per-authority
architecture inside the extractor.

The approach here is cue-based rather than phrase-based. A field declares the *kinds of
word* that indicate it — a currency symbol, the idea of a fee, the idea of exemption — and
any passage carrying enough independent cues becomes a candidate. Candidates are scored,
the best is normalised into a structured value, and the value is accepted only if its
evidence span is found verbatim in the document.

That is what lets one implementation read all of these as the same field:

    "Fee payable: Rs. 100/-"
    "application fee of one hundred rupees"
    "Candidates are required to pay a fee of Rs. 100/- ... Female candidates are exempted"
    "A non-refundable application fee of INR 850 shall be paid"

No specification below names an authority, and none may.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field as dc_field
from typing import Callable, Iterable

from .evidence import Evidence, Extracted, normalise_ws, verified_or_none

# --------------------------------------------------------------------------- passages


def passages(text: str, *, window: int = 320, stride: int = 160) -> list[tuple[int, str]]:
    """Overlapping windows over a document's text, as (offset, text).

    Overlapping matters: a fee sentence and its exemption clause are often split across a
    sentence boundary, and a non-overlapping window would cut the evidence in half.
    """
    flat = normalise_ws(text)
    if not flat:
        return []
    out: list[tuple[int, str]] = []
    for start in range(0, max(1, len(flat)), stride):
        chunk = flat[start:start + window]
        if len(chunk) < 40 and out:
            break
        out.append((start, chunk))
    return out


def sentences(text: str) -> list[str]:
    """Rough sentence split, good enough to trim a window down to its claim."""
    flat = normalise_ws(text)
    parts = re.split(r'(?<=[.;:])\s+(?=[A-Z(])', flat)
    return [p for p in parts if p.strip()]


# ------------------------------------------------------------------------------ cues
@dataclass
class CueSet:
    """What indicates a field, expressed as meaning rather than as one phrasing."""

    #: At least one must be present for a passage to be a candidate at all.
    anchors: tuple[str, ...]
    #: Each raises confidence. These are the words that distinguish a real statement of
    #: the field from a passing mention of it.
    supporting: tuple[str, ...] = ()
    #: Each lowers confidence sharply — the passage is about something adjacent.
    against: tuple[str, ...] = ()

    def score(self, passage: str) -> tuple[float, list[str]]:
        low = passage.lower()
        hit_anchor = [c for c in self.anchors if re.search(c, low)]
        if not hit_anchor:
            return 0.0, []
        hit_support = [c for c in self.supporting if re.search(c, low)]
        hit_against = [c for c in self.against if re.search(c, low)]
        score = 1.0 + 0.6 * len(hit_support) - 1.2 * len(hit_against)
        return max(0.0, score), hit_anchor + hit_support


@dataclass
class FieldSpec:
    """One field, described semantically, with a normaliser that returns its value."""

    name: str
    cues: CueSet
    #: passage -> structured value (or None if this passage does not actually state it)
    normalise: Callable[[str], object | None]
    #: The narrowest sentence carrying the value becomes the evidence span.
    evidence_from: Callable[[str, object], str] | None = None
    purpose: str = ''


# ------------------------------------------------------------------------ normalisers
_AMOUNT = re.compile(r'(?:rs\.?|inr|₹)\s*([\d,]+(?:\.\d{1,2})?)', re.I)
_WORD_AMOUNT = re.compile(
    r'\b(one|two|three|four|five|six|seven|eight|nine|ten|fifteen|twenty|twenty-five|'
    r'fifty|hundred|two hundred|five hundred|thousand)\s+(?:hundred\s+)?rupees\b', re.I)

#: Exemption is stated as a list of categories. These are the category words the
#: authorities use; the list is about people, not about any one exam.
_CATEGORY = re.compile(
    r'\b(female|women|sc|st|scheduled caste|scheduled tribe|pwbd|pwd|persons? with '
    r'benchmark disabilit(?:y|ies)|ex-?servicemen|esm|obc|ews|transgender)\b', re.I)


def _fee(passage: str):
    amounts = [a.replace(',', '') for a in _AMOUNT.findall(passage)]
    worded = bool(_WORD_AMOUNT.search(passage))
    if not amounts and not worded:
        return None
    exempt: list[str] = []
    m = re.search(r'(exempt\w*|remission|not required to pay|no fee)(.{0,220})', passage, re.I)
    if m:
        exempt = sorted({c.lower() for c in _CATEGORY.findall(m.group(2) or '')})
        if not exempt:
            # "Except Female/SC/ST..." — the categories can precede the exemption word.
            before = passage[max(0, m.start() - 200):m.start()]
            exempt = sorted({c.lower() for c in _CATEGORY.findall(before)})
    modes = sorted({w.lower() for w in re.findall(
        r'\b(net\s*banking|upi|debit card|credit card|visa|master(?:card)?|rupay|'
        r'challan|demand draft|cash)\b', passage, re.I)})
    return {'amounts': amounts[:3], 'amountInWords': worded,
            'exemptCategories': exempt, 'paymentModes': modes}


def _iso_date(text: str) -> str:
    """A date phrase as YYYY-MM-DD, or '' — so every field dates the same way."""
    from ..exam_authoring.extract import parse_date
    try:
        return parse_date(text) or ''
    except Exception:                                       # noqa: BLE001
        return ''


def _age(passage: str):
    """Age band, however it is phrased.

    Authorities write this at least four ways: "must have attained the age of 21 years and
    must not have attained the age of 32", "between 18 and 27 years", "not below 21 years
    and not above 30 years", and "age limit: 18-27 years".
    """
    pats = [
        r'attained the age of\s*(\d{2})\s*years.{0,120}?not have attained the age of\s*(\d{2})',
        # "than" is optional: "not below 20 years" and "not less than 20 years" are the
        # same rule, and requiring the word lost every authority that omits it.
        r'not\s+(?:be\s+)?(?:less|below)\s+(?:than\s+)?(\d{2}).{0,80}?'
        r'not\s+(?:be\s+)?(?:more|above|exceed\w*)\s+(?:than\s+)?(\d{2})',
        r'between\s*(\d{2})\s*(?:and|to|-|–)\s*(\d{2})\s*years',
        r'age\s*(?:limit|group)?\s*[:\-]?\s*(\d{2})\s*(?:to|-|–)\s*(\d{2})\s*years',
        r'minimum age\D{0,30}?(\d{2}).{0,140}?maximum age\D{0,30}?(\d{2})',
    ]
    for p in pats:
        m = re.search(p, passage, re.I | re.S)
        if not m:
            continue
        lo, hi = int(m.group(1)), int(m.group(2))
        if not (10 <= lo < hi <= 70):
            continue
        out = {'minAge': lo, 'maxAge': hi, 'asOn': '', 'bornBetween': []}
        # Find the cue, then parse the date out of the text that follows it. Capturing a
        # phrase first and parsing it afterwards kept failing on punctuation: commas are
        # part of "1st of August, 2026" and full stops are part of "01.08.2026", so any
        # character class wide enough for one swallowed the sentence and narrow enough for
        # the other lost the date entirely.
        cue = re.search(r'\bas on\b|\bon the\b|\bcrucial date\b|\breckoned\b', passage, re.I)
        if cue:
            window = passage[cue.end():cue.end() + 48]
            iso = _iso_date(window)
            if iso:
                out['asOn'] = iso
                out['asOnText'] = normalise_ws(window)[:40]
        born = re.search(r'born\s+(?:not earlier than|on or after)\s+([^,;]{4,40})'
                         r'.{0,40}?(?:not later than|on or before)\s+([^.,;]{4,40})',
                         passage, re.I)
        if born:
            out['bornBetween'] = [normalise_ws(born.group(1)), normalise_ws(born.group(2))]
        return out
    return None


def _vacancies(passage: str):
    m = re.search(r'(?:number of\s+)?(?:vacanc|post)\w*\D{0,80}?([\d,]{2,7})', passage, re.I)
    if not m:
        m = re.search(r'([\d,]{2,7})\s*(?:vacanc|post)\w*', passage, re.I)
    if not m:
        return None
    n = m.group(1).replace(',', '')
    if not n.isdigit() or not (1 <= int(n) <= 2_000_000):
        return None
    approx = bool(re.search(r'approx|about|tentativ|expected|likely', passage, re.I))
    return {'count': n, 'isApproximate': approx}


def _attempts(passage: str):
    """Both "six (6) attempts" and "there is no restriction on the number of attempts"."""
    if re.search(r'no\s+(?:restriction|limit|bar)\s+on\s+the\s+number\s+of\s+attempts|'
                 r'attempts?\s+(?:is|are)\s+unlimited', passage, re.I):
        return {'limited': False, 'count': None}
    m = re.search(r'(?:permitted|allowed|eligible for|restricted to)\D{0,40}?'
                  r'(?:(\w+)\s*\()?(\d{1,2})\)?\s*attempts', passage, re.I)
    if not m:
        m = re.search(r'(\d{1,2})\s*attempts', passage, re.I)
        if not m:
            return None
        return {'limited': True, 'count': int(m.group(1))}
    return {'limited': True, 'count': int(m.group(2))}


def _qualification(passage: str):
    m = re.search(r"((?:must|should|shall)\s+(?:hold|possess|have)\b.{0,320}|"
                  r"\b(?:bachelor'?s?|graduat\w+|master'?s?|degree|diploma|"
                  r"matriculation|10\+2|intermediate)\b.{0,300})", passage, re.I | re.S)
    if not m:
        return None
    text = normalise_ws(m.group(1))
    levels = sorted({w.lower() for w in re.findall(
        r"\b(bachelor'?s?|master'?s?|graduat\w+|post[- ]graduat\w+|degree|diploma|"
        r"matriculation|10\+2|intermediate|doctorate|ph\.?d)\b", text, re.I)})
    if not levels:
        return None
    return {'text': text[:400], 'levels': levels}


def _pattern(passage: str):
    """Papers with marks/questions/duration, in whatever order the authority lists them."""
    rows = []
    for m in re.finditer(
            r'(paper[\s\-]*(?:[IVX]+|\d)|tier[\s\-]*(?:[IVX]+|\d)|stage[\s\-]*(?:[IVX]+|\d))'
            r'([^\n]{0,120}?)'
            r'(?:(\d{2,4})\s*(?:marks|mks))', passage, re.I):
        row = {'label': normalise_ws(m.group(1)), 'name': normalise_ws(m.group(2)).strip(' -:—'),
               'marks': int(m.group(3))}
        dur = re.search(r'(\d{1,3})\s*(hours?|hrs?|minutes?|mins?)',
                        passage[m.end():m.end() + 120], re.I)
        if dur:
            row['duration'] = f'{dur.group(1)} {dur.group(2)}'
        qs = re.search(r'(\d{1,3})\s*questions?', passage[max(0, m.start() - 80):m.end() + 120], re.I)
        if qs:
            row['questions'] = int(qs.group(1))
        if row not in rows:
            rows.append(row)
    neg = re.search(r'negative marking.{0,120}?(?:(\d(?:\.\d+)?)\s*/\s*(\d)|'
                    r'(?:of|by)\s*(\d*\.?\d+)\s*mark)', passage, re.I)
    if not rows and not neg:
        return None
    out = {'papers': rows[:12]}
    if neg:
        out['negativeMarking'] = normalise_ws(neg.group(0))[:160]
    return out


# ------------------------------------------------------------------------ the registry
#: Semantic descriptions only. Nothing here names an authority or an exam.
SPECS: tuple[FieldSpec, ...] = (
    FieldSpec(
        name='fee',
        purpose='What a candidate pays, who is exempt, and by which modes.',
        cues=CueSet(
            anchors=(r'\bfees?\b', r'₹', r'\brs\.?\s*\d', r'\binr\b', r'\brupees\b'),
            supporting=(r'payable', r'exempt', r'remission', r'pay\w*', r'non-?refundable',
                        r'net\s*banking|upi|debit|credit|challan'),
            against=(r'fee\s+(?:will|shall)\s+be\s+refunded', r'court fee', r'late fee for'),
        ),
        normalise=_fee),
    FieldSpec(
        name='ageLimits',
        purpose='The age band and the date it is reckoned on.',
        cues=CueSet(
            anchors=(r'\bage\b', r'\byears\s+of\s+age\b', r'\bborn\b'),
            # "attained the age of" and "born not earlier than" are what make an age
            # statement unambiguous. Without them a correct reading scored 0.53 and was
            # sent for review it did not need.
            supporting=(r'limit', r'minimum', r'maximum', r'not\s+(?:less|more|below|above)',
                        r'as on', r'relaxation', r'attained the age',
                        r'born\s+(?:not earlier|on or after)', r'date of birth',
                        r'crucial date', r'candidate\s+(?:must|should)'),
            against=(r'age of the (?:vehicle|document)',),
        ),
        normalise=_age),
    FieldSpec(
        name='vacancies',
        purpose='How many posts, where a number is stated.',
        cues=CueSet(
            anchors=(r'vacanc\w*', r'number of posts'),
            supporting=(r'approx', r'tentativ', r'expected', r'total', r'reserved'),
            against=(r'no vacanc',),
        ),
        normalise=_vacancies),
    FieldSpec(
        name='attempts',
        purpose='Any cap on the number of attempts.',
        cues=CueSet(
            anchors=(r'attempts?\b',),
            supporting=(r'permitted', r'allowed', r'number of', r'restriction', r'relaxation'),
            against=(r'attempt to', r'attempted question'),
        ),
        normalise=_attempts),
    FieldSpec(
        name='qualification',
        purpose='The minimum educational qualification.',
        cues=CueSet(
            anchors=(r"bachelor'?s?", r'graduat\w+', r'\bdegree\b', r'\bdiploma\b',
                     r'matriculation', r'10\+2', r'intermediate'),
            supporting=(r'qualification', r'recognis\w+|recogniz\w+', r'universit\w+',
                        r'must\s+(?:hold|possess|have)', r'eligib\w+'),
            against=(r'degree of difficulty', r'degrees celsius'),
        ),
        normalise=_qualification),
    FieldSpec(
        name='examPattern',
        purpose='Papers, marks, questions, duration and negative marking.',
        cues=CueSet(
            anchors=(r'\bpaper[\s\-]*(?:[ivx]+|\d)', r'\btier[\s\-]*(?:[ivx]+|\d)',
                     r'\bstage[\s\-]*(?:[ivx]+|\d)'),
            supporting=(r'marks', r'questions', r'duration', r'hours?|minutes?',
                        r'objective|descriptive|multiple choice', r'negative marking'),
            against=(r'paper of the year',),
        ),
        normalise=_pattern),
)

SPEC_BY_NAME = {s.name: s for s in SPECS}


# ---------------------------------------------------------------------------- engine
def extract(field_name: str, document_text: str, *, source_url: str,
            document_title: str = '', page_of: Callable[[str], int] | None = None,
            min_confidence: float = 1.0) -> Extracted | None:
    """Read one field from a document, whatever its wording, or return None.

    Returning None is a real outcome and the caller must treat it as "we could not read
    this", never as "the authority did not publish it".
    """
    spec = SPEC_BY_NAME.get(field_name)
    if spec is None or not document_text:
        return None

    scored: list[tuple[float, list[str], str]] = []
    for _, chunk in passages(document_text):
        score, cues = spec.cues.score(chunk)
        if score >= min_confidence:
            scored.append((score, cues, chunk))
    scored.sort(key=lambda t: -t[0])

    for score, cues, chunk in scored[:25]:
        value = spec.normalise(chunk)
        if value is None:
            continue
        # The evidence is the narrowest sentence that still carries the value, so a
        # reviewer sees the claim rather than a paragraph around it.
        span = _narrowest_span(chunk, spec, value)
        ev = Evidence(span=span, source_url=source_url, document_title=document_title,
                      page=(page_of(span) if page_of else 1),
                      reading=f'{field_name} = {value}')
        cand = Extracted(field=field_name, value=value, evidence=ev,
                         confidence=min(1.0, score / 3.0), cues_matched=cues)
        ok = verified_or_none(cand, document_text)
        if ok is not None:
            return ok
    return None


def _narrowest_span(chunk: str, spec: FieldSpec, value: object) -> str:
    """The shortest sentence in the chunk that still yields the same value."""
    best = chunk
    for s in sentences(chunk):
        if len(s) < 25:
            continue
        try:
            if spec.normalise(s) is not None and len(s) < len(best):
                best = s
        except Exception:                                   # noqa: BLE001
            continue
    return best


def extract_all(document_text: str, *, source_url: str, document_title: str = '',
                only: Iterable[str] | None = None) -> dict[str, Extracted]:
    """Every semantic field this document can supply, with verified evidence."""
    wanted = set(only) if only else {s.name for s in SPECS}
    out: dict[str, Extracted] = {}
    for spec in SPECS:
        if spec.name not in wanted:
            continue
        got = extract(spec.name, document_text, source_url=source_url,
                      document_title=document_title)
        if got is not None:
            out[spec.name] = got
    return out
