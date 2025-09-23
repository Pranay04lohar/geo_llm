"""
User Management API Router for Dynamic RAG System.

What: Exposes user management and profile endpoints.

Why: Provides endpoints for user profile management, quota checking,
     and user administration.

How: Uses Firebase Auth for user authentication and Firestore for
     persistent user data management.
"""

import logging
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
from datetime import datetime

from auth.middleware.firebase_auth_middleware import get_current_user, get_current_user_uid
from auth.services.firebase_auth import firebase_auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()


class UserProfileResponse(BaseModel):
    """Response model for user profile."""
    uid: str
    email: str
    name: str
    picture: str
    email_verified: bool
    subscription_tier: str
    quota_limits: Dict[str, int]
    usage_stats: Dict[str, Any]
    created_at: str
    last_login: str


@router.get(
    "/user/profile",
    response_model=UserProfileResponse,
    summary="Get user profile",
    description="Get the current user's profile information including quota limits and usage stats."
)
async def get_user_profile(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's profile information."""
    try:
        uid = user['uid']
        
        # Get user profile from Firestore
        doc_ref = firebase_auth.db.collection('users').document(uid)
        doc = doc_ref.get()
        
        if not doc.exists:
            raise HTTPException(
                status_code=404,
                detail="User profile not found"
            )
        
        user_data = doc.to_dict()
        
        return UserProfileResponse(
            uid=user_data['uid'],
            email=user_data.get('email', ''),
            name=user_data.get('name', ''),
            picture=user_data.get('picture', ''),
            email_verified=user_data.get('email_verified', False),
            subscription_tier=user_data.get('subscription_tier', 'free'),
            quota_limits=user_data.get('quota_limits', {}),
            usage_stats=user_data.get('usage_stats', {}),
            created_at=user_data.get('created_at', datetime.utcnow()).isoformat() if isinstance(user_data.get('created_at'), datetime) else user_data.get('created_at', ''),
            last_login=user_data.get('last_login', datetime.utcnow()).isoformat() if isinstance(user_data.get('last_login'), datetime) else user_data.get('last_login', '')
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting user profile: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving user profile: {str(e)}"
        )


@router.get(
    "/admin/users",
    summary="List all users (Admin only)",
    description="Get a list of all users in the system. This is an admin endpoint."
)
async def list_all_users(
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """List all users (admin endpoint)."""
    try:
        # Get all users from Firestore
        users_ref = firebase_auth.db.collection('users')
        docs = users_ref.stream()
        
        users = []
        for doc in docs:
            user_data = doc.to_dict()
            users.append({
                'uid': user_data.get('uid'),
                'email': user_data.get('email'),
                'name': user_data.get('name'),
                'subscription_tier': user_data.get('subscription_tier', 'free'),
                'created_at': user_data.get('created_at').isoformat() if isinstance(user_data.get('created_at'), datetime) else user_data.get('created_at'),
                'last_login': user_data.get('last_login').isoformat() if isinstance(user_data.get('last_login'), datetime) else user_data.get('last_login')
            })
        
        return {
            'total_users': len(users),
            'users': users
        }
        
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving users: {str(e)}"
        )


@router.get(
    "/user/health",
    summary="User service health check",
    description="Check the health of the user service and Firestore connection."
)
async def user_health_check():
    """Health check for the user service."""
    try:
        # Test Firestore connection
        firestore_status = "healthy"
        try:
            # Try to get a test document
            test_doc = firebase_auth.db.collection('test').document('health').get()
            if not test_doc.exists:
                firebase_auth.db.collection('test').document('health').set({'status': 'ok'})
        except Exception as e:
            firestore_status = f"unhealthy: {str(e)}"
        
        return {
            "status": "healthy" if firestore_status == "healthy" else "degraded",
            "firestore": firestore_status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"User health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail=f"User service health check failed: {str(e)}"
        )


