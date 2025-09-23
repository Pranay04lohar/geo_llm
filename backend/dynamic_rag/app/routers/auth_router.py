"""
Authentication utility routes.

What: Endpoints to verify auth status and fetch current user info.
Why:  Frontend can quickly determine if a user is logged in and backend sees the token.
How:  Uses Firebase auth middleware dependencies to read user from request state.
"""

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any

from auth.middleware.firebase_auth_middleware import (
    get_current_user,
    get_optional_user,
)


router = APIRouter()


class AuthStatus(BaseModel):
    authenticated: bool
    user: Optional[Dict[str, Any]] = None


@router.get("/auth/status", response_model=AuthStatus, summary="Auth status (no error)")
async def auth_status(request: Request, user: Optional[dict] = Depends(get_optional_user)):
    """Return auth status without raising if unauthenticated."""
    return AuthStatus(authenticated=bool(user), user=user)


@router.get("/auth/me", response_model=AuthStatus, summary="Current user (requires auth)")
async def auth_me(request: Request, user: dict = Depends(get_current_user)):
    """Return current user; raises 401 if unauthenticated."""
    return AuthStatus(authenticated=True, user=user)

 