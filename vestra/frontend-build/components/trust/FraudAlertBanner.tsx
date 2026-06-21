'use client';

import { useState } from 'react';
import { useTranslations } from 'next-intl';
import { cn } from '@/lib/utils';
import {
  AlertTriangle,
  ShieldAlert,
  Info,
  X,
  ChevronDown,
  ChevronUp,
  Lightbulb,
  CheckCircle2,
  ExternalLink,
  ShieldCheck,
  FileWarning,
  Siren,
  Eye,
  UserCheck,
  FileSearch,
  Lock,
  Phone,
  HelpCircle,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, Badge } from '@/components/ui/card';
import { Alert } from '@/components/ui/alert';
import { Skeleton, SkeletonText } from '@/components/ui/skeleton';
import { Modal, ModalBody, ModalHeader, ModalFooter } from '@/components/ui/modal';

// ─── Types ──────────────────────────────────────────────────────────────────

export type FraudAlertSeverity = 'critical' | 'warning' | 'info' | 'tip';

export interface FraudAlertMeta {
  reportedCount?: number;
  reportDate?: string;
  source?: string;
  category?: string;
}

export interface FraudAlert {
  id: string;
  severity: FraudAlertSeverity;
  title: string;
  description: string;
  actionLabel?: string;
  actionUrl?: string;
  dismissible?: boolean;
  metadata?: FraudAlertMeta;
}

export interface FraudAlertBannerProps {
  alerts?: FraudAlert[];
  loading?: boolean;
  error?: string | null;
  onDismiss?: (alertId: string) => void;
  onAction?: (alert: FraudAlert) => void;
  onRetry?: () => void;
  className?: string;
  maxVisibleAlerts?: number;
  showSafetyTips?: boolean;
  compact?: boolean;
}

// ─── Constants ──────────────────────────────────────────────────────────────

const SEVERITY_STYLES: Record<
  FraudAlertSeverity,
  {
    border: string;
    bg: string;
    darkBg: string;
    iconBg: string;
    darkIconBg: string;
    iconColor: string;
    dotColor: string;
    titleColor: string;
    badge: string;
  }
> = {
  critical: {
    border: 'border-red-200 dark:border-red-800',
    bg: 'bg-red-50 dark:bg-red-950/40',
    darkBg: 'dark:bg-red-950/40',
    iconBg: 'bg-red-100 dark:bg-red-900/50',
    darkIconBg: 'dark:bg-red-900/50',
    iconColor: 'text-red-600 dark:text-red-400',
    dotColor: 'bg-red-500',
    titleColor: 'text-red-900 dark:text-red-200',
    badge: 'danger',
  },
  warning: {
    border: 'border-amber-200 dark:border-amber-800',
    bg: 'bg-amber-50 dark:bg-amber-950/40',
    darkBg: 'dark:bg-amber-950/40',
    iconBg: 'bg-amber-100 dark:bg-amber-900/50',
    darkIconBg: 'dark:bg-amber-900/50',
    iconColor: 'text-amber-600 dark:text-amber-400',
    dotColor: 'bg-amber-500',
    titleColor: 'text-amber-900 dark:text-amber-200',
    badge: 'warning',
  },
  info: {
    border: 'border-blue-200 dark:border-blue-800',
    bg: 'bg-blue-50 dark:bg-blue-950/40',
    darkBg: 'dark:bg-blue-950/40',
    iconBg: 'bg-blue-100 dark:bg-blue-900/50',
    darkIconBg: 'dark:bg-blue-900/50',
    iconColor: 'text-blue-600 dark:text-blue-400',
    dotColor: 'bg-blue-500',
    titleColor: 'text-blue-900 dark:text-blue-200',
    badge: 'info',
  },
  tip: {
    border: 'border-emerald-200 dark:border-emerald-800',
    bg: 'bg-emerald-50 dark:bg-emerald-950/40',
    darkBg: 'dark:bg-emerald-950/40',
    iconBg: 'bg-emerald-100 dark:bg-emerald-900/50',
    darkIconBg: 'dark:bg-emerald-900/50',
    iconColor: 'text-emerald-600 dark:text-emerald-400',
    dotColor: 'bg-emerald-500',
    titleColor: 'text-emerald-900 dark:text-emerald-200',
    badge: 'success',
  },
};

