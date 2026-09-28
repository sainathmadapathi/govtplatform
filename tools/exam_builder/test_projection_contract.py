"""The canonical-to-runtime projection contract: no verified fact is lost, none is invented.

A synthetic, fictitious exam carries a representative, valid value in *every* canonical
contract field. It is materialized, then held to three checks:

  * the runtime contract (the frontend `Exam` shape)             validate_runtime_exam
  * the projection contract (no FOUND fact silently dropped)     validate_projection
  * field-by-field content and provenance                        the assertions below

Then the failure paths: a projection that loses a field must fail publication on every
route into the registry; a reading that is not what its field claims (a document checklist
where posts were expected) is held for review, not published and not dropped; and an empty
canonical record produces an honest empty runtime exam with nothing supplied from a default.

No network, no authority named, no exam from the register used.

Run: python -m unittest tools.exam_builder.test_projection_contract
"""
from __future__ import annotations

import json
import re
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from ..exam_authoring.record import Citation, ExamRecord, Field, Status
from . import materialize as M
from .completeness import evaluate_completeness
from .contract import CONTRACT
from .gate import evaluate as gate_evaluate

EID = 'exam-zeta-clerk-2031'
NOTICE = 'https://zeta.gov.in/notice-2031.pdf'


def _cit(excerpt='as printed in the notice', page=2) -> Citation:
    return Citation(document_title='Zeta Recruitment Board — Notice of Examination 2031', url=NOTICE,
                    page=page, clause='para 4', excerpt=excerpt, verified_date='2031-01-05')


def _row_prov(pid: str) -> dict:
    return _cit(f'row {pid}').to_provenance(prov_id=pid)


