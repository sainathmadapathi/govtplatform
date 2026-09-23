"""The universal exam contract — one set of shapes that any authority's exam can fill.

The existing shapes could not hold what authorities actually publish. Age was two integers
on a post, with the category relaxation hard-coded in `services.ts` and carrying no source at
all. The exam pattern had exactly two levels and no *paper*, so an exam whose stage contains
papers had to be flattened. The syllabus keyed its subject off a closed union of nineteen
literals, so adding an exam meant editing a type. A past paper was identified by exam and
year, which cannot separate two papers of one exam, let alone two language versions of one
paper. Answer keys had no entity at all. Results carried per-exam branches in the shared
type file. See CONTRACT_AUDIT.md.

Three ideas do the work here, and everything else follows from them.

**One evidence model.** `SourceEvidence` is the only way a claim is attached to a document,
and `Fact` is the only way a value is held. There is no path by which a bare value reaches a
record, so "cite your source" stops being a habit and becomes the type.

**Scopes instead of slots.** A rule does not live *on* the thing it governs; it names what it
applies to. One age rule with no scope is the exam's global rule; the same shape scoped to a
post is a post-specific rule; scoped to a category it is a relaxation. Nothing needs a new
field when an authority is more specific than the last one was.

**Trees instead of levels.** Pattern and syllabus are recursive nodes that carry the
authority's own word for what each level is. Stage/Paper/Section and Stage/Subject/Section
and Stage/Paper/Subject/Section are the same structure at different depths, so none of them
is privileged and no exam needs a branch.

What is deliberately absent: any authority name, any exam name, any closed vocabulary of
stages, subjects, categories or post classifications. Where an authority uses a word, the
word is stored as the authority wrote it.

This module defines shapes only. It reads nothing and extracts nothing.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field as dc_field
from enum import Enum
from typing import Any, Generic, Iterator, Optional, TypeVar

from .evidence import Evidence, EvidenceStatus, normalise_ws

T = TypeVar('T')


# ===================================================================== status
class Status(str, Enum):
    """The four things that can be true of a field, and they are never merged.

    The last two are the distinction the whole pipeline exists to preserve:
    NOT_PUBLISHED is a finding about the authority, NOT_EXTRACTED is a to-do about us.
    Reporting the second as the first tells a candidate an authority is silent when the
    fault is ours.
    """

    VERIFIED = 'VERIFIED'
    NEEDS_REVIEW = 'NEEDS_REVIEW'
    NOT_PUBLISHED = 'NOT_PUBLISHED'
    NOT_EXTRACTED = 'NOT_EXTRACTED'

    @property
    def is_about_the_authority(self) -> bool:
        """True where the status says something about what was published."""
        return self in (Status.VERIFIED, Status.NEEDS_REVIEW, Status.NOT_PUBLISHED)

    @property
    def carries_value(self) -> bool:
        return self in (Status.VERIFIED, Status.NEEDS_REVIEW)


#: Infrastructure is not a status. A fetch failure, a search outage or an unreadable scan
#: says nothing about what an authority publishes, so it is tracked on the build
#: (`gate.BuildState`) and can never be written into a field. Kept here as a named constant
#: so the rule is greppable from the contract itself.
INFRASTRUCTURE_IS_NOT_A_STATUS = True


class SourceKind(str, Enum):
    """What an authority published, by the role the document plays."""

    NOTIFICATION = 'NOTIFICATION'
    APPLICATION_PAGE = 'APPLICATION_PAGE'
    CORRIGENDUM = 'CORRIGENDUM'
    SYLLABUS = 'SYLLABUS'
    QUESTION_PAPER = 'QUESTION_PAPER'
    ANSWER_KEY = 'ANSWER_KEY'
    ADMIT_CARD_NOTICE = 'ADMIT_CARD_NOTICE'
    RESULT = 'RESULT'
    EXAM_PAGE = 'EXAM_PAGE'
    CUTOFF = 'CUTOFF'
    OTHER_OFFICIAL = 'OTHER_OFFICIAL'


# =================================================================== evidence
@dataclass
class SourceDocument:
    """One document, described once and referenced everywhere by its id.

    A record is built from many documents and no single one contains an exam, so documents
    are first-class and facts point at them. The hash is what lets a later build say "this
    changed" rather than silently re-reading something different.
    """

    id: str
    url: str
    kind: SourceKind = SourceKind.OTHER_OFFICIAL
    title: str = ''
    #: The authority as *this document* presents it, which is not always the resolver's name.
    authority: str = ''
    published_at: str = ''
    accessed_at: str = ''
    content_hash: str = ''
    #: The exam this document belongs to, where that is established. Never assumed.
    exam_id: str = ''
    notes: list[str] = dc_field(default_factory=list)


@dataclass
class SourceEvidence:
    """Where a value came from, precisely enough to check by hand.

    This is the *only* evidence shape in the contract. `exam_authoring.Citation` and
    `exam_builder.Evidence` had drifted apart, and only one of them verified that its span
    was really in the document; `from_evidence` folds that one in so the verification is
    kept rather than reimplemented.
    """

    source_id: str
    url: str = ''
    document_title: str = ''
    authority: str = ''
    document_type: SourceKind = SourceKind.OTHER_OFFICIAL
    published_at: str = ''
    accessed_at: str = ''
    page: Optional[int] = None
    section: str = ''
    #: The exact words the value was read from, verbatim from the document.
    span: str = ''
    content_hash: str = ''
    #: Whether the span was found in the source. UNCHECKED is honest; it is not a pass.
    span_status: EvidenceStatus = EvidenceStatus.UNCHECKED
    #: What the extractor understood the span to say, for whoever reviews it.
    reading: str = ''

    @property
    def span_digest(self) -> str:
        return hashlib.sha256(normalise_ws(self.span).encode('utf-8')).hexdigest()[:16]

    @property
    def is_verbatim(self) -> bool:
        return self.span_status is EvidenceStatus.VERIFIED

    def locator(self) -> str:
        """A human-readable 'where', for a report or a UI tooltip."""
        bits = [self.document_title or self.url or self.source_id]
        if self.page:
            bits.append(f'p.{self.page}')
        if self.section:
            bits.append(self.section)
        return ' · '.join(b for b in bits if b)

    @classmethod
    def from_evidence(cls, ev: Evidence, *, source: SourceDocument | None = None,
                      source_id: str = '') -> 'SourceEvidence':
        """Adopt an `Evidence` produced by the extraction layer, keeping its verification."""
        doc = source
        return cls(
            source_id=source_id or (doc.id if doc else ''),
            url=ev.source_url or (doc.url if doc else ''),
            document_title=ev.document_title or (doc.title if doc else ''),
            authority=doc.authority if doc else '',
            document_type=doc.kind if doc else SourceKind.OTHER_OFFICIAL,
            published_at=doc.published_at if doc else '',
            accessed_at=doc.accessed_at if doc else '',
            page=ev.page,
            span=ev.span,
            content_hash=doc.content_hash if doc else '',
            span_status=ev.status,
            reading=ev.reading)


# ======================================================================= fact
@dataclass
class Fact(Generic[T]):
    """A value, what we know about it, and what it was read from.

    Evidence is a list because a value may be stated in more than one document, and because
    a corroborated value and a singly-sourced one should not look alike. A fact with a value
    and no evidence is refused by `is_publishable`, which is the structural form of the
    product's rule that nothing is asserted without a source.
    """

    value: Optional[T] = None
    status: Status = Status.NOT_EXTRACTED
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    #: 0..1, derived from cues that actually fired. Never invented, and never a substitute
    #: for evidence.
    confidence: float = 0.0
    #: Why this is NEEDS_REVIEW or NOT_PUBLISHED, in words a person can act on.
    note: str = ''
    #: The fields this value was computed from, where the authority did not print it
    #: itself. A printed value has an empty list, so the two can never be confused: 200
    #: marks over 100 questions is 2 marks a question and may be shown as such, but it is
    #: our arithmetic on the authority's numbers, not the authority's statement.
    derived_from: list[str] = dc_field(default_factory=list)

    @property
    def is_derived(self) -> bool:
        return bool(self.derived_from)

    @property
    def has_value(self) -> bool:
        return self.value not in (None, '', [], {}, ())

    @property
    def is_publishable(self) -> bool:
        """A value may be shown as the authority's only if it is sourced and verbatim."""
        return (self.status is Status.VERIFIED and self.has_value
                and any(e.is_verbatim for e in self.evidence))

    @property
    def primary_source(self) -> Optional[SourceEvidence]:
        return self.evidence[0] if self.evidence else None

    # -- constructors, so call sites read as intent ---------------------------------
    @classmethod
    def verified(cls, value: T, evidence: SourceEvidence | list[SourceEvidence],
                 confidence: float = 1.0) -> 'Fact[T]':
        ev = evidence if isinstance(evidence, list) else [evidence]
        return cls(value=value, status=Status.VERIFIED, evidence=ev, confidence=confidence)

    @classmethod
    def needs_review(cls, value: T, note: str,
                     evidence: SourceEvidence | list[SourceEvidence] | None = None,
                     confidence: float = 0.0) -> 'Fact[T]':
        ev = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
        return cls(value=value, status=Status.NEEDS_REVIEW, evidence=ev,
                   confidence=confidence, note=note)

    @classmethod
    def not_published(cls, note: str,
                      evidence: SourceEvidence | list[SourceEvidence] | None = None
                      ) -> 'Fact[T]':
        """Only where the authority's own listing shows the thing does not exist.

        The evidence here is evidence of *absence being stated* — the page that lists what
        is published, showing this is not among it.
        """
        ev = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
        return cls(value=None, status=Status.NOT_PUBLISHED, evidence=ev, note=note)

    @classmethod
    def derived(cls, value: T, basis: list[str],
                evidence: SourceEvidence | list[SourceEvidence] | None = None,
                note: str = '') -> 'Fact[T]':
        """A value computed from others, citing the span its inputs were read from.

        Only for arithmetic that is guaranteed by the numbers themselves. It is never a
        way to supply a value the authority did not publish: a missing negative-marking
        rule is NOT_EXTRACTED, never derived from what other exams do.
        """
        ev = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
        return cls(value=value, status=Status.VERIFIED, evidence=ev, confidence=1.0,
                   note=note, derived_from=list(basis))

    @classmethod
    def not_extracted(cls, note: str = '') -> 'Fact[T]':
        """Our gap. Never a claim that the authority is silent."""
        return cls(value=None, status=Status.NOT_EXTRACTED,
                   note=note or 'no reader matched this in the documents that were read; '
                                'this is a gap in GovOS, not a statement about the authority')


