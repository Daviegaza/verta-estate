'use client';

import { useState, useEffect, useCallback, Suspense } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Spinner, Badge } from '@/components/ui/card';
import api from '@/lib/api';
import type { Property } from '@/types';
import {
  formatCurrency, getListingTypeLabel, getPropertyTypeLabel,
  getTrustScoreColor, getTrustScoreBg, getBadgeColor
} from '@/lib/utils';
import {
  X, MapPin, BedDouble, Bath, Maximize, ShieldCheck,
  ChevronRight, Search, Home, BarChart3, CheckCircle2,
  Trash2, Plus, Calendar, ArrowLeft, AlertCircle,
  Star, Scale, Building2, Layers, Eye, Sparkles
} from 'lucide-react';

const MAX_COMPARE = 4;

function CompareContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const idsFromUrl = searchParams.get('ids');

  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [isClient, setIsClient] = useState(false);

  // Ensure we are on the client before reading localStorage
  useEffect(() => {
    setIsClient(true);
  }, []);

  // Load properties from the URL ids or fallback to localStorage
  const loadFromIds = useCallback(async (ids: number[]) => {
    if (ids.length === 0) {
      setProperties([]);
      setLoading(false);
      return;
    }

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
  }, []);

  useEffect(() => {
    if (idsFromUrl) {
      const ids = idsFromUrl.split(',').map(Number).filter((n) => !isNaN(n) && n > 0);
      loadFromIds(ids);
    } else if (isClient && typeof window !== 'undefined') {
      // Read from localStorage as fallback
      try {
        const stored = localStorage.getItem('vestra_compare');
        if (stored) {
          const ids: number[] = JSON.parse(stored);
          if (ids.length > 0) {
            loadFromIds(ids);
          } else {
            setLoading(false);
          }
        } else {
          setLoading(false);
        }
      } catch {
        setLoading(false);
      }
    } else {
      setLoading(false);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idsFromUrl, isClient]);

  const removeProperty = (id: number) => {
    const remaining = properties.filter((p) => p.id !== id);
    setProperties(remaining);

    // Update localStorage
    if (typeof window !== 'undefined') {
      const remainingIds = remaining.map((p) => p.id);
      localStorage.setItem('vestra_compare', JSON.stringify(remainingIds));
    }

    // Option A: keep page usable without URL param
    if (remaining.length === 0) {
      router.replace('/properties/compare', { scroll: false });
    }
  };

  const clearAll = () => {
    setProperties([]);
    if (typeof window !== 'undefined') {
      localStorage.setItem('vestra_compare', JSON.stringify([]));
    }
    router.replace('/properties/compare', { scroll: false });
  };

  const addFromMarket = () => {
    router.push('/market');
  };

  // Determine the highest / lowest values for highlighting
  const bestPrice = properties.length > 0
    ? Math.min(...properties.map((p) => p.price))
    : null;
  const bestTrustScore = properties.length > 0
    ? Math.max(...properties.map((p) => p.trust_score ?? 0))
    : null;
  const largestSize = properties.length > 0
    ? Math.max(...properties.map((p) => p.size_sqft ?? 0))
    : null;
  const mostBedrooms = properties.length > 0
    ? Math.max(...properties.map((p) => p.bedrooms ?? 0))
    : null;
  const mostBathrooms = properties.length > 0
    ? Math.max(...properties.map((p) => p.bathrooms ?? 0))
    : null;

  const isBestPrice = (p: Property) => bestPrice !== null && p.price === bestPrice;
  const isBestTrust = (p: Property) => bestTrustScore !== null && bestTrustScore > 0 && (p.trust_score ?? 0) === bestTrustScore;
  const isLargestSize = (p: Property) => largestSize !== null && largestSize > 0 && (p.size_sqft ?? 0) === largestSize;
  const isMostBedrooms = (p: Property) => mostBedrooms !== null && mostBedrooms > 0 && (p.bedrooms ?? 0) === mostBedrooms;
  const isMostBathrooms = (p: Property) => mostBathrooms !== null && mostBathrooms > 0 && (p.bathrooms ?? 0) === mostBathrooms;

  const renderHighlight = (isBest: boolean, label: string) =>
    isBest ? (
      <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-600 bg-emerald-50 px-1.5 py-0.5 rounded-full mt-0.5">
        <Sparkles className="w-2.5 h-2.5" />
        Best {label}
      </span>
    ) : null;

  // ── Columns grid class ───────────────────────────────────────────────────
  const colsClass = properties.length === 2
    ? 'grid-cols-2'
    : properties.length === 3
    ? 'grid-cols-2 md:grid-cols-3'
    : 'grid-cols-2 md:grid-cols-4';

  return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 transition-colors duration-200">
        <Navbar />

        {/* Breadcrumb */}
        <div className="bg-white dark:bg-gray-900 border-b border-gray-100 dark:border-gray-800">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
            <Link href="/" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors">Home</Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <Link href="/market" className="hover:text-gray-700 dark:hover:text-gray-300 transition-colors">Properties</Link>
            <ChevronRight className="w-3.5 h-3.5" />
            <span className="text-gray-900 dark:text-gray-100 font-medium">Compare Properties</span>
          </div>
        </div>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-8">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
                <BarChart3 className="w-6 h-6 text-emerald-600" />
                Compare Properties
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                Compare up to {MAX_COMPARE} properties side-by-side to make an informed decision.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {properties.length > 0 && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={clearAll}
                  leftIcon={<Trash2 className="w-4 h-4" />}
                  className="text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-950"
                >
                  Clear All
                </Button>
              )}
              <Button
                variant="outline"
                size="sm"
                onClick={addFromMarket}
                leftIcon={<Plus className="w-4 h-4" />}
              >
                {properties.length > 0 ? 'Add More' : 'Browse Properties'}
              </Button>
            </div>
          </div>

          {/* Loading */}
          {loading ? (
            <div className="flex justify-center items-center py-32">
              <Spinner size="lg" />
            </div>
          ) : properties.length < 2 && !error ? (
            /* Empty state — less than 2 properties */
            <div className="text-center py-20">
              <div className="w-20 h-20 bg-emerald-50 dark:bg-emerald-900/30 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <Scale className="w-10 h-10 text-emerald-500" />
              </div>
              <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">Select Properties to Compare</h3>
              <p className="text-gray-400 dark:text-gray-500 mb-2 max-w-md mx-auto">
                {properties.length === 0
                  ? 'Add properties from the market to compare them side-by-side.'
                  : 'Add at least one more property to start comparing.'}
              </p>
              <p className="text-xs text-gray-400 dark:text-gray-600 mb-8">
                Click the compare icon <Scale className="w-3 h-3 inline" /> on any property card in the market.
              </p>
              <div className="flex items-center justify-center gap-3">
                <Link href="/market">
                  <Button leftIcon={<Search className="w-4 h-4" />}>
                    Browse Market
                  </Button>
                </Link>
              </div>
            </div>
          ) : error && properties.length === 0 ? (
            /* Error state */
            <div className="text-center py-20">
              <div className="w-20 h-20 bg-red-50 dark:bg-red-900/30 rounded-3xl flex items-center justify-center mx-auto mb-6">
                <AlertCircle className="w-10 h-10 text-red-400" />
              </div>
              <h3 className="text-xl font-semibold text-gray-700 dark:text-gray-300 mb-2">Could Not Load Properties</h3>
              <p className="text-gray-400 dark:text-gray-500 mb-2">{error}</p>
              <Button variant="outline" onClick={() => window.location.reload()} className="mt-4">
                Try Again
              </Button>
            </div>
          ) : (
            /* Comparison Table */
            <div className="space-y-6">
              {/* Property Header Cards */}
              <div className={`grid ${colsClass} gap-4`}>
                {properties.map((prop, idx) => (
                  <div
                    key={prop.id}
                    className="group relative bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden shadow-sm hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
                  >
                    {/* Rank badge */}
                    <div className="absolute top-3 left-3 z-10 w-7 h-7 bg-emerald-600/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-sm">
                      <span className="text-xs font-bold text-white">{idx + 1}</span>
                    </div>

                    {/* Remove button */}
                    <button
                      onClick={() => removeProperty(prop.id)}
                      className="absolute top-3 right-3 z-10 w-7 h-7 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm rounded-full flex items-center justify-center shadow-sm opacity-0 group-hover:opacity-100 transition-opacity hover:bg-red-50 dark:hover:bg-red-900/50"
                      title="Remove from comparison"
                    >
                      <X className="w-3.5 h-3.5 text-red-500" />
                    </button>

                    {/* Image */}
                    <div className="h-40 bg-gray-100 dark:bg-gray-800 relative">
                      <img
                        src={prop.images?.[0] || `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect fill="#ecfdf5" width="400" height="300"/><text x="200" y="150" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" font-size="20" font-weight="bold" fill="#059669">${prop.city || 'VESTRA'}</text></svg>`)}`}
                        alt={prop.title}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          const target = e.target as HTMLImageElement;
                          target.src = `data:image/svg+xml,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300"><rect fill="#ecfdf5" width="400" height="300"/><text x="200" y="150" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" font-size="20" font-weight="bold" fill="#059669">${prop.city || 'VESTRA'}</text></svg>`)}`;
                        }}
                      />

                      {/* Verification badge overlay */}
                      {prop.is_verified && (
                        <div className={`absolute bottom-2 left-2 text-xs font-semibold px-2 py-1 rounded-full backdrop-blur-sm border inline-flex items-center gap-1 ${getBadgeColor(prop.verification_badge)}`}>
                          <ShieldCheck className="w-3 h-3" />
                          {prop.verification_badge ? prop.verification_badge.charAt(0).toUpperCase() + prop.verification_badge.slice(1) : 'Verified'}
                        </div>
                      )}
                    </div>

                    {/* Content */}
                    <div className="p-4">
                      {/* Type badges */}
                      <div className="flex flex-wrap gap-1 mb-1.5">
                        <Badge variant={prop.listing_type === 'sale' ? 'info' : 'purple'}>
                          {getListingTypeLabel(prop.listing_type)}
                        </Badge>
                        <Badge variant="default">
                          {getPropertyTypeLabel(prop.property_type)}
                        </Badge>
                      </div>

                      {/* Title */}
                      <Link href={`/properties/${prop.id}`}>
                        <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-sm leading-snug line-clamp-2 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors mb-1">
                          {prop.title}
                        </h3>
                      </Link>

                      {/* Price — prominent */}
                      <div className="mb-2">
                        <p className="text-xl font-bold text-gray-900 dark:text-white">
                          {formatCurrency(prop.price, prop.currency)}
                        </p>
                        {prop.listing_type === 'rent' && (
                          <span className="text-xs text-gray-400">per month</span>
                        )}
                        {prop.price_negotiable && (
                          <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium ml-1">Negotiable</span>
                        )}
                        {renderHighlight(isBestPrice(prop), 'Price')}
                      </div>

                      {/* Location */}
                      <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 mb-3">
                        <MapPin className="w-3 h-3 flex-shrink-0" />
                        <span className="truncate">{prop.city}, {prop.county}</span>
                      </div>

                      {/* Quick stats row */}
                      <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 flex-wrap">
                        {prop.bedrooms != null && prop.bedrooms > 0 && (
                          <div className="flex items-center gap-1">
                            <BedDouble className="w-3.5 h-3.5 text-gray-400" />
                            <span className="font-medium text-gray-700 dark:text-gray-300">{prop.bedrooms}</span>
                          </div>
                        )}
                        {prop.bathrooms != null && prop.bathrooms > 0 && (
                          <div className="flex items-center gap-1">
                            <Bath className="w-3.5 h-3.5 text-gray-400" />
                            <span className="font-medium text-gray-700 dark:text-gray-300">{prop.bathrooms}</span>
                          </div>
                        )}
                        {prop.size_sqft != null && prop.size_sqft > 0 && (
                          <div className="flex items-center gap-1">
                            <Maximize className="w-3.5 h-3.5 text-gray-400" />
                            <span className="font-medium text-gray-700 dark:text-gray-300">{prop.size_sqft.toLocaleString()} sqft</span>
                          </div>
                        )}
                      </div>

                      {/* Trust Score */}
                      {prop.trust_score && (
                        <div className={`mt-3 pt-3 border-t border-gray-50 dark:border-gray-800 flex items-center gap-2 ${getTrustScoreBg(prop.trust_score)} rounded-xl p-2`}>
                          <ShieldCheck className={`w-4 h-4 ${getTrustScoreColor(prop.trust_score)}`} />
                          <div className="flex items-center gap-1">
                            <span className={`text-sm font-bold ${getTrustScoreColor(prop.trust_score)}`}>
                              {Math.round(prop.trust_score)}
                            </span>
                            <span className="text-xs text-gray-400">Trust Score</span>
                          </div>
                          {renderHighlight(isBestTrust(prop), 'Trust')}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Detailed Comparison Table */}
              <div className="bg-white dark:bg-gray-900 rounded-2xl border border-gray-100 dark:border-gray-800 overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-100 dark:border-gray-800">
                        <th className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800/50 w-44">
                          Feature
                        </th>
                        {properties.map((prop) => (
                          <th
                            key={prop.id}
                            className="text-left px-4 py-3 text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-50 dark:bg-gray-800/50"
                          >
                            <Link href={`/properties/${prop.id}`} className="hover:text-emerald-600 dark:hover:text-emerald-400 transition-colors">
                              {prop.title.length > 40 ? prop.title.slice(0, 40) + '…' : prop.title}
                            </Link>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50 dark:divide-gray-800">
                      {/* Price */}
                      <CompareRow
                        label="Price"
                        icon={<BarChart3 className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell
                            key={prop.id}
                            isHighlighted={isBestPrice(prop)}
                            highlightLabel="Best Price"
                          >
                            <div>
                              <span className="text-base font-bold text-gray-900 dark:text-white">
                                {formatCurrency(prop.price, prop.currency)}
                              </span>
                              {prop.listing_type === 'rent' && (
                                <span className="text-xs text-gray-400 block">per month</span>
                              )}
                              {prop.price_negotiable && (
                                <span className="text-xs text-emerald-600 dark:text-emerald-400 font-medium">Negotiable</span>
                              )}
                            </div>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Property Type */}
                      <CompareRow
                        label="Property Type"
                        icon={<Building2 className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            <span className="text-gray-700 dark:text-gray-300 capitalize">
                              {getPropertyTypeLabel(prop.property_type)}
                            </span>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Listing Type */}
                      <CompareRow
                        label="Listing Type"
                        icon={<Layers className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            <Badge variant={prop.listing_type === 'sale' ? 'info' : 'purple'}>
                              {getListingTypeLabel(prop.listing_type)}
                            </Badge>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Location */}
                      <CompareRow
                        label="Location"
                        icon={<MapPin className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            <div className="text-gray-700 dark:text-gray-300">
                              <p className="font-medium">{prop.city}</p>
                              <p className="text-xs text-gray-400">{prop.county}, {prop.country}</p>
                            </div>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Bedrooms */}
                      <CompareRow
                        label="Bedrooms"
                        icon={<BedDouble className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell
                            key={prop.id}
                            isHighlighted={isMostBedrooms(prop) && (prop.bedrooms ?? 0) > 0}
                            highlightLabel="Most"
                          >
                            {prop.bedrooms ? (
                              <span className="text-gray-700 dark:text-gray-300 font-semibold text-lg">
                                {prop.bedrooms}
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Bathrooms */}
                      <CompareRow
                        label="Bathrooms"
                        icon={<Bath className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell
                            key={prop.id}
                            isHighlighted={isMostBathrooms(prop) && (prop.bathrooms ?? 0) > 0}
                            highlightLabel="Most"
                          >
                            {prop.bathrooms ? (
                              <span className="text-gray-700 dark:text-gray-300 font-semibold text-lg">
                                {prop.bathrooms}
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Size */}
                      <CompareRow
                        label="Size (sq ft)"
                        icon={<Maximize className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell
                            key={prop.id}
                            isHighlighted={isLargestSize(prop) && (prop.size_sqft ?? 0) > 0}
                            highlightLabel="Largest"
                          >
                            {prop.size_sqft ? (
                              <span className="text-gray-700 dark:text-gray-300 font-semibold">
                                {prop.size_sqft.toLocaleString()} sq ft
                              </span>
                            ) : (
                              <span className="text-gray-400">—</span>
                            )}
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Year Built */}
                      <CompareRow
                        label="Year Built"
                        icon={<Calendar className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            <span className="text-gray-700 dark:text-gray-300">
                              {prop.year_built || '—'}
                            </span>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Verification Status */}
                      <CompareRow
                        label="Verification"
                        icon={<ShieldCheck className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            {prop.is_verified ? (
                              <div className="flex items-center gap-1.5">
                                <ShieldCheck className={`w-4 h-4 ${prop.verification_badge === 'platinum' ? 'text-purple-500' : prop.verification_badge === 'gold' ? 'text-yellow-500' : 'text-emerald-500'}`} />
                                <div>
                                  <span className="text-sm font-medium text-emerald-700 dark:text-emerald-400">Verified</span>
                                  {prop.verification_badge && (
                                    <span className={`text-[10px] font-semibold ml-1 px-1.5 py-0.5 rounded-full ${getBadgeColor(prop.verification_badge)}`}>
                                      {prop.verification_badge.toUpperCase()}
                                    </span>
                                  )}
                                </div>
                              </div>
                            ) : (
                              <span className="text-sm text-gray-400">Not Verified</span>
                            )}
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Trust Score */}
                      <CompareRow
                        label="Trust Score"
                        icon={<Star className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell
                            key={prop.id}
                            isHighlighted={isBestTrust(prop) && (prop.trust_score ?? 0) > 0}
                            highlightLabel="Highest"
                          >
                            {prop.trust_score ? (
                              <div className="flex items-center gap-2">
                                <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl ${getTrustScoreBg(prop.trust_score)}`}>
                                  <ShieldCheck className={`w-4 h-4 ${getTrustScoreColor(prop.trust_score)}`} />
                                  <span className={`text-base font-bold ${getTrustScoreColor(prop.trust_score)}`}>
                                    {Math.round(prop.trust_score)}
                                  </span>
                                </div>
                                {renderHighlight(isBestTrust(prop), '')}
                              </div>
                            ) : (
                              <span className="text-sm text-gray-400">Not yet scored</span>
                            )}
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Views */}
                      <CompareRow
                        label="Views"
                        icon={<Eye className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            <span className="text-gray-700 dark:text-gray-300">
                              {prop.views.toLocaleString()}
                            </span>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Address */}
                      <CompareRow
                        label="Address"
                        icon={<MapPin className="w-4 h-4" />}
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            <span className="text-gray-700 dark:text-gray-300 text-xs leading-relaxed">
                              {prop.address}
                            </span>
                          </CompareCell>
                        ))}
                      </CompareRow>

                      {/* Amenities */}
                      <CompareRow
                        label="Amenities"
                        icon={<CheckCircle2 className="w-4 h-4" />}
                        isLast
                      >
                        {properties.map((prop) => (
                          <CompareCell key={prop.id}>
                            {(prop.amenities || []).length > 0 ? (
                              <div className="flex flex-wrap gap-1.5">
                                {prop.amenities!.map((amenity) => (
                                  <span
                                    key={amenity}
                                    className="inline-flex items-center gap-1 text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 px-2 py-1 rounded-lg"
                                  >
                                    <CheckCircle2 className="w-3 h-3 text-emerald-500 flex-shrink-0" />
                                    {amenity}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-sm text-gray-400">None listed</span>
                            )}
                          </CompareCell>
                        ))}
                      </CompareRow>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Action footer */}
              <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-4">
                <Link href="/market">
                  <Button variant="outline" leftIcon={<ArrowLeft className="w-4 h-4" />}>
                    Back to Market
                  </Button>
                </Link>
                <Button
                  variant="outline"
                  onClick={clearAll}
                  leftIcon={<Trash2 className="w-4 h-4" />}
                  className="text-red-600 border-red-200 hover:bg-red-50 dark:text-red-400 dark:border-red-800 dark:hover:bg-red-950"
                >
                  Clear Comparison
                </Button>
              </div>
            </div>
          )}
        </div>
      </div>
  );
}

// ── Sub-components ──────────────────────────────────────────────────────────

interface CompareRowProps {
  label: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  isLast?: boolean;
}

function CompareRow({ label, icon, children, isLast = false }: CompareRowProps) {
  return (
    <tr className={`${isLast ? '' : 'border-b border-gray-50 dark:border-gray-800'} hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors`}>
      <td className="px-4 py-4 align-top">
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <span className="flex-shrink-0">{icon}</span>
          <span className="text-xs font-semibold uppercase tracking-wider">{label}</span>
        </div>
      </td>
      {children}
    </tr>
  );
}

interface CompareCellProps {
  children: React.ReactNode;
  isHighlighted?: boolean;
  highlightLabel?: string;
}

function CompareCell({ children, isHighlighted = false, highlightLabel }: CompareCellProps) {
  return (
    <td className={`px-4 py-4 ${isHighlighted ? 'bg-emerald-50/50 dark:bg-emerald-900/10' : ''}`}>
      <div className="flex flex-col gap-1">
        {children}
        {isHighlighted && highlightLabel && (
          <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/30 px-1.5 py-0.5 rounded-full w-fit">
            <Sparkles className="w-2.5 h-2.5" />
            {highlightLabel}
          </span>
        )}
      </div>
    </td>
  );
}

export default function ComparePage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 bg-emerald-600 rounded-2xl flex items-center justify-center">
            <Scale className="w-5 h-5 text-white" />
          </div>
          <Spinner size="lg" />
          <p className="text-sm text-gray-500 dark:text-gray-400">Loading comparison...</p>
        </div>
      </div>
    }>
      <CompareContent />
    </Suspense>
  );
}
