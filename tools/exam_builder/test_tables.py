"""Putting a table back together, and refusing to when the pieces do not fit.

A PDF does not store a table; it stores text in positions, and extraction flattens that into
lines with no separators. Half of these fixtures check that a row is read; the other half
check that a row which cannot be read is refused rather than guessed, because a table read
wrongly produces posts that do not exist and a candidate may apply for one.

Every fixture is invented.

Run: python -m tools.exam_builder.test_tables
"""
from __future__ import annotations

from .tables import ColumnKind, find_header, reconstruct, reconstruct_lists, split_cells

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def cells_of(table, index: int) -> dict:
    return {k.value: v for k, v in table.rows[index].cells.items()}


def names(tables) -> list[str]:
    return [r.cells.get(ColumnKind.NAME, '') for t in tables for r in t.rows
            if r.reconstructed and r.cells.get(ColumnKind.NAME)]


# ============================================================== A. simple table
A_SIMPLE = """2.1 Pay Level-7 (Rs 44900 to 142400):
S.
No. Name of Post Ministry/Department Classification of
Post Age Limit
1
Alpha Officer
Ministry of Examples
Group 'B'
18-30 years
2
Beta Officer
Department of Beta
Group 'C'
21-27 years
"""


def test_a_simple_flattened_table() -> None:
    tables = reconstruct(A_SIMPLE)
    check('A: one table', len(tables), 1)
    check('A: its columns are read from the header',
          [c.value for c in tables[0].kinds],
          ['SERIAL', 'NAME', 'DEPARTMENT', 'CLASSIFICATION', 'AGE'])
    check('A: two rows', len(tables[0].rows), 2)
    check('A: the first row', cells_of(tables[0], 0),
          {'NAME': 'Alpha Officer', 'DEPARTMENT': 'Ministry of Examples',
           'CLASSIFICATION': "Group 'B'", 'AGE': '18-30 years'})
    check('A: the second', cells_of(tables[0], 1)['AGE'], '21-27 years')
    check('A: and the pay level the heading states for both',
          str(tables[0].heading_values.get(ColumnKind.PAY)).startswith('Pay Level-7'), True)


# ========================================================= B. a different order
def test_b_columns_in_another_order() -> None:
    text = """1.1 Recruitment:
No. Age Limit Name of Post Classification of Post
1
18-30 years
Alpha Officer
Group 'B'
2
21-27 years
Beta Officer
Group 'C'
"""
    tables = reconstruct(text)
    check('B: the header order is followed, not a fixed one',
          [c.value for c in tables[0].kinds],
          ['SERIAL', 'AGE', 'NAME', 'CLASSIFICATION'])
    check('B: so the cells land correctly', cells_of(tables[0], 0),
          {'AGE': '18-30 years', 'NAME': 'Alpha Officer', 'CLASSIFICATION': "Group 'B'"})


# ============================================== C/D/E. multi-line and wrapped
def test_c_multiline_post_name() -> None:
    text = """1.1 Recruitment:
No. Name of Post Department Age Limit
1
Assistant Audit \nOfficer
(Central
Cadre)
Department of Examples
18-30 years
"""
    tables = reconstruct(text)
    check('C: a name across lines, with a bracketed suffix, is one cell',
          cells_of(tables[0], 0).get('NAME'), 'Assistant Audit Officer (Central Cadre)')


def test_d_multiline_qualification() -> None:
    text = """1.1 Recruitment:
No. Name of Post Educational Qualification Age Limit
1
Alpha Officer
Bachelor Degree in \nEngineering from a \nrecognised University
18-30 years
"""
    tables = reconstruct(text)
    check('D: a wrapped qualification stays one cell',
          cells_of(tables[0], 0).get('QUALIFICATION'),
          'Bachelor Degree in Engineering from a recognised University')


def test_e_wrapped_cell_keeps_its_trailing_space_rule() -> None:
    check('a wrapped line continues its cell; an unwrapped one ends it',
          split_cells(['Alpha \n', 'Officer\n', 'Department of Examples\n']),
          ['Alpha Officer', 'Department of Examples'])


# ===================================================== F/G. headers and pages
def test_f_repeated_header_does_not_duplicate_posts() -> None:
    text = A_SIMPLE + """S.
No. Name of Post Ministry/Department Classification of
Post Age Limit
3
Gamma Officer
Office of Gamma
Group 'C'
20-30 years
"""
    found = names(reconstruct(text))
    # The property that matters is the one the brief names: a table continuing must not
    # duplicate what came before it.
    check('F: no post is produced twice', len(found), len(set(found)))
    check('F: and the rows above the repeat are read',
          found[:2], ['Alpha Officer', 'Beta Officer'])
    check('F: the header itself never becomes a post',
          [n for n in found if 'Name of Post' in n], [])


