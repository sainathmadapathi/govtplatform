"""The audit trail of Claude invocations, and the cache of schema-valid decisions.

Audit rows hold identifiers, statuses, timings and fingerprints, never prompt text, source text,
model output, command lines, paths or environment values. A fingerprint is enough to tell that
two calls had the same input; the input itself lives only where it already lived (the source
document, the job's sanitised input).

The decision cache holds only successful, schema-valid structured outputs, keyed by the input
fingerprint (which includes the prompt-template version). An infrastructure failure is never
cached: a transient outage must not be remembered as an answer.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


INVOCATION_COLUMNS = ('ts', 'operation', 'job_id', 'status', 'exit_category', 'duration_ms',
                      'template_version', 'input_fingerprint', 'output_fingerprint', 'cache_hit',
                      'cli_version', 'turns', 'input_tokens', 'output_tokens',
                      'web_search_requests', 'web_fetch_requests', 'message')


def init_audit_tables(conn: sqlite3.Connection) -> None:
    """Idempotent. Called from the app's database initialisation."""
    conn.execute('''
        CREATE TABLE IF NOT EXISTS claude_invocations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL, operation TEXT NOT NULL, job_id TEXT DEFAULT '',
            status TEXT NOT NULL, exit_category TEXT DEFAULT '', duration_ms INTEGER DEFAULT 0,
            template_version TEXT DEFAULT '', input_fingerprint TEXT DEFAULT '',
            output_fingerprint TEXT DEFAULT '', cache_hit INTEGER DEFAULT 0,
            cli_version TEXT DEFAULT '', turns INTEGER DEFAULT 0, input_tokens INTEGER DEFAULT 0,
            output_tokens INTEGER DEFAULT 0, web_search_requests INTEGER DEFAULT 0,
            web_fetch_requests INTEGER DEFAULT 0, message TEXT DEFAULT ''
        )''')
    conn.execute('CREATE INDEX IF NOT EXISTS idx_claude_invocations_job ON claude_invocations(job_id)')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS claude_decision_cache (
            cache_key TEXT PRIMARY KEY, operation TEXT NOT NULL, template_version TEXT NOT NULL,
            output_json TEXT NOT NULL, created_at TEXT NOT NULL
        )''')


class AuditSink:
    """Where invocation records go. The default drops them."""

    def record(self, event: dict) -> None:                       # pragma: no cover - interface
        pass


class MemoryAuditSink(AuditSink):
    def __init__(self) -> None:
        self.events: list = []

    def record(self, event: dict) -> None:
        self.events.append(dict(event))


class SqliteAuditSink(AuditSink):
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path

    def record(self, event: dict) -> None:
        try:
            conn = sqlite3.connect(self.db_path, timeout=10)
            try:
                init_audit_tables(conn)
                conn.execute(
                    f'INSERT INTO claude_invocations ({",".join(INVOCATION_COLUMNS)}) '
                    f'VALUES ({",".join("?" * len(INVOCATION_COLUMNS))})',
                    [event.get(c, '') if c != 'cache_hit' else int(bool(event.get(c))) for c in INVOCATION_COLUMNS])
                conn.commit()
            finally:
                conn.close()
        except Exception:                                        # noqa: BLE001
            # Auditing must never break the call it describes.
            pass


class DecisionCache:
    """An in-process LRU of valid outputs, optionally mirrored to SQLite."""

    def __init__(self, db_path: Optional[str] = None, max_entries: int = 4000) -> None:
        self.db_path = db_path
        self.max_entries = max_entries
        self._lock = threading.Lock()
        self._memory: 'OrderedDict[str, dict]' = OrderedDict()

    def get(self, key: str) -> Optional[dict]:
        with self._lock:
            hit = self._memory.get(key)
            if hit is not None:
                self._memory.move_to_end(key)
                return json.loads(json.dumps(hit))
        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                try:
                    init_audit_tables(conn)
                    row = conn.execute('SELECT output_json FROM claude_decision_cache WHERE cache_key=?',
                                       (key,)).fetchone()
                finally:
                    conn.close()
                if row:
                    value = json.loads(row[0])
                    with self._lock:
                        self._memory[key] = value
                    return value
            except Exception:                                    # noqa: BLE001
                return None
        return None

    def put(self, key: str, operation: str, template_version: str, output: dict) -> None:
        with self._lock:
            self._memory[key] = json.loads(json.dumps(output))
            self._memory.move_to_end(key)
            while len(self._memory) > self.max_entries:
                self._memory.popitem(last=False)
        if self.db_path:
            try:
                conn = sqlite3.connect(self.db_path, timeout=10)
                try:
                    init_audit_tables(conn)
                    conn.execute(
                        'INSERT OR REPLACE INTO claude_decision_cache '
                        '(cache_key, operation, template_version, output_json, created_at) VALUES (?,?,?,?,?)',
                        (key, operation, template_version, json.dumps(output, ensure_ascii=False), now_iso()))
                    conn.commit()
                finally:
                    conn.close()
            except Exception:                                    # noqa: BLE001
                pass

    def clear(self) -> None:
        with self._lock:
            self._memory.clear()
