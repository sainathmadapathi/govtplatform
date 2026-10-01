"""Regression: TGPSC Group-I 02/2024 frozen at registry v7, the completed reference build.

The fixture is the canonical record the registry held at v7 -- READY, source-exhausted after the
final audit -- with a digest of the runtime exam the universal engine produced from it. This test
re-materializes the record offline and holds the engine to it:

  * the runtime is byte-for-byte the frozen one (every top-level key's digest; only the generation
    timestamp is excluded), so no later change can quietly alter what a candidate sees;
  * the verified facts are still there -- 18 posts, both reconciled vacancy tables, the superseded
    printed deadline, the official admission rule, the notice's own clauses;
  * the source-exhausted gaps stay honest -- still unavailable, still carrying the searches that
    were made, never filled in.

Two digests are frozen. `runtimeDigest` is the whole runtime; `factDigest` is the runtime with
the evidence metadata removed (runtime_evidence.strip_evidence_metadata), so a change to how
evidence is presented can be re-frozen without it ever hiding a change to a fact.

Re-frozen on 2026-09-29 when evidence was attached to every published fact: the only fact-level
differences from v7 were four evidence records that did not exist before (the corrigendum and
three official links); no value, page, clause or excerpt changed. Re-frozen the same day for one
more provenance correction: 113 provenance records gave the day GovOS read the notice
(2026-09-28) as its publishedDate; a read date is not a publication date, and they now carry ''.
Re-frozen again the same day, for two additions and no changed fact: the practice application
form built from the record's own rules (applicationGuide.simulator), and the study order's
reason, which said "Scheduled by weightage" for an authority that publishes no weightage.
Re-frozen once more after the candidate-truth audit, for two changes and no other: a post whose
department the notice does not print now shows none (all 18 had shown the Commission's own name),
and the hall-ticket search page is typed as a service page, not a PDF. Undoing exactly those two on
the new runtime reproduces the previous digest.
Re-frozen on 2026-10-01 for the move from the local model to the Claude CLI, for one change and no
other: studyGuidance.infra, the state of the optional AI step, now reads CLAUDE_DISABLED where it
read LLM_DISABLED. Two digest lines changed (studyGuidance in runtimeDigest and in factDigest); no
fact, page, clause or excerpt did.

The record is TGPSC's; the code under test names no exam. If a digest changes on purpose, re-freeze:
    python -m tools.exam_builder.test_tgpsc_v7_fixture --refreeze
and say in the commit what changed and why.

Run: python -m unittest tools.exam_builder.test_tgpsc_v7_fixture
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest

from . import materialize as M
from .runtime_evidence import evidence_id, evidence_problems, strip_evidence_metadata

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'tgpsc_group_i_2024_v7.json')

#: What varies between two materializations of the same record: when it was done.
_VOLATILE = {('materialization', 'generatedAt')}


def runtime_digest(exam: dict) -> dict:
    """sha256 of every top-level key of a runtime exam, volatile fields removed."""
    out = {}
    for key, value in exam.items():
        if isinstance(value, dict):
            value = {k: v for k, v in value.items() if (key, k) not in _VOLATILE}
        blob = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
        out[key] = hashlib.sha256(blob.encode('utf-8')).hexdigest()
    return out


def _load() -> dict:
    with open(FIXTURE, encoding='utf-8') as fh:
        return json.load(fh)


def _rematerialize(fx: dict):
    reg = M.ExamRegistry(':memory:')
    c = reg._conn()
    c.execute('''INSERT INTO exam_registry (exam_id, cycle, authority_name, authority_domain, official_name, version,
                 gate_decision, published, exam_json, record_json, completeness_json, created_at, updated_at, retired)
                 VALUES (?, ?, ?, ?, ?, ?, 'PASS', 1, '{}', ?, ?, 't', 't', 0)''',
              (fx['examId'], fx['cycle'], fx['record']['authorityName'], fx['record']['officialDomain'],
               fx['record']['title'], fx['registryVersionAtCapture'], json.dumps(fx['record']),
               json.dumps(fx['completeness'])))
    c.commit()
    return M.rematerialize(reg, fx['examId'], fx['cycle'], target=M.ExamRegistry(':memory:'))


class TestTgpscV7Frozen(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.fx = _load()
        cls.out = _rematerialize(cls.fx)
        cls.exam = cls.out.exam or {}
        cls.fields = cls.fx['record']['fields']

    # ------------------------------------------------------------------ the pipeline holds
    def test_rematerializes_through_the_gate_with_no_loss(self):
        self.assertIs(self.out.state, M.EngineState.REGISTERED, self.out.reason)
        self.assertEqual(self.out.materialization['projectionLosses'], [])
        self.assertEqual(M.validate_runtime_exam(self.exam), [])
        self.assertEqual(self.out.gate['decision'], 'PASS')
        self.assertEqual(self.out.gate['runtimeDecision'], 'PASS')

    def test_the_runtime_is_byte_for_byte_the_frozen_one(self):
        got, want = runtime_digest(self.exam), self.fx['runtimeDigest']
        self.assertEqual(sorted(got), sorted(want), 'the runtime gained or lost a top-level key')
        changed = sorted(k for k in want if got[k] != want[k])
        self.assertEqual(changed, [], 'the engine now produces a different runtime for the frozen v7 '
                                      'record in these keys; re-freeze only if that is intended')

    def test_the_facts_are_the_frozen_ones(self):
        # The runtime without its evidence metadata: what a candidate is told, as opposed to how
        # its source is shown. This digest changes only when a fact changes.
        got = runtime_digest(strip_evidence_metadata(self.exam))
        changed = sorted(k for k in self.fx['factDigest'] if got.get(k) != self.fx['factDigest'][k])
        self.assertEqual(changed, [], 'a published fact changed')

    def test_the_runtime_does_not_depend_on_field_order(self):
        # The same canonical record must give the same runtime however it was serialized. The
        # notice resource once borrowed whichever field a build set first, and a record re-saved
        # with its keys in another order showed candidates a different provenance.
        fx = dict(self.fx)
        record = dict(fx['record'])
        record['fields'] = dict(reversed(list(record['fields'].items())))
        fx['record'] = record
        self.assertEqual(runtime_digest(_rematerialize(fx).exam), runtime_digest(self.exam))

    def test_all_seventeen_sections_keep_their_state(self):
        states = {k: v['state'] for k, v in self.exam['sectionStates'].items()}
        self.assertEqual(len(states), 17)
        self.assertEqual(states, {
            'overview': 'VERIFIED_AVAILABLE', 'dates': 'VERIFIED_AVAILABLE',
            'eligibility': 'VERIFIED_AVAILABLE', 'application': 'VERIFIED_AVAILABLE',
            'pattern': 'VERIFIED_AVAILABLE', 'syllabus': 'VERIFIED_AVAILABLE',
            'roadmap': 'SUPPORTED_AND_PROJECTED', 'resources': 'VERIFIED_AVAILABLE',
            'pyqs': 'SOURCE_NOT_FOUND_AFTER_SEARCH', 'mock-tests': 'NOT_YET_GENERATED',
            'admit-card': 'VERIFIED_AVAILABLE', 'exam-day': 'VERIFIED_AVAILABLE',
            'results': 'VERIFIED_AVAILABLE', 'faqs': 'VERIFIED_AVAILABLE',
            'corrigenda': 'VERIFIED_AVAILABLE', 'official-links': 'VERIFIED_AVAILABLE',
            'cutoffs': 'SOURCE_NOT_FOUND_AFTER_SEARCH'})

    # ------------------------------------------------------------------ the verified facts
    def test_posts_are_the_eighteen_notified_posts(self):
        posts = self.exam['posts']
        self.assertEqual([p['postCode'] for p in posts], [f'{i:02d}' for i in range(1, 19)])
        self.assertEqual(sum(p['vacancies'] for p in posts), 563)
        self.assertTrue(all(p['payScale'] and p['specialQualification'] and p['provenance'] for p in posts))

    def test_both_vacancy_tables_reconcile_and_join_every_post(self):
        tables = self.exam['vacancyBreakups']
        self.assertEqual([len(t['rows']) for t in tables], [36, 18])
        self.assertEqual([t['tableTotal'] for t in tables], [563, 563])
        ids = {p['id'] for p in self.exam['posts']}
        for t in tables:
            self.assertTrue(all(r['postId'] in ids for r in t['rows']))
            self.assertTrue(any('printed total row' in c for c in t['checks']))
        # The notice's own table: every post's category counts sum to its vacancies.
        per_post: dict = {}
        for r in tables[0]['rows']:
            per_post[r['postId']] = per_post.get(r['postId'], 0) + sum(
                c['fresh'] + c['carriedForward'] for c in r['counts'])
        self.assertEqual(per_post, {p['id']: p['vacancies'] for p in self.exam['posts']})

    def test_the_printed_deadline_is_superseded_not_overwritten(self):
        closes = sorted((d['dateTimeStr'][:10], d['status']) for d in self.exam['dates']
                        if d['type'] == 'APPLICATION_CLOSE')
        self.assertEqual(closes, [('2024-03-14', 'SUPERSEDED'), ('2024-03-14', 'SUPERSEDED'),
                                  ('2024-03-16', 'AVAILABLE')])
        (corr,) = self.exam['corrigendums']
        self.assertEqual(corr['publishedDate'], '', 'the authority printed no date for the change')
        self.assertIn('No separate corrigendum notice', corr['summary'])

    def test_official_rules_stay_apart_from_guidance(self):
        official = [s for s in self.exam['resultNextSteps'] if s['isGuidance'] is False]
        self.assertEqual(len(official), 1)
        self.assertIn('Fifty (50) times', official[0]['summary'])
        self.assertEqual(official[0]['provenance']['verificationLevel'], 'OFFICIALLY_VERIFIED')
        self.assertEqual(len(self.exam['faqs']), 39)
        self.assertTrue(any('will not be notified as it is a Screening Test' in f['answer']
                            for f in self.exam['faqs']))

    def test_the_overview_states_the_count_as_printed(self):
        # Re-frozen on 2026-09-29 for this change alone: v7 said "approximately 563", but the
        # notice prints "TOTAL 563" in a table and calls it approximate nowhere.
        self.assertIn('The notice states 563 vacancies.', self.exam['overviewDescription'])
        self.assertNotIn('approximately', self.exam['overviewDescription'])
        self.assertIn('Applications close 2024-03-16', self.exam['overviewDescription'])

    def test_no_published_link_points_at_the_retired_domain(self):
        for link in self.exam['officialLinks']:
            self.assertNotIn('tspsc.gov.in', link['url'])
        self.assertEqual(self.exam['applicationGuide']['officialPortal'], 'https://websitenew.tgpsc.gov.in')

    # ------------------------------------------------------------------ evidence
    def test_every_fact_carries_complete_evidence(self):
        self.assertEqual(evidence_problems(self.exam), [])

    def test_the_vacancy_total_cites_its_own_printed_total(self):
        ev = self.exam['factEvidence']['vacanciesTotal']
        self.assertEqual((ev['excerptText'], str(ev['pageNumber']), ev['clauseNumber'], ev['evidenceType']),
                         ('TOTAL 563', '3', 'Vacancies', 'DIRECT'))
        self.assertEqual(ev['authorityName'], 'Telangana Public Service Commission')
        # The same evidence identity as the canonical record's own citation of the fact.
        c = self.fields['vacancies']['citation']
        self.assertEqual(ev['evidenceId'], evidence_id({'officialUrl': c['url'], 'pageNumber': c['page'],
                                                        'clauseNumber': c['clause'], 'excerptText': c['excerpt']}))

    def test_different_facts_keep_different_evidence(self):
        posts = {p['provenance']['evidenceId'] for p in self.exam['posts']}
        self.assertEqual(len(posts), len(self.exam['posts']), 'each post cites its own row')
        self.assertNotIn(self.exam['factEvidence']['vacanciesTotal']['evidenceId'], posts)

    def test_the_reconciled_deadline_shows_both_statements(self):
        gov = next(d for d in self.exam['dates'] if d['type'] == 'APPLICATION_CLOSE' and d['status'] == 'AVAILABLE')
        p = gov['provenance']
        self.assertEqual(p['evidenceType'], 'RECONCILED')
        self.assertEqual(len(p['supersedes']), 2)
        for old in (d for d in self.exam['dates'] if d['status'] == 'SUPERSEDED'):
            self.assertEqual(old['supersededBy'], gov['id'])
            self.assertEqual(old['provenance']['supersededBy']['evidenceId'], p['evidenceId'])
        (corr,) = self.exam['corrigendums']
        self.assertEqual(corr['provenance']['evidenceId'], p['evidenceId'])

    def test_the_homepage_carries_no_invented_evidence(self):
        home = self.exam['officialLinks'][0]
        self.assertNotIn('provenance', home, 'the resolved homepage is not a statement in a document')
        self.assertTrue(all(l.get('provenance') for l in self.exam['officialLinks'][1:]))

    # ------------------------------------------------------------------ source-exhausted gaps
    def test_unavailable_fields_stay_unavailable_with_their_searches(self):
        for name in ('answerKeys', 'officialPapers', 'cutoffs', 'attempts'):
            f = self.fields[name]
            self.assertEqual(f['status'], 'NOT_EXTRACTED', name)
            self.assertIsNone(f['value'], name)
            self.assertTrue(f['note'].startswith('searched'), f'{name} must say what was searched')
        for key in ('answerKeys', 'officialPapers', 'cutoffsHistory', 'practiceQuestions'):
            self.assertFalse(self.exam.get(key), f'{key} must not be filled in')

    def test_conditional_relaxations_are_not_flattened(self):
        by_cat = {r['category']: r for r in self.exam['ageRelaxations']}
        for name in by_cat:
            if 'length of' in (by_cat[name].get('condition') or ''):
                self.assertEqual(by_cat[name]['status'], 'NEEDS_REVIEW', name)
        self.assertEqual(sum(1 for r in by_cat.values() if r['status'] == 'NEEDS_REVIEW'), 3)


def _refreeze() -> None:
    """Re-freeze the runtime digest from the fixture's own canonical record. Deliberate only."""
    fx = _load()
    out = _rematerialize(fx)
    assert out.state is M.EngineState.REGISTERED, out.reason
    fx['runtimeDigest'] = runtime_digest(out.exam)
    fx['factDigest'] = runtime_digest(strip_evidence_metadata(out.exam))
    with open(FIXTURE, 'w', encoding='utf-8') as fh:
        json.dump(fx, fh, indent=1, ensure_ascii=False, sort_keys=True)
    print('re-froze', len(fx['runtimeDigest']), 'runtime keys')


if __name__ == '__main__':
    if '--refreeze' in sys.argv:
        _refreeze()
    else:
        unittest.main()
