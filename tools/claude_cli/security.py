"""Authorisation boundaries for the Claude endpoints.

GovOS has no user accounts, so none of this is production authentication, and it does not
pretend to be. It is an explicit, local-first protection for the operations that spend Claude
usage or could change canonical exam information:

  * ADMIN operations (discovery, extraction, builds, roadmap guidance, job listing, retry) need
    either the configured `GOVOS_CLAUDE_ADMIN_TOKEN` presented in the `X-GovOS-Admin-Token`
    header, or -- only when no token is configured -- a request that arrives directly from the
    loopback interface with no proxy headers. A deployment behind a reverse proxy must set a
    token; without one every remote or proxied admin request is refused.
  * CANDIDATE operations (ask, practice) are open but rate limited, and each job is readable only
    with the per-job token returned when it was created, so one candidate can never read
    another's job or result.

Comparison of tokens is constant-time.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Mapping, Optional
from urllib.parse import urlparse

from .config import ENV_ADMIN_TOKEN

ADMIN_HEADER = 'X-GovOS-Admin-Token'
JOB_TOKEN_HEADER = 'X-GovOS-Job-Token'
_LOOPBACK = ('127.0.0.1', '::1', '::ffff:127.0.0.1')
_PROXY_HEADERS = ('X-Forwarded-For', 'Forwarded', 'X-Real-IP', 'X-Forwarded-Host')
_LOCAL_HOSTNAMES = ('localhost', '127.0.0.1', '::1')


def admin_check(remote_addr: Optional[str], headers: Mapping[str, str],
                env: Optional[Mapping[str, str]] = None) -> tuple[bool, str]:
    """(allowed, reason). Pure: takes what it needs from the request, so it is easy to test."""
    env = os.environ if env is None else env
    configured = (env.get(ENV_ADMIN_TOKEN) or '').strip()
    presented = (headers.get(ADMIN_HEADER) or '').strip()
    if configured:
        if presented and hmac.compare_digest(presented.encode('utf-8'), configured.encode('utf-8')):
            return True, 'token'
        return False, 'admin token required'
    if any(headers.get(h) for h in _PROXY_HEADERS):
        return False, 'proxied request: set GOVOS_CLAUDE_ADMIN_TOKEN to allow admin operations'
    origin = (headers.get('Origin') or '').strip()
    if origin and (urlparse(origin).hostname or '').lower() not in _LOCAL_HOSTNAMES:
        # A browser page on another site can send a request from this machine's loopback address;
        # without a token, an admin operation must come from a GovOS page served from this machine.
        return False, 'cross-origin request refused'
    if (remote_addr or '') in _LOOPBACK:
        return True, 'loopback'
    return False, 'admin operations are local-only unless GOVOS_CLAUDE_ADMIN_TOKEN is set'


def admin_token_required(env: Optional[Mapping[str, str]] = None) -> bool:
    """True when the server is configured to demand an admin token."""
    env = os.environ if env is None else env
    return bool((env.get(ENV_ADMIN_TOKEN) or '').strip())


def new_job_token() -> str:
    return secrets.token_urlsafe(24)


def hash_token(token: str) -> str:
    return hashlib.sha256((token or '').encode('utf-8')).hexdigest()


def token_matches(token: str, stored_hash: str) -> bool:
    if not token or not stored_hash:
        return False
    return hmac.compare_digest(hash_token(token), stored_hash)


class RateLimiter:
    """A sliding-window limiter, in process. Enough to stop a page from hammering an endpoint that
    spends account usage; a multi-process deployment needs a shared store."""

    def __init__(self, clock=time.monotonic) -> None:
        self._clock = clock
        self._hits: dict = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: float) -> tuple[bool, int]:
        """(allowed, seconds to wait). Records the hit only when allowed."""
        now = self._clock()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                return False, max(1, int(window_seconds - (now - q[0])) + 1) if q else max(1, int(window_seconds))
            q.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()
