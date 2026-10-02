"""The typed contract (schemas.py): statuses, the validator, the CLI schema subset, reasoning
stripping, fingerprints and the result type.

Requirement tags in each docstring name the line of the gateway test brief a test answers:
[STATUS] infra statuses are never factual / only transient ones are retryable,
[VALIDATOR] strict validate(), [CLI-SCHEMA] to_cli_schema(), [COT] chain-of-thought stripping,
[RESULT] the typed ClaudeResult.
"""
from __future__ import annotations

import copy
import json
import unittest

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.gateway_fixtures import VALID_OUTPUTS
from tools.claude_cli.schemas import (OPERATION_SCHEMAS, REASONING_KEYS, SAFE_MESSAGES, ClaudeResult,
                                      InfraStatus, Operation, fingerprint, strip_reasoning, to_cli_schema,
                                      validate)

#: Every word any factual state in the repository uses. An infrastructure state must never share one.
FACTUAL_WORDS = {'VERIFIED', 'OFFICIALLY_VERIFIED', 'UNDER_VERIFICATION', 'NOT_PUBLISHED', 'NEEDS_REVIEW',
                 'NOT_EXTRACTED', 'FOUND', 'SUPERSEDED', 'SUPPORTED', 'CONTRADICTED', 'INSUFFICIENT',
                 'PROMOTED', 'AVAILABLE', 'NOT_ANNOUNCED'}

RETRYABLE = {InfraStatus.CLAUDE_CLI_TIMEOUT, InfraStatus.CLAUDE_CLI_BUSY, InfraStatus.CLAUDE_CLI_FAILED}


def _factual_values() -> set:
    values = set(FACTUAL_WORDS)
    for module, name in (('tools.exam_builder.schema', 'Status'), ('tools.exam_authoring.record', 'Status')):
        try:
            mod = __import__(module, fromlist=[name])
            values |= {m.value for m in getattr(mod, name)}
        except ImportError:                                  # pragma: no cover
            pass
    try:
        from tools.exam_builder.verification.schemas import VerificationDecision
        values |= {m.value for m in VerificationDecision if m.value != 'ERROR'}
    except ImportError:                                      # pragma: no cover
        pass
    return values


class InfraStatusTests(unittest.TestCase):
    def test_no_infrastructure_status_is_a_factual_state(self):
        """[STATUS] No InfraStatus name or value equals VERIFIED / NOT_PUBLISHED / NEEDS_REVIEW /
        NOT_EXTRACTED / FOUND / SUPPORTED ... in any of the repository's factual vocabularies."""
        factual = _factual_values()
        self.assertIn('NOT_PUBLISHED', factual)
        self.assertIn('VERIFIED', factual)
        for status in InfraStatus:
            self.assertNotIn(status.value, factual, status)
            self.assertNotIn(status.name, factual, status)
            self.assertEqual(status.value, status.name)

    def test_only_timeout_busy_and_failed_are_retryable(self):
        """[STATUS] Only CLAUDE_CLI_TIMEOUT / CLAUDE_CLI_BUSY / CLAUDE_CLI_FAILED are retryable; a
        malformed or schema-rejected reply, a refused input, a missing CLI and a cancel are not."""
        self.assertEqual({s for s in InfraStatus if s.retryable}, RETRYABLE)
        for status in set(InfraStatus) - RETRYABLE:
            self.assertFalse(status.retryable, status)
        for status in (InfraStatus.CLAUDE_INVALID_OUTPUT, InfraStatus.CLAUDE_SCHEMA_REJECTED,
                       InfraStatus.CLAUDE_INPUT_REJECTED, InfraStatus.CANCELLED, InfraStatus.CLAUDE_DISABLED,
                       InfraStatus.CLAUDE_CLI_NOT_INSTALLED, InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED,
                       InfraStatus.CLAUDE_CLI_UNSUPPORTED, InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE):
            self.assertFalse(status.retryable, status)

    def test_every_status_has_a_fixed_safe_message_with_no_path_or_secret(self):
        """[STATUS] SAFE_MESSAGES covers every state; wording is fixed prose with no path, flag or
        environment value in it."""
        self.assertEqual(set(SAFE_MESSAGES), set(InfraStatus))
        for status, message in SAFE_MESSAGES.items():
            if status is InfraStatus.OK:
                self.assertEqual(message, '')
                continue
            self.assertTrue(message)
            for needle in ('\\', '/Users', 'sk-', '--', 'ANTHROPIC', 'Traceback', 'stderr'):
                self.assertNotIn(needle, message, status)

    def test_operation_allowlist_is_closed_and_complete(self):
        """[TEMPLATES] Operation, OPERATION_SCHEMAS and TEMPLATES name exactly the same set."""
        from tools.claude_cli.prompts import TEMPLATES
        self.assertEqual(set(OPERATION_SCHEMAS), set(Operation))
        self.assertEqual(set(TEMPLATES), set(Operation))
        self.assertEqual(len(Operation), 12)


