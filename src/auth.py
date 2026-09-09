"""
Local Authentication & User Storage System for RAXEL (Phase 6.1).

Uses SQLite database and standard library salted PBKDF2-HMAC-SHA256 password hashing.
All SQL queries use parameterized arguments to prevent injection attacks.
Plaintext passwords are never stored or logged.
"""

import hmac
import secrets
import hashlib
import sqlite3
from typing import Optional, Dict, Any, List
from pathlib import Path
from src.config import Config

VALID_ROLES = {"student", "faculty", "admin"}

def get_db_path(db_path: Optional[Path] = None) -> Path:
    """Get standard auth database path."""
    if db_path is not None:
        return Path(db_path)
    return Config.AUTH_DATABASE_PATH

def get_db_connection(db_path: Optional[Path] = None) -> sqlite3.Connection:
    """Create and return a SQLite database connection."""
    target_path = get_db_path(db_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    return conn

def init_auth_db(db_path: Optional[Path] = None) -> None:
    """Initialize the users table if it does not already exist."""
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
    finally:
        conn.close()

def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with a random salt."""
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = secrets.token_hex(16)
    iterations = 100000
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash."""
    if not password or not hashed:
        return False
    try:
        parts = hashed.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False
        iterations = int(parts[1])
        salt = parts[2]
        expected_hash = parts[3]
        
        derived = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            iterations
        )
        return hmac.compare_digest(derived.hex(), expected_hash)
    except Exception:
        return False

def create_user(
    username: str,
    password: str,
    role: str,
    active: bool = True,
    db_path: Optional[Path] = None
) -> bool:
    """Create a new user with a hashed password using parameterized queries."""
    clean_username = username.strip().lower()
    clean_role = role.strip().lower()
    
    if not clean_username or not password:
        return False
    if clean_role not in VALID_ROLES:
        return False
    
    init_auth_db(db_path)
    hashed_pwd = hash_password(password)
    active_int = 1 if active else 0
    
    conn = get_db_connection(db_path)
    try:
        with conn:
            conn.execute(
                "INSERT INTO users (username, password_hash, role, active) VALUES (?, ?, ?, ?)",
                (clean_username, hashed_pwd, clean_role, active_int)
            )
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def get_user_by_username(username: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary by username (without exposing password hash)."""
    clean_username = username.strip().lower()
    init_auth_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, username, role, active, created_at FROM users WHERE LOWER(username) = LOWER(?)",
            (clean_username,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "active": bool(row["active"]),
                "created_at": row["created_at"]
            }
        return None
    finally:
        conn.close()

def get_user_by_id(user_id: int, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Retrieve user dictionary by user ID."""
    init_auth_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, username, role, active, created_at FROM users WHERE id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "active": bool(row["active"]),
                "created_at": row["created_at"]
            }
        return None
    finally:
        conn.close()

def authenticate_user(username: str, password: str, db_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate user credentials against SQLite database.
    Returns user dict if valid and active, None otherwise.
    Generic return prevents credential probing.
    """
    clean_username = username.strip().lower()
    if not clean_username or not password:
        return None
    
    init_auth_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, username, password_hash, role, active FROM users WHERE LOWER(username) = LOWER(?)",
            (clean_username,)
        )
        row = cursor.fetchone()
        if not row:
            return None
        
        if not bool(row["active"]):
            return None
        
        if verify_password(password, row["password_hash"]):
            return {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "active": bool(row["active"])
            }
        return None
    finally:
        conn.close()

def list_all_users(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Retrieve list of all registered users for administration."""
    init_auth_db(db_path)
    conn = get_db_connection(db_path)
    try:
        cursor = conn.execute(
            "SELECT id, username, role, active, created_at FROM users ORDER BY created_at DESC"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": row["id"],
                "username": row["username"],
                "role": row["role"],
                "active": bool(row["active"]),
                "created_at": row["created_at"]
            }
            for row in rows
        ]
    finally:
        conn.close()

def update_user_role(username: str, new_role: str, db_path: Optional[Path] = None) -> bool:
    """Update the role of a user in SQLite database (Admin action)."""
    clean_username = username.strip().lower()
    clean_role = new_role.strip().lower()
    if clean_role not in VALID_ROLES:
        return False
    
    init_auth_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE users SET role = ? WHERE LOWER(username) = LOWER(?)",
                (clean_role, clean_username)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()

def toggle_user_active(username: str, active: bool, db_path: Optional[Path] = None) -> bool:
    """Toggle user account active status."""
    clean_username = username.strip().lower()
    active_int = 1 if active else 0
    init_auth_db(db_path)
    conn = get_db_connection(db_path)
    try:
        with conn:
            cursor = conn.execute(
                "UPDATE users SET active = ? WHERE LOWER(username) = LOWER(?)",
                (active_int, clean_username)
            )
            return cursor.rowcount > 0
    finally:
        conn.close()

