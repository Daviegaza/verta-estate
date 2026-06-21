'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { RefreshCw, Bell, X, ChevronDown } from 'lucide-react';

/**
 * Service Worker Update Notification
 *
 * Listens for service worker updates and displays a toast when a new
 * version of the app is available. The user can refresh to activate
 * the new version immediately.
 *
 * Integrates with ServiceWorkerRegister.tsx — it uses the same
 * 'updatefound' event pathway but adds the UI layer.
 */
export default function UpdateNotification() {
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(null);
  const [registration, setRegistration] = useState<ServiceRegistration | null>(null);
  const [showToast, setShowToast] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const [updateVersion, setUpdateVersion] = useState<string | null>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [refreshCountdown, setRefreshCountdown] = useState<number | null>(null);
  const mountedRef = useRef(true);
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Parse version from cache metadata ─────────────────────────────────────

  const detectVersion = useCallback(async (reg: ServiceWorkerRegistration): Promise<string | null> => {
    try {
      // Try reading the app version from the cache
      const cache = await caches.open('vestra-app-shell-v1');
      const cachedResponse = await cache.match('/version.json');
      if (cachedResponse) {
        const data = await cachedResponse.json();
        return data.version || null;
      }
    } catch {
      // Fallback: check the SW script URL for a hash
      try {
        const url = reg.active?.scriptURL || reg.installing?.scriptURL || '';
        const match = url.match(/sw\.js\?v=([a-f0-9]+)/);
        if (match) return match[1].slice(0, 8);
      } catch {
        // Ignore
      }
    }
    return null;
  }, []);

  // ── Listen for SW updates ───────────────────────────────────────────────────

  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    mountedRef.current = true;

    const setupListener = async () => {
      try {
        const reg = await navigator.serviceWorker.getRegistration('/');
        if (!reg) return;

        setRegistration(reg);

        // Check if there's already a waiting worker (e.g. after a previous update)
        if (reg.waiting && reg.active) {
          const version = await detectVersion(reg);
          if (mountedRef.current) {
            setWaitingWorker(reg.waiting);
            setUpdateVersion(version);
            setShowToast(true);
          }
          return;
        }

        // Listen for new updates
        reg.addEventListener('updatefound', () => {
          const newWorker = reg.installing;
          if (!newWorker) return;

          newWorker.addEventListener('statechange', async () => {
            if (!mountedRef.current) return;

            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New version is available — show the toast
              const version = await detectVersion(reg);
              setWaitingWorker(newWorker);
              setUpdateVersion(version);
              setShowToast(true);
              setDismissed(false);
            }

            if (newWorker.state === 'activated') {
              // Update completed — clean up
              if (mountedRef.current) {
                setWaitingWorker(null);
                setShowToast(false);
              }
            }
          });
        });
      } catch {
        // SW not available — component is a no-op
      }
    };

    setupListener();

    // Also listen for controller changes (post-refresh signals)
    const handleControllerChange = () => {
      if (mountedRef.current) {
        setWaitingWorker(null);
        setShowToast(false);
        setRefreshCountdown(null);
      }
    };

    navigator.serviceWorker.addEventListener('controllerchange', handleControllerChange);

    return () => {
      mountedRef.current = false;
      navigator.serviceWorker.removeEventListener('controllerchange', handleControllerChange);
      if (countdownRef.current) clearInterval(countdownRef.current);
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current);
    };
  }, [detectVersion]);

  // ── Refresh to activate the new version ─────────────────────────────────────

  const handleRefresh = useCallback(() => {
    // Notify the waiting worker to become active
    if (waitingWorker) {
      // Start a 5-second countdown
      setRefreshCountdown(5);
      countdownRef.current = setInterval(() => {
        setRefreshCountdown((prev) => {
          if (prev === null || prev <= 1) {
            if (countdownRef.current) clearInterval(countdownRef.current);
            // Post message to SW to skip waiting
            waitingWorker.postMessage({ type: 'SKIP_WAITING' });
            // Force reload after a brief delay
            setTimeout(() => window.location.reload(), 300);
            return null;
          }
          return prev - 1;
        });
      }, 1000);
    } else {
      // Fallback: just reload
      window.location.reload();
    }
  }, [waitingWorker]);

  // ── Dismiss ────────────────────────────────────────────────────────────────

  const handleDismiss = useCallback(() => {
    setShowToast(false);
    setDismissed(true);
    setShowDetails(false);
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    setRefreshCountdown(null);
  }, []);

  // ── Postpone (remind later) ────────────────────────────────────────────────

  const handlePostpone = useCallback(() => {
    setShowToast(false);
    setShowDetails(false);
    if (countdownRef.current) {
      clearInterval(countdownRef.current);
      countdownRef.current = null;
    }
    setRefreshCountdown(null);

    // Show again in 30 minutes
    toastTimerRef.current = setTimeout(() => {
      if (mountedRef.current && !dismissed) {
        setShowToast(true);
      }
    }, 30 * 60 * 1000);
  }, [dismissed]);

  // ── Force check for updates ────────────────────────────────────────────────

  const handleCheckForUpdates = useCallback(async () => {
    try {
      const reg = await navigator.serviceWorker.getRegistration('/');
      if (reg) {
        await reg.update();
      }
    } catch {
      // Silent fail
    }
  }, []);

  // ── Render ─────────────────────────────────────────────────────────────────

  if (!showToast || dismissed) return null;

  return (
    <div
      role="alert"
      aria-live="polite"
      className="fixed bottom-4 left-4 right-4 z-50 max-w-md mx-auto animate-slide-up"
    >
      <div className="bg-white rounded-2xl shadow-2xl border border-gray-200 overflow-hidden">
        {/* Header */}
        <div className="flex items-start gap-3 p-4">
          <div className="w-10 h-10 bg-blue-100 rounded-full flex items-center justify-center flex-shrink-0">
            <Bell className="w-5 h-5 text-blue-600" />
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm text-gray-900">
                Update Available
              </h3>
              <button
                onClick={handleDismiss}
                className="text-gray-400 hover:text-gray-600 p-1 -mr-1 rounded-lg hover:bg-gray-100 transition-colors"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <p className="text-sm text-gray-600 mt-1 leading-relaxed">
              A new version of Vestra is ready{updateVersion ? ` (v${updateVersion})` : ''}.
              Refresh to get the latest features and improvements.
            </p>

            {/* Version details */}
            <button
              onClick={() => setShowDetails(!showDetails)}
              className="inline-flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700 mt-1.5 transition-colors"
            >
              <ChevronDown
                className={`w-3 h-3 transition-transform ${
                  showDetails ? 'rotate-180' : ''
                }`}
              />
              {showDetails ? 'Hide details' : 'What\'s in this update?'}
            </button>

            {showDetails && (
              <div className="mt-2 p-2.5 bg-gray-50 rounded-lg border border-gray-100">
                <ul className="text-xs text-gray-500 space-y-1 list-disc list-inside">
                  <li>Performance improvements and bug fixes</li>
                  <li>Enhanced security and reliability</li>
                  <li>Latest features activated on refresh</li>
                </ul>
              </div>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="px-4 pb-4 pt-1 flex items-center gap-2">
          {refreshCountdown !== null ? (
            <div className="flex-1 flex items-center justify-center gap-2 py-2 bg-blue-600 text-white rounded-xl text-sm font-semibold">
              <RefreshCw className="w-4 h-4 animate-spin" />
              Refreshing in {refreshCountdown}s...
            </div>
          ) : (
            <>
              <button
                onClick={handleRefresh}
                className="flex-1 inline-flex items-center justify-center gap-2 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-xl transition-colors"
              >
                <RefreshCw className="w-4 h-4" />
                Refresh Now
              </button>
              <button
                onClick={handlePostpone}
                className="px-4 py-2 text-sm font-medium text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-xl transition-colors"
              >
                Later
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

// ── Type helper ────────────────────────────────────────────────────────────────

interface ServiceRegistration extends ServiceWorkerRegistration {
  waiting: ServiceWorker | null;
}
