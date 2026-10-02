"""Repo-wide smoke test: the retired AI architecture is gone and the Claude CLI is the only AI left.

GovOS used to reach a local model server (llama.cpp running a Qwen GGUF, behind GOVOS_LLM_* settings)
and a third-party search API. Both were replaced by one thing: the installed Claude CLI, run
server-side by `tools/claude_cli`, behind one gateway. This test walks the repository (filesystem
only: no import of the app, no process, no network) and fails if anything of the old design is still
there, or if a second route to a model has appeared.

What it checks:

  * no source file mentions the old server, model, endpoints, settings, provider or an AI vendor's
    SDK / API host (`FORBIDDEN`), apart from an explicit, justified allowlist (`ALLOWED`);
  * the retired verification modules are gone, `.gitignore` carries no model-weights entry,
    `.env.example` documents the Claude switch and holds no secret, and no dependency manifest
    declares a model or search client;
  * no Python module imports a model/HTTP-client library (the repo talks HTTP with urllib only);
  * the only code that starts an operating-system process for Claude is `tools/claude_cli/runner.py`,
    and `shell=True` appears nowhere in `tools/claude_cli`;
  * markdown documents that still describe the old design are marked as archival (or sit in the
    integration guide's migration section) - see `MARKDOWN_BANNERS_PENDING`.
"""
from __future__ import annotations

import ast
import json
import os
import re
import unittest

THIS_FILE = os.path.abspath(__file__)
REPO = os.path.dirname(os.path.dirname(os.path.dirname(THIS_FILE)))
CLAUDE_CLI = os.path.join(REPO, 'tools', 'claude_cli')
VERIFICATION = os.path.join(REPO, 'tools', 'exam_builder', 'verification')

#: Directories that are not source: dependencies, build output, caches, the data the app generates,
#: scratch work and local tool settings.
SKIP_DIRS = frozenset({
    'node_modules', 'dist', '.git', '__pycache__', '.exam_cache', '.exam_staging', '.exam_manifests',
    'exam_data', 'scratch', '.claude', '.pytest_cache', '.venv', 'venv', '.mypy_cache', '.idea', '.vscode',
})
SOURCE_SUFFIXES = frozenset({
    '.py', '.ts', '.tsx', '.mjs', '.js', '.cjs', '.json', '.html', '.css', '.txt', '.yml', '.yaml',
    '.toml', '.cfg', '.ini', '.bat', '.sh', '.ps1',
})
#: Files with no (or an unhelpful) suffix that are source/config. `.env` itself is deliberately NOT
#: here: the real file holds the operator's settings and is never read by a test.
SOURCE_NAMES = frozenset({'.gitignore', '.env.example', 'requirements.txt'})
SKIP_FILES = frozenset({'package-lock.json'})

# --------------------------------------------------------------------------- what is forbidden
FORBIDDEN = {
    'llama.cpp': re.compile(r'llama\.cpp|llama-server|llama_cpp', re.I),
    'qwen': re.compile(r'qwen', re.I),
    'gguf model file': re.compile(r'\.gguf\b|\bgguf\b', re.I),
    'local model server address': re.compile(r'127\.0\.0\.1:8080'),
    'OpenAI-style local endpoint': re.compile(r'/v1/chat/completions|/v1/models'),
    'GOVOS_LLM_ setting': re.compile(r'GOVOS_LLM_'),
    'local provider class': re.compile(r'LocalQwenVerificationProvider', re.I),
    'old search provider': re.compile(r'tavily', re.I),
    'vendor SDK import': re.compile(r'\b(?:import|from)\s+(?:anthropic|openai)\b'),
    'JS/TS vendor SDK import': re.compile(
        r'''(?:from\s+|require\(\s*|import\(\s*)['"](?:@anthropic-ai/[^'"]*|anthropic|openai|@tavily/[^'"]*)['"]'''),
    'vendor API host': re.compile(r'api\.anthropic\.com|api\.openai\.com|api\.tavily\.com', re.I),
}

#: The whole allowlist. Each entry is (labels that may appear, most lines allowed, why). Keep it short:
#: an entry here is a place where an old name is allowed to survive, so it needs a reason that is
#: not "it was easier". This test file is exempt by construction (it has to name the terms).
ALLOWED = {
    'tools/exam_builder/fixtures/tgpsc_group_i_2024_v7.json': (
        {'old search provider'}, 2,
        'a frozen fixture: two historical search notes ("searched ... Tavily restricted to TGPSC\'s domains") '
        'written when that provider was in use. They record what was searched on 2026-09-28, which is data about '
        'the past, and the fixture is frozen by digest (test_tgpsc_v7_fixture), so it is not rewritten.'),
}

