"""The typed contract of every Claude operation: statuses, the operation allowlist, one strict
output schema per operation, a small schema validator, and the result envelope.

Claude's output is untrusted data. Nothing in it is used until it has been parsed as exactly one
JSON object and validated against the schema owned here. A reply that fails either step is an
infrastructure state (`CLAUDE_INVALID_OUTPUT`, `CLAUDE_SCHEMA_REJECTED`), never a factual one:
no infrastructure state can be read as VERIFIED, as NOT_PUBLISHED, or as "the authority
published nothing".
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class InfraStatus(str, Enum):
    """What happened to a Claude call. Deliberately NOT a factual state."""

    OK = 'OK'
    CLAUDE_DISABLED = 'CLAUDE_DISABLED'
    CLAUDE_CLI_NOT_INSTALLED = 'CLAUDE_CLI_NOT_INSTALLED'
    CLAUDE_CLI_NOT_AUTHENTICATED = 'CLAUDE_CLI_NOT_AUTHENTICATED'
    #: The installed CLI lacks a flag the hardened invocation needs, or is a `.cmd` shim.
    CLAUDE_CLI_UNSUPPORTED = 'CLAUDE_CLI_UNSUPPORTED'
    #: No free slot in time, or the account is rate/usage limited.
    CLAUDE_CLI_BUSY = 'CLAUDE_CLI_BUSY'
    CLAUDE_CLI_TIMEOUT = 'CLAUDE_CLI_TIMEOUT'
    CLAUDE_CLI_FAILED = 'CLAUDE_CLI_FAILED'
    #: Not one parseable JSON object, or over the output limit.
    CLAUDE_INVALID_OUTPUT = 'CLAUDE_INVALID_OUTPUT'
    #: Valid JSON that does not match the operation's schema.
    CLAUDE_SCHEMA_REJECTED = 'CLAUDE_SCHEMA_REJECTED'
    #: The call's input was refused before the CLI was started (over the size limit).
    CLAUDE_INPUT_REJECTED = 'CLAUDE_INPUT_REJECTED'
    #: Discovery needs web tools, and the CLI did not provide them.
    CLAUDE_DISCOVERY_UNAVAILABLE = 'CLAUDE_DISCOVERY_UNAVAILABLE'
    CANCELLED = 'CANCELLED'

    @property
    def retryable(self) -> bool:
        """Transient infrastructure only. A malformed or schema-rejected reply is a verdict on
        that reply, not a transient failure, and is never retried as one."""
        return self in _RETRYABLE


_RETRYABLE = frozenset({InfraStatus.CLAUDE_CLI_TIMEOUT, InfraStatus.CLAUDE_CLI_BUSY,
                        InfraStatus.CLAUDE_CLI_FAILED})

#: Safe, fixed wording per state. Raw stderr, command lines and paths are never shown.
SAFE_MESSAGES = {
    InfraStatus.OK: '',
    InfraStatus.CLAUDE_DISABLED: 'Claude integration is disabled (GOVOS_CLAUDE_ENABLED is not true).',
    InfraStatus.CLAUDE_CLI_NOT_INSTALLED: 'The Claude CLI is not installed or could not be found on this host.',
    InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED: 'The Claude CLI on this host is not signed in.',
    InfraStatus.CLAUDE_CLI_UNSUPPORTED: 'The installed Claude CLI does not support the required non-interactive options.',
    InfraStatus.CLAUDE_CLI_BUSY: 'Claude is busy or rate limited right now.',
    InfraStatus.CLAUDE_CLI_TIMEOUT: 'The Claude CLI did not answer in time.',
    InfraStatus.CLAUDE_CLI_FAILED: 'The Claude CLI call failed.',
    InfraStatus.CLAUDE_INVALID_OUTPUT: 'The Claude CLI returned output that was not one valid JSON object.',
    InfraStatus.CLAUDE_SCHEMA_REJECTED: 'The Claude CLI returned JSON that does not match the expected shape.',
    InfraStatus.CLAUDE_INPUT_REJECTED: 'The request was too large to send to Claude.',
    InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE: 'Web discovery is not available through the installed Claude CLI.',
    InfraStatus.CANCELLED: 'The operation was cancelled.',
}


class Operation(str, Enum):
    """The allowlist. A request can only name one of these; flags, prompts, tool permissions and
    working directories are owned by the server and never taken from a caller."""

    VERIFY_CLAIM = 'VERIFY_CLAIM'
    CLASSIFY_ATTRIBUTION = 'CLASSIFY_ATTRIBUTION'
    CLASSIFY_DATE = 'CLASSIFY_DATE'
    CHECK_COMPLETENESS = 'CHECK_COMPLETENESS'
    EXTRACT_DESIGNATION = 'EXTRACT_DESIGNATION'
    CONFIRM_RECRUITMENT = 'CONFIRM_RECRUITMENT'
    ORDER_ROADMAP = 'ORDER_ROADMAP'
    DISCOVER_SOURCES = 'DISCOVER_SOURCES'
    EXTRACT_FIELDS = 'EXTRACT_FIELDS'
    ANSWER_QUESTION = 'ANSWER_QUESTION'
    GENERATE_PRACTICE = 'GENERATE_PRACTICE'
    #: A second, independent pass: solve generated questions WITHOUT being shown the answer key.
    SOLVE_PRACTICE = 'SOLVE_PRACTICE'
    #: Name the role of official links the deterministic rules could not classify. A role only:
    #: never a source class, never a new link (tools/exam_builder/authority_discovery.py).
    CLASSIFY_SOURCE = 'CLASSIFY_SOURCE'


# ------------------------------------------------------------------------------- the validator
_TYPES = {
    'string': lambda v: isinstance(v, str),
    'boolean': lambda v: isinstance(v, bool),
    'integer': lambda v: isinstance(v, int) and not isinstance(v, bool),
    'number': lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    'null': lambda v: v is None,
    'array': lambda v: isinstance(v, list),
    'object': lambda v: isinstance(v, dict),
}

#: The only keywords sent to the CLI. Length and range limits are enforced here, after the
#: reply, because not every structured-output backend accepts them.
_CLI_KEYWORDS = ('type', 'properties', 'required', 'additionalProperties', 'items', 'enum', 'description')


def validate(value: Any, schema: dict, path: str = '$') -> list[str]:
    """Every way `value` departs from `schema` (strict: unknown object keys are errors unless
    the schema says otherwise). An empty list means valid."""
    errors: list[str] = []
    kinds = schema.get('type')
    if kinds is not None:
        kinds = [kinds] if isinstance(kinds, str) else list(kinds)
        if not any(_TYPES[k](value) for k in kinds):
            return [f'{path}: expected {"/".join(kinds)}']
    if 'enum' in schema and value not in schema['enum']:
        errors.append(f'{path}: not one of the allowed values')
    if isinstance(value, str):
        if 'maxLength' in schema and len(value) > schema['maxLength']:
            errors.append(f'{path}: longer than {schema["maxLength"]}')
        if 'minLength' in schema and len(value) < schema['minLength']:
            errors.append(f'{path}: shorter than {schema["minLength"]}')
        if 'pattern' in schema and not re.search(schema['pattern'], value):
            errors.append(f'{path}: does not match the required pattern')
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if 'minimum' in schema and value < schema['minimum']:
            errors.append(f'{path}: below {schema["minimum"]}')
        if 'maximum' in schema and value > schema['maximum']:
            errors.append(f'{path}: above {schema["maximum"]}')
    if isinstance(value, list):
        if 'maxItems' in schema and len(value) > schema['maxItems']:
            errors.append(f'{path}: more than {schema["maxItems"]} items')
        if 'minItems' in schema and len(value) < schema['minItems']:
            errors.append(f'{path}: fewer than {schema["minItems"]} items')
        item_schema = schema.get('items')
        if item_schema:
            for i, item in enumerate(value):
                errors.extend(validate(item, item_schema, f'{path}[{i}]'))
    if isinstance(value, dict):
        props = schema.get('properties', {})
        for name in schema.get('required', []):
            if name not in value:
                errors.append(f'{path}.{name}: missing')
        if schema.get('additionalProperties', True) is False:
            for name in value:
                if name not in props:
                    errors.append(f'{path}.{name}: not allowed')
        for name, sub in props.items():
            if name in value:
                errors.extend(validate(value[name], sub, f'{path}.{name}'))
    return errors


def to_cli_schema(schema: dict) -> dict:
    """The schema as sent to the CLI: only the widely supported keywords, recursively."""
    out = {k: v for k, v in schema.items() if k in _CLI_KEYWORDS}
    if 'properties' in out:
        out['properties'] = {k: to_cli_schema(v) for k, v in out['properties'].items()}
    if 'items' in out:
        out['items'] = to_cli_schema(out['items'])
    return out


#: Top-level keys that carry hidden reasoning rather than the answer. They are dropped before
#: validation; only concise structured reasons the schema asks for are kept.
REASONING_KEYS = frozenset({'thinking', 'thoughts', 'reasoning', 'chain_of_thought', 'chain-of-thought',
                            'scratchpad', 'analysis', 'internal_notes', '_thinking'})


def strip_reasoning(obj: Any) -> tuple[Any, int]:
    """(object without reasoning-like top-level keys, how many were dropped)."""
    if not isinstance(obj, dict):
        return obj, 0
    kept = {k: v for k, v in obj.items() if k not in REASONING_KEYS}
    return kept, len(obj) - len(kept)


def fingerprint(obj: Any) -> str:
    """A stable id for a JSON-able value: sha256 of its canonical form."""
    blob = json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False, default=str)
    return hashlib.sha256(blob.encode('utf-8')).hexdigest()


# ------------------------------------------------------------------------------ building blocks
def _str(max_len: int = 600, enum: Optional[list] = None, min_len: int = 0) -> dict:
    s: dict = {'type': 'string', 'maxLength': max_len}
    if min_len:
        s['minLength'] = min_len
    if enum is not None:
        s['enum'] = list(enum)
    return s


_BOOL = {'type': 'boolean'}
_CONFIDENCE = _str(8, ['high', 'medium', 'low'])


def _obj(props: dict, required: Optional[list] = None) -> dict:
    return {'type': 'object', 'properties': props,
            'required': list(props) if required is None else list(required),
            'additionalProperties': False}


def _arr(items: dict, max_items: int = 50) -> dict:
    return {'type': 'array', 'items': items, 'maxItems': max_items}


#: Every role the attribution check can ask about; each field's own subset is enforced by the
#: caller (attribution_claude.validate), and a test pins that its lists stay inside this one.
ATTRIBUTION_ROLES = [
    'total_vacancies', 'category_count', 'post_count', 'row_serial', 'other_number',
    'qualification_requirement', 'age_relaxation', 'disqualification', 'exemption', 'other',
    'fee_rule', 'certificate_rule', 'refund_rule', 'pay_scale', 'fee_exemption',
    'post_names', 'category_labels', 'table_residue', 'documents',
    'paper_scheme', 'shared_or_partial_marks', 'incidental_mention',
]

#: The milestone reader's own event kinds, plus the two non-events a date can be.
DATE_ROLES = ['NOTIFICATION', 'APPLICATION_START', 'APPLICATION_CLOSE', 'FEE_PAYMENT_END',
              'CORRECTION_WINDOW', 'EXAM', 'SKILL_TEST', 'PHYSICAL_TEST', 'ADMIT_CARD',
              'CITY_INTIMATION', 'ANSWER_KEY', 'RESULT', 'OPTION_ENTRY', 'DOCUMENT_VERIFICATION',
              'INTERVIEW', 'OTHER_EVENT', 'REFERENCE', 'NOT_A_DATE']

#: The candidate-facing sections an answer may point at (mapped to section numbers by the UI).
NAVIGATION_TARGETS = ['OVERVIEW', 'DATES', 'ELIGIBILITY', 'APPLICATION', 'PATTERN', 'SYLLABUS',
                      'ROADMAP', 'RESOURCES', 'PRACTICE', 'MOCKS', 'ADMIT_CARD', 'EXAM_DAY',
                      'RESULTS', 'FAQS', 'CORRIGENDA', 'PORTALS', 'CUTOFFS', 'NONE']

#: The facts extraction may propose. Anything else is not a field GovOS reads.
EXTRACTABLE_FIELDS = ['application_start', 'application_last_date', 'exam_date', 'admit_card_date',
                      'result_date', 'vacancies_total', 'application_fee', 'minimum_age',
                      'maximum_age', 'educational_qualification', 'number_of_attempts',
                      'exam_stage_name', 'official_portal']

DISCOVERY_KINDS = ['NOTIFICATION', 'SYLLABUS', 'RESULT', 'ADMIT_CARD', 'ANSWER_KEY', 'PORTAL', 'OTHER']

#: The roles CLASSIFY_SOURCE may name: tools.exam_builder.discover.DocKind without UNKNOWN. Listed
#: here rather than imported so this package never depends on the builder; a test pins the two
#: together. UNKNOWN is deliberately absent -- "I cannot tell" is CLAUDE leaving a link out.
SOURCE_ROLES = ['EXAM_PAGE', 'NOTIFICATION', 'CORRIGENDUM', 'SYLLABUS', 'EXAM_PATTERN', 'QUESTION_PAPER',
                'ANSWER_KEY', 'ADMIT_CARD', 'RESULT', 'APPLICATION_PORTAL', 'CUTOFF', 'CALENDAR', 'OTR_PORTAL',
                'OFFICIAL_PORTAL', 'APPLICATION_GUIDE', 'EXAM_GUIDE', 'EXAM_DAY_INSTRUCTIONS', 'STUDY_MATERIAL',
                'LECTURE_VIDEO', 'PRACTICE_TOOL', 'DISCOVERY_SIGNAL']

OPERATION_SCHEMAS: dict[Operation, dict] = {
    Operation.VERIFY_CLAIM: _obj({
        'decision': _str(16, ['SUPPORTED', 'CONTRADICTED', 'INSUFFICIENT']),
        'identity_supported': _BOOL, 'evidence_supported': _BOOL, 'claim_supported': _BOOL,
        'reason': _str(600),
    }),
    Operation.CLASSIFY_ATTRIBUTION: _obj({
        'role': _str(40, ATTRIBUTION_ROLES), 'supports_value': _BOOL, 'scope': _str(300),
        'evidence_span': _str(1200), 'confidence': _CONFIDENCE, 'conflicts': _arr(_str(300), 10),
    }),
    Operation.CLASSIFY_DATE: _obj({
        'role': _str(30, DATE_ROLES), 'supports_date': _BOOL, 'evidence_span': _str(1200),
        'is_reference': _BOOL, 'confidence': _CONFIDENCE, 'conflicts': _arr(_str(300), 10),
    }),
    Operation.CHECK_COMPLETENESS: _obj({
        'complete': _BOOL, 'continues_after': _BOOL, 'starts_mid_unit': _BOOL,
        'confidence': _CONFIDENCE, 'reason': _str(300),
    }),
    Operation.EXTRACT_DESIGNATION: _obj({
        'designation_core': _arr(_str(300), 20), 'qualifiers': _arr(_str(300), 20),
        'cycle': _str(40), 'declared_components': _arr(_str(400), 40),
        'evidence_spans': _arr(_str(1500), 20), 'confidence': _CONFIDENCE,
        'ambiguities': _arr(_str(300), 10),
    }),
    Operation.CONFIRM_RECRUITMENT: _obj({
        'same_recruitment': _BOOL, 'evidence_span': _str(1200), 'reason': _str(300),
    }),
    Operation.ORDER_ROADMAP: _obj({
        'order': _arr(_obj({'id': _str(120), 'why': _str(240)}), 400),
    }),
    Operation.DISCOVER_SOURCES: _obj({
        'candidates': _arr(_obj({
            'title': _str(300), 'url': _str(2048), 'authority_name': _str(200),
            'document_kind': _str(20, DISCOVERY_KINDS), 'why_relevant': _str(400),
            'snippet': _str(600),
        }), 20),
        'searched_queries': _arr(_str(300), 20),
        'notes': _str(600),
    }),
    Operation.EXTRACT_FIELDS: _obj({
        'fields': _arr(_obj({
            'field': _str(40, EXTRACTABLE_FIELDS), 'value': _str(600), 'quote': _str(1500),
            'location': _str(160),
        }), 40),
    }),
    Operation.ANSWER_QUESTION: _obj({
        'answer': _str(1600),
        'basis': _str(24, ['VERIFIED_DATA', 'NOT_IN_RECORD', 'NEEDS_CLARIFICATION']),
        'cited_fact_ids': _arr(_str(24), 12),
        'uncertainty': _str(12, ['NONE', 'PARTIAL', 'UNKNOWN']),
        'navigate_to': _str(16, NAVIGATION_TARGETS),
        'follow_up': _str(240),
    }),
    Operation.GENERATE_PRACTICE: _obj({
        'questions': _arr(_obj({
            'topic': _str(300), 'stem': _str(900),
            'options': {'type': 'array', 'items': _str(300), 'minItems': 4, 'maxItems': 4},
            'correct_index': {'type': 'integer', 'minimum': 0, 'maximum': 3},
            'explanation': _str(900),
        }), 10),
    }),
    # `choice` is the option the solver worked out (0-3), or -1 when it cannot say: no option is right,
    # more than one is, or the question is ambiguous. `index` echoes the question's position.
    Operation.SOLVE_PRACTICE: _obj({
        'solutions': _arr(_obj({
            'index': {'type': 'integer', 'minimum': 0, 'maximum': 9},
            'choice': {'type': 'integer', 'minimum': -1, 'maximum': 3},
        }), 10),
    }),
    # Only links GovOS sent; `index` echoes the link's position. A link Claude cannot place is left out.
    Operation.CLASSIFY_SOURCE: _obj({
        'links': _arr(_obj({
            'index': {'type': 'integer', 'minimum': 0, 'maximum': 49},
            'role': _str(24, SOURCE_ROLES),
            'is_repository': _BOOL,
        }), 50),
    }),
}


# ------------------------------------------------------------------------------- the result
@dataclass
class ClaudeResult:
    """One Claude call's outcome. `output` is present only when the reply was valid JSON that
    matched the operation's schema; every other case is an explicit `status`."""

    operation: str
    status: InfraStatus
    job_id: str = ''
    started_at: str = ''
    ended_at: str = ''
    duration_ms: int = 0
    cli_available: bool = False
    #: 'ok' | 'nonzero' | 'timeout' | 'cancelled' | 'not_started' | 'cached'
    exit_category: str = 'not_started'
    timed_out: bool = False
    output: Optional[dict] = None
    validation_errors: list = field(default_factory=list)
    message: str = ''
    template_version: str = ''
    input_fingerprint: str = ''
    output_fingerprint: str = ''
    cache_hit: bool = False
    cli_version: str = ''
    #: Concise accounting from the CLI envelope (turns, tokens, observed web activity).
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.status is InfraStatus.OK and self.output is not None

    def as_dict(self, *, include_output: bool = True) -> dict:
        """The safe, serialisable view: no command line, path, environment or raw stderr."""
        out = {
            'jobId': self.job_id, 'operation': self.operation, 'status': self.status.value,
            'startedAt': self.started_at, 'endedAt': self.ended_at, 'durationMs': self.duration_ms,
            'cliAvailable': self.cli_available, 'exitCategory': self.exit_category,
            'timedOut': self.timed_out, 'validationErrors': list(self.validation_errors),
            'message': self.message, 'templateVersion': self.template_version,
            'inputFingerprint': self.input_fingerprint, 'outputFingerprint': self.output_fingerprint,
            'cacheHit': self.cache_hit,
        }
        if include_output:
            out['output'] = self.output
        return out

    @classmethod
    def failed(cls, operation: str, status: InfraStatus, **kw: Any) -> 'ClaudeResult':
        return cls(operation=operation, status=status, message=SAFE_MESSAGES.get(status, ''), **kw)
