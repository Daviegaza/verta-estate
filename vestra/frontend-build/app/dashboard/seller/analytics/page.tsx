'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import type { Property } from '@/types';
import { ArrowLeft, TrendingUp, Eye, Users, DollarSign, BarChart3, Award } from 'lucide-react';

export default function SellerAnalyticsPage() {
  return (
    <AuthGuard requireAuth requireRoles={['seller']}>
      <AnalyticsContent />
    </AuthGuard>
  );
}

function AnalyticsContent() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyProperties()
      .then(p => setProperties(Array.isArray(p) ? p : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const totalViews = useMemo(() => properties.reduce((s, p) => s + (p.views || 0), 0), [properties]);
  const totalInquiries = useMemo(() => properties.reduce((s, p) => s + (p.inquiries || 0), 0), [properties]);
  const verifiedCount = useMemo(() => properties.filter(p => p.is_verified).length, [properties]);
  const avgTrustScore = useMemo(() =>
    properties.length > 0
      ? Math.round(properties.reduce((s, p) => s + (p.trust_score || 0), 0) / properties.length)
      : 0,
    [properties]
  );

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/seller" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Analytics</h1>
          <p className="text-sm text-gray-500">Performance across all your listings</p>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-4">
        <Card padding="md" className="text-center">
          <Eye className="w-8 h-8 text-blue-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">{totalViews.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Total Views</p>
        </Card>
        <Card padding="md" className="text-center">
          <Users className="w-8 h-8 text-purple-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">{totalInquiries.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Total Inquiries</p>
        </Card>
        <Card padding="md" className="text-center">
          <Award className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">{verifiedCount}</p>
          <p className="text-xs text-gray-500">Verified Listings</p>
        </Card>
        <Card padding="md" className="text-center">
          <BarChart3 className="w-8 h-8 text-amber-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">{avgTrustScore}%</p>
          <p className="text-xs text-gray-500">Avg Trust Score</p>
        </Card>
      </div>

      {/* Performance table */}
      <Card padding="none">
        <div className="px-5 pt-4 pb-3">
          <h2 className="text-lg font-bold text-gray-900">Listing Performance</h2>
        </div>
        {properties.length === 0 ? (
          <div className="text-center py-12">
            <BarChart3 className="w-12 h-12 text-gray-200 mx-auto mb-3" />
            <p className="text-sm text-gray-500">No listings to analyze yet.</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs font-semibold text-gray-400 uppercase bg-gray-50/50">
                  <th className="pl-5 py-3">Property</th>
                  <th className="py-3">Price</th>
                  <th className="py-3">Views</th>
                  <th className="py-3">Inquiries</th>
                  <th className="py-3">Trust</th>
                  <th className="py-3">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {properties
                  .sort((a, b) => (b.views || 0) - (a.views || 0))
                  .map(prop => (
                    <tr key={prop.id} className="hover:bg-gray-50/50">
                      <td className="pl-5 py-3 font-medium text-gray-900 max-w-[200px] truncate">{prop.title}</td>
                      <td className="py-3 text-gray-700">KES {prop.price.toLocaleString()}</td>
                      <td className="py-3">{prop.views || 0}</td>
                      <td className="py-3">{prop.inquiries || 0}</td>
                      <td className="py-3">{prop.trust_score != null ? `${Math.round(prop.trust_score)}%` : 'N/A'}</td>
                      <td className="py-3">
                        <Badge variant={prop.status === 'active' ? 'success' : 'default'} className="text-xs capitalize">
                          {prop.status.replace(/_/g, ' ')}
                        </Badge>
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}
