"""Trusted-secondary ingestion: read a reviewed secondary source for one exam, keep what it says as
*its* claims, and compare them with the official record.

A reviewed secondary source (an education portal a person has checked, for named roles) often has
what an authority's own site makes hard to reach: one page that lists an exam's dates, a list of old
papers, a result announcement. This module reads such a source -- and only such a source -- for one
exam, and produces three things:

    resources    the source's pages and files about this exam, each with its provenance (which of
                 the source's listings it was found on, the words it was listed under, when it was
                 read, a hash of what was read) and its class: TRUSTED_SECONDARY for a role the
                 review names, SECONDARY for any other role -- never PRIMARY_OFFICIAL
    claims       what the source states about this exam's fields (a date, a vacancy count), each
                 with the exact words it was read from, re-checked against the text GovOS fetched
    resolutions  each field compared with the official record through `claims.reconcile`: the
                 official value governs, a trusted source agreeing corroborates it, a source
                 disagreeing is recorded as a conflict and never used, a field only the source
                 states stays the source's claim

Nothing here writes a record, a registry or a page, and nothing here is automatic: it runs when a
person runs it (`python -m tools.exam_builder.secondary_ingestion`). A secondary claim can not make a
value publishable: `Fact.is_publishable` requires official verbatim evidence, and every piece of
evidence this module creates carries its secondary class.

The reviewed-source registry is `source_trust_profiles.json` -- the same file the source classifier
reads -- with an `ingestion` block per source (which of its listings to read, for which authority).
A source is read only when its profile is REVIEWED, TRUSTED_SECONDARY, covers the exam's authority,
and every listing it names is on its own domain.

Reused, not changed: `extract_links`, `exam_words_for` (authority_discovery), `classify_link`
(resource_roles), `classify_source` / `TrustRegistry` (source_trust), `discover.gate`,
`pyq.identity_from_text`, `claims.reconcile`, `fetch_checked`. Claude is not used.
"""
from __future__ import annotations

import argparse
import hashlib
import html as _html
import io
import json
import os
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable, Optional
from urllib.parse import parse_qs, urlparse

from ..claude_cli.discovery import fetch_checked, validate_url_syntax
from ..exam_authoring.sources import estate_of, same_estate
from .authority_discovery import exam_words_for, extract_links
from .claims import ClaimResolution, Resolution, SourceClaim, reconcile
from .discover import DocKind, Relevance, gate
from .evidence import EvidenceStatus, normalise_ws
from .pyq import identity_from_text
from .resource_roles import classify_link
from .source_graph import SourceClass, normalize_url, now_iso
from .source_trust import DEFAULT_PROFILE_PATH, SourceTrustProfile, TrustRegistry, bare_host, classify_source

#: What this layer's output is, stated on every report, claim and resolution it produces: a reviewed
#: secondary source's statements, read from the command line, that the application neither stores nor
#: shows. It changes only when results are persisted and consumed by the application.
STATUS = {'sourceClass': 'TRUSTED_SECONDARY', 'availability': 'COMMAND_LINE_ONLY', 'publication': 'NOT_PUBLISHED',
          'note': 'A reviewed secondary source read from the command line. The application does not store or show '
                  'any of this; nothing here is a candidate fact. Where a field is OFFICIAL_*, the value that governs '
                  "is the official record's, which candidates already see from the official record itself."}

#: Roles whose items are evidence that a document exists ("an answer key for this exam is listed").
_LISTED_ROLES = (DocKind.ANSWER_KEY, DocKind.QUESTION_PAPER, DocKind.RESULT)
_THIN_LINK = re.compile(r'^(download|click\s*here|view|read\s*more|more|link|here|pdf)\.?$', re.I)


# ===================================================================== the registry
@dataclass
class EntryPoint:
    """One listing on a reviewed source: where it is, what it lists, for which authority."""

    url: str
    lists: DocKind
    authority: str = ''
    estates: list = field(default_factory=list)


@dataclass
class ReviewedSource:
    profile: SourceTrustProfile
    entry_points: list
    max_item_pages: int = 8

    @property
    def domain(self) -> str:
        return bare_host(self.profile.domain)

    def review_record(self) -> dict:
        p = self.profile
        return {'domain': self.domain, 'sourceClass': p.source_class, 'reviewStatus': p.review_status,
                'lastReviewed': p.last_reviewed, 'reviewedBy': p.reviewed_by, 'permittedRoles': list(p.permitted_roles)}

    def entry_points_for(self, authority: str, estates: list) -> list:
        own = {e.lower() for e in estates if e}
        return [e for e in self.entry_points
                if (e.authority and e.authority.lower() == (authority or '').lower())
                or any((s or '').lower() in own for s in e.estates)]


def load_reviewed_sources(path: str = DEFAULT_PROFILE_PATH) -> tuple:
    """({domain: ReviewedSource}, [problems]). Only a REVIEWED, TRUSTED_SECONDARY profile with an
    `ingestion` block whose listings are all on its own domain is readable; anything else is reported
    and left out whole -- a review that is wrong in one place is not half-applied."""
    try:
        with io.open(path, encoding='utf-8') as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        return {}, [{'domain': '', 'problems': [f'the registry could not be read: {exc}']}]
    sources, problems = {}, []
    for raw in data.get('profiles') or []:
        if not isinstance(raw, dict):
            continue
        reg = TrustRegistry([raw])
        if reg.rejected:
            problems.extend(reg.rejected)
            continue
        profile = reg.profiles[0]
        ingestion = raw.get('ingestion')
        if not ingestion:
            continue                       # trusted for classification only: nothing to read
        why = []
        if profile.review_status != 'REVIEWED':
            why.append(f'review status is {profile.review_status}; only a REVIEWED source is read')
        if profile.source_class != SourceClass.TRUSTED_SECONDARY.value:
            why.append(f'class is {profile.source_class}; only a TRUSTED_SECONDARY source is read')
        entry_points = []
        for e in ingestion.get('entryPoints') or []:
            url = str((e or {}).get('url') or '')
            ok, reason = validate_url_syntax(url)
            if not ok:
                why.append(f'entry point {url!r} refused: {reason}')
                continue
            if not profile.matches(bare_host(url)):
                why.append(f'entry point {url} is not on {profile.domain}')
                continue
            lists = str(e.get('lists') or '')
            if lists not in DocKind._value2member_map_:
                why.append(f'entry point {url} lists an unknown role {lists!r}')
                continue
            entry_points.append(EntryPoint(url=url, lists=DocKind(lists), authority=str(e.get('authority') or ''),
                                           estates=[str(s) for s in (e.get('estates') or [])]))
        if not entry_points and not why:
            why.append('the ingestion block names no listing to read')
        if why:
            problems.append({'domain': profile.domain, 'problems': why})
            continue
        try:
            max_items = max(1, min(int(ingestion.get('maxItemPages', 8)), 25))
        except (TypeError, ValueError):
            max_items = 8
        sources[bare_host(profile.domain)] = ReviewedSource(profile=profile, entry_points=entry_points,
                                                            max_item_pages=max_items)
    return sources, problems


