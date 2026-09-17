"""What an authority adapter must do.

One adapter per authority, because there is no such thing as a generic government website.
An adapter's whole job is to turn an exam's name into *that authority's own* documents and
then read them; it must never reach for another authority's host, and the pipeline checks
that afterwards (verify.py, `assert_single_authority`).

Adding an authority means adding one file here and one line in registry.py. It must not
touch any other adapter — the same isolation rule the practice engines follow.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Protocol

from ..record import ExamRecord


@dataclass
class ExamTarget:
    """One exam, located on its authority's site, before anything is read."""

    exam_id: str
    code: str
    title: str
    authority_name: str
    official_domain: str
    #: The authority's own page for this exam, if it has one.
    exam_page_url: Optional[str] = None
    #: The examination notice / advertisement PDF.
    notice_url: Optional[str] = None
    #: Anything else the adapter found worth reading (papers, keys, syllabus).
    extra_urls: dict[str, str] = field(default_factory=dict)


class Adapter(Protocol):
    authority_name: str
    official_domain: str

    def discover(self, query: str) -> list[ExamTarget]:
        """Every exam on this authority's site whose name matches `query`."""
        ...

    def gather(self, target: ExamTarget) -> ExamRecord:
        """Read the located documents into a record. Reads only `target`'s own URLs."""
        ...
