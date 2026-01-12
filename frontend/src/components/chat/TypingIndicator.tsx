'use client';

import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar';

export function TypingIndicator() {
  return (
    <div className="flex gap-3">
      <Avatar className="w-8 h-8 flex-shrink-0">
        <AvatarImage src="/images/coach-avatar.png" />
        <AvatarFallback className="bg-primary text-primary-foreground">
          TR
        </AvatarFallback>
      </Avatar>

      <div className="rounded-lg px-4 py-3 bg-background border">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.3s]" />
          <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce [animation-delay:-0.15s]" />
          <span className="w-2 h-2 bg-muted-foreground/50 rounded-full animate-bounce" />
        </div>
      </div>
    </div>
  );
}
