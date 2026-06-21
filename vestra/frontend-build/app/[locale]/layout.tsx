import { NextIntlClientProvider } from 'next-intl';
import { getMessages, getLocale } from 'next-intl/server';
import { ToastProvider } from '@/components/ui/toaster';
import AuthInit from '@/components/layout/AuthInit';
import ErrorBoundary from '@/components/layout/ErrorBoundary';
import OnboardingWrapper from '@/components/layout/OnboardingWrapper';
import PWAInstallPrompt from '@/components/layout/PWAInstallPrompt';
import ServiceWorkerRegister from '@/components/layout/ServiceWorkerRegister';
import { ThemeProvider } from '@/components/layout/ThemeProvider';

export default async function LocaleLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();

  return (
    <NextIntlClientProvider locale={locale} messages={messages}>
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
    </NextIntlClientProvider>
  );
}