def full_record() -> ExamRecord:
    """Every canonical contract field FOUND, each value in the shape its reader produces."""
    rec = ExamRecord(exam_id=EID, code='ZETA_CLERK_2031', title='Zeta Clerk Examination 2031',
                     authority_name='Zeta Recruitment Board', official_domain='https://zeta.gov.in')
    rec.sources_read.append(NOTICE)
    values = {
        'officialName': 'Zeta Clerk Examination 2031',
        'authority': 'Zeta Recruitment Board',
        'applicationPortal': 'https://apply.zeta.gov.in',
        'howToApply': [{'id': 'st-1', 'title': 'Register', 'order': 1,
                        'description': 'Register once on the portal and note the registration number.',
                        'fields': [], 'documents': []},
                       {'id': 'st-2', 'title': 'Pay the fee', 'order': 2,
                        'description': 'Pay the fee online before the last date.', 'fields': [], 'documents': []}],
        'requiredDocuments': [{'id': 'doc-1', 'name': 'Community certificate', 'required': True,
                               'specifications': ['In the prescribed format'], 'evidenceSpan': 'Community certificate in the prescribed format'},
                              {'id': 'doc-2', 'name': 'Degree certificate', 'required': True,
                               'specifications': [], 'evidenceSpan': 'Degree certificate'}],
        'photoSignatureGuidelines': {'hasOfficialGuidelines': True,
                                     'photograph': ['The photograph must be a recent colour photo in JPG, 20 KB to 50 KB.'],
                                     'signature': ['The signature must be in black ink, 10 KB to 20 KB.'],
                                     'evidenceSpans': ['The photograph must be a recent colour photo in JPG, 20 KB to 50 KB.']},
        'fee': {'amount': 500.0, 'amounts': [500.0], 'exemptions': '', 'acceptedModes': ['UPI', 'Net banking'],
                'rules': [{'scope': 'EXAM (global)', 'amount': 500.0, 'isExempt': None},
                          {'scope': 'CATEGORY:sc', 'amount': None, 'isExempt': True}]},
        'feeExemptions': [{'category': 'CATEGORY:sc', 'isExempt': True, 'evidenceSpan': 'SC candidates are exempted from the fee.'}],
        'posts': [{'postName': "Clerk, Group 'C'", 'department': 'Zeta Revenue Department', 'payLevel': 'Level 2',
                   'classification': ''},
                  {'postName': 'Assistant', 'department': 'Zeta Revenue Department', 'payLevel': '', 'classification': ''}],
        'vacancies': 120,
        'ageLimits': {'minAge': 18, 'maxAge': 30, 'asOn': '2031-08-01',
                      'relaxations': [{'category': 'SC/ST', 'years': 5.0, 'status': 'VERIFIED',
                                       'evidenceSpan': 'The upper age limit is relaxable by 5 years for SC/ST.'},
                                      # named without a figure: not a relaxation anyone can apply
                                      {'category': 'Departmental candidates', 'status': 'VERIFIED'}]},
        'qualification': {'text': "A bachelor's degree from a recognised university.", 'levels': ['bachelor']},
        'attempts': {'text': 'There is no limit on the number of attempts.'},
        'dates': [{'id': 'dt-close', 'type': 'APPLICATION_CLOSE', 'label': 'Last date to apply',
                   'dateTimeStr': '2031-02-11 18:00', 'status': 'AVAILABLE', 'provenance': _row_prov('prov-dt-close')},
                  {'id': 'dt-exam', 'type': 'EXAM_TIER1', 'label': 'Preliminary examination',
                   'dateTimeStr': '2031-05-20', 'status': 'AVAILABLE', 'isTentative': True},
                  {'id': 'dt-upload', 'type': 'OTHER', 'label': 'Date of upload of the notice',
                   'dateTimeStr': '2031-01-05', 'status': 'AVAILABLE'}],
        'corrigenda': [{'id': 'corr-1', 'title': 'Corrigendum 1', 'affectedField': 'lastDate',
                        'oldValue': '2031-02-10', 'newValue': '2031-02-11', 'sourceUrl': 'https://zeta.gov.in/corr-1.pdf',
                        'evidenceSpan': 'The last date is extended to 11.02.2031.', 'status': 'ACTIVE',
                        'publishedDate': '2031-02-01'}],
        'examPattern': [{'id': 'pt-prelim', 'level': 'STAGE', 'levelLabel': 'Stage', 'name': 'Preliminary Examination',
                         'marks': 100, 'questions': 100, 'durationMinutes': 60,
                         'negativeMarking': 'One-quarter of the marks for each wrong answer', 'mode': 'CBT',
                         'languages': ['English', 'Zetan'], 'questionType': 'OBJECTIVE',
                         'qualifying': {'asPrinted': 'Screening only; not counted for merit', 'qualifyingOnly': True},
                         'status': 'VERIFIED',
                         'children': [{'id': 'pt-gs', 'level': 'PAPER', 'levelLabel': 'Paper', 'name': 'General Studies',
                                       'marks': 100, 'questions': 100, 'status': 'VERIFIED'}]},
                        {'id': 'pt-main', 'level': 'STAGE', 'levelLabel': 'Stage', 'name': 'Main Examination',
                         'status': 'VERIFIED'}],
        'syllabus': [{'id': 'sy-gs', 'title': 'General Studies', 'levelLabel': 'Paper', 'status': 'VERIFIED',
                      'provenance': _row_prov('prov-sy-gs'),
                      'children': [{'id': 'sy-h', 'title': 'History', 'children': [{'id': 'sy-h1', 'title': 'Ancient India'},
                                                                                  {'id': 'sy-h2', 'title': 'Modern India'}]},
                                   {'id': 'sy-p', 'title': 'Polity'}]}],
        'officialPapers': [{'id': 'op-2030-gs', 'title': 'Preliminary 2030 — General Studies', 'url': 'https://zeta.gov.in/qp/2030-gs.pdf',
                            'identity': {'examId': EID, 'cycle': '2030', 'stage': 'Preliminary', 'paper': 'GS',
                                         'describe': 'Preliminary 2030 — General Studies'},
                            'status': 'VERIFIED', 'contentsStatus': 'NOT_EXTRACTED',
                            'contentsNote': 'a scanned image; its questions are not read'}],
        'answerKeys': [{'id': 'ak-prov', 'kind': 'PROVISIONAL', 'url': 'https://zeta.gov.in/key/prov.pdf',
                        'identity': {'examId': EID, 'cycle': '2030', 'describe': 'Preliminary 2030 — General Studies'},
                        'windowOpens': '2030-06-01', 'windowCloses': '2030-06-05', 'status': 'VERIFIED'},
                       {'id': 'ak-final', 'kind': 'FINAL', 'url': 'https://zeta.gov.in/key/final.pdf', 'revises': 'ak-prov',
                        'identity': {'examId': EID, 'cycle': '2030', 'describe': 'Preliminary 2030 — General Studies'},
                        'status': 'VERIFIED'}],
        'admitCard': [{'id': 'ev-city', 'examId': EID, 'kind': 'CITY_INTIMATION', 'officialLabel': 'City Intimation Slip',
                       'status': 'VERIFIED', 'stageLabel': 'Preliminary', 'releasedAt': '2031-05-10', 'releasePrecision': 'DAY'},
                      {'id': 'ev-admit', 'examId': EID, 'kind': 'ADMIT_CARD', 'officialLabel': 'e-Admit Card',
                       'status': 'VERIFIED', 'stageLabel': 'Preliminary', 'releaseRule': '7 days before the examination'}],
        'results': [{'id': 'res-prelim', 'examId': EID, 'kind': 'WRITTEN_RESULT', 'label': 'Preliminary result',
                     'isDeclaration': True, 'status': 'VERIFIED', 'lifecycle': 'ORIGINAL', 'stageLabel': 'Preliminary',
                     'declaredAt': '2031-07-01', 'declaredPrecision': 'DAY'}],
        'nextSteps': [{'isDerived': True, 'source': 'DERIVED_FROM_LIFECYCLE', 'fromStage': 'Preliminary',
                       'nextStage': 'Main Examination', 'action': 'Prepare for the Main Examination',
                       'guidance': 'Candidates declared qualified in the Preliminary proceed to the Main Examination.'}],
        'cutoffs': [{'year': 2030, 'stage': 'Preliminary', 'category': 'General', 'value': 72.5, 'cutoffType': 'qualifying',
                     'post': 'Clerk'}],
        'examDayChecklist': [{'id': 'ed-1', 'category': 'DOCUMENTS', 'title': 'Carry the admit card',
                              'description': 'Candidates must carry the printed admit card.', 'isMandatory': True}],
        'faqs': [{'question': 'Can I apply offline?', 'answer': 'No. Applications are accepted online only.',
                  'officialClause': 'FAQ 3'}],
    }
    names = {c.name for c in CONTRACT if c.sources or c.name in ('officialName', 'authority')}
    missing = names - set(values)
    assert not missing, f'the synthetic record must cover every canonical field: {sorted(missing)}'
    for name, value in values.items():
        rec.set(Field.found(name, value, _cit(f'{name} as printed')))
    return rec


