"""Fold an extracted syllabus into the one a record already holds, node by node.

The same four operations as every other merge here, and the same reason for them. A
syllabus is the part of a record a candidate studies from for a year; a wrong topic quietly
replacing a right one is not a display bug, it is a year of the wrong preparation.

Matching is by title because that is what both sides have: the record stores a flat list of
topics, the document publishes a tree, and a topic is the same topic whether it was printed
under a paper heading or under a clause number. Where two extracted nodes answer to one
authored topic equally well, nothing is merged.

Revision is the one case where a new value may replace an old one, and it needs a document
that says so: a corrigendum, an addendum, or a notice whose own words revise the syllabus.
Absent that, two sources that disagree are both kept and the fact is refused.
"""
from __future__ import annotations

import re

from .merge import FieldDecision, FieldOutcome, MergeAction
from .schema import SourceKind, Status, Syllabus, SyllabusNode

#: Words too common in a syllabus to identify anything on their own.
_GENERIC = frozenset({
    'and', 'the', 'of', 'in', 'to', 'for', 'with', 'its', 'their', 'general', 'basic',
    'questions', 'topics', 'syllabus', 'paper', 'part', 'section', 'subject', 'unit',
    'including', 'etc', 'other', 'various', 'related', 'level', 'study', 'studies',
})


def _words(text: str) -> set:
    return {w for w in re.split(r'[^a-z0-9]+', (text or '').lower())
            if len(w) > 2 and w not in _GENERIC}


def topic_identity(authored_title: str, node: SyllabusNode) -> float:
    """How sure we are that a record's topic and an extracted node are the same topic.

    A syllabus topic is identified by the words that distinguish it. "Number Systems" and
    "Number System" are the same entry; "Number Systems" and "Number Series" are not, and
    sharing "number" is not evidence that they are.
    """
    left, right = _words(authored_title), _words(node.title)
    if not left or not right:
        return 0.0
    if left == right:
        return 1.0
    shared = left & right
    if not shared:
        return 0.0
    if left <= right or right <= left:
        return 0.9 if len(shared) >= 2 else 0.55
    overlap = len(shared) / max(len(left), len(right))
    return round(0.8 * overlap, 3)


#: Below this, two topics are not established to be the same and nothing is merged.
IDENTITY_THRESHOLD = 0.85

#: A document that revises a syllabus rather than publishing one afresh.
_REVISING_KINDS = (SourceKind.CORRIGENDUM,)
_REVISION_WORDS = re.compile(
    r'\b(?:corrigend\w+|addend\w+|amend\w+|revis\w+|modif\w+|substitut\w+|'
    r'in\s+supersession|read\s+as|stands?\s+(?:amended|revised|modified))\b', re.I)


def revises(document, text_span: str = '') -> bool:
    """Does this document say it changes an earlier syllabus?

    A corrigendum by kind, or a document whose own words revise *the syllabus*: "in
    supersession of", "the syllabus stands amended", "may be read as". Being newer is not
    revising -- that is the distinction this whole layer exists to hold -- and neither is
    the word "revised" somewhere on a notice's cover, which is how a notice that merely
    carries a revision date came within one step of superseding two topics.

    The span the caller passes is therefore the span in which the claim must appear, and it
    must mention the syllabus as well as the revision.
    """
    if document is not None and getattr(document, 'kind', None) in _REVISING_KINDS:
        return True
    span = text_span or ''
    if not _REVISION_WORDS.search(span):
        return False
    return bool(re.search(r'(?:syllab\w+|curricul\w+|topics?|papers?)', span, re.I))


class NodeDecision:
    """What the merge decided about one topic, and about each of its fields."""

    def __init__(self, action: MergeAction, title: str, topic_id: str = '',
                 fields: list | None = None, reason: str = '', identity: float = 0.0,
                 superseded: str = '') -> None:
        self.action = action
        self.title = title
        self.topic_id = topic_id
        self.fields = fields or []
        self.reason = reason
        self.identity = identity
        #: The value this decision replaces, kept so the revision can be shown as one.
        self.superseded = superseded

    def field(self, name: str):
        return next((f for f in self.fields if f.field == name), None)


