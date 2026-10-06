"""Source discovery: Claude proposes candidate pages, deterministic code decides what they are.

Claude (the gateway's DISCOVER_SOURCES operation, the only operation allowed web tools) may locate
candidate URLs. It never decides what is official. Every candidate then passes deterministic
checks owned by this module:

  1. URL syntax: http(s) only, no credentials, a real DNS name (never an IP or `localhost`), sane
     length, no control characters;
  2. a server-side-request guard: the host must resolve only to public addresses, so a discovered
     URL can never point GovOS at its own network;
  3. trust class from the host's suffix: `.gov.in` / `.nic.in` is OFFICIAL, an academic or
     statutory-research suffix is TRUSTED_PUBLIC, everything else UNVERIFIED. Trust is about the
     domain only; owning the right to publish a given exam's notice is established later by the
     builder's own identity gate, never here;
  4. reachability, following redirects hop by hop and re-checking every hop (a redirect to a
     private address, or off an official domain, is recorded and downgrades the candidate);
  5. an identity hint: do the page's own words contain the query's distinctive words?

The whole run is kept as a manifest (what was asked, what Claude returned, what each check
decided and why) so a discovery is auditable. Nothing here publishes anything.
"""
from __future__ import annotations

import hashlib

import ipaddress
import re
import socket
import ssl
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from html import unescape
from typing import Callable, Optional
from urllib.parse import urljoin, urlparse

from .audit import now_iso
from .client import get_gateway
from .schemas import ClaudeResult, InfraStatus, Operation

OFFICIAL_SUFFIXES = ('.gov.in', '.nic.in')
TRUSTED_SUFFIXES = ('.ac.in', '.edu', '.edu.in', '.res.in')
MAX_URL_LENGTH = 2048
MAX_REDIRECTS = 4
FETCH_TIMEOUT = 12.0
FETCH_MAX_BYTES = 1_500_000
_TRUST_RANK = {'OFFICIAL': 2, 'TRUSTED_PUBLIC': 1, 'UNVERIFIED': 0}

_GENERIC = frozenset('the and for with from official notification notice apply online website recruitment '
                     'exam examination services service commission board public details latest'.split())


class DiscoveryUnavailable(RuntimeError):
    """Discovery could not run (Claude disabled, CLI missing/unsupported/unauthenticated, no web
    tools). Never a statement about an authority; never silently replaced by a guess."""

    def __init__(self, status: InfraStatus, message: str = '') -> None:
        super().__init__(message or status.value)
        self.status = status


# ------------------------------------------------------------------------- URL checks
def classify_host(host: str) -> str:
    host = (host or '').lower().rstrip('.')
    if host.endswith(OFFICIAL_SUFFIXES):
        return 'OFFICIAL'
    if host.endswith(TRUSTED_SUFFIXES):
        return 'TRUSTED_PUBLIC'
    return 'UNVERIFIED'


def classify_url(url: str) -> str:
    return classify_host(urlparse(url).hostname or '')


_USERINFO = re.compile(r'(?<=//)[^/@\s]*@')


def redact_url(url: str) -> str:
    """`url` with any `user:password@` part replaced, for the manifest and the audit trail: a rejected
    candidate that embedded credentials must not have them stored verbatim."""
    return _USERINFO.sub('***@', url or '')


def validate_url_syntax(url: str) -> tuple[bool, str]:
    """(ok, reason). Syntax only; says nothing about whether the page exists or is official."""
    if not isinstance(url, str) or not url.strip():
        return False, 'empty URL'
    if len(url) > MAX_URL_LENGTH:
        return False, 'URL is too long'
    if re.search(r'[\x00-\x20\x7f]', url):
        return False, 'URL contains whitespace or control characters'
    try:
        parts = urlparse(url)
        port = parts.port
    except ValueError:
        return False, 'URL is malformed'
    if parts.scheme not in ('http', 'https'):
        return False, 'only http(s) URLs are accepted'
    if parts.username or parts.password:
        return False, 'URL carries credentials'
    host = (parts.hostname or '').lower().rstrip('.')
    if not host or '.' not in host:
        return False, 'URL has no public host name'
    try:
        ipaddress.ip_address(host)
        return False, 'URL names an IP address, not a host name'
    except ValueError:
        pass
    if re.fullmatch(r'0x[0-9a-f]*|[0-9]+', host.rsplit('.', 1)[-1]):      # 127.1, 0x7f.1, 10.1: legacy IPv4 forms
        return False, 'URL names an IP address, not a host name'
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal', '.lan')):
        return False, 'URL names a local host'
    if port not in (None, 80, 443):
        return False, 'URL uses a non-standard port'
    if not re.fullmatch(r'[a-z0-9.-]+', host):
        return False, 'URL host has unexpected characters'
    return True, ''