const SEVERITY_ICONS: Record<FraudAlertSeverity, React.ReactNode> = {
  critical: <ShieldAlert className="w-5 h-5" />,
  warning: <AlertTriangle className="w-5 h-5" />,
  info: <Info className="w-5 h-5" />,
  tip: <Lightbulb className="w-5 h-5" />,
};

const DEFAULT_SAFETY_TIPS: SafetyTip[] = [
  {
    id: 'tip-inspect-property',
    icon: <Eye className="w-4 h-4" />,
    titleKey: 'safety_tips.inspect_property.title',
    descKey: 'safety_tips.inspect_property.description',
  },
  {
    id: 'tip-verify-owner',
    icon: <UserCheck className="w-4 h-4" />,
    titleKey: 'safety_tips.verify_owner.title',
    descKey: 'safety_tips.verify_owner.description',
  },
  {
    id: 'tip-check-documents',
    icon: <FileSearch className="w-4 h-4" />,
    titleKey: 'safety_tips.check_documents.title',
    descKey: 'safety_tips.check_documents.description',
  },
  {
    id: 'tip-use-escrow',
    icon: <Lock className="w-4 h-4" />,
    titleKey: 'safety_tips.use_escrow.title',
    descKey: 'safety_tips.use_escrow.description',
  },
  {
    id: 'tip-report-suspicious',
    icon: <Phone className="w-4 h-4" />,
    titleKey: 'safety_tips.report_suspicious.title',
    descKey: 'safety_tips.report_suspicious.description',
  },
];

// ─── Safety Tip Type ────────────────────────────────────────────────────────

interface SafetyTip {
  id: string;
  icon: React.ReactNode;
  titleKey: string;
  descKey: string;
}

// ─── Sub-components ─────────────────────────────────────────────────────────

/** Severity dot indicator */
function SeverityDot({ severity }: { severity: FraudAlertSeverity }) {
  return (
    <span
      className={cn(
        'absolute left-0 top-1 w-2 h-2 rounded-full',
        SEVERITY_STYLES[severity].dotColor
      )}
      aria-hidden="true"
    />
  );
}

/** Icon for a single alert item */
function AlertIcon({ severity }: { severity: FraudAlertSeverity }) {
  return (
    <div
      className={cn(
        'w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 shadow-sm',
        SEVERITY_STYLES[severity].iconBg,
        SEVERITY_STYLES[severity].iconColor
      )}
      aria-hidden="true"
    >
      {SEVERITY_ICONS[severity]}
    </div>
  );
}

// ─── Loading State ──────────────────────────────────────────────────────────

function FraudAlertBannerSkeleton({ compact }: { compact?: boolean }) {
  if (compact) {
    return (
      <div
        className="flex items-center gap-3 p-3 rounded-xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900"
        aria-label="Loading fraud alerts"
      >
        <Skeleton className="w-10 h-10 rounded-xl flex-shrink-0" />
        <div className="flex-1 space-y-2">
          <Skeleton className="h-4 w-3/4 rounded-md" />
          <Skeleton className="h-3 w-1/2 rounded-md" />
        </div>
      </div>
    );
  }

  return (
    <Card className="overflow-hidden" aria-label="Loading fraud alerts">
      <div className="p-5 space-y-4">
        {/* Header skeleton */}
        <div className="flex items-center gap-3">
          <Skeleton className="w-10 h-10 rounded-xl flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <Skeleton className="h-5 w-48 rounded-md" />
            <Skeleton className="h-3.5 w-32 rounded-md" />
          </div>
        </div>

        {/* Alert items skeleton */}
        <div className="space-y-3 pt-2">
          {Array.from({ length: 2 }).map((_, i) => (
            <div
              key={i}
              className="flex items-start gap-3 p-4 rounded-xl border border-gray-100 dark:border-gray-800"
            >
              <Skeleton className="w-10 h-10 rounded-xl flex-shrink-0" />
              <div className="flex-1 space-y-2">
                <Skeleton className="h-4 w-3/4 rounded-md" />
                <SkeletonText lines={2} lastLineWidth="50%" />
              </div>
            </div>
          ))}
        </div>
      </div>
    </Card>
  );
}

