'use client';

import * as React from 'react';
import { useTranslations } from 'next-intl';
import {
  Badge,
  Card,
  CardContent,
  Progress,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton, SkeletonText } from '@/components/ui/skeleton';
import { cn, formatRelativeTime } from '@/lib/utils';
import {
  ShieldCheck,
  ShieldX,
  Shield,
  Phone,
  Mail,
  IdCard,
  ScrollText,
  UserCheck,
  Building2,
  PhoneOff,
  MailX,
  Loader2,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  Clock,
  Award,
  BadgeCheck,
  Star,
  MessageCircle,
  Eye,
} from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

export type SellerIdentityStatus = 'verified' | 'pending' | 'rejected' | 'not_submitted';

export type SellerLicenseStatus = 'verified' | 'pending' | 'rejected' | 'none';

export type ContactVerifiedStatus = 'verified' | 'unverified';

export interface SellerVerificationData {
  /** Unique identifier for the seller */
  sellerId: number;
  /** Seller display name */
  sellerName: string;
  /** URL or path to seller avatar */
  avatarUrl?: string;
  /** Whether the seller is a registered agent */
  isAgent: boolean;
  /** Agency name if applicable */
  agencyName?: string;
  /** KYC / identity verification status */
  identityStatus: SellerIdentityStatus;
  /** Professional license verification status */
  licenseStatus: SellerLicenseStatus;
  /** License type (e.g. 'Estate Agent', 'Property Manager') */
  licenseType?: string;
  /** License number */
  licenseNumber?: string;
  /** Whether the seller's phone number is verified */
  phoneVerified: ContactVerifiedStatus;
  /** Seller's phone number (masked) */
  phoneNumber?: string;
  /** Whether the seller's email is verified */
  emailVerified: ContactVerifiedStatus;
  /** Seller's email (masked) */
  email?: string;
  /** Overall trust score (0-100) */
  trustScore?: number;
  /** Verification badges earned */
  badges?: string[];
  /** Total number of listings by this seller */
  totalListings?: number;
  /** Active listings count */
  activeListings?: number;
  /** Member since date string */
  memberSince?: string;
  /** Average response time string (e.g. '< 1 hour') */
  responseTime?: string;
  /** Total number of completed transactions */
  completedTransactions?: number;
  /** Verification expiry date */
  verificationExpiresAt?: string;
}

export interface SellerVerificationCardProps {
  /** Seller verification data */
  data?: SellerVerificationData | null;
  /** Whether data is currently loading */
  isLoading?: boolean;
  /** Error message if fetching failed */
  error?: string | null;
  /** Compact variant for sidebar / listing cards */
  compact?: boolean;
  /** Additional class names */
  className?: string;
  /** Callback when "Contact Seller" is clicked */
  onContact?: (sellerId: number) => void;
  /** Callback when "View Listings" is clicked */
  onViewListings?: (sellerId: number) => void;
  /** Callback when user requests identity re-verification */
  onRequestReVerification?: (sellerId: number) => void;
}

// ─── Helper functions ───────────────────────────────────────────────────────

function getIdentityIcon(status: SellerIdentityStatus): React.ReactNode {
  switch (status) {
    case 'verified':
      return <UserCheck className="w-5 h-5 text-emerald-600" aria-hidden="true" />;
    case 'pending':
      return <Clock className="w-5 h-5 text-amber-600" aria-hidden="true" />;
    case 'rejected':
      return <ShieldX className="w-5 h-5 text-red-600" aria-hidden="true" />;
    case 'not_submitted':
      return <IdCard className="w-5 h-5 text-gray-400" aria-hidden="true" />;
  }
}

function getIdentityBadgeVariant(status: SellerIdentityStatus): 'success' | 'warning' | 'danger' | 'default' {
  switch (status) {
    case 'verified':
      return 'success';
    case 'pending':
      return 'warning';
    case 'rejected':
      return 'danger';
    case 'not_submitted':
      return 'default';
  }
}

function getIdentityLabel(status: SellerIdentityStatus, t: (key: string) => string): string {
  switch (status) {
    case 'verified':
      return t('identity.verified');
    case 'pending':
      return t('identity.pending');
    case 'rejected':
      return t('identity.rejected');
    case 'not_submitted':
      return t('identity.notSubmitted');
  }
}

