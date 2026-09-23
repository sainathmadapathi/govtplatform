"""Developer-only smoke test: connect to the local Qwen server, verify one known
evidence/claim pair, validate the structured JSON, print it, and exit non-zero on failure.

    GOVOS_LLM_ENABLED=true python -m tools.exam_builder.verification.test_local_llm

It depends only on the local model -- never on Tavily or the network beyond 127.0.0.1.
"""
from __future__ import annotations

import sys

from .client import get_provider
from .llm_verifier import run_llm
from .schemas import Claim, InfraStatus, VerificationDecision


def main() -> int:
    provider = get_provider()
    health = provider.health()
    print('health:', health)
    if not health['enabled']:
        print('FAIL: set GOVOS_LLM_ENABLED=true to run this test')
        return 2
    if not health['reachable']:
        print('FAIL: local LLM server not reachable at', health['endpoint'])
        return 3

    claim = Claim(
        exam_id='exam-ssc-cgl-2026', field='application_last_date', value='22 June 2026',
        cycle='2026', source_title='SSC CGL 2026 Notice',
        authority='Staff Selection Commission',
        official_name='Combined Graduate Level Examination',
        evidence_span='The last date for submission of online applications is 22 June 2026.')
    result = run_llm(claim, provider)
    print('result:', result.as_dict())

    if result.infra is not InfraStatus.OK:
        print('FAIL: infrastructure error', result.infra.value)
        return 4
    if result.decision is not VerificationDecision.SUPPORTED:
        print('FAIL: expected SUPPORTED for an explicitly supporting evidence span, got',
              result.decision.value)
        return 5
    print('OK: local Qwen verified a supporting evidence/claim pair as SUPPORTED')
    return 0


if __name__ == '__main__':
    sys.exit(main())
