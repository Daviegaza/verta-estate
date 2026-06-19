'use client';

import { useEffect, useState, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, StatCard, Badge, Spinner } from '@/components/ui/card';
import { PropertyCardSkeleton } from '@/components/property/PropertyCard';
import PropertyCard from '@/components/property/PropertyCard';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { Property, Payment } from '@/types';
import { formatCurrency, formatRelativeTime } from '@/lib/utils';
import {
  Building2, ShieldCheck, CreditCard, Plus,
  Eye, Bell, MessageSquare, TrendingUp, TrendingDown,
  ArrowRight, Sparkles, Zap, Home, Search, Star,
  BarChart3, Activity, Users, Target
} from 'lucide-react';

export default function DashboardPage() {
  return (
    <AuthGuard requireAuth>
      <DashboardContent />
    </AuthGuard>
  );
}

function DashboardSkeleton() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 animate-pulse">
        <div className="h-8 bg-gray-200 rounded-xl w-64 mb-2" />
        <div className="h-4 bg-gray-200 rounded-xl w-48 mb-8" />
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {[1,2,3,4].map(i => <div key={i} className="h-28 bg-gray-200 rounded-2xl" />)}
        </div>
        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-4">
            {[1,2,3].map(i => <div key={i} className="h-80 bg-gray-200 rounded-2xl" />)}
          </div>
          <div className="h-96 bg-gray-200 rounded-2xl" />
        </div>
      </div>
    </div>
  );
}

function DashboardContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [properties, setProperties] = useState<Property[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [greeting, setGreeting] = useState('');

  useEffect(() => {
    const hour = new Date().getHours();
    if (hour < 12) setGreeting('Good morning');
    else if (hour < 17) setGreeting('Good afternoon');
    else setGreeting('Good evening');
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [props, pays] = await Promise.all([
        api.getMyProperties().catch(() => []),
        api.getMyPayments().catch(() => []),
      ]);
      setProperties(props || []);
      setPayments(pays || []);
    } finally {
      setLoading(false);
    }
  };

  if (loading) return <DashboardSkeleton />;

  const verifiedProps = useMemo(() => properties.filter(p => p.is_verified).length, [properties]);
  const totalViews = useMemo(() => properties.reduce((sum, p) => sum + (p.views || 0), 0), [properties]);
  const totalSpent = useMemo(() => payments
    .filter(p => p.status === 'completed')
    .reduce((sum, p) => sum + p.amount, 0), [payments]);
  const activeListings = useMemo(() => properties.filter(p => p.status === 'active').length, [properties]);

  const firstName = user?.full_name?.split(' ')[0] || 'there';

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Welcome Banner */}
        <div className="relative overflow-hidden rounded-3xl bg-gradient-to-br from-gray-900 via-emerald-950 to-gray-900 p-8 mb-8 animate-fade-in">
          <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PHBhdGggZD0iTTM2IDE4YzEuNjU3IDAgMy0xLjM0MyAzLTNzLTEuMzQzLTMtMy0zLTMgMS4zNDMtMyAzIDEuMzQzIDMgMyAzem0tMjQgMGMxLjY1NyAwIDMtMS4zNDMgMy0zcy0xLjM0My0zLTMtMy0zIDEuMzQzLTMgMyAxLjM0MyAzIDMgM3oiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-50" />
          {/* Floating decorative circles */}
          <div className="absolute top-10 right-10 w-72 h-72 bg-emerald-500/10 rounded-full blur-3xl" />
          <div className="absolute -bottom-20 -left-20 w-96 h-96 bg-white/5 rounded-full blur-3xl" />
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-64 h-64 bg-emerald-400/5 rounded-full blur-3xl" />
          <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
            <div>
              <h1 className="text-3xl lg:text-4xl font-bold text-white mb-2 animate-fade-in-up">
                {greeting}, <span className="gradient-text">{firstName}</span> 👋
              </h1>
              <p className="text-emerald-100 text-lg animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                Here's how your properties are performing today
              </p>
            </div>
            <div className="flex gap-3 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              <Link href="/verify">
                <Button size="lg" className="bg-white text-gray-900 hover:bg-gray-100 gap-2 font-semibold shadow-lg">
                  <ShieldCheck className="w-4 h-4 text-emerald-600" />
                  Verify Property
                </Button>
              </Link>
              <Link href="/properties/new">
                <Button size="lg" className="bg-emerald-500 hover:bg-emerald-400 text-white gap-2 shadow-emerald-lg">
                  <Plus className="w-4 h-4" />
                  Add Listing
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8 stagger-fade-in">
          <StatCard
            label="My Properties"
            value={properties.length}
            icon={<Building2 className="w-5 h-5" />}
            color="emerald"
            subtext={activeListings > 0 ? `${activeListings} active` : undefined}
            trend={properties.length > 0 ? { value: verifiedProps, label: 'verified' } : undefined}
          />
          <StatCard
            label="Total Views"
            value={totalViews.toLocaleString()}
            icon={<Eye className="w-5 h-5" />}
            color="blue"
            trend={{ value: 12, label: 'this week', positive: true }}
          />
          <StatCard
            label="Trust Score"
            value={properties.length > 0 ? `${verifiedProps}/${properties.length}` : '—'}
            icon={<ShieldCheck className="w-5 h-5" />}
            color="purple"
            subtext={properties.length > 0 ? `${Math.round((verifiedProps / properties.length) * 100)}% verified` : 'No listings yet'}
          />
          <StatCard
            label="Total Spent"
            value={`KES ${totalSpent.toLocaleString()}`}
            icon={<CreditCard className="w-5 h-5" />}
            color="amber"
            subtext={payments.length > 0 ? `${payments.length} payments` : undefined}
          />
        </div>

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main Content — Properties */}
          <div className="lg:col-span-2">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h2 className="text-xl font-bold text-gray-900">Your Properties</h2>
                <p className="text-sm text-gray-600 mt-0.5">Manage and track your listings</p>
              </div>
              <Link href="/properties/new">
                <Button size="sm" className="gap-1.5">
                  <Plus className="w-3.5 h-3.5" />
                  New Listing
                </Button>
              </Link>
            </div>

            {properties.length === 0 ? (
              <Card className="text-center py-20 border-2 border-dashed border-gray-200 bg-white/50">
                <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4 animate-float">
                  <Building2 className="w-8 h-8 text-emerald-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">No properties yet</h3>
                <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
                  List your first property and get it verified by our AI to start attracting serious buyers.
                </p>
                <Link href="/properties/new">
                  <Button size="lg" className="gap-2">
                    <Sparkles className="w-4 h-4" />
                    Add Your First Property
                  </Button>
                </Link>
              </Card>
            ) : (
              <div className="grid sm:grid-cols-2 gap-5 stagger-fade-in">
                {properties.slice(0, 6).map(prop => (
                  <PropertyCard key={prop.id} property={prop} />
                ))}
              </div>
            )}

            {properties.length > 6 && (
              <div className="text-center mt-6">
                <Link href="/properties/my">
                  <Button variant="outline" size="lg" className="gap-2">
                    View All {properties.length} Properties
                    <ArrowRight className="w-4 h-4" />
                  </Button>
                </Link>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-5">
            {/* Quick Actions */}
            <Card className="overflow-hidden">
              <div className="bg-gradient-to-r from-emerald-50 to-transparent -mx-6 -mt-6 px-6 pt-5 pb-3 border-b border-emerald-100/50">
                <h3 className="font-bold text-gray-900 flex items-center gap-2">
                  <Zap className="w-4 h-4 text-emerald-600" />
                  Quick Actions
                </h3>
              </div>
              <div className="space-y-1.5 mt-1">
                {[
                  {
                    label: 'Verify a Property',
                    desc: 'KES 500 — AI Trust Report',
                    icon: <ShieldCheck className="w-4 h-4" />,
                    href: '/verify',
                    bg: 'bg-emerald-50 border-emerald-200 hover:bg-emerald-100',
                    iconBg: 'bg-emerald-600 text-white',
                  },
                  {
                    label: 'Browse Market',
                    desc: 'Search verified listings',
                    icon: <Search className="w-4 h-4" />,
                    href: '/market',
                    bg: 'bg-blue-50 border-blue-200 hover:bg-blue-100',
                    iconBg: 'bg-blue-600 text-white',
                  },
                  {
                    label: 'Add Listing',
                    desc: 'Sell or rent your property',
                    icon: <Plus className="w-4 h-4" />,
                    href: '/properties/new',
                    bg: 'bg-purple-50 border-purple-200 hover:bg-purple-100',
                    iconBg: 'bg-purple-600 text-white',
                  },
                  {
                    label: 'Subscription Plans',
                    desc: 'Upgrade your account',
                    icon: <Star className="w-4 h-4" />,
                    href: '/subscription',
                    bg: 'bg-amber-50 border-amber-200 hover:bg-amber-100',
                    iconBg: 'bg-amber-600 text-white',
                  },
                ].map(action => (
                  <Link key={action.label} href={action.href}>
                    <div className={`flex items-center gap-3 px-3 py-3 rounded-xl transition-all cursor-pointer group border ${action.bg}`}>
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow-md transition-all ${action.iconBg}`}>
                        {action.icon}
                      </div>
                      <div className="min-w-0 flex-1">
                        <p className="text-sm font-bold text-gray-900">{action.label}</p>
                        <p className="text-xs text-gray-600 mt-0.5">{action.desc}</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-400 group-hover:text-gray-700 group-hover:translate-x-0.5 transition-all flex-shrink-0" />
                    </div>
                  </Link>
                ))}
              </div>
            </Card>

            {/* Recent Payments */}
            <Card>
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                Recent Payments
              </h3>
              {payments.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-xl">
                  <CreditCard className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-500 font-medium">No payments yet</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {payments.slice(0, 5).map(pay => (
                    <div key={pay.id} className="flex items-center justify-between py-2.5 px-2 rounded-xl hover:bg-gray-50 transition-colors">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-gray-800 capitalize truncate">
                          {pay.purpose?.replace(/_/g, ' ') || 'Payment'}
                        </p>
                        <p className="text-xs text-gray-400">{formatRelativeTime(pay.created_at)}</p>
                      </div>
                      <div className="text-right flex-shrink-0 ml-3">
                        <p className="text-xs font-bold text-gray-900">
                          {formatCurrency(pay.amount, pay.currency)}
                        </p>
                        <Badge variant={
                          pay.status === 'completed' ? 'success' :
                          pay.status === 'failed' ? 'danger' :
                          pay.status === 'processing' ? 'warning' : 'default'
                        }>
                          {pay.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>

            {/* Trust Tip */}
            <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-600 to-emerald-800 p-6 text-white group">
              <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2 group-hover:scale-150 transition-transform duration-500" />
              <ShieldCheck className="w-10 h-10 text-emerald-200 mb-4 relative z-10" />
              <h3 className="font-bold text-lg mb-2 relative z-10">Get Verified Today</h3>
              <p className="text-emerald-100 text-sm leading-relaxed mb-5 relative z-10">
                Verified properties get <strong className="text-white">5x more views</strong> and sell <strong className="text-white">3x faster</strong>.
              </p>
              <Link href="/verify">
                <Button size="sm" className="bg-white text-emerald-700 hover:bg-emerald-50 w-full relative z-10 font-semibold">
                  Verify Now — KES 500
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