# ===================================================================== reading pages
class _TextParser(HTMLParser):
    """The text a reader sees: no scripts, no styles, no comments."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip += 1
        elif tag in ('br', 'p', 'div', 'li', 'tr', 'td', 'th', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'title'):
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip = max(0, self._skip - 1)
        elif tag in ('td', 'th'):
            self.parts.append(' ')

    def handle_data(self, data):
        if not self._skip:
            self.parts.append(data)


def visible_text(html: str) -> str:
    p = _TextParser()
    try:
        p.feed(html or '')
        p.close()
    except Exception:                                           # noqa: BLE001 - malformed HTML is data
        pass
    return '\n'.join(' '.join(line.split()) for line in ''.join(p.parts).split('\n') if line.strip())


@dataclass
class Table:
    heading: str
    rows: list                         # each a list of cell texts


class _TableParser(HTMLParser):
    """Tables as rows of cell text, each with the heading it sits under. Nested tables are read as
    their own tables; a comment (a portal's disabled duplicate) is not read at all."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list = []
        self._stack: list = []
        self._row: Optional[list] = None
        self._cell: Optional[list] = None
        self._heading = ''
        self._hbuf: Optional[list] = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip += 1
        elif self._skip:
            return
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'caption'):
            self._hbuf = []
        elif tag == 'table':
            self._stack.append(Table(heading=self._heading, rows=[]))
        elif tag == 'tr' and self._stack:
            self._row = []
        elif tag in ('td', 'th') and self._row is not None:
            self._cell = []

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip = max(0, self._skip - 1)
        elif self._skip:
            return
        elif tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'caption') and self._hbuf is not None:
            text = ' '.join(''.join(self._hbuf).split())
            if text:
                self._heading = text
            self._hbuf = None
        elif tag in ('td', 'th') and self._cell is not None and self._row is not None:
            self._row.append(' '.join(''.join(self._cell).split()))
            self._cell = None
        elif tag == 'tr' and self._row is not None and self._stack:
            if any(self._row):
                self._stack[-1].rows.append(self._row)
            self._row = None
        elif tag == 'table' and self._stack:
            self.tables.append(self._stack.pop())

    def handle_data(self, data):
        if self._skip:
            return
        if self._hbuf is not None:
            self._hbuf.append(data)
        if self._cell is not None:
            self._cell.append(data)


def read_tables(html: str) -> list:
    p = _TableParser()
    try:
        p.feed(html or '')
        p.close()
    except Exception:                                           # noqa: BLE001
        pass
    return p.tables


class _BlockParser(HTMLParser):
    """Listing blocks: a list (ul/ol) whose first item is a title and whose other items hold a small
    `Label : Value` table and a link -- how many portals lay out one paper. For each link inside a
    block: the block's title and its label/value pairs."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.records: list = []
        self._blocks: list = []
        self._li_buf: Optional[list] = None
        self._li_has_link = False
        self._row: Optional[list] = None
        self._cell: Optional[list] = None
        self._a: Optional[dict] = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip += 1
            return
        if self._skip:
            return
        if tag in ('ul', 'ol'):
            self._blocks.append({'title': '', 'fields': {}, 'links': []})
        elif tag == 'li' and self._blocks:
            self._li_buf, self._li_has_link = [], False
        elif tag == 'tr':
            self._row = []
        elif tag in ('td', 'th') and self._row is not None:
            self._cell = []
        elif tag == 'a':
            self._a = {'href': dict(attrs).get('href'), 'buf': []}
            self._li_has_link = True

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == 'a' and self._a is not None:
            a, self._a = self._a, None
            href = (a['href'] or '').strip()
            if self._blocks and href and not href.startswith(('#', 'javascript:', 'mailto:')):
                from urllib.parse import urljoin
                self._blocks[-1]['links'].append((urljoin(self.base, href), ' '.join(''.join(a['buf']).split())))
        elif tag in ('td', 'th') and self._cell is not None and self._row is not None:
            self._row.append(' '.join(''.join(self._cell).split()))
            self._cell = None
        elif tag == 'tr' and self._row is not None:
            cells = [c for c in self._row if c and c != ':']
            if len(cells) == 2 and self._blocks:
                self._blocks[-1]['fields'][cells[0].rstrip(':').strip()] = cells[1]
            self._row = None
        elif tag == 'li' and self._li_buf is not None and self._blocks:
            text = ' '.join(''.join(self._li_buf).split())
            if text and not self._li_has_link and not self._blocks[-1]['title']:
                self._blocks[-1]['title'] = text
            self._li_buf = None
        elif tag in ('ul', 'ol') and self._blocks:
            block = self._blocks.pop()
            for url, text in block['links']:
                self.records.append({'url': url, 'text': text, 'title': block['title'], 'fields': dict(block['fields'])})

    def handle_data(self, data):
        if self._skip:
            return
        if self._a is not None:
            self._a['buf'].append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._li_buf is not None:
            self._li_buf.append(data)


def read_blocks(html: str, base_url: str) -> dict:
    p = _BlockParser(base_url)
    try:
        p.feed(html or '')
        p.close()
    except Exception:                                           # noqa: BLE001
        pass
    return {normalize_url(r['url']): r for r in p.records if r['title']}


# ===================================================================== identity
_ROMAN = {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}
#: "Group 1", "Group1", "Gp-2": how portals write a service group. Never "Gr-1" or "Gr.II", which are
#: grades of a post ("Hostel Welfare Officer Gr-1"), not a recruitment.
_GROUP_NUMBER = re.compile(r'\b(group|gp)[\s.-]*([1-4])(?!\d)', re.I)


def designation_text(text: str) -> str:
    """The text with a service group's number written as authorities write it (Group-I), so the
    existing gate -- which reads "Group-I" -- can judge a portal's "Group 1"."""
    return _GROUP_NUMBER.sub(lambda m: f'Group-{_ROMAN[m.group(2)]}', text or '')


