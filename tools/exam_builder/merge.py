"""Getting newly extracted facts into an exam's record without damaging what is there.

This is the gap between a builder that can read documents and a product that shows anything.
It does four things and deliberately no more:

    MATCH      is the extracted fact about the same thing as one already in the record?
    CONFIRM    same answer -> one fact, more sources behind it
    SUPERSEDE  a later official document says it is changing this -> both kept, old inert
    REFUSE     two answers, neither claiming to correct the other -> NEEDS_REVIEW, both kept

The fourth is the one that matters. A merge engine that resolves disagreements is a merge
engine that will eventually resolve one wrongly and quietly, and a candidate cannot tell a
confident wrong date from a right one. So this refuses, loudly, and leaves the record as it
was until a person looks.

What it never does: delete an existing fact, prefer a value because it is newer, or prefer
one because it was extracted rather than authored. A hand-authored record carries a person's
reading of a document, which is at least as good as ours.
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from enum import Enum

import re

from .schema import (Milestone, MilestoneState, ScopeKind, SourceDocument,
                     SourceKind, Status)


class MergeAction(str, Enum):
    ADDED = 'ADDED'                #: nothing in the record covered this
    CONFIRMED = 'CONFIRMED'        #: the record already said this; more evidence now
    SUPERSEDED = 'SUPERSEDED'      #: a later official document changed it
    CONFLICTED = 'CONFLICTED'      #: two answers, no stated relationship between them
    UNCHANGED = 'UNCHANGED'        #: nothing incoming touched this


@dataclass
class MergeDecision:
    """One decision, with enough of its reasoning to be argued with."""

    action: MergeAction
    kind: str
    existing: Milestone | None = None
    incoming: Milestone | None = None
    reason: str = ''

    def describe(self) -> str:
        # The values that were actually compared, not each side's effective date -- for a
        # window against one of its ends those are different, and printing the wrong one
        # makes a correct decision look like a mistake.
        if self.existing is not None and self.incoming is not None:
            left, right = comparable_values(self.existing, self.incoming)
        else:
            left = self.existing.effective_date if self.existing else None
            right = self.incoming.effective_date if self.incoming else None
        return (f'{self.action.value:11} {self.kind:22} '
                f'{left or "—"!s:12} -> {right or "—"!s:12}')


@dataclass
class MergeReport:
    """The merged record, and every decision that produced it."""

    milestones: list[Milestone] = dc_field(default_factory=list)
    decisions: list[MergeDecision] = dc_field(default_factory=list)

    def of(self, action: MergeAction) -> list[MergeDecision]:
        return [d for d in self.decisions if d.action is action]

    @property
    def has_conflicts(self) -> bool:
        return bool(self.of(MergeAction.CONFLICTED))

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out


# ------------------------------------------------------------------- 1. MATCH
#: A window states both ends; a record often stores each end separately. These are the
#: same subject matter at different granularity, so they are allowed to match -- and the
#: comparison below is careful to put the right end against the right end.
_WINDOW_ENDS = {
    'APPLICATION_WINDOW': ('APPLICATION_START', 'APPLICATION_END'),
    'CORRECTION_WINDOW': ('CORRECTION_START', 'CORRECTION_END'),
}


def _kinds_align(a_kind: str, b_kind: str) -> bool:
    if a_kind == b_kind:
        return True
    for window, ends in _WINDOW_ENDS.items():
        if a_kind == window and b_kind in ends:
            return True
        if b_kind == window and a_kind in ends:
            return True
    return False


def comparable_values(a: Milestone, b: Milestone) -> tuple:
    """The two moments to weigh against each other.

    Where one side is a window and the other names a single end, the window's matching end
    is used. Comparing a closing date against an opening date is how the first real merge
    manufactured a disagreement between two values that were never about the same moment.
    """
    for window, (start_kind, end_kind) in _WINDOW_ENDS.items():
        for left, right in ((a, b), (b, a)):
            # Both sides fall back the same way. A window that states only one end still
            # has a moment, and asking one side for a value it does not carry while the
            # other falls back manufactured a difference out of an identical date.
            if left.kind == window and right.kind == start_kind:
                pair = (left.starts_at.value or left.ends_at.value,
                        right.starts_at.value or right.ends_at.value)
                return pair if left is a else tuple(reversed(pair))
            if left.kind == window and right.kind == end_kind:
                pair = (left.ends_at.value or left.starts_at.value,
                        right.ends_at.value or right.starts_at.value)
                return pair if left is a else tuple(reversed(pair))
    return a.effective_date, b.effective_date


def matches(a: Milestone, b: Milestone) -> bool:
    """Are these about the same thing?

    Same kind, same scope, same cycle. Scope is what keeps "Tier II examination" from
    matching "application end" -- and, just as importantly, keeps "Paper I on the 3rd" from
    looking like a contradiction of "Paper II on the 5th". They are two events.
    """
    if not _kinds_align(a.kind, b.kind):
        return False
    if str(a.scope) != str(b.scope):
        return False
    a_cycle, b_cycle = (a.cycle or ''), (b.cycle or '')
    if a_cycle and b_cycle and a_cycle != b_cycle:
        return False
    return True


# ----------------------------------------------------------------- 2/3/4
def _claims_to_revise(incoming: Milestone, source: SourceDocument | None) -> bool:
    """Does this document say it is changing something, rather than merely differing?

    Two ways an authority says so: the wording of the statement itself -- postponed,
    rescheduled, in supersession -- or the document being a corrigendum, which is a document
    whose entire purpose is to correct an earlier one.

    Differing is not revising. A second notice that simply prints a different date is a
    disagreement until something says which came later.
    """
    if incoming.state in (MilestoneState.RESCHEDULED, MilestoneState.POSTPONED,
                          MilestoneState.CANCELLED):
        return True
    return bool(source is not None and source.kind is SourceKind.CORRIGENDUM)


def _same_value(a: Milestone, b: Milestone) -> bool:
    """Do these point at the same moment?

    Only the moments being compared -- not every field. Requiring both ends to agree made a
    record row that stores one end differ from an extracted window that states both, though
    they said exactly the same thing about the end in question.
    """
    left, right = comparable_values(a, b)
    return left == right and left is not None


def _absorb_evidence(keeper: Milestone, other: Milestone) -> None:
    """Add the other reading's evidence, keyed on document as well as wording."""
    for field_name in ('starts_at', 'ends_at'):
        target = getattr(keeper, field_name)
        known = {(e.source_id, e.span_digest) for e in target.evidence}
        for ev in getattr(other, field_name).evidence:
            if (ev.source_id, ev.span_digest) not in known:
                target.evidence.append(ev)


