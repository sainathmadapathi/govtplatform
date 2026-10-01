"""The one Claude CLI gateway.

Every AI/agentic operation in GovOS goes through `ClaudeGateway.run(operation, payload)`. The
gateway turns an allow-listed operation and a payload of schema fields into one hardened,
non-interactive call of the installed Claude CLI, and returns a typed `ClaudeResult`.

The exact invocation (verified against Claude Code 2.1.285; see CLAUDE_CLI_INTEGRATION.md):

    claude -p
        --output-format json
        --json-schema <the operation's schema>
        --system-prompt <the operation's fixed system prompt>
        --tools <"" for none, or the operation's read-only web tools>
        [--allowedTools <the same tools>]
        --no-session-persistence
        --permission-mode dontAsk
        --setting-sources local --strict-mcp-config --disable-slash-commands
        [--no-chrome] [--exclude-dynamic-system-prompt-sections] [--model <alias>]

with the prompt on stdin, in an empty working directory outside the repository, with a narrow
environment. `--bare` is deliberately not used: it forbids the account login and would require an
API key, which GovOS never uses.

Rules this module enforces:
  * the CLI path comes from configuration or PATH, never from a request;
  * supported flags are detected from the installed CLI's own `--help`, not assumed;
  * stdout is untrusted: it is parsed as exactly one JSON object and validated against the
    operation's schema before any caller sees it;
  * infrastructure failure, a malformed reply and a schema-rejected reply are distinct states
    and none of them is ever a factual result;
  * raw stderr, command lines, paths and environment values are never returned or logged.
"""
from __future__ import annotations

import contextlib
import contextvars
import json
import os
import re
import shutil
import tempfile
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from .audit import AuditSink, DecisionCache, now_iso
from .config import ClaudeConfig, load_config
from .prompts import TEMPLATES, PromptTemplate, new_nonce
from .runner import Runner, SubprocessRunner, build_child_env
from .schemas import (OPERATION_SCHEMAS, SAFE_MESSAGES, ClaudeResult, InfraStatus, Operation,
                      fingerprint, strip_reasoning, to_cli_schema, validate)

#: Flags without which the hardened invocation cannot be made. A CLI missing any of them is
#: refused (CLAUDE_CLI_UNSUPPORTED) rather than called with weaker isolation.
REQUIRED_FLAGS = ('--print', '--output-format', '--json-schema', '--system-prompt', '--tools',
                  '--no-session-persistence', '--permission-mode', '--setting-sources',
                  '--strict-mcp-config', '--disable-slash-commands')
#: Used when present; their absence only means a little more overhead.
OPTIONAL_FLAGS = ('--no-chrome', '--exclude-dynamic-system-prompt-sections', '--model', '--allowedtools')

_AUTH_PATTERNS = re.compile(
    r'not logged in|please run /login|please log ?in|invalid api key|authentication[_ ]error|'
    r'oauth token has expired|unauthori[sz]ed|\b401\b', re.I)
_BUSY_PATTERNS = re.compile(
    r'rate[ _-]?limit|usage limit|limit reached|too many requests|overloaded|\b429\b|\b529\b', re.I)

_AUTH_TTL_SECONDS = 60.0
_UNAUTH_TTL_SECONDS = 10.0


# ---------------------------------------------------------------------------- the job scope
@dataclass
class JobScope:
    job_id: str = ''
    cancel_event: Optional[threading.Event] = None


_SCOPE: contextvars.ContextVar = contextvars.ContextVar('govos_claude_scope', default=JobScope())


@contextlib.contextmanager
def job_scope(job_id: str = '', cancel_event: Optional[threading.Event] = None):
    """Everything run inside carries this job's id and can be cancelled through its event, with no
    signature changes in the deep callers (a build's many verification calls)."""
    token = _SCOPE.set(JobScope(job_id, cancel_event))
    try:
        yield
    finally:
        _SCOPE.reset(token)


