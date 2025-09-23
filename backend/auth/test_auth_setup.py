#!/usr/bin/env python3
"""
Authentication Setup Test Script

This script helps you test if the authentication system is properly configured and working.
Run this script to verify your authentication setup before testing the full application.
"""

import os
import sys
import asyncio
from datetime import datetime

# Add the parent directory to Python path so we can import auth
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from auth.services.firebase_auth import firebase_auth

async def test_auth_connection():
    """Test authentication system connection and user creation."""
    print("🔥 Testing Authentication Setup...")
    print("=" * 50)
    
    try:
        # Test 1: Check if Firebase is initialized
        print("1. Testing Firebase initialization...")
        if firebase_auth.app is None:
            print("❌ Firebase app not initialized")
            return False
        print("✅ Firebase app initialized")
        
        # Test 2: Check Firestore connection
        print("\n2. Testing Firestore connection...")
        try:
            # Try to create a test document
            test_doc = firebase_auth.db.collection('test').document('connection_test')
            test_doc.set({
                'status': 'connected',
                'timestamp': datetime.utcnow(),
                'message': 'Authentication setup test successful'
            })
            print("✅ Firestore connection successful")
            
            # Clean up test document
            test_doc.delete()
            print("✅ Test document cleaned up")
            
        except Exception as e:
            print(f"❌ Firestore connection failed: {e}")
            return False
        
        # Test 3: Test user creation
        print("\n3. Testing user creation...")
        test_user_info = {
            'uid': 'test-user-123',
            'email': 'test@example.com',
            'name': 'Test User',
            'picture': 'https://example.com/avatar.jpg',
            'email_verified': True
        }
        
        success = await firebase_auth.create_or_update_user(test_user_info)
        if success:
            print("✅ User creation successful")
            
            # Check if user exists in Firestore
            doc_ref = firebase_auth.db.collection('users').document('test-user-123')
            doc = doc_ref.get()
            if doc.exists:
                print("✅ User found in Firestore")
                user_data = doc.to_dict()
                print(f"   - Email: {user_data.get('email')}")
                print(f"   - Name: {user_data.get('name')}")
                print(f"   - Subscription: {user_data.get('subscription_tier')}")
            else:
                print("❌ User not found in Firestore")
                return False
        else:
            print("❌ User creation failed")
            return False
        
        # Test 4: List all users
        print("\n4. Testing user listing...")
        try:
            users_ref = firebase_auth.db.collection('users')
            docs = users_ref.stream()
            user_count = 0
            for doc in docs:
                user_count += 1
                user_data = doc.to_dict()
                print(f"   - User {user_count}: {user_data.get('email')} ({doc.id})")
            
            print(f"✅ Found {user_count} users in Firestore")
            
        except Exception as e:
            print(f"❌ User listing failed: {e}")
            return False
        
        print("\n" + "=" * 50)
        print("🎉 All authentication tests passed!")
        print("\nNext steps:")
        print("1. Update your dynamic_rag app to import from auth package")
        print("2. Start your backend server")
        print("3. Test the authentication endpoints")
        print("4. Sign in with Google in the frontend")
        print("5. Check Firebase Console → Firestore Database → users collection")
        
        return True
        
    except Exception as e:
        print(f"❌ Authentication test failed: {e}")
        print("\nTroubleshooting:")
        print("1. Check your Firebase service account configuration")
        print("2. Make sure FIREBASE_SERVICE_ACCOUNT_JSON is set correctly")
        print("3. Verify your Firebase project has Firestore enabled")
        print("4. Check that your service account has the right permissions")
        return False

async def main():
    """Main test function."""
    success = await test_auth_connection()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())
