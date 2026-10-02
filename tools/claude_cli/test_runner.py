"""The process runner (runner.py): the only code that starts an operating-system process.

Requirement tags: [ENV] narrow environment, [SHELL] shell=False and list arguments, [STDIN] prompt on
stdin, [TIMEOUT] timeout kills the whole process tree, [CANCEL] cancellation kills it, [OUTPUT-CAP]
output limit enforced while reading, [STDERR] stderr is captured apart, [NO-REAL-CLI] automated tests can
never start the real CLI.

These tests start real child processes, but only the Python interpreter running `fake_cli.py` (the
runner refuses any other program while GOVOS_CLAUDE_TEST_MODE is set).
"""
from __future__ import annotations

import io
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
import tracemalloc
import unittest
from unittest import mock

from tools.claude_cli import runner as runner_module
from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.gateway_fixtures import (kill_pid, pid_alive, read_log, read_pid_file, wait_until,
                                               write_scenario)
from tools.claude_cli.runner import (TEST_MODE_ENV, ProcessOutcome, Runner, SubprocessRunner, build_child_env,
                                     kill_process_tree)
from tools.claude_cli.testing import FAKE_CLI_SCRIPT

SECRET_PARENT_ENV = {
    'ANTHROPIC_API_KEY': 'sk-ant-api-SECRET', 'ANTHROPIC_AUTH_TOKEN': 'ant-token-SECRET',
    'ANTHROPIC_BASE_URL': 'https://evil.example', 'OPENAI_API_KEY': 'sk-openai-SECRET',
    'TAVILY_API_KEY': 'tvly-SECRET', 'GOVOS_CLAUDE_ADMIN_TOKEN': 'admin-SECRET',
    'GOVOS_CLAUDE_ENABLED': '1', 'GOVOS_ANYTHING': 'x', 'CLAUDE_CODE_OAUTH_TOKEN': 'oauth-SECRET',
    'AWS_SECRET_ACCESS_KEY': 'aws-SECRET', 'AZURE_CLIENT_SECRET': 'az-SECRET',
    'GOOGLE_APPLICATION_CREDENTIALS': 'C:\\creds.json', 'GITHUB_TOKEN': 'ghp-SECRET',
    'DATABASE_PASSWORD': 'pw-SECRET', 'MY_APP_SECRET': 'plain-SECRET', 'SESSION_COOKIE': 'cookie-SECRET',
}

#: Variable names a spawned Python may add to its own environment (not passed by the runner).
IMPLICIT_CHILD_ENV = {'__CF_USER_TEXT_ENCODING', 'LC_CTYPE', 'PWD', 'OLDPWD', 'SHLVL', '_', '__PYVENV_LAUNCHER__',
                      'PYTHONIOENCODING', 'PYTHONUTF8', 'PYTHONHOME', 'PYTHONPATH', '__COMPAT_LAYER'}


def fake_argv(scenario: str, *cli_args: str) -> list:
    """argv that runs the fake CLI under the interpreter that is running the tests."""
    return [sys.executable, FAKE_CLI_SCRIPT, '--scenario', scenario, *cli_args]


def run_fake(scenario: str, stdin: str = 'prompt', *, timeout: float = 20.0, cap: int = 262_144, cwd: str = None,
             cancel_event=None, env=None) -> ProcessOutcome:
    return SubprocessRunner().run(fake_argv(scenario, '-p'), stdin_text=stdin, env=env or build_child_env(),
                                  cwd=cwd or os.path.dirname(scenario), timeout=timeout, max_output_bytes=cap,
                                  cancel_event=cancel_event)


