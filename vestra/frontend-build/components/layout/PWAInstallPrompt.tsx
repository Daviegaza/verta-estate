'use client';

import { useState, useEffect } from 'react';
import { Download, X, Share2 } from 'lucide-react';

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: 'accepted' | 'dismissed'; platform: string }>;
}

/**
 * PWA Install Prompt
 * Shows a native-like install banner on iOS Safari (with instructions)
 * and triggers the beforeinstallprompt on Android/Desktop Chrome.
 */
export default function PWAInstallPrompt() {
  const [showPrompt, setShowPrompt] = useState(false);
  const [isIOS, setIsIOS] = useState(false);
  const [isStandalone, setIsStandalone] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    // Check if already installed (standalone mode)
    if (window.matchMedia('(display-mode: standalone)').matches) {
      setIsStandalone(true);
      return;
    }

    // Detect iOS
    const ios = /iphone|ipad|ipod/.test(window.navigator.userAgent.toLowerCase());
    setIsIOS(ios);

    // Listen for install prompt (Android/Desktop Chrome)
    const handler = (e: Event) => {
      e.preventDefault();
      setDeferredPrompt(e as BeforeInstallPromptEvent);
      // Show after 3 seconds on the page
      setTimeout(() => setShowPrompt(true), 3000);
    };

    window.addEventListener('beforeinstallprompt', handler);

    // Show prompt for iOS users after delay
    if (ios) {
      setTimeout(() => setShowPrompt(true), 5000);
    }

    // Track installation
    window.addEventListener('appinstalled', () => {
      setShowPrompt(false);
      setIsStandalone(true);
    });

    return () => {
      window.removeEventListener('beforeinstallprompt', handler);
    };
  }, []);

  const handleInstall = async () => {
    if (deferredPrompt) {
      await deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      if (outcome === 'accepted') {
        setShowPrompt(false);
      }
      setDeferredPrompt(null);
    }
  };

  const handleDismiss = () => {
    setShowPrompt(false);
    // Don't show again for this session
    sessionStorage.setItem('vestra_pwa_prompt_dismissed', 'true');
  };

  if (!showPrompt || isStandalone) return null;

  return (
    <div className="fixed bottom-4 left-4 right-4 z-50 animate-slide-up max-w-md mx-auto">
      <div className="bg-gray-900 text-white rounded-2xl p-4 shadow-2xl border border-gray-700">
        <div className="flex items-start gap-3">
          {/* App Icon */}
          <div className="w-12 h-12 bg-emerald-600 rounded-2xl flex items-center justify-center flex-shrink-0">
            <span className="text-white font-bold text-xl">V</span>
          </div>

          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between">
              <h3 className="font-semibold text-sm">Install Vestra App</h3>
              <button
                onClick={handleDismiss}
                className="text-gray-400 hover:text-white p-1"
                aria-label="Dismiss"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <p className="text-gray-400 text-xs mt-1 leading-relaxed">
              {isIOS
                ? 'Tap the Share button below and select "Add to Home Screen" to install Vestra on your iPhone.'
                : 'Install Vestra on your device for the best experience — fast, offline-ready, and always with you.'}
            </p>

            <div className="flex items-center gap-2 mt-3">
              {isIOS ? (
                <div className="flex items-center gap-2 text-emerald-400 text-xs">
                  <Share2 className="w-4 h-4" />
                  <span>Tap Share → Add to Home Screen</span>
                </div>
              ) : (
                <button
                  onClick={handleInstall}
                  className="inline-flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-semibold px-3 py-1.5 rounded-xl transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  Install App
                </button>
              )}
              <span className="text-gray-500 text-xs">Free • 2MB • Works offline</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
