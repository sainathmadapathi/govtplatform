"""A tiny fingerprint cache so identical (claim, evidence, source, verifier version) is not
re-verified. Successful LLM results are cached; infrastructure failures are never cached, so a
transient outage does not stick. New evidence or a new verifier version changes the
fingerprint and forces re-verification."""
from __future__ import annotations

from .schemas import InfraStatus, VerificationResult


class VerificationCache:
    def __init__(self) -> None:
        self._store: dict = {}

    def get(self, fingerprint: str):
        return self._store.get(fingerprint)

    def put(self, fingerprint: str, result: VerificationResult) -> None:
        # Only cache a real decision. An infrastructure failure must not be remembered as a
        # verdict -- the next run should try again.
        if result.infra is InfraStatus.OK:
            self._store[fingerprint] = result

    def clear(self) -> None:
        self._store.clear()