class ValidatorTests(unittest.TestCase):
    def test_valid_replies_for_every_operation_validate_clean(self):
        """[VALIDATOR] A well-formed reply for each operation passes validate() with no errors."""
        for op in Operation:
            with self.subTest(op=op.value):
                self.assertEqual(validate(VALID_OUTPUTS[op], OPERATION_SCHEMAS[op]), [])

    def test_unknown_keys_are_errors_at_every_object_level(self):
        """[VALIDATOR] A key the schema does not name is rejected (additionalProperties false), at the
        top level and inside nested objects."""
        for op in Operation:
            with self.subTest(op=op.value):
                reply = copy.deepcopy(VALID_OUTPUTS[op])
                reply['zzz'] = 1
                self.assertIn('$.zzz: not allowed', validate(reply, OPERATION_SCHEMAS[op]))
        nested = copy.deepcopy(VALID_OUTPUTS[Operation.ORDER_ROADMAP])
        nested['order'][0]['extra'] = 'x'
        self.assertIn('$.order[0].extra: not allowed', validate(nested, OPERATION_SCHEMAS[Operation.ORDER_ROADMAP]))

    def test_every_object_in_every_schema_is_strict(self):
        """[VALIDATOR] additionalProperties is False on every object of every operation schema, and
        every property is required (nothing is optional by accident)."""
        def walk(schema, where):
            if schema.get('type') == 'object':
                self.assertIs(schema.get('additionalProperties'), False, where)
                self.assertEqual(sorted(schema['required']), sorted(schema['properties']), where)
                for name, sub in schema['properties'].items():
                    walk(sub, f'{where}.{name}')
            if schema.get('type') == 'array' and 'items' in schema:
                walk(schema['items'], f'{where}[]')

        for op, schema in OPERATION_SCHEMAS.items():
            walk(schema, op.value)

    def test_missing_required_keys_are_reported_by_name(self):
        """[VALIDATOR] Each missing required property is an error naming it."""
        schema = OPERATION_SCHEMAS[Operation.VERIFY_CLAIM]
        errors = validate({}, schema)
        for name in schema['required']:
            self.assertIn(f'$.{name}: missing', errors)
        self.assertEqual(len(errors), len(schema['required']))

    def test_wrong_types_are_rejected(self):
        """[VALIDATOR] string / boolean / integer / array / object mismatches are errors; a bool is not
        an integer or a number, a float is not an integer."""
        self.assertEqual(validate('x', {'type': 'string'}), [])
        self.assertTrue(validate(1, {'type': 'string'}))
        self.assertTrue(validate('true', {'type': 'boolean'}))
        self.assertTrue(validate(1, {'type': 'boolean'}))
        self.assertTrue(validate(True, {'type': 'integer'}))
        self.assertTrue(validate(True, {'type': 'number'}))
        self.assertTrue(validate(1.5, {'type': 'integer'}))
        self.assertEqual(validate(1.5, {'type': 'number'}), [])
        self.assertTrue(validate({}, {'type': 'array'}))
        self.assertTrue(validate([], {'type': 'object'}))
        self.assertTrue(validate(None, {'type': 'string'}))
        self.assertEqual(validate(None, {'type': ['string', 'null']}), [])
        reply = copy.deepcopy(VALID_OUTPUTS[Operation.VERIFY_CLAIM])
        reply['identity_supported'] = 'yes'
        self.assertEqual(validate(reply, OPERATION_SCHEMAS[Operation.VERIFY_CLAIM]),
                         ['$.identity_supported: expected boolean'])

    def test_enum_is_enforced_exactly(self):
        """[VALIDATOR] A value outside an enum is an error, including a case or whitespace variant."""
        schema = OPERATION_SCHEMAS[Operation.VERIFY_CLAIM]
        for bad in ('supported', 'SUPPORTED ', 'VERIFIED', 'NOT_PUBLISHED', ''):
            reply = copy.deepcopy(VALID_OUTPUTS[Operation.VERIFY_CLAIM])
            reply['decision'] = bad
            self.assertEqual(validate(reply, schema), ['$.decision: not one of the allowed values'], bad)
        for good in ('SUPPORTED', 'CONTRADICTED', 'INSUFFICIENT'):
            reply = dict(VALID_OUTPUTS[Operation.VERIFY_CLAIM], decision=good)
            self.assertEqual(validate(reply, schema), [])

    def test_length_and_count_limits_are_enforced_after_the_reply(self):
        """[VALIDATOR] maxLength / minLength / maxItems / minItems / minimum / maximum / pattern are
        checked by validate() (the CLI is not sent them, so this is their only enforcement)."""
        self.assertEqual(validate('abc', {'type': 'string', 'maxLength': 3}), [])
        self.assertEqual(validate('abcd', {'type': 'string', 'maxLength': 3}), ['$: longer than 3'])
        self.assertEqual(validate('a', {'type': 'string', 'minLength': 2}), ['$: shorter than 2'])
        self.assertEqual(validate('ab', {'type': 'string', 'pattern': '^[0-9]+$'}),
                         ['$: does not match the required pattern'])
        arr = {'type': 'array', 'items': {'type': 'integer'}, 'minItems': 1, 'maxItems': 2}
        self.assertEqual(validate([1, 2], arr), [])
        self.assertEqual(validate([1, 2, 3], arr), ['$: more than 2 items'])
        self.assertEqual(validate([], arr), ['$: fewer than 1 items'])
        self.assertEqual(validate([1, 'x'], arr), ['$[1]: expected integer'])
        num = {'type': 'integer', 'minimum': 0, 'maximum': 3}
        self.assertEqual(validate(3, num), [])
        self.assertEqual(validate(4, num), ['$: above 3'])
        self.assertEqual(validate(-1, num), ['$: below 0'])

    def test_real_operation_limits_are_enforced(self):
        """[VALIDATOR] The operation schemas' own limits bite: an over-long reason, 11 practice
        questions, 3 options, correct_index 4, a 21st discovery candidate, a 401st roadmap entry."""
        def errs(op, mutate):
            reply = copy.deepcopy(VALID_OUTPUTS[op])
            mutate(reply)
            return validate(reply, OPERATION_SCHEMAS[op])

        self.assertTrue(errs(Operation.VERIFY_CLAIM, lambda r: r.update(reason='x' * 601)))
        self.assertFalse(errs(Operation.VERIFY_CLAIM, lambda r: r.update(reason='x' * 600)))
        self.assertTrue(errs(Operation.GENERATE_PRACTICE, lambda r: r['questions'].extend(
            copy.deepcopy(r['questions']) * 10)))
        self.assertTrue(errs(Operation.GENERATE_PRACTICE, lambda r: r['questions'][0].update(options=['a', 'b', 'c'])))
        self.assertTrue(errs(Operation.GENERATE_PRACTICE, lambda r: r['questions'][0].update(correct_index=4)))
        self.assertTrue(errs(Operation.GENERATE_PRACTICE, lambda r: r['questions'][0].update(correct_index=True)))
        self.assertTrue(errs(Operation.DISCOVER_SOURCES, lambda r: r['candidates'].extend(
            copy.deepcopy(r['candidates']) * 20)))
        self.assertTrue(errs(Operation.ORDER_ROADMAP, lambda r: r.update(order=[{'id': 'a', 'why': 'b'}] * 401)))
        self.assertTrue(errs(Operation.ANSWER_QUESTION, lambda r: r.update(cited_fact_ids=['f'] * 13)))
        self.assertTrue(errs(Operation.ANSWER_QUESTION, lambda r: r.update(navigate_to='ANYWHERE')))

    def test_validate_never_echoes_reply_values(self):
        """[VALIDATOR] Error text carries paths, never the offending value (a reply is untrusted
        text and must not be reflected into messages)."""
        reply = copy.deepcopy(VALID_OUTPUTS[Operation.VERIFY_CLAIM])
        reply['decision'] = 'LEAKED-VALUE-123'
        reply['reason'] = 'y' * 700
        self.assertNotIn('LEAKED-VALUE-123', ' '.join(validate(reply, OPERATION_SCHEMAS[Operation.VERIFY_CLAIM])))

    def test_a_schema_without_additional_properties_false_allows_unknown_keys(self):
        """[VALIDATOR] Strictness comes from the schema: validate() adds none of its own (documents
        the contract the object helper relies on)."""
        self.assertEqual(validate({'a': 1, 'b': 2}, {'type': 'object', 'properties': {'a': {'type': 'integer'}}}), [])

    def test_validate_does_not_mutate_its_inputs(self):
        """[VALIDATOR] validate() leaves value and schema untouched."""
        for op in Operation:
            schema, value = copy.deepcopy(OPERATION_SCHEMAS[op]), copy.deepcopy(VALID_OUTPUTS[op])
            validate(value, schema)
            self.assertEqual(schema, OPERATION_SCHEMAS[op])
            self.assertEqual(value, VALID_OUTPUTS[op])


