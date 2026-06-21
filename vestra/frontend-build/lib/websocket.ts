/**
 * WebSocket Client for VESTRA — auto-reconnecting with exponential backoff.
 *
 * Usage:
 *   const ws = new WsClient(token);
 *   ws.connect();
 *   const unsub = ws.on('notification', (payload) => { ... });
 *   ws.send('ping');
 *   ws.disconnect();
 */
export type WsEventType =
  | 'notification'
  | 'message'
  | 'payment_status'
  | 'typing'
  | 'online_status'
  | 'online_status_batch'
  | 'pong';

export interface WsEventMap {
  notification: {
    id: number;
    type: string;
    title: string;
    body: string | null;
    data: Record<string, unknown>;
    is_read: boolean;
    created_at: string | null;
  };
  message: {
    id: number;
    sender_id: number;
    receiver_id: number;
    body: string;
    property_id: number | null;
    subject: string | null;
    is_read: boolean;
    created_at: string | null;
  };
  payment_status: {
    payment_id: number;
    status: string;
    amount: number;
    purpose: string | null;
    mpesa_receipt?: string | null;
    reference?: string | null;
    created_at: string | null;
  };
  typing: { sender_id: number; is_typing: boolean };
  online_status: { user_id: number; is_online: boolean };
  online_status_batch: Record<number, boolean>;
  pong: void;
}

type WsEventHandler<T> = (payload: T) => void;

const MAX_RECONNECT_ATTEMPTS = 20;
const BASE_DELAY_MS = 1000;
const MAX_DELAY_MS = 30000;
const PING_INTERVAL_MS = 25000;

export class WsClient {
  private ws: WebSocket | null = null;
  private readonly url: string;
  private reconnectAttempts = 0;
  private readonly listeners = new Map<string, Set<WsEventHandler<unknown>>>();
  private shouldReconnect = true;
  private intentionalClose = false;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private connectTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(token: string) {
    const baseUrl =
      process.env.NEXT_PUBLIC_WS_URL ||
      process.env.NEXT_PUBLIC_API_URL ||
      'http://localhost:8000';
    const wsBase = baseUrl.replace(/^http/, 'ws');
    this.url = `${wsBase}/ws?token=${encodeURIComponent(token)}`;
  }

  // ── Lifecycle ──────────────────────────────────────────────────────────

  connect(): void {
    if (this.ws?.readyState === WebSocket.OPEN) return;
    this.intentionalClose = false;
    this.shouldReconnect = true;

    try {
      this.ws = new WebSocket(this.url);
    } catch {
      this.scheduleReconnect();
      return;
    }

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.startPing();
    };

    this.ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const { type, payload } = data;
        if (type && this.listeners.has(type)) {
          this.listeners.get(type)!.forEach((handler) => handler(payload));
        }
      } catch {
        // Ignore malformed messages
      }
    };

    this.ws.onclose = () => {
      this.stopPing();
      if (!this.intentionalClose && this.shouldReconnect) {
        this.scheduleReconnect();
      }
    };

    this.ws.onerror = () => {
      // onclose fires after this
    };
  }

  disconnect(): void {
    this.intentionalClose = true;
    this.shouldReconnect = false;
    this.stopPing();
    if (this.connectTimer) {
      clearTimeout(this.connectTimer);
      this.connectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  // ── Event subscription ─────────────────────────────────────────────────

  on<K extends WsEventType>(
    type: K,
    handler: WsEventHandler<WsEventMap[K]>,
  ): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(handler as WsEventHandler<unknown>);
    return () => {
      this.listeners.get(type)?.delete(handler as WsEventHandler<unknown>);
      if (this.listeners.get(type)?.size === 0) {
        this.listeners.delete(type);
      }
    };
  }

  // ── Send messages ──────────────────────────────────────────────────────

  send(type: string, payload?: unknown): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ type, payload }));
    }
  }

  sendTyping(receiverId: number, isTyping: boolean): void {
    this.send('typing', { receiver_id: receiverId, is_typing: isTyping });
  }

  requestOnlineStatus(userIds: number[]): void {
    this.send('online_status', { user_ids: userIds });
  }

  // ── Connection state ───────────────────────────────────────────────────

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }

  get connectionState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED;
  }

  // ── Private helpers ────────────────────────────────────────────────────

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => {
      this.send('ping');
    }, PING_INTERVAL_MS);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) return;

    const delay = Math.min(
      BASE_DELAY_MS * Math.pow(2, this.reconnectAttempts) +
        Math.random() * 1000,
      MAX_DELAY_MS,
    );
    this.reconnectAttempts++;

    if (this.connectTimer) clearTimeout(this.connectTimer);
    this.connectTimer = setTimeout(() => this.connect(), delay);
  }
}
