"""Cancelling a RUNNING job takes effect at once, not at the next housekeeping heartbeat.

`JobQueue.cancel` flags the job in the database and sets the in-process cancel event the handler (and
the gateway, which kills the CLI process tree) is watching.

Run: python -m unittest tools.claude_cli.test_job_cancel
"""
from __future__ import annotations

import os
import tempfile
import threading
import time
import unittest

from .jobs import JobOutcome, JobQueue, JobSpec, JobStatus


class TestImmediateCancel(unittest.TestCase):

    def setUp(self):
        fd, self.db = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        self.addCleanup(lambda: os.path.exists(self.db) and os.remove(self.db))
        self.started = threading.Event()
        self.saw_cancel_after = []

        def handler(ctx):
            self.started.set()
            t0 = time.monotonic()
            cancelled = ctx.cancel_event.wait(timeout=8.0)       # a long call the cancel must interrupt
            self.saw_cancel_after.append(time.monotonic() - t0)
            return JobOutcome('CANCELLED') if cancelled else JobOutcome('SUCCEEDED', result={'done': True})

        spec = JobSpec('SLOW', handler, lambda inp: dict(inp or {}), candidate=False, max_retries=0)
        self.queue = JobQueue(self.db, {'SLOW': spec}, hooks=None, workers=1)
        self.addCleanup(self.queue.stop)

    def _wait_for(self, job_id, status, timeout=5.0):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            job = self.queue.store.get(job_id)
            if job and job.status is status:
                return job
            time.sleep(0.02)
        return self.queue.store.get(job_id)

    def test_cancelling_a_running_job_reaches_its_handler_within_a_moment(self):
        job, _dup, _tok = self.queue.submit('SLOW', {}, requested_by='admin', role='admin')
        self.assertTrue(self.started.wait(5.0), 'the worker never started the job')
        self.queue.cancel(job.id)
        done = self._wait_for(job.id, JobStatus.CANCELLED)
        self.assertIs(done.status, JobStatus.CANCELLED)
        # The handler saw the event far sooner than the 15 s housekeeping heartbeat (and than its own 8 s wait).
        self.assertTrue(self.saw_cancel_after and self.saw_cancel_after[0] < 3.0, self.saw_cancel_after)

    def test_cancelling_a_queued_job_never_runs_it(self):
        blocker, _d, _t = self.queue.submit('SLOW', {'n': 1}, requested_by='admin', role='admin')
        self.assertTrue(self.started.wait(5.0))
        waiting, _d, _t = self.queue.submit('SLOW', {'n': 2}, requested_by='admin', role='admin')
        cancelled = self.queue.cancel(waiting.id)
        self.assertIs(cancelled.status, JobStatus.CANCELLED)
        self.queue.cancel(blocker.id)
        self._wait_for(blocker.id, JobStatus.CANCELLED)
        self.assertEqual(len(self.saw_cancel_after), 1, 'the cancelled queued job must never reach its handler')

    def test_cancelling_an_unknown_job_is_harmless(self):
        self.assertIsNone(self.queue.cancel('no-such-job'))


if __name__ == '__main__':
    unittest.main()
