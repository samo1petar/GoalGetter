import { apiClient } from './client';
import type { ChatHistoryResponse, ChatAccessResponse } from '@/types';

export interface ChatHistoryParams {
  page?: number;
  page_size?: number;
  meeting_id?: string;
}

export const chatApi = {
  getHistory: async (params?: ChatHistoryParams): Promise<ChatHistoryResponse> => {
    return apiClient.get<ChatHistoryResponse>('/chat/history', params as Record<string, string | number | boolean | undefined>);
  },

  checkAccess: async (): Promise<ChatAccessResponse> => {
    return apiClient.get<ChatAccessResponse>('/chat/access');
  },

  clearHistory: async (): Promise<void> => {
    return apiClient.delete<void>('/chat/history');
  },
};