# ================================================================================== child environment
class ChildEnvironmentTests(unittest.TestCase):
    def test_secrets_and_arbitrary_variables_are_not_forwarded(self):
        """[ENV] ANTHROPIC_*, OPENAI_*, TAVILY_*, GOVOS_* (incl. GOVOS_CLAUDE_ADMIN_TOKEN),
        CLAUDE_CODE_OAUTH_TOKEN, cloud credentials and arbitrary secrets never reach the child."""
        parent = dict(SECRET_PARENT_ENV, PATH='/bin', SYSTEMROOT='C:\\Windows')
        env = build_child_env(parent)
        for name in SECRET_PARENT_ENV:
            self.assertNotIn(name, env)
        blob = json.dumps(env)
        self.assertNotIn('SECRET', blob)
        self.assertNotIn('evil.example', blob)

    def test_matching_is_case_insensitive(self):
        """[ENV] A lower- or mixed-case spelling of a blocked name is blocked too (Windows variable
        names are case-insensitive)."""
        parent = {'anthropic_api_key': 'k', 'Anthropic_Auth_Token': 'k', 'govos_claude_admin_token': 'k',
                  'Openai_Api_Key': 'k', 'claude_code_oauth_token': 'k', 'Tavily_Api_Key': 'k'}
        self.assertEqual(set(build_child_env(parent)), {'NO_COLOR'})

    def test_only_what_the_cli_needs_to_start_and_find_its_login_is_forwarded(self):
        """[ENV] PATH, system / profile / temp locations, locale, proxies, CA bundles and
        CLAUDE_CONFIG_DIR are forwarded unchanged; NO_COLOR=1 is added."""
        parent = {'PATH': '/usr/bin', 'SYSTEMROOT': 'C:\\Windows', 'USERPROFILE': 'C:\\Users\\u', 'HOME': '/home/u',
                  'APPDATA': 'C:\\A', 'LOCALAPPDATA': 'C:\\L', 'TEMP': 'C:\\T', 'TMP': 'C:\\T', 'LANG': 'en_US.UTF-8',
                  'HTTPS_PROXY': 'http://proxy:3128', 'NO_PROXY': 'localhost', 'SSL_CERT_FILE': '/c.pem',
                  'NODE_EXTRA_CA_CERTS': '/n.pem', 'CLAUDE_CONFIG_DIR': '/cfg'}
        env = build_child_env(parent)
        for key, value in parent.items():
            self.assertEqual(env[key], value)
        self.assertEqual(env['NO_COLOR'], '1')
        self.assertEqual(set(env), set(parent) | {'NO_COLOR'})

    def test_an_unlisted_name_is_dropped_even_if_it_looks_harmless(self):
        """[ENV] The rule is an allow-list: PYTHONPATH, EDITOR, NODE_OPTIONS, LD_PRELOAD and friends are
        not forwarded."""
        parent = {n: 'x' for n in ('PYTHONPATH', 'PYTHONSTARTUP', 'EDITOR', 'NODE_OPTIONS', 'LD_PRELOAD', 'LD_LIBRARY_PATH',
                                   'DYLD_INSERT_LIBRARIES', 'CLAUDE_CODE_USE_BEDROCK', 'CLAUDE_CODE_USE_VERTEX',
                                   'CLAUDE_CODE_OAUTH_TOKEN', 'CLAUDE_API_KEY', 'FOO')}
        self.assertEqual(set(build_child_env(parent)), {'NO_COLOR'})

    def test_the_allow_list_itself_holds_no_credential_variable(self):
        """[ENV] No allow-listed name looks like a key/token/secret/password, and none starts with a
        never-forward prefix (so the prefix rule and the allow-list can not contradict each other)."""
        allow = runner_module._ENV_ALLOW_UPPER
        self.assertIn('PATH', allow)
        self.assertNotIn('CLAUDE_CODE_OAUTH_TOKEN', allow)
        for name in allow:
            self.assertIsNone(re.search(r'KEY|TOKEN|SECRET|PASSWORD|CREDENTIAL|AUTH', name), name)
            self.assertFalse(name.startswith(runner_module._ENV_NEVER_PREFIXES), name)
        for prefix in ('ANTHROPIC_', 'OPENAI_', 'GOVOS_'):
            self.assertIn(prefix, runner_module._ENV_NEVER_PREFIXES)

    def test_the_parent_environment_is_not_modified(self):
        """[ENV] build_child_env reads, it does not mutate."""
        parent = {'PATH': '/bin', 'ANTHROPIC_API_KEY': 'k'}
        before = dict(parent)
        build_child_env(parent)
        self.assertEqual(parent, before)

    def test_the_default_parent_is_the_live_process_environment(self):
        """[ENV] With no argument the live os.environ is read at call time."""
        with mock.patch.dict(os.environ, dict(SECRET_PARENT_ENV, CLAUDE_CONFIG_DIR='/live-config')):
            env = build_child_env()
        self.assertEqual(env.get('CLAUDE_CONFIG_DIR'), '/live-config')
        self.assertFalse(set(SECRET_PARENT_ENV) & set(env))

    def test_a_real_child_sees_only_the_narrow_environment(self):
        """[ENV] End to end through a real process: with every secret set in the parent, the names in
        the child's own environment are the allow-list plus NO_COLOR, and no secret name is among them."""
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, SECRET_PARENT_ENV):
            log = os.path.join(tmp, 'log.jsonl')
            out = run_fake(write_scenario(tmp, log=log, output={}))
            self.assertEqual(out.returncode, 0, out.stderr)
            seen = {k.upper() for k in read_log(log)[0]['env_keys']}
        self.assertFalse(seen & {k.upper() for k in SECRET_PARENT_ENV})
        self.assertIn('NO_COLOR', seen)
        unexpected = seen - runner_module._ENV_ALLOW_UPPER - {'NO_COLOR'} - IMPLICIT_CHILD_ENV
        self.assertEqual(unexpected, set())


