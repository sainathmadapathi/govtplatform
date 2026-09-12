import os
import json
import sqlite3
import urllib.request
import urllib.error
from urllib.parse import urlparse, urlencode
import threading
import time
import xml.etree.ElementTree as ET
import base64
import io
import re
import zlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS

# =============================================================================
# SQLite storage layer (schema, connection, seed data)
# =============================================================================

DB_FILE = os.path.join(os.path.abspath(os.path.dirname(__file__)), 'govos.db')

def get_db_connection():
    """Get a connection to the local SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Create all necessary schema tables in govos.db if they don't already exist."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # 1. Users / Candidate Profiles
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL DEFAULT 'Candidate',
            target_post_id TEXT DEFAULT 'post-aso-css',
            target_exam_id TEXT DEFAULT 'ssc-cgl-2026',
            category TEXT DEFAULT 'UR (Unreserved)',
            qualification TEXT DEFAULT 'Graduation Degree',
            dob TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 2. Study Module Progress (Checklist & completion tracking)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS study_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            module_id TEXT NOT NULL,
            post_id TEXT,
            stage TEXT,
            is_completed INTEGER DEFAULT 1,
            completed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, module_id)
        )
    ''')

    # 3. CBT Mock Test & Practice Results
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS mock_attempts (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            topic_id TEXT,
            subject TEXT,
            score REAL NOT NULL,
            total_marks REAL NOT NULL,
            correct_count INTEGER NOT NULL,
            incorrect_count INTEGER NOT NULL,
            unattempted_count INTEGER NOT NULL,
            time_taken_seconds INTEGER DEFAULT 0,
            attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            details_json TEXT
        )
    ''')

    # 4. Bookmarked Resources & Direct Documents
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bookmarked_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            title TEXT,
            resource_type TEXT,
            url TEXT,
            bookmarked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, resource_id)
        )
    ''')

    # 5. Candidate Study Notes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_notes (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            topic_id TEXT NOT NULL,
            title TEXT,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 6. Audit & Discrepancy Reports
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_type TEXT NOT NULL,
            entity_id TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'PENDING_REVIEW',
            submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 7. Candidate Tracked Exams ("My Exam Timeline")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_exams (
            user_id TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            tracked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, exam_id)
        )
    ''')

    # 8. Personalized Notification Preferences
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notification_preferences (
            user_id TEXT PRIMARY KEY,
            channels_json TEXT NOT NULL,
            contact_json TEXT NOT NULL,
            subscriptions_json TEXT NOT NULL,
            schedule_json TEXT NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 9. Candidate Notifications Queue & History
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS candidate_notifications (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            exam_id TEXT NOT NULL,
            event_type TEXT NOT NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            channels_json TEXT,
            action_type TEXT,
            action_payload TEXT,
            priority TEXT DEFAULT 'NORMAL',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 10. Live Source Research (Tavily) — one row per search run
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            query TEXT NOT NULL,
            mode TEXT NOT NULL DEFAULT 'OFFICIAL',
            exam_id TEXT,
            answer TEXT,
            result_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # 11. Live Source Research — individual results awaiting human review
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_findings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            title TEXT,
            url TEXT NOT NULL,
            snippet TEXT,
            trust_level TEXT NOT NULL DEFAULT 'UNVERIFIED',
            score REAL DEFAULT 0,
            published_date TEXT,
            extracted_text TEXT,
            review_status TEXT NOT NULL DEFAULT 'PENDING_REVIEW',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (run_id) REFERENCES research_runs(id)
        )
    ''')

    # Insert default primary user if not exists
    cursor.execute('SELECT id FROM users WHERE id = ?', ('default-candidate',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (id, username, target_post_id, target_exam_id, category, qualification)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('default-candidate', 'Candidate Aspirant', 'post-aso-css', 'ssc-cgl-2026', 'UR (Unreserved)', 'Bachelor Degree'))

    # Seed default tracking for SSC CGL 2026 if no exams tracked yet
    cursor.execute('SELECT COUNT(*) FROM tracked_exams WHERE user_id = ?', ('default-candidate',))
    if cursor.fetchone()[0] == 0:
        cursor.execute('''
            INSERT OR IGNORE INTO tracked_exams (user_id, exam_id)
            VALUES (?, ?)
        ''', ('default-candidate', 'exam-ssc-cgl-2026'))

    # --- live resources: link health, feed caches, verifier-added entries ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resource_link_health (
            url TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'PENDING',
            http_code INTEGER DEFAULT 0,
            checked_at TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS live_feed_cache (
            cache_key TEXT PRIMARY KEY,
            payload_json TEXT NOT NULL,
            fetched_at TEXT NOT NULL,
            error TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS syllabus_revisions (
            id TEXT PRIMARY KEY,
            exam_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            topic_id TEXT,
            topic_json TEXT,
            note TEXT,
            notice_title TEXT,
            notice_url TEXT,
            notice_date TEXT,
            applied_at TEXT NOT NULL,
            applied_by TEXT NOT NULL,
            retired INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resource_additions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            subject TEXT NOT NULL,
            resource_format TEXT NOT NULL,
            author TEXT,
            description TEXT,
            added_at TEXT NOT NULL,
            added_from TEXT NOT NULL,
            finding_id INTEGER,
            retired INTEGER NOT NULL DEFAULT 0
        )
    ''')

    # 13. Candidate Behavioral Interactions (Time-Decayed BPR)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_interactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            type TEXT NOT NULL,
            target_id TEXT NOT NULL,
            target_type TEXT NOT NULL,
            exam_id TEXT,
            category_tag TEXT,
            timestamp INTEGER NOT NULL,
            metadata_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_user_interactions_user_time 
        ON user_interactions(user_id, timestamp DESC)
    ''')

    conn.commit()
    conn.close()
    print(f"[SQLite] Database initialized at: {DB_FILE}")


# =============================================================================
# Flask application
# =============================================================================

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DIST_DIR = os.path.join(BASE_DIR, 'dist')
STATIC_DIR = DIST_DIR if os.path.exists(DIST_DIR) else BASE_DIR

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app)

# Ensure database tables exist on server startup
init_database()

# --- Static File Serving ---

@app.route('/')
def serve_index():
    """Serve the single self-contained index.html from dist or root"""
    if os.path.exists(os.path.join(DIST_DIR, 'index.html')):
        return send_from_directory(DIST_DIR, 'index.html')
    return send_from_directory(BASE_DIR, 'index.html')

# NOTE: GovOS deliberately stores no study material. Every PDF and video in the
# Resource Library is a link to the official publisher's own server, so there is no
# /resources/<file> route to serve. Question banks are the only content GovOS holds,
# and each question cites the official document it was written from.

# --- SQLite REST API Endpoints ---

@app.route('/api/sqlite/status', methods=['GET'])
def get_sqlite_status():
    """Check SQLite database connectivity and row counts across all tables."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM study_progress WHERE is_completed = 1")
        progress_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM mock_attempts")
        mock_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM bookmarked_resources")
        bookmark_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM candidate_notes")
        notes_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tracked_exams")
        tracked_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM candidate_notifications")
        notif_count = cursor.fetchone()[0]
        
        conn.close()
        
        file_size_bytes = os.path.getsize(DB_FILE) if os.path.exists(DB_FILE) else 0
        
        return jsonify({
            "status": "connected",
            "db_type": "SQLite 3",
            "db_file": DB_FILE,
            "db_size_kb": round(file_size_bytes / 1024, 2),
            "stats": {
                "users": user_count,
                "completed_modules": progress_count,
                "mock_attempts": mock_count,
                "bookmarks": bookmark_count,
                "notes": notes_count,
                "tracked_exams": tracked_count,
                "notifications": notif_count
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/sqlite/profile', methods=['GET', 'POST'])
def handle_profile():
    """Get or update candidate profile and target post in SQLite."""
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify({
                "id": row["id"],
                "username": row["username"],
                "target_post_id": row["target_post_id"],
                "target_exam_id": row["target_exam_id"],
                "category": row["category"],
                "qualification": row["qualification"],
                "dob": row["dob"]
            })
        return jsonify({"id": user_id, "target_post_id": "post-aso-css"}), 404

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        username = data.get('username', 'Candidate')
        target_post_id = data.get('target_post_id', 'post-aso-css')
        target_exam_id = data.get('target_exam_id', 'ssc-cgl-2026')
        category = data.get('category', 'UR (Unreserved)')
        qualification = data.get('qualification', 'Bachelor Degree')
        dob = data.get('dob', '')

        cursor.execute('''
            INSERT INTO users (id, username, target_post_id, target_exam_id, category, qualification, dob, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(id) DO UPDATE SET
                username = excluded.username,
                target_post_id = excluded.target_post_id,
                target_exam_id = excluded.target_exam_id,
                category = excluded.category,
                qualification = excluded.qualification,
                dob = excluded.dob,
                updated_at = CURRENT_TIMESTAMP
        ''', (user_id, username, target_post_id, target_exam_id, category, qualification, dob))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "saved", "user_id": user_id, "target_post_id": target_post_id})

@app.route('/api/sqlite/progress', methods=['GET', 'POST'])
def handle_progress():
    """Get or save completed syllabus/study modules in SQLite."""
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT module_id, is_completed FROM study_progress WHERE user_id = ?", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        completed = {row["module_id"]: bool(row["is_completed"]) for row in rows}
        return jsonify({"user_id": user_id, "completed_modules": completed})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        module_id = data.get('module_id')
        is_completed = 1 if data.get('is_completed', True) else 0
        post_id = data.get('post_id', '')
        stage = data.get('stage', '')

        if module_id:
            cursor.execute('''
                INSERT INTO study_progress (user_id, module_id, post_id, stage, is_completed, completed_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, module_id) DO UPDATE SET
                    is_completed = excluded.is_completed,
                    completed_at = CURRENT_TIMESTAMP
            ''', (user_id, module_id, post_id, stage, is_completed))
            conn.commit()

        conn.close()
        return jsonify({"status": "saved", "module_id": module_id, "is_completed": bool(is_completed)})

@app.route('/api/sqlite/mock-attempts', methods=['GET', 'POST'])
def handle_mock_attempts():
    """Store and retrieve CBT mock exam scores and attempt history in SQLite."""
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM mock_attempts WHERE user_id = ? ORDER BY attempted_at DESC LIMIT 50", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        attempts = []
        for r in rows:
            attempts.append({
                "id": r["id"],
                "exam_id": r["exam_id"],
                "topic_id": r["topic_id"],
                "subject": r["subject"],
                "score": r["score"],
                "total_marks": r["total_marks"],
                "correct_count": r["correct_count"],
                "incorrect_count": r["incorrect_count"],
                "unattempted_count": r["unattempted_count"],
                "time_taken_seconds": r["time_taken_seconds"],
                "attempted_at": r["attempted_at"],
                "details": json.loads(r["details_json"]) if r["details_json"] else None
            })
        return jsonify({"user_id": user_id, "attempts": attempts})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        attempt_id = data.get('id', f"mock-{os.urandom(4).hex()}")
        exam_id = data.get('exam_id', 'ssc-cgl-2026')
        topic_id = data.get('topic_id', '')
        subject = data.get('subject', 'Full Mock')
        score = float(data.get('score', 0))
        total_marks = float(data.get('total_marks', 200))
        correct_count = int(data.get('correct_count', 0))
        incorrect_count = int(data.get('incorrect_count', 0))
        unattempted_count = int(data.get('unattempted_count', 0))
        time_taken_seconds = int(data.get('time_taken_seconds', 0))
        details_json = json.dumps(data.get('details', {}))

        cursor.execute('''
            INSERT INTO mock_attempts (id, user_id, exam_id, topic_id, subject, score, total_marks, correct_count, incorrect_count, unattempted_count, time_taken_seconds, details_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (attempt_id, user_id, exam_id, topic_id, subject, score, total_marks, correct_count, incorrect_count, unattempted_count, time_taken_seconds, details_json))
        
        conn.commit()
        conn.close()
        return jsonify({"status": "saved", "attempt_id": attempt_id}), 201

@app.route('/api/sqlite/sync-all', methods=['POST'])
def sync_all():
    """Bulk synchronize frontend localStorage state into SQLite in one atomic transaction."""
    payload = request.get_json(silent=True) or {}
    user_id = payload.get('user_id', 'default-candidate')
    profile = payload.get('profile', {})
    completed_modules = payload.get('completed_modules', {})
    mock_attempts = payload.get('mock_attempts', [])

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # 1. Update Profile
        if profile:
            cursor.execute('''
                INSERT INTO users (id, username, target_post_id, target_exam_id, category, qualification, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    target_post_id = excluded.target_post_id,
                    target_exam_id = excluded.target_exam_id,
                    category = excluded.category,
                    qualification = excluded.qualification,
                    updated_at = CURRENT_TIMESTAMP
            ''', (
                user_id,
                profile.get('username', 'Candidate'),
                profile.get('target_post_id', 'post-aso-css'),
                profile.get('target_exam_id', 'ssc-cgl-2026'),
                profile.get('category', 'UR (Unreserved)'),
                profile.get('qualification', 'Bachelor Degree')
            ))

        # 2. Batch Update Completed Modules
        for mod_id, is_done in completed_modules.items():
            cursor.execute('''
                INSERT INTO study_progress (user_id, module_id, is_completed, completed_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, module_id) DO UPDATE SET
                    is_completed = excluded.is_completed,
                    completed_at = CURRENT_TIMESTAMP
            ''', (user_id, mod_id, 1 if is_done else 0))

        # 3. Batch Insert or Update Mock Attempts with details_json
        for m in mock_attempts:
            if isinstance(m, dict) and m.get('id'):
                details = m.get('details') or {
                    'userAnswers': m.get('userAnswers'),
                    'paperData': m.get('paperData')
                }
                details_json = json.dumps(details) if details else None
                cursor.execute('''
                    INSERT INTO mock_attempts (id, user_id, exam_id, topic_id, subject, score, total_marks, correct_count, incorrect_count, unattempted_count, time_taken_seconds, details_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        details_json = COALESCE(excluded.details_json, mock_attempts.details_json),
                        score = excluded.score,
                        correct_count = excluded.correct_count,
                        incorrect_count = excluded.incorrect_count,
                        unattempted_count = excluded.unattempted_count
                ''', (
                    m['id'],
                    user_id,
                    m.get('exam_id', 'ssc-cgl-2026'),
                    m.get('topic_id', ''),
                    m.get('subject', 'General'),
                    float(m.get('score', 0)),
                    float(m.get('total_marks', 200)),
                    int(m.get('correct_count', 0)),
                    int(m.get('incorrect_count', 0)),
                    int(m.get('unattempted_count', 0)),
                    int(m.get('time_taken_seconds', 0)),
                    details_json
                ))

        conn.commit()
        conn.close()
        return jsonify({"status": "synchronized", "db_type": "SQLite 3", "user_id": user_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/reports', methods=['GET'])
def list_reports():
    """Return the queued data-accuracy reports for the admin Trust Panel."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM audit_reports ORDER BY submitted_at DESC LIMIT 100"
    )
    rows = cursor.fetchall()
    conn.close()
    return jsonify({
        "reports": [
            {
                "id": r["id"],
                "entityType": r["entity_type"],
                "entityId": r["entity_id"],
                "description": r["description"],
                "status": r["status"],
                "submittedAt": r["submitted_at"]
            }
            for r in rows
        ]
    })

@app.route('/api/reports/<int:report_id>/status', methods=['POST'])
def update_report_status(report_id):
    """Let a verifier resolve or reject a queued report."""
    data = request.get_json(silent=True) or {}
    status = data.get('status', 'RESOLVED')
    if status not in ('PENDING_REVIEW', 'RESOLVED', 'REJECTED'):
        return jsonify({"error": "invalid status"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE audit_reports SET status = ? WHERE id = ?", (status, report_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated", "report_id": report_id, "new_status": status})

@app.route('/api/reports', methods=['POST'])
def submit_report():
    data = request.get_json(silent=True) or {}
    entity_type = data.get('entityType', 'Unknown')
    entity_id = data.get('entityId', '')
    desc = data.get('description', '')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_reports (entity_type, entity_id, description)
        VALUES (?, ?, ?)
    ''', (entity_type, entity_id, desc))
    conn.commit()
    conn.close()

    return jsonify({
        "status": "success",
        "message": "Report logged into SQLite audit queue",
        "data": data
    }), 201

# --- Notification & Exam Tracking Endpoints ---

@app.route('/api/sqlite/tracked-exams', methods=['GET', 'POST'])
def handle_tracked_exams():
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT exam_id FROM tracked_exams WHERE user_id = ? ORDER BY tracked_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"user_id": user_id, "tracked_exam_ids": [r["exam_id"] for r in rows]})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        exam_id = data.get('exam_id')
        is_tracked = data.get('is_tracked', True)
        if not exam_id:
            conn.close()
            return jsonify({"error": "exam_id is required"}), 400

        if is_tracked:
            cursor.execute("INSERT OR IGNORE INTO tracked_exams (user_id, exam_id) VALUES (?, ?)", (user_id, exam_id))
        else:
            cursor.execute("DELETE FROM tracked_exams WHERE user_id = ? AND exam_id = ?", (user_id, exam_id))
        conn.commit()

        cursor.execute("SELECT exam_id FROM tracked_exams WHERE user_id = ? ORDER BY tracked_at DESC", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        return jsonify({"status": "updated", "user_id": user_id, "tracked_exam_ids": [r["exam_id"] for r in rows]})

@app.route('/api/sqlite/notifications/preferences', methods=['GET', 'POST'])
def handle_notification_preferences():
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return jsonify({
                "user_id": user_id,
                "channels": json.loads(row["channels_json"]),
                "contactInfo": json.loads(row["contact_json"]),
                "eventSubscriptions": json.loads(row["subscriptions_json"]),
                "reminderSchedule": json.loads(row["schedule_json"])
            })
        return jsonify({
            "user_id": user_id,
            "channels": { "inApp": True, "browserPush": False, "email": False, "whatsapp": False },
            "contactInfo": { "email": "", "phone": "", "whatsappVerified": False },
            "eventSubscriptions": {
                "applicationOpening": True,
                "applicationDeadlines": True,
                "correctionWindows": True,
                "admitCards": True,
                "examDates": True,
                "results": True
            },
            "reminderSchedule": {
                "sevenDaysBefore": True,
                "threeDaysBefore": True,
                "oneDayBefore": True,
                "lastDayHoursBefore": True
            }
        })

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        channels_json = json.dumps(data.get('channels', { "inApp": True, "browserPush": False, "email": False, "whatsapp": False }))
        contact_json = json.dumps(data.get('contactInfo', { "email": "", "phone": "", "whatsappVerified": False }))
        subscriptions_json = json.dumps(data.get('eventSubscriptions', {}))
        schedule_json = json.dumps(data.get('reminderSchedule', {}))

        cursor.execute('''
            INSERT INTO notification_preferences (user_id, channels_json, contact_json, subscriptions_json, schedule_json, updated_at)
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(user_id) DO UPDATE SET
                channels_json = excluded.channels_json,
                contact_json = excluded.contact_json,
                subscriptions_json = excluded.subscriptions_json,
                schedule_json = excluded.schedule_json,
                updated_at = CURRENT_TIMESTAMP
        ''', (user_id, channels_json, contact_json, subscriptions_json, schedule_json))
        conn.commit()
        conn.close()
        return jsonify({"status": "saved", "user_id": user_id})

@app.route('/api/sqlite/notifications', methods=['GET', 'POST', 'DELETE'])
def handle_notifications():
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute("SELECT * FROM candidate_notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT 100", (user_id,))
        rows = cursor.fetchall()
        conn.close()
        notifs = []
        for r in rows:
            notifs.append({
                "id": r["id"],
                "examId": r["exam_id"],
                "eventType": r["event_type"],
                "title": r["title"],
                "message": r["message"],
                "channelsDelivered": json.loads(r["channels_json"]) if r["channels_json"] else ["IN_APP"],
                "actionType": r["action_type"] or "EXAM_DETAIL",
                "actionPayload": json.loads(r["action_payload"]) if r["action_payload"] else None,
                "priority": r["priority"] or "NORMAL",
                "isRead": bool(r["is_read"]),
                "createdAt": r["created_at"]
            })
        return jsonify({"user_id": user_id, "notifications": notifs})

    elif request.method == 'POST':
        data = request.get_json(silent=True) or {}
        items = data.get('notifications') if isinstance(data.get('notifications'), list) else [data]
        inserted = 0
        for item in items:
            if not item or not item.get('id'):
                continue
            cursor.execute('''
                INSERT OR IGNORE INTO candidate_notifications (id, user_id, exam_id, event_type, title, message, channels_json, action_type, action_payload, priority, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                item['id'],
                user_id,
                item.get('examId', ''),
                item.get('eventType', 'APPLICATION_DEADLINE'),
                item.get('title', 'Exam Update'),
                item.get('message', ''),
                json.dumps(item.get('channelsDelivered', ['IN_APP'])),
                item.get('actionType', 'EXAM_DETAIL'),
                json.dumps(item.get('actionPayload')) if item.get('actionPayload') else None,
                item.get('priority', 'NORMAL'),
                1 if item.get('isRead') else 0,
                item.get('createdAt', datetime.now().isoformat())
            ))
            inserted += 1
        conn.commit()
        conn.close()
        return jsonify({"status": "saved", "inserted_count": inserted})

    elif request.method == 'DELETE':
        cursor.execute("DELETE FROM candidate_notifications WHERE user_id = ?", (user_id,))
        conn.commit()
        conn.close()
        return jsonify({"status": "cleared", "user_id": user_id})

@app.route('/api/sqlite/bookmarks', methods=['GET', 'POST'])
def handle_bookmarks():
    """Candidate's saved study resources ("Saved for later" shelf)."""
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'GET':
        cursor.execute(
            "SELECT resource_id, title, resource_type, url, bookmarked_at "
            "FROM bookmarked_resources WHERE user_id = ? ORDER BY bookmarked_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        return jsonify({
            "user_id": user_id,
            "resource_ids": [r["resource_id"] for r in rows],
            "bookmarks": [
                {"resourceId": r["resource_id"], "title": r["title"],
                 "resourceType": r["resource_type"], "url": r["url"],
                 "bookmarkedAt": r["bookmarked_at"]}
                for r in rows
            ]
        })

    data = request.get_json(silent=True) or {}
    resource_id = data.get('resource_id')
    if not resource_id:
        conn.close()
        return jsonify({"error": "resource_id is required"}), 400

    if data.get('is_bookmarked', True):
        cursor.execute(
            "INSERT OR IGNORE INTO bookmarked_resources (user_id, resource_id, title, resource_type, url) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, resource_id, data.get('title', ''), data.get('resource_type', ''), data.get('url', ''))
        )
    else:
        cursor.execute("DELETE FROM bookmarked_resources WHERE user_id = ? AND resource_id = ?",
                       (user_id, resource_id))
    conn.commit()

    cursor.execute("SELECT resource_id FROM bookmarked_resources WHERE user_id = ?", (user_id,))
    ids = [r["resource_id"] for r in cursor.fetchall()]
    conn.close()
    return jsonify({"status": "updated", "user_id": user_id, "resource_ids": ids})


def _check_one_link(url):
    """HEAD then GET with a browser-like UA and a cookie jar, so sites that bounce
    through a session-cookie redirect (e.g. ASP.NET portals) resolve as a browser would."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 GovOS-LinkCheck/1.0",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9"
    }
    checked_at = datetime.now().isoformat(timespec='seconds')
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
    for method in ("HEAD", "GET"):
        try:
            req = urllib.request.Request(url, headers=headers, method=method)
            with opener.open(req, timeout=10) as resp:
                code = resp.getcode()
                status = "REDIRECT" if resp.geturl() != url and code in (301, 302, 303, 307, 308) else "HEALTHY"
                return {"url": url, "status": status, "httpCode": code, "checkedAt": checked_at}
        except urllib.error.HTTPError as e:
            if method == "HEAD":
                continue  # many portals answer HEAD with 404/405 yet serve GET; only trust GET
            status = "BLOCKED" if e.code in (401, 403, 429) else "BROKEN"
            return {"url": url, "status": status, "httpCode": e.code, "checkedAt": checked_at}
        except Exception:
            if method == "HEAD":
                continue
            return {"url": url, "status": "UNREACHABLE", "httpCode": 0, "checkedAt": checked_at}
    return {"url": url, "status": "UNREACHABLE", "httpCode": 0, "checkedAt": checked_at}


@app.route('/api/resources/verify-links', methods=['POST'])
def verify_resource_links():
    """Live health check for study-resource URLs, run server-side (no browser CORS limits)."""
    data = request.get_json(silent=True) or {}
    urls = data.get('urls')
    if not isinstance(urls, list) or not urls:
        return jsonify({"error": "urls[] is required"}), 400
    urls = [u for u in urls if isinstance(u, str) and u.startswith(('http://', 'https://'))][:40]
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_check_one_link, urls))
    return jsonify({"results": results, "checked": len(results)})


@app.route('/api/sqlite/notifications/read', methods=['POST'])
def mark_notification_read():
    user_id = request.args.get('user_id', 'default-candidate')
    data = request.get_json(silent=True) or {}
    notif_id = data.get('notification_id')

    conn = get_db_connection()
    cursor = conn.cursor()
    if notif_id == 'ALL':
        cursor.execute("UPDATE candidate_notifications SET is_read = 1 WHERE user_id = ?", (user_id,))
    elif notif_id:
        cursor.execute("UPDATE candidate_notifications SET is_read = 1 WHERE user_id = ? AND id = ?", (user_id, notif_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "marked_read", "user_id": user_id, "notification_id": notif_id})


@app.route('/api/sqlite/interactions', methods=['GET'])
def get_user_interactions():
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_id, type, target_id, target_type, exam_id, category_tag, timestamp, metadata_json
        FROM user_interactions
        WHERE user_id = ?
        ORDER BY timestamp DESC
        LIMIT 100
    ''', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    items = []
    for r in rows:
        meta = None
        if r['metadata_json']:
            try:
                meta = json.loads(r['metadata_json'])
            except:
                meta = None
        items.append({
            'id': r['id'],
            'type': r['type'],
            'targetId': r['target_id'],
            'targetType': r['target_type'],
            'examId': r['exam_id'],
            'categoryTag': r['category_tag'],
            'timestamp': r['timestamp'],
            'metadata': meta
        })
    return jsonify({'interactions': items})


@app.route('/api/sqlite/interactions', methods=['POST'])
def save_user_interaction():
    data = request.get_json(silent=True) or {}
    user_id = data.get('user_id') or request.args.get('user_id', 'default-candidate')
    event_id = data.get('id') or f"act-{int(time.time()*1000)}"
    ev_type = data.get('type') or 'VIEW'
    target_id = data.get('targetId') or data.get('target_id') or ''
    target_type = data.get('targetType') or data.get('target_type') or 'EXAM'
    exam_id = data.get('examId') or data.get('exam_id')
    category_tag = data.get('categoryTag') or data.get('category_tag')
    timestamp = data.get('timestamp') or int(time.time() * 1000)
    meta_json = json.dumps(data.get('metadata')) if data.get('metadata') else None

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO user_interactions
        (id, user_id, type, target_id, target_type, exam_id, category_tag, timestamp, metadata_json)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (event_id, user_id, ev_type, target_id, target_type, exam_id, category_tag, timestamp, meta_json))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'id': event_id}), 201


