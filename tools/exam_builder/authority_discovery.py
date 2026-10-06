"""Authority source discovery: a bounded walk outward from an authority's own site.

A candidate should not need to know where government-exam information lives. Exam discovery
(discover.py) looks for one exam's documents; this looks at the authority first -- its
navigation, its repositories (old question papers, results, keys, notifications), its
registration portal, the retired domain its pages still link to -- and records everything it
finds in a source graph with the provenance of how it was found.

    authority root
      -> official navigation        deterministic <a href> extraction, with the heading or list
                                    label each link sits under
      -> official repositories      a page that lists many resources of one role; every item is
                                    registered with parent -> child provenance, including items
                                    listed without a working link
      -> linked resources           files fetched (bounded) and hashed, so one file reached two
                                    ways is one resource
      -> search / social leads      supplements, never the source of truth
    then, per exam:
      -> admit_for_exam             the EXISTING discover.gate() decides which official items
                                    belong to an exam; the existing identity, extraction,
                                    evidence and publication gates do the rest
      -> project_for_exam           classified resources for the candidate sections

What it never does: crawl beyond its limits, follow a page off the authority's estate unless the
authority links to it and it is a government repository, decide that a source is official because
a model or a search engine said so, or turn a lead into a fact. Nothing here names an authority or
an exam: TGPSC and SSC are test cases, not branches.
"""
from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Callable, Optional
from urllib.parse import quote, urljoin, urlparse

from ..claude_cli.discovery import fetch_checked
from ..exam_authoring.sources import estate_of, same_estate
from .discover import DiscoveredDoc, DocKind, Relevance, gate, page_is_specific_to
from .resolve import exam_aliases
from .resource_roles import (REPOSITORY_WORDS, SECTION_FOR_ROLE, classify_link, is_headline, is_hub_link,
                             is_learning)
from .source_graph import (DiscoveryLimits, DiscoveryRun, EdgeKind, NodeStatus, NodeType, SearchState, SkipReason,
                           SourceClass, SourceGraph, SourceNode, coverage_report, normalize_url, now_iso,
                           role_by_claude, role_search_state, url_key, CLAUDE_ROLE_REASON)
from .source_trust import TrustRegistry, bare_host, classify_source, is_social, is_video, source_ownership

#: Roles whose page, when it lists many items, is a repository of that role.
REPOSITORY_ROLES = frozenset({DocKind.QUESTION_PAPER, DocKind.ANSWER_KEY, DocKind.RESULT, DocKind.NOTIFICATION,
                              DocKind.CUTOFF, DocKind.SYLLABUS, DocKind.CORRIGENDUM, DocKind.ADMIT_CARD,
                              DocKind.CALENDAR})
