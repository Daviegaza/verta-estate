'use client';

import { useEffect, useState, useRef } from 'react';
import { ShieldCheck, TrendingUp, AlertTriangle, Clock, CheckCircle2, ChevronRight, Lock } from 'lucide-react';

interface TrustScorePanelProps {
  trustScore: number;
  fraudRisk: number;
  ownershipConfidence: number;
  priceReasonableness: number;
  documentCompleteness: number;
  aiRecommendation: string;
  verificationBadge?: string;
  className?: string;
}

interface AnimatedRingProps {
  progress: number; // 0-1
  size: number;
  strokeWidth: number;
  color: string;
  bgColor: string;
  children?: React.ReactNode;
}

function AnimatedRing({ progress, size, strokeWidth, color, bgColor, children }: AnimatedRingProps) {
  const [currentProgress, setCurrentProgress] = useState(0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - currentProgress * circumference;
  const center = size / 2;

  useEffect(() => {
    const timer = setTimeout(() => setCurrentProgress(progress), 100);
    return () => clearTimeout(timer);
  }, [progress]);

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="transform -rotate-90">
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={bgColor}
          strokeWidth={strokeWidth}
        />
        <circle
          cx={center}
          cy={center}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="trust-ring"
          style={{ transition: 'stroke-dashoffset 1.5s cubic-bezier(0.16, 1, 0.3, 1)' }}
        />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        {children}
      </div>
    </div>
  );
}

function MetricBar({ label, value, color, icon: Icon }: { label: string; value: number; color: string; icon: typeof ShieldCheck }) {
  const [width, setWidth] = useState(0);
  const barRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setTimeout(() => setWidth(value / 100), 200);
          observer.disconnect();
        }
      },
      { threshold: 0.3 }
    );
    if (barRef.current) observer.observe(barRef.current);
    return () => observer.disconnect();
  }, [value]);

  const barColor = value >= 80 ? 'bg-emerald-500' : value >= 60 ? 'bg-amber-500' : 'bg-red-500';
  const textColor = value >= 80 ? 'text-emerald-600' : value >= 60 ? 'text-amber-600' : 'text-red-600';

  return (
    <div ref={barRef} className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon className={`w-3.5 h-3.5 ${textColor}`} />
          <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{label}</span>
        </div>
        <span className={`text-xs font-bold ${textColor}`}>{Math.round(value)}%</span>
      </div>
      <div className="h-1.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all duration-1000 ease-out ${barColor}`}
          style={{ width: `${width * 100}%`, transition: 'width 1.2s cubic-bezier(0.16, 1, 0.3, 1)' }}
        />
      </div>
    </div>
  );
}

export default function TrustScorePanel({
  trustScore,
  fraudRisk,
  ownershipConfidence,
  priceReasonableness,
  documentCompleteness,
  aiRecommendation,
  verificationBadge,
  className = '',
}: TrustScorePanelProps) {
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const getScoreColor = (score: number) => {
    if (score >= 80) return { ring: '#10b981', bg: '#d1fae5', label: 'Excellent', textColor: 'text-emerald-600', bgBadge: 'bg-emerald-50' };
    if (score >= 60) return { ring: '#f59e0b', bg: '#fef3c7', label: 'Good', textColor: 'text-amber-600', bgBadge: 'bg-amber-50' };
    return { ring: '#ef4444', bg: '#fee2e2', label: 'Caution', textColor: 'text-red-600', bgBadge: 'bg-red-50' };
  };

  const scoreInfo = getScoreColor(trustScore);
  const fraudReversed = 100 - fraudRisk;

  return (
    <div className={`gradient-border ${className}`}>
      <div className={`bg-white dark:bg-gray-900 rounded-2xl p-6 space-y-5 ${isVisible ? 'animate-fade-in-up' : 'opacity-0'}`}>
        {/* Header with Score Ring */}
        <div className="flex items-center gap-5">
          <div className="trust-glow rounded-full">
            <AnimatedRing progress={trustScore / 100} size={100} strokeWidth={7} color={scoreInfo.ring} bgColor={scoreInfo.bg}>
              <div className="text-center">
                <span className={`text-3xl font-bold ${scoreInfo.textColor}`}>{Math.round(trustScore)}</span>
                <span className={`block text-[10px] font-medium ${scoreInfo.textColor} -mt-0.5`}>/100</span>
              </div>
            </AnimatedRing>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold ${scoreInfo.bgBadge} ${scoreInfo.textColor}`}>
                <ShieldCheck className="w-3 h-3" />
                {scoreInfo.label} Trust Score
              </span>
              {verificationBadge && (
                <span className="trust-badge">
                  <CheckCircle2 className="w-3 h-3" />
                  {verificationBadge}
                </span>
              )}
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed line-clamp-3">
              {aiRecommendation}
            </p>
          </div>
        </div>

        {/* Metric Bars */}
        <div className="space-y-3">
          <MetricBar label="Ownership Confidence" value={ownershipConfidence} color="#10b981" icon={Lock} />
          <MetricBar label="Price Reasonableness" value={priceReasonableness} color="#f59e0b" icon={TrendingUp} />
          <MetricBar label="Document Completeness" value={documentCompleteness} color="#3b82f6" icon={CheckCircle2} />
          <MetricBar label="Fraud Safety" value={fraudReversed} color={fraudReversed >= 80 ? '#10b981' : '#ef4444'} icon={AlertTriangle} />
        </div>

        {/* Action */}
        <button className="w-full flex items-center justify-center gap-2 bg-emerald-500 hover:bg-emerald-600 text-white font-medium py-2.5 px-4 rounded-xl transition-all duration-200 hover:shadow-emerald-md group shine btn-premium">
          <span>View Full Trust Report</span>
          <ChevronRight className="w-4 h-4 group-hover:translate-x-0.5 transition-transform" />
        </button>

        {/* Timestamp */}
        <div className="flex items-center justify-center gap-1.5 text-xs text-gray-400">
          <Clock className="w-3 h-3" />
          <span>AI-verified in real-time • Powered by Vestra Trust Engine</span>
        </div>
      </div>
    </div>
  );
}

export { AnimatedRing, MetricBar };
