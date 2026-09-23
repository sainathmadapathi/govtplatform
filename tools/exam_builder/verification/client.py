"""The verification provider abstraction and the local Qwen (OpenAI-compatible) provider.

Configuration is environment-only; the model file path never appears in source. A provider
fails *safely*: any transport, timeout, or protocol error raises `ProviderError` with a
category, which the verifier turns into an infrastructure result -- never into VERIFIED.

The provider speaks the OpenAI-compatible chat API a llama.cpp `llama-server` exposes, so the
same client works against a local server today and a future remote provider tomorrow. The
production/local split is deliberate: a deployed app cannot reach 127.0.0.1, so when the
provider is unavailable the verifier returns an explicit infrastructure state rather than
silently downgrading to unverified publication.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .schemas import InfraStatus


def _env(name: str, default: str = '') -> str:
    return (os.environ.get(name) or default).strip()


def config() -> dict:
    """Runtime configuration, read from the environment each call (never cached, never
    hard-coded). `.env` is loaded by the app's own loader; here we read the process env."""
    return {
        'enabled': _env('GOVOS_LLM_ENABLED', 'false').lower() in ('1', 'true', 'yes', 'on'),
        'url': _env('GOVOS_LLM_URL', 'http://127.0.0.1:8080/v1'),
        'model': _env('GOVOS_LLM_MODEL', 'qwen3-8b-q4_k_m'),
        'timeout': _float(_env('GOVOS_LLM_TIMEOUT_SECONDS', '60'), 60.0),
        # The model file path is configuration for whoever *runs* the server, not something
        # this client sends or logs to candidates.
        'model_path_set': bool(_env('GOVOS_LLM_MODEL_PATH')),
    }


def _float(value: str, default: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class ProviderError(Exception):
    def __init__(self, infra: InfraStatus, detail: str):
        super().__init__(detail)
        self.infra = infra
        self.detail = detail


class VerificationProvider:
    """A source of semantic verifications. Interface only; implementations must fail safe."""

    name = 'abstract'

    def is_enabled(self) -> bool:
        raise NotImplementedError

    def health(self) -> dict:
        raise NotImplementedError

    def complete(self, messages: list, *, max_tokens: int = 320) -> str:
        raise NotImplementedError


class LocalQwenVerificationProvider(VerificationProvider):
    """Talks to a local llama.cpp server over the OpenAI-compatible chat API."""

    name = 'local-qwen'

    def __init__(self, cfg: dict | None = None):
        self.cfg = cfg or config()

    def is_enabled(self) -> bool:
        return bool(self.cfg['enabled'])

    def _endpoint(self, path: str) -> str:
        base = self.cfg['url'].rstrip('/')
        return base + path

    def health(self) -> dict:
        """A cheap reachability probe. Never raises; returns a diagnostic dict with no
        filesystem paths or secrets."""
        out = {'provider': self.name, 'enabled': self.is_enabled(),
               'reachable': False, 'model': self.cfg['model'],
               'endpoint': self.cfg['url'], 'error': None}
        if not self.is_enabled():
            out['error'] = 'GOVOS_LLM_ENABLED is not true'
            return out
        try:
            req = urllib.request.Request(self._endpoint('/models'), method='GET')
            with urllib.request.urlopen(req, timeout=min(self.cfg['timeout'], 8)) as resp:
                out['reachable'] = 200 <= resp.getcode() < 500
        except Exception as e:                                   # noqa: BLE001
            out['error'] = type(e).__name__
        return out

    def complete(self, messages: list, *, max_tokens: int = 320) -> str:
        if not self.is_enabled():
            raise ProviderError(InfraStatus.LLM_DISABLED, 'local LLM verification is disabled')
        body = json.dumps({
            'model': self.cfg['model'], 'messages': messages,
            'temperature': 0.0, 'max_tokens': max_tokens, 'stream': False,
        }).encode('utf-8')
        req = urllib.request.Request(
            self._endpoint('/chat/completions'), data=body, method='POST',
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=self.cfg['timeout']) as resp:
                raw = json.loads(resp.read().decode('utf-8'))
        except urllib.error.URLError as e:
            reason = getattr(e, 'reason', e)
            if 'timed out' in str(reason).lower():
                raise ProviderError(InfraStatus.LLM_TIMEOUT, f'request timed out: {reason}')
            raise ProviderError(InfraStatus.LLM_UNAVAILABLE, f'server unreachable: {reason}')
        except TimeoutError as e:
            raise ProviderError(InfraStatus.LLM_TIMEOUT, f'request timed out: {e}')
        except Exception as e:                                   # noqa: BLE001
            raise ProviderError(InfraStatus.LLM_ERROR, f'{type(e).__name__}: {e}')
        try:
            return raw['choices'][0]['message']['content']
        except (KeyError, IndexError, TypeError):
            raise ProviderError(InfraStatus.LLM_INVALID_RESPONSE,
                                'response had no message content')


def get_provider(cfg: dict | None = None) -> VerificationProvider:
    """The current provider. Today: the local Qwen server. A future remote provider slots in
    here behind the same interface without touching the verifier."""
    return LocalQwenVerificationProvider(cfg)
