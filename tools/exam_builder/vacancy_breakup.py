"""A recruitment's vacancy break-up, read from its own ruled tables and tied to its posts.

`ruled_table` reads a grid and says whether the grid's own arithmetic holds. This module
decides whether such a table is a break-up of *this record's posts*, and ties each of its
rows to one post. The columns stay the authority's own header paths ("OC / MZ1 / UR",
"PH / VH"); nothing here knows a category, a zone or an authority.

A table is attached only when all of it is:
  * it verified against its own printed totals;
  * every post group in it joins exactly one post of the record -- by name, or failing that
    by its serial number being the post's code *and* its printed total being the post's
    vacancy count *and* one distinctive word shared, three independent agreements;
  * each group's printed total equals the vacancy count the record already holds for the post.
A table that fails any of these is returned as a reason, never partially attached.
"""
from __future__ import annotations

import re

from .ruled_table import (RuledTable, TableReading, _is_total_column, _key, _numeric_columns,
                          parse_count, read_ruled_tables, read_table, header_paths)

#: Words that name a kind of post in half a notice and so identify none.
_GENERIC_WORDS = frozenset({
    'officer', 'officers', 'assistant', 'asst', 'district', 'dist', 'deputy', 'dy', 'grade',
    'service', 'services', 'the', 'and', 'for', 'including', 'of', 'in', 'state', 'supdt',
    'superintendent', 'commissioner', 'comm', 'general', 'post', 'posts',
})


def logical_tables(tables: list[RuledTable]) -> list[list[RuledTable]]:
    """Consecutive page tables with the same column headers are one table continued."""
    groups: list[list[RuledTable]] = []
    for table in tables:
        key = [_key(p) for p in header_paths(table)[1]]
        if (groups and table.page == groups[-1][-1].page + 1
                and [_key(p) for p in header_paths(groups[-1][0])[1]] == key):
            groups[-1].append(table)
        else:
            groups.append([table])
    return groups


def _words(name: str) -> set:
    return {w for w in re.findall(r'[a-z]{3,}', (name or '').lower())} - _GENERIC_WORDS


def _int(text: str) -> int | None:
    digits = re.sub(r'\s+', '', text or '')
    return int(digits) if digits.isdigit() else None


def _columns(reading: TableReading):
    """(serial, name, zone, counts, totals) column indexes, read from the table itself."""
    numeric = _numeric_columns(reading)
    others = [c for c in range(len(reading.columns)) if c not in numeric]
    texts = lambda c: [r['cells'][c] for r in reading.rows if r['cells'][c] and not r['shared'][c]]
    serial = next((c for c in others
                   if texts(c) and all(_int(t) is not None for t in texts(c))), None)
    rest = [c for c in others if c != serial and texts(c)]
    name = max(rest, key=lambda c: sum(len(t) for t in texts(c)) / max(1, len(texts(c))), default=None)
    zone = next((c for c in rest if c != name and max(len(t) for t in texts(c)) <= 12), None)
    totals = [c for c in numeric if _is_total_column(reading.columns[c])]
    counts = [c for c in numeric if c not in totals]
    return serial, name, zone, counts, totals


def attach(reading: TableReading, posts: list[dict]) -> tuple[dict | None, str]:
    """(the break-up tied to the record's posts, '') or (None, why it was not attached)."""
    if not reading.verified:
        return None, 'the table did not reconcile with its own printed totals: ' + '; '.join(reading.problems[:3])
    serial, name, zone, counts, totals = _columns(reading)
    if name is None or not counts:
        return None, 'no post-name column and counting columns were found'
    groups: list[dict] = []
    for row in reading.rows:
        if not row['shared'][name] or not groups:
            groups.append({'serial': row['cells'][serial] if serial is not None else '',
                           'name': row['cells'][name], 'rows': []})
        groups[-1]['rows'].append(row)
    spanning = [c for c in totals if any(r['span_rows'][c] > 1 for r in reading.rows)]

    def group_total(g):
        if spanning:
            return parse_count(g['rows'][0]['cells'][spanning[-1]]).total
        if totals:
            return sum(parse_count(r['cells'][totals[-1]]).total for r in g['rows'])
        return sum(parse_count(r['cells'][c]).total for r in g['rows'] for c in counts)

    used: set = set()
    out_rows = []
    for g in groups:
        printed_total = group_total(g)
        by_name = [p for p in posts if _names_agree(g['name'], p.get('postName', ''))]
        chosen = by_name if len(by_name) == 1 else []
        how = 'name'
        if not chosen:
            code = _int(g['serial'])
            chosen = [p for p in posts
                      if code is not None and _int(str(p.get('postCode') or '')) == code
                      and p.get('vacancies') == printed_total
                      and _words(g['name']) & _words(p.get('postName', ''))]
            how = 'serial, total and a shared word'
        if len(chosen) != 1:
            return None, f'row "{g["name"]}" does not join exactly one post of the record'
        post = chosen[0]
        if post.get('id') in used:
            return None, f'two rows join the same post ({post.get("postName")})'
        used.add(post.get('id'))
        if post.get('vacancies') not in (None, printed_total):
            return None, (f'"{g["name"]}" totals {printed_total} in the table but the record holds '
                          f'{post.get("vacancies")} vacancies for {post.get("postName")}')
        for row in g['rows']:
            cells = []
            for c in counts:
                v = parse_count(row['cells'][c])
                cells.append({'fresh': v.fresh, 'carriedForward': v.carried_forward,
                              'asPrinted': v.as_printed})
            out_rows.append({
                'postId': post.get('id'), 'postCode': str(post.get('postCode') or ''),
                'printedName': re.sub(r'\s+', ' ', g['name']).strip(),
                'zone': row['cells'][zone] if zone is not None else '',
                'counts': cells,
                'rowTotal': (parse_count(row['cells'][totals[0]]).total
                             if totals and not row['shared'][totals[0]] else None),
                'page': row['page'], 'joinedBy': how,
            })
        out_rows[-1]['postTotal'] = printed_total
    if len(used) < len(posts) and len(used) < len(groups):
        return None, 'the table does not cover the posts it names'
    return {
        'columns': [reading.columns[c] for c in counts],
        'pages': reading.pages,
        'rows': out_rows,
        'tableTotal': sum(r.get('postTotal', 0) for r in out_rows),
        'checks': list(reading.checks),
        'postsCovered': len(used),
    }, ''


def _names_agree(a: str, b: str) -> bool:
    from .eligibility import _names_agree as agree
    return agree(a, b)


def breakups_in(pdf_source, posts: list[dict]) -> tuple[list[dict], list[str]]:
    """Every verified break-up of these posts in one PDF, and why any candidate was refused."""
    found, refused = [], []
    tables = read_ruled_tables(pdf_source)
    for group in logical_tables(tables):
        reading = read_table(group)
        if reading is None or not reading.rows:
            continue
        got, why = attach(reading, posts)
        if got is not None:
            found.append(got)
        elif _names_any(reading, posts):
            refused.append(f'pages {reading.pages}: {why}')
    return found, refused


def _names_any(reading: TableReading, posts: list[dict]) -> bool:
    """Did this table name any of the posts at all? Only such a table's refusal is worth a note."""
    return any(_names_agree(cell, p.get('postName', ''))
               for r in reading.rows for cell in r['cells'][:3] for p in posts if cell)
