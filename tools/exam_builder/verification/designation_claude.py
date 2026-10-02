"""Claude's part in designation identity -- locating, never deciding.

Two gateway operations:
  EXTRACT_DESIGNATION      given a notification's title block, point at the strings that name
                           the recruitment, its qualifiers, its cycle and the components the
                           notice declares, each with a verbatim evidence span.
  CONFIRM_RECRUITMENT      given a canonical designation and one document's title block, say
                           whether the document is about that recruitment, with a verbatim
                           evidence span.
Neither result is used as returned. designation.validate_extraction refuses any string that is
not printed in the notification, and the builder uses a confirmation only to *withhold* a
deterministic MATCH -- never to create one. Any transport failure is an infrastructure status,
never a verdict.
"""
from __future__ import annotations

from tools.claude_cli import Operation, get_gateway

from ..evidence import normalise_ws


def extract_designation(title_block: str, gateway=None):
    """(Claude's validated output or None, infra status value, safe detail). The output is still
    unverified: designation.validate_extraction decides what of it may be used."""
    gateway = gateway or get_gateway()
    result = gateway.run(Operation.EXTRACT_DESIGNATION, {'title_block': normalise_ws(title_block)})
    if not result.ok:
        return None, result.status.value, result.message
    return result.output, 'OK', ''


def confirm_same_recruitment(designation: str, cycle: str, components: list[str],
                             document_block: str, gateway=None):
    """(Claude's validated output or None, infra status value, safe detail)."""
    gateway = gateway or get_gateway()
    result = gateway.run(Operation.CONFIRM_RECRUITMENT, {
        'designation': normalise_ws(designation), 'cycle': cycle, 'components': list(components),
        'document_block': normalise_ws(document_block)})
    if not result.ok:
        return None, result.status.value, result.message
    return result.output, 'OK', ''


def validate_confirmation(raw, document_text: str) -> tuple[bool | None, str, str]:
    """(same_recruitment or None when unusable, evidence span, reason). A confirmation whose
    evidence is not printed in the document is unusable, whichever way it answers."""
    if not isinstance(raw, dict) or set(raw) - {'same_recruitment', 'evidence_span', 'reason'}:
        return None, '', 'confirmation was not the agreed JSON object'
    same = raw.get('same_recruitment')
    span = normalise_ws(raw.get('evidence_span') or '')
    if not isinstance(same, bool):
        return None, '', 'same_recruitment must be a boolean'
    if not span or span not in normalise_ws(document_text):
        return None, span, 'the confirmation\'s evidence is not printed in the document'
    reason = raw.get('reason') if isinstance(raw.get('reason'), str) else ''
    return same, span, normalise_ws(reason)[:300]
