"""HTTP surface of the Claude integration, mounted by `app.py` as a Flask blueprint.

    GET  /api/claude/health                  safe readiness (no path, command line or account)
    POST /api/claude/jobs                    ADMIN   create a job from the operation allowlist
    GET  /api/claude/jobs                    ADMIN   recent jobs
    GET  /api/claude/jobs/<id>               ADMIN, or the candidate holding the job's token
    POST /api/claude/jobs/<id>/cancel        ADMIN, or the candidate holding the job's token
    POST /api/claude/jobs/<id>/retry         ADMIN   re-queue a finished job's input
    POST /api/claude/ask                     candidate: a question about ONE exam (rate limited)
    POST /api/claude/practice                candidate: practice questions on a verified syllabus topic

Requests choose an operation from the allowlist and supply schema fields. They never supply a
prompt, flags, a tool permission, a working directory or an executable path. See security.py for
what "admin" means here (a local/admin guard, not production authentication).
"""
from __future__ import annotations

import re
from functools import wraps
from typing import Optional

from flask import Blueprint, jsonify, request

from .handlers import AppHooks, default_specs
from .jobs import JobQueue, QueueFull
from .schemas import InfraStatus, SAFE_MESSAGES
from .security import ADMIN_HEADER, JOB_TOKEN_HEADER, RateLimiter, admin_check, admin_token_required

LIMITER = RateLimiter()
_USER = re.compile(r'[^A-Za-z0-9._:-]')


def admin_denied():
    """A 403 response when the caller may not run admin operations, else None. For routes that
    serve both readers and writers, where only the write needs the guard."""
    ok, why = admin_check(request.remote_addr, request.headers)
    if ok:
        return None
    return jsonify({'error': 'ADMIN_REQUIRED', 'message': why,
                    'hint': f'send {ADMIN_HEADER} with the configured GOVOS_CLAUDE_ADMIN_TOKEN, '
                            f'or call from this machine directly'}), 403


