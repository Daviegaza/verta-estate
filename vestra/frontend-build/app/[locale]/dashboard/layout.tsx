'use client';

import AuthGuard from '@/components/layout/AuthGuard';
import DashboardShell from '@/components/dashboard/DashboardShell';

/**
 * Dashboard Layout
 *
 * Wraps all /dashboard/* routes with AuthGuard + DashboardShell.
 * DashboardShell provides the role-specific sidebar and top bar.
 */
export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard requireAuth>
      <DashboardShell>
        {children}
      </DashboardShell>
    </AuthGuard>
  );
}