#: Negative tests of the Claude package: modules whose whole purpose is to prove that an old thing is
#: refused, not read or never forwarded - for example that the old search provider's credential variable,
#: placed in a fake parent environment, never reaches the CLI's environment, or that the retired local
#: model server's address is refused as a request target. That can not be tested without naming the old
#: thing. Entry: (labels that may appear, line cap, reason). Explicit per module and only for the labels
#: listed, so any other kind of mention (a URL, a vendor SDK import, a settings name) in the same module
#: is still a finding, and the AST checks below still refuse an actual import. Each module could instead
#: build the name from two halves and drop out of this table; unlike `ALLOWED`, an entry that goes stale
#: here is harmless, so staleness is not an error. A new test module that names such a thing fails this
#: scan until it is reworded or listed here with a reason.
ALLOWED_NEGATIVE_TESTS = {
    'tools/claude_cli/test_runner.py': (
        {'old search provider'}, 6,
        'negative test: the child-process environment is built from a fake parent environment that holds '
        'the old search provider\'s credential variable beside the vendor key variables, to prove none of '
        'them is ever forwarded to the CLI. The variable has to be named to be tested.'),
    'tools/claude_cli/test_config.py': (
        {'old search provider'}, 6,
        'negative test: the old search provider\'s credential variable is put in the environment to prove '
        'the configuration neither reads it nor has any API-key setting of its own. The variable has to be '
        'named to be tested.'),
    'tools/claude_cli/test_gateway.py': (
        {'old search provider'}, 6,
        'negative test: the gateway is run against a parent environment holding the old search provider\'s '
        'credential variable to prove the CLI is never started with it. The variable has to be named to be '
        'tested.'),
    'tools/claude_cli/test_gateway_process.py': (
        {'old search provider'}, 6,
        'negative test: a real child process is started and reports its own environment, to prove that the '
        'old search provider\'s credential variable (with the vendor keys and the admin token) is never '
        'forwarded to it. The variable has to be named to be tested.'),
    'tools/claude_cli/test_discovery.py': (
        {'local model server address'}, 4,
        'negative test: the retired local model server address is one of the loopback URLs that discovery\'s '
        'server-side-request guard must refuse as a target. A loopback address with a port has to be named '
        'to be tested.'),
}
NEGATIVE_TEST_LABELS = frozenset({'old search provider', 'local model server address'})


# ------------------------------------------------------------------------------ the walk
def _relative(path: str) -> str:
    return os.path.relpath(path, REPO).replace(os.sep, '/')


def walk_files(suffixes=None, names=None, root: str | None = None):
    """Every non-skipped file under `root` (default: the repository) whose suffix or whole name is wanted."""
    for folder, dirs, files in os.walk(root or REPO):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            path = os.path.join(folder, name)
            if os.path.abspath(path) == THIS_FILE or name in SKIP_FILES:
                continue
            if (names and name in names) or (suffixes and os.path.splitext(name)[1].lower() in suffixes):
                yield path


def read(path: str) -> str:
    with open(path, encoding='utf-8', errors='replace') as fh:
        return fh.read()


def scan_text(text: str):
    """[(label, line number, line)] for every forbidden mention in `text`."""
    hits = []
    for number, line in enumerate(text.splitlines(), start=1):
        for label, rx in FORBIDDEN.items():
            if rx.search(line):
                hits.append((label, number, line.strip()[:140]))
    return hits


def source_hits():
    """{relative path: [(label, line, text)]} over every source file."""
    found = {}
    for path in walk_files(SOURCE_SUFFIXES, SOURCE_NAMES):
        hits = scan_text(read(path))
        if hits:
            found[_relative(path)] = hits
    return found


def describe(found: dict) -> str:
    lines = []
    for path, hits in sorted(found.items()):
        for label, number, text in hits[:6]:
            lines.append('  %s:%d  [%s]  %s' % (path, number, label, text))
        if len(hits) > 6:
            lines.append('  %s: ... and %d more' % (path, len(hits) - 6))
    return '\n'.join(lines)