@app.route('/api/sqlite/interactions', methods=['DELETE'])
def clear_user_interactions():
    user_id = request.args.get('user_id', 'default-candidate')
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_interactions WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'success': True, 'cleared_for': user_id})


# =============================================================================
# Live Source Research pipeline (Tavily)
#
#   search  ->  classify every result by domain  ->  store run + findings
#           ->  human review in the Trust Panel   ->  promote / reject
#
# Nothing found here reaches candidates as "verified"; it enters the audit
# queue exactly like a candidate-submitted report would.
# =============================================================================

def _load_dotenv():
    """Minimal .env loader (no dependency): sets keys that aren't already in the environment."""
    path = os.path.join(BASE_DIR, '.env')
    if not os.path.exists(path):
        return
    try:
        with open(path, encoding='utf-8') as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
    except OSError:
        pass

_load_dotenv()

TAVILY_API_KEY = os.environ.get('TAVILY_API_KEY', '').strip()
TAVILY_BASE_URL = os.environ.get('TAVILY_BASE_URL', 'https://api.tavily.com').rstrip('/')
TAVILY_TIMEOUT = 45

# Domains whose content is treated as OFFICIAL. Any *.gov.in / *.nic.in host is
# official by definition; these are the non-obvious statutory bodies.
OFFICIAL_HOSTS = {
    'ssc.gov.in', 'upsc.gov.in', 'ibps.in', 'www.ibps.in', 'rbi.org.in', 'www.rbi.org.in',
    'sebi.gov.in', 'www.sebi.gov.in', 'nabard.org', 'www.nabard.org', 'ncert.nic.in',
    'egazette.gov.in', 'pib.gov.in', 'legislative.gov.in', 'ndl.iitkgp.ac.in',
    'swayam.gov.in', 'nios.ac.in', 'www.nios.ac.in', 'mospi.gov.in', 'censusindia.gov.in',
    'india.gov.in', 'www.india.gov.in', 'niti.gov.in', 'www.niti.gov.in', 'pmindia.gov.in',
    'www.pmindia.gov.in', 'dopt.gov.in', 'cbic.gov.in', 'cag.gov.in', 'mea.gov.in', 'www.mea.gov.in',
    'sscnr.nic.in', 'ssc-cr.org', 'sscwr.net', 'sscer.org', 'sscsr.gov.in', 'ssckkr.kar.nic.in',
    'sscnwr.org', 'sscmpr.org', 'sscner.org.in',
}

