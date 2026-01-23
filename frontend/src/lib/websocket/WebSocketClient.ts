import type { WebSocketMessage, DraftGoalPayload, LLMProvider } from '@/types';

type MessageHandler = (data: WebSocketMessage) => void;
type ConnectionHandler = () => void;

// Module-level flag to track if we've connected this session.
// This persists across WebSocketClient instances so that navigation
// between pages doesn't reset it and trigger multiple welcome messages.
// IMPORTANT: Must be reset on logout so next login triggers welcome message.
let hasConnectedThisSession = false;

/**
 * Reset the session connection flag.
 * Call this when the user logs out so the next login will trigger a welcome message.
 */
export function resetWebSocketSessionFlag(): void {
  hasConnectedThisSession = false;
}

export interface SendMessageOptions {
  draftGoals?: DraftGoalPayload[];
  provider?: LLMProvider;
  activeGoalId?: string;
}

export class WebSocketClient {
  private url: string;
  private token: string;
  private ws: WebSocket | null = null;
  private messageHandlers: Set<MessageHandler> = new Set();
  private connectHandlers: Set<ConnectionHandler> = new Set();
  private disconnectHandlers: Set<ConnectionHandler> = new Set();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: NodeJS.Timeout | null = null;

  constructor(url: string, token: string) {
    this.url = url;
    this.token = token;
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;

    // Only send is_login=true on first connection of the session, not on
    // reconnections or when navigating between pages. The module-level
    // hasConnectedThisSession flag persists across WebSocketClient instances.
    const isLogin = !hasConnectedThisSession;
    const wsUrl = `${this.url}?token=${encodeURIComponent(this.token)}&is_login=${isLogin}`;
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      // Mark that we've connected this session so subsequent connections
      // (from page navigation or reconnects) won't trigger welcome messages
      hasConnectedThisSession = true;
      this.startPingInterval();
      this.connectHandlers.forEach((handler) => handler());
    };

    this.ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WebSocketMessage;
        this.messageHandlers.forEach((handler) => handler(data));
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    this.ws.onclose = () => {
      this.stopPingInterval();
      this.disconnectHandlers.forEach((handler) => handler());
      this.attemptReconnect();
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect(): void {
    this.reconnectAttempts = this.maxReconnectAttempts; // Prevent reconnection
    this.stopPingInterval();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  sendMessage(content: string, options?: SendMessageOptions): void {
    if (!this.isConnected) {
      console.error('WebSocket not connected');
      return;
    }

    const payload: Record<string, unknown> = {
      type: 'message',
      content,
    };

    // Include draft goals if provided
    if (options?.draftGoals && options.draftGoals.length > 0) {
      payload.draft_goals = options.draftGoals;
    }

    // Include provider selection if provided
    if (options?.provider) {
      payload.provider = options.provider;
    }

    // Include active goal ID if provided
    if (options?.activeGoalId) {
      payload.active_goal_id = options.activeGoalId;
    }

    this.ws?.send(JSON.stringify(payload));
  }

  onMessage(handler: MessageHandler): () => void {
    this.messageHandlers.add(handler);
    return () => this.messageHandlers.delete(handler);
  }

  onConnect(handler: ConnectionHandler): () => void {
    this.connectHandlers.add(handler);
    return () => this.connectHandlers.delete(handler);
  }

  onDisconnect(handler: ConnectionHandler): () => void {
    this.disconnectHandlers.add(handler);
    return () => this.disconnectHandlers.delete(handler);
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) return;

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    setTimeout(() => {
      console.log(`Attempting to reconnect... (${this.reconnectAttempts}/${this.maxReconnectAttempts})`);
      this.connect();
    }, delay);
  }

  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.isConnected) {
        this.ws?.send(JSON.stringify({ type: 'ping' }));
      }
    }, 30000);
  }

  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}
