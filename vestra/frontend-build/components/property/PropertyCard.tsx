'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { cn, formatCurrency, getListingTypeLabel, getPropertyTypeLabel, getBadgeColor } from '@/lib/utils';
import type { Property } from '@/types';
import {
  ShieldCheck, BedDouble, Bath, Maximize, MapPin, Eye,
  Heart, Sparkles, TrendingUp, Clock
} from 'lucide-react';
import api from '@/lib/api';

interface PropertyCardProps {
  property: Property;
  className?: string;
  skeleton?: boolean;
  isFavorited?: boolean;
}

export function PropertyCardSkeleton() {
  return (
    <div className="bg-white rounded-2xl border border-gray-100 overflow-hidden animate-pulse">
      <div className="h-48 bg-gray-100" />
      <div className="p-4 space-y-3">
        <div className="h-4 bg-gray-100 rounded-lg w-3/4" />
        <div className="h-3 bg-gray-100 rounded-lg w-1/2" />
        <div className="flex gap-3">
          <div className="h-3 bg-gray-100 rounded-lg w-12" />
          <div className="h-3 bg-gray-100 rounded-lg w-12" />
          <div className="h-3 bg-gray-100 rounded-lg w-16" />
        </div>
        <div className="flex justify-between items-center pt-2">
          <div className="h-6 bg-gray-100 rounded-lg w-24" />
          <div className="h-4 bg-gray-100 rounded-lg w-12" />
        </div>
      </div>
    </div>
  );
}

