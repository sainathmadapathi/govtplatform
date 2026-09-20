"""Who may apply, read from the document that says so — and never from anywhere else.

The regression at the bottom is the reason this phase exists. A function returned 3 for OBC,
5 for SC and ST and 10 for PwBD, for every exam in the country, with no source. It was right
for many notices and wrong for some, and nothing in the product could tell which. The first
real extraction against an actual notice found that authority publishing six relaxations
including two the constant could not express — PwBD (OBC) at 13 years and PwBD (SC/ST) at 15
— so the constant was not merely unsourced, it was incomplete.

Every fixture is invented.

Run: python -m tools.exam_builder.test_eligibility
"""
from __future__ import annotations

from .eligibility import (extract_age_rules, extract_eligibility, extract_qualifications,
                          extract_relaxations, extract_requirements, extract_vacancies)
from .identity import ExamIdentity, IdentityVerdict, verify
from .schema import ScopeKind, SourceDocument, SourceKind, Status

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


def doc(doc_id: str = 'doc-1') -> SourceDocument:
    return SourceDocument(id=doc_id, url=f'https://authority.example/{doc_id}.pdf',
                          kind=SourceKind.NOTIFICATION, title='Notice of Examination',
                          authority='Example Authority', accessed_at='2026-09-20')


def rules(text: str, **kw):
    return extract_age_rules(doc(), text, **kw)


def relax(text: str, **kw):
    return extract_relaxations(doc(), text, **kw)


# ============================================================ A/B/C/D. age
def test_a_exam_wide_age() -> None:
    r = rules('The candidate must not be less than 21 years and not more than 30 years.')
    check('A: one exam-wide rule', len(r), 1)
    check('A: the band is read', (r[0].minimum_age.value, r[0].maximum_age.value),
          (21.0, 30.0))
    check('A: and it governs the whole exam', r[0].is_global, True)
    check('A: evidenced verbatim', r[0].maximum_age.is_publishable, True)


def test_a_table_cell_band() -> None:
    """A table cell says "18-30 years" and none of the sentence wording."""
    r = rules('Assistant Officer | Group B | 18-30 years')
    check('a bare band in a cell is still an age rule',
          (r[0].minimum_age.value, r[0].maximum_age.value) if r else None, (18.0, 30.0))


def test_b_post_specific_age() -> None:
    from .schema import Post
    posts = [Post(id='p-alpha', name='Alpha Officer'),
             Post(id='p-beta', name='Beta Officer')]
    text = ('For the post of Alpha Officer the age must be between 21 years and 27 years.\n'
            'For the post of Beta Officer the age must be between 18 years and 32 years.')
    r = rules(text, posts=posts)
    check('B: two rules', len(r), 2)
    check('B: each scoped to its own post',
          sorted(x.scope.of(ScopeKind.POST)[0].ref for x in r), ['p-alpha', 'p-beta'])
    check('B: with different bands',
          sorted((x.minimum_age.value, x.maximum_age.value) for x in r),
          [(18.0, 32.0), (21.0, 27.0)])


def test_c_dob_range_is_kept_as_printed() -> None:
    r = rules('Candidates must have been born not earlier than 02.08.1994 '
              'and not later than 01.08.2005.')
    check('C: the window is read',
          (r[0].born_not_earlier_than.value, r[0].born_not_later_than.value),
          ('1994-08-02', '2005-08-01'))
    check('C: and no age band is invented from it',
          r[0].minimum_age.status, Status.NOT_EXTRACTED)


def test_d_cutoff_date() -> None:
    r = rules('The age limit is 21 to 30 years as on 01.08.2026.')
    check('D: the reckoning date is read', r[0].cutoff_date.value, '2026-08-01')
    check('D: from the exam’s own sentence', r[0].cutoff_date.is_publishable, True)


# ======================================================= E/F. relaxation
def test_e_category_relaxation_in_prose() -> None:
    text = ('Upper age limit is relaxable by 5 years for Scheduled Castes candidates.\n'
            'Relaxation of 3 years is available to Other Backward Classes candidates.\n'
            'The upper age limit for Persons with Benchmark Disabilities is 40 years.\n'
            'No age relaxation is admissible to Economically Weaker Sections candidates.')
    found = {r.category_label: r for r in relax(text)}
    check('E: an increment is years',
          found['Scheduled Castes'].years.value, 5.0)
    check('E: another increment', found['Other Backward Classes'].years.value, 3.0)
    check('E: a ceiling is not read as an increment',
          (found['Persons with Benchmark Disabilities'].absolute_maximum.value,
           found['Persons with Benchmark Disabilities'].years.has_value), (40.0, False))
    check('E: a stated refusal is NOT_PUBLISHED',
          found['Economically Weaker Sections'].years.status, Status.NOT_PUBLISHED)
    check('E: every figure is evidenced',
          all(r.years.is_publishable or r.absolute_maximum.is_publishable
              for r in (found['Scheduled Castes'], found['Other Backward Classes'],
                        found['Persons with Benchmark Disabilities'])), True)


