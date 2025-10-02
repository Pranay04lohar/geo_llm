"use client";

import React, {
  createContext,
  useContext,
  useMemo,
  useState,
  useCallback,
} from "react";

// Create context
const AuthContext = createContext(null);

// Safe stub returned when no provider is mounted
const useAuthFallback = () => ({
  user: null,
  userInfo: null,
  loading: false,
  token: null,
  isAuthenticated: false,
  signIn: async () => {
    // No-op stub
    return null;
  },
  signOut: async () => {
    // No-op stub
    return null;
  },
});

export function useAuth() {
  const ctx = useContext(AuthContext);
  return ctx ?? useAuthFallback();
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [userInfo, setUserInfo] = useState(null);
  const [token, setToken] = useState(null);
  const [loading, setLoading] = useState(false);
  const demoAuthEnabled = process.env.NEXT_PUBLIC_DEMO_AUTH === "true";

  const signIn = useCallback(async () => {
    setLoading(true);
    try {
      // TODO: Integrate real auth here (e.g., Firebase, NextAuth, custom backend)
      // By default, prevent auto sign-in and require a real provider.
      if (!demoAuthEnabled) {
        throw new Error(
          "Authentication is not configured. Set NEXT_PUBLIC_DEMO_AUTH=true to enable demo sign-in, or integrate a real provider."
        );
      }
      // Demo sign-in path (explicitly enabled only)
      const fakeUser = { id: "local-user" };
      const fakeUserInfo = { name: "User", email: "user@example.com" };
      setUser(fakeUser);
      setUserInfo(fakeUserInfo);
      setToken(null);
      return fakeUser;
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    setLoading(true);
    try {
      setUser(null);
      setUserInfo(null);
      setToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  const value = useMemo(
    () => ({
      user,
      userInfo,
      token,
      loading,
      isAuthenticated: !!user,
      signIn,
      signOut,
    }),
    [user, userInfo, token, loading, signIn, signOut]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;
