'use client';

import { useEffect, useRef, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useAuthStore } from '@/stores/authStore';
import { useChatStore } from '@/stores/chatStore';
import { useUIStore } from '@/stores/uiStore';
import { WebSocketClient } from '@/lib/websocket/WebSocketClient';
import type { WebSocketMessage, DraftGoalPayload, LLMProvider } from '@/types';
import { toast } from 'sonner';

const WS_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/api/v1/chat/ws';

export function useWebSocket() {
  const { accessToken, isAuthenticated } = useAuthStore();
  const {
    addMessage,
    setStreamingContent,
    appendStreamingContent,
    setTyping,
    setEditingGoal,
    setConnectionStatus,
    setError,
    setWelcomeSummary,
    setHasContext,
    setSessionId,
    setAiUpdatedGoal,
  } = useChatStore();
  const { setActiveGoalId } = useUIStore();
  const queryClient = useQueryClient();

  const wsRef = useRef<WebSocketClient | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !accessToken) {
      setConnectionStatus('disconnected');
      return;
    }

    setConnectionStatus('connecting');
    const client = new WebSocketClient(WS_URL, accessToken);
    wsRef.current = client;

    const unsubMessage = client.onMessage((data: WebSocketMessage) => {
      switch (data.type) {
        case 'connected':
          setConnectionStatus('connected');
          setError(null);
          // Handle session context memory
          if (data.session_id) {
            setSessionId(data.session_id);
          }
          if (data.has_context !== undefined) {
            setHasContext(data.has_context);
          }
          break;

        case 'welcome':
          // Handle welcome message as the first assistant message in chat
          if (data.content && data.message_id) {
            addMessage({
              id: data.message_id,
              user_id: '',
              role: 'assistant',
              content: data.content,
              timestamp: new Date().toISOString(),
            });
          }
          // Also set welcome summary for any legacy UI components that use it
          if (data.content) {
            setWelcomeSummary(data.content);
          }
          break;

        case 'typing':
          setTyping(true);
          break;

        case 'response_chunk':
          setTyping(false);
          if (data.content) {
            appendStreamingContent(data.content);
          }
          break;

        case 'response':
          setTyping(false);
          if (data.content && data.message_id) {
            addMessage({
              id: data.message_id,
              user_id: '',
              role: 'assistant',
              content: data.content,
              timestamp: new Date().toISOString(),
              metadata: {
                tokens_used: data.tokens_used,
              },
            });
          }
          setStreamingContent('');
          break;

        case 'focus_goal':
          // AI Coach is about to modify this goal - switch to it
          if (data.goal_id) {
            setActiveGoalId(data.goal_id);
            // Invalidate goals query to fetch newly created goals
            queryClient.invalidateQueries({ queryKey: ['goals'] });
          }
          break;

        case 'tool_call':
          // Handle AI Coach tool calls for goal manipulation
          setEditingGoal(true);
          if (data.tool_result?.success) {
            switch (data.tool) {
              case 'create_goal':
                // Invalidate goals cache to refetch
                queryClient.invalidateQueries({ queryKey: ['goals'] });
                // Set as active goal to show in editor
                if (data.tool_result.goal_id) {
                  setActiveGoalId(data.tool_result.goal_id);
                }
                // Set AI-updated goal for immediate editor refresh
                if (data.tool_result.goal) {
                  setAiUpdatedGoal(data.tool_result.goal);
                }
                toast.success('AI Coach created a new goal');
                break;

              case 'update_goal': {
                // Invalidate specific goal and goals list
                // Use predicate to match goal queries regardless of user_id position in key
                queryClient.invalidateQueries({ queryKey: ['goals'] });
                const updateGoalId = data.tool_result.goal_id;
                if (updateGoalId) {
                  queryClient.invalidateQueries({
                    predicate: (query) =>
                      query.queryKey[0] === 'goal' &&
                      query.queryKey.includes(updateGoalId),
                  });
                }
                // Set AI-updated goal for immediate editor refresh
                if (data.tool_result.goal) {
                  setAiUpdatedGoal(data.tool_result.goal);
                }
                toast.success('AI Coach updated your goal');
                break;
              }

              case 'set_goal_phase': {
                queryClient.invalidateQueries({ queryKey: ['goals'] });
                const phaseGoalId = data.tool_result.goal_id;
                if (phaseGoalId) {
                  queryClient.invalidateQueries({
                    predicate: (query) =>
                      query.queryKey[0] === 'goal' &&
                      query.queryKey.includes(phaseGoalId),
                  });
                }
                // Set AI-updated goal for immediate editor refresh
                if (data.tool_result.goal) {
                  setAiUpdatedGoal(data.tool_result.goal);
                }
                toast.success('AI Coach updated goal phase');
                break;
              }
            }
          } else if (data.tool_result?.error) {
            console.error(`Tool ${data.tool} failed:`, data.tool_result.error);
            toast.error(`Failed to ${data.tool?.replace('_', ' ')}`);
          }
          // Reset editing state after a short delay for visual feedback
          setTimeout(() => setEditingGoal(false), 500);
          break;

        case 'error':
          setTyping(false);
          setStreamingContent('');
          setError(data.content || 'An error occurred');
          break;
      }
    });

    const unsubConnect = client.onConnect(() => {
      setConnectionStatus('connected');
      setError(null);
    });

    const unsubDisconnect = client.onDisconnect(() => {
      setConnectionStatus('disconnected');
    });

    client.connect();

    return () => {
      unsubMessage();
      unsubConnect();
      unsubDisconnect();
      client.disconnect();
    };
  }, [
    isAuthenticated,
    accessToken,
    addMessage,
    setStreamingContent,
    appendStreamingContent,
    setTyping,
    setConnectionStatus,
    setError,
    setWelcomeSummary,
    setHasContext,
    setSessionId,
    setActiveGoalId,
    setAiUpdatedGoal,
    setEditingGoal,
    queryClient,
  ]);

  const sendMessage = useCallback(
    (
      content: string,
      draftGoals?: DraftGoalPayload[],
      provider?: LLMProvider,
      activeGoalId?: string
    ) => {
      if (!wsRef.current?.isConnected) {
        setError('Not connected to chat server');
        return;
      }

      // Add user message to store immediately
      addMessage({
        id: `temp-${Date.now()}`,
        user_id: '',
        role: 'user',
        content,
        timestamp: new Date().toISOString(),
      });

      wsRef.current.sendMessage(content, { draftGoals, provider, activeGoalId });
    },
    [addMessage, setError]
  );

  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.disconnect();
      wsRef.current.connect();
    }
  }, []);

  return {
    sendMessage,
    reconnect,
    isConnected: wsRef.current?.isConnected ?? false,
  };
}