def resolves_public(host: str, resolver: Optional[Callable] = None) -> tuple[bool, str]:
    """Does every address `host` resolves to belong to the public internet?"""
    try:
        infos = (resolver or socket.getaddrinfo)(host, None)
    except OSError:
        return False, 'host name does not resolve'
    addrs = {i[4][0] for i in infos}
    if not addrs:
        return False, 'host name does not resolve'
    for addr in addrs:
        try:
            ip = ipaddress.ip_address(addr.split('%')[0])
        except ValueError:
            return False, 'host resolves to an unreadable address'
        if not ip.is_global:
            return False, 'host resolves to a private or reserved address'
    return True, ''


# ------------------------------------------------------------------------------ fetching
@dataclass
class FetchResult:
    ok: bool = False
    status: int = 0
    final_url: str = ''
    content_type: str = ''
    text: str = ''
    hops: list = field(default_factory=list)
    error: str = ''
    #: SHA-256 (first 24 hex) of the bytes read, so one file reached at two addresses is one file.
    content_hash: str = ''
    #: True when the body was longer than `max_bytes`: the hash then covers the first `max_bytes` only.
    truncated: bool = False
    #: The bytes read (at most `max_bytes`), only when the caller asked to keep them (`keep_body=True`):
    #: a caller that parses the document reads these, and never fetches the URL a second time.
    body: bytes = field(default=b'', repr=False)
    #: Why it failed, as a category: BLOCKED (an address refused before connecting), TLS (certificate or
    #: handshake), TIMEOUT, NETWORK, HTTP (a status >= 300 with no usable redirect), REDIRECTS (too many).
    error_kind: str = ''


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):                        # we follow redirects ourselves
        return None


def _error_kind(exc: BaseException) -> str:
    reason = getattr(exc, 'reason', exc)
    if isinstance(reason, (ssl.SSLError, ssl.CertificateError)) or isinstance(exc, (ssl.SSLError, ssl.CertificateError)):
        return 'TLS'
    if isinstance(reason, (socket.timeout, TimeoutError)) or isinstance(exc, (socket.timeout, TimeoutError)):
        return 'TIMEOUT'
    return 'NETWORK'


def fetch_checked(url: str, *, timeout: float = FETCH_TIMEOUT, max_bytes: int = FETCH_MAX_BYTES,
                  resolver: Optional[Callable] = None, keep_body: bool = False,
                  max_seconds: Optional[float] = None, headers: Optional[dict] = None) -> FetchResult:
    """GET `url`, following up to MAX_REDIRECTS redirects, re-validating every hop.

    Every hop must pass `validate_url_syntax` (http(s), port 80/443, no IP literal, no local name, no
    credentials) and `resolves_public` before anything connects to it. TLS certificates and host names are
    verified (the default context). `timeout` bounds each socket operation and `max_seconds` (default four
    times it) the whole download; at most `max_bytes` are read, and `truncated` says when there was more.
    With `keep_body` the bytes read are returned for the caller to parse, so it never fetches again."""
    out = FetchResult()
    deadline_budget = max_seconds if max_seconds is not None else timeout * 4
    ctx = ssl.create_default_context()
    opener = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=ctx))
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        ok, why = validate_url_syntax(current)
        if not ok:
            out.error, out.error_kind = f'blocked hop: {why}', 'BLOCKED'
            return out
        public, why = resolves_public(urlparse(current).hostname or '', resolver)
        if not public:
            out.error, out.error_kind = f'blocked hop: {why}', 'BLOCKED'
            return out
        out.hops.append(current)
        req = urllib.request.Request(current, headers={
            'User-Agent': 'Mozilla/5.0 (GovOS source check)', 'Accept': 'text/html,application/pdf,*/*;q=0.5',
            **(headers or {})})
        try:
            with opener.open(req, timeout=timeout) as resp:
                out.status = resp.getcode()
                out.final_url = current
                out.content_type = (resp.headers.get('Content-Type') or '').split(';')[0].strip().lower()
                # Read in chunks, one byte past the limit (so "exactly max_bytes" is not "truncated"), and
                # stop when the whole download overruns its time: a slow drip cannot hold the request.
                deadline = time.monotonic() + deadline_budget
                # read1 returns what has arrived (one socket read), where read(n) would block until n
                # bytes came -- so a server trickling bytes would never reach the deadline check.
                read_some = getattr(resp, 'read1', None) or resp.read
                chunks, got = [], 0
                while got <= max_bytes:
                    chunk = read_some(min(64 * 1024, max_bytes + 1 - got))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    got += len(chunk)
                    if time.monotonic() > deadline:
                        out.error, out.error_kind = 'download took too long', 'TIMEOUT'
                        return out
                body = b''.join(chunks)
                out.truncated = len(body) > max_bytes
                body = body[:max_bytes]
                out.ok = 200 <= out.status < 300
                out.content_hash = hashlib.sha256(body).hexdigest()[:24] if body else ''
                if keep_body:
                    out.body = body
                if 'html' in out.content_type or out.content_type.startswith('text/'):
                    out.text = body.decode('utf-8', 'replace')
                return out
        except urllib.error.HTTPError as e:
            if e.code in (301, 302, 303, 307, 308) and e.headers.get('Location'):
                # As urllib's own redirect handler does: a space in a Location is a %20.
                current = urljoin(current, e.headers['Location'].strip().replace(' ', '%20'))
                continue
            out.status, out.final_url, out.error, out.error_kind = e.code, current, f'HTTP {e.code}', 'HTTP'
            return out
        except Exception as e:                                  # noqa: BLE001
            out.final_url, out.error, out.error_kind = current, type(e).__name__, _error_kind(e)
            return out
    out.error, out.error_kind = 'too many redirects', 'REDIRECTS'
    return out


