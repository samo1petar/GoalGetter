import { create } from 'zustand';
import type { LLMProvider, LLMProviderInfo } from '@/types';

interface ProviderState {
  currentProvider: LLMProvider;
  availableProviders: LLMProviderInfo[];
  isLoading: boolean;
  error: string | null;

  setProvider: (provider: LLMProvider) => Promise<void>;
  fetchProviders: () => Promise<void>;
  setCurrentProvider: (provider: LLMProvider) => void;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

export const useProviderStore = create<ProviderState>((set, get) => ({
  currentProvider: 'claude',
  availableProviders: [],
  isLoading: false,
  error: null,

  setProvider: async (provider: LLMProvider) => {
    set({ isLoading: true, error: null });

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat/provider`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ provider }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to update provider');
      }

      set({ currentProvider: provider, isLoading: false });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to update provider';
      set({ error: message, isLoading: false });
      throw error;
    }
  },

  fetchProviders: async () => {
    set({ isLoading: true, error: null });

    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE_URL}/chat/providers`, {
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });

      if (!response.ok) {
        throw new Error('Failed to fetch providers');
      }

      const data = await response.json();

      set({
        availableProviders: data.providers,
        currentProvider: data.current,
        isLoading: false,
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to fetch providers';
      set({ error: message, isLoading: false });
    }
  },

  setCurrentProvider: (provider: LLMProvider) => {
    set({ currentProvider: provider });
  },
}));
