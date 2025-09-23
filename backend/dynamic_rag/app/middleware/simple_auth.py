"""
Simple Authentication Middleware for Development

What: Provides basic authentication for development/testing
Why: Allows testing without full Firebase setup
How: Accepts any token or no token for development
"""

import logging
from typing import Optional
from fastapi import HTTPException, Request, Depends
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)


class SimpleAuthMiddleware(BaseHTTPMiddleware):
    """Simple middleware for development - accepts any token."""
    
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
        """Process request with simple authentication."""
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)
        
        # Skip authentication for OPTIONS requests (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)
        
        # For development, accept any token or no token
        auth_header = request.headers.get("Authorization")
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            # Mock user info for development
            request.state.user = {
                'uid': 'dev-user-123',
                'email': 'dev@example.com',
                'name': 'Development User',
                'picture': None,
                'email_verified': True
            }
            logger.info(f"Development mode: Using mock user with token: {token[:10]}...")
        else:
            # No token provided - use default user for development
            request.state.user = {
                'uid': 'default-user',
                'email': 'default@example.com',
                'name': 'Default User',
                'picture': None,
                'email_verified': True
            }
            logger.info("Development mode: Using default user (no token)")
        
        # Continue to the next middleware/route
        response = await call_next(request)
        return response


async def get_current_user(request: Request) -> dict:
    """Get current authenticated user (development mode)."""
    if not hasattr(request.state, 'user'):
        return {
            'uid': 'default-user',
            'email': 'default@example.com',
            'name': 'Default User',
            'picture': None,
            'email_verified': True
        }
    
    return request.state.user


async def get_current_user_uid(request: Request) -> str:
    """Get current user UID (development mode)."""
    user = await get_current_user(request)
    return user['uid']