def _words(text: str) -> set:
    return {w for w in re.findall(r'[a-z0-9]{3,}', (text or '').lower()) if w not in _GENERIC}


def identity_hint(query: str, title: str, page_text: str) -> str:
    """MATCHED / WEAK / NOT_MATCHED / UNCHECKED: how much of the query's distinctive wording the
    page itself carries. Advisory only; the builder's identity gate is the real decision."""
    want = _words(query)
    if not want or not (page_text or title):
        return 'UNCHECKED'
    plain = unescape(re.sub(r'<[^>]+>', ' ', page_text or ''))[:40_000]
    have = _words(f'{title} {plain}')
    share = len(want & have) / len(want)
    return 'MATCHED' if share >= 0.6 else 'WEAK' if share >= 0.3 else 'NOT_MATCHED'


# ------------------------------------------------------------------------------ manifest
@dataclass
class Candidate:
    title: str = ''
    url: str = ''
    snippet: str = ''
    authority_name: str = ''
    document_kind: str = 'OTHER'
    why_relevant: str = ''
    trust: str = 'UNVERIFIED'
    syntax_ok: bool = False
    reachable: Optional[bool] = None
    http_status: int = 0
    final_url: str = ''
    final_trust: str = ''
    identity: str = 'UNCHECKED'
    reasons: list = field(default_factory=list)

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or '').lower().replace('www.', '')

    def as_dict(self) -> dict:
        return {'title': self.title, 'url': self.url, 'snippet': self.snippet,
                'authorityName': self.authority_name, 'documentKind': self.document_kind,
                'whyRelevant': self.why_relevant, 'trust': self.trust, 'syntaxOk': self.syntax_ok,
                'reachable': self.reachable, 'httpStatus': self.http_status,
                'finalUrl': self.final_url, 'finalTrust': self.final_trust,
                'identity': self.identity, 'reasons': list(self.reasons)}


@dataclass
class DiscoveryManifest:
    query: str
    started_at: str = ''
    ended_at: str = ''
    status: str = InfraStatus.OK.value
    message: str = ''
    template_version: str = ''
    job_id: str = ''
    #: What Claude returned, verbatim, before any check.
    raw_candidates: list = field(default_factory=list)
    candidates: list = field(default_factory=list)
    rejected: list = field(default_factory=list)
    searched_queries: list = field(default_factory=list)
    notes: str = ''
    web_activity: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {'query': self.query, 'startedAt': self.started_at, 'endedAt': self.ended_at,
                'status': self.status, 'message': self.message, 'templateVersion': self.template_version,
                'jobId': self.job_id, 'rawCandidates': self.raw_candidates,
                'candidates': [c.as_dict() for c in self.candidates], 'rejected': self.rejected,
                'searchedQueries': self.searched_queries, 'notes': self.notes,
                'webActivity': self.web_activity,
                'note': 'Every URL here was proposed by Claude and then checked deterministically. '
                        'None is official because Claude said so.'}


def _check(candidate: Candidate, query: str, fetch: Callable, classify: Callable = classify_url) -> Candidate:
    result = fetch(candidate.url)
    candidate.reachable = bool(result.ok)
    candidate.http_status = result.status
    candidate.final_url = result.final_url or candidate.url
    candidate.final_trust = classify(candidate.final_url)
    if not result.ok:
        candidate.reasons.append(f'not reachable ({result.error or result.status})')
        return candidate
    if candidate.final_trust != candidate.trust:
        candidate.reasons.append(f'redirects from a {candidate.trust} host to a {candidate.final_trust} host')
        if _TRUST_RANK.get(candidate.final_trust, 0) < _TRUST_RANK.get(candidate.trust, 0):
            candidate.trust = candidate.final_trust                   # a redirect may lower trust, never raise it
    if not (result.text or '').strip():
        # A PDF or other non-text file: the server confirmed it is reachable but did not read it, so its
        # title alone says nothing about whether it belongs to this exam. Saying so beats a misleading
        # NOT_MATCHED; the builder reads the document properly and decides identity itself.
        candidate.identity = 'UNREAD'
        candidate.reasons.append('reachable, but its text was not read (not an HTML page); identity unchecked')
        return candidate
    candidate.identity = identity_hint(query, candidate.title, result.text)
    return candidate


