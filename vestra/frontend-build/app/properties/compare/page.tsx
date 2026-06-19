'use client';

import { useState, useEffect, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Spinner, Badge } from '@/components/ui/card';
import api from '@/lib/api';
import type { Property } from '@/types';
import {
  formatCurrency, getListingTypeLabel, getPropertyTypeLabel,
  getTrustScoreColor
} from '@/lib/utils';
import {
  X, MapPin, BedDouble, Bath, Maximize, ShieldCheck,
  ChevronRight, Search, Home, BarChart3, CheckCircle2
} from 'lucide-react';

const MAX_COMPARE = 3;

function CompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idsParam = searchParams.get('ids');

  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [inputValue, setInputValue] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (idsParam) {
      const ids = idsParam.split(',').map(Number).filter((n) => !isNaN(n) && n > 0);
      if (ids.length > 0) {
        loadProperties(ids);
      } else {
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadProperties = async (ids: number[]) => {
    setLoading(true);
    setError('');
    try {
      const slice = ids.slice(0, MAX_COMPARE);
      const results = await Promise.allSettled(
        slice.map((id) => api.getProperty(id))
      );
      const valid: Property[] = [];
      results.forEach((r) => {
        if (r.status === 'fulfilled') valid.push(r.value);
      });
      if (valid.length === 0) {
        setError('No properties found with those IDs. Please check and try again.');
      }
      setProperties(valid);
    } catch {
      setError('Failed to load properties. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSearchIds = () => {
    const ids = inputValue
      .split(/[,;\s]+/)
      .map((s) => parseInt(s.trim()))
      .filter((n) => !isNaN(n) && n > 0);
    if (ids.length === 0) {
      setError('Please enter valid property IDs.');
      return;
    }
    const newIds = [...new Set(ids)].slice(0, MAX_COMPARE);
    router.push(`/properties/compare?ids=${newIds.join(',')}`);
  };

  const removeProperty = (id: number) => {
    const remaining = properties.filter((p) => p.id !== id);
    setProperties(remaining);
    if (remaining.length > 0) {
      const newIds = remaining.map((p) => p.id).join(',');
      router.replace(`/properties/compare?ids=${newIds}`, { scroll: false });
    } else {
      router.replace('/properties/compare', { scroll: false });
    }
  };

  const addMore = () => {
    const currentIds = properties.map((p) => p.id);
    const parsed = inputValue
      .split(/[,;\s]+/)
      .map((s) => parseInt(s.trim()))
      .filter((n) => !isNaN(n) && n > 0 && !currentIds.includes(n));
    if (parsed.length === 0) {
      setError('Enter valid Property IDs not already in the comparison.');
      return;
    }
    const allIds = [...currentIds, ...parsed].slice(0, MAX_COMPARE);
    router.push(`/properties/compare?ids=${allIds.join(',')}`);
  };

  // ── Render ──────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-2 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-700">Home</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <Link href="/market" className="hover:text-gray-700">Properties</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="text-gray-900 font-medium">Compare Properties</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BarChart3 className="w-6 h-6 text-emerald-600" />
            Compare Properties
          </h1>
          <p className="text-sm text-gray-500 mt-1">
            Compare up to {MAX_COMPARE} properties side-by-side to make an informed decision.
          </p>
        </div>

        {/* ID Input */}
        {properties.length < MAX_COMPARE && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-5 mb-6">
            <div className="flex items-center gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => { setInputValue(e.target.value); setError(''); }}
                  onKeyDown={(e) => { if (e.key === 'Enter') { properties.length > 0 ? addMore() : handleSearchIds(); } }}
                  placeholder="Enter Property IDs (e.g. 1, 2, 3)"
                  className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
                />
              </div>
              <Button
                onClick={properties.length > 0 ? addMore : handleSearchIds}
                leftIcon={<Search className="w-4 h-4" />}
              >
                {properties.length > 0 ? 'Add More' : 'Compare'}
              </Button>
            </div>
            {error && <p className="text-xs text-red-500 mt-2">{error}</p>}
            <p className="text-xs text-gray-400 mt-2">
              {properties.length > 0
                ? `Add up to ${MAX_COMPARE - properties.length} more property ID(s)`
                : 'Enter one or more property IDs separated by commas'}
            </p>
          </div>
        )}

        {/* Loading */}
        {loading ? (
          <div className="flex justify-center items-center py-32">
            <Spinner size="lg" />
          </div>
        ) : properties.length === 0 && !error ? (
          /* Empty state —— no properties selected */
          <div className="text-center py-20">
            <BarChart3 className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No Properties to Compare</h3>
            <p className="text-gray-400 mb-6">
              Enter property IDs above or add properties from the market page to start comparing.
            </p>
            <Link href="/market">
              <Button>Browse Properties</Button>
            </Link>
          </div>
        ) : error && properties.length === 0 ? (
          /* Error state */
          <div className="text-center py-20">
            <Home className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">Could Not Load Properties</h3>
            <p className="text-gray-400 mb-2">{error}</p>
            <Button variant="outline" onClick={() => { setError(''); setInputValue(''); }} className="mt-4">
              Try Again
            </Button>
          </div>
        ) : (
          /* Comparison Table */
          <div className="overflow-x-auto">
            <div
              className="grid gap-4 min-w-[600px]"
              style={{ gridTemplateColumns: `200px repeat(${properties.length}, 1fr)` }}
            >
              {/* Headers row */}
              <div className="sticky left-0 bg-gray-50 rounded-xl p-4 flex items-end">
                <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Property</span>
              </div>
              {properties.map((prop) => (
                <div key={prop.id} className="bg-white rounded-2xl border border-gray-100 overflow-hidden shadow-sm group relative">
                  {/* Remove button */}
                  <button
                    onClick={() => removeProperty(prop.id)}
                    className="absolute top-2 right-2 w-7 h-7 bg-white/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-sm opacity-0 group-hover:opacity-100 transition-opacity z-10 hover:bg-red-50"
                    title="Remove from comparison"
                  >
                    <X className="w-3.5 h-3.5 text-red-500" />
                  </button>
                  {/* Image */}
                  <div className="h-40 bg-gray-50">
                    <img
                      src={prop.images?.[0] || `https://placehold.co/400x300/f0fdf4/059669?text=${encodeURIComponent(prop.city)}`}
                      alt={prop.title}
                      className="w-full h-full object-cover"
                      onError={(e) => {
                        (e.target as HTMLImageElement).src =
                          `https://placehold.co/400x300/f0fdf4/059669?text=${encodeURIComponent(prop.city)}`;
                      }}
                    />
                  </div>
                  {/* Title */}
                  <div className="p-3">
                    <div className="flex flex-wrap gap-1 mb-1.5">
                      <Badge variant={prop.listing_type === 'sale' ? 'info' : 'purple'}>
                        {getListingTypeLabel(prop.listing_type)}
                      </Badge>
                      {prop.is_verified && (
                        <Badge variant="success">Verified</Badge>
                      )}
                    </div>
                    <Link href={`/properties/${prop.id}`}>
                      <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 hover:text-emerald-700 transition-colors">
                        {prop.title}
                      </h3>
                    </Link>
                    <p className="text-xs text-gray-500 mt-1 flex items-center gap-1">
                      <MapPin className="w-3 h-3 flex-shrink-0" />
                      {prop.city}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            {/* Comparison rows */}
            <div
              className="grid gap-4 min-w-[600px] mt-4"
              style={{ gridTemplateColumns: `200px repeat(${properties.length}, 1fr)` }}
            >
              {/* Price */}
              <RowHeader label="Price" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  <span className="text-lg font-bold text-gray-900">
                    {formatCurrency(prop.price, prop.currency)}
                  </span>
                  {prop.listing_type === 'rent' && (
                    <span className="text-xs text-gray-400 block">per month</span>
                  )}
                  {prop.price_negotiable && (
                    <span className="text-xs text-emerald-600 font-medium">Negotiable</span>
                  )}
                </Cell>
              ))}

              {/* City */}
              <RowHeader label="City" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  <div className="flex items-center gap-1.5 text-sm text-gray-700">
                    <MapPin className="w-4 h-4 text-gray-400" />
                    {prop.city}, {prop.county}
                  </div>
                </Cell>
              ))}

              {/* Bedrooms */}
              <RowHeader label="Bedrooms" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  {prop.bedrooms ? (
                    <div className="flex items-center gap-1.5 text-sm text-gray-700">
                      <BedDouble className="w-4 h-4 text-gray-400" />
                      <span className="font-semibold">{prop.bedrooms}</span> Bedrooms
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </Cell>
              ))}

              {/* Bathrooms */}
              <RowHeader label="Bathrooms" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  {prop.bathrooms ? (
                    <div className="flex items-center gap-1.5 text-sm text-gray-700">
                      <Bath className="w-4 h-4 text-gray-400" />
                      <span className="font-semibold">{prop.bathrooms}</span> Bathrooms
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </Cell>
              ))}

              {/* Size */}
              <RowHeader label="Size (sq ft)" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  {prop.size_sqft ? (
                    <div className="flex items-center gap-1.5 text-sm text-gray-700">
                      <Maximize className="w-4 h-4 text-gray-400" />
                      <span className="font-semibold">{prop.size_sqft.toLocaleString()}</span> sq ft
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">—</span>
                  )}
                </Cell>
              ))}

              {/* Type */}
              <RowHeader label="Property Type" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  <span className="text-sm text-gray-700 capitalize">{getPropertyTypeLabel(prop.property_type)}</span>
                </Cell>
              ))}

              {/* Listing Type */}
              <RowHeader label="Listing Type" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  <span className="text-sm text-gray-700">{getListingTypeLabel(prop.listing_type)}</span>
                </Cell>
              ))}

              {/* Trust Score */}
              <RowHeader label="Trust Score" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  {prop.trust_score ? (
                    <div className="flex items-center gap-2">
                      <ShieldCheck className={`w-5 h-5 ${getTrustScoreColor(prop.trust_score)}`} />
                      <div>
                        <span className={`text-lg font-bold ${getTrustScoreColor(prop.trust_score)}`}>
                          {Math.round(prop.trust_score)}
                        </span>
                        <span className="text-xs text-gray-400 ml-0.5">/100</span>
                      </div>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">Not yet scored</span>
                  )}
                </Cell>
              ))}

              {/* Amenities */}
              <RowHeader label="Amenities" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  {(prop.amenities || []).length > 0 ? (
                    <div className="flex flex-wrap gap-1.5">
                      {prop.amenities!.slice(0, 8).map((amenity) => (
                        <span
                          key={amenity}
                          className="inline-flex items-center gap-1 text-xs bg-gray-100 text-gray-700 px-2 py-1 rounded-lg"
                        >
                          <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                          {amenity}
                        </span>
                      ))}
                      {prop.amenities!.length > 8 && (
                        <span className="text-xs text-gray-400">+{prop.amenities!.length - 8} more</span>
                      )}
                    </div>
                  ) : (
                    <span className="text-sm text-gray-400">None listed</span>
                  )}
                </Cell>
              ))}

              {/* Year Built */}
              <RowHeader label="Year Built" />
              {properties.map((prop) => (
                <Cell key={prop.id}>
                  <span className="text-sm text-gray-700">{prop.year_built || '—'}</span>
                </Cell>
              ))}
            </div>

            <div className="mt-8 text-center">
              <Link href="/market">
                <Button variant="outline" leftIcon={<Home className="w-4 h-4" />}>
                  Browse All Properties
                </Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function RowHeader({ label }: { label: string }) {
  return (
    <div className="bg-gray-50 rounded-xl px-4 py-3 flex items-center">
      <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">{label}</span>
    </div>
  );
}

function Cell({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-white rounded-xl border border-gray-50 px-4 py-3 flex items-center min-h-[56px]">
      {children}
    </div>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    }>
      <CompareContent />
    </Suspense>
  );
}
