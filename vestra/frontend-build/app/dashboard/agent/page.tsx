'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { Property, Payment } from '@/types';
import { formatCurrency } from '@/lib/utils';
import {
  BarChart2, TrendingUp, Users, Home, Eye, Phone,
  DollarSign, Star, Plus, ArrowRight, AlertCircle,
  Search, ShieldCheck, Activity, Building2,
} from 'lucide-react';

interface AgentStats {
  activeListings: number;
  totalViews: number;
  totalInquiries: number;
  earnings: number;
}

export default function AgentDashboardPage() {
  return (
    <AuthGuard requireAuth>
      <AgentDashboardContent />
    </AuthGuard>
  );
}

function AgentDashboardContent() {
  const { user } = useAuthStore();
  const [properties, setProperties] = useState<Property[]>([]);
  const [payments, setPayments] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [props, pays] = await Promise.all([
        api.getMyProperties().catch(() => [] as Property[]),
        api.getMyPayments().catch(() => [] as Payment[]),
      ]);
      setProperties(props || []);
      setPayments(pays || []);
    } catch {
      setError('Failed to load dashboard. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const activeListings = useMemo(() => properties.filter((p) => p.status === 'active').length, [properties]);
  const totalViews = useMemo(() => properties.reduce((sum, p) => sum + (p.views || 0), 0), [properties]);
  const totalInquiries = useMemo(() => properties.reduce((sum, p) => sum + (p.inquiries || 0), 0), [properties]);
  const earnings = useMemo(() => payments
    .filter((p) => p.status === 'completed' && (p.purpose === 'agent_badge' || p.purpose === 'subscription'))
    .reduce((sum, p) => sum + p.amount, 0), [payments]);

  const stats: AgentStats = { activeListings, totalViews, totalInquiries, earnings };

  const firstName = user?.full_name?.split(' ')[0] || 'Agent';

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-32">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-2xl mx-auto px-4 py-32 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600 mb-4">{error}</p>
          <Button onClick={loadData} variant="outline">Retry</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Agent Dashboard</h1>
            <p className="text-gray-500 mt-1">
              Welcome back, {firstName} — here&apos;s your performance overview
            </p>
          </div>
          <Link href="/properties/new">
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Add New Listing
            </Button>
          </Link>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-emerald-50 rounded-xl">
                <Building2 className="w-5 h-5 text-emerald-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Active Listings</p>
                <p className="text-2xl font-bold text-gray-900">{stats.activeListings}</p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-blue-50 rounded-xl">
                <Eye className="w-5 h-5 text-blue-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Total Views</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats.totalViews.toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-purple-50 rounded-xl">
                <Users className="w-5 h-5 text-purple-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Total Inquiries</p>
                <p className="text-2xl font-bold text-gray-900">
                  {stats.totalInquiries.toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
          <Card>
            <div className="flex items-center gap-3">
              <div className="p-2.5 bg-amber-50 rounded-xl">
                <DollarSign className="w-5 h-5 text-amber-600" />
              </div>
              <div>
                <p className="text-xs text-gray-500">Earnings</p>
                <p className="text-2xl font-bold text-gray-900">
                  KES {stats.earnings.toLocaleString()}
                </p>
              </div>
            </div>
          </Card>
        </div>

        {/* Main Grid */}
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left — My Listings */}
          <div className="lg:col-span-2 space-y-6">
            {/* My Listings */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold text-gray-900">My Listings</h2>
                  <p className="text-sm text-gray-500 mt-0.5">
                    {properties.length} property{properties.length !== 1 ? 'ies' : 'y'} total
                  </p>
                </div>
                <Link href="/properties/my">
                  <Button size="sm" variant="outline" className="gap-1.5">
                    View All <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </Link>
              </div>

              {properties.length === 0 ? (
                <Card className="text-center py-16 border-2 border-dashed border-gray-200">
                  <Building2 className="w-14 h-14 text-gray-200 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-gray-700 mb-2">No listings yet</h3>
                  <p className="text-gray-400 text-sm mb-6 max-w-sm mx-auto">
                    List your first property to start attracting buyers and tenants across Kenya.
                  </p>
                  <Link href="/properties/new">
                    <Button className="gap-2">
                      <Plus className="w-4 h-4" />
                      Add Your First Listing
                    </Button>
                  </Link>
                </Card>
              ) : (
                <div className="space-y-3">
                  {properties.slice(0, 5).map((prop) => (
                    <Card key={prop.id} className="hover:shadow-md transition-shadow" padding="sm">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <h3 className="font-semibold text-gray-900 truncate">{prop.title}</h3>
                            <Badge
                              variant={
                                prop.status === 'active' ? 'success' :
                                prop.status === 'pending_review' ? 'warning' :
                                prop.status === 'sold' || prop.status === 'rented' ? 'info' :
                                'default'
                              }
                            >
                              {prop.status.replace(/_/g, ' ')}
                            </Badge>
                          </div>
                          <div className="flex items-center gap-3 text-sm text-gray-500">
                            <span>{prop.city}</span>
                            <span className="font-medium text-gray-900">
                              KES {prop.price.toLocaleString()}
                            </span>
                          </div>
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-400">
                            <span className="flex items-center gap-1">
                              <Eye className="w-3.5 h-3.5" />
                              {prop.views || 0} views
                            </span>
                            <span className="flex items-center gap-1">
                              <Users className="w-3.5 h-3.5" />
                              {prop.inquiries || 0} inquiries
                            </span>
                            {prop.trust_score != null && (
                              <span className="flex items-center gap-1">
                                <ShieldCheck className="w-3.5 h-3.5 text-emerald-500" />
                                Trust Score: {Math.round(prop.trust_score * 100)}%
                              </span>
                            )}
                          </div>
                        </div>
                        <Link href={`/properties/edit/${prop.id}`}>
                          <Button size="sm" variant="ghost">Edit</Button>
                        </Link>
                      </div>
                    </Card>
                  ))}
                </div>
              )}

              {properties.length > 5 && (
                <div className="text-center mt-4">
                  <Link href="/properties/my">
                    <Button variant="outline" className="gap-2">
                      View All {properties.length} Listings
                      <ArrowRight className="w-4 h-4" />
                    </Button>
                  </Link>
                </div>
              )}
            </div>

            {/* Performance Chart Placeholder */}
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <BarChart2 className="w-5 h-5 text-emerald-600" />
                <h2 className="text-lg font-bold text-gray-900">Performance</h2>
              </div>
              <div className="bg-gray-50 rounded-xl p-8 text-center">
                <div className="flex items-center justify-center gap-8 mb-6">
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900">
                      {stats.totalViews.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">Total Views</p>
                  </div>
                  <div className="w-px h-10 bg-gray-200" />
                  <div className="text-center">
                    <p className="text-2xl font-bold text-gray-900">
                      {stats.totalInquiries.toLocaleString()}
                    </p>
                    <p className="text-xs text-gray-500">Total Inquiries</p>
                  </div>
                </div>
                <TrendingUp className="w-8 h-8 text-gray-300 mx-auto mb-3" />
                <p className="text-sm text-gray-500">
                  Monthly views and inquiries — analytics coming soon
                </p>
              </div>
            </Card>

            {/* Recent Inquiries Placeholder */}
            <Card>
              <div className="flex items-center gap-2 mb-4">
                <Phone className="w-5 h-5 text-emerald-600" />
                <h2 className="text-lg font-bold text-gray-900">Recent Inquiries &amp; Leads</h2>
              </div>
              <div className="text-center py-10 bg-gray-50 rounded-xl">
                <Users className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Coming soon</p>
                <p className="text-xs text-gray-400 mt-1">
                  Inquiry tracking and lead management will be available in a future update.
                </p>
              </div>
            </Card>
          </div>

          {/* Right — Sidebar */}
          <div className="space-y-5">
            {/* Quick Actions */}
            <Card className="overflow-hidden">
              <div className="bg-gradient-to-r from-emerald-50 to-transparent -mx-6 -mt-6 px-6 pt-5 pb-3 border-b border-emerald-100/50">
                <h3 className="font-bold text-gray-900 flex items-center gap-2">
                  <Activity className="w-4 h-4 text-emerald-600" />
                  Quick Actions
                </h3>
              </div>
              <div className="divide-y divide-gray-50 mt-1">
                {[
                  {
                    label: 'Add New Listing',
                    desc: 'List a property for sale or rent',
                    icon: <Plus className="w-4 h-4 text-emerald-600" />,
                    href: '/properties/new',
                    color: 'hover:bg-emerald-50/50',
                  },
                  {
                    label: 'View All Listings',
                    desc: 'Manage your properties',
                    icon: <Building2 className="w-4 h-4 text-blue-600" />,
                    href: '/properties/my',
                    color: 'hover:bg-blue-50/50',
                  },
                  {
                    label: 'Browse Properties',
                    desc: 'Search the market',
                    icon: <Search className="w-4 h-4 text-purple-600" />,
                    href: '/market',
                    color: 'hover:bg-purple-50/50',
                  },
                  {
                    label: 'Upgrade Account',
                    desc: 'Get more features',
                    icon: <Star className="w-4 h-4 text-amber-600" />,
                    href: '/subscription',
                    color: 'hover:bg-amber-50/50',
                  },
                ].map((action) => (
                  <Link key={action.label} href={action.href}>
                    <div className={`flex items-center gap-3 px-1 py-3 rounded-xl transition-all cursor-pointer group ${action.color}`}>
                      <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm group-hover:shadow transition-all">
                        {action.icon}
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 group-hover:text-emerald-700 transition-colors">{action.label}</p>
                        <p className="text-xs text-gray-400">{action.desc}</p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-300 group-hover:text-emerald-500 group-hover:translate-x-0.5 transition-all ml-auto flex-shrink-0" />
                    </div>
                  </Link>
                ))}
              </div>
            </Card>

            {/* Agent Tips */}
            <Card className="relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-100/30 rounded-full -translate-y-1/2 translate-x-1/2" />
              <div className="relative z-10">
                <ShieldCheck className="w-10 h-10 text-emerald-600 mb-4" />
                <h3 className="font-bold text-gray-900 mb-2">Boost Your Credibility</h3>
                <p className="text-sm text-gray-500 leading-relaxed mb-5">
                  Verified listings get <strong className="text-gray-900">5x more views</strong>. Get each property verified by our AI for just KES 500.
                </p>
                <Link href="/verify">
                  <Button size="sm" fullWidth variant="outline" className="border-emerald-200 hover:bg-emerald-50">
                    <ShieldCheck className="w-3.5 h-3.5" />
                    Verify a Property
                  </Button>
                </Link>
              </div>
            </Card>

            {/* Recent Earnings */}
            <Card>
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-600" />
                Recent Earnings
              </h3>
              {payments.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-xl">
                  <DollarSign className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-xs text-gray-400">No earnings yet</p>
                </div>
              ) : (
                <div className="space-y-1">
                  {payments.slice(0, 5).map((pay) => (
                    <div key={pay.id} className="flex items-center justify-between py-2.5 px-2 rounded-xl hover:bg-gray-50 transition-colors">
                      <div className="min-w-0">
                        <p className="text-xs font-semibold text-gray-800 capitalize truncate">
                          {pay.purpose?.replace(/_/g, ' ') || 'Payment'}
                        </p>
                        <p className="text-xs text-gray-400">
                          {new Date(pay.created_at).toLocaleDateString()}
                        </p>
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
          </div>
        </div>
      </div>
    </div>
  );
}
