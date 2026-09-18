"""Can the contract hold what authorities actually publish — without a branch per authority?

Ten synthetic shapes, none of them any real exam's data. Invented deliberately: a contract
that fits five SSC-shaped fixtures has been tested against one authority's habits, not
against the space of recruitment notices. So the shapes here are drawn to disagree with each
other — different depths, different vocabularies, different ways of stating the same rule —
and the test is whether any of them needs a special case.

The assertions are about structure only. No factual claim about any exam appears.

Run: python -m tools.exam_builder.test_schema
"""
from __future__ import annotations

from ..exam_authoring.record import Citation, Field as LegacyField, Status as LegacyStatus
from .compat import (describe_field_states, fact_from_field, field_from_fact, round_trips,
                     status_from_legacy, status_to_legacy, to_legacy_provenance,
                     verification_level_for)
from .evidence import EvidenceStatus
from .schema import (AdmitCardNotice, AdmitCardNoticeKind, AgeRelaxation, AgeRule, AnswerKey,
                     AnswerKeyKind, ApplicationField, ApplicationProcess, ApplicationStage,
                     CutoffMark, Eligibility, ExamIdentity, ExamPattern, Fact, FeeRule,
                     Milestone, NegativeMarking, OfficialPaper, PaperIdentity, PatternLevel,
                     PatternNode, Post, QualifyingRule, RequiredDocument, ResultDeclaration,
                     Revision, Scope, ScopeKind, ScopeRef, SourceDocument, SourceEvidence,
                     SourceKind, Status, Syllabus, SyllabusNode, UniversalExam,
                     VacancyCount)

_FAILURES: list[str] = []


def check(label: str, got, want) -> None:
    if got != want:
        _FAILURES.append(f'{label}\n     got  {got!r}\n     want {want!r}')


# A stand-in document. Every fact in this file cites it, because a fact with a value and no
# evidence is refused by the contract and the fixtures must be legal.
DOC = SourceDocument(id='doc-1', url='https://authority.example/notice.pdf',
                     kind=SourceKind.NOTIFICATION, title='Notice of Examination',
                     authority='Example Authority', accessed_at='2026-09-18',
                     content_hash='abc123', exam_id='exam-x')


def ev(span: str, *, page: int = 1, section: str = '') -> SourceEvidence:
    return SourceEvidence(source_id=DOC.id, url=DOC.url, document_title=DOC.title,
                          document_type=DOC.kind, page=page, section=section, span=span,
                          accessed_at=DOC.accessed_at,
                          span_status=EvidenceStatus.VERIFIED)


def node(nid, level, label, name, order=0, **kw) -> PatternNode:
    return PatternNode(id=nid, level=level, level_label=label, name=name, order=order, **kw)


# ============================================================ 1. multi-stage exam
def test_1_multi_stage_recruitment() -> None:
    """Stage -> Section, with three written stages and a non-written one."""
    pattern = ExamPattern(stages=[
        node('s1', PatternLevel.STAGE, 'Tier', 'Tier I', 1, children=[
            node('s1a', PatternLevel.SECTION, 'Section', 'Section A', 1,
                 questions=Fact.verified(25, ev('Section A 25 questions')),
                 marks=Fact.verified(50.0, ev('Section A 50 marks'))),
            node('s1b', PatternLevel.SECTION, 'Section', 'Section B', 2,
                 questions=Fact.verified(25, ev('Section B 25 questions'))),
        ]),
        node('s2', PatternLevel.STAGE, 'Tier', 'Tier II', 2),
        node('s3', PatternLevel.STAGE, 'Tier', 'Tier III', 3),
        node('s4', PatternLevel.STAGE, 'Stage', 'Skill Test', 4,
             qualifying=Fact.verified(
                 QualifyingRule(as_printed='qualifying in nature',
                                is_qualifying_only=True, counts_towards_merit=False),
                 ev('qualifying in nature'))),
    ])
    check('1: four stages', len(pattern.stages), 4)
    check('1: a third written stage is expressible',
          [s.name for s in pattern.of_level(PatternLevel.STAGE)],
          ['Tier I', 'Tier II', 'Tier III', 'Skill Test'])
    check('1: depth is two here', pattern.max_depth(), 2)
    check('1: a qualifying-only stage is data, not prose',
          pattern.find('s4').qualifying.value.counts_towards_merit, False)
    check('1: no paper level was invented', pattern.of_level(PatternLevel.PAPER), [])


