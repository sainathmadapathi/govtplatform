"""Build docs/GovOS_Guide.html -- one self-contained page that explains the whole project.

Two kinds of content, kept apart on purpose:

* **Written here** -- what GovOS is, how to read the code, a glossary, and the diagrams (inline SVG, so the
  page works offline and has no dependency). Change these when the architecture changes.
* **Read from the code every run** -- every tracked file, every top-level function / component / type /
  constant in the frontend, every class and function in the backend with its docstring, every API route,
  every SQLite table, every browser-storage key, every API call the page makes, every test and frontend
  check, the exam page's sections, the practice-engine registry, and the project's own design records
  (CLAUDE.md, PIPELINE.md and every audit). These can never drift from the code, because they are the code.

Run:  python tools/docs/build_guide.py            (also run by `npm run docs` and before every `npm run build`)
      python tools/docs/build_guide.py --quiet    (no output unless the page changed)

The page is rewritten only when its content changes (the commit and time in its stamp are not part of
that comparison), so re-running it, or committing, does not create noise in git.
"""
from __future__ import annotations

import ast
import hashlib
import html
import json
import os
import re
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import guide_text  # noqa: E402  (the hand-written, plain-language chapters)

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUT = os.path.join(ROOT, 'docs', 'GovOS_Guide.html')
QUIET = '--quiet' in sys.argv

esc = html.escape


def read(rel: str) -> str:
    with open(os.path.join(ROOT, rel), encoding='utf-8', errors='replace') as fh:
        return fh.read()


def git(*args: str) -> str:
    try:
        return subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return ''


def tracked_files() -> list[str]:
    files = [f for f in git('ls-files').splitlines() if f.strip()]
    if not files:   # not a git checkout: walk the tree instead
        for base, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in ('.git', 'node_modules', 'dist', '__pycache__', 'exam_data')]
            files += [os.path.relpath(os.path.join(base, n), ROOT).replace('\\', '/') for n in names]
    return sorted(f for f in files if os.path.exists(os.path.join(ROOT, f)))


def anchor(*parts: str) -> str:
    return re.sub(r'[^a-z0-9]+', '-', '-'.join(parts).lower()).strip('-')


# =============================================================================================== plain language
# tools/docs/plain.json holds a plain-English explanation of every declaration, written by reading its code, each
# stored with the fingerprint (span_hash) of the code it was written for. When the code changes the fingerprint
# no longer matches and the page says the explanation may be out of date -- it never silently describes old code.
#   python tools/docs/build_guide.py --stale   lists explanations whose code changed, and declarations with none
#   python tools/docs/build_guide.py --stamp   records the current fingerprint on explanations that have none
PLAIN_PATH = os.path.join(ROOT, 'tools', 'docs', 'plain.json')


def plain_key(rel: str, name: str) -> str:
    return f'{rel}::{name}'


def load_plain() -> dict:
    try:
        with open(PLAIN_PATH, encoding='utf-8') as fh:
            return json.load(fh).get('entries', {})
    except (OSError, ValueError):
        return {}


PLAIN = load_plain()
PLAIN_SEEN: dict = {}      # key -> current hash, for --stale / --stamp


def name_words(name: str) -> str:
    """'evaluatePostEligibility' -> 'evaluate post eligibility'; '_fetch_upsc_whatsnew' -> 'fetch upsc whatsnew'."""
    last = name.split(' > ')[-1].split('.')[-1]
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', last)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1 \2', s)
    return re.sub(r'[_\s]+', ' ', s).strip().lower()


KIND_PLAIN = {
    'component': 'A piece of the screen (a React component)',
    'function': 'A function (a named set of steps the code can run)',
    'method': 'A function that belongs to a class',
    'hook': 'A React hook (reusable behaviour a screen piece can plug in)',
    'type': 'A description of the shape some data must have (a TypeScript type)',
    'constant': 'A fixed value the code reads',
    'value': 'A value the code reads',
    'class': 'A class (data bundled with the functions that work on it)',
    'state': 'Something this screen piece remembers while it is open (React state)',
    'ref': 'A remembered handle that does not redraw the screen when it changes (React ref)',
    'memo': 'A value worked out once and reused until its inputs change',
    'handler': 'A function run when something happens (a click, a typed key, a reply arriving)',
    'effect': 'Work done after the screen is drawn (a React effect)',
    'check': 'A frontend check',
}


def plain_for(rel: str, name: str, kind: str, current_hash: str | None) -> tuple[str, str, str]:
    """(simple, tech, state) for a declaration: state is 'ok', 'stale' (written for code that has since changed)
    or 'name' (no explanation yet, so only what its kind and name say)."""
    key = plain_key(rel, name)
    if current_hash:
        PLAIN_SEEN.setdefault(key, current_hash)     # a name declared twice in one file: the first one is the key's
    entry = PLAIN.get(key)
    if entry and entry.get('text'):
        if current_hash and entry.get('hash') and entry['hash'] != PLAIN_SEEN.get(key, current_hash):
            return entry['text'], entry.get('tech', ''), 'stale'
        return entry['text'], entry.get('tech', ''), 'ok'
    return f'{KIND_PLAIN.get(kind, "A declaration")}; its name reads “{name_words(name)}”.', '', 'name'


# ---- links from the hand-written chapters into the reference
REF_INDEX: dict = {}       # bare name -> anchor of its reference entry (frontend first)
DOC_HEADINGS: set = set()  # CLAUDE.md headings, for {{doc:…}} links
WARNINGS: list = []


def ref_anchor(rel: str, name: str) -> str:
    return anchor('ref', rel, name)


def index_ref(rel: str, name: str):
    REF_INDEX.setdefault(name, ref_anchor(rel, name))


def rich(text: str) -> str:
    """The hand-written chapters' markup (see guide_text.py): Markdown inline, paragraphs, '- ' lists, plus
    [[name]] links into the reference and {{doc:Heading}} links into CLAUDE.md."""
    links: list[str] = []

    def ref(m):
        name = m.group(1)
        target = REF_INDEX.get(name)
        if not target:
            WARNINGS.append(f'no declaration named {name!r}')
            links.append(f'<code>{esc(name)}</code>')
        else:
            links.append(f'<a class="xref" href="#{target}"><code>{esc(name)}</code></a>')
        return f'\x01{len(links) - 1}\x01'

    def doc(m):
        title = m.group(1)
        if title not in DOC_HEADINGS:
            WARNINGS.append(f'no CLAUDE.md heading {title!r}')
        links.append(f'<a class="xref" href="#{anchor(anchor("doc", "CLAUDE.md"), title)}">{md_inline(title)}</a> (design notes)')
        return f'\x01{len(links) - 1}\x01'

    def inline(s: str) -> str:
        s = re.sub(r'\[\[([^\]]+)\]\]', ref, s)
        s = re.sub(r'\{\{doc:(.+?)\}\}', doc, s)
        return re.sub(r'\x01(\d+)\x01', lambda m: links[int(m.group(1))], md_inline(s))

    out = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = block.strip().split('\n')
        if lines[0].startswith('- '):
            items, cur = [], []
            for l in lines:
                if l.startswith('- '):
                    if cur:
                        items.append(' '.join(cur))
                    cur = [l[2:].strip()]
                else:
                    cur.append(l.strip())
            if cur:
                items.append(' '.join(cur))
            out.append('<ul>' + ''.join(f'<li>{inline(i)}</li>' for i in items) + '</ul>')
        else:
            out.append('<p>' + inline(' '.join(l.strip() for l in lines)) + '</p>')
    return ''.join(out)


# =============================================================================================== markdown
def md_inline(text: str) -> str:
    codes: list[str] = []

    def keep(m):
        codes.append('<code>' + esc(m.group(1)) + '</code>')
        return f'\x00{len(codes) - 1}\x00'
    text = re.sub(r'`([^`]+)`', keep, text)
    text = esc(text, quote=False)
    text = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', lambda m: f'<a href="{esc(m.group(2))}">{m.group(1)}</a>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'(?<![\w*])\*(?!\s)(.+?)(?<!\s)\*(?![\w*])', r'<em>\1</em>', text)
    return re.sub(r'\x00(\d+)\x00', lambda m: codes[int(m.group(1))], text)


def md_to_html(src: str, id_prefix: str, toc: list | None = None) -> str:
    """A small Markdown renderer for the project's own documents: headings, paragraphs, nested lists, tables,
    fenced code, block quotes and rules. No dependency."""
    lines = src.replace('\r\n', '\n').split('\n')
    out: list[str] = []
    i = 0
    para: list[str] = []
    list_stack: list[tuple[int, str]] = []   # (indent, 'ul'|'ol')
    item_open = False

    def flush_para():
        nonlocal para
        if para:
            out.append('<p>' + md_inline(' '.join(s.strip() for s in para)) + '</p>')
            para = []

    def close_lists(to_indent: int = -1):
        nonlocal item_open
        while list_stack and list_stack[-1][0] > to_indent:
            if item_open:
                out.append('</li>')
            out.append(f'</{list_stack.pop()[1]}>')
            item_open = bool(list_stack)

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith('```'):
            flush_para(); close_lists()
            body = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith('```'):
                body.append(lines[i]); i += 1
            out.append('<pre class="code">' + esc('\n'.join(body)) + '</pre>')
            i += 1
            continue
        m = re.match(r'^(#{1,6})\s+(.*)$', stripped)
        if m and not line.startswith(' '):
            flush_para(); close_lists()
            level = len(m.group(1))
            title = m.group(2).strip()
            hid = anchor(id_prefix, title)
            tag = min(6, level + 1)
            out.append(f'<h{tag} id="{hid}" class="md-h">{md_inline(title)}</h{tag}>')
            if toc is not None and level <= 3:
                toc.append((level, title, hid))
            i += 1
            continue
        if stripped.startswith('|') and i + 1 < len(lines) and re.match(r'^\s*\|?[\s:|-]+\|?\s*$', lines[i + 1]) and '-' in lines[i + 1]:
            flush_para(); close_lists()
            def cells(row):
                row = row.strip().strip('|')
                return [c.strip() for c in row.split('|')]
            head = cells(stripped)
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append(cells(lines[i])); i += 1
            out.append('<div class="table-wrap"><table><thead><tr>' + ''.join(f'<th>{md_inline(c)}</th>' for c in head) + '</tr></thead><tbody>'
                       + ''.join('<tr>' + ''.join(f'<td>{md_inline(c)}</td>' for c in r) + '</tr>' for r in rows) + '</tbody></table></div>')
            continue
        if re.match(r'^(-{3,}|\*{3,})$', stripped):
            flush_para(); close_lists(); out.append('<hr>'); i += 1; continue
        if stripped.startswith('>'):
            flush_para(); close_lists()
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(lines[i].strip()[1:].strip()); i += 1
            out.append('<blockquote>' + md_inline(' '.join(quote)) + '</blockquote>')
            continue
        lm = re.match(r'^(\s*)([-*+]|\d+[.)])\s+(.*)$', line)
        if lm:
            flush_para()
            indent = len(lm.group(1).replace('\t', '    '))
            kind = 'ol' if lm.group(2)[0].isdigit() else 'ul'
            if not list_stack or indent > list_stack[-1][0]:
                out.append(f'<{kind}>'); list_stack.append((indent, kind)); item_open = False
            else:
                close_lists(indent)
                if not list_stack:
                    out.append(f'<{kind}>'); list_stack.append((indent, kind)); item_open = False
            if item_open:
                out.append('</li>')
            text = [lm.group(3)]
            i += 1
            while i < len(lines) and lines[i].strip() and not re.match(r'^\s*([-*+]|\d+[.)])\s+', lines[i]) \
                    and not lines[i].strip().startswith(('```', '|', '#')) and (lines[i].startswith(' ') or lines[i].startswith('\t')):
                text.append(lines[i].strip()); i += 1
            out.append('<li>' + md_inline(' '.join(text)))
            item_open = True
            continue
        if not stripped:
            flush_para()
            # a blank line inside a list keeps the list open only if the next line continues it
            nxt = next((l for l in lines[i + 1:] if l.strip()), '')
            if list_stack and not (re.match(r'^\s*([-*+]|\d+[.)])\s+', nxt) or nxt.startswith(' ')):
                close_lists()
            i += 1
            continue
        if list_stack and (line.startswith(' ') or line.startswith('\t')):
            out.append(' ' + md_inline(stripped))   # continuation of the open item
            i += 1
            continue
        close_lists()
        para.append(line)
        i += 1
    flush_para(); close_lists()
    return '\n'.join(out)


