'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import RoleBanner from '@/components/dashboard/RoleBanner';
import StatCardGrid, { type StatItem } from '@/components/dashboard/StatCardGrid';
import QuickActions, { type QuickAction } from '@/components/dashboard/QuickActions';
import ActivityFeed, { type ActivityItem } from '@/components/dashboard/ActivityFeed';
import { Card, Badge, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import { useRecentlyViewed } from '@/hooks/useRecentlyViewed';
import api from '@/lib/api';
import type { Property, EscrowTransaction } from '@/types';
import { formatCurrency } from '@/lib/utils';
import {
  Search, Heart, Shield, TrendingUp, Eye,
  DollarSign, Clock, MapPin, ArrowRight, Plus,
  Building2, Star, Bell, AlertCircle, Zap,
  Home, CreditCard, BarChart3,
} from 'lucide-react';

export default function BuyerDashboardPage() {
  return (
    <AuthGuard requireAuth requireRoles={['buyer']}>
      <BuyerContent />
    </AuthGuard>
  );
}

function BuyerContent() {
  const { user } = useAuthStore();
  const { items: recentViews } = useRecentlyViewed();
  const [savedProperties, setSavedProperties] = useState<Property[]>([]);
  const [escrows, setEscrows] = useState<EscrowTransaction[]>([]);
  const [recommendations, setRecommendations] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [savedResp, escrowResp, marketResp] = await Promise.all([
        api.client.get('/api/favorites/my').catch(() => ({ data: [] })),
        api.getMyEscrows().catch(() => ({ items: [] })),
        api.listProperties({ verified_only: true, size: 6 }).catch(() => ({ items: [] })),
      ]);
      setSavedProperties(Array.isArray(savedResp.data) ? savedResp.data : []);
      setEscrows(Array.isArray(escrowResp.items) ? escrowResp.items : []);
      setRecommendations(marketResp.items || []);
    } catch {} finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  const activeEscrows = escrows.filter(e => !['completed', 'cancelled', 'refunded'].includes(e.status));
  const completedEscrows = escrows.filter(e => e.status === 'completed');

  const stats: StatItem[] = [
    {
      label: 'Saved Properties',
      value: savedProperties.length,
      icon: <Heart className="w-5 h-5" />,
      subtext: savedProperties.length > 0 ? 'Your favorites' : 'Save properties you like',
    },
    {
      label: 'Active Escrows',
      value: activeEscrows.length,
      icon: <Shield className="w-5 h-5" />,
      subtext: activeEscrows.length > 0 ? 'Protected transactions' : 'Start with confidence',
    },
    {
      label: 'Recently Viewed',
      value: recentViews.length,
      icon: <Eye className="w-5 h-5" />,
      subtext: 'Properties you checked',
    },
    {
      label: 'Completed Deals',
      value: completedEscrows.length,
      icon: <TrendingUp className="w-5 h-5" />,
      subtext: completedEscrows.length > 0 ? 'Successfully closed' : 'Your future home awaits',
    },
  ];

  const actions: QuickAction[] = [
    {
      label: 'Browse Properties',
      desc: 'Search verified listings',
      icon: <Search className="w-4 h-4" />,
      href: '/market',
      iconBg: 'bg-blue-600',
    },
    {
      label: 'AI Search',
      desc: 'Natural language property search',
      icon: <Zap className="w-4 h-4" />,
      href: '/market?ai=1',
      iconBg: 'bg-indigo-600',
    },
    {
      label: 'Verify a Property',
      desc: 'Get AI trust report — KES 500',
      icon: <Shield className="w-4 h-4" />,
      href: '/verify',
      iconBg: 'bg-emerald-600',
    },
    {
      label: 'Saved Searches',
      desc: 'Your search alerts',
      icon: <Bell className="w-4 h-4" />,
      href: '/market',
      iconBg: 'bg-amber-600',
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <RoleBanner subtitle="Find your perfect property with AI-powered search and verified listings.">
        <Link href="/market">
          <Button size="lg" className="bg-white text-blue-700 hover:bg-blue-50 gap-2 font-semibold shadow-lg">
            <Search className="w-4 h-4" /> Browse Properties
          </Button>
        </Link>
      </RoleBanner>

      <StatCardGrid stats={stats} columns={4} />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* Main — Recommendations + Saved */}
        <div className="lg:col-span-2 space-y-6">
          {/* AI Recommendations */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Star className="w-5 h-5 text-blue-600" />
                Recommended for You
              </h2>
              <Link href="/market">
                <Button size="sm" variant="ghost" className="gap-1.5 text-blue-600">
                  View All <ArrowRight className="w-3.5 h-3.5" />
                </Button>
              </Link>
            </div>
            {recommendations.length === 0 ? (
              <div className="text-center py-12 px-4">
                <Building2 className="w-14 h-14 text-gray-200 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-700 mb-2">Discover Verified Properties</h3>
                <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
                  Browse our marketplace of AI-verified properties across Kenya.
                </p>
                <Link href="/market">
                  <Button className="gap-2 bg-blue-600 hover:bg-blue-500">
                    <Search className="w-4 h-4" /> Start Browsing
                  </Button>
                </Link>
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 gap-3 px-5 pb-5">
                {recommendations.slice(0, 6).map(prop => (
                  <Link key={prop.id} href={`/properties/${prop.id}`}>
                    <div className="border border-gray-100 rounded-xl p-4 hover:shadow-md hover:border-blue-200 transition-all group">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 transition-colors text-sm truncate max-w-[180px]">
                          {prop.title}
                        </h3>
                        {prop.trust_score != null && (
                          <Badge variant={prop.trust_score >= 75 ? 'success' : 'warning'} className="text-xs flex-shrink-0">
                            {Math.round(prop.trust_score)}%
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                        <MapPin className="w-3 h-3" />
                        <span>{prop.city}</span>
                      </div>
                      <p className="font-bold text-gray-900">{formatCurrency(prop.price, prop.currency)}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                        {prop.bedrooms != null && <span>{prop.bedrooms}br</span>}
                        {prop.bathrooms != null && <span>{prop.bathrooms}ba</span>}
                        {prop.size_sqft != null && <span>{prop.size_sqft.toLocaleString()} sqft</span>}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          {/* Saved Properties */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Heart className="w-5 h-5 text-red-500" />
                Saved Properties
              </h2>
              {savedProperties.length > 0 && (
                <Link href="/dashboard/buyer/favorites">
                  <Button size="sm" variant="ghost" className="gap-1.5 text-blue-600">
                    View All <ArrowRight className="w-3.5 h-3.5" />
                  </Button>
                </Link>
              )}
            </div>
            {savedProperties.length === 0 ? (
              <div className="text-center py-12 px-4">
                <Heart className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                <p className="text-gray-500 text-sm">Save properties by clicking the heart icon while browsing.</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 px-5 pb-4">
                {savedProperties.slice(0, 5).map(prop => (
                  <Link key={prop.id} href={`/properties/${prop.id}`}>
                    <div className="flex items-center justify-between py-3 hover:bg-blue-50/30 px-2 rounded-lg -mx-2 transition-colors">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-900 truncate">{prop.title}</p>
                        <p className="text-xs text-gray-500">{prop.city} · {prop.property_type}</p>
                      </div>
                      <div className="text-right flex-shrink-0 ml-3">
                        <p className="text-sm font-bold text-gray-900">{formatCurrency(prop.price, prop.currency)}</p>
                        {prop.is_verified && <Badge variant="success" className="text-xs">Verified</Badge>}
                      </div>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Card>

          {/* Active Escrows */}
          {activeEscrows.length > 0 && (
            <Card padding="none">
              <div className="px-5 pt-4 pb-3">
                <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                  <Shield className="w-5 h-5 text-blue-600" />
                  Active Escrows
                </h2>
              </div>
              <div className="divide-y divide-gray-50 px-5 pb-4">
                {activeEscrows.map(escrow => (
                  <div key={escrow.id} className="flex items-center justify-between py-3">
                    <div>
                      <p className="text-sm font-semibold text-gray-900">Property #{escrow.property_id}</p>
                      <p className="text-xs text-gray-500">KES {escrow.amount_kes?.toLocaleString()}</p>
                    </div>
                    <Badge variant={escrow.status === 'deposit_paid' ? 'info' : 'warning'}>
                      {escrow.status.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          <QuickActions actions={actions} />

          {/* Market Insight Card */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 p-6 text-white">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <BarChart3 className="w-10 h-10 text-blue-200 mb-4 relative z-10" />
            <h3 className="font-bold text-lg mb-2 relative z-10">Market Insights</h3>
            <p className="text-blue-100 text-sm leading-relaxed mb-5 relative z-10">
              Get AI-powered price trends, neighborhood analysis, and investment recommendations.
            </p>
            <Link href="/market?ai=1">
              <Button size="sm" className="bg-white text-blue-700 hover:bg-blue-50 w-full relative z-10 font-semibold">
                <Zap className="w-3.5 h-3.5" /> Explore Market
              </Button>
            </Link>
          </div>

          {/* Recently Viewed */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h2 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <Eye className="w-4 h-4 text-blue-600" />
                Recently Viewed
              </h2>
            </div>
            {recentViews.length === 0 ? (
              <div className="text-center py-8">
                <Clock className="w-8 h-8 text-gray-200 mx-auto mb-2" />
                <p className="text-xs text-gray-400">Start browsing properties</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-50 px-5 pb-4">
                {recentViews.slice(0, 5).map(item => (
                  <Link key={item.id} href={`/properties/${item.id}`}>
                    <div className="flex items-center justify-between py-2.5 hover:bg-gray-50 px-2 rounded-lg -mx-2 transition-colors">
                      <div>
                        <p className="text-xs font-medium text-gray-900 truncate max-w-[180px]">{item.title}</p>
                        <p className="text-xs text-gray-400">{item.city}</p>
                      </div>
                      <span className="text-xs font-semibold text-gray-900">
                        KES {item.price.toLocaleString()}
                      </span>
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