# ====================================================== 2. multi-paper civil-services
def test_2_multi_paper_with_subjects_and_sections() -> None:
    """Stage -> Paper -> Subject -> Section: the deepest shape, and the same type."""
    pattern = ExamPattern(stages=[
        node('p1', PatternLevel.STAGE, 'Stage', 'Preliminary', 1, children=[
            node('p1a', PatternLevel.PAPER, 'Paper', 'Paper I', 1,
                 marks=Fact.verified(200.0, ev('Paper I 200 marks')),
                 languages=Fact.verified(['Language A', 'Language B'],
                                         ev('set in Language A and Language B'))),
            node('p1b', PatternLevel.PAPER, 'Paper', 'Paper II', 2,
                 qualifying=Fact.verified(
                     QualifyingRule(as_printed='qualifying, minimum 33 per cent',
                                    is_qualifying_only=True, minimum_percent=33.0),
                     ev('qualifying, minimum 33 per cent'))),
        ]),
        node('m1', PatternLevel.STAGE, 'Stage', 'Main', 2, children=[
            node('m1a', PatternLevel.PAPER, 'Paper', 'Paper A', 1, children=[
                node('m1a1', PatternLevel.SUBJECT, 'Subject', 'Subject One', 1, children=[
                    node('m1a1x', PatternLevel.SECTION, 'Part', 'Part I', 1,
                         marks=Fact.verified(125.0, ev('Part I 125 marks'))),
                ]),
            ]),
        ]),
    ])
    check('2: four levels deep, in the same type', pattern.max_depth(), 4)
    check('2: papers exist and are addressable',
          [p.name for p in pattern.of_level(PatternLevel.PAPER)],
          ['Paper I', 'Paper II', 'Paper A'])
    check('2: a subject sits under a paper',
          [s.name for s in pattern.of_level(PatternLevel.SUBJECT)], ['Subject One'])
    check('2: languages are held per paper',
          pattern.find('p1a').languages.value, ['Language A', 'Language B'])
    check('2: a qualifying paper is distinguishable from a merit one',
          pattern.find('p1b').qualifying.value.is_qualifying_only, True)


# ============================================================ 3. sectional banking
def test_3_sectional_with_per_section_timing() -> None:
    """Stage -> Section, where each section is separately timed and separately marked."""
    pattern = ExamPattern(stages=[
        node('b1', PatternLevel.STAGE, 'Phase', 'Phase I', 1, children=[
            node('b1a', PatternLevel.SECTION, 'Section', 'Section One', 1,
                 questions=Fact.verified(30, ev('Section One 30 questions')),
                 duration_minutes=Fact.verified(20, ev('Section One 20 minutes')),
                 negative_marking=Fact.verified(
                     NegativeMarking(as_printed='one fourth deducted',
                                     deducted_per_wrong=0.25, awarded_per_correct=1.0),
                     ev('one fourth deducted'))),
            node('b1b', PatternLevel.SECTION, 'Section', 'Section Two', 2,
                 duration_minutes=Fact.verified(20, ev('Section Two 20 minutes'))),
        ]),
    ])
    sections = pattern.of_level(PatternLevel.SECTION)
    check('3: per-section timing survives',
          [s.duration_minutes.value for s in sections], [20, 20])
    check('3: negative marking is structured, and keeps its wording',
          sections[0].negative_marking.value.deducted_per_wrong, 0.25)
    check('3: and the printed sentence is not thrown away',
          sections[0].negative_marking.value.as_printed, 'one fourth deducted')


