"""What an extracted field is allowed to be.

The product's rule is that nothing is asserted without a source (CLAUDE.md: the provenance
chain is the product's core idea). This module makes that rule structural rather than a
habit: an extractor cannot return a bare string. It returns a Field, and a Field is exactly
one of three things —

    FOUND          a value, with the document, page and the words it was read from
    NOT_PUBLISHED  the authority does not publish this, established by looking at what it
                   does publish; a fact about the authority, not a gap in GovOS
    NOT_EXTRACTED  the document was read but no pattern matched. This is a statement about
                   this pipeline, NOT about the authority, and the two must never be
                   collapsed: "UPSC publishes no answer key" is a finding, while "our regex
                   did not match the age clause in the CDS notice" is a to-do. Reporting the
                   second as the first is the exact discrepancy this tool exists to avoid.
    NEEDS_REVIEW   read, but not confidently; carried through so a person can confirm it,
                   and never rendered as officially verified

There is deliberately no fourth case for "guessed". A field nobody could source simply does
not reach `data.ts`, which is what keeps a thin exam honest instead of plausible.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Any, Optional


class Status(str, Enum):
    FOUND = 'FOUND'
    NOT_PUBLISHED = 'NOT_PUBLISHED'
    NOT_EXTRACTED = 'NOT_EXTRACTED'
    NEEDS_REVIEW = 'NEEDS_REVIEW'


@dataclass
class Citation:
    """Where a value came from, precisely enough to check it by hand."""

    document_title: str
    url: str
    page: int = 1
    clause: str = ''
    excerpt: str = ''
    verified_date: str = ''

    def to_provenance(self, prov_id: str, taxonomy: str = 'FACT',
                      level: str = 'OFFICIALLY_VERIFIED', published: str = '') -> dict:
        return {
            'id': prov_id,
            'documentTitle': self.document_title,
            'officialUrl': self.url,
            'pageNumber': self.page,
            'clauseNumber': self.clause or 'Whole document',
            'publishedDate': published or self.verified_date,
            'verifiedDate': self.verified_date,
            'verifiedBy': f'GovOS exam-authoring pipeline — read from the source on {self.verified_date}',
            'taxonomyType': taxonomy,
            'verificationLevel': level,
            'excerptText': self.excerpt[:600],
        }


@dataclass
class Field:
    """One extracted value and its standing."""

    name: str
    status: Status
    value: Any = None
    citation: Optional[Citation] = None
    #: Why it is NOT_PUBLISHED or NEEDS_REVIEW, in words a person can act on.
    note: str = ''

    @property
    def ok(self) -> bool:
        return self.status is Status.FOUND

    @property
    def usable(self) -> bool:
        """FOUND or NEEDS_REVIEW both carry a real value; they differ in how they are badged."""
        return self.status in (Status.FOUND, Status.NEEDS_REVIEW) and self.value not in (None, '', [], {})

    @property
    def verification_level(self) -> str:
        return 'OFFICIALLY_VERIFIED' if self.status is Status.FOUND else 'UNDER_VERIFICATION'

    # -- constructors, so call sites read as intent ---------------------------------
    @staticmethod
    def found(name: str, value: Any, citation: Citation) -> 'Field':
        return Field(name=name, status=Status.FOUND, value=value, citation=citation)

    @staticmethod
    def not_published(name: str, note: str) -> 'Field':
        """Use only where the authority's own listing shows the thing does not exist."""
        return Field(name=name, status=Status.NOT_PUBLISHED, note=note)

    @staticmethod
    def not_extracted(name: str, where: str, what: str = '') -> 'Field':
        """No pattern matched. Names the document, so a person can go and read it."""
        return Field(name=name, status=Status.NOT_EXTRACTED,
                     note=f'No {what or name} pattern matched in {where} — the document was '
                          f'read but this extractor could not find the clause. Read it by hand '
                          f'or extend the extractor; do not assume the authority is silent.')

    @staticmethod
    def needs_review(name: str, value: Any, note: str, citation: Optional[Citation] = None) -> 'Field':
        return Field(name=name, status=Status.NEEDS_REVIEW, value=value, note=note, citation=citation)


@dataclass
class ExamRecord:
    """Everything the pipeline gathered for exactly one exam.

    `exam_id` is set once at construction and every field written here is checked against it
    before emission (see verify.py). Two exams cannot share a record, which is the structural
    half of the isolation rule — the other half is that each run fetches only the URLs its own
    adapter names.
    """

    exam_id: str
    code: str
    title: str
    authority_name: str
    official_domain: str
    fields: dict[str, Field] = dc_field(default_factory=dict)
    #: Every URL this run actually read, for the audit trail.
    sources_read: list[str] = dc_field(default_factory=list)
    #: Anything the run wants a human to see, in order.
    log: list[str] = dc_field(default_factory=list)

    def set(self, f: Field) -> None:
        self.fields[f.name] = f

    def get(self, name: str) -> Optional[Field]:
        return self.fields.get(name)

    def value(self, name: str, default: Any = None) -> Any:
        f = self.fields.get(name)
        return f.value if (f and f.usable) else default

    def note(self, message: str) -> None:
        self.log.append(message)

    # -- reporting -------------------------------------------------------------------
    def summary(self) -> dict:
        by_status: dict[str, list[str]] = {s.value: [] for s in Status}
        for name, f in self.fields.items():
            by_status[f.status.value].append(name)
        return {
            'examId': self.exam_id,
            'title': self.title,
            'found': sorted(by_status[Status.FOUND.value]),
            'notPublished': sorted(by_status[Status.NOT_PUBLISHED.value]),
            'notExtracted': sorted(by_status[Status.NOT_EXTRACTED.value]),
            'needsReview': sorted(by_status[Status.NEEDS_REVIEW.value]),
            'sourcesRead': self.sources_read,
        }
