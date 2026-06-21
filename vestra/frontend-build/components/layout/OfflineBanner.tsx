'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { Wifi, WifiOff, Clock, RefreshCw, Zap } from 'lucide-react';

/**
 * Offline Detection Banner
 *
 * Listens for navigator.onLine changes and shows a persistent banner
 * when the user loses connectivity. Displays:
 *   - Current connection status
 *   - Last known sync time
 *   - Number of queued offline actions
 *
 * Queued actions are stored in localStorage and replayed when
 * connectivity is restored.
 */
export default function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(true);
  const [wasOffline, setWasOffline] = useState(false);
  const [lastSyncTime, setLastSyncTime] = useState<Date | null>(null);
  const [queuedCount, setQueuedCount] = useState(0);
  const [showBanner, setShowBanner] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [syncInProgress, setSyncInProgress] = useState(false);
  const mountedRef = useRef(true);

  // ── Update queued action count ────────────────────────────────────────────

  const updateQueuedCount = useCallback(() => {
    try {
      const raw = localStorage.getItem('vestra_offline_queue');
      if (raw) {
        const queue = JSON.parse(raw);
        setQueuedCount(Array.isArray(queue) ? queue.length : 0);
      } else {
        setQueuedCount(0);
      }
    } catch {
      setQueuedCount(0);
    }
  }, []);

  // ── Attempt to flush queued actions on reconnect ───────────────────────────

  const flushQueue = useCallback(async () => {
    const raw = localStorage.getItem('vestra_offline_queue');
    if (!raw) return;

    try {
      const queue = JSON.parse(raw);
      if (!Array.isArray(queue) || queue.length === 0) return;

      setSyncInProgress(true);

      // Process each queued action sequentially
      const remaining: unknown[] = [];
      for (const action of queue) {
        try {
          const response = await fetch(action.url, {
            method: action.method || 'POST',
            headers: { 'Content-Type': 'application/json', ...action.headers },
            body: action.body ? JSON.stringify(action.body) : undefined,
          });
          if (!response.ok) {
            // Keep failed items in the queue
            remaining.push(action);
          }
        } catch {
          // Network still unstable — keep in queue
          remaining.push(action);
        }
      }

      localStorage.setItem('vestra_offline_queue', JSON.stringify(remaining));
      setQueuedCount(remaining.length);
      setLastSyncTime(new Date());
    } catch {
      // If parsing fails, clear the corrupt queue
      localStorage.removeItem('vestra_offline_queue');
      setQueuedCount(0);
    } finally {
      setSyncInProgress(false);
    }
  }, []);

  // ── Listen for online/offline events ───────────────────────────────────────

  useEffect(() => {
    mountedRef.current = true;

    const handleOnline = () => {
      if (!mountedRef.current) return;
      setIsOnline(true);
      setShowBanner(true);
      setWasOffline(true);
      setLastSyncTime(new Date());

      // Attempt to flush any queued offline actions
      flushQueue();

      // Auto-dismiss after 4 seconds
      setTimeout(() => {
        if (mountedRef.current) {
          setShowBanner(false);
          // Reset wasOffline after banner hides
          setTimeout(() => setWasOffline(false), 500);
        }
      }, 4000);
    };

    const handleOffline = () => {
      if (!mountedRef.current) return;
      setIsOnline(false);
      setShowBanner(true);
      setDismissed(false);
      updateQueuedCount();
    };

    // Initial state
    setIsOnline(navigator.onLine);
    if (!navigator.onLine) {
      setShowBanner(true);
      updateQueuedCount();
    }

    // Listen for queued action storage changes (cross-tab)
    const handleStorage = (e: StorageEvent) => {
      if (e.key === 'vestra_offline_queue') {
        updateQueuedCount();
      }
    };

    window.addEventListener('online', handleOnline);
    window.addEventListener('offline', handleOffline);
    window.addEventListener('storage', handleStorage);

    // Periodic queued count refresh
    const interval = setInterval(updateQueuedCount, 10000);

    return () => {
      mountedRef.current = false;
      window.removeEventListener('online', handleOnline);
      window.removeEventListener('offline', handleOffline);
      window.removeEventListener('storage', handleStorage);
      clearInterval(interval);
    };
  }, [flushQueue, updateQueuedCount]);

  // ── Listen for visibility changes to re-check status ───────────────────────

  useEffect(() => {
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        const online = navigator.onLine;
        setIsOnline(online);
        if (online && wasOffline) {
          flushQueue();
        }
        if (!online) {
          updateQueuedCount();
        }
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    return () => document.removeEventListener('visibilitychange', handleVisibility);
  }, [wasOffline, flushQueue, updateQueuedCount]);

  // ── Dismiss ────────────────────────────────────────────────────────────────

  const handleDismiss = () => {
    setShowBanner(false);
    setDismissed(true);
  };

  // ── Manual sync trigger ────────────────────────────────────────────────────

  const handleSyncNow = () => {
    flushQueue();
  };

  // ── Render helpers ─────────────────────────────────────────────────────────

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString(undefined, {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  // ── Render ─────────────────────────────────────────────────────────────────

  if (!showBanner || dismissed) return null;

  const isConnected = isOnline && !wasOffline;

  // Don't show anything if we're online and were never offline (normal state)
  if (isConnected) return null;

  return (
    <div
      role="alert"
      aria-live="assertive"
      className={`fixed top-0 left-0 right-0 z-[60] transition-all duration-500 ease-in-out ${
        isOnline ? 'translate-y-0' : 'translate-y-0'
      }`}
    >
      <div
        className={`px-4 py-3 shadow-lg border-b ${
          isOnline
            ? 'bg-emerald-50 border-emerald-200 text-emerald-800'
            : 'bg-amber-50 border-amber-200 text-amber-800'
        }`}
      >
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          {/* Icon */}
          <div
            className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
              isOnline
                ? 'bg-emerald-100 text-emerald-600'
                : 'bg-amber-100 text-amber-600'
            }`}
          >
            {isOnline ? (
              <Wifi className="w-4 h-4" />
            ) : (
              <WifiOff className="w-4 h-4" />
            )}
          </div>

          {/* Message */}
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium">
              {isOnline
                ? 'Back Online'
                : 'You Are Offline'}
            </p>
            <p className="text-xs opacity-80 mt-0.5">
              {isOnline
                ? 'Your connection has been restored.'
                : 'Some features may be limited. Changes will sync when connected.'}
            </p>

            {/* Status details */}
            <div className="flex flex-wrap items-center gap-3 mt-1.5">
              {lastSyncTime && (
                <span className="inline-flex items-center gap-1 text-xs opacity-70">
                  <Clock className="w-3 h-3" />
                  Last sync: {formatTime(lastSyncTime)}
                </span>
              )}
              {!isOnline && queuedCount > 0 && (
                <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                  <Zap className="w-3 h-3" />
                  {queuedCount} action{queuedCount !== 1 ? 's' : ''} queued
                </span>
              )}
              {isOnline && syncInProgress && (
                <span className="inline-flex items-center gap-1 text-xs text-emerald-700">
                  <RefreshCw className="w-3 h-3 animate-spin" />
                  Syncing...
                </span>
              )}
            </div>
          </div>

          {/* Actions */}
          <div className="flex items-center gap-2 flex-shrink-0">
            {isOnline && queuedCount > 0 && !syncInProgress && (
              <button
                onClick={handleSyncNow}
                className="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-lg bg-emerald-200 hover:bg-emerald-300 text-emerald-800 transition-colors"
              >
                <RefreshCw className="w-3 h-3" />
                Sync Now
              </button>
            )}
            <button
              onClick={handleDismiss}
              className="text-xs font-medium px-2 py-1 rounded-md hover:bg-black/5 transition-colors opacity-70 hover:opacity-100"
              aria-label="Dismiss"
            >
              Dismiss
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Helpers for enqueuing offline actions ──────────────────────────────────────

interface OfflineAction {
  url: string;
  method: string;
  headers?: Record<string, string>;
  body?: unknown;
  timestamp: number;
}

/**
 * Queue an API action for later replay when connectivity is restored.
 * Call this from your data-fetching layer when a request fails due to
 * network unavailability.
 *
 * Usage:
 *   import { queueOfflineAction } from './OfflineBanner';
 *   await queueOfflineAction('/api/properties/favorite', 'POST', { property_id: 42 });
 */
export async function queueOfflineAction(
  url: string,
  method: string = 'POST',
  body?: unknown,
  headers?: Record<string, string>,
): Promise<void> {
  try {
    const raw = localStorage.getItem('vestra_offline_queue');
    const queue: OfflineAction[] = raw ? JSON.parse(raw) : [];
    queue.push({ url, method, body, headers, timestamp: Date.now() });

    // Cap queue at 500 actions to prevent storage overflow
    const trimmed = queue.slice(-500);
    localStorage.setItem('vestra_offline_queue', JSON.stringify(trimmed));
  } catch {
    // Silently fail — offline queue is best-effort
  }
}