def sibling_designations(words: list) -> list:
    """For an exam named by a service group, the other groups: the words that mark a sibling."""
    own = {m.group(1).lower() for w in words for m in [re.fullmatch(r'group ([ivx]+)', w)] if m}
    if not own:
        return []
    return [f'group {r.lower()}' for r in _ROMAN.values() if r.lower() not in own]


def relation_of(text: str, *, words: list, siblings: list, cycle: str) -> tuple:
    """(relation, cycle it names) for one item, judged by the existing gate on its own words."""
    t = designation_text(text)
    rel, _matched, foreign = gate(t, '', exam_words=words, page_is_exam_specific=False, sibling_exam_words=siblings)
    item_cycle = identity_from_text(t, exam_id='').cycle
    if rel is not Relevance.REJECTED and words:
        if not item_cycle:
            return 'THIS_EXAM_CYCLE_UNSTATED', ''
        return ('THIS_EXAM' if not cycle or item_cycle == cycle else 'THIS_EXAM_OTHER_CYCLE'), item_cycle
    return ('OTHER_EXAM' if foreign else 'NOT_THIS_EXAM'), item_cycle


# ===================================================================== dates and counts
_MONTHS = {m: i for i, m in enumerate(['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august',
                                       'september', 'october', 'november', 'december'], 1)}
_MON = r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
_ORD = r'(?:st|nd|rd|th)?'
_SEP = r'\s*(?:to|-|–|—)\s*'


def _month(name: str) -> int:
    name = name.lower()
    return next(i for m, i in _MONTHS.items() if m.startswith(name[:3]))


def _iso(y, m, d) -> Optional[str]:
    try:
        y, m, d = int(y), int(m), int(d)
    except (TypeError, ValueError):
        return None
    if not (1900 < y < 2100 and 1 <= m <= 12 and 1 <= d <= 31):
        return None
    return f'{y:04d}-{m:02d}-{d:02d}'


_NUMERIC = r'(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})'
_WHEN_PATTERNS = [
    ('RANGE', re.compile(rf'{_NUMERIC}{_SEP}{_NUMERIC}', re.I),
     lambda g: (_iso(g[2], g[1], g[0]), _iso(g[5], g[4], g[3]))),
    ('RANGE', re.compile(rf'(\d{{1,2}}){_ORD}\s+{_MON}{_SEP}(\d{{1,2}}){_ORD}\s+{_MON},?\s+(\d{{4}})', re.I),
     lambda g: (_iso(g[4], _month(g[1]), g[0]), _iso(g[4], _month(g[3]), g[2]))),
    ('RANGE', re.compile(rf'(\d{{1,2}}){_ORD}{_SEP}(\d{{1,2}}){_ORD}\s+{_MON},?\s+(\d{{4}})', re.I),
     lambda g: (_iso(g[3], _month(g[2]), g[0]), _iso(g[3], _month(g[2]), g[1]))),
    ('DAY', re.compile(_NUMERIC, re.I), lambda g: (_iso(g[2], g[1], g[0]), None)),
    ('DAY', re.compile(rf'{_MON}\s+(\d{{1,2}}){_ORD},?\s+(\d{{4}})', re.I), lambda g: (_iso(g[2], _month(g[0]), g[1]), None)),
    ('DAY', re.compile(rf'(\d{{1,2}}){_ORD}\s+{_MON},?\s+(\d{{4}})', re.I), lambda g: (_iso(g[2], _month(g[1]), g[0]), None)),
    ('MONTHS', re.compile(rf'{_MON}\s*/\s*{_MON},?\s+(\d{{4}})', re.I),
     lambda g: (f'{int(g[2]):04d}-{_month(g[0]):02d}/{int(g[2]):04d}-{_month(g[1]):02d}', None)),
    ('MONTHS', re.compile(rf'{_MON},?\s+(\d{{4}})', re.I), lambda g: (f'{int(g[1]):04d}-{_month(g[0]):02d}', None)),
]


def parse_when(text: str) -> Optional[dict]:
    """A date as a value cell states it, or None. The whole cell must be the date: a cell that says
    more than a date is not read as one."""
    t = ' '.join((text or '').replace(',', ', ').split()).strip(' .')
    for kind, pattern, build in _WHEN_PATTERNS:
        m = pattern.fullmatch(t)
        if not m:
            continue
        try:
            start, end = build(m.groups())
        except StopIteration:
            continue
        if not start:
            continue
        if kind == 'RANGE' and not end:
            continue
        return {'kind': kind, 'start': start, 'end': end}
    return None


def _count(text: str) -> Optional[int]:
    t = (text or '').strip()
    return int(t.replace(',', '')) if re.fullmatch(r'\d{1,3}(?:,\d{3})+|\d{1,6}', t) else None


