import { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import type { AuthContextType, User, MagicLinkResponse } from '../types/auth';
import { authService } from '../services/authService';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state from localStorage
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        const storedToken = authService.getStoredToken();
        const storedUser = authService.getStoredUser();

        if (storedToken && storedUser) {
          setToken(storedToken);
          setUser(storedUser);

          // Optionally verify token with server
          try {
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
          } catch (error) {
            // Token is invalid, clear auth
            console.error('Token verification failed:', error);
            authService.clearAuth();
            setToken(null);
            setUser(null);
          }
        }
      } catch (error) {
        console.error('Auth initialization error:', error);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const login = async (email: string): Promise<MagicLinkResponse> => {
    setIsLoading(true);
    try {
      const response = await authService.requestMagicLink(email);
      return response;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const verifyToken = async (magicToken: string): Promise<void> => {
    setIsLoading(true);
    try {
      const tokenResponse = await authService.verifyToken(magicToken);
      
      // Store auth data
      authService.setAuth(tokenResponse);
      setToken(tokenResponse.access_token);
      setUser(tokenResponse.user);
    } catch (error) {
      console.error('Token verification error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    try {
      // Call backend logout to invalidate tokens
      await authService.logout();
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local auth data
      authService.clearAuth();
      setToken(null);
      setUser(null);
    }
  };

  const isAuthenticated = !!(token && user);

  const value: AuthContextType = {
    user,
    token,
    login,
    verifyToken,
    logout,
    isLoading,
    isAuthenticated,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}