def test_e_relaxation_table() -> None:
    """The shape authorities actually use, once a PDF has flattened it."""
    text = ('Permissible relaxation in upper age limit and category codes are as follows:\n'
            'Code No Category Age-relaxation permissible beyond upper age limit\n'
            '01 SC/ST 5 years\n'
            '02 OBC 3 years\n'
            '03 PwBD 10 years\n'
            '04 PwBD (OBC) 13 years\n')
    found = {r.category_label: r.years.value for r in relax(text)}
    check('E: rows are read from the table',
          {k: v for k, v in found.items() if k in ('SC/ST', 'OBC', 'PwBD', 'PwBD (OBC)')},
          {'SC/ST': 5.0, 'OBC': 3.0, 'PwBD': 10.0, 'PwBD (OBC)': 13.0})
    check('E: a combined category stays one category, with its own figure',
          'PwBD (OBC)' in found, True)


def test_f_post_specific_relaxation() -> None:
    from .schema import Post
    posts = [Post(id='p-alpha', name='Alpha Officer')]
    text = ('For the post of Alpha Officer the upper age limit is relaxable by '
            '7 years for Scheduled Tribes candidates.')
    r = relax(text, posts=posts)
    check('F: the relaxation is scoped to the post',
          [x.ref for x in r[0].scope.of(ScopeKind.POST)], ['p-alpha'])
    check('F: and to the category',
          [x.label for x in r[0].scope.of(ScopeKind.CATEGORY)], ['Scheduled Tribes'])
    check('F: with the authority’s figure', r[0].years.value, 7.0)


def test_relaxation_without_a_figure_is_held_for_review() -> None:
    r = relax('Age relaxation is available to Scheduled Castes candidates as per rules.')
    check('a relaxation with no number is not a value',
          r[0].years.status, Status.NEEDS_REVIEW)
    check('and it is not publishable', r[0].years.is_publishable, False)


# ==================================================== G/H/I/J/K. the rest
def test_g_qualification_keeps_its_wording() -> None:
    q = extract_qualifications(
        doc(), 'Essential educational qualification: Bachelor Degree in Engineering with '
               '60% marks from a recognised University as on 01.08.2026.')
    check('G: the requirement is kept as printed',
          'Bachelor Degree in Engineering with 60% marks' in q[0].requirement.value, True)
    check('G: marked essential where the authority says so', q[0].is_essential, True)
    check('G: and the date it must be held by', 'as on' in (q[0].as_on.value or ''), True)


def test_g_a_tenth_pass_exam_is_representable() -> None:
    q = extract_qualifications(
        doc(), 'Candidates must have passed the Matriculation examination from a '
               'recognised Board to be eligible for this recruitment.')
    check('an exam that does not need a degree is representable',
          bool(q) and 'Matriculation' in q[0].requirement.value, True)


def test_h_experience() -> None:
    r = extract_requirements(
        doc(), 'Candidates must possess experience of not less than three years in a '
               'supervisory capacity in a recognised organisation.')
    check('H: experience is a requirement of its own',
          [x.kind for x in r], ['EXPERIENCE'])
    check('H: kept in the authority’s words',
          'not less than three years' in r[0].statement.value, True)


def test_i_nationality() -> None:
    r = extract_requirements(doc(), 'A candidate must be a citizen of Exampleland.')
    check('I: nationality is read', [x.kind for x in r], ['NATIONALITY'])


def test_j_physical_requirement() -> None:
    r = extract_requirements(
        doc(), 'Candidates shall meet the physical standards: minimum height 165 cm and '
               'chest 81 cm with expansion.')
    check('J: physical standards are read', [x.kind for x in r], ['PHYSICAL'])


def test_k_medical_requirement() -> None:
    r = extract_requirements(
        doc(), 'Candidates must satisfy the prescribed medical standards and must not be '
               'colour blind for this post.')
    check('K: medical standards are read', [x.kind for x in r], ['MEDICAL'])


def test_nothing_is_presumed_to_exist() -> None:
    r = extract_requirements(
        doc(), 'The examination will be conducted in two stages at centres across the '
               'country during the month of August.')
    check('an exam with none of these produces none of them', r, [])