# ===================================================================== fields
#: A table row's label -> (field, kind). Generic recruitment vocabulary, not one portal's.
_ROW_FIELDS = [
    ('vacancies_total', re.compile(r'(total\s+)?(no\.?\s+of\s+)?(vacanc(y|ies)|posts)|total', re.I), 'COUNT'),
    ('notification_date', re.compile(r'(date\s+of\s+)?notification(\s+(release|issue)\s+date|\s+date)?', re.I), 'DAY'),
    ('application_open', re.compile(r'(online\s+)?application\s+(start|starting|opening)(\s+date)?|apply\s+online\s+start(s)?', re.I), 'DAY'),
    ('application_close', re.compile(r'(online\s+)?application\s+(last|end|closing)\s+date|last\s+date\s+(to|for)\s+apply', re.I), 'DAY'),
    ('edit_window', re.compile(r'edit(ing)?\s+(of\s+)?application(\s+form)?|application\s+(edit|correction)(\s+window)?|edit\s+option', re.I), 'SPAN'),
    ('exam_stage_1', re.compile(r'prelim(inary|s)?\s+(exam(ination)?|test)(\s+date)?', re.I), 'SPAN'),
    ('exam_stage_2', re.compile(r'mains?\s+(exam(ination)?|test)(\s+date)?', re.I), 'SPAN'),
    ('result_release', re.compile(r'.*\bresults?(\s+\d{4})?\s+(release\s+)?date|date\s+of\s+results?', re.I), 'DAY'),
]

#: The official record's date types -> the same fields.
_OFFICIAL_TYPES = {'NOTIFICATION': 'notification_date', 'APPLICATION_OPEN': 'application_open',
                   'APPLICATION_CLOSE': 'application_close', 'RESULT': 'result_release',
                   'EXAM_TIER1': 'exam_stage_1', 'EXAM_TIER2': 'exam_stage_2'}

FIELD_LABELS = {
    'vacancies_total': 'Total vacancies', 'notification_date': 'Notification date',
    'application_open': 'Applications open', 'application_close': 'Last date to apply',
    'edit_window_start': 'Application edit window opens', 'edit_window_end': 'Application edit window closes',
    'exam_stage_1_start': 'Preliminary examination begins', 'exam_stage_1_end': 'Preliminary examination ends',
    'exam_stage_1_months': 'Preliminary examination (month)', 'exam_stage_2_start': 'Main examination begins',
    'exam_stage_2_end': 'Main examination ends', 'exam_stage_2_months': 'Main examination (month)',
    'result_release': 'Result released',
}


def _span_values(field_name: str, when: dict) -> list:
    """(field, value) pairs for a span: a range gives its start and end, one day its start only (an
    exam "on 21 October" does not say it ends that day), a month gives its months."""
    if when['kind'] == 'RANGE':
        return [(f'{field_name}_start', when['start']), (f'{field_name}_end', when['end'])]
    if when['kind'] == 'DAY':
        return [(f'{field_name}_start', when['start'])]
    return [(f'{field_name}_months', when['start'])]


def _row_field(label: str) -> Optional[tuple]:
    for name, pattern, kind in _ROW_FIELDS:
        if pattern.fullmatch(label.strip(' :')):
            return name, kind
    return None


# ===================================================================== the run
@dataclass
class SecondaryIngestion:
    source: str
    review: dict
    exam_id: str
    exam_title: str
    authority: str
    cycle: str
    started_at: str = field(default_factory=now_iso)
    ended_at: str = ''
    listings: list = field(default_factory=list)
    resources: list = field(default_factory=list)
    claims: list = field(default_factory=list)
    resolutions: list = field(default_factory=list)
    #: Links from the source to the authority's own site: leads for official discovery, never official here.
    pointers: list = field(default_factory=list)
    refused: list = field(default_factory=list)
    unexplored: list = field(default_factory=list)
    notes: list = field(default_factory=list)

    def counts(self) -> dict:
        by_state: dict = {}
        for r in self.resolutions:
            by_state[r['state']] = by_state.get(r['state'], 0) + 1
        return {'listingsRead': sum(1 for l in self.listings if l['ok']), 'resources': len(self.resources),
                'claims': len(self.claims), 'claimsCompared': sum(1 for c in self.claims if c['compared']),
                'resolutions': by_state, 'pointers': len(self.pointers), 'refused': len(self.refused),
                'unexplored': len(self.unexplored)}

    def as_dict(self) -> dict:
        return {'status': dict(STATUS), 'source': self.source, 'review': self.review, 'examId': self.exam_id,
                'examTitle': self.exam_title,
                'authority': self.authority, 'cycle': self.cycle, 'startedAt': self.started_at,
                'endedAt': self.ended_at, 'counts': self.counts(), 'listings': self.listings,
                'resources': self.resources, 'claims': self.claims, 'resolutions': self.resolutions,
                'pointers': self.pointers, 'refused': self.refused, 'unexplored': self.unexplored,
                'notes': self.notes}


class IngestionRefused(Exception):
    """The source may not be read for this exam (not reviewed for it, or not a secondary source)."""


def _hash(text: str) -> str:
    return hashlib.sha256((text or '').encode('utf-8')).hexdigest()[:24]


