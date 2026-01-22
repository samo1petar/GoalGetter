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
  // Session context memory
  welcomeSummary: string | null;
  hasContext: boolean;
  sessionId: string | null;

  addMessage: (message: ChatMessage) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearMessages: () => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (content: string) => void;
  setTyping: (isTyping: boolean) => void;
  setEditingGoal: (isEditingGoal: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  setError: (error: string | null) => void;
  // Session context actions
  setWelcomeSummary: (summary: string | null) => void;
  setHasContext: (hasContext: boolean) => void;
  setSessionId: (sessionId: string | null) => void;
  clearWelcomeSummary: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  messages: [],
  streamingContent: '',
  isTyping: false,
  isEditingGoal: false,
  connectionStatus: 'disconnected',
  error: null,
  // Session context memory initial state
  welcomeSummary: null,
  hasContext: false,
  sessionId: null,

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
      streamingContent: '',
    })),

  setMessages: (messages) => set({ messages }),

  clearMessages: () => set({ messages: [], streamingContent: '', welcomeSummary: null }),

  setStreamingContent: (streamingContent) => set({ streamingContent }),

  appendStreamingContent: (content) =>
    set((state) => ({
      streamingContent: state.streamingContent + content,
    })),

  setTyping: (isTyping) => set({ isTyping }),

  setEditingGoal: (isEditingGoal) => set({ isEditingGoal }),

  setConnectionStatus: (connectionStatus) => set({ connectionStatus }),

  setError: (error) => set({ error }),

  // Session context actions
  setWelcomeSummary: (welcomeSummary) => set({ welcomeSummary }),

  setHasContext: (hasContext) => set({ hasContext }),

  setSessionId: (sessionId) => set({ sessionId }),

  clearWelcomeSummary: () => set({ welcomeSummary: null }),
}));
