'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import RoleBanner from '@/components/dashboard/RoleBanner';
import StatCardGrid, { type StatItem } from '@/components/dashboard/StatCardGrid';
import QuickActions, { type QuickAction } from '@/components/dashboard/QuickActions';
import ActivityFeed, { type ActivityItem } from '@/components/dashboard/ActivityFeed';
import { Card, Badge, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { Property, Payment } from '@/types';
import { formatCurrency } from '@/lib/utils';
import {
  Building2, ShieldCheck, CreditCard, Plus,
  Eye, TrendingUp, ArrowRight, Sparkles, Zap,
  Search, Star, BarChart3, Activity, Users,
  Target, DollarSign, Award
} from 'lucide-react';

export default function SellerDashboardPage() {
  return (
    <AuthGuard requireAuth requireRoles={['seller']}>
      <SellerContent />
    </AuthGuard>
  );
}

function SellerContent() {
  const { user } = useAuthStore();
  const [properties, setProperties] = useState<Property[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [props, pays] = await Promise.all([
        api.getMyProperties().catch(() => [] as Property[]),
        api.getMyPayments().catch(() => [] as Payment[]),
      ]);
      setProperties(Array.isArray(props) ? props : []);
      setPayments(Array.isArray(pays) ? pays : []);
    } finally {
      setLoading(false);
    }
  };

  const verifiedProps = useMemo(() => properties.filter(p => p.is_verified).length, [properties]);
  const totalViews = useMemo(() => properties.reduce((sum, p) => sum + (p.views || 0), 0), [properties]);
  const totalSpent = useMemo(() => payments
    .filter(p => p.status === 'completed')
    .reduce((sum, p) => sum + p.amount, 0), [payments]);
  const activeListings = useMemo(() => properties.filter(p => p.status === 'active').length, [properties]);
  const totalInquiries = useMemo(() => properties.reduce((sum, p) => sum + (p.inquiries || 0), 0), [properties]);

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  const stats: StatItem[] = [
    {
      label: 'Active Listings',
      value: activeListings,
      icon: <Building2 className="w-5 h-5" />,
      subtext: `${properties.length} total · ${verifiedProps} verified`,
      trend: activeListings > 0 ? { value: 'Live', positive: true } : undefined,
    },
    {
      label: 'Total Views',
      value: totalViews.toLocaleString(),
      icon: <Eye className="w-5 h-5" />,
      subtext: `${totalInquiries} inquiries received`,
    },
    {
      label: 'Trust Coverage',
      value: properties.length > 0 ? `${verifiedProps}/${properties.length}` : '—',
      icon: <ShieldCheck className="w-5 h-5" />,
      subtext: properties.length > 0
        ? `${Math.round((verifiedProps / properties.length) * 100)}% verified`
        : 'No listings yet',
    },
    {
      label: 'Total Spent',
      value: `KES ${totalSpent.toLocaleString()}`,
      icon: <CreditCard className="w-5 h-5" />,
      subtext: payments.length > 0 ? `${payments.length} payments` : 'No payments yet',
    },
  ];

  const actions: QuickAction[] = [
    {
      label: 'Add New Listing',
      desc: 'Sell or rent your property',
      icon: <Plus className="w-4 h-4" />,
      href: '/properties/new',
      iconBg: 'bg-emerald-600',
    },
    {
      label: 'Verify a Property',
      desc: 'KES 500 — AI Trust Report',
      icon: <ShieldCheck className="w-4 h-4" />,
      href: '/verify',
      iconBg: 'bg-teal-600',
    },
    {
      label: 'Browse Market',
      desc: 'See comparable listings',
      icon: <Search className="w-4 h-4" />,
      href: '/market',
      iconBg: 'bg-blue-600',
    },
    {
      label: 'Subscription Plans',
      desc: 'Boost your visibility',
      icon: <Star className="w-4 h-4" />,
      href: '/subscription',
      iconBg: 'bg-amber-600',
    },
  ];

  // Pipeline data
  const pipelineStages = [
    { stage: 'Listed', count: properties.length, icon: <Building2 className="w-5 h-5" />, color: 'bg-emerald-50 text-emerald-700' },
    { stage: 'Inquiries', count: totalInquiries, icon: <Users className="w-5 h-5" />, color: 'bg-blue-50 text-blue-700' },
    { stage: 'Viewings', count: Math.round(totalInquiries * 0.4), icon: <Eye className="w-5 h-5" />, color: 'bg-purple-50 text-purple-700' },
    { stage: 'Sold/Rented', count: properties.filter(p => p.status === 'sold' || p.status === 'rented').length, icon: <Award className="w-5 h-5" />, color: 'bg-amber-50 text-amber-700' },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <RoleBanner subtitle="Track your listings, manage inquiries, and close deals faster.">
        <Link href="/properties/new">
          <Button size="lg" className="bg-white text-emerald-700 hover:bg-emerald-50 gap-2 font-semibold shadow-lg">
            <Plus className="w-4 h-4" /> Add Listing
          </Button>
        </Link>
        <Link href="/verify">
          <Button size="lg" className="bg-white/10 border border-white/20 text-white hover:bg-white/20 gap-2">
            <ShieldCheck className="w-4 h-4" /> Verify Property
          </Button>
        </Link>
      </RoleBanner>

      <StatCardGrid stats={stats} columns={4} />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main */}
        <div className="lg:col-span-2 space-y-6">
          {/* Sales Pipeline */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-600" />
                Sales Pipeline
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">Listing → Inquiry → Viewing → Closed</p>
            </div>
            <div className="grid grid-cols-4 gap-3 px-5 pb-5">
              {pipelineStages.map((stage, i) => (
                <div key={stage.stage} className={`rounded-xl border p-4 text-center ${stage.color}`}>
                  <div className="flex justify-center mb-2">{stage.icon}</div>
                  <p className="text-2xl font-bold">{stage.count}</p>
                  <p className="text-xs font-medium opacity-70">{stage.stage}</p>
                  {i < pipelineStages.length - 1 && (
                    <ArrowRight className="w-4 h-4 mx-auto mt-1 opacity-30" />
                  )}
                </div>
              ))}
            </div>
          </Card>

          {/* My Listings */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-xl font-bold text-gray-900">My Listings</h2>
                <p className="text-sm text-gray-500 mt-0.5">{properties.length} property{properties.length !== 1 ? 'ies' : 'y'} · {activeListings} active</p>
              </div>
              <div className="flex gap-2">
                <Link href="/properties/my">
                  <Button size="sm" variant="outline" className="gap-1.5">
                    View All <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </Link>
                <Link href="/properties/new">
                  <Button size="sm" className="gap-1.5 bg-emerald-600 hover:bg-emerald-500">
                    <Plus className="w-3.5 h-3.5" /> New Listing
                  </Button>
                </Link>
              </div>
            </div>

            {properties.length === 0 ? (
              <Card className="text-center py-20 border-2 border-dashed border-emerald-200">
                <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                  <Building2 className="w-8 h-8 text-emerald-600" />
                </div>
                <h3 className="text-lg font-semibold text-gray-800 mb-2">No properties yet</h3>
                <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
                  List your property and get it AI-verified to attract serious buyers. Verified listings get 5x more views.
                </p>
                <Link href="/properties/new">
                  <Button size="lg" className="gap-2 bg-emerald-600 hover:bg-emerald-500">
                    <Sparkles className="w-4 h-4" /> Add Your First Property
                  </Button>
                </Link>
              </Card>
            ) : (
              <div className="grid sm:grid-cols-2 gap-4">
                {properties.slice(0, 6).map(prop => (
                  <Link key={prop.id} href={`/properties/${prop.id}`}>
                    <Card padding="md" className="hover:shadow-md hover:-translate-y-0.5 transition-all group">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-gray-900 group-hover:text-emerald-700 transition-colors text-sm truncate max-w-[180px]">
                          {prop.title}
                        </h3>
                        <Badge variant={prop.status === 'active' ? 'success' : prop.status === 'pending_review' ? 'warning' : prop.status === 'sold' ? 'info' : 'default'} className="text-xs capitalize flex-shrink-0">
                          {prop.status.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500 mb-2">{prop.city}</p>
                      <p className="font-bold text-gray-900 text-sm mb-2">{formatCurrency(prop.price, prop.currency)}</p>
                      <div className="flex items-center gap-4 text-xs text-gray-400">
                        <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{prop.views || 0} views</span>
                        <span className="flex items-center gap-1"><Users className="w-3 h-3" />{prop.inquiries || 0} inquiries</span>
                      </div>
                      {prop.is_verified && (
                        <div className="mt-2 flex items-center gap-1 text-xs text-emerald-600 font-medium">
                          <ShieldCheck className="w-3 h-3" /> Verified
                        </div>
                      )}
                    </Card>
                  </Link>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          <QuickActions actions={actions} />

          {/* Recent Payments */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-600" />
                Recent Payments
              </h2>
            </div>
            {payments.length === 0 ? (
              <div className="text-center py-8 px-4">
                <CreditCard className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                <p className="text-xs text-gray-400">No payments yet</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 px-5 pb-4">
                {payments.slice(0, 5).map(pay => (
                  <div key={pay.id} className="flex items-center justify-between py-2.5">
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-gray-800 capitalize truncate">
                        {pay.purpose?.replace(/_/g, ' ') || 'Payment'}
                      </p>
                      <p className="text-xs text-gray-400">
                        {new Date(pay.created_at).toLocaleDateString()}
                      </p>
                    </div>
                    <div className="text-right flex-shrink-0 ml-3">
                      <p className="text-xs font-bold text-gray-900">{formatCurrency(pay.amount, pay.currency)}</p>
                      <Badge variant={pay.status === 'completed' ? 'success' : pay.status === 'failed' ? 'danger' : pay.status === 'processing' ? 'warning' : 'default'} className="text-xs">
                        {pay.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Trust Tip */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-emerald-600 to-teal-700 p-6 text-white">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
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
  );
}