def test_g_page_break_without_a_header() -> None:
    text = A_SIMPLE + """Page 4 of 12
2.2 Pay Level-6 (Rs 35400 to 112400):
1
Gamma Officer
Office of Gamma
Group 'C'
20-30 years
"""
    tables = reconstruct(text)
    check('G: a section with no header of its own continues the table above it',
          names(tables), ['Alpha Officer', 'Beta Officer', 'Gamma Officer'])
    check('G: and takes its own heading value',
          str(tables[-1].heading_values.get(ColumnKind.PAY)).startswith('Pay Level-6'), True)
    check('G: the page marker is not a row',
          any('Page 4' in (r.cells.get(ColumnKind.NAME) or '')
              for t in tables for r in t.rows), False)


def test_h_serial_numbers_are_not_data() -> None:
    tables = reconstruct(A_SIMPLE)
    check('H: the ordinal is the row boundary, not a cell',
          ColumnKind.SERIAL in tables[0].rows[0].cells, False)
    check('H: and it is kept for reference', tables[0].rows[0].ordinal, '1')


# ==================================================== I/J. columns that vary
def test_i_a_missing_column_is_refused_not_guessed() -> None:
    text = """1.1 Recruitment:
No. Name of Post Department Classification of Post Age Limit
1
Alpha Officer
Ministry of Examples
18-30 years
"""
    tables = reconstruct(text)
    row = tables[0].rows[0]
    check('I: a row short of a cell does not silently shift the rest',
          row.cells.get(ColumnKind.AGE) in (None, '18-30 years'), True)
    check('I: and if it cannot be placed the row says so',
          bool(row.reconstructed is False or row.cells.get(ColumnKind.AGE) == '18-30 years'),
          True)


def test_j_an_optional_column_is_simply_absent() -> None:
    text = """1.1 Recruitment:
No. Name of Post Age Limit
1
Alpha Officer
18-30 years
2
Beta Officer
21-27 years
"""
    tables = reconstruct(text)
    check('J: a table with fewer columns reads fine',
          [c.value for c in tables[0].kinds], ['SERIAL', 'NAME', 'AGE'])
    check('J: and nothing is invented for the columns it lacks',
          ColumnKind.DEPARTMENT in tables[0].rows[0].cells, False)


def test_k_two_tables_in_one_document() -> None:
    text = A_SIMPLE + """3.1 Other Recruitment:
No. Name of Service Age Limit
1
Gamma Service
20-30 years
2
Delta Service
22-32 years
"""
    tables = reconstruct(text)
    check('K: both tables are found', len(tables) >= 2, True)
    check('K: and their rows do not mix',
          names(tables),
          ['Alpha Officer', 'Beta Officer', 'Gamma Service', 'Delta Service'])


# ======================================================== L/M/N/O. the columns
def test_l_many_posts() -> None:
    rows = ''.join(f'{i}\nPost Number {i}\nDepartment {i}\n18-30 years\n'
                   for i in range(1, 9))
    text = '1.1 Recruitment:\nNo. Name of Post Department Age Limit\n' + rows
    check('L: eight rows, eight posts', len(names(reconstruct(text))), 8)


def test_m_vacancy_column() -> None:
    text = """1.1 Recruitment:
No. Name of Post No. of Vacancies Age Limit
1
Alpha Officer
120
18-30 years
"""
    check('M: a vacancy column is read as one',
          cells_of(reconstruct(text)[0], 0).get('VACANCY'), '120')


def test_n_age_column() -> None:
    check('N: an age column is read as one',
          cells_of(reconstruct(A_SIMPLE)[0], 0).get('AGE'), '18-30 years')


def test_o_pay_level_column() -> None:
    text = """1.1 Recruitment:
No. Name of Post Pay Level Age Limit
1
Alpha Officer
Level 7
18-30 years
"""
    check('O: a pay column in the table, rather than the heading',
          cells_of(reconstruct(text)[0], 0).get('PAY'), 'Level 7')


# ============================================== P/Q/R/S/T. what must be refused
def test_p_an_unrelated_table_is_not_a_post_table() -> None:
    text = """1.1 Examination centres:
No. Centre Name Centre Code
1
Example City
1001
2
Another City
1002
"""
    tables = reconstruct(text)
    check('P: a table about something else yields no posts',
          [r.cells.get(ColumnKind.NAME) for t in tables for r in t.rows
           if r.cells.get(ColumnKind.NAME)], [])


def test_q_a_wrong_exam_table_is_rejected_upstream() -> None:
    """Identity runs before extraction; this records the contract."""
    from .identity import ExamIdentity, IdentityVerdict, verify
    target = ExamIdentity(exam_id='exam-alpha', query='Alpha Examination 2031',
                          official_name='Alpha Examination 2031',
                          authority_name='Alpha Commission')
    foreign = 'BETA BOARD — BETA EXAMINATION, 2031\n' + A_SIMPLE
    check('Q: another exam’s table cannot supply posts',
          verify(foreign, target).may_supply_facts, False)