# ============================================================================== shell, argv and stdin
class FakePopen:
    """Stands in for subprocess.Popen so the call's shape can be inspected without a process."""

    instances: list = []
    stdout_bytes = b'\xff{"ok": true}'

    class _Sink(io.BytesIO):
        def close(self):
            self.data = self.getvalue()
            super().close()

    def __init__(self, args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.pid, self.returncode = 4242, 0
        self.stdin = self._Sink()
        self.stdout = io.BytesIO(self.stdout_bytes)
        self.stderr = io.BytesIO(b'')
        FakePopen.instances.append(self)

    def poll(self):
        return 0

    def wait(self, timeout=None):
        return 0

    def kill(self):
        pass


class ProcessShapeTests(unittest.TestCase):
    def setUp(self):
        FakePopen.instances = []

    def _run(self, argv=None, stdin='STDIN-TEXT é', env=None, cwd='X'):
        argv = argv or [sys.executable, '-p', 'a b', '--x', '$(touch /tmp/pwn); `id` & | > <']
        with mock.patch.object(runner_module.subprocess, 'Popen', FakePopen):
            out = SubprocessRunner().run(argv, stdin_text=stdin, env=env or {'PATH': 'p'}, cwd=cwd, timeout=5,
                                         max_output_bytes=1000)
        return out, FakePopen.instances[0]

    def test_popen_is_called_with_a_list_and_shell_false(self):
        """[SHELL] The command is a list handed to Popen with shell=False, so nothing in an argument is
        ever shell syntax."""
        argv = [sys.executable, '-p', '$(touch /tmp/pwn)', '`id`', '& calc', '| more', '> out', '"quoted"']
        _, proc = self._run(argv)
        self.assertIsInstance(proc.args, list)
        self.assertEqual(proc.args, argv)
        self.assertIs(proc.kwargs['shell'], False)

    def test_stdin_stdout_stderr_are_pipes_and_cwd_and_env_are_exactly_those_given(self):
        """[SHELL][ENV] Pipes for all three streams; the child gets the given cwd and exactly the given
        environment mapping (a copy), nothing merged from the parent."""
        env = {'PATH': 'only-this'}
        _, proc = self._run(env=env, cwd='C:\\work')
        self.assertEqual(proc.kwargs['stdin'], subprocess.PIPE)
        self.assertEqual(proc.kwargs['stdout'], subprocess.PIPE)
        self.assertEqual(proc.kwargs['stderr'], subprocess.PIPE)
        self.assertEqual(proc.kwargs['cwd'], 'C:\\work')
        self.assertEqual(proc.kwargs['env'], env)
        self.assertIsNot(proc.kwargs['env'], env)

    def test_the_child_leads_its_own_process_group_so_the_tree_can_be_killed(self):
        """[TIMEOUT] The child starts in a new process group / session (taskkill /T or killpg then reaches
        everything it spawns)."""
        _, proc = self._run()
        if os.name == 'nt':
            self.assertTrue(proc.kwargs['creationflags'] & subprocess.CREATE_NEW_PROCESS_GROUP)
            self.assertTrue(proc.kwargs['creationflags'] & subprocess.CREATE_NO_WINDOW)
        else:
            self.assertIs(proc.kwargs['start_new_session'], True)

    def test_the_prompt_goes_to_stdin_as_utf8_and_is_not_in_the_arguments(self):
        """[STDIN] stdin_text is written to the child's stdin (UTF-8) and the stream is closed; it is not
        part of the argument list."""
        out, proc = self._run(stdin='STDIN-TEXT é 日本語')
        self.assertEqual(proc.stdin.data, 'STDIN-TEXT é 日本語'.encode('utf-8'))
        self.assertTrue(proc.stdin.closed)
        self.assertFalse(any('STDIN-TEXT' in a for a in proc.args))

    def test_undecodable_output_is_replaced_not_raised(self):
        """[STDERR] Bytes that are not UTF-8 decode with replacement characters; the runner never
        raises on child output."""
        out, _ = self._run()
        self.assertEqual(out.returncode, 0)
        self.assertIn('{"ok": true}', out.stdout)
        self.assertIn('\ufffd', out.stdout)
        self.assertEqual(out.stderr, '')

    def test_runner_interface_is_abstract(self):
        """[SHELL] The base Runner can not be used to run anything."""
        with self.assertRaises(NotImplementedError):
            Runner().run([], stdin_text='', env={}, cwd='', timeout=1, max_output_bytes=1)


# ====================================================================== no real CLI under test
class NoRealCliTests(unittest.TestCase):
    def test_test_mode_is_on(self):
        """[NO-REAL-CLI] Importing the test support module marks the process as under test."""
        self.assertEqual(os.environ.get(TEST_MODE_ENV), '1')

    def test_any_program_but_the_interpreter_is_refused_without_starting_it(self):
        """[NO-REAL-CLI] Under test the runner refuses `claude`, `claude.exe`, cmd, powershell, node ...:
        no Popen call is made at all and the outcome is start_error='denied'."""
        for program in ('claude', 'claude.exe', 'C:\\Users\\x\\AppData\\Roaming\\npm\\claude.cmd', 'cmd.exe',
                        'powershell', 'node', '/usr/bin/claude', ''):
            with self.subTest(program=program), mock.patch.object(runner_module.subprocess, 'Popen') as popen:
                out = SubprocessRunner().run([program, '-p'], stdin_text='x', env={}, cwd=os.getcwd(), timeout=5,
                                             max_output_bytes=100)
                popen.assert_not_called()
                self.assertEqual(out.start_error, 'denied')
                self.assertIsNone(out.returncode)

    def test_the_interpreter_is_allowed_only_when_it_is_exactly_this_one(self):
        """[NO-REAL-CLI] sys.executable is the one permitted program."""
        self.assertFalse(runner_module._refused_under_test([sys.executable, '--version']))
        self.assertTrue(runner_module._refused_under_test([os.path.join(tempfile.gettempdir(), 'python.exe')]))

    def test_start_failures_are_reported_as_categories_not_exceptions(self):
        """[NO-REAL-CLI] With the guard lifted, a program that does not exist is 'not_found' and a
        directory is 'denied' / 'oserror' (never an exception); nothing real is started."""
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {TEST_MODE_ENV: '0'}):
            missing = SubprocessRunner().run([os.path.join(tmp, 'no_such_program')], stdin_text='', env={}, cwd=tmp,
                                             timeout=5, max_output_bytes=100)
            self.assertEqual(missing.start_error, 'not_found')
            directory = SubprocessRunner().run([tmp], stdin_text='', env={}, cwd=tmp, timeout=5, max_output_bytes=100)
            self.assertIn(directory.start_error, ('denied', 'oserror'))


