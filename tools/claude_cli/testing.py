"""Test support for the Claude integration. Automated tests never call the real Claude CLI.

`FakeClaude` is a real `ClaudeGateway` whose process runner is scripted, so a test that uses it
still exercises the production command construction, envelope parsing, reasoning-stripping,
schema validation and failure classification. Only the process is fake.

    gw = FakeClaude({'decision': 'SUPPORTED', ...})          # one valid structured reply
    gw = FakeClaude(reply_one, reply_two)                    # replies in order; the last repeats
    gw = FakeClaude(fail=InfraStatus.CLAUDE_CLI_TIMEOUT)     # an infrastructure failure
    gw = FakeClaude('not json at all')                       # a malformed reply
    gw.calls, gw.argvs, gw.prompts                           # what the CLI was asked

For tests that need a real child process (timeouts, process-tree kill, stdin, environment,
command-injection inertness) use `tools/claude_cli/fake_cli.py` through `fake_cli_config()`.
"""
from __future__ import annotations

import contextlib
import json
import os
import sys
from typing import Any, Callable, Optional

from .audit import AuditSink, DecisionCache
from .client import ClaudeGateway, REQUIRED_FLAGS, OPTIONAL_FLAGS
from .config import ClaudeConfig
from .runner import TEST_MODE_ENV, ProcessOutcome, Runner
from . import client as _client
from .schemas import InfraStatus, OPERATION_SCHEMAS, Operation, to_cli_schema

# Importing this module marks the process as under test: the real CLI can not be started from here on.
os.environ[TEST_MODE_ENV] = '1'

HELP_TEXT = 'Usage: claude [options]\n\nOptions:\n' + '\n'.join(
    f'  {f}   (test help line)' for f in REQUIRED_FLAGS + OPTIONAL_FLAGS) + '\n'

FAKE_VERSION = '2.1.285 (Claude Code)'

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
FAKE_CLI_SCRIPT = os.path.join(_THIS_DIR, 'fake_cli.py')


def envelope(structured: Any = None, *, result: Optional[str] = None, is_error: bool = False,
             subtype: str = 'success', permission_denials: Optional[list] = None,
             web_search: int = 0, web_fetch: int = 0, turns: int = 2, extra: Optional[dict] = None) -> dict:
    """What `claude -p --output-format json` prints on success (shape verified on 2.1.285)."""
    env = {'type': 'result', 'subtype': subtype, 'is_error': is_error, 'num_turns': turns,
           'result': result if result is not None else (json.dumps(structured) if structured is not None else ''),
           'permission_denials': permission_denials or [],
           'usage': {'input_tokens': 2, 'cache_creation_input_tokens': 100, 'cache_read_input_tokens': 0,
                     'output_tokens': 20,
                     'server_tool_use': {'web_search_requests': web_search, 'web_fetch_requests': web_fetch}},
           'total_cost_usd': 0.001}
    if structured is not None:
        env['structured_output'] = structured
    env.update(extra or {})
    return env


class ByOperation(dict):
    """A scripted reply that depends on which operation the CLI was asked for:
    `ByOperation({Operation.CLASSIFY_ATTRIBUTION: reply, Operation.CHECK_COMPLETENESS: whole})`.
    An operation with no entry is answered with an empty object (which the schema rejects)."""


def operation_of(argv: list) -> Optional[Operation]:
    """Which operation a model call was for, read from the JSON schema the gateway passed."""
    try:
        schema = json.loads(argv[argv.index('--json-schema') + 1])
    except (ValueError, IndexError):
        return None
    for op, candidate in OPERATION_SCHEMAS.items():
        if to_cli_schema(candidate) == schema:
            return op
    return None


