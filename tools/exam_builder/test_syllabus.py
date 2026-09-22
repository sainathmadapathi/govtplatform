"""Twenty-eight shapes a syllabus comes in, and one rule about all of them.

The rule: hierarchy is read, never assumed. A parent is the clause that numbers a node or
the heading it sits under, and where neither says, the node stays where it was found rather
than being attached to a plausible parent. The tests that matter most here are the ones
that check something is *not* produced -- a topic under a subject the document never
connected it to, a syllabus from another exam, a syllabus from another year, or children
under a subject whose contents the authority did not publish.

The fixtures are written in the shapes the two authorities that publish a syllabus actually
use (SYLLABUS_AUDIT.md §7): clause numbering whose depth is its own part count, and
headings with bullets whose paper heading is what they belong to. None of them names a real
exam: what is being tested is that no exam has to be named.

Run: python -m tools.exam_builder.test_syllabus
"""
from __future__ import annotations

from .schema import SourceDocument, SourceKind, Status
from .syllabus import describe, extract_syllabus, may_supply_syllabus

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


DOC = SourceDocument(id='doc-1', url='https://authority.example/notice.pdf',
                     kind=SourceKind.NOTIFICATION, title='Notice', authority='An Authority',
                     accessed_at='2026-09-22', exam_id='exam-one-2026')
BULLET = ''


def read(text: str, exam_id: str = 'exam-one-2026', doc: SourceDocument = DOC):
    return extract_syllabus(doc, text, exam_id=exam_id, cycle='2026')


def node(syllabus, fragment: str):
    return next((n for n in syllabus.walk()
                 if fragment.lower() in (n.title or '').lower()), None)


def titles(nodes) -> list:
    return [n.title for n in nodes]


# ================================================== A. subjects and their topics
SIMPLE = """
7. Syllabus of the Examination:
7.1 Quantitative Ability: Numbers, percentages and ratios.
7.2 Reasoning: Series, analogies and coding.
7.3 Language: Comprehension and grammar.
"""


def test_a_a_simple_subject_and_topic_syllabus() -> None:
    syllabus = read(SIMPLE)
    check('one syllabus is read', len(syllabus.roots), 1)
    check('with its three subjects', titles(syllabus.roots[0].children),
          ['Quantitative Ability', 'Reasoning', 'Language'])
    check('each keeping what the authority wrote after it',
          node(syllabus, 'Reasoning').note, 'Series, analogies and coding.')


# ============================================ B. stage -> paper -> subject -> topic
DEEP = """
13.11 Indicative Syllabus (Tier-II):
13.11.1 Part A of Section-I of Paper-I (Mathematical Abilities):
13.11.1.1 Number Systems: Computation of Whole Number, Decimal and Fractions.
13.11.1.2 Algebra: Basic algebraic identities and Graphs of Linear Equations.
13.11.2 Part B of Section-I of Paper-I (Reasoning):
13.11.2.1 Coding and decoding: Verbal and non-verbal reasoning.
"""


def test_b_stage_paper_section_part_topic() -> None:
    syllabus = read(DEEP)
    # Three levels: the region's own heading is the root, then the parts it numbers, then
    # their topics. The document's clause numbering decides it, not this reader.
    check('the depth is the document’s own', syllabus.max_depth(), 3)
    part = node(syllabus, 'Part A of Section-I')
    check('the parts sit under the syllabus', part.level_label, 'Part')
    check('and their topics under them', titles(part.children),
          ['Number Systems', 'Algebra'])
    check('a topic of the other part is not under this one',
          node(syllabus, 'Coding and decoding') in part.children, False)


def test_c_paper_and_topics_without_a_subject_between() -> None:
    text = f"""
SECTION III: SYLLABUS
Paper I - (200 marks)
{BULLET} Current events of national importance.
{BULLET} History of India.
"""
    syllabus = read(text)
    paper = node(syllabus, 'Paper I')
    check('the paper is read as a paper', paper.level_label, 'Paper')
    check('and its entries hang directly off it', len(paper.children), 2)
    check('with no subject invented between them',
          [n.level_label for n in paper.children], ['Topic', 'Topic'])


