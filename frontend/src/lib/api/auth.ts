import { apiClient } from './client';
import type { User, AuthResponse, LoginResponse, TwoFactorSetupResponse } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export interface SignupRequest {
  email: string;
  password: string;
  name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
  totp_code?: string;
}

export const authApi = {
  signup: async (data: SignupRequest): Promise<AuthResponse> => {
    return apiClient.post<AuthResponse>('/auth/signup', data);
  },

  login: async (data: LoginRequest): Promise<LoginResponse> => {
    return apiClient.post<LoginResponse>('/auth/login', data);
  },

  logout: async (): Promise<void> => {
    return apiClient.post<void>('/auth/logout');
  },

  getMe: async (): Promise<User> => {
    return apiClient.get<User>('/auth/me');
  },

  refreshToken: async (refreshToken: string): Promise<AuthResponse> => {
    return apiClient.post<AuthResponse>('/auth/refresh', { refresh_token: refreshToken });
  },

  getGoogleAuthUrl: (): string => {
    return `${API_BASE_URL}/auth/google`;
  },

  forgotPassword: async (email: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>('/auth/forgot-password', { email });
  },

  resetPassword: async (token: string, newPassword: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>('/auth/reset-password', {
      token,
      new_password: newPassword
    });
  },

  // Two-Factor Authentication
  setup2FA: async (): Promise<TwoFactorSetupResponse> => {
    return apiClient.post<TwoFactorSetupResponse>('/auth/2fa/setup');
  },

  verify2FA: async (code: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>('/auth/2fa/verify', { code });
  },

  disable2FA: async (code: string): Promise<{ message: string }> => {
    return apiClient.post<{ message: string }>('/auth/2fa/disable', { code });
  },
};
