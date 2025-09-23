# Firebase Troubleshooting Guide

## Why Users Don't Appear in Firebase Console

The issue is that **Firebase Console shows Authentication users**, but your backend creates **Firestore user records**. These are different!

### Firebase Console Sections:
- **Authentication** → Shows users who signed in with Google OAuth
- **Firestore Database** → Shows user records created by your backend

## Step-by-Step Fix

### 1. Test Firebase Setup

Run the test script to verify everything is working:

```bash
cd backend/dynamic_rag
python test_firebase_setup.py
```

This will test:
- ✅ Firebase initialization
- ✅ Firestore connection
- ✅ User creation
- ✅ User listing

### 2. Check Firestore Database

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Firestore Database** (not Authentication)
4. Look for the **`users`** collection
5. You should see user documents there!

### 3. Check Backend Logs

When you sign in, check your backend logs for:

```
Token verified for user: [user-uid]
Created new user record for [user-uid]
```

If you see these messages, users are being created in Firestore.

### 4. Test User Endpoints

After signing in, test these endpoints:

```bash
# Get your profile (replace TOKEN with your Firebase ID token)
curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
     http://localhost:8000/api/v1/user/profile

# List all users (admin endpoint)
curl -H "Authorization: Bearer YOUR_FIREBASE_TOKEN" \
     http://localhost:8000/api/v1/admin/users
```

### 5. Check Firestore Security Rules

Make sure your Firestore rules allow reading/writing:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Allow users to read/write their own data
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
    
    // Allow reading all users for admin endpoints
    match /users/{document} {
      allow read: if request.auth != null;
    }
  }
}
```

## Common Issues & Solutions

### Issue 1: "Firebase app not initialized"
**Solution**: Check your service account configuration
```bash
# Check if environment variable is set
echo $FIREBASE_SERVICE_ACCOUNT_JSON

# Or check if file exists
ls -la firebase-service-account.json
```

### Issue 2: "Permission denied" errors
**Solution**: Update Firestore security rules (see above)

### Issue 3: "Invalid service account"
**Solution**: Regenerate service account key
1. Go to Firebase Console → Project Settings → Service Accounts
2. Click "Generate new private key"
3. Download and update your configuration

### Issue 4: Users appear in Authentication but not Firestore
**Solution**: This is normal! Check Firestore Database, not Authentication

## Verification Steps

### 1. Check Authentication (Firebase Console)
- Go to **Authentication** → **Users**
- You should see users who signed in with Google

### 2. Check Firestore (Firebase Console)
- Go to **Firestore Database** → **Data**
- Look for **`users`** collection
- You should see user documents with UIDs as document IDs

### 3. Check Backend Logs
- Look for "Created new user record" messages
- Check for any error messages

### 4. Test API Endpoints
- Use the user profile endpoint to verify data
- Check the admin users endpoint to list all users

## Expected Behavior

1. **User signs in with Google** → Appears in Firebase Console → Authentication
2. **Backend validates token** → Creates/updates user in Firestore
3. **User data stored** → Appears in Firebase Console → Firestore Database → users collection

## Still Not Working?

1. **Run the test script**: `python test_firebase_setup.py`
2. **Check backend logs** for error messages
3. **Verify Firestore rules** allow reading/writing
4. **Test with curl** to isolate frontend vs backend issues
5. **Check service account permissions** in Firebase Console

The key is that **Authentication** and **Firestore** are different - users appear in both places, but you need to check the right section!


