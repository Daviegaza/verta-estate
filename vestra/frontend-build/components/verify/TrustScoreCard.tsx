'use client';

import { cn, getTrustScoreColor, getTrustScoreBg } from '@/lib/utils';
import { Progress } from '@/components/ui/card';
import TrustScoreGauge from '@/components/verify/TrustScoreGauge';
import { ShieldCheck, ShieldAlert, ShieldX, Shield } from 'lucide-react';
import type { Verification } from '@/types';

interface TrustScoreCardProps {
  verification: Verification;
  compact?: boolean;
}

export default function TrustScoreCard({ verification, compact = false }: TrustScoreCardProps) {
  const score = verification.trust_score || 0;
  const riskScore = verification.fraud_risk_score || 0;

  const getStatusIcon = () => {
    switch (verification.ai_recommendation) {
      case 'approve': return <ShieldCheck className="w-6 h-6 text-emerald-600" />;
      case 'review': return <ShieldAlert className="w-6 h-6 text-amber-600" />;
      case 'reject': return <ShieldX className="w-6 h-6 text-red-600" />;
      default: return <Shield className="w-6 h-6 text-gray-400" />;
    }
  };

  const statusColors = {
    approve: 'bg-emerald-50 border-emerald-200',
    review: 'bg-amber-50 border-amber-200',
    reject: 'bg-red-50 border-red-200',
    pending: 'bg-gray-50 border-gray-200',
  };

  const rec = verification.ai_recommendation || 'pending';
  const bgColor = statusColors[rec as keyof typeof statusColors] || statusColors.pending;

  if (compact) {
    return (
      <div className={cn('p-3 rounded-xl border flex items-center gap-3', bgColor)}>
        {getStatusIcon()}
        <div>
          <p className="text-sm font-semibold text-gray-900">
            Trust Score: <span className={getTrustScoreColor(score)}>{Math.round(score)}%</span>
          </p>
          <p className="text-xs text-gray-500 capitalize">{rec}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-gray-100 shadow-sm overflow-hidden">
      {/* Header */}
      <div className={cn('p-5 border-b', bgColor)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {getStatusIcon()}
            <div>
              <h3 className="font-semibold text-gray-900 text-lg">AI Verification Report</h3>
              <p className="text-xs text-gray-600 capitalize">
                Status: <strong>{verification.status.replace('_', ' ')}</strong>
              </p>
            </div>
          </div>
          <div className="flex-shrink-0">
            <TrustScoreGauge score={score} size={80} showLabel={true} />
          </div>
        </div>
      </div>

      <div className="p-5 space-y-4">
        {/* Score bars */}
        <div className="space-y-3">
          <div>
            <div className="flex justify-between text-xs text-gray-700 mb-1 font-medium">
              <span>Trust Score</span>
              <span className={cn('font-bold', getTrustScoreColor(score))}>{Math.round(score)}%</span>
            </div>
            <Progress value={score} size="md" />
          </div>
          <div>
            <div className="flex justify-between text-xs text-gray-700 mb-1 font-medium">
              <span>Fraud Risk</span>
              <span className={cn('font-semibold', riskScore > 60 ? 'text-red-600' : riskScore > 30 ? 'text-amber-600' : 'text-emerald-600')}>
                {Math.round(riskScore)}%
              </span>
            </div>
            <Progress value={riskScore} size="md" color={riskScore > 60 ? 'bg-red-500' : riskScore > 30 ? 'bg-amber-500' : 'bg-emerald-500'} />
          </div>
        </div>

        {/* Key metrics */}
        <div className="grid grid-cols-3 gap-3">
          {[
            { label: 'Price', value: verification.price_reasonableness || '—', colors: { under: 'text-blue-600', fair: 'text-emerald-600', over: 'text-red-500' } },
            { label: 'Ownership', value: verification.ownership_confidence || '—', colors: { high: 'text-emerald-600', medium: 'text-amber-600', low: 'text-red-500' } },
            { label: 'Decision', value: verification.ai_recommendation || '—', colors: { approve: 'text-emerald-600', review: 'text-amber-600', reject: 'text-red-500' } },
          ].map(({ label, value, colors }) => (
            <div key={label} className="bg-gray-100 rounded-xl p-3 text-center border border-gray-200">
              <p className="text-xs text-gray-600 mb-1 font-medium">{label}</p>
              <p className={cn('text-sm font-bold capitalize', (colors as unknown as Record<string, string>)[value] || 'text-gray-900')}>
                {value}
              </p>
            </div>
          ))}
        </div>

        {/* AI Summary */}
        {verification.ai_summary && (
          <div className="bg-blue-50 border border-blue-100 rounded-xl p-4">
            <p className="text-xs font-semibold text-blue-700 mb-1">AI Analysis Summary</p>
            <p className="text-sm text-blue-900 leading-relaxed">{verification.ai_summary}</p>
          </div>
        )}

        {/* Document flags */}
        {verification.document_flags && verification.document_flags.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-gray-700 mb-2">⚠️ Flags Found</p>
            <ul className="space-y-1.5">
              {verification.document_flags.map((flag, i) => (
                <li key={i} className="text-xs text-red-700 bg-red-50 border border-red-100 rounded-lg px-3 py-2 flex items-start gap-2">
                  <span className="flex-shrink-0 mt-0.5">•</span>
                  {flag}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
