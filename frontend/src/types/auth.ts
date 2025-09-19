export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  created_at: string;
  last_login?: string;
}

export interface MagicLinkRequest {
  email: string;
}

export interface MagicLinkResponse {
  message: string;
  email: string;
  expires_in_minutes: number;
}

export interface VerifyTokenRequest {
  token: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

export interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string) => Promise<MagicLinkResponse>;
  verifyToken: (token: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
  isAuthenticated: boolean;
}