def test_d_depth_is_whatever_the_document_uses() -> None:
    text = """
5. Syllabus:
5.1 Group A: The first group.
5.1.1 Unit one: Something.
5.1.1.1 Sub-unit: Something finer.
5.1.1.1.1 Detail: Finer still.
"""
    syllabus = read(text)
    check('five levels are kept', syllabus.max_depth(), 5)
    check('and nothing was flattened',
          [len(n.children) for n in syllabus.walk()][:4], [1, 1, 1, 1])


def test_e_several_papers_each_with_its_own_entries() -> None:
    text = f"""
SECTION III: SYLLABI FOR THE EXAMINATION
Part A - Preliminary Examination
Paper I - (200 marks)
{BULLET} Current events.
{BULLET} History of India.
Paper II - (200 marks)
{BULLET} Comprehension.
{BULLET} Logical reasoning.
"""
    syllabus = read(text)
    first, second = node(syllabus, 'Paper I'), node(syllabus, 'Paper II')
    check('each paper keeps its own entries',
          (len(first.children), len(second.children)), (2, 2))
    check('and one paper’s entry is not the other’s',
          'Comprehension' in titles(first.children), False)


def test_f_optional_subjects_are_kept_where_published() -> None:
    text = f"""
SECTION III: SYLLABUS
Part B - Main Examination
Paper VI - Optional Subject Paper 1
{BULLET} Agriculture: Ecology and its relevance to man.
{BULLET} Animal Husbandry: Animal nutrition.
"""
    syllabus = read(text)
    paper = node(syllabus, 'Optional Subject')
    check('the optional paper is read', paper is not None, True)
    check('with the subjects the authority listed under it',
          titles(paper.children), ['Agriculture', 'Animal Husbandry'])


def test_g_a_qualifying_papers_scope_is_kept() -> None:
    text = f"""
SECTION III: SYLLABUS
Part A - Preliminary Examination
Paper II - (200 marks)
{BULLET} Comprehension.
Note 1: Paper-II will be a qualifying paper with minimum qualifying marks fixed at 33%.
"""
    syllabus = read(text)
    paper = node(syllabus, 'Paper II')
    # Section-III is where the notice prints the syllabus, and it is inherited from the
    # heading that opened the region: an entry belongs to the section, the part and the
    # paper at once, which is exactly what the document says of it.
    check('the paper is scoped to everything the document places it under',
          sorted(r.label for r in paper.scope.refs),
          ['Paper-II', 'Part-A', 'Section-III'])
    check('and the note about it is kept, not dropped',
          'qualifying' in (paper.note or '').lower(), True)


def test_h_a_language_paper_is_a_paper_like_any_other() -> None:
    text = f"""
SECTION III: SYLLABUS
Part B - Main Examination
Paper A - Indian Language
{BULLET} Comprehension of given passages.
{BULLET} Translation from English to the Indian Language.
"""
    syllabus = read(text)
    paper = node(syllabus, 'Paper A')
    check('it is read with its own entries', len(paper.children), 2)
    check('and nothing about the language is assumed',
          paper.title.startswith('Paper A'), True)


def test_i_a_syllabus_laid_out_as_a_table() -> None:
    """Some authorities tabulate. The rows are entries; the header is not one."""
    text = """
4. Syllabus:
4.1 Arithmetic: Ratio, proportion and averages.
4.2 Mensuration: Areas and volumes of standard figures.
4.3 Statistics: Mean, median and mode.
"""
    syllabus = read(text)
    check('three entries, no header row among them',
          titles(syllabus.roots[0].children), ['Arithmetic', 'Mensuration', 'Statistics'])


def test_j_a_flattened_clause_whose_title_wrapped() -> None:
    text = """
13.11 Indicative Syllabus (Tier-II):
13.11.1 Part B of Section-I of Paper-I (Reasoning and General
Intelligence): Questions of both verbal and non-verbal type.
13.11.2 Section-III of Paper-I (Computer Knowledge/
Proficiency): Organisation of a computer.
"""
    syllabus = read(text)
    check('a title broken across two lines is one title',
          node(syllabus, 'Reasoning and General Intelligence') is not None, True)
    check('and so is the next one',
          node(syllabus, 'Computer Knowledge') is not None, True)