# Domain list handed to Tavily for "official sources only" searches.
OFFICIAL_SEARCH_DOMAINS = [
    'ssc.gov.in', 'upsc.gov.in', 'ibps.in', 'egazette.gov.in', 'pib.gov.in', 'ncert.nic.in',
    'legislative.gov.in', 'india.gov.in', 'mospi.gov.in', 'rbi.org.in', 'sebi.gov.in',
    'sscnr.nic.in', 'ssc-cr.org', 'sscwr.net', 'sscer.org', 'sscsr.gov.in',
    'ssckkr.kar.nic.in', 'sscnwr.org', 'sscmpr.org', 'sscner.org.in',
]

TRUSTED_PUBLIC_SUFFIXES = ('.ac.in', '.edu', '.edu.in', '.res.in', '.org.in')
TRUSTED_PUBLIC_HOSTS = {'prsindia.org', 'www.prsindia.org', 'archive.org', 'www.archive.org'}


def _classify_trust(url):
    host = (urlparse(url).hostname or '').lower()
    if host.startswith('www.') and host[4:] in OFFICIAL_HOSTS:
        return 'OFFICIAL'
    if host in OFFICIAL_HOSTS or host.endswith('.gov.in') or host.endswith('.nic.in') or host.endswith('.gov'):
        return 'OFFICIAL'
    if host in TRUSTED_PUBLIC_HOSTS or host.endswith(TRUSTED_PUBLIC_SUFFIXES):
        return 'TRUSTED_PUBLIC'
    return 'UNVERIFIED'