# ====================================================================== scope
class ScopeKind(str, Enum):
    """What a rule can be narrowed to. A rule with no scope governs the whole exam."""

    EXAM = 'EXAM'
    POST = 'POST'
    CATEGORY = 'CATEGORY'
    STAGE = 'STAGE'
    PAPER = 'PAPER'
    SUBJECT = 'SUBJECT'
    SECTION = 'SECTION'
    CYCLE = 'CYCLE'
    #: An authority's own grouping that matches none of the above; `label` carries its word.
    OTHER = 'OTHER'


@dataclass(frozen=True)
class ScopeRef:
    """"This applies to ..." — one dimension of it.

    `label` is the authority's own wording, kept because a category or a post group named in
    a notice is often not a word any schema anticipated. `ref` points at an id inside this
    record where one exists.
    """

    kind: ScopeKind
    ref: str = ''
    label: str = ''

    def __str__(self) -> str:
        return f'{self.kind.value}:{self.label or self.ref or "*"}'


@dataclass
class Scope:
    """A conjunction of refs: every one must hold for the rule to apply.

    Empty means the whole exam. `[POST:x]` means that post. `[POST:x, CATEGORY:y]` means
    that post for that category — which is how a notice states a relaxation without needing
    a separate shape for it.
    """

    refs: list[ScopeRef] = dc_field(default_factory=list)

    @property
    def is_global(self) -> bool:
        return not self.refs

    def of(self, kind: ScopeKind) -> list[ScopeRef]:
        return [r for r in self.refs if r.kind is kind]

    def covers(self, other: 'Scope') -> bool:
        """Is `other` at least as specific as this scope?

        A global rule covers everything; a post rule covers that post's category rules. This
        is how a more specific rule is found to override a general one, later, by the
        conflict engine — the contract only needs to make the relation expressible.
        """
        return all(r in other.refs for r in self.refs)

    def __str__(self) -> str:
        return ' & '.join(str(r) for r in self.refs) if self.refs else 'EXAM (global)'


# ======================================================================== age
@dataclass
class AgeRelaxation:
    """An extension of the age band for some group, as the authority states it.

    Two forms are in use and both must be representable: "five years for X" (`years`) and
    "the upper age limit for X is N" (`absolute_maximum`). Storing only the first would
    force us to compute the second, which means inventing an arithmetic the notice did not
    print.
    """

    #: The authority's own words for the group. Not an enum: authorities use their own.
    category_label: str
    scope: Scope = dc_field(default_factory=Scope)
    years: Fact[float] = dc_field(default_factory=Fact)
    absolute_maximum: Fact[float] = dc_field(default_factory=Fact)
    absolute_minimum: Fact[float] = dc_field(default_factory=Fact)
    #: "subject to a maximum of five years", "for those domiciled in ...", as printed.
    conditions: Fact[str] = dc_field(default_factory=Fact)


@dataclass
class AgeRule:
    """One age rule, with the things a rule actually varies by.

    This shape holds, without changing:

      A. a global rule            -- `scope.is_global`
      B. a post-specific rule     -- `scope` names the post
      C. category relaxation      -- `relaxations`, each with its own scope and evidence
      D. a different cutoff date  -- `cutoff_date` is per rule, not per exam
      E. rules from two documents -- two `AgeRule`s, each citing its own source

    The old shape could express only B, with the cutoff shared across the whole exam and the
    relaxations hard-coded in the frontend with no source at all.
    """

    id: str = ''
    scope: Scope = dc_field(default_factory=Scope)
    minimum_age: Fact[float] = dc_field(default_factory=Fact)
    maximum_age: Fact[float] = dc_field(default_factory=Fact)
    #: The date age is reckoned on, in the authority's own format alongside ISO where parsed.
    cutoff_date: Fact[str] = dc_field(default_factory=Fact)
    #: Some notices state a date-of-birth window instead of an age band. Both are kept as
    #: printed rather than converting one into the other.
    born_not_earlier_than: Fact[str] = dc_field(default_factory=Fact)
    born_not_later_than: Fact[str] = dc_field(default_factory=Fact)
    relaxations: list[AgeRelaxation] = dc_field(default_factory=list)
    note: str = ''

    @property
    def is_global(self) -> bool:
        return self.scope.is_global

    def relaxations_for(self, category_label: str) -> list[AgeRelaxation]:
        want = (category_label or '').strip().lower()
        return [r for r in self.relaxations if r.category_label.strip().lower() == want]