// ─── Error State ────────────────────────────────────────────────────────────

function FraudAlertBannerError({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  const t = useTranslations('FraudAlertBanner');

  return (
    <Card
      role="alert"
      aria-live="assertive"
      className="border-red-200 dark:border-red-800"
    >
      <div className="flex items-start gap-4 p-5">
        <div className="w-10 h-10 rounded-xl bg-red-100 dark:bg-red-900/50 flex items-center justify-center flex-shrink-0">
          <FileWarning className="w-5 h-5 text-red-600 dark:text-red-400" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-red-900 dark:text-red-200">
            {t('error_title') || 'Failed to load fraud alerts'}
          </p>
          <p className="text-xs text-red-700 dark:text-red-300 mt-1">{message}</p>
          {onRetry && (
            <Button
              variant="outline"
              size="sm"
              className="mt-3"
              onClick={onRetry}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              {t('retry') || 'Retry'}
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}

// ─── Empty State ────────────────────────────────────────────────────────────

function FraudAlertBannerEmpty({
  compact,
  className,
}: {
  compact?: boolean;
  className?: string;
}) {
  const t = useTranslations('FraudAlertBanner');

  if (compact) {
    return (
      <div
        className={cn(
          'flex items-center gap-3 p-3 rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/40',
          className
        )}
        role="status"
        aria-live="polite"
      >
        <div className="w-8 h-8 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center flex-shrink-0">
          <ShieldCheck className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
        </div>
        <p className="text-sm font-medium text-emerald-800 dark:text-emerald-200">
          {t('no_alerts') || 'No fraud alerts. This listing looks safe.'}
        </p>
      </div>
    );
  }

  return (
    <Card
      className={cn(
        'border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/20',
        className
      )}
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center justify-center py-10 px-6 text-center">
        <div className="w-16 h-16 rounded-2xl bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center mb-4 shadow-sm">
          <ShieldCheck className="w-8 h-8 text-emerald-600 dark:text-emerald-400" />
        </div>
        <h3 className="text-lg font-semibold text-emerald-900 dark:text-emerald-200">
          {t('no_alerts_title') || 'All Clear'}
        </h3>
        <p className="text-sm text-emerald-700 dark:text-emerald-300 mt-1.5 max-w-md">
          {t('no_alerts') ||
            'No fraud alerts or scam indicators detected. This listing has passed our safety checks.'}
        </p>
      </div>
    </Card>
  );
}

// ─── Single Alert Item ──────────────────────────────────────────────────────

interface AlertItemProps {
  alert: FraudAlert;
  onDismiss?: (id: string) => void;
  onAction?: (alert: FraudAlert) => void;
}

function AlertItem({ alert, onDismiss, onAction }: AlertItemProps) {
  const t = useTranslations('FraudAlertBanner');
  const [isExpanded, setIsExpanded] = useState(false);
  const [dismissed, setDismissed] = useState(false);
  const styles = SEVERITY_STYLES[alert.severity];
  const isDismissible = alert.dismissible !== false;

  if (dismissed) return null;

  const severityLabel = t(`severity.${alert.severity}`) || alert.severity;

  return (
    <div
      className={cn(
        'relative rounded-xl border p-4 transition-all duration-200',
        styles.border,
        styles.bg,
        styles.darkBg
      )}
      role="alert"
      aria-live="assertive"
      aria-atomic="true"
    >
      <div className="flex items-start gap-3">
        {/* Severity dot */}
        <SeverityDot severity={alert.severity} />

        {/* Icon */}
        <AlertIcon severity={alert.severity} />

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-start justify-between gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className={cn('text-sm font-semibold', styles.titleColor)}>
                {alert.title}
              </h4>
              <Badge variant={styles.badge as 'danger' | 'warning' | 'info' | 'success'} className="capitalize">
                {severityLabel}
              </Badge>
            </div>

            {/* Dismiss */}
            {isDismissible && onDismiss && (
              <button
                onClick={() => {
                  setDismissed(true);
                  onDismiss(alert.id);
                }}
                className={cn(
                  'flex-shrink-0 w-7 h-7 rounded-lg flex items-center justify-center transition-colors',
                  'hover:bg-black/5 dark:hover:bg-white/10'
                )}
                aria-label={t('dismiss_alert') || 'Dismiss alert'}
              >
                <X className="w-3.5 h-3.5 opacity-60" />
              </button>
            )}
          </div>

          <p className="text-xs text-gray-700 dark:text-gray-300 mt-1 leading-relaxed">
            {alert.description}
          </p>

          {/* Expandable metadata */}
          {alert.metadata && (
            <>
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className={cn(
                  'inline-flex items-center gap-1 text-xs font-medium mt-2 transition-colors',
                  styles.iconColor
                )}
                aria-expanded={isExpanded}
                aria-controls={`alert-meta-${alert.id}`}
              >
                {isExpanded ? (
                  <>
                    <ChevronUp className="w-3.5 h-3.5" />
                    {t('show_less') || 'Show less'}
                  </>
                ) : (
                  <>
                    <ChevronDown className="w-3.5 h-3.5" />
                    {t('show_details') || 'Show details'}
                  </>
                )}
              </button>

              <div
                id={`alert-meta-${alert.id}`}
                className={cn(
                  'mt-2 pt-2 border-t border-black/5 dark:border-white/10 overflow-hidden transition-all duration-200',
                  isExpanded ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
                )}
                aria-hidden={!isExpanded}
              >
                <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
                  {alert.metadata.category && (
                    <>
                      <dt className="text-gray-500 dark:text-gray-400 font-medium">
                        {t('category') || 'Category'}:
                      </dt>
                      <dd className="text-gray-800 dark:text-gray-200 text-right">
                        {alert.metadata.category}
                      </dd>
                    </>
                  )}
                  {alert.metadata.source && (
                    <>
                      <dt className="text-gray-500 dark:text-gray-400 font-medium">
                        {t('source') || 'Source'}:
                      </dt>
                      <dd className="text-gray-800 dark:text-gray-200 text-right">
                        {alert.metadata.source}
                      </dd>
                    </>
                  )}
                  {alert.metadata.reportedCount !== undefined && (
                    <>
                      <dt className="text-gray-500 dark:text-gray-400 font-medium">
                        {t('reported_count') || 'Reports'}:
                      </dt>
                      <dd className="text-gray-800 dark:text-gray-200 text-right">
                        {alert.metadata.reportedCount}
                      </dd>
                    </>
                  )}
                  {alert.metadata.reportDate && (
                    <>
                      <dt className="text-gray-500 dark:text-gray-400 font-medium">
                        {t('report_date') || 'Reported'}:
                      </dt>
                      <dd className="text-gray-800 dark:text-gray-200 text-right">
                        {alert.metadata.reportDate}
                      </dd>
                    </>
                  )}
                </dl>
              </div>
            </>
          )}

          {/* Action button */}
          {alert.actionLabel && (
            <div className="mt-3">
              <Button
                variant="outline"
                size="sm"
                onClick={() => onAction?.(alert)}
                rightIcon={
                  alert.actionUrl ? (
                    <ExternalLink className="w-3 h-3" />
                  ) : undefined
                }
              >
                {alert.actionLabel}
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Safety Tips Section ────────────────────────────────────────────────────

interface SafetyTipsSectionProps {
  tips?: SafetyTip[];
  className?: string;
}

function SafetyTipsSection({
  tips = DEFAULT_SAFETY_TIPS,
  className,
}: SafetyTipsSectionProps) {
  const t = useTranslations('FraudAlertBanner');
  const [isOpen, setIsOpen] = useState(false);
  const [selectedTip, setSelectedTip] = useState<SafetyTip | null>(null);

  return (
    <div className={cn('mt-4', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'inline-flex items-center gap-2 text-sm font-medium transition-colors',
          'text-emerald-700 dark:text-emerald-400 hover:text-emerald-800 dark:hover:text-emerald-300'
        )}
        aria-expanded={isOpen}
        aria-controls="safety-tips-panel"
      >
        <Lightbulb className="w-4 h-4" />
        {t('safety_tips_title') || 'Safety Tips for Buyers & Sellers'}
        {isOpen ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      <div
        id="safety-tips-panel"
        className={cn(
          'mt-3 grid gap-2 overflow-hidden transition-all duration-300',
          'sm:grid-cols-2 lg:grid-cols-3',
          isOpen
            ? 'max-h-[2000px] opacity-100'
            : 'max-h-0 opacity-0 pointer-events-none'
        )}
        role="region"
        aria-label={t('safety_tips_title') || 'Safety tips'}
      >
        {tips.map((tip) => (
          <button
            key={tip.id}
            onClick={() => setSelectedTip(tip)}
            className={cn(
              'flex items-start gap-3 p-3 rounded-xl text-left transition-all duration-200',
              'border border-gray-100 dark:border-gray-800',
              'bg-white dark:bg-gray-900',
              'hover:border-emerald-200 dark:hover:border-emerald-800',
              'hover:shadow-sm hover:-translate-y-0.5',
              'focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2'
            )}
            aria-label={t(tip.titleKey) || tip.titleKey}
          >
            <div className="w-8 h-8 rounded-lg bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center flex-shrink-0 text-emerald-600 dark:text-emerald-400">
              {tip.icon}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-semibold text-gray-900 dark:text-gray-100 line-clamp-1">
                {t(tip.titleKey) || tip.titleKey}
              </p>
              <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5 line-clamp-2 leading-relaxed">
                {t(tip.descKey) || tip.descKey}
              </p>
            </div>
          </button>
        ))}
      </div>

      {/* Safety Tip Detail Modal */}
      <Modal
        isOpen={!!selectedTip}
        onClose={() => setSelectedTip(null)}
        title={
          selectedTip
            ? t(selectedTip.titleKey) || selectedTip.titleKey
            : ''
        }
        size="sm"
      >
        <ModalBody>
          {selectedTip && (
            <div className="space-y-4">
              <div className="flex items-center gap-3 p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800">
                <div className="w-10 h-10 rounded-xl bg-emerald-100 dark:bg-emerald-900/50 flex items-center justify-center flex-shrink-0 text-emerald-600 dark:text-emerald-400">
                  {selectedTip.icon}
                </div>
                <div>
                  <p className="text-sm font-semibold text-emerald-900 dark:text-emerald-200">
                    {t(selectedTip.titleKey) || selectedTip.titleKey}
                  </p>
                  <p className="text-xs text-emerald-700 dark:text-emerald-300">
                    {t('safety_tip') || 'Safety tip'}
                  </p>
                </div>
              </div>
              <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">
                {t(selectedTip.descKey) || selectedTip.descKey}
              </p>
            </div>
          )}
        </ModalBody>
        <ModalFooter>
          <Button variant="primary" size="sm" onClick={() => setSelectedTip(null)}>
            {t('got_it') || 'Got it'}
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

/**
 * FraudAlertBanner
 *
 * Displays fraud warnings, scam indicators, and safety tips for property
 * transactions on the Vestra platform. Supports critical, warning, info,
 * and tip severity levels with appropriate visual styling.
 */
export default function FraudAlertBanner({
  alerts = [],
  loading = false,
  error = null,
  onDismiss,
  onAction,
  onRetry,
  className,
  maxVisibleAlerts = 5,
  showSafetyTips = true,
  compact = false,
}: FraudAlertBannerProps) {
  const t = useTranslations('FraudAlertBanner');

  // ── Loading state ────────────────────────────────────────────────────────
  if (loading) {
    return <FraudAlertBannerSkeleton compact={compact} />;
  }

  // ── Error state ──────────────────────────────────────────────────────────
  if (error) {
    return <FraudAlertBannerError message={error} onRetry={onRetry} />;
  }

  // ── Empty state ──────────────────────────────────────────────────────────
  if (!alerts || alerts.length === 0) {
    return <FraudAlertBannerEmpty compact={compact} className={className} />;
  }

  // ── Content state ────────────────────────────────────────────────────────

  // Separate tips from warnings
  const criticalAlerts = alerts.filter((a) => a.severity === 'critical');
  const warningAlerts = alerts.filter((a) => a.severity === 'warning');
  const infoAlerts = alerts.filter((a) => a.severity === 'info');
  const tipAlerts = alerts.filter((a) => a.severity === 'tip');
  const hasCritical = criticalAlerts.length > 0;

  // Limit visible alerts
  const visibleAlerts = alerts.slice(0, maxVisibleAlerts);
  const hiddenCount = alerts.length - visibleAlerts.length;

  // Count alerts by severity for summary
  const alertSummary = [
    ...(criticalAlerts.length > 0
      ? [{ count: criticalAlerts.length, label: t('critical') || 'critical' }]
      : []),
    ...(warningAlerts.length > 0
      ? [{ count: warningAlerts.length, label: t('warning') || 'warning' }]
      : []),
    ...(infoAlerts.length > 0
      ? [{ count: infoAlerts.length, label: t('info') || 'info' }]
      : []),
    ...(tipAlerts.length > 0
      ? [{ count: tipAlerts.length, label: t('tip') || 'tip' }]
      : []),
  ];

  // ── Compact variant ──────────────────────────────────────────────────────
  if (compact) {
    const criticalCount = criticalAlerts.length;
    const totalCount = alerts.length;

    return (
      <div
        className={cn(
          'rounded-xl border p-3 transition-all duration-200',
          hasCritical
            ? 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-950/40'
            : 'border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/40',
          className
        )}
        role="alert"
        aria-live="polite"
      >
        <div className="flex items-center gap-3">
          <div
            className={cn(
              'w-8 h-8 rounded-xl flex items-center justify-center flex-shrink-0',
              hasCritical
                ? 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400'
                : 'bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
            )}
          >
            {hasCritical ? (
              <ShieldAlert className="w-4 h-4" />
            ) : (
              <AlertTriangle className="w-4 h-4" />
            )}
          </div>
          <div className="flex-1 min-w-0">
            <p
              className={cn(
                'text-sm font-semibold',
                hasCritical
                  ? 'text-red-900 dark:text-red-200'
                  : 'text-amber-900 dark:text-amber-200'
              )}
            >
              {hasCritical
                ? t('compact_critical_title', {
                    count: criticalCount,
                  }) || `${criticalCount} critical alert(s) found`
                : t('compact_warning_title', {
                    count: totalCount,
                  }) || `${totalCount} warning(s) found`}
            </p>
            <p
              className={cn(
                'text-xs mt-0.5',
                hasCritical
                  ? 'text-red-700 dark:text-red-300'
                  : 'text-amber-700 dark:text-amber-300'
              )}
            >
              {t('compact_tap_for_details') || 'Tap for details'}
            </p>
          </div>
          <Badge
            variant={hasCritical ? 'danger' : 'warning'}
            className="flex-shrink-0"
          >
            {totalCount}
          </Badge>
        </div>
      </div>
    );
  }

  // ── Full variant ─────────────────────────────────────────────────────────
  return (
    <div className={cn('space-y-3', className)}>
      {/* Header banner */}
      <Card
        className={cn(
          'overflow-hidden',
          hasCritical
            ? 'border-red-200 dark:border-red-800'
            : 'border-amber-200 dark:border-amber-800'
        )}
      >
        <div
          className={cn(
            'p-5',
            hasCritical
              ? 'bg-gradient-to-r from-red-50 to-red-50/50 dark:from-red-950/40 dark:to-red-950/20'
              : 'bg-gradient-to-r from-amber-50 to-amber-50/50 dark:from-amber-950/40 dark:to-amber-950/20'
          )}
        >
          <div className="flex items-start gap-4">
            {/* Icon */}
            <div
              className={cn(
                'w-12 h-12 rounded-2xl flex items-center justify-center flex-shrink-0 shadow-sm',
                hasCritical
                  ? 'bg-red-100 dark:bg-red-900/50 text-red-600 dark:text-red-400'
                  : 'bg-amber-100 dark:bg-amber-900/50 text-amber-600 dark:text-amber-400'
              )}
            >
              {hasCritical ? (
                <Siren className="w-6 h-6" />
              ) : (
                <AlertTriangle className="w-6 h-6" />
              )}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <h3
                  className={cn(
                    'text-lg font-bold',
                    hasCritical
                      ? 'text-red-900 dark:text-red-200'
                      : 'text-amber-900 dark:text-amber-200'
                  )}
                >
                  {hasCritical
                    ? t('header_critical_title') || 'Fraud Alerts Detected'
                    : t('header_warning_title') || 'Caution Advised'}
                </h3>
                <Badge
                  variant={hasCritical ? 'danger' : 'warning'}
                  className="text-xs"
                >
                  {alerts.length}{' '}
                  {alerts.length === 1
                    ? t('alert_singular') || 'alert'
                    : t('alert_plural') || 'alerts'}
                </Badge>
              </div>

              {/* Summary chips */}
              <div className="flex flex-wrap gap-1.5 mt-2">
                {alertSummary.map(({ count, label }) => (
                  <span
                    key={label}
                    className={cn(
                      'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium',
                      'bg-white/70 dark:bg-gray-900/50 border border-gray-200 dark:border-gray-700',
                      'text-gray-700 dark:text-gray-300'
                    )}
                  >
                    <span
                      className={cn(
                        'w-1.5 h-1.5 rounded-full',
                        label === t('critical') || label === 'critical'
                          ? 'bg-red-500'
                          : label === t('warning') || label === 'warning'
                            ? 'bg-amber-500'
                            : label === t('info') || label === 'info'
                              ? 'bg-blue-500'
                              : 'bg-emerald-500'
                      )}
                      aria-hidden="true"
                    />
                    {count} {label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </Card>

      {/* Alert list */}
      <div className="space-y-2" role="list" aria-label={t('alerts_list') || 'Fraud alerts'}>
        {visibleAlerts.map((alert) => (
          <div key={alert.id} role="listitem">
            <AlertItem
              alert={alert}
              onDismiss={onDismiss}
              onAction={onAction}
            />
          </div>
        ))}
      </div>

      {/* Hidden count notice */}
      {hiddenCount > 0 && (
        <p className="text-xs text-center text-gray-500 dark:text-gray-400 py-1">
          {t('hidden_alerts', { count: hiddenCount }) ||
            `+${hiddenCount} more alert(s) not shown`}
        </p>
      )}

      {/* Safety Tips */}
      {showSafetyTips && alerts.length > 0 && <SafetyTipsSection />}
    </div>
  );
}
