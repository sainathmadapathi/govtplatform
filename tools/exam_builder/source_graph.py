"""The source graph: everything authority source discovery found, and how it found it.

Exam discovery (discover.py) answers "which documents belong to this exam?". This layer answers
the question before it: "what does this authority publish, where, and what lies around it?" -- a
repository of old question papers, a one-time-registration portal, a legacy domain the authority
still links to, a walkthrough video, a social post saying a hall ticket is out. None of that is a
fact about an exam. It is a map of where facts may be found, and every exam-level fact still has
to come through the existing identity, extraction, evidence and publication gates.

    SourceNode   one resource, by normalised URL: what it is (role), what kind of thing it is
                 (node type), how far it can be trusted (source class) and what happened when
                 GovOS looked at it (status)
    SourceEdge   how one node was reached from another -- the provenance a candidate never sees
                 but an auditor must be able to follow
    DiscoveryRun one bounded traversal, with its limits, what it left unexplored and why

Officiality and trust are kept apart on purpose. A PDF on a retired domain that the authority's
current site links to is an official document reached by an OFFICIAL_LINK, even though its host
is not the authority's; a popular coaching site is never official however often it is right.

Nothing here names an authority or an exam.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
import uuid
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from .discover import DocKind

#: The one role vocabulary (discover.DocKind), named for what it means here.
ResourceRole = DocKind


# ======================================================================= vocabulary
class SourceClass(str, Enum):
    """How far a source may be trusted. Explicit, never a boolean.

    PRIMARY_OFFICIAL   the authority itself, or something it controls or links to as its own
    TRUSTED_SECONDARY  an external source GovOS reviewed and allows for named roles only
    SECONDARY          useful external information, not reviewed
    DISCOVERY_ONLY     a lead for finding resources (a social post); never shown as information
    UNVERIFIED         refused (an unsafe or malformed address); contributes nothing
    """

    PRIMARY_OFFICIAL = 'PRIMARY_OFFICIAL'
    TRUSTED_SECONDARY = 'TRUSTED_SECONDARY'
    SECONDARY = 'SECONDARY'
    DISCOVERY_ONLY = 'DISCOVERY_ONLY'
    UNVERIFIED = 'UNVERIFIED'

    @property
    def rank(self) -> int:
        """0 is the strongest. When one URL is reached two ways, the stronger reading is kept."""
        return list(SourceClass).index(self)

    @property
    def may_state_official_fact(self) -> bool:
        return self is SourceClass.PRIMARY_OFFICIAL

    @property
    def may_corroborate(self) -> bool:
        return self in (SourceClass.PRIMARY_OFFICIAL, SourceClass.TRUSTED_SECONDARY)

    @property
    def candidate_visible(self) -> bool:
        """May a candidate be shown this source at all (with its label)?"""
        return self in (SourceClass.PRIMARY_OFFICIAL, SourceClass.TRUSTED_SECONDARY, SourceClass.SECONDARY)

    @property
    def candidate_label(self) -> str:
        return CANDIDATE_LABELS[self]


#: Plain words for a candidate. No internal class names, no confidence jargon.
CANDIDATE_LABELS = {
    SourceClass.PRIMARY_OFFICIAL: 'Official source',
    SourceClass.TRUSTED_SECONDARY: 'Trusted secondary source',
    SourceClass.SECONDARY: 'Third-party source — not verified',
    SourceClass.DISCOVERY_ONLY: 'Community lead — not verified',
    SourceClass.UNVERIFIED: '',
}


class NodeType(str, Enum):
    SITE_ROOT = 'SITE_ROOT'
    PAGE = 'PAGE'
    REPOSITORY = 'REPOSITORY'       # a page that lists many resources of one role
    DOCUMENT = 'DOCUMENT'           # a file: PDF, document, archive
    PORTAL = 'PORTAL'               # a service: registration, application, login
    VIDEO = 'VIDEO'
    SOCIAL = 'SOCIAL'
    LINK = 'LINK'                   # recorded, not yet looked at; what it is is unknown


class EdgeKind(str, Enum):
    """How a node was reached. The smallest set that keeps provenance honest."""

    OFFICIAL_LINK = 'OFFICIAL_LINK'                  # an official page links to it
    OFFICIAL_ARCHIVE_LINK = 'OFFICIAL_ARCHIVE_LINK'  # ... from an archive or old-records page
    REPOSITORY_ITEM = 'REPOSITORY_ITEM'              # it is one item of an official repository
    APPLICATION_LINK = 'APPLICATION_LINK'            # an official page sends candidates there to apply
    REFERENCE_LINK = 'REFERENCE_LINK'                # a non-official page links to it
    DISCOVERED_BY_SEARCH = 'DISCOVERED_BY_SEARCH'    # a search engine returned it
    SECONDARY_REFERENCE = 'SECONDARY_REFERENCE'      # a secondary source cites it
    DISCOVERY_SIGNAL = 'DISCOVERY_SIGNAL'            # a social post or news item pointed at it

    @property
    def is_official(self) -> bool:
        return self in (EdgeKind.OFFICIAL_LINK, EdgeKind.OFFICIAL_ARCHIVE_LINK,
                        EdgeKind.REPOSITORY_ITEM, EdgeKind.APPLICATION_LINK)


class NodeStatus(str, Enum):
    DISCOVERED = 'DISCOVERED'        # seen as a link, not fetched
    READ = 'READ'                    # a page fetched and its links read
    READ_NO_LINKS = 'READ_NO_LINKS'  # fetched, but it carried no links (often script-rendered)
    FETCHED = 'FETCHED'              # a document's bytes fetched and hashed
    UNREADABLE = 'UNREADABLE'        # fetched, but its content could not be read (a scan, say)
    FETCH_FAILED = 'FETCH_FAILED'    # could not be fetched: a fact about the fetch, not the source
    BLOCKED = 'BLOCKED'              # the address was refused (unsafe or malformed)
    SKIPPED_LIMIT = 'SKIPPED_LIMIT'  # within scope, left unexplored because a limit was reached


class SkipReason(str, Enum):
    """Why a node was not read, recorded on the node. A node that was not read is a place the
    search did not look, whatever the reason -- never evidence that something is absent."""

    FILE_BUDGET = 'FILE_BUDGET'          # the run's file budget was used before it was fetched
    PAGE_BUDGET = 'PAGE_BUDGET'          # the run's page budget was used before it was read
    ITEM_BUDGET = 'ITEM_BUDGET'          # the run's item budget was full, so it was not even recorded
    DEPTH_LIMIT = 'DEPTH_LIMIT'          # it sits deeper than the run follows links
    SCRIPT_RENDERED = 'SCRIPT_RENDERED'  # read, but the page lists nothing of its own (built by script)
    FETCH_FAILED = 'FETCH_FAILED'        # it could not be fetched
    REFUSED_ADDRESS = 'REFUSED_ADDRESS'  # the address was refused as unsafe or malformed
    NOT_OPENED = 'NOT_OPENED'            # recorded, never opened (a service, or off the authority's site)
    LINKS_NOT_FOLLOWED = 'LINKS_NOT_FOLLOWED'  # a page opened, but nothing it links to was followed

    @property
    def coverage_key(self) -> str:
        return 'skipped_due_to_' + {'DEPTH_LIMIT': 'depth', 'SCRIPT_RENDERED': 'script_rendering',
                                    'REFUSED_ADDRESS': 'refused_address'}.get(self.value, self.value.lower())


# ============================================================================ URLs
_TRACKING = re.compile(r'^(utm_\w+|fbclid|gclid|mc_cid|mc_eid|igshid|ref_src)$', re.I)
_DEFAULT_PORTS = {'http': 80, 'https': 443}


def normalize_url(url: str) -> str:
    """The URL with what does not change the resource removed: fragment, default port, tracking
    parameters, a trailing slash on the path. Path and query keep their case -- some servers
    encode the file in the path (base64 tokens), and lowering it would name a different file."""
    p = urlparse((url or '').strip())
    if p.scheme.lower() not in ('http', 'https'):
        return (url or '').strip()
    host = (p.hostname or '').lower()
    port = p.port
    netloc = host if port in (None, _DEFAULT_PORTS.get(p.scheme.lower())) else f'{host}:{port}'
    path = p.path or '/'
    if len(path) > 1:
        path = path.rstrip('/') or '/'
    query = urlencode([(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True) if not _TRACKING.match(k)])
    return urlunparse((p.scheme.lower(), netloc, path, '', query, ''))


def url_key(url: str) -> str:
    """The identity of a resource for de-duplication: http and https, and a leading "www.", name
    the same resource on every site this was checked against."""
    n = urlparse(normalize_url(url))
    host = (n.hostname or '').lower()
    host = host[4:] if host.startswith('www.') else host
    return f'{host}{n.path}' + (f'?{n.query}' if n.query else '')


def node_id_for(url: str) -> str:
    return 'n-' + hashlib.sha256(url_key(url).encode('utf-8')).hexdigest()[:16]


# ========================================================================= records
@dataclass
class SourceNode:
    id: str
    url: str
    title: str = ''
    node_type: NodeType = NodeType.LINK
    role: DocKind = DocKind.UNKNOWN
    source_class: SourceClass = SourceClass.UNVERIFIED
    status: NodeStatus = NodeStatus.DISCOVERED
    host: str = ''
    authority: str = ''
    content_type: str = ''
    #: Hash of the bytes fetched (the first `max_content_bytes` of a large file).
    content_hash: str = ''
    #: When another URL served the same bytes, the node that was seen first.
    duplicate_of: str = ''
    depth: int = 0
    #: The heading or group label the link was listed under ("Old Question Papers", "1.AE.").
    context: str = ''
    class_reason: str = ''
    role_reason: str = ''
    #: For a video: STUDY_LECTURE / APPLICATION_WALKTHROUGH / EXAM_EXPLANATION / NEWS_UPDATE / OTHER.
    video_kind: str = ''
    #: What the item's own wording identifies (pyq.identity_from_text), never an exam it is assumed to be.
    identity: dict = field(default_factory=dict)
    #: Items a repository lists without a working link ("href=#"): listed, not obtainable.
    listed_without_link: list = field(default_factory=list)
    #: A SkipReason value when the node was not read or fetched; '' when it was, or never needed to be.
    skipped: str = ''
    #: Who runs the host: its registered domain ("tgpsc.gov.in", "manabadi.co.in").
    owner: str = ''
    #: How the source stands to the authority (source_trust.RELATIONSHIPS): OWNED_BY_AUTHORITY,
    #: GOVERNMENT_HOST, LINKED_FROM_OFFICIAL or INDEPENDENT. A link from an official page is a
    #: relationship, never ownership.
    relationship: str = ''
    notes: list = field(default_factory=list)
    first_seen_at: str = ''
    checked_at: str = ''

    def as_dict(self) -> dict:
        d = asdict(self)
        for k in ('node_type', 'role', 'source_class', 'status'):
            d[k] = getattr(self, k).value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'SourceNode':
        d = dict(d)
        d['node_type'] = NodeType(d.get('node_type', 'LINK'))
        d['role'] = _role(d.get('role', 'UNKNOWN'))
        d['source_class'] = SourceClass(d.get('source_class', 'UNVERIFIED'))
        d['status'] = NodeStatus(d.get('status', 'DISCOVERED'))
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: v for k, v in d.items() if k in known})


def _role(value: str) -> DocKind:
    try:
        return DocKind(value)
    except ValueError:
        return DocKind.UNKNOWN


@dataclass
class SourceEdge:
    source_id: str          # '' for a root, a search result or a signal: nothing GovOS read pointed at it
    target_id: str
    kind: EdgeKind
    anchor_text: str = ''
    context: str = ''
    #: crawl | seed | search | social | claude-classified
    method: str = 'crawl'
    discovered_at: str = ''

    def as_dict(self) -> dict:
        d = asdict(self)
        d['kind'] = self.kind.value
        return d

    @classmethod
    def from_dict(cls, d: dict) -> 'SourceEdge':
        d = dict(d)
        d['kind'] = EdgeKind(d['kind'])
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class DiscoveryLimits:
    """The bounds of one run. Discovery is never an open-ended crawl."""

    max_depth: int = 2              # links followed from a root
    max_pages: int = 25             # HTML pages fetched
    max_nodes: int = 600            # resources recorded
    max_documents: int = 40         # files fetched to hash
    max_content_bytes: int = 1_500_000
    timeout_seconds: float = 12.0
    #: fetch_checked follows at most this many redirects (fixed there; recorded here for the report).
    max_redirects: int = 4
    #: Ambiguous links Claude may be asked to classify, in one batched call.
    max_claude_links: int = 25

    def as_dict(self) -> dict:
        return asdict(self)


def now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


class SourceGraph:
    """Nodes by normalised URL, edges by (from, to, kind). One resource is one node however many
    ways it was reached; every way is kept as an edge."""

    def __init__(self) -> None:
        self.nodes: dict[str, SourceNode] = {}
        self.edges: list[SourceEdge] = []
        self._edge_keys: set = set()
        self._by_hash: dict[str, str] = {}

    def __len__(self) -> int:
        return len(self.nodes)

    def get(self, url: str) -> Optional[SourceNode]:
        return self.nodes.get(node_id_for(url))

    def add(self, url: str, **attrs) -> tuple[SourceNode, bool]:
        """(node, created). A URL seen again keeps its strongest reading: the stronger source class
        with its reason, a known role over UNKNOWN, a known type over LINK, a title over none."""
        nid = node_id_for(url)
        existing = self.nodes.get(nid)
        if existing is None:
            node = SourceNode(id=nid, url=normalize_url(url), first_seen_at=now_iso())
            for k, v in attrs.items():
                setattr(node, k, v)
            if not node.host:
                node.host = (urlparse(node.url).hostname or '').lower()
            self.nodes[nid] = node
            return node, True
        cls = attrs.get('source_class')
        if cls is not None and cls.rank < existing.source_class.rank:
            existing.source_class = cls
            existing.class_reason = attrs.get('class_reason', existing.class_reason)
            existing.relationship = attrs.get('relationship', existing.relationship)
        elif attrs.get('relationship') == 'LINKED_FROM_OFFICIAL' and existing.relationship in ('', 'INDEPENDENT'):
            # Reached again from the authority's own page: the relationship is recorded, the class is not raised.
            existing.relationship = 'LINKED_FROM_OFFICIAL'
        if attrs.get('owner') and not existing.owner:
            existing.owner = attrs['owner']
        role = attrs.get('role')
        if role is not None and existing.role is DocKind.UNKNOWN and role is not DocKind.UNKNOWN:
            existing.role = role
            existing.role_reason = attrs.get('role_reason', existing.role_reason)
        ntype = attrs.get('node_type')
        if ntype is not None and existing.node_type is NodeType.LINK and ntype is not NodeType.LINK:
            existing.node_type = ntype
        for k in ('title', 'context', 'video_kind', 'authority'):
            if attrs.get(k) and not getattr(existing, k):
                setattr(existing, k, attrs[k])
        if 'depth' in attrs:
            existing.depth = min(existing.depth, attrs['depth'])
        return existing, False

    def add_edge(self, source_id: str, target_id: str, kind: EdgeKind, **attrs) -> Optional[SourceEdge]:
        key = (source_id, target_id, kind)
        if key in self._edge_keys or source_id == target_id:
            return None
        self._edge_keys.add(key)
        edge = SourceEdge(source_id=source_id, target_id=target_id, kind=kind,
                          discovered_at=attrs.pop('discovered_at', '') or now_iso(), **attrs)
        self.edges.append(edge)
        return edge

    def record_content(self, node: SourceNode, content_hash: str, content_type: str = '') -> None:
        """Note what a node's bytes hash to. A second URL serving the same bytes is marked as a
        duplicate of the first, so one file reached through two addresses is counted once."""
        node.content_hash = content_hash
        if content_type:
            node.content_type = content_type
        if not content_hash:
            return
        first = self._by_hash.get(content_hash)
        if first and first != node.id:
            node.duplicate_of = first
        else:
            self._by_hash[content_hash] = node.id

    def parents(self, node_id: str) -> list[SourceEdge]:
        return [e for e in self.edges if e.target_id == node_id]

    def children(self, node_id: str) -> list[SourceEdge]:
        return [e for e in self.edges if e.source_id == node_id]

    def provenance(self, node_id: str, *, max_hops: int = 8) -> list[dict]:
        """The chain by which a node was first reached, root first: what a reviewer follows to
        check "where did this come from"."""
        chain, seen, current = [], set(), node_id
        while current and current not in seen and len(chain) < max_hops:
            seen.add(current)
            inbound = self.parents(current)
            if not inbound:
                break
            edge = inbound[0]
            parent = self.nodes.get(edge.source_id)
            chain.append({'from': parent.url if parent else '', 'kind': edge.kind.value,
                          'anchorText': edge.anchor_text, 'context': edge.context, 'method': edge.method})
            current = edge.source_id
        return list(reversed(chain))

    def of_role(self, role: DocKind) -> list[SourceNode]:
        return [n for n in self.nodes.values() if n.role is role]

    def as_dict(self) -> dict:
        return {'nodes': [n.as_dict() for n in self.nodes.values()], 'edges': [e.as_dict() for e in self.edges]}

    @classmethod
    def from_dict(cls, d: dict) -> 'SourceGraph':
        g = cls()
        for nd in d.get('nodes', []):
            node = SourceNode.from_dict(nd)
            g.nodes[node.id] = node
            if node.content_hash and not node.duplicate_of:
                g._by_hash.setdefault(node.content_hash, node.id)
        for ed in d.get('edges', []):
            edge = SourceEdge.from_dict(ed)
            g._edge_keys.add((edge.source_id, edge.target_id, edge.kind))
            g.edges.append(edge)
        return g


@dataclass
class DiscoveryRun:
    id: str = field(default_factory=lambda: 'run-' + uuid.uuid4().hex[:12])
    authority_name: str = ''
    #: The registered domains treated as the authority's own (a commission's site, its apply
    #: portal and its results host share one).
    estates: list = field(default_factory=list)
    roots: list = field(default_factory=list)
    limits: DiscoveryLimits = field(default_factory=DiscoveryLimits)
    graph: SourceGraph = field(default_factory=SourceGraph)
    started_at: str = field(default_factory=now_iso)
    ended_at: str = ''
    pages_fetched: int = 0
    documents_fetched: int = 0
    #: In-scope links a limit stopped GovOS from following: {url, role, reason}.
    frontier: list = field(default_factory=list)
    #: Links judged out of scope (site chrome, unrelated pages): counted, not recorded.
    skipped_out_of_scope: int = 0
    fetch_failures: list = field(default_factory=list)
    #: Things a social post or news item said, waiting for an official source: {role, text, source, state}.
    leads: list = field(default_factory=list)
    claude: dict = field(default_factory=dict)
    cancelled: bool = False
    notes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {'id': self.id, 'authorityName': self.authority_name, 'estates': list(self.estates),
                'roots': list(self.roots), 'limits': self.limits.as_dict(), 'graph': self.graph.as_dict(),
                'startedAt': self.started_at, 'endedAt': self.ended_at, 'pagesFetched': self.pages_fetched,
                'documentsFetched': self.documents_fetched, 'frontier': list(self.frontier),
                'skippedOutOfScope': self.skipped_out_of_scope, 'fetchFailures': list(self.fetch_failures),
                'leads': list(self.leads), 'claude': dict(self.claude), 'cancelled': self.cancelled,
                'notes': list(self.notes)}

    @classmethod
    def from_dict(cls, d: dict) -> 'DiscoveryRun':
        lim = d.get('limits') or {}
        return cls(id=d.get('id', ''), authority_name=d.get('authorityName', ''), estates=list(d.get('estates', [])),
                   roots=list(d.get('roots', [])),
                   limits=DiscoveryLimits(**{k: v for k, v in lim.items() if k in DiscoveryLimits.__dataclass_fields__}),
                   graph=SourceGraph.from_dict(d.get('graph') or {}), started_at=d.get('startedAt', ''),
                   ended_at=d.get('endedAt', ''), pages_fetched=d.get('pagesFetched', 0),
                   documents_fetched=d.get('documentsFetched', 0), frontier=list(d.get('frontier', [])),
                   skipped_out_of_scope=d.get('skippedOutOfScope', 0), fetch_failures=list(d.get('fetchFailures', [])),
                   leads=list(d.get('leads', [])), claude=dict(d.get('claude', {})), cancelled=bool(d.get('cancelled')),
                   notes=list(d.get('notes', [])))


# ======================================================================== coverage
#: For each role, the roles of the listings and items that could hold it. A question paper can sit on a
#: page of answer keys or of results (a commission's "Results, Keys & OMR Downloads" carries the master
#: papers its keys are published with); a corrigendum on a page of notifications.
_HUB_AFFINITY = {
    DocKind.QUESTION_PAPER: {DocKind.QUESTION_PAPER, DocKind.ANSWER_KEY, DocKind.RESULT},
    DocKind.ANSWER_KEY: {DocKind.ANSWER_KEY, DocKind.QUESTION_PAPER, DocKind.RESULT},
    DocKind.CORRIGENDUM: {DocKind.CORRIGENDUM, DocKind.NOTIFICATION},
    DocKind.NOTIFICATION: {DocKind.NOTIFICATION, DocKind.CORRIGENDUM},
    DocKind.RESULT: {DocKind.RESULT, DocKind.ANSWER_KEY},
    DocKind.CUTOFF: {DocKind.CUTOFF, DocKind.RESULT},
}

#: Services that belong to the whole authority, not to one exam: a registration portal serves every
#: recruitment, so asking whether it is "this exam's" is the wrong question.
AUTHORITY_WIDE_ROLES = frozenset({DocKind.OTR_PORTAL, DocKind.APPLICATION_PORTAL, DocKind.OFFICIAL_PORTAL})


class SearchState(str, Enum):
    """What a run can honestly say about one role. Never merged.

    NOT_FOUND_AFTER_DISCOVERY is the only state that says something is absent, and it is allowed only
    when every relevant listing and item the run discovered was read. SEARCH_INCOMPLETE is the state
    for "nothing GovOS read is this exam's, but places that could hold it were not read".
    """

    FOUND_VERIFIED = 'FOUND_VERIFIED'                    # found, read, and identified
    FOUND_AMBIGUOUS = 'FOUND_AMBIGUOUS'                  # found, but its identity is not established
    FOUND_UNREADABLE = 'FOUND_UNREADABLE'                # found, but nothing of it could be read
    NOT_FOUND_AFTER_DISCOVERY = 'NOT_FOUND_AFTER_DISCOVERY'  # every relevant discovered node was read
    SEARCH_INCOMPLETE = 'SEARCH_INCOMPLETE'              # some relevant nodes read, others not; none matched
    NOT_SEARCHED = 'NOT_SEARCHED'                        # no relevant listing was read


_HUB_TYPES = (NodeType.SITE_ROOT, NodeType.PAGE, NodeType.REPOSITORY)
_UNREAD = (NodeStatus.DISCOVERED, NodeStatus.READ_NO_LINKS, NodeStatus.SKIPPED_LIMIT, NodeStatus.FETCH_FAILED,
           NodeStatus.BLOCKED, NodeStatus.UNREADABLE)
#: Relations an item's own listing words can establish that rule it out without opening it.
_RULED_OUT = frozenset({'OTHER_EXAM', 'NOT_THIS_EXAM', 'THIS_EXAM_OTHER_CYCLE'})
_STATUS_SKIP = {NodeStatus.READ_NO_LINKS: SkipReason.SCRIPT_RENDERED, NodeStatus.FETCH_FAILED: SkipReason.FETCH_FAILED,
                NodeStatus.BLOCKED: SkipReason.REFUSED_ADDRESS, NodeStatus.UNREADABLE: SkipReason.FETCH_FAILED}
_SKIP_WORDS = {SkipReason.FILE_BUDGET: 'file budget', SkipReason.PAGE_BUDGET: 'page budget',
               SkipReason.ITEM_BUDGET: 'item budget', SkipReason.DEPTH_LIMIT: 'depth limit',
               SkipReason.SCRIPT_RENDERED: 'built by script', SkipReason.FETCH_FAILED: 'could not be fetched',
               SkipReason.REFUSED_ADDRESS: 'address refused', SkipReason.NOT_OPENED: 'not opened',
               SkipReason.LINKS_NOT_FOLLOWED: 'links not followed'}


def skip_reason(node: SourceNode) -> SkipReason:
    """Why a node that was not read was not read."""
    if node.skipped:
        try:
            return SkipReason(node.skipped)
        except ValueError:
            pass
    return _STATUS_SKIP.get(node.status, SkipReason.NOT_OPENED)


def links_not_followed(run: DiscoveryRun, node: SourceNode) -> bool:
    """A page the walk opened but went no further than: one off the authority's site (recorded, its links
    not followed), or one read with nothing on it kept -- "Click here" to a file names nothing the walk
    follows. Whatever it leads to was not reached, so it is never a listing read in full."""
    if node.node_type is not NodeType.PAGE or node.status is not NodeStatus.READ:
        return False
    return node.skipped == SkipReason.LINKS_NOT_FOLLOWED.value or not run.graph.children(node.id)


def _is_listing(run: DiscoveryRun, node: SourceNode) -> bool:
    """A listing is never ruled out by its title; a page the walk went no further than is an item."""
    return node.node_type in _HUB_TYPES and not links_not_followed(run, node)


def _reaches_a_file(run: DiscoveryRun, page: SourceNode) -> bool:
    return any(run.graph.nodes[e.target_id].node_type is NodeType.DOCUMENT
               and run.graph.nodes[e.target_id].status in (NodeStatus.FETCHED, NodeStatus.UNREADABLE)
               for e in run.graph.children(page.id) if e.target_id in run.graph.nodes)


def _relevant_hubs(run: DiscoveryRun, role: DocKind) -> list[SourceNode]:
    roles = _HUB_AFFINITY.get(role, {role})
    return [n for n in run.graph.nodes.values()
            if n.source_class is SourceClass.PRIMARY_OFFICIAL and n.node_type in _HUB_TYPES and n.role in roles]


def unsearched(run: DiscoveryRun, role: DocKind, *, relation: Optional[dict] = None) -> list[tuple]:
    """[(what, SkipReason)] for every relevant place a run discovered and did not read: a listing that
    could hold `role` and was not read in full, or an item that could be it and was not opened. An item
    whose own listing words name something else (`relation`) is ruled out by those words, read or not;
    a listing is never ruled out by its title, because its title does not say what it lists."""
    roles = _HUB_AFFINITY.get(role, {role})
    hubs = _relevant_hubs(run, role)
    on_hubs = {e.target_id for h in hubs for e in run.graph.children(h.id)}
    out = []
    for n in run.graph.nodes.values():
        # A page opened but not followed is as unread as one never fetched: what it leads to was not reached.
        unfollowed = links_not_followed(run, n)
        if n.source_class is not SourceClass.PRIMARY_OFFICIAL or n.duplicate_of or (n.status not in _UNREAD
                                                                                   and not unfollowed):
            continue
        if n.node_type in (NodeType.SOCIAL, NodeType.VIDEO, NodeType.PORTAL) or n.role in AUTHORITY_WIDE_ROLES:
            continue
        if n.role not in roles and n.id not in on_hubs:
            continue
        if not _is_listing(run, n) and relation and relation.get(n.id) in _RULED_OUT:
            continue
        out.append((n, SkipReason.LINKS_NOT_FOLLOWED if unfollowed else skip_reason(n)))
    # Items the run's item budget kept from being recorded at all: known only from the frontier.
    for f in run.frontier:
        if f.get('skip') == SkipReason.ITEM_BUDGET.value and f.get('role') in {r.value for r in roles}:
            out.append((f, SkipReason.ITEM_BUDGET))
    return out


def _unread_words(missing: list) -> str:
    counts: dict = {}
    for _, reason in missing:
        counts[reason] = counts.get(reason, 0) + 1
    return ', '.join(f'{n} {_SKIP_WORDS[r]}' for r, n in sorted(counts.items(), key=lambda kv: -kv[1]))


def role_search_state(run: DiscoveryRun, role: DocKind, *, identified: Optional[set] = None,
                      unidentifiable: Optional[set] = None, unlinked: Optional[dict] = None,
                      relation: Optional[dict] = None) -> tuple[SearchState, str]:
    """The state of one role across a run, with a reason in words.

    `identified` is the set of node ids the caller's identity check accepted for an exam,
    `unidentifiable` the ids whose own wording is too thin to judge ("Download", "Click here"),
    `unlinked` maps a listing's node id to the items on it that name the exam but have no link, and
    `relation` is the identity check's verdict per node. Without them the question is asked at
    authority level: an official node of the role counts as found.

    "Not found" is claimed only when every relevant listing and item the run discovered was read
    (see `unsearched`); a listing or item skipped for any reason -- a budget, the depth limit, a page
    built by script, a failed fetch -- makes the answer SEARCH_INCOMPLETE (or NOT_SEARCHED, when no
    relevant listing was read at all), never NOT_FOUND_AFTER_DISCOVERY.
    """
    official = [n for n in run.graph.of_role(role)
                if n.source_class is SourceClass.PRIMARY_OFFICIAL and n.node_type not in _HUB_TYPES]
    hubs = _relevant_hubs(run, role)
    # A listing read in full: a page the walk went no further than is not one, whatever its status says.
    read_hubs = [h for h in hubs if h.status is NodeStatus.READ and not links_not_followed(run, h)]
    exam_level = identified is not None and role not in AUTHORITY_WIDE_ROLES
    # A page of this role whose own listing names this exam is this exam's, found -- a paper's own page
    # that links to the PDF is no less the paper's than the PDF. The identity check still decides.
    pages_mine = [n for n in run.graph.of_role(role)
                  if exam_level and n.id in identified and n.node_type is NodeType.PAGE
                  and n.source_class is SourceClass.PRIMARY_OFFICIAL]
    if exam_level:
        # Anything on these listings that names the exam, whatever role it was read as, forbids a
        # "not found": the role may have been misread, the item cannot have been missed.
        listed = {e.target_id for h in hubs for e in run.graph.children(h.id)}
        named_elsewhere = [nid for nid in listed & identified if run.graph.nodes[nid].role is not role]
        if named_elsewhere and not pages_mine and not any(n.id in identified for n in official):
            read_as = sorted({run.graph.nodes[nid].role.value.lower().replace('_', ' ') for nid in named_elsewhere})
            return (SearchState.FOUND_AMBIGUOUS,
                    f'{len(named_elsewhere)} item(s) on these listings name this exam and were read as '
                    f'{" / ".join(read_as)}; a person should check whether any of them is one')
    if unlinked and role not in AUTHORITY_WIDE_ROLES and not pages_mine \
            and not any(n.id in (identified or set()) for n in official):
        listed = [i for h in hubs for i in unlinked.get(h.id, [])]
        if listed:
            return (SearchState.FOUND_UNREADABLE,
                    f'{len(listed)} item(s) naming this exam are listed by the authority without a link to the file')
    if official or pages_mine:
        if exam_level:
            mine = [n for n in official if n.id in identified]
            if mine:
                return SearchState.FOUND_VERIFIED, f'{len(mine)} identified as this exam'
            if pages_mine:
                unreached = [p for p in pages_mine if not _reaches_a_file(run, p)]
                return (SearchState.FOUND_VERIFIED,
                        f'{len(pages_mine)} identified as this exam, as a page on the authority’s site'
                        + (f'; GovOS did not reach the file behind {len(unreached)} of them' if unreached else ''))
            thin = [n for n in official if n.id in (unidentifiable or set())]
            if thin:
                return (SearchState.FOUND_AMBIGUOUS, f'{len(official)} item(s) found; none identified as this exam, '
                                                     f'and {len(thin)} name nothing that could identify them')
        else:
            if all(n.status in (NodeStatus.FETCH_FAILED, NodeStatus.UNREADABLE) for n in official):
                return SearchState.FOUND_UNREADABLE, f'{len(official)} found; none could be read'
            return SearchState.FOUND_VERIFIED, f'{len(official)} official item(s) found'
    missing = unsearched(run, role, relation=relation if exam_level else None)
    if missing:
        listings = sum(1 for what, _ in missing if isinstance(what, SourceNode) and _is_listing(run, what))
        others = len(missing) - listings
        what = ' and '.join(x for x in (f'{listings} listing(s)' if listings else '',
                                         f'{others} item(s)' if others else '') if x)
        if read_hubs:
            return (SearchState.SEARCH_INCOMPLETE,
                    f'{len(read_hubs)} relevant listing(s) read and nothing on them is this exam\'s, but {what} that '
                    f'could hold it were not read ({_unread_words(missing)})')
        return SearchState.NOT_SEARCHED, f'{what} that could hold it were not read ({_unread_words(missing)})'
    if read_hubs:
        if official:
            return (SearchState.NOT_FOUND_AFTER_DISCOVERY,
                    f'every relevant listing and item discovered was read ({len(read_hubs)} listing(s), '
                    f'{len(official)} item(s)); each item names something other than this exam')
        return (SearchState.NOT_FOUND_AFTER_DISCOVERY,
                f'every relevant listing discovered was read ({len(read_hubs)}); none lists one')
    if official:
        return (SearchState.NOT_SEARCHED, f'{len(official)} item(s) of this kind were seen outside any listing, each '
                                          f'naming something else; no listing that could hold it was read')
    return SearchState.NOT_SEARCHED, 'no official listing for this was found to read'


def coverage_report(run: DiscoveryRun, *, roles: Optional[list] = None, identified: Optional[set] = None,
                    unidentifiable: Optional[set] = None, identity_mismatches: Optional[list] = None,
                    unlinked: Optional[dict] = None, relation: Optional[dict] = None) -> dict:
    """What a run looked at, what it found, and what it did not get to. "Not found" and "never
    searched the right repository" must be distinguishable from this alone."""
    g = run.graph
    nodes = list(g.nodes.values())
    official = [n for n in nodes if n.source_class is SourceClass.PRIMARY_OFFICIAL]
    repositories = [n for n in nodes if n.node_type is NodeType.REPOSITORY]
    by_class: dict[str, int] = {}
    for n in nodes:
        by_class[n.source_class.value] = by_class.get(n.source_class.value, 0) + 1
    by_role: dict[str, int] = {}
    for n in official:
        if n.role is not DocKind.UNKNOWN:
            by_role[n.role.value] = by_role.get(n.role.value, 0) + 1
    unreadable = [n for n in nodes if n.status is NodeStatus.UNREADABLE]
    failed = [n for n in nodes if n.status is NodeStatus.FETCH_FAILED]
    no_links = [n for n in nodes if n.status is NodeStatus.READ_NO_LINKS]
    ambiguous = [n for n in official if n.role is DocKind.UNKNOWN and n.node_type not in _HUB_TYPES]
    listed_unlinked = sum(len(n.listed_without_link) for n in nodes)
    wanted = roles or [DocKind.NOTIFICATION, DocKind.CORRIGENDUM, DocKind.QUESTION_PAPER, DocKind.ANSWER_KEY,
                       DocKind.RESULT, DocKind.ADMIT_CARD, DocKind.SYLLABUS, DocKind.CUTOFF,
                       DocKind.APPLICATION_PORTAL, DocKind.OTR_PORTAL]
    states = {}
    for role in wanted:
        state, why = role_search_state(run, role, identified=identified, unidentifiable=unidentifiable,
                                       unlinked=unlinked, relation=relation)
        entry = {'state': state.value, 'reason': why}
        if state in (SearchState.SEARCH_INCOMPLETE, SearchState.NOT_SEARCHED):
            exam_level = identified is not None and role not in AUTHORITY_WIDE_ROLES
            missing = unsearched(run, role, relation=relation if exam_level else None)
            entry['notRead'] = {r.coverage_key: sum(1 for _, x in missing if x is r)
                                for r in SkipReason if any(x is r for _, x in missing)}
        states[role.value] = entry
    skipped: dict = {}
    for n in nodes:
        reason = skip_reason(n) if n.skipped else (SkipReason.LINKS_NOT_FOLLOWED if links_not_followed(run, n)
                                                   else None)
        if reason is not None:
            skipped[reason.coverage_key] = skipped.get(reason.coverage_key, 0) + 1
    budget_dropped = sum(1 for f in run.frontier if f.get('skip') == SkipReason.ITEM_BUDGET.value)
    if budget_dropped:
        skipped[SkipReason.ITEM_BUDGET.coverage_key] = budget_dropped
    exhaustive = not run.frontier and not failed and not no_links and not run.cancelled and not skipped
    return {
        'runId': run.id, 'authorityName': run.authority_name, 'startedAt': run.started_at, 'endedAt': run.ended_at,
        'rootsInspected': list(run.roots), 'pagesFetched': run.pages_fetched,
        'officialRepositories': [{'url': n.url, 'title': n.title, 'role': n.role.value,
                                  'items': sum(1 for e in g.children(n.id) if e.kind is EdgeKind.REPOSITORY_ITEM),
                                  'listedWithoutLink': len(n.listed_without_link), 'status': n.status.value}
                                 for n in repositories if n.source_class is SourceClass.PRIMARY_OFFICIAL],
        'officialResources': len(official), 'officialByRole': by_role, 'bySourceClass': by_class,
        'trustedSecondaryConsulted': by_class.get(SourceClass.TRUSTED_SECONDARY.value, 0),
        'documentsFetched': run.documents_fetched,
        'documentsRead': sum(1 for n in nodes if n.node_type is NodeType.DOCUMENT and n.status is NodeStatus.FETCHED),
        'unreadable': [{'url': n.url, 'title': n.title} for n in unreadable],
        'fetchFailures': [{'url': n.url, 'title': n.title, 'why': (n.notes or [''])[-1]} for n in failed],
        'pagesWithoutLinks': [{'url': n.url, 'title': n.title} for n in no_links],
        'ambiguous': [{'url': n.url, 'title': n.title} for n in ambiguous],
        'identityMismatches': list(identity_mismatches or []),
        'listedWithoutLink': listed_unlinked,
        'remainingUnexploredOfficialLinks': list(run.frontier),
        'skippedOutOfScope': run.skipped_out_of_scope,
        #: Nodes the run found and did not read, by why: skipped_due_to_file_budget, ..._page_budget,
        #: ..._item_budget, ..._depth, ..._script_rendering, ..._fetch_failed, ..._refused_address.
        'skipped': skipped,
        'leads': list(run.leads),
        'exhaustive': exhaustive,
        'searchStates': states,
        'limits': run.limits.as_dict(),
        'claude': dict(run.claude),
    }


