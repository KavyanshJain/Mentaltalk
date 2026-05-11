"""
Authentication module for MindEase Mental Health Chatbot
Handles user signup and login with bcrypt password hashing.
"""

import re
import bcrypt
from typing import Tuple
from psycopg2.errors import IntegrityError

from src.database import get_user_by_username, create_user, get_user_by_id


def _validate_username(username: str) -> Tuple[bool, str]:
    """
    Validate username against requirements.

    Rules:
    - 3-30 characters
    - Alphanumeric + underscore only

    Args:
        username: The username to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(username) < 3 or len(username) > 30:
        return False, "Username must be between 3 and 30 characters."

    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores."

    return True, ""


def _validate_password(password: str) -> Tuple[bool, str]:
    """
    Validate password against requirements.

    Rules:
    - Minimum 8 characters

    Args:
        password: The password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."

    return True, ""


def signup(username: str, password: str) -> Tuple[bool, str]:
    """
    Register a new user.

    Args:
        username: The desired username
        password: The plaintext password

    Returns:
        Tuple of (success, message)
    """
    # Validate inputs
    username_valid, username_msg = _validate_username(username)
    if not username_valid:
        return False, username_msg

    password_valid, password_msg = _validate_password(password)
    if not password_valid:
        return False, password_msg

    # Check if username already exists
    existing_user = get_user_by_username(username)
    if existing_user:
        return False, "Username already exists. Please choose a different one."

    # Hash the password
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    try:
        user_id = create_user(username, password_hash.decode('utf-8'))
        return True, f"User created successfully. Welcome, {username}!"
    except IntegrityError as e:
        # This shouldn't happen due to our check, but handle it anyway
        return False, "Username already exists. Please choose a different one."
    except Exception as e:
        return False, f"An error occurred during signup: {str(e)}"


def login(username: str, password: str) -> Tuple[bool, int, str]:
    """
    Authenticate a user.

    Args:
        username: The username
        password: The plaintext password

    Returns:
        Tuple of (success, user_id, message)
        user_id is None if login failed
    """
    # Get user from database
    user = get_user_by_username(username)
    if user is None:
        return False, None, "Invalid username or password."

    # Check password
    stored_hash = user['password_hash'].encode('utf-8')
    if bcrypt.checkpw(password.encode('utf-8'), stored_hash):
        return True, user['id'], f"Welcome back, {username}!"

    return False, None, "Invalid username or password."


def get_user_info(user_id: int) -> Tuple[bool, dict, str]:
    """
    Get user information by ID.

    Args:
        user_id: The user ID

    Returns:
        Tuple of (success, user_info, message)
    """
    user = get_user_by_id(user_id)
    if user is None:
        return False, {}, "User not found."

    # Return user info without password hash
    user_info = {
        'id': user['id'],
        'username': user['username'],
        'created_at': user['created_at']
    }
    return True, user_info, "User found."
