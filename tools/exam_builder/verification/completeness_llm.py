"""The local model's part in semantic completeness -- judging whether a quoted unit is whole.

A candidate-facing quotation (a qualification, an application step, an exam-day rule, an FAQ
clause) must be the whole unit the document printed. The deterministic check (units.check_value)
catches a value that stops inside a word or inside a sentence the document continues. After that
check passes, and only when a model is enabled, the model is shown the unit and the text around it
and asked one question: does the quotation begin and end where the document's own unit does?

Its answer is used only to WITHHOLD:

    publish  ==  the deterministic check found the unit whole (or could not check it)
                 AND the model says it is complete
                 AND it says the document does not continue the unit past its end
                 AND its confidence is not low

Anything else -- incomplete, continued, low confidence, a malformed reply, an unreachable model --
holds the field for review. The model is never asked for text and none of its words are used as
a value: the reply is a verdict, and the quotation stays the reader's verbatim span.
"""
from __future__ import annotations

import json

from ..evidence import normalise_ws
from .client import ProviderError, VerificationProvider, get_provider
from .llm_verifier import _extract_json

#: What a unit of each field is, in the terms the model is asked to judge.
UNIT_KIND = {
    'qualification': 'a complete qualification requirement (one whole sentence or clause)',
    'howToApply': 'a complete application step (one whole numbered or titled step)',
    'examDayChecklist': 'a complete exam-day rule (one whole sentence or clause)',
    'faqs': 'a complete official clause (one whole numbered clause)',
}

KEYS = ('complete', 'continues_after', 'starts_mid_unit', 'confidence', 'reason')

_SYSTEM = (
    "You check whether a QUOTATION taken from an official recruitment notice is a whole unit of "
    "that notice. Rules:\n"
    "- Use ONLY the supplied text. Do not use outside or prior knowledge.\n"
    "- Never write, complete, correct or paraphrase any part of the quotation.\n"
    "- complete: true only if the quotation contains the whole unit described, from its first "
    "word to its last.\n"
    "- continues_after: true if the CONTEXT shows the same sentence or clause continuing after "
    "the quotation's last word.\n"
    "- starts_mid_unit: true if the CONTEXT shows the quotation beginning inside a sentence.\n"
    "- reason: a few words; do not quote the missing text.\n"
    "Reply with ONE JSON object of exactly this shape and nothing else:\n"
    '{"complete":true|false,"continues_after":true|false,"starts_mid_unit":true|false,'
    '"confidence":"high|medium|low","reason":""}'
)


def classify(field_name: str, quotation: str, context: str,
             provider: VerificationProvider | None = None):
    """(raw model output, infra status value, detail). Unvalidated."""
    provider = provider or get_provider()
    user = (f'UNIT: {UNIT_KIND.get(field_name, "a complete quoted unit")}\n'
            f'QUOTATION: """{normalise_ws(quotation)}"""\n'
            f'CONTEXT AROUND IT: """{normalise_ws(context)}"""\n'
            'Judge the quotation as instructed. /no_think')
    try:
        raw = provider.complete([{'role': 'system', 'content': _SYSTEM},
                                 {'role': 'user', 'content': user}], max_tokens=200)
    except ProviderError as e:
        return None, e.infra.value, e.detail
    except Exception as e:                                       # noqa: BLE001
        return None, 'LLM_ERROR', f'{type(e).__name__}: {e}'
    text = _extract_json(raw)
    try:
        return json.loads(text), 'OK', ''
    except (ValueError, TypeError):
        return text, 'OK', 'model output was not valid JSON'


def validate(raw) -> tuple[bool, str]:
    """(publishable, reason). Only a reply meeting every condition lets the unit stand."""
    if not isinstance(raw, dict) or set(raw) != set(KEYS):
        return False, 'the model\'s reply was not the agreed JSON object'
    flags = ('complete', 'continues_after', 'starts_mid_unit')
    if not all(isinstance(raw[k], bool) for k in flags):
        return False, 'complete, continues_after and starts_mid_unit must be booleans'
    if raw['confidence'] not in ('high', 'medium', 'low'):
        return False, f'unknown confidence {raw["confidence"]!r}'
    why = normalise_ws(str(raw.get('reason') or ''))[:160]
    if not raw['complete']:
        return False, f'the model reads the quotation as incomplete ({why})'
    if raw['continues_after']:
        return False, f'the model sees the unit continue after the quotation ({why})'
    if raw['starts_mid_unit']:
        return False, f'the model sees the quotation begin inside a sentence ({why})'
    if raw['confidence'] == 'low':
        return False, 'the model is not confident the quotation is whole'
    return True, 'the model confirms the quotation is a whole unit'