def merge_milestones(existing: list[Milestone], incoming: list[Milestone], *,
                     source: SourceDocument | None = None) -> MergeReport:
    """Fold newly extracted milestones into a record's existing ones.

    The record is the starting point and stays the starting point: nothing is removed, and
    an existing fact that nothing incoming touches comes through untouched.
    """
    report = MergeReport()
    used: set[int] = set()

    for old in existing:
        partner = next((m for m in incoming
                        if id(m) not in used and matches(old, m)), None)
        if partner is None:
            report.milestones.append(old)
            report.decisions.append(MergeDecision(
                MergeAction.UNCHANGED, old.kind, existing=old,
                reason='nothing extracted concerns this'))
            continue
        used.add(id(partner))

        if partner.effective_date is None:
            # Silence is not disagreement. The authority has stated this event without
            # dating it, which adds nothing to a record that already has a date for it.
            report.milestones.append(old)
            report.decisions.append(MergeDecision(
                MergeAction.UNCHANGED, old.kind, existing=old, incoming=partner,
                reason='the official source names this event but gives no date for it, so '
                       'there is nothing to compare against what the record holds'))
            continue

        # 2. CONFIRM
        if _same_value(old, partner):
            _absorb_evidence(old, partner)
            if old.status is not Status.VERIFIED and partner.status is Status.VERIFIED:
                old.status = Status.VERIFIED
            report.milestones.append(old)
            report.decisions.append(MergeDecision(
                MergeAction.CONFIRMED, old.kind, existing=old, incoming=partner,
                reason='an official source states the same value; kept as one fact with '
                       'both sources behind it'))
            continue

        # 3. SUPERSEDE
        if _claims_to_revise(partner, source):
            old.superseded_by = partner.id
            old.note = (old.note + ' ' if old.note else '') + (
                'replaced by a later official document that states it is changing this')
            partner.supersedes = old.id
            if source is not None:
                partner.revision_source_id = source.id
            report.milestones.extend([old, partner])
            report.decisions.append(MergeDecision(
                MergeAction.SUPERSEDED, old.kind, existing=old, incoming=partner,
                reason='the incoming document says it revises this; the old value is kept '
                       'and marked superseded rather than deleted'))
            continue

        # 4. REFUSE
        note = (f'two official readings disagree — the record holds '
                f'{old.effective_date}, an official source states '
                f'{partner.effective_date}, and neither says it is correcting the other. '
                f'Both are kept and neither is published as effective until a person '
                f'resolves it against the documents.')
        old.status = Status.NEEDS_REVIEW
        old.note = (old.note + ' ' if old.note else '') + note
        partner.status = Status.NEEDS_REVIEW
        partner.note = (partner.note + ' ' if partner.note else '') + note
        report.milestones.extend([old, partner])
        report.decisions.append(MergeDecision(
            MergeAction.CONFLICTED, old.kind, existing=old, incoming=partner, reason=note))

    # 1. MATCH found nothing: genuinely new information.
    for new in incoming:
        if id(new) in used:
            continue
        report.milestones.append(new)
        report.decisions.append(MergeDecision(
            MergeAction.ADDED, new.kind, incoming=new,
            reason='the record held nothing about this event'))

    report.milestones.sort(key=lambda m: (m.effective_date or '9999', m.kind))
    return report


