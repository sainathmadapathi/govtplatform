"""Which class a discovered source belongs to, decided by rules a person can read.

Two questions are kept apart:

  * officiality -- is this the authority, or something the authority itself points at as its own?
    Decided by where the source sits (the authority's estate) and how it was reached (an
    OFFICIAL_LINK from an official page). A PDF on a retired domain that the authority's current
    site links to is official; a coaching site is not, however often it is right.
  * trust -- may an external source be used, and for what? Decided only by a reviewed
    `SourceTrustProfile`. Popularity is never trust: there is no rule here that elevates a site
    because many people use it, and the profile file ships empty. A profile is added by a person,
    with a reason, for named roles, and can be revoked.

Nothing here names an authority, an exam or a website.
"""
from __future__ import annotations

import io
import json
import os
from dataclasses import asdict, dataclass, field
from typing import Optional
from urllib.parse import urlparse

from ..claude_cli.discovery import classify_url, validate_url_syntax
from ..exam_authoring.sources import estate_of, same_estate
from .discover import DocKind
from .source_graph import EdgeKind, SourceClass

DEFAULT_PROFILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'source_trust_profiles.json')

#: Hosts whose pages are accounts and posts, not publications.
SOCIAL_HOSTS = frozenset({'twitter.com', 'x.com', 'facebook.com', 'fb.com', 'instagram.com', 't.me', 'telegram.me',
                          'telegram.org', 'whatsapp.com', 'linkedin.com', 'threads.net', 'kooapp.com'})
VIDEO_HOSTS = frozenset({'youtube.com', 'youtu.be', 'm.youtube.com'})

REVIEW_STATUSES = ('REVIEWED', 'PENDING', 'REVOKED')


def bare_host(url_or_host: str) -> str:
    h = (urlparse(url_or_host).hostname if '//' in (url_or_host or '') else url_or_host) or ''
    h = h.lower().strip('.')
    return h[4:] if h.startswith('www.') else h


def _host_in(host: str, hosts: frozenset) -> bool:
    return host in hosts or any(host.endswith('.' + h) for h in hosts)


def is_social(url: str) -> bool:
    return _host_in(bare_host(url), SOCIAL_HOSTS)


def is_video(url: str) -> bool:
    return _host_in(bare_host(url), VIDEO_HOSTS)


@dataclass
class SourceTrustProfile:
    """A reviewed decision to let an external source contribute, for named roles only."""

    domain: str
    source_class: str = SourceClass.TRUSTED_SECONDARY.value
    #: Authority estates or names it is trusted for; empty means any authority.
    authority_coverage: list = field(default_factory=list)
    #: Roles it may contribute (DocKind values). Empty means none: a profile must say what it is for.
    permitted_roles: list = field(default_factory=list)
    review_status: str = 'PENDING'
    last_reviewed: str = ''
    reviewed_by: str = ''
    notes: str = ''
    #: What the classification was based on: pages read, the reviewer's checks.
    evidence: list = field(default_factory=list)

    def problems(self) -> list[str]:
        out = []
        if not self.domain or '/' in self.domain or ' ' in self.domain:
            out.append('domain must be a bare host name')
        if self.source_class not in (SourceClass.TRUSTED_SECONDARY.value, SourceClass.SECONDARY.value,
                                     SourceClass.DISCOVERY_ONLY.value):
            out.append('a profile may only classify a source as TRUSTED_SECONDARY, SECONDARY or DISCOVERY_ONLY; '
                       'officiality comes from the authority, never from a profile')
        if self.review_status not in REVIEW_STATUSES:
            out.append(f'review_status must be one of {REVIEW_STATUSES}')
        known = {k.value for k in DocKind}
        bad = [r for r in self.permitted_roles if r not in known]
        if bad:
            out.append(f'unknown roles: {bad}')
        if self.source_class == SourceClass.TRUSTED_SECONDARY.value and not self.permitted_roles:
            out.append('a trusted profile must name the roles it is trusted for')
        if self.review_status == 'REVIEWED' and not (self.last_reviewed and self.reviewed_by and (self.notes or self.evidence)):
            out.append('a reviewed profile must record when, by whom and on what basis')
        return out

    def matches(self, host: str) -> bool:
        d = bare_host(self.domain)
        h = bare_host(host)
        return bool(d) and (h == d or h.endswith('.' + d))

    def covers(self, authority: str, estates: list) -> bool:
        if not self.authority_coverage:
            return True
        cov = {c.lower() for c in self.authority_coverage}
        return bool(authority and authority.lower() in cov) or any((e or '').lower() in cov for e in estates)

    def as_dict(self) -> dict:
        return asdict(self)