# ==================================================================== pattern
class PatternLevel(str, Enum):
    """What a node in the pattern tree *is*.

    Deliberately structural. There is no TIER_1, no PRELIMS, no MAINS: those are one
    authority's names for a stage, and the authority's own word is kept in `level_label`
    and `name` instead.
    """

    STAGE = 'STAGE'
    PAPER = 'PAPER'
    SUBJECT = 'SUBJECT'
    SECTION = 'SECTION'
    PART = 'PART'
    OTHER = 'OTHER'


@dataclass
class NegativeMarking:
    """Stated as data, not prose, while keeping the prose.

    `as_printed` is what the notice says; the numbers are a reading of it. A notice with an
    unusual rule keeps its sentence and leaves the numbers unset rather than being forced
    into a fraction nobody printed.
    """

    as_printed: str = ''
    deducted_per_wrong: Optional[float] = None
    awarded_per_correct: Optional[float] = None
    applies_to_unattempted: bool = False
    #: Where the rule is a share of the question's own marks rather than a flat figure --
    #: "one-third of the marks assigned to that question" -- the share is kept as well as
    #: the figure it works out to, because the share is what the notice actually says.
    fraction_of_marks: Optional[float] = None

    @property
    def is_none(self) -> bool:
        """The authority stating there is no penalty. Not the same as not knowing."""
        return self.deducted_per_wrong == 0 and bool(self.as_printed)


@dataclass
class CategoryMinimum:
    """A minimum an authority prints for one group of candidates.

    The label is the authority's own column heading, whatever groups it chooses to name.
    """

    label: str
    minimum_marks: Optional[float] = None
    minimum_percent: Optional[float] = None


@dataclass
class QualifyingRule:
    """Whether a node counts towards the merit, and what clearing it takes."""

    as_printed: str = ''
    is_qualifying_only: Optional[bool] = None
    minimum_marks: Optional[float] = None
    minimum_percent: Optional[float] = None
    counts_towards_merit: Optional[bool] = None
    #: Where the minimum differs by category, as one notice's two columns do. Empty where
    #: the authority prints a single minimum for everyone.
    by_category: list[CategoryMinimum] = dc_field(default_factory=list)


@dataclass
class DurationVariant:
    """A duration an authority prints for a particular group of candidates.

    One notice prints the ordinary time and, in the same cell, a longer time for candidates
    eligible for a scribe. Both are the authority's, and neither replaces the other.
    """

    minutes: Optional[int] = None
    as_printed: str = ''
    #: Who it applies to, in the authority's words. Empty means every candidate.
    applies_to: str = ''


@dataclass
class PatternNode:
    """One node of the exam's structure, whatever depth the authority uses.

    The tree is the point. Stage -> Paper -> Section, Stage -> Subject -> Section and
    Stage -> Paper -> Subject -> Section are one shape at different depths, so no exam needs
    a branch and nothing is flattened away. Every measurable is a `Fact`, because a notice
    may print the marks and not the duration, and "not printed" must survive.
    """

    id: str
    level: PatternLevel
    #: The authority's own word for this level -- "Tier", "Paper", "Session", "Part".
    level_label: str = ''
    #: The authority's own name for this node.
    name: str = ''
    order: int = 0
    children: list['PatternNode'] = dc_field(default_factory=list)

    questions: Fact[int] = dc_field(default_factory=Fact)
    marks: Fact[float] = dc_field(default_factory=Fact)
    duration_minutes: Fact[int] = dc_field(default_factory=Fact)
    negative_marking: Fact[NegativeMarking] = dc_field(default_factory=Fact)
    qualifying: Fact[QualifyingRule] = dc_field(default_factory=Fact)
    #: Languages the paper is set in, as the authority lists them.
    languages: Fact[list] = dc_field(default_factory=Fact)
    mode: Fact[str] = dc_field(default_factory=Fact)
    #: Anything the authority prints about this node that has no dedicated slot.
    remarks: Fact[str] = dc_field(default_factory=Fact)

    #: The authority's own identifier for the node -- "Paper-II", "Section-III", "Tier-I".
    code: str = ''
    #: Objective / multiple choice / descriptive / conventional / practical, as printed.
    question_type: Fact[str] = dc_field(default_factory=Fact)
    #: Printed where a notice writes marks as "60*3 = 180"; otherwise derived from the
    #: marks and the question count, and then marked as derived.
    marks_per_question: Fact[float] = dc_field(default_factory=Fact)
    #: True only where the authority says each section is timed separately.
    sectional_timing: Fact[bool] = dc_field(default_factory=Fact)
    #: Extra durations for named groups of candidates, beside `duration_minutes`.
    duration_variants: list[DurationVariant] = dc_field(default_factory=list)
    #: Evidence for the node's own existence, as distinct from any one of its fields.
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    status: Status = Status.NOT_EXTRACTED

    def walk(self) -> Iterator['PatternNode']:
        yield self
        for child in self.children:
            yield from child.walk()

    def of_level(self, level: PatternLevel) -> list['PatternNode']:
        return [n for n in self.walk() if n.level is level]

    def depth(self) -> int:
        return 1 + max((c.depth() for c in self.children), default=0)

    def path_labels(self) -> list[str]:
        return [self.level_label or self.level.value]


@dataclass
class ExamPattern:
    """The pattern as a forest of stages, plus whatever the authority said about it."""

    stages: list[PatternNode] = dc_field(default_factory=list)
    note: Fact[str] = dc_field(default_factory=Fact)
    #: The exam this pattern belongs to. A pattern with no exam id is not publishable:
    #: a scheme page shared by several exams must not contribute to whichever one happens
    #: to be selected.
    exam_id: str = ''
    #: The cycle the authority printed it for, where it says so.
    cycle: str = ''

    def walk(self) -> Iterator[PatternNode]:
        for s in self.stages:
            yield from s.walk()

    def of_level(self, level: PatternLevel) -> list[PatternNode]:
        return [n for n in self.walk() if n.level is level]

    def max_depth(self) -> int:
        return max((s.depth() for s in self.stages), default=0)

    def find(self, node_id: str) -> Optional[PatternNode]:
        return next((n for n in self.walk() if n.id == node_id), None)


# =================================================================== syllabus
@dataclass
class SyllabusNode:
    """A syllabus entry at whatever level the authority put it.

    Same reasoning as the pattern tree, and the same refusal to fix a depth. An authority
    that writes Paper -> Subject -> Topic -> Subtopic and one that writes Subject -> Topic
    are both represented exactly; neither is padded to five levels nor flattened to one.

    `level_label` preserves the source's own word for the level, so the hierarchy that was
    printed can be shown again rather than reinterpreted.
    """

    id: str
    title: str
    #: The authority's own word: "Paper", "Section", "Unit", "Module", "Topic".
    level_label: str = ''
    #: Where this sits in the exam's structure, if the syllabus says so.
    scope: Scope = dc_field(default_factory=Scope)
    order: int = 0
    children: list['SyllabusNode'] = dc_field(default_factory=list)
    #: Evidence for *this node's existence and wording*, not for its children.
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    status: Status = Status.NOT_EXTRACTED
    #: Anything GovOS derived rather than read -- weightage, question counts. Marked as
    #: derived by its own Fact status, never as the authority's.
    derived: dict = dc_field(default_factory=dict)
    note: str = ''

    def walk(self) -> Iterator['SyllabusNode']:
        yield self
        for child in self.children:
            yield from child.walk()

    def depth(self) -> int:
        return 1 + max((c.depth() for c in self.children), default=0)

    def leaves(self) -> list['SyllabusNode']:
        return [n for n in self.walk() if not n.children]