# ========================================================================= real processes: the basics
class RealProcessTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_a_normal_call_returns_stdout_and_exit_code_zero(self):
        """[STDERR] A clean exit: returncode 0, the envelope on stdout, no flag set."""
        out = run_fake(write_scenario(self.tmp, output={'a': 1}))
        self.assertEqual(out.returncode, 0)
        self.assertEqual(json.loads(out.stdout)['structured_output'], {'a': 1})
        for flag in (out.timed_out, out.cancelled, out.output_truncated):
            self.assertFalse(flag)
        self.assertEqual(out.start_error, '')

    def test_stdout_and_stderr_are_captured_separately(self):
        """[STDERR] A failing child's stderr is in `stderr` only; stdout stays free of it."""
        out = run_fake(write_scenario(self.tmp, mode='stderr_secret'))
        self.assertEqual(out.returncode, 1)
        self.assertIn('SECRET-VALUE', out.stderr)
        self.assertNotIn('SECRET-VALUE', out.stdout)

    def test_the_prompt_reaches_the_child_on_stdin_intact_even_when_large(self):
        """[STDIN] A 600 KB prompt with newlines, quotes, shell metacharacters and non-ASCII text
        arrives byte for byte on the child's stdin; none of it is in the child's arguments."""
        log = os.path.join(self.tmp, 'log.jsonl')
        prompt = ('line "one" \'q\' $(x) `y` & | > < %PATH% é 日本語 😀\n' * 11000) + 'THE-END'
        self.assertGreater(len(prompt.encode('utf-8')), 600_000)
        out = run_fake(write_scenario(self.tmp, log=log, output={}), prompt)
        self.assertEqual(out.returncode, 0)
        entry = read_log(log)[0]
        self.assertEqual(entry['stdin'], prompt)
        self.assertNotIn('THE-END', json.dumps(entry['argv']))

    def test_the_child_runs_in_the_given_working_directory(self):
        """[SHELL] cwd is honoured."""
        work = os.path.join(self.tmp, 'work')
        os.makedirs(work)
        log = os.path.join(self.tmp, 'log.jsonl')
        run_fake(write_scenario(self.tmp, log=log, output={}), cwd=work)
        self.assertEqual(os.path.realpath(read_log(log)[0]['cwd']), os.path.realpath(work))

    def test_shell_metacharacters_in_arguments_are_inert(self):
        """[SHELL] Arguments full of shell syntax are delivered to the child as plain strings and run
        nothing: no file is created by `&`, `|`, `>`, backticks or $( )."""
        log = os.path.join(self.tmp, 'log.jsonl')
        pwned = os.path.join(self.tmp, 'pwned.txt')
        hostile = [f'; echo PWNED > "{pwned}" #', f'& echo PWNED > "{pwned}"', f'| echo PWNED > "{pwned}"',
                   f'$(echo PWNED > "{pwned}")', f'`echo PWNED > "{pwned}"`', f'> "{pwned}"', '%COMSPEC%',
                   '--dangerously-skip-permissions', '--allowedTools Bash']
        argv = fake_argv(write_scenario(self.tmp, log=log, output={}), '-p', *hostile)
        out = SubprocessRunner().run(argv, stdin_text='x', env=build_child_env(), cwd=self.tmp, timeout=20,
                                     max_output_bytes=100_000)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(os.path.exists(pwned))
        self.assertEqual(read_log(log)[0]['argv'][1:], hostile)