def _completeness(rec: ExamRecord):
    return evaluate_completeness(rec, SimpleNamespace(infrastructure_failed=False))


class TestUniversalProjection(unittest.TestCase):

    def setUp(self):
        self.rec = full_record()
        self.exam = M.materialize_exam(self.rec, cycle='2031', completeness=_completeness(self.rec))

    def test_runtime_contract_and_no_loss(self):
        self.assertEqual(M.validate_runtime_exam(self.exam), [])
        self.assertEqual(M.validate_projection(self.rec, self.exam), [])
        self.assertEqual(self.exam['materialization']['heldForReview'], {})

    def test_every_mapped_field_reaches_runtime(self):
        for name, paths in M.PROJECTION_MAP.items():
            for p in paths:
                self.assertTrue(M._path_has_content(self.exam, p), f'{name} -> {p} is empty')

    def test_identity_application_and_fee(self):
        e, g = self.exam, self.exam['applicationGuide']
        self.assertEqual((e['id'], e['title'], e['authorityName'], e['cycle']),
                         (EID, 'Zeta Clerk Examination 2031', 'Zeta Recruitment Board', '2031'))
        self.assertEqual(g['officialPortal'], 'https://apply.zeta.gov.in')
        self.assertEqual(len(g['otrSteps'][0]['instructions']), 2)
        self.assertTrue(all("{'id'" not in line for line in g['otrSteps'][0]['instructions']), 'no raw dict repr')
        self.assertEqual([d['name'] for d in g['requiredDocuments']], ['Community certificate', 'Degree certificate'])
        # Document names stay document requirements; no validity rule is inferred from a name.
        self.assertEqual(g['certificateRules'], [])
        self.assertIn('20 KB to 50 KB', g['photoRules']['rules'][0])
        self.assertIn('black ink', g['signatureRules']['rules'][0])
        self.assertEqual((g['photoRules']['dimensions'], g['photoRules']['fileSize']), ('', ''),
                         'structured slots are never filled with a plausible value')
        self.assertEqual(g['fee']['amounts'], ['500.0'])
        self.assertEqual(g['fee']['acceptedModes'], ['UPI', 'Net banking'])
        self.assertEqual(g['fee']['exemptions'][0]['category'], 'CATEGORY:sc')

    def test_posts_age_and_relaxations(self):
        posts = self.exam['posts']
        self.assertEqual(len(posts), 2)
        assistant = next(p for p in posts if p['postName'] == 'Assistant')
        self.assertEqual(assistant['classification'], '', 'a Group the notice did not print is never inferred')
        self.assertEqual((assistant['minAge'], assistant['maxAge']), (18, 30), 'one exam-wide band applies')
        self.assertEqual(self.exam['crucialEligibilityDate'], '2031-08-01')
        self.assertEqual(self.exam['vacanciesTotal'], '120')
        relax = self.exam['ageRelaxations']
        self.assertEqual([(r['category'], r.get('years')) for r in relax], [('SC/ST', 5.0)],
                         'a relaxation named without a figure is not published')

    def test_pattern_tree_and_stage_projection(self):
        tree, stages = self.exam['patternTree'], self.exam['stages']
        self.assertEqual([n['name'] for n in tree], ['Preliminary Examination', 'Main Examination'])
        pre = tree[0]
        for key, want in (('marks', 100), ('questions', 100), ('durationMinutes', 60), ('mode', 'CBT'),
                          ('questionType', 'OBJECTIVE'), ('languages', ['English', 'Zetan'])):
            self.assertEqual(pre[key], want, key)
        self.assertTrue(pre['qualifying']['qualifyingOnly'])
        self.assertEqual(pre['children'][0]['name'], 'General Studies')
        self.assertEqual([s['stageName'] for s in stages], ['Preliminary Examination', 'Main Examination'],
                         'one legacy stage per STAGE root, none guessed')
        self.assertEqual(stages[0]['unstatedFields'], [])
        self.assertEqual(sorted(stages[1]['unstatedFields']), ['durationMinutes', 'totalMarks', 'totalQuestions'])
        self.assertTrue(all(s['derivedFrom'] == 'patternTree' for s in stages))

    def test_syllabus_tree_and_flat_projection(self):
        self.assertEqual(self.exam['syllabusTree'][0]['title'], 'General Studies')
        flat = {t['topicName']: t for t in self.exam['syllabus']}
        self.assertEqual(flat['History']['subtopics'], ['Ancient India', 'Modern India'])
        self.assertIn('Polity', flat)
        self.assertTrue(all(t['weightagePercentage'] == 0 and not t['isHighYield'] for t in flat.values()),
                        'no weightage is invented')

    def test_lifecycle_fields_keep_identity(self):
        e = self.exam
        self.assertEqual([x['kind'] for x in e['admitCardEvents']], ['CITY_INTIMATION', 'ADMIT_CARD'],
                         'events are never collapsed into one card')
        self.assertNotIn('admitCardDetails', e, 'no single-card status is derived from a list of events')
        self.assertEqual(e['officialPapers'][0]['identity']['cycle'], '2030')
        self.assertEqual(e['officialPapers'][0]['contentsStatus'], 'NOT_EXTRACTED')
        self.assertEqual([(k['kind'], k.get('revises')) for k in e['answerKeys']],
                         [('PROVISIONAL', None), ('FINAL', 'ak-prov')])
        self.assertEqual(e['answerKeys'][0]['windowCloses'], '2030-06-05')
        self.assertEqual(e['resultDeclarations'][0]['declaredAt'], '2031-07-01')

    def test_next_steps_are_labelled_guidance(self):
        steps = self.exam['resultNextSteps']
        self.assertEqual(len(steps), 1)
        self.assertTrue(steps[0]['isGuidance'])
        self.assertIn('not an official statement', steps[0]['basis'])
        self.assertEqual(steps[0]['provenance']['taxonomyType'], 'RECOMMENDATION')
        self.assertNotEqual(steps[0]['provenance']['verificationLevel'], 'OFFICIALLY_VERIFIED')

    def test_cutoffs_keep_their_own_stage(self):
        c = self.exam['cutoffsHistory'][0]
        self.assertEqual((c['year'], c['stage'], c['category'], c['value'], c['cutoffType'], c['post']),
                         (2030, 'Preliminary', 'General', 72.5, 'qualifying', 'Clerk'))
        self.assertNotIn('tier1Cutoff', c, 'never relabelled as a Tier-1 figure')

    def test_dates_including_other_and_corrigenda(self):
        types = [d['type'] for d in self.exam['dates']]
        self.assertEqual(types, ['APPLICATION_CLOSE', 'EXAM_TIER1', 'OTHER'])
        self.assertEqual(self.exam['dates'][0]['provenance']['id'], 'prov-dt-close', 'row provenance kept')
        self.assertEqual(self.exam['corrigendums'][0]['pdfUrl'], 'https://zeta.gov.in/corr-1.pdf')

    def test_provenance_on_every_official_item(self):
        for coll in M._PROVENANCED:
            for item in self.exam.get(coll) or []:
                prov = item.get('provenance')
                self.assertTrue(isinstance(prov, dict) and prov.get('officialUrl'), f'{coll} item without provenance')
        g = self.exam['applicationGuide']
        self.assertTrue(g['photoRules']['provenance']['officialUrl'])
        self.assertTrue(all(d['provenance']['officialUrl'] for d in g['requiredDocuments']))
        self.assertTrue(g['fee']['provenance']['officialUrl'])

    def test_registration_passes_on_the_full_record(self):
        gate = gate_evaluate(self.rec)
        self.assertTrue(gate.may_publish, [str(b) for b in gate.blockers])
        reg = M.ExamRegistry(':memory:')
        rr = reg.register(self.rec, gate=gate, exam=self.exam, cycle='2031')
        self.assertEqual(rr.version, 1)


