"""GovOS's single Claude integration: the installed Claude CLI, run server-side, and nothing else.

    from tools.claude_cli import get_gateway, Operation
    result = get_gateway().run(Operation.CHECK_COMPLETENESS, {...})

Claude is machinery, never factual authority. It may classify, compare, judge completeness and
propose candidate values with quotations; deterministic code verifies every quotation against the
supplied source text and the publication gate decides what is published. See
CLAUDE_CLI_INTEGRATION.md.
"""
from .client import ClaudeGateway, get_gateway, job_scope, set_gateway
from .config import ClaudeConfig, load_config
from .schemas import ClaudeResult, InfraStatus, Operation

__all__ = ['ClaudeGateway', 'ClaudeConfig', 'ClaudeResult', 'InfraStatus', 'Operation',
           'get_gateway', 'set_gateway', 'job_scope', 'load_config']