class TavilyNotConfigured(Exception):
    pass


class TavilyError(Exception):
    def __init__(self, status, detail):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def _tavily_post(path, payload):
    """POST to the Tavily REST API. Sends the key both as a bearer header (current API)
    and in the body (older API) so either server version accepts it."""
    if not TAVILY_API_KEY:
        raise TavilyNotConfigured()
    body = dict(payload)
    body['api_key'] = TAVILY_API_KEY
    req = urllib.request.Request(
        TAVILY_BASE_URL + path,
        data=json.dumps(body).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + TAVILY_API_KEY,
            'User-Agent': 'GovOS-Research/1.0'
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=TAVILY_TIMEOUT) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode('utf-8')[:400]
        except Exception:
            detail = str(e)
        raise TavilyError(e.code, detail)
    except Exception as e:
        raise TavilyError(0, str(e)[:200])


def _not_configured_response():
    return jsonify({
        "error": "Tavily API key is not configured on the server.",
        "setup": "Add TAVILY_API_KEY=tvly-... to the .env file next to app.py (or export it) and restart python app.py.",
        "configured": False
    }), 503


def _finding_row_to_dict(r):
    return {
        "id": r["id"],
        "runId": r["run_id"],
        "title": r["title"] or r["url"],
        "url": r["url"],
        "snippet": r["snippet"] or "",
        "trustLevel": r["trust_level"],
        "score": r["score"] or 0,
        "publishedDate": r["published_date"],
        "reviewStatus": r["review_status"],
        "hasExtractedText": bool(r["extracted_text"]),
        "createdAt": r["created_at"]
    }


@app.route('/api/research/status', methods=['GET'])
def research_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM research_runs")
    run_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM research_findings WHERE review_status = 'PENDING_REVIEW'")
    pending = cursor.fetchone()[0]
    conn.close()
    return jsonify({
        "configured": bool(TAVILY_API_KEY),
        "baseUrl": TAVILY_BASE_URL,
        "officialDomains": OFFICIAL_SEARCH_DOMAINS,
        "runCount": run_count,
        "pendingReview": pending
    })


@app.route('/api/research/search', methods=['POST'])
def research_search():
    data = request.get_json(silent=True) or {}
    query = (data.get('query') or '').strip()
    if not query:
        return jsonify({"error": "query is required"}), 400
    mode = data.get('mode', 'OFFICIAL')
    if mode not in ('OFFICIAL', 'NEWS', 'WEB'):
        mode = 'OFFICIAL'
    exam_id = data.get('exam_id') or None
    try:
        max_results = max(1, min(int(data.get('max_results', 8)), 20))
    except (TypeError, ValueError):
        max_results = 8

    payload = {
        "query": query,
        "max_results": max_results,
        "include_answer": True,
        "include_raw_content": False,
        "search_depth": "advanced" if mode == 'OFFICIAL' else "basic",
        "topic": "news" if mode == 'NEWS' else "general",
    }
    if mode == 'OFFICIAL':
        payload["include_domains"] = OFFICIAL_SEARCH_DOMAINS
    if mode == 'NEWS':
        payload["days"] = 30

    try:
        raw = _tavily_post('/search', payload)
    except TavilyNotConfigured:
        return _not_configured_response()
    except TavilyError as e:
        return jsonify({"error": "Tavily request failed", "status": e.status, "detail": e.detail}), 502

    results = raw.get('results') or []
    answer = raw.get('answer')

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO research_runs (query, mode, exam_id, answer, result_count) VALUES (?, ?, ?, ?, ?)",
        (query, mode, exam_id, answer, len(results))
    )
    run_id = cursor.lastrowid
    stored = []
    # Tavily's include_domains is advisory in practice: live runs returned coaching
    # sites under OFFICIAL scope. Enforce the promise here and report what was dropped.
    classified = [(item, _classify_trust(item.get('url') or '')) for item in results if item.get('url')]
    filtered_out = 0
    if mode == 'OFFICIAL':
        kept = [(item, trust) for item, trust in classified if trust == 'OFFICIAL']
        filtered_out = len(classified) - len(kept)
        classified = kept
        cursor.execute("UPDATE research_runs SET result_count = ? WHERE id = ?", (len(classified), run_id))
    for item, trust in classified:
        url = item['url']
        cursor.execute(
            "INSERT INTO research_findings (run_id, title, url, snippet, trust_level, score, published_date) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (run_id, item.get('title') or url, url, (item.get('content') or '')[:1200], trust,
             float(item.get('score') or 0), item.get('published_date'))
        )
        stored.append({
            "id": cursor.lastrowid,
            "runId": run_id,
            "title": item.get('title') or url,
            "url": url,
            "snippet": (item.get('content') or '')[:1200],
            "trustLevel": trust,
            "score": float(item.get('score') or 0),
            "publishedDate": item.get('published_date'),
            "reviewStatus": "PENDING_REVIEW",
            "hasExtractedText": False
        })
    conn.commit()
    conn.close()

    # Official results first, then by Tavily's relevance score.
    order = {'OFFICIAL': 0, 'TRUSTED_PUBLIC': 1, 'UNVERIFIED': 2}
    stored.sort(key=lambda f: (order[f['trustLevel']], -f['score']))

    return jsonify({
        "runId": run_id,
        "query": query,
        "mode": mode,
        "examId": exam_id,
        "answer": answer,
        "results": stored,
        "filteredOut": filtered_out,
        "responseTime": raw.get('response_time')
    })