# ------------------------------------------------------------------------- markdown rules
#: Historical documents carry an "ARCHIVAL" banner (within their first 12 lines) and keep old names in
#: CLAUDE_CLI_INTEGRATION.md only inside its migration section. While the documents were still being
#: bannered the markdown check was skipped, loudly (set this to True to skip it again); it is enforced now.
MARKDOWN_BANNERS_PENDING = False
MARKDOWN_BANNER_LINES = 12
MIGRATION_GUIDE = 'CLAUDE_CLI_INTEGRATION.md'
_ARCHIVAL = re.compile(r'\bARCHIVAL\b', re.I)
_HEADING = re.compile(r'^(#{1,6})\s+(.*\S)\s*$')


def markdown_violations(text: str, name: str = 'doc.md'):
    """Forbidden mentions in one markdown document that are neither under an archival banner nor in
    the integration guide's migration section. [(label, line, text)]."""
    hits = scan_text(text)
    if not hits:
        return []
    lines = text.splitlines()
    if any(_ARCHIVAL.search(line) for line in lines[:MARKDOWN_BANNER_LINES]):
        return []
    if os.path.basename(name) != MIGRATION_GUIDE:
        return hits
    allowed_lines = set()
    chain = []                                      # (level, title) of the headings above the current line
    for number, line in enumerate(lines, start=1):
        m = _HEADING.match(line)
        if m:
            level = len(m.group(1))
            chain = [(lv, t) for lv, t in chain if lv < level] + [(level, m.group(2))]
        if any('migrat' in title.lower() for _lv, title in chain):
            allowed_lines.add(number)
    return [h for h in hits if h[1] not in allowed_lines]


def all_markdown_violations():
    found = {}
    for path in walk_files(suffixes={'.md'}):
        bad = markdown_violations(read(path), path)
        if bad:
            found[_relative(path)] = bad
    return found


_markdown_gate = (unittest.skip(
    'markdown banners are not all in place yet (MARKDOWN_BANNERS_PENDING): documents that still describe the '
    'retired local-model / search-provider design must start with an ARCHIVAL banner, or sit in the migration '
    'section of CLAUDE_CLI_INTEGRATION.md. Set MARKDOWN_BANNERS_PENDING = False when they are.')
    if MARKDOWN_BANNERS_PENDING else (lambda fn: fn))


# ---------------------------------------------------------------------------- python helpers
def python_files(root: str | None = None):
    return list(walk_files({'.py'}, root=root))


def parse(path: str):
    try:
        return ast.parse(read(path), filename=path)
    except SyntaxError as exc:                      # a file that does not parse can not be vouched for
        raise AssertionError('%s does not parse: %s' % (_relative(path), exc))


