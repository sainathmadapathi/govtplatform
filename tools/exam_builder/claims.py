"""Claims from more than one kind of source, reconciled without letting the weaker one win.

Discovery can now reach a source that is not the authority: a reviewed secondary site, an
unreviewed coaching page, a social post. Each may state the same field as the authority, or a
different value for it. This module records every such statement as a `SourceClaim` and decides,
for one field, what may be said:

    the official value governs          (an official document states it, in words GovOS read)
    a trusted secondary source agreeing  is a corroboration, shown beside the official value
    a source disagreeing                 is a recorded conflict, never a correction
    a secondary value with no official   stays secondary: shown, if at all, as that source's claim,
      statement of the field             never promoted to the authority's

Nothing is averaged, nothing is chosen by recency or by how many sources repeat it, and no model
is asked to arbitrate. Two official statements that disagree are CONFLICTED and neither wins,
the same rule `results_merge` applies -- a later official statement replaces an earlier one only
where it says so, which is the corrigendum pipeline's job, not this module's.

A claim counts only when its quotation is found in the text GovOS fetched itself
(`evidence.Evidence.verify`). A claim whose words are not there is kept as UNSUPPORTED, so an
auditor can see it was made, and contributes nothing.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional

from .evidence import Evidence, EvidenceStatus, normalise_ws
from .schema import Fact, SourceEvidence, Status
from .source_graph import SourceClass


@dataclass
class SourceClaim:
    """One source's statement of one field."""

    field: str
    value: str
    source_url: str
    source_class: SourceClass
    quotation: str = ''
    document_title: str = ''
    published_at: str = ''
    page: Optional[int] = None
    node_id: str = ''
    #: Set by `check_quotation`; a claim is never trusted on its own report of its words.
    quotation_status: EvidenceStatus = EvidenceStatus.UNCHECKED

    @property
    def is_supported(self) -> bool:
        return self.quotation_status is EvidenceStatus.VERIFIED

    def check_quotation(self, fetched_text: str) -> EvidenceStatus:
        self.quotation_status = Evidence(span=self.quotation, source_url=self.source_url).verify(fetched_text)
        return self.quotation_status

    def as_evidence(self) -> SourceEvidence:
        return SourceEvidence(source_id=self.node_id or self.source_url, url=self.source_url,
                              document_title=self.document_title, published_at=self.published_at,
                              page=self.page, span=self.quotation, span_status=self.quotation_status,
                              reading=f'{self.field} = {self.value}', source_class=self.source_class.value)

    def as_dict(self) -> dict:
        return {'field': self.field, 'value': self.value, 'sourceUrl': self.source_url,
                'sourceClass': self.source_class.value, 'sourceLabel': self.source_class.candidate_label,
                'quotation': self.quotation, 'documentTitle': self.document_title,
                'publishedAt': self.published_at, 'page': self.page,
                'quotationStatus': self.quotation_status.value}


class Resolution(str, Enum):
    OFFICIAL = 'OFFICIAL'                      # an official statement, nothing else on the field
    OFFICIAL_CORROBORATED = 'OFFICIAL_CORROBORATED'  # ... and a trusted secondary source agrees
    OFFICIAL_CONTESTED = 'OFFICIAL_CONTESTED'  # ... and a non-official source disagrees; official governs
    OFFICIAL_CONFLICT = 'OFFICIAL_CONFLICT'    # official statements disagree; nothing is published
    SECONDARY_ONLY = 'SECONDARY_ONLY'          # only non-official sources state it; not the authority's
    UNSUPPORTED = 'UNSUPPORTED'                # no claim's quotation was found in its source