#: Services are recorded, never crawled: a login form is not a listing.
_SERVICE_ROLES = frozenset({DocKind.OTR_PORTAL, DocKind.APPLICATION_PORTAL, DocKind.DISCOVERY_SIGNAL})
_SKIP_SCHEMES = ('javascript:', 'mailto:', 'tel:', 'data:', 'about:')
_HEADINGS = ('h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'caption', 'legend')


# ===================================================================== link extraction
@dataclass
class Link:
    url: str
    text: str
    #: The most specific words the link sits in: its table row ("33/2022 - ASSISTANT PROFESSORS ...
    #: Addendum"), else its list label ("1.AE."), else the section heading ("Old Question Papers:").
    context: str = ''
    #: The section heading above it.
    heading: str = ''
    #: Listed as an item but with no working link (href="#").
    unlinked: bool = False
    #: The list item's own label, where it sits in one.
    label: str = ''
    #: The text of the table row it sits in, where it sits in a data row (not a layout table).
    row: str = ''
    #: The heading or caption above that table.
    table_heading: str = ''


#: A row longer than this, or carrying more links, is page layout or navigation, not a listing row.
_ROW_MAX_CHARS = 600
_ROW_MAX_LINKS = 8


def _norm(text: str) -> str:
    return ' '.join((text or '').split())


#: Characters left as they are when an href is percent-encoded: URL syntax and existing escapes.
_URL_SAFE = ":/?#[]@!$&'()*+,;=%~"


def _browser_href(href: str) -> str:
    """An href as a browser would request it: tabs and newlines dropped, spaces and other unsafe
    characters percent-encoded. Government sites link files whose names have spaces in them; refusing
    those refused the authority's own documents. The address checks still run on the result."""
    href = ''.join(ch for ch in href if ch not in '\t\n\r').strip()
    return quote(href, safe=_URL_SAFE)


class _LinkParser(HTMLParser):
    """Reads <a href> links with the heading and list label each sits under. Deterministic: Claude
    is never asked to parse HTML."""

    def __init__(self, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self.base = base_url
        self.links: list[Link] = []
        self.title = ''
        self.heading = ''
        self._in_title = False
        self._skip = 0
        self._hbuf: Optional[list] = None
        self._li: list[dict] = []
        self._a: Optional[dict] = None
        #: Open table rows, innermost last: their text so far and the links placed in them.
        self._rows: list[dict] = []
        #: The heading in force where each open table began.
        self._tables: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip += 1
            return
        if self._skip:
            return
        if tag == 'title':
            self._in_title = True
        elif tag in _HEADINGS:
            self._hbuf = []
        elif tag == 'li':
            self._li.append({'label': '', 'linked': False, 'buf': []})
        elif tag == 'table':
            self._tables.append(self.heading)
        elif tag == 'tr':
            self._rows.append({'buf': [], 'links': []})
        elif tag in ('td', 'th') and self._rows:
            self._rows[-1]['buf'].append(' ')
        elif tag == 'a':
            self._a = {'href': dict(attrs).get('href'), 'buf': []}
        elif tag == 'br' and self._li and not self._li[-1]['label']:
            text = _norm(''.join(self._li[-1]['buf']))
            if text:
                self._li[-1]['label'] = text

    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'noscript', 'template'):
            self._skip = max(0, self._skip - 1)
            return
        if self._skip:
            return
        if tag == 'title':
            self._in_title = False
        elif tag in _HEADINGS and self._hbuf is not None:
            text = _norm(''.join(self._hbuf))
            if text:
                self.heading = text
            self._hbuf = None
        elif tag == 'a' and self._a is not None:
            self._close_anchor()
        elif tag == 'li' and self._li:
            self._li.pop()
        elif tag == 'tr' and self._rows:
            self._close_row(self._rows.pop())
        elif tag == 'table' and self._tables:
            self._tables.pop()

    def handle_data(self, data):
        if self._skip:
            return
        if self._in_title:
            self.title += data
        if self._hbuf is not None:
            self._hbuf.append(data)
        if self._rows:
            self._rows[-1]['buf'].append(data)
        if self._a is not None:
            self._a['buf'].append(data)
        elif self._li and not self._li[-1]['linked'] and not self._li[-1]['label']:
            self._li[-1]['buf'].append(data)

    def _label(self) -> str:
        if self._li:
            li = self._li[-1]
            return li['label'] or _norm(''.join(li['buf']))
        return ''

    def _context(self) -> str:
        return self._label() or self.heading

    def _place(self, link: 'Link') -> None:
        """Add a link, remembering the table row it sits in so the row can name it when it closes."""
        link.label = self._label()
        if self._tables:
            link.table_heading = self._tables[-1]
        self.links.append(link)
        if self._rows:
            self._rows[-1]['links'].append(len(self.links) - 1)

    def _close_row(self, row: dict) -> None:
        """A data row's text is the context of every link in it: "Addendum" in the row of
        "33/2022 - ASSISTANT PROFESSORS ..." is that recruitment's addendum, not the page's. A row that
        is really page layout (very long) or navigation (many links) names nothing and is not used."""
        text = _norm(''.join(row['buf']))
        if not row['links'] or not text or len(text) > _ROW_MAX_CHARS or len(row['links']) > _ROW_MAX_LINKS:
            return
        for i in row['links']:
            link = self.links[i]
            link.row = text[:300]
            label = link.label
            link.context = (f'{label} · {link.row}' if label and label not in link.row else link.row)[:400]

    def _close_anchor(self) -> None:
        a, self._a = self._a, None
        text = _norm(''.join(a['buf']))
        href = _browser_href(a['href'] or '')
        li = self._li[-1] if self._li else None
        if a['href'] is None:
            # An anchor with no address is a label: "<li><a>1.AE.</a> <a href=..>1.AE-CIVIL</a>".
            if li is not None and not li['linked'] and text:
                li['label'] = text
            return
        context = self._context()
        if not href or href.startswith('#'):
            # Listed as an item, with no file behind it. Kept: "listed but not obtainable" is a
            # finding about the repository, and silence would hide it.
            if text and ((li is not None and (li['label'] or li['linked'])) or self._rows):
                self._place(Link(url='', text=text, context=context, heading=self.heading, unlinked=True))
            return
        if href.lower().startswith(_SKIP_SCHEMES):
            return
        if li is not None:
            if not li['label']:
                li['label'] = _norm(''.join(li['buf']))
            li['linked'] = True
        self._place(Link(url=urljoin(self.base, href), text=text, context=context, heading=self.heading))


def extract_links(html: str, base_url: str) -> tuple[list[Link], str]:
    """(links, page title). Within one page a URL linked twice keeps the copy with the most text
    (an icon link and a text link to the same place are one link)."""
    parser = _LinkParser(base_url)
    try:
        parser.feed(html or '')
        parser.close()
    except Exception:                                           # noqa: BLE001 - malformed HTML is data
        pass
    best: dict[str, Link] = {}
    order: list[str] = []
    unlinked = [l for l in parser.links if l.unlinked]
    for link in parser.links:
        if link.unlinked:
            continue
        key = url_key(link.url)
        if key not in best:
            order.append(key)
            best[key] = link
        elif len(link.text) > len(best[key].text):
            kept = best[key]
            best[key] = Link(url=link.url, text=link.text, context=link.context or kept.context,
                             heading=link.heading or kept.heading, label=link.label or kept.label,
                             row=link.row or kept.row, table_heading=link.table_heading or kept.table_heading)
    return [best[k] for k in order] + unlinked, _once(_norm(parser.title))


def _once(title: str) -> str:
    """A title a page prints twice over ("Commission NameCommission Name") is one title."""
    half = len(title) // 2
    for cut in (half, half + 1):
        if title[:cut].strip() and title[:cut].strip() == title[cut:].strip():
            return title[:cut].strip()
    return title


# ========================================================================= traversal
def _skip(run: DiscoveryRun, node: SourceNode, reason: SkipReason, why: str) -> None:
    """Record that a node in scope was left unread, and why: on the node, and in the frontier, so a
    report of what the run did not get to includes it."""
    if node.skipped:
        return                  # queued twice; recorded once
    node.status = NodeStatus.SKIPPED_LIMIT
    node.skipped = reason.value
    run.frontier.append({'url': node.url, 'title': node.title, 'role': node.role.value, 'skip': reason.value,
                         'reason': why})


def _is_html(result) -> bool:
    ctype = (getattr(result, 'content_type', '') or '').lower()
    return 'html' in ctype or ('<html' in (getattr(result, 'text', '') or '')[:600].lower())


def _default_fetch(limits: DiscoveryLimits) -> Callable:
    return lambda url: fetch_checked(url, timeout=limits.timeout_seconds, max_bytes=limits.max_content_bytes)


def discover_authority(roots: list, *, authority_name: str = '', estates: Optional[list] = None,
                       limits: Optional[DiscoveryLimits] = None, fetch: Optional[Callable] = None,
                       registry: Optional[TrustRegistry] = None, search_hits: Optional[list] = None,
                       social_posts: Optional[list] = None, gateway=None,
                       should_continue: Optional[Callable[[], bool]] = None) -> DiscoveryRun:
    """Walk outward from the authority's own roots, within `limits`, and return what was found.

    `roots` must be the authority's verified official address(es) -- the resolver establishes that
    (officiality.py); this module does not decide officiality from a ranking. `fetch` is injectable
    for tests and defaults to the SSRF-guarded `fetch_checked`.
    """
    limits = limits or DiscoveryLimits()
    fetch = fetch or _default_fetch(limits)
    registry = registry if registry is not None else TrustRegistry.load()
    roots = [normalize_url(r) for r in roots if r]
    estates = list(dict.fromkeys(estates or [estate_of(bare_host(r)) for r in roots]))
    run = DiscoveryRun(authority_name=authority_name, estates=estates, roots=list(roots), limits=limits)
    g = run.graph

    for root in roots:
        node, _ = g.add(root, node_type=NodeType.SITE_ROOT, role=DocKind.OFFICIAL_PORTAL,
                        source_class=SourceClass.PRIMARY_OFFICIAL, authority=authority_name,
                        class_reason='the authority’s own address, as resolved and verified', depth=0,
                        owner=estate_of(bare_host(root)), relationship='OWNED_BY_AUTHORITY')
        g.add_edge('', node.id, EdgeKind.OFFICIAL_LINK, method='seed', anchor_text=authority_name)

    #: (node id, expects a document). Pages and repository items, breadth first.
    queue: deque = deque((g.get(r).id, False) for r in roots)
    #: Loose documents (a notice headline on a home page): fetched only with budget left over, so a
    #: home page's news ticker cannot use up the budget before a repository's items are reached.
    later: deque = deque()
    chrome: set = set()      # links on a root page: site navigation, repeated on every page
    visited: set = set()

    def cancelled() -> bool:
        if should_continue is not None and not should_continue():
            run.cancelled = True
            return True
        return False

    while (queue or later) and not cancelled():
        nid, expects_document = queue.popleft() if queue else later.popleft()
        node = g.nodes[nid]
        if nid in visited:
            continue
        if expects_document and run.documents_fetched >= limits.max_documents:
            node.notes.append('not fetched: the run’s document limit was reached')
            _skip(run, node, SkipReason.FILE_BUDGET, f'file budget ({limits.max_documents}) reached')
            continue
        if not expects_document and run.pages_fetched >= limits.max_pages:
            _skip(run, node, SkipReason.PAGE_BUDGET, f'page limit ({limits.max_pages}) reached')
            continue
        visited.add(nid)
        result = fetch(node.url)
        node.checked_at = now_iso()
        if not getattr(result, 'ok', False):
            node.status = NodeStatus.FETCH_FAILED
            node.skipped = SkipReason.FETCH_FAILED.value
            why = getattr(result, 'error', '') or f'HTTP {getattr(result, "status", 0)}'
            node.notes.append(f'could not be fetched ({why}); this says nothing about whether it exists')
            run.fetch_failures.append({'url': node.url, 'why': why})
            if expects_document:
                run.documents_fetched += 1
            else:
                run.pages_fetched += 1
            continue
        if not _is_html(result):
            run.documents_fetched += 1
            node.node_type = NodeType.DOCUMENT if node.node_type in (NodeType.LINK, NodeType.PAGE) else node.node_type
            node.status = NodeStatus.FETCHED
            g.record_content(node, getattr(result, 'content_hash', '') or '', getattr(result, 'content_type', ''))
            if getattr(result, 'truncated', False):
                node.notes.append(f'hashed on its first {limits.max_content_bytes} bytes')
            continue
        if expects_document and run.pages_fetched >= limits.max_pages:
            # Expected a file, got a page, and the page budget is spent. The fetch is charged to the file
            # budget that admitted it and the page is not read: a listing of pages must not read past the
            # page limit by looking like a listing of files.
            run.documents_fetched += 1
            node.notes.append('fetched: a page, not a file; not read, the run’s page limit was reached')
            _skip(run, node, SkipReason.PAGE_BUDGET, f'page limit ({limits.max_pages}) reached')
            continue
        run.pages_fetched += 1
        if not _on_estate(run, node.host) and not _OFF_ESTATE_REPOSITORY.search(f'{node.title} {node.context}'):
            # A page off the authority's site, reached as a link to hash: recorded, not read further.
            node.node_type = NodeType.PAGE if node.node_type is NodeType.LINK else node.node_type
            node.status = NodeStatus.READ
            node.skipped = SkipReason.LINKS_NOT_FOLLOWED.value
            node.notes.append('a page off the authority’s own site; recorded, its links not followed')
            continue
        _read_page(run, node, result, chrome, queue, later, registry)

    if search_hits:
        add_search_hits(run, search_hits, registry=registry)
    for post in social_posts or []:
        add_social_signal(run, post.get('url', ''), post.get('text', ''), registry=registry)
    if gateway is not None:
        classify_ambiguous(run, gateway)
    resolve_leads(run)
    run.ended_at = now_iso()
    return run


def _read_page(run: DiscoveryRun, node: SourceNode, result, chrome: set, queue: deque, later: deque,
               registry: TrustRegistry) -> None:
    g, limits = run.graph, run.limits
    base = getattr(result, 'final_url', '') or node.url
    links, title = extract_links(getattr(result, 'text', '') or '', base)
    if node.node_type is NodeType.LINK:
        node.node_type = NodeType.PAGE
    node.title = node.title or title
    is_root = node.node_type is NodeType.SITE_ROOT
    if is_root:
        chrome.update(url_key(l.url) for l in links if not l.unlinked)
    own = [l for l in links if l.unlinked or is_root or url_key(l.url) not in chrome]
    items = [l for l in own if not l.unlinked]
    # A root counts as read when it has any links (its navigation is all chrome by definition). One
    # with none at all is a page built by script: calling it read once made a site GovOS could not
    # see into look exhaustively searched.
    node.status = NodeStatus.READ if (items or (is_root and links)) else NodeStatus.READ_NO_LINKS
    if node.status is NodeStatus.READ_NO_LINKS:
        node.notes.append('read, but it lists nothing of its own; it may be rendered by script')
        node.skipped = SkipReason.SCRIPT_RENDERED.value

    heading_words = ' '.join([node.title, node.context, *[l.heading for l in items[:3]]])
    named_repository = bool(REPOSITORY_WORDS.search(heading_words)) or node.role in REPOSITORY_ROLES
    is_repository = not is_root and named_repository and len(items) >= 3
    if is_repository:
        node.node_type = NodeType.REPOSITORY
        node.notes.append(f'a repository of {len(items)} item(s)')
    archive = bool(re.search(r'\barchives?\b|\bold\b|\bprevious\b', heading_words, re.I))

    for link in own:
        if link.unlinked:
            if is_repository or node.role is not DocKind.UNKNOWN:
                node.listed_without_link.append({'text': link.text, 'context': link.context})
            continue
        role, hint, reason, vkind = classify_link(link.text, link.url, context=link.context,
                                                  parent_role=node.role, parent_is_repository=is_repository)
        # The authority's own accounts and channels are recorded (never crawled) whatever their link
        # says: "EPSC on X" names no document, but it is where the authority speaks.
        hub = is_hub_link(link.text, role) or is_social(link.url) or is_video(link.url)
        if not is_repository and not hub:
            run.skipped_out_of_scope += 1
            continue
        if len(g) >= limits.max_nodes and not g.get(link.url):
            run.frontier.append({'url': link.url, 'title': link.text, 'role': role.value,
                                 'skip': SkipReason.ITEM_BUDGET.value,
                                 'reason': f'node limit ({limits.max_nodes}) reached'})
            continue
        if node.source_class is not SourceClass.PRIMARY_OFFICIAL:
            edge = EdgeKind.REFERENCE_LINK
        elif is_repository:
            edge = EdgeKind.REPOSITORY_ITEM
        elif role in (DocKind.APPLICATION_PORTAL, DocKind.OTR_PORTAL):
            edge = EdgeKind.APPLICATION_LINK
        elif archive:
            edge = EdgeKind.OFFICIAL_ARCHIVE_LINK
        else:
            edge = EdgeKind.OFFICIAL_LINK
        # A file by its address, never by the listing it sits in: an item of an official repository
        # on someone else's site is still someone else's.
        cls, why = classify_source(link.url, estates=run.estates, via=edge, parent_class=node.source_class,
                                   role=role, is_document=hint is NodeType.DOCUMENT,
                                   registry=registry, authority=run.authority_name)
        owner, relationship = source_ownership(link.url, estates=run.estates, via=edge, parent_class=node.source_class)
        child, created = g.add(link.url, title=link.text, role=role, node_type=hint, source_class=cls,
                               class_reason=why, role_reason=reason, context=link.context,
                               video_kind=vkind, depth=node.depth + 1, authority=run.authority_name,
                               owner=owner, relationship=relationship)
        g.add_edge(node.id, child.id, edge, anchor_text=link.text, context=link.context)
        if cls is SourceClass.UNVERIFIED:
            child.status = NodeStatus.BLOCKED
            child.skipped = SkipReason.REFUSED_ADDRESS.value
            continue
        if not created:
            continue
        _schedule(run, node, child, queue, later, from_repository=is_repository)


def _on_estate(run: DiscoveryRun, host: str) -> bool:
    return any(same_estate(host, e) for e in run.estates)


#: Words that name an archive or repository: the only kind of off-estate page that may be read,
#: and only one hop from the authority's own page (a retired domain's old-papers archive).
_OFF_ESTATE_REPOSITORY = re.compile(
    r'\b(old|previous|past)\s+(year\s+)?(question\s+)?papers\b|\barchives?\b|\brepository\b|'
    r'\bold\s+(website|site|records)\b', re.I)

def _looks_like_document(child: SourceNode) -> bool:
    """A link expected to be a file: a known file type, or a notice headline rather than a menu label."""
    if child.node_type is NodeType.DOCUMENT:
        return True
    if child.role in {DocKind.UNKNOWN, DocKind.EXAM_PAGE, DocKind.OFFICIAL_PORTAL} | _SERVICE_ROLES:
        return False
    return is_headline(child.title)


def _schedule(run: DiscoveryRun, parent: SourceNode, child: SourceNode, queue: deque, later: deque, *,
              from_repository: bool) -> None:
    limits = run.limits
    if child.source_class is not SourceClass.PRIMARY_OFFICIAL:
        return
    if child.node_type in (NodeType.VIDEO, NodeType.SOCIAL, NodeType.PORTAL) or child.role in _SERVICE_ROLES:
        return
    if from_repository:
        # An item of a repository: fetched to hash it (it may turn out to be a page of its own).
        # Items one level beyond the depth limit are still read -- a repository at the limit is
        # useless without its items -- but nothing below them is.
        if child.depth > limits.max_depth + 1:
            _skip(run, child, SkipReason.DEPTH_LIMIT, f'depth limit ({limits.max_depth}) reached')
            return
        queue.append((child.id, True))
        return
    if _looks_like_document(child):
        later.append((child.id, True))
        return
    on_estate = _on_estate(run, child.host)
    if not on_estate and not (_on_estate(run, parent.host) and _OFF_ESTATE_REPOSITORY.search(child.title)):
        return          # off the estate: recorded, never crawled -- unless it is an archive one hop out
    if child.depth > limits.max_depth:
        if child.role in REPOSITORY_ROLES | {DocKind.UNKNOWN} or REPOSITORY_WORDS.search(child.title):
            _skip(run, child, SkipReason.DEPTH_LIMIT, f'depth limit ({limits.max_depth}) reached')
        return
    queue.append((child.id, False))


# ============================================================== supplements: search, social
def add_search_hits(run: DiscoveryRun, hits: list, *, registry: Optional[TrustRegistry] = None) -> None:
    """Search results as DISCOVERED_BY_SEARCH nodes. A hit on the authority's estate is official
    because of where it is, not because a search engine ranked it; anything else is classified by
    the trust rules and is never crawled."""
    registry = registry if registry is not None else TrustRegistry.load()
    for h in hits:
        url = getattr(h, 'url', '') or (h.get('url') if isinstance(h, dict) else '')
        title = getattr(h, 'title', '') or (h.get('title', '') if isinstance(h, dict) else '')
        if not url:
            continue
        role, hint, reason, vkind = classify_link(title, url)
        cls, why = classify_source(url, estates=run.estates, via=EdgeKind.DISCOVERED_BY_SEARCH, role=role,
                                   is_document=hint is NodeType.DOCUMENT, registry=registry,
                                   authority=run.authority_name)
        owner, relationship = source_ownership(url, estates=run.estates)
        node, _ = run.graph.add(url, title=title, role=role, node_type=hint, source_class=cls, class_reason=why,
                                role_reason=reason, video_kind=vkind, depth=0, owner=owner, relationship=relationship)
        run.graph.add_edge('', node.id, EdgeKind.DISCOVERED_BY_SEARCH, anchor_text=title, method='search')
        if cls is SourceClass.UNVERIFIED:
            node.status = NodeStatus.BLOCKED


#: What a lead says has happened, and the role an official source would have to show it.
_LEAD_PATTERNS = [
    (DocKind.ADMIT_CARD, re.compile(r'hall[\s-]*tickets?|admit\s*cards?|call\s*letters?', re.I)),
    (DocKind.ANSWER_KEY, re.compile(r'answer\s*keys?|\bkeys?\b\s+(out|released)', re.I)),
    (DocKind.RESULT, re.compile(r'\bresults?\b|merit\s+list|selection\s+list', re.I)),
    (DocKind.CORRIGENDUM, re.compile(r'corrigendum|extended|re-?opened|postponed|rescheduled', re.I)),
    (DocKind.NOTIFICATION, re.compile(r'notification|recruitment|vacanc', re.I)),
    (DocKind.SYLLABUS, re.compile(r'syllabus', re.I)),
]


def add_social_signal(run: DiscoveryRun, url: str, text: str, *, registry: Optional[TrustRegistry] = None) -> Optional[SourceNode]:
    """A social post or news item as a lead: DISCOVERY_ONLY, whoever posted it. It produces leads for
    official discovery -- never a fact. "Hall ticket released" becomes "look for an official admit-card
    notice", not HALL_TICKET_RELEASED = TRUE. A post on an account the authority's own site links to is
    recorded as LINKED_FROM_OFFICIAL: the link is a relationship, and the post is still not the authority's
    statement until an official source of that role is found."""
    registry = registry if registry is not None else TrustRegistry.load()
    if not url:
        return None
    account = urlparse(url)._replace(path='/'.join(urlparse(url).path.split('/')[:2]), query='').geturl()
    linked = run.graph.get(account)
    linked_account = linked is not None and any(e.kind.is_official for e in run.graph.parents(linked.id))
    cls, why = classify_source(url, estates=run.estates, role=DocKind.DISCOVERY_SIGNAL, registry=registry,
                               authority=run.authority_name)
    if cls is SourceClass.SECONDARY and is_social(url):
        cls = SourceClass.DISCOVERY_ONLY
    owner, relationship = source_ownership(url, estates=run.estates)
    if linked_account and relationship == 'INDEPENDENT':
        relationship = 'LINKED_FROM_OFFICIAL'
        why += '; a post on an account the authority’s own site links to'
    node, _ = run.graph.add(url, title=_norm(text)[:200], role=DocKind.DISCOVERY_SIGNAL, node_type=NodeType.SOCIAL,
                            source_class=cls, class_reason=why, depth=0, owner=owner, relationship=relationship)
    run.graph.add_edge(linked.id if linked_account else '', node.id, EdgeKind.DISCOVERY_SIGNAL,
                       anchor_text=_norm(text)[:200], method='social')
    for role, pattern in _LEAD_PATTERNS:
        if pattern.search(text or ''):
            run.leads.append({'role': role.value, 'text': _norm(text)[:200], 'source': node.url,
                              'sourceClass': cls.value, 'relationship': relationship, 'state': 'UNCONFIRMED'})
            break
    return node


def resolve_leads(run: DiscoveryRun) -> None:
    """Mark each lead confirmed only where an official source of that role was found. A lead that
    stays UNCONFIRMED is shown to nobody as a fact."""
    for lead in run.leads:
        role = DocKind(lead['role'])
        official = [n for n in run.graph.of_role(role)
                    if n.source_class is SourceClass.PRIMARY_OFFICIAL and n.node_type is not NodeType.SOCIAL]
        if official:
            lead['state'] = 'OFFICIAL_SOURCE_FOUND'
            lead['officialSources'] = [n.url for n in official[:5]]
        else:
            lead['state'] = 'UNCONFIRMED'


# ===================================================================== Claude, narrowly
def classify_ambiguous(run: DiscoveryRun, gateway) -> None:
    """Ask Claude, once per run, what the official links the rules could not classify are.

    Claude may only name a role from the vocabulary (validated by the gateway's schema and again
    here); it never sets a source class, never adds a node, and a failure leaves the role UNKNOWN
    -- withheld, not guessed. The links' text is passed as data inside the template's delimiters.
    """
    from ..claude_cli import Operation
    candidates = [n for n in run.graph.nodes.values()
                  if n.role is DocKind.UNKNOWN and n.source_class is SourceClass.PRIMARY_OFFICIAL
                  and n.node_type not in (NodeType.SITE_ROOT, NodeType.SOCIAL)][:run.limits.max_claude_links]
    if not candidates:
        run.claude = {'asked': 0, 'status': 'NOT_NEEDED'}
        return
    if not gateway.is_enabled():
        run.claude = {'asked': 0, 'status': 'CLAUDE_DISABLED', 'unclassified': len(candidates)}
        return
    result = gateway.run(Operation.CLASSIFY_SOURCE, {
        'authority': run.authority_name,
        'links': [{'index': i, 'text': n.title[:200], 'context': n.context[:160], 'path': urlparse(n.url).path[:160]}
                  for i, n in enumerate(candidates)]})
    if not result.ok:
        run.claude = {'asked': len(candidates), 'status': result.status.value, 'unclassified': len(candidates)}
        for n in candidates:
            n.notes.append('Claude could not classify it; its role stays unknown')
        return
    applied = 0
    allowed = {k.value for k in DocKind} - {DocKind.UNKNOWN.value}
    for row in result.output.get('links', []):
        idx, role = row.get('index'), row.get('role')
        if not isinstance(idx, int) or not 0 <= idx < len(candidates) or role not in allowed:
            continue
        node = candidates[idx]
        node.role = DocKind(role)
        node.role_reason = CLAUDE_ROLE_REASON
        if row.get('is_repository') and node.node_type in (NodeType.PAGE, NodeType.LINK):
            node.notes.append('Claude reads it as a repository page')
        applied += 1
    run.claude = {'asked': len(candidates), 'status': 'OK', 'classified': applied,
                  'templateVersion': result.template_version}


# =================================================================== exam admission
@dataclass
class Admission:
    """What one exam may take from a run: through the existing gate, and nothing more."""

    exam_id: str
    docs: list = field(default_factory=list)        # DiscoveredDoc, ready for the existing pipeline
    #: node id -> THIS_EXAM | THIS_EXAM_CYCLE_UNSTATED | THIS_EXAM_OTHER_CYCLE | OTHER_EXAM | NOT_THIS_EXAM | UNIDENTIFIABLE
    relation: dict = field(default_factory=dict)
    matched: dict = field(default_factory=dict)
    identified: set = field(default_factory=set)
    #: node ids whose listing names this exam but no cycle (the exam's cycle being known)
    cycle_unstated: set = field(default_factory=set)
    unidentifiable: set = field(default_factory=set)
    mismatches: list = field(default_factory=list)
    #: listing node id -> items on it that name this exam but carry no link ("listed, not obtainable")
    unlinked: dict = field(default_factory=dict)


#: The document kinds the existing extraction pipeline reads.
_PIPELINE_KINDS = frozenset({DocKind.NOTIFICATION, DocKind.CORRIGENDUM, DocKind.SYLLABUS, DocKind.EXAM_PATTERN,
                             DocKind.QUESTION_PAPER, DocKind.ANSWER_KEY, DocKind.ADMIT_CARD, DocKind.RESULT,
                             DocKind.CUTOFF, DocKind.CALENDAR, DocKind.EXAM_PAGE, DocKind.APPLICATION_PORTAL})

#: Words in a listing that say nothing about which recruitment an item belongs to: link verbs, file
#: words, languages, and the names of document kinds and listings themselves. "Addendum", "Keys" or
#: "Direct Recruitment" say what kind of thing an item is, not whose -- read as identifying, an untitled
#: addendum was judged to name another exam and ruled out of a search it could have answered.
_THIN = frozenset({'download', 'click', 'here', 'view', 'pdf', 'file', 'link', 'open', 'new', 'more', 'details',
                   'read', 'actual', 'shift', 'paper', 'papers', 'question', 'notice', 'english', 'telugu', 'hindi',
                   'urdu', 'version',
                   'addendum', 'addenda', 'corrigendum', 'corrigenda', 'notification', 'notifications', 'key',
                   'keys', 'result', 'results', 'recruitment', 'recruitments', 'direct', 'list', 'lists', 'web',
                   'note', 'notes', 'press', 'schedule', 'omr', 'downloads', 'latest', 'all', 'official',
                   'archive', 'archives', 'old', 'previous', 'past'})


def _identifying_words(text: str) -> list:
    """Words in a listing that could identify what an item is. Short codes count ("AE", "GS",
    "TPBO" are how authorities name recruitments); numbering, filler and language labels do not."""
    from .resolve import id_words
    return [w for w in id_words(text) if w not in _THIN and not re.fullmatch(r'[ivx]+|\d+\w*|[a-z]', w)]


def exam_words_for(query: str, official_name: str, *, authority_name: str = '', authority_domain: str = '') -> list:
    """This exam's distinctive words, without the authority's own (an authority's acronym names
    every exam it runs, so it identifies none of them)."""
    from .identity import ExamIdentity
    probe = ExamIdentity(exam_id='', query=query, official_name=official_name, year='',
                         authority_name=authority_name, authority_domain=authority_domain)
    own = probe.authority_aliases
    return [w for w in exam_aliases(query, official_name) if w not in own]


def admit_for_exam(run: DiscoveryRun, *, exam_id: str, exam_words: list, sibling_words: Optional[list] = None,
                   exam_cycle: str = '', designation=None) -> Admission:
    """Decide, with the existing `discover.gate()`, which official resources of a run belong to
    one exam. An item is matched on its own listing text, its list label and its address path --
    never on the repository it sits in, which is the authority's page for every exam it runs."""
    from .pyq import identity_from_text
    out = Admission(exam_id=exam_id)
    g = run.graph
    for node in g.nodes.values():
        # Every official item is judged, whatever role it was given: a misread role must never be
        # how an exam's own document goes unseen. Only the kinds the pipeline reads become docs.
        if node.source_class is not SourceClass.PRIMARY_OFFICIAL or node.role is DocKind.DISCOVERY_SIGNAL:
            continue
        if node.node_type in (NodeType.SITE_ROOT, NodeType.SOCIAL, NodeType.VIDEO, NodeType.REPOSITORY) \
                or node.duplicate_of:
            continue
        parents = [g.nodes[e.source_id] for e in g.parents(node.id) if e.source_id in g.nodes]
        specific = any(page_is_specific_to(p.title, p.url, exam_words, designation=designation)
                       for p in parents if p.node_type is not NodeType.REPOSITORY)
        text = f'{node.title} {node.context}'.strip()
        rel, matched, foreign = gate(text, node.url, exam_words=exam_words, page_is_exam_specific=specific,
                                     sibling_exam_words=sibling_words, designation=designation)
        cycle = identity_from_text(text, exam_id=exam_id).cycle
        if rel is not Relevance.REJECTED and exam_words:
            # The exam named but no cycle: it is not "this cycle's" on the authority's address alone. It
            # used to become THIS_EXAM, so an undated listing could prove a section of the current cycle.
            relation = ('THIS_EXAM_OTHER_CYCLE' if (exam_cycle and cycle and cycle != exam_cycle)
                        else 'THIS_EXAM_CYCLE_UNSTATED' if (exam_cycle and not cycle) else 'THIS_EXAM')
        elif foreign:
            relation = 'OTHER_EXAM'
        elif _identifying_words(text):
            relation = 'NOT_THIS_EXAM'
        else:
            relation = 'UNIDENTIFIABLE'
        out.relation[node.id] = relation
        out.matched[node.id] = list(matched or foreign)
        if relation == 'THIS_EXAM_CYCLE_UNSTATED':
            out.cycle_unstated.add(node.id)
        if relation in ('THIS_EXAM', 'THIS_EXAM_CYCLE_UNSTATED'):
            # Only THIS_EXAM is identified as this cycle's. A document whose listing names no cycle still goes
            # to the pipeline, whose own gates read the cycle from the document itself.
            if relation == 'THIS_EXAM':
                out.identified.add(node.id)
            parent = parents[0].url if parents else ''
            if node.role in _PIPELINE_KINDS:
                out.docs.append(DiscoveredDoc(url=node.url, kind=node.role, title=node.title[:160], relevance=rel,
                                              matched=list(matched), found_on=parent or '(authority discovery)'))
        elif relation == 'UNIDENTIFIABLE':
            out.unidentifiable.add(node.id)
        elif relation == 'OTHER_EXAM':
            out.mismatches.append({'url': node.url, 'title': node.title, 'names': list(foreign)})
    # An item listed without a link is judged the same way: if it names this exam, the authority
    # lists this exam's document and GovOS cannot obtain it -- never "not found".
    for hub in g.nodes.values():
        if hub.source_class is not SourceClass.PRIMARY_OFFICIAL or not hub.listed_without_link or not exam_words:
            continue
        for item in hub.listed_without_link:
            rel, _m, _f = gate(f"{item.get('text', '')} {item.get('context', '')}", '', exam_words=exam_words,
                               page_is_exam_specific=False, sibling_exam_words=sibling_words, designation=designation)
            if rel is not Relevance.REJECTED:
                out.unlinked.setdefault(hub.id, []).append(dict(item))
    return out


def mark_unreadable(run: DiscoveryRun, url: str, why: str = '') -> None:
    """Called by the reading pipeline when a fetched document has no readable text (a scan)."""
    node = run.graph.get(url)
    if node is not None:
        node.status = NodeStatus.UNREADABLE
        node.notes.append(why or 'fetched, but it has no readable text (a scan); it was not read')


# ========================================================================= projection
def _item(run: DiscoveryRun, node: SourceNode, admission: Optional[Admission] = None) -> dict:
    from .pyq import identity_from_text
    ident = identity_from_text(f'{node.title} {node.context}', exam_id='')
    relation = admission.relation.get(node.id, '') if admission else ''
    found_on = [run.graph.nodes[e.source_id] for e in run.graph.parents(node.id) if e.source_id in run.graph.nodes]
    return {
        'title': node.title or node.url, 'url': node.url, 'context': node.context, 'role': node.role.value,
        'section': SECTION_FOR_ROLE.get(node.role), 'sourceLabel': node.source_class.candidate_label,
        'sourceClass': node.source_class.value, 'status': node.status.value,
        'owner': node.owner, 'relationship': node.relationship,
        'obtainable': node.status not in (NodeStatus.FETCH_FAILED, NodeStatus.BLOCKED),
        'foundOn': found_on[0].url if found_on else '', 'foundOnTitle': (found_on[0].title if found_on else ''),
        'relation': relation,
        # Where the role came from: GovOS's rules, or only Claude's reading (never proof by itself).
        'roleFrom': 'CLAUDE' if role_by_claude(node) else 'RULES',
        'identity': {k: v for k, v in (('cycle', ident.cycle), ('stage', ident.stage), ('paper', ident.paper),
                                        ('session', ident.session)) if v},
        'duplicateOf': run.graph.nodes[node.duplicate_of].url if node.duplicate_of in run.graph.nodes else '',
    }


#: Listings whose having nothing for an exam is itself worth telling its candidate.
_ANSWERING_REPOSITORIES = frozenset({DocKind.QUESTION_PAPER, DocKind.ANSWER_KEY, DocKind.RESULT, DocKind.CUTOFF})

#: Links for an authority's own staff, not for candidates.
_STAFF_ONLY = re.compile(r'office\s+use|official\s+login|staff\s+login|admin(istrator)?\s+login|employee\s+login|'
                         r'intranet|e-?office', re.I)


def _serves_exam(run: DiscoveryRun, node: SourceNode, admission: Admission) -> bool:
    """Whether a candidate service may be offered on one exam's page.

    It may when its listing identifies this exam in this cycle (THIS_EXAM), or when it is the authority's
    own service for every recruitment. Sitting on the authority's site, in the same table as the exam,
    beside the words "Online application", or having been read as a portal does not make it this exam's.
    It is the authority's own service only when all of these hold:
      - its listing names no exam the gate can match and no other cycle of this one;
      - its own words or address make it that service. A role read from the row it sits in describes
        that row's record: a "Web note" beside "Online application" is that recruitment's notice;
      - the site links to it as a service, not only as an entry in a listing of recruitments;
      - its listing names no recruitment cycle ("06/2026 - GROUP-II SERVICES ... Apply Online").
    Anything else stays in the run for the audit, and is not offered on this exam's page."""
    from .pyq import identity_from_text
    relation = admission.relation.get(node.id, '')
    if relation == 'THIS_EXAM':
        return True
    if relation in ('OTHER_EXAM', 'THIS_EXAM_OTHER_CYCLE'):
        return False
    if classify_link(node.title, node.url)[0] is not node.role:
        return False
    if all(e.kind is EdgeKind.REPOSITORY_ITEM for e in run.graph.parents(node.id)):
        return False
    return not identity_from_text(f'{node.title} {node.context}', exam_id='').cycle


def project_for_exam(run: DiscoveryRun, *, exam_id: str, title: str, authority_name: str = '',
                     authority_domain: str = '', cycle: str = '', sibling_words: Optional[list] = None) -> dict:
    """The classified resources one exam's sections may show, read from a run.

    Only official and reviewed-trusted sources are offered as information; a secondary source is
    offered only as a labelled link; discovery-only leads and refused addresses never are. Section
    placement comes from the role (resource_roles.SECTION_FOR_ROLE): learning material is the only
    thing that reaches Resources. A registration or application service is offered only where it is
    this exam's or the authority's own for every recruitment (`_serves_exam`), never for its role alone."""
    words = exam_words_for(title, title, authority_name=authority_name, authority_domain=authority_domain)
    admission = admit_for_exam(run, exam_id=exam_id, exam_words=words, sibling_words=sibling_words, exam_cycle=cycle)
    g = run.graph
    repositories = []
    for repo in (n for n in g.nodes.values() if n.node_type is NodeType.REPOSITORY and n.source_class.candidate_visible):
        items = [g.nodes[e.target_id] for e in g.children(repo.id)
                 if e.kind is EdgeKind.REPOSITORY_ITEM and e.target_id in g.nodes]
        rows = [_item(run, n, admission) for n in items if not n.duplicate_of]
        mine = [r for r in rows if r['relation'] in ('THIS_EXAM', 'THIS_EXAM_CYCLE_UNSTATED', 'THIS_EXAM_OTHER_CYCLE')]
        # A listing reaches this exam's page when it lists something of this exam, or when it is
        # where this exam's papers, keys or results would be -- there "none of these is yours" is
        # itself the answer. An authority's departmental tests and form downloads are not shown.
        if not mine and repo.role not in _ANSWERING_REPOSITORIES:
            continue
        repositories.append({
            'title': repo.title or repo.url, 'url': repo.url, 'role': repo.role.value,
            'section': SECTION_FOR_ROLE.get(repo.role), 'sourceLabel': repo.source_class.candidate_label,
            'items': mine, 'itemCount': len(rows), 'listedWithoutLink': list(repo.listed_without_link),
            'itemsForThisExam': len(mine), 'status': repo.status.value,
            'note': (f'{len(mine)} of {len(rows)} item(s) name this exam.' if mine else
                     f'None of its {len(rows)} item(s) names this exam: each is identified by its own listing '
                     f'text, and these name other recruitments or nothing identifiable.'),
        })
    portals, guidance, learning = [], [], []
    seen_portals: set = set()
    for n in g.nodes.values():
        if not n.source_class.candidate_visible or n.duplicate_of or n.node_type is NodeType.SITE_ROOT:
            continue
        row = None
        if n.role in (DocKind.OTR_PORTAL, DocKind.APPLICATION_PORTAL, DocKind.OFFICIAL_PORTAL) and \
                n.source_class is SourceClass.PRIMARY_OFFICIAL:
            # A candidate service on the authority's own estate. A document that merely mentions an
            # application, a staff login and a second link with the same name are not portals; nor is
            # a service that belongs to another recruitment, or one that nothing shows is this exam's.
            key = ' '.join(n.title.lower().split())
            if (n.node_type is NodeType.DOCUMENT or not _on_estate(run, n.host) or _STAFF_ONLY.search(n.title)
                    or not key or key in seen_portals or not _serves_exam(run, n, admission)):
                continue
            seen_portals.add(key)
            row = _item(run, n, admission)
            portals.append(row)
        elif n.role in (DocKind.APPLICATION_GUIDE, DocKind.EXAM_GUIDE) and n.source_class.may_corroborate:
            row = _item(run, n, admission)
            row['label'] = ('Official guidance' if n.source_class is SourceClass.PRIMARY_OFFICIAL
                            else 'Practical guidance — not an official clause')
            guidance.append(row)
        elif is_learning(n.role) and (n.source_class.may_corroborate or (
                n.source_class.candidate_visible and any(e.kind.is_official for e in g.parents(n.id)))):
            # Learning material: official or trusted, or someone else's that the authority's own page
            # links to (its exam vendor's mock test) -- shown with its label, never as official.
            learning.append(_item(run, n, admission))
    cov = coverage_report(run, identified=admission.identified, unidentifiable=admission.unidentifiable,
                          identity_mismatches=admission.mismatches, unlinked=admission.unlinked,
                          relation=admission.relation)
    return {
        'examId': exam_id, 'runId': run.id, 'authorityName': run.authority_name, 'discoveredAt': run.ended_at,
        'repositories': repositories, 'portals': portals, 'practicalGuidance': guidance, 'learning': learning,
        'searchStates': cov['searchStates'], 'exhaustive': cov['exhaustive'],
        'coverage': {k: cov[k] for k in ('pagesFetched', 'officialResources', 'documentsFetched', 'skippedOutOfScope',
                                         'listedWithoutLink', 'exhaustive')} | {
            'fetchFailures': len(cov['fetchFailures']), 'unexplored': len(cov['remainingUnexploredOfficialLinks']),
            'pagesWithoutLinks': len(cov['pagesWithoutLinks']), 'skipped': dict(cov['skipped'])},
    }


def search_state(run: DiscoveryRun, role: DocKind, admission: Optional[Admission] = None) -> tuple[SearchState, str]:
    return role_search_state(run, role, identified=admission.identified if admission else None,
                             unidentifiable=admission.unidentifiable if admission else None,
                             unlinked=admission.unlinked if admission else None,
                             relation=admission.relation if admission else None)
