"""
MentalTalk — PostgreSQL Database Module
========================================
Handles: user auth (bcrypt), chat persistence, mood tracking, session stats.

All functions use parameterized queries to prevent SQL injection.
Connection pooling is handled by Neon's pooler endpoint.
"""

import os
import logging
import datetime

import psycopg2
import psycopg2.extras
import bcrypt

log = logging.getLogger("mentaltalk.db")

# ── Module-level connection ──────────────────────────────────────────────────
_conn = None


def _get_conn():
    """Get (or create) the PostgreSQL connection."""
    global _conn
    if _conn is None or _conn.closed:
        database_url = os.environ.get("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable not set. "
                "Add it to your .env file or Hugging Face Space secrets."
            )
        _conn = psycopg2.connect(database_url)
        _conn.autocommit = True
        log.info("✅ Connected to PostgreSQL")
    return _conn


#  SCHEMA INITIALIZATION

_SCHEMA_SQL = """
-- Users: secure auth with bcrypt-hashed passwords
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      VARCHAR(50) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Chat messages: full history per user
CREATE TABLE IF NOT EXISTS chat_messages (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
    user_message  TEXT NOT NULL,
    bot_response  TEXT NOT NULL,
    mood_label    VARCHAR(20),
    mood_color    VARCHAR(10),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Mood entries: daily mood logging
CREATE TABLE IF NOT EXISTS mood_entries (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER REFERENCES users(id) ON DELETE CASCADE,
    score         INTEGER CHECK (score >= 1 AND score <= 5),
    label         VARCHAR(20),
    color         VARCHAR(10),
    day_short     VARCHAR(3),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User stats: session counts, streaks
CREATE TABLE IF NOT EXISTS user_stats (
    user_id       INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    session_count INTEGER DEFAULT 0,
    last_checkin  DATE,
    streak        INTEGER DEFAULT 0
);

-- Indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_chat_user_id ON chat_messages(user_id);
CREATE INDEX IF NOT EXISTS idx_mood_user_id ON mood_entries(user_id);
"""


def init_db():
    """Connect to PostgreSQL and create tables if they don't exist.

    Call this once at app startup.
    """
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(_SCHEMA_SQL)
        log.info("✅ Database schema initialized")
    except Exception as e:
        log.error(f"❌ Database initialization failed: {e}")
        raise


#  USER AUTH

def create_user(username: str, password: str) -> dict | None:
    """Create a new user with bcrypt-hashed password.

    Returns:
        {"id": int, "username": str} on success, or None if username taken.
    """
    username = username.strip()
    if not username or not password:
        return None

    # Hash password with bcrypt (auto-generates salt)
    pw_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (%s, %s) "
                "RETURNING id, username",
                (username, hashed),
            )
            user = dict(cur.fetchone())

            # Create initial stats row
            cur.execute(
                "INSERT INTO user_stats (user_id, session_count, streak) "
                "VALUES (%s, 0, 0)",
                (user["id"],),
            )

        log.info(f"👤 User created: {username} (id={user['id']})")
        return user

    except psycopg2.errors.UniqueViolation:
        # Username already taken
        log.warning(f"👤 Username already taken: {username}")
        return None
    except Exception as e:
        log.error(f"User creation error: {e}")
        return None


def verify_user(username: str, password: str) -> dict | None:
    """Verify credentials and return user dict, or None if invalid.

    Returns:
        {"id": int, "username": str} on success, None on failure.
    """
    username = username.strip()
    if not username or not password:
        return None

    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT id, username, password_hash FROM users WHERE username = %s",
                (username,),
            )
            row = cur.fetchone()

        if not row:
            return None

        # Verify password against stored bcrypt hash
        pw_bytes = password.encode("utf-8")
        stored_hash = row["password_hash"].encode("utf-8")

        if bcrypt.checkpw(pw_bytes, stored_hash):
            log.info(f"🔓 Login successful: {username}")
            return {"id": row["id"], "username": row["username"]}
        else:
            log.warning(f"🔒 Invalid password for: {username}")
            return None

    except Exception as e:
        log.error(f"Login verification error: {e}")
        return None


