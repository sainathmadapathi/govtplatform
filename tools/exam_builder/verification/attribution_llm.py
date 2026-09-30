"""The local model's part in fact attribution -- classifying a span's role, never deciding.

After a reading passes the deterministic attribution checks (attribution.py), and only when a
model is enabled, the model is shown the field, the value and the evidence with its immediate
context, and asked what the evidence *does*: states the recruitment's total vacancies, or a
category's count, or a row's serial number; requires a qualification, or relaxes an age
limit; grants a fee exemption, or sets a certificate rule; and so on.

Its answer is used only to WITHHOLD:

    publish  ==  deterministic checks passed
                 AND the model's role is the role the field needs
                 AND it says the evidence supports the value
                 AND its evidence span is printed in the document
                 AND it reports no conflict

Anything else -- another role, no support, an unprinted span, a conflict, a malformed reply, an
unreachable model -- holds the field for review. The model never supplies a value.
"""
from __future__ import annotations

import json

from ..evidence import normalise_ws
from .client import ProviderError, VerificationProvider, get_provider
from .llm_verifier import _extract_json

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

_SYSTEM = (
    "You classify what one passage of an official recruitment notice does. Rules:\n"
    "- Use ONLY the supplied text. Do not use outside or prior knowledge.\n"
    "- Do not add, infer, correct or complete any value.\n"
    "- role: exactly one of the listed roles, describing what the EVIDENCE states.\n"
    "- supports_value: true only if the evidence explicitly states the given value in that role.\n"
    "- scope: whom or what the evidence applies to, in its own words (post, stream, category, "
    "stage, paper), or \"\".\n"
    "- evidence_span: the exact words, copied verbatim, that decide the role.\n"
    "- conflicts: anything in the text that makes the role or scope unclear or contradicts the "
    "value; [] if none.\n"
    "Reply with ONE JSON object of exactly this shape and nothing else:\n"
    '{"role":"<role>","supports_value":true|false,"scope":"","evidence_span":"<verbatim>",'
    '"confidence":"high|medium|low","conflicts":[]}'
)


def classify(field_name: str, value, evidence: str, context: str,
             provider: VerificationProvider | None = None):
    """(raw model output, infra status value, detail). Unvalidated."""
    provider = provider or get_provider()
    need, others = ROLES[field_name]
    user = (f'FIELD: {field_name}\n'
            f'VALUE: {json.dumps(value, ensure_ascii=False)[:600]}\n'
            f'ROLES: {", ".join((need,) + others)}\n'
            f'EVIDENCE: """{normalise_ws(evidence)[:900]}"""\n'
            f'CONTEXT AROUND IT: """{normalise_ws(context)[:1500]}"""\n'
            'Classify the evidence as instructed. /no_think')
    try:
        raw = provider.complete([{'role': 'system', 'content': _SYSTEM},
                                 {'role': 'user', 'content': user}], max_tokens=400)
    except ProviderError as e:
        return None, e.infra.value, e.detail
    except Exception as e:                                       # noqa: BLE001
        return None, 'LLM_ERROR', f'{type(e).__name__}: {e}'
    text = _extract_json(raw)
    try:
        return json.loads(text), 'OK', ''
    except (ValueError, TypeError):
        return text, 'OK', 'model output was not valid JSON'


def validate(field_name: str, raw, source_text: str) -> tuple[bool, str]:
    """(publishable, reason). Only a reply that meets every condition lets the fact stand."""
    need, others = ROLES[field_name]
    if not isinstance(raw, dict) or set(raw) != set(KEYS):
        return False, 'the model\'s reply was not the agreed JSON object'
    if raw['role'] not in (need,) + others:
        return False, f'the model named a role outside the list ({raw["role"]!r})'
    if not isinstance(raw['supports_value'], bool) or not isinstance(raw['conflicts'], list):
        return False, 'supports_value must be a boolean and conflicts a list'
    span = normalise_ws(raw.get('evidence_span') or '')
    if not span or span not in normalise_ws(source_text):
        return False, 'the model\'s evidence is not printed in the document'
    if raw['role'] != need:
        return False, f'the model reads the evidence as {raw["role"]}, not {need} ({span[:120]!r})'
    if not raw['supports_value']:
        return False, f'the model finds the evidence does not state this value ({span[:120]!r})'
    conflicts = [normalise_ws(c) for c in raw['conflicts'] if isinstance(c, str) and normalise_ws(c)]
    if conflicts:
        return False, 'the model reports a conflict: ' + '; '.join(conflicts)[:200]
    return True, f'the model confirms the role {need} ({span[:120]!r})'


# ==================================================================================== dates
#: The milestone reader's own event kinds (dates.EVENT_CUES), so model and reader share one
#: vocabulary, plus the two non-events a date can be.
DATE_ROLES = ('NOTIFICATION', 'APPLICATION_START', 'APPLICATION_CLOSE', 'FEE_PAYMENT_END',
              'CORRECTION_WINDOW', 'EXAM', 'SKILL_TEST', 'PHYSICAL_TEST', 'ADMIT_CARD',
              'CITY_INTIMATION', 'ANSWER_KEY', 'RESULT', 'OPTION_ENTRY', 'DOCUMENT_VERIFICATION',
              'INTERVIEW', 'OTHER_EVENT', 'REFERENCE', 'NOT_A_DATE')
