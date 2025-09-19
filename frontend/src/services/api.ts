import axios from 'axios';
import type { ChatRequest, ChatResponse } from '../types';

const API_BASE_URL = (import.meta.env?.VITE_API_URL as string) || 'http://localhost:8000/api/v1';

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