'use client';

import { useEffect, useRef } from 'react';
import { useChatStore } from '@/stores/chatStore';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { TypingIndicator } from './TypingIndicator';

export function MessageList() {
  const { messages, streamingContent, isTyping, isEditingGoal } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, isTyping, isEditingGoal]);

  if (messages.length === 0 && !streamingContent && !isTyping) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-center p-8">
        <div className="max-w-sm">
          <h3 className="text-lg font-medium mb-2">Start a conversation</h3>
          <p className="text-muted-foreground text-sm">
            Ask your AI coach anything about setting or achieving your goals.
            I&apos;m here to help you break through barriers and reach your full potential!
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}

      {streamingContent && <StreamingMessage content={streamingContent} />}

      {(isTyping || isEditingGoal) && !streamingContent && (
        <TypingIndicator isEditingGoal={isEditingGoal} />
      )}

      <div ref={bottomRef} />
    </div>
  );
}
