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


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item):
    """Several tools/exam_builder suites record failures with `check()` into a module-level `_FAILURES`
    list that only their own `main()` reports. Under pytest that list was never read, so those tests
    could not fail. Anything a test adds to it now fails that test."""
    failures = getattr(getattr(item, 'module', None), '_FAILURES', None)
    before = len(failures) if isinstance(failures, list) else 0
    result = yield
    if isinstance(failures, list) and len(failures) > before:
        new = failures[before:]
        del failures[before:]
        pytest.fail(f'{len(new)} check(s) failed:\n' + '\n'.join('  - ' + f for f in new), pytrace=False)
    return result


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
