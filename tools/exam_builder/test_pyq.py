"""Thirty-six checks on previous-year questions and answer keys, and one rule behind them.

The rule: **the paper is the identity**. Two shifts of one day both have a question 47 and
both have an answer for it, and the only thing between a candidate and the wrong answer is
that the two paper identities do not match. So most of what follows checks that something
is refused — a key for another shift, a question from another cycle, an answer nobody
published, a paper whose file belongs to another examination on the same listing page.

The fixtures use the shapes the real documents use (PYQ_AUDIT.md §5): file names that carry
their own identity, notices that name an examination and a tier, and question papers laid
out as a number, a stem and labelled options. None of them names a real exam.

Run: python -m tools.exam_builder.test_pyq
"""
from __future__ import annotations

from .pyq import (catalogue_papers, describe_keys, describe_questions, extract_questions,
                  identity_from_text, link_revisions, mark_unreadable,
                  read_answer_key_notice, subject_from_name)
from .schema import (AnswerEntry, AnswerKey, AnswerKeyKind, AnswerStatus, PaperIdentity,
                     QuestionFormat, SourceDocument, SourceKind, SourceStatus, Status)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


EXAM = 'exam-one-2026'
DOC = SourceDocument(id='doc-1', url='https://authority.example/paper.pdf',
                     kind=SourceKind.QUESTION_PAPER, title='Paper', authority='An Authority',
                     accessed_at='2026-09-22', exam_id=EXAM)
NOTICE = SourceDocument(id='doc-2', url='https://authority.example/key.pdf',
                        kind=SourceKind.OTHER_OFFICIAL, title='Notice',
                        authority='An Authority', accessed_at='2026-09-22', exam_id=EXAM)
CODES = {'EXM-': {'stage': 'Main'}, 'EXP-': {'stage': 'Preliminary'}}


def paper(**parts) -> PaperIdentity:
    base = dict(exam_id=EXAM, cycle='2025', stage='Tier-I')
    base.update(parts)
    return PaperIdentity(**base)


MCQ = """
1. What is the capital of the country described above?
(a) The first option
(b) The second option
(c) The third option
(d) The fourth option
2. Which of the following statements is correct?
(a) Only one
(b) Only two
(c) Both
(d) Neither
"""


# ============================================================== A. a plain MCQ
def test_a_a_basic_mcq() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('two questions are read', len(questions), 2)
    first = questions[0]
    check('with the number the paper printed', first.number, '1')
    check('its stem', first.text.startswith('What is the capital'), True)
    check('four options, with the labels the paper printed',
          [o.label for o in first.options], ['a', 'b', 'c', 'd'])
    check('and it is read as multiple choice', first.format, QuestionFormat.MULTIPLE_CHOICE)


def test_b_a_descriptive_question_gets_no_options() -> None:
    text = """
1. Discuss the role of institutions in economic development. (250 words)
2. Examine the causes of the decline of that empire. (150 words)
"""
    questions = extract_questions(DOC, text, paper=paper(stage='Main'))
    check('both are read', len(questions), 2)
    check('with no options invented', [len(q.options) for q in questions], [0, 0])
    check('and are marked descriptive',
          {q.format for q in questions}, {QuestionFormat.DESCRIPTIVE})


def test_c_a_numerical_question_keeps_its_wording() -> None:
    text = '1. A train covers 120 km in 90 minutes. Find its speed in km/h.\n'
    questions = extract_questions(DOC, text, paper=paper())
    check('the question is kept as printed',
          questions[0].text.endswith('Find its speed in km/h.'), True)
    check('and no answer is produced from it',
          questions[0].answer.status, AnswerStatus.NOT_PUBLISHED)


def test_d_a_key_may_accept_more_than_one_option() -> None:
    entry = AnswerEntry(question_number='47', paper=paper(),
                        accepted=['b', 'c'], status=AnswerStatus.MULTIPLE_ACCEPTED)
    check('both accepted answers are kept', entry.accepted, ['b', 'c'])
    check('and the status says why', entry.status, AnswerStatus.MULTIPLE_ACCEPTED)


