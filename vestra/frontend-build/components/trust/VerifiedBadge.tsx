'use client';

import * as React from 'react';
import { useTranslations } from 'next-intl';
import {
  Shield,
  Medal,
  Award,
  Trophy,
  Gem,
  HelpCircle,
  AlertCircle,
  XCircle,
  CheckCircle2,
  Clock,
  ExternalLink,
} from 'lucide-react';
import { cn, getBadgeColor } from '@/lib/utils';
import { Tooltip } from '@/components/ui/tooltip';
import { Skeleton } from '@/components/ui/skeleton';
import { Button } from '@/components/ui/button';
import { Modal, ModalBody } from '@/components/ui/modal';

// ─── Types ───────────────────────────────────────────────────────────────────

export type BadgeTier = 'bronze' | 'silver' | 'gold' | 'platinum';

export type VerificationStatus =
  | 'not_verified'
  | 'pending'
  | 'in_progress'
  | 'verified'
  | 'expired'
  | 'revoked';

export interface VerifiedBadgeData {
  /** Current badge tier level */
  tier: BadgeTier | null;
  /** Overall verification status */
  status: VerificationStatus;
  /** Numeric verification score (0-100) */
  score: number;
  /** When the verification was issued */
  verifiedAt?: string;
  /** When the verification expires */
  expiresAt?: string;
  /** Human-readable summary of what was verified */
  checks: VerificationCheck[];
  /** Optional URL to full verification report */
  reportUrl?: string;
}

export interface VerificationCheck {
  label: string;
  passed: boolean;
  detail?: string;
}

export interface VerifiedBadgeProps {
  /** Badge data, or null/undefined while loading */
  data: VerifiedBadgeData | null | undefined;
  /** Whether data is still being fetched */
  isLoading?: boolean;
  /** Error message if fetching failed */
  error?: string | null;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Show tier label next to the icon */
  showLabel?: boolean;
  /** Show inline as a compact badge (vs. interactive tooltip) */
  inline?: boolean;
  /** Additional class names */
  className?: string;
  /** Optional callback when the user clicks the badge for details */
  onViewDetails?: () => void;
}

// ─── Tier metadata ───────────────────────────────────────────────────────────

interface TierMeta {
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  minScore: number;
  descriptionKey: string;
  ariaLabelKey: string;
}

const TIER_MAP: Record<BadgeTier, TierMeta> = {
  bronze: {
    labelKey: 'verified_badge.tier_bronze',
    icon: Medal,
    minScore: 25,
    descriptionKey: 'verified_badge.tier_bronze_desc',
    ariaLabelKey: 'verified_badge.tier_bronze_aria',
  },
  silver: {
    labelKey: 'verified_badge.tier_silver',
    icon: Award,
    minScore: 50,
    descriptionKey: 'verified_badge.tier_silver_desc',
    ariaLabelKey: 'verified_badge.tier_silver_aria',
  },
  gold: {
    labelKey: 'verified_badge.tier_gold',
    icon: Trophy,
    minScore: 75,
    descriptionKey: 'verified_badge.tier_gold_desc',
    ariaLabelKey: 'verified_badge.tier_gold_aria',
  },
  platinum: {
    labelKey: 'verified_badge.tier_platinum',
    icon: Gem,
    minScore: 90,
    descriptionKey: 'verified_badge.tier_platinum_desc',
    ariaLabelKey: 'verified_badge.tier_platinum_aria',
  },
};

const STATUS_ICON: Record<VerificationStatus, React.ComponentType<{ className?: string }>> = {
  verified: CheckCircle2,
  pending: Clock,
  in_progress: Clock,
  not_verified: HelpCircle,
  expired: AlertCircle,
  revoked: XCircle,
};

const STATUS_COLORS: Record<VerificationStatus, string> = {
  verified: 'text-emerald-600 dark:text-emerald-400',
  pending: 'text-amber-600 dark:text-amber-400',
  in_progress: 'text-blue-600 dark:text-blue-400',
  not_verified: 'text-gray-400 dark:text-gray-500',
  expired: 'text-red-500 dark:text-red-400',
  revoked: 'text-red-600 dark:text-red-400',
};

