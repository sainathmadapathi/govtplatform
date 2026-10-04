"""No exception may kill a job worker or leave a job RUNNING for ever (jobs.py).

The audit's failure: `_finalise` ran outside the handler's protection and `_loop` caught only a failed
claim, so a database lock, a result `json.dumps` could not encode, or any bug in finalisation ended the
worker thread with its job still RUNNING. The housekeeping heartbeat then refreshed that row for as long
as the process lived (it refreshed every RUNNING job under the process's worker id), so `recover_stale`
never reclaimed it -- and with one worker, nothing ever ran again.

Each test injects one failure, deterministically, into a real queue on its own temporary database, and
checks three things: the worker thread is alive, the next job runs, and the failed job reaches a state the
existing machine handles -- a terminal state that is true (never SUCCEEDED without its result), or RUNNING
but no longer heartbeated, so `recover_stale` re-queues it within its retry budget or fails it INTERRUPTED.

Run: python -m pytest tools/claude_cli/test_job_worker_resilience.py -q
"""
from __future__ import annotations

import sqlite3
import threading
import unittest
from unittest import mock

from tools.claude_cli.jobs import JobOutcome, JobQueue, JobStatus, STALE_SECONDS
from tools.claude_cli.test_jobs import Clock, QueueCase, echo_spec, ok_handler, wait_for


def workers_alive(q) -> bool:
    threads = [t for t in q._threads if t.name.startswith('claude-job-worker')]
    return bool(threads) and all(t.is_alive() for t in threads)


class _Resilience(QueueCase):

    def queue(self, specs=None, workers: int = 1, clock=None) -> JobQueue:
        """A real threaded queue with ONE worker (so a dead worker means nothing else ever runs)."""
        q = JobQueue(self.db, specs or {'ECHO': echo_spec()}, workers=workers, **({'clock': clock} if clock else {}))
        q._sleep = lambda s: None                     # finalisation retries without waiting
        self._queues.append(q)
        return q

    def status(self, q, job_id):
        return q.store.get(job_id).status

    def submit(self, q, name):
        return q.submit('ECHO', {'q': name})[0]

    def assertRunsNext(self, q, label='B'):
        """The worker is alive and a new, ordinary job runs to completion after the failure."""
        b = self.submit(q, label)
        self.assertTrue(wait_for(lambda: self.status(q, b.id) is JobStatus.SUCCEEDED), 'the next job never ran')
        self.assertTrue(workers_alive(q), 'the worker thread died')
        return b


# --------------------------------------------------------------------------- the exact audit failure
class AuditRegressionTests(_Resilience):

    def test_finalise_raising_does_not_kill_the_worker_and_job_b_runs(self):
        q = self.queue()
        real = q._finalise
        calls = []

        def finalise_breaks_once(job, outcome, cancel):
            calls.append(job.id)
            if len(calls) == 1:
                raise RuntimeError('finalisation broke')
            return real(job, outcome, cancel)
        q._finalise = finalise_breaks_once
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is not JobStatus.RUNNING and calls))
        b = self.assertRunsNext(q)
        done = q.store.get(a.id)
        # A's handler succeeded, but its finalisation failed: it must not be recorded as SUCCEEDED from a
        # path that broke -- it is finished as an internal failure, with the incident on its trail.
        self.assertEqual((done.status, done.error_category), (JobStatus.FAILED, 'INTERNAL'))
        self.assertIn('WORKER_ERROR', [e['event'] for e in q.store.events(a.id)])
        self.assertEqual(q.store.get(b.id).status, JobStatus.SUCCEEDED)


