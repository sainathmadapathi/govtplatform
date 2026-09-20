"""Bridges between the universal contract and everything that already exists.

Two systems are already running against the old shapes and neither is being rewritten in
this phase: the Python builder (`exam_authoring.record.Field`, whose four states call the
first one FOUND) and the GovOS frontend (`src/types.ts`, whose `Exam` is what five real exam
records are written in and what twenty-odd components read).

So the universal contract is added beside them, and this module is the only place the two
vocabularies meet. Nothing here changes a stored record, and nothing here is required in
order to keep using the old shapes — a translation exists so that migration can be gradual
and reversible rather than a single edit that breaks five exams at once.

Two directions, deliberately asymmetric:

    Field   -> Fact          total. Every old field has a new form.
    Fact    -> Field         total, and lossy in a stated way: a Fact may carry several
                             pieces of evidence and a Field has room for one citation, so
                             the first is used and the rest are named in the note.

The frontend projection (`to_legacy_provenance`) produces the `DataProvenance` shape the UI
already renders, including the rule it already follows: a value that is not VERIFIED is
never badged as officially verified.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from ..exam_authoring.record import Citation, Field as LegacyField, Status as LegacyStatus
from .evidence import Evidence, EvidenceStatus
from .schema import (Fact, SourceDocument, SourceEvidence, SourceKind, Status)

#: The only difference in the four-state vocabulary is the name of the first one. Keeping
#: the mapping explicit means a future rename cannot silently merge two states.
_LEGACY_TO_STATUS = {
    LegacyStatus.FOUND: Status.VERIFIED,
    LegacyStatus.NEEDS_REVIEW: Status.NEEDS_REVIEW,
    LegacyStatus.NOT_PUBLISHED: Status.NOT_PUBLISHED,
    LegacyStatus.NOT_EXTRACTED: Status.NOT_EXTRACTED,
}

_STATUS_TO_LEGACY = {v: k for k, v in _LEGACY_TO_STATUS.items()}

#: Verification levels the frontend already understands.
VERIFIED_LEVEL = 'OFFICIALLY_VERIFIED'
UNVERIFIED_LEVEL = 'UNDER_VERIFICATION'
SUPERSEDED_LEVEL = 'SUPERSEDED'


def status_from_legacy(status: LegacyStatus) -> Status:
    return _LEGACY_TO_STATUS[status]


def status_to_legacy(status: Status) -> LegacyStatus:
    return _STATUS_TO_LEGACY[status]


# ------------------------------------------------------------------ old -> new
def evidence_from_citation(citation: Citation, *, source_id: str = '',
                           kind: SourceKind = SourceKind.OTHER_OFFICIAL) -> SourceEvidence:
    """A `Citation` as a `SourceEvidence`.

    The span status is UNCHECKED rather than VERIFIED: a Citation's excerpt was never
    checked against the document, and claiming it was would be exactly the kind of
    unearned confidence this contract exists to prevent.
    """
    return SourceEvidence(
        source_id=source_id or citation.url,
        url=citation.url,
        document_title=citation.document_title,
        document_type=kind,
        page=citation.page,
        section=citation.clause,
        span=citation.excerpt,
        accessed_at=citation.verified_date,
        published_at=citation.verified_date,
        span_status=EvidenceStatus.UNCHECKED,
        reading='carried over from a citation written before spans were verified')


def fact_from_field(field: LegacyField, *, source_id: str = '',
                    kind: SourceKind = SourceKind.OTHER_OFFICIAL) -> Fact:
    """A builder `Field` as a `Fact`. Total: every old field has a new form."""
    evidence = ([evidence_from_citation(field.citation, source_id=source_id, kind=kind)]
                if field.citation else [])
    return Fact(value=field.value,
                status=status_from_legacy(field.status),
                evidence=evidence,
                confidence=1.0 if field.status is LegacyStatus.FOUND else 0.0,
                note=field.note)


# ------------------------------------------------------------------ new -> old
def citation_from_evidence(ev: SourceEvidence) -> Citation:
    return Citation(document_title=ev.document_title or ev.url,
                    url=ev.url,
                    page=ev.page or 1,
                    clause=ev.section,
                    excerpt=ev.span,
                    verified_date=ev.accessed_at)


def field_from_fact(name: str, fact: Fact) -> LegacyField:
    """A `Fact` as a builder `Field`, for code that still expects one.

    Lossy in one stated way: a Fact may cite several documents and a Field has room for one
    citation. The first is used and the others are named in the note, so the fact that
    corroboration existed is not silently dropped.
    """
    citation = citation_from_evidence(fact.primary_source) if fact.primary_source else None
    note = fact.note
    if len(fact.evidence) > 1:
        others = ', '.join(e.locator() for e in fact.evidence[1:])
        note = (note + ' ' if note else '') + f'also stated in: {others}'
    return LegacyField(name=name, status=status_to_legacy(fact.status),
                       value=fact.value, citation=citation, note=note)


# ------------------------------------------------------------- new -> frontend
def verification_level_for(status: Status, *, superseded: bool = False) -> str:
    """The frontend's badge for one of our four states.

    Only VERIFIED earns the official badge — the rule the UI already follows. The two
    absence states have no frontend representation at all, which is a real gap recorded in
    CONTRACT_AUDIT.md; they must not be rendered as though a value existed, so callers
    check `Fact.has_value` before projecting.
    """
    if superseded:
        return SUPERSEDED_LEVEL
    return VERIFIED_LEVEL if status is Status.VERIFIED else UNVERIFIED_LEVEL


def to_legacy_provenance(fact: Fact, *, prov_id: str, taxonomy: str = 'FACT',
                         superseded: bool = False) -> Optional[dict]:
    """The `DataProvenance` object the UI renders, or None when there is nothing to cite.

    Returning None rather than an empty provenance is deliberate: the UI's contract is that
    a provenance button always opens something real.
    """
    ev = fact.primary_source
    if ev is None:
        return None
    return {
        'id': prov_id,
        'documentTitle': ev.document_title or ev.url,
        'officialUrl': ev.url,
        'pageNumber': ev.page or 1,
        'clauseNumber': ev.section or 'Whole document',
        'publishedDate': ev.published_at or ev.accessed_at,
        'verifiedDate': ev.accessed_at,
        'verifiedBy': 'GovOS exam builder — read from the source',
        'taxonomyType': taxonomy,
        'verificationLevel': verification_level_for(fact.status, superseded=superseded),
        'excerptText': (ev.span or '')[:600],
    }


def source_document_from(url: str, *, kind: SourceKind = SourceKind.OTHER_OFFICIAL,
                         title: str = '', authority: str = '', accessed_at: str = '',
                         content_hash: str = '', exam_id: str = '') -> SourceDocument:
    """Build a `SourceDocument` from what the discovery layer already knows.

    `discover.py` classifies document kinds and `manifest.py` computes content hashes; both
    were being discarded at the record boundary because the old `sources_read: list[str]`
    had nowhere to put them.
    """
    return SourceDocument(id=url, url=url, kind=kind, title=title, authority=authority,
                          accessed_at=accessed_at, content_hash=content_hash,
                          exam_id=exam_id)


def evidence_from_extracted(ev: Evidence, doc: SourceDocument) -> SourceEvidence:
    """The extraction layer's `Evidence` as contract evidence, verification intact."""
    return SourceEvidence.from_evidence(ev, source=doc, source_id=doc.id)


