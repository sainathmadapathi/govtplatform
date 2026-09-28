"""The ruled-table reader and the vacancy break-up it feeds, on a PDF built here.

The PDF is written by hand -- rules as thin filled rectangles, as real notices draw them, and
Helvetica text -- so the test needs no PDF library. Every authority, post and figure is
invented.

Run: python -m unittest tools.exam_builder.test_ruled_table
"""
from __future__ import annotations

import unittest

from .ruled_table import parse_count, read_ruled_tables, read_table
from .vacancy_breakup import attach, breakups_in

#: Column boundaries (points) and the header: No | Name | GEN (Z1 Z2) | RES (Z1 Z2) | TOTAL.
XS = [40, 70, 250, 300, 350, 400, 450, 510]
ROW_H = 24


def _pdf(pages: list[list[tuple]]) -> bytes:
    """A PDF of ruled tables. Each page is a list of cells (r0, r1, c0, c1, [lines])."""
    objects: list[bytes] = []

    def add(body: bytes) -> int:
        objects.append(body)
        return len(objects)

    font = add(b'<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>')
    page_ids, content_ids = [], []
    for cells in pages:
        ops = []
        top = 560
        for r0, r1, c0, c1, lines in cells:
            x0, x1 = XS[c0], XS[c1 + 1]
            y1, y0 = top - r0 * ROW_H, top - (r1 + 1) * ROW_H
            for x, y, w, h in ((x0, y1 - 0.25, x1 - x0, 0.5), (x0, y0 - 0.25, x1 - x0, 0.5),
                               (x0 - 0.25, y0, 0.5, y1 - y0), (x1 - 0.25, y0, 0.5, y1 - y0)):
                ops.append(f'{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f')
            for i, line in enumerate(lines):
                ty = y1 - 9 - i * 8
                ops.append(f'BT /F1 7 Tf {x0 + 3:.2f} {ty:.2f} Td ({line}) Tj ET')
        stream = '\n'.join(ops).encode('latin-1')
        content_ids.append(add(b'<< /Length %d >>\nstream\n' % len(stream) + stream + b'\nendstream'))
        page_ids.append(None)
    pages_id = len(objects) + len(pages) + 1
    for i in range(len(pages)):
        page_ids[i] = add(b'<< /Type /Page /Parent %d 0 R /MediaBox [0 0 612 612] '
                          b'/Resources << /Font << /F1 %d 0 R >> >> /Contents %d 0 R >>'
                          % (pages_id, font, content_ids[i]))
    add(b'<< /Type /Pages /Kids [%s] /Count %d >>'
        % (b' '.join(b'%d 0 R' % p for p in page_ids), len(pages)))
    catalog = add(b'<< /Type /Catalog /Pages %d 0 R >>' % pages_id)
    out = bytearray(b'%PDF-1.4\n')
    offsets = []
    for n, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b'%d 0 obj\n' % n + body + b'\nendobj\n'
    xref = len(out)
    out += b'xref\n0 %d\n0000000000 65535 f \n' % (len(objects) + 1)
    for off in offsets:
        out += b'%010d 00000 n \n' % off
    out += b'trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n' % (
        len(objects) + 1, catalog, xref)
    return bytes(out)


HEADER = [
    (0, 1, 0, 0, ['No']), (0, 1, 1, 1, ['NAME OF THE POST']),
    (0, 0, 2, 3, ['GEN']), (0, 0, 4, 5, ['RES']), (0, 1, 6, 6, ['TOTAL']),
    (1, 1, 2, 2, ['Z1']), (1, 1, 3, 3, ['Z2']), (1, 1, 4, 4, ['Z1']), (1, 1, 5, 5, ['Z2']),
]


def _row(r, no, name, values, total):
    cells = [(r, r, 0, 0, [no] if no else []), (r, r, 1, 1, [name] if name else [])]
    cells += [(r, r, 2 + i, 2 + i, v) for i, v in enumerate(values)]
    cells.append((r, r, 6, 6, [total] if total else []))
    return cells


def _one_page(total_row=('3', '14', '1', '2', '20')):
    body = (_row(2, '1', 'Alpha Survey Officer', [['2'], ['1 cf'], ['1'], ['-']], '4')
            + _row(3, '2', 'Beta Revenue Officer', [['1'], ['2'], ['-'], ['1']], '4')
            # A number too wide for its cell, printed one digit per line.
            + _row(4, '3', 'Gamma Audit Officer', [['-'], ['1', '1'], ['-'], ['1']], '12'))
    total = [(5, 5, 0, 1, ['TOTAL'])] + [(5, 5, 2 + i, 2 + i, [v]) for i, v in enumerate(total_row[:4])] \
        + [(5, 5, 6, 6, [total_row[4]])]
    return _pdf([HEADER + body + total])