# =============================================================================================== frontend
TS_DECL = re.compile(r'^(export\s+)?(default\s+)?(declare\s+)?(async\s+)?(const|let|var|function|interface|type|class|enum)\s+([A-Za-z_$][\w$]*)')
BANNER = re.compile(r'^//\s*={6,}\s*$')


def ts_kind(kw: str, name: str, line: str, nxt: str) -> str:
    if kw in ('interface', 'type'):
        return 'type'
    if kw == 'enum':
        return 'type'
    if kw == 'class':
        return 'class'
    if name.startswith('use') and name[3:4].isupper():
        return 'hook'
    if name[:1].isupper() and (('React.FC' in line) or kw == 'function' or re.search(r'=\s*\(?\s*\{?[^=]*\}?\s*\)?\s*=>\s*\(?\s*$', line) or '=> (' in line) \
            and not re.match(r'^[A-Z0-9_]+$', name):
        return 'component'
    if re.match(r'^[A-Z][A-Z0-9_]+$', name):
        return 'constant'
    if kw == 'function' or '=>' in line or '=> ' in nxt or re.search(r'=\s*(async\s*)?\(', line) or re.search(r'=\s*(async\s+)?function', line):
        return 'function'
    return 'value'


def clean_comment(lines: list[str]) -> str:
    text = []
    for l in lines:
        s = l.strip()
        s = re.sub(r'^/\*\*?', '', s)
        s = re.sub(r'\*/$', '', s)
        s = re.sub(r'^\*\s?', '', s)
        s = re.sub(r'^//+\s?', '', s)
        if re.match(r'^=+$', s.strip()):
            continue
        text.append(s.rstrip())
    return re.sub(r'\n{3,}', '\n\n', '\n'.join(text)).strip()


def scan_ts(rel: str) -> dict:
    """Every top-level declaration of a TypeScript file with its line, kind and the comment written above it,
    grouped under the file's own `// ===== Name` banners."""
    lines = read(rel).split('\n')
    groups: list[dict] = [{'title': 'Top of file', 'note': '', 'line': 1, 'items': []}]
    pending: list[str] = []
    in_block = False
    i = 0
    while i < len(lines):
        line = lines[i]
        s = line.strip()
        if BANNER.match(line):
            # banner: // ===== / // Title — note / // =====
            j = i + 1
            head = []
            while j < len(lines) and lines[j].startswith('//') and not BANNER.match(lines[j]):
                head.append(lines[j]); j += 1
            if j < len(lines) and BANNER.match(lines[j]) and head:
                title_line = clean_comment(head[:1])
                title, _, note = title_line.partition(' — ')
                rest = clean_comment(head[1:])
                groups.append({'title': title.strip() or 'Section', 'note': (note + ('\n' + rest if rest else '')).strip(), 'line': i + 1, 'items': []})
                pending = []
                i = j + 1
                continue
        if in_block:
            pending.append(line)
            if '*/' in s:
                in_block = False
            i += 1
            continue
        if s.startswith('/*'):
            pending = [line]
            in_block = '*/' not in s[2:]
            i += 1
            continue
        if s.startswith('//') and line.startswith('//'):
            pending.append(line)
            i += 1
            continue
        if not s:
            pending = []
            i += 1
            continue
        m = TS_DECL.match(line)
        if m:
            kw, name = m.group(5), m.group(6)
            nxt = lines[i + 1] if i + 1 < len(lines) else ''
            sig = line.strip()
            if len(sig) > 220:
                sig = sig[:217] + '…'
            groups[-1]['items'].append({'name': name, 'kind': ts_kind(kw, name, line, nxt), 'line': i + 1,
                                        'exported': bool(m.group(1)), 'sig': sig, 'doc': clean_comment(pending)})
        pending = []
        i += 1
    # each declaration runs to the line before the next one; its inner declarations are read from that span
    flat = [it for g in groups for it in g['items']]
    for k, it in enumerate(flat):
        it['end'] = (flat[k + 1]['line'] - 1) if k + 1 < len(flat) else len(lines)
        it['hash'] = span_hash(lines, it['line'], it['end'])
        it['inner'] = (scan_inner(lines, it['line'], it['end']) if it['kind'] in ('component', 'function', 'hook')
                       else scan_methods(lines, it['line'], it['end']) if (it['kind'] == 'class' or (it['kind'] == 'value' and lines[it['line'] - 1].rstrip().endswith('{')))
                       else [])
    groups = [g for g in groups if g['items'] or g['note']]
    return {'file': rel, 'lines': len(lines), 'groups': groups}


INNER_DECL = re.compile(r'^  (?:const|let|var|async function|function)\s+(\[[^\]]*\]|[A-Za-z_$][\w$]*)\s*(?::[^=]*)?=?\s*(.*)$')
INNER_EFFECT = re.compile(r'^  (?:React\.)?(useEffect|useLayoutEffect)\(')


def scan_inner(lines: list[str], start: int, end: int) -> list[dict]:
    """What a component or function keeps inside itself, one indentation level in (two spaces): its state
    (useState pairs), refs, memoised values, handlers and helpers, and its effects -- each with its line and the
    comment written above it. Deeper nesting is left to the code."""
    out = []
    pending: list[str] = []
    for n in range(start, min(end, len(lines))):          # 0-based index n is line n + 1
        line = lines[n]
        s = line.strip()
        if s.startswith('//') and line.startswith('  //') and not line.startswith('   '):
            pending.append(line); continue
        if s.startswith(('/*', '*')) and line.startswith('  ') and not line.startswith('    '):
            pending.append(line); continue
        m = INNER_DECL.match(line)
        if m:
            target, rest = m.group(1), m.group(2)
            if target.startswith('['):
                names = [x.strip() for x in target.strip('[]').split(',') if x.strip()]
                if 'useState' in rest or 'useReducer' in rest:
                    out.append({'kind': 'state', 'name': names[0] if names else target, 'line': n + 1, 'doc': clean_comment(pending),
                                'sig': s[:200]})
            else:
                kind = ('ref' if 'useRef' in rest else 'memo' if ('useMemo' in rest or 'useCallback' in rest)
                        else 'handler' if (re.match(r'^(handle|on)[A-Z]', target) or ('=>' in rest) or line.startswith('  function') or line.startswith('  async function'))
                        else 'value')
                out.append({'kind': kind, 'name': target, 'line': n + 1, 'doc': clean_comment(pending), 'sig': s[:200]})
            pending = []
            continue
        e = INNER_EFFECT.match(line)
        if e:
            out.append({'kind': 'effect', 'name': e.group(1), 'line': n + 1, 'doc': clean_comment(pending), 'sig': ''})
            pending = []
            continue
        if s and not line.startswith('    '):
            pending = []
    for k, o in enumerate(out):
        o['end'] = (out[k + 1]['line'] - 1) if k + 1 < len(out) else end
        o['hash'] = span_hash(lines, o['line'], o['end'])
    return out


OBJ_METHOD = re.compile(r'^  (?:(?:private|public|protected|static|readonly|async|get|set)\s+)*([A-Za-z_$][\w$]*)\s*(?:<[^>]*>)?\([^)]*\)?\s*(?::[^{]*)?\{?\s*$|^  (?:async\s+)?([A-Za-z_$][\w$]*)\s*\(')
OBJ_ARROW = re.compile(r'^  ([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?(?:\([^)]*\)|[A-Za-z_$][\w$]*)\s*(?::[^=]*)?=>')


def scan_methods(lines: list[str], start: int, end: int) -> list[dict]:
    """The methods of an object literal such as `export const storageService = { … }` (one level in), each with its
    line, its own span's fingerprint and the comment above it."""
    found = []
    pending: list[str] = []
    for n in range(start, min(end, len(lines))):
        line = lines[n]
        s = line.strip()
        if line.startswith('  //') or (line.startswith('  /*') or (line.startswith('   *') and not line.startswith('    '))):
            pending.append(line); continue
        m = OBJ_ARROW.match(line) or OBJ_METHOD.match(line)
        if m and not line.startswith('   ') and not re.match(r'^  (if|for|while|switch|return|catch)\b', line):
            name = next(g for g in m.groups() if g)
            found.append({'kind': 'method', 'name': name, 'line': n + 1, 'doc': clean_comment(pending), 'sig': s[:200]})
            pending = []
            continue
        if s and not line.startswith('    '):
            pending = []
    for k, f in enumerate(found):
        f['end'] = (found[k + 1]['line'] - 1) if k + 1 < len(found) else end
        f['hash'] = span_hash(lines, f['line'], f['end'])
    return found


def span_hash(lines: list[str], start: int, end: int) -> str:
    """A fingerprint of a declaration's own code (start..end, 1-based, inclusive), blind to trailing spaces, so a
    plain-language explanation can tell when the code it describes has changed since it was written."""
    body = '\n'.join(l.rstrip() for l in lines[start - 1:end]).strip()
    return hashlib.sha1(body.encode('utf-8')).hexdigest()[:12]


def exam_sections() -> tuple[list, list]:
    src = read('src/ui.tsx')
    def grab(name):
        m = re.search(name + r'\s*=\s*\[(.*?)\n\];', src, re.S)
        return [{'num': int(a), 'label': b, 'under': c} for a, b, c in
                re.findall(r"num:\s*(\d+),\s*label:\s*'([^']+)'(?:,\s*icon:\s*\w+)?(?:,\s*under:\s*'([^']+)')?", m.group(1))] if m else []
    return grab('const EXAM_SECTIONS'), grab('const REFERENCE_SECTIONS')


def practice_engines() -> list:
    src = read('src/ui.tsx')
    m = re.search(r'const PRACTICE_ENGINES[^=]*=\s*\{(.*?)\n\};', src, re.S)
    if not m:
        return []
    body = m.group(1)
    out = []
    for em in re.finditer(r"['\"]?(exam-[\w-]+)['\"]?\s*:\s*\{(.*?)\n  \}", body, re.S):
        block = em.group(2)
        comp = re.search(r'(?:Engine|engine|component)\s*:\s*(\w+)', block)
        label = re.search(r"(?:label|name|title)\s*:\s*'([^']+)'", block)
        out.append({'id': em.group(1), 'engine': comp.group(1) if comp else '', 'label': label.group(1) if label else ''})
    return out


