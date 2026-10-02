"""Claude's part in fact attribution -- classifying a span's role, never deciding.

After a reading passes the deterministic attribution checks (attribution.py), and only when Claude
is enabled, the gateway's CLASSIFY_ATTRIBUTION / CLASSIFY_DATE operations are shown the field, the
value and the evidence with its immediate context, and asked what the evidence *does*: states the
recruitment's total vacancies, or a category's count, or a row's serial number; requires a
qualification, or relaxes an age limit; grants a fee exemption, or sets a certificate rule; and so on.

Its answer is used only to WITHHOLD:

    publish  ==  deterministic checks passed
                 AND Claude's role is the role the field needs
                 AND it says the evidence supports the value
                 AND its evidence span is printed in the document
                 AND it reports no conflict

Anything else -- another role, no support, an unprinted span, a conflict, a malformed or
schema-rejected reply, an unreachable Claude -- holds the field for review. Claude never supplies a
value.
"""
from __future__ import annotations

import json

from tools.claude_cli import Operation, get_gateway
from tools.claude_cli.schemas import DATE_ROLES as _DATE_ROLES

from ..evidence import normalise_ws

#: The role each field needs, and the other roles the same kind of evidence commonly plays.
ROLES = {
    'vacancies': ('total_vacancies', ('category_count', 'post_count', 'row_serial', 'other_number')),
    'qualification': ('qualification_requirement',
                      ('age_relaxation', 'disqualification', 'exemption', 'other')),
    'fee': ('fee_rule', ('certificate_rule', 'refund_rule', 'pay_scale', 'other')),
    'feeExemptions': ('fee_exemption', ('certificate_rule', 'refund_rule', 'other')),
    'posts': ('post_names', ('category_labels', 'table_residue', 'documents', 'other')),
    'examPattern': ('paper_scheme', ('shared_or_partial_marks', 'incidental_mention', 'other')),
}

KEYS = ('role', 'supports_value', 'scope', 'evidence_span', 'confidence', 'conflicts')


def classify(field_name: str, value, evidence: str, context: str, gateway=None):
    """(Claude's validated output or None, infra status value, safe detail). The output has the
    operation's schema's shape; `validate` still decides what it is allowed to do."""
    gateway = gateway or get_gateway()
    need, others = ROLES[field_name]
    result = gateway.run(Operation.CLASSIFY_ATTRIBUTION, {
        'field': field_name, 'value_json': json.dumps(value, ensure_ascii=False),
        'roles': [need, *others], 'evidence': normalise_ws(evidence),
        'context': normalise_ws(context)})
    if not result.ok:
        return None, result.status.value, result.message
    return result.output, 'OK', ''


def validate(field_name: str, raw, source_text: str) -> tuple[bool, str]:
    """(publishable, reason). Only a reply that meets every condition lets the fact stand."""
    need, others = ROLES[field_name]
    if not isinstance(raw, dict) or set(raw) != set(KEYS):
        return False, 'Claude\'s reply was not the agreed JSON object'
    if raw['role'] not in (need,) + others:
        return False, f'Claude named a role outside the list ({raw["role"]!r})'
    if not isinstance(raw['supports_value'], bool) or not isinstance(raw['conflicts'], list):
        return False, 'supports_value must be a boolean and conflicts a list'
    span = normalise_ws(raw.get('evidence_span') or '')
    if not span or span not in normalise_ws(source_text):
        return False, 'Claude\'s evidence is not printed in the document'
    if raw['role'] != need:
        return False, f'Claude reads the evidence as {raw["role"]}, not {need} ({span[:120]!r})'
    if not raw['supports_value']:
        return False, f'Claude finds the evidence does not state this value ({span[:120]!r})'
    conflicts = [normalise_ws(c) for c in raw['conflicts'] if isinstance(c, str) and normalise_ws(c)]
    if conflicts:
        return False, 'Claude reports a conflict: ' + '; '.join(conflicts)[:200]
    return True, f'Claude confirms the role {need} ({span[:120]!r})'


# ==================================================================================== dates
#: The milestone reader's own event kinds (dates.EVENT_CUES), so Claude and the reader share one
#: vocabulary, plus the two non-events a date can be.
DATE_ROLES = tuple(_DATE_ROLES)
DATE_KEYS = ('role', 'supports_date', 'evidence_span', 'is_reference', 'confidence', 'conflicts')

def classify_date(item: dict, context: str, gateway=None):
    """(Claude's validated output or None, infra status value, safe detail)."""
    gateway = gateway or get_gateway()
    label = item.get('rawLabel') or item.get('label') or ''
    stated = item.get('rawValue') or (item.get('provenance') or {}).get('excerptText') or ''
    result = gateway.run(Operation.CLASSIFY_DATE, {
        'date': (item.get('dateTimeStr') or '')[:10], 'label': normalise_ws(label),
        'stated': normalise_ws(stated), 'roles': list(DATE_ROLES), 'context': normalise_ws(context)})
    if not result.ok:
        return None, result.status.value, result.message
    return result.output, 'OK', ''


def validate_date(item: dict, raw, source_text: str, need_role) -> tuple[bool, str]:
    """(stands, reason). `need_role` is a callable role -> bool (the role the evidence already
    established), or None when Claude is being asked to supply a missing role."""
    from ..dates import read_dates
    if not isinstance(raw, dict) or set(raw) != set(DATE_KEYS):
        return False, 'Claude\'s reply was not the agreed JSON object'
    if raw['role'] not in DATE_ROLES:
        return False, f'Claude named a role outside the list ({raw["role"]!r})'
    if not all(isinstance(raw[k], bool) for k in ('supports_date', 'is_reference')) \
            or not isinstance(raw['conflicts'], list):
        return False, 'supports_date/is_reference must be booleans and conflicts a list'
    span = normalise_ws(raw.get('evidence_span') or '')
    if not span or span not in normalise_ws(source_text):
        return False, 'Claude\'s evidence is not printed in the document'
    iso = (item.get('dateTimeStr') or '')[:10]
    if not any(d.iso == iso or (d.iso[:7] == iso[:7] and d.precision.value != 'DAY')
               for d in read_dates(span)):
        return False, f'Claude\'s evidence does not contain the date {iso}'
    if raw['role'] == 'NOT_A_DATE':
        return False, f'Claude reads the text as not a date ({span[:100]!r})'
    if raw['is_reference'] or raw['role'] == 'REFERENCE':
        # A notice's own dateline is "dated" by nature: cited and the notification's date at once.
        if not (need_role is not None and need_role('REFERENCE')):
            return False, f'Claude reads the date as cited, not scheduled ({span[:100]!r})'
        return True, f'Claude reads the notice\'s own dateline ({span[:100]!r})'
    if not raw['supports_date']:
        return False, f'Claude finds the evidence does not state this date for the event'
    conflicts = [normalise_ws(c) for c in raw['conflicts'] if isinstance(c, str) and normalise_ws(c)]
    if conflicts:
        return False, 'Claude reports a conflict: ' + '; '.join(conflicts)[:160]
    if need_role is not None and not need_role(raw['role']):
        return False, f'Claude reads the date as {raw["role"]}, not the event it was published as'
    return True, f'Claude confirms the date as {raw["role"]} ({span[:100]!r})'
