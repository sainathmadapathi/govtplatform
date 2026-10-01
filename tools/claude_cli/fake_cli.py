"""A stand-in for the Claude CLI, run as a real child process by the gateway's tests.

It is test support only (never imported by the app). Behaviour is chosen by a scenario file given
as `--scenario <path>` before the CLI's own arguments:

    {"mode": "ok", "output": {...}, "log": "<path>", "logged_in": true, "help_omit": ["--tools"]}

Modes: ok, timeout, tree (starts a child that also hangs), exit1, bad_json, wrong_schema, huge,
stderr_secret, stderr_flood (writes `flood_bytes` of stderr, then a valid reply), auth_error,
rate_limit, text_json, prose_json, cot, denied_tools, sequence (per-call modes).

Other scenario keys: `auth_extra` (extra fields printed by `auth status`, e.g. an account email,
so a test can prove the gateway never surfaces them), `child_pid_file` (tree mode), `counter` and
`steps` (sequence mode), `huge_bytes`.

Every `-p` call appends one JSON line to the log: its arguments, its stdin, its working directory,
its own process id and the NAMES (never values) of its environment variables.
"""
import json
import os
import subprocess
import sys
import time

HELP_FLAGS = ['--print', '--output-format', '--json-schema', '--system-prompt', '--tools',
              '--no-session-persistence', '--permission-mode', '--setting-sources',
              '--strict-mcp-config', '--disable-slash-commands', '--no-chrome',
              '--exclude-dynamic-system-prompt-sections', '--model', '--allowedTools']


def envelope(structured=None, **kw):
    env = {'type': 'result', 'subtype': 'success', 'is_error': False, 'num_turns': 2,
           'result': json.dumps(structured) if structured is not None else '',
           'permission_denials': [],
           'usage': {'input_tokens': 2, 'cache_creation_input_tokens': 10, 'output_tokens': 5,
                     'server_tool_use': {'web_search_requests': 0, 'web_fetch_requests': 0}}}
    if structured is not None:
        env['structured_output'] = structured
    env.update(kw)
    return env


def main():
    argv = sys.argv[1:]
    scenario = {}
    if argv[:1] == ['--scenario']:
        with open(argv[1], encoding='utf-8') as fh:
            scenario = json.load(fh)
        argv = argv[2:]
    log = scenario.get('log')

    if argv == ['--version']:
        print('2.1.285 (Claude Code)')
        return 0
    if argv == ['--help']:
        omit = set(scenario.get('help_omit', []))
        print('Usage: claude [options]\n' + '\n'.join(f'  {f}  help' for f in HELP_FLAGS if f not in omit))
        return 0
    if argv[:2] == ['auth', 'status']:
        print(json.dumps(dict({'loggedIn': scenario.get('logged_in', True), 'authMethod': 'claude.ai'},
                              **scenario.get('auth_extra', {}))))
        return 0

    stdin = sys.stdin.buffer.read().decode('utf-8', 'replace')     # the gateway writes UTF-8, as the real CLI reads it
    if log:
        with open(log, 'a', encoding='utf-8') as fh:
            fh.write(json.dumps({'argv': argv, 'stdin': stdin, 'cwd': os.getcwd(), 'pid': os.getpid(),
                                 'env_keys': sorted(os.environ)}) + '\n')

    mode = scenario.get('mode', 'ok')
    if mode == 'sequence':
        counter = scenario['counter']
        n = 0
        if os.path.exists(counter):
            n = int(open(counter).read() or 0)
        open(counter, 'w').write(str(n + 1))
        steps = scenario['steps']
        mode = steps[min(n, len(steps) - 1)]
    output = scenario.get('output', {})

    if mode == 'timeout':
        time.sleep(600)
    elif mode == 'tree':
        child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(600)'])
        if scenario.get('child_pid_file'):
            open(scenario['child_pid_file'], 'w').write(str(child.pid))
        time.sleep(600)
    elif mode == 'exit1':
        sys.stderr.write('internal failure')
        return 1
    elif mode == 'bad_json':
        print('not { valid json')
    elif mode == 'wrong_schema':
        print(json.dumps(envelope({'unexpected': 'shape'})))
    elif mode == 'huge':
        print('{"type":"result","result":"' + 'x' * int(scenario.get('huge_bytes', 2_000_000)) + '"}')
    elif mode == 'stderr_secret':
        sys.stderr.write('token=sk-ant-SECRET-VALUE path=C:\\Users\\someone\\.claude')
        return 1
    elif mode == 'stderr_flood':
        sys.stderr.write('e' * int(scenario.get('flood_bytes', 1_000_000)))
        sys.stderr.flush()
        print(json.dumps(envelope(output)))
    elif mode == 'auth_error':
        print(json.dumps(envelope(is_error=True, result='Not logged in · Please run /login')))
        return 1
    elif mode == 'rate_limit':
        print(json.dumps(envelope(is_error=True, result='429 rate limit reached', subtype='error_during_execution')))
        return 1
    elif mode == 'text_json':
        print(json.dumps(envelope(result=json.dumps(output))))
    elif mode == 'prose_json':
        print(json.dumps(envelope(result='Here you go: ' + json.dumps(output))))
    elif mode == 'cot':
        print(json.dumps(envelope(dict(output, thinking='step by step secret'))))
    elif mode == 'denied_tools':
        print(json.dumps(envelope(output, permission_denials=[{'tool_name': 'WebSearch'}])))
    else:
        print(json.dumps(envelope(output)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
