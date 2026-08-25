import sqlite3
import os
import json
from datetime import datetime

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

    # Insert default primary user if not exists
    cursor.execute('SELECT id FROM users WHERE id = ?', ('default-candidate',))
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO users (id, username, target_post_id, target_exam_id, category, qualification)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('default-candidate', 'Candidate Aspirant', 'post-aso-css', 'ssc-cgl-2026', 'UR (Unreserved)', 'Bachelor Degree'))

    conn.commit()
    conn.close()
    print(f"[SQLite] Database initialized at: {DB_FILE}")

# Initialize immediately on import
init_database()
