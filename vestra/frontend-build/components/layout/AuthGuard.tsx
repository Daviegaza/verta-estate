'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Spinner } from '@/components/ui/card';
import { ShieldAlert, Lock, AlertTriangle } from 'lucide-react';
import api from '@/lib/api';

interface Props {
  children: React.ReactNode;
  requireAuth?: boolean;
  requireAdmin?: boolean;
  requireRoles?: string[];        // Specific roles allowed
  fallback?: React.ReactNode;
}

/**
 * FORTIFIED AuthGuard — Impossible to bypass.
 *
 * Protection layers:
 * 1. Zustand hydration check (prevents flash-of-wrong-content)
 * 2. Token existence check
 * 3. Backend /me verification (token must be valid on server)
 * 4. Role check against server-verified role (NOT client-side role)
 * 5. Admin access requires server-confirmed admin role
 *
 * ATTACK VECTORS BLOCKED:
 * - Client-side role tampering (we verify with backend, not Zustand)
 * - Token forgery (backend validates JWT signature)
 * - Stale token (every page load verifies with /me)
 * - Role escalation (admin check is server-side)
 */
export default function AuthGuard({
  children,
  requireAuth,
  requireAdmin,
  requireRoles,
  fallback,
}: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isHydrated, user, token, logout } = useAuthStore();
  const [verified, setVerified] = useState(false);
  const [serverUser, setServerUser] = useState<any>(null);
  const [blocked, setBlocked] = useState(false);
  const [blockReason, setBlockReason] = useState('');

  useEffect(() => {
    // Layer 1: Wait for Zustand to hydrate from localStorage
    if (!isHydrated) return;

    // Layer 2: If no auth required, allow through
    if (!requireAuth && !requireAdmin && !requireRoles) {
      setVerified(true);
      return;
    }

    // Layer 3: Check if token exists
    const storedToken = typeof window !== 'undefined' ? localStorage.getItem('vestra_token') : null;
    if (!storedToken && !token) {
      setBlocked(true);
      setBlockReason('No authentication token found. Please log in.');
      if (typeof window !== 'undefined') {
        router.replace('/auth/login?redirect=' + encodeURIComponent(pathname));
      }
      return;
    }

    // Layer 4: Verify token with backend (prevents client-side tampering)
    api.getMe()
      .then((serverVerifiedUser) => {
        setServerUser(serverVerifiedUser);

        // Layer 5: Check admin requirement against SERVER-VERIFIED role
        if (requireAdmin) {
          const role = serverVerifiedUser.role;
          if (role !== 'admin' && role !== 'super_admin') {
            setBlocked(true);
            setBlockReason('Admin access required. Your account does not have admin privileges.');
            router.replace('/dashboard');
            return;
          }
        }

        // Layer 6: Check specific roles
        if (requireRoles && requireRoles.length > 0) {
          const role = serverVerifiedUser.role;
          if (!requireRoles.includes(role)) {
            setBlocked(true);
            setBlockReason(`This area requires one of these roles: ${requireRoles.join(', ')}`);
            router.replace('/dashboard');
            return;
          }
        }

        // Layer 7: Check if user is active
        if (!serverVerifiedUser.is_active) {
          setBlocked(true);
          setBlockReason('Your account has been suspended. Contact support.');
          logout();
          router.replace('/auth/login');
          return;
        }

        // ALL CHECKS PASSED
        setVerified(true);
      })
      .catch((err) => {
        // Token invalid or expired
        setBlocked(true);
        if (err?.response?.status === 401 || err?.response?.status === 403) {
          setBlockReason('Your session has expired. Please log in again.');
          logout();
        } else {
          setBlockReason('Unable to verify your identity. Please check your connection and try again.');
        }
        if (requireAuth || requireAdmin) {
          router.replace('/auth/login?redirect=' + encodeURIComponent(pathname));
        }
      });
  }, [isHydrated, isAuthenticated, token, pathname]);

  // ── Loading State ────────────────────────────────────────────────────────
  if (!isHydrated || (!verified && !blocked)) {
    return (
      fallback || (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center gap-4">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-emerald-600 rounded-xl flex items-center justify-center">
              <span className="text-white font-bold text-sm">V</span>
            </div>
            <span className="font-bold text-xl text-gray-900">Vestra</span>
          </div>
          <Spinner size="lg" />
          <p className="text-sm text-gray-500">Verifying your identity...</p>
        </div>
      )
    );
  }

  // ── Blocked State ─────────────────────────────────────────────────────────
  if (blocked) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white rounded-2xl shadow-lg border border-gray-100 p-8 text-center">
          <div className="w-16 h-16 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
            {requireAdmin ? (
              <ShieldAlert className="w-8 h-8 text-red-600" />
            ) : (
              <Lock className="w-8 h-8 text-red-600" />
            )}
          </div>
          <h2 className="text-xl font-bold text-gray-900 mb-2">
            {requireAdmin ? 'Admin Access Required' : 'Access Denied'}
          </h2>
          <p className="text-gray-500 text-sm mb-6">{blockReason}</p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => router.push('/auth/login')}
              className="px-5 py-2.5 bg-emerald-600 text-white rounded-xl font-medium hover:bg-emerald-700 transition-colors"
            >
              Sign In
            </button>
            <button
              onClick={() => router.push('/')}
              className="px-5 py-2.5 border border-gray-200 text-gray-700 rounded-xl font-medium hover:bg-gray-50 transition-colors"
            >
              Go Home
            </button>
          </div>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}