@app.route('/api/research/extract', methods=['POST'])
def research_extract():
    """Pull the readable text of one or more pages so a verifier can read the primary source in-app."""
    data = request.get_json(silent=True) or {}
    urls = data.get('urls')
    if not isinstance(urls, list) or not urls:
        return jsonify({"error": "urls[] is required"}), 400
    urls = [u for u in urls if isinstance(u, str) and u.startswith(('http://', 'https://'))][:5]
    finding_id = data.get('finding_id')

    try:
        raw = _tavily_post('/extract', {"urls": urls})
    except TavilyNotConfigured:
        return _not_configured_response()
    except TavilyError as e:
        return jsonify({"error": "Tavily request failed", "status": e.status, "detail": e.detail}), 502

    out = []
    for item in raw.get('results') or []:
        text = (item.get('raw_content') or '')[:20000]
        out.append({"url": item.get('url'), "rawContent": text, "chars": len(text), "failed": False})
    for item in raw.get('failed_results') or []:
        out.append({"url": item.get('url'), "rawContent": "", "chars": 0, "failed": True,
                    "reason": item.get('error')})

    if finding_id and out and not out[0]["failed"]:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE research_findings SET extracted_text = ? WHERE id = ?",
                       (out[0]["rawContent"], int(finding_id)))
        conn.commit()
        conn.close()

    return jsonify({"results": out})


@app.route('/api/research/history', methods=['GET'])
def research_history():
    try:
        limit = max(1, min(int(request.args.get('limit', 15)), 50))
    except (TypeError, ValueError):
        limit = 15
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM research_runs ORDER BY created_at DESC, id DESC LIMIT ?", (limit,))
    runs = cursor.fetchall()
    out = []
    for run in runs:
        cursor.execute("SELECT * FROM research_findings WHERE run_id = ? ORDER BY id", (run["id"],))
        findings = [_finding_row_to_dict(r) for r in cursor.fetchall()]
        out.append({
            "id": run["id"], "query": run["query"], "mode": run["mode"], "examId": run["exam_id"],
            "answer": run["answer"], "resultCount": run["result_count"], "createdAt": run["created_at"],
            "findings": findings
        })
    conn.close()
    return jsonify({"runs": out})


@app.route('/api/research/findings/<int:finding_id>', methods=['GET'])
def research_finding_detail(finding_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM research_findings WHERE id = ?", (finding_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return jsonify({"error": "not found"}), 404
    d = _finding_row_to_dict(row)
    d["extractedText"] = row["extracted_text"] or ""
    return jsonify(d)


@app.route('/api/research/findings/<int:finding_id>/status', methods=['POST'])
def research_finding_status(finding_id):
    data = request.get_json(silent=True) or {}
    status = data.get('status', 'REVIEWED')
    if status not in ('PENDING_REVIEW', 'REVIEWED', 'PROMOTED', 'REJECTED'):
        return jsonify({"error": "invalid status"}), 400
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE research_findings SET review_status = ? WHERE id = ?", (status, finding_id))
    conn.commit()
    conn.close()
    return jsonify({"status": "updated", "finding_id": finding_id, "new_status": status})


# =============================================================================
# Live resources
#
# The Resource Library must not be a static list. Three things keep it current:
#   1. SSC's own notice board, read from the portal's public API (official by construction);
#   2. each YouTube channel's public upload feed (no API key);
#   3. a scheduled re-check of every resource link, so health badges are always recent.
# Plus verifier-added entries, so a promoted research finding can reach candidates without
# a code edit. Everything is cached in SQLite and refreshed on a timer, so page loads are
# fast and the upstream sites are not hammered.
# =============================================================================

FEED_MAX_AGE_SECONDS = 6 * 3600      # SSC notices and channel uploads
HEALTH_MAX_AGE_SECONDS = 12 * 3600   # link re-check
SSC_NOTICE_API = 'https://ssc.gov.in/api/general-website/portal/notice-boards'
SSC_ATTACHMENT_BASE = 'https://ssc.gov.in/api/attachment/'
_LIVE_UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36 GovOS-LiveFeed/1.0",
    "Accept": "application/json, application/xml, text/xml, */*"
}
_health_lock = threading.Lock()
_health_running = False


def _now_iso():
    return datetime.now().isoformat(timespec='seconds')


def _age_seconds(iso_str):
    try:
        return (datetime.now() - datetime.fromisoformat(iso_str)).total_seconds()
    except Exception:
        return float('inf')


def _cache_get(key, max_age):
    conn = get_db_connection()
    row = conn.execute('SELECT payload_json, fetched_at, error FROM live_feed_cache WHERE cache_key = ?', (key,)).fetchone()
    conn.close()
    if not row:
        return None
    return {"payload": json.loads(row["payload_json"]), "fetchedAt": row["fetched_at"], "error": row["error"],
            "stale": _age_seconds(row["fetched_at"]) > max_age}


def _cache_put(key, payload, error=None):
    conn = get_db_connection()
    conn.execute('INSERT OR REPLACE INTO live_feed_cache (cache_key, payload_json, fetched_at, error) VALUES (?, ?, ?, ?)',
                 (key, json.dumps(payload), _now_iso(), error))
    conn.commit()
    conn.close()


def _fetch_ssc_notices():
    """Latest page of SSC's notice board, newest first, with each attachment as an absolute URL."""
    params = {'page': 1, 'limit': 40, 'key': 'createdAt', 'order': 'DESC', 'isPaginationRequired': 'true',
              'isAttachment': 'true', 'language': 'english',
              'attributes': 'id,headline,examId,contentType,startDate,endDate,language,createdAt'}
    req = urllib.request.Request(SSC_NOTICE_API + '?' + urlencode(params), headers=_LIVE_UA)
    with urllib.request.urlopen(req, timeout=25) as resp:
        data = json.loads(resp.read().decode('utf-8', 'ignore'))
    items = []
    for row in data.get('data') or []:
        headline = ' '.join((row.get('headline') or '').split())
        files = []
        for att in row.get('attachments') or []:
            path = (att.get('path') or '').replace('\\', '/')
            if not path:
                continue
            files.append({"name": att.get('fileName') or path.rsplit('/', 1)[-1],
                          "url": SSC_ATTACHMENT_BASE + path,
                          "sizeKb": int((att.get('size') or 0) / 1024)})
        low = headline.lower()
        items.append({"id": row.get('id'), "headline": headline, "createdAt": (row.get('createdAt') or '')[:10],
                      "files": files,
                      "isCgl": 'combined graduate level' in low or 'cgl' in low})
    return items


