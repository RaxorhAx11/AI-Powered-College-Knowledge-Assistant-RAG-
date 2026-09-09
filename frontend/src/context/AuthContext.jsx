import React, { createContext, useContext, useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { api } from '../services/api';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState({
    id: null,
    username: 'Guest Student',
    role: 'student',
    authenticated: false,
  });
  const [loading, setLoading] = useState(true);
  const isMounted = useRef(true);

  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  const refreshUser = useCallback(async () => {
    try {
      setLoading(true);
      const data = await api.getMe();
      if (isMounted.current) {
        if (data.authenticated) {
          setUser({
            id: data.id || null,
            username: data.username || 'Guest Student',
            role: data.role || 'student',
            authenticated: true,
          });
        } else {
          // Server explicitly says not authenticated
          localStorage.removeItem('raxel_token');
          setUser({
            id: null,
            username: 'Guest Student',
            role: 'student',
            authenticated: false,
          });
        }
      }
    } catch (err) {
      if (isMounted.current) {
        // If explicitly 401 or Unauthorized, invalidate session. Otherwise, preserve local session if token exists.
        const isAuthError = err.message && (err.message.includes('401') || err.message.toLowerCase().includes('unauthorized'));
        if (isAuthError) {
          localStorage.removeItem('raxel_token');
          setUser({
            id: null,
            username: 'Guest Student',
            role: 'student',
            authenticated: false,
          });
        } else {
          console.warn('Network issue during session check, retaining current auth state:', err.message);
        }
      }
    } finally {
      if (isMounted.current) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    refreshUser();
  }, [refreshUser]);

  const login = useCallback(async (username, password) => {
    const res = await api.login(username, password);
    if (res.token) {
      localStorage.setItem('raxel_token', res.token);
    }
    await refreshUser();
    return res;
  }, [refreshUser]);

  const signup = useCallback(async (username, password, role) => {
    const res = await api.signup(username, password, role);
    if (res.token) {
      localStorage.setItem('raxel_token', res.token);
    }
    await refreshUser();
    return res;
  }, [refreshUser]);

  const logout = useCallback(async () => {
    try {
      await api.logout();
    } catch (err) {
      console.error(err);
    }
    localStorage.removeItem('raxel_token');
    if (isMounted.current) {
      setUser({
        id: null,
        username: 'Guest Student',
        role: 'student',
        authenticated: false,
      });
    }
  }, []);

  const value = useMemo(() => ({
    user,
    loading,
    login,
    signup,
    logout,
    refreshUser,
  }), [user, loading, login, signup, logout, refreshUser]);

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