def ingest_secondary(source: ReviewedSource, exam: dict, *, fetch: Optional[Callable] = None,
                     registry: Optional[TrustRegistry] = None, official_listing: Optional[dict] = None,
                     max_item_pages: Optional[int] = None) -> SecondaryIngestion:
    """Read `source` for `exam` (a GovOS exam record: id, title, authorityName, officialDomain, cycle,
    dates, vacanciesTotal, factEvidence) and compare what it says with the record.

    `official_listing` is an optional `authority_discovery.project_for_exam` result for the same exam
    (a walk of the authority's own site): it lets "an answer key is listed" be checked against the
    authority's listings. `fetch` is injectable for tests and defaults to the SSRF-guarded fetcher.
    """
    fetch = fetch or (lambda url: fetch_checked(url, timeout=20, max_bytes=3_000_000))
    registry = registry if registry is not None else TrustRegistry([source.profile])
    authority = str(exam.get('authorityName') or '')
    domain_url = str(exam.get('officialDomain') or '')
    estates = [estate_of(bare_host(domain_url))] if domain_url else []
    cycle = str(exam.get('cycle') or '')
    title = str(exam.get('title') or '')
    out = SecondaryIngestion(source=source.domain, review=source.review_record(), exam_id=str(exam.get('id') or ''),
                             exam_title=title, authority=authority, cycle=cycle)

    # -- may this source be read for this exam at all? -----------------------------------------
    if any(same_estate(source.domain, e) for e in estates if e):
        raise IngestionRefused(f'{source.domain} is the authority\'s own site; it is read by authority discovery, '
                               f'never as a secondary source')
    if not source.profile.covers(authority, estates):
        raise IngestionRefused(f'the review of {source.domain} does not cover {authority or "this authority"}')
    entry_points = source.entry_points_for(authority, estates)
    if not entry_points:
        raise IngestionRefused(f'the review of {source.domain} names no listing for {authority or "this authority"}')

    words = exam_words_for(title, title, authority_name=authority, authority_domain=domain_url)
    siblings = sibling_designations(words)
    if not words:
        raise IngestionRefused('the exam has no word of its own to recognise its items by')

    def classify(url: str, role: DocKind) -> tuple:
        cls, why = classify_source(url, estates=estates, role=role, registry=registry, authority=authority)
        if cls is SourceClass.PRIMARY_OFFICIAL:      # defence in depth: never, for a secondary source's own page
            cls, why = SourceClass.SECONDARY, 'a secondary source is never official'
        return cls, why

    def get(url: str):
        result = fetch(url)
        final = getattr(result, 'final_url', '') or url
        if getattr(result, 'ok', False) and not source.profile.matches(bare_host(final)):
            return None, f'it redirected off {source.domain} (to {bare_host(final)}); not read'
        if not getattr(result, 'ok', False):
            return None, getattr(result, 'error', '') or f'HTTP {getattr(result, "status", 0)}'
        return result, ''

    # -- listings -----------------------------------------------------------------------------
    resources: dict = {}
    for ep in entry_points:
        result, why = get(ep.url)
        retrieved = now_iso()
        listing = {'url': ep.url, 'lists': ep.lists.value, 'ok': result is not None, 'retrievedAt': retrieved,
                   'contentHash': '', 'linksSeen': 0, 'itemsForThisExam': 0, 'otherItems': 0, 'note': why}
        out.listings.append(listing)
        if result is None:
            out.unexplored.append({'url': ep.url, 'why': f'the listing could not be read: {why}'})
            continue
        page = getattr(result, 'text', '') or ''
        listing['contentHash'] = getattr(result, 'content_hash', '') or _hash(page)
        pager = re.search(r'\b(\d+)\s*-\s*(\d+)\s+of\s+(\d+)\b', visible_text(page))
        if pager and int(pager.group(2)) < int(pager.group(3)):
            out.unexplored.append({'url': ep.url, 'why': f'the listing shows items {pager.group(1)}-{pager.group(2)} of '
                                                         f'{pager.group(3)}; the rest are behind its page buttons, '
                                                         f'which GovOS does not press'})
        blocks = read_blocks(page, ep.url)
        links, _ = extract_links(page, ep.url)
        listing['linksSeen'] = len(links)
        for link in links:
            if link.unlinked or not link.url:
                continue
            host = bare_host(link.url)
            if not source.profile.matches(host):
                if any(same_estate(host, e) for e in estates if e):
                    out.pointers.append({'url': link.url, 'text': link.text, 'foundOn': ep.url,
                                         'note': 'a pointer to the authority\'s own site: a lead for authority '
                                                 'discovery, never official because a secondary source links to it'})
                continue
            block = blocks.get(normalize_url(link.url))
            words_of = ' '.join(filter(None, [block['title'] if block else '',
                                             ' '.join(f'{k} {v}' for k, v in (block or {}).get('fields', {}).items()),
                                             '' if _THIN_LINK.match(link.text) else link.text]))
            if not words_of.strip():
                continue
            relation, item_cycle = relation_of(words_of, words=words, siblings=siblings, cycle=cycle)
            if relation in ('OTHER_EXAM', 'NOT_THIS_EXAM'):
                listing['otherItems'] += 1
                continue
            listing['itemsForThisExam'] += 1
            label = (block['title'] if block else '') or link.text
            role, _hint, role_reason, _ = classify_link(designation_text(label), link.url, context=link.context,
                                                        parent_role=ep.lists, parent_is_repository=True)
            if role is DocKind.UNKNOWN:
                role, role_reason = ep.lists, f'an item of the source\'s {ep.lists.value.lower().replace("_", " ")} listing'
            key = normalize_url(link.url)
            res = resources.get(key)
            if res is None:
                cls, class_reason = classify(link.url, role)
                res = resources[key] = {
                    'url': key, 'title': label, 'anchors': [], 'role': role.value, 'roleReason': role_reason,
                    'sourceClass': cls.value, 'sourceLabel': cls.candidate_label, 'classReason': class_reason,
                    'relation': relation, 'cycle': item_cycle, 'foundOn': [], 'fields': dict((block or {}).get('fields', {})),
                    'embeddedFile': _embedded_file(link.url), 'fetched': False, 'retrievedAt': '', 'contentHash': '',
                    'sourceDomain': source.domain, 'review': out.review}
            if link.text and link.text not in res['anchors']:
                res['anchors'].append(link.text)
            if ep.url not in res['foundOn']:
                res['foundOn'].append(ep.url)
            if res['relation'] != relation:
                # One page listed under two cycles (a portal's evergreen page): its cycle is whatever
                # the page itself says, judged when it is read.
                res['relation'], res['cycle'] = 'THIS_EXAM_CYCLE_UNSTATED', ''
            # The words it was listed under are themselves the source's statement that it exists.
            if role in _LISTED_ROLES and relation == 'THIS_EXAM':
                c = SourceClaim(field=f'listed:{role.value}', value='listed', source_url=ep.url,
                                source_class=SourceClass(res['sourceClass']), quotation=link.text if not _THIN_LINK.match(link.text) else label,
                                document_title=label, node_id=key)
                c.check_quotation(visible_text(page))
                out.claims.append(_claim_row(c, cycle=item_cycle, printed=label, origin='listing',
                                             row_label=ep.lists.value, compared=item_cycle == cycle and bool(cycle)))

    # -- item pages: read only this exam's, within the budget --------------------------------
    budget = max_item_pages or source.max_item_pages
    order = sorted(resources.values(), key=lambda r: (r['relation'] != 'THIS_EXAM', r['url']))
    seen_hashes: dict = {}
    for res in order:
        if res['relation'] not in ('THIS_EXAM', 'THIS_EXAM_CYCLE_UNSTATED'):
            continue
        if res['embeddedFile'] or res['url'].lower().split('?')[0].endswith('.pdf'):
            continue                   # a file viewer: recorded with its listing, its file is not read here
        if budget <= 0:
            out.unexplored.append({'url': res['url'], 'why': f'the page budget ({max_item_pages or source.max_item_pages}) was used'})
            continue
        budget -= 1
        result, why = get(res['url'])
        res['retrievedAt'] = now_iso()
        if result is None:
            res['note'] = f'could not be read: {why}'
            out.unexplored.append({'url': res['url'], 'why': why})
            continue
        page = getattr(result, 'text', '') or ''
        res['fetched'] = True
        res['contentHash'] = getattr(result, 'content_hash', '') or _hash(page)
        if res['contentHash'] in seen_hashes:
            res['duplicateOf'] = seen_hashes[res['contentHash']]
            continue
        seen_hashes[res['contentHash']] = res['url']
        _claims_from_page(out, res, page, words=words, siblings=siblings, cycle=cycle, estates=estates,
                          source=source)

    out.resources = sorted(resources.values(), key=lambda r: (r['relation'], r['role'], r['title']))
    _cross_check(out, exam, official_listing=official_listing)
    out.ended_at = now_iso()
    return out


