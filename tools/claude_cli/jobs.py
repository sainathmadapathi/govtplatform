"""A persistent, bounded job queue for Claude work.

Long Claude operations never run inside a Flask request. A request creates a job row; a small
pool of worker threads (at most `GOVOS_CLAUDE_MAX_CONCURRENCY`) claims and runs it; the client
polls for its status. The queue is SQLite-backed, so jobs survive a restart.

Properties, all tested:

  * identical ACTIVE jobs from one requester are deduplicated by input fingerprint;
  * two builds of the same exam and cycle never run at once (`exclusive_key`);
  * cancellation: a queued job is cancelled immediately; a running job has its cancel event set,
    which the gateway honours by killing the CLI process tree, and a cancelled build registers
    nothing;
  * bounded retries, for transient infrastructure failure only (timeout, busy, CLI failure) with
    backoff. A malformed or schema-rejected reply is a verdict on that reply and is never retried;
  * stale RUNNING jobs (no heartbeat, e.g. after a crash) are recovered, never silently lost;
  * a finished job is never an automatic publication: nothing here writes a fact. Handlers
    return results; anything that changes canonical information goes through the existing gate
    and human review;
  * candidate jobs are readable only with the per-job token returned at creation, and their
    input and result are purged after a day.
"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional

from .audit import now_iso
from .client import get_gateway, job_scope
from .schemas import fingerprint
from .security import hash_token, new_job_token, token_matches

STALE_SECONDS = 90.0
HEARTBEAT_SECONDS = 15.0
CANDIDATE_RETENTION_SECONDS = 24 * 3600
MAX_QUEUED_CANDIDATE_JOBS = 20
MAX_QUEUED_JOBS = 200


class JobStatus(str, Enum):
    QUEUED = 'QUEUED'
    RUNNING = 'RUNNING'
    SUCCEEDED = 'SUCCEEDED'
    FAILED = 'FAILED'
    CANCELLED = 'CANCELLED'

    @property
    def terminal(self) -> bool:
        return self in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED)


class QueueFull(RuntimeError):
    pass


def init_job_tables(conn: sqlite3.Connection) -> None:
    """Idempotent. Called from the app's database initialisation."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS claude_jobs (
            id TEXT PRIMARY KEY,
            operation TEXT NOT NULL,
            exam_id TEXT DEFAULT '',
            cycle TEXT DEFAULT '',
            requested_by TEXT DEFAULT '',
            role TEXT NOT NULL DEFAULT 'admin',
            input_json TEXT NOT NULL DEFAULT '{}',
            input_fingerprint TEXT NOT NULL,
            dedupe_key TEXT NOT NULL,
            exclusive_key TEXT DEFAULT '',
            status TEXT NOT NULL DEFAULT 'QUEUED',
            stage TEXT DEFAULT '',
            result_json TEXT,
            error_category TEXT DEFAULT '',
            error_message TEXT DEFAULT '',
            template_version TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            started_at TEXT DEFAULT '',
            finished_at TEXT DEFAULT '',
            retry_count INTEGER NOT NULL DEFAULT 0,
            max_retries INTEGER NOT NULL DEFAULT 0,
            cancel_requested INTEGER NOT NULL DEFAULT 0,
            evidence_links_json TEXT DEFAULT '[]',
            audit_json TEXT DEFAULT '{}',
            access_hashes_json TEXT DEFAULT '[]',
            worker_id TEXT DEFAULT '',
            heartbeat_at REAL DEFAULT 0,
            not_before REAL DEFAULT 0,
            created_epoch REAL NOT NULL DEFAULT 0
        )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_claude_jobs_status ON claude_jobs(status, created_epoch)')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_claude_jobs_dedupe ON claude_jobs(dedupe_key, status)')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS claude_job_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL, ts TEXT NOT NULL, event TEXT NOT NULL, detail TEXT DEFAULT ''
        )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_claude_job_events_job ON claude_job_events(job_id)')


