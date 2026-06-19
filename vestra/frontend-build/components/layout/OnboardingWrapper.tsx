'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/store/authStore';
import { useOnboardingStore } from '@/store/onboardingStore';
import OnboardingWizard from '@/components/layout/OnboardingWizard';

export default function OnboardingWrapper({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isHydrated } = useAuthStore();
  const { hasCompletedOnboarding, complete } = useOnboardingStore();
  const [showOnboarding, setShowOnboarding] = useState(false);

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) return;

    // Check if user was just created (flag set after registration or first-time phone login)
    const shouldShow = localStorage.getItem('vestra_show_onboarding') === 'true';
    if (shouldShow && !hasCompletedOnboarding) {
      // Small delay so the page renders first
      const timer = setTimeout(() => setShowOnboarding(true), 500);
      return () => clearTimeout(timer);
    }
  }, [isHydrated, isAuthenticated, hasCompletedOnboarding]);

  const handleClose = () => {
    localStorage.removeItem('vestra_show_onboarding');
    complete();
    setShowOnboarding(false);
  };

  return (
    <>
      {children}
      {showOnboarding && <OnboardingWizard onClose={handleClose} />}
    </>
  );
}
