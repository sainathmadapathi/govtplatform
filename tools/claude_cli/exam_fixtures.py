"""Synthetic exams and temporary-file plumbing shared by the discovery / handler / context tests.

Nothing here is real exam data. The authority and exams are invented ("Example Commission",
"Sample Board"), so the tests cannot pass or fail because of what a real authority published, and
nothing here touches `govos.db`, `exam_data/` or the network.

    env = ExamEnv()            # a temp dir, a temp SQLite file with an `exam_registry` table,
                               # a temp authored-exams JSON file, and an `ExamStore` over both
    env.put_registry(exam_a())             # a machine-built (runtime registry) exam
    env.put_authored([exam_b()])           # an authored-register exam

`NoNetwork` records (and refuses) every socket-level attempt made while it is active, which is how
the tests prove a code path never reached a network or an HTTP client.
"""
from __future__ import annotations

import contextlib
import copy
import dataclasses
import http.client
import json
import os
import socket
import sqlite3
import tempfile
import unittest
from typing import Optional
from unittest import mock

from .context import ExamStore
from .handlers import AppHooks, default_specs
from .jobs import Job, JobQueue

REGISTRY_DDL = '''
    CREATE TABLE IF NOT EXISTS exam_registry (
        exam_id TEXT NOT NULL, cycle TEXT NOT NULL, version INTEGER NOT NULL DEFAULT 1,
        published INTEGER NOT NULL DEFAULT 0, retired INTEGER NOT NULL DEFAULT 0,
        exam_json TEXT NOT NULL, PRIMARY KEY (exam_id, cycle))'''

A_ID, B_ID, C_ID = 'exam-example-2031', 'exam-sample-2032', 'exam-empty-2033'
A_NOTICE_URL = 'https://notice.example-commission.gov.in/07-2031.pdf'
A_PORTAL = 'https://apply.example-commission.gov.in'
B_NOTICE_URL = 'https://jobs.sample-board.nic.in/notice-2032.pdf'
B_PORTAL = 'https://jobs.sample-board.nic.in/portal'


def prov(evidence_id: str, url: str, excerpt: str, page: int = 2, level: str = 'OFFICIALLY_VERIFIED') -> dict:
    # The record's own DataProvenance keys (src/types.ts), as every authored and runtime exam carries them;
    # the fixture used to say page/excerpt/sourceDocument, which no real record does.
    return {'documentTitle': 'Notice of Examination', 'officialUrl': url, 'pageNumber': page, 'clauseNumber': '',
            'excerptText': excerpt, 'taxonomyType': 'FACT', 'verificationLevel': level,
            'evidenceType': 'DIRECT', 'evidenceId': evidence_id}