# =================================================================== posts
#: Words appearing in so many post names that sharing one proves nothing. Structural: no
#: authority, exam or post is named.
_COMMON_POST_WORDS = frozenset({
    'officer', 'assistant', 'grade', 'service', 'services', 'post', 'posts', 'of', 'the',
    'and', 'in', 'for', 'to', 'central', 'state', 'government', 'india', 'indian',
    'senior', 'junior', 'deputy', 'sub', 'department', 'ministry', 'office', 'cadre',
    'general', 'other', 'various',
})

#: A bracketed abbreviation a record adds for readability -- "(IAS)", "(ASO)". The
#: expansion beside it is already in the name, so it adds nothing to matching.
_ABBREVIATION = re.compile(r'\(\s*[A-Z][A-Z&./-]{1,7}\s*\)')


class FieldOutcome(str, Enum):
    KEPT = 'KEPT'                  #: the record has it; the document says nothing
    CONFIRMED = 'CONFIRMED'        #: both say the same thing
    ADDED = 'ADDED'                #: the document supplies what the record lacked
    UNDER_REVIEW = 'UNDER_REVIEW'  #: they disagree, or the record asserts the unstated


@dataclass
class FieldDecision:
    field: str
    outcome: FieldOutcome
    existing: object = None
    incoming: object = None
    reason: str = ''


@dataclass
class PostDecision:
    action: MergeAction
    name: str
    post_id: str = ''
    fields: list = dc_field(default_factory=list)
    reason: str = ''
    #: How sure we are the two posts are the same, where a match was attempted.
    identity: float = 0.0

    def field(self, name: str):
        return next((f for f in self.fields if f.field == name), None)


@dataclass
class PostMergeReport:
    decisions: list = dc_field(default_factory=list)

    def of(self, action: MergeAction) -> list:
        return [d for d in self.decisions if d.action is action]

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out

    def fields_of(self, outcome: FieldOutcome) -> list:
        return [(d, f) for d in self.decisions for f in d.fields if f.outcome is outcome]


def _name_tokens(name: str) -> set:
    cleaned = _ABBREVIATION.sub(' ', name or '')
    words = re.split(r'[^a-z0-9]+', cleaned.lower())
    return {w for w in words if len(w) > 1 and w not in _COMMON_POST_WORDS}


def post_identity(existing_name: str, incoming_name: str) -> float:
    """How sure we are that two names are the same post.

    One name's distinctive words being a subset of the other's identifies the post a record
    abbreviates and a notice spells out. Sharing a word or two is not enough: post names are
    built from a small shared vocabulary, and "Assistant Section Officer" describes a dozen
    different posts in one notice.
    """
    left, right = _name_tokens(existing_name), _name_tokens(incoming_name)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    shared = left & right
    if not shared:
        return 0.0
    if left <= right or right <= left:
        return 0.9 if len(shared) >= 2 else 0.5
    # Each carries something the other lacks: either two different posts sharing
    # vocabulary, or one post described two ways. Not decidable from the names.
    return 0.4 * len(shared) / max(len(left), len(right))


#: Below this, two posts are not established to be the same, and are not merged.
IDENTITY_THRESHOLD = 0.85


def _classification_letter(text: str) -> str:
    m = re.search(r"\bgroup\s*[-\u2013\u2014]?\s*['\"\u2018\u2019\u201c\u201d]?([a-d])\b",
                  text or '', re.I)
    return m.group(1).lower() if m else ''


def _same_classification(left: str, right: str) -> bool:
    """"Group B (Non-Gazetted)" and "Group B Gazetted (Non-Ministerial)" both say B."""
    a, b = _classification_letter(left), _classification_letter(right)
    return bool(a) and a == b