@dataclass
class Syllabus:
    """The syllabus as the authority structured it."""

    roots: list[SyllabusNode] = dc_field(default_factory=list)
    source_note: Fact[str] = dc_field(default_factory=Fact)

    def walk(self) -> Iterator[SyllabusNode]:
        for r in self.roots:
            yield from r.walk()

    def max_depth(self) -> int:
        return max((r.depth() for r in self.roots), default=0)

    def level_labels(self) -> list[str]:
        """Every level word this authority used, in the order they first appear."""
        return list(dict.fromkeys(n.level_label for n in self.walk() if n.level_label))

    def find(self, node_id: str) -> Optional[SyllabusNode]:
        return next((n for n in self.walk() if n.id == node_id), None)


# ================================================================ paper identity
@dataclass(frozen=True)
class PaperIdentity:
    """Which paper, exactly.

    Exam plus year identifies a *cycle*, not a paper, and a cycle can contain many papers —
    and a paper can exist in several languages and several booklet series. Identifying by
    exam and year is what lets one exam's key be attached to another's paper, so identity
    here is a tuple and `key()` is what anything else must match on.

    Every part beyond `exam_id` is optional, because authorities differ in how finely they
    label. What is not optional is that the parts which *were* printed are kept.
    """

    exam_id: str
    #: The cycle as the authority labels it -- usually a year, sometimes "2026-I".
    cycle: str = ''
    stage: str = ''
    paper: str = ''
    subject: str = ''
    language: str = ''
    #: Booklet series / set code, where the authority prints one.
    set_code: str = ''
    #: Shift or session, for exams conducted in multiple sittings.
    session: str = ''

    def key(self) -> str:
        parts = [self.exam_id, self.cycle, self.stage, self.paper, self.subject,
                 self.language, self.set_code, self.session]
        return '|'.join(re.sub(r'\s+', ' ', (p or '').strip().lower()) for p in parts)

    @property
    def is_paper_level(self) -> bool:
        """Does this identify a paper, or merely a cycle?

        Exam plus cycle is not a paper. Something naming the stage, the paper or the
        subject is the minimum that can distinguish one paper of a cycle from another.
        """
        return bool(self.exam_id and (self.stage or self.paper or self.subject))

    def describe(self) -> str:
        bits = [b for b in (self.cycle, self.stage, self.paper, self.subject,
                            self.language, self.set_code, self.session) if b]
        return ' · '.join(bits) or self.exam_id

    def matches(self, other: 'PaperIdentity') -> bool:
        """Same paper, allowing either side to be less specific about parts it never printed."""
        if self.exam_id != other.exam_id:
            return False
        for a, b in ((self.cycle, other.cycle), (self.stage, other.stage),
                     (self.paper, other.paper), (self.subject, other.subject),
                     (self.language, other.language), (self.set_code, other.set_code),
                     (self.session, other.session)):
            if a and b and a.strip().lower() != b.strip().lower():
                return False
        return True


@dataclass
class OfficialPaper:
    """A question paper the authority itself published."""

    identity: PaperIdentity
    url: Fact[str] = dc_field(default_factory=Fact)
    title: str = ''
    published_at: Fact[str] = dc_field(default_factory=Fact)
    #: Where the text could not be read -- a scan with no text layer -- this stays
    #: NOT_EXTRACTED. "We could not read it" and "they published nothing" are not the same
    #: claim, and the paper's own presence is the proof of which one applies.
    contents: Fact[list] = dc_field(default_factory=Fact)
    status: Status = Status.NOT_EXTRACTED
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    note: str = ''


# =================================================================== questions
class QuestionFormat(str, Enum):
    """What kind of question it is, as the paper presents it.

    Open by design. An authority that asks for an essay, a numerical value, a match, or a
    passage-based comprehension is not asking an MCQ with the options missing, and forcing
    all of them into one shape is how a descriptive paper acquires four fake options.
    """

    MULTIPLE_CHOICE = 'MULTIPLE_CHOICE'
    MULTIPLE_SELECT = 'MULTIPLE_SELECT'
    NUMERICAL = 'NUMERICAL'
    DESCRIPTIVE = 'DESCRIPTIVE'
    ASSERTION_REASON = 'ASSERTION_REASON'
    MATCHING = 'MATCHING'
    PASSAGE_BASED = 'PASSAGE_BASED'
    OTHER = 'OTHER'


class AnswerStatus(str, Enum):
    """What the authority has said about this question's answer.

    ACTIVE and PUBLISHED are not the same thing: a question is ACTIVE and its answer may
    still be unpublished. DROPPED, CANCELLED and MULTIPLE_ACCEPTED are published decisions
    and are recorded only where a document states them -- silence is UNKNOWN, never a
    cancellation.
    """

    PUBLISHED = 'PUBLISHED'
    NOT_PUBLISHED = 'NOT_PUBLISHED'
    DROPPED = 'DROPPED'
    CANCELLED = 'CANCELLED'
    MULTIPLE_ACCEPTED = 'MULTIPLE_ACCEPTED'
    REVISED = 'REVISED'
    UNKNOWN = 'UNKNOWN'


class SourceStatus(str, Enum):
    """How good the evidence behind an item is, in the candidate's terms.

    Only OFFICIAL_VERIFIED may be badged as official. A coaching site's transcription of a
    paper may be useful for finding the paper; it is never the paper.
    """

    OFFICIAL_VERIFIED = 'OFFICIAL_VERIFIED'
    SECONDARY_UNVERIFIED = 'SECONDARY_UNVERIFIED'
    NEEDS_REVIEW = 'NEEDS_REVIEW'
    NOT_PUBLISHED = 'NOT_PUBLISHED'
    NOT_EXTRACTED = 'NOT_EXTRACTED'


@dataclass
class QuestionOption:
    """One option, with the label the paper printed beside it.

    The label matters: a key that says "(b)" cannot be applied to a paper whose options are
    numbered 1-4 unless the label is kept, and matching by position is how an answer ends up
    against the wrong option.
    """

    label: str
    text: str = ''


@dataclass
class AnswerEntry:
    """What the authority says the answer is, for one question of one paper.

    A list, because a key may accept more than one option after objections. A status,
    because "no answer published" and "this question was dropped" are different findings and
    neither is the other's default.
    """

    question_number: str
    paper: 'PaperIdentity' = dc_field(default_factory=lambda: PaperIdentity(exam_id=''))
    #: Option labels the key accepts -- usually one, sometimes several, sometimes none.
    accepted: list = dc_field(default_factory=list)
    #: For a numerical answer, the value as printed.
    value: str = ''
    status: AnswerStatus = AnswerStatus.UNKNOWN
    #: The answer this one replaces, where a later key changed it. Kept, never overwritten.
    supersedes: Optional['AnswerEntry'] = None
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    note: str = ''

    @property
    def is_publishable(self) -> bool:
        """An answer is shown only where a document was read and its span verified."""
        return (self.status in (AnswerStatus.PUBLISHED, AnswerStatus.MULTIPLE_ACCEPTED,
                                AnswerStatus.REVISED)
                and bool(self.accepted or self.value)
                and any(e.is_verbatim for e in self.evidence))


