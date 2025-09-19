import axios from 'axios';
import type { ChatRequest, ChatResponse } from '../types';
// Ensure TypeScript knows about Vite env vars (they must be prefixed with VITE_)
declare global {
  interface ImportMetaEnv {
    readonly VITE_API_URL?: string;
    // add other VITE_* variables here as needed
  }
  interface ImportMeta {
    readonly env: ImportMetaEnv;
  }
}

// Helper to read Vite env vars with an optional fallback
export const getEnv = (key: keyof ImportMetaEnv, fallback?: string) =>
  (import.meta.env[key as string] as string | undefined) ?? fallback;
const API_BASE_URL = (import.meta.env?.VITE_API_URL as string) || 'http://200.144.245.12:8000/api/v1';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const chatApi = {
  async sendMessage(message: string): Promise<ChatResponse> {
    const request: ChatRequest = { message };
    const response = await api.post<ChatResponse>('/chat/', request);
    return response.data;
  }
};

export default api;