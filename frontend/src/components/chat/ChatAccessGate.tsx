'use client';

import { useQuery } from '@tanstack/react-query';
import { chatApi } from '@/lib/api/chat';
import { Button } from '@/components/ui/button';
import { Lock, Calendar, Clock, Loader2 } from 'lucide-react';
import Link from 'next/link';

interface ChatAccessGateProps {
  children: React.ReactNode;
}

export function ChatAccessGate({ children }: ChatAccessGateProps) {
  const { data: access, isLoading } = useQuery({
    queryKey: ['chat', 'access'],
    queryFn: chatApi.checkAccess,
    refetchInterval: 60000, // Check every minute
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  if (!access?.can_access) {
    const nextAvailable = access?.next_available
      ? new Date(access.next_available)
      : null;

    return (
      <div className="flex flex-col items-center justify-center h-full p-8 text-center bg-muted/30">
        <div className="p-4 rounded-full bg-muted mb-4">
          <Lock className="w-10 h-10 text-muted-foreground" />
        </div>
        <h3 className="text-xl font-semibold mb-2">Chat Unavailable</h3>
        <p className="text-muted-foreground mb-6 max-w-sm">
          {access?.reason ||
            'Chat is only available during scheduled meetings in tracking phase.'}
        </p>

        {nextAvailable && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground mb-6 p-3 bg-background rounded-lg border">
            <Clock className="w-4 h-4" />
            <span>
              Next available:{' '}
              {nextAvailable.toLocaleDateString()}{' '}
              at {nextAvailable.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          </div>
        )}

        <Link href="/app/meetings">
          <Button variant="outline" className="gap-2">
            <Calendar className="w-4 h-4" />
            View Meetings
          </Button>
        </Link>
      </div>
    );
  }

  return <>{children}</>;
}
