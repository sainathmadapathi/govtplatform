"""Read an exam's admit-card events out of whatever its authority published.

ADMIT_CARD_AUDIT.md §5 records what four real authorities actually publish, and no two of
them publish it the same way:

  * one puts **two events in one sentence** — city details from one date, the admit card
    from another — inside a notice whose headline also carries the *exam* date;
  * one publishes a **row in a document table** on the exam's own page: a label and a date,
    with no URL, no credentials and no instructions;
  * one publishes **two schedule rows, one per stage**, at **month precision**;
  * one publishes **no date at all**, only a rule: "7 days before examination".

So there is no single admit-card record to read. There are *events*, each one bound to the
stage it admits to, each carrying the authority's own name for it, and each either dated or
ruled. Three things this module refuses to do, all of them from the audit's findings:

  * **It never merges a city intimation with an admit card.** They are different documents
    released on different days, and one authority's own headline names both; a reader that
    took the first date it found would tell a candidate the admit card was out four days
    early.
  * **It never lets a release date become an exam date.** They sit in the same sentence, and
    `exam_date` is a separate field for exactly that reason.
  * **It never presents an authority's homepage as a download link.** A URL whose path is
    empty is a portal, and portals are where a candidate logs in — which is a true and
    useful fact, and a different one from "here is your admit card".

And a failure to read a source is recorded as a `SourceOutcome`, never as a `Status`. "We
could not fetch the page" and "the authority has published nothing" are different claims,
and only the second is ever shown to a candidate.
"""
from __future__ import annotations

import re
import urllib.parse

from .dates import read_dates
from .pattern import _evidence, _slug
from .schema import (AdmitCardNotice, AdmitCardNoticeKind, DatePrecision, Fact, Scope,
                     ScopeKind, ScopeRef, SourceDocument, SourceOutcome, Status,
                     normalise_ws)

# ===================================================================== vocabulary
#: What an authority calls the document that admits a candidate to the hall. Structural
#: vocabulary shared across authorities -- which words a given one uses is read, not assumed.
#: Order matters: a city-intimation phrase is checked before the admit-card one, because
#: "City and Admit Card" names both and the longer, more specific idea must win its own span.
_KIND_CUES: tuple[tuple[AdmitCardNoticeKind, re.Pattern], ...] = (
    (AdmitCardNoticeKind.CITY_INTIMATION, re.compile(
        r'\b(?:exam(?:ination)?\s+)?(?:city|centre|center)\s*'
        r'(?:[-–]\s*)?(?:intimation|details|slip|information|allotment)\b'
        r'|\bintimation\s+of\s+(?:exam(?:ination)?\s+)?(?:city|centre|center)\b'
        r'|\bcity\s+and\s+(?:date\s+)?intimation\b', re.I)),
    (AdmitCardNoticeKind.EXAM_INTIMATION, re.compile(
        r'\bpre[\s\-]?exam(?:ination)?\s+(?:training|intimation)\b'
        r'|\bexam(?:ination)?\s+intimation\s+slip\b', re.I)),
    (AdmitCardNoticeKind.ADMIT_CARD, re.compile(
        r'\be[\s\-]*admit\s*cards?\b|\badmit\s*cards?\b|\bcall\s*letters?\b'
        r'|\badmission\s+certificates?\b|\bhall\s*tickets?\b', re.I)),
)

#: The examination's own date, which shares sentences with every release date above and must
#: never be read as one.
#:
#: A bare "exam date" is deliberately **not** a cue. It occurs in "the Admission Certificate
#: will be available 2/3 days before the respective exam date" -- a sentence whose whole
#: point is that the date is *not* stated here -- and reading it as one took the notice's
#: dateline as an examination date.
_EXAM_DATE_CUE = re.compile(
    r'\bexam(?:ination)?\s+(?:\w+\s+){0,2}?'
    r'(?:is|was|will\s+be|has\s+been)?\s*'
    r'(?:scheduled|rescheduled|held|conducted|commencing|to\s+be\s+held)\b'
    r'|\bexam(?:ination)?\s+on\b'
    r'|\bdate\s+of\s+(?:the\s+)?(?:commencement\s+of\s+)?exam(?:ination)?\b', re.I)