def round_trips(field: LegacyField) -> bool:
    """Does an old field survive a trip through the new contract unchanged?

    Used by the tests as the backward-compatibility guarantee: if this holds for every
    field the builder produces, adopting the contract cannot change what a record says.
    """
    back = field_from_fact(field.name, fact_from_field(field))
    same_citation = ((field.citation is None) == (back.citation is None)) and (
        field.citation is None or (
            field.citation.url == back.citation.url
            and field.citation.page == back.citation.page
            and field.citation.excerpt == back.citation.excerpt))
    return (back.name == field.name and back.status == field.status
            and back.value == field.value and same_citation)


def describe_field_states() -> dict[str, str]:
    """The four states and what each claims, for a report or a UI legend."""
    return {
        Status.VERIFIED.value: 'read from the authority’s document, span checked verbatim',
        Status.NEEDS_REVIEW.value: 'read, but not confidently; never badged official',
        Status.NOT_PUBLISHED.value: 'the authority publishes no such thing — about them',
        Status.NOT_EXTRACTED.value: 'we could not read it — about us, never about them',
    }


# ------------------------------------- ApplicationProcess -> the existing simulator
def application_simulator_spec(process, *, exam_id: str, portal_name: str = '',
                               modelled_on: str = '') -> Optional[dict]:
    """Project an extracted process into the `ApplicationSimulatorSpec` the UI renders.

    Deliberately partial, and the missing part is the point. Modules and fields are
    structural, so they project: a stage becomes a module and its fields become inputs,
    keeping the authority's own wording for both.

    **Traps do not project.** A trap asserts that one specific mistake is fatal, which is a
    reading of a clause rather than a shape in it, and manufacturing those from extracted
    sentences would be exactly the invention this phase forbids. So a projected spec carries
    an empty trap list and says so in `modelledOnNote`, and the two hand-authored specs stay
    the richer ones until rules are extracted with the same rigour a person applied.

    Returns None when there is not enough source-backed material to render honestly — an
    empty form is worse than no form, because it implies the authority published nothing.
    """
    usable = [s for s in getattr(process, 'stages', [])
              if s.status in (Status.VERIFIED, Status.NEEDS_REVIEW)]
    if not usable:
        return None

    portal = getattr(process, 'portal', None)
    portal_url = portal.value if (portal and portal.has_value) else ''
    primary = portal.primary_source if (portal and portal.evidence) else None

    modules = []
    for index, stage in enumerate(usable, start=1):
        ev = stage.evidence[0] if stage.evidence else None
        modules.append({
            'moduleNumber': index,
            # The authority's own word for the step, never normalised onto another's.
            'cardName': stage.title,
            'title': stage.title,
            'introduction': stage.description,
            'noticeReference': ev.locator() if ev else '',
            'fields': [{
                'id': f.id,
                'label': f.label,
                # The UI's kinds are a closed set; anything the document did not state
                # falls back to free text rather than being guessed into a control.
                'kind': {'SELECT': 'SELECT', 'DATE': 'DATE'}.get(f.input_kind, 'TEXT'),
                'defaultValue': '',
                'noteFromNotice': f.help_text,
            } for f in stage.fields],
        })

    note = (modelled_on or
            'Built from the authority’s own application instructions. The steps and fields '
            'below are the ones that document names. It carries no mistake-traps: those '
            'assert that a particular error is fatal, which is a reading of a clause and is '
            'authored by a person, not extracted.')

    return {
        'examId': exam_id,
        'portalName': portal_name or (primary.document_title if primary else ''),
        'portalUrl': portal_url,
        'sourceDocumentTitle': primary.document_title if primary else '',
        'sourceDocumentUrl': primary.url if primary else '',
        'modelledOnNote': note,
        'modules': modules,
        'traps': [],
        'cleanSubmissionNote': 'No mistake-traps are authored for this exam yet.',
        'provenance': to_legacy_provenance(
            portal if portal else Fact.not_extracted(),
            prov_id=f'prov-app-{exam_id}') or {},
    }