@dataclass
class OfficialQuestion:
    """One question of one paper, bound to the exact paper it was printed in.

    Identity is the paper *and* the number: "Question 47" means nothing on its own, and two
    shifts of one day both have a 47. `identity_key()` is what anything matching questions
    must compare, and it is deliberately not the question's text -- a bilingual paper prints
    the same question twice and both are the same question.
    """

    paper: 'PaperIdentity'
    number: str
    text: str = ''
    format: QuestionFormat = QuestionFormat.OTHER
    options: list[QuestionOption] = dc_field(default_factory=list)
    #: Where the paper prints marks per question. Never assumed from the pattern, and where
    #: it is derived from a verified pattern the Fact records what it was derived from.
    marks: Fact[float] = dc_field(default_factory=Fact)
    negative_marks: Fact[float] = dc_field(default_factory=Fact)
    #: The authority's own language label for this version of the question.
    language: str = ''
    #: Questions that share a passage carry the same group id; the passage itself is one
    #: node rather than being repeated into each question.
    passage_id: str = ''
    passage_text: str = ''
    section: str = ''
    subject: str = ''
    answer: Optional[AnswerEntry] = None
    source_status: SourceStatus = SourceStatus.NOT_EXTRACTED
    status: Status = Status.NOT_EXTRACTED
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    note: str = ''

    def identity_key(self) -> str:
        return f'{self.paper.key()}#{(self.number or "").strip().lower()}'

    @property
    def is_publishable(self) -> bool:
        """Publishable only with an exact paper, a number, text, and verbatim evidence."""
        return (self.paper.is_paper_level and bool(self.number) and bool(self.text.strip())
                and self.source_status is SourceStatus.OFFICIAL_VERIFIED
                and any(e.is_verbatim for e in self.evidence))


class AnswerKeyKind(str, Enum):
    PROVISIONAL = 'PROVISIONAL'
    FINAL = 'FINAL'
    REVISED = 'REVISED'
    UNSPECIFIED = 'UNSPECIFIED'


@dataclass
class AnswerKey:
    """A key, bound to the exact paper it answers.

    `paper` is a full `PaperIdentity` and not an exam id with a year, because a key attached
    to a cycle could be applied to any paper in it. A revised key points at what it revises,
    so the history survives instead of being overwritten.
    """

    paper: PaperIdentity
    kind: AnswerKeyKind = AnswerKeyKind.UNSPECIFIED
    url: Fact[str] = dc_field(default_factory=Fact)
    published_at: Fact[str] = dc_field(default_factory=Fact)
    #: Key id this one supersedes, where the authority issued a correction.
    revises: str = ''
    id: str = ''
    status: Status = Status.NOT_EXTRACTED
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    note: str = ''
    #: The answers themselves, where the authority publishes them. Empty is an ordinary
    #: outcome: several authorities announce a key and serve it only to each candidate
    #: behind their own login, so the key exists, its paper is exact, and its contents are
    #: not public.
    entries: list['AnswerEntry'] = dc_field(default_factory=list)
    #: How a candidate reaches the key, in the authority's words.
    access: str = ''
    #: The window in which the key may be viewed or challenged, where one is published.
    window_opens: str = ''
    window_closes: str = ''
    source_status: 'SourceStatus' = None

    @property
    def is_publishable(self) -> bool:
        """A key is shown only when it names its exact paper and cites a document."""
        return (self.paper.is_paper_level
                and any(e.is_verbatim for e in self.evidence))

    @property
    def is_attached_to_a_paper(self) -> bool:
        return self.paper.is_paper_level


# ================================================================ application
@dataclass
class ApplicationField:
    """One thing the form asks for, as the source describes it."""

    id: str
    label: str
    #: The authority's own word for the input, where it gives one.
    input_kind: str = ''
    required: Optional[bool] = None
    #: Format rules as printed -- sizes, ranges, accepted values.
    constraints: list = dc_field(default_factory=list)
    help_text: str = ''
    evidence: list[SourceEvidence] = dc_field(default_factory=list)


@dataclass
class RequiredDocument:
    """A document or upload the stage requires, with whatever specification was printed."""

    id: str
    name: str
    #: Dimensions, file size, format, ink colour -- whatever the source states, as stated.
    specifications: list = dc_field(default_factory=list)
    required: Optional[bool] = None
    evidence: list[SourceEvidence] = dc_field(default_factory=list)


@dataclass
class ApplicationStage:
    """One step of applying, exactly as the official source describes it.

    Nothing here presumes account creation, registration or payment. An authority that
    applies in two steps has two stages; one that applies in eight has eight. The names are
    the authority's.
    """

    id: str
    title: str
    order: int = 0
    description: str = ''
    fields: list[ApplicationField] = dc_field(default_factory=list)
    documents: list[RequiredDocument] = dc_field(default_factory=list)
    #: Rules and warnings printed for this step, each carrying where it was read from.
    instructions: list[Fact] = dc_field(default_factory=list)
    #: Steps that must be finished first, by id, where the source says so.
    depends_on: list[str] = dc_field(default_factory=list)
    is_one_time: Optional[bool] = None
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    status: Status = Status.NOT_EXTRACTED
    #: Why this stage is NEEDS_REVIEW, in words a person can act on.
    note: str = ''


@dataclass
class ApplicationProcess:
    """How one applies for one exam."""

    exam_id: str = ''
    authority: str = ''
    portal: Fact[str] = dc_field(default_factory=Fact)
    stages: list[ApplicationStage] = dc_field(default_factory=list)
    #: Fees live here because an authority states them per category and per post, which the
    #: scope on each entry carries.
    fees: list['FeeRule'] = dc_field(default_factory=list)
    note: str = ''

    def stage(self, stage_id: str) -> Optional[ApplicationStage]:
        return next((s for s in self.stages if s.id == stage_id), None)


@dataclass
class FeeRule:
    """An amount, and who it applies to."""

    scope: Scope = dc_field(default_factory=Scope)
    amount: Fact[float] = dc_field(default_factory=Fact)
    currency: str = 'INR'
    #: "exempted", "nil" -- stated exemptions are a fact, not a zero we computed.
    is_exempt: Fact[bool] = dc_field(default_factory=Fact)
    accepted_modes: Fact[list] = dc_field(default_factory=Fact)
    note: str = ''


# ================================================================== milestones
class DatePrecision(str, Enum):
    """How exactly the authority stated it. Never more exact than what was printed.

    An authority that says "in June 2026" has said a month, and recording a day would be
    inventing one. MONTH and YEAR exist so that imprecision can be carried honestly rather
    than rounded into a false certainty or dropped.
    """

    DAY = 'DAY'
    MONTH = 'MONTH'
    YEAR = 'YEAR'
    #: A date the authority described without giving one -- "a date to be notified later".
    UNSPECIFIED = 'UNSPECIFIED'


class MilestoneState(str, Enum):
    """What has happened to this event, as distinct from how well we know it.

    `Status` says how confident we are in the reading. This says what the authority did:
    announced it, moved it, or called it off. A postponed exam with no new date is a real
    thing to show a candidate, and the old shape could not show it.
    """

    ANNOUNCED = 'ANNOUNCED'
    POSTPONED = 'POSTPONED'
    RESCHEDULED = 'RESCHEDULED'
    CANCELLED = 'CANCELLED'
    #: Stated as existing but with no date yet -- "will be announced in due course".
    AWAITED = 'AWAITED'