POSTS = [
    {'id': 'p1', 'postName': 'Alpha Survey Officer (Survey Service)', 'postCode': '01', 'vacancies': 4},
    {'id': 'p2', 'postName': 'Beta Revenue Officer (Revenue Service)', 'postCode': '02', 'vacancies': 4},
    {'id': 'p3', 'postName': 'Gamma Audit Officer (Audit Service)', 'postCode': '03', 'vacancies': 12},
]


class TestRuledTable(unittest.TestCase):

    def test_header_paths_come_from_merged_header_cells(self):
        reading = read_table(read_ruled_tables(_one_page()))
        self.assertEqual(reading.columns, [['No'], ['NAME OF THE POST'], ['GEN', 'Z1'], ['GEN', 'Z2'],
                                           ['RES', 'Z1'], ['RES', 'Z2'], ['TOTAL']])

    def test_cells_are_read_by_position_not_by_order(self):
        reading = read_table(read_ruled_tables(_one_page()))
        alpha, _beta, gamma = reading.rows
        self.assertEqual(parse_count(alpha['cells'][3]).carried_forward, 1)
        self.assertEqual(parse_count(gamma['cells'][3]).total, 11, 'a wrapped "1" over "1" is 11')
        self.assertEqual(parse_count(gamma['cells'][2]).total, 0, 'a "-" is nil, and the next cell keeps its column')

    def test_a_table_is_verified_only_when_its_own_totals_reconcile(self):
        self.assertTrue(read_table(read_ruled_tables(_one_page())).verified)
        wrong = read_table(read_ruled_tables(_one_page(total_row=('3', '14', '1', '2', '21'))))
        self.assertFalse(wrong.verified)
        self.assertTrue(any('TOTAL' in p for p in wrong.problems))

    def test_a_cell_continued_across_a_page_break_is_one_value(self):
        page1 = HEADER + _row(2, '1', 'Alpha Survey Officer', [['1 +'], ['2'], ['-'], ['-']], '4')
        page2 = (HEADER + [(2, 2, 2, 2, ['1 cf'])]
                 + _row(3, '2', 'Beta Revenue Officer', [['1'], ['2'], ['-'], ['1']], '4')
                 + [(4, 4, 0, 1, ['TOTAL']), (4, 4, 2, 2, ['3']), (4, 4, 3, 3, ['4']),
                    (4, 4, 4, 4, ['0']), (4, 4, 5, 5, ['1']), (4, 4, 6, 6, ['8'])])
        reading = read_table(read_ruled_tables(_pdf([page1, page2])))
        self.assertEqual(reading.pages, [1, 2])
        first = parse_count(reading.rows[0]['cells'][2])
        self.assertEqual((first.fresh, first.carried_forward), (1, 1))
        self.assertTrue(reading.verified, reading.problems)

    def test_counts_parse_as_printed_or_not_at_all(self):
        self.assertEqual((parse_count('2 + 2 cf').fresh, parse_count('2 + 2 cf').carried_forward), (2, 2))
        self.assertEqual(parse_count('1 c f').carried_forward, 1)
        self.assertIsNone(parse_count('Deputy Collector'))
        self.assertTrue(parse_count('').blank)


class TestVacancyBreakup(unittest.TestCase):

    def test_every_row_joins_one_post_and_the_totals_match(self):
        found, refused = breakups_in(_one_page(), POSTS)
        self.assertEqual(refused, [])
        self.assertEqual(len(found), 1)
        self.assertEqual([r['postId'] for r in found[0]['rows']], ['p1', 'p2', 'p3'])
        self.assertEqual(found[0]['tableTotal'], 20)

    def test_a_total_disagreeing_with_the_record_is_not_attached(self):
        posts = [dict(p) for p in POSTS]
        posts[2]['vacancies'] = 13
        reading = read_table(read_ruled_tables(_one_page()))
        got, why = attach(reading, posts)
        self.assertIsNone(got)
        self.assertIn('13', why)

    def test_an_unreconciled_table_is_never_attached(self):
        found, _ = breakups_in(_one_page(total_row=('3', '14', '1', '2', '21')), POSTS)
        self.assertEqual(found, [])


if __name__ == '__main__':
    unittest.main()