def storage_keys() -> list:
    seen: dict = {}
    for rel in ('src/services.ts', 'src/ui.tsx', 'src/main.tsx'):
        for n, line in enumerate(read(rel).split('\n'), 1):
            for k in re.findall(r"['\"`](govos_[a-z0-9_]+)['\"`]", line):
                seen.setdefault(k, []).append(f'{rel}:{n}')
    return sorted(seen.items())


def api_calls() -> list:
    seen: dict = {}
    for rel in ('src/services.ts', 'src/ui.tsx', 'src/main.tsx'):
        for n, line in enumerate(read(rel).split('\n'), 1):
            for p in re.findall(r"['\"`](/api/[A-Za-z0-9_\-/{}$.]+)", line):
                p = re.sub(r'\$\{[^}]*\}', '<id>', p).rstrip('/')
                seen.setdefault(p, []).append(f'{rel}:{n}')
    return sorted(seen.items())


def frontend_checks() -> list:
    out = []
    for rel in tracked_files():
        if rel.startswith('tools/frontend_checks/') and rel.endswith('.ts') and 'fixture' not in rel and rel != 'tools/frontend_checks/stub.ts':
            src = read(rel)
            names = re.findall(r"check\(\s*[`'\"]([^`'\"]{3,200})", src)
            head = re.match(r'\s*/\*\*?(.*?)\*/', src, re.S)
            out.append({'file': rel, 'checks': names, 'doc': clean_comment(head.group(0).split('\n')) if head else ''})
    return out


# =============================================================================================== backend
def first_para(doc: str | None) -> str:
    return (doc or '').strip()


def py_signature(node) -> str:
    try:
        return f'{node.name}({ast.unparse(node.args)})'
    except Exception:
        return node.name


def decorator_text(d) -> str:
    try:
        return ast.unparse(d)
    except Exception:
        return ''


def scan_py(rel: str) -> dict:
    src = read(rel)
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        return {'file': rel, 'lines': src.count('\n') + 1, 'doc': f'(could not parse: {e})', 'items': []}
    items = []
    src_lines = src.split('\n')

    def h(node):
        first = min([node.lineno] + [d.lineno for d in getattr(node, 'decorator_list', [])])
        return span_hash(src_lines, first, getattr(node, 'end_lineno', node.lineno) or node.lineno)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            items.append({'kind': 'function', 'name': node.name, 'line': node.lineno, 'end': node.end_lineno, 'hash': h(node), 'sig': py_signature(node),
                          'doc': first_para(ast.get_docstring(node)), 'decorators': [decorator_text(d) for d in node.decorator_list]})
        elif isinstance(node, ast.ClassDef):
            methods = []
            for sub in node.body:
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    methods.append({'name': sub.name, 'line': sub.lineno, 'end': sub.end_lineno, 'hash': h(sub), 'sig': py_signature(sub),
                                    'doc': first_para(ast.get_docstring(sub)), 'decorators': [decorator_text(d) for d in sub.decorator_list]})
            bases = ', '.join(decorator_text(b) for b in node.bases)
            items.append({'kind': 'class', 'name': node.name, 'line': node.lineno, 'end': node.end_lineno, 'hash': h(node),
                          'sig': f'class {node.name}({bases})' if bases else f'class {node.name}',
                          'doc': first_para(ast.get_docstring(node)), 'methods': methods})
        elif isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                and re.match(r'^[A-Z][A-Z0-9_]+$', node.targets[0].id):
            try:
                value = ast.unparse(node.value)
            except Exception:
                value = ''
            items.append({'kind': 'constant', 'name': node.targets[0].id, 'line': node.lineno, 'end': node.end_lineno,
                          'hash': span_hash(src_lines, node.lineno, node.end_lineno or node.lineno),
                          'sig': (node.targets[0].id + ' = ' + (value if len(value) < 160 else value[:157] + '…')), 'doc': ''})
    return {'file': rel, 'lines': src.count('\n') + 1, 'doc': first_para(ast.get_docstring(tree)), 'items': items}


def routes() -> list:
    out = []
    for rel in tracked_files():
        if not rel.endswith('.py') or '/test_' in rel or rel.startswith('test_'):
            continue
        src = read(rel)
        if '.route(' not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        prefixes = {}
        for m in re.finditer(r"(\w+)\s*=\s*Blueprint\([^)]*url_prefix\s*=\s*['\"]([^'\"]+)['\"]", src):
            prefixes[m.group(1)] = m.group(2)
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            decos = [decorator_text(d) for d in node.decorator_list]
            for d in node.decorator_list:
                if isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr == 'route' and d.args:
                    owner = decorator_text(d.func.value)
                    try:
                        path = ast.literal_eval(d.args[0])
                    except Exception:
                        path = decorator_text(d.args[0])
                    methods = ['GET']
                    for kw in d.keywords:
                        if kw.arg == 'methods':
                            try:
                                methods = list(ast.literal_eval(kw.value))
                            except Exception:
                                methods = [decorator_text(kw.value)]
                    full = prefixes.get(owner, '') + path
                    admin = any('admin_required' in x for x in decos) or 'admin_denied()' in ast.get_source_segment(src, node) if ast.get_source_segment(src, node) else False
                    out.append({'path': full, 'methods': methods, 'func': node.name, 'file': rel, 'line': node.lineno,
                                'doc': first_para(ast.get_docstring(node)), 'admin': admin})
    return sorted(out, key=lambda r: (r['path'], r['methods']))


def route_words(r: dict) -> str:
    """What a route does: its handler's plain explanation where one is written, else its docstring's first paragraph."""
    entry = PLAIN.get(plain_key(r['file'], r['func']))
    if entry and entry.get('text'):
        return entry['text']
    return r['doc'].split('\n\n')[0]


def sqlite_tables() -> list:
    out = {}
    for rel in tracked_files():
        if not rel.endswith('.py') or 'test_' in rel:
            continue
        src = read(rel)
        for m in re.finditer(r'CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n\s*\)', src, re.S):
            name, body = m.group(1), m.group(2)
            cols = []
            for raw in body.split('\n'):
                s = raw.strip().rstrip(',')
                if not s or re.match(r'^(PRIMARY|FOREIGN|UNIQUE|CHECK|CONSTRAINT)\b', s, re.I):
                    continue
                parts = s.split(None, 1)
                cols.append((parts[0], parts[1] if len(parts) > 1 else ''))
            line = src[:m.start()].count('\n') + 1
            out.setdefault(name, {'name': name, 'file': rel, 'line': line, 'cols': cols})
    return sorted(out.values(), key=lambda t: t['name'])


def py_tests() -> list:
    out = []
    for rel in tracked_files():
        base = rel.rsplit('/', 1)[-1]
        if not (rel.endswith('.py') and base.startswith('test_')):
            continue
        try:
            tree = ast.parse(read(rel))
        except SyntaxError:
            continue
        classes, loose = [], []
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                tests = [(s.name, s.lineno, first_para(ast.get_docstring(s))) for s in node.body
                         if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef)) and s.name.startswith('test')]
                if tests:
                    classes.append({'name': node.name, 'line': node.lineno, 'doc': first_para(ast.get_docstring(node)), 'tests': tests})
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith('test'):
                loose.append((node.name, node.lineno, first_para(ast.get_docstring(node))))
        n = sum(len(c['tests']) for c in classes) + len(loose)
        if n:
            out.append({'file': rel, 'doc': first_para(ast.get_docstring(tree)), 'classes': classes, 'loose': loose, 'count': n})
    return out


# =============================================================================================== files
def describe_file(rel: str) -> str:
    """One line on what a file is: its own module docstring / header comment, else its kind."""
    if rel.endswith('.py'):
        try:
            doc = ast.get_docstring(ast.parse(read(rel))) or ''
            return doc.strip().split('\n\n')[0].replace('\n', ' ')[:400]
        except SyntaxError:
            return ''
    if rel.endswith(('.ts', '.tsx', '.mjs', '.js')):
        src = '\n'.join(l for l in read(rel).split('\n') if not l.startswith('///')).lstrip()
        m = re.match(r'/\*\*?(.*?)\*/', src, re.S)
        if m:
            return clean_comment(m.group(0).split('\n')).split('\n\n')[0].replace('\n', ' ')[:400]
        lines = []
        for l in src.split('\n'):
            if l.startswith('//'):
                lines.append(l)
            elif lines:
                break
        return clean_comment(lines).split('\n\n')[0].replace('\n', ' ')[:400]
    if rel.endswith('.md'):
        for l in read(rel).split('\n'):
            if l.startswith('#'):
                return l.lstrip('# ').strip()
    return ''


def file_lines(rel: str) -> int:
    if rel.endswith(('.png', '.jpg', '.db', '.ico', '.pdf', '.woff', '.woff2')):
        return 0
    try:
        return read(rel).count('\n') + 1
    except OSError:
        return 0


# =============================================================================================== diagrams
def svg_flow(view_w: int, view_h: int, nodes: list, edges: list, groups: list = (), caption: str = '') -> str:
    """Boxes and elbow arrows. nodes: (id, x, y, w, h, text, tone); text lines split on '\\n', the first bold.
    edges: (from, to, label, opts) with opts a string of flags: 'dash', 'h' / 'v' to force the exit side."""
    pos = {n[0]: n for n in nodes}
    parts = [f'<svg class="flow" viewBox="0 0 {view_w} {view_h}" role="img" aria-label="{esc(caption)}" xmlns="http://www.w3.org/2000/svg">',
             '<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
             '<path d="M0 0 L10 5 L0 10 z" class="ah"/></marker></defs>']
    for gx, gy, gw, gh, glabel in groups:
        parts.append(f'<rect class="grp" x="{gx}" y="{gy}" width="{gw}" height="{gh}" rx="18"/>'
                     f'<text class="grp-l" x="{gx + 14}" y="{gy + 20}">{esc(glabel)}</text>')
    labels = []
    for e in edges:
        a, b, label = e[0], e[1], e[2] if len(e) > 2 else ''
        opts = e[3] if len(e) > 3 else ''
        _, ax, ay, aw, ah, *_ = pos[a]
        _, bx, by, bw, bh, *_ = pos[b]
        acx, acy, bcx, bcy = ax + aw / 2, ay + ah / 2, bx + bw / 2, by + bh / 2
        horiz = 'h' in opts or ('v' not in opts and abs(bcx - acx) > abs(bcy - acy))
        if horiz:
            sx = ax + aw if bcx > acx else ax
            ex = bx if bcx > acx else bx + bw
            sy, ey = acy, bcy
            mx = (sx + ex) / 2
            d = f'M{sx} {sy} H{mx} V{ey} H{ex}' if abs(sy - ey) > 1 else f'M{sx} {sy} H{ex}'
            lx, ly = mx, (sy + ey) / 2 if abs(sy - ey) > 1 else sy
        else:
            sy = ay + ah if bcy > acy else ay
            ey = by if bcy > acy else by + bh
            sx, ex = acx, bcx
            my = (sy + ey) / 2
            d = f'M{sx} {sy} V{my} H{ex} V{ey}' if abs(sx - ex) > 1 else f'M{sx} {sy} V{ey}'
            lx, ly = (sx + ex) / 2 if abs(sx - ex) > 1 else sx, my
        parts.append(f'<path class="edge{" dash" if "dash" in opts else ""}" d="{d}" marker-end="url(#ah)"/>')
        if label:
            w = 7.2 * len(label) + 14
            labels.append(f'<g class="el"><rect x="{lx - w / 2}" y="{ly - 11}" width="{w}" height="20" rx="10"/>'
                          f'<text x="{lx}" y="{ly + 4}">{esc(label)}</text></g>')
    for nid, x, y, w, h, text, tone in nodes:
        lines = text.split('\n')
        parts.append(f'<g class="node t-{tone}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12"/>')
        total = len(lines)
        for k, ln in enumerate(lines):
            ty = y + h / 2 + (k - (total - 1) / 2) * 16 + 5
            parts.append(f'<text x="{x + w / 2}" y="{ty}" class="{"nt" if k == 0 else "ns"}">{esc(ln)}</text>')
        parts.append('</g>')
    parts += labels
    parts.append('</svg>')
    return f'<figure class="diagram">{"".join(parts)}<figcaption>{esc(caption)}</figcaption></figure>'


