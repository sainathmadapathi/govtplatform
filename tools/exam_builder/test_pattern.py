"""Twenty-three shapes an examination pattern comes in, and one rule about all of them.

The rule: a figure is the authority's or it is not there. Most of these check that the
reader refuses — a merged cell whose parts cannot be separated, a penalty nobody printed, a
document belonging to another exam, two sources disagreeing with no revision between them.

The fixtures are written in the shapes the four captured notices actually use (see
PATTERN_AUDIT.md §8): a flattened table with the ordinal and the name on one line, a header
wrapped across fifteen lines, a duration cell spanning every row, a totals row in the
middle of the table, minimum marks split into category columns, and a scheme with no table
at all. None of them names a real exam: what is being tested is that no exam has to be
named.

Run: python -m tools.exam_builder.test_pattern
"""
from __future__ import annotations

from .pattern import describe, extract_pattern, may_supply_pattern, read_negative_marking
from .schema import PatternLevel, SourceDocument, SourceKind, Status

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


DOC = SourceDocument(id='doc-1', url='https://authority.example/notice.pdf',
                     kind=SourceKind.NOTIFICATION, title='Notice', authority='An Authority',
                     accessed_at='2026-09-20', exam_id='exam-one-2026')


def read(text: str, exam_id: str = 'exam-one-2026'):
    return extract_pattern(DOC, text, exam_id=exam_id, cycle='2026')


def node_named(pattern, fragment: str):
    return next((n for n in pattern.walk() if fragment.lower() in (n.name or '').lower()),
                None)


# ============================================================== A. one stage
SINGLE_STAGE = """
3. Scheme of the Examination:
Sr.
No.
Name of Tests No. of
Questions
Maximum
Marks
Time allotted
1 Reasoning Ability 30 60 20 minutes
2 Quantitative Aptitude 35 70 20 minutes
3 English Language 35 70 20 minutes
Total 100 200 60 minutes
There will be negative marking of 0.25 marks for each wrong answer.
"""


def test_a_single_stage_exam() -> None:
    pattern = read(SINGLE_STAGE)
    check('one stage is read', len(pattern.stages), 1)
    check('with its three tests', len(pattern.stages[0].children), 3)
    check('and the totals it states', (pattern.stages[0].questions.value,
                                       pattern.stages[0].marks.value,
                                       pattern.stages[0].duration_minutes.value),
          (100, 200.0, 60))


# ========================================================= B. several stages
TWO_STAGES = """
D. STRUCTURE OF EXAMINATION
a. Preliminary Examination (Objective Test)
Sr.
No.
Name of Tests No. of
Questions
Maximum
Marks
Medium of
Exam
Time allotted for
each test
(Separately timed)
1 English Language 30 30 English 20 minutes
2 Quantitative Aptitude 35 30 English and Hindi 20 minutes
Total 65 60 40 minutes
b. Main Examination (Objective and Descriptive)
Sr.
No.
Name of Tests No. of
Questions
Maximu
m
Marks
Medium of
Exam
Time allotted for
each test
1 Reasoning 40 60 English and Hindi 45 minutes
2 Data Analysis 40 60 English and Hindi 45 minutes
Total 80 120 90 minutes
"""


def test_b_two_stages_each_with_its_own_table() -> None:
    pattern = read(TWO_STAGES)
    check('both stages are read', len(pattern.stages), 2)
    check('each keeps its own rows', [len(s.children) for s in pattern.stages], [2, 2])
    check('and its own totals', [s.marks.value for s in pattern.stages], [60.0, 120.0])
    check('the heading that introduces them is not itself a stage',
          any('STRUCTURE' in (s.name or '').upper() for s in pattern.stages), False)


