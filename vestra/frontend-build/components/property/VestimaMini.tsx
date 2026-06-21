'use client';

import { cn, formatCurrency } from '@/lib/utils';
import type { VestimaEstimate } from '@/types';
import { TrendingUp, Sparkles, ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface VestimaMiniProps {
  estimate: VestimaEstimate;
  submittedPrice?: number;
  className?: string;
}

export default function VestimaMini({ estimate, submittedPrice, className }: VestimaMiniProps) {
  const { estimated_value, low_estimate, high_estimate, confidence_score, confidence_label, market_trend } = estimate;

  const confidenceDot = confidence_score >= 80
    ? 'bg-emerald-500'
    : confidence_score >= 55
      ? 'bg-amber-500'
      : 'bg-red-500';

  const trendIcon = market_trend === 'appreciating'
    ? <ArrowUpRight className="w-3 h-3 text-emerald-500" />
    : market_trend === 'declining'
      ? <ArrowDownRight className="w-3 h-3 text-red-500" />
      : <Minus className="w-3 h-3 text-gray-400" />;

  const diffPct = submittedPrice && submittedPrice > 0
    ? ((estimated_value - submittedPrice) / submittedPrice * 100).toFixed(1)
    : null;

  const isGoodDeal = diffPct && parseFloat(diffPct) > 0;

  return (
    <div className={cn('bg-gradient-to-r from-emerald-50 to-blue-50 rounded-xl p-2.5 border border-emerald-100', className)}>
      {/* Header */}
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-semibold text-emerald-700 flex items-center gap-1">
          <Sparkles className="w-2.5 h-2.5" />
          Vestima AI
        </span>
        <div className="flex items-center gap-1">
          {trendIcon}
          <span className="text-[10px] capitalize text-gray-500">{market_trend}</span>
        </div>
      </div>

      {/* Value */}
      <p className="text-sm font-bold text-gray-900 leading-tight">
        {formatCurrency(estimated_value)}
      </p>
      <p className="text-[10px] text-gray-400">
        {formatCurrency(low_estimate)} &ndash; {formatCurrency(high_estimate)}
      </p>

      {/* Footer */}
      <div className="flex items-center justify-between mt-1.5 pt-1.5 border-t border-emerald-100">
        <div className="flex items-center gap-1.5">
          <span className={cn('w-1.5 h-1.5 rounded-full', confidenceDot)} />
          <span className="text-[10px] text-gray-500 capitalize">{confidence_label}</span>
          {diffPct && (
            <span className={cn(
              'text-[10px] font-medium',
              isGoodDeal ? 'text-emerald-600' : 'text-amber-600',
            )}>
              {isGoodDeal ? '-' : '+'}{Math.abs(parseFloat(diffPct))}%
            </span>
          )}
        </div>
        {estimate.price_per_sqft && (
          <span className="text-[10px] text-gray-400">
            KES {estimate.price_per_sqft.toLocaleString()}/sqft
          </span>
        )}
      </div>
    </div>
  );
}
