# backend/database.py
import sqlite3
import datetime
import json
from contextlib import contextmanager
from backend.config import DATABASE_PATH


@contextmanager
def get_db():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Initialise tables (mirrors the Streamlit app schema exactly)."""
    with get_db() as conn:
        c = conn.cursor()

        c.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name TEXT,
            dob TEXT,
            class_level TEXT,
            department TEXT,
            email TEXT UNIQUE,
            password TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS academic_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            result_type TEXT,
            subject TEXT,
            score REAL,
            exam_date TEXT,
            uploaded_at TEXT,
            UNIQUE(user_id, result_type, subject, score, exam_date)
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS test_responses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            test_type TEXT,
            question_id TEXT,
            answer TEXT,
            score REAL,
            submitted_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            career_path TEXT,
            confidence REAL,
            universities TEXT,
            linkedin_mentors TEXT,
            narrative TEXT,
            top3 TEXT,
            generated_at TEXT
        )""")

        c.execute("""CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            role TEXT,
            message TEXT,
            created_at TEXT
        )""")

        # Migration: add columns that may be missing in existing DB
        for col, typ in [("narrative", "TEXT"), ("top3", "TEXT")]:
            try:
                c.execute(f"ALTER TABLE recommendations ADD COLUMN {col} {typ}")
            except Exception:
                pass


# ── User helpers ──────────────────────────────────────────────────────────────

def get_user_by_email(email: str):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, full_name, dob, class_level, department, email, password "
            "FROM users WHERE email=?", (email,)
        ).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, full_name, dob, class_level, department, email "
            "FROM users WHERE id=?", (user_id,)
        ).fetchone()
    return dict(row) if row else None


def update_user_password(user_id: int, hashed_password: str) -> bool:
    """Update the stored password hash for a user. Returns True on success."""
    with get_db() as conn:
        conn.execute(
            "UPDATE users SET password=? WHERE id=?",
            (hashed_password, user_id)
        )
    return True


def create_user(full_name, dob, class_level, department, email, hashed_password) -> bool:
    try:
        with get_db() as conn:
            conn.execute(
                "INSERT INTO users (full_name,dob,class_level,department,email,password) "
                "VALUES (?,?,?,?,?,?)",
                (full_name, str(dob), class_level, department, email, hashed_password)
            )
        return True
    except sqlite3.IntegrityError:
        return False


# ── Academic results ──────────────────────────────────────────────────────────

def save_academic_result(user_id, result_type, subject, score, exam_date) -> bool:
    """Returns True if inserted, False if duplicate."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM academic_results "
            "WHERE user_id=? AND result_type=? AND subject=? AND score=? AND exam_date=?",
            (user_id, result_type, subject, score, str(exam_date))
        ).fetchone()
        if existing:
            return False
        conn.execute(
            "INSERT INTO academic_results "
            "(user_id,result_type,subject,score,exam_date,uploaded_at) VALUES (?,?,?,?,?,?)",
            (user_id, result_type, subject, score, str(exam_date),
             datetime.datetime.now().isoformat())
        )
    return True


def get_user_results(user_id: int):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT id,result_type,subject,score,exam_date,uploaded_at "
            "FROM academic_results WHERE user_id=? ORDER BY uploaded_at DESC",
            (user_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def delete_academic_result(result_id: int, user_id: int) -> bool:
    with get_db() as conn:
        conn.execute(
            "DELETE FROM academic_results WHERE id=? AND user_id=?",
            (result_id, user_id)
        )
    return True


# ── Test responses ────────────────────────────────────────────────────────────

def save_test_responses(user_id, test_type, answers_dict: dict, score: float):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM test_responses WHERE user_id=? AND test_type=?",
            (user_id, test_type)
        )
        now = datetime.datetime.now().isoformat()
        for q_id, ans in answers_dict.items():
            conn.execute(
                "INSERT INTO test_responses "
                "(user_id,test_type,question_id,answer,score,submitted_at) VALUES (?,?,?,?,?,?)",
                (user_id, test_type, q_id, str(ans), score, now)
            )


def get_completed_tests(user_id: int) -> set:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT DISTINCT test_type FROM test_responses WHERE user_id=?",
            (user_id,)
        ).fetchall()
    return {r["test_type"] for r in rows}


def get_test_scores(user_id: int) -> dict:
    """Returns {test_type: score} for each completed test."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT test_type, score FROM test_responses WHERE user_id=? "
            "GROUP BY test_type ORDER BY submitted_at DESC",
            (user_id,)
        ).fetchall()
    scores = {}
    for r in rows:
        if r["test_type"] not in scores:
            scores[r["test_type"]] = r["score"]
    return scores


# ── Recommendations ───────────────────────────────────────────────────────────

def save_recommendation(user_id, career_path, confidence, universities,
                        linkedin_mentors, narrative, top3):
    with get_db() as conn:
        conn.execute("DELETE FROM recommendations WHERE user_id=?", (user_id,))
        conn.execute(
            "INSERT INTO recommendations "
            "(user_id,career_path,confidence,universities,linkedin_mentors,"
            "narrative,top3,generated_at) VALUES (?,?,?,?,?,?,?,?)",
            (user_id, career_path, confidence,
             json.dumps(universities), json.dumps(linkedin_mentors),
             narrative, json.dumps(top3),
             datetime.datetime.now().isoformat())
        )


def get_recommendation(user_id: int):
    with get_db() as conn:
        row = conn.execute(
            "SELECT career_path,confidence,universities,linkedin_mentors,"
            "narrative,top3,generated_at "
            "FROM recommendations WHERE user_id=? ORDER BY generated_at DESC LIMIT 1",
            (user_id,)
        ).fetchone()
    if not row:
        return None
    return {
        "career_path":  row["career_path"],
        "confidence":   row["confidence"],
        "universities": json.loads(row["universities"] or "[]"),
        "mentors":      json.loads(row["linkedin_mentors"] or "[]"),
        "narrative":    row["narrative"] or "",
        "top3":         json.loads(row["top3"] or "[]"),
        "generated_at": row["generated_at"],
    }


# ── Chat history ──────────────────────────────────────────────────────────────

def save_chat_message(user_id, role, message):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_id,role,message,created_at) VALUES (?,?,?,?)",
            (user_id, role, message, datetime.datetime.now().isoformat())
        )


def get_chat_history(user_id: int, limit: int = 40):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT role,message FROM chat_history "
            "WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        ).fetchall()
    return list(reversed([dict(r) for r in rows]))


def clear_chat_history(user_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM chat_history WHERE user_id=?", (user_id,))

