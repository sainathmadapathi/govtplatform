"""pytest configuration shared by every test in the repository.

No automated test may start the real Claude CLI, whatever the machine's configuration says:

  * the test-mode flag below makes `SubprocessRunner` refuse every program except the Python
    interpreter that is running the tests (which is what hosts the fake CLI script);
  * every test starts with a disabled, scripted gateway installed as the process-wide one, so code
    that reaches Claude through `get_gateway()` reads "disabled" unless the test installs its own
    fake (`tools.claude_cli.testing.use_gateway`).
"""
import os

os.environ['GOVOS_CLAUDE_TEST_MODE'] = '1'

import pytest


@pytest.fixture(autouse=True)
def _no_real_claude():
    from tools.claude_cli import client
    from tools.claude_cli.testing import FakeClaude

    previous = client._DEFAULT
    client.set_gateway(FakeClaude(enabled=False))
    try:
        yield
    finally:
        client.set_gateway(previous)
