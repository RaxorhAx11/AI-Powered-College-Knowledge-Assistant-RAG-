"""
Authentication API Router (Phase 7.2).
Exposes login, signup, logout, and current user info.
Reuses existing src/auth.py and SQLite user database.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Response, Depends, status
from pydantic import BaseModel, Field

from src.auth import authenticate_user, create_user
from backend.dependencies import (
    create_session,
    revoke_session,
    get_session_token_from_request,
    get_current_user_optional
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class SignupRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=4)
    role: str = Field(default="student")

class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: Optional[int]
    username: str
    role: str
    authenticated: bool
    token: Optional[str] = None

@router.post("/signup", response_model=UserResponse)
def signup(payload: SignupRequest, response: Response):
    """Register a new user account (defaults strictly to student role)."""
    clean_username = payload.username.strip().lower()
    clean_role = payload.role.strip().lower()

    if clean_role != "student":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Public registration is only allowed for the Student role. Faculty and Admin roles must be assigned by an Administrator."
        )
    
    success = create_user(clean_username, payload.password, "student")
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken or registration invalid."
        )
    
    user_dict = authenticate_user(clean_username, payload.password)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="User registration succeeded but login failed."
        )
    
    token = create_session(user_dict)
    response.set_cookie(
        key="raxel_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    return {
        "id": user_dict["id"],
        "username": user_dict["username"],
        "role": user_dict["role"],
        "authenticated": True,
        "token": token
    }

@router.post("/login", response_model=UserResponse)
def login(payload: LoginRequest, response: Response):
    """Authenticate user credentials and start session."""
    user_dict = authenticate_user(payload.username, payload.password)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password."
        )
    
    token = create_session(user_dict)
    response.set_cookie(
        key="raxel_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False
    )
    
    return {
        "id": user_dict["id"],
        "username": user_dict["username"],
        "role": user_dict["role"],
        "authenticated": True,
        "token": token
    }

@router.post("/logout")
def logout(response: Response, token: Optional[str] = Depends(get_session_token_from_request)):
    """Clear user session."""
    if token:
        revoke_session(token)
    response.delete_cookie(key="raxel_session")
    return {"message": "Successfully logged out."}

@router.get("/me", response_model=UserResponse)
def get_me(user: dict = Depends(get_current_user_optional), token: Optional[str] = Depends(get_session_token_from_request)):
    """Retrieve current authenticated or guest user info."""
    return {
        "id": user.get("id"),
        "username": user.get("username", "Guest Student"),
        "role": user.get("role", "student"),
        "authenticated": user.get("authenticated", False),
        "token": token if user.get("authenticated", False) else None
    }
