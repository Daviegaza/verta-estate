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
import type { Property, Payment, Payout } from '@/types';
import { formatCurrency } from '@/lib/utils';
import {
  Building2, Users, DollarSign, TrendingUp, Eye,
  Phone, Star, Plus, ArrowRight, Shield,
  Search, Activity, Briefcase, Zap, BarChart3,
  Award, UserCheck, CreditCard, Target,
} from 'lucide-react';

export default function AgentDashboardPage() {
  return (
    <AuthGuard requireAuth requireRoles={['agent']}>
      <AgentContent />
    </AuthGuard>
  );
}

function AgentContent() {
  const { user } = useAuthStore();
  const [properties, setProperties] = useState<Property[]>([]);
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [props, pays] = await Promise.all([
        api.getMyProperties().catch(() => [] as Property[]),
        api.getMyPayouts().catch(() => ({ items: [] })),
      ]);
      setProperties(Array.isArray(props) ? props : []);
      setPayouts(Array.isArray(pays.items) ? pays.items : []);
    } catch {} finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadData(); }, []);

  const activeListings = useMemo(() => properties.filter(p => p.status === 'active').length, [properties]);
  const totalViews = useMemo(() => properties.reduce((sum, p) => sum + (p.views || 0), 0), [properties]);
  const totalInquiries = useMemo(() => properties.reduce((sum, p) => sum + (p.inquiries || 0), 0), [properties]);
  const totalEarnings = useMemo(() =>
    payouts.filter(p => p.status === 'completed').reduce((sum, p) => sum + p.amount_kes, 0),
  [payouts]);
  const pendingPayouts = useMemo(() =>
    payouts.filter(p => p.status === 'pending' || p.status === 'processing').reduce((sum, p) => sum + p.amount_kes, 0),
  [payouts]);

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  const stats: StatItem[] = [
    {
      label: 'Active Listings',
      value: activeListings,
      icon: <Building2 className="w-5 h-5" />,
      subtext: `${properties.length} total · ${properties.filter(p => p.is_verified).length} verified`,
    },
    {
      label: 'Total Views',
      value: totalViews.toLocaleString(),
      icon: <Eye className="w-5 h-5" />,
      trend: { value: 'All time', positive: true },
    },
    {
      label: 'Total Inquiries',
      value: totalInquiries.toLocaleString(),
      icon: <Users className="w-5 h-5" />,
      subtext: 'Leads generated',
    },
    {
      label: 'Earnings',
      value: `KES ${totalEarnings.toLocaleString()}`,
      icon: <DollarSign className="w-5 h-5" />,
      subtext: pendingPayouts > 0 ? `KES ${pendingPayouts.toLocaleString()} pending payout` : 'All paid out',
    },
  ];

  const actions: QuickAction[] = [
    {
      label: 'Add New Listing',
      desc: 'List a property for a client',
      icon: <Plus className="w-4 h-4" />,
      href: '/properties/new',
      iconBg: 'bg-cyan-600',
    },
    {
      label: 'View All Listings',
      desc: 'Manage your portfolio',
      icon: <Building2 className="w-4 h-4" />,
      href: '/properties/my',
      iconBg: 'bg-teal-600',
    },
    {
      label: 'Browse Market',
      desc: 'Find properties for clients',
      icon: <Search className="w-4 h-4" />,
      href: '/market',
      iconBg: 'bg-blue-600',
    },
    {
      label: 'Request Payout',
      desc: 'Withdraw your commissions',
      icon: <CreditCard className="w-4 h-4" />,
      href: '/wallet',
      iconBg: 'bg-emerald-600',
    },
  ];

  // Lead pipeline — derived from properties with inquiry counts
  const leadsData = properties
    .filter(p => (p.inquiries || 0) > 0)
    .sort((a, b) => (b.inquiries || 0) - (a.inquiries || 0));
  const totalLeads = properties.reduce((sum, p) => sum + (p.inquiries || 0), 0);

  return (
    <div className="space-y-6 animate-fade-in">
      <RoleBanner subtitle="Manage your listings, track leads, and grow your real estate business.">
        <Link href="/properties/new">
          <Button size="lg" className="bg-white text-cyan-700 hover:bg-cyan-50 gap-2 font-semibold shadow-lg">
            <Plus className="w-4 h-4" /> Add Listing
          </Button>
        </Link>
      </RoleBanner>

      <StatCardGrid stats={stats} columns={4} />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main */}
        <div className="lg:col-span-2 space-y-6">
          {/* Lead Pipeline */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <UserCheck className="w-5 h-5 text-cyan-600" />
                Lead Pipeline
              </h2>
              <p className="text-xs text-gray-500 mt-0.5">
                {totalLeads} total inquiries across {leadsData.length} listings
              </p>
            </div>

            {/* Pipeline stages */}
            <div className="grid grid-cols-4 gap-2 px-5 pb-4 mb-4">
              {[
                { stage: 'New', count: totalLeads, icon: <Users className="w-4 h-4" />, color: 'bg-blue-50 text-blue-700 border-blue-200' },
                { stage: 'Contacted', count: Math.round(totalLeads * 0.6), icon: <Phone className="w-4 h-4" />, color: 'bg-amber-50 text-amber-700 border-amber-200' },
                { stage: 'Viewing', count: Math.round(totalLeads * 0.3), icon: <Eye className="w-4 h-4" />, color: 'bg-purple-50 text-purple-700 border-purple-200' },
                { stage: 'Closed', count: Math.round(totalLeads * 0.1), icon: <Award className="w-4 h-4" />, color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
              ].map(stage => (
                <div key={stage.stage} className={`text-center rounded-xl border p-3 ${stage.color}`}>
                  <div className="flex justify-center mb-1">{stage.icon}</div>
                  <p className="text-lg font-bold">{stage.count}</p>
                  <p className="text-xs font-medium opacity-70">{stage.stage}</p>
                </div>
              ))}
            </div>

            {leadsData.length === 0 ? (
              <div className="text-center py-12 px-4">
                <Users className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">No leads yet. Add listings to start attracting buyers.</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {leadsData.slice(0, 5).map(prop => (
                  <div key={prop.id} className="flex items-center justify-between px-5 py-3 hover:bg-cyan-50/30 transition-colors">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900 truncate">{prop.title}</p>
                        <Badge variant={prop.status === 'active' ? 'success' : 'default'} className="text-xs capitalize">
                          {prop.status.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500">{prop.city} · {formatCurrency(prop.price, prop.currency)}</p>
                    </div>
                    <div className="flex items-center gap-4 text-xs text-gray-500 flex-shrink-0 ml-4">
                      <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{prop.views || 0}</span>
                      <span className="flex items-center gap-1 font-semibold text-cyan-600"><Users className="w-3 h-3" />{prop.inquiries || 0} leads</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>

          {/* Performance Overview */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-cyan-600" />
                Performance Overview
              </h2>
            </div>
            <div className="px-5 pb-5 grid sm:grid-cols-3 gap-4">
              <div className="bg-cyan-50 rounded-xl p-4 text-center">
                <Building2 className="w-6 h-6 text-cyan-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{properties.length}</p>
                <p className="text-xs text-gray-500">Total Listings</p>
              </div>
              <div className="bg-teal-50 rounded-xl p-4 text-center">
                <Shield className="w-6 h-6 text-teal-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">{properties.filter(p => p.is_verified).length}</p>
                <p className="text-xs text-gray-500">Verified</p>
              </div>
              <div className="bg-emerald-50 rounded-xl p-4 text-center">
                <Star className="w-6 h-6 text-emerald-600 mx-auto mb-2" />
                <p className="text-2xl font-bold text-gray-900">
                  {properties.length > 0
                    ? Math.round(properties.reduce((sum, p) => sum + (p.trust_score || 0), 0) / properties.length)
                    : '—'}%
                </p>
                <p className="text-xs text-gray-500">Avg Trust Score</p>
              </div>
            </div>
          </Card>

          {/* My Listings Quick View */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Building2 className="w-5 h-5 text-cyan-600" />
                My Listings
              </h2>
              <Link href="/properties/my">
                <Button size="sm" variant="ghost" className="gap-1.5 text-cyan-600">
                  View All <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            </div>
            {properties.length === 0 ? (
              <div className="text-center py-12 px-4">
                <Building2 className="w-14 h-14 text-gray-200 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">No listings yet</h3>
                <p className="text-gray-500 text-sm mb-6">List your first property to start attracting buyers.</p>
                <Link href="/properties/new">
                  <Button className="gap-2 bg-cyan-600 hover:bg-cyan-500">
                    <Plus className="w-4 h-4" /> Add Your First Listing
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-gray-50">
                {properties.slice(0, 5).map(prop => (
                  <div key={prop.id} className="flex items-center justify-between px-5 py-3 hover:bg-cyan-50/30 transition-colors">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-semibold text-gray-900 truncate max-w-[200px]">{prop.title}</p>
                        <Badge variant={prop.status === 'active' ? 'success' : prop.status === 'pending_review' ? 'warning' : 'default'} className="text-xs capitalize">
                          {prop.status.replace(/_/g, ' ')}
                        </Badge>
                      </div>
                      <p className="text-xs text-gray-500">{prop.city} · {formatCurrency(prop.price, prop.currency)}</p>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-400">
                      <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{prop.views || 0}</span>
                      <span className="flex items-center gap-1"><Users className="w-3 h-3" />{prop.inquiries || 0}</span>
                      <Link href={`/properties/edit/${prop.id}`}>
                        <Button size="sm" variant="ghost" className="text-xs">Edit</Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          <QuickActions actions={actions} />

          {/* Earnings Summary */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-cyan-600" />
                Earnings Summary
              </h2>
            </div>
            <div className="px-5 pb-4 space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Total Earned</span>
                <span className="font-bold text-gray-900">KES {totalEarnings.toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-500">Pending Payout</span>
                <span className="font-bold text-amber-600">KES {pendingPayouts.toLocaleString()}</span>
              </div>
              <Link href="/wallet">
                <Button size="sm" variant="outline" className="w-full mt-2 border-cyan-200 text-cyan-700 hover:bg-cyan-50">
                  <CreditCard className="w-3.5 h-3.5" /> Request Payout
                </Button>
              </Link>
            </div>
          </Card>

          {/* Pro Tip */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-cyan-600 to-teal-700 p-6 text-white">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <Award className="w-10 h-10 text-cyan-200 mb-4 relative z-10" />
            <h3 className="font-bold text-lg mb-2 relative z-10">Boost Your Listings</h3>
            <p className="text-cyan-100 text-sm leading-relaxed mb-5 relative z-10">
              Verified listings get <strong className="text-white">5x more views</strong>. Verify each property for just KES 500.
            </p>
            <Link href="/verify">
              <Button size="sm" className="bg-white text-cyan-700 hover:bg-cyan-50 w-full relative z-10 font-semibold">
                <Shield className="w-3.5 h-3.5" /> Verify Listing
              </Button>
            </Link>
          </div>

          {/* Recent Payouts Activity */}
          {payouts.length > 0 && (
            <ActivityFeed
              items={payouts.slice(0, 5).map(p => ({
                id: p.id,
                title: `Payout — KES ${p.amount_kes.toLocaleString()}`,
                description: p.payout_type || 'Commission',
                timestamp: p.created_at,
                type: p.status === 'completed' ? 'success' as const :
                      p.status === 'failed' ? 'danger' as const : 'warning' as const,
              }))}
              title="Recent Payouts"
              emptyMessage="No payouts yet"
            />
          )}
        </div>
      </div>
    </div>
  );
}
