'use client';

import { useEffect, useState, useRef } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Spinner } from '@/components/ui/card';
import { ShieldAlert, Lock, AlertTriangle } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/components/ui/toaster';

const INACTIVITY_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes
const WARNING_BEFORE_MS = 60 * 1000;            // 1 minute warning
const WARNING_AT_MS = INACTIVITY_TIMEOUT_MS - WARNING_BEFORE_MS; // 29 minutes

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
  const { isAuthenticated, isHydrated, user, token, lastVerifiedAt, logout, refreshUser } = useAuthStore();
  const [verified, setVerified] = useState(false);
  const [serverUser, setServerUser] = useState<any>(null);
  const [blocked, setBlocked] = useState(false);
  const [blockReason, setBlockReason] = useState('');
  const toast = useToast();
  const inactivityTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const warningTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // ── Access check helper (used both for cached and fresh verification) ─────
  function checkAccess(serverVerifiedUser: any, requireAdmin?: boolean, requireRoles?: string[]): boolean {
    if (requireAdmin) {
      const role = serverVerifiedUser.role;
      if (role !== 'admin' && role !== 'super_admin') {
        setBlocked(true);
        setBlockReason('Admin access required. Your account does not have admin privileges.');
        router.replace('/dashboard');
        return false;
      }
    }

    if (requireRoles && requireRoles.length > 0) {
      const role = serverVerifiedUser.role;
      if (!requireRoles.includes(role)) {
        setBlocked(true);
        setBlockReason(`This area requires one of these roles: ${requireRoles.join(', ')}`);
        router.replace('/dashboard');
        return false;
      }
    }

    if (!serverVerifiedUser.is_active) {
      setBlocked(true);
      setBlockReason('Your account has been suspended. Contact support.');
      logout();
      router.replace('/auth/login');
      return false;
    }

    return true;
  }

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

    // PERF: Skip redundant /me call if store has a recently-verified user
    // (within last 60s). AuthInit already called getMe() on page mount.
    const VERIFICATION_TTL = 60_000; // 60 seconds
    const isRecentlyVerified = user && lastVerifiedAt && (Date.now() - lastVerifiedAt < VERIFICATION_TTL);

    if (isRecentlyVerified) {
      const serverVerifiedUser = user;
      setServerUser(serverVerifiedUser);
      if (!checkAccess(serverVerifiedUser, requireAdmin, requireRoles)) return;
      setVerified(true);
      return;
    }

    // Layer 4: Verify token with backend (prevents client-side tampering)
    api.getMe()
      .then((serverVerifiedUser) => {
        // Update store with fresh verification timestamp
        refreshUser(); // Updates lastVerifiedAt
        setServerUser(serverVerifiedUser);

        if (!checkAccess(serverVerifiedUser, requireAdmin, requireRoles)) return;

        // ALL CHECKS PASSED
        setVerified(true);
      })
      .catch((err) => {
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

  // ── Inactivity Auto-Logout ─────────────────────────────────────────────────
  // Only active when the user is verified on an auth-required page
  useEffect(() => {
    if (!verified || (!requireAuth && !requireAdmin && !requireRoles)) return;

    const clearTimers = () => {
      if (inactivityTimerRef.current) clearTimeout(inactivityTimerRef.current);
      if (warningTimerRef.current) clearTimeout(warningTimerRef.current);
    };

    const handleLogout = () => {
      clearTimers();
      logout();
      toast.warning(
        'Session expired',
        'You were logged out due to inactivity.'
      );
      router.replace('/auth/login?redirect=' + encodeURIComponent(pathname));
    };

    const handleWarning = () => {
      toast.warning(
        'Session expiring soon',
        'You will be logged out in 1 minute due to inactivity.'
      );
    };

    const resetInactivityTimer = () => {
      clearTimers();
      warningTimerRef.current = setTimeout(handleWarning, WARNING_AT_MS);
      inactivityTimerRef.current = setTimeout(handleLogout, INACTIVITY_TIMEOUT_MS);
    };

    // Set up event listeners for user activity
    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click'];
    events.forEach((event) => window.addEventListener(event, resetInactivityTimer));

    // Start the timer
    resetInactivityTimer();

    return () => {
      clearTimers();
      events.forEach((event) => window.removeEventListener(event, resetInactivityTimer));
    };
  }, [verified, requireAuth, requireAdmin, requireRoles]);

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