# --------------------------------------------------------------------------- injected failures
class FailureInjectionTests(_Resilience):

    def test_execution_failure(self):
        def boom(ctx):
            raise KeyError('a handler bug')
        q = self.queue({'ECHO': echo_spec(boom)})
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.FAILED))
        self.assertEqual(q.store.get(a.id).error_category, 'INTERNAL')
        q.specs['ECHO'] = echo_spec(ok_handler)
        self.assertRunsNext(q)

    def test_a_malformed_outcome_is_a_failure_not_a_crash(self):
        for bad in (None, {'status': 'SUCCEEDED'}, JobOutcome('DONE')):
            with self.subTest(outcome=bad):
                q = self.queue({'ECHO': echo_spec(lambda ctx, bad=bad: bad)})
                a = self.submit(q, f'A-{type(bad).__name__}')
                self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.FAILED))
                self.assertEqual(q.store.get(a.id).error_category, 'INTERNAL')
                q.specs['ECHO'] = echo_spec(ok_handler)
                self.assertRunsNext(q, f'B-{type(bad).__name__}')
                q.stop(timeout=3)

    def test_serialisation_failure_is_never_a_false_success(self):
        q = self.queue({'ECHO': echo_spec(lambda ctx: JobOutcome('SUCCEEDED', result={'value': object()}))})
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.FAILED))
        done = q.store.get(a.id)
        self.assertEqual((done.error_category, done.result), ('RESULT_NOT_SAVED', None))
        self.assertIn(('finalise', 'ResultNotPersistable'), [(i['where'], i['error']) for i in q.incidents])
        q.specs['ECHO'] = echo_spec(ok_handler)
        self.assertRunsNext(q)

    def test_unserialisable_evidence_or_audit_is_caught_too(self):
        q = self.queue({'ECHO': echo_spec(lambda ctx: JobOutcome('SUCCEEDED', result={}, audit={'x': {1, 2}}))})
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.FAILED))
        self.assertEqual(q.store.get(a.id).error_category, 'RESULT_NOT_SAVED')

    def test_a_brief_database_lock_at_finalisation_is_retried_and_the_true_state_written(self):
        q = self.queue()
        real = q.store.finish
        attempts = []

        def locked_once(job, outcome, *, status):
            attempts.append(status)
            if len(attempts) == 1:
                raise sqlite3.OperationalError('database is locked')
            return real(job, outcome, status=status)
        q.store.finish = locked_once
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.SUCCEEDED))
        self.assertEqual(attempts, [JobStatus.SUCCEEDED, JobStatus.SUCCEEDED])
        self.assertEqual(q.store.get(a.id).retry_count, 0, 'a retried write is not a retried job')
        self.assertRunsNext(q)

    def test_a_lasting_database_failure_leaves_the_job_reclaimable_never_succeeded(self):
        clock = Clock()
        q = self.queue(clock=clock)
        real = q.store.finish
        broken = {'on': True}

        def finish(job, outcome, *, status):
            if broken['on']:
                raise sqlite3.OperationalError('database is locked')
            return real(job, outcome, status=status)
        q.store.finish = finish
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: any(i['where'] == 'finalise' for i in q.incidents)))
        self.assertTrue(wait_for(lambda: a.id not in q._active))
        row = q.store.get(a.id)
        self.assertEqual((row.status, row.result), (JobStatus.RUNNING, None), 'no false SUCCEEDED')
        broken['on'] = False
        self.assertRunsNext(q)                                    # the worker went on meanwhile
        # The heartbeat refreshes only jobs being executed: A goes stale and the existing recovery takes it.
        clock.advance(STALE_SECONDS + 1)
        q._housekeeping_tick(clock())
        recovered = q.store.get(a.id)
        self.assertIn(recovered.status, (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.SUCCEEDED))
        self.assertEqual(recovered.retry_count, 1)
        self.assertIn('RECOVERED', [e['event'] for e in q.store.events(a.id)])
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.SUCCEEDED), 'the reclaimed job never re-ran')

    def test_a_lasting_failure_with_no_retry_left_ends_interrupted_not_looping(self):
        clock = Clock()
        q = self.queue({'ECHO': echo_spec(max_retries=0)}, clock=clock)
        q.store.finish = mock.Mock(side_effect=sqlite3.OperationalError('disk I/O error'))
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: a.id not in q._active and any(i['where'] == 'finalise' for i in q.incidents)))
        clock.advance(STALE_SECONDS + 1)
        q._housekeeping_tick(clock())
        done = q.store.get(a.id)
        self.assertEqual((done.status, done.error_category), (JobStatus.FAILED, 'INTERRUPTED'))
        self.assertTrue(workers_alive(q))

    def test_heartbeat_failure_lets_a_job_go_stale_and_be_reclaimed(self):
        clock = Clock()
        gate = threading.Event()
        runs = []

        def slow(ctx):
            runs.append(ctx.job.retry_count)
            if len(runs) == 1:
                gate.wait(10)                             # the first attempt hangs while its heartbeat fails
            return JobOutcome('SUCCEEDED', result={'run': len(runs)})
        q = self.queue({'ECHO': echo_spec(slow, max_retries=2)}, clock=clock)
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: runs))
        with mock.patch.object(q.store, 'heartbeat', side_effect=sqlite3.OperationalError('database is locked')):
            clock.advance(STALE_SECONDS + 1)
            q._housekeeping_tick(clock())                 # the heartbeat fails; recovery still runs
        self.assertIn('heartbeat', [i['where'] for i in q.incidents])
        back = q.store.get(a.id)
        self.assertEqual((back.status, back.retry_count), (JobStatus.QUEUED, 1), 'the stale job was not reclaimed')
        gate.set()                                        # the first attempt now finishes -- too late to own the job
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.SUCCEEDED))
        done = q.store.get(a.id)
        self.assertEqual(done.result, {'run': 2}, 'the reclaimed attempt is the one recorded')
        terminal = [e['event'] for e in q.store.events(a.id) if e['event'] in ('SUCCEEDED', 'FAILED', 'CANCELLED')]
        self.assertEqual(terminal, ['SUCCEEDED'], 'one terminal state, written once')
        self.assertTrue(workers_alive(q))

    def test_an_unexpected_worker_loop_exception_is_contained(self):
        q = self.queue()
        real_claim = q.store.claim_next
        broke = []

        def claim(worker_id):
            if not broke:
                broke.append(1)
                raise RuntimeError('unexpected, outside any job')
            return real_claim(worker_id)
        q.store.claim_next = claim
        self.assertRunsNext(q, 'after-claim-failure')
        self.assertIn('claim', [i['where'] for i in q.incidents])

    def test_a_bug_escaping_execute_is_contained_and_the_job_left_reclaimable(self):
        clock = Clock()
        q = self.queue(clock=clock)
        real = q._finalise_safely
        broke = []

        def bug(job, outcome, cancel):
            if not broke:
                broke.append(job.id)
                raise AttributeError('a bug in the containment itself')
            return real(job, outcome, cancel)
        q._finalise_safely = bug
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: broke and a.id not in q._active))
        self.assertIn(('execute', 'AttributeError'), [(i['where'], i['error']) for i in q.incidents])
        self.assertRunsNext(q)
        self.assertEqual(self.status(q, a.id), JobStatus.RUNNING)
        clock.advance(STALE_SECONDS + 1)
        q._housekeeping_tick(clock())
        self.assertTrue(wait_for(lambda: self.status(q, a.id) is JobStatus.SUCCEEDED))

    def test_housekeeping_survives_every_step_failing(self):
        q = self.queue()
        with mock.patch.object(q.store, 'heartbeat', side_effect=RuntimeError('x')), \
                mock.patch.object(q.store, 'recover_stale', side_effect=sqlite3.OperationalError('locked')), \
                mock.patch.object(q.store, 'purge_candidate_data', side_effect=ValueError('y')):
            self.assertEqual(q._housekeeping_tick(0.0), 0.0)
        self.assertEqual([i['where'] for i in q.incidents][-3:], ['heartbeat', 'recover', 'purge'])

    def test_cleanup_failure_is_swallowed(self):
        q = self.queue()
        with mock.patch.object(q.store, '_conn', side_effect=sqlite3.OperationalError('unable to open database')):
            self.assertIsNone(q.store.note('job-x', 'WORKER_ERROR', 'detail'))
            q._incident('finalise', RuntimeError('x'), 'job-x')     # must not raise either

    def test_a_job_whose_row_disappeared_does_not_crash_the_worker(self):
        q = self.queue()
        gate = threading.Event()

        def wait_then_succeed(ctx):
            gate.wait(10)
            return JobOutcome('SUCCEEDED', result={})
        q.specs['ECHO'] = echo_spec(wait_then_succeed)
        a = self.submit(q, 'A')
        self.assertTrue(wait_for(lambda: a.id in q._active))
        conn = sqlite3.connect(self.db)
        conn.execute('DELETE FROM claude_jobs WHERE id=?', (a.id,))
        conn.commit()
        conn.close()
        gate.set()
        self.assertTrue(wait_for(lambda: a.id not in q._active))
        q.specs['ECHO'] = echo_spec(ok_handler)
        self.assertRunsNext(q)


