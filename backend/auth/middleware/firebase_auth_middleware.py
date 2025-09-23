"""
Firebase Authentication Middleware for Dynamic RAG System.

What: Middleware to validate Firebase JWT tokens on all protected API routes.

Why: Ensures all API requests are authenticated and provides user context
     for quota enforcement and session management.

How: Extracts Bearer token from Authorization header, validates with Firebase,
     and injects user information into request state.
"""

import logging
from typing import Optional
from fastapi import HTTPException, Request, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from auth.services.firebase_auth import firebase_auth

logger = logging.getLogger(__name__)

# Security scheme for OpenAPI documentation
security = HTTPBearer(auto_error=False)


class FirebaseAuthMiddleware(BaseHTTPMiddleware):
    """Middleware to validate Firebase JWT tokens."""
    
    def __init__(self, app, excluded_paths: Optional[list] = None):
        super().__init__(app)
        self.excluded_paths = excluded_paths or [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and validate authentication."""
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # Extract token from Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=401,
                detail="Missing or invalid Authorization header. Expected 'Bearer <token>'"
            )
        
        token = auth_header.split(" ")[1]
        
        # Verify token with Firebase
        user_info = await firebase_auth.verify_token(token)
        if not user_info:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired authentication token"
            )
        
        # Store user info in request state
        request.state.user = user_info
        
        # Continue to the next middleware/route
        response = await call_next(request)
        return response


async def get_current_user(request: Request) -> dict:
    """
    Dependency to get current authenticated user.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User information dictionary
        
    Raises:
        HTTPException: If user is not authenticated
    """
    if not hasattr(request.state, 'user'):
        raise HTTPException(
            status_code=401,
            detail="Authentication required"
        )
    
    return request.state.user


async def get_current_user_uid(request: Request) -> str:
    """
    Dependency to get current user UID.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User UID string
        
    Raises:
        HTTPException: If user is not authenticated
    """
    user = await get_current_user(request)
    return user['uid']


async def get_optional_user(request: Request) -> Optional[dict]:
    """
    Dependency to get current user if authenticated, None otherwise.
    
    Args:
        request: FastAPI request object
        
    Returns:
        User information dictionary or None
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def require_auth():
    """
    Decorator to require authentication on routes.
    This is used as a dependency in FastAPI route decorators.
    """
    return Depends(get_current_user)


def require_user_uid():
    """
    Dependency to require authentication and return user UID.
    """
    return Depends(get_current_user_uid)


