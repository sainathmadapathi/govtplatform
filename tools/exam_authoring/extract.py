"""Reading facts out of an authority's own documents.

Every function here returns a `Field`, so a miss is recorded as a miss. The extractors are
deliberately literal: they look for the wording the notices actually use and, where they
cannot find it, they say so rather than relaxing the pattern until something matches. A
loose pattern that always finds *an* answer is worse than no extractor, because it produces
a confident wrong date.

Two rules learned from this repo and encoded here:

* A date on the authority's examination page outranks the same date in the notice PDF. UPSC
  extended CSE 2026 by three days after publishing its notice, so a pipeline that reads only
  the PDF is guaranteed to be stale (CLAUDE.md, "A notice PDF is not the last word on a date").
* A scanned PDF is reported as unreadable, never as empty. "The authority published nothing"
  and "we could not read what they published" are different claims.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from .record import Citation, Field
from .sources import Document

MONTHS = ('January February March April May June July August September October November December').split()
_MONTH_RX = '|'.join(MONTHS) + '|' + '|'.join(m[:3] for m in MONTHS)


def _clean(s: str) -> str:
    return ' '.join((s or '').split())


def pages_of(doc: Document) -> list[str]:
    """Each page as one line of normalised text.

    A PDF wraps sentences at the page's column width, so a clause like "born not earlier
    than 2nd August, 1994" arrives with a newline in the middle of the fact. Matching
    against the raw text made
    every multi-line clause silently unfindable, which reads as "the authority did not
    publish it" — the one wrong answer this pipeline must not give. Normalising first costs
    nothing and keeps the page number, which is what the citation needs.
    """
    return [_clean(p) for p in (doc.pages or [doc.text])]


def excerpt_around(text: str, match: re.Match, width: int = 260) -> str:
    start = max(0, match.start() - width // 3)
    return _clean(text[start:match.end() + width])


def cite(doc: Document, title: str, page: int, clause: str, excerpt: str) -> Citation:
    return Citation(document_title=title, url=doc.url, page=page, clause=clause,
                    excerpt=_clean(excerpt), verified_date=doc.fetched_at)


# ---------------------------------------------------------------------------- dates
# Birth years are 19xx. Restricting every pattern to 20xx meant the age band -- the one
# clause that must carry a 19xx year -- could never be read, and came back as "not published".
_YEAR = r'(19\d{2}|20\d{2})'
_DATE_PATTERNS = [
    # 27/02/2026 - 6:00pm   |   27-02-2026
    (rf'(\d{{1,2}})[/.\-](\d{{1,2}})[/.\-]{_YEAR}', 'dmy'),
    # 24th May, 2026  |  4 February 2026
    (rf'(\d{{1,2}})(?:st|nd|rd|th)?\s+({_MONTH_RX})[,\s]+{_YEAR}', 'dMy'),
    # February 4, 2026
    (rf'({_MONTH_RX})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,\s]+{_YEAR}', 'Mdy'),
]

_TIME_RX = re.compile(r'(\d{1,2})[:.](\d{2})\s*(a\.?m\.?|p\.?m\.?)|(\d{1,2})\s*(a\.?m\.?|p\.?m\.?)', re.I)


def _month_num(name: str) -> int:
    name = name[:3].lower()
    for i, m in enumerate(MONTHS, start=1):
        if m[:3].lower() == name:
            return i
    return 0


#: Indian notices write a crucial date as "the 1st of August, 2026". Dropping the "of"
#: before matching is the difference between reading that date and reporting it missing.
_OF_RX = re.compile(r'\b(\d{1,2}(?:st|nd|rd|th)?)\s+of\s+(' + _MONTH_RX + r')\b', re.I)


def parse_date(text: str) -> Optional[str]:
    """First date in `text` as YYYY-MM-DD, or None. Never guesses a missing component."""
    text = _OF_RX.sub(r'\1 \2', text or '')
    for pattern, order in _DATE_PATTERNS:
        m = re.search(pattern, text, re.I)
        if not m:
            continue
        try:
            if order == 'dmy':
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            elif order == 'dMy':
                d, mo, y = int(m.group(1)), _month_num(m.group(2)), int(m.group(3))
            else:
                mo, d, y = _month_num(m.group(1)), int(m.group(2)), int(m.group(3))
            if not (1 <= mo <= 12 and 1 <= d <= 31):
                continue
            return f'{y:04d}-{mo:02d}-{d:02d}'
        except (ValueError, IndexError):
            continue
    return None


def parse_time(text: str) -> str:
    """'18:00:00' from '6:00pm'. Defaults to 00:00:00 only when no time is printed."""
    m = _TIME_RX.search(text or '')
    if not m:
        return '00:00:00'
    if m.group(1):
        h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or '').lower()
    else:
        h, mi, ap = int(m.group(4)), 0, (m.group(5) or '').lower()
    if ap.startswith('p') and h != 12:
        h += 12
    if ap.startswith('a') and h == 12:
        h = 0
    return f'{h:02d}:{mi:02d}:00'


#: Label wording -> the ImportantDate.type the register uses. Only labels the authorities
#: actually print; an unrecognised label is carried through as OTHER rather than forced.
DATE_LABELS: list[tuple[str, str, str]] = [
    (r'date of notification|notification.*(date|published)|date of advertisement', 'NOTIFICATION', 'Notification published'),
    (r'last date.*(receipt|submission).*application|closing date|last date for apply', 'APPLICATION_CLOSE', 'Last date for online applications'),
    (r'(commencement|opening|start).*(online )?application|application.*begin|date of.*start.*application', 'APPLICATION_OPEN', 'Online applications open'),
    (r'date of commencement of exam|date of exam|examination date|date of preliminary|prelim', 'EXAM_TIER1', 'Examination date'),
    (r'main(s)? exam|date of main', 'EXAM_TIER2', 'Main examination'),
    (r'admit card|e-admit card|hall ticket', 'ADMIT_CARD', 'Admit card'),
    (r'answer key', 'ANSWER_KEY', 'Answer key'),
    (r'result|written result', 'RESULT', 'Result'),
    (r'interview|personality test', 'INTERVIEW', 'Interview / Personality Test'),
    (r'correction window|edit window|modification window', 'CORRECTION_WINDOW', 'Correction window'),
]


def dates_from_rows(doc: Document, rows: Iterable[list[str]], doc_title: str) -> Field:
    """Dates from a label/value table — the most trustworthy shape an authority publishes.

    UPSC's per-examination page is exactly this, and it is where an extension shows up; the
    notice PDF cannot know about a change made after it was printed.
    """
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        if len(row) < 2:
            continue
        label, value = _clean(row[0]), _clean(' '.join(row[1:]))
        iso = parse_date(value)
        if not iso:
            continue
        kind, nice = 'OTHER', label
        for rx, k, n in DATE_LABELS:
            if re.search(rx, label, re.I):
                kind, nice = k, n
                break
        key = (kind, iso)
        if key in seen:
            continue
        seen.add(key)
        found.append({
            'type': kind,
            'label': f'{nice} ({label})' if nice != label else label,
            'dateTimeStr': f'{iso} {parse_time(value)}',
            'rawLabel': label,
            'rawValue': value,
        })
    if not found:
        return Field.not_extracted('dates', doc.url, 'label/value date row')
    return Field.found('dates', found, cite(
        doc, doc_title, 1, 'Examination details table',
        '; '.join(f"{d['rawLabel']} {d['rawValue']}" for d in found[:6])))


def dates_from_notice(doc: Document, doc_title: str) -> Field:
    """Fallback for authorities with no structured page: dates beside their labels in prose."""
    found: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for page_no, page in enumerate(pages_of(doc), start=1):
        for rx, kind, nice in DATE_LABELS:
            for m in re.finditer(rx, page, re.I):
                window = page[m.start():m.start() + 220]
                iso = parse_date(window)
                if not iso:
                    continue
                key = (kind, iso)
                if key in seen:
                    continue
                seen.add(key)
                found.append({
                    'type': kind,
                    'label': nice,
                    'dateTimeStr': f'{iso} {parse_time(window)}',
                    'page': page_no,
                    'rawValue': _clean(window)[:160],
                })
    if not found:
        return Field.not_extracted('dates', doc.url, 'dated label')
    # Prose is looser than a table: a date beside a label in running text can belong to a
    # sentence about a previous cycle, so this path is offered for review, not asserted.
    return Field.needs_review(
        'dates', found,
        'Read from prose in the notice rather than a label/value table — confirm each against the authority’s examination page.',
        cite(doc, doc_title, found[0]['page'], 'Dates in notice text', found[0]['rawValue']))


# ------------------------------------------------------------------------ eligibility
def age_limits(doc: Document, doc_title: str) -> Field:
    """The age band and the date it is reckoned on."""
    rx = re.compile(
        r'attained the age of\s+(\d{2})\s*years.{0,80}?not have attained the age of\s+(\d{2})\s*years',
        re.I | re.S)
    # The crucial date gets its own search. As an optional tail after a lazy span the regex
    # engine simply never entered it, so the band was read without the date it is reckoned on.
    as_on_rx = re.compile(r'on the\s+(\d{1,2}(?:st|nd|rd|th)?\s+of\s+\w+,?\s+20\d{2})', re.I)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = rx.search(page)
        if not m:
            continue
        born = re.search(r'born not earlier than\s+(.{0,40}?)\s+and not later than\s+(.{0,40}?)[;.]', page, re.I)
        as_on = as_on_rx.search(page[m.start():m.start() + 400])
        value = {
            'minAge': int(m.group(1)),
            'maxAge': int(m.group(2)),
            'asOn': parse_date(as_on.group(1)) if as_on else '',
            'bornNotEarlierThan': parse_date(born.group(1)) if born else '',
            'bornNotLaterThan': parse_date(born.group(2)) if born else '',
        }
        return Field.found('ageLimits', value,
                           cite(doc, doc_title, page_no, 'Conditions of Eligibility — Age Limits',
                                excerpt_around(page, m)))
    return Field.not_extracted('ageLimits', doc.url, 'age-limit clause')


def qualification(doc: Document, doc_title: str) -> Field:
    """The Conditions-of-Eligibility clause, not the first time the words appear.

    The phrase "educational qualification" also occurs in How-to-Apply ("...date of birth,
    educational qualification, etc as may be sought..."), which is earlier in the notice and
    says nothing about what degree is required. Anchoring on the heading is what makes this
    the eligibility rule rather than a passing mention.
    """
    heading = re.compile(r'Minimum Educational Qualification\s*[:\-]?\s*(.{80,900})', re.I)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = heading.search(page)
        if m:
            return Field.found('qualification', _clean(m.group(1))[:700],
                               cite(doc, doc_title, page_no,
                                    'Conditions of Eligibility — Minimum Educational Qualification',
                                    _clean(m.group(0))))
    # No heading: a degree sentence is better than nothing, but it is offered for review.
    loose = re.compile(r'must hold a\s+(?:Bachelor|Graduate|Degree)[^.]{0,400}\.', re.I)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = loose.search(page)
        if m:
            return Field.needs_review('qualification', _clean(m.group(0))[:700],
                                      'Read from a degree sentence, not from a "Minimum Educational '
                                      'Qualification" heading — confirm it is the eligibility rule.',
                                      cite(doc, doc_title, page_no, 'Degree requirement', _clean(m.group(0))))
    return Field.not_extracted('qualification', doc.url, 'educational-qualification clause')


def attempts(doc: Document, doc_title: str) -> Field:
    rx = re.compile(r'number of attempts.{0,400}', re.I | re.S)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = rx.search(page)
        if m:
            n = re.search(r'permitted\s+(\w+)\s*\((\d+)\)\s*attempts|(\d+)\s*attempts', m.group(0), re.I)
            return Field.found('attempts',
                               {'text': _clean(m.group(0))[:400],
                                'count': int(n.group(2) or n.group(3)) if n else None},
                               cite(doc, doc_title, page_no, 'Conditions of Eligibility — Number of attempts',
                                    _clean(m.group(0))))
    return Field.not_extracted('attempts', doc.url, 'number-of-attempts clause')


def fee(doc: Document, doc_title: str) -> Field:
    rx = re.compile(r'(?:^|\n)\s*(?:\d+\.\s*)?FEE\s*[:\-].{0,700}|fee of\s*(?:Rs\.?|₹)\s*[\d,]+/?-?.{0,500}', re.I | re.S)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = rx.search(page)
        if not m:
            continue
        body = _clean(m.group(0))
        amounts = re.findall(r'(?:Rs\.?|₹)\s*([\d,]+)', body)
        exempt = re.search(r'except\s*\(?([^)]{0,140}?)\s*(?:who are exempted|\))', body, re.I)
        return Field.found('fee', {
            'text': body[:600],
            'amounts': [a.replace(',', '') for a in amounts[:3]],
            'exemptions': _clean(exempt.group(1)) if exempt else '',
        }, cite(doc, doc_title, page_no, 'Fee', body))
    return Field.not_extracted('fee', doc.url, 'fee clause')


# --------------------------------------------------------------------------- pattern
def scheme_tables(doc: Document, doc_title: str) -> Field:
    """Paper rows — 'Paper I ... 200 marks ... 2 hours' — as the exam pattern."""
    papers: list[dict] = []
    rx = re.compile(
        # The name runs up to the marks with no second lazy span between them; with one
        # there, the name stopped at its two-character minimum ("Ess" for "Essay").
        r'\bPaper[\s\-]*([IVX]+|\d)\b[\s:\-–]*([A-Za-z][^\n]{2,90}?)\s*[\-–—|]?\s*'
        r'(\d{2,4})\s*marks(?:[^\n]{0,60}?(\d{1,3})\s*(?:hours?|hrs?|minutes?|mins?))?',
        re.I | re.S)
    for page_no, page in enumerate(pages_of(doc), start=1):
        for m in rx.finditer(page):
            entry = {
                'paper': _clean(m.group(1)),
                'name': _clean(m.group(2)),
                'marks': int(m.group(3)),
                'duration': _clean(m.group(4) or ''),
                'page': page_no,
            }
            if entry not in papers:
                papers.append(entry)
    if not papers:
        return Field.not_extracted('examPattern', doc.url, 'paper/marks row')
    return Field.needs_review(
        'examPattern', papers[:20],
        'Paper rows read from prose; check marks and duration against the notice’s scheme table before badging as verified.',
        cite(doc, doc_title, papers[0]['page'], 'Scheme of Examination', str(papers[:3])))


# ----------------------------------------------------------------------------- posts
#: The list marker these notices use: a roman numeral in brackets, "(i)" ... "(xxiii)".
_MARKER_RX = re.compile(r'\(\s*(?=[ivxlc])([ivxlc]{1,6})\s*\)')


def services_list(doc: Document, doc_title: str) -> Field:
    """A roman-numbered services list, which is how these notices print the posts.

    The item text is taken as everything *between* two markers rather than by matching a
    run of non-bracket characters. Excluding brackets truncated every service whose name
    carries a qualifier — "Indian Railway Management Service (Traffic), Group 'A'" became
    "Indian Railway Management Service", which collapsed the Traffic, Personnel and
    Accounts services into three identical entries and threw away the Group with them.
    """
    best: list[str] = []
    best_page = 1
    for page_no, page in enumerate(pages_of(doc), start=1):
        marks = list(_MARKER_RX.finditer(page))
        if len(marks) < 3:
            continue
        items = []
        for i, m in enumerate(marks):
            end = marks[i + 1].start() if i + 1 < len(marks) else min(len(page), m.end() + 140)
            text = _clean(page[m.end():end])
            # Stop at the sentence that follows the last item, so trailing prose about
            # vacancies does not become a service name.
            text = re.split(r'(?<=[a-z’\'])\.\s+[A-Z]', text)[0]
            if 6 <= len(text) <= 160 and re.match(r'^[A-Z]', text):
                items.append(text.rstrip(' .;,'))
        items = [i for i in items if not re.match(r'^(the|a|an)\b', i, re.I)]
        if len(items) > len(best):
            best, best_page = items, page_no
    if len(best) < 3:
        return Field.not_extracted('posts', doc.url, 'services/posts list')
    return Field.found('posts', best, cite(doc, doc_title, best_page, 'Services / posts',
                                           '; '.join(best[:5])))


def vacancies(doc: Document, doc_title: str) -> Field:
    rx = re.compile(r'number of vacancies[^.]{0,160}?(?:approximately|about|is|be)\s*([\d,]{2,7})', re.I | re.S)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = rx.search(page)
        if m:
            return Field.found('vacancies', m.group(1).replace(',', ''),
                               cite(doc, doc_title, page_no, 'Vacancies', excerpt_around(page, m)))
    return Field.not_extracted('vacancies', doc.url, 'vacancy count')


# ----------------------------------------------------------------------- application
def application_portal(doc: Document, doc_title: str) -> Field:
    rx = re.compile(r'apply online[^.]{0,80}?(https?://[\w./-]+)|website\s*(https?://[\w./-]+)', re.I)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = rx.search(page)
        if m:
            url = (m.group(1) or m.group(2)).rstrip('.')
            return Field.found('applicationPortal', url,
                               cite(doc, doc_title, page_no, 'How to Apply', excerpt_around(page, m)))
    return Field.not_extracted('applicationPortal', doc.url, 'application URL')


def how_to_apply(doc: Document, doc_title: str) -> Field:
    """The How-to-Apply section verbatim, which is what the mock form is authored from."""
    # No leading newline anchor: pages_of() normalises each page to a single line, so an
    # anchor on "\n" matches nothing at all once the text has been cleaned.
    rx = re.compile(r'\bHOW TO APPLY\s*[:\-]?.{300,6000}', re.I | re.S)
    for page_no, page in enumerate(pages_of(doc), start=1):
        m = rx.search(page)
        if m:
            return Field.found('howToApply', _clean(m.group(0))[:6000],
                               cite(doc, doc_title, page_no, 'How to Apply', _clean(m.group(0))[:400]))
    return Field.not_extracted('howToApply', doc.url, '"How to Apply" section')


def admit_card(doc: Document, doc_title: str) -> Field:
    # The heading first. "admit card" alone also appears mid-sentence ("Mere issue of
    # e-Admit Card to the candidate will not imply..."), which says nothing about when or
    # where to download one — matching it produced the fragment "Admit Card to the".
    for rx in (re.compile(r'ISSUANCE OF E?-?ADMIT CARD\s*[:\-]?.{80,700}', re.I | re.S),
               re.compile(r'e-Admit Card will be made available[^.]{0,300}\.', re.I | re.S),
               re.compile(r'(?<![a-z])admit card[^.]{40,400}\.', re.I | re.S)):
        for page_no, page in enumerate(pages_of(doc), start=1):
            m = rx.search(page)
            if not m:
                continue
            body = _clean(m.group(0))
            portal = re.search(r'(https?://[\w./-]+)', body)
            return Field.found('admitCard', {
                'text': body[:500],
                'portalUrl': portal.group(1).rstrip('.]') if portal else '',
            }, cite(doc, doc_title, page_no, 'Issuance of e-Admit Card', body))
    return Field.not_extracted('admitCard', doc.url, 'admit-card clause')