def _classification_decision(existing, incoming) -> FieldDecision:
    """The field that prompted this work.

    A record asserting a classification its authority does not print is not *contradicted*
    by that authority — silence is not denial. But the assertion is unsupported by the
    document, and saying so is the whole value of having read it.
    """
    stated = bool(incoming is not None and getattr(incoming, 'has_value', False))
    existing = existing or ''
    if not existing and not stated:
        return FieldDecision('classification', FieldOutcome.KEPT,
                             reason='neither the record nor the document states one')
    if not existing and stated:
        return FieldDecision('classification', FieldOutcome.ADDED, None, incoming.value,
                             'the document states a classification the record lacked')
    if existing and not stated:
        return FieldDecision(
            'classification', FieldOutcome.UNDER_REVIEW, existing, None,
            'the record asserts a classification that this official document does not '
            'print for this post. The document is silent rather than opposed, so the '
            'assertion is not contradicted — but it is unsupported, and must not be shown '
            'as the authority’s own.')
    if _same_classification(existing, incoming.value):
        return FieldDecision('classification', FieldOutcome.CONFIRMED, existing,
                             incoming.value, 'the document states the same classification')
    return FieldDecision('classification', FieldOutcome.UNDER_REVIEW, existing,
                         incoming.value,
                         'the record and the document state different classifications')


def _age_decision(existing_min, existing_max, rule) -> FieldDecision:
    if rule is None:
        return FieldDecision('age', FieldOutcome.KEPT, (existing_min, existing_max),
                             reason='the document states no age for this post')
    low, high = rule.minimum_age.value, rule.maximum_age.value
    if low is None or high is None:
        return FieldDecision('age', FieldOutcome.KEPT, (existing_min, existing_max),
                             reason='the document states only part of the band')
    if existing_min is None or existing_max is None:
        return FieldDecision('age', FieldOutcome.ADDED, None, (low, high),
                             'the document states a band the record lacked')
    if (float(existing_min), float(existing_max)) == (float(low), float(high)):
        return FieldDecision('age', FieldOutcome.CONFIRMED, (existing_min, existing_max),
                             (low, high), 'the document states the same band')
    return FieldDecision('age', FieldOutcome.UNDER_REVIEW, (existing_min, existing_max),
                         (low, high),
                         'the record and the document state different age bands for this '
                         'post; neither is published until a person resolves it')


def merge_posts(existing: list, incoming: list, *, age_rules=None) -> PostMergeReport:
    """Fold extracted posts into a record's authored ones, field by field.

    Whole-post rejection would discard a correct name, department and pay scale because one
    field disagreed. So identity is settled for the post and then each field is settled on
    its own: what the record has and the document does not is kept, what both state is
    confirmed, and what they disagree about — or what the record asserts and the document
    does not print — is held for review without being deleted.
    """
    report = PostMergeReport()
    rules_by_post = {}
    for rule in (age_rules or []):
        for ref in rule.scope.of(ScopeKind.POST):
            rules_by_post[ref.ref] = rule

    used: set = set()
    for row in existing:
        name = row.get('postName', '')
        scored = sorted(((post_identity(name, p.name), p) for p in incoming),
                        key=lambda t: -t[0])
        best_score, match = scored[0] if scored else (0.0, None)
        runner_up = scored[1][0] if len(scored) > 1 else 0.0

        if best_score < IDENTITY_THRESHOLD:
            report.decisions.append(PostDecision(
                MergeAction.UNCHANGED, name, row.get('id', ''), identity=best_score,
                reason='no extracted post is established to be this one; the record is '
                       'left exactly as it is'))
            continue
        if runner_up >= IDENTITY_THRESHOLD:
            equal = sum(1 for s, _ in scored if s >= IDENTITY_THRESHOLD)
            report.decisions.append(PostDecision(
                MergeAction.CONFLICTED, name, row.get('id', ''), identity=best_score,
                reason=f'{equal} extracted posts match this one equally well, so which is '
                       f'which is not established; nothing is merged rather than merging '
                       f'the wrong pair'))
            continue

        used.add(id(match))
        fields = [
            FieldDecision('name', FieldOutcome.KEPT, name, match.name,
                          'the record’s wording is kept; the document’s is evidence that '
                          'the post exists'),
            _classification_decision(row.get('classification'), match.classification),
            _age_decision(row.get('minAge'), row.get('maxAge'),
                          rules_by_post.get(match.id)),
        ]
        for field_name in ('department', 'payLevel', 'payScale'):
            if row.get(field_name):
                fields.append(FieldDecision(
                    field_name, FieldOutcome.KEPT, row.get(field_name),
                    reason='the record has it and the document does not improve on it'))

        contested = [f for f in fields if f.outcome is FieldOutcome.UNDER_REVIEW]
        report.decisions.append(PostDecision(
            MergeAction.CONFIRMED if not contested else MergeAction.CONFLICTED,
            name, row.get('id', ''), fields=fields, identity=best_score,
            reason=('the document confirms this post exists' if not contested else
                    f'{len(contested)} field(s) held for review: '
                    f'{", ".join(f.field for f in contested)}')))

    for post in incoming:
        if id(post) in used:
            continue
        report.decisions.append(PostDecision(
            MergeAction.ADDED, post.name, post.id, identity=1.0,
            reason='the document names this post and the record does not hold it'))
    return report
