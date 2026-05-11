"""
Database module for MindEase Mental Health Chatbot
Handles PostgreSQL connections, schema initialization, and data operations.
"""

import os
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extensions import ISOLATION_LEVEL_READ_COMMITTED
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

NEON_DATABASE_URL = os.getenv("NEON_DATABASE_URL")

# Connection pool
_connection_pool = None


def get_connection_pool():
    """Get or create the connection pool."""
    global _connection_pool
    if _connection_pool is None:
        if not NEON_DATABASE_URL:
            raise ValueError(
                "NEON_DATABASE_URL environment variable is not set. "
                "Please set it in your .env file or environment."
            )
        _connection_pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=NEON_DATABASE_URL,
        )
    return _connection_pool


@contextmanager
def get_connection():
    """
    Context manager for getting a database connection.
    Yields a connection and ensures it's returned to the pool.
    Caller is responsible for creating and closing cursors.

    Usage:
        with get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT * FROM users")
                results = cursor.fetchall()
            finally:
                cursor.close()
    """
    pool = get_connection_pool()
    conn = pool.getconn()
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_READ_COMMITTED)
        yield conn
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        pool.putconn(conn)


def init_db():
    """
    Initialize the database schema.
    Creates all required tables if they don't exist.
    Also handles migrations for existing tables.
    """
    create_tables_sql = """
    -- users table
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- chat_sessions table
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- messages table
    CREATE TABLE IF NOT EXISTS messages (
        id SERIAL PRIMARY KEY,
        session_id INTEGER REFERENCES chat_sessions(id) ON DELETE CASCADE,
        role VARCHAR(10) NOT NULL,
        content TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- mood_logs table
    CREATE TABLE IF NOT EXISTS mood_logs (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
        mood_label VARCHAR(30) NOT NULL,
        mood_score FLOAT NOT NULL,
        message_snippet TEXT,
        logged_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);
    CREATE INDEX IF NOT EXISTS idx_mood_logs_user_id ON mood_logs(user_id);
        CREATE INDEX IF NOT EXISTS idx_chat_sessions_user_id ON chat_sessions(user_id);
    """

    # Migration: Add logged_at column to mood_logs if it doesn't exist
    migration_sql = """
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = 'mood_logs' AND column_name = 'logged_at'
        ) THEN
            ALTER TABLE mood_logs ADD COLUMN logged_at TIMESTAMP;
ALTER TABLE mood_logs ALTER COLUMN logged_at SET DEFAULT CURRENT_TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_mood_logs_logged_at ON mood_logs(logged_at);
        END IF;
    END $$;
    """

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(create_tables_sql)
            cursor.execute(migration_sql)
            conn.commit()
        finally:
            cursor.close()


def create_session(user_id: int) -> int:
    """
    Create a new chat session for a user.

    Args:
        user_id: The ID of the user

    Returns:
        The ID of the newly created session
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("INSERT INTO chat_sessions (user_id) VALUES (%s) RETURNING id"),
                (user_id,)
            )
            session_id = cursor.fetchone()[0]
            conn.commit()
            return session_id
        finally:
            cursor.close()


def save_message(session_id: int, role: str, content: str) -> int:
    """
    Save a message to the database.

    Args:
        session_id: The ID of the chat session
        role: The role of the message ('user' or 'assistant')
        content: The content of the message

    Returns:
        The ID of the saved message
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("INSERT INTO messages (session_id, role, content) VALUES (%s, %s, %s) RETURNING id"),
                (session_id, role, content)
            )
            message_id = cursor.fetchone()[0]
            conn.commit()
            return message_id
        finally:
            cursor.close()


def get_session_messages(session_id: int) -> List[Dict[str, Any]]:
    """
    Get all messages for a chat session.

    Args:
        session_id: The ID of the chat session

    Returns:
        List of message dictionaries with keys: id, session_id, role, content, created_at
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("SELECT id, session_id, role, content, created_at FROM messages WHERE session_id = %s ORDER BY created_at ASC"),
                (session_id,)
            )
            columns = [desc[0] for desc in cursor.description]
            messages = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return messages
        finally:
            cursor.close()


def log_mood(user_id: int, mood_label: str, mood_score: float, message_snippet: str) -> int:
    """
    Log a mood entry to the database.

    Args:
        user_id: The ID of the user
        mood_label: The mood category label
        mood_score: The mood score (-1.0 to 1.0)
        message_snippet: A snippet of the message that triggered this mood log

    Returns:
        The ID of the logged mood entry
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("""
                    INSERT INTO mood_logs (user_id, mood_label, mood_score, message_snippet)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                """),
                (user_id, mood_label, mood_score, message_snippet)
            )
            mood_id = cursor.fetchone()[0]
            conn.commit()
            return mood_id
        finally:
            cursor.close()


def get_mood_history(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
    """
    Get mood history for a user within the specified time period.

    Args:
        user_id: The ID of the user
        days: Number of days to look back (default: 30)

    Returns:
        List of mood log dictionaries with keys: id, user_id, mood_label, mood_score, message_snippet, logged_at
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("""
                    SELECT id, user_id, mood_label, mood_score, message_snippet, logged_at
                    FROM mood_logs
                    WHERE user_id = %s AND logged_at >= CURRENT_TIMESTAMP - INTERVAL '%s days'
                    ORDER BY logged_at ASC
                """),
                (user_id, days)
            )
            columns = [desc[0] for desc in cursor.description]
            mood_history = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return mood_history
        finally:
            cursor.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get a user by their ID.

    Args:
        user_id: The ID of the user

    Returns:
        User dictionary or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("SELECT id, username, password_hash, created_at FROM users WHERE id = %s"),
                (user_id,)
            )
            columns = [desc[0] for desc in cursor.description]
            user = cursor.fetchone()
            if user:
                return dict(zip(columns, user))
            return None
        finally:
            cursor.close()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    """
    Get a user by their username.

    Args:
        username: The username to search for

    Returns:
        User dictionary or None if not found
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("SELECT id, username, password_hash, created_at FROM users WHERE username = %s"),
                (username,)
            )
            columns = [desc[0] for desc in cursor.description]
            user = cursor.fetchone()
            if user:
                return dict(zip(columns, user))
            return None
        finally:
            cursor.close()


def create_user(username: str, password_hash: str) -> int:
    """
    Create a new user.

    Args:
        username: The username
        password_hash: The bcrypt-hashed password

    Returns:
        The ID of the newly created user
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("INSERT INTO users (username, password_hash) VALUES (%s, %s) RETURNING id"),
                (username, password_hash)
            )
            user_id = cursor.fetchone()[0]
            conn.commit()
            return user_id
        finally:
            cursor.close()


def get_all_sessions(user_id: int) -> List[Dict[str, Any]]:
    """
    Get all chat sessions for a user.

    Args:
        user_id: The ID of the user

    Returns:
        List of session dictionaries
    """
    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                sql.SQL("SELECT id, user_id, session_start FROM chat_sessions WHERE user_id = %s ORDER BY session_start DESC"),
                (user_id,)
            )
            columns = [desc[0] for desc in cursor.description]
            sessions = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return sessions
        finally:
            cursor.close()
