import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiRequest } from './api';

export interface CurrentUser {
  id: string;
  email: string;
  role: 'student' | 'company' | 'recruiter' | 'admin';
  is_active: boolean;
  email_verified: boolean;
  profile?: Record<string, any> | null;
}

interface AuthContextType {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<CurrentUser>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<CurrentUser | null>(() => {
    const saved = localStorage.getItem('current_user');
    return saved ? JSON.parse(saved) : null;
  });
  const [isLoading, setIsLoading] = useState(true);

  const fetchCurrentUser = async () => {
    try {
      const data = await apiRequest<CurrentUser>('/me');
      setUser(data);
      localStorage.setItem('current_user', JSON.stringify(data));
      return data;
    } catch {
      setUser(null);
      localStorage.removeItem('current_user');
      localStorage.removeItem('access_token');
      return null;
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      fetchCurrentUser();
    } else {
      setIsLoading(false);
    }

    const handleLogout = () => {
      setUser(null);
    };
    window.addEventListener('auth:logout', handleLogout);
    return () => window.removeEventListener('auth:logout', handleLogout);
  }, []);

  const login = async (email: string, password: string): Promise<CurrentUser> => {
    const res = await apiRequest<{ access_token: string; user: any }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });

    localStorage.setItem('access_token', res.access_token);
    const currentUser = await fetchCurrentUser();
    if (!currentUser) {
      throw new Error('Failed to load user profile after login');
    }
    return currentUser;
  };

  const logout = async () => {
    try {
      await apiRequest('/auth/logout', { method: 'POST' });
    } catch {
      // Ignore network errors on logout
    }
    localStorage.removeItem('access_token');
    localStorage.removeItem('current_user');
    setUser(null);
  };

  const refreshUser = async () => {
    await fetchCurrentUser();
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