DATE_KEYS = ('role', 'supports_date', 'evidence_span', 'is_reference', 'confidence', 'conflicts')

_DATE_SYSTEM = (
    "You classify one date printed in an official recruitment notice. Rules:\n"
    "- Use ONLY the supplied text. Do not use outside or prior knowledge.\n"
    "- Never write, correct or normalise a date; judge only the date given.\n"
    "- role: exactly one of the listed roles -- the event THIS date is scheduled for in THIS "
    "recruitment. FEE_PAYMENT_END is a fee-payment deadline; CORRECTION_WINDOW is an "
    "application edit/correction window; PHYSICAL_TEST includes a medical board and physical "
    "tests; OPTION_ENTRY is web options or post/zone preferences; DOCUMENT_VERIFICATION is "
    "certificate or document verification. NOTIFICATION is the notice's own date. REFERENCE "
    "means the date is cited, not scheduled (another document's date, an age reference date, "
    "a historical or rule date). NOT_A_DATE means the text is not a date. Use only a listed "
    "role, spelled exactly.\n"
    "- supports_date: true only if the evidence explicitly states this date for that event.\n"
    "- evidence_span: the exact words, copied verbatim, that contain the date and name its event.\n"
    "- is_reference: true if the date is cited rather than scheduled.\n"
    "- conflicts: anything that makes the event or the date unclear, or another date stated for "
    "the same event; [] if none.\n"
    "Reply with ONE JSON object of exactly this shape and nothing else:\n"
    '{"role":"<role>","supports_date":true|false,"evidence_span":"<verbatim>",'
    '"is_reference":true|false,"confidence":"high|medium|low","conflicts":[]}'
)


def classify_date(item: dict, context: str, provider: VerificationProvider | None = None):
    """(raw model output, infra status value, detail). Unvalidated."""
    provider = provider or get_provider()
    label = item.get('rawLabel') or item.get('label') or ''
    stated = item.get('rawValue') or (item.get('provenance') or {}).get('excerptText') or ''
    user = (f'DATE: {(item.get("dateTimeStr") or "")[:10]} (as read)\n'
            f'ROW LABEL / STATEMENT: {normalise_ws(label)[:200]}\n'
            f'STATED AS: """{normalise_ws(stated)[:600]}"""\n'
            f'ROLES: {", ".join(DATE_ROLES)}\n'
            f'CONTEXT AROUND IT: """{normalise_ws(context)[:1500]}"""\n'
            'Classify the date as instructed. /no_think')
    try:
        raw = provider.complete([{'role': 'system', 'content': _DATE_SYSTEM},
                                 {'role': 'user', 'content': user}], max_tokens=350)
    except ProviderError as e:
        return None, e.infra.value, e.detail
    except Exception as e:                                       # noqa: BLE001
        return None, 'LLM_ERROR', f'{type(e).__name__}: {e}'
    text = _extract_json(raw)
    try:
        return json.loads(text), 'OK', ''
    except (ValueError, TypeError):
        return text, 'OK', 'model output was not valid JSON'


def validate_date(item: dict, raw, source_text: str, need_role) -> tuple[bool, str]:
    """(stands, reason). `need_role` is a callable role -> bool (the role the evidence already
    established), or None when the model is being asked to supply a missing role."""
    from ..dates import read_dates
    if not isinstance(raw, dict) or set(raw) != set(DATE_KEYS):
        return False, 'the model\'s reply was not the agreed JSON object'
    if raw['role'] not in DATE_ROLES:
        return False, f'the model named a role outside the list ({raw["role"]!r})'
    if not all(isinstance(raw[k], bool) for k in ('supports_date', 'is_reference')) \
            or not isinstance(raw['conflicts'], list):
        return False, 'supports_date/is_reference must be booleans and conflicts a list'
    span = normalise_ws(raw.get('evidence_span') or '')
    if not span or span not in normalise_ws(source_text):
        return False, 'the model\'s evidence is not printed in the document'
    iso = (item.get('dateTimeStr') or '')[:10]
    if not any(d.iso == iso or (d.iso[:7] == iso[:7] and d.precision.value != 'DAY')
               for d in read_dates(span)):
        return False, f'the model\'s evidence does not contain the date {iso}'
    if raw['role'] == 'NOT_A_DATE':
        return False, f'the model reads the text as not a date ({span[:100]!r})'
    if raw['is_reference'] or raw['role'] == 'REFERENCE':
        # A notice's own dateline is "dated" by nature: cited and the notification's date at once.
        if not (need_role is not None and need_role('REFERENCE')):
            return False, f'the model reads the date as cited, not scheduled ({span[:100]!r})'
        return True, f'the model reads the notice\'s own dateline ({span[:100]!r})'
    if not raw['supports_date']:
        return False, f'the model finds the evidence does not state this date for the event'
    conflicts = [normalise_ws(c) for c in raw['conflicts'] if isinstance(c, str) and normalise_ws(c)]
    if conflicts:
        return False, 'the model reports a conflict: ' + '; '.join(conflicts)[:160]
    if need_role is not None and not need_role(raw['role']):
        return False, f'the model reads the date as {raw["role"]}, not the event it was published as'
    return True, f'the model confirms the date as {raw["role"]} ({span[:100]!r})'
