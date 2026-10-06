"""Candidate data is never silently lost, overwritten, downgraded or presented from a failed read.

Each test runs on its own temporary database (DB_FILE is pointed at it before any request); govos.db is
never written. What these pin, each a defect reproduced before it was fixed:

  * sync-all / mock-attempts: `details: {}` stored {"userAnswers": null, "paperData": null} over the
    candidate's paper and answers, a payload without a score set it to 0, and re-sending an attempt
    failed with "UNIQUE constraint failed" -- leaving the database locked, so the next save failed too.
  * profile: every absent field was written as an SSC CGL default, so choosing a target post reset the
    stored category and qualification, and saving the profile reset the post.
  * preferences: with nothing stored the server answered with the defaults, which the app took as the
    candidate's saved choice; tracked exams: a new database tracked SSC CGL for the candidate.
  * feeds: a reply that parsed to nothing (an error body, a changed page) was stored as an empty board
    over the last good copy.
  * link health: a timeout is UNREACHABLE (rechecked), never BROKEN; a later success replaces it.

Run: python -m pytest test_persistence_integrity.py -q
"""
from __future__ import annotations

import io
import json
import os
import tempfile
import time
import unittest
import urllib.request
from unittest.mock import patch

import app as govos

SSC = 'exam-ssc-cgl-2026'
UPSC = 'exam-upsc-cse-2026'


def attempt(**over):
    a = {'id': 'att-1', 'exam_id': SSC, 'subject': 'Full Mock', 'score': 150, 'total_marks': 200,
         'correct_count': 80, 'incorrect_count': 10, 'unattempted_count': 10, 'time_taken_seconds': 3000,
         'details': {'userAnswers': {'q1': 2, 'q2': 0}, 'paperData': {'id': 'p1', 'questions': [{'id': 'q1'}, {'id': 'q2'}]}}}
    a.update(over)
    return a


