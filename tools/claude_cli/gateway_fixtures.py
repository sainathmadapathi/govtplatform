"""Shared fixtures for the gateway-level tests (not a test module: pytest does not collect it).

  * one valid payload and one valid structured reply per operation;
  * `RecordingRunner`, which records every process the gateway asks for and delegates to a scripted
    runner, so a test can prove that NO process was started;
  * helpers for the real-child-process tests that run `fake_cli.py`: scenario files, the fake CLI's
    log, and process-liveness checks that work on Windows and POSIX.

Nothing here can start the real Claude CLI: the only program the runner will start under test is
the Python interpreter (see `runner._refused_under_test`).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from typing import Any, Callable, Optional

from tools.claude_cli import testing  # noqa: F401  (marks the process as under test)
from tools.claude_cli.runner import ProcessOutcome, Runner
from tools.claude_cli.schemas import Operation
from tools.claude_cli.testing import ScriptedRunner, verdict_reply

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OP = Operation

# ------------------------------------------------------------------------------ valid payloads
PAYLOADS: dict = {
    OP.VERIFY_CLAIM: {'exam': 'Example Exam', 'cycle': '2026', 'field': 'exam_date', 'value': '1 January 2027',
                      'evidence': 'The examination will be held on 1 January 2027.',
                      'source_title': 'Notice', 'authority': 'Example Commission',
                      'source_url': 'https://example.gov.in/notice.pdf'},
    OP.CLASSIFY_ATTRIBUTION: {'field': 'vacancies_total', 'value_json': '100',
                              'evidence': 'Total vacancies: 100.', 'context': 'Vacancy table.',
                              'roles': ['total_vacancies', 'other']},
    OP.CLASSIFY_DATE: {'date': '2027-01-01', 'label': 'Date of examination', 'stated': '01.01.2027',
                       'context': 'Schedule of examination.', 'roles': ['EXAM', 'REFERENCE']},
    OP.CHECK_COMPLETENESS: {'quotation': 'Candidates must hold a degree.', 'context': 'Candidates must hold a '
                            'degree from a recognised university.', 'unit_kind': 'a whole sentence'},
    OP.EXTRACT_DESIGNATION: {'title_block': 'Notice for recruitment of Example Officer, 2026.'},
    OP.CONFIRM_RECRUITMENT: {'designation': 'Example Officer', 'cycle': '2026', 'components': ['Grade A', 'Grade B'],
                             'document_block': 'Result of Example Officer recruitment 2026.'},
    OP.ORDER_ROADMAP: {'exam_label': 'Example Exam 2026',
                       'topics': [{'id': 't1', 'subject': 'Maths', 'name': 'Algebra', 'high_yield': True},
                                  {'id': 't2', 'subject': 'English', 'name': 'Grammar', 'high_yield': False}]},
    OP.DISCOVER_SOURCES: {'query': 'Example Commission recruitment 2026 notification', 'max_results': 5,
                          'domain_hints': ['.gov.in', '.nic.in']},
    OP.EXTRACT_FIELDS: {'exam': 'Example Exam', 'cycle': '2026', 'authority': 'Example Commission',
                        'source_title': 'Notice', 'source_url': 'https://example.gov.in/n.pdf',
                        'fields': ['exam_date', 'vacancies_total'],
                        'source_text': 'Vacancies: 100. Examination on 1 January 2027.'},
    OP.ANSWER_QUESTION: {'exam_title': 'Example Exam 2026', 'authority': 'Example Commission',
                         'facts': [{'id': 'f1', 'section': 'DATES', 'label': 'Exam date', 'text': '1 January 2027'}],
                         'question': 'When is the exam?',
                         'history': [{'role': 'user', 'text': 'hello'}, {'role': 'assistant', 'text': 'hi'}]},
    OP.GENERATE_PRACTICE: {'exam_title': 'Example Exam 2026', 'topic': 'Algebra', 'allowed_topics': ['Algebra', 'Ratio'],
                           'count': 3, 'difficulty': 'MEDIUM', 'pattern_note': 'Four options.'},
    OP.SOLVE_PRACTICE: {'questions': [{'stem': 'x + 1 = 3. x = ?', 'options': ['1', '2', '3', '4']}]},
}

# ------------------------------------------------------------------------- valid structured replies
VALID_OUTPUTS: dict = {
    OP.VERIFY_CLAIM: verdict_reply('SUPPORTED', reason='stated'),
    OP.CLASSIFY_ATTRIBUTION: {'role': 'total_vacancies', 'supports_value': True, 'scope': '',
                              'evidence_span': 'Total vacancies: 100.', 'confidence': 'high', 'conflicts': []},
    OP.CLASSIFY_DATE: {'role': 'EXAM', 'supports_date': True, 'evidence_span': '01.01.2027',
                       'is_reference': False, 'confidence': 'high', 'conflicts': []},
    OP.CHECK_COMPLETENESS: {'complete': True, 'continues_after': False, 'starts_mid_unit': False,
                            'confidence': 'high', 'reason': 'whole sentence'},
    OP.EXTRACT_DESIGNATION: {'designation_core': ['Example Officer'], 'qualifiers': [], 'cycle': '2026',
                             'declared_components': [], 'evidence_spans': ['Example Officer, 2026'],
                             'confidence': 'high', 'ambiguities': []},
    OP.CONFIRM_RECRUITMENT: {'same_recruitment': True, 'evidence_span': 'Example Officer recruitment 2026',
                             'reason': 'named'},
    OP.ORDER_ROADMAP: {'order': [{'id': 't1', 'why': 'foundation'}, {'id': 't2', 'why': 'then language'}]},
    OP.DISCOVER_SOURCES: {'candidates': [{'title': 'Notice', 'url': 'https://example.gov.in/n.pdf',
                                          'authority_name': 'Example Commission', 'document_kind': 'NOTIFICATION',
                                          'why_relevant': 'the notice', 'snippet': 'Notice of examination'}],
                          'searched_queries': ['example commission recruitment'], 'notes': ''},
    OP.EXTRACT_FIELDS: {'fields': [{'field': 'exam_date', 'value': '1 January 2027',
                                    'quote': 'Examination on 1 January 2027.', 'location': 'p.1'}]},
    OP.ANSWER_QUESTION: {'answer': 'The exam is on 1 January 2027.', 'basis': 'VERIFIED_DATA',
                         'cited_fact_ids': ['f1'], 'uncertainty': 'NONE', 'navigate_to': 'DATES', 'follow_up': ''},
    OP.GENERATE_PRACTICE: {'questions': [{'topic': 'Algebra', 'stem': 'x + 1 = 3. x = ?',
                                          'options': ['1', '2', '3', '4'], 'correct_index': 1,
                                          'explanation': 'Subtract one from both sides.'}]},
    OP.SOLVE_PRACTICE: {'solutions': [{'index': 0, 'choice': 1}]},
}

#: The payload keys each template places inside a delimited data block.
BLOCK_KEYS: dict = {
    OP.VERIFY_CLAIM: ('evidence',),
    OP.CLASSIFY_ATTRIBUTION: ('evidence', 'context'),
    OP.CLASSIFY_DATE: ('stated', 'context'),
    OP.CHECK_COMPLETENESS: ('quotation', 'context'),
    OP.EXTRACT_DESIGNATION: ('title_block',),
    OP.CONFIRM_RECRUITMENT: ('document_block',),
    OP.DISCOVER_SOURCES: ('query',),
    OP.EXTRACT_FIELDS: ('source_text',),
    OP.ANSWER_QUESTION: ('question',),
    OP.GENERATE_PRACTICE: ('topic', 'pattern_note'),
    OP.SOLVE_PRACTICE: ('questions',),
}

#: A key of each payload that is NOT in a block (the template prints it inline).
INLINE_KEYS: dict = {
    OP.VERIFY_CLAIM: ('exam', 'field', 'value', 'cycle', 'source_title', 'authority', 'source_url'),
    OP.CLASSIFY_ATTRIBUTION: ('field', 'value_json', 'roles'),
    OP.CLASSIFY_DATE: ('date', 'label', 'roles'),
    OP.CHECK_COMPLETENESS: ('unit_kind',),
    OP.CONFIRM_RECRUITMENT: ('designation', 'cycle', 'components'),
    OP.ORDER_ROADMAP: ('exam_label',),
    OP.DISCOVER_SOURCES: ('domain_hints',),
    OP.EXTRACT_FIELDS: ('exam', 'cycle', 'authority', 'source_title', 'source_url', 'fields'),
    OP.ANSWER_QUESTION: ('exam_title', 'authority'),
    OP.GENERATE_PRACTICE: ('exam_title', 'difficulty'),
}


def payload_for(op: Operation) -> dict:
    return json.loads(json.dumps(PAYLOADS[op]))


def map_strings(value: Any, fn: Callable[[str], str]) -> Any:
    """`value` with `fn` applied to every string in it (dict values, list items), recursively."""
    if isinstance(value, str):
        return fn(value)
    if isinstance(value, list):
        return [map_strings(v, fn) for v in value]
    if isinstance(value, dict):
        return {k: map_strings(v, fn) for k, v in value.items()}
    return value


def outside_block_lines(prompt: str, nonce: str) -> list:
    """The lines of `prompt` that are not inside a data block (and are not block markers)."""
    opener = re.compile(r'^<<<(?!END )(?P<label>.*):' + re.escape(nonce) + r'>>>$')
    out: list = []
    open_label = None
    for line in prompt.split('\n'):
        if open_label is None:
            m = opener.match(line)
            if m:
                open_label = m.group('label')
            else:
                out.append(line)
        elif line == f'<<<END {open_label}:{nonce}>>>':
            open_label = None
    assert open_label is None, 'a data block was never closed'
    return out


def block_labels(prompt: str, nonce: str) -> list:
    return re.findall(r'^<<<(?!END )(.*):' + re.escape(nonce) + r'>>>$', prompt, re.M)


# ----------------------------------------------------------------------------- recording runner
class RecordingRunner(Runner):
    """Records every process request, then delegates to a scripted runner."""

    def __init__(self, inner: Optional[Runner] = None, *replies: Any, **scripted_kw: Any) -> None:
        self.inner = inner or ScriptedRunner(replies, **scripted_kw)
        self.calls: list = []

    def run(self, argv, *, stdin_text, env, cwd, timeout, max_output_bytes, cancel_event=None):
        self.calls.append({'argv': list(argv), 'stdin_text': stdin_text, 'env': dict(env), 'cwd': cwd,
                           'timeout': timeout, 'max_output_bytes': max_output_bytes})
        return self.inner.run(argv, stdin_text=stdin_text, env=env, cwd=cwd, timeout=timeout,
                              max_output_bytes=max_output_bytes, cancel_event=cancel_event)

    @property
    def model_calls(self) -> list:
        return [c for c in self.calls if '-p' in c['argv']]


class CallableRunner(Runner):
    """A runner whose model calls are answered by `fn(argv, stdin_text, cancel_event) -> ProcessOutcome`;
    help / version / auth probes are answered like a healthy CLI."""

    def __init__(self, fn: Callable[..., ProcessOutcome]) -> None:
        self.fn = fn
        self.probe = ScriptedRunner(())

    def run(self, argv, *, stdin_text, env, cwd, timeout, max_output_bytes, cancel_event=None):
        if '-p' not in argv:
            return self.probe.run(argv, stdin_text=stdin_text, env=env, cwd=cwd, timeout=timeout,
                                  max_output_bytes=max_output_bytes, cancel_event=cancel_event)
        return self.fn(argv, stdin_text, cancel_event)


# ------------------------------------------------------------------------- real child processes
def write_scenario(directory: str, name: str = 'scenario.json', **scenario: Any) -> str:
    path = os.path.join(directory, name)
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(scenario, fh)
    return path


def read_log(path: str) -> list:
    if not os.path.exists(path):
        return []
    with open(path, encoding='utf-8') as fh:
        return [json.loads(line) for line in fh if line.strip()]


def wait_until(predicate: Callable[[], bool], timeout: float = 15.0, interval: float = 0.05) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return bool(predicate())


def pid_alive(pid: int) -> bool:
    """Whether a process with this id is still running (never signals it)."""
    if os.name == 'nt':
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.OpenProcess.restype = ctypes.c_void_p
        k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
        k32.GetExitCodeProcess.argtypes = [ctypes.c_void_p, ctypes.POINTER(ctypes.c_ulong)]
        k32.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = k32.OpenProcess(0x1000, 0, pid)           # PROCESS_QUERY_LIMITED_INFORMATION
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return True
            return code.value == 259                        # STILL_ACTIVE
        finally:
            k32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:                                                    # a zombie is dead for our purposes
        with open(f'/proc/{pid}/stat', encoding='utf-8') as fh:
            return fh.read().rsplit(')', 1)[-1].split()[0] != 'Z'
    except (OSError, IndexError):
        return True


def kill_pid(pid: int) -> None:
    """Best-effort cleanup for a test that failed to kill its own child."""
    try:
        if os.name == 'nt':
            subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], stdout=subprocess.DEVNULL,
                           stderr=subprocess.DEVNULL, timeout=15, check=False)
        else:
            import signal
            os.kill(pid, signal.SIGKILL)
    except Exception:                                       # noqa: BLE001
        pass


def read_pid_file(path: str) -> Optional[int]:
    try:
        with open(path, encoding='utf-8') as fh:
            text = fh.read().strip()
        return int(text) if text else None
    except (OSError, ValueError):
        return None


PYTHON = sys.executable
