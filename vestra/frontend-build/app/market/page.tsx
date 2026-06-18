'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import PropertyCard from '@/components/property/PropertyCard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import type { Property, PropertyListResponse } from '@/types';
import {
  Search, SlidersHorizontal, X, Sparkles, MapPin,
  Home, Building2, Trees, ChevronLeft, ChevronRight
} from 'lucide-react';
import { KENYA_CITIES } from '@/lib/utils';

const PROPERTY_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'residential', label: 'Residential' },
  { value: 'commercial', label: 'Commercial' },
  { value: 'land', label: 'Land' },
  { value: 'agricultural', label: 'Agricultural' },
  { value: 'short_stay', label: 'Short Stay' },
];

const LISTING_TYPES = [
  { value: '', label: 'Buy & Rent' },
  { value: 'sale', label: 'For Sale' },
  { value: 'rent', label: 'For Rent' },
  { value: 'lease', label: 'For Lease' },
];

const PRICE_RANGES = [
  { label: 'Any Price', min: undefined, max: undefined },
  { label: 'Under KES 20K', min: undefined, max: 20000 },
  { label: 'KES 20K–50K', min: 20000, max: 50000 },
  { label: 'KES 50K–200K', min: 50000, max: 200000 },
  { label: 'KES 200K–1M', min: 200000, max: 1000000 },
  { label: 'Above KES 1M', min: 1000000, max: undefined },
];

