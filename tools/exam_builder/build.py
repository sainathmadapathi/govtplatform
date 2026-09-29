"""resolve -> discover -> contract -> extract, for one exam and only that exam.

This is the orchestrator the single command drives. It holds no knowledge of any authority:
the resolver finds who publishes, discovery finds what they published for this exam, the
contract says what GovOS wants to know and which document kinds could answer it, and the
extractors read whatever was actually found.

The contract is consulted *before* extraction runs, which is what keeps two very different
statements apart — "the authority published nothing that could answer this" (NO_SOURCE) and
"we read the document and our pattern missed it" (NOT_EXTRACTED).
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass, field as dc_field
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlparse

from ..exam_authoring import extract as X
from ..exam_authoring.record import Citation, ExamRecord, Field, Status as RecordStatus
from ..exam_authoring.sources import FetchError, load_document, load_html, load_pdf, same_estate
from . import admit_card as D_ADMIT
from . import application as D_APPLICATION
from . import compat as COMPAT
from . import corrigenda as D_CORRIGENDA
from . import dates as D_DATES
from . import eligibility as D_ELIGIBILITY
from . import pattern as D_PATTERN
from . import pyq as D_PYQ
from . import results as D_RESULTS
from . import syllabus as D_SYLLABUS
from .completeness import CompletenessState, ExamCompletenessReport, evaluate_completeness
from .contract import CONTRACT, Coverage, coverage_from
from .discover import DiscoveredDoc, DocKind, Relevance, SourceSet, classify_kind, discover, exam_aliases
from .gate import BuildState
from .identity import ExamIdentity, IdentityCheck, IdentityVerdict, field_is_attributable, verify as verify_identity
from .manifest import SourceManifest, content_hash, from_source_set, to_source_set
from .resolve import Authority, ResolvedExam, resolve, stable_exam_id
from .evidence import normalise_ws
from .schema import SourceDocument, SourceKind, Status as SchemaStatus


def _today() -> str:
    return time.strftime('%Y-%m-%d')


@dataclass
class BuildResult:
    resolved: ResolvedExam
    sources: SourceSet
    coverage: Coverage
    record: ExamRecord
    notes: list[str] = dc_field(default_factory=list)
    #: Whether the build itself completed, separately from any field's status.
    build_state: BuildState = BuildState.COMPLETE
    #: url -> what the document's own text says it is about.
    identity: dict[str, IdentityCheck] = dc_field(default_factory=dict)
    #: The discovery snapshot for this build, capturable for a deterministic rebuild.
    manifest: SourceManifest | None = None
    #: Sources whose bytes differ from the manifest that named them.
    changed_sources: list[str] = dc_field(default_factory=list)
    #: Semantic 17-section completeness evaluation with failure-state separation.
    completeness: ExamCompletenessReport | None = None
    #: What the completeness evaluation was told, kept so it can be re-run after a review.
    reacquisition_attempts: int = 0
    searched_not_found: frozenset = frozenset()


def _load(doc: DiscoveredDoc):
    """Fetch a discovered document as something the extractors can read.

    The address decides only when it is explicit; otherwise the bytes do, because a PDF
    served from an extension-less viewer route is still a PDF.
    """
    if doc.is_pdf:
        return load_pdf(doc.url)
    return load_document(doc.url)


def _load_order(docs: list[DiscoveredDoc]) -> list[DiscoveredDoc]:
    """Most exam-specific first: a link that names this exam by more of its aliases (a
    compound one such as "group i" counts double, since it is what tells siblings apart),
    DIRECT before INHERITED, a document of a known kind before an unclassified page. Stable,
    so crawl order still decides between equals."""
    def key(d: DiscoveredDoc):
        specificity = sum(2 if ' ' in m else 1 for m in (d.matched or []))
        return (-specificity,
                0 if d.relevance is Relevance.DIRECT else 1,
                1 if d.kind is DocKind.UNKNOWN else 0)
    return sorted(docs, key=key)


def _reclassify_from_content(doc: DiscoveredDoc, document, rec: ExamRecord) -> None:
    """A document whose link said nothing about its kind is classified by its own opening.

    A listing row reads "02/2024 - GROUP-I SERVICES" and links a file whose first line is
    "NOTIFICATION NO. 02/2024" -- the document knows what it is even when the link did not.
    Only an UNKNOWN kind is ever changed, and the change is logged.
    """
    if doc.kind is not DocKind.UNKNOWN:
        return
    text = document.all_text() if hasattr(document, 'all_text') else ''
    head = ' '.join((text or '').split())[:600]
    kind = classify_kind(head, '')
    if kind is not DocKind.UNKNOWN:
        rec.note(f'{doc.url} classified as {kind.value} from its own opening text')
        doc.kind = kind


#: A discovered document's kind as the reconciler ranks it.
_SOURCE_KIND = {
    DocKind.EXAM_PAGE: SourceKind.EXAM_PAGE,
    DocKind.NOTIFICATION: SourceKind.NOTIFICATION,
    DocKind.CORRIGENDUM: SourceKind.CORRIGENDUM,
    DocKind.RESULT: SourceKind.RESULT,
    DocKind.ADMIT_CARD: SourceKind.ADMIT_CARD_NOTICE,
    DocKind.APPLICATION_PORTAL: SourceKind.APPLICATION_PAGE,
}


def record_official_sources(rec: ExamRecord, sources: SourceSet, loaded: dict,
                            identity: dict) -> int:
    """Every document read whose own text identified it as this exam, with its title.

    The contract names this field ("every document this record was read from") but only the
    bare URLs were kept, so a notice that fed only the timeline -- a medical-board schedule,
    a vacancy break-up -- never reached the candidate's library. Only a MATCH is listed: a
    page that merely mentions this exam among others is not this exam's document.
    """
    items = []
    for doc in sources.docs:
        check = identity.get(doc.url)
        if doc.url not in loaded or check is None or check.verdict is not IdentityVerdict.MATCH:
            continue
        items.append({'url': doc.url, 'title': normalise_ws(doc.title or '')[:220],
                      'kind': doc.kind.value, 'identity': check.verdict.value})
    if not items:
        return 0
    cite = Citation(document_title=f'{rec.authority_name} — documents read for this exam',
                    url=rec.official_domain, page=1, clause='Official sources',
                    excerpt='; '.join(i['title'] for i in items[:6])[:400],
                    verified_date=_today())
    rec.set(Field.found('officialSources', items, cite))
    return len(items)


def record_vacancy_breakups(rec: ExamRecord, sources: SourceSet, loaded: dict,
                            identity: dict) -> int:
    """Vacancy break-ups printed as ruled tables in this exam's own PDFs, tied to its posts.

    A break-up table flattens to a run of numbers whose column cannot be told once one cell is
    blank or carries a marker, so the flattened-text post reader never publishes one. The
    ruled-table reader reads the drawn grid instead, and a table is attached only when its own
    printed totals reconcile and every row joins one post (see `vacancy_breakup.attach`).
    Returns the number of tables recorded.
    """
    from . import vacancy_breakup as VB
    posts = rec.value('posts')
    if not isinstance(posts, list) or not posts:
        return 0
    found = []
    for doc in sources.docs:
        document = loaded.get(doc.url)
        check = identity.get(doc.url)
        if (document is None or getattr(document, 'kind', '') != 'PDF' or not getattr(document, 'raw', b'')
                or check is None or check.verdict is not IdentityVerdict.MATCH):
            continue
        try:
            tables, refused = VB.breakups_in(document.raw, posts)
        except Exception as exc:                      # noqa: BLE001 - recorded, not hidden
            rec.note(f'ruled-table reading failed on {doc.url}: {exc!r}')
            continue
        for why in refused:
            rec.note(f'vacancy table in {doc.url} not attached: {why}')
        for t in tables:
            t.update({'documentTitle': normalise_ws(doc.title or '')[:220], 'documentUrl': doc.url,
                      'documentKind': doc.kind.value})
            found.append(t)
    if not found:
        return 0
    first = found[0]
    cite = Citation(document_title=first['documentTitle'], url=first['documentUrl'],
                    page=first['pages'][0], clause='Vacancy break-up (ruled table)',
                    excerpt='; '.join(first['checks'])[:400], verified_date=_today())
    field = Field.found('vacancyBreakup', found, cite)
    field.note = ('read from the drawn grid of the authority\'s own table; each table reconciled '
                  'with its printed totals and every row joined one post')
    rec.set(field)
    return len(found)


#: A notice's own dateline, on a line of its own: "Dated: 23.06.2026". A body reference such as
#: "the Notice ... dated 21.05.2026 shall remain unchanged" names another document's date.
_DATELINE = re.compile(r'(?im)^\s*dated\s*[:\-–]\s*(\d{1,2})[./-](\d{1,2})[./-](\d{4})\s*$')


def _amending_notice(url: str, sources, loaded) -> tuple[bool, str]:
    """Is the document at `url` an amending notice, and the date it prints for itself ('' if none)."""
    doc = next((d for d in (getattr(sources, 'docs', None) or []) if d.url == url), None)
    if doc is None or doc.kind is not DocKind.CORRIGENDUM:
        return False, ''
    document = (loaded or {}).get(url)
    text = document.all_text() if hasattr(document, 'all_text') else ''
    lines = _DATELINE.findall(text or '')
    if len(lines) != 1:
        return True, ''                      # none, or several: not one date to state
    d, m, y = lines[0]
    return True, f'{y}-{int(m):02d}-{int(d):02d}'


def record_date_revisions(rec: ExamRecord, sources=None, loaded: dict | None = None) -> int:
    """Every superseded date becomes one entry in the exam's revision history, old to new.

    Reconciliation keeps a printed date that a later official statement replaced, struck
    through, and links it to the row that replaced it. That change is a revision whether or
    not the authority issued a separate corrigendum notice, and a candidate who remembers the
    printed date needs to see it was moved and by what. Each entry quotes both statements and
    names both documents; where no corrigendum notice exists, the entry says so rather than
    being titled as one. Returns the number of entries recorded.
    """
    dates = rec.get('dates')
    if not (dates and dates.usable and isinstance(dates.value, list)):
        return 0
    rows = [r for r in dates.value if isinstance(r, dict)]
    by_id = {r.get('id'): r for r in rows}
    # One change is one entry, however many times the notice printed the value it replaced
    # ("Applications From X To 14/03" and "Last Date … 14/03 at 5:00 PM" are one deadline).
    replaced: dict[str, list[dict]] = {}
    for row in rows:
        if row.get('status') == 'SUPERSEDED' and row.get('supersededBy') in by_id:
            replaced.setdefault(row['supersededBy'], []).append(row)
    entries: list[dict] = []
    for newer_id, olds in replaced.items():
        newer = by_id[newer_id]
        new_p = newer.get('provenance') or {}
        new_d = str(newer.get('dateTimeStr', ''))[:10]
        old_dates = sorted({str(r.get('dateTimeStr', ''))[:10] for r in olds})
        printed = ' '.join(
            f'Printed in "{(r.get("provenance") or {}).get("documentTitle", "")}": '
            f'"{(r.get("provenance") or {}).get("excerptText", "")}".' for r in olds)
        what = str(newer.get('type') or 'date').replace('_', ' ').lower()
        if what == 'other':
            # An untyped event is named by the notice's own label for it, not "Other".
            what = normalise_ws(str(olds[0].get('label') or 'date')).rstrip(' :-–').lower()[:80]
        amending, dated = _amending_notice(str(new_p.get('officialUrl') or ''), sources, loaded)
        if amending:
            # The later statement is itself a notice amending the schedule; say so, and give
            # the date it prints for itself only where it prints exactly one.
            note = ('Recorded from the authority’s own later notice amending the schedule'
                    + (f', dated {dated}.' if dated else ', which prints no date of its own.'))
        else:
            note = ('No separate corrigendum notice was found; the change is recorded from the '
                    'authority’s own later statement, which does not print the date it was made.')
        entries.append({
            'id': f'rev-{newer_id}',
            'title': f'{what.capitalize()} revised: {", ".join(old_dates)} → {new_d}',
            'sourceTitle': str(new_p.get('documentTitle') or ''),
            'publishedDate': dated,
            'effectiveDate': new_d,
            'evidenceSpan': (f'{printed} Stated later in "{new_p.get("documentTitle", "")}": '
                             f'"{new_p.get("excerptText", "")}".'),
            'sourceUrl': str(new_p.get('officialUrl') or ''),
            'oldSourceUrls': sorted({str((r.get('provenance') or {}).get('officialUrl') or '')
                                     for r in olds}),
            'status': 'ACTIVE',
            'affectedField': f'dates · {what}',
            'oldValue': ', '.join(old_dates),
            'newValue': new_d,
            'note': note,
        })
    if not entries:
        return 0
    existing = rec.get('corrigenda')
    if existing and existing.usable and isinstance(existing.value, list):
        known = {e.get('id') for e in existing.value if isinstance(e, dict)}
        existing.value.extend(e for e in entries if e['id'] not in known)
        return len(entries)
    cite = Citation(document_title=entries[0]['sourceTitle'], url=entries[0]['sourceUrl'], page=1,
                    clause='Revision recorded from a later official statement',
                    excerpt=entries[0]['evidenceSpan'][:400], verified_date=_today())
    field = Field.found('corrigenda', entries, cite)
    amended = any(e['note'].startswith('Recorded from the authority’s own later notice') for e in entries)
    field.note = ('revisions read from later official statements that replace a printed date; '
                  + ('the authority’s own amending notice is cited on each entry it made' if amended
                     else 'no corrigendum notice document was found for this exam'))
    rec.set(field)
    return len(entries)


def _listing_entry(document, target: ExamIdentity):
    """The part of a many-recruitment listing page that names this exam, or None.

    A commission lists every recruitment on one page ("02/2024 - GROUP-I SERVICES | Start
    Date: … End Date …"). The page as a whole names eighty examinations and vouches for none,
    yet its row for this one is the authority's own later word on that recruitment's window.
    Only rows whose own text identifies this exam are kept; every other row is dropped before
    any extractor sees the page. None when no row matches, or when every row does (then the
    page was never a listing).
    """
    from ..exam_authoring.sources import Document, html_rows
    if getattr(document, 'kind', '') != 'HTML' or not getattr(document, 'html', ''):
        return None
    rows = html_rows(document)
    # A service page lists the recruitments it serves as a drop-down, not a table: each
    # option is an entry like a row ("02/2024 - GROUP-I SERVICES" under "Select Notification").
    from html import unescape
    rows += [[normalise_ws(unescape(re.sub(r'<[^>]+>', ' ', o)))]
             for o in re.findall(r'<option\b[^>]*>(.*?)</option>', document.html, re.S | re.I)
             if o.strip()]
    own = [r for r in rows
           if verify_identity(' | '.join(r), target).verdict is IdentityVerdict.MATCH]
    if not own or len(own) == len(rows):
        return None
    entry = Document(url=document.url, kind='HTML', fetched_at=document.fetched_at,
                     raw=document.raw, text='\n'.join(' | '.join(r) for r in own))
    # No table markup: the entry is one recruitment's row, not a label/value table, and a
    # table reader would read its title cell as a label.
    entry.html = ''
    return entry


def _semantic_read(field_name: str, sources, loaded: dict, rec: ExamRecord,
                   identity: dict | None = None, target=None):
    """Try every loaded document for one field, semantically.

    The best-evidenced reading across documents wins; a document that does not state the
    field simply yields nothing, which is not an error.
    """
    from .evidence import EvidenceStatus
    from .semantic import SPEC_BY_NAME, extract

    if field_name not in SPEC_BY_NAME:
        return None

    best = None
    for doc in sources.docs:
        document = loaded.get(doc.url)
        if document is None:
            continue
        text = document.all_text() if hasattr(document, 'all_text') else ''
        if not text:
            continue
        got = extract(field_name, text, source_url=doc.url,
                      document_title=f'{rec.title} — {doc.kind.value.replace("_", " ").title()}',
                      page_of=lambda span, d=document: _page_of(d, span))
        if got is None:
            continue
        # A document naming several exams may still supply a fact, but only where the span
        # carrying that fact names this exam itself.
        check = (identity or {}).get(doc.url)
        if check is not None and check.verdict is IdentityVerdict.AMBIGUOUS:
            if target is None or not field_is_attributable(text, target, got.evidence.span):
                rec.note(f'{field_name}: evidence found in a multi-exam document but the '
                         f'span does not name this exam; not attributed ({doc.url})')
                continue
        if best is None or got.confidence > best[0].confidence:
            best = (got, doc)

    if best is None:
        return None
    got, doc = best
    cite = Citation(document_title=got.evidence.document_title, url=got.evidence.source_url,
                    page=got.evidence.page, clause=f'Read semantically ({field_name})',
                    excerpt=got.evidence.span, verified_date=_today())
    if got.confidence >= 0.66 and got.evidence.status is EvidenceStatus.VERIFIED:
        return Field.found(field_name, got.value, cite)
    return Field.needs_review(
        field_name, got.value,
        f'Read from the source and the evidence span was verified, but only '
        f'{len(got.cues_matched)} supporting cue(s) fired — confirm the reading.', cite)


def _page_of(document, span: str) -> int:
    """Which page a span sits on, so a citation can name it."""
    pages = getattr(document, 'pages', None) or []
    needle = ' '.join(span.split())[:60]
    for i, page in enumerate(pages, start=1):
        if needle and needle in ' '.join(page.split()):
            return i
    return 1


# ------------------------------------------------------------------ page placement
# The pattern and syllabus readers read a PDF as one joined text (`document.all_text()`), and
# their evidence is made with `page=1` (pattern._evidence), so every node used to cite page 1.
# The loaded document still holds its pages; these put each span back on the page it is printed
# on. A span found on one page takes that page; a span printed on several (a heading repeated
# in a scheme table and in the syllabus) takes the first of them at or after the previous
# node's page, since a reader returns its nodes in document order. A span found nowhere, or
# too short to place, keeps what the reader gave it.
def _span_pages(norm_pages: list, span: str) -> list:
    needle = re.sub(r'[^a-z0-9]', '', (span or '').lower())
    if len(needle) < 8:
        return []
    return [i for i, page in enumerate(norm_pages, start=1) if needle in page]


def _place_tree_pages(roots, document) -> Optional[int]:
    """Set each node's evidence page from the document's own pages; the first placed page."""
    from collections import Counter
    from dataclasses import fields as dc_fields
    from .schema import Fact as SchemaFact
    pages = getattr(document, 'pages', None) or []
    if len(pages) < 2:
        return None
    norm_pages = [re.sub(r'[^a-z0-9]', '', (p or '').lower()) for p in pages]
    ordered, owner, spans = [], [], []          # evidence in document order; its node; node -> [start, end)

    def walk(node):
        start = len(ordered)
        own = list(getattr(node, 'evidence', None) or [])
        for f in dc_fields(node):
            value = getattr(node, f.name, None)
            if isinstance(value, SchemaFact):
                own.extend(value.evidence or [])
        for ev in own:
            ordered.append(ev)
            owner.append(len(spans))
        me = len(spans)
        spans.append([start, None])
        for child in getattr(node, 'children', None) or []:
            walk(child)
        spans[me][1] = len(ordered)

    for root in roots or []:
        walk(root)
    candidates = [_span_pages(norm_pages, ev.span) for ev in ordered]
    unique = [c[0] for c in candidates if len(c) == 1]
    if not unique:
        return None
    cursor, first = min(unique), None
    for i, (ev, cands) in enumerate(zip(ordered, candidates)):
        if len(cands) == 1:
            ev.page = cands[0]
            cursor = max(cursor, cands[0])
        elif cands:
            # A repeated heading belongs where the rest of its own node is printed.
            start, end = spans[owner[i]]
            pool = Counter(c[0] for k, c in enumerate(candidates[start:end], start=start)
                           if k != i and len(c) == 1 and c[0] in cands)
            later = [p for p in cands if p >= cursor]
            if pool:
                ev.page = pool.most_common(1)[0][0]
            elif later:
                ev.page = cursor = later[0]
            else:
                # Printed only before the cursor: the nearest such page still prints it.
                ev.page = max(cands)
        else:
            continue
        first = first or ev.page
    return first


def _place_citation_page(got: Field, loaded: dict) -> Field:
    """A field citation made with page 1 takes the page its excerpt is printed on, where that
    is one page only; an excerpt printed on several pages is left for a person to place."""
    cite = got.citation if got else None
    if not cite or (cite.page not in (None, 1)) or not cite.url:
        return got
    document = loaded.get(cite.url)
    pages = getattr(document, 'pages', None) or []
    if len(pages) < 2:
        return got
    norm_pages = [re.sub(r'[^a-z0-9]', '', (p or '').lower()) for p in pages]
    hits = _span_pages(norm_pages, cite.excerpt)
    if len(hits) == 1:
        cite.page = hits[0]
    # Items read with their own span (a document, a fee component) carry their own page, which
    # materialize already prefers to the field's.
    if isinstance(got.value, list):
        for item in got.value:
            if isinstance(item, dict) and item.get('evidenceSpan') and not item.get('page'):
                item_hits = _span_pages(norm_pages, item['evidenceSpan'])
                if len(item_hits) == 1:
                    item['page'] = item_hits[0]
    return got


def _unread_by_us(name: str, docs, loaded: dict) -> Optional[Field]:
    """NOT_EXTRACTED when none of the documents offered for a field had readable text.

    A scanned notice with no text layer says nothing to this reader, so "the authority
    published none" would be a claim made out of GovOS's own gap. None when any text was read.
    """
    for doc in docs:
        document = loaded.get(doc.url)
        if document is not None and hasattr(document, 'all_text') and document.all_text().strip():
            return None
    what = (f'{len(docs)} document(s) were offered for {name} and none had a readable text layer '
            f'(scanned images)' if docs else
            # Nothing reached this reader: no document of a kind that states it, or none the
            # identity check could establish as this exam's own. Not a statement about scans.
            f'no document established as this exam\'s own was available to read for {name}')
    return Field(name=name, status=RecordStatus.NOT_EXTRACTED,
                 note=f'{what}; nothing could be read, which is a gap here, not a statement that the '
                      f'authority published none.')


def _extract_html_tables(html: str) -> list[list[list[str]]]:
    """Extracts tables from HTML with rows and cells."""
    table_rx = re.compile(r'<table[^>]*>(.*?)</table>', re.S | re.I)
    row_rx = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S | re.I)
    cell_rx = re.compile(r'<t[dh][^>]*>(.*?)</t[dh]>', re.S | re.I)
    tag_rx = re.compile(r'<[^>]+>')
    tables = []
    for tm in table_rx.finditer(html or ''):
        t_rows = []
        for rm in row_rx.finditer(tm.group(1)):
            cells = [' '.join(tag_rx.sub(' ', c).split()) for c in cell_rx.findall(rm.group(1))]
            cells = [c for c in cells if c != '']
            if cells:
                t_rows.append(cells)
        if t_rows:
            tables.append(t_rows)
    return tables


def _printed_relaxations(age_rules) -> list[dict]:
    """The age relaxations the notice itself printed, each with its figure and evidence.

    A plain printed figure is VERIFIED. A figure the notice qualifies ("up to 5 years based on
    service", "3 years & length of service") is kept as printed, NEEDS_REVIEW, with the
    qualification as its condition -- shown to the candidate, never added to a limit. A group
    whose relaxation is stated only in words is kept as a NEEDS_REVIEW textual rule with no
    figure. No figure is ever supplied from a national default."""
    from .schema import Status as _S
    out, seen = [], set()
    for rule in age_rules:
        post_ids = [ref.ref for ref in getattr(rule.scope, 'refs', [])
                    if getattr(ref.kind, 'value', '') == 'POST' and ref.ref]
        for rx in getattr(rule, 'relaxations', []) or []:
            if rx.years.status is _S.NOT_PUBLISHED:
                continue
            years = rx.years.value if rx.years.has_value and rx.years.status in (_S.VERIFIED, _S.NEEDS_REVIEW) else None
            maximum = (rx.absolute_maximum.value if rx.absolute_maximum.has_value
                       and rx.absolute_maximum.status in (_S.VERIFIED, _S.NEEDS_REVIEW) else None)
            fact = rx.years if (years is not None or not rx.absolute_maximum.has_value) else rx.absolute_maximum
            if not fact.evidence:
                continue
            key = (rx.category_label, years, maximum, tuple(post_ids))
            if key in seen:
                continue
            seen.add(key)
            verified = fact.status is _S.VERIFIED and (years is not None or maximum is not None)
            item = {'category': rx.category_label, 'status': 'VERIFIED' if verified else 'NEEDS_REVIEW',
                    'evidenceSpan': fact.evidence[0].span}
            if years is not None:
                item['years'] = float(years)
            if maximum is not None:
                item['maximumAge'] = float(maximum)
            if rx.conditions.has_value:
                item['condition'] = str(rx.conditions.value)
            elif years is None and maximum is None:
                item['condition'] = 'stated in words without a figure: ' + fact.evidence[0].span[:200]
            if len(post_ids) == 1:
                item['appliesToPostId'] = post_ids[0]
            out.append(item)
    return out


def _printed_amount(value) -> str:
    """A fee amount as the notice printed it: "100" for 100.0, "12.50" kept as "12.5"."""
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return str(int(number)) if number.is_integer() else repr(number)


def _post_item(p, document) -> dict:
    """One post as the record stores it: every fact its own table rows printed, each value
    from a verified span, and the span and page the post was read from."""
    import re as _re
    item = {'id': p.id, 'postName': p.name,
            'classification': p.classification.value if p.classification.has_value else '',
            'department': p.department.value if p.department.has_value else '',
            'payLevel': p.pay.value if p.pay.has_value else ''}
    if p.code:
        item['postCode'] = p.code
    counts = [v.count.value for v in p.vacancies if v.count.has_value]
    if len(counts) == 1:
        item['vacancies'] = int(counts[0])
    if p.age_band.has_value:
        m = _re.search(r'(\d{1,2})\s*(?:[-–—]|to)\s*(\d{1,2})', str(p.age_band.value))
        if m:
            item['minAge'], item['maxAge'] = int(m.group(1)), int(m.group(2))
    if p.qualification and p.qualification[0].requirement.has_value:
        item['qualification'] = str(p.qualification[0].requirement.value)
    physical = [str(f.value) for f in p.other_requirements if f.note == 'physical requirement']
    other = [str(f.value) for f in p.other_requirements if f.note != 'physical requirement']
    if physical:
        item['physicalRequirements'] = physical
    if other:
        item['conditions'] = other
    if p.evidence:
        item['evidenceSpan'] = p.evidence[0].span
        item['page'] = _page_of(document, p.evidence[0].span)
    if p.status is SchemaStatus.NEEDS_REVIEW:
        item['status'] = 'NEEDS_REVIEW'
    return item


def _post_name(item) -> str:
    if isinstance(item, dict):
        return str(item.get('postName') or item.get('name') or '').strip()
    return str(item or '').strip()


def _vet_posts(got: Field, rec: ExamRecord, loaded: dict | None = None) -> Field:
    """Every posts reading passes one test, whichever reader produced it.

    A checklist of documents to produce ("Hall Ticket", "Non-Creamy Layer Certificate")
    reconstructs exactly like a list of posts, and the semantic reader, the table reader and
    the legacy extractor have each returned one. The candidates are classified on their own
    words and on the text around the evidence in the cited document (a checklist's
    instructions against a post table's headers). Only POSTS and MIXED readings publish
    posts; DOCUMENTS and AMBIGUOUS readings are kept, with their evidence, as NEEDS_REVIEW --
    never published as posts and never discarded."""
    from .eligibility import classify_post_candidates

    if got is None or not got.usable or not isinstance(got.value, list):
        return got
    # The text *before* the list -- its heading and its instructions. The candidates' own
    # words are weighed separately, so they must not also count as their neighbourhood.
    context = ''
    document = (loaded or {}).get(got.citation.url) if got.citation else None
    text = document.all_text() if document is not None and hasattr(document, 'all_text') else ''
    if text and got.citation and got.citation.excerpt:
        flat = ' '.join(text.split())
        at = flat.find(' '.join(got.citation.excerpt.split())[:60])
        if at >= 0:
            context = flat[max(0, at - 600):at]
    verdict = classify_post_candidates([_post_name(x) for x in got.value], context=context)
    if verdict.kind in ('DOCUMENTS', 'AMBIGUOUS'):
        what = ('documents a candidate must produce, not posts' if verdict.kind == 'DOCUMENTS'
                else f'not separable into posts and documents with confidence '
                     f'({len(verdict.documents)} read as documents, {len(verdict.ambiguous)} undecided)')
        example = (verdict.documents or verdict.ambiguous or [''])[0]
        return Field.needs_review(
            'posts', got.value,
            f'the {len(got.value)} candidate(s) read here are {what} (e.g. "{example}"); '
            f'{"; ".join(verdict.reasons) or "judged on the candidates' own words"}. '
            f'Held for review with the evidence, not published as posts',
            got.citation)
    if not verdict.documents:
        return got
    kept = [x for x in got.value if normalise_ws(_post_name(x)) not in set(verdict.documents)]
    rec.note(f'posts: removed {len(verdict.documents)} document name(s) from the post list: '
             f'{", ".join(verdict.documents[:4])}')
    return Field(name='posts', status=got.status, value=kept, citation=got.citation, note=got.note)


def record_search_outcomes(rec: ExamRecord, searched: dict[str, str]) -> frozenset:
    """Record, for fields still without a reading, that the authority's own listings were
    searched for them and held nothing for this recruitment.

    `searched` maps a field to the listings that were searched, in words. A field that was
    NOT_PUBLISHED only because no document of its kind turned up, or NOT_EXTRACTED, becomes
    NOT_EXTRACTED with that search named: "we searched and did not find it" is a gap of ours,
    never a statement that the authority published nothing. A field with a reading is left
    alone. Returns the fields to report as SOURCE_NOT_FOUND_AFTER_SEARCH.
    """
    found: set[str] = set()
    for name, where in searched.items():
        f = rec.fields.get(name)
        if f is not None and f.status in (RecordStatus.FOUND, RecordStatus.NEEDS_REVIEW):
            continue
        if f is not None and f.status is RecordStatus.NOT_PUBLISHED and 'No document of kind' not in (f.note or ''):
            # A NOT_PUBLISHED established by the authority's own statement stands.
            continue
        rec.set(Field(name=name, status=RecordStatus.NOT_EXTRACTED,
                      note=(f'searched {where}; nothing for this recruitment was found there. '
                            f'This is not a statement that the authority never published it.')))
        found.add(name)
    return frozenset(found)


def enforce_semantic_states(rec: ExamRecord) -> list[str]:
    """A field's status must agree with what its value and evidence are, not only with
    whether a value exists. Applied after extraction, and to a stored record re-read offline.

      * posts FOUND whose candidates are documents (or cannot be told apart) -> NEEDS_REVIEW;
      * examPattern FOUND with no stage read with confidence -> NEEDS_REVIEW;
      * feeExemptions NOT_PUBLISHED while the fee's own evidence states an exemption ->
        NEEDS_REVIEW with that sentence, because "we did not structure it" is not "the
        authority published none".
    Returns what it changed, each also noted on the record."""
    from .eligibility import classify_post_candidates
    changed: list[str] = []
    posts = rec.fields.get('posts')
    if posts is not None and posts.status is RecordStatus.FOUND and isinstance(posts.value, list):
        verdict = classify_post_candidates([_post_name(x) for x in posts.value])
        if verdict.kind in ('DOCUMENTS', 'AMBIGUOUS'):
            rec.set(Field.needs_review('posts', posts.value,
                                       f'the candidates read as posts are {verdict.kind.lower()} '
                                       f'(e.g. "{(verdict.documents or verdict.ambiguous or [""])[0]}"); '
                                       f'held for review, not published as posts', posts.citation))
            changed.append(f'posts FOUND -> NEEDS_REVIEW ({verdict.kind})')
    pattern = rec.fields.get('examPattern')
    if pattern is not None and pattern.status is RecordStatus.FOUND and isinstance(pattern.value, list):
        # Only a tree that says what its roots are is judged: every root carries a level, and
        # none is a stage whose own status is verified. A reader that emits no level or status
        # (an HTML scheme table) has not claimed anything this check could contradict.
        roots = [n for n in pattern.value if isinstance(n, dict)]
        described = roots and all('level' in n and 'status' in n for n in roots)
        if described and not any(n['level'] == 'STAGE' and n['status'] == 'VERIFIED' for n in roots):
            rec.set(Field.needs_review('examPattern', pattern.value,
                                       'no root of the pattern tree is a stage read with confidence',
                                       pattern.citation))
            changed.append('examPattern FOUND -> NEEDS_REVIEW (no confident stage)')
    fee, exemptions = rec.fields.get('fee'), rec.fields.get('feeExemptions')
    if (exemptions is not None and exemptions.status is RecordStatus.NOT_PUBLISHED
            and fee is not None and fee.citation and fee.citation.excerpt):
        stated = D_APPLICATION.exemption_wording(fee.citation.excerpt)
        if stated:
            cite = Citation(document_title=fee.citation.document_title, url=fee.citation.url,
                            page=fee.citation.page, clause='Fee Exemptions', excerpt=stated[:400],
                            verified_date=fee.citation.verified_date)
            rec.set(Field.needs_review('feeExemptions',
                                       [{'category': '', 'isExempt': True, 'evidenceSpan': stated[:400],
                                         'status': 'NEEDS_REVIEW'}],
                                       "the fee's own evidence states an exemption; it was recorded as "
                                       'not published, which the evidence contradicts', cite))
            changed.append('feeExemptions NOT_PUBLISHED -> NEEDS_REVIEW (exemption in the fee evidence)')
    for c in changed:
        rec.note(f'semantic state: {c}')
    return changed


def _dispatch_domain_extraction(
    cf,
    sources: SourceSet,
    loaded: dict[str, object],
    rec: ExamRecord,
    resolved: ResolvedExam,
    identity: dict[str, IdentityCheck] | None = None,
    target: ExamIdentity | None = None
) -> Field:
    """Dispatch one contract field, then vet the reading where a generic test applies."""
    got = _dispatch_domain_extraction_raw(cf, sources, loaded, rec, resolved, identity, target)
    got = _place_citation_page(got, loaded)
    if cf.name == 'posts':
        got = _vet_posts(got, rec, loaded)
    if cf.name == 'fee':
        got = _type_fee_components(got, loaded, rec, resolved)
    return got


_FEE_TYPE_LABEL = {'APPLICATION_PROCESSING': 'Application processing fee',
                   'EXAMINATION': 'Examination fee', 'TOTAL': 'Total fee'}


def _type_fee_components(got: Field, loaded: dict, rec: ExamRecord, resolved) -> Field:
    """Which fee each printed amount is, read from the document the fee field cites.

    A notice that charges an application processing fee and a separate examination fee
    states two amounts with two names; a reading that keeps only "200" loses the second fee
    and the relationship between them. Only amounts the document itself names as a fee type
    are added, each with its own sentence as evidence -- nothing is summed, and a pay scale
    or a recounting charge the reader also saw is not promoted into the application fee.
    """
    if got is None or not got.usable or not isinstance(got.value, dict) or not got.citation:
        return got
    document = loaded.get(got.citation.url)
    text = document.all_text() if document is not None and hasattr(document, 'all_text') else ''
    if not text:
        return got
    src_doc = SourceDocument(id=got.citation.url, url=got.citation.url, kind=SourceKind.OTHER_OFFICIAL,
                             title=got.citation.document_title, authority=resolved.authority.name,
                             exam_id=rec.exam_id)
    try:
        rules = D_APPLICATION.extract_fees(src_doc, text)
    except Exception as exc:                      # noqa: BLE001 - reported, not hidden
        rec.note(f'fee components: extract_fees failed on {got.citation.url}: {exc!r}')
        return got
    components, seen = [], set()
    for r in rules:
        if not (r.fee_type and r.amount.has_value and r.amount.status is SchemaStatus.VERIFIED
                and r.scope.is_global and r.amount.evidence):
            continue
        key = (r.fee_type, float(r.amount.value))
        if key in seen:
            continue
        seen.add(key)
        components.append({'feeType': r.fee_type, 'label': _FEE_TYPE_LABEL.get(r.fee_type, r.fee_type),
                           'amount': float(r.amount.value), 'currency': r.currency or 'INR',
                           'evidenceSpan': r.amount.evidence[0].span})
    if not components:
        return got
    value = dict(got.value, components=components)
    rec.note(f'fee: {len(components)} named fee component(s) read from the cited document: '
             + ', '.join(f"{c['label']} {c['amount']:g}" for c in components))
    return Field(name='fee', status=got.status, value=value, citation=got.citation, note=got.note)


def _states_something(field_name: str, value) -> bool:
    """Does a semantic reading carry the substance of its field, or only a sentence near it?

    A pattern read as {"papers": [], "negativeMarking": "..."} names no stage and no paper:
    one sentence about wrong answers. Accepted, it pre-empted the scheme reader that builds
    the real stage and paper tree, and the section had nothing to show."""
    if field_name == 'examPattern' and isinstance(value, dict):
        return bool(value.get('papers'))
    return True


#: Fields whose facts belong to the authority rather than to one of its exams. A page that
#: names no examination (the portal, the photo-upload rules, the exam-day instructions, the
#: commission's FAQ) states them for every exam it conducts.
_AUTHORITY_WIDE = frozenset({'applicationPortal', 'howToApply', 'photoSignatureGuidelines',
                             'examDayChecklist', 'faqs'})


def _facts_view(field_name: str, loaded: dict, identity: dict | None) -> dict:
    """The documents a field's domain reader may take facts from."""
    if identity is None or field_name in _AUTHORITY_WIDE:
        return loaded
    return {url: doc for url, doc in loaded.items()
            if identity.get(url) is not None and identity[url].verdict is IdentityVerdict.MATCH}


def _dispatch_domain_extraction_raw(
    cf,
    sources: SourceSet,
    loaded: dict[str, object],
    rec: ExamRecord,
    resolved: ResolvedExam,
    identity: dict[str, IdentityCheck] | None = None,
    target: ExamIdentity | None = None
) -> Field:
    """Dispatches extraction of one contract field to the canonical domain reader or legacy extractor."""
    # A fact about this exam comes only from a document that identifies itself as this exam.
    # AMBIGUOUS is not a weak yes: an undated corrigendum that names no examination supplied
    # "application close revised to 20" to one exam from another's notice. An authority-wide
    # field (its portal, its photo rules) may still come from a page that names no exam.
    facts = _facts_view(cf.name, loaded, identity)
    candidate_docs = [d for d in sources.docs if d.kind in cf.sources and d.url in facts]

    # 1. Semantic read: reads verbatim fact from document text. Not for the age limits: the
    # semantic reader returns one band, and a notice that states its limits per post has no
    # single band -- the scope-aware domain reader below decides that, and only where it
    # finds nothing is the semantic reading used.
    got = None if cf.name == 'ageLimits' else _semantic_read(cf.name, sources, loaded, rec, identity, target)
    if got is not None and getattr(got, 'ok', False) and _states_something(cf.name, got.value):
        return got

    # 2. Domain-specific readers
    if cf.name == 'dates':
        # If HTML row table is present on exam page, check it
        for doc in candidate_docs:
            document = loaded[doc.url]
            if getattr(document, 'kind', '') == 'HTML':
                from ..exam_authoring.sources import html_rows
                try:
                    title = f'{rec.title} — {doc.kind.value.replace("_", " ").title()}'
                    got = X.dates_from_rows(document, html_rows(document), title)
                    # A table whose every date is unlabelled (OTHER) is not a timeline; taking
                    # it here would replace every milestone the other documents state.
                    if got is not None and got.ok and any(
                            d.get('type') != 'OTHER' for d in (got.value or [])):
                        return got
                except Exception as exc:
                    rec.note(f'dates_from_rows failed on {doc.url}: {exc!r}')

        # Next, milestones extraction + multi-document reconciliation
        groups = []
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            # The document's role travels with its dates: reconciliation lets an examination
            # page or a corrigendum outrank a printed notice, and cannot if every source is
            # labelled alike.
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=_SOURCE_KIND.get(
                                         doc.kind, SourceKind.OTHER_OFFICIAL),
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                ms = D_DATES.extract_milestones(src_doc, text, exam_id=rec.exam_id, cycle=resolved.year)
                if ms:
                    groups.append((src_doc, ms))
            except Exception as exc:
                rec.note(f'extract_milestones failed on {doc.url}: {exc!r}')

        if groups:
            reconciled = D_DATES.reconcile(groups)
            dates_list = COMPAT.important_dates(reconciled, exam_id=rec.exam_id)
            if dates_list:
                first_m = reconciled[0]
                ev = (first_m.ends_at.evidence[0] if first_m.ends_at.evidence
                      else (first_m.starts_at.evidence[0] if first_m.starts_at.evidence else None))
                excerpt = ev.span if ev else first_m.label
                doc_title = ev.document_title if ev else f"{rec.title} Timeline"
                url = ev.url if ev else resolved.authority.domain
                cite = Citation(document_title=doc_title, url=url, page=1, clause='Dates & Timeline',
                                excerpt=excerpt, verified_date=_today())
                return Field.found('dates', dates_list, cite)

        # Legacy prose fallback
        for doc in candidate_docs:
            document = loaded[doc.url]
            title = f'{rec.title} — {doc.kind.value.replace("_", " ").title()}'
            try:
                got = X.dates_from_notice(document, title)
                if got is not None and got.ok:
                    return got
            except Exception as exc:
                rec.note(f'dates_from_notice failed on {doc.url}: {exc!r}')

        return Field.not_extracted('dates', resolved.authority.domain, 'dates')

    elif cf.name == 'examPattern':
        for doc in candidate_docs:
            document = loaded[doc.url]
            html = getattr(document, 'html', '')
            if getattr(document, 'kind', '') == 'HTML' and html:
                tables = _extract_html_tables(html)
                pattern_headers = {'stage', 'tier', 'paper', 'scheme', 'marks'}
                for rows in tables:
                    if not rows:
                        continue
                    row_lower = [c.lower() for c in rows[0]]
                    if any(any(h == c or h in c for h in pattern_headers) for c in row_lower) and len(rows[0]) >= 2:
                        headers = row_lower
                        stage_col = next((idx for idx, c in enumerate(headers) if 'stage' in c or 'tier' in c), -1)
                        paper_col = next((idx for idx, c in enumerate(headers) if 'paper' in c or 'subject' in c), -1)
                        marks_col = next((idx for idx, c in enumerate(headers) if 'mark' in c), -1)
                        dur_col = next((idx for idx, c in enumerate(headers) if 'duration' in c or 'time' in c), -1)
                        html_stages = []
                        for idx, r in enumerate(rows[1:], start=1):
                            st_name = r[stage_col].strip() if stage_col >= 0 and len(r) > stage_col else f'Stage {idx}'
                            p_name = r[paper_col].strip() if paper_col >= 0 and len(r) > paper_col else ''
                            m_val = r[marks_col].strip() if marks_col >= 0 and len(r) > marks_col else ''
                            d_val = r[dur_col].strip() if dur_col >= 0 and len(r) > dur_col else ''
                            marks_num = int(re.search(r'\d+', m_val).group(0)) if re.search(r'\d+', m_val) else 100
                            html_stages.append({
                                'id': f'{rec.exam_id}-stage-{idx}',
                                'name': st_name,
                                'title': st_name,
                                'levelLabel': 'STAGE',
                                'totalMarks': marks_num,
                                'children': [{
                                    'id': f'{rec.exam_id}-paper-{idx}',
                                    'name': p_name or st_name,
                                    'title': p_name or st_name,
                                    'levelLabel': 'PAPER',
                                    'totalMarks': marks_num,
                                    'duration': d_val
                                }] if p_name else []
                            })
                        if html_stages:
                            cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Exam Pattern',
                                            excerpt=html_stages[0]['name'], verified_date=_today())
                            return Field.found('examPattern', html_stages, cite)

            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                pat = D_PATTERN.extract_pattern(src_doc, text, exam_id=rec.exam_id, cycle=resolved.year)
                if pat and pat.stages:
                    first_page = _place_tree_pages(pat.stages, document)
                    tree = COMPAT.pattern_tree(pat, exam_id=rec.exam_id)
                    if tree:
                        cite = Citation(document_title=doc.title, url=doc.url, page=first_page or 1,
                                        clause='Exam Pattern',
                                        excerpt=getattr(pat.stages[0], 'name', 'Pattern') or 'Scheme',
                                        verified_date=_today())
                        # FOUND means a stage was read. A tree whose roots are only headings
                        # or held rows is kept with its evidence, for a person to confirm.
                        if not any(s.level is D_PATTERN.PatternLevel.STAGE
                                   and s.status is SchemaStatus.VERIFIED for s in pat.stages):
                            return Field.needs_review(
                                'examPattern', tree,
                                'no stage of the examination was read with confidence: '
                                + '; '.join(f'"{s.name}" is a {s.level.value.lower()} '
                                            f'({s.status.value})' for s in pat.stages[:4]),
                                cite)
                        return Field.found('examPattern', tree, cite)
            except Exception as exc:
                rec.note(f'extract_pattern failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Exam Pattern'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('examPattern', resolved.authority.domain, 'examPattern')

    elif cf.name == 'syllabus':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                syl = D_SYLLABUS.extract_syllabus(src_doc, text, exam_id=rec.exam_id, cycle=resolved.year)
                if syl and syl.roots:
                    first_page = _place_tree_pages(syl.roots, document)
                    tree = COMPAT.syllabus_tree(syl, exam_id=rec.exam_id)
                    if tree:
                        cite = Citation(document_title=doc.title, url=doc.url, page=first_page or 1,
                                        clause='Syllabus', excerpt=syl.roots[0].title or 'Syllabus',
                                        verified_date=_today())
                        return Field.found('syllabus', tree, cite)
            except Exception as exc:
                rec.note(f'extract_syllabus failed on {doc.url}: {exc!r}')

        return Field.not_extracted('syllabus', resolved.authority.domain, 'syllabus')

    elif cf.name == 'posts':
        for doc in candidate_docs:
            document = loaded[doc.url]
            html = getattr(document, 'html', '')
            if getattr(document, 'kind', '') == 'HTML' and html:
                tables = _extract_html_tables(html)
                post_headers = {'post', 'service', 'designation', 'cadre', 'post name', 'name of post'}
                for rows in tables:
                    if not rows:
                        continue
                    row_lower = [c.lower() for c in rows[0]]
                    if any(any(h == c or h in c for h in post_headers) for c in row_lower) and len(rows[0]) >= 2:
                        headers = row_lower
                        name_col = next((idx for idx, c in enumerate(headers) if any(h in c for h in post_headers)), -1)
                        dept_col = next((idx for idx, c in enumerate(headers) if 'department' in c or 'ministry' in c), -1)
                        pay_col = next((idx for idx, c in enumerate(headers) if 'pay' in c or 'level' in c or 'scale' in c), -1)
                        html_posts = []
                        for r in rows[1:]:
                            if name_col >= 0 and len(r) > name_col and len(r[name_col].strip()) >= 3:
                                p_name = r[name_col].strip()
                                p_dept = r[dept_col].strip() if dept_col >= 0 and len(r) > dept_col else ''
                                p_pay = r[pay_col].strip() if pay_col >= 0 and len(r) > pay_col else ''
                                slug = re.sub(r'[^a-z0-9]+', '-', p_name.lower()).strip('-')[:40] or 'x'
                                html_posts.append({
                                    'id': f'post-{rec.exam_id}-{slug}',
                                    'postName': p_name,
                                    'department': p_dept,
                                    'payLevel': p_pay,
                                    'classification': ''
                                })
                        if html_posts:
                            cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Posts',
                                            excerpt=html_posts[0]['postName'], verified_date=_today())
                            return Field.found('posts', html_posts, cite)

            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                held: list = []
                posts = D_ELIGIBILITY.extract_posts(src_doc, text, exam_id=rec.exam_id, held=held)
                if posts:
                    D_ELIGIBILITY.post_code_clauses(
                        src_doc, text, posts,
                        heading=re.compile(r'physical\s+(?:requirements?|standards?)\s*:', re.I))
                    D_ELIGIBILITY.post_scoped_sentences(src_doc, text, posts)
                    posts_list = [_post_item(p, document) for p in posts]
                    ev = posts[0].evidence[0] if posts[0].evidence else None
                    excerpt = ev.span if ev else posts[0].name
                    cite = Citation(document_title=doc.title, url=doc.url,
                                    page=_page_of(document, excerpt), clause='Posts',
                                    excerpt=excerpt, verified_date=_today())
                    found = Field.found('posts', posts_list, cite)
                    if held:
                        # Listed posts whose rows print nothing but the name: said, not published.
                        found.note = (
                            f'{len(held)} row(s) of the posts table print only a post name and '
                            f'nothing else in their own row, so they are not published as posts: '
                            + '; '.join(f'row {o} "{n}" under "{h}"' for o, n, h in held))
                        rec.note(f'posts: {found.note}')
                    return found
            except Exception as exc:
                rec.note(f'extract_posts failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Posts'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('posts', resolved.authority.domain, 'posts')

    elif cf.name == 'vacancies':
        for doc in candidate_docs:
            document = loaded[doc.url]
            html = getattr(document, 'html', '')
            if getattr(document, 'kind', '') == 'HTML' and html:
                tables = _extract_html_tables(html)
                for rows in tables:
                    if not rows:
                        continue
                    row_lower = [c.lower() for c in rows[0]]
                    if any('vacanc' in c for c in row_lower):
                        v_col = next((idx for idx, c in enumerate(row_lower) if 'vacanc' in c), -1)
                        if v_col >= 0:
                            v_sum = 0
                            for data_row in rows[1:]:
                                if len(data_row) > v_col and data_row[v_col].strip().isdigit():
                                    v_sum += int(data_row[v_col].strip())
                            if v_sum > 0:
                                cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Vacancies',
                                                excerpt=f'Total Vacancies: {v_sum}', verified_date=_today())
                                return Field.found('vacancies', v_sum, cite)

            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            total = D_ELIGIBILITY.printed_vacancy_total(src_doc, text)
            if total is not None and total.count.evidence:
                ev = total.count.evidence[0]
                cite = Citation(document_title=doc.title, url=doc.url, page=_page_of(document, ev.span),
                                clause='Vacancies', excerpt=ev.span, verified_date=_today())
                return Field.found('vacancies', total.count.value, cite)
            try:
                vacs = D_ELIGIBILITY.extract_vacancies(src_doc, text, posts=[])
                with_value = [v for v in vacs if v.count.has_value]
                cnts = [v.count.value for v in with_value]
                if cnts:
                    ev = with_value[0].count.evidence[0] if with_value[0].count.evidence else None
                    cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Vacancies',
                                    excerpt=(ev.span if ev else str(cnts[0])), verified_date=_today())
                    if len(set(cnts)) == 1:
                        return Field.found('vacancies', cnts[0], cite)
                    # Several figures (a total, per-post or per-category counts, a figure in a
                    # note). Adding them up is arithmetic the authority did not print, and
                    # picking one is a guess; a person chooses, with every figure in front of them.
                    return Field.needs_review(
                        'vacancies', max(cnts),
                        f'the document states {len(set(cnts))} different vacancy figures '
                        f'({", ".join(str(c) for c in sorted(set(cnts), reverse=True)[:8])}); '
                        f'the total is not asserted from them', cite)
            except Exception as exc:
                rec.note(f'extract_vacancies failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Vacancies'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('vacancies', resolved.authority.domain, 'vacancies')

    elif cf.name == 'ageLimits':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                outcome = D_ELIGIBILITY.extract_eligibility(src_doc, text, exam_id=rec.exam_id)
                rules = outcome.eligibility.age_rules
                if rules:
                    # A notice may state its limits in several clauses -- a minimum in one,
                    # a maximum in another, each scoped to a list of posts. One band exists
                    # only if every clause agrees; several minima or maxima are post-scoped
                    # limits, and collapsing them into one band would assert a rule the
                    # authority did not print for any post.
                    scoped = [r for r in rules if r.is_global] or rules
                    mins = sorted({int(r.minimum_age.value) for r in scoped if r.minimum_age.has_value})
                    maxs = sorted({int(r.maximum_age.value) for r in scoped if r.maximum_age.has_value})
                    cutoffs = [r.cutoff_date.value for r in scoped if r.cutoff_date.has_value]
                    first = next((r for r in scoped if r.minimum_age.has_value or r.maximum_age.has_value), None)
                    ev = None
                    if first is not None:
                        facts = first.minimum_age if first.minimum_age.has_value else first.maximum_age
                        ev = facts.evidence[0] if facts.evidence else None
                    if mins and maxs:
                        val = {'minAge': mins[0], 'maxAge': maxs[-1], 'asOn': str(cutoffs[0]) if cutoffs else ''}
                        relax = _printed_relaxations(rules)
                        if relax:
                            val['relaxations'] = relax
                        cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Age Limits',
                                        excerpt=(ev.span if ev else str(val)), verified_date=_today())
                        if len(mins) == 1 and len(maxs) == 1:
                            return Field.found('ageLimits', val, cite)
                        return Field.needs_review(
                            'ageLimits', {**val, 'minima': mins, 'maxima': maxs},
                            f'the document states post-scoped age limits (minimum {"/".join(map(str, mins))}, '
                            f'maximum {"/".join(map(str, maxs))} years); no single band applies to every post',
                            cite)
            except Exception as exc:
                rec.note(f'extract_eligibility (age) failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Age Limits'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('ageLimits', resolved.authority.domain, 'ageLimits')

    elif cf.name == 'qualification':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                outcome = D_ELIGIBILITY.extract_eligibility(src_doc, text, exam_id=rec.exam_id)
                if outcome.eligibility.qualifications:
                    q = outcome.eligibility.qualifications[0]
                    ev = q.requirement.evidence[0] if q.requirement.evidence else None
                    excerpt = ev.span if ev else str(q.requirement.value)
                    cite = Citation(document_title=doc.title, url=doc.url, page=1,
                                    clause='Educational Qualification', excerpt=excerpt,
                                    verified_date=_today())
                    return Field.found('qualification', q.requirement.value, cite)
            except Exception as exc:
                rec.note(f'extract_eligibility (qualification) failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Qualification'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('qualification', resolved.authority.domain, 'qualification')

    elif cf.name == 'officialPapers':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                from ..exam_authoring.sources import html_links
                links = [(t, h) for t, h in getattr(document, 'links', []) or html_links(document, r'.*')]
                papers, rejected = D_PYQ.catalogue_papers(links, exam_id=rec.exam_id,
                                                          exam_codes=[rec.exam_id], doc=src_doc,
                                                          page_text=text)
                if papers:
                    proj = COMPAT.official_papers(papers, exam_id=rec.exam_id)
                    cite = Citation(document_title=doc.title, url=doc.url, page=1,
                                    clause='Official Papers', excerpt=papers[0].title,
                                    verified_date=_today())
                    return Field.found('officialPapers', proj, cite)
            except Exception as exc:
                rec.note(f'catalogue_papers failed on {doc.url}: {exc!r}')

        return Field.not_extracted('officialPapers', resolved.authority.domain, 'officialPapers')

    elif cf.name == 'answerKeys':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                key = D_PYQ.read_answer_key_notice(src_doc, text, exam_id=rec.exam_id)
                if key:
                    proj = COMPAT.answer_keys([key], exam_id=rec.exam_id)
                    cite = Citation(document_title=doc.title, url=doc.url, page=1,
                                    clause='Answer Keys', excerpt=key.url.value or doc.title,
                                    verified_date=_today())
                    return Field.found('answerKeys', proj, cite)
            except Exception as exc:
                rec.note(f'read_answer_key_notice failed on {doc.url}: {exc!r}')

        return Field.not_extracted('answerKeys', resolved.authority.domain, 'answerKeys')

    elif cf.name == 'admitCard':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                events = D_ADMIT.read_notice(src_doc, text, exam_id=rec.exam_id,
                                             authority_domain=resolved.authority.domain,
                                             cycle=resolved.year)
                if events:
                    proj = COMPAT.admit_card_events(events, exam_id=rec.exam_id)
                    cite = Citation(document_title=doc.title, url=doc.url, page=1,
                                    clause='Admit Card', excerpt=events[0].official_label,
                                    verified_date=_today())
                    return Field.found('admitCard', proj, cite)
            except Exception as exc:
                rec.note(f'admit_card.read_notice failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Admit Card'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('admitCard', resolved.authority.domain, 'admitCard')

    elif cf.name == 'results':
        # A cycle declares many results -- a ranking list, calls to verification, a selection
        # -- each in its own notice. Every result document of the cycle is read, and each
        # declaration keeps the notice it came from; the first one found is not the answer.
        collected, first = [], None
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                decls = D_RESULTS.read_notice(src_doc, text, exam_id=rec.exam_id,
                                              headline=doc.title,
                                              authority_domain=resolved.authority.domain,
                                              cycle=resolved.year)
                for d in decls:
                    if (not d.published_at.has_value and not d.qualified_count.has_value
                            and getattr(d.qualification, 'value', d.qualification) == 'UNSTATED'):
                        # A companion document of a stage (its verification material, a
                        # break-up of vacancies) names the stage but declares nothing: no
                        # date, no count, no outcome. It stays a source, not a declaration.
                        rec.note(f'results: {doc.title[:80]} declares nothing of its own; kept as a source only')
                        continue
                    if d.document_url.status is not SchemaStatus.VERIFIED:
                        d.document_url = __import__('tools.exam_builder.schema', fromlist=['Fact']).Fact.verified(
                            doc.url, d.evidence[0]) if d.evidence else d.document_url
                    if all(x.id != d.id for x in collected):
                        collected.append(d)
                        first = first or (doc, d)
            except Exception as exc:
                rec.note(f'results.read_notice failed on {doc.url}: {exc!r}')
        if collected:
            proj = COMPAT.result_declarations(collected, exam_id=rec.exam_id)
            doc, d0 = first
            cite = Citation(document_title=doc.title, url=doc.url, page=1,
                            clause='Results', excerpt=d0.label, verified_date=_today())
            return Field.found('results', proj, cite)

        return Field.not_extracted('results', resolved.authority.domain, 'results')

    elif cf.name == 'corrigenda':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                notices = D_CORRIGENDA.extract_corrigenda(src_doc, text, exam_id=rec.exam_id,
                                                          cycle=resolved.year)
                if notices:
                    proj = [n.to_dict() for n in notices]
                    cite = Citation(document_title=doc.title, url=doc.url, page=1,
                                    clause='Corrigenda Log', excerpt=notices[0].evidence_span,
                                    verified_date=_today())
                    return Field.found('corrigenda', proj, cite)
            except Exception as exc:
                rec.note(f'extract_corrigenda failed on {doc.url}: {exc!r}')

        return Field.not_extracted('corrigenda', resolved.authority.domain, 'corrigenda')

    elif cf.name == 'applicationPortal':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                portal = D_APPLICATION.extract_portal(src_doc, text, authority_domain=resolved.authority.domain)
                if portal and portal.has_value and portal.status is SchemaStatus.VERIFIED:
                    ev = portal.evidence[0] if portal.evidence else None
                    excerpt = ev.span if ev else portal.value
                    cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Application Portal',
                                    excerpt=excerpt, verified_date=_today())
                    return Field.found('applicationPortal', portal.value, cite)
            except Exception as exc:
                rec.note(f'extract_portal failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Application Portal'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('applicationPortal', resolved.authority.domain, 'applicationPortal')

    elif cf.name == 'howToApply':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                stages = D_APPLICATION.extract_stages(src_doc, text)
                if stages:
                    stages_data = [{
                        'id': s.id,
                        'title': s.title,
                        'order': s.order,
                        'description': s.description,
                        'fields': [{'label': f.label, 'kind': f.input_kind, 'required': f.required} for f in s.fields],
                        'documents': [{'name': d.name, 'required': d.required, 'specs': d.specifications} for d in s.documents]
                    } for s in stages]
                    ev = stages[0].evidence[0] if stages[0].evidence else None
                    excerpt = ev.span if ev else stages[0].title
                    cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='How to Apply',
                                    excerpt=excerpt, verified_date=_today())
                    return Field.found('howToApply', stages_data, cite)
            except Exception as exc:
                rec.note(f'extract_stages failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — How to Apply'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('howToApply', resolved.authority.domain, 'howToApply')

    elif cf.name == 'fee':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                fees = D_APPLICATION.extract_fees(src_doc, text)
                if fees:
                    unscoped = next((f for f in fees if f.scope.is_global and f.amount.has_value), fees[0])
                    ev = unscoped.amount.evidence[0] if unscoped.amount.evidence else (fees[0].amount.evidence[0] if fees[0].amount.evidence else None)
                    excerpt = ev.span if ev else str(unscoped.amount.value)
                    exemptions = [str(f.scope) for f in fees if f.is_exempt.has_value and f.is_exempt.value]
                    modes = list(unscoped.accepted_modes.value) if unscoped.accepted_modes.has_value else []
                    fee_obj = {
                        'amount': unscoped.amount.value if unscoped.amount.has_value else 0,
                        # As printed, the shape the semantic and legacy readers emit and the
                        # frontend's `ApplicationFeeDetails.amounts` declares: 100, not 100.0.
                        'amounts': [_printed_amount(f.amount.value) for f in fees if f.amount.has_value],
                        'exemptions': ', '.join(exemptions),
                        'acceptedModes': modes,
                        'rules': [{'scope': str(f.scope), 'amount': f.amount.value, 'isExempt': f.is_exempt.value} for f in fees]
                    }
                    cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Application Fee',
                                    excerpt=excerpt, verified_date=_today())
                    return Field.found('fee', fee_obj, cite)
            except Exception as exc:
                rec.note(f'extract_fees failed on {doc.url}: {exc!r}')

        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    title = f'{rec.title} — Fee'
                    got = fn(loaded[doc.url], title)
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')

        return Field.not_extracted('fee', resolved.authority.domain, 'fee')

    elif cf.name == 'feeExemptions':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                exemptions = D_APPLICATION.extract_fee_exemptions(src_doc, text)
                if exemptions:
                    cite = Citation(document_title=doc.title, url=doc.url,
                                    page=_page_of(document, exemptions[0]['evidenceSpan']), clause='Fee Exemptions',
                                    excerpt=exemptions[0]['evidenceSpan'] or exemptions[0]['category'],
                                    verified_date=_today())
                    return Field.found('feeExemptions', exemptions, cite)
            except Exception as exc:
                rec.note(f'extract_fee_exemptions failed on {doc.url}: {exc!r}')

        # Not finding a structured exemption is not the authority publishing none. Where any
        # document read for this field states an exemption in words, the reading is held for
        # review with that sentence; only a document set with no such wording at all is
        # evidence that no exemption was published.
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            stated = D_APPLICATION.exemption_wording(text)
            if stated:
                cite = Citation(document_title=doc.title, url=doc.url, page=_page_of(document, stated),
                                clause='Fee Exemptions', excerpt=stated[:400], verified_date=_today())
                return Field.needs_review(
                    'feeExemptions', [{'category': '', 'isExempt': True, 'evidenceSpan': stated[:400],
                                       'status': 'NEEDS_REVIEW'}],
                    'the document states a fee exemption, but the group it applies to could not be '
                    'read with confidence; the sentence is kept for a person to confirm', cite)
        return _unread_by_us('feeExemptions', candidate_docs, loaded) or Field.not_published('feeExemptions', 'No fee exemptions published in official document')

    elif cf.name == 'requiredDocuments':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                docs = D_APPLICATION.extract_required_documents(src_doc, text)
                if docs:
                    cite = Citation(document_title=doc.title, url=doc.url, page=1, clause='Required Documents',
                                    excerpt=docs[0]['evidenceSpan'] or docs[0]['name'],
                                    verified_date=_today())
                    return Field.found('requiredDocuments', docs, cite)
            except Exception as exc:
                rec.note(f'extract_required_documents failed on {doc.url}: {exc!r}')

        return _unread_by_us('requiredDocuments', candidate_docs, loaded) or Field.not_published('requiredDocuments', 'No specific upload documents announced in notice')

    elif cf.name == 'photoSignatureGuidelines':
        for doc in candidate_docs:
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            if not text:
                continue
            src_doc = SourceDocument(id=doc.url, url=doc.url, kind=SourceKind.OTHER_OFFICIAL,
                                     title=doc.title, authority=resolved.authority.name,
                                     exam_id=rec.exam_id)
            try:
                guidelines = D_APPLICATION.extract_photo_signature_guidelines(src_doc, text)
                if guidelines and guidelines.get('hasOfficialGuidelines'):
                    ev = guidelines['evidenceSpans'][0] if guidelines.get('evidenceSpans') else 'Photograph & signature specifications'
                    cite = Citation(document_title=doc.title, url=doc.url, page=1,
                                    clause='Photo & Signature Guidelines', excerpt=ev,
                                    verified_date=_today())
                    return Field.found('photoSignatureGuidelines', guidelines, cite)
            except Exception as exc:
                rec.note(f'extract_photo_signature_guidelines failed on {doc.url}: {exc!r}')

        return _unread_by_us('photoSignatureGuidelines', candidate_docs, loaded) or Field.not_published('photoSignatureGuidelines', 'No distinct photograph/signature guidelines published')

    elif cf.name == 'faqs':
        # An FAQ document for this exam first; failing that, the notice's own procedure
        # clauses, each quoted under the heading the notice printed (see `clauses`).
        fn = getattr(X, cf.extractor, None) if cf.extractor else None
        if fn is not None:
            for doc in candidate_docs:
                try:
                    got = fn(loaded[doc.url], f'{rec.title} — FAQs')
                    if got is not None and got.ok:
                        return got
                except Exception as exc:
                    rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')
        from .clauses import procedure_clauses
        for doc in candidate_docs:
            check = (identity or {}).get(doc.url)
            if doc.kind is not DocKind.NOTIFICATION or check is None or check.verdict is not IdentityVerdict.MATCH:
                continue
            document = loaded[doc.url]
            text = document.all_text() if hasattr(document, 'all_text') else ''
            items = procedure_clauses(text, page_of=lambda span, d=document: _page_of(d, span))
            if items:
                faqs = [{'question': c['heading'], 'answer': c['text'],
                         'officialClause': f"Clause {c['number']} of the notice", 'excerpt': c['text'],
                         'page': c['page']} for c in items]
                cite = Citation(document_title=doc.title, url=doc.url, page=items[0]['page'],
                                clause='Procedure clauses of the notice', excerpt=items[0]['text'][:400],
                                verified_date=_today())
                field = Field.found('faqs', faqs, cite)
                field.note = ('the notice\'s own procedure clauses, quoted under its headings; no FAQ '
                              'page specific to this recruitment was found')
                return field
        return Field.not_extracted('faqs', resolved.authority.domain, 'faqs')

    elif cf.name == 'nextSteps':
        res_field = rec.fields.get('results')
        pat_field = rec.fields.get('examPattern')
        res_val = res_field.value if (res_field and res_field.ok and res_field.value) else []
        pat_val = pat_field.value if (pat_field and pat_field.ok and pat_field.value) else []
        
        from .results import admission_rules, derive_next_steps
        guidance = derive_next_steps(res_val, pat_val)
        # The authority's own rule for moving candidates between its stages, quoted from an
        # identity-matched notification. Official statements, listed before any guidance.
        rules: list[dict] = []
        for doc in sources.docs:
            check = (identity or {}).get(doc.url)
            document = loaded.get(doc.url)
            if (doc.kind is not DocKind.NOTIFICATION or document is None or check is None
                    or check.verdict is not IdentityVerdict.MATCH):
                continue
            text = document.all_text() if hasattr(document, 'all_text') else ''
            for rule in admission_rules(text, pat_val, document_title=doc.title, document_url=doc.url,
                                        page_of=lambda span, d=document: _page_of(d, span)):
                if (rule['fromStage'], rule['nextStage']) not in {(r['fromStage'], r['nextStage']) for r in rules}:
                    rules.append(rule)
        if rules:
            # A derived step keeps the declaration it was derived from as its own source; the
            # field's citation becomes the rule's, and must not be lent to the guidance.
            basis = res_field.citation if (res_field and res_field.citation) else None
            derived = [dict(g, **({'documentTitle': basis.document_title, 'documentUrl': basis.url,
                                   'basisPage': 1, 'basisClause': 'Next Steps Guidance',
                                   'basisExcerpt': 'Derived from verified result declaration and exam pattern'}
                                  if basis else {}))
                       for g in guidance if g.get('action') != 'Awaiting Official Result Declaration']
            steps = rules + derived
            first = rules[0]
            cite = Citation(document_title=first['documentTitle'], url=first['documentUrl'],
                            page=first['page'], clause='Admission to the next stage',
                            excerpt=first['evidenceSpan'][:400], verified_date=_today())
            return Field.found('nextSteps', steps, cite)
        if res_val:
            doc_title = res_field.citation.document_title if (res_field and res_field.citation) else rec.title
            doc_url = res_field.citation.url if (res_field and res_field.citation) else resolved.authority.domain
            cite = Citation(document_title=doc_title, url=doc_url, page=1, clause='Next Steps Guidance',
                            excerpt='Derived from verified result declaration and exam pattern',
                            verified_date=_today())
            return Field.found('nextSteps', guidance, cite)
        else:
            return Field.not_published('nextSteps', 'Awaiting official result declaration to determine next steps')

    # 3. Legacy extractor fallback for any other fields
    fn = getattr(X, cf.extractor, None) if cf.extractor else None
    if fn is not None:
        last_field = None
        for doc in candidate_docs:
            document = loaded[doc.url]
            title = f'{rec.title} — {doc.kind.value.replace("_", " ").title()}'
            try:
                got = fn(document, title)
                last_field = got
                if got is not None and getattr(got, 'ok', False):
                    return got
            except Exception as exc:
                rec.note(f'{cf.extractor} failed on {doc.url}: {exc!r}')
                continue
        if last_field is not None:
            return last_field

    return Field.not_extracted(cf.name, resolved.authority.domain, cf.name)


_REACQUISITION_KEYWORDS: dict[str, tuple[str, DocKind]] = {
    'syllabus': ('syllabus scheme of examination', DocKind.SYLLABUS),
    'examPattern': ('scheme of examination pattern', DocKind.EXAM_PATTERN),
    'admitCard': ('admit card hall ticket', DocKind.ADMIT_CARD),
    'results': ('result declaration merit list', DocKind.RESULT),
    'officialPapers': ('previous year question paper', DocKind.QUESTION_PAPER),
    'answerKeys': ('answer key', DocKind.ANSWER_KEY),
    'corrigenda': ('corrigendum notice amendment', DocKind.CORRIGENDUM),
    'dates': ('examination schedule dates calendar', DocKind.CALENDAR),
    # The fields a notice may or may not carry. Searching the authority's own domain for a
    # dedicated document is what turns "our reader found nothing" into the evidence-based
    # "no applicable official source was found after search" -- never into "not published".
    'faqs': ('frequently asked questions', DocKind.EXAM_PAGE),
    'examDayChecklist': ('instructions to candidates examination day admit card', DocKind.ADMIT_CARD),
    'attempts': ('number of attempts eligibility conditions', DocKind.NOTIFICATION),
    'howToApply': ('how to apply online application procedure', DocKind.APPLICATION_PORTAL),
}


def _targeted_reacquire(
    resolved: ResolvedExam,
    sources: SourceSet,
    loaded: dict[str, object],
    hashes: dict[str, str],
    identity: dict[str, IdentityCheck],
    target: ExamIdentity,
    unpopulated: list[str],
    rec: ExamRecord,
    *,
    max_queries: int = 3,
    search_fn: Optional[Callable] = None,
    queried: Optional[list[str]] = None,
) -> int:
    """Bounded targeted discovery on the authority's domain for unpopulated contract fields.

    `queried`, when given, receives the name of every field a search was actually issued for,
    so completeness can tell "searched and nothing found" from "never looked".
    """
    from .search import SearchUnavailable, search as default_web_search
    from . import discover as D_MOD

    if getattr(D_MOD._search_for_missing_kinds, '__name__', '') == 'no_search':
        return 0

    searcher = search_fn or default_web_search
    host = (urlparse(resolved.authority.domain).hostname or resolved.authority.domain).replace('www.', '').lower()
    seen_urls = {d.url for d in sources.docs} | {d.url for d in sources.rejected}
    attempts = 0

    for field_name in unpopulated:
        if attempts >= max_queries:
            break
        target_info = _REACQUISITION_KEYWORDS.get(field_name)
        if not target_info:
            continue
        kw, expected_kind = target_info
        query_str = f"{resolved.official_name or resolved.query} {kw} {host}"
        try:
            hits = searcher(query_str, max_results=5, official_only=False)
            attempts += 1
            if queried is not None:
                queried.append(field_name)
        except SearchUnavailable as exc:
            sources.infrastructure_failed = True
            sources.infrastructure_note = f'Search service unavailable during targeted re-acquisition: {exc}'
            rec.note(sources.infrastructure_note)
            return attempts
        except Exception as exc:
            sources.infrastructure_failed = True
            sources.infrastructure_note = f'Network failure during targeted re-acquisition: {exc}'
            rec.note(sources.infrastructure_note)
            return attempts

        for h in (hits or []):
            h_url = getattr(h, 'url', '')
            h_title = getattr(h, 'title', '')
            if not h_url or h_url in seen_urls:
                continue
            seen_urls.add(h_url)

            # Restrict strictly to the authority's own estate (its registered domain)
            h_host = (urlparse(h_url).hostname or '').replace('www.', '').lower()
            if not same_estate(h_host, host):
                continue

            doc_kind = classify_kind(h_title, h_url)
            if doc_kind is DocKind.UNKNOWN:
                doc_kind = expected_kind

            disc_doc = DiscoveredDoc(
                url=h_url,
                kind=doc_kind,
                title=h_title[:160] or f'{field_name} document',
                relevance=Relevance.DIRECT,
                matched=[resolved.query],
                found_on='(targeted re-acquisition)'
            )

            try:
                document = _load(disc_doc)
            except FetchError as exc:
                sources.infrastructure_failed = True
                sources.infrastructure_note = f'could not fetch re-acquired source {h_url}: {exc}'
                rec.note(sources.infrastructure_note)
                continue

            raw = getattr(document, 'raw', b'') or (document.all_text() or '').encode('utf-8')
            chash = content_hash(raw)
            if chash in hashes.values():
                # Duplicate document content already read
                continue

            text = document.all_text() if hasattr(document, 'all_text') else ''
            check = verify_identity(text, target, source_url=h_url, document_title=disc_doc.title)
            identity[h_url] = check
            if check.verdict is IdentityVerdict.MISMATCH:
                sources.rejected.append(disc_doc)
                rec.note(f're-acquired doc MISMATCH: {h_url}')
                continue

            loaded[h_url] = document
            hashes[h_url] = chash
            sources.docs.append(disc_doc)
            rec.sources_read.append(h_url)
            rec.note(f're-acquired official source for {field_name}: {h_url}')

    return attempts


def build(exam_query: str = '', *, year: str = '',
          sibling_exam_words: list[str] | None = None, max_docs: int = 8,
          replay: SourceManifest | None = None,
          search_fn: Optional[Callable] = None) -> BuildResult:
    """Build one exam, either from fresh discovery or from a captured manifest.

    `replay` freezes which documents are used and nothing else: they are re-fetched and
    re-validated exactly as on a fresh build.
    """
    if replay is not None:
        resolved = ResolvedExam(
            query=replay.query,
            official_name=replay.query,
            year=year or '',
            authority=Authority(name=replay.authority_name,
                                domain=replay.authority_domain, confidence=1.0),
            seed_urls=list(replay.urls))
        exam_id = replay.exam_id
        sources = to_source_set(replay)
    else:
        resolved = resolve(exam_query, year=year)
        exam_id = stable_exam_id(resolved)
        own = exam_aliases(resolved.query, resolved.official_name)
        siblings = [w for w in (sibling_exam_words or []) if w not in own]
        sources = discover(resolved, exam_id=exam_id, sibling_exam_words=siblings)

    rec = ExamRecord(
        exam_id=exam_id,
        code=exam_id.replace('exam-', '').upper().replace('-', '_'),
        title=resolved.official_name or resolved.query,
        authority_name=resolved.authority.name,
        official_domain=resolved.authority.domain,
    )
    rec.sources_read.extend(d.url for d in sources.docs)
    rec.log.extend(sources.log)
    if resolved.authority.corroborated_by:
        rec.note(f'{resolved.authority.domain} is not a government domain; it was accepted '
                 f'because {resolved.authority.corroborated_by} names it.')
    if sources.rejected:
        rec.note(f'{len(sources.rejected)} document(s) were rejected as belonging to another '
                 f'exam on the same site — the isolation gate working, not an error.')

    # Read each document once, then let every contract field that names its kind try it.
    # Only `max_docs` are read, so the ones that name this exam most specifically go first:
    # a site's listing pages and its other recruitments' notices came before the exam's own
    # notification in crawl order, and the cap then left that notification unread.
    loaded: dict[str, object] = {}
    hashes: dict[str, str] = {}
    changed: list[str] = []
    prior = {s.url: s.content_hash for s in (replay.sources if replay else [])}
    for doc in _load_order(sources.docs)[:max_docs]:
        try:
            document = _load(doc)
        except FetchError as exc:
            sources.infrastructure_failed = True
            sources.infrastructure_note = f'could not read {doc.url}: {exc}'
            rec.note(sources.infrastructure_note)
            continue
        loaded[doc.url] = document
        _reclassify_from_content(doc, document, rec)
        raw = getattr(document, 'raw', b'') or (document.all_text() or '').encode('utf-8')
        hashes[doc.url] = content_hash(raw)
        if prior.get(doc.url) and prior[doc.url] != hashes[doc.url]:
            changed.append(doc.url)
            rec.note(f'source changed since the manifest was captured: {doc.url}')

    # Coverage is computed after loading, so a document that only its own text could
    # classify counts for the kind it turned out to be.
    available = {d.kind for d in sources.docs}
    coverage = coverage_from(available)

    # Content identity check
    target = ExamIdentity(exam_id=exam_id, query=resolved.query,
                          official_name=resolved.official_name, year=resolved.year,
                          authority_name=resolved.authority.name,
                          authority_domain=resolved.authority.domain)
    identity: dict[str, IdentityCheck] = {}
    for doc in list(sources.docs):
        document = loaded.get(doc.url)
        if document is None:
            continue
        text = document.all_text() if hasattr(document, 'all_text') else ''
        check = verify_identity(text, target, source_url=doc.url, document_title=doc.title)
        if check.verdict is not IdentityVerdict.MATCH:
            entry = _listing_entry(document, target)
            if entry is not None:
                loaded[doc.url] = entry
                check = verify_identity(entry.text, target, source_url=doc.url,
                                        document_title=doc.title)
                rec.note(f'{doc.url} lists many recruitments; only its row(s) naming this exam '
                         f'were kept ({len(entry.text)} chars)')
        identity[doc.url] = check
        if check.verdict is IdentityVerdict.MISMATCH:
            loaded.pop(doc.url, None)
            rec.note(f'content identity MISMATCH, excluded from extraction: {doc.url} '
                     f'({"; ".join(check.reasons)[:120]})')
        elif check.verdict is IdentityVerdict.AMBIGUOUS:
            rec.note(f'content identity AMBIGUOUS: {doc.url} '
                     f'({"; ".join(check.reasons)[:120]})')

    identity_cite = Citation(
        document_title=f'{resolved.authority.name} — official web presence',
        url=resolved.authority.domain, page=1, clause='Authority resolution',
        excerpt=f'Resolved from official sources with confidence '
                f'{resolved.authority.confidence}; evidence: '
                f'{", ".join(resolved.authority.evidence[:3])}',
        verified_date=_today())
    rec.set(Field.found('officialName', rec.title, identity_cite))
    rec.set(Field.found('authority', resolved.authority.name, identity_cite))

    # Initial extraction pass
    for cf in CONTRACT:
        if cf.name in ('officialName', 'authority'):
            continue
        status = coverage.supplied.get(cf.name, 'NO_SOURCE')
        if status == 'INTRINSIC':
            continue
        if status == 'NO_SOURCE':
            if sources.infrastructure_failed:
                rec.set(Field.not_extracted(
                    cf.name, resolved.authority.domain,
                    f'{cf.name} (search or fetch did not complete: '
                    f'{sources.infrastructure_note[:120]})'))
                continue
            rec.set(Field.not_published(
                cf.name,
                f'No document of kind {" or ".join(k.value for k in cf.sources)} was found '
                f'for this exam on {resolved.authority.domain}.'))
            continue

        got = _dispatch_domain_extraction(cf, sources, loaded, rec, resolved, identity, target)
        rec.set(got)

    # Completeness-driven re-acquisition loop
    reacquire_attempts = 0
    queried_fields: list[str] = []
    if replay is None and not sources.infrastructure_failed:
        unpopulated = [
            cf.name for cf in CONTRACT
            if cf.name not in ('officialName', 'authority', 'officialSources')
            and (rec.fields.get(cf.name) is None
                 or rec.fields[cf.name].status in (RecordStatus.NOT_PUBLISHED, RecordStatus.NOT_EXTRACTED))
            and cf.name in _REACQUISITION_KEYWORDS
        ]
        if unpopulated:
            initial_count = len(sources.docs)
            # One bounded, domain-restricted query per unpopulated field. A global cap of three
            # left later fields unsearched, which then read as reader failures rather than as
            # genuinely absent sources.
            reacquire_attempts = _targeted_reacquire(
                resolved, sources, loaded, hashes, identity, target,
                unpopulated, rec, max_queries=len(unpopulated), search_fn=search_fn,
                queried=queried_fields
            )
            if len(sources.docs) > initial_count:
                available = {d.kind for d in sources.docs}
                coverage = coverage_from(available)
                for cf in CONTRACT:
                    if cf.name in unpopulated:
                        status = coverage.supplied.get(cf.name, 'NO_SOURCE')
                        if status not in ('NO_SOURCE', 'INTRINSIC'):
                            got = _dispatch_domain_extraction(
                                cf, sources, loaded, rec, resolved, identity, target)
                            if got is not None:
                                rec.set(got)

    record_official_sources(rec, sources, loaded, identity)
    breakups = record_vacancy_breakups(rec, sources, loaded, identity)
    if breakups:
        rec.note(f'{breakups} vacancy break-up table(s) read from ruled grids and verified')
    revisions = record_date_revisions(rec, sources, loaded)
    if revisions:
        rec.note(f'{revisions} date revision(s) recorded in the revision history from later '
                 f'official statements')
    enforce_semantic_states(rec)

    # A field that was searched for on the authority's own domain and is still unread has been
    # through every acquisition path this engine has: that is "no applicable source found after
    # search", kept distinct from a reader failure and from an authority that published nothing.
    searched_not_found = frozenset(
        name for name in queried_fields
        if rec.fields.get(name) is None or rec.fields[name].status is RecordStatus.NOT_EXTRACTED)
    if searched_not_found:
        rec.note(f'searched the authority domain and found no applicable source for: '
                 f'{", ".join(sorted(searched_not_found))}')
    completeness_report = evaluate_completeness(
        rec, sources, reacquisition_attempts=reacquire_attempts,
        searched_not_found=searched_not_found)

    state = (BuildState.PAUSED_INFRASTRUCTURE if sources.infrastructure_failed
             else BuildState.COMPLETE)
    snapshot = from_source_set(
        sources, query=resolved.query, authority_name=resolved.authority.name,
        identity={u: c.verdict.value for u, c in identity.items()}, hashes=hashes)
    return BuildResult(resolved=resolved, sources=sources, coverage=coverage, record=rec,
                       build_state=state, identity=identity, manifest=snapshot,
                       changed_sources=changed, completeness=completeness_report,
                       reacquisition_attempts=reacquire_attempts, searched_not_found=searched_not_found)