# ------------------------------------------------------------------------------- data
@dataclass
class Job:
    id: str
    operation: str
    exam_id: str = ''
    cycle: str = ''
    requested_by: str = ''
    role: str = 'admin'
    input: dict = field(default_factory=dict)
    input_fingerprint: str = ''
    dedupe_key: str = ''
    exclusive_key: str = ''
    status: JobStatus = JobStatus.QUEUED
    stage: str = ''
    result: Optional[dict] = None
    error_category: str = ''
    error_message: str = ''
    template_version: str = ''
    created_at: str = ''
    started_at: str = ''
    finished_at: str = ''
    retry_count: int = 0
    max_retries: int = 0
    cancel_requested: bool = False
    evidence_links: list = field(default_factory=list)
    audit: dict = field(default_factory=dict)
    access_hashes: list = field(default_factory=list)
    worker_id: str = ''
    heartbeat_at: float = 0.0

    def as_dict(self, *, include_input: bool = True) -> dict:
        """The safe public view. Never includes access hashes or worker identity."""
        out = {'jobId': self.id, 'operation': self.operation, 'examId': self.exam_id, 'cycle': self.cycle,
               'status': self.status.value, 'stage': self.stage, 'result': self.result,
               'errorCategory': self.error_category, 'errorMessage': self.error_message,
               'templateVersion': self.template_version, 'createdAt': self.created_at,
               'startedAt': self.started_at, 'finishedAt': self.finished_at,
               'retryCount': self.retry_count, 'maxRetries': self.max_retries,
               'cancelRequested': self.cancel_requested, 'evidenceLinks': self.evidence_links,
               'audit': self.audit, 'inputFingerprint': self.input_fingerprint,
               'requestedBy': self.requested_by, 'role': self.role}
        if include_input:
            out['input'] = self.input
        return out


@dataclass
class JobOutcome:
    """What a handler returns. `status` is SUCCEEDED, FAILED or CANCELLED."""

    status: str = 'SUCCEEDED'
    result: Optional[dict] = None
    error_category: str = ''
    error_message: str = ''
    retryable: bool = False
    evidence_links: list = field(default_factory=list)
    template_version: str = ''
    audit: dict = field(default_factory=dict)


class JobContext:
    def __init__(self, job: Job, db_path: str, cancel_event: threading.Event, hooks: Any, store: 'JobStore'):
        self.job = job
        self.db_path = db_path
        self.cancel_event = cancel_event
        self.hooks = hooks
        self._store = store

    def stage(self, name: str) -> None:
        self._store.set_stage(self.job.id, name)

    @property
    def cancelled(self) -> bool:
        return self.cancel_event.is_set()


@dataclass
class JobSpec:
    name: str
    handler: Callable[[JobContext], JobOutcome]
    #: input dict -> sanitised input dict (raises ValueError with a safe message when invalid).
    normalize: Callable[[dict], dict]
    #: True when a candidate (not just an admin) may create this job.
    candidate: bool = False
    max_retries: int = 2
    #: (normalised input, exam_id, cycle) -> key that at most one RUNNING job may hold, or ''.
    exclusive: Optional[Callable[[dict, str, str], str]] = None


# ------------------------------------------------------------------------------- store
def _row_to_job(r: sqlite3.Row) -> Job:
    def loads(text, default):
        try:
            return json.loads(text) if text else default
        except (TypeError, ValueError):
            return default
    return Job(
        id=r['id'], operation=r['operation'], exam_id=r['exam_id'] or '', cycle=r['cycle'] or '',
        requested_by=r['requested_by'] or '', role=r['role'], input=loads(r['input_json'], {}),
        input_fingerprint=r['input_fingerprint'], dedupe_key=r['dedupe_key'],
        exclusive_key=r['exclusive_key'] or '', status=JobStatus(r['status']), stage=r['stage'] or '',
        result=loads(r['result_json'], None), error_category=r['error_category'] or '',
        error_message=r['error_message'] or '', template_version=r['template_version'] or '',
        created_at=r['created_at'], started_at=r['started_at'] or '', finished_at=r['finished_at'] or '',
        retry_count=r['retry_count'], max_retries=r['max_retries'], cancel_requested=bool(r['cancel_requested']),
        evidence_links=loads(r['evidence_links_json'], []), audit=loads(r['audit_json'], {}),
        access_hashes=loads(r['access_hashes_json'], []), worker_id=r['worker_id'] or '',
        heartbeat_at=r['heartbeat_at'] or 0.0)


