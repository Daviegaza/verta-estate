'use client';

import { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/authStore';
import { getRoleTheme, normalizeRole, type RoleSlug } from '@/lib/roleThemes';
import { Button } from '@/components/ui/button';
import {
  Home, Search, Building2, Users, TrendingUp,
  Briefcase, Shield, Settings, CreditCard, MessageSquare,
  Star, Bell, Menu, X, ChevronLeft, LogOut,
  Plus, Eye, DollarSign, Wrench, FileText, Heart,
  UserCheck, Activity, BarChart3, Phone, Key, Zap,
} from 'lucide-react';

// ── Navigation config per role ──────────────────────────────────────────────

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
  external?: boolean;
}

const ROLE_NAV: Record<RoleSlug, { header: string; items: NavItem[]; secondary: NavItem[] }> = {
  buyer: {
    header: 'Buyer Dashboard',
    items: [
      { label: 'Overview', href: '/dashboard/buyer', icon: <Home className="w-4 h-4" /> },
      { label: 'Saved Properties', href: '/dashboard/buyer/favorites', icon: <Heart className="w-4 h-4" /> },
      { label: 'My Escrows', href: '/dashboard/buyer/escrow', icon: <Shield className="w-4 h-4" /> },
      { label: 'Market Insights', href: '/market', icon: <TrendingUp className="w-4 h-4" /> },
    ],
    secondary: [
      { label: 'Browse Properties', href: '/market', icon: <Search className="w-4 h-4" /> },
      { label: 'Verify Property', href: '/verify', icon: <Shield className="w-4 h-4" /> },
      { label: 'Messages', href: '/messages', icon: <MessageSquare className="w-4 h-4" /> },
      { label: 'Settings', href: '/settings', icon: <Settings className="w-4 h-4" /> },
    ],
  },
  seller: {
    header: 'Seller Dashboard',
    items: [
      { label: 'Overview', href: '/dashboard/seller', icon: <Home className="w-4 h-4" /> },
      { label: 'My Listings', href: '/properties/my', icon: <Building2 className="w-4 h-4" /> },
      { label: 'Add Listing', href: '/properties/new', icon: <Plus className="w-4 h-4" /> },
      { label: 'Analytics', href: '/dashboard/seller/analytics', icon: <BarChart3 className="w-4 h-4" /> },
      { label: 'Pending Verifications', href: '/verify', icon: <Shield className="w-4 h-4" /> },
    ],
    secondary: [
      { label: 'Browse Market', href: '/market', icon: <Search className="w-4 h-4" /> },
      { label: 'Messages', href: '/messages', icon: <MessageSquare className="w-4 h-4" /> },
      { label: 'Payouts', href: '/wallet', icon: <DollarSign className="w-4 h-4" /> },
      { label: 'Settings', href: '/settings', icon: <Settings className="w-4 h-4" /> },
    ],
  },
  landlord: {
    header: 'Landlord Dashboard',
    items: [
      { label: 'Overview', href: '/dashboard/landlord', icon: <Home className="w-4 h-4" /> },
      { label: 'My Units', href: '/properties/my', icon: <Building2 className="w-4 h-4" /> },
      { label: 'Tenants', href: '/dashboard/landlord/tenants', icon: <Users className="w-4 h-4" /> },
      { label: 'Maintenance', href: '/dashboard/landlord/maintenance', icon: <Wrench className="w-4 h-4" /> },
      { label: 'Add Unit', href: '/properties/new', icon: <Plus className="w-4 h-4" /> },
    ],
    secondary: [
      { label: 'Messages', href: '/messages', icon: <MessageSquare className="w-4 h-4" /> },
      { label: 'Collect Rent', href: '/wallet', icon: <CreditCard className="w-4 h-4" /> },
      { label: 'Settings', href: '/settings', icon: <Settings className="w-4 h-4" /> },
    ],
  },
  tenant: {
    header: 'Tenant Portal',
    items: [
      { label: 'Overview', href: '/dashboard/tenant', icon: <Home className="w-4 h-4" /> },
      { label: 'Find a Home', href: '/dashboard/tenant/discover', icon: <Search className="w-4 h-4" /> },
      { label: 'Pay Rent', href: '/dashboard/tenant/rent', icon: <CreditCard className="w-4 h-4" /> },
      { label: 'My Receipts', href: '/dashboard/tenant/receipts', icon: <FileText className="w-4 h-4" /> },
      { label: 'Maintenance', href: '/dashboard/tenant/maintenance', icon: <Wrench className="w-4 h-4" /> },
    ],
    secondary: [
      { label: 'Browse Market', href: '/market', icon: <Search className="w-4 h-4" /> },
      { label: 'Messages', href: '/messages', icon: <MessageSquare className="w-4 h-4" /> },
      { label: 'Settings', href: '/settings', icon: <Settings className="w-4 h-4" /> },
    ],
  },
  agent: {
    header: 'Agent Dashboard',
    items: [
      { label: 'Overview', href: '/dashboard/agent', icon: <Home className="w-4 h-4" /> },
      { label: 'My Listings', href: '/properties/my', icon: <Building2 className="w-4 h-4" /> },
      { label: 'Leads', href: '/dashboard/agent/leads', icon: <UserCheck className="w-4 h-4" /> },
      { label: 'Commissions', href: '/dashboard/agent/commissions', icon: <DollarSign className="w-4 h-4" /> },
      { label: 'Add Listing', href: '/properties/new', icon: <Plus className="w-4 h-4" /> },
    ],
    secondary: [
      { label: 'Browse Market', href: '/market', icon: <Search className="w-4 h-4" /> },
      { label: 'Messages', href: '/messages', icon: <MessageSquare className="w-4 h-4" /> },
      { label: 'Payouts', href: '/wallet', icon: <CreditCard className="w-4 h-4" /> },
      { label: 'Reviews', href: '/agents', icon: <Star className="w-4 h-4" /> },
      { label: 'Settings', href: '/settings', icon: <Settings className="w-4 h-4" /> },
    ],
  },
  admin: {
    header: 'Admin Panel',
    items: [
      { label: 'Overview', href: '/admin', icon: <Home className="w-4 h-4" /> },
      { label: 'Users', href: '/admin?tab=users', icon: <Users className="w-4 h-4" /> },
      { label: 'Properties', href: '/admin?tab=properties', icon: <Building2 className="w-4 h-4" /> },
      { label: 'Payments', href: '/admin?tab=payments', icon: <CreditCard className="w-4 h-4" /> },
      { label: 'Verifications', href: '/admin?tab=verifications', icon: <Shield className="w-4 h-4" /> },
      { label: 'KYC', href: '/admin?tab=kyc', icon: <FileText className="w-4 h-4" /> },
      { label: 'Fraud', href: '/admin?tab=fraud', icon: <Shield className="w-4 h-4" /> },
      { label: 'Audit', href: '/admin?tab=audit', icon: <Activity className="w-4 h-4" /> },
    ],
    secondary: [
      { label: 'Monitoring', href: '/admin/monitoring', icon: <Activity className="w-4 h-4" /> },
      { label: 'Settings', href: '/settings', icon: <Settings className="w-4 h-4" /> },
    ],
  },
};

