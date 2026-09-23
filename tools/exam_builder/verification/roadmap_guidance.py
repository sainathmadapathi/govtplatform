"""GovOS study-roadmap *guidance* — a learning sequence over the verified syllabus.

This is the one place the local model touches the roadmap, and it is fenced hard:

  * it is **GOVOS_GUIDANCE**, never an official recommendation, and every result says so;
  * it consumes only **verified** syllabus topics passed in by the caller -- it never fetches,
    recalls, or invents a topic, a mark, a date, or a rule;
  * the model may only **reorder the supplied topics** and attach a short sequencing rationale.
    The output is validated against the input's own topic ids; any topic the model did not
    receive is a rejection, and the deterministic order is used instead;
  * if the model is disabled, unreachable, or malformed, the guidance falls back to a
    deterministic order and is still returned -- a roadmap must not become a fake official fact,
    and it must not vanish either.

It writes nothing to any exam record. It is universal: the structure is whatever the exam's own
syllabus is, and no authority or exam type is named.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Optional

from .client import VerificationProvider, get_provider
from .schemas import InfraStatus

GUIDANCE_LABEL = 'GOVOS_GUIDANCE'


@dataclass
class RoadmapStep:
    topic_id: str
    topic_name: str
    subject: str
    rationale: str = ''


@dataclass
class RoadmapGuidance:
    exam_id: str
    #: Always GOVOS_GUIDANCE. This is not an official fact and never becomes one.
    source: str = GUIDANCE_LABEL
    #: 'qwen' when the model produced a validated order, else 'deterministic'.
    generated_by: str = 'deterministic'
    steps: list = field(default_factory=list)
    disclaimer: str = ''
    #: Set when no guidance could be built (e.g. the exam has no verified syllabus).
    unavailable_reason: str = ''
    #: Recorded when the model was tried; never turns the guidance into an official fact.
    infra: str = InfraStatus.OK.value

    @property
    def available(self) -> bool:
        return bool(self.steps) and not self.unavailable_reason

    def as_dict(self) -> dict:
        return {'examId': self.exam_id, 'source': self.source,
                'generatedBy': self.generated_by, 'disclaimer': self.disclaimer,
                'unavailableReason': self.unavailable_reason, 'infra': self.infra,
                'steps': [{'topicId': s.topic_id, 'topicName': s.topic_name,
                           'subject': s.subject, 'rationale': s.rationale} for s in self.steps]}


def _norm_topics(topics: list) -> list:
    """Accept verified topics as dicts and keep only the fields sequencing needs."""
    out = []
    for t in topics or []:
        tid = str(t.get('id') or t.get('topicId') or '').strip()
        name = str(t.get('topicName') or t.get('name') or '').strip()
        if not tid or not name:
            continue
        out.append({'id': tid, 'name': name,
                    'subject': str(t.get('subject') or ''),
                    'weightage': float(t.get('weightagePercentage') or 0),
                    'high_yield': bool(t.get('isHighYield'))})
    return out


def deterministic_sequence(topics: list) -> list:
    """A sensible default order from verified data alone: high-yield first, then by weightage,
    grouped so a subject's topics stay together. No model, no invention."""
    norm = _norm_topics(topics)
    subjects = []
    for t in norm:
        if t['subject'] not in subjects:
            subjects.append(t['subject'])
    subj_rank = {s: i for i, s in enumerate(subjects)}
    ordered = sorted(norm, key=lambda t: (not t['high_yield'], subj_rank.get(t['subject'], 99),
                                          -t['weightage'], t['name']))
    return [RoadmapStep(topic_id=t['id'], topic_name=t['name'], subject=t['subject'],
                        rationale='High-yield; scheduled early.' if t['high_yield']
                        else 'Scheduled by weightage within its subject.') for t in ordered]


def _disclaimer(authority: str) -> str:
    who = authority.split(' (')[0] if authority else 'the authority'
    return (f'GovOS study guidance — a suggested learning order over the official syllabus. '
            f'It is not an official recommendation of {who}.')


_JSON = re.compile(r'\{.*\}', re.S)
_THINK = re.compile(r'<think>.*?</think>', re.S | re.I)