@dataclass
class Milestone:
    """A dated event, scoped to whatever it concerns.

    `kind` is the authority's own label. There is no closed set, because the old one
    contained EXAM_TIER1 and EXAM_TIER2 and could not express a third written stage. The
    scope is what lets a paper-specific or stage-specific date exist at all.

    A range is one milestone with both ends, not two rows: an application window is a single
    event in a candidate's head and splitting it loses the relationship between its ends.
    """

    id: str
    #: The authority's own wording for the event.
    label: str
    #: A coarse, open classification for grouping in a UI. Free text by design.
    kind: str = ''
    scope: Scope = dc_field(default_factory=Scope)
    #: The cycle this belongs to, as the authority labels it. A document may describe more
    #: than one, and a date from the wrong cycle is as wrong as one from the wrong exam.
    cycle: str = ''
    starts_at: Fact[str] = dc_field(default_factory=Fact)
    ends_at: Fact[str] = dc_field(default_factory=Fact)
    precision: DatePrecision = DatePrecision.DAY
    state: MilestoneState = MilestoneState.ANNOUNCED
    is_tentative: Optional[bool] = None
    #: Dates the authority offered as alternatives to this one, each evidenced. Not
    #: candidates we are choosing between -- alternatives the authority itself published.
    alternatives: list[Fact] = dc_field(default_factory=list)
    #: Set when a later document replaced this milestone; the old one is kept, not deleted.
    superseded_by: str = ''
    #: The milestone this one replaces, so the chain reads in both directions.
    supersedes: str = ''
    #: The document that made the change, for a revision.
    revision_source_id: str = ''
    status: Status = Status.NOT_EXTRACTED
    note: str = ''

    @property
    def is_superseded(self) -> bool:
        return bool(self.superseded_by)

    @property
    def is_range(self) -> bool:
        return self.starts_at.has_value and self.ends_at.has_value

    @property
    def effective_date(self) -> Optional[str]:
        """The moment this milestone currently points at, or None.

        The end of a window is what a candidate needs -- a deadline, not an opening -- so a
        range reports its end. A superseded or cancelled milestone reports nothing, because
        it no longer points anywhere a candidate should act on.
        """
        if self.is_superseded or self.state is MilestoneState.CANCELLED:
            return None
        if self.ends_at.has_value:
            return self.ends_at.value
        return self.starts_at.value if self.starts_at.has_value else None

    @property
    def is_actionable(self) -> bool:
        """May this drive a reminder?

        Only a verified, effective date. A reading we are unsure of, an event the authority
        has not dated, and a date that has been replaced must never become a notification --
        a candidate acting on one of those is worse off than a candidate with no reminder.
        """
        return (self.status is Status.VERIFIED
                and self.effective_date is not None
                and self.state in (MilestoneState.ANNOUNCED, MilestoneState.RESCHEDULED)
                and self.precision is DatePrecision.DAY)


# ======================================================================= posts
@dataclass
class Post:
    """One post or service, with everything stated about it kept as a Fact.

    Nothing is required beyond an id and a name. The old shape made `classification` a
    required closed union, which meant a post whose group the notice did not print could
    not be recorded at all -- and that really happened.
    """

    id: str
    name: str
    department: Fact[str] = dc_field(default_factory=Fact)
    classification: Fact[str] = dc_field(default_factory=Fact)
    pay: Fact[str] = dc_field(default_factory=Fact)
    #: Per post, per category, per cycle -- whatever the notice breaks them down by.
    vacancies: list['VacancyCount'] = dc_field(default_factory=list)
    qualification: list['QualificationRule'] = dc_field(default_factory=list)
    #: Physical standards, medical standards, licences -- open, because authorities differ.
    other_requirements: list[Fact] = dc_field(default_factory=list)
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    status: Status = Status.NOT_EXTRACTED
    note: str = ''


@dataclass
class VacancyCount:
    scope: Scope = dc_field(default_factory=Scope)
    count: Fact[int] = dc_field(default_factory=Fact)
    #: "expected", "provisional", "subject to variation" -- as printed.
    qualifier: str = ''


@dataclass
class QualificationRule:
    """An educational or professional requirement, scoped like every other rule."""

    scope: Scope = dc_field(default_factory=Scope)
    requirement: Fact[str] = dc_field(default_factory=Fact)
    #: "on or before the last date of application" -- when it must be held by.
    as_on: Fact[str] = dc_field(default_factory=Fact)
    is_essential: Optional[bool] = None


@dataclass
class Requirement:
    """A condition on who may apply, beyond age and qualification.

    `kind` is open on purpose. Experience, domicile, medical standards, a driving licence, a
    language, a physical standard -- the old contract had a slot for none of these and a
    closed enum for the ones it did have, so an authority with an unusual condition could
    not be recorded at all. The authority's own wording is kept in `statement`.
    """

    kind: str
    statement: Fact[str] = dc_field(default_factory=Fact)
    scope: Scope = dc_field(default_factory=Scope)
    #: True where the authority marks it essential, False where desirable, None unstated.
    is_essential: Optional[bool] = None
    note: str = ''


@dataclass
class Eligibility:
    """Every rule about who may apply, each carrying its own scope and source."""

    age_rules: list[AgeRule] = dc_field(default_factory=list)
    qualifications: list[QualificationRule] = dc_field(default_factory=list)
    nationality: list[Fact] = dc_field(default_factory=list)
    attempts: list['AttemptRule'] = dc_field(default_factory=list)
    #: Experience, domicile, medical, physical, licence, language -- whatever was published.
    requirements: list[Requirement] = dc_field(default_factory=list)
    other_rules: list[Fact] = dc_field(default_factory=list)

    def relaxations_for(self, category_label: str, *, post_id: str = ''):
        """Every relaxation an authority published for this category, with its evidence.

        Returns nothing where the authority published nothing. That is the whole point:
        the value this replaces was a constant applied to every exam in the country.
        """
        want = (category_label or '').strip().lower()
        out = []
        for rule in self.age_rules:
            if post_id and rule.scope.refs:
                posts = [r.ref for r in rule.scope.of(ScopeKind.POST)]
                if posts and post_id not in posts:
                    continue
            for relaxation in rule.relaxations:
                if relaxation.category_label.strip().lower() != want:
                    continue
                if post_id:
                    posts = [r.ref for r in relaxation.scope.of(ScopeKind.POST)]
                    if posts and post_id not in posts:
                        continue
                out.append(relaxation)
        return out

    def age_rules_for(self, scope: Scope) -> list[AgeRule]:
        """Rules that govern the given scope, most general first."""
        return [r for r in self.age_rules if r.scope.covers(scope)]

    @property
    def global_age_rule(self) -> Optional[AgeRule]:
        return next((r for r in self.age_rules if r.is_global), None)


@dataclass
class AttemptRule:
    scope: Scope = dc_field(default_factory=Scope)
    maximum_attempts: Fact[int] = dc_field(default_factory=Fact)
    conditions: Fact[str] = dc_field(default_factory=Fact)