# ------------------------------------------- Milestone -> the existing timeline
#: The frontend's `ImportantDate.type` is a closed union written around one authority's
#: vocabulary. The universal `kind` is open, so the projection maps what it can and falls
#: back rather than dropping a milestone the UI has no word for -- a date the candidate needs
#: must not disappear because a type name is missing.
_KIND_TO_LEGACY_TYPE = {
    'NOTIFICATION': 'NOTIFICATION',
    'APPLICATION_WINDOW': 'APPLICATION_CLOSE',
    'APPLICATION_START': 'APPLICATION_OPEN',
    'APPLICATION_END': 'APPLICATION_CLOSE',
    'FEE_PAYMENT_END': 'APPLICATION_CLOSE',
    'CORRECTION_WINDOW': 'CORRECTION_WINDOW',
    'ADMIT_CARD': 'ADMIT_CARD',
    'CITY_INTIMATION': 'ADMIT_CARD',
    'ANSWER_KEY': 'ANSWER_KEY',
    'RESULT': 'RESULT',
    'INTERVIEW': 'INTERVIEW',
    'SKILL_TEST': 'INTERVIEW',
    'PHYSICAL_TEST': 'INTERVIEW',
    'DOCUMENT_VERIFICATION': 'INTERVIEW',
    'EXAM': 'EXAM_TIER1',
}


