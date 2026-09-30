"""The local model's part in designation identity -- locating, never deciding.

Two calls, both on the existing provider (client.py) and its safe-failure contract:

  extract_designation      given a notification's title block, point at the strings that name
                           the recruitment, its qualifiers, its cycle and the components the
                           notice declares, each with a verbatim evidence span.
  confirm_same_recruitment given a canonical designation and one document's title block, say
                           whether the document is about that recruitment, with a verbatim
                           evidence span.

Neither result is used as returned. designation.validate_extraction refuses any string that is
not printed in the notification, and the builder uses a confirmation only to *withhold* a
deterministic MATCH -- never to create one. Any transport failure is an infrastructure status,
never a verdict.
"""
from __future__ import annotations

import json

from ..evidence import normalise_ws
from .client import ProviderError, VerificationProvider, get_provider
from .llm_verifier import _extract_json

_EXTRACT_SYSTEM = (
    "You read the opening of an official recruitment notification and report what the "
    "notification itself says it recruits for.\n"
    "Rules you must obey:\n"
    "- Use ONLY the supplied text. Do not use outside or prior knowledge.\n"
    "- Copy every string EXACTLY as printed: same words, same order, same brackets. Never add, "
    "expand, translate, abbreviate or correct anything.\n"
    "- designation_core: the printed name of the post(s) recruited for, as printed.\n"
    "- qualifiers: each bracketed qualifier printed immediately with that designation.\n"
    "- cycle: the year / panel year / cycle printed with the designation, or \"\".\n"
    "- declared_components: each cadre, stream or post the notification itself lists as part of "
    "THIS recruitment, copied as printed TOGETHER WITH the designation (a component line names "
    "the designation and then the cadre/stream/post). Reservation categories (such as "
    "unreserved, backward-class, scheduled-caste/tribe, economically-weaker-section or disability "
    "columns), totals, and table headings are NOT components. [] if none are printed.\n"
    "- evidence_spans: the verbatim passages that contain every string above.\n"
    "- ambiguities: anything that makes it unclear which single recruitment this is; [] if none.\n"
    "- If something is not printed, leave it empty. Do not guess.\n"
    "Reply with ONE JSON object of exactly this shape and nothing else:\n"
    '{"designation_core":[],"qualifiers":[],"cycle":"","declared_components":[],'
    '"evidence_spans":[],"confidence":"high|medium|low","ambiguities":[]}'
)

_CONFIRM_SYSTEM = (
    "You compare one official document against one recruitment designation.\n"
    "Rules you must obey:\n"
    "- Use ONLY the supplied text. Do not use outside or prior knowledge.\n"
    "- same_recruitment is true only if the document's own words say it concerns the given "
    "recruitment (the same post designation and cycle). A different post, stream, qualifier or "
    "cycle is false. If the document does not say, answer false.\n"
    "- evidence_span must be copied EXACTLY from the document.\n"
    "Reply with ONE JSON object of exactly this shape and nothing else:\n"
    '{"same_recruitment":true|false,"evidence_span":"<verbatim>","reason":"<one short sentence>"}'
)


def _model_name(provider: VerificationProvider) -> str:
    return getattr(provider, 'cfg', {}).get('model', provider.name) if hasattr(provider, 'cfg') \
        else provider.name


def _call(provider: VerificationProvider, system: str, user: str, max_tokens: int):
    try:
        raw = provider.complete([{'role': 'system', 'content': system},
                                 {'role': 'user', 'content': user}], max_tokens=max_tokens)
    except ProviderError as e:
        return None, e.infra.value, e.detail
    except Exception as e:                                       # noqa: BLE001
        return None, 'LLM_ERROR', f'{type(e).__name__}: {e}'
    text = _extract_json(raw)
    try:
        return json.loads(text), 'OK', ''
    except (ValueError, TypeError):
        return text, 'OK', 'model output was not valid JSON'


def extract_designation(title_block: str, provider: VerificationProvider | None = None):
    """(raw model output, infra status value, detail). The output is unvalidated."""
    provider = provider or get_provider()
    user = ('NOTIFICATION TEXT (its opening, verbatim):\n"""' + normalise_ws(title_block)
            + '"""\nReport the designation as instructed. /no_think')
    return _call(provider, _EXTRACT_SYSTEM, user, max_tokens=900)


def confirm_same_recruitment(designation: str, cycle: str, components: list[str],
                             document_block: str, provider: VerificationProvider | None = None):
    """(raw model output, infra status value, detail). The output is unvalidated."""
    provider = provider or get_provider()
    user = ('RECRUITMENT DESIGNATION: ' + normalise_ws(designation) + '\n'
            + f'CYCLE: {cycle}\n'
            + ('COMPONENTS DECLARED BY ITS NOTIFICATION: ' + ', '.join(components) + '\n'
               if components else '')
            + 'DOCUMENT (its opening, verbatim):\n"""' + normalise_ws(document_block)
            + '"""\nAnswer as instructed. /no_think')
    return _call(provider, _CONFIRM_SYSTEM, user, max_tokens=300)


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