def _embedded_file(url: str) -> str:
    """The file address a viewer link carries in its query (a portal's `DocUrl=`), as printed."""
    for key, values in parse_qs(urlparse(url).query).items():
        if key.lower() in ('docurl', 'qpurl', 'file', 'pdf') and values:
            return values[0]
    return ''


def _claim_row(c: SourceClaim, *, cycle: str, printed: str, origin: str, row_label: str, compared: bool,
               why_not: str = '') -> dict:
    row = c.as_dict()
    row.update({'publication': STATUS['publication'], 'availability': STATUS['availability'],
                'cycle': cycle, 'printed': printed, 'origin': origin, 'rowLabel': row_label, 'compared': compared,
                'whyNotCompared': '' if compared else (why_not or 'it is about another cycle, or does not say which')})
    row['_claim'] = c
    return row


#: A sentence stating a count of vacancies or posts.
_VACANCY_SENTENCE = re.compile(r'(\d{1,3}(?:,\d{3})+|\d{1,6})\s+(?:advertised\s+|administrative\s+)?(?:vacanc(?:y|ies)|posts)\b', re.I)


def _claims_from_page(out: SecondaryIngestion, res: dict, page: str, *, words, siblings, cycle, estates, source) -> None:
    text = visible_text(page)
    title_m = re.search(r'(?is)<title[^>]*>(.*?)</title>', page)
    page_title = ' '.join(_html.unescape(re.sub(r'<[^>]+>', ' ', title_m.group(1))).split()) if title_m else ''
    res['pageTitle'] = page_title
    rel, page_cycle = relation_of(page_title, words=words, siblings=siblings, cycle=cycle)
    if rel == 'OTHER_EXAM':
        res['note'] = 'its own title names another exam; nothing on it is read as this exam\'s'
        return
    if not page_cycle and res['relation'] == 'THIS_EXAM':
        page_cycle = res['cycle']
    res['pageCycle'] = page_cycle
    cls = SourceClass(res['sourceClass'])

    seen: set = set()

    def add(field_name, value, quotation, printed, origin, row_label, claim_cycle):
        key = (field_name, value, quotation)
        if key in seen:              # the same words read twice on one page are one statement
            return
        seen.add(key)
        c = SourceClaim(field=field_name, value=value, source_url=res['url'], source_class=cls, quotation=quotation,
                        document_title=page_title or res['title'], node_id=res['url'])
        c.check_quotation(text)
        compared = bool(cycle) and claim_cycle == cycle
        why = '' if compared else ('it is about another cycle' if claim_cycle else
                                   'neither the statement nor its page says which cycle it is about')
        out.claims.append(_claim_row(c, cycle=claim_cycle, printed=printed, origin=origin, row_label=row_label,
                                     compared=compared, why_not=why))

    # Pointers to the authority's own site, from the page itself.
    links, _ = extract_links(page, res['url'])
    for link in links:
        if link.url and any(same_estate(bare_host(link.url), e) for e in estates if e):
            out.pointers.append({'url': link.url, 'text': link.text, 'foundOn': res['url'],
                                 'note': 'a pointer to the authority\'s own site: a lead for authority discovery, '
                                         'never official because a secondary source links to it'})

    # Tables: a row "Label | Value" whose label names a field. A table under a heading naming another
    # exam is that exam's; one naming this exam's cycle (or none) takes the page's.
    for table in read_tables(page):
        heading_rel, heading_cycle = relation_of(table.heading, words=words, siblings=siblings, cycle=cycle)
        if heading_rel == 'OTHER_EXAM':
            continue
        table_cycle = heading_cycle or page_cycle
        stage_hint = ''
        for cells in table.rows:
            cells = [c for c in cells if c and c != ':']
            if len(cells) == 1:
                # A one-cell row is the table's own heading ("TSPSC Group 1 Vacancy 2024").
                sub_rel, sub_cycle = relation_of(cells[0], words=words, siblings=siblings, cycle=cycle)
                if sub_rel == 'OTHER_EXAM':
                    break
                table_cycle = sub_cycle or table_cycle
                continue
            if len(cells) != 2:
                continue
            label, value = cells
            if re.fullmatch(r'exam(ination)?\s+name', label.strip(' :'), re.I):
                named_rel, named_cycle = relation_of(value, words=words, siblings=siblings, cycle=cycle)
                if named_rel == 'OTHER_EXAM':
                    break                  # the table is about another exam
                table_cycle = named_cycle or table_cycle
                stage_hint = 'exam_stage_1' if re.search(r'prelim', value, re.I) else (
                    'exam_stage_2' if re.search(r'\bmains?\b', value, re.I) else '')
                continue
            hit = _row_field(label)
            if hit is None and re.fullmatch(r'exam(ination)?\s+dates?', label.strip(' :'), re.I) and stage_hint:
                hit = (stage_hint, 'SPAN')
            if hit is None:
                continue
            name, kind = hit
            quotation = f'{label} {value}'
            if kind == 'COUNT':
                n = _count(value)
                if n is not None:
                    add(name, str(n), quotation, value, 'table', label, table_cycle)
                continue
            when = parse_when(value)
            if when is None:
                continue
            if kind == 'DAY' and when['kind'] == 'DAY':
                add(name, when['start'], quotation, value, 'table', label, table_cycle)
            elif kind == 'SPAN':
                for f, v in _span_values(name, when):
                    add(f, v, quotation, value, 'table', label, table_cycle)

    # Sentences that state a count of vacancies, and name this exam. The number is read after the
    # group is written as a designation, so "Group 1 Vacancy" and "Group 1 posts" state no count.
    for sentence in re.split(r'(?<=[.!?])\s+|\n', text):
        m = _VACANCY_SENTENCE.search(designation_text(sentence))
        if not m or re.fullmatch(r'(19|20)\d\d', m.group(1)):
            continue
        rel, sentence_cycle = relation_of(sentence, words=words, siblings=siblings, cycle=cycle)
        if rel not in ('THIS_EXAM', 'THIS_EXAM_CYCLE_UNSTATED', 'THIS_EXAM_OTHER_CYCLE'):
            continue
        quotation = sentence.strip()[:300]
        add('vacancies_total', str(int(m.group(1).replace(',', ''))), quotation, m.group(0), 'sentence', '',
            sentence_cycle or page_cycle)