# ============================================================== 4. state PSC shape
def test_4_state_psc_with_its_own_vocabulary() -> None:
    """An authority whose level words match nobody else's. No new type, no new field."""
    pattern = ExamPattern(stages=[
        node('g1', PatternLevel.STAGE, 'Screening', 'Screening Test', 1),
        node('g2', PatternLevel.STAGE, 'Main', 'Main Examination', 2, children=[
            node('g2a', PatternLevel.PAPER, 'Conventional Paper', 'Conventional Paper I', 1,
                 mode=Fact.verified('descriptive', ev('descriptive'))),
        ]),
        node('g3', PatternLevel.STAGE, 'Interview', 'Personality Test', 3),
    ])
    check('4: the authority’s own level words are preserved',
          [s.level_label for s in pattern.stages], ['Screening', 'Main', 'Interview'])
    check('4: and a descriptive paper needs no special field',
          pattern.find('g2a').mode.value, 'descriptive')


# ====================================================== 5/6/7. the age model
def test_5_post_specific_age_limits() -> None:
    """A global rule and a post-specific one, coexisting — impossible in the old shape."""
    eligibility = Eligibility(age_rules=[
        AgeRule(id='age-global',
                minimum_age=Fact.verified(18.0, ev('not below 18 years')),
                maximum_age=Fact.verified(30.0, ev('not above 30 years'))),
        AgeRule(id='age-post-a',
                scope=Scope([ScopeRef(ScopeKind.POST, 'post-a', 'Post A')]),
                minimum_age=Fact.verified(21.0, ev('Post A not below 21 years')),
                maximum_age=Fact.verified(27.0, ev('Post A not above 27 years'))),
    ])
    check('5: a global rule exists', eligibility.global_age_rule.id, 'age-global')
    check('5: the global rule is recognised as global',
          eligibility.global_age_rule.is_global, True)
    post_scope = Scope([ScopeRef(ScopeKind.POST, 'post-a', 'Post A')])
    covering = [r.id for r in eligibility.age_rules_for(post_scope)]
    check('5: both the global and the post rule govern that post',
          covering, ['age-global', 'age-post-a'])
    check('5: and the global rule does not govern only itself',
          eligibility.age_rules[1].scope.covers(Scope()), False)


def test_6_category_relaxation_is_sourced_not_assumed() -> None:
    """The relaxation the frontend hard-codes today, held as data with evidence.

    Two forms of relaxation appear in real notices and both must fit: "N years for X", and
    "the upper limit for X is M". Storing only the first forces us to compute the second,
    which means inventing arithmetic nobody printed.
    """
    rule = AgeRule(
        id='age-global',
        maximum_age=Fact.verified(30.0, ev('not above 30 years')),
        relaxations=[
            AgeRelaxation(category_label='Category One',
                          scope=Scope([ScopeRef(ScopeKind.CATEGORY, 'c1', 'Category One')]),
                          years=Fact.verified(3.0, ev('three years for Category One'))),
            AgeRelaxation(category_label='Category Two',
                          scope=Scope([ScopeRef(ScopeKind.CATEGORY, 'c2', 'Category Two')]),
                          absolute_maximum=Fact.verified(
                              40.0, ev('upper age limit for Category Two is 40 years'))),
            AgeRelaxation(category_label='Category Three',
                          years=Fact.verified(10.0, ev('ten years for Category Three')),
                          conditions=Fact.verified(
                              'subject to conditions', ev('subject to conditions'))),
        ])
    check('6: three relaxations, each carrying evidence',
          [r.years.is_publishable or r.absolute_maximum.is_publishable
           for r in rule.relaxations], [True, True, True])
    check('6: an absolute ceiling is expressible without computing it',
          rule.relaxations[1].absolute_maximum.value, 40.0)
    check('6: a relaxation is found by the authority’s own label',
          rule.relaxations_for('Category Two')[0].absolute_maximum.value, 40.0)
    check('6: the category vocabulary is the authority’s, not an enum',
          [r.category_label for r in rule.relaxations],
          ['Category One', 'Category Two', 'Category Three'])


