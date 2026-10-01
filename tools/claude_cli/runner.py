"""The only place in GovOS that starts an operating-system process for Claude.

Guarantees, all enforced here and tested:

  * `shell=False`, arguments as a list, so a string in a prompt or a payload can never become
    shell syntax. The prompt travels on stdin, never in the command line.
  * a narrow, allow-listed environment (see `build_child_env`): nothing is inherited that the CLI
    does not need to run and sign in with the host account, and no API-key variable is ever
    forwarded;
  * an explicit timeout, after which the whole process tree is killed (Windows: `taskkill /T`;
    POSIX: the process group), not just the direct child;
  * a hard cap on captured output, enforced while reading, so a runaway child cannot fill memory;
  * stdout and stderr captured separately; stderr is returned to the gateway for classification
    and is never shown to anyone.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from typing import Mapping, Optional, Sequence

IS_WINDOWS = os.name == 'nt'

#: Variables the CLI needs to start and to find the host account's login (its credentials live in the
#: CLI's own config directory, which `CLAUDE_CONFIG_DIR` may relocate). Everything else is dropped.
#: No `ANTHROPIC_*` variable, and no token of any kind, is ever forwarded: the login is the host's.
_ENV_ALLOW = (
    'PATH', 'PATHEXT', 'SYSTEMROOT', 'SYSTEMDRIVE', 'WINDIR', 'COMSPEC', 'USERNAME', 'USERPROFILE',
    'HOME', 'HOMEDRIVE', 'HOMEPATH', 'APPDATA', 'LOCALAPPDATA', 'PROGRAMDATA', 'PROGRAMFILES',
    'PROGRAMFILES(X86)', 'TEMP', 'TMP', 'TMPDIR', 'LANG', 'LC_ALL', 'TERM', 'SHELL', 'USER',
    'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME',
    'HTTPS_PROXY', 'HTTP_PROXY', 'NO_PROXY', 'ALL_PROXY', 'SSL_CERT_FILE', 'SSL_CERT_DIR',
    'NODE_EXTRA_CA_CERTS', 'REQUESTS_CA_BUNDLE',
    'CLAUDE_CONFIG_DIR',
)
_ENV_ALLOW_UPPER = frozenset(k.upper() for k in _ENV_ALLOW)
_ENV_NEVER_PREFIXES = ('ANTHROPIC_', 'OPENAI_', 'AWS_', 'AZURE_', 'GOOGLE_', 'GOVOS_')


def build_child_env(parent: Optional[Mapping[str, str]] = None) -> dict:
    """The environment handed to the CLI. Case-insensitive match on Windows variable names."""
    parent = os.environ if parent is None else parent
    out: dict = {}
    for key, value in parent.items():
        up = key.upper()
        if up.startswith(_ENV_NEVER_PREFIXES):
            continue
        if up in _ENV_ALLOW_UPPER:
            out[key] = value
    out['NO_COLOR'] = '1'
    return out


@dataclass
class ProcessOutcome:
    returncode: Optional[int] = None
    stdout: str = ''
    stderr: str = ''
    timed_out: bool = False
    cancelled: bool = False
    output_truncated: bool = False
    #: Set when the process could not be started at all: 'not_found' | 'denied' | 'oserror'.
    start_error: str = ''


class Runner:
    """Interface the gateway runs processes through. Tests inject a fake."""

    def run(self, argv: Sequence[str], *, stdin_text: str, env: Mapping[str, str], cwd: str,
            timeout: float, max_output_bytes: int,
            cancel_event: Optional[threading.Event] = None) -> ProcessOutcome:
        raise NotImplementedError


def kill_process_tree(proc: subprocess.Popen) -> None:
    """Kill `proc` and everything it started."""
    try:
        if IS_WINDOWS:
            subprocess.run(['taskkill', '/PID', str(proc.pid), '/T', '/F'],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15,
                           shell=False, check=False)
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except Exception:                                            # noqa: BLE001
        pass
    try:
        proc.kill()
    except Exception:                                            # noqa: BLE001
        pass


def _pump(stream, chunks: list, cap: int, flags: dict, drain: bool = False) -> None:
    total = 0
    try:
        while True:
            data = stream.read(8192)
            if not data:
                break
            total += len(data)
            if total > cap:
                flags['truncated'] = True
                if drain:        # stderr: keep emptying the pipe (discarding) so the child is never blocked on it
                    continue
                break
            chunks.append(data)
    except Exception:                                            # noqa: BLE001
        pass


#: Set by the test support module and the test configuration. While it is set, the only program
#: this runner will start is the Python interpreter running the tests (which hosts the fake CLI):
#: an automated test can never start the real Claude CLI, whatever the configuration says.
TEST_MODE_ENV = 'GOVOS_CLAUDE_TEST_MODE'


def _refused_under_test(argv) -> bool:
    if os.environ.get(TEST_MODE_ENV) != '1' or not argv:
        return False
    try:
        return os.path.realpath(argv[0]) != os.path.realpath(sys.executable)
    except OSError:
        return True


class SubprocessRunner(Runner):
    def run(self, argv, *, stdin_text, env, cwd, timeout, max_output_bytes, cancel_event=None):
        out = ProcessOutcome()
        if _refused_under_test(argv):
            out.start_error = 'denied'
            return out
        kwargs: dict = {}
        if IS_WINDOWS:
            kwargs['creationflags'] = (getattr(subprocess, 'CREATE_NO_WINDOW', 0)
                                       | getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0))
        else:
            kwargs['start_new_session'] = True
        try:
            proc = subprocess.Popen(list(argv), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE, env=dict(env), cwd=cwd, shell=False,
                                    **kwargs)
        except FileNotFoundError:
            out.start_error = 'not_found'
            return out
        except PermissionError:
            out.start_error = 'denied'
            return out
        except OSError:
            out.start_error = 'oserror'
            return out

        flags = {'truncated': False}
        stdout_chunks: list = []
        stderr_chunks: list = []
        threads = [
            threading.Thread(target=_pump, args=(proc.stdout, stdout_chunks, max_output_bytes, flags), daemon=True),
            threading.Thread(target=_pump, args=(proc.stderr, stderr_chunks, 65_536, {}, True), daemon=True),
        ]

        def feed() -> None:
            try:
                proc.stdin.write((stdin_text or '').encode('utf-8'))
            except Exception:                                    # noqa: BLE001
                pass
            finally:
                try:
                    proc.stdin.close()
                except Exception:                                # noqa: BLE001
                    pass

        threads.append(threading.Thread(target=feed, daemon=True))
        for t in threads:
            t.start()

        deadline = time.monotonic() + timeout
        while proc.poll() is None:
            if cancel_event is not None and cancel_event.is_set():
                out.cancelled = True
                kill_process_tree(proc)
                break
            if flags['truncated']:
                out.output_truncated = True
                kill_process_tree(proc)
                break
            if time.monotonic() > deadline:
                out.timed_out = True
                kill_process_tree(proc)
                break
            time.sleep(0.05)
        try:
            proc.wait(timeout=10)
        except Exception:                                        # noqa: BLE001
            kill_process_tree(proc)
        for t in threads:
            t.join(timeout=5)
        for stream in (proc.stdout, proc.stderr, proc.stdin):    # no pipe is left for the garbage collector
            try:
                stream.close()
            except Exception:                                    # noqa: BLE001
                pass
        out.returncode = proc.returncode
        out.output_truncated = out.output_truncated or flags['truncated']
        out.stdout = b''.join(stdout_chunks).decode('utf-8', 'replace')
        out.stderr = b''.join(stderr_chunks).decode('utf-8', 'replace')
        return out
