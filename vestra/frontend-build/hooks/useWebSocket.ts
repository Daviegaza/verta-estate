'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { WsClient } from '@/lib/websocket';
import type { WsEventType, WsEventMap } from '@/lib/websocket';
import { useAuthStore } from '@/store/authStore';

type WsHandler<K extends WsEventType> = (payload: WsEventMap[K]) => void;

interface UseWebSocketReturn {
  /** Subscribe to a WebSocket event type. Returns an unsubscribe function. */
  subscribe: <K extends WsEventType>(
    type: K,
    handler: WsHandler<K>,
  ) => () => void;
  /** Send a message to the server (only if connected). */
  send: (type: string, payload?: unknown) => void;
  /** Send a typing indicator to another user. */
  sendTyping: (receiverId: number, isTyping: boolean) => void;
  /** Request online status for a batch of user IDs. */
  requestOnlineStatus: (userIds: number[]) => void;
  /** Whether the WebSocket connection is currently open. */
  connected: boolean;
}

/**
 * React hook for VESTRA's real-time WebSocket system.
 *
 * Automatically connects when the user is authenticated and disconnects
 * on unmount or logout. Returns subscribe/send helpers.
 *
 * Usage:
 *   const { subscribe, send, connected } = useWebSocket();
 *   useEffect(() => {
 *     const unsub = subscribe('notification', (payload) => { ... });
 *     return unsub;
 *   }, [subscribe]);
 */
export function useWebSocket(): UseWebSocketReturn {
  const { token, isAuthenticated } = useAuthStore();
  const wsRef = useRef<WsClient | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!isAuthenticated || !token) {
      if (wsRef.current) {
        wsRef.current.disconnect();
        wsRef.current = null;
      }
      setConnected(false);
      return;
    }

    const ws = new WsClient(token);
    wsRef.current = ws;

    // Track connection state via pong events
    const unsubPong = ws.on('pong', () => {
      setConnected(true);
    });

    ws.connect();

    return () => {
      unsubPong();
      ws.disconnect();
      wsRef.current = null;
      setConnected(false);
    };
  }, [isAuthenticated, token]);

  const subscribe = useCallback(
    <K extends WsEventType>(type: K, handler: WsHandler<K>): (() => void) => {
      if (wsRef.current) {
        return wsRef.current.on(type, handler as any);
      }
      // Fallback: return a no-op if WS not yet connected
      return () => {};
    },
    [],
  );

  const send = useCallback((type: string, payload?: unknown) => {
    wsRef.current?.send(type, payload);
  }, []);

  const sendTyping = useCallback((receiverId: number, isTyping: boolean) => {
    wsRef.current?.sendTyping(receiverId, isTyping);
  }, []);

  const requestOnlineStatus = useCallback((userIds: number[]) => {
    wsRef.current?.requestOnlineStatus(userIds);
  }, []);

  return {
    subscribe,
    send,
    sendTyping,
    requestOnlineStatus,
    connected,
  };
}