class CliSchemaTests(unittest.TestCase):
    ALLOWED = {'type', 'properties', 'required', 'additionalProperties', 'items', 'enum', 'description'}
    LIMITS = {'maxLength', 'minLength', 'maxItems', 'minItems', 'minimum', 'maximum', 'pattern'}

    def _walk(self, schema, where=''):
        yield where, schema
        for name, sub in schema.get('properties', {}).items():
            yield from self._walk(sub, f'{where}.{name}')
        if 'items' in schema:
            yield from self._walk(schema['items'], f'{where}[]')

    def test_cli_schema_emits_only_the_allowed_keyword_subset(self):
        """[CLI-SCHEMA] Every schema node sent to the CLI uses only type / properties / required /
        additionalProperties / items / enum / description, recursively; no length or count limit."""
        for op, schema in OPERATION_SCHEMAS.items():
            sent = to_cli_schema(schema)
            for where, node in self._walk(sent, op.value):
                self.assertLessEqual(set(node), self.ALLOWED, where)
                self.assertFalse(set(node) & self.LIMITS, where)

    def test_cli_schema_keeps_the_structure_that_matters(self):
        """[CLI-SCHEMA] Structure is preserved: same property names, required list, strictness,
        enums and item shapes; only the limits are dropped."""
        for op, schema in OPERATION_SCHEMAS.items():
            sent = to_cli_schema(schema)
            self.assertEqual(sent['type'], 'object')
            self.assertEqual(sorted(sent['properties']), sorted(schema['properties']))
            self.assertEqual(sent['required'], schema['required'])
            self.assertIs(sent['additionalProperties'], False)
        sent = to_cli_schema(OPERATION_SCHEMAS[Operation.VERIFY_CLAIM])
        self.assertEqual(sent['properties']['decision']['enum'], ['SUPPORTED', 'CONTRADICTED', 'INSUFFICIENT'])
        practice = to_cli_schema(OPERATION_SCHEMAS[Operation.GENERATE_PRACTICE])
        self.assertEqual(practice['properties']['questions']['items']['properties']['options'],
                         {'type': 'array', 'items': {'type': 'string'}})

    def test_cli_schema_does_not_mutate_the_source_schema(self):
        """[CLI-SCHEMA] to_cli_schema() returns a new structure; the strict schema keeps its limits."""
        for op, schema in OPERATION_SCHEMAS.items():
            before = copy.deepcopy(schema)
            to_cli_schema(schema)
            self.assertEqual(schema, before, op)
        self.assertIn('maxLength', OPERATION_SCHEMAS[Operation.VERIFY_CLAIM]['properties']['reason'])

    def test_cli_schema_serialises_to_compact_json(self):
        """[CLI-SCHEMA] The schema is plain JSON (it travels as one argv element)."""
        for op, schema in OPERATION_SCHEMAS.items():
            text = json.dumps(to_cli_schema(schema), separators=(',', ':'))
            self.assertEqual(json.loads(text), to_cli_schema(schema))


