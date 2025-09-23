# Firebase Quick Setup Guide

## Why No Users Appear in Firebase Console

The reason you don't see users in Firebase Console is because the backend was using **mock authentication** instead of real Firebase authentication.

## Quick Fix

I've now switched the backend to use **real Firebase authentication**. Here's what you need to do:

### 1. Set Up Firebase Backend Configuration

Create a `.env` file in `backend/dynamic_rag/` with your Firebase service account:

```env
# Redis Configuration
REDIS_URL=redis://localhost:6379

# Firebase Configuration (choose one option)
# Option 1: Service Account File
FIREBASE_SERVICE_ACCOUNT_PATH=./firebase-service-account.json

# Option 2: JSON Credentials (recommended)
FIREBASE_SERVICE_ACCOUNT_JSON={"type":"service_account","project_id":"your-project-id",...}
```

### 2. Get Firebase Service Account

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project
3. Go to **Project Settings** → **Service Accounts**
4. Click **"Generate new private key"**
5. Download the JSON file
6. Either:
   - Place it in `backend/dynamic_rag/firebase-service-account.json`, OR
   - Copy the JSON content and set it as `FIREBASE_SERVICE_ACCOUNT_JSON` environment variable

### 3. Restart Backend

```bash
cd backend/dynamic_rag
python start_server.py
```

### 4. Test Authentication

1. Go to your frontend (`http://localhost:3000`)
2. Click "Sign In with Google"
3. Complete the Google OAuth flow
4. Check Firebase Console → **Authentication** → **Users**
5. You should now see the signed-in user!

## What Changed

- ✅ **Removed test files** and debug logging
- ✅ **Switched to real Firebase authentication** (no more mock users)
- ✅ **Backend now validates Firebase JWT tokens**
- ✅ **Users will appear in Firebase Console** when they sign in

## Troubleshooting

If you still don't see users:

1. **Check Firebase Console** → **Authentication** → **Sign-in method** → **Google** is enabled
2. **Verify your service account** has the correct permissions
3. **Check backend logs** for Firebase initialization errors
4. **Make sure your frontend `.env.local`** has the correct Firebase config

The authentication should now work end-to-end with real Firebase users appearing in the console!


