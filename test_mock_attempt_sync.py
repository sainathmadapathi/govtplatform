"""The server side of mock-attempt sync, with the payloads the client now sends.

Each attempt carries its answers and its paper once, under `details`; sync-all arrives as several
size-bounded requests (the first with the profile, the rest with only `user_id` and attempts). The
server is unchanged: these tests pin that it stores every attempt once, from either route, that
running the sync again changes nothing, and that its 16 MB limit still stands.
Every test runs on its own temporary database; govos.db is never touched.

Run: python -m pytest test_mock_attempt_sync.py -q
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest

import app as govos

BATCH_BUDGET = 4 * 1024 * 1024        # the client's SYNC_BATCH_BUDGET_BYTES


def paper(seed: int) -> dict:
    """A paper of realistic size (~300 KB): 100 questions with options and worked explanations."""
    return {'id': f'paper-{seed}', 'title': f'Practice paper {seed}', 'questions': [
        {'id': f'p{seed}-q{i}', 'questionText': f'Question {i} ' + 'text ' * 120,
         'options': [{'id': o, 'text': f'option {o} ' * 8} for o in range(4)],
         'correctOptionIndex': i % 4, 'explanation': 'because ' * 300} for i in range(100)]}


def clean_attempt(i: int, exam_id: str = 'exam-ssc-cgl-2026') -> dict:
    """An attempt as attemptSyncPayload (src/services.ts) builds it: answers and paper once, in details."""
    return {'id': f'att-{i}', 'exam_id': exam_id, 'subject': 'Full Mock', 'score': 100 + i, 'total_marks': 200,
            'correct_count': 60, 'incorrect_count': 20, 'unattempted_count': 20, 'time_taken_seconds': 3600,
            'details': {'userAnswers': {str(q): q % 4 for q in range(100)}, 'paperData': paper(i)}}


def batches(attempts: list, budget: int = BATCH_BUDGET) -> list:
    """The client's greedy split (planAttemptSyncBatches), by serialized size."""
    out, current, size = [], [], 0
    for a in attempts:
        n = len(json.dumps(a).encode()) + 1
        if current and size + n > budget:
            out.append(current)
            current, size = [], 0
        current.append(a)
        size += n
    return out + ([current] if current else [])


class MockAttemptSyncTests(unittest.TestCase):

    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self._orig_db = govos.DB_FILE
        govos.DB_FILE = self.path
        govos.init_database()
        self.client = govos.app.test_client()

    def tearDown(self):
        govos.DB_FILE = self._orig_db
        try:
            os.remove(self.path)
        except OSError:
            pass

    def rows(self):
        conn = govos.get_db_connection()
        out = {r['id']: dict(r) for r in conn.execute("SELECT * FROM mock_attempts WHERE id LIKE 'att-%'").fetchall()}
        conn.close()
        return out

    def sync(self, attempts: list) -> list:
        """Send `attempts` as the client does: size-bounded requests, the profile with the first."""
        codes = []
        for n, batch in enumerate(batches(attempts) or [[]]):
            body = ({'user_id': 'default-candidate', 'profile': {'target_post_id': ''}, 'completed_modules': {},
                     'mock_attempts': batch, 'tracked_exams': [], 'notification_preferences': {}}
                    if n == 0 else {'user_id': 'default-candidate', 'mock_attempts': batch})
            data = json.dumps(body)
            self.assertLess(len(data.encode()), govos.app.config['MAX_CONTENT_LENGTH'])
            codes.append(self.client.post('/api/sqlite/sync-all', data=data, content_type='application/json').status_code)
        return codes

    def test_one_paper_is_stored_once_from_the_single_attempt_route(self):
        r = self.client.post('/api/sqlite/mock-attempts', json=clean_attempt(1))
        self.assertEqual(r.status_code, 201, r.get_data(as_text=True)[:200])
        row = self.rows()['att-1']
        self.assertEqual(row['details_json'].count('"p1-q0"'), 1)
        details = json.loads(row['details_json'])
        self.assertEqual((details['paperData']['id'], len(details['userAnswers'])), ('paper-1', 100))

    def test_a_large_realistic_history_arrives_in_bounded_requests_and_every_attempt_is_stored_once(self):
        history = [clean_attempt(i) for i in range(50)]
        codes = self.sync(history)
        self.assertGreater(len(codes), 1)
        self.assertEqual(set(codes), {200})
        rows = self.rows()
        self.assertEqual(set(rows), {a['id'] for a in history}, 'an attempt disappeared')
        for i in range(50):
            self.assertEqual(rows[f'att-{i}']['details_json'].count(f'"p{i}-q0"'), 1)
            self.assertEqual(json.loads(rows[f'att-{i}']['details_json'])['paperData']['id'], f'paper-{i}')

    def test_running_the_sync_again_changes_nothing(self):
        history = [clean_attempt(i) for i in range(12)]
        self.sync(history)
        first = self.rows()
        self.sync(history)
        self.assertEqual(self.rows(), first)
        self.assertEqual(len(first), 12)

    def test_later_requests_carry_no_profile_and_leave_it_alone(self):
        self.client.post('/api/sqlite/sync-all', json={'user_id': 'default-candidate',
                                                        'profile': {'target_post_id': 'post-x'}, 'mock_attempts': []})
        r = self.client.post('/api/sqlite/sync-all', json={'user_id': 'default-candidate', 'mock_attempts': [clean_attempt(3)]})
        self.assertEqual(r.status_code, 200)
        conn = govos.get_db_connection()
        target = conn.execute("SELECT target_post_id FROM users WHERE id = 'default-candidate'").fetchone()[0]
        conn.close()
        self.assertEqual(target, 'post-x')
        self.assertIn('att-3', self.rows())

    def test_an_empty_history_still_syncs_the_profile(self):
        self.assertEqual(self.sync([]), [200])
        self.assertEqual(self.rows(), {})

    def test_a_request_near_the_limit_is_accepted_and_one_over_it_is_refused(self):
        near = clean_attempt(7)
        near['details']['paperData']['padding'] = 'x' * (15 * 1024 * 1024)
        r = self.client.post('/api/sqlite/sync-all', data=json.dumps({'user_id': 'default-candidate', 'mock_attempts': [near]}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 200)
        self.assertIn('att-7', self.rows())
        near['details']['paperData']['padding'] = 'x' * (17 * 1024 * 1024)
        r = self.client.post('/api/sqlite/sync-all', data=json.dumps({'user_id': 'default-candidate', 'mock_attempts': [near]}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 413)
        self.assertEqual(govos.app.config['MAX_CONTENT_LENGTH'], 16 * 1024 * 1024)


if __name__ == '__main__':
    unittest.main()