# ===================================================================== the official side
def official_claims(exam: dict) -> tuple:
    """(claims, superseded) from the official record. Only statements the record holds as
    OFFICIALLY_VERIFIED with the words they were read from and the document they are in -- the record
    passed the publication gate with those words verified verbatim, so they are taken as verified
    here. Superseded statements are kept apart: a source repeating one is told so, never believed."""
    claims, superseded = [], {}

    def take(field_name, value, prov, printed):
        quote = str((prov or {}).get('excerptText') or '')
        url = str((prov or {}).get('officialUrl') or '')
        level = (prov or {}).get('verificationLevel')
        if not (quote and url and value):
            return
        if level == 'SUPERSEDED':
            superseded.setdefault(field_name, []).append({'value': value, 'quotation': quote, 'url': url,
                                                          'printed': printed})
            return
        if level != 'OFFICIALLY_VERIFIED':
            return
        c = SourceClaim(field=field_name, value=value, source_url=url, source_class=SourceClass.PRIMARY_OFFICIAL,
                        quotation=quote, document_title=str(prov.get('documentTitle') or ''),
                        page=_page(prov.get('pageNumber')))
        c.quotation_status = EvidenceStatus.VERIFIED
        claims.append((c, printed))

    for d in exam.get('dates') or []:
        prov = d.get('provenance') or {}
        dtype = str(d.get('type') or '')
        printed = str(d.get('displayWhen') or d.get('dateTimeStr') or '')
        superseded_date = str(d.get('status') or '') == 'SUPERSEDED'
        if superseded_date:
            prov = dict(prov, verificationLevel='SUPERSEDED')
        if dtype == 'CORRECTION_WINDOW':
            label = str(d.get('label') or '').lower()
            name = 'edit_window_start' if 'open' in label else ('edit_window_end' if 'close' in label else '')
            day = str(d.get('dateTimeStr') or '')[:10]
            if name and re.fullmatch(r'\d{4}-\d{2}-\d{2}', day):
                take(name, day, prov, printed)
            continue
        name = _OFFICIAL_TYPES.get(dtype)
        if not name:
            continue
        if name.startswith('exam_stage_'):
            # The printed form first ("May/June 2024", "21/10/2024 to 27/10/2024"); a bare day otherwise.
            shown = str(d.get('displayWhen') or '')
            day = str(d.get('dateTimeStr') or '')[:10]
            when = parse_when(shown) if shown else (
                {'kind': 'DAY', 'start': day, 'end': None} if re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) else None)
            if not when:
                continue
            for f, v in _span_values(name, when):
                take(f, v, prov, printed)
            continue
        day = str(d.get('dateTimeStr') or '')[:10]
        if re.fullmatch(r'\d{4}-\d{2}-\d{2}', day) and not d.get('displayWhen'):
            take(name, day, prov, printed)
    vac = _count(str(exam.get('vacanciesTotal') or ''))        # records hold it as a number or a string
    if vac:
        take('vacancies_total', str(vac), (exam.get('factEvidence') or {}).get('vacanciesTotal'), str(vac))
    return claims, superseded


def _page(value) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _official_listed(exam: dict, official_listing: Optional[dict]) -> tuple:
    """Official statements that a document of a role exists for this exam: the authority's own
    listings (from a walk of its site) and the record's own declarations. Returns (claims, notes)."""
    claims, notes = [], {}
    for repo in (official_listing or {}).get('repositories') or []:
        for item in repo.get('items') or []:
            if item.get('relation') != 'THIS_EXAM' or item.get('role') not in {r.value for r in _LISTED_ROLES}:
                continue
            c = SourceClaim(field=f"listed:{item['role']}", value='listed', source_url=item['url'],
                            source_class=SourceClass.PRIMARY_OFFICIAL, quotation=item['title'],
                            document_title=repo.get('title') or '')
            c.quotation_status = EvidenceStatus.VERIFIED         # the walk read these words on the authority's listing
            claims.append(c)
    for decl in exam.get('resultDeclarations') or []:
        prov = decl.get('provenance') or {}
        if prov.get('verificationLevel') == 'OFFICIALLY_VERIFIED' and prov.get('excerptText') and prov.get('officialUrl'):
            c = SourceClaim(field='listed:RESULT', value='listed', source_url=prov['officialUrl'],
                            source_class=SourceClass.PRIMARY_OFFICIAL, quotation=prov['excerptText'],
                            document_title=str(prov.get('documentTitle') or ''))
            c.quotation_status = EvidenceStatus.VERIFIED
            claims.append(c)
            break
    for role, st in ((official_listing or {}).get('searchStates') or {}).items():
        notes[f'listed:{role}'] = f"GovOS's walk of the authority's site: {st.get('state', '').replace('_', ' ').lower()} — {st.get('reason', '')}"
    if official_listing is None:
        for role in _LISTED_ROLES:
            notes[f'listed:{role.value}'] = 'the authority\'s own listings were not walked for this comparison'
    return claims, notes


