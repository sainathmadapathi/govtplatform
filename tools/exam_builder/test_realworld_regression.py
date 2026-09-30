"""Regression: a real, previously unseen recruitment re-materialized from its stored record.

The fixture is the canonical ExamRecord the runtime registry held for a state commission's
Group-I recruitment (Notification 02/2024), captured after the real-world build test. It is
re-projected through the current materializer with no network and no re-acquisition. The code
under test has no branch for this authority or this exam; only this test names it.

The rule the test enforces is the product's: a field that exists canonically must exist at
runtime; a field that does not exist canonically must not be fabricated.

Run: python -m unittest tools.exam_builder.test_realworld_regression
"""
from __future__ import annotations

import json
import os
import sqlite3
import unittest

from ..exam_authoring.record import Status
from . import materialize as M

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'realworld_state_psc_group_i_2024.json')


def _load():
    with open(FIXTURE, encoding='utf-8') as fh:
        return json.load(fh)


def _registry_with_fixture(fx) -> M.ExamRegistry:
    """An in-memory registry holding the stored row exactly as the real one did."""
    reg = M.ExamRegistry(':memory:')
    c = reg._conn()
    c.execute('''INSERT INTO exam_registry (exam_id, cycle, authority_name, authority_domain, official_name, version,
                 gate_decision, published, exam_json, record_json, completeness_json, created_at, updated_at, retired)
                 VALUES (?, ?, ?, ?, ?, ?, 'PASS', 1, '{}', ?, ?, '2026-09-28T00:00:00Z', '2026-09-28T00:00:00Z', 0)''',
              (fx['examId'], fx['cycle'], fx['record']['authorityName'], fx['record']['officialDomain'],
               fx['record']['title'], fx['registryVersionAtCapture'], json.dumps(fx['record']),
               json.dumps(fx['completeness'])))
    c.commit()
    return reg


