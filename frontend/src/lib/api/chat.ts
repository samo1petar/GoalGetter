import { apiClient } from './client';
import type {
  ChatHistoryResponse,
  ChatAccessResponse,
  AvailableProvidersResponse,
  LLMProvider,
} from '@/types';

export interface ChatHistoryParams {
  page?: number;
  page_size?: number;
  meeting_id?: string;
}

export interface ProviderResponse {
  provider: LLMProvider;
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

  getProviders: async (): Promise<AvailableProvidersResponse> => {
    return apiClient.get<AvailableProvidersResponse>('/chat/providers');
  },

  setProvider: async (provider: LLMProvider): Promise<ProviderResponse> => {
    return apiClient.put<ProviderResponse>('/chat/provider', { provider });
  },
};