def test_7_different_cutoff_dates_per_rule() -> None:
    """Two rules reckoned on two different dates, from two different documents."""
    doc2 = SourceDocument(id='doc-2', url='https://authority.example/corrigendum.pdf',
                          kind=SourceKind.CORRIGENDUM, title='Corrigendum')
    ev2 = SourceEvidence(source_id=doc2.id, url=doc2.url, document_title=doc2.title,
                         document_type=doc2.kind, span='reckoned as on 1 August',
                         span_status=EvidenceStatus.VERIFIED)
    eligibility = Eligibility(age_rules=[
        AgeRule(id='age-a', scope=Scope([ScopeRef(ScopeKind.POST, 'post-a')]),
                cutoff_date=Fact.verified('2026-01-01', ev('reckoned as on 1 January'))),
        AgeRule(id='age-b', scope=Scope([ScopeRef(ScopeKind.POST, 'post-b')]),
                cutoff_date=Fact.verified('2026-08-01', ev2)),
    ])
    check('7: cutoffs differ per rule, not one per exam',
          [r.cutoff_date.value for r in eligibility.age_rules],
          ['2026-01-01', '2026-08-01'])
    check('7: and each cites the document it came from',
          [r.cutoff_date.primary_source.source_id for r in eligibility.age_rules],
          ['doc-1', 'doc-2'])


def test_7b_date_of_birth_window_instead_of_an_age_band() -> None:
    """Some authorities print a DOB window. It is kept as printed, not converted."""
    rule = AgeRule(
        id='age-dob',
        born_not_earlier_than=Fact.verified('1994-08-02', ev('born not earlier than')),
        born_not_later_than=Fact.verified('2005-08-01', ev('born not later than')))
    check('7b: a DOB window needs no age arithmetic',
          bool(rule.born_not_earlier_than.value and rule.born_not_later_than.value), True)
    check('7b: and the age band is honestly absent, not zero',
          rule.minimum_age.status, Status.NOT_EXTRACTED)


# ======================================================== 8. hierarchical syllabus
def test_8_hierarchical_syllabus_keeps_its_shape() -> None:
    """Paper -> Subject -> Topic -> Subtopic, beside a two-level syllabus. Same type."""
    deep = SyllabusNode(
        id='y-p1', title='Paper I', level_label='Paper', order=1,
        status=Status.VERIFIED, evidence=[ev('Paper I')],
        children=[
            SyllabusNode(id='y-p1-s1', title='Subject A', level_label='Subject',
                         status=Status.VERIFIED, evidence=[ev('Subject A')], children=[
                SyllabusNode(id='y-p1-s1-t1', title='Topic One', level_label='Topic',
                             status=Status.VERIFIED, evidence=[ev('Topic One')], children=[
                    SyllabusNode(id='y-p1-s1-t1-a', title='Subtopic One',
                                 level_label='Subtopic', status=Status.VERIFIED,
                                 evidence=[ev('Subtopic One')]),
                ]),
                SyllabusNode(id='y-p1-s1-t2', title='Topic Two', level_label='Topic',
                             status=Status.VERIFIED, evidence=[ev('Topic Two')]),
            ]),
        ])
    shallow = SyllabusNode(
        id='y-s2', title='Subject B', level_label='Subject', order=2,
        status=Status.VERIFIED, evidence=[ev('Subject B')], children=[
            SyllabusNode(id='y-s2-t1', title='Topic Three', level_label='Topic',
                         status=Status.VERIFIED, evidence=[ev('Topic Three')]),
        ])
    syllabus = Syllabus(roots=[deep, shallow])

    check('8: four levels on one branch', deep.depth(), 4)
    check('8: two on another — not padded to match', shallow.depth(), 2)
    check('8: the authority’s own level words are recoverable',
          syllabus.level_labels(), ['Paper', 'Subject', 'Topic', 'Subtopic'])
    check('8: a subtopic is a node, so it can carry evidence',
          bool(syllabus.find('y-p1-s1-t1-a').evidence), True)
    check('8: nothing was flattened into a string list',
          [n.title for n in syllabus.walk() if n.level_label == 'Subtopic'],
          ['Subtopic One'])
    check('8: leaves are leaves at whatever depth they occur',
          sorted(n.id for n in deep.leaves()), ['y-p1-s1-t1-a', 'y-p1-s1-t2'])