# --------------------------------------------------------------------------- concurrency
class OwnershipTests(QueueCase):
    """Only the attempt that holds a job (RUNNING, its worker, its retry count) may finish it."""

    def test_a_worker_whose_job_was_reclaimed_cannot_overwrite_the_new_attempt(self):
        q = self.manual()
        job, *_ = q.submit('ECHO', {'q': 'x'})
        a = q.store.claim_next('worker-A')                           # 1. A claims
        self.clock.advance(STALE_SECONDS + 1)                         # 2. A stops heartbeating
        self.assertEqual(q.store.recover_stale(), 1)                  # 3. reclaimable, re-queued
        b = q.store.claim_next('worker-B')                            # 4. B reclaims it
        self.assertEqual((b.id, b.retry_count), (a.id, 1))
        self.assertFalse(q.store.finish(a, JobOutcome('FAILED', error_category='STALE'), status=JobStatus.FAILED))
        self.assertTrue(q.store.finish(b, JobOutcome('SUCCEEDED', result={'by': 'B'}), status=JobStatus.SUCCEEDED))
        self.assertFalse(q.store.requeue(a, 0, 'late'))
        done = q.store.get(job.id)
        self.assertEqual((done.status, done.result), (JobStatus.SUCCEEDED, {'by': 'B'}))
        terminal = [e['event'] for e in q.store.events(job.id) if e['event'] in ('SUCCEEDED', 'FAILED', 'CANCELLED')]
        self.assertEqual(terminal, ['SUCCEEDED'])

    def test_two_finishes_of_one_attempt_race_to_exactly_one_terminal_state(self):
        for _ in range(20):
            q = self.manual()
            job, *_ = q.submit('ECHO', {'q': f'x{_}'})
            claimed = q.store.claim_next('worker-A')
            results = {}
            barrier = threading.Barrier(2)

            def finish(kind, status):
                barrier.wait()
                results[kind] = q.store.finish(claimed, JobOutcome(status.value, result={'k': kind}), status=status)
            ts = [threading.Thread(target=finish, args=('s', JobStatus.SUCCEEDED)),
                  threading.Thread(target=finish, args=('f', JobStatus.FAILED))]
            [t.start() for t in ts]
            [t.join() for t in ts]
            self.assertEqual(sorted(results.values()), [False, True])
            winner = 's' if results['s'] else 'f'
            self.assertEqual(q.store.get(job.id).status, JobStatus.SUCCEEDED if winner == 's' else JobStatus.FAILED)
            terminal = [e['event'] for e in q.store.events(job.id) if e['event'] in ('SUCCEEDED', 'FAILED')]
            self.assertEqual(len(terminal), 1)
            self.tick()

    def test_an_old_attempt_finishing_does_not_stop_the_heartbeat_of_the_new_one(self):
        q = self.manual()
        job, *_ = q.submit('ECHO', {'q': 'x'})
        with q._lock:
            q._active[job.id] += 1                  # attempt 1, reclaimed but still running
            q._active[job.id] += 1                  # attempt 2 started on another thread
            q._active[job.id] -= 1                  # attempt 1 finishes
        self.assertIn(job.id, [j for j, n in q._active.items() if n > 0])

    def test_the_heartbeat_keeps_alive_only_the_jobs_being_executed(self):
        q = self.manual()
        a, *_ = q.submit('ECHO', {'q': 'a'})
        self.tick()
        b, *_ = q.submit('ECHO', {'q': 'b'})
        q.store.claim_next('w-1')
        q.store.claim_next('w-1')
        self.clock.advance(STALE_SECONDS - 10)
        q.store.heartbeat('w-1', [a.id])                              # only A is still being executed
        self.clock.advance(20)
        self.assertEqual(q.store.recover_stale(), 1)
        self.assertIs(q.store.get(a.id).status, JobStatus.RUNNING)
        self.assertIs(q.store.get(b.id).status, JobStatus.QUEUED)
        self.assertEqual(q.store.heartbeat('w-1', []), [])           # nothing executing: nothing refreshed


if __name__ == '__main__':
    unittest.main()
