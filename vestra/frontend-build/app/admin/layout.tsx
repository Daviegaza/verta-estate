'use client';

import { useEffect, useState } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import Link from 'next/link';
import { useAuthStore } from '@/store/authStore';
import { Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import {
  BarChart3, Users, Building2, ShieldCheck, CreditCard,
  FileText, AlertTriangle, Activity, Settings, LogOut,
  ChevronLeft, ChevronRight, Menu, X, Search, Bell,
  Home, Key, Database, TrendingUp, DollarSign,
} from 'lucide-react';

const NAV_ITEMS = [
  { key: 'overview', label: 'Dashboard', href: '/admin', icon: <BarChart3 className="w-5 h-5" /> },
  { key: 'users', label: 'Users', href: '/admin?tab=users', icon: <Users className="w-5 h-5" /> },
  { key: 'properties', label: 'Properties', href: '/admin?tab=properties', icon: <Building2 className="w-5 h-5" /> },
  { key: 'payments', label: 'Payments', href: '/admin?tab=payments', icon: <CreditCard className="w-5 h-5" /> },
  { key: 'verifications', label: 'Verifications', href: '/admin?tab=verifications', icon: <ShieldCheck className="w-5 h-5" /> },
  { key: 'kyc', label: 'KYC Review', href: '/admin?tab=kyc', icon: <FileText className="w-5 h-5" /> },
  { key: 'fraud', label: 'Fraud Reports', href: '/admin?tab=fraud', icon: <AlertTriangle className="w-5 h-5" /> },
  { key: 'audit', label: 'Audit Logs', href: '/admin?tab=audit', icon: <Activity className="w-5 h-5" /> },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isHydrated, logout } = useAuthStore();
  const [verified, setVerified] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const isAdmin = user?.role === 'admin' || user?.role === 'super_admin';
  const isLoginPage = pathname === '/admin/login';

  useEffect(() => {
    if (isLoginPage) { setVerified(true); return; }

    const token = typeof window !== 'undefined' ? localStorage.getItem('vestra_token') : null;
    if (!token) { router.replace('/admin/login'); return; }

    // Trust the store first (login page already verified role)
    const storedUser = useAuthStore.getState().user;
    if (storedUser && (storedUser.role === 'admin' || storedUser.role === 'super_admin')) {
      setVerified(true);
      // Background re-verify (non-blocking)
      api.getMe().catch(() => {});
      return;
    }

    // Fallback: verify via API (only if store doesn't have admin)
    api.getMe()
      .then(serverUser => {
        if (serverUser.role !== 'admin' && serverUser.role !== 'super_admin') {
          logout(); router.replace('/admin/login'); return;
        }
        useAuthStore.setState({ user: serverUser, isAuthenticated: true, token });
        setVerified(true);
      })
      .catch(() => { logout(); router.replace('/admin/login'); });
  }, [isLoginPage]);

  if (!verified && !isLoginPage) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 bg-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
            <Settings className="w-6 h-6 text-white" />
          </div>
          <Spinner size="lg" />
          <p className="text-gray-400 text-sm mt-4">Verifying admin access...</p>
        </div>
      </div>
    );
  }

  // Login page — no sidebar
  if (isLoginPage) return <>{children}</>;

  // Get active tab from URL
  const searchParams = typeof window !== 'undefined' ? new URLSearchParams(window.location.search) : null;
  const activeTab = searchParams?.get('tab') || 'overview';

  return (
    <div className="min-h-screen bg-gray-100 flex">
      {/* ── Sidebar ── */}
      <aside className={`fixed inset-y-0 left-0 z-40 bg-gray-950 text-gray-300 flex flex-col transition-all duration-300 ${
        collapsed ? 'w-[72px]' : 'w-64'
      } ${mobileOpen ? 'translate-x-0' : '-translate-x-full'} lg:translate-x-0`}>
        {/* Logo */}
        <div className={`flex items-center h-16 px-4 border-b border-gray-800 ${collapsed ? 'justify-center' : 'gap-3'}`}>
          <div className="w-9 h-9 bg-emerald-600 rounded-xl flex items-center justify-center shrink-0">
            <span className="text-white font-bold text-sm">V</span>
          </div>
          {!collapsed && (
            <div>
              <p className="text-white font-bold text-sm">Vestra Admin</p>
              <p className="text-gray-500 text-xs">Control Panel</p>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
          {NAV_ITEMS.map(item => (
            <button
              key={item.key}
              onClick={() => {
                setMobileOpen(false);
                window.history.pushState({}, '', item.href);
                window.dispatchEvent(new Event('admin-tab-change'));
              }}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all w-full text-left ${
                activeTab === item.key || (item.key === 'overview' && !searchParams?.get('tab') && pathname === '/admin')
                  ? 'bg-emerald-600 text-white shadow-lg shadow-emerald-900/30'
                  : 'text-gray-400 hover:text-white hover:bg-gray-800'
              } ${collapsed ? 'justify-center' : ''}`}
              title={collapsed ? item.label : undefined}
            >
              {item.icon}
              {!collapsed && <span>{item.label}</span>}
            </button>
          ))}
        </nav>

        {/* Bottom */}
        <div className={`p-3 border-t border-gray-800 ${collapsed ? 'text-center' : ''}`}>
          {!collapsed && user && (
            <div className="flex items-center gap-2 mb-3 px-2">
              <div className="w-8 h-8 bg-emerald-700 rounded-full flex items-center justify-center text-white text-xs font-bold shrink-0">
                {user.full_name?.[0]?.toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-medium text-white truncate">{user.full_name}</p>
                <p className="text-xs text-gray-500">{user.role?.replace('_', ' ')}</p>
              </div>
            </div>
          )}
          <div className={`flex ${collapsed ? 'flex-col' : ''} gap-1`}>
            <Link href="/" className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-gray-400 hover:text-white hover:bg-gray-800 transition-colors ${collapsed ? 'justify-center' : ''}`}>
              <Home className="w-4 h-4" />
              {!collapsed && 'Main Site'}
            </Link>
            <button onClick={() => { logout(); router.push('/admin/login'); }}
              className={`flex items-center gap-2 px-3 py-2 rounded-xl text-xs text-red-400 hover:text-red-300 hover:bg-red-900/20 transition-colors ${collapsed ? 'justify-center' : ''}`}>
              <LogOut className="w-4 h-4" />
              {!collapsed && 'Sign Out'}
            </button>
          </div>
        </div>

        {/* Collapse button (desktop) */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="hidden lg:flex absolute -right-3 top-20 w-6 h-6 bg-gray-800 border border-gray-700 rounded-full items-center justify-center hover:bg-gray-700 transition-colors"
        >
          {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
        </button>
      </aside>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div className="fixed inset-0 z-30 bg-black/50 lg:hidden" onClick={() => setMobileOpen(false)} />
      )}

      {/* ── Main Content ── */}
      <div className={`flex-1 transition-all duration-300 ${collapsed ? 'lg:ml-[72px]' : 'lg:ml-64'}`}>
        {/* Top bar */}
        <header className="sticky top-0 z-20 bg-white border-b border-gray-200 h-16 flex items-center justify-between px-4 sm:px-6">
          <div className="flex items-center gap-3">
            <button onClick={() => setMobileOpen(true)} className="lg:hidden p-2 -ml-2 rounded-lg hover:bg-gray-100">
              <Menu className="w-5 h-5 text-gray-600" />
            </button>
            <div>
              <h1 className="text-lg font-bold text-gray-900 hidden sm:block">Admin Panel</h1>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/" className="text-xs text-gray-500 hover:text-gray-700 hidden sm:flex items-center gap-1">
              <Home className="w-3.5 h-3.5" /> View Site
            </Link>
            <div className="w-px h-6 bg-gray-200 hidden sm:block" />
            <button
              onClick={() => { logout(); router.push('/admin/login'); }}
              className="text-xs text-gray-500 hover:text-red-600 flex items-center gap-1"
            >
              <LogOut className="w-3.5 h-3.5" /> Sign Out
            </button>
          </div>
        </header>

        {/* Page content */}
        <main className="p-4 sm:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