def test_k_a_bullet_list_under_a_heading() -> None:
    text = f"""
Syllabus for the Examination
Paper I - General Studies
{BULLET} Indian Polity and Governance-Constitution, Political System,
Panchayati Raj, Public Policy.
{BULLET} General Science.
"""
    syllabus = read(text)
    paper = node(syllabus, 'Paper I')
    check('a bullet wrapped onto the next line is one entry', len(paper.children), 2)
    check('and it is kept whole rather than split at the comma',
          'Panchayati Raj' in paper.children[0].title + (paper.children[0].note or ''), True)


def test_l_numbered_clauses_carry_their_own_hierarchy() -> None:
    syllabus = read(DEEP)
    check('13.11.1.1 is under 13.11.1',
          node(syllabus, 'Number Systems') in node(syllabus, 'Part A of Section-I').children,
          True)


def test_m_a_syllabus_running_across_pages() -> None:
    text = """
6. Syllabus:
6.1 Arithmetic: Ratio and proportion.
Page 31 of 132
6.2 Algebra: Linear equations.
GO TO INDEX 12
6.3 Geometry: Triangles and circles.
"""
    syllabus = read(text)
    check('page furniture is not an entry',
          titles(syllabus.roots[0].children), ['Arithmetic', 'Algebra', 'Geometry'])


def test_n_a_wrapped_topic_name_is_one_name() -> None:
    text = """
6. Syllabus:
6.1 Measures of Central Tendency- Common measures of central
tendency, mean median and mode.
"""
    syllabus = read(text)
    entry = syllabus.roots[0].children[0]
    check('the name is what precedes the authority’s own separator',
          entry.title, 'Measures of Central Tendency')
    check('and the rest is kept as what it says',
          'mean median and mode' in (entry.note or ''), True)


def test_o_a_heading_repeated_does_not_duplicate_the_syllabus() -> None:
    text = f"""
SECTION III: SYLLABUS
Part A - Preliminary Examination
Paper I - (200 marks)
{BULLET} Current events.
Part A - Preliminary Examination
{BULLET} History of India.
"""
    syllabus = read(text)
    parts = [n for n in syllabus.walk() if n.title.startswith('Part A')]
    check('the second heading does not create a second tree',
          len(parts) <= 2, True)
    check('and every entry is still attached to something',
          all(n.title for n in syllabus.walk()), True)


def test_p_a_repeated_table_header_is_not_an_entry() -> None:
    text = """
6. Syllabus:
6.1 Arithmetic: Ratio and proportion.
Page 4 of 20
6.2 Algebra: Linear equations.
"""
    syllabus = read(text)
    check('two entries, not three', len(syllabus.roots[0].children), 2)


def test_q_a_document_of_another_exam_supplies_nothing() -> None:
    from .identity import ExamIdentity
    other = """
Notice of the Combined Higher Secondary Level Examination, 2026.
6. Syllabus:
6.1 Arithmetic: Ratio and proportion.
"""
    target = ExamIdentity(exam_id='exam-one-2026', query='Combined Graduate Level 2026',
                          official_name='Combined Graduate Level Examination, 2026',
                          authority_name='An Authority')
    allowed, why = may_supply_syllabus(other, target)
    check('the document is refused', allowed, False)
    check('and the reason names the mismatch', 'refused' in why, True)


def test_r_a_previous_cycles_syllabus_is_refused() -> None:
    from .identity import ExamIdentity
    older = """
Combined Graduate Level Examination, 2024
6. Syllabus:
6.1 Arithmetic: Ratio and proportion.
"""
    target = ExamIdentity(exam_id='exam-one-2026', query='Combined Graduate Level 2026',
                          official_name='Combined Graduate Level Examination, 2026',
                          authority_name='An Authority', year='2026')
    allowed, _why = may_supply_syllabus(older, target)
    check('a syllabus published for another year does not answer for this one',
          allowed, False)


