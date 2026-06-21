'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Card, Progress, Badge } from '@/components/ui/card';
import { formatCurrency } from '@/lib/utils';
import api from '@/lib/api';
import { TrendingUp, DollarSign, BarChart3, Loader2 } from 'lucide-react';

interface ValuationData {
  estimated_value_kes: number;
  value_range_low: number;
  value_range_high: number;
  rental_estimate_monthly: number | null;
  rental_yield_percent: number | null;
  price_per_sqft: number;
  market_sentiment: string;
  confidence_level: string;
  investment_score: number;
  appreciation_forecast: { '1_year': string; '3_year': string; '5_year': string };
  key_value_drivers: string[];
  risk_factors: string[];
  valuation_summary: string;
}

interface Props {
  propertyId: number;
  submittedPrice: number;
}

export default function ValuationWidget({ propertyId, submittedPrice }: Props) {
  const [valuation, setValuation] = useState<ValuationData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runValuation = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.valuateProperty(propertyId);
      setValuation(data.valuation as unknown as ValuationData);
    } catch {
      setError('Valuation unavailable. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const sentimentColor = (s: string) =>
    s === 'bullish' ? 'success' : s === 'bearish' ? 'danger' : 'warning';

  const confidenceColor = (c: string) =>
    c === 'high' ? 'text-emerald-600' : c === 'medium' ? 'text-amber-600' : 'text-red-500';

  if (!valuation && !loading) {
    return (
      <Card className="border-dashed border-2 border-gray-200 text-center">
        <div className="py-6">
          <BarChart3 className="w-10 h-10 text-gray-300 mx-auto mb-3" />
          <h3 className="font-semibold text-gray-700 mb-1">AI Property Valuation</h3>
          <p className="text-sm text-gray-400 mb-4">
            Get an instant AI estimate of this property&apos;s market value, rental yield, and investment score.
          </p>
          <Button onClick={runValuation} variant="outline" size="sm">
            <TrendingUp className="w-4 h-4 mr-2" />
            Run Free Valuation
          </Button>
        </div>
      </Card>
    );
  }

  if (loading) {
    return (
      <Card className="text-center py-8">
        <Loader2 className="w-8 h-8 text-emerald-500 animate-spin mx-auto mb-3" />
        <p className="text-sm text-gray-500">Vestra AI is calculating market value...</p>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="text-center py-6">
        <p className="text-sm text-red-500 mb-3">{error}</p>
        <Button onClick={runValuation} variant="outline" size="sm">Retry</Button>
      </Card>
    );
  }

  if (!valuation) return null;

  const diff = valuation.estimated_value_kes - submittedPrice;
  const diffPct = submittedPrice > 0 ? ((diff / submittedPrice) * 100).toFixed(1) : '0';
  const isUndervalued = diff > 0;

  return (
    <Card>
      <div className="flex items-center justify-between mb-5">
        <h3 className="font-semibold text-gray-900 flex items-center gap-2">
          <TrendingUp className="w-4 h-4 text-emerald-600" />
          AI Valuation Report
        </h3>
        <Badge variant={sentimentColor(valuation.market_sentiment) as any}>
          {valuation.market_sentiment}
        </Badge>
      </div>

      {/* Main value */}
      <div className="bg-gray-50 rounded-xl p-4 mb-5 text-center">
        <p className="text-xs text-gray-500 mb-1">AI Estimated Value</p>
        <p className="text-3xl font-bold text-gray-900">
          {formatCurrency(valuation.estimated_value_kes)}
        </p>
        <p className="text-xs text-gray-400 mt-1">
          Range: {formatCurrency(valuation.value_range_low)} – {formatCurrency(valuation.value_range_high)}
        </p>
        {submittedPrice > 0 && (
          <p className={`text-xs font-medium mt-2 ${isUndervalued ? 'text-emerald-600' : 'text-red-500'}`}>
            {isUndervalued ? '↑' : '↓'} {Math.abs(parseFloat(diffPct))}%{' '}
            {isUndervalued ? 'below market — good deal' : 'above market — negotiate'}
          </p>
        )}
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-3 mb-5">
        <div className="bg-emerald-50 rounded-xl p-3">
          <p className="text-xs text-emerald-600 mb-1">Monthly Rent Est.</p>
          <p className="font-bold text-emerald-900 text-sm">
            {valuation.rental_estimate_monthly
              ? formatCurrency(valuation.rental_estimate_monthly)
              : '—'}
          </p>
        </div>
        <div className="bg-blue-50 rounded-xl p-3">
          <p className="text-xs text-blue-600 mb-1">Rental Yield</p>
          <p className="font-bold text-blue-900 text-sm">
            {valuation.rental_yield_percent
              ? `${valuation.rental_yield_percent}% p.a.`
              : '—'}
          </p>
        </div>
        <div className="bg-purple-50 rounded-xl p-3">
          <p className="text-xs text-purple-600 mb-1">Price per sqft</p>
          <p className="font-bold text-purple-900 text-sm">
            KES {valuation.price_per_sqft?.toLocaleString() ?? '—'}
          </p>
        </div>
        <div className="bg-amber-50 rounded-xl p-3">
          <p className="text-xs text-amber-600 mb-1">Confidence</p>
          <p className={`font-bold text-sm capitalize ${confidenceColor(valuation.confidence_level)}`}>
            {valuation.confidence_level}
          </p>
        </div>
      </div>

      {/* Investment score */}
      <div className="mb-5">
        <div className="flex justify-between text-xs text-gray-600 mb-1.5">
          <span className="font-medium">Investment Score</span>
          <span className="font-bold text-gray-900">{valuation.investment_score}/100</span>
        </div>
        <Progress value={valuation.investment_score} size="md" />
      </div>

      {/* Appreciation forecast */}
      <div className="mb-5">
        <p className="text-xs font-semibold text-gray-700 mb-2">Appreciation Forecast</p>
        <div className="grid grid-cols-3 gap-2">
          {[
            { period: '1 Year', value: valuation.appreciation_forecast['1_year'] },
            { period: '3 Years', value: valuation.appreciation_forecast['3_year'] },
            { period: '5 Years', value: valuation.appreciation_forecast['5_year'] },
          ].map(({ period, value }) => (
            <div key={period} className="text-center bg-gray-50 rounded-xl p-2">
              <p className="text-xs text-gray-500">{period}</p>
              <p className="text-sm font-bold text-emerald-600">+{value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Value drivers */}
      <div className="mb-4">
        <p className="text-xs font-semibold text-gray-700 mb-2">Value Drivers</p>
        <ul className="space-y-1.5">
          {valuation.key_value_drivers.map((d, i) => (
            <li key={i} className="text-xs text-gray-600 flex items-start gap-1.5">
              <span className="text-emerald-500 flex-shrink-0">↑</span>
              {d}
            </li>
          ))}
        </ul>
      </div>

      {/* Risk factors */}
      {valuation.risk_factors.length > 0 && (
        <div className="mb-4">
          <p className="text-xs font-semibold text-gray-700 mb-2">Risk Factors</p>
          <ul className="space-y-1.5">
            {valuation.risk_factors.map((r, i) => (
              <li key={i} className="text-xs text-amber-700 flex items-start gap-1.5">
                <span className="flex-shrink-0">⚠</span>
                {r}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Summary */}
      <div className="bg-blue-50 border border-blue-100 rounded-xl p-3">
        <p className="text-xs font-semibold text-blue-700 mb-1">Vestra AI Summary</p>
        <p className="text-xs text-blue-800 leading-relaxed">{valuation.valuation_summary}</p>
      </div>
    </Card>
  );
}