# ======================================================================= persistence
class SourceGraphStore:
    """One row per run in SQLite (the store GovOS already uses). A run is never overwritten: it is
    the record of what one traversal actually saw."""

    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        with self._conn() as conn:
            init_source_tables(conn)

    @contextmanager
    def _conn(self):
        # Committed and closed every time: an unclosed handle keeps the file locked on Windows.
        conn = sqlite3.connect(self.db_path, timeout=30)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def save(self, run: DiscoveryRun, *, job_id: str = '', coverage: Optional[dict] = None) -> str:
        estate = (run.estates or [''])[0]
        with self._conn() as conn:
            conn.execute('INSERT INTO source_discovery_runs (id, estate, authority_name, started_at, ended_at, job_id, '
                         'node_count, run_json, coverage_json) VALUES (?,?,?,?,?,?,?,?,?)',
                         (run.id, estate, run.authority_name, run.started_at, run.ended_at, job_id, len(run.graph),
                          json.dumps(run.as_dict()), json.dumps(coverage or coverage_report(run))))
        return run.id

    def get(self, run_id: str) -> Optional[DiscoveryRun]:
        with self._conn() as conn:
            row = conn.execute('SELECT run_json FROM source_discovery_runs WHERE id = ?', (run_id,)).fetchone()
        return DiscoveryRun.from_dict(json.loads(row['run_json'])) if row else None

    def latest(self, estate: str) -> Optional[DiscoveryRun]:
        with self._conn() as conn:
            row = conn.execute('SELECT run_json FROM source_discovery_runs WHERE estate = ? '
                               'ORDER BY ended_at DESC, rowid DESC LIMIT 1', (estate,)).fetchone()
        return DiscoveryRun.from_dict(json.loads(row['run_json'])) if row else None

    def list(self, *, limit: int = 20) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute('SELECT id, estate, authority_name, started_at, ended_at, job_id, node_count, coverage_json '
                                'FROM source_discovery_runs ORDER BY rowid DESC LIMIT ?', (max(1, min(limit, 100)),)).fetchall()
        out = []
        for r in rows:
            cov = json.loads(r['coverage_json'] or '{}')
            out.append({'id': r['id'], 'estate': r['estate'], 'authorityName': r['authority_name'],
                        'startedAt': r['started_at'], 'endedAt': r['ended_at'], 'jobId': r['job_id'],
                        'nodes': r['node_count'], 'exhaustive': cov.get('exhaustive', False),
                        'repositories': len(cov.get('officialRepositories', []))})
        return out


def init_source_tables(conn: sqlite3.Connection) -> None:
    conn.execute('''CREATE TABLE IF NOT EXISTS source_discovery_runs (
        id TEXT PRIMARY KEY,
        estate TEXT NOT NULL DEFAULT '',
        authority_name TEXT DEFAULT '',
        started_at TEXT DEFAULT '',
        ended_at TEXT DEFAULT '',
        job_id TEXT DEFAULT '',
        node_count INTEGER DEFAULT 0,
        run_json TEXT NOT NULL,
        coverage_json TEXT DEFAULT '{}'
    )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_source_runs_estate ON source_discovery_runs(estate)')
