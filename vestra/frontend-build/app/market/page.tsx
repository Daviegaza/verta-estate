'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import Link from 'next/link';
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
  Home, Building2, Trees, ChevronLeft, ChevronRight,
  LayoutGrid, List, BedDouble, Bath, Maximize, Eye, ShieldCheck, Clock
} from 'lucide-react';
import { KENYA_CITIES, formatCurrency } from '@/lib/utils';

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
  const [aiContext, setAiContext] = useState<{ market_context?: string; ai_recommendations?: string[]; search_tips?: string[] }>({});

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

  const [viewMode, setViewMode] = useState<'grid' | 'list' | 'map'>('grid');
  const [compareIds, setCompareIds] = useState<number[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('vestra_compare');
        return stored ? JSON.parse(stored) : [];
      } catch { return []; }
    }
    return [];
  });

  const toggleCompare = (id: number) => {
    setCompareIds((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      if (typeof window !== 'undefined') localStorage.setItem('vestra_compare', JSON.stringify(next));
      return next;
    });
  };

  const fetchProperties = useCallback(async () => {
    setLoading(true);
    try {
      if (useAi && query) {
        const result = await api.aiSearch(query);
        setProperties(result.items || []);
        setTotal(result.total || 0);
        setPages(result.pages || 1);
        setAiInterpretation(result.interpretation || '');
        setAiContext({
          market_context: result.market_context || '',
          ai_recommendations: result.ai_recommendations || [],
          search_tips: result.search_tips || [],
        });
      } else {
        setAiContext({});
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
              onClick={() => { setUseAi(!useAi); setProperties([]); setLoading(true); }}
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
        {/* AI interpretation — enhanced */}
        {aiInterpretation && (
          <div className="mb-6 space-y-3">
            <div className="p-4 bg-gradient-to-r from-blue-50 to-emerald-50 border border-blue-200 rounded-xl flex items-start gap-3">
              <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center flex-shrink-0 mt-0.5">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-blue-900 mb-1">Vestra AI understood your search</p>
                <p className="text-sm text-blue-700 leading-relaxed">{aiInterpretation}</p>
                {aiContext.market_context && (
                  <p className="text-xs text-blue-600 mt-2 italic">{aiContext.market_context}</p>
                )}
              </div>
            </div>
            {/* AI recommendations */}
            {aiContext.ai_recommendations && aiContext.ai_recommendations.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {aiContext.ai_recommendations.map((tip: string, i: number) => (
                  <span key={i} className="inline-flex items-center gap-1 px-2.5 py-1 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-800">
                    <Sparkles className="w-3 h-3" /> {tip}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <p className="text-sm text-gray-500">
              {loading ? 'Searching...' : `${total.toLocaleString()} properties found`}
            </p>
            {/* View toggle */}
            {!loading && properties.length > 0 && (
              <div className="flex items-center gap-0.5 bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setViewMode('grid')}
                  className={`p-1.5 rounded-md text-xs font-medium transition-all ${
                    viewMode === 'grid' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title="Grid View"
                >
                  <LayoutGrid className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setViewMode('list')}
                  className={`p-1.5 rounded-md text-xs font-medium transition-all ${
                    viewMode === 'list' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title="List View"
                >
                  <List className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setViewMode('map')}
                  className={`p-1.5 rounded-md text-xs font-medium transition-all ${
                    viewMode === 'map' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
                  }`}
                  title="Map / Browse by City"
                >
                  <MapPin className="w-3.5 h-3.5" />
                </button>
              </div>
            )}
          </div>
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
            {/* Grid View */}
            {viewMode === 'grid' && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
                {properties.map((prop) => (
                  <PropertyCard key={prop.id} property={prop} />
                ))}
              </div>
            )}

            {/* List View */}
            {viewMode === 'list' && (
              <div className="space-y-2">
                {properties.map((prop) => (
                  <Link
                    key={prop.id}
                    href={`/properties/${prop.id}`}
                    className="block group focus:outline-none"
                  >
                    <div className="flex items-center gap-4 bg-white rounded-xl border border-gray-100 p-3 hover:shadow-card-hover hover:-translate-y-0.5 transition-all duration-200">
                      {/* Thumbnail */}
                      <div className="w-20 h-20 rounded-lg overflow-hidden bg-gray-50 flex-shrink-0">
                        <img
                          src={prop.images?.[0] || `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80"><rect fill="#ecfdf5" width="80" height="80"/><text x="40" y="40" text-anchor="middle" dominant-baseline="central" font-size="20">🏠</text></svg>`)}`}
                          alt={prop.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      </div>
                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <span className={`text-xs font-bold px-2 py-0.5 rounded-full ${
                            prop.listing_type === 'sale' ? 'bg-blue-100 text-blue-700' : prop.listing_type === 'rent' ? 'bg-purple-100 text-purple-700' : 'bg-gray-100 text-gray-700'
                          }`}>
                            {prop.listing_type === 'sale' ? 'For Sale' : prop.listing_type === 'rent' ? 'For Rent' : 'For Lease'}
                          </span>
                          {prop.is_verified && (
                            <span className="text-xs text-emerald-600 font-medium flex items-center gap-0.5">
                              <ShieldCheck className="w-3 h-3" /> Verified
                            </span>
                          )}
                        </div>
                        <h3 className="font-semibold text-gray-900 text-sm leading-snug truncate group-hover:text-emerald-700 transition-colors">
                          {prop.title}
                        </h3>
                        <div className="flex items-center gap-1 text-xs text-gray-500 mt-0.5">
                          <MapPin className="w-3 h-3 flex-shrink-0" />
                          <span className="truncate">{prop.city}, {prop.county}</span>
                        </div>
                      </div>
                      {/* Features */}
                      <div className="hidden sm:flex items-center gap-3 text-xs text-gray-500 flex-shrink-0">
                        {prop.bedrooms != null && prop.bedrooms > 0 && (
                          <span className="flex items-center gap-1 bg-gray-50 px-2 py-1 rounded-lg">
                            <BedDouble className="w-3.5 h-3.5 text-gray-400" />
                            <span className="font-medium text-gray-700">{prop.bedrooms}</span>
                          </span>
                        )}
                        {prop.bathrooms != null && prop.bathrooms > 0 && (
                          <span className="flex items-center gap-1 bg-gray-50 px-2 py-1 rounded-lg">
                            <Bath className="w-3.5 h-3.5 text-gray-400" />
                            <span className="font-medium text-gray-700">{prop.bathrooms}</span>
                          </span>
                        )}
                        {prop.size_sqft != null && prop.size_sqft > 0 && (
                          <span className="flex items-center gap-1 bg-gray-50 px-2 py-1 rounded-lg">
                            <Maximize className="w-3.5 h-3.5 text-gray-400" />
                            <span className="font-medium text-gray-700">{prop.size_sqft.toLocaleString()}</span>
                          </span>
                        )}
                      </div>
                      {/* Price & Trust */}
                      <div className="text-right flex-shrink-0">
                        <p className="text-lg font-bold text-gray-900 leading-none">
                          {formatCurrency(prop.price, prop.currency)}
                        </p>
                        {prop.listing_type === 'rent' && <span className="text-xs text-gray-400">/mo</span>}
                        {prop.trust_score && (
                          <div className={`flex items-center justify-end gap-1 mt-1.5 px-2 py-1 rounded-lg text-xs font-bold ${
                            prop.trust_score >= 80 ? 'bg-emerald-50 text-emerald-600' : prop.trust_score >= 60 ? 'bg-amber-50 text-amber-600' : 'bg-red-50 text-red-500'
                          }`}>
                            <ShieldCheck className="w-3 h-3" />
                            {Math.round(prop.trust_score)}
                          </div>
                        )}
                      </div>
                      {/* Compare checkbox */}
                      <button
                        onClick={(e) => { e.preventDefault(); e.stopPropagation(); toggleCompare(prop.id); }}
                        className={`flex-shrink-0 p-2 rounded-lg border transition-all ${
                          compareIds.includes(prop.id)
                            ? 'bg-emerald-50 border-emerald-300 text-emerald-600'
                            : 'border-gray-200 text-gray-400 hover:text-gray-600 hover:border-gray-300'
                        }`}
                        title={compareIds.includes(prop.id) ? 'Remove from compare' : 'Add to compare'}
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
                        </svg>
                      </button>
                    </div>
                  </Link>
                ))}
              </div>
            )}

            {/* Map / Browse by City View */}
            {viewMode === 'map' && (
              <div className="space-y-8">
                {(() => {
                  const grouped: Record<string, typeof properties> = {};
                  properties.forEach((p) => {
                    const city = p.city || 'Other';
                    if (!grouped[city]) grouped[city] = [];
                    grouped[city].push(p);
                  });
                  const cityOrder = ['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret', ...Object.keys(grouped).filter(c => !['Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret'].includes(c))];
                  const sortedCities = [...new Set([...cityOrder, ...Object.keys(grouped)])].filter(c => grouped[c]);
                  return sortedCities.map((city) => (
                    <div key={city}>
                      <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-200">
                        <div className="w-8 h-8 bg-emerald-100 rounded-full flex items-center justify-center">
                          <MapPin className="w-4 h-4 text-emerald-600" />
                        </div>
                        <h3 className="text-lg font-bold text-gray-900">{city}</h3>
                        <span className="text-sm text-gray-400 font-medium">({grouped[city].length} properties)</span>
                      </div>
                      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                        {grouped[city].map((prop) => (
                          <PropertyCard key={prop.id} property={prop} />
                        ))}
                      </div>
                    </div>
                  ));
                })()}
              </div>
            )}

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

        {/* Floating Compare Button */}
        {compareIds.length > 0 && (
          <div className="fixed bottom-6 right-6 z-50">
            <Link
              href={`/properties/compare?ids=${compareIds.join(',')}`}
              className="flex items-center gap-2 px-5 py-3 bg-emerald-600 text-white rounded-2xl shadow-xl hover:bg-emerald-700 hover:shadow-2xl hover:-translate-y-0.5 transition-all duration-200 font-semibold text-sm"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
              </svg>
              Compare ({compareIds.length})
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}
export default function MarketPage() { return <Suspense fallback={<div className="flex justify-center items-center min-h-screen"><div className="animate-spin rounded-full border-2 border-emerald-600 border-t-transparent w-10 h-10"/></div>}><MarketContent /></Suspense>; }