class TestLossFailsPublication(unittest.TestCase):

    def test_a_dropped_field_is_a_loss_on_every_route(self):
        rec = full_record()
        with patch.object(M, '_admit_card_events', return_value=[]):
            exam = M.materialize_exam(rec, cycle='2031')
        losses = M.validate_projection(rec, exam)
        self.assertTrue(any(l.startswith('admitCard:') for l in losses), losses)
        gate = gate_evaluate(rec)
        with self.assertRaises(M.MaterializationLoss):
            M.ExamRegistry(':memory:').register(rec, gate=gate, exam=exam, cycle='2031')
        with patch.object(M, '_admit_card_events', return_value=[]):
            out = M._materialize_and_publish(
                M.EngineBuildResult(query=EID, year='2031', state=M.EngineState.BLOCKED_BY_GATE), rec,
                gate=gate, completeness=None, cycle='2031', registry=M.ExamRegistry(':memory:'), data_ts=M.P.DATA_TS)
        self.assertIs(out.state, M.EngineState.PROJECTION_LOSS)
        self.assertEqual(out.registry, {'status': 'NOT_REGISTERED'})
        self.assertEqual(out.gate.get('runtimeDecision'), 'BLOCK')

    def test_a_partially_dropped_list_is_a_loss(self):
        rec = full_record()
        with patch.object(M, '_answer_keys', lambda r: M._event_list(r, 'answerKeys', 'key')[:1]):
            exam = M.materialize_exam(rec, cycle='2031')
        self.assertTrue(any('answerKeys: 2 canonical item(s) but only 1' in l for l in M.validate_projection(rec, exam)))

    def test_a_stage_tree_without_stage_projection_is_a_loss(self):
        rec = full_record()
        with patch.object(M, 'stages_from_pattern', return_value=[]):
            exam = M.materialize_exam(rec, cycle='2031')
        self.assertIn('examPattern: the pattern tree names stages, but the stages projection is empty',
                      M.validate_projection(rec, exam))

    def test_an_item_without_provenance_is_a_loss(self):
        rec = full_record()
        exam = M.materialize_exam(rec, cycle='2031')
        exam['admitCardEvents'][0]['provenance'] = {}
        self.assertTrue(any('carries no provenance' in l for l in M.validate_projection(rec, exam)))

    def test_an_unrepresentable_cutoff_fails_rather_than_vanishing(self):
        rec = full_record()
        rec.set(Field.found('cutoffs', [{'year': 2030, 'category': 'General', 'value': 'about seventy'}], _cit()))
        exam = M.materialize_exam(rec, cycle='2031')
        self.assertTrue(any(l.startswith('cutoffs:') for l in M.validate_projection(rec, exam)))