def imported_modules(tree) -> list:
    """[(dotted module name, line)] for every import statement and literal dynamic import."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(a.name, node.lineno) for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.append((node.module, node.lineno))
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, 'id', '')
            if name in ('__import__', 'import_module') and node.args \
                    and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                found.append((node.args[0].value, node.lineno))
    return found


def call_name(node: ast.Call) -> str:
    fn = node.func
    parts = []
    while isinstance(fn, ast.Attribute):
        parts.append(fn.attr)
        fn = fn.value
    if isinstance(fn, ast.Name):
        parts.append(fn.id)
    return '.'.join(reversed(parts))


#: Libraries a Python module may not import: a model vendor's SDK, a search provider, a local model
#: runtime, an agent framework, and the general HTTP clients (the repo uses urllib only, so a model
#: can not be reached through one of them unnoticed).
BANNED_IMPORT_ROOTS = frozenset({
    'anthropic', 'openai', 'tavily', 'llama_cpp', 'litellm', 'langchain', 'langchain_core', 'langchain_anthropic',
    'langchain_openai', 'ollama', 'claude_agent_sdk', 'claude_code_sdk', 'cohere', 'mistralai', 'groq',
    'requests', 'httpx', 'aiohttp',
})
BANNED_IMPORT_PREFIXES = ('google.generativeai', 'google.genai', 'vertexai')

SPAWN_MODULES = frozenset({'subprocess', 'pty', 'pexpect', 'plumbum', 'sh'})
SPAWN_CALLS = re.compile(
    r'^(?:subprocess\.\w+|os\.(?:system|popen|startfile|spawn\w*|exec\w*|fork\w*)|pty\.spawn|Popen|'
    r'asyncio\.create_subprocess_(?:exec|shell)|multiprocessing\.\w*Process)$')


#: Modules of the package that exist only for tests. They may start processes to test process handling.
TEST_SUPPORT_FILES = frozenset({'fake_cli.py', 'gateway_fixtures.py', 'exam_fixtures.py'})


def is_test_support(path: str) -> bool:
    name = os.path.basename(path)
    return name.startswith('test_') or name in TEST_SUPPORT_FILES


def harmless_test_spawn(node: ast.Call) -> bool:
    """A test helper's process start that can not be Claude: the interpreter running the tests, or
    `taskkill` reaping one, as an argument list (no shell) that never names Claude."""
    argv = ast.unparse(node.args[0]) if node.args else ''
    for kw in node.keywords:
        if kw.arg == 'shell' and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
            return False
    if re.search(r'claude', argv, re.I):
        return False
    return argv.startswith('[sys.executable') or argv.startswith("['taskkill'")



class RetiredArchitecture(unittest.TestCase):
    # ---------------------------------------------------------------- the main sweep
    def test_no_source_file_mentions_the_retired_design(self):
        found = source_hits()
        unexpected = {}
        for path, hits in found.items():
            rule = ALLOWED.get(path) or ALLOWED_NEGATIVE_TESTS.get(path)
            if rule is None:
                unexpected[path] = hits
                continue
            labels, limit = rule[0], rule[1]
            extra = [h for h in hits if h[0] not in labels]
            if extra or len(hits) > limit:
                unexpected[path] = extra or hits
        self.assertFalse(unexpected, 'the retired local-model / search-provider design is still referenced:\n'
                         + describe(unexpected))

    def test_the_negative_test_exemptions_are_narrow(self):
        self.assertLessEqual(len(ALLOWED_NEGATIVE_TESTS), 6, 'reword a negative test rather than exempting another')
        for path, (labels, limit, why) in ALLOWED_NEGATIVE_TESTS.items():
            with self.subTest(path=path):
                self.assertTrue(path.startswith('tools/claude_cli/test_') and path.endswith('.py'),
                                'only the Claude package\'s own test modules may name an old thing')
                self.assertTrue(labels and labels <= NEGATIVE_TEST_LABELS, labels)
                self.assertLessEqual(limit, 6)
                self.assertGreater(len(why.split()), 20, 'an exemption needs a real reason')
                self.assertTrue(why.startswith('negative test:'))
                self.assertNotIn(path, ALLOWED)
                self.assertNotEqual(os.path.basename(path), os.path.basename(THIS_FILE))

    def test_the_allowlist_is_small_justified_and_not_stale(self):
        self.assertLessEqual(len(ALLOWED), 1, 'the allowlist should stay as small as possible')
        found = source_hits()
        for path, (labels, limit, why) in ALLOWED.items():
            with self.subTest(path=path):
                self.assertGreater(len(why.split()), 20, 'an allowlist entry needs a real reason')
                self.assertTrue(os.path.isfile(os.path.join(REPO, path)), 'allowlisted file is gone: remove its entry')
                hits = found.get(path, [])
                self.assertTrue(hits, 'the file no longer mentions anything forbidden: remove its entry')
                self.assertTrue({h[0] for h in hits} <= labels)
                self.assertLessEqual(len(hits), limit)

    def test_the_scanner_itself_recognises_every_forbidden_term(self):
        samples = {
            'llama.cpp': ['llama.cpp', 'run llama-server now', 'import llama_cpp'],
            'qwen': ['Qwen3-8B', 'a qwen model', 'QWEN'],
            'gguf model file': ['model.gguf', '*.gguf', 'GGUF weights'],
            'local model server address': ['http://127.0.0.1:8080/v1'],
            'OpenAI-style local endpoint': ['POST /v1/chat/completions', 'GET /v1/models'],
            'GOVOS_LLM_ setting': ['GOVOS_LLM_ENABLED=1', 'GOVOS_LLM_URL', 'GOVOS_LLM_MODEL', 'GOVOS_LLM_MODEL_PATH',
                                   'GOVOS_LLM_TIMEOUT_SECONDS'],
            'local provider class': ['class LocalQwenVerificationProvider:'],
            'old search provider': ['Tavily', 'TAVILY_API_KEY', 'tavily'],
            'vendor SDK import': ['import anthropic', 'from anthropic import Anthropic', 'import openai',
                                  'from openai import OpenAI'],
            'JS/TS vendor SDK import': ["import Anthropic from '@anthropic-ai/sdk'", 'import OpenAI from "openai"',
                                        "const x = require('openai')"],
            'vendor API host': ['https://api.anthropic.com/v1/messages', 'api.openai.com', 'https://api.tavily.com/search'],
        }
        self.assertEqual(set(samples), set(FORBIDDEN), 'a forbidden term has no sample here')
        for label, lines in samples.items():
            for line in lines:
                with self.subTest(label=label, line=line):
                    self.assertIn(label, {h[0] for h in scan_text(line)})
        for innocent in ('from anthropic_style import x', 'the openai-compatible word', 'import os, sys',
                         'We use the Claude CLI.', 'GOVOS_CLAUDE_ENABLED=1', 'llamas are animals'):
            with self.subTest(innocent=innocent):
                self.assertEqual(scan_text(innocent), [])

    # -------------------------------------------------------------- retired files and config
    def test_retired_verification_modules_are_gone(self):
        retired = {'client.py', 'llm_verifier.py', 'test_local_llm.py', 'prompts.py',
                   # the per-field local-model readers that the *_claude.py modules replaced
                   'attribution_llm.py', 'completeness_llm.py', 'designation_llm.py'}
        self.assertTrue(os.path.isdir(VERIFICATION), 'tools/exam_builder/verification moved? update this test')
        present = []
        for folder, dirs, files in os.walk(VERIFICATION):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            present += [_relative(os.path.join(folder, f)) for f in files if f in retired]
        self.assertEqual(present, [], 'retired local-model modules are back')

    def test_gitignore_has_no_model_weights_entry(self):
        path = os.path.join(REPO, '.gitignore')
        self.assertTrue(os.path.isfile(path))
        entries = [line.strip() for line in read(path).splitlines() if line.strip() and not line.lstrip().startswith('#')]
        self.assertEqual([e for e in entries if 'gguf' in e.lower()], [])
        self.assertNotIn('*.gguf', entries)

    def test_env_example_documents_the_claude_switch_and_holds_no_secret(self):
        path = os.path.join(REPO, '.env.example')
        self.assertTrue(os.path.isfile(path), '.env.example is the documented template for .env')
        text = read(path)
        self.assertIn('GOVOS_CLAUDE_ENABLED', text)
        key_shapes = [r'(?<![A-Za-z0-9])sk-[A-Za-z0-9_-]{8,}', r'tvly-', r'AKIA[0-9A-Z]{16}', r'gh[pousr]_[A-Za-z0-9]{20,}',
                      r'xox[abprs]-', r'AIza[0-9A-Za-z_-]{20,}', r'eyJ[A-Za-z0-9_-]{20,}\.', r'-----BEGIN [A-Z ]*KEY']
        for shape in key_shapes:
            self.assertIsNone(re.search(shape, text), 'a value in .env.example looks like a key: %s' % shape)
        assignments = []
        for number, line in enumerate(text.splitlines(), start=1):
            m = re.match(r'^\s*(#\s*)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$', line)
            if m:
                assignments.append((number, bool(m.group(1)), m.group(2), m.group(3)))
        self.assertTrue(any(name == 'GOVOS_CLAUDE_ENABLED' and not commented for _n, commented, name, _v in assignments),
                        'GOVOS_CLAUDE_ENABLED should be a live, documented line')
        for number, commented, name, value in assignments:
            with self.subTest(name=name, line=number):
                self.assertTrue(name.startswith('GOVOS_') or name == 'PORT',
                                'only GOVOS_* and PORT are read from .env, so nothing else belongs in its template')
                self.assertNotRegex(name, r'(?i)^(anthropic|openai)|API_KEY')
                if re.search(r'(?i)KEY|TOKEN|SECRET|PASSWORD|PASSWD', name):
                    self.assertEqual(value, '', 'a secret-shaped setting must be empty in the template')

    def test_dependency_manifests_declare_no_model_or_search_client(self):
        banned_py = re.compile(r'^(anthropic|openai|tavily[\w.-]*|llama[-_.]?cpp[\w.-]*|litellm|langchain[\w.-]*|ollama|'
                               r'claude[-_.]?(?:agent|code)[-_.]?sdk|google[-_.]generativeai|google[-_.]genai|cohere|'
                               r'mistralai|groq)$', re.I)
        names = []
        for raw in read(os.path.join(REPO, 'requirements.txt')).splitlines():
            line = raw.split('#', 1)[0].strip()
            if line:
                names.append(re.split(r'[\s<>=!~;\[@]', line, maxsplit=1)[0])
        self.assertTrue(names, 'requirements.txt should list Flask at least')
        self.assertEqual([n for n in names if banned_py.match(n)], [], 'requirements.txt declares a model/search client')

        banned_js = re.compile(r'^(?:@anthropic-ai/.*|anthropic|openai|tavily|@tavily/.*|@langchain/.*|langchain|ollama|'
                               r'llamaindex|@google/generative-ai|cohere-ai|@mistralai/.*|groq-sdk)$', re.I)
        pkg = json.loads(read(os.path.join(REPO, 'package.json')))
        declared = set()
        for section in ('dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies'):
            declared |= set((pkg.get(section) or {}))
        self.assertEqual(sorted(n for n in declared if banned_js.match(n)), [], 'package.json declares a model/search client')
        lock = os.path.join(REPO, 'package-lock.json')
        if os.path.isfile(lock):
            packages = (json.loads(read(lock)).get('packages') or {})
            installed = {k.rsplit('node_modules/', 1)[-1] for k in packages if k}
            self.assertEqual(sorted(n for n in installed if banned_js.match(n)), [],
                             'package-lock.json installs a model/search client')

    # -------------------------------------------------------------------- python code rules
    def test_no_python_module_imports_a_model_or_http_client_library(self):
        problems = []
        for path in python_files():
            for module, line in imported_modules(parse(path)):
                root = module.split('.')[0]
                if root in BANNED_IMPORT_ROOTS or module.startswith(BANNED_IMPORT_PREFIXES):
                    problems.append('%s:%d imports %s' % (_relative(path), line, module))
        self.assertEqual(problems, [], 'a module can reach a model or the network through a client library:\n  '
                         + '\n  '.join(problems))

    def test_the_only_code_that_starts_a_process_for_claude_is_the_runner(self):
        """`tools/claude_cli/runner.py` is the one place GovOS starts a process for Claude. The package's
        test-support files (the fake CLI, fixtures, test modules) may start processes of their own to test
        process handling, but only the Python interpreter or `taskkill` - never anything that names Claude,
        and never through a shell. Production modules, and every module outside the package, may not start
        a process that names Claude at all (inside the package: no process at all)."""
        offenders = []
        runner = os.path.join(CLAUDE_CLI, 'runner.py')
        self.assertTrue(os.path.isfile(runner))
        for path in python_files():
            if os.path.abspath(path) == os.path.abspath(runner):
                continue
            tree = parse(path)
            in_package = os.path.abspath(path).startswith(CLAUDE_CLI + os.sep)
            support = in_package and is_test_support(path)
            where = _relative(path)
            for module, line in imported_modules(tree):
                if in_package and not support and module.split('.')[0] in SPAWN_MODULES:
                    offenders.append('%s:%d imports %s' % (where, line, module))
            for node in ast.walk(tree):
                if not (isinstance(node, ast.Call) and SPAWN_CALLS.match(call_name(node))):
                    continue
                shown = ast.unparse(node)[:160]
                if support:
                    if not harmless_test_spawn(node):
                        offenders.append('%s:%d a test helper starts something other than python/taskkill: %s'
                                         % (where, node.lineno, shown))
                elif in_package:
                    offenders.append('%s:%d starts a process: %s' % (where, node.lineno, shown))
                elif re.search(r'claude', shown, re.I):
                    offenders.append('%s:%d starts a process that names claude: %s' % (where, node.lineno, shown))
        self.assertEqual(offenders, [], 'a process is started outside tools/claude_cli/runner.py:\n  ' + '\n  '.join(offenders))

    def test_the_process_rule_itself_distinguishes_claude_from_test_helpers(self):
        def call(src):
            return ast.parse(src, mode='eval').body

        self.assertTrue(harmless_test_spawn(call("subprocess.Popen([sys.executable, '-c', 'pass'])")))
        self.assertTrue(harmless_test_spawn(call("subprocess.run(['taskkill', '/PID', str(pid), '/T', '/F'], check=False)")))
        self.assertFalse(harmless_test_spawn(call("subprocess.Popen(['claude', '-p'])")))
        self.assertFalse(harmless_test_spawn(call("subprocess.Popen([sys.executable, 'claude.py'])")))
        self.assertFalse(harmless_test_spawn(call("subprocess.run('claude -p', shell=True)")))
        self.assertFalse(harmless_test_spawn(call("subprocess.run(['taskkill'], shell=True)")))
        self.assertFalse(harmless_test_spawn(call("subprocess.run(cmd)")))
        self.assertTrue(SPAWN_CALLS.match('subprocess.run') and SPAWN_CALLS.match('os.system') and SPAWN_CALLS.match('Popen'))
        self.assertFalse(SPAWN_CALLS.match('os.path.join'))
        self.assertTrue(is_test_support('/x/tools/claude_cli/test_runner.py') and is_test_support('fake_cli.py'))
        self.assertFalse(is_test_support('/x/tools/claude_cli/client.py'))

    def test_shell_true_appears_nowhere_in_the_claude_package(self):
        offenders = []
        for path in walk_files({'.py'}, root=CLAUDE_CLI):
            text = read(path)
            for node in ast.walk(parse(path)):
                if isinstance(node, ast.Call):
                    for kw in node.keywords:
                        if kw.arg == 'shell' and not (isinstance(kw.value, ast.Constant) and kw.value.value is False):
                            offenders.append('%s:%d shell=%s' % (_relative(path), node.lineno, ast.unparse(kw.value)))
            is_test = os.path.basename(path).startswith('test_')
            if not is_test:
                for number, line in enumerate(text.splitlines(), start=1):
                    if re.search(r'shell\s*=\s*(True|1)\b', line):
                        offenders.append('%s:%d %s' % (_relative(path), number, line.strip()[:100]))
        self.assertEqual(offenders, [])

    def test_the_runner_never_uses_a_shell(self):
        # the positive side of the previous test: the one place a process starts says shell=False
        tree = parse(os.path.join(CLAUDE_CLI, 'runner.py'))
        popens = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and call_name(n) == 'subprocess.Popen']
        self.assertTrue(popens, 'the runner starts the CLI with subprocess.Popen')
        for node in popens:
            kw = {k.arg: k.value for k in node.keywords}
            self.assertIn('shell', kw)
            self.assertTrue(isinstance(kw['shell'], ast.Constant) and kw['shell'].value is False)
            self.assertIsInstance(node.args[0], ast.Call, 'argv is a list built by the runner, never a string')


class MarkdownDocuments(unittest.TestCase):
    """Old-design mentions in documents are history, and must say so."""

    def test_the_markdown_rule_is_correct(self):
        # the checker is exercised on invented documents, so it is trusted when it is switched on
        old = 'The model ran on llama.cpp with a Qwen GGUF.\nSearch used Tavily.\n'
        self.assertEqual(len(markdown_violations('# Old design\n\n' + old)), 4)
        self.assertEqual(markdown_violations('> **ARCHIVAL** - describes the retired design.\n\n' + old), [])
        self.assertEqual(markdown_violations('# t\n' * 11 + '> Archival note\n' + old), [])
        self.assertEqual(len(markdown_violations('# t\n' * 12 + '> ARCHIVAL (too late: after line 12)\n' + old)), 4)
        self.assertEqual(markdown_violations('# Notes\nNothing old here, only the Claude CLI.\n'), [])
        guide = ('# Claude integration\n\nIt replaced Tavily.\n\n## Migration from the local model\n\n'
                 'Qwen and llama.cpp are gone.\n\n### Settings\n\nGOVOS_LLM_URL is ignored.\n\n## Operations\n\nNo mention.\n')
        bad = markdown_violations(guide, 'CLAUDE_CLI_INTEGRATION.md')
        self.assertEqual([(label, line) for label, line, _t in bad], [('old search provider', 3)])
        self.assertEqual(len(markdown_violations(guide, 'OTHER.md')), 4)

    @_markdown_gate
    def test_markdown_mentions_are_archival_or_migration_notes(self):
        found = all_markdown_violations()
        self.assertFalse(found, 'documents mention the retired design without an ARCHIVAL banner (first %d lines) '
                         'and outside the migration section of %s:\n%s'
                         % (MARKDOWN_BANNER_LINES, MIGRATION_GUIDE, describe(found)))

    @_markdown_gate
    def test_the_integration_guide_exists_where_the_code_points_to_it(self):
        self.assertTrue(os.path.isfile(os.path.join(REPO, MIGRATION_GUIDE)),
                        '%s is referenced by app.py, tools/claude_cli and .env.example' % MIGRATION_GUIDE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