@dataclass
class ClaimResolution:
    field: str
    state: Resolution
    #: The value that may be presented as the authority's. None unless an official statement governs.
    value: Optional[str] = None
    governing: list = field(default_factory=list)       # official claims stating `value`
    corroborations: list = field(default_factory=list)  # trusted secondary claims agreeing
    agreeing_unreviewed: list = field(default_factory=list)  # unreviewed secondary claims agreeing
    conflicts: list = field(default_factory=list)       # claims disagreeing (any class)
    secondary: list = field(default_factory=list)       # secondary claims where no official one exists
    leads: list = field(default_factory=list)           # discovery-only claims: never information
    unsupported: list = field(default_factory=list)     # quotations not found in their source
    note: str = ''

    @property
    def publishable(self) -> bool:
        return self.value is not None and self.state in (
            Resolution.OFFICIAL, Resolution.OFFICIAL_CORROBORATED, Resolution.OFFICIAL_CONTESTED)

    def as_fact(self) -> Fact:
        """The existing contract's shape: official evidence first, corroboration after it, and a
        secondary-only or conflicted field never VERIFIED."""
        if self.publishable:
            evidence = [c.as_evidence() for c in self.governing + self.corroborations]
            fact = Fact.verified(self.value, evidence)
            fact.note = self.note
            return fact
        if self.state is Resolution.UNSUPPORTED:
            return Fact(status=Status.NOT_EXTRACTED, note=self.note)
        evidence = [c.as_evidence() for c in self.conflicts + self.secondary]
        # NEEDS_REVIEW carries no value: a secondary or contested reading is the source's claim,
        # held for a person, and never presented as the authority's.
        return Fact(value=None, status=Status.NEEDS_REVIEW, evidence=evidence, note=self.note)

    def as_dict(self) -> dict:
        return {'field': self.field, 'state': self.state.value, 'value': self.value,
                'publishable': self.publishable, 'note': self.note,
                'governing': [c.as_dict() for c in self.governing],
                'corroborations': [c.as_dict() for c in self.corroborations],
                'agreeingUnreviewed': [c.as_dict() for c in self.agreeing_unreviewed],
                'conflicts': [c.as_dict() for c in self.conflicts],
                'secondary': [c.as_dict() for c in self.secondary],
                'leads': [c.as_dict() for c in self.leads],
                'unsupported': [c.as_dict() for c in self.unsupported]}


def _default_key(value: str) -> str:
    return normalise_ws(str(value)).lower()


def reconcile(field_name: str, claims: list, *, key: Optional[Callable[[str], str]] = None) -> ClaimResolution:
    """Decide what may be said about one field from every claim on it.

    `key` normalises a value for comparison (a date to ISO, a figure to digits); it compares, it
    never rewrites what a source said.
    """
    key = key or _default_key
    mine = [c for c in claims if c.field == field_name]
    out = ClaimResolution(field=field_name, state=Resolution.UNSUPPORTED)
    supported = []
    for c in mine:
        if c.source_class is SourceClass.UNVERIFIED:
            continue
        if not c.is_supported:
            out.unsupported.append(c)
        elif c.source_class is SourceClass.DISCOVERY_ONLY:
            out.leads.append(c)
        else:
            supported.append(c)
    official = [c for c in supported if c.source_class.may_state_official_fact]
    others = [c for c in supported if not c.source_class.may_state_official_fact]
    if not official:
        if others:
            out.state, out.secondary = Resolution.SECONDARY_ONLY, others
            out.note = (f'no official statement of this was found; {len(others)} non-official source(s) state it, '
                        f'and that is their claim, not the authority\'s')
        else:
            out.note = ('nothing stated this in words GovOS could find in the source' if mine or out.leads
                        else 'no source stated this')
            if out.leads:
                out.note = 'only community leads mention this; a lead is a reason to look, not information'
        return out
    values = {}
    for c in official:
        values.setdefault(key(c.value), []).append(c)
    if len(values) > 1:
        out.state = Resolution.OFFICIAL_CONFLICT
        out.conflicts = official + [c for c in others]
        out.note = (f'official statements disagree ({", ".join(repr(v[0].value) for v in values.values())}); '
                    f'neither is published until a person establishes which governs')
        return out
    (k, governing), = values.items()
    out.value, out.governing = governing[0].value, governing
    for c in others:
        if key(c.value) == k:
            (out.corroborations if c.source_class is SourceClass.TRUSTED_SECONDARY
             else out.agreeing_unreviewed).append(c)
        else:
            out.conflicts.append(c)
    if out.conflicts:
        out.state = Resolution.OFFICIAL_CONTESTED
        out.note = (f'{len(out.conflicts)} non-official source(s) state a different value; the official '
                    f'statement governs and theirs is recorded, not used')
    elif out.corroborations:
        out.state = Resolution.OFFICIAL_CORROBORATED
        out.note = f'{len(out.corroborations)} trusted secondary source(s) state the same value'
    else:
        out.state = Resolution.OFFICIAL
    return out


def reconcile_all(claims: list, *, keys: Optional[dict] = None) -> dict:
    """Every field any claim names, each reconciled on its own."""
    keys = keys or {}
    return {f: reconcile(f, claims, key=keys.get(f)) for f in sorted({c.field for c in claims})}