class TestHeldForReviewIsNotALoss(unittest.TestCase):

    def test_a_document_checklist_is_held_not_published(self):
        rec = full_record()
        rec.set(Field.found('posts', ['PDF Application form', 'Hall Ticket', 'Community Certificate',
                                      'Declaration by the Unemployed'], _cit()))
        exam = M.materialize_exam(rec, cycle='2031', completeness=_completeness(rec))
        self.assertEqual(exam['posts'], [])
        held = exam['materialization']['heldForReview']['posts']
        self.assertEqual(len(held['items']), 4)
        self.assertFalse(held['partial'])
        self.assertEqual(M.validate_projection(rec, exam), [], 'a reasoned hold is not a silent loss')
        elig = next(v for v in exam['sectionStates'].values() if v['sectionNum'] == 3)
        self.assertEqual(elig['state'], 'NEEDS_REVIEW')

    def test_documents_mixed_into_posts_are_removed_and_posts_kept(self):
        rec = full_record()
        rec.set(Field.found('posts', ['Revenue Inspector', 'Hall Ticket'], _cit()))
        exam = M.materialize_exam(rec, cycle='2031')
        self.assertEqual([p['postName'] for p in exam['posts']], ['Revenue Inspector'])
        self.assertTrue(exam['materialization']['heldForReview']['posts']['partial'])
        self.assertEqual(M.validate_projection(rec, exam), [])

    def test_the_build_choke_point_demotes_a_checklist(self):
        from .build import _vet_posts
        rec = full_record()
        got = _vet_posts(Field.found('posts', ['Hall Ticket', 'Non-Creamy Layer Certificate'], _cit()), rec)
        self.assertIs(got.status, Status.NEEDS_REVIEW)
        self.assertEqual(got.value, ['Hall Ticket', 'Non-Creamy Layer Certificate'], 'evidence retained')
        mixed = _vet_posts(Field.found('posts', ['Revenue Inspector', 'Hall Ticket'], _cit()), rec)
        self.assertIs(mixed.status, Status.FOUND)
        self.assertEqual(mixed.value, ['Revenue Inspector'])
        clean = Field.found('posts', ['Photographer', 'Signal Inspector'], _cit())
        self.assertIs(_vet_posts(clean, rec), clean, 'a post whose name merely contains a document word stays')

    def test_unreliable_pattern_figures_are_ledgered(self):
        rec = full_record()
        tree = json.loads(json.dumps(rec.value('examPattern')))
        tree[0]['children'].append({'id': 'x', 'level': 'SUBJECT', 'name': 'History, 1757 to 1947', 'marks': 1757,
                                    'status': 'NEEDS_REVIEW'})
        tree[0]['children'].append({'id': 'y', 'level': 'SUBJECT', 'name': '½', 'status': 'VERIFIED'})
        rec.set(Field.found('examPattern', tree, _cit()))
        exam = M.materialize_exam(rec, cycle='2031')
        kids = {k['name']: k for k in exam['patternTree'][0]['children']}
        self.assertNotIn('marks', kids['History, 1757 to 1947'])
        self.assertNotIn('½', kids)
        withheld = exam['materialization']['heldForReview']['examPattern']['items']
        self.assertTrue(any(w['node'] == 'History, 1757 to 1947' and w['values'] == {'marks': 1757} for w in withheld))
        self.assertTrue(any(w['node'] == '½' for w in withheld))
        self.assertEqual(M.validate_projection(rec, exam), [])


