'use client';

import { useEffect } from 'react';

/**
 * Registers the service worker for PWA offline support and push notifications.
 * Runs once on app load. Silent — no UI.
 */
export default function ServiceWorkerRegister() {
  useEffect(() => {
    if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
      return;
    }

    // Register the service worker
    navigator.serviceWorker
      .register('/sw.js', { scope: '/' })
      .then((registration) => {
        // Check for updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          if (newWorker) {
            newWorker.addEventListener('statechange', () => {
              if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
                // New content available — could show update prompt here
                console.log('[Vestra PWA] New version available. Refresh to update.');
              }
            });
          }
        });
      })
      .catch((err) => {
        // Service worker registration failed — app works fine without it
        console.debug('[Vestra PWA] Service worker registration skipped:', err.message);
      });

    // Request push notification permission (deferred — only when user triggers it)
    // The actual permission request happens when user clicks "Enable Notifications"
    if ('Notification' in window && Notification.permission === 'default') {
      // Don't auto-request — wait for user action
      // Notification.requestPermission() is called from a user-triggered button elsewhere
    }
  }, []);

  return null; // This component renders nothing
}