def _build_messages(exam_label: str, norm: list) -> list:
    lines = ['Topics (id | subject | name | high_yield):']
    for t in norm:
        lines.append(f"{t['id']} | {t['subject']} | {t['name']} | {'yes' if t['high_yield'] else 'no'}")
    system = (
        "You arrange an already-fixed list of study topics into a sensible learning order. "
        "Hard rules:\n"
        "- Use ONLY the topics given, by their id. Do not add, rename, split, or invent any "
        "topic.\n"
        "- Do not state any facts, numbers, marks, dates, weightages, or rules. Give only a "
        "short ordering reason (why this topic comes where it does).\n"
        "- This is study guidance, not an official recommendation.\n"
        'Reply with ONE JSON object: {"order":[{"id":"<id>","why":"<short reason>"}, ...]} '
        "listing every id exactly once, and nothing else."
    )
    user = (f'Exam syllabus to sequence ({exam_label}). Arrange every topic into a learning '
            f'order.\n\n' + '\n'.join(lines) + '\n\nReturn the JSON order now. /no_think')
    return [{'role': 'system', 'content': system}, {'role': 'user', 'content': user}]


def _parse_order(raw: str, norm: list) -> Optional[list]:
    """Validate the model's order against the input ids. Returns reordered steps, or None if
    the model invented an id, dropped topics, or produced anything malformed."""
    text = _THINK.sub('', raw or '').strip()
    m = _JSON.search(text)
    if not m:
        return None
    try:
        data = json.loads(m.group(0))
    except (ValueError, TypeError):
        return None
    order = data.get('order')
    if not isinstance(order, list) or not order:
        return None
    by_id = {t['id']: t for t in norm}
    seen, steps = set(), []
    for item in order:
        if not isinstance(item, dict):
            return None
        tid = str(item.get('id') or '').strip()
        if tid not in by_id or tid in seen:      # invented, or duplicated -> reject wholesale
            return None
        seen.add(tid)
        t = by_id[tid]
        why = item.get('why')
        steps.append(RoadmapStep(topic_id=tid, topic_name=t['name'], subject=t['subject'],
                                 rationale=(why if isinstance(why, str) else '')[:200]))
    # Every supplied topic must be placed exactly once; a partial order is a rejection.
    if seen != set(by_id):
        return None
    return steps


def generate(exam_id: str, topics: list, *, authority: str = '', exam_label: str = '',
             provider: VerificationProvider | None = None) -> RoadmapGuidance:
    """Build study guidance for one exam from its verified syllabus topics.

    A deterministic order is always available; the model, when reachable, may replace it with a
    validated reordering. The result is always GOVOS_GUIDANCE.
    """
    norm = _norm_topics(topics)
    disclaimer = _disclaimer(authority)
    if not norm:
        # No verified syllabus -> no guidance is fabricated; the reason is explicit.
        return RoadmapGuidance(exam_id=exam_id, generated_by='deterministic', steps=[],
                               disclaimer=disclaimer,
                               unavailable_reason='NOT_EXTRACTED: no verified syllabus topics '
                                                  'for this exam to sequence')
    baseline = deterministic_sequence(topics)
    provider = provider or get_provider()
    if not provider.is_enabled():
        return RoadmapGuidance(exam_id=exam_id, generated_by='deterministic', steps=baseline,
                               disclaimer=disclaimer, infra=InfraStatus.LLM_DISABLED.value)
    try:
        raw = provider.complete(_build_messages(exam_label or exam_id, norm), max_tokens=900)
    except Exception as e:                                       # noqa: BLE001
        infra = getattr(e, 'infra', InfraStatus.LLM_ERROR)
        return RoadmapGuidance(exam_id=exam_id, generated_by='deterministic', steps=baseline,
                               disclaimer=disclaimer,
                               infra=(infra.value if hasattr(infra, 'value') else str(infra)))
    steps = _parse_order(raw, norm)
    if steps is None:
        # Malformed, or the model tried to invent/drop a topic -> deterministic order stands.
        return RoadmapGuidance(exam_id=exam_id, generated_by='deterministic', steps=baseline,
                               disclaimer=disclaimer,
                               infra=InfraStatus.LLM_INVALID_RESPONSE.value)
    return RoadmapGuidance(exam_id=exam_id, generated_by='qwen', steps=steps,
                           disclaimer=disclaimer)