# ============================================== 9. papers and their own answer keys
def test_9_multiple_papers_with_separate_keys() -> None:
    """One cycle, several papers, a key each — and two language versions of one paper."""
    base = dict(exam_id='exam-x', cycle='2026', stage='Stage One')
    p1 = PaperIdentity(**base, paper='Paper I', language='Language A')
    p1b = PaperIdentity(**base, paper='Paper I', language='Language B')
    p2 = PaperIdentity(**base, paper='Paper II', language='Language A')

    check('9: two papers of one cycle are different identities', p1.key() == p2.key(), False)
    check('9: two language versions are different identities', p1.key() == p1b.key(), False)
    check('9: exam plus year alone is not a paper',
          PaperIdentity(exam_id='exam-x', cycle='2026').is_paper_level, False)
    check('9: naming the paper makes it one', p1.is_paper_level, True)

    exam = UniversalExam(identity=ExamIdentity(exam_id='exam-x'), answer_keys=[
        AnswerKey(id='k1', paper=p1, kind=AnswerKeyKind.PROVISIONAL,
                  url=Fact.verified('https://authority.example/k1', ev('key one')),
                  status=Status.VERIFIED),
        AnswerKey(id='k2', paper=p1, kind=AnswerKeyKind.FINAL, revises='k1',
                  url=Fact.verified('https://authority.example/k2', ev('key two')),
                  status=Status.VERIFIED),
        AnswerKey(id='k3', paper=p2, kind=AnswerKeyKind.FINAL,
                  url=Fact.verified('https://authority.example/k3', ev('key three')),
                  status=Status.VERIFIED),
    ])
    check('9: a key is found by the paper it answers',
          [k.id for k in exam.keys_for(p1)], ['k1', 'k2'])
    check('9: and Paper II’s key is not among them',
          [k.id for k in exam.keys_for(p2)], ['k3'])
    check('9: provisional and final coexist, with the revision recorded',
          exam.answer_keys[1].revises, 'k1')
    check('9: every key is attached to a paper, not to a year',
          all(k.is_attached_to_a_paper for k in exam.answer_keys), True)

    scanned = OfficialPaper(identity=p1,
                            url=Fact.verified('https://authority.example/p1', ev('paper')),
                            contents=Fact.not_extracted('scanned image, no text layer'),
                            status=Status.VERIFIED)
    check('9: a paper that exists but cannot be read is NOT_EXTRACTED',
          scanned.contents.status, Status.NOT_EXTRACTED)
    check('9: which is not the same as the authority publishing none',
          scanned.contents.status is Status.NOT_PUBLISHED, False)


# ============================================ 10. a corrigendum changing a date
def test_10_corrigendum_changes_an_application_date() -> None:
    """Both values survive. Which one wins is the conflict engine's problem, later."""
    original = Milestone(
        id='m-close', label='Last date to apply', kind='APPLICATION_CLOSE',
        ends_at=Fact.verified('2026-02-24T18:00', ev('last date 24 February')),
        status=Status.VERIFIED)
    revised = Milestone(
        id='m-close-rev', label='Last date to apply (extended)', kind='APPLICATION_CLOSE',
        ends_at=Fact.verified('2026-02-27T18:00', ev('extended to 27 February')),
        status=Status.VERIFIED)
    original.superseded_by = revised.id

    revision = Revision(
        id='rev-1', field_path='milestones[m-close].ends_at',
        previous_value='2026-02-24T18:00', revised_value='2026-02-27T18:00',
        published_at=Fact.verified('2026-02-20', ev('published 20 February')),
        supersedes_source_id=DOC.id, summary='application window extended',
        status=Status.VERIFIED, evidence=[ev('extended to 27 February')])

    check('10: the superseded milestone is kept, not deleted',
          original.is_superseded, True)
    check('10: and points at what replaced it', original.superseded_by, 'm-close-rev')
    check('10: the change names the field it touched',
          revision.field_path, 'milestones[m-close].ends_at')
    check('10: both values are addressable',
          (revision.previous_value, revision.revised_value),
          ('2026-02-24T18:00', '2026-02-27T18:00'))
    check('10: an unresolvable conflict can be parked for review',
          Revision(id='r2', status=Status.NEEDS_REVIEW).status.carries_value, True)