def test_c_papers_listed_in_prose() -> None:
    """One authority publishes no table at all."""
    text = """
B. MAIN EXAMINATION:
The Written Examination will consist of the following papers:
Qualifying Papers:
Paper-A
(One of the Indian Languages) 300 Marks
Paper-B
English 300 Marks
Papers to be counted for merit:
Paper-I
Essay 250 Marks
Paper-II
General Studies-I 250 Marks
"""
    pattern = read(text)
    papers = pattern.of_level(PatternLevel.PAPER)
    check('four papers are read', len(papers), 4)
    check('with the marks each states', sorted(p.marks.value for p in papers),
          [250.0, 250.0, 300.0, 300.0])
    qualifying = [p for p in papers
                  if p.qualifying.has_value and p.qualifying.value.is_qualifying_only]
    check('and the two under "Qualifying Papers" are marked as such',
          sorted(p.code for p in qualifying), ['Paper-A', 'Paper-B'])
    merit = [p for p in papers
             if p.qualifying.has_value and p.qualifying.value.counts_towards_merit]
    check('while the others count towards the merit', len(merit), 2)


def test_d_sections_within_a_stage() -> None:
    pattern = read(SINGLE_STAGE)
    check('the rows are children of the stage, not stages themselves',
          len(pattern.stages), 1)
    check('and they are one level down', pattern.max_depth(), 2)


def test_e_a_stage_with_no_sections_is_still_a_stage() -> None:
    """An interview has no paper, no marks and nothing countable."""
    pattern = read(SINGLE_STAGE + '\nPhase-III: Interview\n'
                   'Candidates who qualify will be called for it.\n')
    names = [s.name for s in pattern.stages]
    check('the interview is kept', any('Interview' in n for n in names), True)


def test_f_marks_are_not_the_question_count() -> None:
    pattern = read(SINGLE_STAGE)
    row = node_named(pattern, 'Reasoning Ability')
    check('thirty questions', row.questions.value, 30)
    check('sixty marks', row.marks.value, 60.0)
    check('two marks a question, derived', row.marks_per_question.value, 2.0)
    check('and marked as derived, not as printed', row.marks_per_question.is_derived, True)


def test_g_a_printed_marks_per_question_is_not_derived() -> None:
    text = """
13.9 Scheme of Tier-II Examination:
Tier Paper Subject
Number
of
Questions
Maximum
Marks Time allowed
Paper-II Statistics
100
100*2
= 200
2 hours
Paper-III General Studies
100 100*2
= 200
2 hours
"""
    pattern = read(text)
    row = node_named(pattern, 'Statistics')
    check('the marks are the total', row.marks.value, 200.0)
    check('the cell states two marks a question', row.marks_per_question.value, 2.0)
    check('and that is the authority’s arithmetic, not ours',
          row.marks_per_question.is_derived, False)


def test_h_duration_in_hours_and_minutes() -> None:
    from .pattern import _minutes
    check('minutes', _minutes('20 minutes'), 20)
    check('hours', _minutes('2 hours'), 120)
    check('both', _minutes('1 hour and 20 minutes'), 80)
    check('and nothing where nothing is said', _minutes('as notified'), None)


def test_i_negative_marking_in_its_several_forms() -> None:
    flat = read_negative_marking('There will be negative marking of 0.50 marks for each '
                                 'wrong answer.')
    check('a flat figure', flat.deducted_per_wrong, 0.5)
    share = read_negative_marking('One-third (0.33) of the marks assigned to that question '
                                  'will be deducted.')
    check('a share of the marks', share.fraction_of_marks, 0.33)
    quarter = read_negative_marking('There shall be a penalty of 1/4th of the marks '
                                    'assigned to that question.')
    check('written as a fraction', quarter.fraction_of_marks, 0.25)


def test_j_no_negative_marking_is_a_statement() -> None:
    none = read_negative_marking('There will be NO negative marks.')
    check('the authority says there is none', none.deducted_per_wrong, 0.0)
    check('and that is a statement, not a gap', none.is_none, True)
    check('silence is not that statement',
          read_negative_marking('The test will be conducted online.'), None)
    check('nor is a quarter assumed from other exams',
          read_negative_marking('Candidates must answer all questions.'), None)


