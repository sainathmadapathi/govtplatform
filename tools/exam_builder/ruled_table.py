"""Reading a ruled table from a PDF by its drawn grid, not by its flattened text.

A vacancy table printed as a grid -- posts down the side, category x zone x sub-column across
the top, sixty-odd columns -- flattens to a run of numbers in which a blank cell, a
carried-forward marker ("1 cf") or a number wrapped inside a narrow cell ("2" over "0") silently
shifts every value after it into the wrong column. The page itself is not ambiguous: the
authority drew a line around every cell. This module reads those lines.

  1. The table's rules are the page's thin path objects, horizontal and vertical.
  2. The distinct rule positions make an atomic grid; two neighbouring atomic cells are one
     cell wherever the rule between them is absent (a merged header, a post name spanning its
     zone rows).
  3. Each character goes to the cell containing its centre, lines kept top to bottom.
  4. Header rows are those above the first row of values; each leaf column's header path is
     the stack of header cells over it, as printed.
  5. A table is *verified* only when every value cell parses and the table's own printed
     arithmetic holds: a TOTAL row equal to its column sums, or a TOTAL column equal to the
     row's other value columns and a GRAND TOTAL equal to the rows it spans. A table whose
     figures do not reconcile is returned unverified, with the reasons, and must not be
     published as read.

Nothing here knows an authority, an exam or a category name.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

#: How close two rule positions must be to be one rule (PDF points).
_SNAP = 1.6
#: A rule is thin: anything thicker is a shaded cell or a box, not a line.
_THIN = 2.2


@dataclass
class Cell:
    r0: int
    r1: int            # inclusive
    c0: int
    c1: int            # inclusive
    lines: list = field(default_factory=list)

    @property
    def text(self) -> str:
        return ' '.join(self.lines).strip()


@dataclass
class RuledTable:
    page: int                      # 1-indexed
    n_rows: int
    n_cols: int
    cells: list                    # list[Cell]
    grid: list                     # grid[r][c] -> Cell

    def cell(self, r: int, c: int) -> Cell:
        return self.grid[r][c]


def _snap(values: list[float]) -> list[float]:
    out: list[float] = []
    for v in sorted(values):
        if out and abs(v - out[-1]) <= _SNAP:
            out[-1] = (out[-1] + v) / 2
        else:
            out.append(v)
    return out


def _rules(page):
    """(horizontal [(y, x0, x1)], vertical [(x, y0, y1)]) from the page's path objects."""
    import pypdfium2.raw as R
    hs, vs = [], []
    for obj in page.get_objects(max_depth=6):
        if obj.type != R.FPDF_PAGEOBJ_PATH:
            continue
        l, b, r, t = obj.get_bounds()
        w, h = r - l, t - b
        if h <= _THIN and w > 3 * max(h, 0.05):
            hs.append(((b + t) / 2, l, r))
        elif w <= _THIN and h > 3 * max(w, 0.05):
            vs.append(((l + r) / 2, b, t))
    return hs, vs