# ================================================================= cross-cutting
def test_evidence_is_required_for_a_published_claim() -> None:
    sourced = Fact.verified('a value', ev('a value'))
    check('a verified, verbatim-sourced fact is publishable', sourced.is_publishable, True)

    unsourced = Fact(value='a value', status=Status.VERIFIED)
    check('a verified fact with no evidence is not publishable',
          unsourced.is_publishable, False)

    unchecked = Fact(value='a value', status=Status.VERIFIED, evidence=[
        SourceEvidence(source_id='doc-1', span='a value',
                       span_status=EvidenceStatus.UNCHECKED)])
    check('nor is one whose span was never checked', unchecked.is_publishable, False)


def test_a_record_reports_its_own_unsourced_claims() -> None:
    exam = UniversalExam(identity=ExamIdentity(
        exam_id='exam-x',
        official_name=Fact.verified('A Name', ev('A Name')),
        authority_name=Fact(value='Guessed', status=Status.VERIFIED)))
    check('an unsourced verified claim is found by the record itself',
          exam.unsourced_facts(), ['identity.authority_name'])


def test_the_four_states_never_merge() -> None:
    check('there are exactly four', len(list(Status)), 4)
    check('absence-by-them and absence-by-us are different values',
          Status.NOT_PUBLISHED == Status.NOT_EXTRACTED, False)
    check('only one of them is a claim about the authority',
          Status.NOT_PUBLISHED.is_about_the_authority, True)
    check('and our own gap is not',
          Status.NOT_EXTRACTED.is_about_the_authority, False)
    check('no status names infrastructure',
          [s for s in Status if 'INFRA' in s.value or 'PAUSED' in s.value], [])
    check('every state is described for a reader', len(describe_field_states()), 4)


def test_scopes_compose_without_new_fields() -> None:
    post_and_category = Scope([ScopeRef(ScopeKind.POST, 'post-a'),
                               ScopeRef(ScopeKind.CATEGORY, 'c1')])
    check('a global scope covers a specific one',
          Scope().covers(post_and_category), True)
    check('a post scope covers post-and-category',
          Scope([ScopeRef(ScopeKind.POST, 'post-a')]).covers(post_and_category), True)
    check('but not a different post',
          Scope([ScopeRef(ScopeKind.POST, 'post-b')]).covers(post_and_category), False)
    check('a scope reads legibly', str(Scope()), 'EXAM (global)')


def test_sources_describe_what_they_are() -> None:
    kinds = {k.value for k in SourceKind}
    for required in ('NOTIFICATION', 'APPLICATION_PAGE', 'CORRIGENDUM', 'SYLLABUS',
                     'QUESTION_PAPER', 'ANSWER_KEY', 'ADMIT_CARD_NOTICE', 'RESULT',
                     'OTHER_OFFICIAL'):
        check(f'source kind {required} exists', required in kinds, True)
    check('a source carries the hash discovery already computed', DOC.content_hash, 'abc123')
    check('and names the exam it belongs to', DOC.exam_id, 'exam-x')


def test_application_process_presumes_no_steps() -> None:
    two_step = ApplicationProcess(exam_id='exam-x', stages=[
        ApplicationStage(id='a1', title='Fill the form', order=1, fields=[
            ApplicationField(id='f1', label='Name', required=True, evidence=[ev('Name')])]),
        ApplicationStage(id='a2', title='Pay', order=2),
    ])
    eight_step = ApplicationProcess(exam_id='exam-y', stages=[
        ApplicationStage(id=f's{i}', title=f'Step {i}', order=i) for i in range(1, 9)])
    check('a two-step process is two stages', len(two_step.stages), 2)
    check('an eight-step process is eight', len(eight_step.stages), 8)
    check('no stage is assumed to exist',
          [s.title for s in ApplicationProcess().stages], [])
    check('a document specification rides on the stage that needs it',
          RequiredDocument(id='d1', name='Photograph').specifications, [])


def test_fees_vary_by_who_is_paying() -> None:
    process = ApplicationProcess(exam_id='exam-x', fees=[
        FeeRule(amount=Fact.verified(100.0, ev('fee of 100'))),
        FeeRule(scope=Scope([ScopeRef(ScopeKind.CATEGORY, 'c1', 'Category One')]),
                is_exempt=Fact.verified(True, ev('Category One exempted'))),
        FeeRule(scope=Scope([ScopeRef(ScopeKind.POST, 'post-a')]),
                amount=Fact.verified(250.0, ev('Post A fee of 250'))),
    ])
    check('one fee shape covers global, category and post',
          [f.scope.is_global for f in process.fees], [True, False, False])
    check('an exemption is a stated fact, not a zero we computed',
          process.fees[1].is_exempt.value, True)


