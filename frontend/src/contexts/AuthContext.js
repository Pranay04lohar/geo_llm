// "use client";

// import React, {
//   createContext,
//   useContext,
//   useMemo,
//   useState,
//   useCallback,
// } from "react";

// // Create context
// const AuthContext = createContext(null);

// // Safe stub returned when no provider is mounted
// const useAuthFallback = () => ({
//   user: null,
//   userInfo: null,
//   loading: false,
//   token: null,
//   isAuthenticated: false,
//   signIn: async () => {
//     // No-op stub
//     return null;
//   },
//   signOut: async () => {
//     // No-op stub
//     return null;
//   },
// });

// export function useAuth() {
//   const ctx = useContext(AuthContext);
//   return ctx ?? useAuthFallback();
// }

// export function AuthProvider({ children }) {
//   const [user, setUser] = useState(null);
//   const [userInfo, setUserInfo] = useState(null);
//   const [token, setToken] = useState(null);
//   const [loading, setLoading] = useState(false);
//   const demoAuthEnabled = process.env.NEXT_PUBLIC_DEMO_AUTH === "true";

//   const signIn = useCallback(async () => {
//     setLoading(true);
//     try {
//       // TODO: Integrate real auth here (e.g., Firebase, NextAuth, custom backend)
//       // By default, prevent auto sign-in and require a real provider.
//       if (!demoAuthEnabled) {
//         throw new Error(
//           "Authentication is not configured. Set NEXT_PUBLIC_DEMO_AUTH=true to enable demo sign-in, or integrate a real provider."
//         );
//       }
//       // Demo sign-in path (explicitly enabled only)
//       const fakeUser = { id: "local-user" };
//       const fakeUserInfo = { name: "User", email: "user@example.com" };
//       setUser(fakeUser);
//       setUserInfo(fakeUserInfo);
//       setToken(null);
//       return fakeUser;
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   const signOut = useCallback(async () => {
//     setLoading(true);
//     try {
//       setUser(null);
//       setUserInfo(null);
//       setToken(null);
//     } finally {
//       setLoading(false);
//     }
//   }, []);

//   const value = useMemo(
//     () => ({
//       user,
//       userInfo,
//       token,
//       loading,
//       isAuthenticated: !!user,
//       signIn,
//       signOut,
//     }),
//     [user, userInfo, token, loading, signIn, signOut]
//   );

//   return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
// }

// export default AuthContext;

"use client";

/**
 * Authentication Context for React Components
 *
 * What: Provides authentication state and methods to all components
 * Why: Centralizes authentication logic and provides consistent user state
 * How: Uses React Context API with Firebase Auth state management
 */

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  onAuthStateChange,
  signInWithGoogle,
  signOutUser,
  getCurrentUserToken,
  getCurrentUser,
} from "../lib/firebase";

const AuthContext = createContext();

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
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
          console.error("Error getting token:", error);
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
      console.error("Sign in error:", error);
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
      console.error("Sign out error:", error);
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
        console.error("Error refreshing token:", error);
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
    userInfo: user
      ? {
          uid: user.uid,
          email: user.email,
          name: user.displayName,
          picture: user.photoURL,
          emailVerified: user.emailVerified,
        }
      : null,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