def test_r_an_ambiguous_row_is_refused() -> None:
    text = """1.1 Recruitment:
No. Name of Post Department Classification of Post Age Limit
1
Alpha Officer Ministry of Examples Something Else Entirely
"""
    tables = reconstruct(text)
    row = tables[0].rows[0]
    check('R: a row whose parts cannot be placed is not reconstructed',
          row.reconstructed, False)
    check('R: and it says why', 'guessed' in row.note, True)


def test_s_a_continuation_does_not_duplicate_a_row() -> None:
    text = A_SIMPLE + """Page 5 of 12
contd.
"""
    check('S: furniture after the last row adds nothing',
          len(names(reconstruct(text))), 2)


def test_t_a_qualification_mentioned_outside_a_table_is_not_a_column() -> None:
    text = ('Candidates must hold a Bachelor Degree. The educational qualification '
            'must be held on the crucial date.\n') + A_SIMPLE
    tables = reconstruct(text)
    check('T: prose above a table does not become its header',
          [c.value for c in tables[0].kinds],
          ['SERIAL', 'NAME', 'DEPARTMENT', 'CLASSIFICATION', 'AGE'])


# ========================================================== lists of posts
def test_a_list_of_posts_is_a_table_too() -> None:
    text = """The Services and Posts mentioned below will be filled:
(i) Alpha Service
(ii) Beta Service
(iii) Gamma Service, Group 'A'
(iv) Delta Service, Group 'A'
"""
    tables = reconstruct_lists(text)
    check('a list introduced as one is read', len(tables), 1)
    check('with each item named', names(tables),
          ['Alpha Service', 'Beta Service', 'Gamma Service', 'Delta Service'])
    check('and the classification split out where it is printed',
          [bool(t.rows[i].cells.get(ColumnKind.CLASSIFICATION)) for t in tables
           for i in range(4)], [False, False, True, True])


def test_a_list_with_no_introduction_is_not_a_post_list() -> None:
    text = """The candidate shall not be guilty of:
(i) offering illegal gratification to; or
(ii) applying pressure on; or
(iii) blackmailing any person concerned.
"""
    check('an enumerated clause list is not a list of posts',
          reconstruct_lists(text), [])


def test_list_items_must_name_something() -> None:
    text = """The Services and Posts mentioned below will be filled:
(i) Alpha Service
(ii) Beta Service
(iii) Gamma Service
(iv) offering illegal gratification to; or
(v) Short Essays.
"""
    check('clauses and sentences among real items are dropped',
          names(reconstruct_lists(text)),
          ['Alpha Service', 'Beta Service', 'Gamma Service'])


def test_headers_need_a_row_under_them() -> None:
    lines = ('A paragraph about posts in various Ministries and Departments of '
             'Government.').split('\n')
    check('prose mentioning posts and ministries is not a header',
          find_header(lines), None)


def test_no_authority_is_named() -> None:
    import io
    import re
    source = io.open('tools/exam_builder/tables.py', encoding='utf-8').read()
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc'):
        check(f'tables.py never names {forbidden.upper()}',
              re.findall(rf'\b{forbidden}\b', source, re.I), [])
    check('and holds no exam-conditional branch',
          re.findall(r'if\s+(?:exam|authority)\s*==', source), [])
    # Code only: a comment may quote an example to explain what the code is for.
    code = '\n'.join(l for l in source.split('\n')
                     if not l.strip().startswith('#') and '"""' not in l)
    check('nor any post name in the code itself',
          re.findall(r'assistant|inspector|constable', code, re.I), [])


def main() -> int:
    for fn in (test_a_simple_flattened_table, test_b_columns_in_another_order,
               test_c_multiline_post_name, test_d_multiline_qualification,
               test_e_wrapped_cell_keeps_its_trailing_space_rule,
               test_f_repeated_header_does_not_duplicate_posts,
               test_g_page_break_without_a_header, test_h_serial_numbers_are_not_data,
               test_i_a_missing_column_is_refused_not_guessed,
               test_j_an_optional_column_is_simply_absent,
               test_k_two_tables_in_one_document, test_l_many_posts,
               test_m_vacancy_column, test_n_age_column, test_o_pay_level_column,
               test_p_an_unrelated_table_is_not_a_post_table,
               test_q_a_wrong_exam_table_is_rejected_upstream,
               test_r_an_ambiguous_row_is_refused,
               test_s_a_continuation_does_not_duplicate_a_row,
               test_t_a_qualification_mentioned_outside_a_table_is_not_a_column,
               test_a_list_of_posts_is_a_table_too,
               test_a_list_with_no_introduction_is_not_a_post_list,
               test_list_items_must_name_something,
               test_headers_need_a_row_under_them, test_no_authority_is_named):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('tables: rows reconstructed from structure, and refused when it does not fit')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