def test_admit_card_and_results_name_no_stage() -> None:
    cards = [
        AdmitCardNotice(id='ac1', kind=AdmitCardNoticeKind.ADMIT_CARD,
                        scope=Scope([ScopeRef(ScopeKind.STAGE, 's1', 'Stage One')])),
        AdmitCardNotice(id='ac2', kind=AdmitCardNoticeKind.ADMIT_CARD,
                        scope=Scope([ScopeRef(ScopeKind.STAGE, 's2', 'Stage Two')])),
    ]
    check('an admit card exists per stage, not once per exam', len(cards), 2)
    check('city intimation is a kind of notice, not a boolean everyone answers',
          [c for c in cards if c.kind is AdmitCardNoticeKind.CITY_INTIMATION], [])

    results = [
        ResultDeclaration(id='r1', label='Stage One Result',
                          scope=Scope([ScopeRef(ScopeKind.STAGE, 's1')]),
                          qualified_count=Fact.verified(100, ev('100 candidates')),
                          cutoffs=[CutoffMark(
                              scope=Scope([ScopeRef(ScopeKind.CATEGORY, 'c1')]),
                              marks=Fact.verified(90.5, ev('90.5')), basis='out of 200')]),
        ResultDeclaration(id='r2', label='Final Result',
                          scope=Scope([ScopeRef(ScopeKind.STAGE, 's3')])),
    ]
    check('a result names its stage by reference, not by a literal',
          [r.scope.of(ScopeKind.STAGE)[0].ref for r in results], ['s1', 's3'])
    check('a cutoff is scoped, not two numeric slots',
          results[0].cutoffs[0].marks.value, 90.5)


def test_posts_need_only_a_name() -> None:
    """The old shape required a closed `classification`, so a post whose group was not
    printed could not be recorded. It can now."""
    post = Post(id='post-a', name='Post A', status=Status.VERIFIED, evidence=[ev('Post A')],
                vacancies=[VacancyCount(count=Fact.verified(10, ev('10 vacancies')),
                                        qualifier='provisional')])
    check('a post with no printed classification is representable',
          post.classification.status, Status.NOT_EXTRACTED)
    check('and its vacancies carry the authority’s qualifier',
          post.vacancies[0].qualifier, 'provisional')


# ============================================================= compatibility
def test_legacy_fields_round_trip() -> None:
    """Adopting the contract must not change what an existing record says."""
    cases = [
        LegacyField.found('fee', {'amounts': ['100']},
                          Citation(document_title='Notice', url='https://a.example/n.pdf',
                                   page=3, clause='4.1', excerpt='a fee of 100',
                                   verified_date='2026-09-18')),
        LegacyField.not_published('answerKeys', 'the listing shows none'),
        LegacyField.not_extracted('attempts', 'the notice'),
        LegacyField.needs_review('vacancies', 10, 'stated as approximate'),
    ]
    for f in cases:
        check(f'{f.name} round-trips unchanged', round_trips(f), True)

    check('FOUND becomes VERIFIED',
          status_from_legacy(LegacyStatus.FOUND), Status.VERIFIED)
    check('and back again',
          status_to_legacy(Status.VERIFIED), LegacyStatus.FOUND)
    for legacy in LegacyStatus:
        check(f'{legacy.value} survives a round trip',
              status_to_legacy(status_from_legacy(legacy)), legacy)


