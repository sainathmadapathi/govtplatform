"""Official-domain search — the substrate the universal resolver stands on.

Discovering that "LIC AAO" is conducted by LIC at licindia.in, without anyone having
written an LIC connector, needs a search engine. This wraps the same Tavily pipeline the
Trust Panel uses, with the same domain classification, so the two halves of the product
agree on what "official" means.

The key lives in the gitignored `.env` and the user puts it there themselves. Without it
this module raises `SearchUnavailable` and the caller reports that the authority could not
be resolved — it does **not** fall back to guessing an authority from the exam's name.
"""
from __future__ import annotations

import io
import json
import os
import re
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from urllib.parse import urlparse

TAVILY_URL = os.environ.get('TAVILY_BASE_URL', 'https://api.tavily.com') + '/search'

#: Same rule as app.py's _classify_trust. Kept in one expression so the two cannot drift
#: apart silently; if app.py's list grows, mirror it here.
_OFFICIAL_SUFFIXES = ('.gov.in', '.nic.in', '.gov')
_TRUSTED_SUFFIXES = ('.ac.in', '.edu', '.edu.in', '.res.in')


class SearchUnavailable(RuntimeError):
    """No API key, or the search service refused. Never silently downgraded to a guess."""


def _load_key() -> str:
    key = os.environ.get('TAVILY_API_KEY', '')
    if key:
        return key
    try:
        env = io.open(os.path.join(os.getcwd(), '.env'), encoding='utf-8').read()
    except OSError:
        return ''
    m = re.search(r'^\s*TAVILY_API_KEY\s*=\s*["\']?([^"\'\s]+)', env, re.M)
    return m.group(1) if m else ''


def classify(url: str) -> str:
    host = (urlparse(url).hostname or '').lower()
    if host.endswith(_OFFICIAL_SUFFIXES):
        return 'OFFICIAL'
    if host.endswith(_TRUSTED_SUFFIXES):
        return 'TRUSTED_PUBLIC'
    return 'UNVERIFIED'


@dataclass
class Hit:
    title: str
    url: str
    content: str
    trust: str

    @property
    def host(self) -> str:
        return (urlparse(self.url).hostname or '').lower().replace('www.', '')


def search(query: str, *, max_results: int = 20, official_only: bool = True) -> list[Hit]:
    """Search, then enforce the scope ourselves.

    Tavily's `include_domains` is advisory in practice (CLAUDE.md records a run that
    returned five coaching sites alongside one ssc.gov.in notice), so the filter that
    matters is applied here, after the results come back.
    """
    key = _load_key()
    if not key:
        raise SearchUnavailable(
            'No TAVILY_API_KEY. The universal resolver needs search to discover an '
            'authority it has no connector for. Add the key to .env, or name an exam whose '
            'authority already has a connector.')

    payload = {'query': query, 'max_results': max_results, 'search_depth': 'advanced'}
    body = json.dumps({**payload, 'api_key': key}).encode('utf-8')
    req = urllib.request.Request(TAVILY_URL, data=body, headers={
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {key}',
    })
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=45, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8', 'replace'))
    except urllib.error.HTTPError as exc:
        raise SearchUnavailable(f'search HTTP {exc.code}: {exc.read()[:200]!r}') from exc
    except Exception as exc:                       # noqa: BLE001
        raise SearchUnavailable(f'search failed: {exc!r}') from exc

    hits = []
    for item in data.get('results', []):
        url = item.get('url', '')
        trust = classify(url)
        if official_only and trust != 'OFFICIAL':
            continue
        hits.append(Hit(title=item.get('title', ''), url=url,
                        content=item.get('content', ''), trust=trust))
    return hits