def diagrams() -> dict:
    d = {}
    d['architecture'] = svg_flow(1000, 560, [
        ('main', 40, 70, 200, 56, 'main.tsx\nApp shell, modals, navigate()', 'ui'),
        ('ui', 40, 200, 200, 56, 'ui.tsx\nevery component and view', 'ui'),
        ('data', 40, 330, 200, 56, 'data.ts + types.ts\nexam register, every type', 'ui'),
        ('services', 285, 200, 200, 56, 'services.ts\nstorage, eligibility, API client', 'ui'),
        ('ls', 285, 330, 200, 56, 'localStorage\nthe source of truth', 'db'),
        ('vite', 565, 60, 200, 56, 'vite build\n→ dist/index.html (one file)', 'build'),
        ('flask', 565, 200, 200, 56, 'app.py (Flask)\nAPI + serves the page', 'api'),
        ('sqlite', 565, 330, 200, 56, 'govos.db (SQLite)\ncopy + registry + caches', 'db'),
        ('ext', 810, 60, 170, 56, 'Official sites\nSSC, UPSC, feeds', 'ext'),
        ('claude', 810, 200, 170, 56, 'tools/claude_cli\ngateway + job queue', 'claude'),
        ('cli', 810, 330, 170, 56, 'Claude CLI\nhost login, subprocess', 'claude'),
        ('builder', 810, 460, 170, 56, 'exam_builder\nbuild-time pipeline', 'build'),
    ], [
        ('main', 'ui', 'renders'), ('ui', 'data', 'reads'), ('ui', 'services', 'calls'),
        ('services', 'ls', 'writes first'), ('services', 'flask', 'fetch /api/*'),
        ('vite', 'flask', 'served at /', 'dash'), ('flask', 'sqlite', 'SQL'),
        ('flask', 'claude', 'jobs'), ('claude', 'cli', 'array args, stdin'),
        ('flask', 'ext', 'public addresses only'), ('builder', 'sqlite', 'exam_registry'),
    ], [(20, 40, 490, 380, 'Browser — React single-page app'), (545, 40, 440, 500, 'Server and build tools')],
        'Figure 1. The whole system: the page writes the browser first, the server keeps a copy; Claude is called only through one gateway.')

    d['pipeline'] = svg_flow(1000, 500, [
        ('c1', 20, 50, 210, 54, 'Authority websites\nnotices, exam pages, PDFs', 'ext'),
        ('c2', 20, 140, 210, 54, 'Discovery\nauthority first, then the exam', 'build'),
        ('c3', 20, 230, 210, 54, 'Readers\ndates, pattern, syllabus, PYQ…', 'build'),
        ('c4', 20, 320, 210, 54, 'Evidence + completeness\nquotes re-checked', 'gate'),
        ('c5', 20, 410, 210, 54, 'Publication gate\nnothing unsourced passes', 'gate'),
        ('s1', 270, 50, 210, 54, 'data.ts register\nauthored exams', 'db'),
        ('s2', 270, 140, 210, 54, 'exam_registry\nmachine-read exams', 'db'),
        ('s3', 270, 230, 210, 54, 'live_feed_cache\nnotice boards, link health', 'db'),
        ('s4', 270, 320, 210, 54, 'Verifier changes\nrevisions, additions', 'db'),
        ('s5', 270, 410, 210, 54, 'claude_jobs\nslow work as jobs', 'db'),
        ('v1', 520, 50, 210, 54, 'Bundled into the page\n(no request needed)', 'api'),
        ('v2', 520, 140, 210, 54, 'GET /api/exams', 'api'),
        ('v3', 520, 230, 210, 54, 'GET /api/resources/live/*', 'api'),
        ('v4', 520, 320, 210, 54, '/api/syllabus/*\n/api/resources/additions', 'api'),
        ('v5', 520, 410, 210, 54, 'POST /api/claude/ask', 'api'),
        ('w1', 770, 50, 210, 54, 'Home & Exam Finder', 'ui'),
        ('w2', 770, 140, 210, 54, 'Exam page\n13 parts + 4 references', 'ui'),
        ('w3', 770, 230, 210, 54, 'Official Links, Resources', 'ui'),
        ('w4', 770, 320, 210, 54, 'Syllabus, Library\n(with REVISED badges)', 'ui'),
        ('w5', 770, 410, 210, 54, 'Ask GovOS AI\nper-fact evidence', 'ui'),
    ], [('c1', 'c2'), ('c2', 'c3'), ('c3', 'c4'), ('c4', 'c5'), ('c5', 's2', 'published', 'h'),
        ('s1', 'v1'), ('v1', 'w1'), ('s2', 'v2'), ('v2', 'w2'), ('s3', 'v3'), ('v3', 'w3'), ('s4', 'v4'), ('v4', 'w4'), ('s5', 'v5'), ('v5', 'w5')],
        [(10, 18, 230, 470, 'Collect (build time)'), (260, 18, 230, 470, 'Store'), (510, 18, 230, 470, 'Serve'), (760, 18, 230, 470, 'Show')],
        'Figure 2. How a fact reaches a candidate. PIPELINE.md (below, in Design records) describes every stage in detail.')

    d['navigation'] = svg_flow(1000, 470, [
        ('h', 20, 40, 180, 50, 'Header pills', 'ui'),
        ('n', 20, 110, 180, 50, 'Alert "Take action"', 'ui'),
        ('a', 20, 180, 180, 50, 'Assistant action button', 'ui'),
        ('c', 20, 250, 180, 50, 'Home cards & links', 'ui'),
        ('nav', 250, 145, 230, 70, 'navigate(tab, section, examId)\nthe single entry point', 'api'),
        ('map', 250, 290, 230, 70, 'Practice / Resources / Planner\n→ the exam page, part 9 / 8 / 7', 'gate'),
        ('res', 530, 145, 230, 70, 'Resolve the exam\nassistant or notification destination', 'gate'),
        ('none', 530, 290, 230, 70, 'Exam not held?\nopen nothing, show a notice', 'warn'),
        ('tab', 800, 46, 190, 90, 'activeTab\nFINDER, MY_EXAMS,\nCOMPARE, CALENDAR,\nAI_ASSISTANT, ADMIN', 'ui'),
        ('exam', 800, 210, 190, 70, 'ExamDetailView\nkey = exam.id (fresh state)', 'ui'),
        ('sec', 800, 350, 190, 70, 'Section by stable number\n1–17 (see the table)', 'ui'),
    ], [('h', 'nav', '', 'h'), ('n', 'nav', '', 'h'), ('a', 'nav', '', 'h'), ('c', 'nav', '', 'h'),
        ('nav', 'map', 'exam-scoped tab?'), ('nav', 'res', 'exam tab'), ('res', 'none', 'not found'),
        ('res', 'tab', 'other views'), ('res', 'exam', 'found'), ('exam', 'sec', 'initialSection')], [],
        'Figure 3. Navigation. There is no router: one activeTab string, and every button goes through navigate().')

    d['evidence'] = svg_flow(1000, 640, [
        ('q1', 40, 30, 380, 54, 'Does it have a source URL or quoted words?', 'gate'),
        ('q2', 40, 120, 380, 54, 'Is the value flagged as not in its quote?', 'gate'),
        ('q3', 40, 210, 380, 54, 'Was it replaced by a later statement?', 'gate'),
        ('q4', 40, 300, 380, 54, 'Is it marked OFFICIALLY_VERIFIED?', 'gate'),
        ('q5', 40, 390, 380, 54, 'Does it have a URL and a page or a quote?', 'gate'),
        ('q6', 40, 480, 380, 54, 'Do the quoted words contain the value?', 'gate'),
        ('o1', 560, 30, 260, 54, 'UNVERIFIED\n"No official source on record"', 'warn'),
        ('o2', 560, 120, 260, 54, 'UNSUPPORTED\n"Not in the quoted words"', 'warn'),
        ('o3', 560, 210, 260, 54, 'SUPERSEDED\n"Not the governing statement"', 'warn'),
        ('o4', 560, 300, 260, 54, 'UNDER_VERIFICATION\n"Verification pending"', 'warn'),
        ('o5', 560, 390, 260, 54, 'UNVERIFIED\n"Source incomplete"', 'warn'),
        ('o6', 560, 480, 260, 54, 'VERIFIED\n"Officially verified"', 'ok'),
        ('o7', 40, 570, 380, 54, 'UNSUPPORTED', 'warn'),
    ], [('q1', 'o1', 'no'), ('q1', 'q2', 'yes'), ('q2', 'o2', 'yes'), ('q2', 'q3', 'no'), ('q3', 'o3', 'yes'), ('q3', 'q4', 'no'),
        ('q4', 'o4', 'no'), ('q4', 'q5', 'yes'), ('q5', 'o5', 'no'), ('q5', 'q6', 'yes'), ('q6', 'o6', 'yes'), ('q6', 'o7', 'no')], [],
        'Figure 4. factVerification(provenance, claim) in ui.tsx — the one rule (shared with the server) that decides whether a fact may be called verified.')

    d['persistence'] = svg_flow(1000, 330, [
        ('act', 20, 40, 170, 56, 'Candidate acts\ntrack, save, submit', 'ui'),
        ('svc', 230, 40, 200, 56, 'storageService\n(services.ts)', 'ui'),
        ('ls', 230, 170, 200, 56, 'localStorage\nwritten first', 'db'),
        ('post', 480, 40, 200, 56, 'POST /api/sqlite/*\nfire-and-forget', 'api'),
        ('merge', 730, 40, 240, 56, 'Merge rules in app.py\npresent values only', 'gate'),
        ('db', 730, 170, 240, 56, 'govos.db\nthe server copy', 'db'),
        ('fail', 480, 170, 200, 56, 'Local write refused?\nscreen says "not kept"', 'warn'),
        ('load', 20, 250, 170, 56, 'Page load', 'ui'),
        ('rec', 480, 250, 490, 56, 'Reconcile: the browser list stands; server data is laid over, never swapped in', 'gate'),
    ], [('act', 'svc'), ('svc', 'ls'), ('svc', 'post'), ('post', 'merge'), ('merge', 'db'), ('ls', 'fail', '', 'h'),
        ('load', 'ls', 'reads', 'h'), ('db', 'rec', '', 'v')], [],
        'Figure 5. Persistence. Nothing the candidate saved may be silently lost; see "Persistence" in the design notes.')

    d['ask'] = svg_flow(1000, 560, [
        ('q', 20, 40, 180, 54, 'Question typed', 'ui'),
        ('fix', 240, 40, 220, 54, 'correctAssistantQuery\ntypos repaired, said so', 'ui'),
        ('loc', 500, 40, 220, 54, 'Asks where something is?', 'gate'),
        ('map', 760, 40, 220, 54, 'PLATFORM_MAP answer\n+ a button to that part', 'ok'),
        ('fact', 500, 150, 220, 54, 'Matches a fact intent?', 'gate'),
        ('reg', 760, 150, 220, 54, 'Register answer\ncited, with Evidence', 'ok'),
        ('ready', 500, 260, 220, 54, 'Is Claude ready?', 'gate'),
        ('fb', 760, 260, 220, 54, 'Register reply + note', 'warn'),
        ('job', 500, 370, 220, 54, 'POST /api/claude/ask\na job, never in the request', 'api'),
        ('gw', 240, 370, 220, 54, 'ClaudeGateway.run\nfixed template, schema', 'claude'),
        ('chk', 240, 470, 220, 54, 'Schema + quotes re-checked\nagainst text GovOS fetched', 'gate'),
        ('show', 500, 470, 220, 54, 'Each fact re-verified\non the page itself', 'ok'),
    ], [('q', 'fix'), ('fix', 'loc'), ('loc', 'map', 'yes'), ('loc', 'fact', 'no'), ('fact', 'reg', 'yes'), ('fact', 'ready', 'no'),
        ('ready', 'fb', 'no'), ('ready', 'job', 'yes'), ('job', 'gw', ''), ('gw', 'chk'), ('chk', 'show')], [],
        'Figure 6. Ask GovOS AI. Deterministic first; Claude only for what the register cannot place, and never trusted on its own word.')

    d['upload'] = svg_flow(1000, 470, [
        ('u', 20, 40, 180, 54, 'Scorecard uploaded\n(JSON, base64)', 'ui'),
        ('rate', 240, 40, 200, 54, 'Rate limit\n10 per minute per client', 'gate'),
        ('size', 480, 40, 200, 54, 'Size ≤ 8 MB\nelse refused', 'gate'),
        ('kind', 720, 40, 250, 54, 'PDF, or a PNG / JPEG / WEBP image?', 'gate'),
        ('pre', 720, 150, 250, 70, 'PDF pre-flight\n≤ 2,000 stream starts, ≤ 48 MB each,\n≤ 96 MB together (failures counted)', 'gate'),
        ('img', 480, 150, 200, 70, 'Image header checked\nsize before any pixel', 'gate'),
        ('child', 480, 290, 250, 70, 'Child process\n2.5 GB memory cap, 90 s, 2 at a time', 'claude'),
        ('read', 770, 290, 200, 70, 'Text layer, else OCR\n(OCR is optional)', 'api'),
        ('parse', 770, 400, 200, 56, '_parse_scorecard\nmarks, category, roll number', 'api'),
        ('back', 480, 400, 250, 56, 'Sent back to confirm\nnever stored', 'ok'),
    ], [('u', 'rate'), ('rate', 'size'), ('size', 'kind'), ('kind', 'pre', 'PDF'), ('kind', 'img', 'image'),
        ('pre', 'child', 'within limits', 'v'), ('img', 'child', '', 'v'), ('child', 'read'), ('read', 'parse', '', 'v'), ('parse', 'back')], [],
        'Figure 7. Reading an uploaded scorecard (POST /api/results/parse). Every limit applies before the work it protects.')
    return d


