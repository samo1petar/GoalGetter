'use client';

import { cn } from '@/lib/utils';

type Status = 'connected' | 'connecting' | 'disconnected' | 'error';

interface ConnectionStatusProps {
  status: Status;
}

export function ConnectionStatus({ status }: ConnectionStatusProps) {
  const statusConfig = {
    connected: {
      color: 'bg-green-500',
      text: 'Online',
    },
    connecting: {
      color: 'bg-yellow-500 animate-pulse',
      text: 'Connecting...',
    },
    disconnected: {
      color: 'bg-gray-500',
      text: 'Offline',
    },
    error: {
      color: 'bg-red-500',
      text: 'Error',
    },
  };

  const config = statusConfig[status];

  return (
    <div className="flex items-center gap-1.5">
      <span className={cn('w-2 h-2 rounded-full', config.color)} />
      <span className="text-xs text-muted-foreground">{config.text}</span>
    </div>
  );
}