class ScriptedRunner(Runner):
    """A runner that plays back scripted CLI output without starting a process."""

    def __init__(self, replies: tuple, *, fail: Optional[InfraStatus] = None, authenticated: bool = True,
                 help_text: str = HELP_TEXT) -> None:
        self.replies = list(replies)
        self.fail = fail
        self.authenticated = authenticated
        self.help_text = help_text
        self.argvs: list = []
        self.prompts: list = []
        self.envs: list = []
        self.cwds: list = []
        self.quick: list = []
        self.ops: list = []

    # ------------------------------------------------------------------------- helpers
    def _next(self) -> Any:
        if not self.replies:
            return {}
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]

    def run(self, argv, *, stdin_text, env, cwd, timeout, max_output_bytes, cancel_event=None):
        args = list(argv)
        if '--help' in args:
            return ProcessOutcome(returncode=0, stdout=self.help_text)
        if '--version' in args:
            return ProcessOutcome(returncode=0, stdout=FAKE_VERSION)
        if 'auth' in args and 'status' in args:
            self.quick.append('auth status')
            return ProcessOutcome(returncode=0, stdout=json.dumps({'loggedIn': self.authenticated}))
        if cancel_event is not None and cancel_event.is_set():
            return ProcessOutcome(cancelled=True)
        # a real model call
        self.argvs.append(args)
        self.prompts.append(stdin_text)
        self.envs.append(dict(env))
        self.cwds.append(cwd)
        op = operation_of(args)
        self.ops.append(op)
        s = self.fail
        if s is InfraStatus.CLAUDE_CLI_TIMEOUT:
            return ProcessOutcome(timed_out=True)
        if s is InfraStatus.CLAUDE_CLI_FAILED:
            return ProcessOutcome(returncode=1, stderr='boom')
        if s is InfraStatus.CLAUDE_CLI_BUSY:
            return ProcessOutcome(returncode=0, stdout=json.dumps(envelope(
                is_error=True, subtype='error_during_execution', result='API Error: 429 rate limit reached')))
        if s is InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED:
            return ProcessOutcome(returncode=1, stdout=json.dumps(envelope(
                is_error=True, result='Not logged in · Please run /login')))
        if s is InfraStatus.CLAUDE_INVALID_OUTPUT:
            return ProcessOutcome(returncode=0, stdout='this is not json')
        if s is InfraStatus.CLAUDE_SCHEMA_REJECTED:
            return ProcessOutcome(returncode=0, stdout=json.dumps(envelope({'unexpected': True})))
        if s is InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE:
            return ProcessOutcome(returncode=0, stdout=json.dumps(envelope(
                {'candidates': [], 'searched_queries': [], 'notes': ''}, permission_denials=[{'tool': 'WebSearch'}])))
        reply = self._next()
        if isinstance(reply, ByOperation):
            reply = reply.get(op, {})
        if callable(reply):
            reply = reply(args, stdin_text)
        if isinstance(reply, ProcessOutcome):
            return reply
        if isinstance(reply, str):
            return ProcessOutcome(returncode=0, stdout=reply)
        if isinstance(reply, dict) and reply.get('type') == 'result':      # a ready-made envelope
            return ProcessOutcome(returncode=0, stdout=json.dumps(reply))
        return ProcessOutcome(returncode=0, stdout=json.dumps(envelope(reply)))


class FakeClaude(ClaudeGateway):
    """A `ClaudeGateway` over a scripted runner. See the module docstring."""

    def __init__(self, *replies: Any, enabled: bool = True, fail: Optional[InfraStatus] = None,
                 authenticated: Optional[bool] = None, cache: Optional[DecisionCache] = None,
                 audit: Optional[AuditSink] = None, help_text: Optional[str] = None,
                 concurrency: int = 2, **config_kw: Any) -> None:
        if fail is InfraStatus.CLAUDE_DISABLED:
            enabled = False
        if authenticated is None:
            authenticated = fail is not InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED
        if fail is InfraStatus.CLAUDE_CLI_UNSUPPORTED and help_text is None:
            help_text = 'Usage: claude [options]\n  --print\n'
        cli = os.path.join(_THIS_DIR, '__does_not_exist__') if fail is InfraStatus.CLAUDE_CLI_NOT_INSTALLED \
            else sys.executable
        cfg = ClaudeConfig(enabled=enabled, cli_path=cli, max_concurrency=concurrency, slot_wait_seconds=2.0,
                           **config_kw)
        self.scripted = ScriptedRunner(replies, fail=fail, authenticated=authenticated,
                                       help_text=help_text or HELP_TEXT)
        super().__init__(cfg, runner=self.scripted, audit=audit, cache=cache)

    @property
    def calls(self) -> int:
        """How many model calls reached the (fake) CLI. Cache hits and refusals do not count."""
        return len(self.scripted.argvs)

    @property
    def argvs(self) -> list:
        return self.scripted.argvs

    @property
    def ops(self) -> list:
        """The operation of each model call that reached the (fake) CLI, in order."""
        return self.scripted.ops

    def calls_for(self, operation: Operation) -> int:
        return sum(1 for o in self.scripted.ops if o is operation)

    @property
    def prompts(self) -> list:
        return self.scripted.prompts


def fake_cli_config(scenario_path: str, **kw: Any) -> ClaudeConfig:
    """A config that runs `fake_cli.py` as a real child process under `sys.executable`."""
    return ClaudeConfig(enabled=True, cli_path=sys.executable, cli_args_prefix=(FAKE_CLI_SCRIPT, '--scenario', scenario_path),
                        slot_wait_seconds=kw.pop('slot_wait_seconds', 3.0), **kw)


class ForbiddenClaude(ClaudeGateway):
    """A gateway that fails the test if anything asks it to run: proof that a code path never
    reaches Claude (a deterministic failure must stop before any call)."""

    def __init__(self, message: str = 'Claude must not be called on this path') -> None:
        super().__init__(ClaudeConfig(enabled=True, cli_path=sys.executable), runner=ScriptedRunner(()))
        self._message = message
        self.attempts = 0

    def run(self, *args: Any, **kwargs: Any):                            # noqa: D401
        self.attempts += 1
        raise AssertionError(self._message)


def verdict_reply(decision: str, *, identity: bool = True, evidence: bool = True, claim: bool = True,
                  reason: str = 'stub') -> dict:
    """A VERIFY_CLAIM structured reply."""
    return {'decision': decision, 'identity_supported': identity, 'evidence_supported': evidence,
            'claim_supported': claim, 'reason': reason}


@contextlib.contextmanager
def use_gateway(gateway: Optional[ClaudeGateway]):
    """Install `gateway` as the process-wide one for the duration of a block (the builder reaches
    Claude through `get_gateway()`), restoring whatever was there before."""
    previous = _client._DEFAULT
    _client.set_gateway(gateway)
    try:
        yield gateway
    finally:
        _client.set_gateway(previous)
