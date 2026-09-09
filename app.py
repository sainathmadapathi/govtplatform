import os
import json
import sqlite3
import urllib.request
import urllib.error
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

@app.route('/resources/<path:filename>')
def serve_resources(filename):
    """Serve authentic downloaded PDF documents from public/resources"""
    res_dir = os.path.join(BASE_DIR, 'public', 'resources')
    if os.path.exists(os.path.join(res_dir, filename)):
        return send_from_directory(res_dir, filename)
    return jsonify({"error": "File not found"}), 404

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
    app.run(host='0.0.0.0', port=port, debug=False)