def admin_required(fn):
    """Refuse the request unless it passes `security.admin_check`. Usable on any app route."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        denied = admin_denied()
        return denied if denied is not None else fn(*args, **kwargs)
    return wrapper


def _is_admin() -> bool:
    return admin_check(request.remote_addr, request.headers)[0]


def _user() -> str:
    raw = request.headers.get('X-GovOS-User') or request.args.get('user_id') or 'default-candidate'
    return _USER.sub('', raw)[:64] or 'default-candidate'


def _client_key(scope: str) -> str:
    return f'{scope}:{request.remote_addr}'


def _body() -> dict:
    """The JSON request body when it is an object; anything else ([], a string, a number) is no body."""
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _limit_arg() -> int:
    try:
        return int(request.args.get('limit', 30) or 30)
    except (TypeError, ValueError, OverflowError):
        return 30


def _candidate_view(job) -> dict:
    """What a candidate may see of their own job: state, and the validated result."""
    d = job.as_dict(include_input=False)
    for k in ('audit', 'requestedBy', 'role', 'evidenceLinks', 'inputFingerprint', 'maxRetries', 'retryCount'):
        d.pop(k, None)
    return d


def create_blueprint(db_path: str, hooks: AppHooks, *, queue: Optional[JobQueue] = None,
                     specs: Optional[dict] = None) -> tuple[Blueprint, JobQueue]:
    queue = queue or JobQueue(db_path, specs or default_specs(), hooks)
    bp = Blueprint('claude', __name__)
    gateway = lambda: hooks.claude()

    @bp.route('/api/claude/health', methods=['GET'])
    def health():
        return jsonify({**gateway().health(), 'adminTokenRequired': admin_token_required()})

    # ----------------------------------------------------------------------------- jobs
    def _create(operation: str, payload: dict, *, exam_id: str, cycle: str, role: str, by: str):
        try:
            job, dup, token = queue.submit(operation, payload, exam_id=exam_id, cycle=cycle,
                                           requested_by=by, role=role)
        except PermissionError:
            return jsonify({'error': 'FORBIDDEN', 'message': 'This operation is not available.'}), 403
        except ValueError as e:
            return jsonify({'error': 'INVALID_INPUT', 'message': str(e)}), 400
        except QueueFull as e:
            return jsonify({'error': 'QUEUE_FULL', 'message': str(e)}), 429
        body = {'jobId': job.id, 'status': job.status.value, 'deduplicated': dup,
                'pollUrl': f'/api/claude/jobs/{job.id}'}
        if token:
            body['token'] = token
        return jsonify(body), 202

    @bp.route('/api/claude/jobs', methods=['POST'])
    @admin_required
    def create_job():
        data = _body()
        operation = str(data.get('operation') or '')
        payload = data.get('input') if isinstance(data.get('input'), dict) else {}
        return _create(operation, payload, exam_id=str(data.get('examId') or '')[:120],
                       cycle=str(data.get('cycle') or '')[:20], role='admin', by='admin')

    @bp.route('/api/claude/jobs', methods=['GET'])
    @admin_required
    def list_jobs():
        jobs = queue.store.list(limit=_limit_arg(),
                                status=request.args.get('status', ''), operation=request.args.get('operation', ''))
        return jsonify({'jobs': [j.as_dict() for j in jobs], 'counts': queue.store.counts()})

    def _visible(job_id: str):
        job = queue.store.get(job_id)
        if job is None:
            return None, False
        admin = _is_admin()
        token = request.headers.get(JOB_TOKEN_HEADER, '')
        if not queue.store.can_read(job, token, admin=admin):
            return None, False                      # indistinguishable from "no such job"
        return job, admin

    @bp.route('/api/claude/jobs/<job_id>', methods=['GET'])
    def get_job(job_id):
        job, admin = _visible(job_id)
        if job is None:
            return jsonify({'error': 'NOT_FOUND'}), 404
        body = job.as_dict() if admin else _candidate_view(job)
        if admin and request.args.get('events'):
            body['events'] = queue.store.events(job_id)
        return jsonify(body)

    @bp.route('/api/claude/jobs/<job_id>/cancel', methods=['POST'])
    def cancel_job(job_id):
        job, admin = _visible(job_id)
        if job is None:
            return jsonify({'error': 'NOT_FOUND'}), 404
        updated = queue.cancel(job_id)
        return jsonify(updated.as_dict() if admin else _candidate_view(updated))

    @bp.route('/api/claude/jobs/<job_id>/retry', methods=['POST'])
    @admin_required
    def retry_job(job_id):
        job = queue.store.get(job_id)
        if job is None:
            return jsonify({'error': 'NOT_FOUND'}), 404
        if not job.status.terminal or job.status.value == 'SUCCEEDED':
            return jsonify({'error': 'NOT_RETRYABLE', 'message': 'Only a failed or cancelled job can be retried.'}), 409
        return _create(job.operation, job.input, exam_id=job.exam_id, cycle=job.cycle, role='admin', by='admin')

    # ------------------------------------------------------------------------ candidates
    def _ready() -> Optional[tuple]:
        h = gateway().health()
        if h.get('ready'):
            return None
        status = h.get('status') or InfraStatus.CLAUDE_CLI_FAILED.value
        return jsonify({'error': 'CLAUDE_UNAVAILABLE', 'status': status, 'fallback': True,
                        'message': h.get('message') or SAFE_MESSAGES[InfraStatus.CLAUDE_CLI_FAILED]}), 503

    @bp.route('/api/claude/ask', methods=['POST'])
    def ask():
        ok, wait = LIMITER.allow(_client_key('ask'), 8, 60)
        if not ok:
            return jsonify({'error': 'RATE_LIMITED', 'retryAfter': wait, 'fallback': True}), 429
        unavailable = _ready()
        if unavailable:
            return unavailable
        data = _body()
        return _create('ANSWER_QUESTION', data, exam_id=str(data.get('examId') or '')[:120], cycle='',
                       role='candidate', by=_user())

    @bp.route('/api/claude/practice', methods=['POST'])
    def practice():
        ok, wait = LIMITER.allow(_client_key('practice'), 4, 60)
        if not ok:
            return jsonify({'error': 'RATE_LIMITED', 'retryAfter': wait}), 429
        unavailable = _ready()
        if unavailable:
            return unavailable
        data = _body()
        return _create('GENERATE_PRACTICE', data, exam_id=str(data.get('examId') or '')[:120], cycle='',
                       role='candidate', by=_user())

    bp.queue = queue                                                     # type: ignore[attr-defined]
    return bp, queue