def test_e_a_dropped_question_is_a_published_decision() -> None:
    dropped = AnswerEntry(question_number='12', paper=paper(), status=AnswerStatus.DROPPED)
    check('a dropped question has no accepted answer', dropped.accepted, [])
    check('and is not publishable as an answer', dropped.is_publishable, False)
    silent = AnswerEntry(question_number='13', paper=paper())
    check('silence is not a cancellation', silent.status, AnswerStatus.UNKNOWN)


def test_f_a_revised_answer_keeps_the_one_it_replaced() -> None:
    from .pyq_merge import merge_answers
    first = AnswerKey(paper=paper(), kind=AnswerKeyKind.PROVISIONAL, id='k1',
                      entries=[AnswerEntry(question_number='47', paper=paper(),
                                           accepted=['c'], status=AnswerStatus.PUBLISHED)])
    final = AnswerKey(paper=paper(), kind=AnswerKeyKind.FINAL, id='k2',
                      entries=[AnswerEntry(question_number='47', paper=paper(),
                                           accepted=['a'], status=AnswerStatus.PUBLISHED)])
    merged = merge_answers(first, final)
    check('the final answer is the one now published', merged[0].accepted, ['a'])
    check('and it carries the one it replaced',
          merged[0].supersedes.accepted, ['c'])
    check('which is recorded as a revision', merged[0].status, AnswerStatus.REVISED)


def test_g_a_question_is_identified_by_its_paper_and_its_number() -> None:
    from .pyq_merge import merge_questions
    one = extract_questions(DOC, MCQ, paper=paper(paper='Paper-I'))
    two = extract_questions(DOC, MCQ, paper=paper(paper='Paper-II'))
    check('the same number in two papers is two identities',
          one[0].identity_key() == two[0].identity_key(), False)
    report = merge_questions([{'id': 'r1', 'paper': paper(paper='Paper-I'), 'number': '1',
                               'text': one[0].text}], two)
    from .merge import MergeAction
    check('and a question of the other paper never matches it',
          report.decisions[0].action, MergeAction.UNCHANGED)


def test_h_two_shifts_of_one_day_are_two_papers() -> None:
    from .pyq_merge import same_paper
    shift2 = paper(session='Shift 2')
    shift3 = paper(session='Shift 3')
    check('the shifts do not match', same_paper(shift2, shift3), False)
    check('and a key for one is not a key for the other',
          shift2.key() == shift3.key(), False)
    check('a paper silent about its shift still matches one that names it',
          same_paper(paper(), shift2), True)


def test_i_a_previous_cycle_is_a_different_paper() -> None:
    from .pyq_merge import same_paper
    check('2024 and 2025 are not the same paper',
          same_paper(paper(cycle='2024'), paper(cycle='2025')), False)


def test_j_a_bilingual_paper_keeps_both_sides_as_one_question() -> None:
    english = extract_questions(DOC, MCQ, paper=paper(language='English'))[0]
    hindi = extract_questions(DOC, MCQ, paper=paper(language='Hindi'))[0]
    check('each language version carries its own paper identity',
          (english.paper.language, hindi.paper.language), ('English', 'Hindi'))
    check('and they are the same question number', english.number, hindi.number)
    check('so they are distinguishable but not unrelated',
          english.identity_key() != hindi.identity_key(), True)


def test_k_a_question_spanning_a_page_break_is_one_question() -> None:
    text = """
1. What is the capital of the country described in the passage
above, according to the census of that year?
(a) The first option
(b) The second option
"""
    questions = extract_questions(DOC, text, paper=paper())
    check('one question, not two', len(questions), 1)
    check('and its stem is whole',
          'according to the census' in questions[0].text, True)