# ==================================================== L/M/N. posts, vacancies
def test_l_multiple_posts_keep_separate_rules() -> None:
    from .schema import Post
    posts = [Post(id='p1', name='Alpha Officer'), Post(id='p2', name='Beta Officer')]
    out = extract_eligibility(
        doc(),
        'For the post of Alpha Officer the age must be between 21 years and 27 years.\n'
        'For the post of Beta Officer the age must be between 18 years and 32 years.\n',
        exam_id='exam-x')
    check('L: posts are not merged into one rule',
          len(extract_age_rules(doc(),
              'For the post of Alpha Officer the age must be between 21 years and 27 years.\n'
              'For the post of Beta Officer the age must be between 18 years and 32 years.',
              posts=posts)), 2)
    check('L: and the extraction runs end to end', bool(out.eligibility.age_rules), True)


def test_m_vacancies_with_their_qualifier() -> None:
    v = extract_vacancies(doc(), 'The number of vacancies is 1200 (tentative) and is '
                                 'liable to change.')
    check('M: the count is read', v[0].count.value, 1200)
    check('M: with the authority’s own qualifier', 'tentative' in v[0].qualifier, True)
    check('M: and evidenced', v[0].count.is_publishable, True)


def test_m_unannounced_vacancies_are_not_zero() -> None:
    v = extract_vacancies(
        doc(), 'The number of vacancies will be notified later by the Commission.')
    check('an unannounced count is NOT_PUBLISHED', v[0].count.status, Status.NOT_PUBLISHED)
    check('and carries no number', v[0].count.value, None)


def test_n_a_revised_vacancy_uses_the_merge_engine() -> None:
    """Revision is not this module's job; it must reach the engine that owns it."""
    from .merge import MergeAction, merge_milestones
    from .schema import Fact, Milestone, MilestoneState, SourceEvidence
    from .evidence import EvidenceStatus
    ev = SourceEvidence(source_id='doc-corr', span='x',
                        span_status=EvidenceStatus.VERIFIED)
    old = Milestone(id='v-old', label='Vacancies', kind='VACANCIES', cycle='2026',
                    ends_at=Fact.verified('933', ev), status=Status.VERIFIED)
    new = Milestone(id='v-new', label='Vacancies', kind='VACANCIES', cycle='2026',
                    ends_at=Fact.verified('1016', ev), state=MilestoneState.RESCHEDULED,
                    status=Status.VERIFIED)
    report = merge_milestones([old], [new])
    check('N: a revised count supersedes rather than overwrites',
          [d.action for d in report.decisions], [MergeAction.SUPERSEDED])
    check('N: and the old figure survives', len(report.milestones), 2)


# ============================================== O/P/Q/R. absence and isolation
def test_o_missing_eligibility_is_not_invented() -> None:
    out = extract_eligibility(
        doc(), 'This notice concerns the scheme of examination and the centres.',
        exam_id='exam-x')
    check('O: no age rule is manufactured', out.eligibility.age_rules, [])
    check('O: no relaxation either',
          [r for rule in out.eligibility.age_rules for r in rule.relaxations], [])
    check('O: and no vacancy', out.vacancies, [])


def test_p_an_unreadable_source_yields_nothing_rather_than_absence() -> None:
    out = extract_eligibility(doc(), '', exam_id='exam-x')
    check('P: nothing read, nothing claimed', out.eligibility.age_rules, [])
    check('P: and no NOT_PUBLISHED is asserted about the authority',
          [r for rule in out.eligibility.age_rules for r in rule.relaxations
           if r.years.status is Status.NOT_PUBLISHED], [])


def test_q_a_wrong_exam_document_cannot_supply_rules() -> None:
    target = ExamIdentity(exam_id='exam-alpha', query='Alpha Clerical Examination 2031',
                          official_name='Alpha Clerical Examination 2031',
                          authority_name='Alpha Commission')
    foreign = ('BETA BOARD — TECHNICAL SERVICES EXAMINATION, 2031. The age limit is '
               '21 to 30 years and is relaxable by 5 years for Scheduled Castes.')
    verdict = verify(foreign, target)
    check('Q: another exam’s notice cannot supply facts', verdict.may_supply_facts, False)