def exam_a() -> dict:
    """The exam the tests ask about. Disjoint figures from `exam_b` (4217 / 21-30 / Rs 100 / 14 March)."""
    n = lambda eid, ex: prov(eid, A_NOTICE_URL, ex)
    return {
        'id': A_ID, 'code': 'EXAMPLE_AO_2031', 'cycle': '2031',
        'title': 'Example Commission Assistant Officer Examination 2031',
        'authorityName': 'Example Commission', 'vacanciesTotal': 4217,
        'factEvidence': {'vacanciesTotal': n('ev-a-vac', 'Total number of vacancies: 4217')},
        'crucialEligibilityDate': '2031-01-01',
        'overviewDescription': 'Recruitment of Assistant Officers by Example Commission.',
        'dates': [
            {'label': 'Last date to apply', 'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2031-03-14 18:00:00',
             'provenance': n('ev-a-close', 'The last date for submission of online applications is 14 March 2031')},
            {'label': 'Earlier last date', 'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2031-03-07 18:00:00',
             'status': 'SUPERSEDED', 'provenance': n('ev-a-old', 'extended')},
            {'label': 'Tier-I examination', 'type': 'EXAM', 'displayWhen': 'June 2031', 'isTentative': True,
             'provenance': n('ev-a-exam', 'Tier-I will be held in June 2031')},
        ],
        'eligibilityHighlights': [
            {'title': 'Age limit', 'body': 'Between 21 and 30 years on 1 January 2031.',
             'provenance': n('ev-a-age', 'between 21 and 30 years of age')}],
        'posts': [{'postName': 'Assistant Officer', 'minAge': 21, 'maxAge': 30, 'payLevel': 'Level 7',
                   'classification': 'Group B', 'provenance': n('ev-a-post', 'Assistant Officer, Level 7')}],
        'applicationGuide': {
            'fee': {'rules': [{'statedAs': 'Application fee is Rs. 100/-; women and SC/ST candidates are exempted.',
                               'provenance': n('ev-a-fee', 'Application fee: Rs. 100/-')}],
                    'acceptedModes': ['UPI', 'Net banking'], 'provenance': n('ev-a-fee-modes', 'UPI, Net banking')},
            'officialPortal': A_PORTAL},
        'stages': [{'stageName': 'Tier-I (objective)', 'mode': 'Computer based', 'totalMarks': 200,
                    'durationMinutes': 60, 'negativeMarking': '0.25 for each wrong answer',
                    'provenance': n('ev-a-stage', 'Tier-I 200 marks, 60 minutes')}],
        'syllabus': [
            {'id': 't-quant', 'topicName': 'Quantitative Aptitude', 'subject': 'Mathematics',
             'weightagePercentage': 25, 'isHighYield': True, 'officialProvenance': n('ev-a-syl-1', 'Quantitative Aptitude')},
            {'id': 't-reason', 'topicName': 'Logical Reasoning', 'subject': 'Reasoning',
             'weightagePercentage': 25, 'isHighYield': False, 'officialProvenance': n('ev-a-syl-2', 'Logical Reasoning')},
            {'id': 't-polity', 'topicName': 'Indian Polity', 'subject': 'General Awareness',
             'weightagePercentage': 10, 'isHighYield': False, 'officialProvenance': n('ev-a-syl-3', 'Indian Polity')}],
        'faqs': [{'question': 'Can I change my form after submission?',
                  'answer': 'A correction window of three days opens after the last date.',
                  'provenance': n('ev-a-faq', 'correction window')}],
        'corrigendums': [], 'admitCardEvents': [], 'resultDeclarations': [], 'examDayChecklist': [],
        'officialLinks': [{'title': 'Notice PDF', 'url': A_NOTICE_URL, 'note': 'The official notice'}],
        'cutoffsHistory': [],
    }


def exam_b() -> dict:
    """Another exam, with nothing in common with `exam_a` (figures, URLs, names, topics)."""
    n = lambda eid, ex: prov(eid, B_NOTICE_URL, ex, page=5)
    return {
        'id': B_ID, 'code': 'SAMPLE_JC_2032', 'cycle': '2032',
        'title': 'Sample Board Junior Clerk Examination 2032', 'authorityName': 'Sample Board',
        'vacanciesTotal': 953,
        'factEvidence': {'vacanciesTotal': n('ev-b-vac', 'Total vacancies: 953')},
        'overviewDescription': 'Recruitment of Junior Clerks by Sample Board.',
        'dates': [{'label': 'Last date to apply', 'type': 'APPLICATION_CLOSE', 'dateTimeStr': '2032-05-09 17:00:00',
                   'provenance': n('ev-b-close', 'last date is 9 May 2032')}],
        'eligibilityHighlights': [{'title': 'Age limit', 'body': 'Between 18 and 27 years.',
                                   'provenance': n('ev-b-age', '18 to 27 years')}],
        'posts': [{'postName': 'Junior Clerk', 'minAge': 18, 'maxAge': 27, 'payLevel': 'Level 2',
                   'provenance': n('ev-b-post', 'Junior Clerk')}],
        'applicationGuide': {'fee': {'rules': [{'statedAs': 'Application fee is Rs. 750/-.',
                                                'provenance': n('ev-b-fee', 'Rs. 750/-')}],
                                     'acceptedModes': ['Challan'], 'provenance': n('ev-b-fee-m', 'Challan')},
                             'officialPortal': B_PORTAL},
        'stages': [{'stageName': 'Written test', 'totalMarks': 150, 'durationMinutes': 90,
                    'provenance': n('ev-b-stage', 'Written test')}],
        'syllabus': [
            {'id': 'b-clerical', 'topicName': 'Clerical Aptitude', 'subject': 'Aptitude',
             'officialProvenance': n('ev-b-syl-1', 'Clerical Aptitude')},
            {'id': 'b-english', 'topicName': 'English Comprehension', 'subject': 'English',
             'officialProvenance': n('ev-b-syl-2', 'English Comprehension')}],
        'faqs': [], 'officialLinks': [{'title': 'Board portal', 'url': B_PORTAL, 'note': 'Apply here'}],
    }