class ReasoningStripTests(unittest.TestCase):
    def test_every_reasoning_key_is_removed_and_counted(self):
        """[COT] thinking / thoughts / reasoning / chain_of_thought / chain-of-thought / scratchpad /
        analysis / internal_notes / _thinking are dropped from the top level."""
        self.assertEqual(REASONING_KEYS, {'thinking', 'thoughts', 'reasoning', 'chain_of_thought',
                                          'chain-of-thought', 'scratchpad', 'analysis', 'internal_notes',
                                          '_thinking'})
        for key in sorted(REASONING_KEYS):
            kept, dropped = strip_reasoning({'decision': 'SUPPORTED', key: 'secret reasoning'})
            self.assertEqual(kept, {'decision': 'SUPPORTED'}, key)
            self.assertEqual(dropped, 1, key)
        kept, dropped = strip_reasoning({k: 'x' for k in REASONING_KEYS} | {'keep': 1})
        self.assertEqual(kept, {'keep': 1})
        self.assertEqual(dropped, len(REASONING_KEYS))

    def test_non_dicts_and_clean_dicts_pass_through(self):
        """[COT] Lists/strings are untouched; a dict with no reasoning key is returned equal, count 0."""
        self.assertEqual(strip_reasoning([1]), ([1], 0))
        self.assertEqual(strip_reasoning('x'), ('x', 0))
        self.assertEqual(strip_reasoning({'a': 1}), ({'a': 1}, 0))

    def test_no_operation_schema_uses_a_reasoning_key_as_a_real_field(self):
        """[COT] Stripping can never remove a legitimate field: no schema property (at any depth) is a
        reasoning key. (`reason` and `why` are concise answers the schema asks for, and are kept.)"""
        def names(schema):
            for name, sub in schema.get('properties', {}).items():
                yield name
                yield from names(sub)
            if 'items' in schema:
                yield from names(schema['items'])

        for op, schema in OPERATION_SCHEMAS.items():
            self.assertFalse(set(names(schema)) & REASONING_KEYS, op)

    def test_strip_does_not_mutate_the_input(self):
        """[COT] The caller's object is not modified in place."""
        original = {'a': 1, 'thinking': 't'}
        strip_reasoning(original)
        self.assertEqual(original, {'a': 1, 'thinking': 't'})


