import axios from 'axios';
import type { MagicLinkRequest, MagicLinkResponse, VerifyTokenRequest, TokenResponse, User } from '../types/auth';

const API_BASE_URL = 'http://localhost:8000/api/v1';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add token to requests if available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token expiration
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('accessToken');
      localStorage.removeItem('user');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  // Request magic link
  async requestMagicLink(email: string): Promise<MagicLinkResponse> {
    const request: MagicLinkRequest = { email };
    const response = await api.post('/auth/request-magic-link', request);
    return response.data;
  },

  // Verify magic token
  async verifyToken(token: string): Promise<TokenResponse> {
    const request: VerifyTokenRequest = { token };
    const response = await api.post('/auth/verify-token', request);
    return response.data;
  },

  // Get current user info
  async getCurrentUser(): Promise<User> {
    const response = await api.get('/auth/me');
    return response.data;
  },

  // Refresh token
  async refreshToken(): Promise<TokenResponse> {
    const response = await api.post('/auth/refresh');
    return response.data;
  },

  // Store token and user info
  setAuth(tokenResponse: TokenResponse) {
    localStorage.setItem('accessToken', tokenResponse.access_token);
    localStorage.setItem('user', JSON.stringify(tokenResponse.user));
  },

  // Get stored token
  getStoredToken(): string | null {
    return localStorage.getItem('accessToken');
  },

  // Get stored user
  getStoredUser(): User | null {
    const userStr = localStorage.getItem('user');
    return userStr ? JSON.parse(userStr) : null;
  },

  // Clear auth data
  clearAuth() {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('user');
  },

  // Check if user is authenticated
  isAuthenticated(): boolean {
    const token = this.getStoredToken();
    const user = this.getStoredUser();
    return !!(token && user);
  },
};

export { api };