#: Who signed the notice. Every date after this is a dateline, an office address or a
#: reference to some other document -- never an event this notice announces. One real notice
#: ends "Under Secretary to the Govt. of India 03.09.2025", and that date was published as
#: the examination's.
_SIGNATURE = re.compile(
    r'\b(?:under\s+secretary|joint\s+secretary|deputy\s+secretary|regional\s+director'
    r'|dy\.?\s*director|director\s*\(|chairman|controller\s+of\s+exam\w*'
    r'|general\s+manager|sd/-|signed)\b', re.I)

#: "from 05.10.2025 onwards", "w.e.f. 09.10.2025", "available from", "download ... on".
#: A release cue makes a nearby date a *release* date; without one the date is only a date.
_RELEASE_CUE = re.compile(
    r'\bw\.?\s*e\.?\s*f\.?\b|\bwith\s+effect\s+from\b|\bfrom\b|\bonwards?\b'
    r'|\bavailable\b|\breleased?\b|\buploaded?\b|\bdownload(?:ed|able)?\b|\bissued?\b'
    r'|\bactivated?\b|\blive\b', re.I)

#: An authority that publishes no date but a rule. Kept as printed: "7 days before
#: examination" resolved into a date would be GovOS's arithmetic on an exam date that may
#: itself move, presented as the authority's statement.
#:
#: The leading `(?<![\d/])` and the optional `2/3` part are not tidiness. Two real notices
#: say "2/3 days before the respective exam date" and "02/03 days prior to date of
#: examination"; a pattern starting at a bare digit quotes the Commission as saying "3 days"
#: and "03 days", which is a different rule from the one it published.
_RELATIVE_RULE = re.compile(
    r'(?<![\d/])(?:\d{1,3}\s*[/\u2013-]\s*)?\d{1,3}\s*(?:\(\s*\w+\s*\)\s*)?'
    r'(?:days?|weeks?)\s+'
    r'(?:before|prior\s+to|in\s+advance\s+of)\b[^.;]{0,60}', re.I)

#: What a candidate signs in with. Each is an ordinary phrase; none is invented for them.
_CREDENTIAL_CUES: tuple[tuple[str, re.Pattern], ...] = (
    ('Registration number', re.compile(r'\bregistration\s*(?:no\.?|number|id)\b', re.I)),
    ('Roll number', re.compile(r'\broll\s*(?:no\.?|number)\b', re.I)),
    ('User ID', re.compile(r'\buser\s*(?:id|name)\b', re.I)),
    ('Password', re.compile(r'\bpassword\b', re.I)),
    ('Date of birth', re.compile(r'\bdate\s+of\s+birth\b|\bdob\b', re.I)),
    ('Login on the authority’s own portal',
     re.compile(r'\blog(?:ging)?\s*[\s\-]?in\b|\blogin\s+module\b', re.I)),
)

#: What a candidate must carry. Read only where the source states it for this exam; exam-day
#: requirements borrowed from another authority are how someone is turned away at the gate.
_DOCUMENT_CUES: tuple[tuple[str, re.Pattern], ...] = (
    ('Printed call letter / admit card', re.compile(
        r'\b(?:valid|printed)\s+(?:call\s*letter|admit\s*card)\b'
        r'|\bcall\s*letter\s+with\s+(?:a\s+)?photograph\s+affixed\b', re.I)),
    ('Photo identity proof in original', re.compile(
        r'\bphoto\s*(?:\-?\s*)?id(?:entity)?\s+proof\b[^.;]{0,80}\boriginal\b'
        r'|\boriginal\b[^.;]{0,40}\bphoto\s*(?:\-?\s*)?id(?:entity)?\s+proof\b', re.I)),
    ('Photocopy of the photo identity proof', re.compile(
        r'\bphoto\s*copy\b[^.;]{0,60}\bid(?:entity)?\b'
        r'|\bphotocopy\s+of\b[^.;]{0,60}\bid(?:entity)?\b', re.I)),
    ('Photograph identical to the one uploaded', re.compile(
        r'\bphotograph\b[^.;]{0,60}\b(?:same\s+as|identical\s+to|uploaded)\b', re.I)),
)

