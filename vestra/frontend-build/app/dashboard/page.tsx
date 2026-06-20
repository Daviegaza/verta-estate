'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { normalizeRole, getDashboardRoute } from '@/lib/roleThemes';
import { Spinner } from '@/components/ui/card';

/**
 * SMART DASHBOARD ROUTER
 *
 * Detects the user's role and redirects to the correct dashboard.
 * - buyer    → /dashboard/buyer
 * - seller   → /dashboard/seller
 * - landlord → /dashboard/landlord
 * - tenant   → /dashboard/tenant
 * - agent    → /dashboard/agent
 * - admin / super_admin → /admin
 *
 * This means the navbar always links to /dashboard and each
 * user lands where they belong.
 */
export default function DashboardRouter() {
  const router = useRouter();
  const { user, isAuthenticated, isHydrated } = useAuthStore();

  useEffect(() => {
    if (!isHydrated) return;

    if (!isAuthenticated || !user) {
      router.replace('/auth/login?redirect=/dashboard');
      return;
    }

    const route = getDashboardRoute(user.role);
    router.replace(route);
  }, [isHydrated, isAuthenticated, user, router]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
      <div className="flex items-center gap-2">
        <div className="w-10 h-10 bg-emerald-600 rounded-xl flex items-center justify-center animate-pulse">
          <span className="text-white font-bold text-lg">V</span>
        </div>
      </div>
      <Spinner size="lg" />
      <p className="text-sm text-gray-500 font-medium">Loading your dashboard...</p>
    </div>
  );
}
