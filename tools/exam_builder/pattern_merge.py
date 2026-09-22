"""Fold an extracted pattern into the one a record already holds, field by field.

The same four operations as every other merge in this pipeline -- match, confirm, supersede
through a revision, refuse -- and the same reason for them: a pattern that resolves a
disagreement quietly will one day resolve one wrongly, and a candidate cannot tell a
confident wrong mark from a right one.

Field-level, because a stage is worth more than its weakest field. An authority that has
changed its negative marking has not changed its paper's name, its marks or its duration,
and rejecting the whole paper over the one contested field would throw away four correct
facts to avoid one uncertain one.
"""
from __future__ import annotations

import re

from .merge import FieldDecision, FieldOutcome, MergeAction
from .schema import ExamPattern, PatternNode, Status

#: Words in half the headings an authority writes; they identify nothing on their own.
_GENERIC = frozenset({
    'exam', 'exams', 'examination', 'examinations', 'test', 'tests', 'paper', 'papers',
    'phase', 'tier', 'stage', 'part', 'parts', 'section', 'sections', 'session', 'scheme',
    'online', 'offline', 'objective', 'written', 'round', 'the', 'and', 'of', 'for',
})


def _words(text: str) -> set:
    return {w for w in re.split(r'[^a-z0-9]+', (text or '').lower())
            if len(w) > 2 and w not in _GENERIC}


def _words_all(text: str) -> list:
    """Every word of a name, generic ones included."""
    return [w for w in re.split(r'[^a-z0-9]+', (text or '').lower()) if w]