def _fetch_channel_uploads(channel_id):
    """Newest uploads from a YouTube channel's public Atom feed."""
    req = urllib.request.Request(f'https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}', headers=_LIVE_UA)
    with urllib.request.urlopen(req, timeout=20) as resp:
        root = ET.fromstring(resp.read())
    ns = {'a': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
    out = []
    for entry in root.findall('a:entry', ns)[:4]:
        vid = entry.findtext('yt:videoId', default='', namespaces=ns)
        if not vid:
            continue
        out.append({"videoId": vid,
                    "title": entry.findtext('a:title', default='', namespaces=ns),
                    "published": entry.findtext('a:published', default='', namespaces=ns)[:10],
                    "url": f'https://www.youtube.com/watch?v={vid}'})
    return out


def _ssc_notices_cached(force=False):
    cached = _cache_get('ssc-notices', FEED_MAX_AGE_SECONDS)
    if cached and not cached["stale"] and not force:
        return cached
    try:
        items = _fetch_ssc_notices()
        _cache_put('ssc-notices', items)
        return {"payload": items, "fetchedAt": _now_iso(), "error": None, "stale": False}
    except Exception as e:
        # keep serving the last good copy, but say it is stale
        if cached:
            cached["error"] = f'refresh failed: {e}'
            return cached
        return {"payload": [], "fetchedAt": None, "error": str(e), "stale": True}


def _channel_uploads_cached(channel_ids, force=False):
    result = {}
    to_fetch = []
    for cid in channel_ids:
        cached = _cache_get(f'yt-{cid}', FEED_MAX_AGE_SECONDS)
        if cached and not cached["stale"] and not force:
            result[cid] = {"items": cached["payload"], "fetchedAt": cached["fetchedAt"]}
        else:
            to_fetch.append((cid, cached))
    if to_fetch:
        def one(pair):
            cid, cached = pair
            try:
                items = _fetch_channel_uploads(cid)
                _cache_put(f'yt-{cid}', items)
                return cid, {"items": items, "fetchedAt": _now_iso()}
            except Exception as e:
                if cached:
                    return cid, {"items": cached["payload"], "fetchedAt": cached["fetchedAt"], "error": str(e)}
                return cid, {"items": [], "fetchedAt": None, "error": str(e)}
        with ThreadPoolExecutor(max_workers=8) as pool:
            for cid, val in pool.map(one, to_fetch):
                result[cid] = val
    return result


def _health_rows(urls=None):
    conn = get_db_connection()
    if urls:
        marks = ','.join('?' * len(urls))
        rows = conn.execute(f'SELECT url, status, http_code, checked_at FROM resource_link_health WHERE url IN ({marks})', urls).fetchall()
    else:
        rows = conn.execute('SELECT url, status, http_code, checked_at FROM resource_link_health').fetchall()
    conn.close()
    return [{"url": r["url"], "status": r["status"], "httpCode": r["http_code"], "checkedAt": r["checked_at"]} for r in rows]


def _store_health(results):
    conn = get_db_connection()
    for r in results:
        conn.execute('INSERT OR REPLACE INTO resource_link_health (url, status, http_code, checked_at) VALUES (?, ?, ?, ?)',
                     (r["url"], r["status"], r["httpCode"], r["checkedAt"]))
    conn.commit()
    conn.close()


def _recheck_links(urls):
    """Check a list of URLs and persist the results; guarded so only one sweep runs at a time."""
    global _health_running
    with _health_lock:
        if _health_running:
            return False
        _health_running = True
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(_check_one_link, urls))
        _store_health(results)
        print(f"[LiveResources] link health: {len(results)} checked at {_now_iso()}")
        return True
    finally:
        with _health_lock:
            _health_running = False


def _health_due():
    """URLs never checked, or checked longer ago than the interval."""
    rows = _health_rows()
    return [r["url"] for r in rows if not r["checkedAt"] or _age_seconds(r["checkedAt"]) > HEALTH_MAX_AGE_SECONDS]


def _background_refresh_loop():
    time.sleep(20)  # let the server come up first
    while True:
        try:
            due = _health_due()
            if due:
                _recheck_links(due[:80])
            _ssc_notices_cached()
            conn = get_db_connection()
            keys = [r["cache_key"][3:] for r in conn.execute("SELECT cache_key FROM live_feed_cache WHERE cache_key LIKE 'yt-%'").fetchall()]
            conn.close()
            if keys:
                _channel_uploads_cached(keys)
        except Exception as e:
            print(f"[LiveResources] background refresh error: {e}")
        time.sleep(3600)  # re-evaluate hourly; each feed refreshes only once its own interval has passed


def _start_background_refresh():
    t = threading.Thread(target=_background_refresh_loop, name='govos-live-refresh', daemon=True)
    t.start()


@app.route('/api/resources/live/status', methods=['GET'])
def live_resources_status():
    ssc = _cache_get('ssc-notices', FEED_MAX_AGE_SECONDS)
    rows = _health_rows()
    checked = [r["checkedAt"] for r in rows if r["checkedAt"]]
    return jsonify({
        "sscFetchedAt": ssc["fetchedAt"] if ssc else None,
        "healthLastRun": max(checked) if checked else None,
        "healthTracked": len(rows),
        "healthPending": len([r for r in rows if not r["checkedAt"]]),
        "feedIntervalHours": FEED_MAX_AGE_SECONDS // 3600,
        "healthIntervalHours": HEALTH_MAX_AGE_SECONDS // 3600
    })


