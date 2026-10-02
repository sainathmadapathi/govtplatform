"""Configuration and readiness (config.py, and the gateway's health / CLI-resolution paths).

Requirement tags: [CONFIG] load_config bounds and the absence of any API-key setting, [HEALTH]
readiness states and what health() may say, [RESOLVE] where the executable may come from.
No test here starts the real Claude CLI: probes are scripted, or answered by `fake_cli.py`.
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
import tempfile
import unittest
from unittest import mock

from tools.claude_cli import config as config_module
from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.client import REQUIRED_FLAGS, ClaudeGateway
from tools.claude_cli.config import (DEFAULT_CONCURRENCY, DEFAULT_MAX_OUTPUT_BYTES, DEFAULT_TIMEOUT_SECONDS,
                                     ENV_ADMIN_TOKEN, ENV_CLI_PATH, ENV_CONCURRENCY, ENV_ENABLED,
                                     ENV_MAX_OUTPUT, ENV_MODEL, ENV_TIMEOUT, ENV_WORKDIR, ClaudeConfig,
                                     load_config)
from tools.claude_cli.gateway_fixtures import (OP, REPO_ROOT, VALID_OUTPUTS, RecordingRunner, payload_for,
                                               write_scenario)
from tools.claude_cli.runner import ProcessOutcome, Runner
from tools.claude_cli.schemas import SAFE_MESSAGES, InfraStatus
from tools.claude_cli.testing import FAKE_CLI_SCRIPT, HELP_TEXT, FakeClaude, ScriptedRunner, fake_cli_config

VERIFY = OP.VERIFY_CLAIM


def help_without(*flags: str) -> str:
    return '\n'.join(line for line in HELP_TEXT.splitlines() if not set(flags) & set(line.split()))


def gateway(cli_path: str, *replies, enabled: bool = True, **runner_kw) -> tuple:
    runner = RecordingRunner(None, *(replies or (VALID_OUTPUTS[VERIFY],)), **runner_kw)
    return ClaudeGateway(ClaudeConfig(enabled=enabled, cli_path=cli_path, slot_wait_seconds=1.0), runner=runner), runner


# ===================================================================================== load_config
class LoadConfigTests(unittest.TestCase):
    def test_defaults_are_disabled_and_conservative(self):
        """[CONFIG] With an empty environment: disabled, no explicit CLI path, 120 s, 2 slots, 256 KiB
        of output, no model, no argument prefix."""
        cfg = load_config({})
        self.assertFalse(cfg.enabled)
        self.assertEqual((cfg.cli_path, cfg.model, cfg.workdir, cfg.cli_args_prefix), ('', '', '', ()))
        self.assertEqual(cfg.timeout_seconds, DEFAULT_TIMEOUT_SECONDS)
        self.assertEqual(cfg.max_concurrency, DEFAULT_CONCURRENCY)
        self.assertEqual(cfg.max_output_bytes, DEFAULT_MAX_OUTPUT_BYTES)
        self.assertEqual(cfg, ClaudeConfig())

    def test_enabled_accepts_only_explicit_truthy_words(self):
        """[CONFIG] 1/true/yes/on (any case, padded) enable; everything else, including 0, empty,
        'enabled' and 'y', leaves the integration off."""
        for text in ('1', 'true', 'TRUE', ' Yes ', 'on', 'On'):
            with self.subTest(on=text):
                self.assertTrue(load_config({ENV_ENABLED: text}).enabled)
        for text in ('', ' ', '0', 'false', 'no', 'off', 'enabled', 'y', 'tru', '2'):
            with self.subTest(off=text):
                self.assertFalse(load_config({ENV_ENABLED: text}).enabled)

    def test_timeout_is_clamped(self):
        """[CONFIG] Timeout below 10 s becomes 10, above 900 s becomes 900; garbage falls back to the
        default; NaN/infinity stay inside the bounds."""
        self.assertEqual(load_config({ENV_TIMEOUT: '1'}).timeout_seconds, 10.0)
        self.assertEqual(load_config({ENV_TIMEOUT: '-50'}).timeout_seconds, 10.0)
        self.assertEqual(load_config({ENV_TIMEOUT: '90'}).timeout_seconds, 90.0)
        self.assertEqual(load_config({ENV_TIMEOUT: '99999'}).timeout_seconds, 900.0)
        for junk in ('abc', '', '12s', '1,5'):
            self.assertEqual(load_config({ENV_TIMEOUT: junk}).timeout_seconds, DEFAULT_TIMEOUT_SECONDS, junk)
        for odd in ('nan', 'inf', '-inf', 'infinity'):
            self.assertTrue(10.0 <= load_config({ENV_TIMEOUT: odd}).timeout_seconds <= 900.0, odd)

    def test_concurrency_is_clamped_to_one_through_four(self):
        """[CONFIG] max concurrency is an int in [1, 4] whatever is configured."""
        self.assertEqual(load_config({ENV_CONCURRENCY: '0'}).max_concurrency, 1)
        self.assertEqual(load_config({ENV_CONCURRENCY: '-3'}).max_concurrency, 1)
        self.assertEqual(load_config({ENV_CONCURRENCY: '3'}).max_concurrency, 3)
        self.assertEqual(load_config({ENV_CONCURRENCY: '3.9'}).max_concurrency, 3)
        self.assertEqual(load_config({ENV_CONCURRENCY: '64'}).max_concurrency, 4)
        self.assertEqual(load_config({ENV_CONCURRENCY: 'many'}).max_concurrency, DEFAULT_CONCURRENCY)
        for odd in ('nan', 'inf', '-inf'):
            value = load_config({ENV_CONCURRENCY: odd}).max_concurrency
            self.assertIsInstance(value, int)
            self.assertTrue(1 <= value <= 4, odd)

    def test_max_output_is_clamped_between_4_kib_and_4_mib(self):
        """[CONFIG] max output bytes is an int in [4096, 4194304]."""
        self.assertEqual(load_config({ENV_MAX_OUTPUT: '1'}).max_output_bytes, 4096)
        self.assertEqual(load_config({ENV_MAX_OUTPUT: '100000'}).max_output_bytes, 100000)
        self.assertEqual(load_config({ENV_MAX_OUTPUT: '999999999999'}).max_output_bytes, 4_194_304)
        self.assertEqual(load_config({ENV_MAX_OUTPUT: 'big'}).max_output_bytes, DEFAULT_MAX_OUTPUT_BYTES)
        for odd in ('nan', 'inf', '-inf'):
            value = load_config({ENV_MAX_OUTPUT: odd}).max_output_bytes
            self.assertIsInstance(value, int)
            self.assertTrue(4096 <= value <= 4_194_304, odd)

    def test_cli_path_model_and_workdir_are_read_and_stripped(self):
        """[CONFIG][RESOLVE] GOVOS_CLAUDE_CLI_PATH, _MODEL and _JOB_WORKDIR are read from the
        environment (whitespace trimmed)."""
        cfg = load_config({ENV_CLI_PATH: '  /opt/claude/claude  ', ENV_MODEL: ' sonnet ', ENV_WORKDIR: ' /tmp/w '})
        self.assertEqual((cfg.cli_path, cfg.model, cfg.workdir), ('/opt/claude/claude', 'sonnet', '/tmp/w'))

    def test_the_environment_is_read_on_every_call_never_cached(self):
        """[CONFIG] load_config() reflects os.environ at the moment of the call."""
        with mock.patch.dict(os.environ, {ENV_ENABLED: '1'}):
            self.assertTrue(load_config().enabled)
        with mock.patch.dict(os.environ, {ENV_ENABLED: '0'}):
            self.assertFalse(load_config().enabled)

    def test_the_config_object_is_immutable(self):
        """[CONFIG] ClaudeConfig is frozen: nothing can flip a setting after the fact."""
        cfg = load_config({ENV_ENABLED: '1'})
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cfg.enabled = False                                # type: ignore[misc]
        with self.assertRaises(dataclasses.FrozenInstanceError):
            cfg.cli_path = 'x'                                 # type: ignore[misc]

    def test_the_default_workdir_is_outside_the_repository(self):
        """[CONFIG] With no workdir configured, calls run in a temp-directory subfolder, never in the
        repository (where a CLAUDE.md would be discovered); an explicit workdir wins."""
        wd = os.path.realpath(ClaudeConfig().effective_workdir)
        repo = os.path.realpath(REPO_ROOT)
        self.assertNotEqual(os.path.commonpath([wd, repo]), repo)
        self.assertTrue(wd.startswith(os.path.realpath(tempfile.gettempdir())))
        self.assertEqual(ClaudeConfig(workdir='/somewhere').effective_workdir, '/somewhere')


class NoApiKeyTests(unittest.TestCase):
    def test_no_config_field_is_a_key_or_credential(self):
        """[CONFIG] ClaudeConfig has no field that could hold an API key, token, secret or password
        (Claude is reached only through the CLI's own account login)."""
        for field in dataclasses.fields(ClaudeConfig):
            for word in ('key', 'token', 'secret', 'password', 'credential', 'auth', 'bearer'):
                self.assertNotIn(word, field.name.lower(), field.name)

    def test_no_environment_variable_name_is_a_model_api_key(self):
        """[CONFIG] Of the environment names this package defines, none mentions KEY or API; the only
        TOKEN is the admin-endpoint guard token, which never reaches the model or the CLI."""
        names = {k: v for k, v in vars(config_module).items() if k.startswith('ENV_')}
        self.assertTrue(names)
        for const, env_name in names.items():
            self.assertNotIn('KEY', env_name, const)
            self.assertNotIn('API', env_name, const)
            self.assertTrue(env_name.startswith('GOVOS_CLAUDE_'), env_name)
            if 'TOKEN' in env_name:
                self.assertEqual(const, 'ENV_ADMIN_TOKEN')
                self.assertEqual(env_name, ENV_ADMIN_TOKEN)

    def test_api_key_variables_in_the_environment_change_nothing(self):
        """[CONFIG] Setting ANTHROPIC_API_KEY / OPENAI_API_KEY / TAVILY_API_KEY / an admin token does
        not alter the loaded configuration."""
        env = {'ANTHROPIC_API_KEY': 'sk-ant-xxx', 'OPENAI_API_KEY': 'sk-xxx', 'TAVILY_API_KEY': 'tvly-xxx',
               'ANTHROPIC_AUTH_TOKEN': 'tok', ENV_ADMIN_TOKEN: 'admin-secret'}
        self.assertEqual(load_config(env), load_config({}))
        self.assertNotIn('admin-secret', repr(load_config(env)))

    def test_the_cli_argument_prefix_has_no_environment_or_request_input(self):
        """[CONFIG][RESOLVE] cli_args_prefix (which exists so tests can run a script) is never read
        from the environment."""
        env = {name: '--dangerously-skip-permissions' for name in
               ('GOVOS_CLAUDE_ARGS', 'GOVOS_CLAUDE_CLI_ARGS', 'GOVOS_CLAUDE_FLAGS', 'GOVOS_CLAUDE_ARGS_PREFIX')}
        self.assertEqual(load_config(env).cli_args_prefix, ())


# ===================================================================================== readiness
class DisabledTests(unittest.TestCase):
    def test_disabled_integration_starts_no_process_and_says_so(self):
        """[HEALTH] CLAUDE_DISABLED: run() answers with that state, health() says disabled, and not one
        process (not even --help) was started."""
        gw, runner = gateway(sys.executable, enabled=False)
        res = gw.run(VERIFY, payload_for(VERIFY))
        self.assertEqual(res.status, InfraStatus.CLAUDE_DISABLED)
        self.assertIsNone(res.output)
        self.assertFalse(res.ok)
        self.assertEqual(res.message, SAFE_MESSAGES[InfraStatus.CLAUDE_DISABLED])
        health = gw.health()
        self.assertEqual(health['status'], 'CLAUDE_DISABLED')
        self.assertFalse(health['enabled'])
        self.assertFalse(health['ready'])
        self.assertEqual(runner.calls, [])

    def test_disabled_wins_over_every_other_check(self):
        """[HEALTH] Even a missing CLI is reported as disabled while the switch is off, and still no
        process runs."""
        gw, runner = gateway(os.path.join(tempfile.gettempdir(), '__no_such_claude__'), enabled=False)
        self.assertEqual(gw.run(VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_DISABLED)
        self.assertEqual(gw.health()['status'], 'CLAUDE_DISABLED')
        self.assertEqual(runner.calls, [])

    def test_every_operation_is_refused_when_disabled(self):
        """[HEALTH] No operation runs while disabled."""
        gw, runner = gateway(sys.executable, enabled=False)
        for op in OP:
            self.assertEqual(gw.run(op, payload_for(op)).status, InfraStatus.CLAUDE_DISABLED, op)
        self.assertEqual(runner.calls, [])


class NotInstalledTests(unittest.TestCase):
    def test_missing_explicit_path_is_cli_not_installed(self):
        """[HEALTH] CLAUDE_CLI_NOT_INSTALLED when the configured file does not exist; no process runs."""
        missing = os.path.join(tempfile.gettempdir(), '__no_such_claude__.exe')
        gw, runner = gateway(missing)
        res = gw.run(VERIFY, payload_for(VERIFY))
        self.assertEqual(res.status, InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
        self.assertFalse(res.cli_available)
        self.assertEqual(runner.calls, [])
        health = gw.health()
        self.assertEqual(health['status'], 'CLAUDE_CLI_NOT_INSTALLED')
        self.assertFalse(health['installed'])
        self.assertFalse(health['ready'])

    def test_a_directory_is_not_an_executable(self):
        """[HEALTH] A configured path that is a directory counts as not installed."""
        with tempfile.TemporaryDirectory() as tmp:
            gw, runner = gateway(tmp)
            self.assertEqual(gw.run(VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
            self.assertEqual(runner.calls, [])

    def test_nothing_on_path_is_cli_not_installed(self):
        """[HEALTH][RESOLVE] With no explicit path the CLI is looked up on PATH; an empty PATH finds
        none."""
        with tempfile.TemporaryDirectory() as empty, mock.patch.dict(os.environ, {'PATH': empty}):
            gw, runner = gateway('')
            self.assertEqual(gw.run(VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
            self.assertEqual(gw.health()['status'], 'CLAUDE_CLI_NOT_INSTALLED')
            self.assertEqual(runner.calls, [])

    def test_fake_gateway_not_installed(self):
        """[HEALTH] The scripted test double reports the same state through the same code path."""
        gw = FakeClaude(fail=InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
        self.assertEqual(gw.run(VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_CLI_NOT_INSTALLED)
        self.assertEqual(gw.calls, 0)


class NotAuthenticatedTests(unittest.TestCase):
    def test_signed_out_cli_is_not_authenticated_and_makes_no_model_call(self):
        """[HEALTH] CLAUDE_CLI_NOT_AUTHENTICATED when `auth status` says not logged in; the model call
        is never made; health shows authenticated False and not ready."""
        gw = FakeClaude(fail=InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED)
        res = gw.run(VERIFY, payload_for(VERIFY))
        self.assertEqual(res.status, InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED)
        self.assertEqual(gw.calls, 0)
        self.assertFalse(res.status.retryable)
        health = gw.health()
        self.assertEqual(health['status'], 'CLAUDE_CLI_NOT_AUTHENTICATED')
        self.assertIs(health['authenticated'], False)
        self.assertFalse(health['ready'])

    def test_unknown_auth_state_is_not_treated_as_signed_out(self):
        """[HEALTH] If `auth status` cannot be read the gateway proceeds (authenticated is None, ready
        True) and lets the real call decide, rather than refusing on a guess."""
        class OddAuth(ScriptedRunner):
            def run(self, argv, **kw):
                if 'auth' in argv:
                    return ProcessOutcome(returncode=0, stdout='<<not json>>')
                return super().run(argv, **kw)

        gw = ClaudeGateway(ClaudeConfig(enabled=True, cli_path=sys.executable), runner=OddAuth((VALID_OUTPUTS[VERIFY],)))
        health = gw.health()
        self.assertIsNone(health['authenticated'])
        self.assertTrue(health['ready'])
        self.assertTrue(gw.run(VERIFY, payload_for(VERIFY)).ok)

    def test_auth_state_is_cached_briefly_and_forgettable(self):
        """[HEALTH] `auth status` is probed once per minute (10 s while signed out) and again after
        forget_auth()."""
        clock = [1000.0]

        def probes(runner):
            return runner.quick.count('auth status')

        for authenticated, ttl in ((True, 60.0), (False, 10.0)):
            with self.subTest(authenticated=authenticated):
                scripted = ScriptedRunner((), authenticated=authenticated)
                gw = ClaudeGateway(ClaudeConfig(enabled=True, cli_path=sys.executable), runner=scripted,
                                   clock=lambda: clock[0])
                gw.health()
                gw.health()
                self.assertEqual(probes(scripted), 1)
                clock[0] += ttl - 1
                gw.health()
                self.assertEqual(probes(scripted), 1)
                clock[0] += 2
                gw.health()
                self.assertEqual(probes(scripted), 2)
                gw.forget_auth()
                gw.health()
                self.assertEqual(probes(scripted), 3)


class UnsupportedCliTests(unittest.TestCase):
    def test_a_cli_missing_any_required_flag_is_refused(self):
        """[HEALTH] CLAUDE_CLI_UNSUPPORTED when the installed CLI's --help lacks any one of the
        required flags; nothing weaker is attempted (no model call); health reports it."""
        for flag in REQUIRED_FLAGS:
            with self.subTest(flag=flag):
                gw = FakeClaude(VALID_OUTPUTS[VERIFY], help_text=help_without(flag))
                res = gw.run(VERIFY, payload_for(VERIFY))
                self.assertEqual(res.status, InfraStatus.CLAUDE_CLI_UNSUPPORTED)
                self.assertEqual(gw.calls, 0)
                self.assertEqual(gw.health()['status'], 'CLAUDE_CLI_UNSUPPORTED')
                self.assertFalse(gw.health()['ready'])

    def test_missing_flags_are_detected_from_the_help_not_assumed(self):
        """[HEALTH] The flag set comes from --help: a help text with no flags at all is unsupported,
        and a complete one is supported."""
        self.assertEqual(FakeClaude(VALID_OUTPUTS[VERIFY], help_text='nothing useful').run(
            VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_CLI_UNSUPPORTED)
        self.assertTrue(FakeClaude(VALID_OUTPUTS[VERIFY]).run(VERIFY, payload_for(VERIFY)).ok)

    def test_fake_gateway_unsupported(self):
        """[HEALTH] fail=CLAUDE_CLI_UNSUPPORTED on the test double goes through the same path."""
        gw = FakeClaude(fail=InfraStatus.CLAUDE_CLI_UNSUPPORTED)
        self.assertEqual(gw.run(VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_CLI_UNSUPPORTED)
        self.assertEqual(gw.calls, 0)

    def test_optional_flags_missing_only_drop_those_arguments(self):
        """[HEALTH] Without --no-chrome / --exclude-dynamic-system-prompt-sections / --model /
        --allowedTools the call still runs, with those arguments simply absent."""
        gw = FakeClaude(VALID_OUTPUTS[VERIFY], model='opus',
                        help_text=help_without('--no-chrome', '--exclude-dynamic-system-prompt-sections',
                                               '--model', '--allowedTools'))
        self.assertTrue(gw.run(VERIFY, payload_for(VERIFY)).ok)
        argv = gw.argvs[0]
        for flag in ('--no-chrome', '--exclude-dynamic-system-prompt-sections', '--model', 'opus', '--allowedTools'):
            self.assertNotIn(flag, argv)

    def test_a_transient_help_failure_is_not_remembered_as_unsupported(self):
        """[HEALTH] If `--help` fails once (timeout, antivirus scan, cold start) the CLI must not be
        written off for the life of the process: the next probe sees the real help and the gateway
        becomes ready."""
        class FlakyHelp(Runner):
            def __init__(self):
                self.scripted = ScriptedRunner((VALID_OUTPUTS[VERIFY],))
                self.help_calls = 0

            def run(self, argv, **kw):
                if '--help' in argv:
                    self.help_calls += 1
                    if self.help_calls == 1:
                        return ProcessOutcome(timed_out=True)
                return self.scripted.run(argv, **kw)

        runner = FlakyHelp()
        gw = ClaudeGateway(ClaudeConfig(enabled=True, cli_path=sys.executable), runner=runner)
        self.assertEqual(gw.health()['status'], 'CLAUDE_CLI_UNSUPPORTED')
        self.assertEqual(gw.health()['status'], 'OK')
        self.assertTrue(gw.run(VERIFY, payload_for(VERIFY)).ok)

    def test_capabilities_are_probed_once_per_executable(self):
        """[HEALTH] A successful --help / --version probe is cached; repeated health() calls do not
        re-run it."""
        runner = RecordingRunner(None, VALID_OUTPUTS[VERIFY])
        gw = ClaudeGateway(ClaudeConfig(enabled=True, cli_path=sys.executable), runner=runner)
        for _ in range(3):
            gw.health()
        self.assertEqual(sum('--help' in c['argv'] for c in runner.calls), 1)
        self.assertEqual(sum('--version' in c['argv'] for c in runner.calls), 1)


class ShimTests(unittest.TestCase):
    def test_cmd_bat_and_ps1_shims_are_refused_without_running_anything(self):
        """[HEALTH] A `.cmd` / `.bat` / `.ps1` launcher would be re-parsed by cmd.exe / PowerShell
        (the JSON schema and system prompt are arguments), so it is refused as UNSUPPORTED and no
        process starts. Checked by suffix, so it holds on every platform."""
        with tempfile.TemporaryDirectory() as tmp:
            for name in ('claude.cmd', 'claude.bat', 'claude.ps1', 'CLAUDE.CMD', 'Claude.Bat'):
                with self.subTest(name=name):
                    path = os.path.join(tmp, name)
                    with open(path, 'w', encoding='utf-8') as fh:
                        fh.write('@echo off\n')
                    gw, runner = gateway(path)
                    res = gw.run(VERIFY, payload_for(VERIFY))
                    self.assertEqual(res.status, InfraStatus.CLAUDE_CLI_UNSUPPORTED)
                    self.assertEqual(runner.calls, [])
                    health = gw.health()
                    self.assertEqual(health['status'], 'CLAUDE_CLI_UNSUPPORTED')
                    self.assertFalse(health['ready'])
                    self.assertEqual(health['executable'], '')

    @unittest.skipUnless(os.name == 'nt', 'PATHEXT resolution of .cmd is a Windows behaviour')
    def test_a_cmd_shim_found_on_path_is_refused_but_an_exe_beside_it_wins(self):
        """[HEALTH][RESOLVE] On Windows `claude` on PATH usually resolves to claude.cmd: that is refused,
        yet a claude.exe is preferred when one exists."""
        with tempfile.TemporaryDirectory() as only_cmd, tempfile.TemporaryDirectory() as with_exe:
            for directory, names in ((only_cmd, ['claude.cmd']), (with_exe, ['claude.cmd', 'claude.exe'])):
                for name in names:
                    with open(os.path.join(directory, name), 'w', encoding='utf-8') as fh:
                        fh.write('x')
            with mock.patch.dict(os.environ, {'PATH': only_cmd}):
                gw, runner = gateway('')
                self.assertEqual(gw.run(VERIFY, payload_for(VERIFY)).status, InfraStatus.CLAUDE_CLI_UNSUPPORTED)
                self.assertEqual(runner.calls, [])
            with mock.patch.dict(os.environ, {'PATH': with_exe}):
                gw, runner = gateway('')
                self.assertTrue(gw.run(VERIFY, payload_for(VERIFY)).ok)
                self.assertEqual(runner.model_calls[0]['argv'][0].lower(), os.path.join(with_exe, 'claude.exe').lower())


class ExecutableResolutionTests(unittest.TestCase):
    def test_the_executable_is_the_configured_one(self):
        """[RESOLVE] argv[0] is exactly the configured path."""
        gw = FakeClaude(VALID_OUTPUTS[VERIFY])
        gw.run(VERIFY, payload_for(VERIFY))
        self.assertEqual(gw.argvs[0][0], sys.executable)

    def test_gateway_picks_up_govos_claude_cli_path_from_the_environment(self):
        """[RESOLVE] A gateway built with no fixed config resolves GOVOS_CLAUDE_CLI_PATH on each call."""
        with mock.patch.dict(os.environ, {ENV_ENABLED: '1', ENV_CLI_PATH: sys.executable}):
            runner = RecordingRunner(None, VALID_OUTPUTS[VERIFY])
            gw = ClaudeGateway(runner=runner)
            self.assertTrue(gw.run(VERIFY, payload_for(VERIFY)).ok)
            self.assertEqual(runner.model_calls[0]['argv'][0], sys.executable)

    def test_without_an_explicit_path_the_executable_comes_from_path_only(self):
        """[RESOLVE] With GOVOS_CLAUDE_CLI_PATH unset, `claude` is looked up on PATH and nowhere else."""
        name = 'claude.exe' if os.name == 'nt' else 'claude'
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, name)
            with open(target, 'w', encoding='utf-8') as fh:
                fh.write('not a real program')
            os.chmod(target, 0o755)
            with mock.patch.dict(os.environ, {'PATH': tmp}):
                gw, runner = gateway('')
                self.assertTrue(gw.run(VERIFY, payload_for(VERIFY)).ok)
                self.assertEqual(os.path.normcase(runner.model_calls[0]['argv'][0]), os.path.normcase(target))

    def test_no_payload_field_can_choose_the_executable(self):
        """[RESOLVE] Payload keys named cli_path / executable / command / path / argv / binary change
        nothing: the process started is the configured one."""
        evil = os.path.join(tempfile.gettempdir(), 'evil.exe')
        gw = FakeClaude(VALID_OUTPUTS[VERIFY])
        payload = payload_for(VERIFY)
        payload.update({'cli_path': evil, 'executable': evil, 'command': evil, 'path': evil, 'argv': [evil],
                        'binary': evil, 'claude_path': evil, 'GOVOS_CLAUDE_CLI_PATH': evil})
        self.assertTrue(gw.run(VERIFY, payload).ok)
        self.assertEqual(gw.argvs[0][0], sys.executable)
        for element in gw.argvs[0]:
            self.assertNotIn('evil.exe', element)


# ================================================================================ what health says
class HealthContentTests(unittest.TestCase):
    FORBIDDEN_KEYS = ('path', 'cmd', 'command', 'argv', 'account', 'email', 'org', 'env', 'token', 'secret',
                      'key', 'stderr', 'stdout', 'cwd', 'workdir', 'prompt', 'flag')

    def _assert_safe(self, health: dict, *needles: str) -> None:
        blob = json.dumps(health)
        for needle in needles:
            self.assertNotIn(needle, blob)
        for key in health:
            for word in self.FORBIDDEN_KEYS:
                self.assertNotIn(word, key.lower(), key)
        self.assertEqual(set(health), {'enabled', 'installed', 'authenticated', 'ready', 'executable', 'version',
                                       'busy', 'status', 'message'})

    def test_health_never_contains_the_path_command_line_account_or_secrets(self):
        """[HEALTH] With a real child process answering --help/--version/auth status (and `auth status`
        printing an account email), health() names only a label and a version: no directory, no script
        path, no argument, no email, no environment value."""
        secrets = {'ANTHROPIC_API_KEY': 'sk-ant-SECRETKEY', 'OPENAI_API_KEY': 'sk-OPENAISECRET',
                   'TAVILY_API_KEY': 'tvly-SECRET', ENV_ADMIN_TOKEN: 'ADMIN-TOKEN-SECRET',
                   'DATABASE_PASSWORD': 'hunter2-SECRET'}
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, secrets):
            scenario = write_scenario(tmp, auth_extra={'email': 'person@example.com', 'orgName': 'Private Org',
                                                       'orgId': 'org-123-SECRET'})
            gw = ClaudeGateway(fake_cli_config(scenario, workdir=os.path.join(tmp, 'work')))
            health = gw.health()
            self.assertTrue(health['ready'], health)
            self.assertEqual(health['version'], '2.1.285')
            self.assertEqual(health['executable'], os.path.basename(sys.executable))
            self._assert_safe(health, os.path.dirname(sys.executable), sys.executable, FAKE_CLI_SCRIPT, scenario,
                              tmp, 'person@example.com', 'Private Org', 'org-123', 'claude.ai', 'loggedIn',
                              '--system-prompt', '--output-format', 'SECRET', 'hunter2')

    def test_health_is_safe_in_every_failure_state_too(self):
        """[HEALTH] The same key set, and no path or secret, when disabled / missing / signed out /
        unsupported."""
        missing = os.path.join(tempfile.gettempdir(), 'secret-dir-xyz', 'claude.exe')
        for gw in (gateway(sys.executable, enabled=False)[0], gateway(missing)[0],
                   FakeClaude(fail=InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED),
                   FakeClaude(fail=InfraStatus.CLAUDE_CLI_UNSUPPORTED)):
            self._assert_safe(gw.health(), os.path.dirname(sys.executable), 'secret-dir-xyz', FAKE_CLI_SCRIPT)

    def test_a_ready_health_is_a_label_and_a_version(self):
        """[HEALTH] When ready: executable is a bare file name (no directory separator), version is a
        dotted number, status OK, authenticated True."""
        health = FakeClaude().health()
        self.assertTrue(health['ready'])
        self.assertEqual(health['status'], 'OK')
        self.assertIs(health['authenticated'], True)
        self.assertNotIn(os.sep, health['executable'])
        self.assertNotIn('/', health['executable'])
        self.assertRegex(health['version'], r'^\d+\.\d+\.\d+$')
        self.assertEqual(health['message'], '')

    def test_health_message_is_the_fixed_wording(self):
        """[HEALTH] Non-ready states carry the SAFE_MESSAGES text for their status, nothing from stderr."""
        for gw, status in ((FakeClaude(fail=InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED), InfraStatus.CLAUDE_CLI_NOT_AUTHENTICATED),
                           (FakeClaude(fail=InfraStatus.CLAUDE_CLI_UNSUPPORTED), InfraStatus.CLAUDE_CLI_UNSUPPORTED),
                           (FakeClaude(fail=InfraStatus.CLAUDE_CLI_NOT_INSTALLED), InfraStatus.CLAUDE_CLI_NOT_INSTALLED),
                           (FakeClaude(fail=InfraStatus.CLAUDE_DISABLED), InfraStatus.CLAUDE_DISABLED)):
            health = gw.health()
            self.assertEqual(health['status'], status.value)
            self.assertEqual(health['message'], SAFE_MESSAGES[status])


if __name__ == '__main__':
    unittest.main()