def test_l_a_flattened_paper_with_options_on_their_own_lines() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('every option is its own option',
          [len(q.options) for q in questions], [4, 4])
    check('and no option leaked into the stem',
          'The first option' in questions[0].text, False)


def test_m_an_option_label_that_looks_like_a_question_number() -> None:
    text = """
1. Which of these is correct?
1. The first option
2. The second option
2. What follows from the above?
1. Another first option
2. Another second option
"""
    questions = extract_questions(DOC, text, paper=paper())
    check('two questions, each with its numbered options', len(questions), 2)
    check('and the options are not read as questions',
          [len(q.options) for q in questions], [2, 2])


def test_n_a_passage_is_kept_once_and_shared() -> None:
    text = """
Directions: Read the following passage and answer the questions that follow.
1. What does the author mean by that phrase?
2. What is the tone of the passage?
"""
    questions = extract_questions(DOC, text, paper=paper())
    check('both questions belong to one passage',
          len({q.passage_id for q in questions}), 1)
    check('the passage is kept', questions[0].passage_text.startswith('Directions'), True)
    check('and they are read as passage-based',
          {q.format for q in questions}, {QuestionFormat.PASSAGE_BASED})


def test_o_a_matching_question_keeps_its_wording() -> None:
    text = ('1. Match List-I with List-II and select the correct answer using the code '
            'given below the Lists.\n(a) A-1, B-2, C-3\n(b) A-2, B-1, C-3\n')
    questions = extract_questions(DOC, text, paper=paper())
    check('the instruction is kept verbatim',
          'Match List-I with List-II' in questions[0].text, True)
    check('and its options are its options', len(questions[0].options), 2)


def test_p_an_answer_key_may_exist_with_no_question_paper() -> None:
    text = ('Subject: Uploading of Final Answer Key(s) of the Combined Examination, 2025 '
            '(Tier-II) -regarding. The Commission has uploaded the Final Answer Key(s) on '
            '17.06.2026. Candidates may view them from 17.06.2026 to 16.07.2026 by '
            'logging-in through their Registered ID and Password.')
    key = read_answer_key_notice(NOTICE, text, exam_id=EXAM,
                                 headline='Combined Examination, 2025 (Tier-II): Final '
                                          'Answer Key(s)')
    check('the key is recorded', key is not None, True)
    check('bound to the exact paper', key.paper.describe(), '2025 · Tier-II')
    check('with the kind the notice calls it', key.kind, AnswerKeyKind.FINAL)
    check('the window it gives', (key.window_opens, key.window_closes),
          ('2026-06-17', '2026-07-16'))
    check('and no per-question answers, because none are published', key.entries, [])
    check('which is said plainly', 'not published publicly' in key.note, True)


def test_q_a_question_without_an_answer_is_still_a_question() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('the question is verified', questions[0].status, Status.VERIFIED)
    check('its answer is not published', questions[0].answer.status,
          AnswerStatus.NOT_PUBLISHED)
    check('and that does not make the question invalid',
          questions[0].source_status, SourceStatus.OFFICIAL_VERIFIED)


def test_r_a_provisional_key_is_read_as_provisional() -> None:
    key = read_answer_key_notice(
        NOTICE, 'Uploading of Tentative Answer Keys of the Combined Examination, 2025 '
                '(Tier-I) on 16.10.2025.', exam_id=EXAM,
        headline='Tentative Answer Keys … Combined Examination (Tier-I) - 2025')
    check('a tentative key is the provisional one', key.kind, AnswerKeyKind.PROVISIONAL)


