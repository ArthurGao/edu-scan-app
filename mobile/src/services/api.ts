import axios, { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from 'axios';
// Removed top-level import of useAuthStore to break circular dependency


const API_BASE_URL = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';

class ApiClient {
  private client: AxiosInstance;

  constructor() {
    this.client = axios.create({
      baseURL: API_BASE_URL,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    this.setupInterceptors();
  }

  private setupInterceptors(): void {
    // Request interceptor - add auth token
    this.client.interceptors.request.use(
      (config: InternalAxiosRequestConfig) => {
        const authStore = require('@/stores/authStore').useAuthStore;
        const token = authStore.getState().accessToken;
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor - handle errors
    this.client.interceptors.response.use(
      (response) => response,
      async (error: AxiosError) => {
        const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

        if (error.response?.status === 401 && !originalRequest._retry) {
          originalRequest._retry = true;
          const authStore = require('@/stores/authStore').useAuthStore;
          const refreshToken = authStore.getState().refreshToken;

          if (refreshToken) {
            try {
              // Call refresh endpoint directly using axios to avoid circular dependency
              const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
                refresh_token: refreshToken,
              });

              const { accessToken, refreshToken: newRefreshToken } = response.data;
              authStore.getState().setTokens(accessToken, newRefreshToken);

              // Retry the original request with the new token
              originalRequest.headers.Authorization = `Bearer ${accessToken}`;
              return this.client(originalRequest);
            } catch (refreshError) {
              authStore.getState().logout();
              return Promise.reject(refreshError);
            }
          }
          authStore.getState().logout();
        }
        return Promise.reject(error);
      }
    );
  }

  get instance(): AxiosInstance {
    return this.client;
  }
}

export const apiClient = new ApiClient().instance;
export default apiClient;