class TestEveryPatternReaderShape(unittest.TestCase):
    """Three readers produce examPattern in three shapes; each reaches runtime."""

    def _exam_with(self, value):
        rec = full_record()
        rec.set(Field.found('examPattern', value, _cit()))
        exam = M.materialize_exam(rec, cycle='2031')
        self.assertEqual(M.validate_projection(rec, exam), [])
        return exam

    def test_semantic_paper_rows(self):
        exam = self._exam_with({'papers': [{'label': 'Paper-I', 'name': 'Civil Engineering (', 'marks': 150,
                                            'duration': '150 minutes'}],
                                'negativeMarking': 'negative marking of 1/3 mark'})
        node = exam['patternTree'][0]
        self.assertEqual((node['level'], node['code'], node['name']), ('PAPER', 'Paper-I', 'Paper-I — Civil Engineering'))
        self.assertEqual((node['marks'], node['durationMinutes']), (150, 150))
        self.assertEqual(node['negativeMarking'], 'negative marking of 1/3 mark')
        self.assertEqual(node['derived'], ['negativeMarking'], 'a rule stated once is marked as such on each paper')
        self.assertEqual(exam['stages'], [], 'a paper is not a stage; no stage is guessed')

    def test_legacy_prose_rows(self):
        exam = self._exam_with([{'paper': 'II', 'name': 'Essay', 'marks': 250, 'duration': '3 hours', 'page': 4}])
        node = exam['patternTree'][0]
        self.assertEqual((node['name'], node['marks'], node['durationMinutes']), ('II — Essay', 250, 180))

    def test_a_rule_without_papers_is_held_not_dropped(self):
        rec = full_record()
        rec.set(Field.found('examPattern', {'papers': [], 'negativeMarking': 'one-quarter mark per wrong answer'}, _cit()))
        exam = M.materialize_exam(rec, cycle='2031')
        self.assertNotIn('patternTree', exam)
        self.assertIn('no paper rows', exam['materialization']['heldForReview']['examPattern']['reason'])
        self.assertEqual(M.validate_projection(rec, exam), [])


