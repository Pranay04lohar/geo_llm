"""
Firebase Authentication Service for Dynamic RAG System.

What: Handles Firebase Admin SDK initialization and JWT token validation.

Why: Provides secure authentication using Firebase Auth with Google OAuth,
     allowing users to authenticate once and maintain persistent sessions
     while backend manages ephemeral Redis sessions.

How: Initializes Firebase Admin SDK, validates JWT tokens from frontend,
     extracts user UID, and provides user management functions.
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google.auth.exceptions import GoogleAuthError

logger = logging.getLogger(__name__)


class FirebaseAuthService:
    """Firebase authentication service for JWT validation and user management."""
    
    def __init__(self):
        """Initialize Firebase Admin SDK."""
        self.app = None
        self.db = None
        # Load backend/.env for local development (no-op in prod if vars already set)
        try:
            backend_root = Path(__file__).resolve().parents[2]
            env_path = backend_root / ".env"
            # Only attempt to load if the file exists to avoid surprises in prod
            if env_path.exists():
                load_dotenv(dotenv_path=str(env_path), override=False)
                logger.info("Loaded environment variables from backend/.env")
        except Exception as e:
            logger.warning(f"Could not load backend/.env: {e}")

        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Initialize Firebase Admin SDK with credentials."""
        try:
            # Check if Firebase is already initialized
            if firebase_admin._apps:
                self.app = firebase_admin.get_app()
                logger.info("Using existing Firebase app")
            else:
                # Initialization order:
                # 1) Use explicit service account file if provided
                service_account_path = os.getenv("FIREBASE_SERVICE_ACCOUNT_PATH")
                if service_account_path:
                    resolved_path = os.path.expanduser(os.path.expandvars(service_account_path))
                    if not os.path.isabs(resolved_path):
                        # Resolve relative to backend root if a relative path was given
                        backend_root = Path(__file__).resolve().parents[2]
                        resolved_path = str((backend_root / resolved_path).resolve())
                    if not os.path.exists(resolved_path):
                        raise RuntimeError(
                            f"FIREBASE_SERVICE_ACCOUNT_PATH not found: {resolved_path}"
                        )
                    cred = credentials.Certificate(resolved_path)
                    self.app = firebase_admin.initialize_app(cred)
                    logger.info("✅ Firebase initialized with service account file")
                else:
                    # 2) Use inline JSON if provided
                    service_account_json = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
                    if service_account_json:
                        try:
                            cred_dict = json.loads(service_account_json)
                        except json.JSONDecodeError as e:
                            raise RuntimeError(
                                f"FIREBASE_SERVICE_ACCOUNT_JSON contains invalid JSON: {e}"
                            )
                        cred = credentials.Certificate(cred_dict)
                        self.app = firebase_admin.initialize_app(cred)
                        logger.info("✅ Firebase initialized with inline JSON credentials")
                    else:
                        # 3) Fail fast with a descriptive error
                        raise RuntimeError(
                            "Firebase credentials not provided. Set either FIREBASE_SERVICE_ACCOUNT_PATH "
                            "(absolute path to JSON) or FIREBASE_SERVICE_ACCOUNT_JSON (inline JSON)."
                        )

            # Initialize Firestore
            self.db = firestore.client()
            logger.info("✅ Firebase Auth service initialized successfully")

        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {e}")
            raise
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify Firebase ID token and return user information.
        
        Args:
            token: Firebase ID token from frontend
            
        Returns:
            Dict containing user info (uid, email, etc.) or None if invalid
        """
        try:
            # Verify the ID token
            decoded_token = auth.verify_id_token(token)
            
            # Extract user information
            user_info = {
                'uid': decoded_token['uid'],
                'email': decoded_token.get('email'),
                'name': decoded_token.get('name'),
                'picture': decoded_token.get('picture'),
                'email_verified': decoded_token.get('email_verified', False),
                'auth_time': decoded_token.get('auth_time'),
                'exp': decoded_token.get('exp'),
                'iat': decoded_token.get('iat')
            }
            
            # Create or update user record in Firestore
            await self.create_or_update_user(user_info)
            
            logger.info(f"Token verified for user: {user_info['uid']}")
            return user_info
            
        except auth.InvalidIdTokenError as e:
            logger.warning(f"Invalid ID token: {e}")
            return None
        except auth.ExpiredIdTokenError as e:
            logger.warning(f"Expired ID token: {e}")
            return None
        except Exception as e:
            logger.error(f"Token verification error: {e}")
            return None
    
    async def create_or_update_user(self, user_info: Dict[str, Any]) -> bool:
        """
        Create or update user record in Firestore.
        
        Args:
            user_info: User information from Firebase Auth
            
        Returns:
            True if successful, False otherwise
        """
        try:
            uid = user_info['uid']
            
            # Check if user already exists
            doc_ref = self.db.collection('users').document(uid)
            doc = doc_ref.get()
            
            if doc.exists:
                # Update existing user
                doc_ref.update({
                    'last_login': datetime.utcnow(),
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'email_verified': user_info.get('email_verified', False)
                })
                logger.info(f"Updated user record for {uid}")
            else:
                # Create new user
                user_data = {
                    'uid': uid,
                    'email': user_info.get('email'),
                    'name': user_info.get('name'),
                    'picture': user_info.get('picture'),
                    'email_verified': user_info.get('email_verified', False),
                    'created_at': datetime.utcnow(),
                    'last_login': datetime.utcnow(),
                    'subscription_tier': 'free',
                    'quota_limits': {
                        'max_files_per_day': 10,
                        'max_storage_mb': 100,
                        'max_sessions_per_day': 5,
                        'max_queries_per_day': 100
                    },
                    'usage_stats': {
                        'files_uploaded_today': 0,
                        'storage_used_mb': 0,
                        'sessions_created_today': 0,
                        'queries_made_today': 0,
                        'last_reset_date': datetime.utcnow().date().isoformat()
                    },
                    'settings': {
                        'notifications_enabled': True,
                        'data_retention_days': 7
                    }
                }
                
                doc_ref.set(user_data)
                logger.info(f"Created new user record for {uid}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating/updating user {user_info.get('uid', 'unknown')}: {e}")
            return False


# Global instance
firebase_auth = FirebaseAuthService()