// ─── Size scale helpers ──────────────────────────────────────────────────────

const ICON_SIZES = { sm: 'w-4 h-4', md: 'w-5 h-5', lg: 'w-7 h-7' } as const;
const TEXT_SIZES = { sm: 'text-xs', md: 'text-sm', lg: 'text-base' } as const;

// ─── Sub-components ──────────────────────────────────────────────────────────

/** Icon-only shield representing the badge tier */
function TierIcon({
  tier,
  size = 'md',
}: {
  tier: BadgeTier | null;
  size?: 'sm' | 'md' | 'lg';
}) {
  if (!tier) return <Shield className={cn('text-gray-400', ICON_SIZES[size])} aria-hidden="true" />;

  const meta = TIER_MAP[tier];
  const IconComponent = meta.icon;
  return <IconComponent className={cn(ICON_SIZES[size])} aria-hidden="true" />;
}

/** Colored dot indicator for check pass/fail */
function CheckDot({ passed }: { passed: boolean }) {
  return (
    <span
      className={cn(
        'inline-block w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1.5',
        passed
          ? 'bg-emerald-500 dark:bg-emerald-400'
          : 'bg-red-400 dark:bg-red-500'
      )}
      aria-hidden="true"
    />
  );
}

// ─── Tooltip content (extracted for reuse between interactive and modal) ─────

