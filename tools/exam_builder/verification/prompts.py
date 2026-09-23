"""Evidence-first prompting. The model is asked to *verify* supplied evidence against a
supplied claim, never to find or recall anything. Universal: every value comes from the
claim, and no authority or exam type is named in the template."""
from __future__ import annotations

from .schemas import Claim

_SYSTEM = (
    "You are a strict verification assistant for a government-exam data platform. "
    "You judge ONLY whether the supplied EVIDENCE supports the supplied CLAIM. "
    "Rules you must obey:\n"
    "- Use only the supplied evidence. Do not use any outside or prior knowledge.\n"
    "- Do not add, infer, correct, or complete any fact.\n"
    "- If the evidence does not explicitly support the claim, answer INSUFFICIENT.\n"
    "- If the evidence explicitly contradicts the claim, answer CONTRADICTED.\n"
    "- Only answer SUPPORTED when the evidence explicitly states the claim.\n"
    "- You never decide what is official, and you never choose between exams or cycles.\n"
    "Reply with ONE JSON object and nothing else, of exactly this shape:\n"
    '{"decision":"SUPPORTED|CONTRADICTED|INSUFFICIENT",'
    '"identity_supported":true|false,"evidence_supported":true|false,'
    '"claim_supported":true|false,"reason":"<one short sentence>"}'
)


def build_messages(claim: Claim) -> list:
    """The chat messages for one verification. `/no_think` keeps Qwen3 out of its long
    chain-of-thought so the reply is the JSON object we validate."""
    exam = claim.official_name or claim.exam_id
    lines = [
        'CLAIM:',
        f'- exam: {exam}' + (f' (cycle {claim.cycle})' if claim.cycle else ''),
        f'- field: {claim.field}',
        f'- value: {claim.value}' if claim.value else '- value: (none; this is a structural claim)',
        '',
        'SOURCE:',
        f'- title: {claim.source_title or "(untitled)"}',
        f'- url: {claim.source_url or "(none)"}',
        f'- authority: {claim.authority or "(unstated)"}',
        '',
        'EVIDENCE (use only this text):',
        f'"""{claim.evidence_span.strip()}"""',
        '',
        'TASK: Determine whether the EVIDENCE supports the CLAIM.',
        '- identity_supported: does the evidence concern this exam and cycle?',
        '- evidence_supported: does the evidence explicitly state the value/claim?',
        '- claim_supported: is the overall claim supported by this evidence alone?',
        'Answer with the single JSON object described in the system message. /no_think',
    ]
    return [{'role': 'system', 'content': _SYSTEM},
            {'role': 'user', 'content': '\n'.join(lines)}]