def test_s_a_final_key_supersedes_the_provisional_one_for_that_paper() -> None:
    provisional = read_answer_key_notice(
        NOTICE, 'Uploading of Tentative Answer Keys of the Combined Examination, 2025 '
                '(Tier-I) on 16.10.2025.', exam_id=EXAM,
        headline='Tentative Answer Keys, Combined Examination, 2025 (Tier-I)')
    final = read_answer_key_notice(
        NOTICE, 'Uploading of Final Answer Key(s) of the Combined Examination, 2025 '
                '(Tier-I) on 09.01.2026.', exam_id=EXAM,
        headline='Final Answer Key(s), Combined Examination, 2025 (Tier-I)')
    keys = link_revisions([provisional, final])
    check('the final key records what it revises', final.revises, provisional.id)
    check('and the provisional key is still there', provisional in keys, True)


def test_t_a_key_for_another_paper_never_supersedes_this_one() -> None:
    tier_one = read_answer_key_notice(
        NOTICE, 'Tentative Answer Keys of the Combined Examination, 2025 (Tier-I).',
        exam_id=EXAM, headline='Tentative Answer Keys, Combined Examination, 2025 (Tier-I)')
    tier_two = read_answer_key_notice(
        NOTICE, 'Final Answer Key(s) of the Combined Examination, 2025 (Tier-II).',
        exam_id=EXAM, headline='Final Answer Key(s), Combined Examination, 2025 (Tier-II)')
    link_revisions([tier_one, tier_two])
    check('a key for Tier-II does not revise the Tier-I key', tier_two.revises, '')


def test_u_two_keys_of_the_same_standing_that_disagree_are_refused() -> None:
    from .pyq_merge import merge_answers
    one = AnswerKey(paper=paper(), kind=AnswerKeyKind.PROVISIONAL, id='k1',
                    entries=[AnswerEntry(question_number='9', paper=paper(),
                                         accepted=['a'], status=AnswerStatus.PUBLISHED)])
    two = AnswerKey(paper=paper(), kind=AnswerKeyKind.PROVISIONAL, id='k2',
                    entries=[AnswerEntry(question_number='9', paper=paper(),
                                         accepted=['d'], status=AnswerStatus.PUBLISHED)])
    merged = merge_answers(one, two)
    check('neither answer is published', merged[0].accepted, [])
    check('the disagreement is recorded', merged[0].status, AnswerStatus.UNKNOWN)
    check('and the reason is legible', 'neither revises the other' in merged[0].note, True)


def test_v_a_paper_of_another_exam_is_refused() -> None:
    links = ['https://a.example/QP-EXM-25-OTHER.pdf',
             'https://a.example/QP-ZZZ-25-SOMETHING.pdf']
    kept, rejected = catalogue_papers(links, exam_id=EXAM, exam_codes=CODES, doc=DOC,
                                      page_text=' '.join(links))
    check('only this exam’s file is kept', len(kept), 1)
    check('and the other is refused by name',
          rejected[0][1], 'the file does not carry this exam’s own code')


def test_w_a_paper_of_another_cycle_keeps_its_own_cycle() -> None:
    older = identity_from_text('QP-EXM-24-GENERAL-STUDIES-PAPER-I.pdf', exam_id=EXAM,
                               codes=CODES, subject='General Studies')
    newer = identity_from_text('QP-EXM-26-GENERAL-STUDIES-PAPER-I.pdf', exam_id=EXAM,
                               codes=CODES, subject='General Studies')
    check('each carries the cycle its own name gives', (older.cycle, newer.cycle),
          ('2024', '2026'))
    from .pyq_merge import same_paper
    check('and they are not the same paper', same_paper(older, newer), False)


def test_x_paper_ii_never_becomes_paper_i() -> None:
    from .pyq_merge import same_paper
    one = identity_from_text('QP-EXM-26-GENERAL-STUDIES-PAPER-I.pdf', exam_id=EXAM,
                             codes=CODES)
    two = identity_from_text('QP-EXM-26-GENERAL-STUDIES-PAPER-II.pdf', exam_id=EXAM,
                             codes=CODES)
    check('the papers are read apart', (one.paper, two.paper), ('Paper-I', 'Paper-II'))
    check('and never match', same_paper(one, two), False)


