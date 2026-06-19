import type { Metadata, Viewport } from 'next';
import './globals.css';
import { ToastProvider } from '@/components/ui/toaster';
import AuthInit from '@/components/layout/AuthInit';
import ErrorBoundary from '@/components/layout/ErrorBoundary';
import OnboardingWrapper from '@/components/layout/OnboardingWrapper';
import PWAInstallPrompt from '@/components/layout/PWAInstallPrompt';
import ServiceWorkerRegister from '@/components/layout/ServiceWorkerRegister';
import { ThemeProvider } from '@/components/layout/ThemeProvider';

export const metadata: Metadata = {
  title: 'Vestra — AI-Powered Property Trust Platform | Kenya',
  description: 'Buy, sell, rent, and verify properties in Kenya with AI-powered trust scoring. M-Pesa payments, title chain verification, and escrow protection.',
  keywords: ['real estate', 'Kenya', 'property verification', 'AI', 'M-Pesa', 'Africa', 'WhatsApp', 'title deed', 'escrow'],
  authors: [{ name: 'Vestra', url: 'https://vestra.co.ke' }],
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000'),
  alternates: { canonical: '/' },
  openGraph: {
    title: 'Vestra — AI-Powered Property Trust Platform | Kenya',
    description: 'Buy, sell, rent, and verify properties in Kenya with AI-powered trust scoring. M-Pesa payments, title chain verification, and escrow protection.',
    type: 'website',
    locale: 'en_KE',
    siteName: 'Vestra',
    url: '/',
    images: [{ url: '/screenshots/home.png', width: 1280, height: 720 }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Vestra — AI-Powered Property Trust Platform | Kenya',
    description: 'Buy, sell, rent, and verify properties in Kenya with AI-powered trust scoring. M-Pesa payments, title chain verification, and escrow protection.',
    images: ['/screenshots/home.png'],
  },
  appleWebApp: {
    capable: true,
    title: 'Vestra',
    statusBarStyle: 'black-translucent',
    startupImage: ['/icons/icon-512x512.png'],
  },
  applicationName: 'Vestra',
  formatDetection: { telephone: true, date: true, address: true },
  manifest: '/manifest.json',
  robots: { index: true, follow: true },
  other: {
    'mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-capable': 'yes',
    'apple-mobile-web-app-title': 'Vestra',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
  themeColor: '#10b981',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning className="light" style={{ colorScheme: 'light' }}>
      <head>
        {/* Apple touch icon */}
        <link rel="apple-touch-icon" href="/icons/icon-192x192.png" />
        <link rel="apple-touch-icon" sizes="512x512" href="/icons/icon-512x512.png" />
        {/* Favicon */}
        <link rel="icon" type="image/png" sizes="32x32" href="/icons/icon-72x72.png" />
        <link rel="icon" type="image/png" sizes="192x192" href="/icons/icon-192x192.png" />
        {/* Safari pinned tab */}
        <link rel="mask-icon" href="/icons/icon-512x512.png" color="#10b981" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="apple-mobile-web-app-title" content="Vestra" />
        {/* Microsoft tiles */}
        <meta name="msapplication-TileColor" content="#10b981" />
        <meta name="msapplication-TileImage" content="/icons/icon-144x144.png" />
        {/* Theme color */}
        <meta name="theme-color" content="#10b981" media="(prefers-color-scheme: light)" />
        <meta name="theme-color" content="#111827" media="(prefers-color-scheme: dark)" />
      </head>
      <body style={{ fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif' }}>
        <ErrorBoundary>
          <ThemeProvider>
            <AuthInit>
              <ToastProvider>
                <OnboardingWrapper>
                  {children}
                </OnboardingWrapper>
                <PWAInstallPrompt />
                <ServiceWorkerRegister />
              </ToastProvider>
            </AuthInit>
          </ThemeProvider>
        </ErrorBoundary>
      </body>
    </html>
  );
}