class TestRealWorldRematerialization(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fx = _load()
        cls.rec = M.record_from_snapshot(cls.fx['record'])
        cls.out = M.rematerialize(_registry_with_fixture(cls.fx), cls.fx['examId'], cls.fx['cycle'],
                                  target=M.ExamRegistry(':memory:'))
        cls.exam = cls.out.exam or {}

    def test_publishes_with_no_projection_loss(self):
        self.assertIs(self.out.state, M.EngineState.REGISTERED, self.out.reason)
        self.assertEqual(self.out.materialization['projectionLosses'], [])
        self.assertEqual(M.validate_runtime_exam(self.exam), [])
        self.assertEqual(self.out.gate['runtimeDecision'], 'PASS')

    def test_every_canonical_found_field_is_at_runtime_or_held_with_a_reason(self):
        held = self.exam['materialization']['heldForReview']
        for name, paths in M.PROJECTION_MAP.items():
            f = self.rec.get(name)
            if not (f and f.status is Status.FOUND):
                continue
            if name in held and not held[name].get('partial'):
                self.assertTrue(held[name]['reason'])
                continue
            for p in paths:
                self.assertTrue(M._path_has_content(self.exam, p), f'{name} FOUND canonically but {p} is empty')

    def test_identity_and_application(self):
        e, g = self.exam, self.exam['applicationGuide']
        self.assertEqual(e['title'], 'TGPSC Group-I Services')
        self.assertEqual(e['authorityName'], 'Telangana Public Service Commission')
        self.assertEqual(e['cycle'], '2024')
        # Changed expectation: the notice prints https://www.tspsc.gov.in, the Commission's
        # address before it was renamed, and that host no longer resolves (DNS failure, checked
        # 2026-09-28). Linking it sent candidates to a dead address; CLAUDE.md's rule is that a
        # link failing from the candidate's network is replaced, never kept. The runtime now
        # links the authority's own site, and the printed address is kept -- in the canonical
        # record and quoted on the official-links card -- rather than lost.
        self.assertEqual(g['officialPortal'], 'https://websitenew.tgpsc.gov.in')
        self.assertEqual(self.rec.value('applicationPortal'), 'https://www.tspsc.gov.in')
        self.assertTrue(any('https://www.tspsc.gov.in' in l.get('note', '') for l in e['officialLinks']))
        self.assertEqual(len(g['otrSteps'][0]['instructions']), 8)
        self.assertGreater(len(g['requiredDocuments']), 0)
        self.assertEqual(len(g['photoRules']['rules']), 2, 'the notice’s own photo sentences, not a blank placeholder')
        self.assertEqual(len(g['signatureRules']['rules']), 2)
        self.assertEqual(g['fee']['amounts'], ['200'])

    def test_dates_eligibility_pattern_syllabus(self):
        e = self.exam
        self.assertEqual(len(e['dates']), 4)
        titles = [c['title'] for c in e['eligibilityHighlights']]
        self.assertIn('Educational qualification', titles)
        self.assertIn('Age limits', titles)
        self.assertEqual(e['crucialEligibilityDate'], '', 'the record states none; none is invented')
        self.assertEqual(len(e['patternTree']), 3)
        self.assertEqual(len(e['stages']), 3, 'one compatibility stage per STAGE root of the tree')
        self.assertEqual(len(e['syllabus']), 125)

    def test_admit_card_and_exam_day(self):
        events = self.exam['admitCardEvents']
        self.assertEqual(len(events), 1)
        self.assertEqual((events[0]['officialLabel'], events[0]['releaseRule']), ('Hall Tickets', '7 days prior to the'))
        self.assertNotIn('releasedAt', events[0], 'a release rule is never resolved into a date')
        self.assertEqual(len(self.exam['examDayChecklist']), 1)

    def test_resources_and_links(self):
        kinds = {r['type'] for r in self.exam['resources']}
        self.assertEqual(kinds, {'OFFICIAL_PDF', 'OFFICIAL_PORTAL'})
        self.assertEqual(len(self.exam['officialLinks']), 2)

    def test_absent_lifecycle_is_not_fabricated(self):
        # The authority's listing shows none of these for this cycle: they stay absent.
        for name, key in (('officialPapers', 'officialPapers'), ('answerKeys', 'answerKeys'),
                          ('results', 'resultDeclarations'), ('nextSteps', 'resultNextSteps'),
                          ('cutoffs', 'cutoffsHistory'), ('corrigenda', 'corrigendums')):
            self.assertIs(self.rec.get(name).status, Status.NOT_PUBLISHED, name)
            self.assertFalse(self.exam.get(key), f'{key} must stay empty: nothing canonical to project')
        self.assertFalse(self.exam.get('ageRelaxations'), 'the record carries no printed relaxation')

    def test_the_document_checklist_is_not_published_as_posts(self):
        self.assertEqual(self.exam['posts'], [])
        held = self.exam['materialization']['heldForReview']['posts']
        self.assertEqual(len(held['items']), 12)
        self.assertEqual(held['items'][1]['candidate'], 'Hall Ticket')
        elig = next(v for v in self.exam['sectionStates'].values() if v['sectionNum'] == 3)
        self.assertEqual(elig['state'], 'NEEDS_REVIEW')

    def test_derived_sections_say_not_generated(self):
        # Changed expectation: section 07 used to report NOT_YET_GENERATED because nothing
        # generated study guidance. The materializer now carries a deterministic study order
        # over the verified syllabus (GOVOS_GUIDANCE), so the roadmap is supported and projected
        # -- and it may contain nothing but the record's own syllabus topics. Mock Tests has
        # no verified question source and must still say so.
        mock = next(v for v in self.exam['sectionStates'].values() if v['sectionNum'] == 17)
        self.assertEqual(mock['state'], 'NOT_YET_GENERATED')
        road = next(v for v in self.exam['sectionStates'].values() if v['sectionNum'] == 7)
        self.assertEqual(road['state'], 'SUPPORTED_AND_PROJECTED')
        guidance = self.exam['studyGuidance']
        self.assertEqual(guidance['source'], 'GOVOS_GUIDANCE')
        self.assertEqual(guidance['generatedBy'], 'deterministic')
        topics = {t['topicName'] for t in self.exam['syllabus']}
        self.assertTrue(guidance['steps'])
        self.assertTrue(all(s['topicName'] in topics for s in guidance['steps']))
        self.assertNotIn('durationWeeks', json.dumps(guidance))

    def test_improvement_over_the_stored_runtime(self):
        before = self.fx['runtimeBeforeSummary']
        e, g = self.exam, self.exam['applicationGuide']
        self.assertEqual(before['stages'], 0)
        self.assertGreater(len(e['stages']), before['stages'])
        self.assertIsNone(before['admitCardEvents'])
        self.assertEqual(len(e['admitCardEvents']), 1)
        self.assertEqual(before['applicationGuide']['photoRules'], 0)
        self.assertEqual(len(g['photoRules']['rules']), 2)
        self.assertEqual(before['applicationGuide']['requiredDocuments'], 0)
        self.assertGreater(len(g['requiredDocuments']), 0)
        self.assertFalse(before['applicationGuide']['fee'])
        self.assertTrue(g['fee'])

    def test_no_other_exam_is_present_in_the_runtime_record(self):
        blob = json.dumps(self.exam)
        for foreign in ('Staff Selection Commission', 'ssc.gov.in', 'upsc.gov.in', 'Union Public Service',
                        'ibps.in', 'psc.ap.gov.in'):
            self.assertNotIn(foreign, blob)


class TestStoredRecordSemanticStates(unittest.TestCase):
    """The stored record predates the semantic-state check; applying it to that record must
    turn the two states its own evidence contradicts into NEEDS_REVIEW, and touch nothing else."""

    def test_contradicted_states_become_needs_review(self):
        from .build import enforce_semantic_states
        rec = M.record_from_snapshot(_load()['record'])
        before = {n: f.status for n, f in rec.fields.items()}
        changed = enforce_semantic_states(rec)
        self.assertIs(rec.fields['posts'].status, Status.NEEDS_REVIEW)
        self.assertIs(rec.fields['feeExemptions'].status, Status.NEEDS_REVIEW)
        self.assertIn('exempted', rec.fields['feeExemptions'].citation.excerpt)
        self.assertEqual(len(changed), 2, changed)
        after = {n: f.status for n, f in rec.fields.items()}
        self.assertEqual({n for n in before if before[n] is not after[n]}, {'posts', 'feeExemptions'})


if __name__ == '__main__':
    unittest.main()