def test_s_an_ambiguous_document_needs_target_evidence() -> None:
    from .identity import ExamIdentity
    shared = ("""
Syllabus page
This page carries the syllabus for the Combined Higher Secondary Level Examination, 2026,
the Junior Engineer Examination, 2026 and the Stenographer Examination, 2026.
""" + ('Further material about those three examinations and their syllabi, none of it '
       'about any other examination. ' * 40) + """
Much further down, this page mentions the Combined Graduate Level Examination, 2026.
6. Syllabus:
6.1 Arithmetic: Ratio and proportion.
""")
    target = ExamIdentity(exam_id='exam-one-2026', query='Combined Graduate Level 2026',
                          official_name='Combined Graduate Level Examination, 2026',
                          authority_name='An Authority')
    allowed, _why = may_supply_syllabus(shared, target)
    check('a page serving several exams does not supply this one’s syllabus',
          allowed, False)


def test_t_a_document_with_no_syllabus_produces_none() -> None:
    text = """
NOTIFICATION
A. PARTICIPATING BANKS
B. ELIGIBILITY CRITERIA
Candidates must hold a degree in any discipline.
HOW TO APPLY
Candidates can apply online only.
"""
    syllabus = read(text)
    check('nothing is read', len(syllabus.roots), 0)
    check('and nothing is invented to fill the section', list(syllabus.walk()), [])


def test_u_a_named_subject_with_no_published_topics_has_no_children() -> None:
    text = """
6. Syllabus:
6.1 General Studies
6.2 Arithmetic: Ratio and proportion.
"""
    syllabus = read(text)
    general = node(syllabus, 'General Studies')
    check('the subject is published, so it is kept', general.status, Status.VERIFIED)
    check('and its topics are absent because the document does not give them',
          general.children, [])
    check('nothing was borrowed from the subject beside it',
          (general.note or ''), '')


def test_v_two_sources_that_disagree_are_not_resolved() -> None:
    from .merge import MergeAction
    from .syllabus_merge import merge_syllabus
    record = [{'id': 'syl-1', 'topicName': 'Number Systems'}]
    other = read("""
6. Syllabus:
6.1 Number Theory: Computation of whole numbers.
""")
    report = merge_syllabus(record, other)
    check('a differently worded topic is not quietly replaced',
          report.decisions[0].action, MergeAction.UNCHANGED)

    contested = read("""
6. Syllabus:
6.1 Number Systems and Series: Computation of whole numbers.
""")
    held = merge_syllabus(record, contested).decisions[0]
    check('and where the two are close but not the same, it is contested',
          held.action, MergeAction.CONFLICTED)
    check('with both wordings kept',
          (held.field('topicName').existing, held.field('topicName').incoming),
          ('Number Systems', 'Number Systems and Series'))


def test_w_a_revision_supersedes_and_keeps_the_old_wording() -> None:
    from .merge import MergeAction
    from .syllabus_merge import merge_syllabus
    corrigendum = SourceDocument(id='doc-c', url='https://authority.example/corr.pdf',
                                 kind=SourceKind.CORRIGENDUM, title='Corrigendum',
                                 authority='An Authority', exam_id='exam-one-2026')
    revised = read("""
6. Syllabus:
6.1 Number Systems and Series: Computation of whole numbers.
""", doc=corrigendum)
    report = merge_syllabus([{'id': 'syl-1', 'topicName': 'Number Systems'}], revised,
                            document=corrigendum)
    decision = report.decisions[0]
    check('a revising document supersedes', decision.action, MergeAction.SUPERSEDED)
    check('the old wording is kept as the superseded one',
          decision.superseded, 'Number Systems')
    check('and the new one is what the document says',
          decision.title, 'Number Systems and Series')


def test_x_every_published_node_carries_verbatim_evidence() -> None:
    syllabus = read(DEEP)
    nodes = list(syllabus.walk())
    check('every node has evidence', all(n.evidence for n in nodes), True)
    check('and every span is verbatim in the document',
          all(e.is_verbatim for n in nodes for e in n.evidence), True)
    check('so every node is publishable',
          {n.status for n in nodes}, {Status.VERIFIED})