function PropertyCard({ property, className, isFavorited = false }: PropertyCardProps) {
  const [isLiked, setIsLiked] = useState(isFavorited);
  const [imageLoaded, setImageLoaded] = useState(false);
  const [isCompared, setIsCompared] = useState(() => {
    if (typeof window !== 'undefined') {
      try {
        const stored = localStorage.getItem('vestra_compare');
        const ids: number[] = stored ? JSON.parse(stored) : [];
        return ids.includes(property.id);
      } catch { return false; }
    }
    return false;
  });

  const trustScore = property.trust_score ? Math.round(property.trust_score) : null;
  const trustColor = trustScore
    ? trustScore >= 80 ? 'text-emerald-600' : trustScore >= 60 ? 'text-amber-600' : 'text-red-500'
    : 'text-gray-400';
  const trustBg = trustScore
    ? trustScore >= 80 ? 'bg-emerald-50' : trustScore >= 60 ? 'bg-amber-50' : 'bg-red-50'
    : 'bg-gray-50';
  const borderAccentColor = trustScore
    ? trustScore >= 80 ? 'border-l-emerald-500' : trustScore >= 60 ? 'border-l-amber-500' : 'border-l-red-500'
    : '';

  const toggleCompare = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const stored = localStorage.getItem('vestra_compare');
    const ids: number[] = stored ? JSON.parse(stored) : [];
    const next = isCompared
      ? ids.filter((id) => id !== property.id)
      : [...ids, property.id].slice(0, 3);
    localStorage.setItem('vestra_compare', JSON.stringify(next));
    setIsCompared(!isCompared);
  };

  // Use local CSS gradient placeholder — instant, no external requests
  const placeholderGradient = 'data:image/svg+xml,' + encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="400" viewBox="0 0 600 400">
      <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#ecfdf5"/><stop offset="100%" style="stop-color:#d1fae5"/>
      </linearGradient></defs>
      <rect width="600" height="400" fill="url(#g)"/>
      <text x="300" y="200" text-anchor="middle" dominant-baseline="central" font-family="sans-serif" font-size="24" font-weight="bold" fill="#059669">🏠 ${property.city || 'VESTRA'}</text>
    </svg>`
  );
  const mainImage = property.images?.[0] || placeholderGradient;

  const isNew = property.created_at && (Date.now() - new Date(property.created_at).getTime() < 7 * 24 * 60 * 60 * 1000);

  return (
    <Link
      href={`/properties/${property.id}`}
      className={cn('group block focus:outline-none', className)}
    >
      <article className={cn(
        'bg-white rounded-2xl border border-gray-100 shadow-card hover:shadow-card-hover hover:-translate-y-1 transition-all duration-300 overflow-hidden hover-card',
        borderAccentColor && `border-l-2 ${borderAccentColor}`
      )}>
        {/* Image Section */}
        <div className="relative h-52 bg-gray-50 overflow-hidden">
          {!imageLoaded && (
            <div className="absolute inset-0 skeleton" />
          )}
          <img
            src={mainImage}
            alt={property.title}
            loading="lazy"
            className={cn(
              'w-full h-full object-cover group-hover:scale-105 transition-transform duration-500',
              imageLoaded ? 'opacity-100' : 'opacity-0'
            )}
            onLoad={() => setImageLoaded(true)}
            onError={(e) => {
              (e.target as HTMLImageElement).src = placeholderGradient;
              setImageLoaded(true);
            }}
          />

          {/* Gradient overlay at bottom */}
          <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/30 to-transparent pointer-events-none" />

          {/* Top badges row */}
          <div className="absolute top-3 left-3 right-3 flex items-center justify-between">
            <span className={cn(
              'text-xs font-bold px-3 py-1.5 rounded-full backdrop-blur-sm shadow-sm',
              property.listing_type === 'sale'
                ? 'bg-blue-600/90 text-white'
                : property.listing_type === 'rent'
                ? 'bg-purple-600/90 text-white'
                : 'bg-gray-900/90 text-white'
            )}>
              {getListingTypeLabel(property.listing_type)}
            </span>

            <div className="flex items-center gap-1.5">
              {isNew && (
                <span className="text-xs font-semibold px-2.5 py-1.5 rounded-full bg-emerald-500/90 text-white backdrop-blur-sm shadow-sm flex items-center gap-1">
                  <Sparkles className="w-3 h-3" />
                  New
                </span>
              )}
              {property.is_verified && (
                <span className={cn(
                  'text-xs font-medium px-2 py-1.5 rounded-full backdrop-blur-sm shadow-sm flex items-center gap-1',
                  getBadgeColor(property.verification_badge)
                )}>
                  <ShieldCheck className="w-3 h-3" />
                  Verified
                </span>
              )}
            </div>
          </div>

          {/* Wishlist button */}
          <button
            onClick={async (e) => {
              e.preventDefault();
              e.stopPropagation();
              try {
                if (isLiked) {
                  await api.client.delete(`/api/favorites/${property.id}`);
                } else {
                  await api.client.post(`/api/favorites/${property.id}`);
                }
                setIsLiked(!isLiked);
              } catch {
                // If API fails (e.g., not authenticated), toggle locally
                setIsLiked(!isLiked);
              }
            }}
            className={cn(
              'absolute bottom-3 right-3 w-9 h-9 rounded-full flex items-center justify-center backdrop-blur-sm shadow-sm transition-all duration-200',
              isLiked
                ? 'bg-red-500 text-white scale-110'
                : 'bg-white/90 text-gray-600 hover:bg-white hover:scale-105'
            )}
            aria-label={isLiked ? 'Remove from favorites' : 'Add to favorites'}
          >
            <Heart className={cn('w-4 h-4 transition-all', isLiked && 'fill-white')} />
          </button>
        </div>

        {/* Content Section */}
        <div className="p-4">
          {/* Title */}
          <h3 className="font-semibold text-gray-900 text-sm leading-snug line-clamp-2 group-hover:text-emerald-700 transition-colors mb-1.5">
            {property.title}
          </h3>

          {/* Location */}
          <div className="flex items-center gap-1 text-gray-500 text-xs mb-3">
            <MapPin className="w-3 h-3 flex-shrink-0 text-gray-400" />
            <span className="truncate">{property.city}, {property.county}</span>
          </div>

          {/* Features row */}
          <div className="flex items-center gap-3 text-xs text-gray-500 mb-4">
            {property.bedrooms != null && property.bedrooms > 0 && (
              <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded-lg">
                <BedDouble className="w-3.5 h-3.5 text-gray-400" />
                <span className="font-medium text-gray-700">{property.bedrooms}</span>
                <span className="text-gray-400">bed</span>
              </span>
            )}
            {property.bathrooms != null && property.bathrooms > 0 && (
              <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded-lg">
                <Bath className="w-3.5 h-3.5 text-gray-400" />
                <span className="font-medium text-gray-700">{property.bathrooms}</span>
                <span className="text-gray-400">bath</span>
              </span>
            )}
            {property.size_sqft != null && property.size_sqft > 0 && (
              <span className="flex items-center gap-1.5 bg-gray-50 px-2 py-1 rounded-lg">
                <Maximize className="w-3.5 h-3.5 text-gray-400" />
                <span className="font-medium text-gray-700">{property.size_sqft.toLocaleString()}</span>
                <span className="text-gray-400">sqft</span>
              </span>
            )}
          </div>

          {/* Price + Trust Score */}
          <div className="flex items-end justify-between">
            <div>
              <p className="text-xl font-bold text-gray-900 leading-none">
                {formatCurrency(property.price, property.currency)}
              </p>
              {property.listing_type === 'rent' && (
                <span className="text-xs text-gray-400 font-medium">per month</span>
              )}
              {property.price_negotiable && (
                <span className="text-xs text-emerald-600 font-medium ml-2">Negotiable</span>
              )}
            </div>

            {trustScore && (
              <div className={cn(
                'flex items-center gap-1.5 px-2.5 py-1.5 rounded-xl',
                trustBg
              )}>
                <ShieldCheck className={cn('w-4 h-4', trustColor)} />
                <span className={cn('text-sm font-bold', trustColor)}>
                  {trustScore}
                </span>
              </div>
            )}
          </div>

          {/* AI Insight tags (from smart AI search) */}
          {(property as any).ai_trust_insight && (
            <div className="flex items-center gap-1.5 mt-2 pt-2 border-t border-gray-50 text-xs">
              <span className="flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-lg">
                <Sparkles className="w-3 h-3" />
                {(property as any).ai_trust_insight}
              </span>
              {(property as any).ai_price_tip && (
                <span className="px-2 py-1 bg-green-50 text-green-700 rounded-lg">
                  {(property as any).ai_price_tip}
                </span>
              )}
            </div>
          )}

          {/* Footer meta */}
          <div className="flex items-center gap-3 mt-3 pt-3 border-t border-gray-50 text-xs text-gray-400">
            <span className="flex items-center gap-1">
              <Eye className="w-3 h-3" />
              {property.views?.toLocaleString() || 0}
            </span>
            <span className="capitalize">{getPropertyTypeLabel(property.property_type)}</span>
            <button
              onClick={toggleCompare}
              className={`ml-auto flex items-center gap-1 px-2 py-1 rounded-lg font-medium transition-all ${
                isCompared
                  ? 'bg-emerald-50 text-emerald-600 border border-emerald-200'
                  : 'text-gray-400 hover:text-emerald-600 hover:bg-emerald-50'
              }`}
              title={isCompared ? 'Remove from comparison' : 'Add to comparison'}
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 17V7m0 10a2 2 0 01-2 2H5a2 2 0 01-2-2V7a2 2 0 012-2h2a2 2 0 012 2m0 10a2 2 0 002 2h2a2 2 0 002-2M9 7a2 2 0 012-2h2a2 2 0 012 2m0 10V7" />
              </svg>
              {isCompared ? 'Comparing' : 'Compare'}
            </button>
            {property.created_at && (
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                {formatTimeAgo(property.created_at)}
              </span>
            )}
          </div>
        </div>
      </article>
    </Link>
  );
}

export default React.memo(PropertyCard);

function formatTimeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  return `${months}mo ago`;
}