function MarketContent() {
  const searchParams = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const isAiSearch = searchParams.get('ai') === '1';

  const [properties, setProperties] = useState<Property[]>([]);
  const [total, setTotal] = useState(0);
  const [pages, setPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [showFilters, setShowFilters] = useState(false);
  const [aiInterpretation, setAiInterpretation] = useState('');

  const [query, setQuery] = useState(initialQuery);
  const [inputValue, setInputValue] = useState(initialQuery);
  const [useAi, setUseAi] = useState(isAiSearch);
  const [page, setPage] = useState(1);

  const [filters, setFilters] = useState({
    city: '',
    property_type: '',
    listing_type: '',
    min_price: undefined as number | undefined,
    max_price: undefined as number | undefined,
    bedrooms: undefined as number | undefined,
    verified_only: false,
  });

  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      if (useAi && query) {
        const result = await api.aiSearch(query);
        setProperties(result.items || []);
        setTotal(result.total || 0);
        setPages(result.pages || 1);
        setAiInterpretation(result.interpretation || '');
      } else {
        const result: PropertyListResponse = await api.listProperties({
          query: query || undefined,
          city: filters.city || undefined,
          property_type: (filters.property_type as any) || undefined,
          listing_type: (filters.listing_type as any) || undefined,
          min_price: filters.min_price,
          max_price: filters.max_price,
          bedrooms: filters.bedrooms,
          verified_only: filters.verified_only,
          page,
          size: 20,
        });
        setProperties(result.items || []);
        setTotal(result.total || 0);
        setPages(result.pages || 1);
        setAiInterpretation('');
      }
    } catch (err) {
      console.error('Search error:', err);
      setProperties([]);
    } finally {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, page, useAi,
    filters.city, filters.property_type, filters.listing_type,
    filters.min_price, filters.max_price, filters.bedrooms, filters.verified_only,
  ]);

  useEffect(() => {
    fetchProperties();
  }, [fetchProperties]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(inputValue);
    setPage(1);
  };

  const clearFilters = () => {
    setFilters({ city: '', property_type: '', listing_type: '', min_price: undefined, max_price: undefined, bedrooms: undefined, verified_only: false });
    setPage(1);
  };

  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      {/* Search header */}
      <div className="bg-white border-b border-gray-100 sticky top-16 z-30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <form onSubmit={handleSearch} className="flex gap-2">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={useAi ? 'Try: 3 bedroom house in Karen with garden...' : 'Search properties...'}
                className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white"
              />
            </div>
            <button
              type="button"
              onClick={() => setUseAi(!useAi)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-medium border transition-all ${
                useAi ? 'bg-emerald-600 text-white border-emerald-600' : 'bg-white text-gray-600 border-gray-200 hover:border-emerald-400'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              AI
            </button>
            <Button type="submit" size="sm">Search</Button>
            <button
              type="button"
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-1.5 px-3 py-2 rounded-xl text-sm border transition-all ${
                activeFilterCount > 0 ? 'bg-emerald-50 border-emerald-300 text-emerald-700' : 'border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
              Filters
              {activeFilterCount > 0 && (
                <span className="w-4 h-4 bg-emerald-600 text-white rounded-full text-xs flex items-center justify-center">{activeFilterCount}</span>
              )}
            </button>
          </form>

          {/* Filter pills */}
          <div className="flex gap-2 mt-3 overflow-x-auto pb-1">
            {LISTING_TYPES.map((lt) => (
              <button
                key={lt.value}
                onClick={() => { setFilters((f) => ({ ...f, listing_type: lt.value })); setPage(1); }}
                className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                  filters.listing_type === lt.value
                    ? 'bg-gray-900 text-white border-gray-900'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                }`}
              >
                {lt.label}
              </button>
            ))}
            <div className="w-px bg-gray-200 mx-1 flex-shrink-0" />
            {PROPERTY_TYPES.slice(1).map((pt) => (
              <button
                key={pt.value}
                onClick={() => { setFilters((f) => ({ ...f, property_type: pt.value })); setPage(1); }}
                className={`flex-shrink-0 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                  filters.property_type === pt.value
                    ? 'bg-emerald-600 text-white border-emerald-600'
                    : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
                }`}
              >
                {pt.label}
              </button>
            ))}
            <button
              onClick={() => { setFilters((f) => ({ ...f, verified_only: !f.verified_only })); setPage(1); }}
              className={`flex-shrink-0 flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium border transition-all ${
                filters.verified_only
                  ? 'bg-blue-600 text-white border-blue-600'
                  : 'bg-white text-gray-600 border-gray-200 hover:border-gray-400'
              }`}
            >
              ✓ Verified Only
            </button>
          </div>
        </div>

        {/* Expanded filters */}
        {showFilters && (
          <div className="border-t border-gray-100 bg-gray-50 px-4 sm:px-6 py-4">
            <div className="max-w-7xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">City</label>
                <select
                  value={filters.city}
                  onChange={(e) => { setFilters((f) => ({ ...f, city: e.target.value })); setPage(1); }}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">All Cities</option>
                  {KENYA_CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">Price Range</label>
                <select
                  onChange={(e) => {
                    const range = PRICE_RANGES[parseInt(e.target.value)];
                    setFilters((f) => ({ ...f, min_price: range.min, max_price: range.max }));
                    setPage(1);
                  }}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  {PRICE_RANGES.map((r, i) => <option key={i} value={i}>{r.label}</option>)}
                </select>
              </div>
              <div>
                <label className="text-xs font-medium text-gray-600 mb-1.5 block">Bedrooms</label>
                <select
                  value={filters.bedrooms ?? ''}
                  onChange={(e) => { setFilters((f) => ({ ...f, bedrooms: e.target.value ? parseInt(e.target.value) : undefined })); setPage(1); }}
                  className="w-full text-sm border border-gray-200 rounded-xl px-3 py-2.5 bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                >
                  <option value="">Any</option>
                  {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}+ Beds</option>)}
                </select>
              </div>
              <div className="flex items-end">
                {activeFilterCount > 0 && (
                  <button onClick={clearFilters} className="flex items-center gap-1.5 text-sm text-red-600 hover:text-red-700 font-medium">
                    <X className="w-4 h-4" /> Clear All
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Results */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
        {/* AI interpretation */}
        {aiInterpretation && (
          <div className="mb-4 p-4 bg-blue-50 border border-blue-200 rounded-xl flex items-start gap-3">
            <Sparkles className="w-4 h-4 text-blue-600 flex-shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-medium text-blue-800">AI Search</p>
              <p className="text-sm text-blue-700">{aiInterpretation}</p>
            </div>
          </div>
        )}

        <div className="flex items-center justify-between mb-4">
          <p className="text-sm text-gray-500">
            {loading ? 'Searching...' : `${total.toLocaleString()} properties found`}
          </p>
          <p className="text-xs text-gray-400">Page {page} of {pages}</p>
        </div>

        {loading ? (
          <div className="flex justify-center items-center py-32">
            <Spinner size="lg" />
          </div>
        ) : properties.length === 0 ? (
          <div className="text-center py-32">
            <Home className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No properties found</h3>
            <p className="text-gray-400 mb-6">Try adjusting your search or filters</p>
            <Button onClick={clearFilters} variant="outline">Clear Filters</Button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
              {properties.map((prop) => (
                <PropertyCard key={prop.id} property={prop} />
              ))}
            </div>

            {/* Pagination */}
            {pages > 1 && (
              <div className="flex items-center justify-center gap-2 mt-10">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="p-2 rounded-xl border border-gray-200 text-gray-600 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-5 h-5" />
                </button>
                {Array.from({ length: pages }, (_, i) => i + 1).map((p) => (
                  <button
                    key={p}
                    onClick={() => setPage(p)}
                    className={`w-10 h-10 rounded-xl text-sm font-medium transition-all ${
                      page === p ? 'bg-emerald-600 text-white' : 'border border-gray-200 text-gray-600 hover:border-gray-400'
                    }`}
                  >
                    {p}
                  </button>
                ))}
                <button
                  onClick={() => setPage((p) => Math.min(pages, p + 1))}
                  disabled={page === pages}
                  className="p-2 rounded-xl border border-gray-200 text-gray-600 hover:border-gray-400 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="w-5 h-5" />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
export default function MarketPage() { return <Suspense fallback={<div className="flex justify-center items-center min-h-screen"><div className="animate-spin rounded-full border-2 border-emerald-600 border-t-transparent w-10 h-10"/></div>}><MarketContent /></Suspense>; }
