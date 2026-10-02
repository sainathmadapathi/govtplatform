"""A verifier-added resource belongs to ONE exam and is labelled by what its host really is.

Two defects in the original mechanism, found when a third-party TGPSC paper list was to be added:

  * additions had no exam: every addition appeared in every exam's library, so a TGPSC link would have shown
    up under SSC and UPSC (and so did three test entries);
  * the library badged every addition OFFICIALLY_VERIFIED, which would have been false for a coaching portal.

The server now stores the exam, requires one on every new addition, filters the list per exam, and derives the
source kind (OFFICIAL / TRUSTED_PUBLIC / THIRD_PARTY) from the URL's host on every read, so a client can not
claim a coaching site is official.

Run: python -m unittest test_resource_additions
"""
import os
import sqlite3
import tempfile
import unittest

import app as govos

SSC = 'exam-ssc-cgl-2026'
TGPSC = 'exam-websitenew-tgpsc-group-i-2024'
MANABADI = 'https://www.manabadi.co.in/sourceview/questionpaperlist.aspx?sourceid=1550'
OFFICIAL_PAGE = 'https://websitenew.tgpsc.gov.in/oldquestionp.jsp'


class _Base(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self._tmp.close()
        self._orig_db = govos.DB_FILE
        govos.DB_FILE = self._tmp.name
        govos.init_database()
        self._orig_check = govos._check_one_link
        govos._check_one_link = lambda url: {'url': url, 'status': 'HEALTHY', 'httpCode': 200, 'checkedAt': 'now'}
        self.client = govos.app.test_client()

    def tearDown(self):
        govos._check_one_link = self._orig_check
        govos.DB_FILE = self._orig_db
        try:
            os.unlink(self._tmp.name)
        except OSError:
            pass

    def add(self, body, **kw):
        return self.client.post('/api/resources/additions', json=body, **kw)

    def listed(self, exam_id=None):
        path = '/api/resources/additions' + ('?exam_id=' + exam_id if exam_id else '')
        return self.client.get(path).get_json()['additions']


class TestAnAdditionBelongsToOneExam(_Base):

    def test_an_addition_without_an_exam_is_refused(self):
        r = self.add({'title': 'x', 'url': 'https://example.org/a'})
        self.assertEqual(r.status_code, 400)
        self.assertIn('examId', r.get_json()['error'])
        self.assertEqual(self.listed(), [])

    def test_a_malformed_exam_id_is_refused(self):
        for bad in ('../../etc', 'exam id with spaces', 'x' * 200, "'; DROP TABLE users;--"):
            with self.subTest(bad=bad):
                self.assertEqual(self.add({'title': 'x', 'url': 'https://example.org/a', 'examId': bad}).status_code, 400)

    def test_the_list_is_filtered_by_exam_so_one_exams_link_never_reaches_another(self):
        self.add({'title': 'TGPSC list', 'url': MANABADI, 'examId': TGPSC})
        self.add({'title': 'SSC notice', 'url': 'https://ssc.gov.in/n.pdf', 'examId': SSC})
        self.assertEqual([a['title'] for a in self.listed(TGPSC)], ['TGPSC list'])
        self.assertEqual([a['title'] for a in self.listed(SSC)], ['SSC notice'])
        self.assertEqual(self.listed('exam-upsc-cse-2026'), [])
        self.assertEqual(len(self.listed()), 2, 'without a filter the Trust Panel sees all of them')

    def test_the_exam_is_returned_with_each_addition(self):
        self.add({'title': 'x', 'url': MANABADI, 'examId': TGPSC})
        self.assertEqual(self.listed()[0]['examId'], TGPSC)

    def test_posting_still_needs_the_admin_guard(self):
        r = self.add({'title': 'x', 'url': MANABADI, 'examId': TGPSC}, environ_overrides={'REMOTE_ADDR': '203.0.113.9'})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.listed(), [])