def test_y_a_shift_named_in_a_notice_is_kept() -> None:
    identity = identity_from_text(
        'Answer key of the Examination, 2025 (Tier-I) Shift 2', exam_id=EXAM)
    check('the shift is part of the identity', identity.session, 'Shift 2')
    check('and the tier with it', identity.stage, 'Tier-I')


def test_z_a_key_whose_paper_cannot_be_identified_is_refused() -> None:
    key = read_answer_key_notice(
        NOTICE, 'The Commission has uploaded answer keys on its website. Candidates may '
                'view them by logging in.', exam_id=EXAM,
        headline='Uploading of Answer Keys')
    check('a key naming no paper is not recorded at all', key, None)


def test_aa_there_is_no_fallback() -> None:
    check('a paper with no exam id yields no questions',
          extract_questions(DOC, MCQ, paper=PaperIdentity(exam_id='')), [])
    check('and an empty document yields none either',
          extract_questions(DOC, '', paper=paper()), [])


def test_ab_one_exam_s_paper_cannot_reach_another() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('every question carries this exam',
          {q.paper.exam_id for q in questions}, {EXAM})
    other = paper()
    check('and an identity of another exam never matches',
          PaperIdentity(exam_id='exam-two-2026', cycle='2025',
                        stage='Tier-I').matches(other), False)


def test_ac_the_accessor_filters_on_the_exact_exam() -> None:
    """The frontend's own rule, checked here so it cannot drift."""
    import io
    source = io.open('src/data.ts', encoding='utf-8').read()
    check('the accessor filters on the exact id',
          'ALL_OFFICIAL_QUESTIONS.filter(q => q.examId === examId)' in source, True)


def test_ad_every_published_item_cites_its_document() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('every question has evidence', all(q.evidence for q in questions), True)
    check('and every span is verbatim in the paper',
          all(e.is_verbatim for q in questions for e in q.evidence), True)


def test_ae_only_official_evidence_may_be_badged_official() -> None:
    secondary = extract_questions(DOC, MCQ, paper=paper(),
                                  source_status=SourceStatus.SECONDARY_UNVERIFIED)
    check('a secondary source is marked as one',
          {q.source_status for q in secondary}, {SourceStatus.SECONDARY_UNVERIFIED})
    check('and is not publishable as official',
          any(q.is_publishable for q in secondary), False)
    official = extract_questions(DOC, MCQ, paper=paper())
    check('an official reading is', official[0].is_publishable, True)


def test_af_question_numbers_are_scoped_by_paper() -> None:
    one = extract_questions(DOC, MCQ, paper=paper(paper='Paper-I'))[0]
    two = extract_questions(DOC, MCQ, paper=paper(paper='Paper-II'))[0]
    check('both are question 1', (one.number, two.number), ('1', '1'))
    check('and their identities differ',
          one.identity_key() != two.identity_key(), True)


def test_ag_no_marking_is_assumed() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('a paper that prints no marks gives no marks',
          [q.marks.has_value for q in questions], [False, False])
    check('and no negative marking is invented',
          [q.negative_marks.has_value for q in questions], [False, False])
    priced = extract_questions(DOC, '1. Discuss the question. (15 marks)\n', paper=paper())
    check('a paper that prints them is read', priced[0].marks.value, 15.0)


def test_ah_no_answer_is_fabricated() -> None:
    questions = extract_questions(DOC, MCQ, paper=paper())
    check('no question arrives with an answer',
          all(q.answer.status is AnswerStatus.NOT_PUBLISHED for q in questions), True)
    check('and none is publishable as one',
          any(q.answer.is_publishable for q in questions), False)


def test_ai_an_unreadable_paper_says_why() -> None:
    links = ['https://a.example/QP-EXM-26-GENERAL-STUDIES-PAPER-I.pdf']
    kept, _rejected = catalogue_papers(links, exam_id=EXAM, exam_codes=CODES, doc=DOC,
                                       page_text=' '.join(links))
    paper_record = mark_unreadable(kept[0], words=0)
    check('the paper is still catalogued', paper_record.identity.is_paper_level, True)
    check('its contents are not extracted', paper_record.contents.has_value, False)
    check('and the reason is about the file, not the authority',
          'no text layer' in paper_record.contents.note, True)


