"""Focused tests for the field-level research validation layer (RESEARCH_VALIDATION_DESIGN.md).

No Tavily call and no network: findings are inserted directly (as research_search would have
stored them) and reachability is stubbed, so the rules are exercised deterministically. The
last group proves the existing pipeline (findings review, promote gate, resource_additions) is
untouched by this layer.
"""
import json
import os
import tempfile
import unittest

import app as govos


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        self._orig_db = govos.DB_FILE
        govos.DB_FILE = self._tmp.name
        govos.init_database()
        # Reachability is stubbed: any URL containing "dead" is unreachable, else healthy.
        self._orig_check = govos._check_one_link
        govos._check_one_link = lambda url: {
            'url': url, 'status': 'UNREACHABLE' if 'dead' in url else 'HEALTHY',
            'httpCode': 0, 'checkedAt': 'now'}
        self.client = govos.app.test_client()

    def tearDown(self):
        govos._check_one_link = self._orig_check
        govos.DB_FILE = self._orig_db
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def _run(self, query='SSC CGL 2026 dates', exam_id='exam-ssc-cgl-2026'):
        conn = govos.get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO research_runs (query, mode, exam_id, answer, result_count) "
                    "VALUES (?,?,?,?,?)", (query, 'OFFICIAL', exam_id, '', 0))
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        return rid

    def _finding(self, run_id, url, snippet, trust='OFFICIAL', title='Notice'):
        conn = govos.get_db_connection()
        cur = conn.cursor()
        cur.execute("INSERT INTO research_findings (run_id, title, url, snippet, trust_level, "
                    "score, review_status) VALUES (?,?,?,?,?,?,?)",
                    (run_id, title, url, snippet, trust, 0.9, 'PENDING_REVIEW'))
        fid = cur.lastrowid
        conn.commit()
        conn.close()
        return fid

    def _extract(self, run_id=None, finding_id=None):
        body = {}
        if run_id:
            body['run_id'] = run_id
        if finding_id:
            body['finding_id'] = finding_id
        return self.client.post('/api/research/facts/extract', json=body)