def _code(text: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', (text or '').lower())


def node_identity(existing_name: str, existing_code: str,
                  node: PatternNode) -> float:
    """How sure we are that a record's stage and an extracted one are the same stage.

    The code decides where both have one -- "Tier-II" is "Tier-II" whatever else the
    heading says. Otherwise the distinguishing words do, and sharing only the vocabulary
    every heading uses ("Examination", "Paper") is not evidence of anything.
    """
    left_code, right_code = _code(existing_code), _code(node.code)
    if left_code and right_code:
        if left_code == right_code:
            return 1.0
        # Different codes are different things, whatever their names look like.
        return 0.0
    left, right = _words(existing_name), _words(node.name)
    if not left or not right:
        # Both names are built entirely from the common vocabulary -- "Scheme of the
        # Examination" against "Scheme of the Examination - one paper". The distinguishing
        # words cannot decide it, so the whole names are compared instead.
        plain_left = ' '.join(_words_all(existing_name))
        plain_right = ' '.join(_words_all(node.name))
        if plain_left and plain_right and (plain_left == plain_right
                                           or plain_right in plain_left
                                           or plain_left in plain_right):
            return 0.9
        return 0.0
    if left == right:
        return 1.0
    shared = left & right
    if not shared:
        return 0.0
    if left <= right or right <= left:
        return 0.9 if len(shared) >= 2 else 0.5
    return 0.4 * len(shared) / max(len(left), len(right))


#: Below this, two stages are not established to be the same and nothing is merged.
IDENTITY_THRESHOLD = 0.85

#: Fields compared one by one. Each is (record key, extracted attribute, how to compare).
_NUMERIC_FIELDS = (
    ('totalQuestions', 'questions'),
    ('totalMarks', 'marks'),
    ('durationMinutes', 'duration_minutes'),
)


def _numeric_decision(field: str, existing, fact) -> FieldDecision:
    """Compare a figure the record holds with the one the document states."""
    stated = fact is not None and fact.has_value and fact.status is Status.VERIFIED
    has_existing = existing not in (None, 0, '')
    if not stated:
        return FieldDecision(field, FieldOutcome.KEPT, existing, None,
                             'the document does not state this for this stage')
    if not has_existing:
        return FieldDecision(field, FieldOutcome.ADDED, None, fact.value,
                             'the document states a figure the record lacked')
    if float(existing) == float(fact.value):
        return FieldDecision(field, FieldOutcome.CONFIRMED, existing, fact.value,
                             'the record and the document agree')
    return FieldDecision(
        field, FieldOutcome.UNDER_REVIEW, existing, fact.value,
        f'the record states {existing} and this official document states {fact.value}; '
        f'no revision relationship is established between them, so neither replaces the '
        f'other until a person decides')


def _negative_decision(existing: str, fact) -> FieldDecision:
    """Negative marking, which is prose in the record and structured in the extraction."""
    stated = fact is not None and fact.has_value
    existing = (existing or '').strip()
    if not stated:
        return FieldDecision('negativeMarking', FieldOutcome.KEPT, existing, None,
                             'the document states no penalty for this stage')
    printed = fact.value.as_printed or ''
    if not existing:
        return FieldDecision('negativeMarking', FieldOutcome.ADDED, None, printed,
                             'the document states a penalty the record lacked')
    if _same_penalty(existing, fact.value):
        return FieldDecision('negativeMarking', FieldOutcome.CONFIRMED, existing, printed,
                             'the record and the document state the same penalty')
    return FieldDecision(
        'negativeMarking', FieldOutcome.UNDER_REVIEW, existing, printed,
        'the record and this official document describe the penalty differently; a wrong '
        'penalty changes how a candidate answers, so neither is published over the other')


def _same_penalty(existing: str, marking) -> bool:
    """Do a sentence and a read rule say the same thing?

    Compared on the figure, because that is the part a candidate acts on. "There will be
    negative marking of 0.50 marks for each wrong answer" and "0.50 marks deducted per
    wrong answer" are the same rule written twice.
    """
    lowered = existing.lower()
    if marking.deducted_per_wrong == 0:
        return bool(re.search(r'\bno\b[^.]{0,20}\bnegative\b|\bnone\b|\bnil\b', lowered))
    figures = {float(f) for f in re.findall(r'\d+(?:\.\d+)?', lowered)}
    if marking.deducted_per_wrong is not None:
        return marking.deducted_per_wrong in figures
    if marking.fraction_of_marks is not None:
        near = {round(marking.fraction_of_marks, 2), round(marking.fraction_of_marks, 4)}
        if figures & near:
            return True
        words = {'one-third': 1 / 3, 'one third': 1 / 3, 'one-fourth': 0.25,
                 'one fourth': 0.25, 'one-quarter': 0.25, 'quarter': 0.25, 'half': 0.5}
        return any(abs(v - marking.fraction_of_marks) < 0.02
                   for key, v in words.items() if key in lowered)
    return False


class StageDecision:
    """What the merge decided about one stage, and about each of its fields."""

    def __init__(self, action: MergeAction, name: str, stage_id: str = '',
                 fields: list | None = None, reason: str = '',
                 identity: float = 0.0) -> None:
        self.action = action
        self.name = name
        self.stage_id = stage_id
        self.fields = fields or []
        self.reason = reason
        self.identity = identity

    def field(self, name: str):
        return next((f for f in self.fields if f.field == name), None)


class PatternMergeReport:
    def __init__(self) -> None:
        self.decisions: list[StageDecision] = []

    def of(self, action: MergeAction) -> list:
        return [d for d in self.decisions if d.action is action]

    def summary(self) -> dict:
        out: dict = {}
        for d in self.decisions:
            out[d.action.value] = out.get(d.action.value, 0) + 1
        return out

    def fields_of(self, outcome: FieldOutcome) -> list:
        return [(d, f) for d in self.decisions for f in d.fields if f.outcome is outcome]


def merge_pattern(existing: list, incoming: ExamPattern) -> PatternMergeReport:
    """Fold an extracted pattern into a record's authored stages.

    `existing` is the record's `ExamStage[]` as plain dictionaries. Nothing is written
    here: the report says what would change, and publishing is a separate, deliberate step.
    """
    report = PatternMergeReport()
    stages = list(incoming.stages)
    used: set = set()

    for row in existing:
        name = row.get('stageName', '')
        # The record's own label for the stage, read from the name the way it is read from
        # a heading -- "Tier-II — Computer Based Examination" is Tier-II. Its `tier`
        # field is the frontend's own vocabulary ("TIER_1") and no authority prints that,
        # so it is only a fallback.
        from .pattern import _STAGE_LABELLED
        in_name = _STAGE_LABELLED.search(name or '')
        code = in_name.group(0) if in_name else (row.get('tier', '') or '')
        scored = sorted(((node_identity(name, code, node), node) for node in stages),
                        key=lambda t: -t[0])
        best, match = scored[0] if scored else (0.0, None)
        runner_up = scored[1][0] if len(scored) > 1 else 0.0

        if best < IDENTITY_THRESHOLD:
            report.decisions.append(StageDecision(
                MergeAction.UNCHANGED, name, row.get('id', ''), identity=best,
                reason='no extracted stage is established to be this one; the record is '
                       'left exactly as it is'))
            continue
        if runner_up >= IDENTITY_THRESHOLD:
            report.decisions.append(StageDecision(
                MergeAction.CONFLICTED, name, row.get('id', ''), identity=best,
                reason='more than one extracted stage matches this one equally well, so '
                       'nothing is merged rather than merging the wrong pair'))
            continue

        used.add(id(match))
        fields = [FieldDecision('stageName', FieldOutcome.KEPT, name, match.name,
                                'the record’s wording is kept; the document’s '
                                'is evidence that the stage exists')]
        for key, attribute in _NUMERIC_FIELDS:
            fields.append(_numeric_decision(key, row.get(key), getattr(match, attribute)))
        fields.append(_negative_decision(row.get('negativeMarking', ''),
                                         match.negative_marking))

        contested = [f for f in fields if f.outcome is FieldOutcome.UNDER_REVIEW]
        report.decisions.append(StageDecision(
            MergeAction.CONFIRMED if not contested else MergeAction.CONFLICTED,
            name, row.get('id', ''), fields=fields, identity=best,
            reason=('the document confirms this stage exists' if not contested else
                    f'{len(contested)} field(s) held for review: '
                    f'{", ".join(f.field for f in contested)}')))

    for node in stages:
        if id(node) in used:
            continue
        report.decisions.append(StageDecision(
            MergeAction.ADDED, node.name, node.id, identity=1.0,
            reason='the document sets out this stage and the record does not hold it'))
    return report