# =============================================================================================== page
CSS = r"""
:root { --bg:#f6f7fb; --panel:#fff; --ink:#14213d; --muted:#5b6478; --line:#e3e6ef; --accent:#2b62eb; --accent-soft:#e8eefc;
  --c-ui:#e7efff; --c-api:#e6f6ee; --c-db:#fff3dc; --c-ext:#f1eafd; --c-build:#eef1f6; --c-claude:#fde9e4; --c-gate:#fff; --c-ok:#dcf5e5; --c-warn:#fdecd8;
  --code:#f1f3f8; color-scheme: light; }
@media (prefers-color-scheme: dark) { :root { --bg:#0e1424; --panel:#151d33; --ink:#e7ebf5; --muted:#a2acc3; --line:#27314c; --accent:#7ea2ff; --accent-soft:#1f2b4d;
  --c-ui:#1d2a4d; --c-api:#173a2c; --c-db:#3a2f17; --c-ext:#2e2348; --c-build:#222a3c; --c-claude:#40231d; --c-gate:#151d33; --c-ok:#173a26; --c-warn:#40301a; --code:#10172b; color-scheme: dark; } }
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--ink); font:15px/1.6 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
a { color: var(--accent); }
code, pre { font-family: ui-monospace, "Cascadia Code", Consolas, monospace; font-size: 0.86em; font-variant-ligatures: none; }
code { background: var(--code); padding: 1px 5px; border-radius: 5px; }
pre.code { background: var(--code); padding: 12px 14px; border-radius: 10px; overflow-x: auto; line-height: 1.45; }
.layout { display: grid; grid-template-columns: 290px minmax(0, 1fr); min-height: 100vh; }
nav.toc { position: sticky; top: 0; height: 100vh; overflow-y: auto; overflow-x: hidden; padding: 22px 18px; border-right: 1px solid var(--line); background: var(--panel); font-size: 0.88rem; }
nav.toc h1 { font-size: 1.15rem; margin: 0 0 4px; }
nav.toc .stamp { color: var(--muted); font-size: 0.76rem; margin-bottom: 14px; }
nav.toc a { display: block; padding: 3px 8px; border-radius: 7px; color: var(--ink); text-decoration: none; }
nav.toc a:hover { background: var(--accent-soft); }
nav.toc .sub a { padding-left: 22px; font-size: 0.82rem; color: var(--muted); }
main { padding: 28px clamp(16px, 4vw, 56px) 80px; min-width: 0; max-width: 1180px; }
section.chapter { margin-bottom: 56px; }
h2.ch { font-size: 1.8rem; margin: 0 0 8px; letter-spacing: -0.02em; border-bottom: 2px solid var(--line); padding-bottom: 8px; }
h3 { font-size: 1.2rem; margin: 28px 0 8px; }
.lead { font-size: 1.05rem; color: var(--muted); max-width: 80ch; }
.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 12px; margin: 14px 0; }
.card { background: var(--panel); border: 1px solid var(--line); border-radius: 14px; padding: 14px 16px; }
.card b { display: block; font-size: 1.5rem; }
.card span { color: var(--muted); font-size: 0.85rem; }
.table-wrap { overflow-x: auto; margin: 10px 0 16px; }
table { border-collapse: collapse; width: 100%; background: var(--panel); border: 1px solid var(--line); border-radius: 10px; font-size: 0.88rem; }
th, td { text-align: left; padding: 7px 10px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { background: var(--accent-soft); font-weight: 700; }
details { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; margin: 8px 0; }
details > summary { cursor: pointer; padding: 10px 14px; font-weight: 650; list-style: none; }
details > summary::before { content: "▸ "; color: var(--muted); }
details[open] > summary::before { content: "▾ "; }
details > .body { padding: 4px 16px 14px; }
.ref { border-top: 1px solid var(--line); padding: 8px 0; }
.ref:first-child { border-top: none; }
.ref .hd { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.ref .nm { font-weight: 700; font-family: ui-monospace, Consolas, monospace; }
.ref .ln { color: var(--muted); font-size: 0.8rem; font-family: ui-monospace, Consolas, monospace; }
.ref .sig { color: var(--muted); font-size: 0.8rem; font-family: ui-monospace, Consolas, monospace; white-space: pre-wrap; word-break: break-word; }
.ref .doc { white-space: pre-wrap; margin-top: 4px; font-size: 0.9rem; }
.kind { font-size: 0.68rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; padding: 1px 7px; border-radius: 6px; background: var(--code); color: var(--muted); }
.k-component { background: var(--c-ui); } .k-function { background: var(--c-api); } .k-type { background: var(--c-ext); } .k-constant { background: var(--c-db); }
.k-hook { background: var(--c-claude); } .k-class { background: var(--c-build); } .k-route { background: var(--c-api); } .k-admin { background: var(--c-warn); }
.group-note { color: var(--muted); white-space: pre-wrap; font-size: 0.88rem; margin: 2px 0 6px; }
.search { position: sticky; top: 0; z-index: 3; background: var(--bg); padding: 10px 0; }
.search input { width: 100%; padding: 11px 14px; border-radius: 12px; border: 1px solid var(--line); background: var(--panel); color: var(--ink); font-size: 0.95rem; }
.search small { color: var(--muted); }
figure.diagram { margin: 18px 0 26px; background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 14px; overflow-x: auto; }
figure.diagram figcaption { color: var(--muted); font-size: 0.85rem; margin-top: 6px; }
svg.flow { width: 100%; min-width: 860px; height: auto; display: block; }
svg.flow .grp { fill: none; stroke: var(--line); stroke-width: 1.5; stroke-dasharray: 6 5; }
svg.flow .grp-l { fill: var(--muted); font-size: 12px; font-weight: 700; text-anchor: start; }
svg.flow .node rect { stroke: var(--line); stroke-width: 1.4; }
svg.flow .t-ui rect { fill: var(--c-ui); } svg.flow .t-api rect { fill: var(--c-api); } svg.flow .t-db rect { fill: var(--c-db); }
svg.flow .t-ext rect { fill: var(--c-ext); } svg.flow .t-build rect { fill: var(--c-build); } svg.flow .t-claude rect { fill: var(--c-claude); }
svg.flow .t-gate rect { fill: var(--c-gate); stroke-dasharray: 5 3; stroke: var(--muted); } svg.flow .t-ok rect { fill: var(--c-ok); } svg.flow .t-warn rect { fill: var(--c-warn); }
svg.flow text { fill: var(--ink); text-anchor: middle; font-size: 12px; font-family: system-ui, sans-serif; }
svg.flow .nt { font-weight: 700; font-size: 13px; } svg.flow .ns { fill: var(--muted); font-size: 11.5px; }
svg.flow .edge { fill: none; stroke: var(--muted); stroke-width: 1.6; } svg.flow .edge.dash { stroke-dasharray: 5 4; }
svg.flow .ah { fill: var(--muted); }
svg.flow .el rect { fill: var(--panel); stroke: var(--line); } svg.flow .el text { font-size: 11px; fill: var(--muted); }
.md-h { scroll-margin-top: 70px; }
.hidden { display: none !important; }
.legend { display: flex; flex-wrap: wrap; gap: 8px; margin: 8px 0; font-size: 0.8rem; }
.topic { background: var(--panel); border: 1px solid var(--line); border-radius: 16px; padding: 16px 20px; margin: 16px 0; scroll-margin-top: 12px; }
.topic h3 { margin: 0 0 10px; }
.two { display: grid; grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr); gap: 22px; }
.two .lab, .pl { display: inline-block; font-size: 0.7rem; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; color: var(--muted); margin: 0 8px 4px 0; }
.two .simple { font-size: 0.98rem; }
.two .under { font-size: 0.88rem; border-left: 3px solid var(--line); padding-left: 16px; color: var(--ink); }
.two p { margin: 0 0 10px; } .two ul { margin: 0 0 10px; padding-left: 20px; }
.steps { background: var(--accent-soft); border-radius: 12px; padding: 12px 16px; margin: -12px 0 26px; font-size: 0.93rem; }
.steps p { margin: 0; }
.ref .plain { margin-top: 5px; font-size: 0.93rem; }
.ref .plain.dim { color: var(--muted); }
.ref .tech { margin-top: 4px; font-size: 0.86rem; }
.ref .stale { margin-top: 4px; font-size: 0.8rem; color: var(--ink); background: var(--c-warn); border-radius: 8px; padding: 3px 8px; display: inline-block; }
.ref .doc .pl { display: block; }
details.inner { margin-top: 6px; border-radius: 10px; background: var(--bg); }
details.inner > summary { padding: 6px 12px; font-weight: 600; font-size: 0.85rem; }
details.inner .inn { padding: 5px 14px; border-top: 1px solid var(--line); font-size: 0.85rem; }
.k-method { background: var(--c-api); } .k-state, .k-ref, .k-memo { background: var(--c-db); } .k-handler { background: var(--c-api); } .k-effect { background: var(--c-claude); }
a.xref { text-decoration: none; } a.xref:hover { text-decoration: underline; }
:target { outline: 2px solid var(--accent); outline-offset: 4px; border-radius: 8px; }
@media (max-width: 1000px) { .two { grid-template-columns: 1fr; } .two .under { border-left: none; padding-left: 0; border-top: 1px solid var(--line); padding-top: 10px; } }
@media (max-width: 860px) { .layout { grid-template-columns: 1fr; } nav.toc { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--line); } }
"""

