"""App-level tests for authority source discovery as wired into `app.py`: the admin guard on starting
a walk, the job it queues, the stored run, and the candidate-facing projection. Uses the isolated
harness of test_app_claude (temporary database, network blocked, Claude faked)."""
import json
import os
import unittest
from unittest import mock

import tools.claude_cli.testing  # noqa: F401  (marks the process as under test BEFORE app is imported)
from test_app_claude import REMOTE, AppCase
from tools.exam_builder import authority_discovery as AD
from tools.exam_builder.authority_fixture_site import AUTHORITY, ROOT, FakeSite
from tools.exam_builder.source_graph import SourceGraphStore

EXAM_ID = 'exam-epsc-group-i-2026'


class SourceDiscoveryRoutes(AppCase):
    def setUp(self):
        super().setUp()
        authored = os.path.join(self.tmpdir, 'no-authored-exams.json')
        with open(authored, 'w', encoding='utf-8') as fh:
            json.dump([{'id': EXAM_ID, 'title': 'Group-I Services', 'authorityName': AUTHORITY,
                        'officialDomain': ROOT, 'resources': []}], fh)

    def test_an_exam_never_walked_says_so_and_claims_nothing_about_the_authority(self):
        body = self.get(f'/api/sources/exam/{EXAM_ID}').get_json()
        self.assertEqual(body['state'], 'NOT_DISCOVERED')
        self.assertIn('not a statement about what the authority publishes', body['note'])
        self.assertEqual(self.get('/api/sources/exam/exam-missing-2026').status_code, 404)

    def test_starting_a_walk_is_admin_only(self):
        r = self.post('/api/sources/discover', {'examId': EXAM_ID}, remote=REMOTE)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.post('/api/sources/runs', remote=REMOTE).status_code, 405)
        self.assertEqual(self.get('/api/sources/runs', remote=REMOTE).status_code, 403)

    def test_a_walk_is_a_job_and_its_run_reaches_the_exams_sections(self):
        r = self.post('/api/sources/discover', {'examId': EXAM_ID, 'root': 'http://169.254.169.254/'})
        self.assertEqual(r.status_code, 202, r.get_json())
        job_id = r.get_json()['jobId']
        site = FakeSite()
        with mock.patch.object(AD, 'fetch_checked', lambda url, **kw: site(url)):
            body = self.finish(job_id)
        self.assertEqual(body['status'], 'SUCCEEDED', body)
        self.assertEqual(site.calls[0], ROOT, 'the walk starts at the exam\'s own address, never a supplied one')
        self.assertNotIn('169.254.169.254', ' '.join(site.calls))
        projection = self.get(f'/api/sources/exam/{EXAM_ID}').get_json()
        self.assertEqual(projection['state'], 'DISCOVERED')
        self.assertEqual(projection['searchStates']['NOTIFICATION']['state'], 'FOUND_VERIFIED')
        repos = {x['title']: x for x in projection['repositories']}
        self.assertEqual(repos['Old Question Papers']['itemsForThisExam'], 0)
        (mock_exam,) = projection['learning']
        self.assertEqual((mock_exam['title'], mock_exam['sourceClass']), ('Online Mock Exam', 'SECONDARY'))
        runs = self.get('/api/sources/runs').get_json()['runs']
        self.assertEqual(len(runs), 1)
        cov = self.get(f"/api/sources/runs/{runs[0]['id']}/coverage").get_json()
        self.assertEqual(cov['rootsInspected'], [ROOT])
        self.assertEqual(self.get('/api/sources/runs/run-missing/coverage').status_code, 404)
        self.assertEqual(SourceGraphStore(self.db).latest('epsc.gov.in').id, runs[0]['id'])

    def walk(self):
        job_id = self.post('/api/sources/discover', {'examId': EXAM_ID}).get_json()['jobId']
        site = FakeSite()
        with mock.patch.object(AD, 'fetch_checked', lambda url, **kw: site(url)):
            self.assertEqual(self.finish(job_id)['status'], 'SUCCEEDED')

    def test_a_walk_is_projected_once_and_a_new_walk_replaces_it(self):
        # Every section of an exam page asks for the projection; it used to be rebuilt from the whole
        # stored walk on each request. It is now projected once per run, and a new walk is read at once.
        self.walk()
        with mock.patch.object(AD, 'project_for_exam', wraps=AD.project_for_exam) as projected:
            first = self.get(f'/api/sources/exam/{EXAM_ID}').get_json()
            again = self.get(f'/api/sources/exam/{EXAM_ID}').get_json()
            self.assertEqual(projected.call_count, 1)
            self.assertEqual(first, again)
            self.walk()
            before = projected.call_count
            newer = self.get(f'/api/sources/exam/{EXAM_ID}').get_json()
            self.assertEqual(projected.call_count, before + 1)
        self.assertEqual(newer['state'], 'DISCOVERED')
        self.assertNotEqual(newer['runId'], first['runId'])

    def test_asking_for_claude_when_it_is_not_ready_is_refused_before_anything_is_queued(self):
        r = self.post('/api/sources/discover', {'examId': EXAM_ID, 'useClaude': True})
        self.assertEqual(r.status_code, 503)
        self.assertEqual(self.scalar('SELECT COUNT(*) FROM claude_jobs'), 0)


if __name__ == '__main__':
    unittest.main()
