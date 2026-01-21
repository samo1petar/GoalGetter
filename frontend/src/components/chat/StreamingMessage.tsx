'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';
import { MarkdownRenderer } from './MarkdownRenderer';

interface StreamingMessageProps {
  content: string;
}

export function StreamingMessage({ content }: StreamingMessageProps) {
  if (!content) return null;

  return (
    <div className="flex gap-3">
      <Avatar className="w-8 h-8 flex-shrink-0">
        <AvatarImage src="/images/coach-avatar.png" />
        <AvatarFallback className="bg-primary text-primary-foreground">
          TR
        </AvatarFallback>
      </Avatar>

      <div className="max-w-[80%] rounded-lg px-4 py-2 bg-background border">
        <div className="relative">
          <MarkdownRenderer content={content} />
          <span className="inline-block w-2 h-4 bg-primary/50 animate-pulse ml-0.5 align-middle" />
        </div>
      </div>
    </div>
  );
}
