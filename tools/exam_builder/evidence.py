"""Evidence: a value is only as good as the words it was read from.

Every extracted value carries the exact span of source text that states it, and that span is
**verified to exist verbatim in the document** before the value is accepted. This is the
guard that makes the rest of the extraction architecture safe: a semantic classifier — or
later an LLM — may decide *which* passage states the fee, but it can never invent the fee,
because a value whose evidence is not found in the source is rejected outright.

The check is deliberately mechanical. `verify()` re-reads the document and looks for the
span; it does not trust the extractor's own report of where it looked.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field as dc_field
from enum import Enum


def normalise_ws(text: str) -> str:
    """Collapse whitespace. PDFs wrap mid-sentence, so a span and its source rarely match
    byte-for-byte without this — and requiring an exact byte match would reject true
    evidence, which is its own kind of wrong answer."""
    return ' '.join((text or '').split())


class EvidenceStatus(str, Enum):
    VERIFIED = 'VERIFIED'            # the span was found verbatim in the source
    NOT_IN_SOURCE = 'NOT_IN_SOURCE'  # claimed evidence does not exist — value rejected
    UNCHECKED = 'UNCHECKED'          # no source was available to check against


@dataclass
class Evidence:
    """The words a value was read from, and where they are."""

    span: str
    source_url: str
    document_title: str = ''
    page: int = 1
    #: What the extractor understood this span to say, for a person reviewing it.
    reading: str = ''
    status: EvidenceStatus = EvidenceStatus.UNCHECKED

    @property
    def digest(self) -> str:
        return hashlib.sha256(normalise_ws(self.span).encode('utf-8')).hexdigest()[:16]

    def verify(self, source_text: str) -> EvidenceStatus:
        """Confirm the span really is in the source. Never trust the extractor's word."""
        if not source_text:
            self.status = EvidenceStatus.UNCHECKED
            return self.status
        needle = normalise_ws(self.span)
        haystack = normalise_ws(source_text)
        if not needle:
            self.status = EvidenceStatus.NOT_IN_SOURCE
        elif needle in haystack:
            self.status = EvidenceStatus.VERIFIED
        else:
            self.status = EvidenceStatus.NOT_IN_SOURCE
        return self.status


@dataclass
class Extracted:
    """A normalised value, the evidence for it, and how confident the reading is."""

    field: str
    value: object
    evidence: Evidence
    #: 0..1. Derived from how many independent cues supported the reading, never invented.
    confidence: float = 0.0
    #: Cues that fired, so a low score is explainable rather than mysterious.
    cues_matched: list[str] = dc_field(default_factory=list)

    @property
    def is_usable(self) -> bool:
        return (self.value not in (None, '', [], {})
                and self.evidence.status is EvidenceStatus.VERIFIED)


def verified_or_none(candidate: Extracted, source_text: str) -> Extracted | None:
    """Accept a reading only if its evidence survives verification.

    A value whose span is not in the source is not downgraded to "uncertain" — it is
    dropped. Something that cannot be pointed at in an official document has no place in a
    record whose entire premise is that every claim can be checked.
    """
    candidate.evidence.verify(source_text)
    return candidate if candidate.is_usable else None
