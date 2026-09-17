"""A fetch that returns None instead of raising.

Officiality checking tries several candidate domains and most of them will not resolve;
an exception per candidate would turn ordinary shortlisting into an error path. The
distinction that matters is preserved by the caller: a domain that could not be fetched is
reported as unfetched, never as "not official".
"""
from __future__ import annotations

from ..exam_authoring.sources import FetchError, load_html


def safe_load_html(url: str, **kw):
    try:
        return load_html(url, **kw)
    except (FetchError, Exception):          # noqa: BLE001 - any failure is "unreachable"
        return None
