'use client';

import { useMemo } from 'react';
import { useTranslations } from 'next-intl';
import { cn, getTrustScoreColor } from '@/lib/utils';
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  Badge,
  Progress,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import {
  Shield,
  UserCheck,
  FileText,
  Building2,
  Phone,
  Mail,
  CreditCard,
  TrendingUp,
  TrendingDown,
  Minus,
  Lightbulb,
  ChevronRight,
  AlertCircle,
  RefreshCw,
  ArrowUpRight,
  Clock,
  Target,
  Sparkles,
  BarChart3,
  Activity,
  Info,
} from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

interface TrustScoreCategory {
  id: string;
  label: string;
  score: number;
  maxScore: number;
  icon?: React.ReactNode;
  description: string;
  weight: number;
}

interface TrustScoreTrendPoint {
  date: string;
  score: number;
}

interface ImprovementSuggestion {
  id: string;
  category: string;
  description: string;
  impact: 'high' | 'medium' | 'low';
  effort: 'easy' | 'moderate' | 'hard';
  actionLabel: string;
  actionHref?: string;
}

interface TrustScorePanelProps {
  overallScore: number;
  categories: TrustScoreCategory[];
  trend?: TrustScoreTrendPoint[];
  suggestions?: ImprovementSuggestion[];
  isLoading?: boolean;
  error?: string | null;
  onRetry?: () => void;
  className?: string;
}

// ─── Category icons map ─────────────────────────────────────────────────────

const CATEGORY_ICONS: Record<string, React.ReactNode> = {
  identity: <UserCheck className="w-5 h-5" />,
  documents: <FileText className="w-5 h-5" />,
  property: <Building2 className="w-5 h-5" />,
  contact: <Phone className="w-5 h-5" />,
  email: <Mail className="w-5 h-5" />,
  payment: <CreditCard className="w-5 h-5" />,
  verification: <Shield className="w-5 h-5" />,
};

// ─── Helpers ────────────────────────────────────────────────────────────────

function getScoreBadgeVariant(score: number): 'success' | 'warning' | 'danger' {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'danger';
}

function getScoreLabel(score: number, t: (key: string) => string): string {
  if (score >= 90) return t('labels.excellent');
  if (score >= 80) return t('labels.veryGood');
  if (score >= 70) return t('labels.good');
  if (score >= 60) return t('labels.fair');
  if (score >= 40) return t('labels.poor');
  return t('labels.risky');
}

function getOverallEmoji(score: number): string {
  if (score >= 80) return '\u{1F31F}';
  if (score >= 60) return '\u{1F44D}';
  if (score >= 40) return '\u{26A0}\u{FE0F}';
  return '\u{274C}';
}

function formatTrendDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-KE', { month: 'short', day: 'numeric' });
}

function getTrendIcon(current: number, previous: number): React.ReactNode {
  const diff = current - previous;
  if (diff > 2) return <TrendingUp className="w-4 h-4 text-emerald-500" />;
  if (diff < -2) return <TrendingDown className="w-4 h-4 text-red-500" />;
  return <Minus className="w-4 h-4 text-gray-400" />;
}

function getImpactColor(impact: 'high' | 'medium' | 'low'): string {
  switch (impact) {
    case 'high': return 'bg-red-100 text-red-700 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800';
    case 'medium': return 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800';
    case 'low': return 'bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800';
  }
}

function getEffortLabel(effort: 'easy' | 'moderate' | 'hard'): string {
  switch (effort) {
    case 'easy': return 'Quick Win';
    case 'moderate': return 'Moderate';
    case 'hard': return 'Complex';
  }
}

function getEffortColor(effort: 'easy' | 'moderate' | 'hard'): string {
  switch (effort) {
    case 'easy': return 'bg-emerald-100 text-emerald-700 border-emerald-200 dark:bg-emerald-900/30 dark:text-emerald-400 dark:border-emerald-800';
    case 'moderate': return 'bg-amber-100 text-amber-700 border-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:border-amber-800';
    case 'hard': return 'bg-purple-100 text-purple-700 border-purple-200 dark:bg-purple-900/30 dark:text-purple-400 dark:border-purple-800';
  }
}

// ─── Sub-components ─────────────────────────────────────────────────────────