def exam_empty() -> dict:
    """An exam with a record but no syllabus."""
    return {'id': C_ID, 'code': 'EMPTY_EX_2033', 'cycle': '2033', 'title': 'Empty Recruitment Test 2033',
            'authorityName': 'Empty Authority', 'syllabus': [], 'dates': []}


def clone(exam: dict) -> dict:
    return copy.deepcopy(exam)


class ExamEnv:
    """A temp directory holding a SQLite file (with an `exam_registry` table) and an authored JSON."""

    def __init__(self) -> None:
        self._dir = tempfile.TemporaryDirectory(prefix='govos-claude-test-')
        self.dir = self._dir.name
        self.db_path = os.path.join(self.dir, 'test.db')
        self.authored_path = os.path.join(self.dir, 'authored_exams.json')
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(REGISTRY_DDL)
            conn.commit()
        finally:
            conn.close()
        self.store = ExamStore(self.db_path, self.authored_path)

    def close(self) -> None:
        self._dir.cleanup()

    def put_registry(self, exam: dict, *, cycle: Optional[str] = None, version: int = 1, published: int = 1,
                     retired: int = 0, raw_json: Optional[str] = None) -> None:
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute('INSERT OR REPLACE INTO exam_registry (exam_id, cycle, version, published, retired, exam_json) '
                         'VALUES (?,?,?,?,?,?)',
                         (exam['id'], cycle or str(exam.get('cycle') or '2031'), version, published, retired,
                          raw_json if raw_json is not None else json.dumps(exam)))
            conn.commit()
        finally:
            conn.close()

    def put_authored(self, exams: list) -> None:
        with open(self.authored_path, 'w', encoding='utf-8') as fh:
            json.dump(exams, fh)

    def registry_rows(self) -> int:
        conn = sqlite3.connect(self.db_path)
        try:
            return conn.execute('SELECT COUNT(*) FROM exam_registry').fetchone()[0]
        finally:
            conn.close()


class NoNetwork:
    """While active, every attempt to resolve a name or open a socket is recorded and refused."""

    def __init__(self) -> None:
        self.attempts: list = []
        self._stack = contextlib.ExitStack()

    def _refuse(self, what: str):
        def refuse(*args, **kwargs):
            self.attempts.append((what, args[:1]))
            raise OSError(f'network is disabled in tests ({what})')
        return refuse

    def __enter__(self) -> 'NoNetwork':
        for target, name in ((socket, 'getaddrinfo'), (socket, 'create_connection'),
                             (socket.socket, 'connect'), (http.client.HTTPConnection, 'connect')):
            self._stack.enter_context(mock.patch.object(target, name, self._refuse(name)))
        return self

    def __exit__(self, *exc) -> None:
        self._stack.close()


class ExamTestCase(unittest.TestCase):
    """A TestCase with a temp `ExamEnv` (exam A in the runtime registry, exam B authored) and a
    network guard that fails the test if anything tried to reach the network."""

    def setUp(self) -> None:
        super().setUp()
        self.env = ExamEnv()
        self.addCleanup(self.env.close)
        self.env.put_registry(exam_a())
        self.env.put_authored([exam_b(), exam_empty()])
        self.net = NoNetwork()
        self.net.__enter__()
        self.addCleanup(self._check_network)

    def _check_network(self) -> None:
        self.net.__exit__(None, None, None)
        self.assertEqual(self.net.attempts, [], 'the test reached for the network')


def make_hooks(env: ExamEnv, gateway, **kw) -> AppHooks:
    """Hooks over the temp exam store and a scripted gateway; extra hooks come in as keywords."""
    return AppHooks(exam_store=env.store, gateway=gateway, **kw)


def run_job(env: ExamEnv, operation: str, payload: dict, hooks: AppHooks, *, role: str = 'admin',
            exam_id: str = '', max_retries: int = 0) -> Job:
    """Create one job through the real normaliser and queue store, run it in THIS thread (no worker
    threads), and return the finished row. A job that fails transiently is not retried unless asked."""
    spec = dataclasses.replace(default_specs()[operation], max_retries=max_retries)
    queue = JobQueue(env.db_path, {operation: spec}, hooks, workers=1)
    job, _, _ = queue.store.create(spec, spec.normalize(payload), exam_id=exam_id, cycle='',
                                   requested_by='test', role=role)
    queue.run_pending()
    return queue.store.get(job.id)