class TrustRegistry:
    """The reviewed profiles, loaded from a JSON file that ships empty. Invalid entries are refused
    and reported, never silently half-applied."""

    def __init__(self, profiles: Optional[list] = None) -> None:
        self.profiles: list[SourceTrustProfile] = []
        self.rejected: list[dict] = []
        for p in profiles or []:
            self.add(p)

    def add(self, profile) -> bool:
        p = profile if isinstance(profile, SourceTrustProfile) else SourceTrustProfile(
            **{k: v for k, v in dict(profile).items() if k in SourceTrustProfile.__dataclass_fields__})
        problems = p.problems()
        if problems:
            self.rejected.append({'domain': p.domain, 'problems': problems})
            return False
        self.profiles.append(p)
        return True

    @classmethod
    def load(cls, path: str = DEFAULT_PROFILE_PATH) -> 'TrustRegistry':
        try:
            with io.open(path, encoding='utf-8') as fh:
                data = json.load(fh)
        except (OSError, ValueError):
            return cls()
        return cls(list(data.get('profiles') or []))

    def for_host(self, host: str) -> Optional[SourceTrustProfile]:
        live = [p for p in self.profiles if p.review_status != 'REVOKED' and p.matches(host)]
        # The most specific profile wins: news.example.com over example.com.
        return max(live, key=lambda p: len(p.domain), default=None)


#: How a source stands to the authority. Ownership and linking are different things: an authority's
#: page linking to a URL says the authority points at it, never that the authority runs it.
RELATIONSHIPS = ('OWNED_BY_AUTHORITY',    # on the authority's own registered domain(s)
                 'GOVERNMENT_HOST',       # a government domain (.gov.in, .nic.in, ...) the authority links to
                 'LINKED_FROM_OFFICIAL',  # someone else's host, linked from the authority's own page
                 'INDEPENDENT')           # reached any other way (search, a secondary source, a post)


def _officially_linked(via: Optional[EdgeKind], parent_class: Optional[SourceClass]) -> bool:
    return parent_class is SourceClass.PRIMARY_OFFICIAL and via is not None and via.is_official


def source_ownership(url: str, *, estates: list, via: Optional[EdgeKind] = None,
                     parent_class: Optional[SourceClass] = None) -> tuple:
    """(owner, relationship) for one source: who runs its host, and how it stands to the authority."""
    host = bare_host(url)
    owner = estate_of(host) if host else ''
    if host and any(same_estate(host, e) for e in estates if e):
        return owner, 'OWNED_BY_AUTHORITY'
    linked = _officially_linked(via, parent_class)
    if linked and classify_url(url) == 'OFFICIAL':
        return owner, 'GOVERNMENT_HOST'
    return owner, 'LINKED_FROM_OFFICIAL' if linked else 'INDEPENDENT'


def classify_source(url: str, *, estates: list, via: Optional[EdgeKind] = None,
                    parent_class: Optional[SourceClass] = None, role: DocKind = DocKind.UNKNOWN,
                    is_document: bool = False, registry: Optional[TrustRegistry] = None,
                    authority: str = '') -> tuple[SourceClass, str]:
    """(class, reason in words) for one source. Deterministic; Claude has no say in it.

    PRIMARY_OFFICIAL requires the host itself to qualify: the authority's own domain, or a government
    domain the authority's page links to (a retired or sister domain of the authority). Nothing else is
    official, whatever links to it and whatever it is -- a page, a PDF, a channel or an account. A file
    on someone else's host that the authority links to is that someone's file, LINKED_FROM_OFFICIAL
    (see `source_ownership`): a reviewed source's file stays TRUSTED_SECONDARY, a social post stays a
    lead, anything else is SECONDARY. `is_document` no longer bears on officiality; it is kept so callers
    need not change.
    """
    ok, why = validate_url_syntax(url)
    if not ok:
        return SourceClass.UNVERIFIED, f'the address was refused: {why}'
    host = bare_host(url)
    if any(same_estate(host, e) for e in estates if e):
        return SourceClass.PRIMARY_OFFICIAL, 'on the authority’s own site'

    officially_linked = _officially_linked(via, parent_class)
    if officially_linked and classify_url(url) == 'OFFICIAL':
        return (SourceClass.PRIMARY_OFFICIAL,
                f'a government site ({estate_of(host)}) the authority’s own page links to — a retired or sister '
                f'domain still counts as official when the authority itself points at it')
    linked_note = '; the authority’s own page links to it, which does not make it the authority’s' if officially_linked else ''

    profile = (registry or TrustRegistry()).for_host(host)
    if profile is not None and profile.review_status == 'REVIEWED' and profile.covers(authority, estates):
        if profile.source_class != SourceClass.TRUSTED_SECONDARY.value:
            return (SourceClass(profile.source_class),
                    f'classified by a reviewed profile ({profile.notes or profile.domain}){linked_note}')
        if role.value in profile.permitted_roles:
            return (SourceClass.TRUSTED_SECONDARY,
                    f'a reviewed trusted source for {role.value.lower().replace("_", " ")}{linked_note}')
        return (SourceClass.SECONDARY,
                f'trusted only for {", ".join(r.lower().replace("_", " ") for r in profile.permitted_roles)}, '
                f'not for this{linked_note}')

    if is_social(url):
        return SourceClass.DISCOVERY_ONLY, f'a social account or post: a lead, not a source{linked_note}'
    if officially_linked:
        return SourceClass.SECONDARY, f'run by {estate_of(host) or "someone else"}{linked_note}'
    if classify_url(url) == 'OFFICIAL':
        return SourceClass.SECONDARY, 'a government site, but not this authority’s, and not linked by it'
    return SourceClass.SECONDARY, 'an external site with no reviewed trust profile'