JS = r"""
const q = document.getElementById('q');
const counter = document.getElementById('qcount');
function run() {
  const term = q.value.trim().toLowerCase();
  const items = document.querySelectorAll('[data-s]');
  let shown = 0;
  items.forEach(el => {
    const hit = !term || el.dataset.s.includes(term);
    el.classList.toggle('hidden', !hit);
    if (hit) shown++;
  });
  document.querySelectorAll('details.ref-group').forEach(d => {
    const any = d.querySelector('[data-s]:not(.hidden)');
    d.classList.toggle('hidden', !!term && !any);
    if (term) d.open = !!any;
  });
  counter.textContent = term ? shown + ' matching entries' : '';
}
q.addEventListener('input', run);
// a link into the reference may point inside closed sections: open every one around the target first
function openTo(id) {
  const el = id && document.getElementById(decodeURIComponent(id));
  if (!el) return;
  for (let p = el.parentElement; p; p = p.parentElement) if (p.tagName === 'DETAILS') p.open = true;
  if (el.classList.contains('hidden')) { q.value = ''; run(); }
  el.scrollIntoView({ block: 'start' });
}
document.addEventListener('click', e => {
  const a = e.target.closest && e.target.closest('a[href^="#"]');
  if (a) { e.preventDefault(); history.pushState(null, '', a.getAttribute('href')); openTo(a.getAttribute('href').slice(1)); }
});
window.addEventListener('hashchange', () => openTo(location.hash.slice(1)));
if (location.hash) openTo(location.hash.slice(1));
"""


def ref_entry(kind: str, name: str, where: str, sig: str = '', doc: str = '', extra_kinds: list | None = None,
              rel: str | None = None, h: str | None = None, inner: list | None = None) -> str:
    """One reference entry. With `rel`, it carries an anchor and its plain-language explanation (plain.json);
    with `inner`, what it keeps inside itself."""
    kinds = f'<span class="kind k-{kind}" title="{esc(KIND_PLAIN.get(kind, kind))}">{esc(kind)}</span>' + ''.join(
        f'<span class="kind k-{k}">{esc(k)}</span>' for k in (extra_kinds or []))
    plain_html, plain_words, attr = '', '', ''
    if rel is not None:
        attr = f' id="{ref_anchor(rel, name)}"'
        simple, tech, state = plain_for(rel, name, kind, h)
        plain_words = simple + ' ' + tech
        if state == 'name':
            plain_html = f'<div class="plain dim"><span class="pl">In simple words</span>{esc(simple)} <i>(read from its name; no explanation written yet)</i></div>'
        else:
            stale = ('<div class="stale">The code changed after this explanation was written, so it may be out of date. '
                     'Run <code>python tools/docs/build_guide.py --stale</code> to list these.</div>') if state == 'stale' else ''
            plain_html = (f'<div class="plain"><span class="pl">In simple words</span>{esc(simple)}</div>'
                          + (f'<div class="tech"><span class="pl">How it works</span>{esc(tech)}</div>' if tech else '') + stale)
    inner_html = ''
    if inner:
        rows = []
        shown: set = set()
        for inn in inner:
            sub, inn_attr = '', ''
            full = f'{name}.{inn["name"]}' if inn['kind'] == 'method' else f'{name} > {inn["name"]}'
            if (rel == 'src/main.tsx' or inn['kind'] == 'method') and full not in shown:   # effects share a name: one explanation, on the first
                shown.add(full)
                inn_attr = f' id="{ref_anchor(rel, full)}"'
                s2, t2, st2 = plain_for(rel, full, inn['kind'], inn.get('hash'))
                if st2 != 'name':
                    sub = f'<div class="plain"><span class="pl">In simple words</span>{esc(s2)}</div>' + (f'<div class="tech"><span class="pl">How it works</span>{esc(t2)}</div>' if t2 else '')
                    if st2 == 'stale':
                        sub += '<div class="stale">The code changed after this explanation was written, so it may be out of date.</div>'
                    plain_words += ' ' + s2 + ' ' + t2
            plain_words += ' ' + inn['name'] + ' ' + inn['doc']
            rows.append(f'<div class="inn"{inn_attr}><span class="kind k-{inn["kind"]}" title="{esc(KIND_PLAIN.get(inn["kind"], ""))}">{esc(inn["kind"])}</span> '
                        f'<span class="nm">{esc(inn["name"])}</span> <span class="ln">line {inn["line"]}</span>{sub}'
                        + (f'<div class="doc">{esc(inn["doc"])}</div>' if inn['doc'] else '') + '</div>')
        counts: dict = {}
        for inn in inner:
            counts[inn['kind']] = counts.get(inn['kind'], 0) + 1
        summary = ', '.join(f'{n} {k}{"s" if n != 1 else ""}' for k, n in counts.items())
        inner_html = f'<details class="inner"><summary>Inside it: {summary}</summary>{"".join(rows)}</details>'
    search = esc(' '.join([name, where, sig, doc, plain_words]).lower(), quote=True)
    return (f'<div class="ref"{attr} data-s="{search}"><div class="hd">{kinds}<span class="nm">{esc(name)}</span><span class="ln">{esc(where)}</span></div>'
            + plain_html
            + (f'<div class="sig">{esc(sig)}</div>' if sig and sig != name else '')
            + (f'<div class="doc"><span class="pl">Notes in the code</span>{esc(doc)}</div>' if doc else '') + inner_html + '</div>')


GLOSSARY = [
    ('Exam record', 'One `Exam` object (types.ts): the posts, dates, stages, syllabus, cut-offs, resources and every fact\'s provenance for one examination cycle. Authored ones live in data.ts; machine-read ones in the `exam_registry` table.'),
    ('Provenance', '`DataProvenance`: where a value came from — the document, its official URL, page, clause and the exact quoted words. The product\'s core idea: every fact can answer "where did GovOS get this?".'),
    ('Evidence button / panel', 'The one action on every cited value. It opens the EvidencePanel, which shows only what the provenance states (DIRECT, RECONCILED or DERIVED evidence).'),
    ('VERIFIED', 'A fact whose officially verified source has a URL and a page or quote, and whose quoted words contain the value. Nothing else may be called "Officially verified".'),
    ('UNDER_VERIFICATION', 'A source is known but nothing deterministic has checked the value against it (for example every verifier revision, every Claude-assisted reading).'),
    ('UNSUPPORTED', 'A source is cited but its quoted words do not contain the value.'),
    ('SUPERSEDED', 'A later official statement replaced this one (a corrigendum or an extension). It stays listed, struck through, and is never the "next" date.'),
    ('NOT_PUBLISHED vs NOT_EXTRACTED', 'NOT_PUBLISHED is a finding about the authority (it publishes no such thing). NOT_EXTRACTED is a gap in GovOS\'s reader. They must never be merged.'),
    ('SEARCH_INCOMPLETE', 'Discovery did not read every listing that could hold the item, so it may not say "not found".'),
    ('Register', 'The set of exams GovOS holds: the authored exams in data.ts plus published registry exams.'),
    ('Section numbers', 'Each exam-page part has a stable number (1–17) used for deep links; Mock Tests is 17 even though it sits in the middle.'),
    ('Admin guard', '`admin_required` in app.py: a token or a loopback request with no proxy headers. A local guard, not production authentication.'),
    ('Job', 'Slow work (anything that calls Claude) runs as a row in `claude_jobs`, never inside the web request.'),
    ('localStorage first', 'The browser is the source of truth; SQLite is a copy written in the background. The page works offline.'),
]


