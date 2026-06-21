'use client';

import { useState, useCallback } from 'react';
import { Card, Progress, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { formatCurrency, cn } from '@/lib/utils';
import api from '@/lib/api';
import type { VestimaEstimate } from '@/types';
import {
  TrendingUp, DollarSign, BarChart3, Loader2, ChevronDown, ChevronUp,
  MapPin, Home, ShieldCheck, Info, ArrowUpRight, ArrowDownRight, Minus,
  BrainCircuit, Building2, Ruler, Calendar, Layers, Sparkles,
} from 'lucide-react';

interface VestimaWidgetProps {
  propertyId: number;
  submittedPrice: number;
  /** Optional pre-loaded estimate from property detail response */
  initialEstimate?: VestimaEstimate | null;
}

export default function VestimaWidget({ propertyId, submittedPrice, initialEstimate }: VestimaWidgetProps) {
  const [vestima, setVestima] = useState<VestimaEstimate | null>(initialEstimate ?? null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showMethodology, setShowMethodology] = useState(false);
  const [showComparables, setShowComparables] = useState(false);

  const runEstimate = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getVestimaEstimate(propertyId);
      setVestima(data.vestima);
    } catch {
      setError('Vestima estimate unavailable. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [propertyId]);

  // ── Derived styles ─────────────────────────────────────────────────────

  const confidenceColor = (() => {
    if (!vestima) return 'bg-gray-200';
    const s = vestima.confidence_score;
    if (s >= 80) return 'bg-emerald-500';
    if (s >= 55) return 'bg-amber-500';
    return 'bg-red-500';
  })();

  const confidenceBg = (() => {
    if (!vestima) return 'bg-gray-50';
    const s = vestima.confidence_score;
    if (s >= 80) return 'bg-emerald-50 border-emerald-200';
    if (s >= 55) return 'bg-amber-50 border-amber-200';
    return 'bg-red-50 border-red-200';
  })();

  const trendIcon = (() => {
    if (!vestima) return null;
    switch (vestima.market_trend) {
      case 'appreciating': return <ArrowUpRight className="w-5 h-5 text-emerald-500" />;
      case 'declining': return <ArrowDownRight className="w-5 h-5 text-red-500" />;
      default: return <Minus className="w-5 h-5 text-gray-400" />;
    }
  })();

  const trendLabel = (() => {
    if (!vestima) return '';
    switch (vestima.market_trend) {
      case 'appreciating': return 'Appreciating';
      case 'declining': return 'Declining';
      default: return 'Stable';
    }
  })();

  const trendColor = (() => {
    if (!vestima) return 'text-gray-500';
    switch (vestima.market_trend) {
      case 'appreciating': return 'text-emerald-600';
      case 'declining': return 'text-red-600';
      default: return 'text-gray-500';
    }
  })();

  const priceDiffPct = (() => {
    if (!vestima || !submittedPrice) return null;
    const diff = vestima.estimated_value - submittedPrice;
    return ((diff / submittedPrice) * 100).toFixed(1);
  })();

  const isGoodDeal = priceDiffPct && parseFloat(priceDiffPct) > 0;
  const isOverpriced = priceDiffPct && parseFloat(priceDiffPct) < -5;

  // ── Idle state (no estimate loaded) ─────────────────────────────────────

  if (!vestima && !loading) {
    return (
      <Card className="border-dashed border-2 border-gray-200 text-center">
        <div className="py-6">
          <BrainCircuit className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <h3 className="font-semibold text-gray-700 mb-1">Vestima AI Price Estimate</h3>
          <p className="text-sm text-gray-400 mb-4">
            Get an AI-powered estimate of this property&apos;s fair market value, confidence range,
            comparable sales, and market trend — all powered by Vestra&apos;s own AI engine.
          </p>
          <Button onClick={runEstimate} variant="outline" size="sm">
            <Sparkles className="w-4 h-4 mr-2" />
            Run Vestima Estimate
          </Button>
        </div>
      </Card>
    );
  }

  // ── Loading state ───────────────────────────────────────────────────────

  if (loading) {
    return (
      <Card className="text-center py-8">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-500">Vestima AI is analyzing the market...</p>
        <div className="flex justify-center gap-1 mt-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="w-2 h-2 rounded-full bg-emerald-200 animate-bounce"
              style={{ animationDelay: `${i * 0.15}s` }} />
          ))}
        </div>
      </Card>
    );
  }

  // ── Error state ─────────────────────────────────────────────────────────

  if (error) {
    return (
      <Card className="text-center py-6">
        <p className="text-sm text-red-500 mb-3">{error}</p>
        <Button onClick={runEstimate} variant="outline" size="sm">Retry</Button>
      </Card>
    );
  }

  if (!vestima) return null;

  // ── Bar width calculation ───────────────────────────────────────────────

  const barMin = vestima.low_estimate;
  const barMax = vestima.high_estimate;
  const barRange = barMax - barMin;
  const estPct = barRange > 0 ? ((vestima.estimated_value - barMin) / barRange) * 100 : 50;
  const subPricePct = submittedPrice > 0 ? ((submittedPrice - barMin) / barRange) * 100 : null;

  return (
    <Card>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <BrainCircuit className="w-5 h-5 text-emerald-600" />
          Vestima AI Estimate
        </h3>
        <Badge variant="default" className="bg-emerald-50 text-emerald-700 border-emerald-200">
          <Sparkles className="w-3 h-3 mr-1" />
          AI Powered
        </Badge>
      </div>

      {/* Main value */}
      <div className={cn('rounded-xl p-4 mb-4 border', confidenceBg)}>
        <div className="flex items-center justify-between mb-2">
          <p className="text-xs text-gray-500 font-medium">AI Estimated Market Value</p>
          <div className="flex items-center gap-1.5">
            <span className={cn('w-2 h-2 rounded-full', confidenceColor)} />
            <span className={cn('text-xs font-semibold capitalize', confidenceColor.replace('bg-', 'text-'))}>
              {vestima.confidence_label} confidence
            </span>
          </div>
        </div>
        <p className="text-3xl font-bold text-gray-900">
          {formatCurrency(vestima.estimated_value)}
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Range: {formatCurrency(vestima.low_estimate)} &ndash; {formatCurrency(vestima.high_estimate)}
        </p>

        {/* Price comparison vs submitted */}
        {priceDiffPct && (
          <div className={cn(
            'mt-3 inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg',
            isGoodDeal
              ? 'bg-emerald-100 text-emerald-700'
              : isOverpriced
                ? 'bg-red-100 text-red-700'
                : 'bg-blue-100 text-blue-700',
          )}>
            {isGoodDeal ? <ArrowDownRight className="w-3 h-3" /> : <ArrowUpRight className="w-3 h-3" />}
            {isGoodDeal
              ? `${Math.abs(parseFloat(priceDiffPct))}% below estimated value — good deal`
              : `${Math.abs(parseFloat(priceDiffPct))}% above estimated value — negotiate`
            }
          </div>
        )}
      </div>

      {/* Confidence range bar */}
      <div className="mb-5">
        <div className="relative h-3 bg-gray-100 rounded-full overflow-hidden">
          <div
            className="absolute h-full bg-gradient-to-r from-emerald-200 via-emerald-400 to-emerald-500 rounded-full opacity-50"
            style={{ left: '5%', right: '5%' }}
          />
          {/* Submitted price marker */}
          {subPricePct != null && (
            <div
              className="absolute top-0 w-1 h-full bg-blue-600 rounded z-10"
              style={{ left: `${Math.max(0, Math.min(100, subPricePct))}%` }}
              title="Listed price"
            />
          )}
          {/* Estimated value marker */}
          <div
            className={cn(
              'absolute top-1/2 -translate-y-1/2 w-4 h-4 border-2 border-white rounded-full shadow-md z-20',
              confidenceColor,
            )}
            style={{ left: `calc(${Math.max(2, Math.min(98, estPct))}% - 8px)` }}
            title="Vestima estimate"
          />
        </div>
        <div className="flex justify-between text-[10px] text-gray-400 mt-1">
          <span>{formatCurrency(vestima.low_estimate)}</span>
          <span className="text-gray-500 font-medium">AI Range</span>
          <span>{formatCurrency(vestima.high_estimate)}</span>
        </div>
      </div>

      {/* Key metrics grid */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="bg-emerald-50 rounded-xl p-3">
          <p className="text-xs text-emerald-600 mb-1 flex items-center gap-1">
            <DollarSign className="w-3 h-3" /> Price / sqft
          </p>
          <p className="font-bold text-emerald-900 text-sm">
            {vestima.price_per_sqft
              ? `KES ${vestima.price_per_sqft.toLocaleString()}`
              : '—'}
          </p>
        </div>
        <div className="bg-blue-50 rounded-xl p-3">
          <p className="text-xs text-blue-600 mb-1 flex items-center gap-1">
            <TrendingUp className="w-3 h-3" /> Market Trend
          </p>
          <p className={cn('font-bold text-sm flex items-center gap-1', trendColor)}>
            {trendIcon}
            {trendLabel}
          </p>
        </div>
        <div className="bg-purple-50 rounded-xl p-3">
          <p className="text-xs text-purple-600 mb-1 flex items-center gap-1">
            <BarChart3 className="w-3 h-3" /> Confidence
          </p>
          <p className={cn('font-bold text-sm', confidenceColor.replace('bg-', 'text-'))}>
            {vestima.confidence_score}/100
          </p>
        </div>
        <div className="bg-amber-50 rounded-xl p-3">
          <p className="text-xs text-amber-600 mb-1 flex items-center gap-1">
            <Building2 className="w-3 h-3" /> Market Status
          </p>
          <p className="font-bold text-amber-900 text-sm capitalize">
            {vestima.market_status}
          </p>
        </div>
      </div>

      {/* Comparables */}
      {vestima.comparables.length > 0 && (
        <div className="mb-4">
          <button
            onClick={() => setShowComparables(!showComparables)}
            className="flex items-center justify-between w-full text-xs font-semibold text-gray-700 mb-2 hover:text-gray-900 transition-colors"
          >
            <span className="flex items-center gap-1.5">
              <Layers className="w-3.5 h-3.5" />
              Comparable Properties ({vestima.comparables.length})
            </span>
            {showComparables ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>
          {showComparables && (
            <div className="space-y-2">
              {vestima.comparables.map((cmp, i) => (
                <div key={i} className="flex items-center justify-between text-xs bg-gray-50 rounded-lg p-2.5">
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-800 truncate">{cmp.title}</p>
                    <p className="text-gray-400 flex items-center gap-1 mt-0.5">
                      <MapPin className="w-3 h-3" />
                      {cmp.location}
                      {cmp.distance_km != null && <span>&middot; {cmp.distance_km} km</span>}
                    </p>
                  </div>
                  <div className="text-right flex-shrink-0 ml-3">
                    <p className="font-semibold text-gray-900">{formatCurrency(cmp.price)}</p>
                    <p className="text-gray-400">
                      {cmp.bedrooms && `${cmp.bedrooms}br `}
                      {cmp.size_sqft && `${cmp.size_sqft.toLocaleString()} sqft`}
                    </p>
                  </div>
                  <div className="flex items-center gap-1 ml-3">
                    {cmp.is_verified && <ShieldCheck className="w-3 h-3 text-emerald-500" />}
                    <span className={cn(
                      'text-[10px] font-medium px-1.5 py-0.5 rounded',
                      cmp.relevance_score >= 85
                        ? 'bg-emerald-100 text-emerald-700'
                        : 'bg-gray-100 text-gray-500',
                    )}>
                      {cmp.relevance_score}%
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Methodology section */}
      <div className="mb-4">
        <button
          onClick={() => setShowMethodology(!showMethodology)}
          className="flex items-center justify-between w-full text-xs font-semibold text-gray-700 mb-2 hover:text-gray-900 transition-colors"
        >
          <span className="flex items-center gap-1.5">
            <Info className="w-3.5 h-3.5" />
            Methodology
          </span>
          {showMethodology ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
        </button>
        {showMethodology && (
          <div className="bg-gray-50 rounded-xl p-3 space-y-2 text-xs text-gray-600">
            <div className="flex items-start gap-2">
              <Building2 className="w-3.5 h-3.5 text-emerald-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-gray-800">City Price Baselines</span>
                <p>Market data from {vestima.comparables.length > 0 ? vestima.comparables[0]?.location?.split(',')[0] || 'the area' : 'Kenyan real estate'} establishes base price ranges for each property type.</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Calendar className="w-3.5 h-3.5 text-amber-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-gray-800">Depreciation Curves</span>
                <p>Properties older than 10 years are adjusted at ~0.8% per year of age, capped at 35% total depreciation.</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Layers className="w-3.5 h-3.5 text-blue-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-gray-800">Amenity Premiums</span>
                <p>Premium features (pool, gym, generator, solar) each add ~4% to the base value.</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Home className="w-3.5 h-3.5 text-purple-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-gray-800">Neighborhood Scoring</span>
                <p>Prime areas (Karen, Runda, Muthaiga) and growth corridors (Ruaka, Kitengela) receive location-based adjustments.</p>
              </div>
            </div>
            <div className="flex items-start gap-2">
              <Ruler className="w-3.5 h-3.5 text-green-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="font-medium text-gray-800">Comparable Analysis</span>
                <p>Similar active listings in the same area are scored by relevance (bedrooms, size, price proximity) to validate the estimate.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* AI Summary */}
      <div className="bg-gradient-to-br from-emerald-50 to-blue-50 border border-emerald-100 rounded-xl p-3">
        <p className="text-xs font-semibold text-emerald-700 mb-1 flex items-center gap-1.5">
          <BrainCircuit className="w-3.5 h-3.5" />
          Vestima AI Summary
        </p>
        <p className="text-xs text-gray-700 leading-relaxed">{vestima.valuation_summary}</p>
      </div>
    </Card>
  );
}
