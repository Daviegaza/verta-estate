'use client';

import { useEffect } from 'react';
import { useAuthStore } from '@/store/authStore';

export default function AuthInit({ children }: { children: React.ReactNode }) {
  const refreshUser = useAuthStore((s) => s.refreshUser);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  useEffect(() => {
    // If a token exists in localStorage but the user isn't authenticated yet,
    // refresh the user session on mount
    const token = localStorage.getItem('vestra_token');
    if (token && !isAuthenticated) {
      refreshUser();
    }
  }, []);

  return <>{children}</>;
}