// ── Component ────────────────────────────────────────────────────────────────

interface DashboardShellProps {
  children: React.ReactNode;
  /** Optionally force a role (for admin pages that live outside /dashboard) */
  roleOverride?: RoleSlug;
}

export default function DashboardShell({ children, roleOverride }: DashboardShellProps) {
  const pathname = usePathname();
  const { user, logout } = useAuthStore();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  const role = roleOverride || normalizeRole(user?.role);
  const theme = getRoleTheme(role);
  const nav = ROLE_NAV[role] || ROLE_NAV.buyer;

  const isActive = (href: string) => {
    if (href === `/dashboard/${role}` && pathname === `/dashboard/${role}`) return true;
    if (href !== `/dashboard/${role}` && pathname.startsWith(href)) return true;
    return false;
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/40 z-40 lg:hidden backdrop-blur-sm"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed lg:sticky top-0 left-0 z-50 h-screen flex flex-col transition-all duration-300 bg-white border-r shadow-sm',
          collapsed ? 'w-[72px]' : 'w-64',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0',
          theme.borderColor
        )}
      >
        {/* Logo */}
        <div className={cn('flex items-center h-16 px-4 border-b', theme.borderColor)}>
          <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
            <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center shadow-sm', theme.primary)}>
              <span className="text-white font-bold text-sm">V</span>
            </div>
            {!collapsed && <span className="font-bold text-lg text-gray-900">Vestra</span>}
          </Link>
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="hidden lg:flex ml-auto p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
          >
            <ChevronLeft className={cn('w-4 h-4 transition-transform', collapsed && 'rotate-180')} />
          </button>
          <button
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden ml-auto p-1.5 rounded-lg hover:bg-gray-100 text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Role badge */}
        {!collapsed && (
          <div className="px-4 py-3">
            <div className={cn('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border', theme.badge)}>
              <span>{theme.emoji}</span>
              <span className="capitalize">{role.replace('_', ' ')}</span>
            </div>
          </div>
        )}

        {/* Primary Nav */}
        <nav className="flex-1 px-3 py-2 space-y-0.5 overflow-y-auto">
          {!collapsed && (
            <p className="px-3 py-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Main
            </p>
          )}
          {nav.items.map((item) => (
            <Link
              key={item.href + item.label}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group',
                isActive(item.href)
                  ? cn('shadow-sm', theme.sidebarActive)
                  : cn('text-gray-600 hover:text-gray-900', theme.sidebarHover)
              )}
              title={collapsed ? item.label : undefined}
            >
              <span className={cn('flex-shrink-0', isActive(item.href) ? theme.primaryText : 'text-gray-400 group-hover:text-gray-600')}>
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
              {!collapsed && item.badge && (
                <span className="ml-auto text-xs bg-red-500 text-white px-1.5 py-0.5 rounded-full">{item.badge}</span>
              )}
            </Link>
          ))}

          {/* Secondary Nav */}
          {!collapsed && (
            <p className="px-3 pt-5 pb-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
              Quick Links
            </p>
          )}
          {nav.secondary.map((item) => (
            <Link
              key={item.href + item.label}
              href={item.href}
              className={cn(
                'flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all group',
                isActive(item.href)
                  ? cn('shadow-sm', theme.sidebarActive)
                  : cn('text-gray-600 hover:text-gray-900', theme.sidebarHover)
              )}
              title={collapsed ? item.label : undefined}
            >
              <span className={cn('flex-shrink-0', isActive(item.href) ? theme.primaryText : 'text-gray-400 group-hover:text-gray-600')}>
                {item.icon}
              </span>
              {!collapsed && <span>{item.label}</span>}
            </Link>
          ))}
        </nav>

        {/* User Footer */}
        <div className={cn('border-t p-3', theme.borderColor)}>
          <div className={cn('flex items-center gap-3', collapsed && 'justify-center')}>
            <div className="w-8 h-8 bg-gray-200 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-gray-600 font-semibold text-xs">
                {user?.full_name?.[0]?.toUpperCase() || 'U'}
              </span>
            </div>
            {!collapsed && (
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-900 truncate">{user?.full_name}</p>
                <p className="text-xs text-gray-500 truncate">{user?.email}</p>
              </div>
            )}
            <button
              onClick={logout}
              className="p-1.5 rounded-lg hover:bg-red-50 text-gray-400 hover:text-red-500 transition-colors"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 min-w-0">
        {/* Top bar */}
        <header className={cn('sticky top-0 z-30 bg-white/95 backdrop-blur border-b h-16 flex items-center px-4 lg:px-6 gap-4', theme.borderColor)}>
          <button
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden p-2 rounded-lg hover:bg-gray-100 text-gray-500"
          >
            <Menu className="w-5 h-5" />
          </button>
          <div className="flex-1" />
          <Link href="/notifications" className="relative p-2 rounded-lg hover:bg-gray-100 text-gray-400">
            <Bell className="w-5 h-5" />
          </Link>
          <Link href="/messages" className="p-2 rounded-lg hover:bg-gray-100 text-gray-400">
            <MessageSquare className="w-5 h-5" />
          </Link>
        </header>

        {/* Page Content */}
        <main className="p-4 lg:p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