class JobStore:
    def __init__(self, db_path: str, clock=time.time) -> None:
        self.db_path = db_path
        self._clock = clock
        conn = self._conn()
        try:
            init_job_tables(conn)
            conn.commit()
        finally:
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30, isolation_level=None)
        conn.row_factory = sqlite3.Row
        return conn

    def _event(self, conn: sqlite3.Connection, job_id: str, event: str, detail: str = '') -> None:
        conn.execute('INSERT INTO claude_job_events (job_id, ts, event, detail) VALUES (?,?,?,?)',
                     (job_id, now_iso(), event, detail[:300]))

    # ---------------------------------------------------------------------- create
    def create(self, spec: JobSpec, normalized: dict, *, exam_id: str, cycle: str, requested_by: str,
               role: str) -> tuple[Job, bool, str]:
        """(job, deduplicated, access token). The token is returned only here; only its hash is
        stored. A deduplicated call gets the existing job and a fresh token for it."""
        fp = fingerprint({'op': spec.name, 'exam': exam_id, 'cycle': cycle, 'input': normalized})
        dedupe = fingerprint({'fp': fp, 'by': requested_by, 'role': role})
        exclusive = spec.exclusive(normalized, exam_id, cycle) if spec.exclusive else ''
        token = new_job_token() if role == 'candidate' else ''
        conn = self._conn()
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute(
                "SELECT * FROM claude_jobs WHERE dedupe_key=? AND status IN ('QUEUED','RUNNING') "
                'ORDER BY created_epoch LIMIT 1', (dedupe,)).fetchone()
            if row is not None:
                job = _row_to_job(row)
                if token:
                    hashes = job.access_hashes + [hash_token(token)]
                    conn.execute('UPDATE claude_jobs SET access_hashes_json=? WHERE id=?',
                                 (json.dumps(hashes), job.id))
                self._event(conn, job.id, 'DEDUPLICATED', f'requested by {requested_by}')
                conn.execute('COMMIT')
                return job, True, token
            queued = conn.execute("SELECT COUNT(*) FROM claude_jobs WHERE status='QUEUED'").fetchone()[0]
            if queued >= MAX_QUEUED_JOBS:
                conn.execute('ROLLBACK')
                raise QueueFull('the job queue is full')
            if role == 'candidate':
                cq = conn.execute("SELECT COUNT(*) FROM claude_jobs WHERE status='QUEUED' AND role='candidate'").fetchone()[0]
                if cq >= MAX_QUEUED_CANDIDATE_JOBS:
                    conn.execute('ROLLBACK')
                    raise QueueFull('too many candidate requests are waiting')
            job_id = uuid.uuid4().hex
            now = self._clock()
            conn.execute(
                'INSERT INTO claude_jobs (id, operation, exam_id, cycle, requested_by, role, input_json, '
                'input_fingerprint, dedupe_key, exclusive_key, status, created_at, max_retries, '
                'access_hashes_json, created_epoch) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',
                (job_id, spec.name, exam_id, cycle, requested_by, role, json.dumps(normalized, ensure_ascii=False),
                 fp, dedupe, exclusive, 'QUEUED', now_iso(), spec.max_retries,
                 json.dumps([hash_token(token)] if token else []), now))
            self._event(conn, job_id, 'CREATED', f'{spec.name} by {requested_by or "?"} ({role})')
            row = conn.execute('SELECT * FROM claude_jobs WHERE id=?', (job_id,)).fetchone()
            conn.execute('COMMIT')
            return _row_to_job(row), False, token
        except sqlite3.Error:
            try:
                conn.execute('ROLLBACK')
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()

    # ------------------------------------------------------------------------ read
    def get(self, job_id: str) -> Optional[Job]:
        conn = self._conn()
        try:
            row = conn.execute('SELECT * FROM claude_jobs WHERE id=?', (job_id,)).fetchone()
            return _row_to_job(row) if row else None
        finally:
            conn.close()

    def list(self, *, limit: int = 30, status: str = '', operation: str = '') -> list:
        clauses, params = [], []
        if status:
            clauses.append('status=?')
            params.append(status)
        if operation:
            clauses.append('operation=?')
            params.append(operation)
        where = ('WHERE ' + ' AND '.join(clauses)) if clauses else ''
        conn = self._conn()
        try:
            rows = conn.execute(f'SELECT * FROM claude_jobs {where} ORDER BY created_epoch DESC LIMIT ?',
                                params + [max(1, min(limit, 100))]).fetchall()
            return [_row_to_job(r) for r in rows]
        finally:
            conn.close()

    def events(self, job_id: str) -> list:
        conn = self._conn()
        try:
            return [dict(r) for r in conn.execute(
                'SELECT ts, event, detail FROM claude_job_events WHERE job_id=? ORDER BY id', (job_id,))]
        finally:
            conn.close()

    def can_read(self, job: Job, token: str, *, admin: bool) -> bool:
        if admin:
            return True
        return any(token_matches(token, h) for h in job.access_hashes)

    # ----------------------------------------------------------------------- claim
    def claim_next(self, worker_id: str) -> Optional[Job]:
        now = self._clock()
        conn = self._conn()
        try:
            conn.execute('BEGIN IMMEDIATE')
            running = {r[0] for r in conn.execute(
                "SELECT exclusive_key FROM claude_jobs WHERE status='RUNNING' AND exclusive_key != ''")}
            rows = conn.execute(
                "SELECT * FROM claude_jobs WHERE status='QUEUED' AND not_before <= ? "
                'ORDER BY created_epoch LIMIT 50', (now,)).fetchall()
            chosen = None
            for r in rows:
                if r['exclusive_key'] and r['exclusive_key'] in running:
                    continue
                chosen = r
                break
            if chosen is None:
                conn.execute('COMMIT')
                return None
            conn.execute("UPDATE claude_jobs SET status='RUNNING', started_at=?, worker_id=?, heartbeat_at=?, "
                         "stage='STARTING' WHERE id=?", (now_iso(), worker_id, now, chosen['id']))
            self._event(conn, chosen['id'], 'STARTED', f'attempt {chosen["retry_count"] + 1}')
            row = conn.execute('SELECT * FROM claude_jobs WHERE id=?', (chosen['id'],)).fetchone()
            conn.execute('COMMIT')
            return _row_to_job(row)
        except sqlite3.Error:
            try:
                conn.execute('ROLLBACK')
            except sqlite3.Error:
                pass
            raise
        finally:
            conn.close()

    # --------------------------------------------------------------------- updates
    def set_stage(self, job_id: str, stage: str) -> None:
        conn = self._conn()
        try:
            conn.execute('UPDATE claude_jobs SET stage=?, heartbeat_at=? WHERE id=? AND status=\'RUNNING\'',
                         (stage[:60], self._clock(), job_id))
        finally:
            conn.close()

    def heartbeat(self, worker_id: str) -> list:
        """Refresh this worker's running jobs; return the ids that have a cancel request."""
        conn = self._conn()
        try:
            conn.execute("UPDATE claude_jobs SET heartbeat_at=? WHERE status='RUNNING' AND worker_id=?",
                         (self._clock(), worker_id))
            return [r[0] for r in conn.execute(
                "SELECT id FROM claude_jobs WHERE status='RUNNING' AND worker_id=? AND cancel_requested=1",
                (worker_id,))]
        finally:
            conn.close()

    def finish(self, job: Job, outcome: JobOutcome, *, status: JobStatus) -> None:
        conn = self._conn()
        try:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute(
                'UPDATE claude_jobs SET status=?, result_json=?, error_category=?, error_message=?, '
                'template_version=?, finished_at=?, evidence_links_json=?, audit_json=?, stage=? WHERE id=?',
                (status.value, json.dumps(outcome.result, ensure_ascii=False) if outcome.result is not None else None,
                 outcome.error_category, outcome.error_message[:300], outcome.template_version, now_iso(),
                 json.dumps(outcome.evidence_links), json.dumps(outcome.audit), status.value, job.id))
            self._event(conn, job.id, status.value, outcome.error_category)
            conn.execute('COMMIT')
        finally:
            conn.close()

    def requeue(self, job: Job, delay: float, reason: str) -> None:
        conn = self._conn()
        try:
            conn.execute('BEGIN IMMEDIATE')
            conn.execute("UPDATE claude_jobs SET status='QUEUED', retry_count=retry_count+1, not_before=?, "
                         "stage='', worker_id='' WHERE id=?", (self._clock() + delay, job.id))
            self._event(conn, job.id, 'RETRY_SCHEDULED', reason)
            conn.execute('COMMIT')
        finally:
            conn.close()

    def request_cancel(self, job_id: str) -> Optional[Job]:
        """Cancel a queued job now; flag a running one (the worker kills its CLI process)."""
        conn = self._conn()
        try:
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT * FROM claude_jobs WHERE id=?', (job_id,)).fetchone()
            if row is None:
                conn.execute('ROLLBACK')
                return None
            if row['status'] == 'QUEUED':
                conn.execute("UPDATE claude_jobs SET status='CANCELLED', cancel_requested=1, finished_at=?, "
                             "error_category='CANCELLED', stage='CANCELLED' WHERE id=?", (now_iso(), job_id))
                self._event(conn, job_id, 'CANCELLED', 'while queued')
            elif row['status'] == 'RUNNING':
                conn.execute('UPDATE claude_jobs SET cancel_requested=1 WHERE id=?', (job_id,))
                self._event(conn, job_id, 'CANCEL_REQUESTED', '')
            row = conn.execute('SELECT * FROM claude_jobs WHERE id=?', (job_id,)).fetchone()
            conn.execute('COMMIT')
            return _row_to_job(row)
        finally:
            conn.close()

    # ------------------------------------------------------------------ housekeeping
    def recover_stale(self, *, stale_after: float = STALE_SECONDS) -> int:
        """RUNNING jobs whose worker stopped heartbeating are re-queued (within their retry
        budget) or failed as INTERRUPTED. Nothing is silently dropped."""
        cutoff = self._clock() - stale_after
        conn = self._conn()
        n = 0
        try:
            conn.execute('BEGIN IMMEDIATE')
            for r in conn.execute("SELECT * FROM claude_jobs WHERE status='RUNNING' AND heartbeat_at < ?",
                                  (cutoff,)).fetchall():
                if r['retry_count'] < r['max_retries'] and not r['cancel_requested']:
                    conn.execute("UPDATE claude_jobs SET status='QUEUED', retry_count=retry_count+1, "
                                 "worker_id='', stage='', not_before=0 WHERE id=?", (r['id'],))
                    self._event(conn, r['id'], 'RECOVERED', 'worker stopped; re-queued')
                else:
                    status = 'CANCELLED' if r['cancel_requested'] else 'FAILED'
                    conn.execute("UPDATE claude_jobs SET status=?, finished_at=?, error_category='INTERRUPTED', "
                                 "error_message='The worker stopped before the job finished.' WHERE id=?",
                                 (status, now_iso(), r['id']))
                    self._event(conn, r['id'], status, 'interrupted')
                n += 1
            conn.execute('COMMIT')
        finally:
            conn.close()
        return n

    def purge_candidate_data(self, *, older_than: float = CANDIDATE_RETENTION_SECONDS) -> int:
        """Candidate questions and answers are not kept: input and result are cleared a day after
        the job finished. The row (status, timings, fingerprints) stays for the audit trail."""
        cutoff = self._clock() - older_than
        conn = self._conn()
        try:
            cur = conn.execute(
                "UPDATE claude_jobs SET input_json='{}', result_json=NULL WHERE role='candidate' "
                "AND status IN ('SUCCEEDED','FAILED','CANCELLED') AND created_epoch < ? AND "
                "(input_json != '{}' OR result_json IS NOT NULL)", (cutoff,))
            return cur.rowcount or 0
        finally:
            conn.close()

    def counts(self) -> dict:
        conn = self._conn()
        try:
            return {r[0]: r[1] for r in conn.execute('SELECT status, COUNT(*) FROM claude_jobs GROUP BY status')}
        finally:
            conn.close()


