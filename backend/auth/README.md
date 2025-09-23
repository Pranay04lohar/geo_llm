# Authentication Package

This package contains all authentication-related components for the Dynamic RAG system.

## Structure

```
backend/auth/
├── __init__.py
├── services/
│   ├── __init__.py
│   └── firebase_auth.py          # Firebase authentication service
├── middleware/
│   ├── __init__.py
│   └── firebase_auth_middleware.py  # Authentication middleware
├── routers/
│   ├── __init__.py
│   └── user_router.py            # User management endpoints
├── requirements.txt              # Auth package dependencies
├── test_auth_setup.py           # Test script
└── README.md                    # This file
```

## Features

- **Firebase Authentication**: Google OAuth integration
- **User Management**: Create, update, and manage user profiles
- **JWT Validation**: Secure token validation middleware
- **Firestore Integration**: Persistent user data storage
- **Admin Endpoints**: User administration and health checks

## Setup

### 1. Install Dependencies

```bash
cd backend/auth
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Set up your Firebase service account:

```bash
# Option 1: Service Account File
export FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json

# Option 2: JSON Credentials (recommended)
export FIREBASE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"your-project",...}'
```

### 3. Test Setup

```bash
python test_auth_setup.py
```

## Usage

### In Dynamic RAG App

```python
# Import authentication components
from auth.middleware.firebase_auth_middleware import FirebaseAuthMiddleware, get_current_user_uid
from auth.routers.user_router import router as user_router

# Add middleware to FastAPI app
app.add_middleware(FirebaseAuthMiddleware)

# Include user router
app.include_router(user_router, prefix="/api/v1", tags=["users"])

# Use in routes
async def my_route(user_id: str = Depends(get_current_user_uid)):
    # user_id contains the authenticated user's UID
    pass
```

## API Endpoints

### User Management
- `GET /api/v1/user/profile` - Get user profile
- `GET /api/v1/admin/users` - List all users (admin)
- `GET /api/v1/user/health` - Health check

### Authentication
- All endpoints require `Authorization: Bearer <firebase-token>` header
- Middleware automatically validates tokens and injects user context

## Testing

Run the test script to verify everything is working:

```bash
python test_auth_setup.py
```

Expected output:
```
🔥 Testing Authentication Setup...
==================================================
1. Testing Firebase initialization...
✅ Firebase app initialized

2. Testing Firestore connection...
✅ Firestore connection successful
✅ Test document cleaned up

3. Testing user creation...
✅ User creation successful
✅ User found in Firestore
   - Email: test@example.com
   - Name: Test User
   - Subscription: free

4. Testing user listing...
   - User 1: test@example.com (test-user-123)
✅ Found 1 users in Firestore

==================================================
🎉 All authentication tests passed!
```

## Integration with Dynamic RAG

The authentication package is designed to be imported and used by the Dynamic RAG system:

1. **Middleware**: Validates Firebase tokens on all protected routes
2. **User Service**: Creates and manages user records in Firestore
3. **Dependencies**: Provides user context to route handlers
4. **Admin Tools**: User management and health monitoring

## Troubleshooting

### Common Issues

1. **Import Errors**: Make sure the auth package is in your Python path
2. **Firebase Errors**: Check your service account configuration
3. **Permission Errors**: Verify Firestore security rules
4. **Token Errors**: Ensure frontend is sending valid Firebase tokens

### Debug Mode

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Security

- **JWT Validation**: All tokens are validated with Firebase
- **User Isolation**: Users can only access their own data
- **Admin Endpoints**: Protected with authentication
- **CORS**: Properly configured for frontend integration

## Dependencies

- `firebase-admin`: Firebase Admin SDK
- `google-auth`: Google authentication libraries
- `google-auth-oauthlib`: OAuth integration
- `google-auth-httplib2`: HTTP transport for Google Auth


