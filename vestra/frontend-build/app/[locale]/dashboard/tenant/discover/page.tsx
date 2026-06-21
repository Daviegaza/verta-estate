'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { formatCurrency } from '@/lib/utils';
import {
  Search, MapPin, Building2, Home, Heart, Star, Shield,
  ArrowLeft, Zap, Filter, SlidersHorizontal, BedDouble,
  Bath, Ruler, Phone, MessageSquare, Eye, DollarSign,
  Wifi, Car, Dumbbell, ShieldCheck,
} from 'lucide-react';

const PROPERTY_TYPES = ['All', 'bedsitter', 'studio', '1br', '2br', '3br', 'penthouse', 'house'];
const CITIES = ['All', 'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', 'Thika', 'Kiambu'];

export default function TenantDiscoverPage() {
  return (
    <AuthGuard requireAuth requireRoles={['tenant']}>
      <DiscoverContent />
    </AuthGuard>
  );
}

function DiscoverContent() {
  const [properties, setProperties] = useState<any[]>([]);
  const [saved, setSaved] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [city, setCity] = useState('All');
  const [propType, setPropType] = useState('All');
  const [minPrice, setMinPrice] = useState('');
  const [maxPrice, setMaxPrice] = useState('');
  const [bedrooms, setBedrooms] = useState('');

  useEffect(() => { loadProperties(); }, [city, propType]);

  const loadProperties = async () => {
    setLoading(true);
    try {
      const params: any = { listing_type: 'rent', size: 24 };
      if (city !== 'All') params.city = city;
      if (propType !== 'All') params.property_type = propType;
      if (minPrice) params.min_price = Number(minPrice);
      if (maxPrice) params.max_price = Number(maxPrice);
      if (bedrooms) params.bedrooms = Number(bedrooms);

      const res = await api.listProperties(params);
      setProperties(res.items || []);
    } catch {} finally {
      setLoading(false);
    }
  };

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (search.trim()) {
      api.aiSearch(search).then(r => {
        setProperties(r.items || []);
      }).catch(() => {});
    } else {
      loadProperties();
    }
  };

  const toggleSave = (id: number) => {
    const next = new Set(saved);
    if (next.has(id)) {
      next.delete(id);
      api.client.delete(`/api/favorites/${id}`).catch(() => {});
    } else {
      next.add(id);
      api.client.post(`/api/favorites/${id}`).catch(() => {});
    }
    setSaved(next);
  };

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3 mb-2">
        <Link href="/dashboard/tenant" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Find Your Next Home</h1>
          <p className="text-sm text-gray-500">Browse verified rental listings across Kenya</p>
        </div>
      </div>

      {/* Search & Filters */}
      <Card padding="md" className="bg-gradient-to-r from-orange-50 to-amber-50 border-orange-100">
        <form onSubmit={handleSearch} className="flex gap-3 mb-4">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Try: 2 bedroom apartment in Westlands under 50k..."
              className="w-full pl-9 pr-4 py-3 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-orange-500 focus:border-transparent bg-white"
            />
          </div>
          <Button type="submit" className="gap-2 bg-orange-600 hover:bg-orange-500">
            <Search className="w-4 h-4" /> Search
          </Button>
        </form>

        <div className="flex flex-wrap gap-3 items-center">
          {/* City filter */}
          <div className="flex gap-1 bg-white rounded-xl p-1 border border-gray-200">
            {CITIES.slice(0, 5).map(c => (
              <button
                key={c}
                onClick={() => setCity(c)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                  city === c ? 'bg-orange-600 text-white shadow' : 'text-gray-600 hover:bg-gray-100'
                }`}
              >
                {c}
              </button>
            ))}
          </div>

          {/* Property type */}
          <select
            value={propType}
            onChange={e => setPropType(e.target.value)}
            className="px-3 py-2 rounded-xl border border-gray-200 text-sm bg-white"
          >
            {PROPERTY_TYPES.map(t => (
              <option key={t} value={t}>{t === 'All' ? 'All Types' : t.charAt(0).toUpperCase() + t.slice(1)}</option>
            ))}
          </select>

          {/* Price range */}
          <input
            type="number"
            placeholder="Min KES"
            value={minPrice}
            onChange={e => setMinPrice(e.target.value)}
            className="w-28 px-3 py-2 rounded-xl border border-gray-200 text-sm"
          />
          <span className="text-gray-400">—</span>
          <input
            type="number"
            placeholder="Max KES"
            value={maxPrice}
            onChange={e => setMaxPrice(e.target.value)}
            className="w-28 px-3 py-2 rounded-xl border border-gray-200 text-sm"
          />

          <Button onClick={loadProperties} variant="outline" size="sm" className="gap-1.5">
            <Filter className="w-3.5 h-3.5" /> Apply
          </Button>
        </div>
      </Card>

      {/* Results */}
      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : properties.length === 0 ? (
        <Card className="text-center py-20">
          <Search className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-xl font-bold text-gray-700 mb-2">No rentals found</h2>
          <p className="text-gray-500 mb-6">Try adjusting your filters or search terms.</p>
          <Button onClick={() => { setCity('All'); setPropType('All'); setSearch(''); loadProperties(); }} variant="outline">
            Clear Filters
          </Button>
        </Card>
      ) : (
        <>
          <p className="text-sm text-gray-500">{properties.length} rental{properties.length !== 1 ? 's' : ''} found</p>
          <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {properties.map(prop => (
              <Card key={prop.id} padding="none" className="hover:shadow-lg hover:-translate-y-0.5 transition-all group overflow-hidden">
                {/* Image placeholder */}
                <div className="h-40 bg-gradient-to-br from-orange-100 to-amber-100 relative flex items-center justify-center">
                  <Home className="w-12 h-12 text-orange-300" />
                  <button
                    onClick={() => toggleSave(prop.id)}
                    className="absolute top-3 right-3 p-2 bg-white/90 rounded-xl hover:bg-white transition-colors shadow-sm"
                  >
                    <Heart className={`w-4 h-4 ${saved.has(prop.id) ? 'text-red-500 fill-red-500' : 'text-gray-400'}`} />
                  </button>
                  {prop.is_verified && (
                    <div className="absolute top-3 left-3 bg-emerald-500 text-white text-xs px-2 py-0.5 rounded-full flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" /> Verified
                    </div>
                  )}
                  {prop.property_type && (
                    <div className="absolute bottom-3 left-3 bg-black/60 text-white text-xs px-2 py-0.5 rounded-full capitalize">
                      {prop.property_type.replace('_', ' ')}
                    </div>
                  )}
                </div>

                <div className="p-4">
                  <div className="flex items-start justify-between mb-1">
                    <h3 className="font-semibold text-gray-900 group-hover:text-orange-700 transition-colors truncate max-w-[180px]">
                      {prop.title}
                    </h3>
                    {prop.trust_score != null && (
                      <span className={`text-xs font-bold flex-shrink-0 ml-2 ${
                        prop.trust_score >= 75 ? 'text-emerald-600' : 'text-amber-600'
                      }`}>
                        {Math.round(prop.trust_score)}%
                      </span>
                    )}
                  </div>

                  <div className="flex items-center gap-1 text-xs text-gray-500 mb-2">
                    <MapPin className="w-3 h-3" />
                    <span>{prop.city}{prop.county ? `, ${prop.county}` : ''}</span>
                  </div>

                  <p className="text-lg font-bold text-orange-600 mb-3">
                    {formatCurrency(prop.price, prop.currency)}<span className="text-xs text-gray-400 font-normal">/mo</span>
                  </p>

                  <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
                    {prop.bedrooms != null && <span className="flex items-center gap-1"><BedDouble className="w-3 h-3" />{prop.bedrooms}br</span>}
                    {prop.bathrooms != null && <span className="flex items-center gap-1"><Bath className="w-3 h-3" />{prop.bathrooms}ba</span>}
                    {prop.size_sqft != null && <span className="flex items-center gap-1"><Ruler className="w-3 h-3" />{prop.size_sqft}sqft</span>}
                  </div>

                  <div className="flex gap-2">
                    <Link href={`/properties/${prop.id}`} className="flex-1">
                      <Button size="sm" variant="outline" className="w-full text-xs border-orange-200 text-orange-700 hover:bg-orange-50">
                        <Eye className="w-3 h-3" /> View
                      </Button>
                    </Link>
                    <Link href={`/messages?user=${prop.owner_id}`} className="flex-1">
                      <Button size="sm" className="w-full text-xs bg-orange-600 hover:bg-orange-500 gap-1">
                        <MessageSquare className="w-3 h-3" /> Contact
                      </Button>
                    </Link>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
