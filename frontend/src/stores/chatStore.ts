import { create } from 'zustand';
import type { ChatMessage } from '@/types';

type ConnectionStatus = 'disconnected' | 'connecting' | 'connected' | 'error';

interface ChatState {
  messages: ChatMessage[];
  streamingContent: string;
  isTyping: boolean;
  isEditingGoal: boolean;
  connectionStatus: ConnectionStatus;
  error: string | null;

  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearMessages: () => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (content: string) => void;
  setTyping: (isTyping: boolean) => void;
  setEditingGoal: (isEditingGoal: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setError: (error: string | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingContent: '',
  isTyping: false,
  isEditingGoal: false,
  connectionStatus: 'disconnected',
  error: null,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      streamingContent: '',
    })),

  setMessages: (messages) => set({ messages }),

  clearMessages: () => set({ messages: [], streamingContent: '' }),

  setStreamingContent: (streamingContent) => set({ streamingContent }),

  appendStreamingContent: (content) =>
    set((state) => ({
      streamingContent: state.streamingContent + content,
    })),

  setTyping: (isTyping) => set({ isTyping }),

  setEditingGoal: (isEditingGoal) => set({ isEditingGoal }),

  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),

  setError: (error) => set({ error }),
}));