def discover(query: str, *, max_results: int = 8, official_only: bool = True, verify: bool = True,
             gateway=None, fetch: Optional[Callable] = None, job_id: str = '',
             classify: Optional[Callable] = None) -> DiscoveryManifest:
    """Run one discovery. Raises `DiscoveryUnavailable` when Claude could not run it; returns a
    manifest (possibly with no candidates) when it ran. `classify` maps a URL to its trust class
    (default: the host-suffix rule); the Trust Panel passes the app's richer statutory-host list."""
    gateway = gateway or get_gateway()
    fetch = fetch or fetch_checked
    classify = classify or classify_url
    manifest = DiscoveryManifest(query=query, started_at=now_iso(), job_id=job_id)
    hints = list(OFFICIAL_SUFFIXES) if official_only else []
    result: ClaudeResult = gateway.run(Operation.DISCOVER_SOURCES, {
        'query': query, 'max_results': max_results, 'domain_hints': hints}, job_id=job_id)
    manifest.template_version = result.template_version
    manifest.web_activity = {k: result.stats.get(k, 0) for k in ('webSearchRequests', 'webFetchRequests', 'turns')}
    if not result.ok:
        manifest.status, manifest.message = result.status.value, result.message
        manifest.ended_at = now_iso()
        if result.status is InfraStatus.CANCELLED:
            return manifest
        raise DiscoveryUnavailable(result.status, result.message)

    out = result.output or {}
    manifest.searched_queries = list(out.get('searched_queries', []))
    manifest.notes = out.get('notes', '')
    raw_candidates = list(out.get('candidates', []))
    manifest.raw_candidates = [dict(r, url=redact_url(r.get('url') or '')) if isinstance(r, dict) else r
                               for r in raw_candidates]
    seen: set = set()
    pending: list[Candidate] = []
    for raw in raw_candidates[:max(1, max_results)]:
        c = Candidate(title=raw.get('title', ''), url=(raw.get('url') or '').strip(),
                      snippet=raw.get('snippet', ''), authority_name=raw.get('authority_name', ''),
                      document_kind=raw.get('document_kind', 'OTHER'), why_relevant=raw.get('why_relevant', ''))
        ok, why = validate_url_syntax(c.url)
        c.syntax_ok = ok
        if not ok:
            manifest.rejected.append({'url': redact_url(c.url)[:200], 'reasons': [why]})
            continue
        key = c.url.split('#')[0]
        if key in seen:
            manifest.rejected.append({'url': redact_url(c.url)[:200], 'reasons': ['duplicate of an earlier candidate']})
            continue
        seen.add(key)
        c.trust = classify(c.url)
        if official_only and c.trust != 'OFFICIAL':
            manifest.rejected.append({'url': redact_url(c.url)[:200], 'reasons': [f'{c.trust} host; official-only scope']})
            continue
        pending.append(c)

    if verify and pending:
        with ThreadPoolExecutor(max_workers=4) as pool:
            checked = list(pool.map(lambda c: _check(c, query, fetch, classify), pending))
    else:
        checked = pending
    for c in checked:
        if verify and c.reachable is False:
            manifest.rejected.append({'url': redact_url(c.url)[:200], 'reasons': c.reasons})
        elif official_only and c.trust != 'OFFICIAL':              # it redirected off the official domain
            manifest.rejected.append({'url': redact_url(c.url)[:200], 'reasons': c.reasons})
        else:
            manifest.candidates.append(c)
    manifest.ended_at = now_iso()
    return manifest


# --------------------------------------------------------------------- a short-lived memo
_MEMO: dict = {}
_MEMO_LOCK = threading.Lock()
MEMO_TTL_SECONDS = 600.0


def memo_get(key):
    with _MEMO_LOCK:
        hit = _MEMO.get(key)
        if hit and time.monotonic() < hit[0]:
            return hit[1]
        _MEMO.pop(key, None)
    return None


def memo_put(key, value) -> None:
    with _MEMO_LOCK:
        _MEMO[key] = (time.monotonic() + MEMO_TTL_SECONDS, value)
        if len(_MEMO) > 200:
            _MEMO.pop(next(iter(_MEMO)))


def memo_clear() -> None:
    with _MEMO_LOCK:
        _MEMO.clear()