class TestNoFabrication(unittest.TestCase):

    def test_an_empty_record_yields_an_honest_empty_exam(self):
        rec = ExamRecord(exam_id='exam-omega-board-2032', code='OMEGA_2032', title='Omega Board Examination 2032',
                         authority_name='Omega Board', official_domain='https://omega.gov.in')
        for name in ('officialName', 'authority'):
            rec.set(Field.found(name, rec.title if name == 'officialName' else rec.authority_name, _cit()))
        rec.set(Field.found('applicationPortal', 'https://omega.gov.in/apply', _cit()))
        rec.set(Field.found('dates', [{'id': 'd', 'type': 'APPLICATION_CLOSE', 'label': 'Last date',
                                       'dateTimeStr': '2032-03-01', 'status': 'AVAILABLE'}], _cit()))
        for name in ('posts', 'ageLimits', 'examPattern', 'syllabus', 'admitCard', 'officialPapers', 'answerKeys',
                     'results', 'nextSteps', 'cutoffs', 'faqs', 'examDayChecklist', 'corrigenda', 'fee',
                     'feeExemptions', 'requiredDocuments', 'photoSignatureGuidelines', 'howToApply'):
            rec.set(Field.not_published(name, 'the authority publishes none'))
        exam = M.materialize_exam(rec, cycle='2032', completeness=_completeness(rec))
        self.assertEqual(M.validate_runtime_exam(exam), [])
        self.assertEqual(M.validate_projection(rec, exam), [])
        self.assertEqual(exam['crucialEligibilityDate'], '', 'no default date is supplied')
        for key in ('posts', 'stages', 'syllabus', 'cutoffsHistory', 'roadmapTracks', 'practiceQuestions',
                    'faqs', 'corrigendums'):
            self.assertEqual(exam[key], [], key)
        for key in ('admitCardEvents', 'officialPapers', 'answerKeys', 'resultDeclarations', 'resultNextSteps',
                    'ageRelaxations', 'patternTree', 'syllabusTree', 'examDayChecklist', 'admitCardDetails'):
            self.assertNotIn(key, exam, key)
        g = exam['applicationGuide']
        self.assertEqual((g['photoRules']['rules'], g['signatureRules']['rules'], g['certificateRules'],
                          g['rejectionPitfalls']), ([], [], [], []))
        self.assertNotIn('fee', g)
        roadmap = next(v for v in exam['sectionStates'].values() if v['sectionNum'] == 7)
        self.assertNotEqual(roadmap['state'], 'SUPPORTED_AND_PROJECTED',
                            'a derived section with nothing generated is never reported as projected')

    def test_post_scoped_ages_give_no_exam_wide_band(self):
        rec = full_record()
        rec.set(Field.found('ageLimits', {'minAge': 18, 'maxAge': 46, 'asOn': '', 'minima': [18, 21],
                                          'maxima': [35, 46]}, _cit()))
        exam = M.materialize_exam(rec, cycle='2031')
        self.assertTrue(all((p['minAge'], p['maxAge']) == (0, 0) for p in exam['posts']),
                        'the widest band is never given to every post')
        card = next(c for c in exam['eligibilityHighlights'] if c['title'] == 'Age limits')
        self.assertIn('18/21 to 35/46', card['body'])

    def test_no_exam_or_authority_is_named_in_the_materializer(self):
        import inspect
        src = inspect.getsource(M)
        hits = re.findall(r'\b(?:SSC|UPSC|IBPS|APPSC|TGPSC|TSPSC|LIC|CGL|NAEB)\b', src)
        self.assertEqual(hits, [], f'exam or authority names in generic materialization code: {hits}')


class TestRematerializeStoredRecord(unittest.TestCase):

    def test_snapshot_round_trip_is_exact(self):
        rec = full_record()
        back = M.record_from_snapshot(M._record_snapshot(rec))
        self.assertEqual(M._record_snapshot(back), M._record_snapshot(rec))

    def test_rematerialize_publishes_a_new_version_offline(self):
        rec = full_record()
        reg = M.ExamRegistry(':memory:')
        gate = gate_evaluate(rec)
        reg.register(rec, gate=gate, exam=M.materialize_exam(rec, cycle='2031'), cycle='2031')
        out = M.rematerialize(reg, EID, '2031')
        self.assertIs(out.state, M.EngineState.REGISTERED, out.reason)
        self.assertEqual(out.registry['version'], 2)
        self.assertEqual(out.materialization['projectionLosses'], [])


if __name__ == '__main__':
    unittest.main()