def legacy_date_type(kind: str, *, stage_label: str = '') -> str:
    """The nearest type the existing union has for this event.

    Lossy by construction, and the loss is recorded rather than hidden: the milestone's own
    `kind` and label carry the authority's meaning, and the label is what the timeline
    actually shows. A stage-scoped examination maps onto the second tier where the authority
    numbered it beyond the first, which is the most the closed union can express.
    """
    mapped = _KIND_TO_LEGACY_TYPE.get(kind, 'NOTIFICATION')
    if kind == 'EXAM' and stage_label:
        if re.search(r'\b(?:2|ii|b)\b', stage_label, re.I):
            return 'EXAM_TIER2'
    return mapped


def important_dates(milestones, *, exam_id: str, timezone: str = 'IST') -> list[dict]:
    """Project milestones into the `ImportantDate[]` the Dates & Timeline section renders.

    Three rules, all of them about not overstating what was read:

      * a milestone with no effective date is left out. The UI has no way to render "the
        authority has not said", and a row with an empty date reads as a bug.
      * `SUPERSEDED` is used for a milestone that a later document replaced, which is
        exactly what the UI already does with it -- shown struck through, never announced
        as next.
      * a reading we are unsure of is marked tentative and its provenance is not badged
        official, so nothing uncertain is presented as the authority's final word.
    """
    from .schema import DatePrecision, MilestoneState, Status as _Status

    rows: list[dict] = []
    for index, milestone in enumerate(milestones):
        effective = milestone.effective_date
        superseded = milestone.is_superseded
        if effective is None and not superseded:
            continue
        shown = effective or (milestone.ends_at.value or milestone.starts_at.value)
        if not shown:
            continue

        fact = milestone.ends_at if milestone.ends_at.has_value else milestone.starts_at
        provenance = to_legacy_provenance(
            fact, prov_id=f'prov-{milestone.id}', superseded=superseded)
        if provenance is None:
            continue

        from .schema import ScopeKind
        stage_scopes = milestone.scope.of(ScopeKind.STAGE)
        stage_refs = stage_scopes[0].label if stage_scopes else ''
        rows.append({
            'id': milestone.id or f'date-{exam_id}-{index}',
            'type': legacy_date_type(milestone.kind, stage_label=stage_refs),
            'label': milestone.label,
            'dateTimeStr': f'{shown} 00:00:00',
            'timezone': timezone,
            'isTentative': bool(milestone.is_tentative
                                or milestone.precision is not DatePrecision.DAY
                                or milestone.status is _Status.NEEDS_REVIEW),
            'status': 'SUPERSEDED' if superseded else 'AVAILABLE',
            'provenance': provenance,
        })
    return rows


def notification_candidates(milestones) -> list:
    """The milestones that may drive a reminder.

    Deliberately strict, and the strictness is the point: a candidate who acts on an
    uncertain date is worse off than one who got no reminder. Only a verified, effective,
    day-precision milestone qualifies -- never NEEDS_REVIEW, never NOT_PUBLISHED, never a
    date that has been superseded or cancelled.
    """
    return [m for m in milestones if m.is_actionable]


