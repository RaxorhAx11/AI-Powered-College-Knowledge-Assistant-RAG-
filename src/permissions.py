"""
Role-Based Access Control (RBAC) & Session Management Layer (Phase 6.1).

Centralized authorization enforcement preventing unauthorized feature execution.
Manages user session state and guarantees chat history isolation between users.
"""

from typing import Optional, Dict, Any

ROLE_STUDENT = "student"
ROLE_FACULTY = "faculty"
ROLE_ADMIN = "admin"

ROLE_LEVELS = {
    ROLE_STUDENT: 1,
    ROLE_FACULTY: 2,
    ROLE_ADMIN: 3
}

def has_role(user_role: Optional[str], required_role: str) -> bool:
    """
    Check whether a user role meets or exceeds the required role level.
    Hierarchy: admin (3) >= faculty (2) >= student (1).
    """
    if not user_role or user_role not in ROLE_LEVELS:
        return False
    if required_role not in ROLE_LEVELS:
        return False
    return ROLE_LEVELS[user_role] >= ROLE_LEVELS[required_role]

def require_role(required_role: str, user: Optional[Dict[str, Any]] = None, allow_guest: bool = False) -> bool:
    """
    Server-side authorization check.
    Raises PermissionError if unauthorized.
    Allows unauthenticated Guest Students for student-level features.
    """
    if user is None:
        user = {"authenticated": False, "role": ROLE_STUDENT, "username": "Guest Student"}
    
    is_auth = user.get("authenticated", False)
    user_role = user.get("role", ROLE_STUDENT)
    
    if required_role == ROLE_STUDENT or allow_guest:
        if has_role(user_role, required_role):
            return True

    if not is_auth:
        raise PermissionError("Authentication required. Please log in as a registered user.")
    
    if not has_role(user_role, required_role):
        raise PermissionError(f"You do not have permission to access {required_role} area.")
    
    return True

def login_user(session_state: Any, user_dict: Dict[str, Any]) -> None:
    """
    Update session state upon successful authentication and isolate conversation history.
    """
    session_state["authenticated"] = True
    session_state["user_id"] = user_dict["id"]
    session_state["username"] = user_dict["username"]
    session_state["role"] = user_dict["role"]
    # Enforce chat history isolation upon user login
    session_state["messages"] = []

def logout_user(session_state: Any) -> None:
    """
    Clear authentication session state and purge active conversation history.
    """
    session_state["authenticated"] = False
    session_state.pop("user_id", None)
    session_state.pop("username", None)
    session_state.pop("role", None)
    # Clear conversation messages on logout to prevent cross-user leaks
    session_state["messages"] = []

def get_current_user(session_state: Any) -> Optional[Dict[str, Any]]:
    """
    Retrieve current active user info from session state if authenticated.
    """
    if getattr(session_state, "authenticated", False) or (isinstance(session_state, dict) and session_state.get("authenticated")):
        getter = getattr(session_state, "get", None) or (lambda k, d=None: session_state.get(k, d))
        return {
            "authenticated": True,
            "id": getter("user_id"),
            "username": getter("username"),
            "role": getter("role", ROLE_STUDENT)
        }
    return {
        "authenticated": False,
        "id": None,
        "username": "Guest Student",
        "role": ROLE_STUDENT
    }