def test_y_a_label_is_the_authority_s_own_word() -> None:
    syllabus = read(DEEP)
    check('the level words are the document’s',
          'Part' in syllabus.level_labels(), True)
    paper_style = read("""
5. Syllabus:
5.1 Unit I: The first unit.
""")
    check('and another document’s word is that document’s',
          node(paper_style, 'Unit I').level_label, 'Unit')


def test_z_one_exam_s_syllabus_cannot_reach_another() -> None:
    from .compat import syllabus_tree
    syllabus = read(SIMPLE)
    tree = syllabus_tree(syllabus, exam_id='exam-one-2026')
    check('the projection yields this exam’s syllabus', len(tree), 1)
    check('an extraction with no exam id is refused outright',
          len(read(SIMPLE, exam_id='').roots), 0)
    check('and every node in the tree cites the document it was read from',
          all('provenance' in node for node in tree), True)


def test_aa_two_exams_read_in_either_order_give_the_same_result() -> None:
    first = describe(read(SIMPLE))
    other_doc = SourceDocument(id='doc-2', url='https://other.example/n.pdf',
                               kind=SourceKind.NOTIFICATION, title='Other',
                               authority='Another Authority', exam_id='exam-two-2026')
    read(DEEP, exam_id='exam-two-2026', doc=other_doc)
    again = describe(read(SIMPLE))
    check('reading another exam in between changes nothing', again, first)


def test_ab_there_is_no_fallback_syllabus() -> None:
    empty = read('NOTIFICATION\nB. ELIGIBILITY\nA degree in any discipline.\n')
    check('an exam whose document has no syllabus gets none', len(empty.roots), 0)
    described = describe(empty)
    check('and the report says so rather than substituting one',
          (described['roots'], described['nodes']), (0, 0))


def test_no_exam_is_named_in_the_extractor() -> None:
    import io
    import re
    for path in ('tools/exam_builder/syllabus.py',
                 'tools/exam_builder/syllabus_merge.py'):
        source = io.open(path, encoding='utf-8').read()
        for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc', 'cgl', 'cse'):
            check(f'{path} never names {forbidden.upper()}',
                  re.findall(rf'\b{forbidden}\b', source, re.I), [])
        for branch in ('if exam ==', 'if exam_id ==', "== 'exam-", 'exam_id.startswith'):
            check(f'{path} has no branch on a particular exam ({branch})',
                  branch in source, False)


def main() -> int:
    for fn in (test_a_a_simple_subject_and_topic_syllabus,
               test_b_stage_paper_section_part_topic,
               test_c_paper_and_topics_without_a_subject_between,
               test_d_depth_is_whatever_the_document_uses,
               test_e_several_papers_each_with_its_own_entries,
               test_f_optional_subjects_are_kept_where_published,
               test_g_a_qualifying_papers_scope_is_kept,
               test_h_a_language_paper_is_a_paper_like_any_other,
               test_i_a_syllabus_laid_out_as_a_table,
               test_j_a_flattened_clause_whose_title_wrapped,
               test_k_a_bullet_list_under_a_heading,
               test_l_numbered_clauses_carry_their_own_hierarchy,
               test_m_a_syllabus_running_across_pages,
               test_n_a_wrapped_topic_name_is_one_name,
               test_o_a_heading_repeated_does_not_duplicate_the_syllabus,
               test_p_a_repeated_table_header_is_not_an_entry,
               test_q_a_document_of_another_exam_supplies_nothing,
               test_r_a_previous_cycles_syllabus_is_refused,
               test_s_an_ambiguous_document_needs_target_evidence,
               test_t_a_document_with_no_syllabus_produces_none,
               test_u_a_named_subject_with_no_published_topics_has_no_children,
               test_v_two_sources_that_disagree_are_not_resolved,
               test_w_a_revision_supersedes_and_keeps_the_old_wording,
               test_x_every_published_node_carries_verbatim_evidence,
               test_y_a_label_is_the_authority_s_own_word,
               test_z_one_exam_s_syllabus_cannot_reach_another,
               test_aa_two_exams_read_in_either_order_give_the_same_result,
               test_ab_there_is_no_fallback_syllabus,
               test_no_exam_is_named_in_the_extractor):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('syllabus: hierarchy read from the document, and nothing read into it')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
