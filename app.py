import os
import json
import sqlite3
from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from database import get_db_connection, init_database, DB_FILE

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
                "notes": notes_count
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

        # 3. Batch Insert Mock Attempts
        for m in mock_attempts:
            if isinstance(m, dict) and m.get('id'):
                cursor.execute('''
                    INSERT OR IGNORE INTO mock_attempts (id, user_id, exam_id, topic_id, subject, score, total_marks, correct_count, incorrect_count, unattempted_count, time_taken_seconds)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    int(m.get('time_taken_seconds', 0))
                ))

        conn.commit()
        conn.close()
        return jsonify({"status": "synchronized", "db_type": "SQLite 3", "user_id": user_id})
    except Exception as e:
        conn.rollback()
        conn.close()
        return jsonify({"status": "error", "message": str(e)}), 500

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
    port = int(os.environ.get('PORT', 3000))
    print(f"GovOS Unified Server + SQLite starting at http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=False)
