"""Claude's part in semantic completeness -- judging whether a quoted unit is whole.

A candidate-facing quotation (a qualification, an application step, an exam-day rule, an FAQ
clause, a syllabus entry) must be the whole unit the document printed. The deterministic check
(units.check_value) catches a value that stops inside a word or inside a sentence the document
continues. After that check passes, and only when Claude is enabled, the gateway's CHECK_COMPLETENESS
operation is shown the unit and the text around it and asked one question: does the quotation begin
and end where the document's own unit does?

Its answer is used only to WITHHOLD:

    publish  ==  the deterministic check found the unit whole (or could not check it)
                 AND Claude says it is complete
                 AND it says the document does not continue the unit past its end
                 AND its confidence is not low

Anything else -- incomplete, continued, low confidence, a malformed or schema-rejected reply, an
unreachable Claude -- holds the field for review. Claude is never asked for text and none of its
words are used as a value: the reply is a verdict, and the quotation stays the reader's verbatim span.
"""
from __future__ import annotations

from tools.claude_cli import Operation, get_gateway

from ..evidence import normalise_ws

#: What a unit of each field is, in the terms Claude is asked to judge.
UNIT_KIND = {
    'qualification': 'a complete qualification requirement (one whole sentence or clause)',
    'howToApply': 'a complete application step (one whole numbered or titled step)',
    'examDayChecklist': 'a complete exam-day rule (one whole sentence or clause)',
    'faqs': 'a complete official clause (one whole numbered clause)',
    'syllabus': 'a complete syllabus entry (one whole numbered or listed entry, as printed)',
}

KEYS = ('complete', 'continues_after', 'starts_mid_unit', 'confidence', 'reason')


def classify(field_name: str, quotation: str, context: str, gateway=None):
    """(Claude's validated output or None, infra status value, safe detail)."""
    gateway = gateway or get_gateway()
    result = gateway.run(Operation.CHECK_COMPLETENESS, {
        'unit_kind': UNIT_KIND.get(field_name, 'a complete quoted unit'),
        'quotation': normalise_ws(quotation), 'context': normalise_ws(context)})
    if not result.ok:
        return None, result.status.value, result.message
    return result.output, 'OK', ''


def validate(raw) -> tuple[bool, str]:
    """(publishable, reason). Only a reply meeting every condition lets the unit stand."""
    if not isinstance(raw, dict) or set(raw) != set(KEYS):
        return False, 'Claude\'s reply was not the agreed JSON object'
    flags = ('complete', 'continues_after', 'starts_mid_unit')
    if not all(isinstance(raw[k], bool) for k in flags):
        return False, 'complete, continues_after and starts_mid_unit must be booleans'
    if raw['confidence'] not in ('high', 'medium', 'low'):
        return False, f'unknown confidence {raw["confidence"]!r}'
    why = normalise_ws(str(raw.get('reason') or ''))[:160]
    if not raw['complete']:
        return False, f'Claude reads the quotation as incomplete ({why})'
    if raw['continues_after']:
        return False, f'Claude sees the unit continue after the quotation ({why})'
    if raw['starts_mid_unit']:
        return False, f'Claude sees the quotation begin inside a sentence ({why})'
    if raw['confidence'] == 'low':
        return False, 'Claude is not confident the quotation is whole'
    return True, 'Claude confirms the quotation is a whole unit'