def test_a_listing_of_many_examinations_is_filtered_by_the_file_itself() -> None:
    links = [f'https://a.example/QP-EXM-26-SUBJECT-{n}.pdf' for n in range(3)] + \
            [f'https://a.example/QP-OTH-26-SUBJECT-{n}.pdf' for n in range(5)]
    kept, rejected = catalogue_papers(links, exam_id=EXAM, exam_codes=CODES, doc=DOC,
                                      page_text=' '.join(links))
    check('only this exam’s files are kept', len(kept), 3)
    check('and the rest are refused', len(rejected), 5)


def test_no_exam_is_named_in_the_readers() -> None:
    import io
    import re
    for path in ('tools/exam_builder/pyq.py', 'tools/exam_builder/pyq_merge.py'):
        source = io.open(path, encoding='utf-8').read()
        for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'cgl', 'cse'):
            check(f'{path} never names {forbidden.upper()}',
                  re.findall(rf'\b{forbidden}\b', source, re.I), [])
        for branch in ('if exam ==', 'if exam_id ==', "== 'exam-", 'exam_id.startswith'):
            check(f'{path} has no branch on a particular exam ({branch})',
                  branch in source, False)


def main() -> int:
    for fn in (test_a_a_basic_mcq,
               test_b_a_descriptive_question_gets_no_options,
               test_c_a_numerical_question_keeps_its_wording,
               test_d_a_key_may_accept_more_than_one_option,
               test_e_a_dropped_question_is_a_published_decision,
               test_f_a_revised_answer_keeps_the_one_it_replaced,
               test_g_a_question_is_identified_by_its_paper_and_its_number,
               test_h_two_shifts_of_one_day_are_two_papers,
               test_i_a_previous_cycle_is_a_different_paper,
               test_j_a_bilingual_paper_keeps_both_sides_as_one_question,
               test_k_a_question_spanning_a_page_break_is_one_question,
               test_l_a_flattened_paper_with_options_on_their_own_lines,
               test_m_an_option_label_that_looks_like_a_question_number,
               test_n_a_passage_is_kept_once_and_shared,
               test_o_a_matching_question_keeps_its_wording,
               test_p_an_answer_key_may_exist_with_no_question_paper,
               test_q_a_question_without_an_answer_is_still_a_question,
               test_r_a_provisional_key_is_read_as_provisional,
               test_s_a_final_key_supersedes_the_provisional_one_for_that_paper,
               test_t_a_key_for_another_paper_never_supersedes_this_one,
               test_u_two_keys_of_the_same_standing_that_disagree_are_refused,
               test_v_a_paper_of_another_exam_is_refused,
               test_w_a_paper_of_another_cycle_keeps_its_own_cycle,
               test_x_paper_ii_never_becomes_paper_i,
               test_y_a_shift_named_in_a_notice_is_kept,
               test_z_a_key_whose_paper_cannot_be_identified_is_refused,
               test_aa_there_is_no_fallback,
               test_ab_one_exam_s_paper_cannot_reach_another,
               test_ac_the_accessor_filters_on_the_exact_exam,
               test_ad_every_published_item_cites_its_document,
               test_ae_only_official_evidence_may_be_badged_official,
               test_af_question_numbers_are_scoped_by_paper,
               test_ag_no_marking_is_assumed,
               test_ah_no_answer_is_fabricated,
               test_ai_an_unreadable_paper_says_why,
               test_a_listing_of_many_examinations_is_filtered_by_the_file_itself,
               test_no_exam_is_named_in_the_readers):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('pyq: the paper is the identity, and nothing is answered that nobody answered')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
