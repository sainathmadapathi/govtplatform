"""Exam name in, authority adapter out.

This is the only place an exam name is matched to an authority. Adding an authority is one
import and one entry; nothing else in the pipeline changes, and no adapter learns about
another.
"""
from __future__ import annotations

import re

from .adapters.upsc import UPSCAdapter

#: (pattern the user might type, adapter). First match wins, so put the specific first.
AUTHORITIES: list[tuple[str, object]] = [
    (r'\bupsc\b|civil services|\bcse\b|\bifs\b|indian forest service|combined defence|'
     r'\bnda\b|\bcds\b|engineering services|\bese\b|geo-?scientist|combined medical|'
     r'\bcapf\b|economic service|statistical service', UPSCAdapter()),
]


def resolve(query: str):
    """The adapter for an exam name, or None with the list of what is supported."""
    q = (query or '').strip()
    for pattern, adapter in AUTHORITIES:
        if re.search(pattern, q, re.I):
            return adapter
    return None


def supported() -> list[str]:
    return [type(a).__name__ for _, a in AUTHORITIES]
