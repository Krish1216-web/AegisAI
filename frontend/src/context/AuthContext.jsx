import React, { createContext, useContext, useState, useEffect } from 'react';
import * as authApi from '../api/auth';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [role, setRole] = useState(null);
  const [workspaceId, setWorkspaceId] = useState(null);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  // Restore session from localStorage/cookies on mount
  useEffect(() => {
    refreshSession();
  }, []);

  const refreshSession = async () => {
    setIsLoading(true);
    const isLogged = localStorage.getItem('aegis_auth_logged') === 'true';
    if (!isLogged) {
      setIsLoading(false);
      return;
    }

    try {
      const profile = await authApi.getMe();
      setUser(profile);
      setRole(profile.role.name.toLowerCase());
      setIsAuthenticated(true);
      
      const wsId = profile.settings?.default_workspace_id;
      if (wsId) {
        setWorkspaceId(wsId);
      }
    } catch (err) {
      console.error('Session refresh failed:', err);
      // Clear invalid session
      localStorage.removeItem('aegis_access_token');
      localStorage.removeItem('aegis_auth_logged');
      localStorage.removeItem('aegis_auth_role');
      setIsAuthenticated(false);
    } finally {
      setIsLoading(false);
    }
  };

  const login = async (username, password) => {
    setIsLoading(true);
    try {
      const token = await authApi.login(username, password);
      localStorage.setItem('aegis_access_token', token.access_token);
      localStorage.setItem('aegis_auth_logged', 'true');
      
      const profile = await authApi.getMe();
      setUser(profile);
      const userRole = profile.role.name.toLowerCase();
      setRole(userRole);
      localStorage.setItem('aegis_auth_role', userRole);
      setIsAuthenticated(true);

      const wsId = profile.settings?.default_workspace_id;
      if (wsId) {
        setWorkspaceId(wsId);
      }
      return profile;
    } catch (err) {
      localStorage.removeItem('aegis_access_token');
      localStorage.removeItem('aegis_auth_logged');
      localStorage.removeItem('aegis_auth_role');
      setIsAuthenticated(false);
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (username, email, password) => {
    setIsLoading(true);
    try {
      const profile = await authApi.register(username, email, password);
      return profile;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await authApi.logout();
    } catch (err) {
      console.error('Logout request failed:', err);
    } finally {
      localStorage.removeItem('aegis_access_token');
      localStorage.removeItem('aegis_auth_logged');
      localStorage.removeItem('aegis_auth_role');
      setUser(null);
      setRole(null);
      setWorkspaceId(null);
      setIsAuthenticated(false);
      setIsLoading(false);
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        role,
        workspaceId,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
        refreshSession,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
