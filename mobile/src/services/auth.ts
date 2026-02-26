import apiClient from './api';
import { LoginRequest, RegisterRequest, TokenResponse, User } from '@/types';

export const authService = {
  async register(data: RegisterRequest): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/auth/register', data);
    return response.data;
  },

  async login(data: LoginRequest): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/auth/login', data);
    return response.data;
  },

  async refreshToken(refreshToken: string): Promise<TokenResponse> {
    const response = await apiClient.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me');
    return response.data;
  },
};