class FingerprintTests(unittest.TestCase):
    def test_fingerprint_is_stable_order_independent_and_sensitive(self):
        """[RESULT] sha256 over canonical JSON: key order is irrelevant, any value change changes it."""
        a = fingerprint({'x': 1, 'y': [1, 2], 'z': 'é'})
        self.assertEqual(a, fingerprint({'z': 'é', 'y': [1, 2], 'x': 1}))
        self.assertRegex(a, r'^[0-9a-f]{64}$')
        self.assertNotEqual(a, fingerprint({'x': 1, 'y': [2, 1], 'z': 'é'}))
        self.assertNotEqual(a, fingerprint({'x': 2, 'y': [1, 2], 'z': 'é'}))

    def test_fingerprint_reveals_nothing_readable(self):
        """[RESULT] The digest does not contain the input text."""
        self.assertNotIn('secret-source-text', fingerprint({'text': 'secret-source-text'}))


class ClaudeResultTests(unittest.TestCase):
    def test_ok_requires_status_ok_and_an_output(self):
        """[RESULT] `ok` is true only for OK with an output object; every other state is not ok."""
        self.assertTrue(ClaudeResult('VERIFY_CLAIM', InfraStatus.OK, output={'a': 1}).ok)
        self.assertFalse(ClaudeResult('VERIFY_CLAIM', InfraStatus.OK).ok)
        for status in set(InfraStatus) - {InfraStatus.OK}:
            self.assertFalse(ClaudeResult('VERIFY_CLAIM', status, output={'a': 1}).ok, status)

    def test_failed_helper_carries_the_fixed_message_and_no_output(self):
        """[RESULT] ClaudeResult.failed() has the status, the safe message and no output."""
        res = ClaudeResult.failed('NOPE', InfraStatus.CLAUDE_INPUT_REJECTED, validation_errors=['x'])
        self.assertEqual(res.status, InfraStatus.CLAUDE_INPUT_REJECTED)
        self.assertEqual(res.message, SAFE_MESSAGES[InfraStatus.CLAUDE_INPUT_REJECTED])
        self.assertIsNone(res.output)
        self.assertFalse(res.ok)

    def test_as_dict_is_the_safe_serialisable_view(self):
        """[RESULT] as_dict() is JSON-serialisable, names the typed fields, and has no command line,
        path, environment or stderr field."""
        res = ClaudeResult(operation='VERIFY_CLAIM', status=InfraStatus.OK, job_id='j1', started_at='a',
                           ended_at='b', duration_ms=5, output={'k': 'v'}, template_version='verify-claim/1',
                           input_fingerprint='i' * 64, output_fingerprint='o' * 64)
        data = json.loads(json.dumps(res.as_dict()))
        self.assertEqual(set(data), {'jobId', 'operation', 'status', 'startedAt', 'endedAt', 'durationMs',
                                     'cliAvailable', 'exitCategory', 'timedOut', 'validationErrors', 'message',
                                     'templateVersion', 'inputFingerprint', 'outputFingerprint', 'cacheHit',
                                     'output'})
        self.assertEqual(data['status'], 'OK')
        self.assertNotIn('output', res.as_dict(include_output=False))
        for forbidden in ('argv', 'cmd', 'command', 'path', 'env', 'stderr', 'stdout', 'cwd', 'prompt'):
            self.assertNotIn(forbidden, {k.lower() for k in data})


if __name__ == '__main__':
    unittest.main()
