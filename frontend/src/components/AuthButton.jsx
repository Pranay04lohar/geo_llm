/**
 * Authentication Button Component
 * 
 * What: Provides login/logout functionality with user profile display
 * Why: Centralizes authentication UI and provides consistent user experience
 * How: Uses Firebase Auth context and displays user info when authenticated
 */

import React from 'react';
import { useAuth } from '../contexts/AuthContext';
import { FiLogIn, FiLogOut, FiUser, FiLoader } from 'react-icons/fi';
import { useAlert } from '@/components/AlertProvider';

const AuthButton = ({ className = '' }) => {
  const { user, loading, signIn, signOut, userInfo } = useAuth();
  const { showSuccess, showError } = useAlert();

  const handleSignIn = async () => {
    try {
      await signIn();
      showSuccess('Signed in', `Welcome${userInfo?.name ? `, ${userInfo.name}` : ''}!`);
    } catch (error) {
      console.error('Sign in failed:', error);
      showError('Sign in failed', error?.message || 'Unable to sign in. Please try again.');
    }
  };

  const handleSignOut = async () => {
    try {
      await signOut();
      showSuccess('Signed out', 'You have been signed out successfully.');
    } catch (error) {
      console.error('Sign out failed:', error);
      showError('Sign out failed', error?.message || 'Unable to sign out. Please try again.');
    }
  };

  if (loading) {
    return (
      <button 
        disabled 
        className={`flex items-center space-x-2 px-4 py-2 rounded-lg bg-gray-100 text-gray-500 ${className}`}
      >
        <FiLoader className="animate-spin" />
        <span>Loading...</span>
      </button>
    );
  }

  if (user) {
    return (
      <div className={`flex items-center space-x-3 ${className}`}>
        {/* User Profile */}
        <div className="flex items-center space-x-2">
          {userInfo?.picture ? (
            <img 
              src={userInfo.picture} 
              alt={userInfo.name || 'User'} 
              className="w-8 h-8 rounded-full"
            />
          ) : (
            <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center">
              <FiUser className="w-4 h-4 text-white" />
            </div>
          )}
          <div className="hidden sm:block">
            <p className="text-sm font-medium text-gray-900">
              {userInfo?.name || 'User'}
            </p>
            <p className="text-xs text-gray-500">
              {userInfo?.email}
            </p>
          </div>
        </div>

        {/* Sign Out Button */}
        <button
          onClick={handleSignOut}
          className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 transition-colors"
        >
          <FiLogOut className="w-4 h-4" />
          <span className="hidden sm:inline">Sign Out</span>
        </button>
      </div>
    );
  }

  return (
    <button
      onClick={handleSignIn}
      className={`flex items-center space-x-2 px-4 py-2 rounded-lg bg-emerald-600 text-white hover:bg-emerald-500 transition-colors ${className}`}
    >
      <FiLogIn className="w-4 h-4" />
      <span>Sign In with Google</span>
    </button>
  );
};

export default AuthButton;