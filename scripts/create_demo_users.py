"""
Script to initialize RAXEL SQLite authentication database and create initial demo users.

DEVELOPMENT / DEMO ONLY.

Do NOT use default credentials in production environments.
"""

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config
from src.auth import init_auth_db, create_user, get_user_by_username

DEMO_USERS = [
    {"username": "student1", "password": "StudentPass123!", "role": "student"},
    {"username": "faculty1", "password": "FacultyPass123!", "role": "faculty"},
    {"username": "admin1", "password": "AdminPass123!", "role": "admin"},
]

def initialize_demo_users():
    """Seed demo accounts into local SQLite auth DB if they do not exist."""
    print("=" * 60)
    print(" RAXEL DEMO USER INITIALIZATION (DEVELOPMENT / DEMO ONLY)")
    print("=" * 60)
    
    Config.ensure_directories()
    init_auth_db()
    
    created_count = 0
    skipped_count = 0
    
    for u in DEMO_USERS:
        existing = get_user_by_username(u["username"])
        if existing:
            print(f"[-] User '{u['username']}' ({existing['role']}) already exists. Skipping.")
            skipped_count += 1
        else:
            success = create_user(u["username"], u["password"], u["role"])
            if success:
                print(f"[+] Created demo user: '{u['username']}' | Role: {u['role']}")
                created_count += 1
            else:
                print(f"[!] Failed to create demo user: '{u['username']}'")
                
    print("-" * 60)
    print(f"Summary: {created_count} user(s) created, {skipped_count} user(s) already present.")
    print("=" * 60)

if __name__ == "__main__":
    initialize_demo_users()