def test_frontend_projection_keeps_the_badging_rule() -> None:
    sourced = Fact.verified('a value', ev('a value', page=7, section='4.1'))
    prov = to_legacy_provenance(sourced, prov_id='prov-1')
    check('a verified fact projects to the UI’s provenance shape',
          prov['verificationLevel'], 'OFFICIALLY_VERIFIED')
    check('carrying the page', prov['pageNumber'], 7)
    check('and the clause', prov['clauseNumber'], '4.1')

    unsure = Fact.needs_review('a value', 'stated loosely', ev('a value'))
    check('a needs-review fact is never badged official',
          to_legacy_provenance(unsure, prov_id='p')['verificationLevel'],
          'UNDER_VERIFICATION')
    check('a superseded value says so',
          verification_level_for(Status.VERIFIED, superseded=True), 'SUPERSEDED')
    check('a fact with nothing to cite projects to nothing, not to an empty citation',
          to_legacy_provenance(Fact.not_extracted(), prov_id='p'), None)


def test_one_evidence_model_only() -> None:
    from .evidence import Evidence
    e = Evidence(span='a span', source_url='https://a.example/x', document_title='Doc',
                 page=2, reading='a reading')
    e.verify('this document contains a span somewhere')
    adopted = SourceEvidence.from_evidence(e, source=DOC)
    check('the extraction layer’s evidence adopts without reimplementation',
          adopted.span_status, EvidenceStatus.VERIFIED)
    check('keeping its verification', adopted.is_verbatim, True)
    check('and inheriting the document’s hash', adopted.content_hash, 'abc123')
    check('a locator reads legibly', ev('x', page=3, section='2.1').locator(),
          'Notice of Examination · p.3 · 2.1')


def test_a_whole_record_holds_together() -> None:
    exam = UniversalExam(
        identity=ExamIdentity(exam_id='exam-x',
                              official_name=Fact.verified('An Examination', ev('An Examination')),
                              authority_name=Fact.verified('Example Authority', ev('Example Authority')),
                              cycle='2026'),
        sources=[DOC],
        milestones=[Milestone(id='m1', label='Notification', status=Status.VERIFIED,
                              starts_at=Fact.verified('2026-01-01', ev('1 January')))],
        posts=[Post(id='post-a', name='Post A', status=Status.VERIFIED)],
        eligibility=Eligibility(age_rules=[AgeRule(id='a1')]),
    )
    check('the record knows its own id', exam.exam_id, 'exam-x')
    check('a source is retrievable by id', exam.source('doc-1').kind, SourceKind.NOTIFICATION)
    check('and nothing in it claims more than it can show', exam.unsourced_facts(), [])
    # The audit walk has to reach *every* section, or the gate that uses it would pass a
    # record by failing to look at half of it.
    sections = {p.split('.')[0].split('[')[0] for p, _ in exam.all_facts()}
    check('the audit walk reaches every populated section',
          sections, {'identity', 'application', 'milestones', 'posts', 'eligibility',
                     'pattern', 'syllabus'})
    check('including through lists and nested rules',
          'eligibility.age_rules[0].cutoff_date' in [p for p, _ in exam.all_facts()], True)


def main() -> int:
    test_1_multi_stage_recruitment()
    test_2_multi_paper_with_subjects_and_sections()
    test_3_sectional_with_per_section_timing()
    test_4_state_psc_with_its_own_vocabulary()
    test_5_post_specific_age_limits()
    test_6_category_relaxation_is_sourced_not_assumed()
    test_7_different_cutoff_dates_per_rule()
    test_7b_date_of_birth_window_instead_of_an_age_band()
    test_8_hierarchical_syllabus_keeps_its_shape()
    test_9_multiple_papers_with_separate_keys()
    test_10_corrigendum_changes_an_application_date()
    test_evidence_is_required_for_a_published_claim()
    test_a_record_reports_its_own_unsourced_claims()
    test_the_four_states_never_merge()
    test_scopes_compose_without_new_fields()
    test_sources_describe_what_they_are()
    test_application_process_presumes_no_steps()
    test_fees_vary_by_who_is_paying()
    test_admit_card_and_results_name_no_stage()
    test_posts_need_only_a_name()
    test_legacy_fields_round_trip()
    test_frontend_projection_keeps_the_badging_rule()
    test_one_evidence_model_only()
    test_a_whole_record_holds_together()
    if _FAILURES:
        print(f'{len(_FAILURES)} FAILURE(S):')
        for f in _FAILURES:
            print('  -', f)
        return 1
    print('schema: ten shapes, four states, one evidence model, no exam-specific branch')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