# ------------------------------------------------------------------------------- slot control
class _Slots:
    """A counting semaphore whose limit can be changed between calls."""

    def __init__(self, limit: int) -> None:
        self._cond = threading.Condition()
        self._limit = max(1, limit)
        self._in_use = 0

    def set_limit(self, limit: int) -> None:
        with self._cond:
            self._limit = max(1, limit)
            self._cond.notify_all()

    def acquire(self, wait: float) -> bool:
        deadline = time.monotonic() + wait
        with self._cond:
            while self._in_use >= self._limit:
                left = deadline - time.monotonic()
                if left <= 0:
                    return False
                self._cond.wait(left)
            self._in_use += 1
            return True

    def release(self) -> None:
        with self._cond:
            self._in_use = max(0, self._in_use - 1)
            self._cond.notify()

    @property
    def in_use(self) -> int:
        with self._cond:
            return self._in_use

    @property
    def limit(self) -> int:
        return self._limit


@dataclass
class Capabilities:
    version: str = ''
    flags: frozenset = frozenset()
    missing_required: tuple = ()
    ok: bool = False


@dataclass
class _Resolved:
    path: str = ''
    status: Optional[InfraStatus] = None
    label: str = ''


class ClaudeGateway:
    """Runs allow-listed operations through the installed Claude CLI."""

    def __init__(self, config: Optional[ClaudeConfig] = None, *, runner: Optional[Runner] = None,
                 audit: Optional[AuditSink] = None, cache: Optional[DecisionCache] = None,
                 clock=time.monotonic) -> None:
        self._config_fixed = config
        self.runner: Runner = runner or SubprocessRunner()
        self.audit: AuditSink = audit or AuditSink()
        self.cache = cache
        self._clock = clock
        self._slots = _Slots((config or load_config()).max_concurrency)
        self._caps: dict = {}
        self._auth: dict = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------------ configuration
    @property
    def config(self) -> ClaudeConfig:
        cfg = self._config_fixed or load_config()
        self._slots.set_limit(cfg.max_concurrency)
        return cfg

    def is_enabled(self) -> bool:
        return self.config.enabled

    # ------------------------------------------------------------------ locating the CLI
    def _resolve(self, cfg: ClaudeConfig) -> _Resolved:
        path = cfg.cli_path
        if path:
            path = os.path.expandvars(os.path.expanduser(path))
            if not os.path.isfile(path):
                return _Resolved(status=InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
        else:
            path = shutil.which('claude') or ''
            if os.name == 'nt' and not path.lower().endswith('.exe'):
                exe = shutil.which('claude.exe')
                path = exe or path
            if not path:
                return _Resolved(status=InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
        # A .cmd/.bat/.ps1 shim would be run through cmd.exe or PowerShell, which re-parse the
        # arguments (and the JSON schema and system prompt are arguments). Refuse rather than risk it.
        if path.lower().endswith(('.cmd', '.bat', '.ps1')):
            return _Resolved(status=InfraStatus.CLAUDE_CLI_UNSUPPORTED)
        return _Resolved(path=path, label=os.path.basename(path))

    def _base_argv(self, cfg: ClaudeConfig, path: str) -> list:
        return [path, *cfg.cli_args_prefix]

    def _quick(self, cfg: ClaudeConfig, path: str, args: list, timeout: float = 20.0):
        return self.runner.run(self._base_argv(cfg, path) + args, stdin_text='', env=build_child_env(),
                               cwd=self._workdir(cfg), timeout=timeout, max_output_bytes=262_144)

    def _workdir(self, cfg: ClaudeConfig) -> str:
        wd = cfg.effective_workdir
        try:
            os.makedirs(wd, exist_ok=True)
        except OSError:
            # Never the process's own directory (the repository, with its CLAUDE.md and settings):
            # an unusable configured directory falls back to the default empty one outside it.
            wd = os.path.join(tempfile.gettempdir(), 'govos-claude-work')
            try:
                os.makedirs(wd, exist_ok=True)
            except OSError:
                wd = tempfile.gettempdir()
        return wd

    # ------------------------------------------------------------- capability detection
    def capabilities(self, cfg: Optional[ClaudeConfig] = None, path: str = '') -> Capabilities:
        cfg = cfg or self.config
        resolved = self._resolve(cfg) if not path else _Resolved(path=path)
        if resolved.status is not None:
            return Capabilities()
        try:
            st = os.stat(resolved.path)
            key = (resolved.path, st.st_mtime_ns, st.st_size, tuple(cfg.cli_args_prefix))
        except OSError:
            key = (resolved.path, 0, 0, tuple(cfg.cli_args_prefix))
        with self._lock:
            if key in self._caps:
                return self._caps[key]
        help_out = self._quick(cfg, resolved.path, ['--help'])
        ver_out = self._quick(cfg, resolved.path, ['--version'], timeout=10.0)
        flags = frozenset(m.lower() for m in re.findall(r'(?<![\w-])(--[A-Za-z][A-Za-z0-9-]*)',
                                                        help_out.stdout or ''))
        version = ''
        m = re.search(r'\d+\.\d+\.\d+', ver_out.stdout or '')
        if m:
            version = m.group(0)
        missing = tuple(f for f in REQUIRED_FLAGS if f not in flags)
        caps = Capabilities(version=version, flags=flags, missing_required=missing,
                            ok=bool(flags) and not missing)
        if flags:                  # an unreadable --help (timeout, cold start) is retried, never remembered
            with self._lock:
                self._caps[key] = caps
        return caps

    # ---------------------------------------------------------------- authentication
    def _auth_state(self, cfg: ClaudeConfig, path: str) -> Optional[bool]:
        """True (signed in), False (not), None (cannot tell). Cached briefly."""
        key = (path, tuple(cfg.cli_args_prefix))
        now = self._clock()
        with self._lock:
            cached = self._auth.get(key)
            if cached and now < cached[1]:
                return cached[0]
        state: Optional[bool] = None
        try:
            out = self._quick(cfg, path, ['auth', 'status'], timeout=20.0)
            data = json.loads((out.stdout or '').strip() or 'null')
            if isinstance(data, dict) and isinstance(data.get('loggedIn'), bool):
                state = data['loggedIn']
        except Exception:                                        # noqa: BLE001
            state = None
        ttl = _AUTH_TTL_SECONDS if state is not False else _UNAUTH_TTL_SECONDS
        with self._lock:
            self._auth[key] = (state, now + ttl)
        return state

    def forget_auth(self) -> None:
        with self._lock:
            self._auth.clear()

    # -------------------------------------------------------------------------- health
    def health(self) -> dict:
        """What may be said about readiness. No path, command line, account or secret."""
        cfg = self.config
        out = {'enabled': cfg.enabled, 'installed': False, 'authenticated': None, 'ready': False,
               'executable': '', 'version': '', 'busy': False, 'status': InfraStatus.OK.value,
               'message': ''}
        if not cfg.enabled:
            out['status'] = InfraStatus.CLAUDE_DISABLED.value
            out['message'] = SAFE_MESSAGES[InfraStatus.CLAUDE_DISABLED]
            return out
        resolved = self._resolve(cfg)
        if resolved.status is not None:
            out['status'] = resolved.status.value
            out['message'] = SAFE_MESSAGES[resolved.status]
            out['installed'] = resolved.status is InfraStatus.CLAUDE_CLI_UNSUPPORTED
            return out
        out['installed'] = True
        out['executable'] = resolved.label
        caps = self.capabilities(cfg, resolved.path)
        out['version'] = caps.version
        if not caps.ok:
            out['status'] = InfraStatus.CLAUDE_CLI_UNSUPPORTED.value
            out['message'] = SAFE_MESSAGES[InfraStatus.CLAUDE_CLI_UNSUPPORTED]
            return out
        out['busy'] = self._slots.in_use >= self._slots.limit
        auth = self._auth_state(cfg, resolved.path)
        out['authenticated'] = auth
        if auth is False:
            out['status'] = InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED.value
            out['message'] = SAFE_MESSAGES[InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED]
            return out
        out['ready'] = True
        return out

    # --------------------------------------------------------------------------- the call
    def run(self, operation: Operation | str, payload: dict, *, job_id: str = '',
            cancel_event: Optional[threading.Event] = None) -> ClaudeResult:
        scope = _SCOPE.get()
        job_id = job_id or scope.job_id
        cancel_event = cancel_event or scope.cancel_event
        started = now_iso()
        t0 = self._clock()
        try:
            op = Operation(operation)
        except ValueError:
            result = ClaudeResult.failed(str(operation), InfraStatus.CLAUDE_INPUT_REJECTED,
                                         validation_errors=['operation is not on the allowlist'])
            return self._finish(result, started, t0, job_id)
        template = TEMPLATES[op]
        result = ClaudeResult(operation=op.value, status=InfraStatus.CLAUDE_CLI_FAILED,
                              template_version=template.version, job_id=job_id)
        try:
            self._run(op, template, payload, result, cancel_event)
        except Exception:                                        # noqa: BLE001
            # Whatever went wrong, the caller gets a typed infrastructure state, never a traceback
            # with paths and never a half-built result.
            result.status = InfraStatus.CLAUDE_CLI_FAILED
            result.message = SAFE_MESSAGES[InfraStatus.CLAUDE_CLI_FAILED]
            result.output = None
        return self._finish(result, started, t0, job_id)

    def _finish(self, result: ClaudeResult, started: str, t0: float, job_id: str) -> ClaudeResult:
        result.started_at = started
        result.ended_at = now_iso()
        result.duration_ms = int((self._clock() - t0) * 1000)
        result.job_id = job_id or result.job_id
        if not result.message:
            result.message = SAFE_MESSAGES.get(result.status, '')
        if result.output is not None:
            result.output_fingerprint = fingerprint(result.output)
        try:
            self.audit.record({
                'ts': result.ended_at, 'operation': result.operation, 'job_id': result.job_id,
                'status': result.status.value, 'exit_category': result.exit_category,
                'duration_ms': result.duration_ms, 'template_version': result.template_version,
                'input_fingerprint': result.input_fingerprint,
                'output_fingerprint': result.output_fingerprint, 'cache_hit': result.cache_hit,
                'cli_version': result.cli_version, 'turns': result.stats.get('turns', 0),
                'input_tokens': result.stats.get('inputTokens', 0),
                'output_tokens': result.stats.get('outputTokens', 0),
                'web_search_requests': result.stats.get('webSearchRequests', 0),
                'web_fetch_requests': result.stats.get('webFetchRequests', 0),
                'message': result.message})
        except Exception:                                        # noqa: BLE001
            pass
        return result

    def _run(self, op: Operation, template: PromptTemplate, payload: Any, result: ClaudeResult,
             cancel_event: Optional[threading.Event]) -> None:
        cfg = self.config
        if not cfg.enabled:
            result.status = InfraStatus.CLAUDE_DISABLED
            return
        if cancel_event is not None and cancel_event.is_set():
            result.status, result.exit_category = InfraStatus.CANCELLED, 'cancelled'
            return

        # ---- input checks, before anything is started
        errors = self._check_payload(template, payload)
        if errors:
            result.status = InfraStatus.CLAUDE_INPUT_REJECTED
            result.validation_errors = errors
            return
        result.input_fingerprint = fingerprint({'op': op.value, 'v': template.version, 'payload': payload})

        # ---- a valid earlier decision for exactly this input
        if template.cacheable and self.cache is not None:
            hit = self.cache.get(result.input_fingerprint)
            if hit is not None and not validate(hit, OPERATION_SCHEMAS[op]):
                result.status, result.output, result.exit_category = InfraStatus.OK, hit, 'cached'
                result.cache_hit = True
                return

        # ---- the CLI
        resolved = self._resolve(cfg)
        if resolved.status is not None:
            result.status = resolved.status
            return
        result.cli_available = True
        caps = self.capabilities(cfg, resolved.path)
        result.cli_version = caps.version
        if not caps.ok:
            result.status = InfraStatus.CLAUDE_CLI_UNSUPPORTED
            return
        if template.tools and any(t.lower() not in ('websearch', 'webfetch') for t in template.tools):
            result.status = InfraStatus.CLAUDE_CLI_UNSUPPORTED     # the allowlist is read-only web tools
            return
        if self._auth_state(cfg, resolved.path) is False:
            result.status = InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED
            return

        argv = self._argv(cfg, resolved.path, op, template, caps)
        prompt = template.render(payload, new_nonce())
        timeout = max(10.0, cfg.timeout_seconds * template.timeout_factor)

        if not self._slots.acquire(cfg.slot_wait_seconds):
            result.status = InfraStatus.CLAUDE_CLI_BUSY
            return
        try:
            outcome = self.runner.run(argv, stdin_text=prompt, env=build_child_env(),
                                      cwd=self._workdir(cfg), timeout=timeout,
                                      max_output_bytes=cfg.max_output_bytes, cancel_event=cancel_event)
        finally:
            self._slots.release()
        self._interpret(op, template, outcome, result)
        if result.status is InfraStatus.OK and template.cacheable and self.cache is not None \
                and result.output is not None:
            self.cache.put(result.input_fingerprint, op.value, template.version, result.output)

    # ------------------------------------------------------------------------- building
    @staticmethod
    def _check_payload(template: PromptTemplate, payload: Any) -> list:
        if not isinstance(payload, dict):
            return ['payload must be an object']
        errors = [f'missing input: {k}' for k in template.required if payload.get(k) in (None, '')]
        try:
            size = len(json.dumps(payload, ensure_ascii=False))
        except (TypeError, ValueError, RecursionError):
            return ['payload is not JSON serialisable']
        if size > template.max_input_chars:
            errors.append(f'input is larger than {template.max_input_chars} characters')
        elif not errors:
            try:
                template.render(payload, '0' * 16)      # a wrong-shaped value is a bad input, not a CLI failure
            except Exception:                                    # noqa: BLE001
                errors.append('input does not have the shape this operation expects')
        return errors

    def _argv(self, cfg: ClaudeConfig, path: str, op: Operation, template: PromptTemplate,
              caps: Capabilities) -> list:
        argv = self._base_argv(cfg, path) + [
            '-p', '--output-format', 'json',
            '--json-schema', json.dumps(to_cli_schema(OPERATION_SCHEMAS[op]), separators=(',', ':')),
            '--system-prompt', template.system,
            '--tools', ','.join(template.tools),
            '--no-session-persistence', '--permission-mode', 'dontAsk',
            '--setting-sources', 'local', '--strict-mcp-config', '--disable-slash-commands',
        ]
        if template.tools and '--allowedtools' in caps.flags:
            argv += ['--allowedTools', ','.join(template.tools)]
        if '--no-chrome' in caps.flags:
            argv.append('--no-chrome')
        if '--exclude-dynamic-system-prompt-sections' in caps.flags:
            argv.append('--exclude-dynamic-system-prompt-sections')
        if cfg.model and '--model' in caps.flags:
            argv += ['--model', cfg.model]
        return argv

    # ---------------------------------------------------------------------- interpreting
    def _interpret(self, op: Operation, template: PromptTemplate, outcome, result: ClaudeResult) -> None:
        if outcome.start_error:
            result.status = (InfraStatus.CLAUDE_CLI_NOT_INSTALLED if outcome.start_error == 'not_found'
                             else InfraStatus.CLAUDE_CLI_FAILED)
            result.exit_category = 'not_started'
            return
        result.exit_category = 'timeout' if outcome.timed_out else 'cancelled' if outcome.cancelled \
            else 'ok' if outcome.returncode == 0 else 'nonzero'
        if outcome.cancelled:
            result.status = InfraStatus.CANCELLED
            return
        if outcome.timed_out:
            result.status, result.timed_out = InfraStatus.CLAUDE_CLI_TIMEOUT, True
            return
        if outcome.output_truncated:
            result.status = InfraStatus.CLAUDE_INVALID_OUTPUT
            result.validation_errors = ['output exceeded the size limit']
            return

        envelope = None
        text = (outcome.stdout or '').strip()
        if text:
            try:
                envelope = json.loads(text)
            except (ValueError, TypeError):
                envelope = None

        if not isinstance(envelope, dict):
            result.status = self._failure_status(outcome.stderr, outcome.stdout, outcome.returncode)
            if result.status is InfraStatus.CLAUDE_CLI_FAILED and outcome.returncode == 0:
                result.status = InfraStatus.CLAUDE_INVALID_OUTPUT
                result.validation_errors = ['output was not a JSON envelope']
            return

        result.stats = self._stats(envelope)
        if envelope.get('is_error') or (envelope.get('subtype') not in (None, 'success')) \
                or (outcome.returncode not in (0, None)):
            body = ' '.join(str(x) for x in (envelope.get('result'), envelope.get('error'),
                                              outcome.stderr) if x)
            result.status = self._failure_status(body, '', outcome.returncode)
            return
        if op is Operation.DISCOVER_SOURCES and envelope.get('permission_denials'):
            result.status = InfraStatus.CLAUDE_DISCOVERY_UNAVAILABLE
            return

        structured = envelope.get('structured_output')
        if structured is None:
            # Without a structured payload the only acceptable alternative is a `result` that is,
            # by itself, exactly one JSON object. No prose is searched for JSON.
            raw = envelope.get('result')
            if isinstance(raw, str):
                try:
                    structured = json.loads(raw.strip())
                except (ValueError, TypeError):
                    structured = None
        if not isinstance(structured, dict):
            result.status = InfraStatus.CLAUDE_INVALID_OUTPUT
            result.validation_errors = ['no structured JSON object in the reply']
            return

        structured, dropped = strip_reasoning(structured)
        if dropped:
            result.stats['reasoningKeysDropped'] = dropped
        errors = validate(structured, OPERATION_SCHEMAS[op])
        if errors:
            result.status = InfraStatus.CLAUDE_SCHEMA_REJECTED
            result.validation_errors = errors[:12]
            return
        result.status, result.output = InfraStatus.OK, structured

    @staticmethod
    def _failure_status(body: str, stdout: str, returncode: Optional[int]) -> InfraStatus:
        blob = f'{body or ""} {stdout or ""}'
        if _AUTH_PATTERNS.search(blob):
            return InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED
        if _BUSY_PATTERNS.search(blob):
            return InfraStatus.CLAUDE_CLI_BUSY
        return InfraStatus.CLAUDE_CLI_FAILED

    @staticmethod
    def _stats(envelope: dict) -> dict:
        usage = envelope.get('usage') if isinstance(envelope.get('usage'), dict) else {}
        tools = usage.get('server_tool_use') if isinstance(usage.get('server_tool_use'), dict) else {}

        def num(v: Any) -> int:
            return v if isinstance(v, int) and not isinstance(v, bool) else 0

        # Verified on Claude Code 2.1.286: `usage.server_tool_use` stays 0 even when the web tools ran. The
        # search count is reported per model in `modelUsage`; WebFetch has no counter at all, so `turns`
        # (a call that used a tool takes more than the usual two) is the only signal for it.
        per_model = envelope.get('modelUsage') if isinstance(envelope.get('modelUsage'), dict) else {}
        searches = num(tools.get('web_search_requests')) + sum(
            num(m.get('webSearchRequests')) for m in per_model.values() if isinstance(m, dict))

        return {'turns': num(envelope.get('num_turns')),
                'inputTokens': num(usage.get('input_tokens')) + num(usage.get('cache_creation_input_tokens'))
                + num(usage.get('cache_read_input_tokens')),
                'outputTokens': num(usage.get('output_tokens')),
                'webSearchRequests': searches,
                'webFetchRequests': num(tools.get('web_fetch_requests'))}


# ------------------------------------------------------------------------ the shared gateway
_DEFAULT: Optional[ClaudeGateway] = None
_DEFAULT_LOCK = threading.Lock()


def get_gateway() -> ClaudeGateway:
    """The process-wide gateway (configuration is read from the environment on each call)."""
    global _DEFAULT
    with _DEFAULT_LOCK:
        if _DEFAULT is None:
            _DEFAULT = ClaudeGateway()
        return _DEFAULT


def set_gateway(gateway: Optional[ClaudeGateway]) -> None:
    """Install (or, with None, reset) the shared gateway. The app uses it to attach its audit
    sink and decision cache; tests use it to inject a fake."""
    global _DEFAULT
    with _DEFAULT_LOCK:
        _DEFAULT = gateway