/** Circular gauge rendered in SVG for the overall score */
function OverallGauge({ score, size = 140, strokeWidth = 10 }: { score: number; size?: number; strokeWidth?: number }) {
  const radius = (size - strokeWidth * 2) / 2;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;

  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

  return (
    <div
      className="relative flex-shrink-0"
      style={{ width: size, height: size }}
      role="img"
      aria-label={`Trust score: ${Math.round(score)} out of 100`}
    >
      <svg
        width={size}
        height={size}
        className="transform -rotate-90"
        aria-hidden="true"
      >
        {/* Background */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth={strokeWidth}
          className="text-gray-200 dark:text-gray-700"
        />
        {/* Foreground */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 0.6s ease-out' }}
        />
      </svg>

      {/* Center content */}
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-sm" aria-hidden="true">{getOverallEmoji(score)}</span>
        <span className="text-3xl font-extrabold tabular-nums" style={{ color }}>
          {Math.round(score)}
        </span>
      </div>
    </div>
  );
}

/** Minimal sparkline SVG for trend data */
function TrendSparkline({ data, height = 48 }: { data: TrustScoreTrendPoint[]; height?: number }) {
  const width = 280;

  const { pathDefinition, points } = useMemo(() => {
    if (data.length < 2) return { pathDefinition: '', points: [] as { x: number; y: number }[] };

    const minScore = Math.min(...data.map((d) => d.score));
    const maxScore = Math.max(...data.map((d) => d.score));
    const range = Math.max(maxScore - minScore, 10);
    const padding = 4;
    const chartHeight = height - padding * 2;
    const chartWidth = width - padding * 2;
    const stepX = chartWidth / (data.length - 1);

    const pts = data.map((d, i) => ({
      x: padding + i * stepX,
      y: padding + chartHeight - ((d.score - minScore) / range) * chartHeight,
    }));

    const path = pts
      .map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`)
      .join(' ');

    return { pathDefinition: path, points: pts };
  }, [data, height]);

  if (data.length < 2) {
    return (
      <div className="flex items-center justify-center text-xs text-gray-400 py-2">
        <BarChart3 className="w-4 h-4 mr-1" />
        Insufficient data for trend
      </div>
    );
  }

  const latestScore = data[data.length - 1]?.score ?? 0;
  const previousScore = data.length >= 2 ? data[data.length - 2]?.score ?? 0 : 0;
  const trendDiff = latestScore - previousScore;

  return (
    <div className="flex flex-col" role="img" aria-label={`Trend chart: score went from ${previousScore} to ${latestScore}`}>
      <div className="relative" style={{ width, height }}>
        <svg width={width} height={height} aria-hidden="true">
          {/* Gradient fill under the line */}
          <defs>
            <linearGradient id="trend-fill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="rgb(16 185 129)" stopOpacity="0.25" />
              <stop offset="100%" stopColor="rgb(16 185 129)" stopOpacity="0.02" />
            </linearGradient>
          </defs>
          <path
            d={`${pathDefinition} L${points[points.length - 1]?.x ?? 0},${height} L${points[0]?.x ?? 0},${height} Z`}
            fill="url(#trend-fill)"
          />
          <path
            d={pathDefinition}
            fill="none"
            stroke={latestScore >= previousScore ? '#10b981' : '#ef4444'}
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
          {/* Latest point dot */}
          {points.length > 0 && (
            <circle
              cx={points[points.length - 1].x}
              cy={points[points.length - 1].y}
              r="3.5"
              fill={latestScore >= previousScore ? '#10b981' : '#ef4444'}
              stroke="white"
              strokeWidth="2"
            />
          )}
        </svg>
      </div>
      <div className="flex items-center justify-between mt-1 text-xs text-gray-500">
        <span>{formatTrendDate(data[0]?.date ?? '')}</span>
        <span className="font-medium">{formatTrendDate(data[data.length - 1]?.date ?? '')}</span>
      </div>
      <div className="flex items-center gap-1.5 mt-1 text-xs">
        {getTrendIcon(latestScore, previousScore)}
        <span className={cn(
          'font-semibold tabular-nums',
          trendDiff > 2 ? 'text-emerald-600 dark:text-emerald-400' : trendDiff < -2 ? 'text-red-600 dark:text-red-400' : 'text-gray-500'
        )}>
          {trendDiff > 0 ? '+' : ''}{Math.round(trendDiff)} pts
        </span>
        <span className="text-gray-400">this period</span>
      </div>
    </div>
  );
}

/** Category breakdown row */
function CategoryRow({ category }: { category: TrustScoreCategory }) {
  const pct = category.maxScore > 0 ? (category.score / category.maxScore) * 100 : 0;

  return (
    <div
      className="flex flex-col gap-1.5 py-3 first:pt-0 last:pb-0"
      role="group"
      aria-label={`${category.label}: ${Math.round(pct)}%`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 text-gray-400 dark:text-gray-500">
            {category.icon || CATEGORY_ICONS[category.id] || <Activity className="w-4 h-4" />}
          </span>
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">
            {category.label}
          </span>
          <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
            ({category.weight}%)
          </span>
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className={cn(
            'text-sm font-bold tabular-nums',
            getTrustScoreColor(Math.round(pct))
          )}>
            {Math.round(pct)}%
          </span>
          <Badge
            variant={getScoreBadgeVariant(pct)}
            className="hidden sm:inline-flex"
          >
            {pct >= 80 ? 'Verified' : pct >= 60 ? 'Partial' : 'Needs Work'}
          </Badge>
        </div>
      </div>
      <Progress
        value={pct}
        size="sm"
        color={pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'}
      />
      {category.description && (
        <p className="text-xs text-gray-500 dark:text-gray-400 pl-7 leading-relaxed">
          {category.description}
        </p>
      )}
    </div>
  );
}

/** Single improvement suggestion card */
function SuggestionCard({
  suggestion,
  translationPrefix,
}: {
  suggestion: ImprovementSuggestion;
  translationPrefix: string;
}) {
  return (
    <div
      className="group flex items-start gap-3 p-4 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 hover:border-emerald-200 dark:hover:border-emerald-800 hover:shadow-sm transition-all duration-200"
      role="listitem"
    >
      <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-amber-50 dark:bg-amber-900/30 flex items-center justify-center text-amber-600 dark:text-amber-400">
        <Lightbulb className="w-4.5 h-4.5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-start justify-between gap-2">
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
            {suggestion.description}
          </p>
          <ChevronRight className="w-4 h-4 text-gray-300 dark:text-gray-600 flex-shrink-0 mt-0.5 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
        <div className="flex flex-wrap items-center gap-2 mt-2">
          <span className={cn(
            'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border',
            getImpactColor(suggestion.impact)
          )}>
            {suggestion.impact === 'high' ? 'High Impact' : suggestion.impact === 'medium' ? 'Medium Impact' : 'Low Impact'}
          </span>
          <span className={cn(
            'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border',
            getEffortColor(suggestion.effort)
          )}>
            {getEffortLabel(suggestion.effort)}
          </span>
          <span className="text-[10px] text-gray-400 dark:text-gray-500 capitalize">
            {suggestion.category}
          </span>
        </div>
        <div className="mt-3">
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              if (suggestion.actionHref) {
                window.location.href = suggestion.actionHref;
              }
            }}
            rightIcon={<ArrowUpRight className="w-3 h-3" />}
          >
            {suggestion.actionLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Loading Skeleton ───────────────────────────────────────────────────────

function PanelSkeleton() {
  return (
    <div className="space-y-6 animate-pulse" aria-label="Loading trust score panel" role="status">
      {/* Overall gauge skeleton */}
      <Card>
        <CardContent className="flex flex-col sm:flex-row items-center gap-6">
          <Skeleton className="w-[140px] h-[140px] rounded-full" />
          <div className="flex-1 space-y-3 text-center sm:text-left">
            <Skeleton className="h-6 w-40 mx-auto sm:mx-0" />
            <Skeleton className="h-4 w-56 mx-auto sm:mx-0" />
            <Skeleton className="h-4 w-32 mx-auto sm:mx-0" />
          </div>
        </CardContent>
      </Card>

      {/* Category breakdown skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-36" />
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="h-4 w-12" />
                </div>
                <Skeleton className="h-2 w-full rounded-full" />
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Trend skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-28" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-[72px] w-full rounded-lg" />
        </CardContent>
      </Card>

      {/* Suggestions skeleton */}
      <Card>
        <CardHeader>
          <Skeleton className="h-5 w-40" />
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array.from({ length: 2 }).map((_, i) => (
              <div key={i} className="flex gap-3 p-4 border rounded-xl">
                <Skeleton className="w-9 h-9 rounded-lg flex-shrink-0" />
                <div className="flex-1 space-y-2">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-3 w-1/2" />
                  <Skeleton className="h-8 w-28 rounded-lg" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <span className="sr-only">Loading trust score panel...</span>
    </div>
  );
}

// ─── Empty State ────────────────────────────────────────────────────────────

function EmptyState({
  onRefresh,
}: {
  onRefresh?: () => void;
}) {
  return (
    <Card className="py-12">
      <div className="flex flex-col items-center text-center px-6">
        <div className="w-16 h-16 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center mb-4">
          <Shield className="w-8 h-8 text-gray-400 dark:text-gray-500" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
          No Trust Score Yet
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
          Complete identity verification and list your first property to generate your trust score.
          Higher scores unlock more visibility and buyer confidence.
        </p>
        {onRefresh && (
          <Button
            variant="primary"
            size="md"
            onClick={onRefresh}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Check Status
          </Button>
        )}
      </div>
    </Card>
  );
}

// ─── Error State ────────────────────────────────────────────────────────────

function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <Card className="py-10">
      <div className="flex flex-col items-center text-center px-6">
        <div className="w-14 h-14 rounded-2xl bg-red-50 dark:bg-red-900/20 flex items-center justify-center mb-4">
          <AlertCircle className="w-7 h-7 text-red-500" />
        </div>
        <h3 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">
          Unable to Load Trust Score
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 max-w-sm mb-6">
          {message}
        </p>
        {onRetry && (
          <Button
            variant="outline"
            size="md"
            onClick={onRetry}
            leftIcon={<RefreshCw className="w-4 h-4" />}
          >
            Try Again
          </Button>
        )}
      </div>
    </Card>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function TrustScorePanel({
  overallScore,
  categories,
  trend,
  suggestions,
  isLoading = false,
  error = null,
  onRetry,
  className,
}: TrustScorePanelProps) {
  const t = useTranslations('trust');

  // ── Loading state ───────────────────────────────────────────────────────
  if (isLoading) {
    return <PanelSkeleton />;
  }

  // ── Error state ─────────────────────────────────────────────────────────
  if (error) {
    return <ErrorState message={error} onRetry={onRetry} />;
  }

  // ── Empty state ─────────────────────────────────────────────────────────
  if (overallScore === 0 && categories.length === 0) {
    return <EmptyState onRefresh={onRetry} />;
  }

  // ── Score breakdown helpers ─────────────────────────────────────────────
  const scoreLabel = getScoreLabel(overallScore, t);

  const weakCategories = categories.filter((c) => {
    const pct = c.maxScore > 0 ? (c.score / c.maxScore) * 100 : 0;
    return pct < 60;
  });

  const topSuggestions = (suggestions ?? []).slice(0, 5);

  return (
    <div
      className={cn('space-y-6', className)}
      role="region"
      aria-label="Trust Score Panel"
    >
      {/* ── Score Overview Card ──────────────────────────────────────────── */}
      <Card>
        <CardContent className="flex flex-col sm:flex-row items-center gap-6">
          <OverallGauge score={overallScore} />

          <div className="flex-1 text-center sm:text-left space-y-1.5">
            <div className="flex items-center gap-2 justify-center sm:justify-start">
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">
                {t('title') || 'Trust Score'}
              </h2>
              <Badge variant={getScoreBadgeVariant(overallScore)}>
                {scoreLabel}
              </Badge>
            </div>

            <p className="text-sm text-gray-500 dark:text-gray-400">
              {overallScore >= 80
                ? (t('highScoreMessage') || 'Your profile demonstrates strong trust indicators. Buyers and sellers can transact with confidence.')
                : overallScore >= 60
                  ? (t('mediumScoreMessage') || 'Your trust profile is developing. Complete the suggested actions below to improve your score.')
                  : (t('lowScoreMessage') || 'Your trust score needs attention. Follow the improvement suggestions to unlock full platform features.')
              }
            </p>

            <div className="flex flex-wrap items-center gap-2 pt-1 justify-center sm:justify-start">
              <div className="flex items-center gap-1 text-xs text-gray-400 dark:text-gray-500">
                <Target className="w-3.5 h-3.5" />
                <span>
                  {categories.length} {t('categories') || 'categories'}
                </span>
              </div>
              {weakCategories.length > 0 && (
                <div className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
                  <AlertCircle className="w-3.5 h-3.5" />
                  <span>
                    {weakCategories.length} {t('needImprovement') || 'need improvement'}
                  </span>
                </div>
              )}
              {suggestions && suggestions.length > 0 && (
                <div className="flex items-center gap-1 text-xs text-emerald-600 dark:text-emerald-400">
                  <Lightbulb className="w-3.5 h-3.5" />
                  <span>
                    {suggestions.length} {t('suggestions') || 'suggestions'}
                  </span>
                </div>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ── Category Breakdown ───────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-gray-400" />
            <CardTitle>{t('categoryBreakdown') || 'Category Breakdown'}</CardTitle>
          </div>
          <Badge variant="default" className="text-xs">
            {Math.round(
              categories.reduce((sum, c) => sum + (c.maxScore > 0 ? (c.score / c.maxScore) * 100 * c.weight : 0), 0) /
                Math.max(categories.reduce((sum, c) => sum + c.weight, 0), 1)
            )}% weighted
          </Badge>
        </CardHeader>
        <CardContent>
          {categories.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <Activity className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {t('noCategories') || 'No category data available yet.'}
              </p>
            </div>
          ) : (
            <div className="divide-y divide-gray-100 dark:divide-gray-800" role="list" aria-label="Score categories">
              {categories.map((cat) => (
                <CategoryRow key={cat.id} category={cat} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Trend Chart ──────────────────────────────────────────────────── */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-5 h-5 text-gray-400" />
            <CardTitle>{t('scoreTrend') || 'Score Trend'}</CardTitle>
          </div>
          {trend && trend.length >= 2 && (
            <Badge variant="default" className="text-xs">
              {trend.length} {t('dataPoints') || 'data points'}
            </Badge>
          )}
        </CardHeader>
        <CardContent>
          {!trend || trend.length === 0 ? (
            <div className="flex flex-col items-center py-8 text-center">
              <Clock className="w-8 h-8 text-gray-300 dark:text-gray-600 mb-2" />
              <p className="text-sm text-gray-500 dark:text-gray-400">
                {t('noTrendData') || 'Trend data will appear as your trust score changes over time.'}
              </p>
            </div>
          ) : (
            <div className="flex justify-center sm:justify-start overflow-x-auto pb-2">
              <TrendSparkline data={trend} />
            </div>
          )}
        </CardContent>
      </Card>

      {/* ── Improvement Suggestions ──────────────────────────────────────── */}
      {topSuggestions.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-amber-500" />
              <CardTitle>{t('improvementSuggestions') || 'Improvement Suggestions'}</CardTitle>
            </div>
            <Badge variant="warning" className="text-xs">
              {topSuggestions.filter((s) => s.impact === 'high').length} {t('highImpact') || 'high impact'}
            </Badge>
          </CardHeader>
          <CardContent>
            <div
              className="space-y-3"
              role="list"
              aria-label="Improvement suggestions"
            >
              {topSuggestions.map((suggestion) => (
                <SuggestionCard
                  key={suggestion.id}
                  suggestion={suggestion}
                  translationPrefix={t('suggestion') || 'Suggestion'}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* ── Legend / Info Footer ─────────────────────────────────────────── */}
      <div
        className="flex flex-wrap items-center gap-x-6 gap-y-2 text-[11px] text-gray-400 dark:text-gray-500 px-1"
        aria-label="Legend"
      >
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-emerald-500" aria-hidden="true" />
          Strong (80-100)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-amber-500" aria-hidden="true" />
          Developing (60-79)
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" aria-hidden="true" />
          Needs Attention (0-59)
        </span>
        <span className="flex items-center gap-1.5">
          <Info className="w-3 h-3" aria-hidden="true" />
          Scores update every 24 hours
        </span>
      </div>
    </div>
  );
}

// ─── Public exports ─────────────────────────────────────────────────────────

export type { TrustScorePanelProps, TrustScoreCategory, TrustScoreTrendPoint, ImprovementSuggestion };
export { PanelSkeleton as TrustScorePanelSkeleton };
