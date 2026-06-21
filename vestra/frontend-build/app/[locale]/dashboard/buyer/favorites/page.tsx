'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import type { Property } from '@/types';
import { formatCurrency } from '@/lib/utils';
import { Heart, ArrowLeft, MapPin, Eye, Shield, Trash2 } from 'lucide-react';

export default function FavoritesPage() {
  return (
    <AuthGuard requireAuth requireRoles={['buyer']}>
      <FavoritesContent />
    </AuthGuard>
  );
}

function FavoritesContent() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.client.get('/api/favorites/my')
      .then(r => setProperties(Array.isArray(r.data) ? r.data : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/buyer" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Saved Properties</h1>
          <p className="text-sm text-gray-500">{properties.length} saved</p>
        </div>
      </div>

      {properties.length === 0 ? (
        <Card className="text-center py-20">
          <Heart className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No saved properties</h2>
          <p className="text-gray-500 text-sm mb-6">Browse the market and save properties you like.</p>
          <Link href="/market"><Button className="bg-blue-600 hover:bg-blue-500">Browse Properties</Button></Link>
        </Card>
      ) : (
        <div className="grid sm:grid-cols-2 gap-4">
          {properties.map(prop => (
            <Link key={prop.id} href={`/properties/${prop.id}`}>
              <Card padding="md" className="hover:shadow-md transition-all group">
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 group-hover:text-blue-700 text-sm truncate max-w-[200px]">{prop.title}</h3>
                  {prop.is_verified && <Shield className="w-4 h-4 text-emerald-500 flex-shrink-0" />}
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500 mb-2">
                  <MapPin className="w-3 h-3" /><span>{prop.city}</span>
                </div>
                <p className="font-bold text-gray-900">{formatCurrency(prop.price, prop.currency)}</p>
                <div className="flex items-center gap-3 mt-2 text-xs text-gray-400">
                  {prop.bedrooms != null && <span>{prop.bedrooms}br</span>}
                  {prop.bathrooms != null && <span>{prop.bathrooms}ba</span>}
                  <span className="flex items-center gap-1"><Eye className="w-3 h-3" />{prop.views || 0}</span>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