# ================================================================== admit card
class SourceOutcome(str, Enum):
    """What happened when a source was read -- never what an authority published.

    `INFRASTRUCTURE_IS_NOT_A_STATUS` is the rule this enum serves. A page that could not be
    fetched, a network that was down, a PDF with no readable text: each says something about
    this run and nothing about the authority, so each is recorded on the *report* and can
    never reach a field. The one claim this enum cannot express is NOT_PUBLISHED, which is a
    finding about the authority and belongs to `Status`.
    """

    READ = 'READ'
    SOURCE_FETCH_FAILURE = 'SOURCE_FETCH_FAILURE'
    NETWORK_UNAVAILABLE = 'NETWORK_UNAVAILABLE'
    SOURCE_UNREADABLE = 'SOURCE_UNREADABLE'
    BUILD_PAUSED = 'BUILD_PAUSED'
    IDENTITY_REFUSED = 'IDENTITY_REFUSED'


class AdmitCardNoticeKind(str, Enum):
    """Kinds of pre-exam notice. Each is a thing that may or may not exist.

    City intimation used to be a boolean every exam answered. It is an advance notice some
    authorities issue and others do not, so it is a kind of notice here: absent means the
    authority issued none, which is a different claim from `false`.
    """

    ADMIT_CARD = 'ADMIT_CARD'
    CITY_INTIMATION = 'CITY_INTIMATION'
    EXAM_INTIMATION = 'EXAM_INTIMATION'
    OTHER = 'OTHER'


@dataclass
class AdmitCardNotice:
    """One call-letter release, scoped to the stage or paper it admits to."""

    id: str
    kind: AdmitCardNoticeKind = AdmitCardNoticeKind.ADMIT_CARD
    scope: Scope = dc_field(default_factory=Scope)
    #: The authority's own words for this thing: "e-Admit Card", "Call Letter",
    #: "Admission Certificate", "City Intimation Slip". Shown to candidates as printed,
    #: because that is the name they will be looking for on the authority's own site.
    official_label: str = ''
    #: The whole row or headline this was read from, where that is longer than the document's
    #: own name. "Download of call letters for Online examination - Preliminary" names an
    #: activity in a schedule; the document it concerns is a "Call letter", and a banner
    #: reading the first is unreadable. Both are kept, and each is shown where it belongs.
    source_label: str = ''
    #: The exam this event admits to, as the source names it. Never the cycle of the record
    #: it is published into: an admit card for a previous cycle is a previous cycle's.
    cycle: str = ''
    released_at: Fact[str] = dc_field(default_factory=Fact)
    #: `DAY` or `MONTH`, as the authority published it. An ISO date has to name some day, so
    #: a month-precision release stores the first -- and without this field a UI would print
    #: "1 August 2026" for an authority that wrote "August, 2026".
    released_precision: str = ''
    available_until: Fact[str] = dc_field(default_factory=Fact)
    #: Where a date is not published but a rule is: "7 days before the examination",
    #: "in August 2026". Kept as printed rather than resolved into a date nobody stated.
    release_rule: Fact[str] = dc_field(default_factory=Fact)
    #: The date of the examination this admits to, where the same source states it. A
    #: separate field from every release date above, because conflating them sends a
    #: candidate to the centre on the day the download opened.
    exam_date: Fact[str] = dc_field(default_factory=Fact)
    #: Where a candidate logs in. Almost every authority has one; almost none publishes a
    #: direct file link, and the two are not the same thing.
    portal_url: Fact[str] = dc_field(default_factory=Fact)
    download_url: Fact[str] = dc_field(default_factory=Fact)
    #: What a candidate needs in order to log in, as listed.
    credentials_required: Fact[list] = dc_field(default_factory=Fact)
    instructions: list[Fact] = dc_field(default_factory=list)
    #: Regional or zonal portals, for authorities organised that way. Empty for those not.
    alternate_portals: list[Fact] = dc_field(default_factory=list)
    #: Documents and items the source says a candidate must bring. Each is its own Fact so
    #: each cites the sentence it came from: exam-day instructions borrowed from another
    #: exam are how a candidate arrives without the identity proof their own authority asked
    #: for.
    documents_required: list[Fact] = dc_field(default_factory=list)
    #: The id of the event this one supersedes, where an authority rescheduled or corrected.
    supersedes: str = ''
    status: Status = Status.NOT_EXTRACTED
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    note: str = ''

    @property
    def is_publishable(self) -> bool:
        """Shown to a candidate only when scoped, evidenced and verbatim.

        A release date with no stage is an admit card for no exam in particular, and a
        claim with no verbatim span is a claim with nothing behind it.
        """
        return (self.status is Status.VERIFIED
                and bool(self.scope.refs or self.cycle)
                and any(e.is_verbatim for e in self.evidence))


# ===================================================================== results
class ResultKind(str, Enum):
    """What an authority published, in structural terms shared across authorities.

    SCHEDULED is deliberately in the same enum and deliberately not a declaration: it is a
    future date an authority printed for a result it has not yet declared. Keeping it here,
    distinct, is what lets the reader carry "expected September 2026" without ever letting it
    render as "declared".
    """

    RESULT = 'RESULT'
    WRITTEN_RESULT = 'WRITTEN_RESULT'
    STAGE_RESULT = 'STAGE_RESULT'
    FINAL_RESULT = 'FINAL_RESULT'
    SHORTLIST = 'SHORTLIST'
    QUALIFIED_LIST = 'QUALIFIED_LIST'
    MERIT_LIST = 'MERIT_LIST'
    SCORECARD = 'SCORECARD'
    MARKS = 'MARKS'
    SELECTION = 'SELECTION'
    WAITLIST = 'WAITLIST'
    DV_SHORTLIST = 'DV_SHORTLIST'
    INTERVIEW_SHORTLIST = 'INTERVIEW_SHORTLIST'
    RECOMMENDATION = 'RECOMMENDATION'
    #: A date the authority scheduled for a result it has not yet declared. Not a result.
    SCHEDULED = 'SCHEDULED'
    OTHER = 'OTHER'

    @property
    def is_declaration(self) -> bool:
        """A result the authority has actually declared, as opposed to a scheduled date."""
        return self not in (ResultKind.SCHEDULED, ResultKind.OTHER)


class ResultLifecycle(str, Enum):
    """Where a declaration sits in its own revision history. Never inferred from a timestamp."""

    ORIGINAL = 'ORIGINAL'
    REVISED = 'REVISED'
    CANCELLED = 'CANCELLED'
    SUPERSEDED = 'SUPERSEDED'


class QualificationState(str, Enum):
    """What the source says happened to the candidates it names -- only where it says it."""

    QUALIFIED = 'QUALIFIED'
    NOT_QUALIFIED = 'NOT_QUALIFIED'
    SHORTLISTED = 'SHORTLISTED'
    SELECTED = 'SELECTED'
    RECOMMENDED = 'RECOMMENDED'
    WAITLISTED = 'WAITLISTED'
    #: The source declares a result but states no qualification outcome in it.
    UNSTATED = 'UNSTATED'



@dataclass
class CutoffMark:
    """A bar, scoped to whatever the authority published it against."""

    scope: Scope = dc_field(default_factory=Scope)
    marks: Fact[float] = dc_field(default_factory=Fact)
    #: "out of 200", "aggregate", as printed.
    basis: str = ''