#: Stage vocabulary, for binding an event to the stage it admits to. An event with no stage
#: is not wrong -- some authorities issue one card for one examination -- but an event bound
#: to the *wrong* stage sends a candidate to the wrong hall.
_STAGE_CUES: tuple[tuple[str, re.Pattern], ...] = (
    # `[\s\-\u2010-\u2015]` and not `[\s\-]`: a PDF extractor renders the
    # Commission's own hyphen in "Tier-1" as an en dash, and the narrower class read
    # that as naming no tier at all.
    ('Tier', re.compile(r'\btier[\s\u2010-\u2015\-]*([IVX]{1,4}|\d)\b', re.I)),
    ('Phase', re.compile(r'\bphase[\s\u2010-\u2015\-]*([IVX]{1,4}|\d)\b', re.I)),
    ('Stage', re.compile(r'\bstage[\s\u2010-\u2015\-]*([IVX]{1,4}|\d)\b', re.I)),
    ('Preliminary', re.compile(r'\b(prelims?|preliminary)\b', re.I)),
    ('Main', re.compile(r'\b(mains?)\b', re.I)),
    ('Interview', re.compile(r'\b(interview|personality\s+test)\b', re.I)),
)

_URL = re.compile(r'https?://[^\s<>"\'),\]]+', re.I)
_YEAR = re.compile(r'\b(20\d{2})\b')

#: How far from a cue a date may sit and still be that cue's date. A sentence in a flattened
#: PDF runs long, and the alternative -- taking the nearest date anywhere -- is what pairs an
#: admit-card cue with an exam date on the next line.
_DATE_WINDOW = 140

#: Much tighter for the examination's own date, because a statement of it puts the date
#: immediately after the cue: "exam on 14.10.2025", "held from 12.09.2025". At the release
#: window, "examination has been rescheduled or not through their candidate login.
#: Candidates ... can view their examination city details from 05.10.2025" reached the city
#: date and published it as the examination's.
_EXAM_DATE_WINDOW = 34

#: And tighter still for a release. Every genuine case puts the date right against the
#: phrase: "admit card w.e.f. 09.10.2025", "city details from 05.10.2025" -- six to eight
#: characters of hand-over. At 140, one notification's single mention of a call letter
#: reached "Candidates can apply online from 16.08.2025" and published the application
#: window's opening as a call-letter release.
_RELEASE_WINDOW = 60


# ====================================================================== helpers
def stage_scope(label: str) -> Scope:
    """The stage a label names, as a scope -- or the whole exam, where it names none."""
    for name, pattern in _STAGE_CUES:
        m = pattern.search(label or '')
        if not m:
            continue
        part = (m.group(1) or '').strip()
        full = f'{name}-{part.upper()}' if part and part.lower() != name.lower() else name
        return Scope(refs=[ScopeRef(kind=ScopeKind.STAGE, ref=_slug(full), label=full)])
    return Scope()


def classify_label(label: str) -> AdmitCardNoticeKind | None:
    """Which of the two documents a label names, in the authority's own words."""
    for kind, pattern in _KIND_CUES:
        if pattern.search(label or ''):
            return kind
    return None


def _is_portal_only(url: str) -> bool:
    """A URL with no path of its own: a front door, not a document.

    The existing section presents exactly this as the "Official Download Portal" for every
    exam. It is a portal, it is worth showing as one, and it is not a download link.
    """
    try:
        parts = urllib.parse.urlsplit(url)
    except ValueError:
        return True
    return parts.path.strip('/') == ''