# ------------------------------------------------------------------------------- queue
RETRY_BACKOFF_SECONDS = (5.0, 20.0, 60.0)


class JobQueue:
    def __init__(self, db_path: str, specs: dict, hooks: Any = None, *, workers: Optional[int] = None,
                 clock=time.time) -> None:
        self.store = JobStore(db_path, clock=clock)
        self.specs = specs
        self.hooks = hooks
        self.db_path = db_path
        self._workers_wanted = workers
        self._threads: list = []
        self._stop = threading.Event()
        self._wake = threading.Event()
        self._cancels: dict = {}
        self._lock = threading.Lock()
        self.worker_id = f'w-{uuid.uuid4().hex[:10]}'
        self._clock = clock
        self._started = False

    # ----------------------------------------------------------------------- submit
    def submit(self, operation: str, payload: dict, *, exam_id: str = '', cycle: str = '',
               requested_by: str = '', role: str = 'admin') -> tuple[Job, bool, str]:
        spec = self.specs.get(operation)
        if spec is None:
            raise ValueError('unknown operation')
        if role == 'candidate' and not spec.candidate:
            raise PermissionError('this operation is not available to candidates')
        normalized = spec.normalize(payload if isinstance(payload, dict) else {})
        job, dup, token = self.store.create(spec, normalized, exam_id=exam_id, cycle=cycle,
                                            requested_by=requested_by, role=role)
        self.ensure_started()
        self._wake.set()
        return job, dup, token

    # ---------------------------------------------------------------------- workers
    def _worker_count(self) -> int:
        if self._workers_wanted:
            return max(1, self._workers_wanted)
        from .config import load_config
        return load_config().max_concurrency

    def ensure_started(self) -> None:
        with self._lock:
            if self._started:
                return
            self._started = True
            self._stop.clear()
            self.store.recover_stale()
            for i in range(self._worker_count()):
                t = threading.Thread(target=self._loop, name=f'claude-job-worker-{i}', daemon=True)
                t.start()
                self._threads.append(t)
            h = threading.Thread(target=self._housekeeping, name='claude-job-housekeeping', daemon=True)
            h.start()
            self._threads.append(h)

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        for t in self._threads:
            t.join(timeout=timeout)
        with self._lock:
            self._threads.clear()
            self._started = False

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                job = self.store.claim_next(self.worker_id)
            except sqlite3.Error:
                time.sleep(1.0)
                continue
            if job is None:
                self._wake.wait(timeout=1.0)
                self._wake.clear()
                continue
            self._execute(job)

    def _housekeeping(self) -> None:
        last_purge = 0.0
        while not self._stop.wait(HEARTBEAT_SECONDS):
            try:
                for job_id in self.store.heartbeat(self.worker_id):
                    ev = self._cancels.get(job_id)
                    if ev is not None:
                        ev.set()
                self.store.recover_stale()
                if self._clock() - last_purge > 600:
                    self.store.purge_candidate_data()
                    last_purge = self._clock()
            except sqlite3.Error:
                pass

    def cancel(self, job_id: str) -> Optional[Job]:
        """Cancel a job now. A queued job is cancelled at once; for one running in THIS process the cancel
        event is set immediately, so its CLI process tree is killed without waiting for the next
        housekeeping heartbeat (which still covers a job running in another process)."""
        job = self.store.request_cancel(job_id)
        ev = self._cancels.get(job_id)
        if ev is not None:
            ev.set()
        return job

    def run_pending(self, max_jobs: int = 50) -> int:
        """Run queued jobs in the calling thread (for tests and one-shot tooling)."""
        done = 0
        while done < max_jobs:
            job = self.store.claim_next(self.worker_id)
            if job is None:
                break
            self._execute(job)
            done += 1
        return done

    # ---------------------------------------------------------------------- execute
    def _execute(self, job: Job) -> None:
        spec = self.specs.get(job.operation)
        cancel = threading.Event()
        if job.cancel_requested:
            cancel.set()
        self._cancels[job.id] = cancel
        outcome: JobOutcome
        try:
            if spec is None:
                outcome = JobOutcome('FAILED', error_category='UNKNOWN_OPERATION',
                                     error_message='This job type is no longer supported.')
            else:
                ctx = JobContext(job, self.db_path, cancel, self.hooks, self.store)
                with job_scope(job.id, cancel):
                    outcome = spec.handler(ctx)
        except Exception:                                        # noqa: BLE001
            outcome = JobOutcome('FAILED', error_category='INTERNAL',
                                 error_message='The job failed unexpectedly.')
        finally:
            self._cancels.pop(job.id, None)
        self._finalise(job, outcome, cancel)

    def _finalise(self, job: Job, outcome: JobOutcome, cancel: threading.Event) -> None:
        fresh = self.store.get(job.id) or job
        if cancel.is_set() or fresh.cancel_requested or outcome.status == 'CANCELLED':
            if outcome.status != 'CANCELLED':
                outcome = JobOutcome('CANCELLED', error_category='CANCELLED',
                                     error_message='The job was cancelled.')
            self.store.finish(job, outcome, status=JobStatus.CANCELLED)
            return
        if outcome.status == 'FAILED' and outcome.retryable and fresh.retry_count < fresh.max_retries:
            delay = RETRY_BACKOFF_SECONDS[min(fresh.retry_count, len(RETRY_BACKOFF_SECONDS) - 1)]
            self.store.requeue(job, delay, outcome.error_category)
            self._wake.set()
            return
        status = JobStatus.SUCCEEDED if outcome.status == 'SUCCEEDED' else JobStatus.FAILED
        self.store.finish(job, outcome, status=status)