function getLicenseIcon(status: SellerLicenseStatus): React.ReactNode {
  switch (status) {
    case 'verified':
      return <ScrollText className="w-5 h-5 text-emerald-600" aria-hidden="true" />;
    case 'pending':
      return <Clock className="w-5 h-5 text-amber-600" aria-hidden="true" />;
    case 'rejected':
      return <ShieldX className="w-5 h-5 text-red-600" aria-hidden="true" />;
    case 'none':
      return <ScrollText className="w-5 h-5 text-gray-400" aria-hidden="true" />;
  }
}

function getContactIcon(verified: ContactVerifiedStatus): React.ReactNode {
  return verified === 'verified'
    ? <Check className="w-4 h-4 text-emerald-600" aria-hidden="true" />
    : <X className="w-4 h-4 text-red-400" aria-hidden="true" />;
}

function getTrustScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-amber-600';
  return 'text-red-600';
}

function getTrustScoreBg(score: number): string {
  if (score >= 80) return 'bg-emerald-50 dark:bg-emerald-900/20';
  if (score >= 60) return 'bg-amber-50 dark:bg-amber-900/20';
  return 'bg-red-50 dark:bg-red-900/20';
}

function getTrustScoreLabel(score: number, t: (key: string) => string): string {
  if (score >= 90) return t('trustScore.excellent');
  if (score >= 75) return t('trustScore.good');
  if (score >= 50) return t('trustScore.fair');
  if (score >= 30) return t('trustScore.poor');
  return t('trustScore.risky');
}

function maskPhone(phone?: string): string {
  if (!phone) return '';
  if (phone.length < 6) return phone;
  return phone.slice(0, 3) + '****' + phone.slice(-3);
}

function maskEmail(email?: string): string {
  if (!email) return '';
  const [local, domain] = email.split('@');
  if (!local || !domain) return email;
  const maskedLocal = local.length > 2
    ? local[0] + '****' + local[local.length - 1]
    : local[0] + '****';
  return `${maskedLocal}@${domain}`;
}

// ─── Loading Skeleton ───────────────────────────────────────────────────────

