import apiClient from './api';
import { ScanRecord, PaginatedResponse } from '@/types';

export interface HistoryParams {
  subject?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  limit?: number;
}

export const historyService = {
  async getHistory(params: HistoryParams = {}): Promise<PaginatedResponse<ScanRecord>> {
    const response = await apiClient.get<PaginatedResponse<ScanRecord>>('/history', {
      params: {
        subject: params.subject,
        start_date: params.startDate,
        end_date: params.endDate,
        page: params.page || 1,
        limit: params.limit || 20,
      },
    });
    return response.data;
  },

  async deleteHistoryItem(scanId: string): Promise<void> {
    await apiClient.delete(`/history/${scanId}`);
  },
};
