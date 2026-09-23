"""Run one semantic verification through the model and return a strictly validated result.

Every failure mode -- disabled, unreachable, timeout, protocol error, non-JSON, wrong shape
-- becomes a `VerificationResult.error(...)` with an infrastructure status. None of them can
be read as SUPPORTED, so the model can never publish by failing.
"""
from __future__ import annotations

import re

from .client import ProviderError, VerificationProvider, get_provider
from .prompts import build_messages
from .schemas import Claim, InfraStatus, VerificationResult

#: Qwen3 emits a <think>…</think> chain-of-thought; strip it before looking for the JSON.
_THINK = re.compile(r'<think>.*?</think>', re.S | re.I)
_JSON = re.compile(r'\{.*\}', re.S)


def _extract_json(text: str) -> str:
    text = _THINK.sub('', text or '').strip()
    m = _JSON.search(text)
    return m.group(0) if m else text


def run_llm(claim: Claim, provider: VerificationProvider | None = None) -> VerificationResult:
    provider = provider or get_provider()
    model = getattr(provider, 'cfg', {}).get('model', provider.name) if hasattr(provider, 'cfg') else provider.name
    try:
        raw = provider.complete(build_messages(claim))
    except ProviderError as e:
        return VerificationResult.error(e.infra, e.detail, model)
    except Exception as e:                                       # noqa: BLE001
        return VerificationResult.error(InfraStatus.LLM_ERROR, f'{type(e).__name__}: {e}', model)
    return VerificationResult.from_model_json(_extract_json(raw), model=model)