@app.route('/api/resources/health/sync', methods=['POST'])
def resource_health_sync():
    """Register the library's URLs for scheduled checking and return what is known now.
    New URLs are checked in the background; the client polls again shortly after."""
    data = request.get_json(silent=True) or {}
    urls = [u for u in (data.get('urls') or []) if isinstance(u, str) and u.startswith(('http://', 'https://'))][:120]
    if not urls:
        return jsonify({"error": "urls[] is required"}), 400
    conn = get_db_connection()
    for u in urls:
        conn.execute('INSERT OR IGNORE INTO resource_link_health (url, status, http_code, checked_at) VALUES (?, ?, ?, ?)', (u, 'PENDING', 0, None))
    conn.commit()
    conn.close()
    rows = _health_rows(urls)
    pending = [r["url"] for r in rows if not r["checkedAt"]]
    if pending and not _health_running:
        threading.Thread(target=_recheck_links, args=(pending[:80],), daemon=True).start()
    checked = [r["checkedAt"] for r in rows if r["checkedAt"]]
    return jsonify({"results": [r for r in rows if r["checkedAt"]], "pending": len(pending),
                    "lastRun": max(checked) if checked else None, "intervalHours": HEALTH_MAX_AGE_SECONDS // 3600})


@app.route('/api/resources/health/recheck', methods=['POST'])
def resource_health_recheck():
    """Force an immediate sweep of the given URLs (the library's "Verify all links now")."""
    data = request.get_json(silent=True) or {}
    urls = [u for u in (data.get('urls') or []) if isinstance(u, str) and u.startswith(('http://', 'https://'))][:80]
    if not urls:
        return jsonify({"error": "urls[] is required"}), 400
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(_check_one_link, urls))
    _store_health(results)
    return jsonify({"results": results, "checked": len(results)})


@app.route('/api/resources/live/ssc-notices', methods=['GET'])
def live_ssc_notices():
    scope = (request.args.get('scope') or 'cgl').lower()
    limit = max(1, min(40, int(request.args.get('limit') or 8)))
    force = request.args.get('refresh') == '1'
    cached = _ssc_notices_cached(force=force)
    items = cached["payload"]
    if scope == 'cgl':
        items = [i for i in items if i["isCgl"]]
    return jsonify({"items": items[:limit], "total": len(cached["payload"]), "scope": scope,
                    "fetchedAt": cached["fetchedAt"], "stale": cached["stale"], "error": cached["error"],
                    "source": "https://ssc.gov.in/notice-board", "intervalHours": FEED_MAX_AGE_SECONDS // 3600})


@app.route('/api/resources/live/channel-uploads', methods=['GET'])
def live_channel_uploads():
    ids = [i.strip() for i in (request.args.get('ids') or '').split(',') if i.strip().startswith('UC')][:16]
    if not ids:
        return jsonify({"channels": {}})
    return jsonify({"channels": _channel_uploads_cached(ids, force=request.args.get('refresh') == '1'),
                    "intervalHours": FEED_MAX_AGE_SECONDS // 3600})


def _addition_row(r):
    return {"id": r["id"], "title": r["title"], "url": r["url"], "subject": r["subject"],
            "resourceFormat": r["resource_format"], "author": r["author"], "description": r["description"],
            "addedAt": r["added_at"], "addedFrom": r["added_from"], "findingId": r["finding_id"]}


@app.route('/api/resources/additions', methods=['GET', 'POST'])
def resource_additions():
    if request.method == 'GET':
        conn = get_db_connection()
        rows = conn.execute('SELECT * FROM resource_additions WHERE retired = 0 ORDER BY added_at DESC').fetchall()
        conn.close()
        return jsonify({"additions": [_addition_row(r) for r in rows]})
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    url = (data.get('url') or '').strip()
    if not title or not url.startswith(('http://', 'https://')):
        return jsonify({"error": "title and an http(s) url are required"}), 400
    lower = url.lower()
    fmt = data.get('resourceFormat') or ('DIRECT_PDF' if lower.endswith('.pdf') else 'OFFICIAL_PORTAL')
    row = {
        "id": f"add-{int(time.time() * 1000)}",
        "title": title[:200],
        "url": url,
        "subject": data.get('subject') or 'Official Gazette',
        "resource_format": fmt,
        "author": (data.get('author') or urlparse(url).netloc)[:160],
        "description": (data.get('description') or f'Added by the GovOS verifier from a live official-domain search on {_now_iso()[:10]}.')[:1200],
        "added_at": _now_iso(),
        "added_from": data.get('addedFrom') or 'TRUST_PANEL',
        "finding_id": data.get('findingId')
    }
    conn = get_db_connection()
    conn.execute("""INSERT INTO resource_additions (id, title, url, subject, resource_format, author, description, added_at, added_from, finding_id)
                    VALUES (:id, :title, :url, :subject, :resource_format, :author, :description, :added_at, :added_from, :finding_id)""", row)
    conn.commit()
    conn.close()
    _store_health([_check_one_link(url)])
    conn = get_db_connection()
    saved = conn.execute('SELECT * FROM resource_additions WHERE id = ?', (row["id"],)).fetchone()
    conn.close()
    return jsonify({"addition": _addition_row(saved), "health": _health_rows([url])})


@app.route('/api/resources/additions/<addition_id>/retire', methods=['POST'])
def retire_resource_addition(addition_id):
    conn = get_db_connection()
    cur = conn.execute('UPDATE resource_additions SET retired = 1 WHERE id = ?', (addition_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"retired": addition_id})


# =============================================================================
# Syllabus: watched on the notice board, revised only by a verifier
#
# The syllabus in the register carries the date it was verified. SSC's notice board is
# already cached here; the notices that can change a syllabus are the exam's own notice and
# any corrigendum, addendum or revision to it. `watch` lists those dated after the verified
# date. `revisions` stores what a verifier decided after reading one, citing it. The
# frontend merges active revisions over the seed - the board itself never edits the syllabus.
# =============================================================================

SYLLABUS_CHANGE_WORDS = re.compile(r'corrigend|addend|revis|amend|modif|syllab|scheme of exam|pattern|notice of', re.I)


def _syllabus_watch_items(exam_id, since):
    """Notices on the cached SSC board that may change this exam's syllabus, newest first."""
    if not exam_id.startswith('exam-ssc'):
        return None
    cached = _ssc_notices_cached(force=False)
    hits = []
    for item in cached["payload"]:
        if not item["isCgl"]:
            continue
        if since and item["createdAt"] <= since:
            continue
        if not SYLLABUS_CHANGE_WORDS.search(item["headline"]):
            continue
        hits.append(item)
    return {"items": hits, "fetchedAt": cached["fetchedAt"], "stale": cached["stale"], "error": cached["error"],
            "source": "https://ssc.gov.in/notice-board"}


@app.route('/api/syllabus/watch', methods=['GET'])
def syllabus_watch():
    exam_id = request.args.get('exam_id') or ''
    since = request.args.get('since') or ''
    found = _syllabus_watch_items(exam_id, since)
    if found is None:
        return jsonify({"items": [], "fetchedAt": None, "stale": False, "error": None, "source": None,
                        "note": "No live notice board is wired for this exam yet."})
    return jsonify(found)


def _revision_row(r):
    return {"id": r["id"], "examId": r["exam_id"], "kind": r["kind"], "topicId": r["topic_id"],
            "topic": json.loads(r["topic_json"]) if r["topic_json"] else None, "note": r["note"],
            "noticeTitle": r["notice_title"], "noticeUrl": r["notice_url"], "noticeDate": r["notice_date"],
            "appliedAt": r["applied_at"], "appliedBy": r["applied_by"]}


@app.route('/api/syllabus/revisions', methods=['GET', 'POST'])
def syllabus_revisions():
    if request.method == 'GET':
        exam_id = request.args.get('exam_id') or ''
        conn = get_db_connection()
        if exam_id:
            rows = conn.execute('SELECT * FROM syllabus_revisions WHERE retired = 0 AND exam_id = ? ORDER BY applied_at ASC', (exam_id,)).fetchall()
        else:
            rows = conn.execute('SELECT * FROM syllabus_revisions WHERE retired = 0 ORDER BY applied_at ASC').fetchall()
        conn.close()
        return jsonify({"revisions": [_revision_row(r) for r in rows]})

    data = request.get_json(silent=True) or {}
    exam_id = (data.get('examId') or '').strip()
    kind = (data.get('kind') or '').strip().upper()
    topic_id = (data.get('topicId') or '').strip() or None
    topic = data.get('topic') if isinstance(data.get('topic'), dict) else None
    notice_url = (data.get('noticeUrl') or '').strip()
    if not exam_id or kind not in ('ADD', 'AMEND', 'RETIRE'):
        return jsonify({"error": "examId and a kind of ADD, AMEND or RETIRE are required"}), 400
    if kind in ('AMEND', 'RETIRE') and not topic_id:
        return jsonify({"error": "topicId is required to amend or retire a topic"}), 400
    if kind in ('ADD', 'AMEND') and not topic:
        return jsonify({"error": "topic fields are required to add or amend"}), 400
    if kind == 'ADD' and not (topic.get('topicName') and topic.get('subject')):
        return jsonify({"error": "a new topic needs at least a subject and a topicName"}), 400
    if notice_url and not notice_url.startswith(('http://', 'https://')):
        return jsonify({"error": "noticeUrl must be http(s)"}), 400
    if not notice_url and not (data.get('note') or '').strip():
        return jsonify({"error": "cite the notice (noticeUrl) or say why (note); a change needs a basis"}), 400

    clean_topic = None
    if topic:
        clean_topic = {
            "subject": topic.get('subject'),
            "tier": topic.get('tier') or 'BOTH',
            "topicName": (topic.get('topicName') or '')[:200],
            "subtopics": [str(x)[:120] for x in (topic.get('subtopics') or []) if str(x).strip()][:20],
            "weightagePercentage": topic.get('weightagePercentage'),
            "avgQuestions": topic.get('avgQuestions'),
            "isHighYield": bool(topic.get('isHighYield')) if topic.get('isHighYield') is not None else None
        }
    row = {
        "id": f"rev-{int(time.time() * 1000)}",
        "exam_id": exam_id,
        "kind": kind,
        "topic_id": topic_id if kind != 'ADD' else None,
        "topic_json": json.dumps(clean_topic) if clean_topic else None,
        "note": (data.get('note') or '')[:1000] or None,
        "notice_title": (data.get('noticeTitle') or '')[:300] or None,
        "notice_url": notice_url or None,
        "notice_date": (data.get('noticeDate') or '')[:10] or None,
        "applied_at": _now_iso(),
        "applied_by": (data.get('appliedBy') or 'GovOS verifier')[:120]
    }
    conn = get_db_connection()
    conn.execute("""INSERT INTO syllabus_revisions (id, exam_id, kind, topic_id, topic_json, note, notice_title, notice_url, notice_date, applied_at, applied_by)
                    VALUES (:id, :exam_id, :kind, :topic_id, :topic_json, :note, :notice_title, :notice_url, :notice_date, :applied_at, :applied_by)""", row)
    conn.commit()
    saved = conn.execute('SELECT * FROM syllabus_revisions WHERE id = ?', (row["id"],)).fetchone()
    conn.close()
    return jsonify({"revision": _revision_row(saved)})


@app.route('/api/syllabus/revisions/<revision_id>/retire', methods=['POST'])
def retire_syllabus_revision(revision_id):
    conn = get_db_connection()
    cur = conn.execute('UPDATE syllabus_revisions SET retired = 1 WHERE id = ?', (revision_id,))
    conn.commit()
    conn.close()
    if cur.rowcount == 0:
        return jsonify({"error": "not found"}), 404
    return jsonify({"retired": revision_id})


# =============================================================================
# Reading a candidate's scorecard
#
# SSC publishes scorecards as generated PDFs, which carry real text: it can be pulled out
# with zlib and a regex, so GovOS reads the marks rather than asking the candidate to work
# out their own status. The file is parsed in memory and never written anywhere.
#
# Text in these PDFs is laid out character by character ("M a r k s   O b t a i ned"), so
# every match has to tolerate spaces inside words. Whatever is read is sent back for the
# candidate to confirm — a misread number must never silently become their result.
# =============================================================================

MAX_UPLOAD_BYTES = 8 * 1024 * 1024

def _pdf_text(blob):
    """Visible text of a text-based PDF. Empty for a scanned one, which has no text layer."""
    out = []
    for match in re.finditer(rb'stream\r?\n(.*?)\r?\nendstream', blob, re.S):
        chunk = match.group(1)
        try:
            chunk = zlib.decompress(chunk)
        except Exception:
            pass
        if b'Tj' not in chunk and b'TJ' not in chunk:
            continue
        text = chunk.decode('latin-1', 'ignore')
        for segment in re.findall(r'\((?:\\.|[^()\\])*\)', text):
            out.append(re.sub(r'\\([()\\])', r'\1', segment[1:-1]))
        out.append('\n')
    return ' '.join(out)


# ---- OCR for scans and photos. Optional: the app runs without these libraries. -----------
_OCR_ENGINE = None
_OCR_STATE = {"checked": False, "available": False, "reason": None}


def _ocr_available():
    """True when rapidocr_onnxruntime and pypdfium2 import; cached after the first look."""
    global _OCR_ENGINE
    if _OCR_STATE["checked"]:
        return _OCR_STATE["available"]
    _OCR_STATE["checked"] = True
    try:
        from rapidocr_onnxruntime import RapidOCR  # noqa: F401
        import pypdfium2  # noqa: F401
        import PIL  # noqa: F401
        _OCR_ENGINE = RapidOCR()
        _OCR_STATE["available"] = True
    except Exception as exc:  # ImportError, or a model that failed to load
        _OCR_STATE["reason"] = str(exc)[:200]
    return _OCR_STATE["available"]


OCR_INSTALL_HINT = "pip install rapidocr-onnxruntime pypdfium2 pillow numpy (they are in requirements.txt), then restart python app.py"


def _ocr_image(pil_image):
    """Text lines from one image, top to bottom, as RapidOCR read them."""
    import numpy as np
    img = pil_image.convert('RGB')
    # Small phone photos read badly; upscale to a sensible width before recognition.
    if img.width < 1400:
        ratio = 1400 / img.width
        img = img.resize((1400, int(img.height * ratio)))
    result, _elapsed = _OCR_ENGINE(np.array(img))
    if not result:
        return []
    # each item: [box, text, confidence]; sort by the box's top edge, then left edge
    result.sort(key=lambda item: (round(item[0][0][1] / 12), item[0][0][0]))
    return [item[1] for item in result if item[1] and item[1].strip()]


def _ocr_pdf(blob, max_pages=3):
    """Render the first pages of a scanned PDF and read them."""
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument(blob)
    lines = []
    try:
        for index in range(min(len(pdf), max_pages)):
            page = pdf[index]
            bitmap = page.render(scale=2.2)  # ~160 dpi: enough for print, small enough to be quick
            lines.extend(_ocr_image(bitmap.to_pil()))
            lines.append('')
    finally:
        pdf.close()
    return lines


def _ocr_bytes_as_image(raw):
    from PIL import Image
    return _ocr_image(Image.open(io.BytesIO(raw)))


def _join_numbers(text):
    """"1 5 0 . 0 4" is one number split by kerning; put it back together."""
    joined = re.sub(r'(?<=\d)\s+(?=\d)', '', text)
    return re.sub(r'(?<=\d)\s*\.\s*(?=\d)', '.', joined)


def _loose(word):
    """A pattern matching a word even when its letters are spaced apart."""
    return r'\s*'.join(re.escape(ch) for ch in word if not ch.isspace())


MARK_LABELS = ['normalized marks', 'normalised marks', 'total normalized marks', 'marks obtained',
               'total marks', 'aggregate marks', 'marks secured', 'total score']
CATEGORY_WORDS = [('pwbd', 'PwBD'), ('pwd', 'PwBD'), ('ews', 'EWS'), ('obc', 'OBC'),
                  ('sc', 'SC'), ('st', 'ST'), ('unreserved', 'UR'), ('general', 'UR'), ('ur', 'UR')]


def _parse_scorecard(text):
    """Pull the few fields that decide next steps. Everything is returned for confirmation."""
    numeric = _join_numbers(text)
    squashed = re.sub(r'\s+', '', text).lower()
    fields = {}
    notes = []

    # marks: prefer a number that follows a marks label, since a page is full of other numbers
    for label in MARK_LABELS:
        hit = re.search(_loose(label) + r'[^0-9]{0,40}(\d{1,3}(?:\.\d{1,2})?)', numeric, re.I)
        if hit:
            value = float(hit.group(1))
            if 0 <= value <= 700:
                fields['marks'] = value
                fields['marksLabel'] = label
                break
    if 'marks' not in fields:
        # nothing labelled: offer the plausible decimals so the candidate can pick
        loose_numbers = [float(n) for n in re.findall(r'\b\d{1,3}\.\d{1,2}\b', numeric)]
        plausible = [n for n in loose_numbers if 10 <= n <= 700]
        if plausible:
            fields['marksCandidates'] = sorted(set(plausible))[:6]
            notes.append('No "marks obtained" label found, so the number could not be identified with confidence.')

    for word, label in CATEGORY_WORDS:
        if re.search(r'(category|community)[^a-z]{0,20}' + _loose(word), squashed) or f'category{word}' in squashed:
            fields['category'] = label
            break

    roll = re.search(r'\b(\d{10,11})\b', numeric)
    if roll:
        fields['rollNumber'] = roll.group(1)

    if 'notqualified' in squashed or 'notshortlisted' in squashed:
        fields['declared'] = 'NOT_QUALIFIED'
    elif 'qualified' in squashed or 'shortlisted' in squashed:
        fields['declared'] = 'QUALIFIED'

    confidence = 'HIGH' if 'marks' in fields else ('LOW' if 'marksCandidates' in fields else 'NONE')
    return fields, confidence, notes


@app.route('/api/results/parse', methods=['POST'])
def parse_result_document():
    """Read an uploaded scorecard. Parsed in memory, never stored, always sent back to confirm."""
    data = request.get_json(silent=True) or {}
    content = data.get('contentBase64') or ''
    filename = (data.get('filename') or 'upload').lower()
    try:
        raw = base64.b64decode(content, validate=False)
    except Exception:
        return jsonify({"ok": False, "reason": "UNREADABLE", "message": "That file could not be decoded."}), 400
    if not raw:
        return jsonify({"ok": False, "reason": "EMPTY", "message": "The file was empty."}), 400
    if len(raw) > MAX_UPLOAD_BYTES:
        return jsonify({"ok": False, "reason": "TOO_LARGE", "message": "Scorecards are small files; this one is over 8 MB."}), 400

    method = "TEXT_LAYER"
    if raw[:4] != b'%PDF':
        is_image = raw[:3] == b'\xff\xd8\xff' or raw[:8] == b'\x89PNG\r\n\x1a\n' or raw[:4] == b'RIFF' or filename.endswith(('.png', '.jpg', '.jpeg', '.webp'))
        if not is_image:
            return jsonify({"ok": False, "reason": "NOT_A_PDF",
                            "message": "That is not a PDF or an image. Upload the scorecard PDF from the SSC portal, a photo of it, or type your marks in."}), 200
        if not _ocr_available():
            return jsonify({"ok": False, "reason": "OCR_NOT_INSTALLED",
                            "message": f"This is a photo or screenshot, and the OCR engine is not installed on this GovOS server, so it cannot be read yet. To enable it: {OCR_INSTALL_HINT}. Until then, type your marks in."}), 200
        try:
            lines = _ocr_bytes_as_image(raw)
        except Exception as exc:
            return jsonify({"ok": False, "reason": "OCR_FAILED", "message": f"The image could not be read ({str(exc)[:120]}). Try a sharper, straighter photo, or type your marks in."}), 200
        text = '\n'.join(lines)
        method = "OCR"
    else:
        text = _pdf_text(raw)
        if len(text.strip()) < 40:
            # No text layer: a scan, or an image inside a PDF wrapper. Read the pixels.
            if not _ocr_available():
                return jsonify({"ok": False, "reason": "OCR_NOT_INSTALLED",
                                "message": f"This PDF holds no text — it is a scan or an image inside a PDF wrapper — and the OCR engine is not installed on this GovOS server. To enable it: {OCR_INSTALL_HINT}. Until then, type your marks in."}), 200
            try:
                lines = _ocr_pdf(raw)
            except Exception as exc:
                return jsonify({"ok": False, "reason": "OCR_FAILED", "message": f"The scan could not be read ({str(exc)[:120]}). Type your marks in instead."}), 200
            text = '\n'.join(lines)
            method = "OCR"

    if len(text.strip()) < 12:
        return jsonify({"ok": False, "reason": "NO_TEXT_FOUND",
                        "message": "Nothing readable was found in that file — the scan may be too blurry or too dark. Try a clearer copy, or type your marks in."}), 200

    fields, confidence, notes = _parse_scorecard(text)
    if method == "OCR":
        notes.append("Read by OCR from the image, so a digit can be misread — check the marks against your scorecard before using them.")
    excerpt = ' '.join(text.split())[:400]
    return jsonify({
        "ok": True,
        "method": method,
        "fields": fields,
        "confidence": confidence,
        "notes": notes,
        "excerpt": excerpt,
        "storedOnServer": False
    })

# Fallback for SPA routing
@app.route('/<path:path>')
def serve_static_or_fallback(path):
    target_dir = DIST_DIR if os.path.exists(DIST_DIR) else BASE_DIR
    file_path = os.path.join(target_dir, path)
    if os.path.exists(file_path) and not os.path.isdir(file_path):
        return send_from_directory(target_dir, path)
    if os.path.exists(os.path.join(DIST_DIR, 'index.html')):
        return send_from_directory(DIST_DIR, 'index.html')
    return send_from_directory(BASE_DIR, 'index.html')

if __name__ == '__main__':
    # 5000 matches the /api proxy target in vite.config.ts and avoids colliding
    # with the Vite dev server, which also listens on 3000.
    port = int(os.environ.get('PORT', 5000))
    print(f"GovOS Unified Server + SQLite starting at http://localhost:{port}")
    _start_background_refresh()
    app.run(host='0.0.0.0', port=port, debug=False)
