"""Official-domain search — the substrate the universal resolver stands on.

Discovering that "LIC AAO" is conducted by LIC at licindia.in, without anyone having written an
LIC connector, needs a way to find pages. That is the Claude CLI's DISCOVER_SOURCES operation
(web search and fetch, run server-side through the single gateway), followed by deterministic
validation (`tools.claude_cli.discovery`): URL syntax, a server-side-request guard, the host's
suffix, redirect-aware reachability and an identity hint. A URL Claude returns is only ever a
*candidate*; it is "official" because its host's suffix says so and the builder's identity gate
later agrees, never because Claude said so.

Trust classification is the rule the Trust Panel and `app.py` share:

A bare `.gov` is the **United States**; India's government uses `.gov.in` and `.nic.in`.
Accepting it meant a search for "LIC AAO" resolved the authority to epa.gov and then to
insurance.ca.gov -- the US Environmental Protection Agency and the California Department of
Insurance, offered as the conductors of an Indian recruitment examination.

When Claude cannot run discovery (disabled, CLI missing, not signed in, no web tools) this module
raises `SearchUnavailable`, and the caller reports that the authority could not be resolved. It
does **not** fall back to guessing an authority from the exam's name, and it never calls any other
search service.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from tools.claude_cli.discovery import (DiscoveryUnavailable, classify_url, discover, memo_get,
                                        memo_put)


class SearchUnavailable(RuntimeError):
    """Discovery could not run. Never silently downgraded to a guess."""


def classify(url: str) -> str:
    return classify_url(url)


@dataclass
class Hit:
    title: str
    url: str
    content: str
    trust: str

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or '').lower().replace('www.', '')


def search(query: str, *, max_results: int = 20, official_only: bool = True, gateway=None) -> list[Hit]:
    """Discover candidate pages for `query`, then enforce the scope ourselves.

    Claude's own scoping is advisory (a search can return coaching sites beside a notice), so the
    filter that matters is applied here, after the candidates come back and have been checked.
    """
    key = (query.strip().lower(), int(max_results), bool(official_only))
    cached = None if gateway is not None else memo_get(key)
    if cached is not None:
        return list(cached)
    try:
        manifest = discover(query, max_results=min(int(max_results), 12), official_only=official_only,
                            gateway=gateway)
    except DiscoveryUnavailable as exc:
        raise SearchUnavailable(
            f'Claude discovery is unavailable ({exc.status.value}). The universal resolver needs '
            f'discovery to find an authority it has no connector for; enable and sign in to the '
            f'Claude CLI (see CLAUDE_CLI_INTEGRATION.md), or name an exam whose authority already '
            f'has a connector.') from exc
    hits = [Hit(title=c.title, url=c.final_url or c.url, content=c.snippet or c.why_relevant, trust=c.trust)
            for c in manifest.candidates
            if not official_only or classify_url(c.final_url or c.url) == 'OFFICIAL']
    if gateway is None:
        memo_put(key, hits)
    return hits