def test_k_a_qualifying_paper_is_marked_as_one() -> None:
    text = SINGLE_STAGE + """
The English Language test will be of qualifying nature and the marks thereof will not be
counted for ranking.
"""
    pattern = read(text)
    row = node_named(pattern, 'English Language')
    check('it is qualifying only', row.qualifying.value.is_qualifying_only, True)
    check('and does not count towards the merit',
          row.qualifying.value.counts_towards_merit, False)
    other = node_named(pattern, 'Reasoning Ability')
    check('the other tests are untouched', other.qualifying.has_value, False)


def test_l_qualifying_marks_by_category() -> None:
    text = """
Phase I: Preliminary Examination:
Section Name of the test Number
of
Questions
Maximum
Marks
Medium
of Exam
Minimum Qualifying
Marks
Duration
SC/ST/PWBD Others
1 Reasoning Ability 35 35 English and Hindi 16 18 20 Minutes
2 Quantitative Aptitude 35 35 English and Hindi 16 18 20 Minutes
Total 70 70 40 minutes
"""
    pattern = read(text)
    row = node_named(pattern, 'Reasoning Ability')
    minima = {c.label: c.minimum_marks for c in row.qualifying.value.by_category}
    check('both category minima are read, under the authority’s own labels',
          minima, {'SC/ST/PWBD': 16.0, 'Others': 18.0})


def test_m_sectional_timing_and_a_group_specific_duration() -> None:
    text = """
13.8 Scheme of Tier-I Examination:
Tier Subject Number of
Questions
Maximum
Marks
Time allowed
I
A. General Intelligence 25 50 1 hour (with sectional
timer of 15 minutes for
each subject)
(1 hour and 20 minutes for
the candidates eligible for scribe)
B. General Awareness 25 50
"""
    pattern = read(text)
    stage = pattern.stages[0]
    check('the stage says each section is timed separately',
          stage.sectional_timing.value, True)
    row = node_named(pattern, 'General Intelligence')
    check('the ordinary duration is the first one', row.duration_minutes.value, 60)
    check('and the longer one is kept for whom it is printed',
          [(v.minutes, 'scribe' in v.applies_to) for v in row.duration_variants], [(80, True)])


def test_n_languages_are_whatever_the_authority_names() -> None:
    pattern = read(TWO_STAGES)
    row = node_named(pattern, 'Quantitative Aptitude')
    check('both languages of the medium cell', row.languages.value, ['English', 'Hindi'])
    english = node_named(pattern, 'English Language')
    check('and one where one is named', english.languages.value, ['English'])


def test_o_a_flattened_table_with_wrapped_cells() -> None:
    text = """
a. Preliminary Examination (Objective Test)
Sr.
No.
Name of Tests No. of
Questions
Maximum
Marks
Time allotted
1 General/ Economy/
Banking
Awareness
including circulars
50 60 35 minutes
2 English Language 40 20 35 minutes
"""
    pattern = read(text)
    row = node_named(pattern, 'Banking')
    check('a cell wrapped over four lines is one cell',
          (row.questions.value, row.marks.value, row.duration_minutes.value),
          (50, 60.0, 35))
    check('and the row after it is its own row',
          node_named(pattern, 'English Language').questions.value, 40)


def test_p_a_pattern_stated_in_prose() -> None:
    text = """
A. PRELIMINARY EXAMINATION:
The Examination shall comprise of two compulsory Papers of 200 marks each.
Note:
(i) Both the question papers will be of the objective type (multiple choice questions).
(ii) The General Studies Paper-II will be a qualifying paper with minimum qualifying marks
fixed at 33%.
(iii) The question papers will be set both in Hindi and English.
"""
    pattern = read(text)
    check('the stage is read from its rules alone', len(pattern.stages), 1)
    stage = pattern.stages[0]
    check('its qualifying percentage', stage.qualifying.value.minimum_percent, 33.0)
    check('its languages', stage.languages.value, ['Hindi', 'English'])
    check('and its question type', 'objective' in (stage.question_type.value or '').lower(),
          True)