# ====================================================================== real processes: kill behaviour
class KillTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)
        self.log = os.path.join(self.tmp, 'log.jsonl')
        self.child_pid_file = os.path.join(self.tmp, 'child.pid')

    def _guard(self, pid):
        self.addCleanup(lambda: kill_pid(pid) if pid_alive(pid) else None)

    def _direct_pid(self) -> int:
        self.assertTrue(wait_until(lambda: bool(read_log(self.log)), 15), 'the fake CLI never started')
        pid = read_log(self.log)[0]['pid']
        self._guard(pid)
        return pid

    def _grandchild_pid(self) -> int:
        self.assertTrue(wait_until(lambda: read_pid_file(self.child_pid_file) is not None, 15),
                        'the fake CLI never spawned its child')
        pid = read_pid_file(self.child_pid_file)
        self._guard(pid)
        return pid

    def test_a_hanging_process_is_killed_at_the_timeout(self):
        """[TIMEOUT] A child that never answers is killed when the timeout passes: timed_out is set,
        the call returns promptly after the deadline, and the process is gone."""
        scenario = write_scenario(self.tmp, mode='timeout', log=self.log)
        started = time.monotonic()
        out = run_fake(scenario, timeout=3.0)
        elapsed = time.monotonic() - started
        self.assertTrue(out.timed_out)
        self.assertFalse(out.cancelled)
        self.assertLess(elapsed, 25)
        pid = self._direct_pid()
        self.assertTrue(wait_until(lambda: not pid_alive(pid), 10), 'the timed-out process survived')

    def test_the_whole_process_tree_is_killed_on_timeout(self):
        """[TIMEOUT] The CLI's own child (a grandchild of the runner, sleeping for ten minutes) is dead
        after the timeout, not only the direct child."""
        scenario = write_scenario(self.tmp, mode='tree', log=self.log, child_pid_file=self.child_pid_file)
        out = run_fake(scenario, timeout=4.0)
        self.assertTrue(out.timed_out)
        grandchild, direct = self._grandchild_pid(), self._direct_pid()
        self.assertTrue(wait_until(lambda: not pid_alive(direct), 10), 'the direct child survived')
        self.assertTrue(wait_until(lambda: not pid_alive(grandchild), 10), 'the grandchild survived the timeout')

    def test_cancellation_kills_the_whole_tree_and_is_reported(self):
        """[CANCEL] Setting the cancel event stops the call quickly: cancelled is set, timed_out is not,
        and both the child and its own child are dead."""
        scenario = write_scenario(self.tmp, mode='tree', log=self.log, child_pid_file=self.child_pid_file)
        cancel = threading.Event()

        def cancel_when_running():
            wait_until(lambda: read_pid_file(self.child_pid_file) is not None, 20)
            cancel.set()

        threading.Thread(target=cancel_when_running, daemon=True).start()
        started = time.monotonic()
        out = run_fake(scenario, timeout=120.0, cancel_event=cancel)
        self.assertTrue(out.cancelled)
        self.assertFalse(out.timed_out)
        self.assertLess(time.monotonic() - started, 60)
        grandchild, direct = self._grandchild_pid(), self._direct_pid()
        self.assertTrue(wait_until(lambda: not pid_alive(direct), 10))
        self.assertTrue(wait_until(lambda: not pid_alive(grandchild), 10), 'the grandchild survived the cancel')

    def test_an_already_set_cancel_event_stops_the_call_at_once(self):
        """[CANCEL] A cancel event that is set before the call kills the child on the first poll."""
        scenario = write_scenario(self.tmp, mode='timeout', log=self.log)
        cancel = threading.Event()
        cancel.set()
        started = time.monotonic()
        out = run_fake(scenario, timeout=120.0, cancel_event=cancel)
        self.assertTrue(out.cancelled)
        self.assertLess(time.monotonic() - started, 30)
        if read_log(self.log):
            pid = read_log(self.log)[0]['pid']
            self._guard(pid)
            self.assertTrue(wait_until(lambda: not pid_alive(pid), 10))

    def test_kill_process_tree_tolerates_a_process_that_is_already_gone(self):
        """[TIMEOUT] Killing a finished process raises nothing."""
        proc = subprocess.Popen([sys.executable, '-c', 'pass'])
        proc.wait()
        kill_process_tree(proc)