#  CHAT MESSAGES

def save_chat_message(
    user_id: int,
    user_message: str,
    bot_response: str,
    mood_label: str = "",
    mood_color: str = "",
):
    """Persist a chat turn to the database."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO chat_messages "
                "(user_id, user_message, bot_response, mood_label, mood_color) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, user_message, bot_response, mood_label, mood_color),
            )
    except Exception as e:
        log.error(f"Failed to save chat message: {e}")


def get_chat_history(user_id: int, limit: int = 50) -> list:
    """Retrieve recent chat messages for a user (oldest first).

    Returns:
        List of dicts: [{user_message, bot_response, mood_label, mood_color, created_at}, ...]
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT user_message, bot_response, mood_label, mood_color, created_at "
                "FROM chat_messages WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()

        # Reverse to get oldest-first order
        return [dict(r) for r in reversed(rows)]

    except Exception as e:
        log.error(f"Failed to get chat history: {e}")
        return []


#  MOOD ENTRIES

def save_mood(
    user_id: int,
    score: int,
    label: str,
    color: str,
    day_short: str,
):
    """Log a mood entry for a user."""
    conn = _get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO mood_entries (user_id, score, label, color, day_short) "
                "VALUES (%s, %s, %s, %s, %s)",
                (user_id, score, label, color, day_short),
            )
    except Exception as e:
        log.error(f"Failed to save mood: {e}")


def get_recent_moods(user_id: int, limit: int = 7) -> list:
    """Get the last N mood entries for a user (oldest first).

    Returns:
        List of dicts: [{score, label, color, day_short, created_at}, ...]
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT score, label, color, day_short, created_at "
                "FROM mood_entries WHERE user_id = %s "
                "ORDER BY created_at DESC LIMIT %s",
                (user_id, limit),
            )
            rows = cur.fetchall()

        return [dict(r) for r in reversed(rows)]

    except Exception as e:
        log.error(f"Failed to get moods: {e}")
        return []


#  USER STATS (sessions, streaks)

def increment_session(user_id: int) -> dict:
    """Increment session count and update streak logic.

    Returns:
        {"session_count": int, "streak": int}
    """
    conn = _get_conn()
    try:
        today = datetime.date.today()

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Get current stats
            cur.execute(
                "SELECT session_count, last_checkin, streak "
                "FROM user_stats WHERE user_id = %s",
                (user_id,),
            )
            stats = cur.fetchone()

            if stats is None:
                # Create stats row if missing
                cur.execute(
                    "INSERT INTO user_stats (user_id, session_count, last_checkin, streak) "
                    "VALUES (%s, 1, %s, 1)",
                    (user_id, today),
                )
                return {"session_count": 1, "streak": 1}

            new_count = stats["session_count"] + 1
            last = stats["last_checkin"]
            streak = stats["streak"]

            if last is None:
                streak = 1
            elif last == today:
                # Same day — don't increment streak
                pass
            elif last == today - datetime.timedelta(days=1):
                # Consecutive day — increment streak
                streak += 1
            else:
                # Gap — reset streak
                streak = 1

            cur.execute(
                "UPDATE user_stats "
                "SET session_count = %s, last_checkin = %s, streak = %s "
                "WHERE user_id = %s",
                (new_count, today, streak, user_id),
            )

        return {"session_count": new_count, "streak": streak}

    except Exception as e:
        log.error(f"Failed to increment session: {e}")
        return {"session_count": 0, "streak": 0}


def get_user_stats(user_id: int) -> dict:
    """Get session count and streak for a user.

    Returns:
        {"session_count": int, "streak": int}
    """
    conn = _get_conn()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT session_count, streak FROM user_stats WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()

        if row:
            return {"session_count": row["session_count"], "streak": row["streak"]}
        return {"session_count": 0, "streak": 0}

    except Exception as e:
        log.error(f"Failed to get user stats: {e}")
        return {"session_count": 0, "streak": 0}