class SyllabusMergeReport:
    def __init__(self) -> None:
        self.decisions: list[NodeDecision] = []

    def of(self, action: MergeAction) -> list:
        return [d for d in self.decisions if d.action is action]

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out

    def fields_of(self, outcome: FieldOutcome) -> list:
        return [(d, f) for d in self.decisions for f in d.fields if f.outcome is outcome]


def merge_syllabus(existing: list, incoming: Syllabus, *, document=None,
                   revision_span: str = '') -> SyllabusMergeReport:
    """Fold an extracted syllabus into a record's authored topics.

    `existing` is the record's `SyllabusTopic[]` as plain dictionaries. Nothing is written
    here: the report says what would change, and publishing is a separate, deliberate step.
    """
    report = SyllabusMergeReport()
    nodes = [n for n in incoming.walk() if n.title]
    is_revision = revises(document, revision_span)
    used: set = set()

    for row in existing:
        title = row.get('topicName', '')
        scored = sorted(((topic_identity(title, node), node) for node in nodes),
                        key=lambda t: -t[0])
        best, match = scored[0] if scored else (0.0, None)
        runner_up = scored[1][0] if len(scored) > 1 else 0.0

        if best < IDENTITY_THRESHOLD:
            report.decisions.append(NodeDecision(
                MergeAction.UNCHANGED, title, row.get('id', ''), identity=best,
                reason='no published entry is established to be this topic; the record is '
                       'left exactly as it is'))
            continue
        if runner_up >= IDENTITY_THRESHOLD:
            report.decisions.append(NodeDecision(
                MergeAction.CONFLICTED, title, row.get('id', ''), identity=best,
                reason='more than one published entry matches this topic equally well, so '
                       'which is which is not established; nothing is merged'))
            continue

        used.add(id(match))
        fields = [FieldDecision(
            'topicName', FieldOutcome.KEPT, title, match.title,
            'the record’s wording is kept; the document’s is evidence that the '
            'authority publishes this topic')]

        same_wording = _words(title) == _words(match.title)
        if not same_wording and is_revision:
            report.decisions.append(NodeDecision(
                MergeAction.SUPERSEDED, match.title, row.get('id', ''), fields=fields,
                identity=best, superseded=title,
                reason='a revising document publishes this topic differently; the old '
                       'wording is kept as superseded rather than deleted'))
            continue
        if not same_wording:
            fields.append(FieldDecision(
                'topicName', FieldOutcome.UNDER_REVIEW, title, match.title,
                'the record and this document word the topic differently and no document '
                'in hand establishes a revision between them, so neither replaces the '
                'other'))
            report.decisions.append(NodeDecision(
                MergeAction.CONFLICTED, title, row.get('id', ''), fields=fields,
                identity=best, reason='the wording is contested'))
            continue

        fields.append(FieldDecision(
            'published', FieldOutcome.CONFIRMED, title, match.title,
            'the authority publishes this topic in its own syllabus'))
        report.decisions.append(NodeDecision(
            MergeAction.CONFIRMED, title, row.get('id', ''), fields=fields, identity=best,
            reason='the document confirms this topic is in the published syllabus'))

    for node in nodes:
        if id(node) in used or node.children:
            # Only entries, not the headings above them: a paper is confirmed by the
            # pattern, and adding it as a topic would double it.
            continue
        report.decisions.append(NodeDecision(
            MergeAction.ADDED, node.title, node.id, identity=1.0,
            reason='the authority publishes this entry and the record does not hold it'))
    return report


def unsupported_topics(existing: list, incoming: Syllabus) -> list:
    """Topics the record asserts that the published syllabus does not contain.

    Not a deletion and not an error: an authority may publish an indicative syllabus while
    a record holds a finer breakdown of it. It is a list for a person, and the reason the
    UI can say which topics are the authority's own words and which are GovOS's reading.
    """
    nodes = [n for n in incoming.walk() if n.title]
    out = []
    for row in existing:
        title = row.get('topicName', '')
        if max((topic_identity(title, n) for n in nodes), default=0.0) < IDENTITY_THRESHOLD:
            out.append(row.get('id', title))
    return out
