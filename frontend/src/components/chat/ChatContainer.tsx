'use client';

import { useEffect, useCallback, useRef } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { useAuthStore } from '@/stores/authStore';
import { useEditorStore } from '@/stores/editorStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useDraftGoals } from '@/hooks/useDraftGoals';
import { useUIStore } from '@/stores/uiStore';
import { ChatAccessGate } from './ChatAccessGate';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ConnectionStatus } from './ConnectionStatus';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';

export function ChatContainer() {
  const { clearMessages, connectionStatus } = useChatStore();
  const { user } = useAuthStore();
  const { saveIfNeeded } = useEditorStore();
  const { sendMessage } = useWebSocket();
  const { getDraftsArray, activeEditingGoalId } = useDraftGoals();
  const { activeGoalId } = useUIStore();
  const prevUserIdRef = useRef<string | null>(null);

  // Clear messages when user changes (safety measure)
  useEffect(() => {
    const currentUserId = user?.id || null;
    if (prevUserIdRef.current !== null && prevUserIdRef.current !== currentUserId) {
      // User changed, clear messages
      clearMessages();
    }
    prevUserIdRef.current = currentUserId;
  }, [user?.id, clearMessages]);

  // Wrap sendMessage to include draft goals with Markdown content and active goal ID
  // The getDraftsArray() now returns content as Markdown (via contentMarkdown field)
  // which gives AI Coach better context about goal structure (headers, lists, etc.)
  // Also saves any pending editor changes before sending to ensure AI has latest content
  const handleSendMessage = useCallback(
    (content: string) => {
      // Save any pending changes before sending message to AI Coach (fire-and-forget)
      saveIfNeeded().catch((error) => {
        console.error('Failed to save before sending message:', error);
      });

      const draftGoals = getDraftsArray();
      // Use activeEditingGoalId if available, otherwise fall back to activeGoalId
      const currentGoalId = activeEditingGoalId || activeGoalId || undefined;
      sendMessage(content, draftGoals, undefined, currentGoalId);
    },
    [sendMessage, getDraftsArray, activeEditingGoalId, activeGoalId, saveIfNeeded]
  );

  // Note: Chat history is intentionally NOT loaded on login.
  // Each session starts fresh with a context-aware welcome message from AI Coach.
  // The welcome message is sent via WebSocket on connect and saved to the database.

  return (
    <ChatAccessGate>
      <div className="h-full flex flex-col bg-muted/30">
        {/* Chat Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-background">
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarImage src="/images/coach-avatar.png" />
              <AvatarFallback className="bg-primary text-primary-foreground">
                A
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="font-medium">Alfred - AI Coach</h3>
              <ConnectionStatus status={connectionStatus} />
            </div>
          </div>
        </div>

        {/* Messages (includes welcome message as first assistant message) */}
        <ScrollArea className="flex-1 p-4">
          <MessageList />
        </ScrollArea>

        {/* Input */}
        <div className="p-4 border-t bg-background">
          <ChatInput
            onSend={handleSendMessage}
            disabled={connectionStatus !== 'connected'}
          />
        </div>
      </div>
    </ChatAccessGate>
  );
}
