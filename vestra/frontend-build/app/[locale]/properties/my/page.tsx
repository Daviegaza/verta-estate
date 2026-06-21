'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card, Badge, LoadingScreen } from '@/components/ui/card';
import PropertyCard from '@/components/property/PropertyCard';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { Property } from '@/types';
import { Building2, Plus, ArrowLeft, Filter, ShieldCheck } from 'lucide-react';

export default function MyPropertiesPage() {
  return (
    <AuthGuard requireAuth>
      <MyPropertiesContent />
    </AuthGuard>
  );
}

function MyPropertiesContent() {
  const router = useRouter();
  const { isAuthenticated, isHydrated } = useAuthStore();
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<'all' | 'verified' | 'unverified' | 'sale' | 'rent'>('all');

  const loadProperties = async () => {
    try {
      const props = await api.getMyProperties();
      setProperties(props || []);
    } catch {
      setProperties([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) { router.push('/auth/login'); return; }
    loadProperties();
  }, [isHydrated, isAuthenticated]);

  const filtered = properties.filter((p) => {
    switch (filter) {
      case 'verified': return p.is_verified;
      case 'unverified': return !p.is_verified;
      case 'sale': return p.listing_type === 'sale';
      case 'rent': return p.listing_type === 'rent';
      default: return true;
    }
  });

  const filters = [
    { key: 'all', label: 'All' },
    { key: 'verified', label: 'Verified' },
    { key: 'unverified', label: 'Unverified' },
    { key: 'sale', label: 'For Sale' },
    { key: 'rent', label: 'For Rent' },
  ] as const;

  if (loading) return <LoadingScreen message="Loading your properties..." />;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
              <ArrowLeft className="w-5 h-5 text-gray-600" />
            </Link>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">My Properties</h1>
              <p className="text-gray-500 text-sm">{properties.length} listing{properties.length !== 1 ? 's' : ''} total</p>
            </div>
          </div>
          <Link href="/properties/new">
            <Button leftIcon={<Plus className="w-4 h-4" />}>Add New Listing</Button>
          </Link>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 mb-6 overflow-x-auto pb-2">
          {filters.map((f) => (
            <button
              key={f.key}
              onClick={() => setFilter(f.key)}
              className={`px-4 py-1.5 rounded-full text-xs font-medium whitespace-nowrap transition-colors ${
                filter === f.key
                  ? 'bg-emerald-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-600 hover:border-gray-400'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>

        {/* Properties grid */}
        {filtered.length === 0 ? (
          <Card className="text-center py-20">
            <Building2 className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-700 mb-2">
              {properties.length === 0 ? 'No properties yet' : 'No matching properties'}
            </h3>
            <p className="text-sm text-gray-400 mb-6">
              {properties.length === 0
                ? 'List your first property to reach thousands of potential buyers and tenants.'
                : 'Try adjusting your filter to see more results.'}
            </p>
            {properties.length === 0 && (
              <Link href="/properties/new">
                <Button>List Your First Property</Button>
              </Link>
            )}
          </Card>
        ) : (
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {filtered.map((prop) => (
              <PropertyCard key={prop.id} property={prop} />
            ))}
          </div>
        )}

        {/* Tip for unverified */}
        {properties.filter((p) => !p.is_verified).length > 0 && (
          <div className="mt-8 bg-amber-50 border border-amber-200 rounded-2xl p-5 flex items-start gap-4">
            <ShieldCheck className="w-6 h-6 text-amber-600 flex-shrink-0 mt-0.5" />
            <div>
              <h3 className="font-semibold text-amber-900 mb-1">
                {properties.filter((p) => !p.is_verified).length} unverified listing{properties.filter((p) => !p.is_verified).length !== 1 ? 's' : ''}
              </h3>
              <p className="text-sm text-amber-700 mb-3">
                Verified properties get 5x more inquiries. Run an AI verification for just KES 500 per property.
              </p>
              <Link href="/verify">
                <Button size="sm" variant="outline" className="border-amber-400 text-amber-700 hover:bg-amber-100">
                  Verify a Property — KES 500
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