class _ScratchDb(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self._orig = govos.DB_FILE
        govos.DB_FILE = self.path
        govos.init_database()
        self.client = govos.app.test_client()

    def tearDown(self):
        govos.DB_FILE = self._orig
        try:
            os.unlink(self.path)
        except OSError:
            pass

    def assertFailed(self, call):
        """The request failed -- as a 500 or as the exception itself, whichever the test client surfaces."""
        try:
            r = call()
        except RuntimeError:
            return
        self.assertEqual(r.status_code, 500)

    def stored(self, attempt_id='att-1'):
        rows = self.client.get('/api/sqlite/mock-attempts').get_json()['attempts']
        return [r for r in rows if r['id'] == attempt_id]

    def sync(self, *attempts, **extra):
        return self.client.post('/api/sqlite/sync-all', json=dict({'mock_attempts': list(attempts)}, **extra))


class AttemptMerge(_ScratchDb):
    """An attempt id names one submitted attempt: a later payload may add or correct, never erase."""

    def test_empty_details_keep_the_stored_paper_and_answers(self):
        self.sync(attempt())
        self.sync(attempt(details={}))
        (row,) = self.stored()
        self.assertEqual(row['details']['paperData']['id'], 'p1')
        self.assertEqual(row['details']['userAnswers'], {'q1': 2, 'q2': 0})

    def test_missing_paper_keeps_the_paper(self):
        self.sync(attempt())
        self.sync(attempt(details={'userAnswers': {'q1': 1}}))
        (row,) = self.stored()
        self.assertEqual(row['details']['paperData']['id'], 'p1')
        self.assertEqual(row['details']['userAnswers'], {'q1': 1}, 'a present value is a correction')

    def test_missing_answers_keep_the_answers(self):
        self.sync(attempt())
        self.sync(attempt(details={'paperData': None, 'userAnswers': None}))
        (row,) = self.stored()
        self.assertEqual(row['details']['userAnswers'], {'q1': 2, 'q2': 0})

    def test_an_explicit_valid_replacement_replaces(self):
        self.sync(attempt())
        self.sync(attempt(score=160, details={'paperData': {'id': 'p1', 'questions': [{'id': 'q1'}], 'rev': 2}}))
        (row,) = self.stored()
        self.assertEqual(row['details']['paperData']['rev'], 2)
        self.assertEqual(row['score'], 160)

    def test_a_payload_without_scores_keeps_the_scores(self):
        self.sync(attempt())
        self.sync({'id': 'att-1', 'exam_id': SSC})
        (row,) = self.stored()
        self.assertEqual((row['score'], row['correct_count']), (150, 80))

    def test_older_clients_top_level_fields_still_count(self):
        self.sync({'id': 'att-2', 'exam_id': SSC, 'score': 10, 'userAnswers': {'q': 1}, 'paperData': {'id': 'p9'}})
        (row,) = self.stored('att-2')
        self.assertEqual(row['details'], {'userAnswers': {'q': 1}, 'paperData': {'id': 'p9'}})

    def test_an_attempt_with_nothing_in_it_stores_no_null_details(self):
        self.sync({'id': 'att-3', 'exam_id': SSC, 'score': 1, 'details': {}})
        (row,) = self.stored('att-3')
        self.assertIsNone(row['details'])

    def test_the_same_attempt_resent_merges_on_both_routes(self):
        first = self.client.post('/api/sqlite/mock-attempts', json=attempt())
        again = self.client.post('/api/sqlite/mock-attempts', json=attempt(details={}))
        self.assertEqual((first.status_code, again.status_code), (201, 200), again.get_json())
        self.assertEqual(len(self.stored()), 1)
        self.assertEqual(self.stored()[0]['details']['paperData']['id'], 'p1')

    def test_an_id_stored_under_another_exam_is_refused_not_refiled(self):
        self.client.post('/api/sqlite/mock-attempts', json=attempt())
        r = self.client.post('/api/sqlite/mock-attempts', json=attempt(exam_id=UPSC, details={}))
        self.assertEqual(r.status_code, 409)
        res = self.sync(attempt(exam_id=UPSC)).get_json()
        self.assertEqual(res['conflictingAttempts'], ['att-1'])
        (row,) = self.stored()
        self.assertEqual(row['exam_id'], SSC)

    def test_a_failed_write_does_not_lock_the_next_one(self):
        """One refused write used to keep its transaction open; the next save waited 30 s and failed."""
        self.client.post('/api/sqlite/mock-attempts', json=attempt())
        def write_then_fail(cursor, *_):
            cursor.execute("INSERT INTO mock_attempts (id, user_id, exam_id, score, total_marks) VALUES ('half', 'u', 'e', 0, 0)")
            raise RuntimeError('boom')          # as the UNIQUE failure did: mid-transaction
        with patch.object(govos, '_merge_attempt', side_effect=write_then_fail):
            self.assertFailed(lambda: self.client.post('/api/sqlite/mock-attempts', json=attempt(id='att-9')))
        started = time.monotonic()
        r = self.client.post('/api/sqlite/profile', json={'category': 'SC'})
        self.assertEqual(r.status_code, 200)
        self.assertLess(time.monotonic() - started, 5)
        self.assertEqual(self.stored('half'), [], 'the half-done write was rolled back')

    def test_running_the_same_sync_twice_changes_nothing(self):
        self.sync(attempt(), attempt(id='att-2'))
        before = self.client.get('/api/sqlite/mock-attempts').get_json()['attempts']
        self.sync(attempt(), attempt(id='att-2'))
        self.assertEqual(self.client.get('/api/sqlite/mock-attempts').get_json()['attempts'], before)

    def test_an_oversized_request_is_refused_and_stored_data_is_kept(self):
        self.sync(attempt())
        huge = attempt(details={'paperData': {'blob': 'x' * (17 * 1024 * 1024)}})
        r = self.client.post('/api/sqlite/sync-all', data=json.dumps({'mock_attempts': [huge]}),
                             content_type='application/json')
        self.assertEqual(r.status_code, 413)
        self.assertEqual(self.stored()[0]['details']['paperData']['id'], 'p1')

    def test_sync_success_failure_recovery(self):
        self.sync(attempt())
        with patch.object(govos, '_merge_attempt', side_effect=RuntimeError('disk')):
            self.assertFailed(lambda: self.sync(attempt(score=1)))
        self.assertEqual(self.stored()[0]['score'], 150, 'the failed request changed nothing')
        self.sync(attempt(score=170))
        self.assertEqual(self.stored()[0]['score'], 170)


class ProfileAndPreferences(_ScratchDb):

    def profile(self):
        return {k: v for k, v in self.client.get('/api/sqlite/profile').get_json().items()
                if k in ('target_post_id', 'target_exam_id', 'category', 'qualification')}

    def test_a_new_database_invents_no_candidate(self):
        self.assertEqual(self.profile(), {'target_post_id': '', 'target_exam_id': '', 'category': '', 'qualification': ''})
        self.assertEqual(self.client.get('/api/sqlite/tracked-exams').get_json()['tracked_exam_ids'], [])

    def test_a_partial_update_changes_only_its_own_fields(self):
        self.client.post('/api/sqlite/profile', json={'category': 'SC', 'qualification': 'Class 12'})
        self.client.post('/api/sqlite/profile', json={'target_post_id': 'post-x'})
        self.assertEqual(self.profile(), {'target_post_id': 'post-x', 'target_exam_id': '', 'category': 'SC',
                                          'qualification': 'Class 12'})
        self.client.post('/api/sqlite/profile', json={'category': 'OBC'})
        self.assertEqual(self.profile()['target_post_id'], 'post-x')

    def test_sync_all_writes_only_the_profile_fields_it_carries(self):
        self.client.post('/api/sqlite/profile', json={'category': 'ST', 'qualification': 'Graduate', 'target_exam_id': UPSC})
        self.sync(profile={'target_post_id': 'post-y'})
        self.assertEqual(self.profile(), {'target_post_id': 'post-y', 'target_exam_id': UPSC, 'category': 'ST',
                                          'qualification': 'Graduate'})

    def test_preferences_never_stored_are_said_so_not_defaulted(self):
        got = self.client.get('/api/sqlite/notifications/preferences').get_json()
        self.assertEqual(got.get('stored'), False)
        self.assertNotIn('channels', got)
        prefs = {'channels': {'inApp': True, 'email': True}, 'contactInfo': {'email': 'a@b.c'},
                 'eventSubscriptions': {'results': False}, 'reminderSchedule': {'oneDayBefore': False}}
        self.client.post('/api/sqlite/notifications/preferences', json=prefs)
        got = self.client.get('/api/sqlite/notifications/preferences').get_json()
        self.assertEqual(got['eventSubscriptions'], {'results': False})


class DuplicateWrites(_ScratchDb):
    """A repeated write (double click, retried request) is one record, not two."""

    def setUp(self):
        super().setUp()
        self._orig_check = govos._check_one_link
        govos._check_one_link = lambda url: {'url': url, 'status': 'HEALTHY', 'httpCode': 200, 'checkedAt': 'now'}

    def tearDown(self):
        govos._check_one_link = self._orig_check
        super().tearDown()

    def test_the_same_addition_twice_is_one_addition(self):
        body = {'title': 'Old papers', 'url': 'https://upsc.gov.in/papers', 'examId': UPSC}
        first = self.client.post('/api/resources/additions', json=body).get_json()
        again = self.client.post('/api/resources/additions', json=body).get_json()
        self.assertTrue(again.get('deduplicated'))
        self.assertEqual(first['addition']['id'], again['addition']['id'])
        self.assertEqual(len(self.client.get(f'/api/resources/additions?exam_id={UPSC}').get_json()['additions']), 1)

    def test_the_same_revision_twice_is_one_revision(self):
        body = {'examId': UPSC, 'kind': 'ADD', 'topic': {'subject': 'General Studies', 'topicName': 'New topic'},
                'noticeUrl': 'https://upsc.gov.in/corr.pdf'}
        self.client.post('/api/syllabus/revisions', json=body)
        again = self.client.post('/api/syllabus/revisions', json=body).get_json()
        self.assertTrue(again.get('deduplicated'))
        self.assertEqual(len(self.client.get(f'/api/syllabus/revisions?exam_id={UPSC}').get_json()['revisions']), 1)
        # a different change is a different revision
        self.client.post('/api/syllabus/revisions', json=dict(body, topic={'subject': 'General Studies', 'topicName': 'Other'}))
        self.assertEqual(len(self.client.get(f'/api/syllabus/revisions?exam_id={UPSC}').get_json()['revisions']), 2)

    def test_a_retired_revision_can_be_applied_again(self):
        body = {'examId': UPSC, 'kind': 'RETIRE', 'topicId': 't1', 'note': 'dropped in the corrigendum'}
        rid = self.client.post('/api/syllabus/revisions', json=body).get_json()['revision']['id']
        self.client.post(f'/api/syllabus/revisions/{rid}/retire')
        again = self.client.post('/api/syllabus/revisions', json=body).get_json()
        self.assertFalse(again.get('deduplicated'))


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FeedsKeepTheirLastGoodCopy(_ScratchDb):

    def age(self, key, seconds):
        import sqlite3
        conn = sqlite3.connect(self.path)
        from datetime import datetime, timedelta
        conn.execute('UPDATE live_feed_cache SET fetched_at = ? WHERE cache_key = ?',
                     ((datetime.now() - timedelta(seconds=seconds)).isoformat(timespec='seconds'), key))
        conn.commit()
        conn.close()

    def ssc(self, body):
        govos._feed_failures.pop('ssc-notices', None)
        with patch.object(urllib.request, 'urlopen', return_value=_Resp(json.dumps(body).encode())):
            return govos._ssc_notices_cached(force=True)

    def good(self):
        return {'data': [{'id': 1, 'headline': 'Combined Graduate Level Examination, 2026 - notice', 'createdAt': '2026-10-01'}]}

    def test_failed_refresh_keeps_the_copy_with_its_error(self):
        self.ssc(self.good())
        self.age('ssc-notices', 7 * 3600)
        govos._feed_failures.pop('ssc-notices', None)
        with patch.object(urllib.request, 'urlopen', side_effect=OSError('timed out')):
            got = govos._ssc_notices_cached(force=True)
        self.assertEqual(len(got['payload']), 1)
        self.assertIn('refresh failed', got['error'])
        self.assertEqual(len(govos._cache_get('ssc-notices', 1e9)['payload']), 1)

    def test_a_reply_without_the_list_is_a_failure_not_an_empty_board(self):
        self.ssc(self.good())
        self.age('ssc-notices', 7 * 3600)
        got = self.ssc({'message': 'Service Unavailable'})
        self.assertEqual(len(got['payload']), 1)
        self.assertIn('refresh failed', got['error'])
        self.assertEqual(len(govos._cache_get('ssc-notices', 1e9)['payload']), 1)

    def test_an_authoritative_empty_list_is_accepted(self):
        self.ssc(self.good())
        self.age('ssc-notices', 7 * 3600)
        got = self.ssc({'data': []})
        self.assertEqual(got['payload'], [])
        self.assertIsNone(got['error'])

    def test_recovery_after_a_failure(self):
        self.ssc(self.good())
        self.age('ssc-notices', 7 * 3600)
        self.ssc({'message': 'down'})
        self.age('ssc-notices', 7 * 3600)
        body = self.good()
        body['data'].append({'id': 2, 'headline': 'Second', 'createdAt': '2026-10-02'})
        got = self.ssc(body)
        self.assertEqual((len(got['payload']), got['error']), (2, None))

    def test_upsc_page_without_rows_and_non_atom_channel_reply_are_failures(self):
        with patch.object(urllib.request, 'urlopen', return_value=_Resp(b'<html><body>Maintenance</body></html>')):
            with self.assertRaises(ValueError):
                govos._fetch_upsc_whatsnew([])
        with patch.object(urllib.request, 'urlopen', return_value=_Resp(b'<html><body>consent</body></html>')):
            with self.assertRaises(Exception):
                govos._fetch_channel_uploads('UCxyz')
        empty_feed = b'<feed xmlns="http://www.w3.org/2005/Atom"><title>c</title></feed>'
        with patch.object(urllib.request, 'urlopen', return_value=_Resp(empty_feed)):
            self.assertEqual(govos._fetch_channel_uploads('UCxyz'), [], 'a channel with no uploads is empty')


class LinkHealth(_ScratchDb):

    def check(self, effect):
        class Opener:
            def open(self, req, timeout=None):
                if isinstance(effect, Exception):
                    raise effect
                return effect
        with patch.object(govos, '_public_link', return_value=(True, '')), \
                patch.object(urllib.request, 'build_opener', return_value=Opener()):
            return govos._check_one_link('https://example.gov.in/x')

    def test_timeout_is_unreachable_never_broken_and_recovers(self):
        url = 'https://example.gov.in/x'
        govos._store_health([{'url': url, 'status': 'HEALTHY', 'httpCode': 200, 'checkedAt': '2026-10-01T00:00:00'}])
        timed_out = self.check(TimeoutError('timed out'))
        self.assertEqual(timed_out['status'], 'UNREACHABLE')
        govos._store_health([timed_out])
        self.assertEqual(govos._health_rows([url])[0]['status'], 'UNREACHABLE')

        class Ok(_Resp):
            def getcode(self):
                return 200

            def geturl(self):
                return url
        recovered = self.check(Ok(b''))
        govos._store_health([recovered])
        (row,) = govos._health_rows([url])
        self.assertEqual(row['status'], 'HEALTHY')

    def test_a_stored_result_is_rechecked_once_old(self):
        url = 'https://example.gov.in/y'
        old = '2020-01-01T00:00:00'
        govos._store_health([{'url': url, 'status': 'HEALTHY', 'httpCode': 200, 'checkedAt': old},
                             {'url': url + 'z', 'status': 'UNREACHABLE', 'httpCode': 0, 'checkedAt': old}])
        due = govos._health_due()
        self.assertIn(url, due, 'a success is not proof forever')
        self.assertIn(url + 'z', due, 'a failure is not permanent')


if __name__ == '__main__':
    unittest.main()