function BadgeTooltipContent({
  data,
  t,
  onViewDetails,
}: {
  data: VerifiedBadgeData;
  t: (key: string, values?: Record<string, unknown>) => string;
  onViewDetails?: () => void;
}) {
  const StatusIcon = STATUS_ICON[data.status];
  const passedCount = data.checks.filter((c) => c.passed).length;

  return (
    <div
      className="min-w-[220px] max-w-xs space-y-3"
      data-testid="badge-tooltip-content"
    >
      {/* Header: tier + status */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          {data.tier ? (
            <TierIcon tier={data.tier} size="sm" />
          ) : (
            <StatusIcon className={cn('w-4 h-4', STATUS_COLORS[data.status])} aria-hidden="true" />
          )}
          <div>
            <p className="text-xs font-semibold text-white dark:text-gray-100">
              {data.tier
                ? `${t(TIER_MAP[data.tier].labelKey)}`
                : t(`verified_badge.status_${data.status}`)}
            </p>
            {data.tier && (
              <p className="text-[10px] text-gray-300 dark:text-gray-400 mt-0.5">
                {t(TIER_MAP[data.tier].descriptionKey)}
              </p>
            )}
          </div>
        </div>
        <span
          className={cn(
            'text-[10px] font-medium px-1.5 py-0.5 rounded-full border',
            data.status === 'verified'
              ? 'bg-emerald-500/20 text-emerald-300 border-emerald-500/30'
              : data.status === 'pending' || data.status === 'in_progress'
              ? 'bg-amber-500/20 text-amber-300 border-amber-500/30'
              : data.status === 'expired' || data.status === 'revoked'
              ? 'bg-red-500/20 text-red-300 border-red-500/30'
              : 'bg-gray-500/20 text-gray-300 border-gray-500/30'
          )}
        >
          {t(`verified_badge.status_${data.status}`)}
        </span>
      </div>

      {/* Score bar */}
      {data.tier && (
        <div>
          <div className="flex justify-between text-[10px] text-gray-300 mb-1">
            <span>{t('verified_badge.trust_score')}</span>
            <span className="font-semibold">{data.score}%</span>
          </div>
          <div className="w-full h-1.5 bg-gray-700 rounded-full overflow-hidden">
            <div
              className={cn(
                'h-full rounded-full transition-all duration-500',
                data.score >= 75
                  ? 'bg-emerald-400'
                  : data.score >= 50
                  ? 'bg-amber-400'
                  : 'bg-red-400'
              )}
              style={{ width: `${data.score}%` }}
            />
          </div>
        </div>
      )}

      {/* Verification checks */}
      {data.checks.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mb-1.5">
            {t('verified_badge.checks', { count: passedCount, total: data.checks.length })}
          </p>
          <ul className="space-y-1" role="list">
            {data.checks.map((check, idx) => (
              <li
                key={idx}
                className="flex items-start gap-1.5 text-[10px]"
              >
                <CheckDot passed={check.passed} />
                <span
                  className={cn(
                    check.passed
                      ? 'text-gray-200'
                      : 'text-gray-400 line-through'
                  )}
                >
                  {check.label}
                  {check.detail && (
                    <span className="text-gray-500 ml-1">({check.detail})</span>
                  )}
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Timestamps */}
      {(data.verifiedAt || data.expiresAt) && (
        <div className="text-[10px] text-gray-400 space-y-0.5">
          {data.verifiedAt && (
            <p>
              {t('verified_badge.verified_at')}:{' '}
              {new Date(data.verifiedAt).toLocaleDateString('en-KE', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </p>
          )}
          {data.expiresAt && (
            <p>
              {t('verified_badge.expires_at')}:{' '}
              {new Date(data.expiresAt).toLocaleDateString('en-KE', {
                year: 'numeric',
                month: 'short',
                day: 'numeric',
              })}
            </p>
          )}
        </div>
      )}

      {/* Report link or details button */}
      {(data.reportUrl || onViewDetails) && (
        <div className="pt-1">
          {onViewDetails ? (
            <Button
              size="sm"
              variant="ghost"
              className="w-full text-[10px] text-emerald-300 hover:text-emerald-200 hover:bg-emerald-500/10 py-1 px-2 h-auto"
              onClick={(e) => {
                e.stopPropagation();
                onViewDetails();
              }}
            >
              {t('verified_badge.view_details')}
            </Button>
          ) : data.reportUrl ? (
            <a
              href={data.reportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[10px] text-emerald-300 hover:text-emerald-200 transition-colors"
            >
              {t('verified_badge.full_report')}
              <ExternalLink className="w-3 h-3" aria-hidden="true" />
            </a>
          ) : null}
        </div>
      )}
    </div>
  );
}

// ─── Main VerifiedBadge Component ────────────────────────────────────────────

export default function VerifiedBadge({
  data,
  isLoading = false,
  error = null,
  size = 'md',
  showLabel = true,
  inline = false,
  className,
  onViewDetails,
}: VerifiedBadgeProps) {
  const t = useTranslations();

  // ── Loading state ──────────────────────────────────────────────────────────

  if (isLoading) {
    if (inline) {
      return (
        <div
          className={cn('inline-flex items-center gap-2', className)}
          aria-busy="true"
          aria-label={t('verified_badge.loading')}
        >
          <Skeleton className={cn('rounded-full', ICON_SIZES[size])} />
          {showLabel && <Skeleton className={cn('h-3.5 w-20 rounded', TEXT_SIZES[size])} />}
        </div>
      );
    }

    return (
      <div
        className={cn(
          'inline-flex items-center gap-2 rounded-xl bg-gray-50 dark:bg-gray-800/50 border border-gray-100 dark:border-gray-800 px-3 py-1.5',
          className
        )}
        aria-busy="true"
        aria-label={t('verified_badge.loading')}
      >
        <Skeleton className={cn('rounded-full', ICON_SIZES[size])} />
        {showLabel && (
          <div className="flex flex-col gap-1">
            <Skeleton className="h-3 w-16 rounded" />
            <Skeleton className="h-2.5 w-10 rounded" />
          </div>
        )}
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────────

  if (error) {
    if (inline) {
      return (
        <div
          className={cn(
            'inline-flex items-center gap-1.5 text-red-600 dark:text-red-400',
            TEXT_SIZES[size],
            className
          )}
          role="alert"
          aria-label={t('verified_badge.error')}
        >
          <AlertCircle className={cn('flex-shrink-0', ICON_SIZES[size])} aria-hidden="true" />
          {showLabel && (
            <span className="text-xs font-medium">{t('verified_badge.error')}</span>
          )}
        </div>
      );
    }

    return (
      <div
        className={cn(
          'inline-flex items-center gap-2 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/30 px-3 py-1.5',
          className
        )}
        role="alert"
        aria-label={t('verified_badge.error')}
      >
        <XCircle className={cn('text-red-500 flex-shrink-0', ICON_SIZES[size])} aria-hidden="true" />
        {showLabel && (
          <div className="flex flex-col">
            <span className={cn('font-medium text-red-700 dark:text-red-300', TEXT_SIZES[size])}>
              {t('verified_badge.error')}
            </span>
            <span className="text-[10px] text-red-500 dark:text-red-400">
              {error}
            </span>
          </div>
        )}
      </div>
    );
  }

  // ── Empty / no data state ──────────────────────────────────────────────────

  if (!data) {
    if (inline) {
      return (
        <div
          className={cn(
            'inline-flex items-center gap-1.5 text-gray-400 dark:text-gray-500',
            TEXT_SIZES[size],
            className
          )}
          aria-label={t('verified_badge.not_verified')}
        >
          <HelpCircle className={cn('flex-shrink-0', ICON_SIZES[size])} aria-hidden="true" />
          {showLabel && (
            <span className="text-xs font-medium">
              {t('verified_badge.not_verified')}
            </span>
          )}
        </div>
      );
    }

    return (
      <div
        className={cn(
          'inline-flex items-center gap-2 rounded-xl bg-gray-50 dark:bg-gray-800/30 border border-dashed border-gray-200 dark:border-gray-700 px-3 py-1.5',
          className
        )}
        aria-label={t('verified_badge.not_verified')}
      >
        <Shield
          className={cn('text-gray-300 dark:text-gray-600', ICON_SIZES[size])}
          aria-hidden="true"
        />
        {showLabel && (
          <span className={cn('text-gray-400 dark:text-gray-500 font-medium', TEXT_SIZES[size])}>
            {t('verified_badge.not_verified')}
          </span>
        )}
      </div>
    );
  }

  // ── Badge tier color classes ───────────────────────────────────────────────

  const iconColorClass =
    data.tier === 'platinum'
      ? 'text-purple-600 dark:text-purple-400'
      : data.tier === 'gold'
      ? 'text-yellow-600 dark:text-yellow-400'
      : data.tier === 'silver'
      ? 'text-gray-500 dark:text-gray-300'
      : data.tier === 'bronze'
      ? 'text-orange-600 dark:text-orange-400'
      : STATUS_COLORS[data.status];

  // ── Inline badge variant ───────────────────────────────────────────────────

  if (inline) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1.5',
          TEXT_SIZES[size],
          iconColorClass,
          className
        )}
        aria-label={
          data.tier
            ? `${t(TIER_MAP[data.tier].labelKey)} — ${t('verified_badge.status_verified')}`
            : t(`verified_badge.status_${data.status}`)
        }
        role="status"
      >
        {data.tier ? (
          <TierIcon tier={data.tier} size={size} />
        ) : (
          (() => {
            const SIcon = STATUS_ICON[data.status];
            return <SIcon className={cn(STATUS_COLORS[data.status])} aria-hidden="true" />;
          })()
        )}
        {showLabel && (
          <span className="font-medium">
            {data.tier
              ? t(TIER_MAP[data.tier].labelKey)
              : t(`verified_badge.status_${data.status}`)}
          </span>
        )}
      </span>
    );
  }

  // ── Interactive badge with tooltip ─────────────────────────────────────────

  /**
   * Determine the ARIA label based on verification data for accessibility.
   */
  const ariaLabel = data.tier
    ? `${t(TIER_MAP[data.tier].labelKey)} — ${t('verified_badge.status_verified')}`
    : t(`verified_badge.status_${data.status}`);

  const passedChecks = data.checks.filter((c) => c.passed).length;

  return (
    <Tooltip
      content={
        <BadgeTooltipContent
          data={data}
          t={t as (key: string, values?: Record<string, unknown>) => string}
          onViewDetails={onViewDetails}
        />
      }
      position="bottom"
      delay={300}
      contentClassName="p-3 bg-gray-900 dark:bg-gray-800 border border-gray-700 dark:border-gray-600 rounded-xl shadow-xl"
      className={cn('inline-flex', className)}
      disabled={inline}
    >
      <button
        type="button"
        className={cn(
          'inline-flex items-center gap-1.5 rounded-xl border px-2.5 py-1',
          'transition-all duration-200 cursor-default',
          'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2',
          'dark:focus:ring-offset-gray-900',
          data.tier
            ? getBadgeColor(data.tier)
            : 'bg-gray-50 dark:bg-gray-800/30 border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500',
          TEXT_SIZES[size]
        )}
        aria-label={ariaLabel}
        aria-describedby={data.tier ? `badge-desc-${data.tier}` : undefined}
        tabIndex={0}
      >
        {data.tier ? (
          <TierIcon tier={data.tier} size={size} />
        ) : (
          (() => {
            const SIcon = STATUS_ICON[data.status];
            return <SIcon className={cn('w-4 h-4', STATUS_COLORS[data.status])} aria-hidden="true" />;
          })()
        )}
        {showLabel && (
          <span className="font-semibold">
            {data.tier
              ? t(TIER_MAP[data.tier].labelKey)
              : t(`verified_badge.status_${data.status}`)}
          </span>
        )}
        {data.tier && (
          <span className="sr-only" id={`badge-desc-${data.tier}`}>
            {t(TIER_MAP[data.tier].descriptionKey)}. {t('verified_badge.checks', { count: passedChecks, total: data.checks.length })}{' '}
            {t('verified_badge.trust_score')}: {data.score}%
          </span>
        )}
      </button>
    </Tooltip>
  );
}

// ─── Detail Modal ────────────────────────────────────────────────────────────

interface VerifiedBadgeModalProps {
  data: VerifiedBadgeData;
  isOpen: boolean;
  onClose: () => void;
}

/**
 * Modal that shows the full verification breakdown.
 * Useful for user profiles or property detail pages.
 */
export function VerifiedBadgeModal({ data, isOpen, onClose }: VerifiedBadgeModalProps) {
  const t = useTranslations();
  const passedCount = data.checks.filter((c) => c.passed).length;
  const StatusIcon = data.tier ? TIER_MAP[data.tier].icon : STATUS_ICON[data.status];

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={t('verified_badge.detail_title')} size="md">
      <ModalBody>
        <div className="space-y-6">
          {/* Tier header */}
          <div className="text-center">
            <div
              className={cn(
                'inline-flex items-center justify-center w-16 h-16 rounded-2xl mb-3',
                data.tier === 'platinum'
                  ? 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'
                  : data.tier === 'gold'
                  ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-600 dark:text-yellow-400'
                  : data.tier === 'silver'
                  ? 'bg-gray-100 dark:bg-gray-800 text-gray-500 dark:text-gray-300'
                  : data.tier === 'bronze'
                  ? 'bg-orange-100 dark:bg-orange-900/30 text-orange-600 dark:text-orange-400'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-400 dark:text-gray-500'
              )}
            >
              <StatusIcon className="w-8 h-8" aria-hidden="true" />
            </div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {data.tier
                ? t(TIER_MAP[data.tier].labelKey)
                : t(`verified_badge.status_${data.status}`)}
            </h3>
            {data.tier && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {t(TIER_MAP[data.tier].descriptionKey)}
              </p>
            )}
          </div>

          {/* Score */}
          {data.tier && (
            <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
              <div className="flex justify-between items-center mb-1.5">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('verified_badge.trust_score')}
                </span>
                <span
                  className={cn(
                    'text-sm font-bold',
                    data.score >= 75
                      ? 'text-emerald-600 dark:text-emerald-400'
                      : data.score >= 50
                      ? 'text-amber-600 dark:text-amber-400'
                      : 'text-red-600 dark:text-red-400'
                  )}
                >
                  {data.score}%
                </span>
              </div>
              <div className="w-full h-2.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                <div
                  className={cn(
                    'h-full rounded-full transition-all duration-700',
                    data.score >= 75
                      ? 'bg-emerald-500'
                      : data.score >= 50
                      ? 'bg-amber-500'
                      : 'bg-red-500'
                  )}
                  style={{ width: `${data.score}%` }}
                />
              </div>
            </div>
          )}

          {/* Checks */}
          <div>
            <h4 className="text-sm font-semibold text-gray-900 dark:text-gray-100 mb-3">
              {t('verified_badge.verification_checks')}
              <span className="ml-1.5 text-xs font-normal text-gray-500">
                ({passedCount}/{data.checks.length})
              </span>
            </h4>
            <ul className="space-y-2" role="list">
              {data.checks.map((check, idx) => (
                <li
                  key={idx}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-xl border',
                    check.passed
                      ? 'bg-emerald-50 dark:bg-emerald-900/10 border-emerald-100 dark:border-emerald-800/20'
                      : 'bg-red-50 dark:bg-red-900/10 border-red-100 dark:border-red-800/20'
                  )}
                >
                  {check.passed ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                  ) : (
                    <XCircle className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" aria-hidden="true" />
                  )}
                  <div>
                    <p
                      className={cn(
                        'text-sm font-medium',
                        check.passed
                          ? 'text-emerald-800 dark:text-emerald-200'
                          : 'text-red-800 dark:text-red-200'
                      )}
                    >
                      {check.label}
                    </p>
                    {check.detail && (
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {check.detail}
                      </p>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {/* Timestamps */}
          {(data.verifiedAt || data.expiresAt) && (
            <div className="flex flex-col sm:flex-row gap-3 text-xs text-gray-500 dark:text-gray-400">
              {data.verifiedAt && (
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>
                    <strong>{t('verified_badge.verified_at')}:</strong>{' '}
                    {new Date(data.verifiedAt).toLocaleDateString('en-KE', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </span>
                </div>
              )}
              {data.expiresAt && (
                <div className="flex items-center gap-1.5">
                  <Clock className="w-3.5 h-3.5" aria-hidden="true" />
                  <span>
                    <strong>{t('verified_badge.expires_at')}:</strong>{' '}
                    {new Date(data.expiresAt).toLocaleDateString('en-KE', {
                      year: 'numeric',
                      month: 'long',
                      day: 'numeric',
                    })}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Full report link */}
          {data.reportUrl && (
            <a
              href={data.reportUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm font-medium text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors"
            >
              {t('verified_badge.full_report')}
              <ExternalLink className="w-4 h-4" aria-hidden="true" />
            </a>
          )}
        </div>
      </ModalBody>
    </Modal>
  );
}

// ─── Helper: determine tier from score ───────────────────────────────────────

/**
 * Determine the appropriate badge tier from a numeric trust score.
 * Returns `null` if the score is below the minimum threshold (25).
 */
export function getTierFromScore(score: number): BadgeTier | null {
  if (score >= 90) return 'platinum';
  if (score >= 75) return 'gold';
  if (score >= 50) return 'silver';
  if (score >= 25) return 'bronze';
  return null;
}

/**
 * Get the minimum score required for a given badge tier.
 */
export function getMinScoreForTier(tier: BadgeTier): number {
  return TIER_MAP[tier].minScore;
}

/**
 * Return the human-readable label key for a given badge tier.
 */
export function getTierLabelKey(tier: BadgeTier): string {
  return TIER_MAP[tier].labelKey;
}

/**
 * Return the human-readable description key for a given badge tier.
 */
export function getTierDescriptionKey(tier: BadgeTier): string {
  return TIER_MAP[tier].descriptionKey;
}