# ====================================================================== real processes: output limits
class OutputLimitTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = self._tmp.name
        self.addCleanup(self._tmp.cleanup)

    def test_oversize_stdout_is_cut_at_the_cap_and_the_child_is_killed(self):
        """[OUTPUT-CAP] 8 MB of output against a 64 KiB cap: output_truncated is set, no more than the
        cap is kept, and the call ends promptly instead of waiting for the child."""
        cap = 65_536
        started = time.monotonic()
        out = run_fake(write_scenario(self.tmp, mode='huge', huge_bytes=8_000_000), timeout=60.0, cap=cap)
        self.assertTrue(out.output_truncated)
        self.assertLessEqual(len(out.stdout.encode('utf-8')), cap)
        self.assertFalse(out.timed_out)
        self.assertLess(time.monotonic() - started, 40)

    def test_memory_stays_bounded_while_a_child_floods_stdout(self):
        """[OUTPUT-CAP] Peak Python memory while reading an 8 MB flood against a 64 KiB cap stays far
        below the flood's size (output is bounded while it is read, not after)."""
        tracemalloc.start()
        try:
            out = run_fake(write_scenario(self.tmp, mode='huge', huge_bytes=8_000_000), timeout=60.0, cap=65_536)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        self.assertTrue(out.output_truncated)
        self.assertLess(peak, 2_000_000, f'peak traced memory {peak} bytes')

    def test_output_exactly_under_the_cap_is_not_truncated(self):
        """[OUTPUT-CAP] A reply within the cap is returned whole."""
        out = run_fake(write_scenario(self.tmp, output={'a': 'b'}), cap=262_144)
        self.assertFalse(out.output_truncated)
        self.assertEqual(out.returncode, 0)

    def test_a_noisy_stderr_does_not_stall_a_child_that_then_answers(self):
        """[STDERR] A child that writes 1 MB to stderr and then returns a valid reply is not blocked on
        a full pipe: it finishes normally, well before the timeout."""
        started = time.monotonic()
        out = run_fake(write_scenario(self.tmp, mode='stderr_flood', flood_bytes=1_000_000, output={'a': 1}),
                       timeout=30.0)
        self.assertFalse(out.timed_out, 'a flooded stderr pipe stalled the child until the timeout')
        self.assertEqual(out.returncode, 0)
        self.assertEqual(json.loads(out.stdout)['structured_output'], {'a': 1})
        self.assertLess(time.monotonic() - started, 25)
        self.assertLessEqual(len(out.stderr), 65_536)

    def test_stderr_capture_is_capped(self):
        """[STDERR] Captured stderr never exceeds 64 KiB however much a child writes."""
        out = run_fake(write_scenario(self.tmp, mode='stderr_flood', flood_bytes=300_000, output={}), timeout=30.0)
        self.assertLessEqual(len(out.stderr), 65_536)


if __name__ == '__main__':
    unittest.main()
