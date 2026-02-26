import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import * as SecureStore from 'expo-secure-store';
import { User, AuthState, LoginRequest, RegisterRequest } from '@/types';
import { authService } from '@/services';

interface AuthActions {
  login: (data: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  setTokens: (accessToken: string, refreshToken: string) => void;
}

type AuthStore = AuthState & AuthActions;

import { Platform } from 'react-native';

// Custom storage adapter
const secureStorage = Platform.OS === 'web'
  ? {
    getItem: (name: string) => localStorage.getItem(name),
    setItem: (name: string, value: string) => localStorage.setItem(name, value),
    removeItem: (name: string) => localStorage.removeItem(name),
  }
  : {
    getItem: (name: string) => SecureStore.getItemAsync(name),
    setItem: (name: string, value: string) => SecureStore.setItemAsync(name, value),
    removeItem: (name: string) => SecureStore.deleteItemAsync(name),
  };

const store = (set: any, get: any) => ({
  // State
  user: {
    id: 'mock-user-id',
    email: 'user@example.com',
    full_name: 'Test User',
    is_active: true,
  },
  accessToken: 'mock-access-token',
  refreshToken: 'mock-refresh-token',
  isAuthenticated: true,
  isLoading: false,

  // Actions
  login: async (data: LoginRequest) => {
    set({ isLoading: true });
    try {
      const tokens = await authService.login(data);
      set({
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        isAuthenticated: true,
      });
      await get().loadUser();
    } finally {
      set({ isLoading: false });
    }
  },

  register: async (data: RegisterRequest) => {
    set({ isLoading: true });
    try {
      const tokens = await authService.register(data);
      set({
        accessToken: tokens.accessToken,
        refreshToken: tokens.refreshToken,
        isAuthenticated: true,
      });
      await get().loadUser();
    } finally {
      set({ isLoading: false });
    }
  },

  logout: () => {
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isAuthenticated: false,
    });
  },

  loadUser: async () => {
    // Skip real API call in bypass mode
    console.log('[AuthStore] Skipping real user load, using mock user.');
    return;
  },

  setTokens: (accessToken: string, refreshToken: string) => {
    set({ accessToken, refreshToken, isAuthenticated: true });
  },
});

export const useAuthStore = create<AuthStore>()(
  (Platform.OS === 'web'
    ? store
    : persist(store, {
      name: 'auth-storage',
      storage: createJSONStorage(() => secureStorage as any),
      partialize: (state: any) => ({
        accessToken: state.accessToken,
        refreshToken: state.refreshToken,
      }),
    })) as any
);