def build() -> tuple[str, dict]:
    files = tracked_files()
    stats = {'files': len(files)}
    sha = git('rev-parse', '--short', 'HEAD').strip() or 'unknown'
    branch = git('rev-parse', '--abbrev-ref', 'HEAD').strip() or ''
    dirty = bool([l for l in git('status', '--porcelain').splitlines() if l[3:].startswith(('src/', 'app.py', 'tools/', 'index.html'))])

    fe = [scan_ts(f) for f in ('src/main.tsx', 'src/ui.tsx', 'src/services.ts', 'src/data.ts', 'src/types.ts') if f in files]
    py_files = [f for f in files if f.endswith('.py') and not f.rsplit('/', 1)[-1].startswith('test_') and f != 'conftest.py']
    py = [scan_py(f) for f in py_files]
    rts, tables, tests, checks = routes(), sqlite_tables(), py_tests(), frontend_checks()
    keys, calls = storage_keys(), api_calls()
    parts_main, parts_ref = exam_sections()
    engines = practice_engines()
    docs_md = [f for f in files if f.endswith('.md') and '/' not in f] + [f for f in files if f.endswith('.md') and '/' in f]
    total_lines = sum(file_lines(f) for f in files)
    fe_decls = sum(len(it) for m in fe for g in m['groups'] for it in [g['items']])
    py_decls = sum(len(m['items']) + sum(len(i.get('methods', [])) for i in m['items']) for m in py)
    n_tests = sum(t['count'] for t in tests)
    n_checks = sum(len(c['checks']) for c in checks)
    stats.update(lines=total_lines, fe=fe_decls, py=py_decls, routes=len(rts), tables=len(tables), tests=n_tests, checks=n_checks)

    toc: list[tuple[str, str, list]] = []
    body: list[str] = []

    def chapter(cid: str, title: str, content: str, subs: list | None = None):
        toc.append((cid, title, subs or []))
        body.append(f'<section class="chapter" id="{cid}"><h2 class="ch">{esc(title)}</h2>{content}</section>')

    figs = diagrams()

    # index every declaration first, so the hand-written chapters can link into the reference
    for m in fe:
        for g in m['groups']:
            for it in g['items']:
                index_ref(m['file'], it['name'])
                for inn in it['inner']:
                    if inn['kind'] == 'method':
                        index_ref(m['file'], f"{it['name']}.{inn['name']}")
                    elif m['file'] == 'src/main.tsx':
                        index_ref(m['file'], f"{it['name']} > {inn['name']}")
    for m in py:
        for it in m['items']:
            index_ref(m['file'], it['name'])
            for me in it.get('methods', []):
                index_ref(m['file'], f"{it['name']}.{me['name']}")
    DOC_HEADINGS.update(re.sub(r'^#+\s*', '', l).strip() for l in read('CLAUDE.md').split('\n') if re.match(r'^#{1,6}\s', l))

    def steps(key: str) -> str:
        return f'<div class="steps">{rich(guide_text.FIGURE_STEPS[key])}</div>' if key in guide_text.FIGURE_STEPS else ''

    # ---- 1. In plain words (hand-written, guide_text.py)
    topics = []
    for title, tid, simple, tech in guide_text.STORY:
        topics.append(f'<div class="topic" id="plain-{tid}"><h3>{esc(title)}</h3><div class="two">'
                      f'<div class="simple"><div class="lab">In simple words</div>{rich(simple)}</div>'
                      f'<div class="under"><div class="lab">Under the hood</div>{rich(tech)}</div></div></div>')
    chapter('plain', '1. GovOS in plain words', f"""
<p class="lead">The whole project, explained twice. On the left, in everyday words for anyone. On the right, the exact technical
mechanism, with links straight to the code it names in the reference chapters. Read the left column top to bottom for the story;
use the right column when you want to know precisely how.</p>{''.join(topics)}""",
            [(f'plain-{tid}', title) for title, tid, _, _ in guide_text.STORY])

    # ---- 2. Words
    chapter('words', '2. Words used in this guide', f"""
<p class="lead">First the everyday meaning of the technical words, then GovOS's own terms.</p>
<h3>Technical words</h3>
<div class="table-wrap"><table><thead><tr><th>Word</th><th>What it means</th></tr></thead><tbody>
{''.join(f'<tr><td><b>{esc(t)}</b></td><td>{md_inline(m)}</td></tr>' for t, m in guide_text.TECH_WORDS)}
</tbody></table></div>
<h3>GovOS's own terms</h3>
<div class="table-wrap"><table><thead><tr><th>Term</th><th>Meaning</th></tr></thead><tbody>
{''.join(f'<tr><td><b>{esc(t)}</b></td><td>{md_inline(m)}</td></tr>' for t, m in GLOSSARY)}
</tbody></table></div>""")

    # ---- 3. Start here
    chapter('start', '3. Start here: the numbers, and how to read the rest', f"""
<p class="lead">GovOS turns India's scattered government-recruitment notices into one verified, cited journey per exam: find an exam,
check eligibility, read the dates, apply, study, practise, sit the exam and read the result — with every fact traceable to the
authority's own document. This page explains the whole project. Most of it is generated from the code itself, so it is
current as of the build stamp in the sidebar.</p>
<div class="cards">
<div class="card"><b>{stats['files']}</b><span>tracked files</span></div>
<div class="card"><b>{stats['lines']:,}</b><span>lines in them</span></div>
<div class="card"><b>{fe_decls:,}</b><span>frontend declarations documented</span></div>
<div class="card"><b>{py_decls:,}</b><span>backend functions, classes and methods</span></div>
<div class="card"><b>{len(rts)}</b><span>API routes</span></div>
<div class="card"><b>{len(tables)}</b><span>database tables</span></div>
<div class="card"><b>{n_tests:,}</b><span>Python test functions</span></div>
<div class="card"><b>{n_checks:,}</b><span>frontend checks</span></div>
</div>
<h3>How to read this page</h3>
<ul>
<li><b>Chapters 1–2</b> are for everyone: the whole project in plain words, and the words it uses.</li>
<li><b>Chapters 4–6</b> are the picture: what runs where, how a fact travels, and the diagrams of each important flow, each with a
step-by-step explanation in plain words.</li>
<li><b>Chapters 7–11</b> are the reference, generated from the code: every file, every frontend declaration (grouped by the
section banners inside each file), every backend module, route, table, storage key and test — each with its line number and
an explanation in simple words, a precise "how it works", and the notes written above it in the code. Use the search box to find anything by name or by a word in its explanation.</li>
<li><b>Chapter 12</b> holds the project's own design records — CLAUDE.md (the living design document), PIPELINE.md and every
audit — rendered in full. They explain <em>why</em> the code is the way it is.</li>
<li>Line numbers refer to the working tree at the stamp. To read the code itself, open the file at that line.</li>
</ul>
<h3>Run it</h3>
<pre class="code">npm install                 # the frontend's dependencies
pip install -r requirements.txt
npm run dev                 # Vite dev server on :3000 (proxies /api to :5000)
python app.py               # Flask API + static server on :5000
npm run build               # → dist/index.html (one self-contained file); also refreshes this guide
npm run docs                # refresh this guide only
npx tsc --noEmit            # type check
npm run check:frontend      # the frontend contract checks
python -m pytest tools test_*.py -q   # the backend suite</pre>
<p>The words used here are explained in <a href="#words">chapter 2</a>.</p>""")

    # ---- 2. Architecture
    chapter('architecture', '4. Architecture', f"""
<p class="lead">Two halves joined only by <code>fetch('/api/…')</code> calls, all of which live in <code>src/services.ts</code>.
The page is one self-contained HTML file; the server is one Python file plus the <code>tools/</code> packages it imports.</p>
{figs['architecture']}{steps('architecture')}
<h3>The five frontend files</h3>
<div class="table-wrap"><table><thead><tr><th>File</th><th>Lines</th><th>What it is</th></tr></thead><tbody>
{''.join(f"<tr><td><code>{esc(m['file'])}</code></td><td>{m['lines']:,}</td><td>{esc(describe_file(m['file']) or '')}</td></tr>" for m in fe)}
</tbody></table></div>
<h3>The backend</h3>
<p><code>app.py</code> ({file_lines('app.py'):,} lines) is the Flask application: the SQLite schema, every API route, static serving of
<code>dist/index.html</code>, the live feeds, the link checker, the research pipeline and the wiring for Claude. The
<code>tools/</code> packages are imported by it or run at build time:</p>
<ul>
<li><code>tools/claude_cli/</code> — the only Claude integration: one gateway, one persistent job queue, fixed prompt templates, strict output validation.</li>
<li><code>tools/exam_builder/</code> — the build-time pipeline that reads an authority's documents into an exam record (discovery, readers, evidence, completeness, publication gate).</li>
<li><code>tools/exam_authoring/</code> — reads one authority's pages and PDFs into a <code>data.ts</code>-shaped record.</li>
<li><code>tools/scorecard_decode.py</code> — bounded decoding of uploaded scorecards; <code>tools/single_flight.py</code> — one fetch per key at a time.</li>
<li><code>tools/frontend_checks/</code> — headless checks of the frontend contract (run by <code>npm run check:frontend</code>).</li>
</ul>""")

    # ---- 3. Flows
    chapter('flows', '5. How things flow', f"""
<h3 id="flow-pipeline">How a fact reaches a candidate</h3>{figs['pipeline']}{steps('pipeline')}
<h3 id="flow-navigation">Navigation</h3>{figs['navigation']}{steps('navigation')}
<h3 id="flow-evidence">Whether a fact may be called verified</h3>{figs['evidence']}{steps('evidence')}
<h3 id="flow-persistence">Saving the candidate's data</h3>{figs['persistence']}{steps('persistence')}
<h3 id="flow-ask">Ask GovOS AI</h3>{figs['ask']}{steps('ask')}
<h3 id="flow-upload">Reading an uploaded scorecard</h3>{figs['upload']}{steps('upload')}""",
            [('flow-pipeline', 'Fact pipeline'), ('flow-navigation', 'Navigation'), ('flow-evidence', 'Verification'),
             ('flow-persistence', 'Persistence'), ('flow-ask', 'Ask GovOS AI'), ('flow-upload', 'Scorecard upload')])

    # ---- 4. The exam page (generated)
    rows = ''.join(f"<tr><td>{p['num']}</td><td>{esc(p['label'])}</td><td>Part {i + 1} of {len(parts_main)}</td></tr>" for i, p in enumerate(parts_main))
    refs = ''.join(f"<tr><td>{p['num']}</td><td>{esc(p['label'])}</td><td>Reference — backs {esc(p['under'] or '')}</td></tr>" for p in parts_ref)
    eng = ''.join(f"<tr><td><code>{esc(e['id'])}</code></td><td><code>{esc(e['engine'])}</code></td><td>{esc(e['label'])}</td></tr>" for e in engines)
    chapter('exam-page', '6. The exam page', f"""
<p class="lead">Everything that belongs to one exam lives inside that exam (<code>ExamDetailView</code> in ui.tsx). These tables are read
from <code>EXAM_SECTIONS</code>, <code>REFERENCE_SECTIONS</code> and <code>PRACTICE_ENGINES</code>, so they always match the code.
A section's number is its stable deep-link id, not its position.</p>
<div class="table-wrap"><table><thead><tr><th>Number</th><th>Part</th><th>Where it sits</th></tr></thead><tbody>{rows}{refs}</tbody></table></div>
<h3>Which practice engine each exam gets</h3>
<p>An exam with no entry gets <code>UnavailablePracticeEngine</code>, which says so honestly. No exam ever falls back to another exam's engine.</p>
<div class="table-wrap"><table><thead><tr><th>Exam id</th><th>Engine</th><th>Label</th></tr></thead><tbody>{eng or '<tr><td colspan="3">(registry not found)</td></tr>'}</tbody></table></div>""")

    # ---- 5. Frontend reference
    fe_html = ['<div class="search"><input id="q" type="search" placeholder="Search every function, component, type, route, table, test… by name or by a word in its explanation" aria-label="Search the reference"><small id="qcount"></small></div>']
    fe_subs = []
    for m in fe:
        fid = anchor('fe', m['file'])
        fe_subs.append((fid, m['file']))
        groups_html = []
        for g in m['groups']:
            entries = ''.join(ref_entry(it['kind'], it['name'], f"{m['file']}:{it['line']}", it['sig'], it['doc'],
                                        ['exported'] if it['exported'] else [], rel=m['file'], h=it['hash'], inner=it['inner']) for it in g['items'])
            groups_html.append(f'<details class="ref-group"><summary>{esc(g["title"])} <span class="ln">line {g["line"]} · {len(g["items"])} declarations</span></summary>'
                               f'<div class="body">{"<div class=group-note>" + esc(g["note"]) + "</div>" if g["note"] else ""}{entries}</div></details>')
        fe_html.append(f'<h3 id="{fid}"><code>{esc(m["file"])}</code> <span class="ln">{m["lines"]:,} lines</span></h3>'
                       f'<p>{esc(describe_file(m["file"]))}</p>{"".join(groups_html)}')
    chapter('frontend', '7. Frontend reference (src/)', '<p class="lead">Every top-level declaration of the five frontend files, grouped under the section banners the files use. Each has an explanation in simple words, how it works, the notes written above it in the code, and for screen pieces and functions what they keep inside themselves (state, handlers, effects). Hover a kind badge for what that kind is. <span class="kind k-component">component</span> renders UI; <span class="kind k-function">function</span>; <span class="kind k-hook">hook</span>; <span class="kind k-type">type</span>; <span class="kind k-constant">constant</span>.</p>' + ''.join(fe_html), fe_subs)

    # ---- 6. Backend reference
    be_html, be_subs = [], []
    order = ['app.py'] + sorted(f['file'] for f in py if f['file'] != 'app.py')
    by_file = {m['file']: m for m in py}
    for rel in order:
        m = by_file.get(rel)
        if not m:
            continue
        entries = []
        for it in m['items']:
            entries.append(ref_entry(it['kind'], it['name'], f"{rel}:{it['line']}", it['sig'] + ('\n@' + '\n@'.join(it['decorators']) if it.get('decorators') else ''), it['doc'],
                                     rel=rel, h=it['hash']))
            for me in it.get('methods', []):
                entries.append(ref_entry('method', f"{it['name']}.{me['name']}", f"{rel}:{me['line']}", me['sig'], me['doc'], rel=rel, h=me['hash']))
        pid = anchor('be', rel)
        if rel == 'app.py' or '/' not in rel.replace('tools/', '', 1):
            be_subs.append((pid, rel))
        be_html.append(f'<details class="ref-group" id="{pid}"><summary><code>{esc(rel)}</code> <span class="ln">{m["lines"]:,} lines · {len(m["items"])} top-level</span></summary>'
                       f'<div class="body">{"<div class=group-note>" + esc(m["doc"]) + "</div>" if m["doc"] else ""}{"".join(entries) or "<p>(no top-level functions or classes)</p>"}</div></details>')
    chapter('backend', '8. Backend reference (app.py and tools/)', '<p class="lead">Every Python module that is not a test: its own explanation, then every class (with its methods), function and constant — each in simple words, how it works, its signature and decorators, and the docstring written in the code.</p>' + ''.join(be_html), be_subs[:1])

    # ---- 7. API routes
    rrows = ''.join(f"<tr data-s=\"{esc((r['path'] + ' ' + r['func'] + ' ' + r['doc']).lower(), quote=True)}\"><td><code>{esc(' '.join(r['methods']))}</code></td><td><code>{esc(r['path'])}</code>"
                    f"{' <span class=\"kind k-admin\">admin</span>' if r['admin'] else ''}</td><td><code>{esc(r['func'])}</code><br><span class=\"ln\">{esc(r['file'])}:{r['line']}</span></td>"
                    f"<td>{esc(route_words(r))}</td></tr>" for r in rts)
    crow = ''.join(f"<tr><td><code>{esc(p)}</code></td><td class=\"ln\">{esc(', '.join(w[:6]))}{' …' if len(w) > 6 else ''}</td></tr>" for p, w in calls)
    chapter('api', '9. API routes and the calls the page makes', f"""
<p class="lead">Every route the server answers (read from the route decorators), whether it needs the admin guard, the handler and its
explanation. Then every <code>/api/</code> path the frontend calls, with where.</p>
<div class="table-wrap"><table><thead><tr><th>Method</th><th>Path</th><th>Handler</th><th>What it does</th></tr></thead><tbody>{rrows}</tbody></table></div>
<h3>Paths the frontend calls</h3>
<div class="table-wrap"><table><thead><tr><th>Path</th><th>Called from</th></tr></thead><tbody>{crow}</tbody></table></div>""")

    # ---- 8. Data
    trows = ''.join(f"<details class=\"ref-group\"><summary><code>{esc(t['name'])}</code> <span class=\"ln\">{esc(t['file'])}:{t['line']} · {len(t['cols'])} columns</span></summary><div class=\"body\"><div class=\"table-wrap\"><table><thead><tr><th>Column</th><th>Type and constraints</th></tr></thead><tbody>"
                    + ''.join(f"<tr><td><code>{esc(c)}</code></td><td><code>{esc(ty)}</code></td></tr>" for c, ty in t['cols']) + '</tbody></table></div></div></details>' for t in tables)
    krows = ''.join(f"<tr><td><code>{esc(k)}</code></td><td class=\"ln\">{esc(', '.join(w[:5]))}{' …' if len(w) > 5 else ''}</td></tr>" for k, w in keys)
    chapter('data', '10. Data: database tables and browser storage', f"""
<p class="lead">The SQLite tables (read from their <code>CREATE TABLE</code> statements) and every browser-storage key the page uses.
The browser's copy is the source of truth; the database is its copy plus the server's own registry, caches and audit records.</p>
{trows}
<h3>Browser storage keys</h3>
<div class="table-wrap"><table><thead><tr><th>Key</th><th>Used at</th></tr></thead><tbody>{krows}</tbody></table></div>""")

    # ---- 9. Tests
    t_html = []
    for t in tests:
        inner = ''
        for c in t['classes']:
            inner += f'<p><b>{esc(c["name"])}</b> <span class="ln">line {c["line"]}</span>{(" — " + esc(c["doc"].split(chr(10))[0])) if c["doc"] else ""}</p>'
            inner += ''.join(ref_entry('function', n, f"{t['file']}:{ln}", '', d) for n, ln, d in c['tests'])
        inner += ''.join(ref_entry('function', n, f"{t['file']}:{ln}", '', d) for n, ln, d in t['loose'])
        t_html.append(f'<details class="ref-group"><summary><code>{esc(t["file"])}</code> <span class="ln">{t["count"]} tests</span></summary><div class="body">'
                      f'{"<div class=group-note>" + esc(t["doc"]) + "</div>" if t["doc"] else ""}{inner}</div></details>')
    c_html = ''.join(f'<details class="ref-group"><summary><code>{esc(c["file"])}</code> <span class="ln">{len(c["checks"])} checks</span></summary><div class="body">'
                     f'{"<div class=group-note>" + esc(c["doc"]) + "</div>" if c["doc"] else ""}' + ''.join(ref_entry('check', n, c['file']) for n in c['checks']) + '</div></details>' for c in checks)
    chapter('tests', '11. Tests and checks', f"""
<p class="lead">{n_tests:,} Python test functions in {len(tests)} files (many expand into subtests), and {n_checks:,} named frontend checks.
Each test's name states the rule it holds the code to.</p>
<h3>Python tests</h3>{''.join(t_html)}
<h3>Frontend checks</h3>{c_html}""")

    # ---- 10. Files and design records
    frows = ''.join(f"<tr data-s=\"{esc((f + ' ' + describe_file(f)).lower(), quote=True)}\"><td><code>{esc(f)}</code></td><td>{file_lines(f) or ''}</td><td>{esc(describe_file(f))}</td></tr>" for f in files)
    md_toc: list = []
    docs_html = []
    for rel in docs_md:
        sub: list = []
        rendered = md_to_html(read(rel), anchor('doc', rel), sub)
        did = anchor('doc', rel, 'top')
        md_toc.append((did, rel))
        open_attr = ' open' if rel == 'CLAUDE.md' else ''
        docs_html.append(f'<details class="ref-group" id="{did}"{open_attr}><summary><code>{esc(rel)}</code> <span class="ln">{file_lines(rel):,} lines</span></summary><div class="body">{rendered}</div></details>')
    chapter('files', '12. Every file, and the design records', f"""
<h3>Every tracked file</h3>
<div class="table-wrap"><table><thead><tr><th>File</th><th>Lines</th><th>What it says it is</th></tr></thead><tbody>{frows}</tbody></table></div>
<h3>Design records</h3>
<p>The project's own documents, rendered in full. CLAUDE.md is the living design document — it is updated with every change, so its
explanations are the current ones.</p>{''.join(docs_html)}""", md_toc[:1])

    # ---- assemble
    nav = []
    for cid, title, subs in toc:
        nav.append(f'<a href="#{cid}">{esc(title)}</a>')
        if subs:
            nav.append('<div class="sub">' + ''.join(f'<a href="#{sid}">{esc(st)}</a>' for sid, st in subs) + '</div>')
    # The stamp (commit, time) is filled in at write time and is not part of the content hash: otherwise every
    # commit would change the page and the Stop hook would leave a modified guide behind after each one.
    stats['stamp'] = f'Generated from <b>{esc(branch)}</b> @ <code>{esc(sha)}</code>{" + uncommitted changes" if dirty else ""} · __GENERATED_AT__'
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GovOS — Project Guide</title><style>{CSS}</style></head>
<body><div class="layout">
<nav class="toc" aria-label="Contents"><h1>GovOS Project Guide</h1><div class="stamp">__STAMP__</div>{''.join(nav)}</nav>
<main>{''.join(body)}</main></div>
<script>{JS}</script>
<!-- content-hash: __HASH__ -->
</body></html>"""
    return page, stats


def plain_maintenance() -> int:
    """--stamp: record the current code fingerprint on every explanation that has none (after new ones are written).
    --stale: list explanations whose code changed since they were written, and how many declarations have none."""
    if '--stamp' in sys.argv:
        stamped = 0
        for key, entry in PLAIN.items():
            if not entry.get('hash') and key in PLAIN_SEEN:
                entry['hash'] = PLAIN_SEEN[key]
                stamped += 1
        with open(PLAIN_PATH, 'w', encoding='utf-8', newline='\n') as fh:
            json.dump({'version': 1, 'entries': dict(sorted(PLAIN.items()))}, fh, ensure_ascii=False, indent=1)
            fh.write('\n')
        print(f'plain.json: stamped {stamped} explanations.')
    if '--stale' in sys.argv:
        stale = sorted(k for k, e in PLAIN.items() if e.get('hash') and k in PLAIN_SEEN and e['hash'] != PLAIN_SEEN[k])
        missing = sorted(k for k in PLAIN_SEEN if k not in PLAIN)
        gone = sorted(k for k in PLAIN if k not in PLAIN_SEEN and ' > ' not in k)
        print(f'{len(stale)} explanations describe code that has changed since:')
        for k in stale:
            print('  ' + k)
        print(f'{len(missing)} declarations have no explanation yet:')
        for k in missing:
            print('  ' + k)
        print(f'{len(gone)} explanations name a declaration that no longer exists:')
        for k in gone:
            print('  ' + k)
    return 0


def main() -> int:
    page, stats = build()
    if WARNINGS and not QUIET:
        for w in sorted(set(WARNINGS)):
            print('guide warning: ' + w, file=sys.stderr)
    if '--stamp' in sys.argv or '--stale' in sys.argv:
        plain_maintenance()
        if '--stamp' not in sys.argv:
            return 0
        page, stats = build()    # rebuilt with the fingerprints just recorded
    digest = hashlib.sha256(page.encode('utf-8')).hexdigest()[:16]
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    if os.path.exists(OUT):
        with open(OUT, encoding='utf-8') as fh:
            old = fh.read()
        m = re.search(r'content-hash: ([0-9a-f]{16})', old)
        if m and m.group(1) == digest:
            if not QUIET:
                print(f'docs/GovOS_Guide.html is current ({digest}).')
            return 0
    stamp = datetime.now().strftime('%Y-%m-%d %H:%M')
    final = page.replace('__STAMP__', stats['stamp']).replace('__GENERATED_AT__', esc(stamp)).replace('__HASH__', digest)
    with open(OUT, 'w', encoding='utf-8', newline='\n') as fh:
        fh.write(final)
    print(f"docs/GovOS_Guide.html written: {len(final) // 1024:,} KB, {stats['fe']:,} frontend + {stats['py']:,} backend declarations, "
          f"{stats['routes']} routes, {stats['tables']} tables, {stats['tests']:,} tests, {stats['checks']:,} checks.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
