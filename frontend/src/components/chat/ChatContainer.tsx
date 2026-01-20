'use client';

import { useEffect, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { chatApi } from '@/lib/api/chat';
import { useChatStore } from '@/stores/chatStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import { useDraftGoals } from '@/hooks/useDraftGoals';
import { ChatAccessGate } from './ChatAccessGate';
import { MessageList } from './MessageList';
import { ChatInput } from './ChatInput';
import { ConnectionStatus } from './ConnectionStatus';
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { ScrollArea } from '@/components/ui/scroll-area';

export function ChatContainer() {
  const { messages, setMessages, connectionStatus } = useChatStore();
  const { sendMessage } = useWebSocket();
  const { getDraftsArray } = useDraftGoals();

  // Wrap sendMessage to include draft goals (provider is set server-side via DEFAULT_LLM_PROVIDER)
  const handleSendMessage = useCallback(
    (content: string) => {
      const draftGoals = getDraftsArray();
      sendMessage(content, draftGoals);
    },
    [sendMessage, getDraftsArray]
  );

  // Load chat history
  const { data: historyData } = useQuery({
    queryKey: ['chat', 'history'],
    queryFn: () => chatApi.getHistory({ page_size: 50 }),
    staleTime: 60000,
  });

  // Set messages from history
  useEffect(() => {
    if (historyData?.messages && messages.length === 0) {
      setMessages(historyData.messages.reverse());
    }
  }, [historyData, messages.length, setMessages]);

  return (
    <ChatAccessGate>
      <div className="h-full flex flex-col bg-muted/30">
        {/* Chat Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b bg-background">
          <div className="flex items-center gap-3">
            <Avatar>
              <AvatarImage src="/images/coach-avatar.png" />
              <AvatarFallback className="bg-primary text-primary-foreground">
                TR
              </AvatarFallback>
            </Avatar>
            <div>
              <h3 className="font-medium">Alfred - AI Coach</h3>
              <ConnectionStatus status={connectionStatus} />
            </div>
          </div>
        </div>

        {/* Messages */}
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