function LoadingSkeleton({ compact }: { compact?: boolean }) {
  if (compact) {
    return (
      <div
        className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 space-y-3 shadow-sm"
        aria-label="Loading seller verification"
      >
        <div className="flex items-center gap-3">
          <Skeleton className="w-12 h-12 rounded-full flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-4 w-28 rounded-md" />
            <Skeleton className="h-3 w-20 rounded-md" />
          </div>
        </div>
        <Skeleton className="h-3 w-full rounded-md" />
        <Skeleton className="h-3 w-3/4 rounded-md" />
      </div>
    );
  }

  return (
    <div
      className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden shadow-sm"
      aria-label="Loading seller verification"
    >
      {/* Header skeleton */}
      <div className="p-5 border-b border-gray-100 dark:border-gray-800">
        <div className="flex items-center gap-3">
          <Skeleton className="w-14 h-14 rounded-full flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-40 rounded-md" />
            <Skeleton className="h-3.5 w-24 rounded-md" />
          </div>
          <Skeleton className="h-8 w-20 rounded-xl" />
        </div>
      </div>

      {/* Body skeleton */}
      <div className="p-5 space-y-5">
        {/* Trust score bar skeleton */}
        <div className="space-y-2">
          <Skeleton className="h-4 w-24 rounded-md" />
          <Skeleton className="h-2.5 w-full rounded-full" />
        </div>

        {/* Two-column grid skeleton */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-3 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50">
            <Skeleton className="h-4 w-20 rounded-md" />
            <SkeletonText lines={2} />
          </div>
          <div className="space-y-3 p-4 rounded-xl bg-gray-50 dark:bg-gray-800/50">
            <Skeleton className="h-4 w-20 rounded-md" />
            <SkeletonText lines={2} />
          </div>
        </div>

        {/* Contact skeleton */}
        <div className="space-y-3">
          <Skeleton className="h-4 w-28 rounded-md" />
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded-full" />
            <Skeleton className="h-3.5 w-36 rounded-md" />
          </div>
          <div className="flex items-center gap-2">
            <Skeleton className="h-4 w-4 rounded-full" />
            <Skeleton className="h-3.5 w-44 rounded-md" />
          </div>
        </div>

        {/* Footer skeleton */}
        <div className="flex gap-3 pt-2">
          <Skeleton className="h-10 flex-1 rounded-xl" />
          <Skeleton className="h-10 flex-1 rounded-xl" />
        </div>
      </div>
    </div>
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
  const t = useTranslations('SellerVerification');

  return (
    <div
      role="alert"
      className="rounded-2xl border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20 p-6 text-center"
    >
      <div className="flex flex-col items-center gap-3">
        <div className="w-12 h-12 rounded-2xl bg-red-100 dark:bg-red-900/30 flex items-center justify-center">
          <AlertTriangle className="w-6 h-6 text-red-600 dark:text-red-400" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold text-red-900 dark:text-red-200">
            {t('error.title')}
          </p>
          <p className="text-xs text-red-700 dark:text-red-300 mt-1 max-w-sm mx-auto">
            {message}
          </p>
        </div>
        {onRetry && (
          <Button
            variant="outline"
            size="sm"
            onClick={onRetry}
            className="mt-2"
            aria-label={t('error.retry')}
          >
            <Loader2 className="w-3.5 h-3.5 mr-1.5" aria-hidden="true" />
            {t('error.retry')}
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Empty State ────────────────────────────────────────────────────────────

function EmptyState({ className }: { className?: string }) {
  const t = useTranslations('SellerVerification');

  return (
    <div
      className={cn(
        'rounded-2xl border border-dashed border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-900 p-8 text-center',
        className
      )}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="w-14 h-14 rounded-2xl bg-gray-100 dark:bg-gray-800 flex items-center justify-center">
          <Shield className="w-7 h-7 text-gray-400 dark:text-gray-500" aria-hidden="true" />
        </div>
        <div>
          <p className="text-sm font-semibold text-gray-900 dark:text-gray-200">
            {t('empty.title')}
          </p>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-1 max-w-xs mx-auto">
            {t('empty.description')}
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Trust Score Section ────────────────────────────────────────────────────

function TrustScoreSection({
  score,
  compact,
}: {
  score: number;
  compact?: boolean;
}) {
  const t = useTranslations('SellerVerification');

  if (compact) {
    return (
      <div className="flex items-center gap-2">
        <div
          className={cn(
            'w-2 h-2 rounded-full flex-shrink-0',
            score >= 80 ? 'bg-emerald-500' : score >= 60 ? 'bg-amber-500' : 'bg-red-500'
          )}
          aria-hidden="true"
        />
        <span className={cn('text-xs font-semibold', getTrustScoreColor(score))}>
          {t('trustScore.label')}: {Math.round(score)}%
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Shield className="w-4 h-4 text-gray-500 dark:text-gray-400" aria-hidden="true" />
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            {t('trustScore.label')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('text-lg font-extrabold tabular-nums', getTrustScoreColor(score))}>
            {Math.round(score)}%
          </span>
          <span className={cn('text-xs font-medium', getTrustScoreColor(score))}>
            {getTrustScoreLabel(score, t)}
          </span>
        </div>
      </div>
      <Progress
        value={score}
        size="md"
        color={
          score >= 80
            ? 'bg-emerald-500'
            : score >= 60
              ? 'bg-amber-500'
              : 'bg-red-500'
        }
      />
    </div>
  );
}

// ─── Identity Section ───────────────────────────────────────────────────────

function IdentitySection({
  data,
}: {
  data: SellerVerificationData;
}) {
  const t = useTranslations('SellerVerification');
  const status = data.identityStatus;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getIdentityIcon(status)}
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            {t('identity.title')}
          </span>
        </div>
        <Badge variant={getIdentityBadgeVariant(status)}>
          {getIdentityLabel(status, t)}
        </Badge>
      </div>

      {data.isAgent && data.agencyName && (
        <div className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
          <Building2 className="w-3.5 h-3.5 flex-shrink-0" aria-hidden="true" />
          <span>{data.agencyName}</span>
        </div>
      )}

      {data.memberSince && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          {t('memberSince')}: {new Date(data.memberSince).toLocaleDateString('en-KE', {
            year: 'numeric',
            month: 'long',
          })}
        </p>
      )}

      {status === 'verified' && data.verificationExpiresAt && (
        <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
          <Clock className="w-3 h-3" aria-hidden="true" />
          {t('identity.expires')}: {formatRelativeTime(data.verificationExpiresAt)}
        </p>
      )}

      {status === 'rejected' && (
        <p className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1.5 mt-1">
          <AlertTriangle className="w-3 h-3" aria-hidden="true" />
          {t('identity.rejectedHelp')}
        </p>
      )}
    </div>
  );
}

// ─── License Section ────────────────────────────────────────────────────────

function LicenseSection({
  data,
}: {
  data: SellerVerificationData;
}) {
  const t = useTranslations('SellerVerification');

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {getLicenseIcon(data.licenseStatus)}
          <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
            {t('license.title')}
          </span>
        </div>
        <Badge
          variant={
            data.licenseStatus === 'verified'
              ? 'success'
              : data.licenseStatus === 'pending'
                ? 'warning'
                : data.licenseStatus === 'rejected'
                  ? 'danger'
                  : 'default'
          }
        >
          {data.licenseStatus === 'verified'
            ? t('license.verified')
            : data.licenseStatus === 'pending'
              ? t('license.pending')
              : data.licenseStatus === 'rejected'
                ? t('license.rejected')
                : t('license.none')}
        </Badge>
      </div>

      {data.licenseStatus === 'verified' && data.licenseType && (
        <div className="text-xs text-gray-600 dark:text-gray-400 space-y-1">
          <div className="flex items-center gap-2">
            <Award className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0" aria-hidden="true" />
            <div>
              <span className="font-medium">{data.licenseType}</span>
              {data.licenseNumber && (
                <p className="text-gray-500 dark:text-gray-500">
                  {t('license.number')}: {data.licenseNumber}
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {data.licenseStatus === 'none' && data.isAgent && (
        <p className="text-xs text-amber-600 dark:text-amber-400 flex items-center gap-1.5">
          <AlertTriangle className="w-3 h-3" aria-hidden="true" />
          {t('license.notAvailable')}
        </p>
      )}
    </div>
  );
}

// ─── Contact Verification Section ───────────────────────────────────────────

function ContactSection({
  data,
}: {
  data: SellerVerificationData;
}) {
  const t = useTranslations('SellerVerification');

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Phone className="w-4 h-4 text-gray-500 dark:text-gray-400" aria-hidden="true" />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
          {t('contact.title')}
        </span>
      </div>

      <div className="space-y-2.5">
        {/* Phone */}
        <div className="flex items-center justify-between group">
          <div className="flex items-center gap-2.5">
            {data.phoneVerified === 'verified' ? (
              <Phone className="w-4 h-4 text-emerald-600" aria-hidden="true" />
            ) : (
              <PhoneOff className="w-4 h-4 text-red-400" aria-hidden="true" />
            )}
            <div>
              <p className="text-sm text-gray-900 dark:text-gray-200 font-medium">
                {data.phoneNumber ? maskPhone(data.phoneNumber) : t('contact.noPhone')}
              </p>
              {data.phoneNumber && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {data.phoneVerified === 'verified'
                    ? t('contact.phoneVerified')
                    : t('contact.phoneUnverified')}
                </p>
              )}
            </div>
          </div>
          {getContactIcon(data.phoneVerified)}
        </div>

        {/* Email */}
        <div className="flex items-center justify-between group">
          <div className="flex items-center gap-2.5">
            {data.emailVerified === 'verified' ? (
              <Mail className="w-4 h-4 text-emerald-600" aria-hidden="true" />
            ) : (
              <MailX className="w-4 h-4 text-red-400" aria-hidden="true" />
            )}
            <div>
              <p className="text-sm text-gray-900 dark:text-gray-200 font-medium">
                {data.email ? maskEmail(data.email) : t('contact.noEmail')}
              </p>
              {data.email && (
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {data.emailVerified === 'verified'
                    ? t('contact.emailVerified')
                    : t('contact.emailUnverified')}
                </p>
              )}
            </div>
          </div>
          {getContactIcon(data.emailVerified)}
        </div>
      </div>
    </div>
  );
}

// ─── Stats Bar ──────────────────────────────────────────────────────────────

function StatsBar({
  data,
}: {
  data: SellerVerificationData;
}) {
  const t = useTranslations('SellerVerification');

  const stats: { label: string; value: string | number; icon?: React.ReactNode }[] = [];

  if (data.totalListings !== undefined) {
    stats.push({
      label: t('stats.totalListings'),
      value: data.totalListings,
      icon: <Eye className="w-3.5 h-3.5" aria-hidden="true" />,
    });
  }

  if (data.activeListings !== undefined) {
    stats.push({
      label: t('stats.activeListings'),
      value: data.activeListings,
      icon: <BadgeCheck className="w-3.5 h-3.5" aria-hidden="true" />,
    });
  }

  if (data.completedTransactions !== undefined) {
    stats.push({
      label: t('stats.transactions'),
      value: data.completedTransactions,
      icon: <Star className="w-3.5 h-3.5" aria-hidden="true" />,
    });
  }

  if (data.responseTime) {
    stats.push({
      label: t('stats.responseTime'),
      value: data.responseTime,
      icon: <MessageCircle className="w-3.5 h-3.5" aria-hidden="true" />,
    });
  }

  if (stats.length === 0) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
      {stats.map((stat) => (
        <div
          key={stat.label}
          className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-3 text-center border border-gray-100 dark:border-gray-700"
        >
          {stat.icon && (
            <div className="flex justify-center mb-1 text-gray-500 dark:text-gray-400">
              {stat.icon}
            </div>
          )}
          <p className="text-xs text-gray-500 dark:text-gray-400 font-medium truncate">
            {stat.label}
          </p>
          <p className="text-sm font-bold text-gray-900 dark:text-gray-100 mt-0.5">
            {stat.value}
          </p>
        </div>
      ))}
    </div>
  );
}

// ─── Badges Row ─────────────────────────────────────────────────────────────

function BadgesRow({ badges }: { badges: string[] }) {
  const t = useTranslations('SellerVerification');

  if (!badges || badges.length === 0) return null;

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <Award className="w-4 h-4 text-amber-500" aria-hidden="true" />
        <span className="text-xs font-semibold text-gray-700 dark:text-gray-300 uppercase tracking-wider">
          {t('badges.title')}
        </span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {badges.map((badge) => (
          <Badge key={badge} variant="success" className="capitalize">
            <Award className="w-3 h-3 mr-1" aria-hidden="true" />
            {badge}
          </Badge>
        ))}
      </div>
    </div>
  );
}

// ─── Expandable Details (mobile) ────────────────────────────────────────────

function ExpandableDetails({
  data,
  isExpanded,
  onToggle,
}: {
  data: SellerVerificationData;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const t = useTranslations('SellerVerification');

  return (
    <div>
      <button
        onClick={onToggle}
        className="flex items-center gap-1.5 text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors"
        aria-expanded={isExpanded}
        aria-controls="seller-verification-details"
      >
        {isExpanded ? (
          <>
            <ChevronUp className="w-3.5 h-3.5" aria-hidden="true" />
            {t('showLess')}
          </>
        ) : (
          <>
            <ChevronDown className="w-3.5 h-3.5" aria-hidden="true" />
            {t('showMore')}
          </>
        )}
      </button>

      {isExpanded && (
        <div
          id="seller-verification-details"
          className="mt-4 space-y-4 pt-4 border-t border-gray-100 dark:border-gray-800"
        >
          {/* Stats */}
          <StatsBar data={data} />

          {/* Badges */}
          <BadgesRow badges={data.badges || []} />
        </div>
      )}
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function SellerVerificationCard({
  data,
  isLoading = false,
  error = null,
  compact = false,
  className,
  onContact,
  onViewListings,
  onRequestReVerification,
}: SellerVerificationCardProps) {
  const t = useTranslations('SellerVerification');
  const [isExpanded, setIsExpanded] = React.useState(false);

  // ── Loading state ──────────────────────────────────────────────────────
  if (isLoading) {
    return <LoadingSkeleton compact={compact} />;
  }

  // ── Error state ────────────────────────────────────────────────────────
  if (error) {
    return <ErrorState message={error} />;
  }

  // ── Empty / No data state ──────────────────────────────────────────────
  if (!data) {
    return <EmptyState className={className} />;
  }

  // ── Compact variant ────────────────────────────────────────────────────
  if (compact) {
    const score = data.trustScore ?? 0;

    return (
      <div
        className={cn(
          'rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-4 shadow-sm hover:shadow-md transition-shadow duration-200',
          className
        )}
        role="region"
        aria-label={t('aria.compactLabel', { name: data.sellerName })}
      >
        {/* Header */}
        <div className="flex items-center gap-3 mb-3">
          <div
            className={cn(
              'w-10 h-10 rounded-full flex items-center justify-center text-white font-bold text-sm flex-shrink-0',
              data.identityStatus === 'verified'
                ? 'bg-emerald-500'
                : data.identityStatus === 'pending'
                  ? 'bg-amber-500'
                  : 'bg-gray-400'
            )}
            aria-hidden="true"
          >
            {data.avatarUrl ? (
              <img
                src={data.avatarUrl}
                alt=""
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              data.sellerName.charAt(0).toUpperCase()
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-semibold text-gray-900 dark:text-gray-100 truncate">
              {data.sellerName}
            </p>
            <div className="flex items-center gap-2 mt-0.5">
              {data.isAgent && (
                <Badge variant="info" className="text-[10px] px-1.5 py-0">
                  {t('agentBadge')}
                </Badge>
              )}
              {score > 0 && <TrustScoreSection score={score} compact />}
            </div>
          </div>
        </div>

        {/* Quick stats row */}
        <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400 mb-3">
          {data.totalListings !== undefined && (
            <span>
              {data.totalListings} {t('listings')}
            </span>
          )}
          {data.responseTime && (
            <>
              <span className="text-gray-300 dark:text-gray-600" aria-hidden="true">|</span>
              <span className="flex items-center gap-1">
                <MessageCircle className="w-3 h-3" aria-hidden="true" />
                {data.responseTime}
              </span>
            </>
          )}
        </div>

        {/* Verification status chips */}
        <div className="flex flex-wrap gap-1.5 mb-3">
          <Badge variant={getIdentityBadgeVariant(data.identityStatus)} className="text-[10px]">
            {getIdentityIcon(data.identityStatus)}
            {getIdentityLabel(data.identityStatus, t)}
          </Badge>
          {data.phoneVerified === 'verified' && (
            <Badge variant="success" className="text-[10px]">
              <Phone className="w-3 h-3 mr-0.5" aria-hidden="true" />
              {t('contact.phoneChip')}
            </Badge>
          )}
          {data.emailVerified === 'verified' && (
            <Badge variant="success" className="text-[10px]">
              <Mail className="w-3 h-3 mr-0.5" aria-hidden="true" />
              {t('contact.emailChip')}
            </Badge>
          )}
        </div>

        {/* Actions */}
        <div className="flex gap-2">
          {onContact && (
            <Button
              variant="primary"
              size="sm"
              fullWidth
              onClick={() => onContact(data.sellerId)}
              aria-label={t('aria.contact', { name: data.sellerName })}
            >
              <MessageCircle className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
              {t('contactSeller')}
            </Button>
          )}
          {onViewListings && (
            <Button
              variant="outline"
              size="sm"
              fullWidth
              onClick={() => onViewListings(data.sellerId)}
              aria-label={t('aria.viewListings', { name: data.sellerName })}
            >
              <Eye className="w-3.5 h-3.5 mr-1" aria-hidden="true" />
              {t('viewListings')}
            </Button>
          )}
        </div>
      </div>
    );
  }

  // ── Full variant ───────────────────────────────────────────────────────
  const showDetailsSection = data.badges && data.badges.length > 0
    || data.totalListings !== undefined
    || data.activeListings !== undefined
    || data.completedTransactions !== undefined
    || !!data.responseTime;

  return (
    <Card
      className={cn('overflow-hidden', className)}
      padding="none"
      role="region"
      aria-label={t('aria.fullLabel', { name: data.sellerName })}
    >
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div
        className={cn(
          'p-5 border-b border-gray-100 dark:border-gray-800 flex flex-col sm:flex-row sm:items-center gap-4',
          getTrustScoreBg(data.trustScore ?? 0)
        )}
      >
        <div className="flex items-center gap-4 flex-1 min-w-0">
          {/* Avatar */}
          <div
            className={cn(
              'w-14 h-14 rounded-full flex items-center justify-center text-white font-bold text-lg flex-shrink-0 shadow-sm',
              data.identityStatus === 'verified'
                ? 'bg-emerald-500'
                : data.identityStatus === 'pending'
                  ? 'bg-amber-500'
                  : 'bg-gray-400'
            )}
            aria-hidden="true"
          >
            {data.avatarUrl ? (
              <img
                src={data.avatarUrl}
                alt=""
                className="w-full h-full rounded-full object-cover"
              />
            ) : (
              data.sellerName.charAt(0).toUpperCase()
            )}
          </div>

          {/* Seller name & meta */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
                {data.sellerName}
              </h3>
              {data.identityStatus === 'verified' && (
                <BadgeCheck className="w-5 h-5 text-emerald-600 flex-shrink-0" aria-label={t('identityVerifiedBadge')} />
              )}
              {data.isAgent && (
                <Badge variant="info" className="text-xs">
                  <Building2 className="w-3 h-3 mr-1" aria-hidden="true" />
                  {t('agentBadge')}
                </Badge>
              )}
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
              {data.isAgent && data.agencyName
                ? data.agencyName
                : t('individualSeller')}
            </p>
          </div>
        </div>

        {/* Trust score gauge (compact gauge in header) */}
        {data.trustScore !== undefined && data.trustScore > 0 && (
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="text-right">
              <p className={cn('text-2xl font-extrabold tabular-nums', getTrustScoreColor(data.trustScore))}>
                {Math.round(data.trustScore)}%
              </p>
              <p className={cn('text-xs font-medium', getTrustScoreColor(data.trustScore))}>
                {getTrustScoreLabel(data.trustScore, t)}
              </p>
            </div>
            <div
              className={cn(
                'w-12 h-12 rounded-full flex items-center justify-center',
                data.trustScore >= 80
                  ? 'bg-emerald-100 dark:bg-emerald-900/30'
                  : data.trustScore >= 60
                    ? 'bg-amber-100 dark:bg-amber-900/30'
                    : 'bg-red-100 dark:bg-red-900/30'
              )}
              aria-hidden="true"
            >
              <ShieldCheck className={cn(
                'w-6 h-6',
                data.trustScore >= 80 ? 'text-emerald-600' : data.trustScore >= 60 ? 'text-amber-600' : 'text-red-600'
              )} />
            </div>
          </div>
        )}
      </div>

      {/* ── Body ────────────────────────────────────────────────────────── */}
      <CardContent className="p-5 space-y-5">
        {/* Trust score progress bar */}
        {data.trustScore !== undefined && data.trustScore > 0 && (
          <TrustScoreSection score={data.trustScore} />
        )}

        {/* Two-column grid: Identity + License */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
            <IdentitySection data={data} />
          </div>
          <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
            <LicenseSection data={data} />
          </div>
        </div>

        {/* Contact verification */}
        <div className="bg-gray-50 dark:bg-gray-800/50 rounded-xl p-4 border border-gray-100 dark:border-gray-700">
          <ContactSection data={data} />
        </div>

        {/* Details (collapsible on mobile) */}
        {showDetailsSection && (
          <div className="sm:hidden">
            <ExpandableDetails
              data={data}
              isExpanded={isExpanded}
              onToggle={() => setIsExpanded((prev) => !prev)}
            />
          </div>
        )}

        {/* Details (always visible on desktop) */}
        {showDetailsSection && (
          <div className="hidden sm:block space-y-4">
            <StatsBar data={data} />
            <BadgesRow badges={data.badges || []} />
          </div>
        )}

        {/* ── Footer actions ────────────────────────────────────────────── */}
        <div className="flex flex-col sm:flex-row gap-3 pt-2 border-t border-gray-100 dark:border-gray-800">
          {onContact && (
            <Button
              variant="primary"
              fullWidth
              onClick={() => onContact(data.sellerId)}
              aria-label={t('aria.contact', { name: data.sellerName })}
            >
              <MessageCircle className="w-4 h-4 mr-2" aria-hidden="true" />
              {t('contactSeller')}
            </Button>
          )}
          {onViewListings && (
            <Button
              variant="outline"
              fullWidth
              onClick={() => onViewListings(data.sellerId)}
              aria-label={t('aria.viewListings', { name: data.sellerName })}
            >
              <Eye className="w-4 h-4 mr-2" aria-hidden="true" />
              {t('viewListings')}
            </Button>
          )}
          {onRequestReVerification && data.identityStatus === 'rejected' && (
            <Button
              variant="ghost"
              fullWidth
              onClick={() => onRequestReVerification(data.sellerId)}
              aria-label={t('aria.requestReVerification')}
            >
              <AlertTriangle className="w-4 h-4 mr-2" aria-hidden="true" />
              {t('identity.requestReVerification')}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