# ------------------------------------------- the existing record -> Milestone
#: The inverse of `_KIND_TO_LEGACY_TYPE`. Lossy in the other direction: the closed union has
#: one word where the universal side has several, so a record's ADMIT_CARD could have been a
#: city intimation and an INTERVIEW could have been a skill test. The mapping is to the
#: commonest reading, and the milestone keeps the record's own label, which is what a reader
#: actually sees.
_LEGACY_TYPE_TO_KIND = {
    'NOTIFICATION': 'NOTIFICATION',
    # Kept apart: an opening and a closing are two moments, and merging them onto one
    # kind made a window's closing date conflict with the record's opening date.
    'APPLICATION_OPEN': 'APPLICATION_START',
    'APPLICATION_CLOSE': 'APPLICATION_END',
    'CORRECTION_WINDOW': 'CORRECTION_WINDOW',
    'ADMIT_CARD': 'ADMIT_CARD',
    'EXAM_TIER1': 'EXAM',
    'EXAM_TIER2': 'EXAM',
    'ANSWER_KEY': 'ANSWER_KEY',
    'RESULT': 'RESULT',
    'INTERVIEW': 'INTERVIEW',
}


def milestone_from_important_date(row: dict, *, exam_id: str, source_id: str = 'record'):
    """Read one row of an existing record back as a Milestone, so it can be matched.

    An authored row is not treated as weaker than an extracted one. A person read a document
    to write it, which is at least as good as our reading, and the merge engine has no
    business preferring whichever came last.

    `APPLICATION_OPEN` and `APPLICATION_CLOSE` both map to the application window, and the
    open/close distinction is carried by which end of the milestone the date sits on -- that
    is what lets an extracted range match an authored pair.
    """
    from .schema import (DatePrecision, Fact, Milestone, MilestoneState, Scope, ScopeKind,
                         ScopeRef, SourceEvidence, Status)
    from .evidence import EvidenceStatus

    provenance = row.get('provenance') or {}
    evidence = SourceEvidence(
        source_id=source_id,
        url=provenance.get('officialUrl', ''),
        document_title=provenance.get('documentTitle', ''),
        page=provenance.get('pageNumber'),
        section=provenance.get('clauseNumber', ''),
        span=provenance.get('excerptText', ''),
        accessed_at=provenance.get('verifiedDate', ''),
        published_at=provenance.get('publishedDate', ''),
        # Not re-verified here: the record's excerpt was checked by whoever wrote it, and
        # claiming our own verification for somebody else's reading would be false.
        span_status=EvidenceStatus.UNCHECKED,
        reading='carried from the existing exam record')

    legacy_type = row.get('type', '')
    when = (row.get('dateTimeStr') or '')[:10]
    fact = Fact(value=when, status=Status.VERIFIED, evidence=[evidence]) if when else Fact()

    scope = Scope()
    stage_hint = 'II' if legacy_type == 'EXAM_TIER2' else ''
    if stage_hint:
        scope = Scope([ScopeRef(ScopeKind.STAGE, f'tier-{stage_hint.lower()}',
                                f'Tier {stage_hint}')])

    superseded = row.get('status') == 'SUPERSEDED'
    return Milestone(
        id=row.get('id') or f'date-{exam_id}',
        label=row.get('label', ''),
        kind=_LEGACY_TYPE_TO_KIND.get(legacy_type, legacy_type or 'OTHER'),
        scope=scope,
        cycle=when[:4],
        # The date sits on the end it describes, so `effective_date` answers correctly
        # for both: an opening's moment is its start, a closing's is its end.
        starts_at=fact if legacy_type == 'APPLICATION_OPEN' else Fact(),
        ends_at=fact if legacy_type != 'APPLICATION_OPEN' else Fact(),
        precision=DatePrecision.DAY,
        state=MilestoneState.ANNOUNCED,
        is_tentative=row.get('isTentative') or None,
        superseded_by='(recorded in this exam record)' if superseded else '',
        status=Status.VERIFIED,
        note='')
