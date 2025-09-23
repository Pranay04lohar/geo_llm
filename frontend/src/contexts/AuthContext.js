/**
 * Authentication Context for React Components
 * 
 * What: Provides authentication state and methods to all components
 * Why: Centralizes authentication logic and provides consistent user state
 * How: Uses React Context API with Firebase Auth state management
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { 
  onAuthStateChange, 
  signInWithGoogle, 
  signOutUser, 
  getCurrentUserToken,
  getCurrentUser 
} from '../lib/firebase';

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [token, setToken] = useState(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChange(async (user) => {
      setUser(user);
      
      if (user) {
        try {
          // Get fresh token
          const idToken = await getCurrentUserToken();
          setToken(idToken);
        } catch (error) {
          console.error('Error getting token:', error);
          setToken(null);
        }
      } else {
        setToken(null);
      }
      
      setLoading(false);
    });

    return () => unsubscribe();
  }, []);

  const signIn = async () => {
    try {
      setLoading(true);
      await signInWithGoogle();
    } catch (error) {
      console.error('Sign in error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      setLoading(true);
      await signOutUser();
      setToken(null);
    } catch (error) {
      console.error('Sign out error:', error);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const refreshToken = async () => {
    if (user) {
      try {
        const newToken = await getCurrentUserToken();
        setToken(newToken);
        return newToken;
      } catch (error) {
        console.error('Error refreshing token:', error);
        return null;
      }
    }
    return null;
  };

  const value = {
    user,
    token,
    loading,
    signIn,
    signOut,
    refreshToken,
    isAuthenticated: !!user,
    userInfo: user ? {
      uid: user.uid,
      email: user.email,
      name: user.displayName,
      picture: user.photoURL,
      emailVerified: user.emailVerified
    } : null
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};