def _components(hs, vs):
    """Rules grouped into tables: two rules are one table where they touch or cross."""
    items = [('h', *s) for s in hs] + [('v', *s) for s in vs]
    parent = list(range(len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def touches(a, b):
        tol = _SNAP + 0.5
        if a[0] == b[0] == 'h':
            return abs(a[1] - b[1]) <= tol and a[2] <= b[3] + tol and b[2] <= a[3] + tol
        if a[0] == b[0] == 'v':
            return abs(a[1] - b[1]) <= tol and a[2] <= b[3] + tol and b[2] <= a[3] + tol
        h, v = (a, b) if a[0] == 'h' else (b, a)
        return (h[2] - tol <= v[1] <= h[3] + tol) and (v[2] - tol <= h[1] <= v[3] + tol)

    # Sort-and-sweep would be faster; a page holds a few thousand rules and this runs once.
    order = sorted(range(len(items)), key=lambda i: (items[i][0], items[i][1]))
    for n, i in enumerate(order):
        for j in order[n + 1:]:
            if items[j][0] == items[i][0] and items[j][1] - items[i][1] > _SNAP + 0.5:
                break
            if touches(items[i], items[j]):
                parent[find(i)] = find(j)
        # crossings between an h and every v
    hs_idx = [i for i, it in enumerate(items) if it[0] == 'h']
    vs_idx = [i for i, it in enumerate(items) if it[0] == 'v']
    for i in hs_idx:
        for j in vs_idx:
            if find(i) != find(j) and touches(items[i], items[j]):
                parent[find(i)] = find(j)
    groups: dict[int, tuple[list, list]] = {}
    for i, it in enumerate(items):
        g = groups.setdefault(find(i), ([], []))
        (g[0] if it[0] == 'h' else g[1]).append(it[1:])
    return [g for g in groups.values() if len(g[0]) >= 3 and len(g[1]) >= 3]


def _covers(segments, at: float, lo: float, hi: float) -> bool:
    """Is there a rule at `at` covering the midpoint of [lo, hi]?"""
    mid = (lo + hi) / 2
    return any(abs(pos - at) <= _SNAP + 0.5 and a - 0.5 <= mid <= b + 0.5
               for pos, a, b in segments)


def read_ruled_tables(pdf_source) -> list[RuledTable]:
    """Every ruled table in the PDF, as merged cells holding their own text."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(pdf_source)
    tables: list[RuledTable] = []
    for page_index in range(len(pdf)):
        page = pdf[page_index]
        hs, vs = _rules(page)
        if len(hs) < 3 or len(vs) < 3:
            continue
        textpage = page.get_textpage()
        chars = []
        for i in range(textpage.count_chars()):
            # A hyphen the authority broke a word at arrives as U+FFFE or a soft hyphen.
            ch = textpage.get_text_range(i, 1).replace('\ufffe', '-').replace('\u00ad', '-')
            if not ch or not ch.strip():
                continue
            l, b, r, t = textpage.get_charbox(i)
            chars.append((ch, (l + r) / 2, (b + t) / 2, max(t - b, 1.0), l, r))
        for comp_h, comp_v in _components(hs, vs):
            table = _grid_table(page_index + 1, comp_h, comp_v, chars)
            if table is not None:
                tables.append(table)
    return tables


def _grid_table(page_no, hs, vs, chars) -> RuledTable | None:
    ys = sorted(_snap([y for y, _a, _b in hs]), reverse=True)     # top to bottom
    xs = _snap([x for x, _a, _b in vs])                             # left to right
    n_rows, n_cols = len(ys) - 1, len(xs) - 1
    if n_rows < 2 or n_cols < 2:
        return None
    parent = {(r, c): (r, c) for r in range(n_rows) for c in range(n_cols)}

    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    for r in range(n_rows):
        top, bottom = ys[r], ys[r + 1]
        for c in range(n_cols - 1):
            if not _covers(vs, xs[c + 1], bottom, top):
                parent[find((r, c))] = find((r, c + 1))
    for r in range(n_rows - 1):
        for c in range(n_cols):
            if not _covers(hs, ys[r + 1], xs[c], xs[c + 1]):
                parent[find((r, c))] = find((r + 1, c))

    members: dict = {}
    for k in parent:
        members.setdefault(find(k), []).append(k)
    cells, grid = [], [[None] * n_cols for _ in range(n_rows)]
    for ks in members.values():
        rs, cs = [k[0] for k in ks], [k[1] for k in ks]
        cell = Cell(min(rs), max(rs), min(cs), max(cs))
        if len(ks) != (cell.r1 - cell.r0 + 1) * (cell.c1 - cell.c0 + 1):
            # An L-shaped merge is not a cell any printed table draws; keep the atoms apart
            # by refusing the table rather than inventing a shape.
            return None
        cells.append(cell)
        for r, c in ks:
            grid[r][c] = cell

    placed: dict[int, list] = {}
    for ch, cx, cy, h, l, r in chars:
        if not (xs[0] <= cx <= xs[-1] and ys[-1] <= cy <= ys[0]):
            continue
        col = next((c for c in range(n_cols) if xs[c] <= cx <= xs[c + 1]), None)
        row = next((r_ for r_ in range(n_rows) if ys[r_ + 1] <= cy <= ys[r_]), None)
        if col is None or row is None:
            continue
        placed.setdefault(id(grid[row][col]), []).append((ch, cx, cy, h, l, r))
    for cell in cells:
        cell.lines = _lines(placed.get(id(cell), []))
    return RuledTable(page=page_no, n_rows=n_rows, n_cols=n_cols, cells=cells, grid=grid)


def _lines(chars) -> list[str]:
    """A cell's characters as lines, top to bottom, words spaced by their gaps."""
    if not chars:
        return []
    rows: list[list] = []
    for ch in sorted(chars, key=lambda c: -c[2]):
        if rows and abs(rows[-1][0][2] - ch[2]) <= 0.45 * max(rows[-1][0][3], ch[3]):
            rows[-1].append(ch)
        else:
            rows.append([ch])
    out = []
    for row in rows:
        row.sort(key=lambda c: c[1])
        text, prev = '', None
        for ch in row:
            if prev is not None and ch[4] - prev[5] > 0.28 * max(ch[3], prev[3]):
                text += ' '
            text += ch[0]
            prev = ch
        out.append(text.strip())
    return [t for t in out if t]


# ====================================================================== interpretation
_COUNT = re.compile(r'^(?:(\d+))?(?:\+?(\d+)cf)?\+?$', re.I)
_NIL = re.compile(r'^[-–—]$')
_TOTAL_LABEL = re.compile(r'^(?:grand\s*)?total$', re.I)


@dataclass
class Count:
    """A vacancy-style count as printed: fresh, carried forward, and the cell's own text."""
    fresh: int
    carried_forward: int
    as_printed: str
    blank: bool = False            # the cell was empty, not "-"

    @property
    def total(self) -> int:
        return self.fresh + self.carried_forward


def parse_count(text: str) -> Count | None:
    """"-" -> 0; "11" (wrapped "1" over "1") -> 11; "2 + 2 cf" -> 2 fresh + 2 carried forward.
    Anything else is not a count, and the caller must not treat it as one."""
    raw = (text or '').strip()
    if not raw:
        return Count(0, 0, '', blank=True)
    if _NIL.match(raw):
        return Count(0, 0, raw)
    squeezed = re.sub(r'\s+', '', raw)
    m = _COUNT.match(squeezed)
    if not m or not (m.group(1) or m.group(2)):
        return None
    return Count(int(m.group(1) or 0), int(m.group(2) or 0), raw)


@dataclass
class TableReading:
    """A ruled table read into leaf columns and body rows, and whether its figures reconcile."""
    pages: list
    columns: list                  # list[list[str]] header path per leaf column
    rows: list                     # list[dict] {'cells': [str...], 'spans': [(r0, r1)...], 'page': n}
    total_row: dict | None
    verified: bool
    checks: list                   # human-readable arithmetic that was checked
    problems: list                 # why it is not verified


def _is_value(text: str) -> bool:
    return parse_count(text) is not None and bool(text.strip())


def header_paths(table: RuledTable) -> tuple[int, list]:
    """(index of the first body row, header path per leaf column)."""
    body_start = table.n_rows
    for r in range(table.n_rows):
        seen, values, filled = set(), 0, 0
        for c in range(table.n_cols):
            cell = table.cell(r, c)
            if id(cell) in seen or cell.r0 != r:
                continue
            seen.add(id(cell))
            if cell.text:
                filled += 1
                values += _is_value(cell.text)
        if filled and values * 2 >= filled and values >= 2:
            body_start = r
            break
    # A row directly above the first body row that holds nothing but counts -- the tail of a
    # cell continued from the previous page ("1 cf") -- is body, not header.
    while body_start > 0 and body_start < table.n_rows:
        above = {id(table.cell(body_start - 1, c)): table.cell(body_start - 1, c)
                 for c in range(table.n_cols)
                 if table.cell(body_start - 1, c).r0 == body_start - 1
                 and table.cell(body_start - 1, c).r1 == body_start - 1}
        texts = [c.text for c in above.values() if c.text]
        if texts and all(_is_value(t) for t in texts):
            body_start -= 1
        else:
            break
    paths = []
    for c in range(table.n_cols):
        path, last = [], None
        for r in range(body_start):
            cell = table.cell(r, c)
            if cell is last:
                continue
            last = cell
            # A caption spanning the whole table (the authority's own heading) names the table,
            # not the column.
            if cell.c0 == 0 and cell.c1 == table.n_cols - 1:
                continue
            label = re.sub(r'\s+', ' ', ' '.join(cell.lines)).strip()
            # "U R" printed one letter per line in a narrow cell is the label "UR".
            if re.fullmatch(r'(?:[A-Za-z]\s)+[A-Za-z]', label):
                label = label.replace(' ', '')
            if label:
                path.append(label)
        paths.append(path)
    return body_start, paths


def read_table(tables: list[RuledTable]) -> TableReading | None:
    """One logical table from consecutive page tables sharing the same column headers.

    A row whose identifying cells (the first two columns) are empty continues the row above
    it across the page break: its cells are appended to that row's, which is how a cell such
    as "1 +" at the foot of one page and "1 cf" at the head of the next is one value."""
    if not tables:
        return None
    body0, columns = header_paths(tables[0])
    rows: list[dict] = []
    pages = []
    for t in tables:
        start, cols = header_paths(t)
        if len(cols) != len(columns) or [_key(c) for c in cols] != [_key(c) for c in columns]:
            break
        pages.append(t.page)
        for r in range(start, t.n_rows):
            cells = [t.cell(r, c) for c in range(t.n_cols)]
            texts = [c.text if c.r0 == r else '' for c in cells]
            spans = [(c.r0, c.r1) for c in cells]
            owned = [c.r0 == r for c in cells]
            if not any(texts):
                continue
            if rows and not any(texts[:2]) and all(not o or not tx for o, tx in zip(owned[:2], texts[:2])) \
                    and not _TOTAL_LABEL.match(' '.join(texts[:2]).strip()) and rows[-1]['page'] != t.page:
                prev = rows[-1]
                prev['cells'] = [(a + ' ' + b).strip() if b else a for a, b in zip(prev['cells'], texts)]
                prev['continued_on'] = t.page
                continue
            rows.append({'cells': texts, 'shared': [not o for o in owned],
                         'span_rows': [c.r1 - c.r0 + 1 for c in cells], 'page': t.page,
                         'row_index': r})
    total_row = None
    for row in rows:
        # A label cell merged across the first columns is read once, not once per column.
        label = re.sub(r'\s+', '', ' '.join(dict.fromkeys(
            x for x in row['cells'][:3] if x and not _is_value(x))))
        if re.fullmatch(r'(?:GRAND)?TOTAL', label, re.I):
            total_row = row
    data = [r for r in rows if r is not total_row]
    return _verify(TableReading(pages=pages, columns=columns, rows=data, total_row=total_row,
                                verified=False, checks=[], problems=[]))


def _numeric_columns(reading: TableReading) -> list[int]:
    """Columns every data row fills with a count (or blank/nil), excluding a serial column."""
    out = []
    for c in range(len(reading.columns)):
        vals = [r['cells'][c] for r in reading.rows if not r['shared'][c]]
        if not vals or not any(v.strip() for v in vals):
            continue
        if not all(parse_count(v) is not None for v in vals):
            continue
        nums = [parse_count(v).total for v in vals if v.strip()]
        if nums and nums == list(range(1, len(nums) + 1)):
            continue                                   # 1, 2, 3 ... is a serial number
        out.append(c)
    return out


def _key(path: list) -> tuple:
    """A header path compared as printed but without the spaces a narrow cell wraps into it:
    "MZ 1", "M Z1" and "MZ1" are one label."""
    return tuple(re.sub(r'\s+', '', p).upper() for p in path)


def _is_total_column(path: list) -> bool:
    return any(re.fullmatch(r'(?:GRAND)?TOTAL', k) for k in _key(path))


def _verify(reading: TableReading) -> TableReading:
    numeric = _numeric_columns(reading)
    if not numeric:
        reading.problems.append('no column of counts was found')
        return reading
    # Every cell in a counting column must parse, or the column is not read.
    for row in reading.rows:
        for c in numeric:
            if not row['shared'][c] and parse_count(row['cells'][c]) is None:
                reading.problems.append(f'row {row["cells"][:2]}: cell "{row["cells"][c]}" is not a count')
    if reading.problems:
        return reading

    def value(row, c):
        return parse_count(row['cells'][c]).total

    checked = False
    if reading.total_row is not None:
        # The authority's own TOTAL row: every counting column's sum.
        for c in numeric:
            printed = parse_count(reading.total_row['cells'][c])
            if printed is None:
                reading.problems.append(f'total row cell "{reading.total_row["cells"][c]}" is not a count')
                continue
            got = sum(value(r, c) for r in reading.rows if not r['shared'][c])
            if got != printed.total:
                reading.problems.append(f'column {"/".join(reading.columns[c])}: rows sum to {got}, '
                                        f'the total row prints {printed.total}')
        reading.checks.append(f'{len(numeric)} columns summed against the printed total row')
        checked = True
    totals = [c for c in numeric if _is_total_column(reading.columns[c])]
    plain = [c for c in numeric if c not in totals]
    # Row arithmetic, by the table's own structure:
    #   * a total spanning several rows (GRAND TOTAL beside a post's zone rows) is the sum of
    #     the one-row total over those rows;
    #   * a bare one-row total sums the run of total columns immediately before it where there
    #     is one (GRAND TOTAL = TOTAL MZ1 + TOTAL MZ2), otherwise every plain counting column
    #     before it;
    #   * a total carrying sub-labels (TOTAL / MZ1) sums a group the header alone does not
    #     delimit, so it is checked only against a printed TOTAL row, never guessed at.
    spanning = [c for c in totals if any(r['span_rows'][c] > 1 for r in reading.rows)]
    bare = [c for c in totals if c not in spanning and len(reading.columns[c]) == 1]
    for c in bare:
        run, x = [], c - 1
        while x in totals:
            run.insert(0, x)
            x -= 1
        addends = run or [x for x in plain if x < c]
        for r in reading.rows:
            got = sum(value(r, x) for x in addends)
            if got != value(r, c):
                reading.problems.append(f'row {r["cells"][:3]}: values sum to {got}, '
                                        f'its {"/".join(reading.columns[c])} prints {value(r, c)}')
        reading.checks.append(f'{len(reading.rows)} rows: {"/".join(reading.columns[c])} equals the '
                              + ('sum of the totals before it' if run else 'sum of the row'))
        checked = True
    for c in spanning:
        row_total = [x for x in bare if x < c]
        if not row_total:
            continue
        group, running = None, 0
        for r in reading.rows + [None]:
            if r is None or not r['shared'][c]:
                if group is not None and running != value(group, c):
                    reading.problems.append(
                        f'{group["cells"][:2]}: {"/".join(reading.columns[c])} prints '
                        f'{value(group, c)}, its rows total {running}')
                if r is None:
                    break
                group, running = r, 0
            running += value(r, row_total[-1])
        reading.checks.append(f'{"/".join(reading.columns[c])} equals the sum of the rows it spans')
        checked = True
    # Verified means every counting column reconciled against the authority's own TOTAL row;
    # the row checks are additional layers, never a substitute. A fragment whose one or two
    # rows satisfy a row total proves little about the columns, and is not called verified.
    if reading.total_row is None:
        reading.problems.append('the table prints no TOTAL row to reconcile its columns against')
    reading.verified = checked and reading.total_row is not None and not reading.problems
    return reading