class TestExtraction(_Base):
    def test_a_valid_fact_extraction(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/notice',
                      'The last date to apply is 15/07/2026 for all candidates.')
        r = self._extract(run_id=run).get_json()
        facts = {f['field']: f for f in r['facts']}
        self.assertIn('application_last_date', facts)
        f = facts['application_last_date']
        self.assertEqual(f['value'], '2026-07-15')
        self.assertEqual(f['valueType'], 'DATE')
        self.assertEqual(f['status'], 'validated')
        self.assertTrue(f['evidence'])            # evidence preserved
        self.assertEqual(f['sourceUrl'], 'https://ssc.gov.in/notice')

    def test_b_missing_value_is_not_a_fact(self):
        # A date-field cue fires but no date is present -> no fact (a gap is not a fact).
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/x', 'The date of examination will be announced later.')
        r = self._extract(run_id=run).get_json()
        self.assertNotIn('exam_date', {f['field'] for f in r['facts']})

    def test_c_uncertain_value_stays_pending_not_guessed(self):
        # A reachable source but a low-confidence TEXT value stays pending, never validated.
        run = self._run()
        self._finding(run, 'https://example.org/blog', 'Eligibility: graduation in any stream.',
                      trust='UNVERIFIED')
        r = self._extract(run_id=run).get_json()
        elig = next(f for f in r['facts'] if f['field'] == 'eligibility')
        self.assertEqual(elig['status'], 'pending')   # TEXT, confidence < 0.6

    def test_d_official_vs_non_official_source(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/a', 'Last date: 10/06/2026.', trust='OFFICIAL')
        self._finding(run, 'https://coaching.example/a', 'Last date: 10/06/2026.',
                      trust='UNVERIFIED')
        r = self._extract(run_id=run).get_json()
        by_src = {f['sourceType'] for f in r['facts'] if f['field'] == 'application_last_date'}
        self.assertIn('OFFICIAL', by_src)
        self.assertIn('LOW', by_src)


class TestValidationRules(_Base):
    def test_e_invalid_date_is_rejected(self):
        conn = govos.get_db_connection(); cur = conn.cursor()
        status, notes = govos._validate_fact(cur, {
            'field': 'exam_date', 'value_type': 'DATE', 'value': '2026-13-40',
            'source_url': 'https://ssc.gov.in/x', 'confidence': 0.7}, 'exam-x', {})
        conn.close()
        self.assertEqual(status, 'rejected')
        self.assertIn('date value did not parse', notes)

    def test_f_invalid_url_is_rejected(self):
        conn = govos.get_db_connection(); cur = conn.cursor()
        status, _ = govos._validate_fact(cur, {
            'field': 'notification', 'value_type': 'URL', 'value': 'not-a-url',
            'source_url': 'not-a-url', 'confidence': 0.7}, 'exam-x', {})
        conn.close()
        self.assertEqual(status, 'rejected')

    def test_g_missing_required_is_rejected(self):
        conn = govos.get_db_connection(); cur = conn.cursor()
        status, _ = govos._validate_fact(cur, {
            'field': 'vacancies', 'value_type': 'INTEGER', 'value': '',
            'source_url': 'https://ssc.gov.in/x', 'confidence': 0.9}, 'exam-x', {})
        conn.close()
        self.assertEqual(status, 'rejected')

    def test_h_duplicate_is_skipped(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/n', 'Last date: 15/07/2026.')
        first = self._extract(run_id=run).get_json()
        self.assertEqual(first['summary'].get('duplicate', 0), 0)
        again = self._extract(run_id=run).get_json()   # same finding, re-run
        self.assertGreaterEqual(again['summary'].get('duplicate', 0), 1)
        # no second copy stored
        listed = self.client.get('/api/research/facts?run_id=%d' % run).get_json()
        lasts = [f for f in listed['facts'] if f['field'] == 'application_last_date']
        self.assertEqual(len(lasts), 1)

    def test_i_unreachable_url_stays_pending(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/dead-notice', 'Last date: 15/07/2026.')
        r = self._extract(run_id=run).get_json()
        f = next(x for x in r['facts'] if x['field'] == 'application_last_date')
        self.assertEqual(f['status'], 'pending')   # good date, but source not reachable
        self.assertTrue(any('not reachable' in n for n in f['validationNotes']))


class TestConflict(_Base):
    def test_j_conflicting_sources_kept_both(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/a', 'The last date is 15/07/2026.')
        self._finding(run, 'https://pib.gov.in/b', 'The last date is 22/07/2026.', trust='OFFICIAL')
        r = self._extract(run_id=run).get_json()
        lasts = [f for f in r['facts'] if f['field'] == 'application_last_date']
        self.assertEqual(len(lasts), 2)                       # both kept
        listed = self.client.get('/api/research/facts?run_id=%d&status=conflicting' % run).get_json()
        conf = [f for f in listed['facts'] if f['field'] == 'application_last_date']
        self.assertEqual(len(conf), 2)                        # both conflicting
        groups = {f['conflictGroup'] for f in conf}
        self.assertEqual(len(groups), 1)                      # one shared group
        vals = {f['value'] for f in conf}
        self.assertEqual(vals, {'2026-07-15', '2026-07-22'})  # neither chosen

    def test_k_multiple_sources_same_value_not_conflict(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/a', 'The last date is 15/07/2026.')
        self._finding(run, 'https://pib.gov.in/b', 'The last date is 15/07/2026.', trust='OFFICIAL')
        r = self._extract(run_id=run).get_json()
        lasts = [f for f in r['facts'] if f['field'] == 'application_last_date']
        self.assertEqual(len(lasts), 2)                       # two sources, both kept
        self.assertTrue(all(f['status'] != 'conflicting' for f in lasts))


class TestHumanReview(_Base):
    def test_l_human_approval_and_rejection(self):
        run = self._run()
        self._finding(run, 'https://ssc.gov.in/n', 'Last date: 15/07/2026.')
        fid = self._extract(run_id=run).get_json()['facts'][0]['id']
        ok = self.client.post('/api/research/facts/%d/status' % fid, json={'status': 'approved'})
        self.assertEqual(ok.get_json()['newStatus'], 'approved')
        listed = self.client.get('/api/research/facts?run_id=%d' % run).get_json()
        row = next(f for f in listed['facts'] if f['id'] == fid)
        self.assertEqual(row['status'], 'approved')
        self.assertTrue(row['reviewedAt'])
        bad = self.client.post('/api/research/facts/%d/status' % fid, json={'status': 'nonsense'})
        self.assertEqual(bad.status_code, 400)

    def test_m_bad_target_is_404(self):
        self.assertEqual(self.client.post('/api/research/facts/9999/status',
                                          json={'status': 'approved'}).status_code, 404)


class TestExistingPipelineUntouched(_Base):
    def test_n_extract_does_not_touch_findings_or_promotion(self):
        run = self._run()
        fid = self._finding(run, 'https://ssc.gov.in/n', 'Last date: 15/07/2026.')
        # extracting facts must not change the finding's review_status...
        self._extract(run_id=run)
        conn = govos.get_db_connection()
        rev = conn.execute("SELECT review_status FROM research_findings WHERE id=?", (fid,)).fetchone()[0]
        # ...and must not have created any resource addition (the candidate-facing path).
        adds = conn.execute("SELECT COUNT(*) FROM resource_additions").fetchone()[0]
        conn.close()
        self.assertEqual(rev, 'PENDING_REVIEW')
        self.assertEqual(adds, 0)

    def test_o_existing_finding_promote_gate_still_works(self):
        run = self._run()
        fid = self._finding(run, 'https://ssc.gov.in/n', 'Last date: 15/07/2026.')
        res = self.client.post('/api/research/findings/%d/status' % fid, json={'status': 'PROMOTED'})
        self.assertEqual(res.get_json()['new_status'], 'PROMOTED')
        # approving a fact never auto-creates a candidate-facing addition
        conn = govos.get_db_connection()
        adds = conn.execute("SELECT COUNT(*) FROM resource_additions").fetchone()[0]
        conn.close()
        self.assertEqual(adds, 0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