def test_q_a_document_belonging_to_another_exam_supplies_nothing() -> None:
    from .identity import ExamIdentity
    other = """
Notice of the Combined Higher Secondary Level Examination, 2026.
2. Scheme of the Examination:
Tier Subject Number of Questions Maximum Marks Time allowed
I
A. General Awareness 25 50 60 minutes
"""
    target = ExamIdentity(exam_id='exam-one-2026', query='Combined Graduate Level 2026',
                          official_name='Combined Graduate Level Examination, 2026',
                          authority_name='An Authority')
    allowed, why = may_supply_pattern(other, target)
    check('the document is refused', allowed, False)
    check('and the reason names the mismatch', 'refused' in why, True)


def test_r_an_ambiguous_document_needs_target_evidence() -> None:
    from .identity import ExamIdentity
    shared = """
Examination Pattern
This page sets out the pattern for the Combined Higher Secondary Level Examination, 2026,
the Junior Engineer Examination, 2026 and the Stenographer Examination, 2026.
""" + ('Further material about those three examinations, their schemes, their centres, '
        'their fees and their syllabi, none of it about any other examination. ' * 40) + """
Much further down, this page also mentions the Combined Graduate Level Examination, 2026
in passing.
"""
    target = ExamIdentity(exam_id='exam-one-2026', query='Combined Graduate Level 2026',
                          official_name='Combined Graduate Level Examination, 2026',
                          authority_name='An Authority')
    allowed, why = may_supply_pattern(shared, target)
    check('a page serving several exams does not supply this one’s facts',
          allowed, False)
    check('and says why', 'identify itself' in why or 'refused' in why, True)


def test_s_two_sources_disagreeing_are_not_resolved() -> None:
    from .merge import FieldOutcome, MergeAction
    from .pattern_merge import merge_pattern
    record = [{'id': 'stage-1', 'stageName': 'Scheme of the Examination — one paper',
               'tier': 'TIER_1', 'totalQuestions': 100, 'totalMarks': 200,
               'durationMinutes': 60,
               'negativeMarking': '0.25 marks deducted for each wrong answer'}]
    pattern = read(SINGLE_STAGE)
    report = merge_pattern(record, pattern)
    decision = report.decisions[0]
    check('the stage matches', decision.action, MergeAction.CONFIRMED)
    check('the figures both state are confirmed',
          [decision.field(f).outcome for f in ('totalQuestions', 'totalMarks')],
          [FieldOutcome.CONFIRMED, FieldOutcome.CONFIRMED])

    record[0]['totalMarks'] = 180
    contested = merge_pattern(record, pattern).decisions[0]
    field = contested.field('totalMarks')
    check('a disagreement is held, not resolved', field.outcome, FieldOutcome.UNDER_REVIEW)
    check('both values are kept', (field.existing, field.incoming), (180, 200.0))
    check('and the rest of the stage survives',
          contested.field('totalQuestions').outcome, FieldOutcome.CONFIRMED)


def test_t_a_penalty_written_two_ways_is_one_penalty() -> None:
    from .merge import FieldOutcome
    from .pattern_merge import merge_pattern
    record = [{'id': 'stage-1', 'stageName': 'Scheme of the Examination — one paper',
               'tier': 'TIER_1',
               'negativeMarking': 'A penalty of 0.25 marks applies to each wrong answer'}]
    decision = merge_pattern(record, read(SINGLE_STAGE)).decisions[0]
    check('the same figure, differently worded, is confirmed',
          decision.field('negativeMarking').outcome, FieldOutcome.CONFIRMED)

    record[0]['negativeMarking'] = 'There will be no negative marking'
    contested = merge_pattern(record, read(SINGLE_STAGE)).decisions[0]
    check('and a real disagreement about the penalty is held for review',
          contested.field('negativeMarking').outcome, FieldOutcome.UNDER_REVIEW)


def test_u_a_derived_value_is_never_a_printed_one() -> None:
    pattern = read(SINGLE_STAGE)
    row = node_named(pattern, 'Quantitative Aptitude')
    check('two marks a question is computed', row.marks_per_question.is_derived, True)
    check('from the two figures the table states',
          row.marks_per_question.derived_from, ['marks', 'questions'])
    check('the figures themselves are the authority’s',
          row.marks.is_derived or row.questions.is_derived, False)
    stage = pattern.stages[0]
    check('and the stage total it printed is not derived either',
          stage.marks.is_derived, False)


