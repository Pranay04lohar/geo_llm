# Authentication Migration Guide

## Overview

The authentication system has been moved from `backend/dynamic_rag/app/` to a separate `backend/auth/` package for better organization and modularity.

## New Structure

```
backend/
├── auth/                        # Authentication package (NEW)
│   ├── services/
│   │   └── firebase_auth.py
│   ├── middleware/
│   │   └── firebase_auth_middleware.py
│   ├── routers/
│   │   └── user_router.py
│   ├── requirements.txt
│   ├── test_auth_setup.py
│   └── README.md
└── dynamic_rag/                 # RAG system (UPDATED)
    └── app/
        ├── main.py              # Updated imports
        └── routers/             # Updated imports
```

## Changes Made

### 1. Moved Files

**From:** `backend/dynamic_rag/app/services/firebase_auth.py`  
**To:** `backend/auth/services/firebase_auth.py`

**From:** `backend/dynamic_rag/app/middleware/firebase_auth_middleware.py`  
**To:** `backend/auth/middleware/firebase_auth_middleware.py`

**From:** `backend/dynamic_rag/app/routers/user_router.py`  
**To:** `backend/auth/routers/user_router.py`

### 2. Updated Imports

**In `backend/dynamic_rag/app/main.py`:**
```python
# OLD
from app.middleware.firebase_auth_middleware import FirebaseAuthMiddleware
from app.routers import user_router

# NEW
from auth.middleware.firebase_auth_middleware import FirebaseAuthMiddleware
from auth.routers.user_router import router as user_router
```

**In `backend/dynamic_rag/app/routers/ingest_router.py`:**
```python
# OLD
from app.middleware.firebase_auth_middleware import get_current_user_uid

# NEW
from auth.middleware.firebase_auth_middleware import get_current_user_uid
```

**In `backend/dynamic_rag/app/routers/retrieve_router.py`:**
```python
# OLD
from app.middleware.firebase_auth_middleware import get_current_user_uid

# NEW
from auth.middleware.firebase_auth_middleware import get_current_user_uid
```

### 3. Updated Import Paths in Auth Package

**In `backend/auth/middleware/firebase_auth_middleware.py`:**
```python
# OLD
from app.services.firebase_auth import firebase_auth

# NEW
from auth.services.firebase_auth import firebase_auth
```

**In `backend/auth/routers/user_router.py`:**
```python
# OLD
from app.middleware.firebase_auth_middleware import get_current_user, get_current_user_uid
from app.services.firebase_auth import firebase_auth

# NEW
from auth.middleware.firebase_auth_middleware import get_current_user, get_current_user_uid
from auth.services.firebase_auth import firebase_auth
```

## Migration Steps

### 1. Install Auth Package Dependencies

```bash
cd backend/auth
pip install -r requirements.txt
```

### 2. Test Auth Package

```bash
cd backend/auth
python test_auth_setup.py
```

### 3. Test Dynamic RAG Integration

```bash
cd backend/dynamic_rag
python start_server.py
```

### 4. Verify Everything Works

1. **Backend starts** without import errors
2. **Authentication endpoints** work (`/api/v1/user/profile`)
3. **File upload** works with authentication
4. **Query endpoints** work with authentication
5. **Frontend** can sign in and use the system

## Benefits of New Structure

### 1. **Separation of Concerns**
- Authentication logic is isolated
- RAG system focuses on its core functionality
- Easier to maintain and test

### 2. **Reusability**
- Auth package can be used by other services
- Clear API boundaries
- Independent versioning

### 3. **Modularity**
- Auth package can be developed independently
- Clear dependencies
- Easier to deploy separately

### 4. **Organization**
- Logical grouping of related functionality
- Clear package structure
- Better documentation

## Testing the Migration

### 1. Test Auth Package

```bash
cd backend/auth
python test_auth_setup.py
```

**Expected Output:**
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

### 2. Test Dynamic RAG Integration

```bash
cd backend/dynamic_rag
python start_server.py
```

**Expected Output:**
```
🚀 Starting Dynamic RAG System...
📊 Redis URL: redis://localhost:6379
🔧 GPU Available: False
✅ Firebase Auth service initialized successfully
✅ RAG Store initialized successfully
```

### 3. Test API Endpoints

```bash
# Test user profile endpoint
curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
     http://localhost:8000/api/v1/user/profile

# Test admin users endpoint
curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
     http://localhost:8000/api/v1/admin/users
```

## Rollback Plan

If you need to rollback:

1. **Move files back** to `backend/dynamic_rag/app/`
2. **Update imports** in `main.py` and routers
3. **Update import paths** in auth files
4. **Test** that everything works

## Troubleshooting

### Common Issues

1. **Import Errors**: Check Python path includes both `backend/auth` and `backend/dynamic_rag`
2. **Module Not Found**: Ensure all `__init__.py` files are present
3. **Firebase Errors**: Check service account configuration
4. **Permission Errors**: Verify Firestore security rules

### Debug Steps

1. **Check imports**: `python -c "from auth.services.firebase_auth import firebase_auth"`
2. **Test auth package**: `python backend/auth/test_auth_setup.py`
3. **Check logs**: Look for import or initialization errors
4. **Verify paths**: Ensure all files are in correct locations

## Next Steps

1. **Test the migration** using the steps above
2. **Update documentation** to reflect new structure
3. **Consider versioning** the auth package
4. **Plan for future** auth package enhancements

The migration maintains all existing functionality while providing better organization and modularity!