@dataclass
class ResultDeclaration:
    """One declaration by the authority, scoped to a stage or paper.

    No stage is named in this type. An exam with three written stages and one with a
    prelims/mains pair produce the same shape with different scopes, which is what stops the
    renderer needing to know either of them.
    """

    id: str
    #: The authority's own wording -- "Written Result", "Final Result", "Shortlist".
    label: str = ''
    #: The whole row or headline it was read from, where longer than the document's name.
    source_label: str = ''
    kind: ResultKind = ResultKind.OTHER
    scope: Scope = dc_field(default_factory=Scope)
    #: The cycle the source names -- never the record's own, so a past cycle stays past.
    cycle: str = ''
    #: When the result was declared. A declaration has this; a schedule row does not.
    published_at: Fact[str] = dc_field(default_factory=Fact)
    published_precision: str = ''
    #: When a scheduled result is expected. A schedule row has this; a declaration does not.
    #: Kept apart from `published_at` so an expectation can never render as a declaration.
    expected_at: Fact[str] = dc_field(default_factory=Fact)
    expected_precision: str = ''
    document_url: Fact[str] = dc_field(default_factory=Fact)
    #: Where a candidate signs in for a result served behind login, distinct from a document.
    portal_url: Fact[str] = dc_field(default_factory=Fact)
    qualified_count: Fact[int] = dc_field(default_factory=Fact)
    #: What the source says happened to the candidates, only where it says it.
    qualification: QualificationState = QualificationState.UNSTATED
    #: What happens to those who cleared, in the authority's words. Never inferred.
    next_step: Fact[str] = dc_field(default_factory=Fact)
    #: The stage a cleared candidate advances to, where the source names it.
    next_stage_ref: str = ''
    cutoffs: list[CutoffMark] = dc_field(default_factory=list)
    lifecycle: ResultLifecycle = ResultLifecycle.ORIGINAL
    #: The id of the declaration this one revises, cancels or supersedes.
    supersedes: str = ''
    status: Status = Status.NOT_EXTRACTED
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    note: str = ''

    @property
    def is_declaration(self) -> bool:
        return self.kind.is_declaration

    @property
    def is_publishable(self) -> bool:
        """Shown to a candidate only when scoped, evidenced and verbatim.

        A declaration with no stage is a result for no examination sitting in particular, and
        a claim with no verbatim span is a claim with nothing behind it.
        """
        return (self.status is Status.VERIFIED
                and bool(self.scope.refs or self.cycle)
                and any(e.is_verbatim for e in self.evidence))


# ================================================================== revisions
@dataclass
class Revision:
    """A correction the authority published, and what it changed.

    The old shape had a prose `diffSummary`, so nothing could tell which field a corrigendum
    touched. Here the change is addressable: the field path, the value before and the value
    after, both kept. Deciding *which* wins is the conflict engine's job in a later phase;
    the contract's job is to make sure the question can be asked without losing either side.
    """

    id: str
    #: Dotted path into this record, e.g. "milestones.application_close.ends_at".
    field_path: str = ''
    scope: Scope = dc_field(default_factory=Scope)
    previous_value: Any = None
    revised_value: Any = None
    published_at: Fact[str] = dc_field(default_factory=Fact)
    effective_from: Fact[str] = dc_field(default_factory=Fact)
    #: The document that made the change.
    evidence: list[SourceEvidence] = dc_field(default_factory=list)
    #: The source the change applies *to*.
    supersedes_source_id: str = ''
    summary: str = ''
    #: NEEDS_REVIEW where two documents disagree and nothing in them settles it. A field in
    #: that state is blocked from publication rather than resolved by guesswork.
    status: Status = Status.NOT_EXTRACTED
    note: str = ''


# ==================================================================== identity
@dataclass
class ExamIdentity:
    """Who runs this exam and what it is called, with how well that is known.

    The name statuses from the resolver (CANONICAL_NAME_VERIFIED / INFERRED /
    NAME_UNRESOLVED) had nowhere to land in the old contract; `authority_name` being a Fact
    is where they land now.
    """

    exam_id: str
    official_name: Fact[str] = dc_field(default_factory=Fact)
    authority_name: Fact[str] = dc_field(default_factory=Fact)
    authority_domain: Fact[str] = dc_field(default_factory=Fact)
    #: The cycle this record is about -- a year, or the authority's own cycle label.
    cycle: str = ''
    #: Open, free-text classifications for discovery. Never used for extraction decisions.
    tags: list = dc_field(default_factory=list)


# ======================================================================== root
@dataclass
class UniversalExam:
    """One exam, entirely. One record holds one exam; that is the isolation rule.

    Every section is a list or a tree of scoped, evidenced facts, so an authority that
    publishes little produces a small record rather than a record full of holes labelled as
    absences.
    """

    identity: ExamIdentity
    sources: list[SourceDocument] = dc_field(default_factory=list)
    application: ApplicationProcess = dc_field(default_factory=ApplicationProcess)
    milestones: list[Milestone] = dc_field(default_factory=list)
    posts: list[Post] = dc_field(default_factory=list)
    eligibility: Eligibility = dc_field(default_factory=Eligibility)
    pattern: ExamPattern = dc_field(default_factory=ExamPattern)
    syllabus: Syllabus = dc_field(default_factory=Syllabus)
    papers: list[OfficialPaper] = dc_field(default_factory=list)
    answer_keys: list[AnswerKey] = dc_field(default_factory=list)
    admit_cards: list[AdmitCardNotice] = dc_field(default_factory=list)
    results: list[ResultDeclaration] = dc_field(default_factory=list)
    revisions: list[Revision] = dc_field(default_factory=list)
    #: Build-level infrastructure state (`gate.BuildState`). Kept off every field so an
    #: outage can never be read as an authority's silence.
    build_state: str = ''
    log: list[str] = dc_field(default_factory=list)

    @property
    def exam_id(self) -> str:
        return self.identity.exam_id

    def source(self, source_id: str) -> Optional[SourceDocument]:
        return next((s for s in self.sources if s.id == source_id), None)

    def keys_for(self, paper: PaperIdentity) -> list[AnswerKey]:
        """Every key published for exactly this paper."""
        return [k for k in self.answer_keys if k.paper.matches(paper)]

    def all_facts(self) -> Iterator[tuple[str, Fact]]:
        """Every Fact in the record, with a dotted path. Used by audits and the gate."""
        yield from _walk_facts(self, '')

    def unsourced_facts(self) -> list[str]:
        """Paths of facts claiming a verified value with no verbatim evidence.

        This should always be empty. It is the structural check that the product's central
        rule held for this record.
        """
        return [path for path, f in self.all_facts()
                if f.status is Status.VERIFIED and f.has_value and not f.is_publishable]


def _walk_facts(obj: Any, path: str, _seen: set | None = None) -> Iterator[tuple[str, Fact]]:
    """Walk any nesting of dataclasses, lists and dicts, yielding every Fact found."""
    _seen = _seen if _seen is not None else set()
    if id(obj) in _seen:
        return
    if isinstance(obj, Fact):
        yield path, obj
        return
    if isinstance(obj, (str, bytes, int, float, bool)) or obj is None:
        return
    _seen.add(id(obj))
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _walk_facts(v, f'{path}.{k}' if path else str(k), _seen)
        return
    if isinstance(obj, (list, tuple, set)):
        for i, v in enumerate(obj):
            yield from _walk_facts(v, f'{path}[{i}]', _seen)
        return
    if hasattr(obj, '__dataclass_fields__'):
        for name in obj.__dataclass_fields__:
            yield from _walk_facts(getattr(obj, name, None),
                                   f'{path}.{name}' if path else name, _seen)
