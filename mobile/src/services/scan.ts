import apiClient from './api';
import { ScanResult, ScanRecord, SolveRequest, PaginatedResponse } from '@/types';

export const scanService = {
  async solve(data: SolveRequest): Promise<ScanResult> {
    const formData = new FormData();
    formData.append('image', data.image as any);
    
    if (data.subject) {
      formData.append('subject', data.subject);
    }
    if (data.aiProvider) {
      formData.append('ai_provider', data.aiProvider);
    }
    if (data.gradeLevel) {
      formData.append('grade_level', data.gradeLevel);
    }

    const response = await apiClient.post<ScanResult>('/scan/solve', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async getScanResult(scanId: string): Promise<ScanResult> {
    const response = await apiClient.get<ScanResult>(`/scan/${scanId}`);
    return response.data;
  },

  // For SSE streaming - to be implemented with EventSource
  createStreamUrl(scanId: string): string {
    const baseUrl = process.env.EXPO_PUBLIC_API_BASE_URL || 'http://localhost:8000/api/v1';
    return `${baseUrl}/scan/stream/${scanId}`;
  },
};