def classify_url(url: str, *, authority_domain: str = '') -> str:
    """`'DOWNLOAD'`, `'PORTAL'`, or `''` for a URL that may not be offered at all.

    A link is only a download link when it has a path of its own *and* lives on the
    authority's own host. A link somewhere else is not offered to a candidate as the place
    to get their admit card, however plausible it looks.
    """
    url = (url or '').strip().rstrip('.,;')
    if not _URL.fullmatch(url):
        return ''
    host = urllib.parse.urlsplit(url).netloc.lower()
    if authority_domain:
        wanted = urllib.parse.urlsplit(
            authority_domain if '//' in authority_domain else '//' + authority_domain
        ).netloc.lower() or authority_domain.lower()
        base = wanted.split(':')[0].removeprefix('www.')
        if not (host.removeprefix('www.') == base or host.endswith('.' + base)):
            return ''
    return 'PORTAL' if _is_portal_only(url) else 'DOWNLOAD'


def _near(text: str, at: int, width: int = 200) -> str:
    """The span around a cue, for evidence. Verbatim by construction: it is a slice."""
    return text[max(0, at - width // 2):at + width].strip()


#: The end of a sentence in a flattened PDF: a stop, then a capitalised word. The lookahead
#: excludes digits deliberately -- "admit card w.e.f. 09.10.2025" would otherwise read as
#: two sentences and the genuine release would be refused.
_SENTENCE_END = re.compile(r'[.;:]\s+(?=[A-Z])')


def _owns(text: str, at: int, end: int, *, claimants) -> bool:
    """Does a rival cue stand between this cue and its date?

    "Admit Card ... live ... Exam on 14.10.2025": the words "Exam on" sit between the
    admit-card cue and the date and claim it. Proximity alone would have given the admit
    card an exam date as its release.
    """
    between = text[at:end]
    return not any(p.search(between) for p in claimants)


def _dated_fact(reading: str, at: int, text: str, doc: SourceDocument,
                *, dates: list, require_release_cue: bool = True,
                window: int | None = None, claimants=(), measure_from: int | None = None,
                same_sentence: bool = True):
    """The date a cue refers to, or nothing.

    The date must sit within `_DATE_WINDOW` of the cue *after* it, which is how English
    states this ("admit card w.e.f. 09.10.2025"), and -- for a release -- a release cue must
    sit between the two. Without that cue the date beside an admit-card mention may be the
    exam's own, and guessing which is the failure this whole module is shaped around.
    """
    reach = window or _DATE_WINDOW
    # Measured from where the cue *ends* -- the point at which the authority's phrasing
    # hands over to the date. Measured from its start, the length of the cue itself eats the
    # window: "examination is now scheduled to be held from 12.09.2025" is 17 characters of
    # hand-over and 45 characters of total span.
    edge = measure_from if measure_from is not None else at
    for d in dates:
        if d.start < at or d.start - edge > reach:
            continue
        between = text[at:d.start]
        if require_release_cue and not _RELEASE_CUE.search(between):
            continue
        if claimants and not _owns(text, at, d.start, claimants=claimants):
            continue
        # A date in another sentence belongs to another statement. One notification
        # mentions call letters at the end of a clause and opens the next with "How to
        # apply: Candidates can apply online from 16.08.2025"; without this, the
        # application window's opening was published as a call-letter release.
        if same_sentence and _SENTENCE_END.search(between):
            continue
        span = _near(text, at, 240)
        ev = _evidence(span, doc, text, reading=reading)
        note = ''
        if d.precision is DatePrecision.MONTH:
            note = ('the authority published a month, not a day; shown as the month it '
                    'printed rather than a date it did not')
        if ev is None:
            return Fact.needs_review(d.iso, 'the date was read but its span could not be '
                                            'found verbatim in the document'), d
        fact = Fact.verified(d.iso, ev, confidence=0.9 if not note else 0.7)
        fact.note = note
        return fact, d
    return None, None


#: The seam between two cells of a flattened table: a lower-case word, then a capitalised
#: one, with no punctuation between. Splitting there is what keeps "7 days before
#: examination" from being quoted as "7 days before examination Dates of Online Examination
#: - Preliminary (tent".
_CELL_SEAM = re.compile(r'(?<=[a-z,)])\s+(?=[A-Z])')


def _rule_text(raw: str) -> str:
    """A rule as the authority wrote it, ending where its own sentence ends."""
    return _CELL_SEAM.split(normalise_ws(raw), 1)[0].strip(' ,-')


def _rule_fact(at: int, text: str, doc: SourceDocument):
    """A relative release rule near a cue, kept in the authority's own words."""
    window = text[at:at + 220]
    m = _RELATIVE_RULE.search(window)
    if not m:
        return None
    phrase = _rule_text(m.group(0))
    ev = _evidence(_near(text, at, 240), doc, text,
                   reading=f'release rule: {phrase}')
    if ev is None:
        return Fact.needs_review(phrase, 'the rule was read but its span could not be '
                                         'found verbatim in the document')
    fact = Fact.verified(phrase, ev, confidence=0.8)
    fact.note = ('the authority published a rule, not a date; GovOS does not resolve it '
                 'into one, because the examination date it counts back from can itself '
                 'move')
    return fact


#: A document withdrawing its own earlier date. What follows one of these governs.
_SUPERSEDED_CUE = re.compile(
    r'\bhowever\b|\bpostponed\b|\brescheduled\b|\bre[\s\-]?scheduled\b'
    r'|\bnow\s+scheduled\b|\brevised\b|\bin\s+supersession\b|\bdeferred\b', re.I)


def _operative_exam_date(body: str, dates: list, doc: SourceDocument, sig):
    """The examination date a document is *currently* asserting.

    A real notice states two: the date it originally published and the date it moved to.
    Taking the first match published a withdrawn date as the operative one. Where the
    document carries its own supersession marker, the date after that marker governs, and
    the earlier is named in the fact’s note rather than dropped -- a discrepancy inside one
    document is something a candidate should be able to see, not something to resolve
    silently.
    """
    found = []
    for m in _EXAM_DATE_CUE.finditer(body):
        if sig is not None and m.start() > sig.start():
            break
        fact, read = _dated_fact('the date of the examination itself', m.start(), body,
                                 doc, dates=dates, require_release_cue=False,
                                 window=_EXAM_DATE_WINDOW, measure_from=m.end(),
                                 claimants=[p for _, p in _KIND_CUES])
        if fact is not None:
            found.append((m.start(), fact, read))
    if not found:
        return None
    distinct = {f.value for _, f, _ in found}
    if len(distinct) == 1:
        return found[0][1]
    mark = _SUPERSEDED_CUE.search(body)
    after = [row for row in found if mark is not None and row[0] > mark.start()]
    chosen = after[0] if after else found[-1]
    earlier = sorted(distinct - {chosen[1].value})
    fact = chosen[1]
    fact.note = ('this document states more than one examination date; '
                 + ', '.join(earlier) + ' appears before its own '
                 + (f'“{mark.group(0)}”' if mark else 'later statement')
                 + ', so the later one is taken as operative and the earlier is recorded '
                   'as superseded rather than dropped')
    return fact


def _list_facts(cues, text: str, doc: SourceDocument, *, reading: str) -> list:
    out = []
    for label, pattern in cues:
        m = pattern.search(text)
        if not m:
            continue
        ev = _evidence(_near(text, m.start(), 220), doc, text,
                       reading=f'{reading}: {label}')
        out.append(Fact.verified(label, ev, confidence=0.8) if ev
                   else Fact.needs_review(label, 'the span could not be found verbatim'))
    return out


def _urls_in(text: str, doc: SourceDocument, *, authority_domain: str):
    """`(portal_fact, download_fact)` from the links a passage actually contains."""
    portal = download = None
    for m in _URL.finditer(text):
        raw = m.group(0).rstrip('.,;)')
        kind = classify_url(raw, authority_domain=authority_domain)
        if not kind:
            continue
        ev = _evidence(_near(text, m.start(), 200), doc, text,
                       reading=f'{kind.lower()} URL: {raw}')
        fact = (Fact.verified(raw, ev, confidence=0.9) if ev
                else Fact.needs_review(raw, 'the span could not be found verbatim'))
        if kind == 'PORTAL' and portal is None:
            fact.note = ('the authority names this portal, not a file; a candidate signs '
                         'in here, and GovOS does not present it as a direct download')
            portal = fact
        elif kind == 'DOWNLOAD' and download is None:
            download = fact
    return portal, download


def _cycle_in(text: str, fallback: str = '') -> str:
    m = _YEAR.search(text or '')
    return m.group(1) if m else fallback


# ================================================================ prose notices
def read_notice(doc: SourceDocument, text: str, *, exam_id: str, headline: str = '',
                published_at: str = '', authority_domain: str = '',
                cycle: str = '') -> list[AdmitCardNotice]:
    """Every admit-card event a notice states, one per cue it carries.

    A single real notice carries a city-intimation date, an admit-card date and the
    examination's own date in one paragraph. Each cue gets its own event; the examination
    date is attached to each as `exam_date` and is never any of them.
    """
    body = normalise_ws(f'{headline} {text}' if headline else text)
    if not body:
        return []
    dates = read_dates(body)
    # Everything after the signature is a dateline or an address, not an event.
    sig = _SIGNATURE.search(body)
    live = [d for d in dates if sig is None or d.start < sig.start()]
    exam_fact = _operative_exam_date(body, live, doc, sig)
    # An authority commonly names the tier in the notice's own headline and nowhere near the
    # sentence carrying the date, so the headline scopes what the body states.
    headline_scope = stage_scope(headline)
    document_scope, document_note = Scope(), ''
    if not headline_scope.refs:
        named = {r.label for r in
                 (stage_scope(body[m.start():m.start() + 40]) for m in
                  re.finditer(r'\b(?:tier|phase|stage|prelims?|preliminary|mains?)\b',
                              body, re.I))
                 for r in ([r.refs[0]] if r.refs else [])}
        if len(named) == 1:
            document_scope = stage_scope(named.pop())
            document_note = ('the stage was named by the document as a whole rather than '
                             'beside this statement')

    out: list[AdmitCardNotice] = []
    seen: set[tuple] = set()
    for kind, pattern in _KIND_CUES:
        for m in pattern.finditer(body):
            label = normalise_ws(m.group(0))
            if sig is not None and m.start() > sig.start():
                continue
            released, used = _dated_fact(f'{label} released', m.start(), body, doc,
                                         dates=live, claimants=[_EXAM_DATE_CUE],
                                         window=_RELEASE_WINDOW, measure_from=m.end())
            rule = None if released is not None else _rule_fact(m.start(), body, doc)
            if released is None and rule is None:
                continue
            if exam_fact is not None and released is not None \
                    and used is not None and exam_fact.value == released.value:
                # The only date in reach is the examination's own. A release date GovOS
                # cannot separate from the exam date is not a release date.
                continue
            scope = stage_scope(body[max(0, m.start() - 160):m.start() + 160])
            scoped_by_document = False
            if not scope.refs:
                scope = headline_scope
            if not scope.refs and document_scope.refs:
                scope, scoped_by_document = document_scope, True
            key = (kind, scope.refs[0].ref if scope.refs else '',
                   released.value if released else (rule.value if rule else ''))
            if key in seen:
                continue
            seen.add(key)

            passage = _near(body, m.start(), 700)
            portal, download = _urls_in(passage, doc, authority_domain=authority_domain)
            event = AdmitCardNotice(
                id=f'{exam_id}-{kind.value.lower().replace("_", "-")}-'
                   f'{_slug(scope.refs[0].label if scope.refs else "exam")}-'
                   f'{(released.value if released else "rule")}',
                kind=kind, scope=scope,
                official_label=label,
                cycle=_cycle_in(headline or body[:200], cycle),
                released_at=released or Fact.not_extracted(
                    'the notice states a rule rather than a date'),
                release_rule=rule or Fact.not_extracted(
                    'no relative release rule was stated'),
                exam_date=exam_fact or Fact.not_extracted(
                    'this source does not state the examination date'),
                portal_url=portal or Fact.not_extracted(
                    'no portal link appears beside this statement'),
                download_url=download or Fact.not_extracted(
                    'the authority publishes no direct file link; the document is served '
                    'to each candidate after sign-in'),
                credentials_required=Fact.not_extracted(),
                instructions=[],
                documents_required=_list_facts(_DOCUMENT_CUES, passage, doc,
                                               reading='document required'),
                status=Status.VERIFIED,
                evidence=[e for f in (released, rule, portal) if f for e in f.evidence],
            )
            if released is not None and used is not None:
                event.released_precision = used.precision.value
            if scoped_by_document:
                event.note = (event.note + ' ' if event.note else '') + document_note
            creds = _list_facts(_CREDENTIAL_CUES, passage, doc, reading='credential')
            if creds:
                event.credentials_required = Fact.verified(
                    [c.value for c in creds],
                    [e for c in creds for e in c.evidence][:2], confidence=0.8)
            if not event.evidence or not any(e.is_verbatim for e in event.evidence):
                event.status = Status.NEEDS_REVIEW
                event.note = ('no span of this event could be verified verbatim in the '
                              'document, so it is not shown as the authority’s own')
            out.append(event)
    out.sort(key=lambda e: (e.released_at.value or e.release_rule.value or ''))
    return out


# ================================================================= table rows
def read_row(label: str, value: str, doc: SourceDocument, text: str, *, exam_id: str,
             authority_domain: str = '', cycle: str = '',
             portal_url: str = '') -> AdmitCardNotice | None:
    """One row of a document table or a schedule: a label and whatever sits beside it.

    Two authorities publish admit cards this way and nothing else -- a row reading
    `e - Admit Card | 15/05/2026`, or `Download of call letters ... Preliminary |
    August, 2026`. The label carries the kind *and* the stage; the value carries a date, a
    month, or a rule where the authority published no date at all.
    """
    kind = classify_label(label)
    if kind is None:
        return None
    # The document's own name is the phrase that identified it, not the whole activity row.
    named = next((m.group(0) for _, pattern in _KIND_CUES
                  for m in [pattern.search(label or '')] if m), '')
    document_name = normalise_ws(named).strip(' -\u2013') or normalise_ws(label)
    # A flattened table has no cell boundaries, so a value regularly runs into the next
    # row: "7 days before examination Dates of Online Examination - Preliminary
    # (tentative) 03.10.2025". Read whole, that row's release date becomes the *next*
    # row's examination date. The cell ends where its own sentence does.
    value = _rule_text(value)
    joined = normalise_ws(f'{label} {value}')
    dates = read_dates(joined)
    at = len(normalise_ws(label))
    released, _ = _dated_fact(f'{normalise_ws(label)}: {normalise_ws(value)}', 0, joined,
                              doc, dates=dates, require_release_cue=False)
    rule = None
    if released is None:
        rule = _rule_fact(0, joined, doc)
        if rule is None:
            m = _RELATIVE_RULE.search(normalise_ws(value))
            if m:
                rule = Fact.needs_review(
                    _rule_text(m.group(0)),
                    'the rule was read from the row but its span could not be verified '
                    'verbatim in the document')
    if released is None and rule is None:
        return None

    scope = stage_scope(label)
    portal = None
    # The domain guard belongs to links read *out of a document*, where an unknown host
    # could be anyone. A portal handed in by the caller comes from the record, and an
    # authority's sign-in portal routinely lives on another of its own hosts --
    # upsconline.nic.in for upsc.gov.in -- so guarding it there hid the real portal.
    if portal_url and _URL.fullmatch(portal_url.strip()):
        portal = Fact.needs_review(
            portal_url,
            'the portal is the authority’s own sign-in page, named in this record rather '
            'than in the row; it is not a direct link to the document')
    event = AdmitCardNotice(
        id=f'{exam_id}-{kind.value.lower().replace("_", "-")}-'
           f'{_slug(scope.refs[0].label if scope.refs else "exam")}-'
           f'{(released.value if released else _slug(rule.value))}',
        kind=kind, scope=scope,
        official_label=document_name,
        source_label=normalise_ws(label),
        cycle=_cycle_in(joined, cycle),
        released_at=released or Fact.not_extracted(
            'the authority published a rule rather than a date for this row'),
        release_rule=rule or Fact.not_extracted('no relative release rule was stated'),
        exam_date=Fact.not_extracted('this row does not state the examination date'),
        portal_url=portal or Fact.not_extracted('this row carries no portal link'),
        download_url=Fact.not_extracted(
            'the authority publishes no direct file link; the document is served to each '
            'candidate after sign-in'),
        credentials_required=Fact.not_extracted(),
        status=Status.VERIFIED,
        evidence=list((released or rule).evidence),
    )
    del at
    if released is not None:
        for d in dates:
            if d.iso == released.value:
                event.released_precision = d.precision.value
                break
    if not any(e.is_verbatim for e in event.evidence):
        event.status = Status.NEEDS_REVIEW
        event.note = ('the row was read but no span of it could be verified verbatim in '
                      'the document')
    return event


def read_rows(rows, doc: SourceDocument, text: str, *, exam_id: str,
              authority_domain: str = '', cycle: str = '',
              portal_url: str = '') -> list[AdmitCardNotice]:
    """Every admit-card row in a table, and none of the rows that are about something else."""
    out = []
    for label, value in rows:
        event = read_row(label, value, doc, text, exam_id=exam_id,
                         authority_domain=authority_domain, cycle=cycle,
                         portal_url=portal_url)
        if event is not None:
            out.append(event)
    return out


# ================================================================= publication
def may_supply_admit_card(text: str, target) -> tuple[bool, str]:
    """Whether this document's admit-card facts belong to this exam.

    The same gate the pattern and syllabus readers use, and for the same reason: a notice
    that merely mentions an exam among the fourteen its rules cover supplies nothing unless
    its own title block names it. An admit-card notice makes that sharper, because one
    authority publishes dozens of them a month and they differ only in which examination and
    which cycle they name.
    """
    from .pattern import may_supply_pattern

    return may_supply_pattern(text, target)


def source_failed(error: Exception | str) -> tuple[SourceOutcome, str]:
    """Classify a read failure as infrastructure -- which is never a candidate-facing fact.

    Returned so a build report can say what went wrong. Nothing here may ever become a
    `Status`: the whole point is that "we could not reach the page" is not "the authority
    has issued no admit card".
    """
    message = str(error)
    lowered = message.lower()
    if any(w in lowered for w in ('timed out', 'timeout', 'temporary failure',
                                  'name or service not known', 'getaddrinfo',
                                  'connection refused', 'unreachable')):
        return SourceOutcome.NETWORK_UNAVAILABLE, message
    if any(w in lowered for w in ('no text', 'not a pdf', 'cannot decode', 'unreadable',
                                  'empty document')):
        return SourceOutcome.SOURCE_UNREADABLE, message
    return SourceOutcome.SOURCE_FETCH_FAILURE, message


# ====================================================================== report
def describe(events: list) -> dict:
    """What was found, counted by what it is, for a build report."""
    by_kind: dict = {}
    for event in events:
        by_kind[event.kind.value] = by_kind.get(event.kind.value, 0) + 1
    return {
        'events': len(events),
        'byKind': by_kind,
        'publishable': sum(1 for e in events if e.is_publishable),
        'withStage': sum(1 for e in events if e.scope.refs),
        'withDate': sum(1 for e in events if e.released_at.has_value),
        'withRuleOnly': sum(1 for e in events
                            if not e.released_at.has_value and e.release_rule.has_value),
        'withExamDate': sum(1 for e in events if e.exam_date.has_value),
        'withDownloadUrl': sum(1 for e in events if e.download_url.has_value),
        'rows': [
            {'kind': e.kind.value, 'label': e.official_label,
             'stage': e.scope.refs[0].label if e.scope.refs else '',
             'cycle': e.cycle,
             'released': e.released_at.value, 'rule': e.release_rule.value,
             'examDate': e.exam_date.value, 'status': e.status.value}
            for e in events],
    }