def _cross_check(out: SecondaryIngestion, exam: dict, *, official_listing: Optional[dict]) -> None:
    official, superseded = official_claims(exam)
    listed, listed_notes = _official_listed(exam, official_listing)
    by_field: dict = {}
    for c, printed in official:
        by_field.setdefault(c.field, []).append((c, printed))
    for c in listed:
        by_field.setdefault(c.field, []).append((c, 'listed'))
    compared = [row for row in out.claims if row['compared']]
    for field_name in sorted({row['field'] for row in compared}):
        secondary = [row['_claim'] for row in compared if row['field'] == field_name]
        officials = [c for c, _ in by_field.get(field_name, [])]
        resolution: ClaimResolution = reconcile(field_name, officials + secondary)
        row = resolution.as_dict()
        row['publication'], row['availability'] = STATUS['publication'], STATUS['availability']
        row['label'] = FIELD_LABELS.get(field_name, field_name.replace('_', ' ').replace(':', ': ').capitalize())
        row['officialPrinted'] = [p for _, p in by_field.get(field_name, [])]
        notes = []
        if resolution.state is Resolution.OFFICIAL_CONTESTED:
            for conflict in resolution.conflicts:
                old = [s for s in superseded.get(field_name, []) if s['value'] == conflict.value]
                if old:
                    notes.append(f'{conflict.source_url} states {conflict.value}, which is what the authority first '
                                 f'printed ("{old[0]["quotation"]}") before a later official statement replaced it: '
                                 f'the source has not caught up with the revision')
                else:
                    notes.append(f'{conflict.source_url} states {conflict.value}; the official record states '
                                 f'{resolution.value}. The official statement governs; the source\'s value is recorded, '
                                 f'not used. It may describe a different event than the one the record holds.')
        if resolution.state in (Resolution.SECONDARY_ONLY, Resolution.UNSUPPORTED) and field_name in listed_notes:
            notes.append(listed_notes[field_name])
        if resolution.state is Resolution.SECONDARY_ONLY:
            notes.append('Nothing official states this in what GovOS holds: it is the source\'s claim, kept as a lead '
                         'for official discovery, and is never shown as the authority\'s.')
        row['notes'] = notes
        out.resolutions.append(row)
    for row in out.claims:
        row.pop('_claim', None)
    not_compared = [r for r in out.claims if not r['compared']]
    if not_compared:
        out.notes.append(f'{len(not_compared)} claim(s) were not compared: they are about another cycle of the exam, '
                         f'or neither they nor their page say which cycle.')


# ===================================================================== command line
def _default_out(domain: str, exam_id: str) -> str:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(root, 'exam_data', 'secondary', f'{domain}__{exam_id}.json')


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description='Read one reviewed secondary source for one exam and compare it with '
                                             'the official record. Read-only: it writes only its JSON report.')
    ap.add_argument('--source', required=True, help='the reviewed source\'s domain, as in source_trust_profiles.json')
    ap.add_argument('--exam', required=True, help='a GovOS exam id (authored register or runtime registry)')
    ap.add_argument('--db', default='', help='the database to read the exam from (opened read-only); default govos.db')
    ap.add_argument('--walk', action='store_true', help='also walk the authority\'s own site (read-only) to check '
                                                         '"listed" claims against its listings')
    ap.add_argument('--max-items', type=int, default=0)
    ap.add_argument('--out', default='')
    args = ap.parse_args(argv)

    from ..claude_cli.context import ExamStore
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    exam = ExamStore(args.db or os.path.join(root, 'govos.db')).get(args.exam)
    if exam is None:
        print(f'no such exam: {args.exam}', file=sys.stderr)
        return 2
    sources, problems = load_reviewed_sources()
    for p in problems:
        print(f'registry: {p["domain"]}: {"; ".join(p["problems"])}', file=sys.stderr)
    source = sources.get(bare_host(args.source))
    if source is None:
        print(f'{args.source} is not a reviewed, readable secondary source in the registry', file=sys.stderr)
        return 2
    listing = None
    if args.walk:
        from .authority_discovery import discover_authority, project_for_exam
        run = discover_authority([exam['officialDomain']], authority_name=exam.get('authorityName', ''))
        listing = project_for_exam(run, exam_id=exam['id'], title=exam.get('title', ''),
                                   authority_name=exam.get('authorityName', ''),
                                   authority_domain=exam.get('officialDomain', ''), cycle=str(exam.get('cycle') or ''))
    try:
        result = ingest_secondary(source, exam, official_listing=listing, max_item_pages=args.max_items or None)
    except IngestionRefused as exc:
        print(f'refused: {exc}', file=sys.stderr)
        return 3
    out_path = args.out or _default_out(source.domain, args.exam)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with io.open(out_path, 'w', encoding='utf-8') as fh:
        json.dump(result.as_dict(), fh, ensure_ascii=False, indent=1)
    print(f"status: {STATUS['sourceClass']} / {STATUS['availability']} / {STATUS['publication']} -- {STATUS['note']}")
    print(json.dumps(result.counts(), indent=1))
    for r in result.resolutions:
        print(f"{r['state']:22} {r['label']:38} official={r['value']!s:24} "
              f"secondary={','.join(sorted({c['value'] for c in r['corroborations'] + r['agreeingUnreviewed'] + r['conflicts'] + r['secondary']}))}")
    print('report:', out_path)
    return 0


if __name__ == '__main__':
    sys.exit(main())
