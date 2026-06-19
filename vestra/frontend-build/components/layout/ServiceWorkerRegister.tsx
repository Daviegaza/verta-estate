'use client';

import { useEffect } from 'react';

/**
 * Registers the service worker for PWA offline support and push notifications.
 *
 * IMPORTANT: In development, ALL service workers are aggressively unregistered
 * to prevent stale chunk errors. The SW file (sw.js.prod-only) is only copied
 * to sw.js during the production build.
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    const isDev = process.env.NODE_ENV !== 'production';

    // In development: NUKES all service workers immediately.
    // Stale SWs are the #1 cause of "module factory not available" errors
    // because they serve outdated Turbopack chunks with immutable hashes.
    if (isDev) {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        if (regs.length > 0) {
          console.debug(
            `[Vestra] Dev mode — unregistering ${regs.length} service worker(s) to prevent stale chunks.`
          );
          regs.forEach((r) => r.unregister());
        }
      });
      // Also clear any SW caches for good measure
      if ('caches' in window) {
        caches.keys().then((keys) => {
          keys.forEach((k) => caches.delete(k));
        });
      }
      return;
    }

    // Production: register the service worker (must exist at /sw.js)
    // The build pipeline copies sw.js.prod-only → sw.js in the output.
    navigator.serviceWorker
      .register('/sw.js', { scope: '/', updateViaCache: 'none' })
      .then((registration) => {
        // Listen for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                console.log('[Vestra PWA] New version available. Refresh to update.');
              }
            });
          }
        });
      })
      .catch((err) => {
        // SW registration failed — app works fine without it
        console.debug('[Vestra PWA] Service worker registration skipped:', err.message);
      });
  }, []);

  return null; // This component renders nothing
}
