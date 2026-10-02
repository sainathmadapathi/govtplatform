"""Claude CLI integration configuration.

Everything here is read from the process environment on each call (never cached, never
hard-coded, never accepted from an HTTP request). `.env` is loaded by the app's own loader
(`app.py`); this module only reads `os.environ`.

There is deliberately no API-key setting. Claude is reached only through the installed
Claude CLI, authenticated on the host by the account login (`claude auth login`). See
CLAUDE_CLI_INTEGRATION.md.
"""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from typing import Mapping, Optional

ENV_ENABLED = 'GOVOS_CLAUDE_ENABLED'
ENV_CLI_PATH = 'GOVOS_CLAUDE_CLI_PATH'
ENV_TIMEOUT = 'GOVOS_CLAUDE_TIMEOUT_SECONDS'
ENV_CONCURRENCY = 'GOVOS_CLAUDE_MAX_CONCURRENCY'
ENV_MAX_OUTPUT = 'GOVOS_CLAUDE_MAX_OUTPUT_BYTES'
ENV_WORKDIR = 'GOVOS_CLAUDE_JOB_WORKDIR'
ENV_ADMIN_TOKEN = 'GOVOS_CLAUDE_ADMIN_TOKEN'
ENV_MODEL = 'GOVOS_CLAUDE_MODEL'

DEFAULT_TIMEOUT_SECONDS = 120.0
DEFAULT_CONCURRENCY = 2
DEFAULT_MAX_OUTPUT_BYTES = 262_144
#: How long a caller waits for a free CLI slot before the call is reported BUSY.
DEFAULT_SLOT_WAIT_SECONDS = 30.0

_TRUE = ('1', 'true', 'yes', 'on')


def _truthy(value: str) -> bool:
    return (value or '').strip().lower() in _TRUE


def _number(value: str, default: float, low: float, high: float) -> float:
    try:
        n = float((value or '').strip())
    except (TypeError, ValueError):
        return default
    return max(low, min(high, n))


@dataclass(frozen=True)
class ClaudeConfig:
    """The gateway's settings. Immutable; build a new one rather than mutating."""

    enabled: bool = False
    #: An explicit executable path, or '' to resolve `claude` from PATH.
    cli_path: str = ''
    #: The base per-call timeout. Operations scale it (web discovery is slower).
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_concurrency: int = DEFAULT_CONCURRENCY
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES
    #: An empty directory, outside the repository, that every call runs in, so no project
    #: instructions (CLAUDE.md) or settings are discovered from the working directory.
    workdir: str = ''
    #: Optional model alias passed to the CLI. Empty means the CLI's own default.
    model: str = ''
    slot_wait_seconds: float = DEFAULT_SLOT_WAIT_SECONDS
    #: Arguments placed between the executable and the fixed flags. Never read from the
    #: environment or a request: it exists so tests can run a fake CLI script
    #: (`cli_path=sys.executable`, `cli_args_prefix=(fake_script,)`).
    cli_args_prefix: tuple = ()

    @property
    def effective_workdir(self) -> str:
        return self.workdir or os.path.join(tempfile.gettempdir(), 'govos-claude-work')


def load_config(env: Optional[Mapping[str, str]] = None) -> ClaudeConfig:
    """The configuration as the environment currently states it."""
    env = os.environ if env is None else env

    def get(name: str) -> str:
        return (env.get(name) or '').strip()

    return ClaudeConfig(
        enabled=_truthy(get(ENV_ENABLED)),
        cli_path=get(ENV_CLI_PATH),
        timeout_seconds=_number(get(ENV_TIMEOUT), DEFAULT_TIMEOUT_SECONDS, 10.0, 900.0),
        max_concurrency=int(_number(get(ENV_CONCURRENCY), DEFAULT_CONCURRENCY, 1, 4)),
        max_output_bytes=int(_number(get(ENV_MAX_OUTPUT), DEFAULT_MAX_OUTPUT_BYTES, 4096, 4_194_304)),
        workdir=get(ENV_WORKDIR),
        model=get(ENV_MODEL),
    )