def test_v_a_field_the_authority_did_not_print_is_absent() -> None:
    pattern = read(SINGLE_STAGE)
    row = node_named(pattern, 'Reasoning Ability')
    check('no language column, so no languages', row.languages.status,
          Status.NOT_EXTRACTED)
    check('and nothing is invented in its place', row.languages.value, None)
    check('the three rows and the stage total are all read from the table',
          describe(pattern)['questions'].get('VERIFIED'), 4)


def test_w_one_exam_s_pattern_cannot_reach_another() -> None:
    from .compat import pattern_tree
    pattern = read(SINGLE_STAGE)
    check('the pattern carries its exam', pattern.exam_id, 'exam-one-2026')
    check('projecting it for another exam yields nothing',
          pattern_tree(pattern, exam_id='exam-two-2026'), [])
    check('and for its own exam it yields its stages',
          len(pattern_tree(pattern, exam_id='exam-one-2026')), 1)
    check('an extraction with no exam id is refused outright',
          len(read(SINGLE_STAGE, exam_id='').stages), 0)


def test_merged_cells_are_held_for_review_not_guessed() -> None:
    text = """
13.9 Scheme of Tier-II Examination:
Tier Paper Subject
Number
of
Questions
Maximum
Marks Time allowed
Section-I:
A:
Mathematical
Abilities
B: Reasoning
30
30
Total =
60
60*3
= 180
1 hour
Section-III: Computer Knowledge Test 20 20*3 = 60 15 Minutes
"""
    pattern = read(text)
    row = node_named(pattern, 'Reasoning')
    check('a row summing across parts states nothing about one part',
          row.questions.has_value, False)
    check('while the row beside it, which sums nothing, is read',
          node_named(pattern, 'Computer Knowledge').marks.value, 60.0)
    check('it is held for review', row.status, Status.NEEDS_REVIEW)
    check('and its raw text is kept for a person to read', bool(row.remarks.note), True)


def test_no_exam_is_named_in_the_extractor() -> None:
    import io
    import re
    for path in ('tools/exam_builder/pattern.py', 'tools/exam_builder/pattern_merge.py'):
        source = io.open(path, encoding='utf-8').read()
        for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'cgl', 'cse'):
            check(f'{path} never names {forbidden.upper()}',
                  re.findall(rf'\b{forbidden}\b', source, re.I), [])
        for branch in ('if exam ==', 'if exam_id ==', "== 'exam-", 'exam_id.startswith'):
            check(f'{path} has no branch on a particular exam ({branch})',
                  branch in source, False)


def main() -> int:
    for fn in (test_a_single_stage_exam,
               test_b_two_stages_each_with_its_own_table,
               test_c_papers_listed_in_prose,
               test_d_sections_within_a_stage,
               test_e_a_stage_with_no_sections_is_still_a_stage,
               test_f_marks_are_not_the_question_count,
               test_g_a_printed_marks_per_question_is_not_derived,
               test_h_duration_in_hours_and_minutes,
               test_i_negative_marking_in_its_several_forms,
               test_j_no_negative_marking_is_a_statement,
               test_k_a_qualifying_paper_is_marked_as_one,
               test_l_qualifying_marks_by_category,
               test_m_sectional_timing_and_a_group_specific_duration,
               test_n_languages_are_whatever_the_authority_names,
               test_o_a_flattened_table_with_wrapped_cells,
               test_p_a_pattern_stated_in_prose,
               test_q_a_document_belonging_to_another_exam_supplies_nothing,
               test_r_an_ambiguous_document_needs_target_evidence,
               test_s_two_sources_disagreeing_are_not_resolved,
               test_t_a_penalty_written_two_ways_is_one_penalty,
               test_u_a_derived_value_is_never_a_printed_one,
               test_v_a_field_the_authority_did_not_print_is_absent,
               test_w_one_exam_s_pattern_cannot_reach_another,
               test_merged_cells_are_held_for_review_not_guessed,
               test_no_exam_is_named_in_the_extractor):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('pattern: twenty-three shapes read, and the unreadable ones refused')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