class TestTheSourceKindIsTheServersOwn(_Base):

    def test_a_coaching_portal_is_a_third_party_link_never_official(self):
        added = self.add({'title': 'Papers', 'url': MANABADI, 'examId': TGPSC}).get_json()['addition']
        self.assertEqual(added['sourceKind'], 'THIRD_PARTY')
        self.assertEqual(added['resourceFormat'], 'EXTERNAL_PAGE', 'not filed as an official portal')
        self.assertIn('not an official source', added['description'])
        self.assertNotIn('official-domain search', added['description'])

    def test_a_client_can_not_claim_a_third_party_page_is_official(self):
        added = self.add({'title': 'Papers', 'url': MANABADI, 'examId': TGPSC, 'resourceFormat': 'OFFICIAL_PORTAL',
                          'sourceKind': 'OFFICIAL', 'officialSource': True}).get_json()['addition']
        self.assertEqual(added['sourceKind'], 'THIRD_PARTY')
        self.assertEqual(added['resourceFormat'], 'EXTERNAL_PAGE')

    def test_lookalike_hosts_are_third_party(self):
        for url in ('https://tgpsc.gov.in.evil.example/p', 'https://gov.in.attacker.net/x',
                    'https://www.tgpsc-papers.com/p', 'https://example.gov/p'):
            with self.subTest(url=url):
                added = self.add({'title': 't', 'url': url, 'examId': TGPSC}).get_json()['addition']
                self.assertEqual(added['sourceKind'], 'THIRD_PARTY')

    def test_an_official_host_is_official_and_keeps_the_portal_format(self):
        added = self.add({'title': 'Old papers', 'url': OFFICIAL_PAGE, 'examId': TGPSC}).get_json()['addition']
        self.assertEqual((added['sourceKind'], added['resourceFormat']), ('OFFICIAL', 'OFFICIAL_PORTAL'))
        self.assertIn('official-domain search', added['description'])

    def test_a_pdf_on_an_official_host_is_a_direct_pdf(self):
        added = self.add({'title': 'n', 'url': 'https://ssc.gov.in/n.pdf', 'examId': SSC}).get_json()['addition']
        self.assertEqual((added['sourceKind'], added['resourceFormat']), ('OFFICIAL', 'DIRECT_PDF'))

    def test_an_academic_host_is_trusted_public_not_official(self):
        added = self.add({'title': 'n', 'url': 'https://nptel.ac.in/courses', 'examId': SSC}).get_json()['addition']
        self.assertEqual(added['sourceKind'], 'TRUSTED_PUBLIC')

    def test_the_source_kind_is_recomputed_on_read_and_never_stored(self):
        self.add({'title': 'Papers', 'url': MANABADI, 'examId': TGPSC})
        columns = [r[1] for r in sqlite3.connect(self._tmp.name).execute('PRAGMA table_info(resource_additions)')]
        self.assertNotIn('source_kind', columns)
        self.assertEqual(self.listed(TGPSC)[0]['sourceKind'], 'THIRD_PARTY')

    def test_a_caller_supplied_description_is_kept_and_is_what_candidates_read(self):
        text = 'Third-party list; none of these is the Group-I 02/2024 paper.'
        added = self.add({'title': 'Papers', 'url': MANABADI, 'examId': TGPSC, 'description': text}).get_json()['addition']
        self.assertEqual(added['description'], text)


class TestTheMigration(unittest.TestCase):

    def test_legacy_additions_without_an_exam_stay_with_ssc_and_nothing_is_lost(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        orig = govos.DB_FILE
        try:
            conn = sqlite3.connect(path)
            conn.execute("""CREATE TABLE resource_additions (id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT NOT NULL,
                            subject TEXT NOT NULL, resource_format TEXT NOT NULL, author TEXT, description TEXT,
                            added_at TEXT NOT NULL, added_from TEXT NOT NULL, finding_id INTEGER,
                            retired INTEGER NOT NULL DEFAULT 0)""")
            conn.execute("INSERT INTO resource_additions VALUES ('add-1','Old SSC notice','https://ssc.gov.in/n.pdf',"
                         "'Official Gazette','DIRECT_PDF','ssc.gov.in','d','2026-05-01','LIVE_RESEARCH',7,0)")
            conn.commit()
            conn.close()
            govos.DB_FILE = path
            govos.init_database()
            govos.init_database()                                   # idempotent
            conn = sqlite3.connect(path)
            rows = conn.execute('SELECT id, title, exam_id, finding_id FROM resource_additions').fetchall()
            conn.close()
            self.assertEqual(rows, [('add-1', 'Old SSC notice', SSC, 7)])
        finally:
            govos.DB_FILE = orig
            os.unlink(path)


if __name__ == '__main__':
    unittest.main()