def test_r_no_cross_exam_contamination() -> None:
    alpha = extract_eligibility(
        doc('doc-alpha'),
        'ALPHA COMMISSION. The age limit is 21 to 27 years, relaxable by 4 years for '
        'Scheduled Castes candidates.', exam_id='exam-alpha')
    beta = extract_eligibility(
        doc('doc-beta'),
        'BETA BOARD. The age limit is 18 to 35 years, relaxable by 9 years for '
        'Scheduled Castes candidates.', exam_id='exam-beta')

    def relaxation_of(out):
        return [r.years.value for rule in out.eligibility.age_rules
                for r in rule.relaxations]

    check('R: alpha keeps its own figure', relaxation_of(alpha), [4.0])
    check('R: beta keeps its own', relaxation_of(beta), [9.0])
    check('R: and their sources do not cross',
          {e.source_id for out in (alpha, beta) for rule in out.eligibility.age_rules
           for r in rule.relaxations for e in r.years.evidence},
          {'doc-alpha', 'doc-beta'})
    check('R: build order changes nothing',
          relaxation_of(extract_eligibility(
              doc('doc-alpha'),
              'ALPHA COMMISSION. The age limit is 21 to 27 years, relaxable by 4 years '
              'for Scheduled Castes candidates.', exam_id='exam-alpha')), [4.0])


# ================================================= S. the regression that matters
def test_s_no_universal_relaxation_without_evidence() -> None:
    """The phase's reason for existing.

    A notice that does not publish a relaxation must produce none. There is no national
    default anywhere in this path, and a category the authority never mentioned yields
    nothing at all rather than a familiar number.
    """
    silent = extract_eligibility(
        doc(), 'The age limit for the post is 21 to 30 years as on 01.08.2026.',
        exam_id='exam-x')
    published = [r for rule in silent.eligibility.age_rules for r in rule.relaxations]
    check('S: a notice silent on relaxation publishes none', published, [])
    check('S: and the lookup finds nothing for a familiar category',
          silent.eligibility.relaxations_for('OBC'), [])
    check('S: nor for any of the three the old constant knew',
          [silent.eligibility.relaxations_for(c) for c in ('OBC', 'SC', 'PwBD')],
          [[], [], []])


def test_s_the_extractor_carries_no_default_table() -> None:
    """Checked mechanically: no 3/5/10 mapping can hide in the source."""
    import io
    import re
    source = io.open('tools/exam_builder/eligibility.py', encoding='utf-8').read()
    body = source[source.index('_CATEGORY = re.compile'):]
    for pattern in (r"'OBC'\s*:\s*\d", r"'SC'\s*:\s*\d", r"'PwBD'\s*:\s*\d",
                    r'return\s+3\b', r'return\s+5\b', r'return\s+10\b'):
        check(f'no default mapping like {pattern!r}',
              re.findall(pattern, body), [])
    for forbidden in ('ssc', 'upsc', 'ibps', 'lic', 'appsc'):
        check(f'and no authority named ({forbidden.upper()})',
              re.findall(rf'\b{forbidden}\b', source, re.I), [])


def test_s_the_frontend_lookup_needs_the_exam() -> None:
    """The replacement cannot answer without being told which exam."""
    import io
    services = io.open('src/services.ts', encoding='utf-8').read()
    check('the old constant body is gone',
          "case 'OBC':\n      return 3;" in services, False)
    check('the replacement takes an exam',
          'export function getCategoryAgeRelaxation(\n  exam: Exam | null | undefined,'
          in services, True)
    check('and reads the exam’s own published rules',
          'const published = exam?.ageRelaxations;' in services, True)


def main() -> int:
    for fn in (test_a_exam_wide_age, test_a_table_cell_band, test_b_post_specific_age,
               test_c_dob_range_is_kept_as_printed, test_d_cutoff_date,
               test_e_category_relaxation_in_prose, test_e_relaxation_table,
               test_f_post_specific_relaxation,
               test_relaxation_without_a_figure_is_held_for_review,
               test_g_qualification_keeps_its_wording,
               test_g_a_tenth_pass_exam_is_representable, test_h_experience,
               test_i_nationality, test_j_physical_requirement,
               test_k_medical_requirement, test_nothing_is_presumed_to_exist,
               test_l_multiple_posts_keep_separate_rules,
               test_m_vacancies_with_their_qualifier,
               test_m_unannounced_vacancies_are_not_zero,
               test_n_a_revised_vacancy_uses_the_merge_engine,
               test_o_missing_eligibility_is_not_invented,
               test_p_an_unreadable_source_yields_nothing_rather_than_absence,
               test_q_a_wrong_exam_document_cannot_supply_rules,
               test_r_no_cross_exam_contamination,
               test_s_no_universal_relaxation_without_evidence,
               test_s_the_extractor_carries_no_default_table,
               test_s_the_frontend_lookup_needs_the_exam):
        fn()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('eligibility: every rule from the exam’s own notice, and no national default')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
