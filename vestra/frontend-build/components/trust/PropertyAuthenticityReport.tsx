'use client';

import * as React from 'react';
import { useTranslations } from 'next-intl';
import Image from 'next/image';
import { cn } from '@/lib/utils';
import {
  Card,
  Badge,
} from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { Modal } from '@/components/ui/modal';
import { Button } from '@/components/ui/button';
import { Alert } from '@/components/ui/alert';

import {
  FileText,
  UserCheck,
  Camera,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ShieldX,
  MapPin,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  HelpCircle,
  Building2,
  Calendar,
  Hash,
  Phone,
  ImageIcon,
  AlertCircle,
  FileSearch,
  Scale,
  Landmark,
  Users,
  Home,
  Eye,
  Info,
} from 'lucide-react';

// ─── Types ──────────────────────────────────────────────────────────────────

export interface TitleDeedVerification {
  document_number: string;
  holder_name: string;
  land_size_hectares: number;
  land_size_acres: number;
  location: string;
  status: 'valid' | 'invalid' | 'pending';
  verified_at: string;
  encumbrances: string[];
  registered_owner: string;
  title_deed_image_url?: string;
  notes?: string;
}

export interface OwnershipCheckResult {
  is_owner: boolean;
  owner_name: string;
  id_number?: string;
  phone_number?: string;
  confidence: 'high' | 'medium' | 'low';
  matched_fields: string[];
  mismatched_fields: string[];
  previous_owners: Array<{ name: string; period: string }>;
  checked_at: string;
}

export type PhotoCategory = 'exterior' | 'interior' | 'surroundings' | 'documentation';

export interface SiteVerificationPhoto {
  id: string;
  image_url: string;
  caption: string;
  category: PhotoCategory;
  location_verified: boolean;
  captured_at: string;
  uploaded_by?: string;
  geotag?: { latitude: number; longitude: number };
}

export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface RiskFactor {
  name: string;
  severity: RiskLevel;
  description: string;
}

export interface RiskAssessment {
  overall_risk: RiskLevel;
  risk_score: number;
  factors: RiskFactor[];
  recommendations: string[];
  fraud_indicators: string[];
  last_assessed_at: string;
}

export type AuthenticityStatus = 'pending' | 'verified' | 'flagged' | 'rejected';

export interface PropertyAuthenticityReportData {
  id: string;
  property_id: string;
  title_deed: TitleDeedVerification | null;
  ownership_check: OwnershipCheckResult | null;
  site_photos: SiteVerificationPhoto[];
  risk_assessment: RiskAssessment | null;
  overall_authenticity_score: number;
  status: AuthenticityStatus;
  created_at: string;
  updated_at: string;
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface PropertyAuthenticityReportProps {
  report: PropertyAuthenticityReportData | null;
  loading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
  className?: string;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

const statusConfig: Record<AuthenticityStatus, {
  label: string;
  icon: React.ReactNode;
  badgeVariant: 'success' | 'warning' | 'danger' | 'info';
  containerClass: string;
}> = {
  verified: {
    label: 'Verified',
    icon: <ShieldCheck className="w-5 h-5" />,
    badgeVariant: 'success',
    containerClass: 'bg-emerald-50 border-emerald-200 dark:bg-emerald-900/20 dark:border-emerald-800',
  },
  flagged: {
    label: 'Flagged',
    icon: <ShieldAlert className="w-5 h-5" />,
    badgeVariant: 'warning',
    containerClass: 'bg-amber-50 border-amber-200 dark:bg-amber-900/20 dark:border-amber-800',
  },
  rejected: {
    label: 'Rejected',
    icon: <ShieldX className="w-5 h-5" />,
    badgeVariant: 'danger',
    containerClass: 'bg-red-50 border-red-200 dark:bg-red-900/20 dark:border-red-800',
  },
  pending: {
    label: 'Pending',
    icon: <HelpCircle className="w-5 h-5" />,
    badgeVariant: 'info',
    containerClass: 'bg-blue-50 border-blue-200 dark:bg-blue-900/20 dark:border-blue-800',
  },
};

function getScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-amber-600';
  if (score >= 40) return 'text-orange-600';
  return 'text-red-600';
}

function getScoreBgColor(score: number): string {
  if (score >= 80) return 'bg-emerald-500';
  if (score >= 60) return 'bg-amber-500';
  if (score >= 40) return 'bg-orange-500';
  return 'bg-red-500';
}

function getRiskColor(risk: RiskLevel): string {
  switch (risk) {
    case 'low': return 'text-emerald-600';
    case 'medium': return 'text-amber-600';
    case 'high': return 'text-orange-600';
    case 'critical': return 'text-red-600';
  }
}

function getConfidenceBadge(c: 'high' | 'medium' | 'low'): 'success' | 'warning' | 'danger' {
  switch (c) {
    case 'high': return 'success';
    case 'medium': return 'warning';
    case 'low': return 'danger';
  }
}

const categoryLabels: Record<PhotoCategory, string> = {
  exterior: 'Exterior',
  interior: 'Interior',
  surroundings: 'Surroundings',
  documentation: 'Documentation',
};

const categoryIcons: Record<PhotoCategory, React.ReactNode> = {
  exterior: <Building2 className="w-4 h-4" />,
  interior: <Home className="w-4 h-4" />,
  surroundings: <MapPin className="w-4 h-4" />,
  documentation: <FileText className="w-4 h-4" />,
};

function formatDate(dateStr: string): string {
  try {
    return new Date(dateStr).toLocaleDateString('en-KE', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return dateStr;
  }
}

function formatRiskScore(score: number): string {
  return `${Math.round(Math.max(0, Math.min(100, score)))}%`;
}

const riskIcons: Record<RiskLevel, React.ReactNode> = {
  low: <CheckCircle2 className="w-5 h-5 text-emerald-600" />,
  medium: <AlertTriangle className="w-5 h-5 text-amber-600" />,
  high: <AlertCircle className="w-5 h-5 text-orange-600" />,
  critical: <XCircle className="w-5 h-5 text-red-600" />,
};

// ─── Sub-components ─────────────────────────────────────────────────────────

function PhotoGalleryModal({
  photos,
  initialIndex,
  isOpen,
  onClose,
}: {
  photos: SiteVerificationPhoto[];
  initialIndex: number;
  isOpen: boolean;
  onClose: () => void;
}) {
  const [currentIndex, setCurrentIndex] = React.useState(initialIndex);

  React.useEffect(() => {
    setCurrentIndex(initialIndex);
  }, [initialIndex]);

  const current = photos[currentIndex];
  if (!current) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Site Verification Photos" size="xl">
      <div className="p-6">
        {/* Main image */}
        <div className="relative w-full aspect-video rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 mb-4">
          {current.image_url ? (
            <Image
              src={current.image_url}
              alt={current.caption}
              fill
              className="object-cover"
              sizes="(max-width: 768px) 100vw, 800px"
              priority
            />
          ) : (
            <div className="flex items-center justify-center h-full">
              <ImageIcon className="w-12 h-12 text-gray-300 dark:text-gray-600" />
            </div>
          )}
        </div>

        {/* Photo details */}
        <div className="space-y-3">
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="font-semibold text-gray-900 dark:text-gray-100">{current.caption}</p>
              <div className="flex items-center gap-2 mt-1">
                <Badge variant="info">
                  {categoryIcons[current.category]}
                  <span className="ml-1">{categoryLabels[current.category]}</span>
                </Badge>
                {current.location_verified && (
                  <Badge variant="success">
                    <MapPin className="w-3 h-3 mr-0.5" />
                    Geo-verified
                  </Badge>
                )}
              </div>
            </div>
            <span className="text-xs text-gray-400 shrink-0">{formatDate(current.captured_at)}</span>
          </div>

          {current.uploaded_by && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Uploaded by: {current.uploaded_by}
            </p>
          )}

          {current.geotag && (
            <p className="text-xs text-gray-500 dark:text-gray-400 flex items-center gap-1">
              <MapPin className="w-3 h-3" />
              {current.geotag.latitude.toFixed(6)}, {current.geotag.longitude.toFixed(6)}
            </p>
          )}
        </div>

        {/* Thumbnail navigation */}
        {photos.length > 1 && (
          <div className="mt-6">
            <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-3">
              {currentIndex + 1} of {photos.length} photos
            </p>
            <div className="flex gap-2 overflow-x-auto pb-2">
              {photos.map((photo, idx) => (
                <button
                  key={photo.id}
                  onClick={() => setCurrentIndex(idx)}
                  className={cn(
                    'relative w-16 h-16 rounded-lg overflow-hidden flex-shrink-0 border-2 transition-all',
                    idx === currentIndex
                      ? 'border-emerald-500 ring-2 ring-emerald-200'
                      : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
                  )}
                  aria-label={`View photo ${idx + 1}: ${photo.caption}`}
                >
                  {photo.image_url ? (
                    <Image
                      src={photo.image_url}
                      alt={photo.caption}
                      fill
                      className="object-cover"
                      sizes="64px"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full bg-gray-100 dark:bg-gray-800">
                      <ImageIcon className="w-4 h-4 text-gray-400" />
                    </div>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Navigation buttons */}
        <div className="flex items-center justify-between mt-4">
          <Button
            variant="outline"
            size="sm"
            disabled={currentIndex === 0}
            onClick={() => setCurrentIndex((i) => Math.max(0, i - 1))}
            aria-label="Previous photo"
          >
            Previous
          </Button>
          <Button
            variant="outline"
            size="sm"
            disabled={currentIndex === photos.length - 1}
            onClick={() => setCurrentIndex((i) => Math.min(photos.length - 1, i + 1))}
            aria-label="Next photo"
          >
            Next
          </Button>
        </div>
      </div>
    </Modal>
  );
}

function TitleDeedSection({ deed }: { deed: TitleDeedVerification }) {
  const t = useTranslations();
  const [expanded, setExpanded] = React.useState(false);

  const deedStatusConfig: Record<string, { label: string; variant: 'success' | 'danger' | 'info' }> = {
    valid: { label: 'Valid', variant: 'success' },
    invalid: { label: 'Invalid', variant: 'danger' },
    pending: { label: 'Pending', variant: 'info' },
  };

  const statusInfo = deedStatusConfig[deed.status] || deedStatusConfig.pending;

  return (
    <div className="border border-gray-100 dark:border-gray-800 rounded-2xl bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
      <div className="flex items-center justify-between p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-900/20 flex items-center justify-center">
            <Landmark className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Title Deed</h4>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {deed.document_number}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label={expanded ? 'Collapse section' : 'Expand section'}
            aria-expanded={expanded}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 sm:px-5 pb-5 border-t border-gray-100 dark:border-gray-800 pt-4">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Registered Owner
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100 font-medium flex items-center gap-1.5">
                <UserCheck className="w-3.5 h-3.5 text-gray-400" />
                {deed.registered_owner}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Holder Name
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100">
                {deed.holder_name}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Land Size
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100">
                {deed.land_size_hectares.toLocaleString('en-KE', { maximumFractionDigits: 2 })} ha
                <span className="text-gray-400 mx-1">&middot;</span>
                {deed.land_size_acres.toLocaleString('en-KE', { maximumFractionDigits: 2 })} acres
              </dd>
            </div>

            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Location
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                <MapPin className="w-3.5 h-3.5 text-gray-400" />
                {deed.location}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Verified At
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                <Calendar className="w-3.5 h-3.5 text-gray-400" />
                {formatDate(deed.verified_at)}
              </dd>
            </div>

            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Document Number
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                <Hash className="w-3.5 h-3.5 text-gray-400" />
                {deed.document_number}
              </dd>
            </div>
          </dl>

          {/* Encumbrances */}
          {deed.encumbrances.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-1.5">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-500" />
                Encumbrances
              </p>
              <ul className="space-y-1.5" role="list">
                {deed.encumbrances.map((item, i) => (
                  <li
                    key={i}
                    className="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 border border-amber-100 dark:border-amber-800 rounded-lg px-3 py-2 flex items-start gap-2"
                  >
                    <span className="mt-0.5 shrink-0">&bull;</span>
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Notes */}
          {deed.notes && (
            <div className="mt-4 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-1">Notes</p>
              <p className="text-sm text-gray-700 dark:text-gray-300">{deed.notes}</p>
            </div>
          )}

          {/* Title deed image */}
          {deed.title_deed_image_url && (
            <div className="mt-4">
              <a
                href={deed.title_deed_image_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600 hover:text-emerald-700 dark:text-emerald-400 dark:hover:text-emerald-300 transition-colors"
              >
                <FileText className="w-3.5 h-3.5" />
                View title deed document
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function OwnershipCheckSection({ ownership }: { ownership: OwnershipCheckResult }) {
  const t = useTranslations();
  const [expanded, setExpanded] = React.useState(false);

  return (
    <div className="border border-gray-100 dark:border-gray-800 rounded-2xl bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
      <div className="flex items-center justify-between p-4 sm:p-5">
        <div className="flex items-center gap-3">
          <div className={cn(
            'w-10 h-10 rounded-xl flex items-center justify-center',
            ownership.is_owner
              ? 'bg-emerald-50 dark:bg-emerald-900/20'
              : 'bg-red-50 dark:bg-red-900/20'
          )}>
            {ownership.is_owner ? (
              <UserCheck className="w-5 h-5 text-emerald-600 dark:text-emerald-400" />
            ) : (
              <ShieldX className="w-5 h-5 text-red-600 dark:text-red-400" />
            )}
          </div>
          <div>
            <h4 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Ownership Check</h4>
            <p className={cn(
              'text-xs font-medium',
              ownership.is_owner ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'
            )}>
              {ownership.is_owner ? 'Owner matches' : 'Owner mismatch detected'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={getConfidenceBadge(ownership.confidence)}>
            {ownership.confidence} confidence
          </Badge>
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-7 h-7 rounded-lg flex items-center justify-center hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
            aria-label={expanded ? 'Collapse section' : 'Expand section'}
            aria-expanded={expanded}
          >
            {expanded ? (
              <ChevronUp className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            )}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="px-4 sm:px-5 pb-5 border-t border-gray-100 dark:border-gray-800 pt-4">
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Owner Name
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100 font-medium flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5 text-gray-400" />
                {ownership.owner_name}
              </dd>
            </div>

            {ownership.id_number && (
              <div>
                <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                  ID Number
                </dt>
                <dd className="text-sm text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                  <Hash className="w-3.5 h-3.5 text-gray-400" />
                  {ownership.id_number}
                </dd>
              </div>
            )}

            {ownership.phone_number && (
              <div>
                <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                  Phone Number
                </dt>
                <dd className="text-sm text-gray-900 dark:text-gray-100 flex items-center gap-1.5">
                  <Phone className="w-3.5 h-3.5 text-gray-400" />
                  {ownership.phone_number}
                </dd>
              </div>
            )}

            <div>
              <dt className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-1">
                Checked At
              </dt>
              <dd className="text-sm text-gray-900 dark:text-gray-100">
                {formatDate(ownership.checked_at)}
              </dd>
            </div>
          </dl>

          {/* Matched fields */}
          {ownership.matched_fields.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-emerald-600 dark:text-emerald-400 mb-2 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Matched Fields
              </p>
              <ul className="flex flex-wrap gap-2" role="list">
                {ownership.matched_fields.map((field, i) => (
                  <li key={i}>
                    <Badge variant="success">{field}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Mismatched fields */}
          {ownership.mismatched_fields.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-2 flex items-center gap-1.5">
                <XCircle className="w-3.5 h-3.5" />
                Mismatched Fields
              </p>
              <ul className="flex flex-wrap gap-2" role="list">
                {ownership.mismatched_fields.map((field, i) => (
                  <li key={i}>
                    <Badge variant="danger">{field}</Badge>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Previous owners */}
          {ownership.previous_owners.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-2">
                Previous Owners
              </p>
              <div className="space-y-2">
                {ownership.previous_owners.map((owner, i) => (
                  <div
                    key={i}
                    className="flex items-center justify-between p-2.5 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800"
                  >
                    <span className="text-sm text-gray-700 dark:text-gray-300">{owner.name}</span>
                    <span className="text-xs text-gray-400">{owner.period}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function SitePhotosSection({
  photos,
  onPhotoClick,
}: {
  photos: SiteVerificationPhoto[];
  onPhotoClick: (index: number) => void;
}) {
  const t = useTranslations();
  const [filter, setFilter] = React.useState<PhotoCategory | 'all'>('all');

  const filtered = filter === 'all' ? photos : photos.filter((p) => p.category === filter);

  const categories: Array<{ key: PhotoCategory | 'all'; label: string }> = [
    { key: 'all', label: 'All' },
    { key: 'exterior', label: 'Exterior' },
    { key: 'interior', label: 'Interior' },
    { key: 'surroundings', label: 'Surroundings' },
    { key: 'documentation', label: 'Documentation' },
  ];

  return (
    <div className="border border-gray-100 dark:border-gray-800 rounded-2xl bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
      <div className="p-4 sm:p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
              <Camera className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Site Photos</h4>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {photos.length} photo{photos.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        </div>

        {/* Filter tabs */}
        <div className="flex flex-wrap gap-2 mb-4" role="tablist" aria-label="Photo category filter">
          {categories.map((cat) => (
            <button
              key={cat.key}
              role="tab"
              aria-selected={filter === cat.key}
              onClick={() => setFilter(cat.key)}
              className={cn(
                'px-3 py-1.5 rounded-lg text-xs font-medium transition-all',
                filter === cat.key
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-gray-700'
              )}
            >
              {cat.label}
            </button>
          ))}
        </div>

        {/* Photo grid */}
        {filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-10 text-center">
            <Camera className="w-10 h-10 text-gray-300 dark:text-gray-600 mb-3" />
            <p className="text-sm text-gray-500 dark:text-gray-400">No photos in this category</p>
          </div>
        ) : (
          <div
            className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3"
            role="list"
            aria-label="Verification photos"
          >
            {filtered.map((photo, idx) => (
              <button
                key={photo.id}
                onClick={() => onPhotoClick(photos.indexOf(photo))}
                className="group relative aspect-[4/3] rounded-xl overflow-hidden bg-gray-100 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 hover:border-emerald-400 dark:hover:border-emerald-500 transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2"
                role="listitem"
                aria-label={`View photo: ${photo.caption}`}
              >
                {photo.image_url ? (
                  <Image
                    src={photo.image_url}
                    alt={photo.caption}
                    fill
                    className="object-cover transition-transform duration-300 group-hover:scale-105"
                    sizes="(max-width: 640px) 50vw, (max-width: 1024px) 33vw, 25vw"
                  />
                ) : (
                  <div className="flex items-center justify-center h-full">
                    <ImageIcon className="w-8 h-8 text-gray-300 dark:text-gray-600" />
                  </div>
                )}

                {/* Overlay on hover */}
                <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center">
                  <Eye className="w-6 h-6 text-white opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>

                {/* Badges */}
                <div className="absolute top-2 left-2 flex flex-wrap gap-1">
                  <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-md bg-black/50 text-white backdrop-blur-sm">
                    {categoryLabels[photo.category]}
                  </span>
                  {photo.location_verified && (
                    <span className="text-[10px] font-medium px-1.5 py-0.5 rounded-md bg-emerald-600/80 text-white backdrop-blur-sm flex items-center gap-0.5">
                      <MapPin className="w-2.5 h-2.5" />
                      GPS
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function RiskAssessmentSection({ assessment }: { assessment: RiskAssessment }) {
  const t = useTranslations();
  const [expanded, setExpanded] = React.useState(false);

  const riskBarColor = getScoreBgColor(100 - assessment.risk_score);

  return (
    <div className="border border-gray-100 dark:border-gray-800 rounded-2xl bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
      <div className="p-4 sm:p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className={cn(
              'w-10 h-10 rounded-xl flex items-center justify-center',
              assessment.overall_risk === 'low' ? 'bg-emerald-50 dark:bg-emerald-900/20' :
              assessment.overall_risk === 'medium' ? 'bg-amber-50 dark:bg-amber-900/20' :
              assessment.overall_risk === 'high' ? 'bg-orange-50 dark:bg-orange-900/20' :
              'bg-red-50 dark:bg-red-900/20'
            )}>
              <Scale className={cn(
                'w-5 h-5',
                getRiskColor(assessment.overall_risk)
              )} />
            </div>
            <div>
              <h4 className="font-semibold text-gray-900 dark:text-gray-100 text-sm">Risk Assessment</h4>
              <p className={cn('text-xs font-medium', getRiskColor(assessment.overall_risk))}>
                {assessment.overall_risk.toUpperCase()} risk
              </p>
            </div>
          </div>
          <span className="text-2xl font-bold tabular-nums" style={{ color: assessment.risk_score >= 70 ? '#ef4444' : assessment.risk_score >= 40 ? '#f59e0b' : '#10b981' }}>
            {formatRiskScore(assessment.risk_score)}
          </span>
        </div>

        {/* Risk score bar */}
        <div className="mb-4">
          <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400 mb-1.5">
            <span>Risk Level</span>
            <span className="font-semibold">{formatRiskScore(assessment.risk_score)}</span>
          </div>
          <div className="w-full h-2.5 bg-gray-100 dark:bg-gray-800 rounded-full overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all duration-700', riskBarColor)}
              style={{ width: `${assessment.risk_score}%` }}
              role="progressbar"
              aria-valuenow={assessment.risk_score}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`Risk score: ${assessment.risk_score}%`}
            />
          </div>
        </div>

        {/* Fraud indicators */}
        {assessment.fraud_indicators.length > 0 && (
          <div className="mb-4">
            <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-2 flex items-center gap-1.5">
              <AlertTriangle className="w-3.5 h-3.5" />
              Fraud Indicators
            </p>
            <ul className="space-y-1.5" role="list">
              {assessment.fraud_indicators.map((indicator, i) => (
                <li
                  key={i}
                  className="text-xs text-red-700 dark:text-red-300 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800 rounded-lg px-3 py-2 flex items-start gap-2"
                >
                  <span className="mt-0.5 shrink-0">&bull;</span>
                  {indicator}
                </li>
              ))}
            </ul>
          </div>
        )}

        {/* Toggle details */}
        <div className="flex items-center justify-between">
          <button
            onClick={() => setExpanded(!expanded)}
            className="inline-flex items-center gap-1 text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors"
            aria-expanded={expanded}
          >
            {expanded ? 'Hide details' : 'View details'}
            {expanded ? (
              <ChevronUp className="w-3.5 h-3.5" />
            ) : (
              <ChevronDown className="w-3.5 h-3.5" />
            )}
          </button>
          <span className="text-xs text-gray-400">Last assessed {formatDate(assessment.last_assessed_at)}</span>
        </div>

        {expanded && (
          <div className="mt-4 pt-4 border-t border-gray-100 dark:border-gray-800 space-y-4">
            {/* Risk factors */}
            {assessment.factors.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                  Risk Factors
                </p>
                <div className="space-y-2">
                  {assessment.factors.map((factor, i) => (
                    <div
                      key={i}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-xl border',
                        factor.severity === 'critical' ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800' :
                        factor.severity === 'high' ? 'bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800' :
                        factor.severity === 'medium' ? 'bg-amber-50 dark:bg-amber-900/20 border-amber-200 dark:border-amber-800' :
                        'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800'
                      )}
                    >
                      <div className="shrink-0 mt-0.5">
                        {riskIcons[factor.severity]}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-0.5">
                          <p className="text-sm font-semibold text-gray-900 dark:text-gray-100">
                            {factor.name}
                          </p>
                          <Badge
                            variant={
                              factor.severity === 'critical' ? 'danger' :
                              factor.severity === 'high' ? 'danger' :
                              factor.severity === 'medium' ? 'warning' : 'success'
                            }
                            className="capitalize"
                          >
                            {factor.severity}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-600 dark:text-gray-400">
                          {factor.description}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Recommendations */}
            {assessment.recommendations.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <Info className="w-3.5 h-3.5 text-blue-500" />
                  Recommendations
                </p>
                <ul className="space-y-2" role="list">
                  {assessment.recommendations.map((rec, i) => (
                    <li
                      key={i}
                      className="flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-100 dark:border-blue-800 rounded-xl text-xs text-blue-800 dark:text-blue-200"
                    >
                      <span className="w-5 h-5 rounded-full bg-blue-200 dark:bg-blue-800 text-blue-700 dark:text-blue-300 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5">
                        {i + 1}
                      </span>
                      {rec}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function AuthenticityGauge({ score }: { score: number }) {
  const radius = 56;
  const circumference = radius * 2 * Math.PI;
  const offset = circumference - (Math.min(100, Math.max(0, score)) / 100) * circumference;
  const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : score >= 40 ? '#f97316' : '#ef4444';

  return (
    <div className="relative inline-flex items-center justify-center" role="img" aria-label={`Authenticity score: ${score} out of 100`}>
      <svg width="140" height="140" className="transform -rotate-90">
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke="currentColor"
          strokeWidth="12"
          className="text-gray-100 dark:text-gray-800"
        />
        <circle
          cx="70"
          cy="70"
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth="12"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          style={{ transition: 'stroke-dashoffset 1s ease-out' }}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span
          className="text-3xl font-extrabold tabular-nums"
          style={{ color }}
        >
          {Math.round(score)}
        </span>
        <span className="text-[10px] font-medium text-gray-400 uppercase tracking-wider mt-0.5">
          Score
        </span>
      </div>
    </div>
  );
}

// ─── Main Loading State ─────────────────────────────────────────────────────

function LoadingState() {
  return (
    <div className="space-y-4" aria-label="Loading authenticity report">
      {/* Header skeleton */}
      <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-5 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Skeleton className="w-10 h-10 rounded-xl" />
            <div>
              <Skeleton className="h-5 w-48 rounded-md" />
              <Skeleton className="h-3.5 w-32 rounded-md mt-1.5" />
            </div>
          </div>
          <Skeleton className="w-20 h-6 rounded-full" />
        </div>
      </div>

      {/* Score gauge skeleton */}
      <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-6 shadow-sm">
        <div className="flex flex-col items-center">
          <Skeleton className="w-[140px] h-[140px] rounded-full" />
          <Skeleton className="h-4 w-40 rounded-md mt-3" />
        </div>
      </div>

      {/* Section skeletons */}
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 overflow-hidden shadow-sm">
          <div className="p-4 sm:p-5">
            <div className="flex items-center gap-3">
              <Skeleton className="w-10 h-10 rounded-xl" />
              <div className="flex-1">
                <Skeleton className="h-4 w-32 rounded-md" />
                <Skeleton className="h-3 w-24 rounded-md mt-1" />
              </div>
              <Skeleton className="w-16 h-5 rounded-full" />
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// ─── Main Error State ───────────────────────────────────────────────────────

function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="rounded-2xl border border-red-100 dark:border-red-800 bg-white dark:bg-gray-900 p-6 shadow-sm">
      <Alert
        variant="error"
        title="Failed to load authenticity report"
        description={message}
      >
        {onRetry && (
          <div className="mt-3">
            <Button
              variant="outline"
              size="sm"
              onClick={onRetry}
              leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
            >
              Try again
            </Button>
          </div>
        )}
      </Alert>
    </div>
  );
}

// ─── Empty State ────────────────────────────────────────────────────────────

function EmptyState({ onRefresh }: { onRefresh?: () => void }) {
  return (
    <div className="rounded-2xl border border-gray-100 dark:border-gray-800 bg-white dark:bg-gray-900 p-8 shadow-sm">
      <div className="flex flex-col items-center text-center max-w-sm mx-auto">
        <div className="w-16 h-16 rounded-2xl bg-gray-50 dark:bg-gray-800 flex items-center justify-center mb-4">
          <FileSearch className="w-8 h-8 text-gray-300 dark:text-gray-600" />
        </div>
        <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
          No authenticity report yet
        </h3>
        <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
          This property has not been verified. Run an authenticity check to get a detailed report with title deed verification, ownership check, and risk assessment.
        </p>
        {onRefresh && (
          <Button
            variant="primary"
            size="md"
            onClick={onRefresh}
            leftIcon={<Shield className="w-4 h-4" />}
          >
            Run authenticity check
          </Button>
        )}
      </div>
    </div>
  );
}

// ─── Main Component ─────────────────────────────────────────────────────────

export default function PropertyAuthenticityReport({
  report,
  loading = false,
  error = null,
  onRefresh,
  className,
}: PropertyAuthenticityReportProps) {
  const t = useTranslations();
  const [galleryOpen, setGalleryOpen] = React.useState(false);
  const [galleryIndex, setGalleryIndex] = React.useState(0);

  // Loading state
  if (loading) {
    return (
      <div className={cn('space-y-4', className)} role="status" aria-label="Loading">
        <LoadingState />
        <span className="sr-only">Loading authenticity report...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={cn('space-y-4', className)} role="alert">
        <ErrorState message={error} onRetry={onRefresh} />
      </div>
    );
  }

  // Empty state
  if (!report) {
    return (
      <div className={cn('space-y-4', className)}>
        <EmptyState onRefresh={onRefresh} />
      </div>
    );
  }

  const status = statusConfig[report.status] || statusConfig.pending;
  const hasSitePhotos = report.site_photos.length > 0;

  function handlePhotoClick(index: number) {
    setGalleryIndex(index);
    setGalleryOpen(true);
  }

  return (
    <div className={cn('space-y-4', className)}>
      {/* Photo gallery modal */}
      {hasSitePhotos && (
        <PhotoGalleryModal
          photos={report.site_photos}
          initialIndex={galleryIndex}
          isOpen={galleryOpen}
          onClose={() => setGalleryOpen(false)}
        />
      )}

      {/* ── Header card ── */}
      <Card className="overflow-hidden">
        <div className={cn('p-4 sm:p-6', status.containerClass)}>
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 rounded-xl bg-white/80 dark:bg-gray-800/80 flex items-center justify-center shadow-sm">
                {status.icon}
              </div>
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-gray-100 text-base sm:text-lg">
                  Property Authenticity Report
                </h3>
                <p className="text-xs sm:text-sm text-gray-600 dark:text-gray-400">
                  {report.property_id ? `Property #${report.property_id}` : ''}
                  <span className="mx-1.5">&middot;</span>
                  Updated {formatDate(report.updated_at)}
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              <Badge variant={status.badgeVariant} className="text-xs sm:text-sm px-3 py-1">
                {status.label}
              </Badge>
              {onRefresh && (
                <button
                  onClick={onRefresh}
                  className="w-8 h-8 rounded-xl flex items-center justify-center hover:bg-white/40 dark:hover:bg-gray-800/40 transition-colors"
                  aria-label="Refresh authenticity report"
                >
                  <RefreshCw className="w-4 h-4 text-gray-600 dark:text-gray-400" />
                </button>
              )}
            </div>
          </div>
        </div>
      </Card>

      {/* ── Authenticity score gauge ── */}
      <Card className="p-4 sm:p-6">
        <div className="flex flex-col items-center">
          <AuthenticityGauge score={report.overall_authenticity_score} />
          <div className="flex items-center gap-2 mt-3">
            <Shield className={cn('w-4 h-4', getScoreColor(report.overall_authenticity_score))} />
            <p className={cn('text-sm font-semibold', getScoreColor(report.overall_authenticity_score))}>
              {report.overall_authenticity_score >= 80 ? 'Highly authentic property' :
               report.overall_authenticity_score >= 60 ? 'Moderately authentic' :
               report.overall_authenticity_score >= 40 ? 'Needs further verification' :
               'Suspicious - proceed with caution'}
            </p>
          </div>

          {/* Summary metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 w-full">
            {[
              {
                label: 'Title Deed',
                icon: <Landmark className="w-4 h-4" />,
                status: report.title_deed?.status === 'valid' ? 'Verified' :
                        report.title_deed?.status === 'invalid' ? 'Invalid' :
                        report.title_deed ? 'Pending' : 'Not checked',
                color: report.title_deed?.status === 'valid' ? 'text-emerald-600' :
                       report.title_deed?.status === 'invalid' ? 'text-red-600' : 'text-gray-500',
              },
              {
                label: 'Ownership',
                icon: <UserCheck className="w-4 h-4" />,
                status: report.ownership_check
                  ? (report.ownership_check.is_owner ? 'Confirmed' : 'Mismatch')
                  : 'Not checked',
                color: report.ownership_check?.is_owner ? 'text-emerald-600' : 'text-red-600',
              },
              {
                label: 'Site Photos',
                icon: <Camera className="w-4 h-4" />,
                status: `${report.site_photos.length} photo${report.site_photos.length !== 1 ? 's' : ''}`,
                color: report.site_photos.length > 0 ? 'text-emerald-600' : 'text-gray-500',
              },
              {
                label: 'Risk Level',
                icon: <Scale className="w-4 h-4" />,
                status: report.risk_assessment
                  ? report.risk_assessment.overall_risk.charAt(0).toUpperCase() + report.risk_assessment.overall_risk.slice(1)
                  : 'Not assessed',
                color: report.risk_assessment
                  ? getRiskColor(report.risk_assessment.overall_risk)
                  : 'text-gray-500',
              },
            ].map((metric) => (
              <div
                key={metric.label}
                className="flex flex-col items-center p-3 bg-gray-50 dark:bg-gray-800/50 rounded-xl border border-gray-100 dark:border-gray-800"
              >
                <div className={cn('flex items-center gap-1.5 text-xs font-medium mb-1', metric.color)}>
                  {metric.icon}
                  <span>{metric.label}</span>
                </div>
                <span className={cn('text-xs font-bold', metric.color)}>
                  {metric.status}
                </span>
              </div>
            ))}
          </div>
        </div>
      </Card>

      {/* ── Title Deed Verification ── */}
      {report.title_deed ? (
        <TitleDeedSection deed={report.title_deed} />
      ) : (
        <Card className="p-4 sm:p-5">
          <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
            <Landmark className="w-5 h-5" />
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Title Deed Verification</p>
              <p className="text-xs">No title deed data available</p>
            </div>
          </div>
        </Card>
      )}

      {/* ── Ownership Check ── */}
      {report.ownership_check ? (
        <OwnershipCheckSection ownership={report.ownership_check} />
      ) : (
        <Card className="p-4 sm:p-5">
          <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
            <UserCheck className="w-5 h-5" />
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Ownership Check</p>
              <p className="text-xs">No ownership data available</p>
            </div>
          </div>
        </Card>
      )}

      {/* ── Site Verification Photos ── */}
      {hasSitePhotos ? (
        <SitePhotosSection
          photos={report.site_photos}
          onPhotoClick={handlePhotoClick}
        />
      ) : (
        <Card className="p-4 sm:p-5">
          <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
            <Camera className="w-5 h-5" />
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Site Verification Photos</p>
              <p className="text-xs">No site photos available</p>
            </div>
          </div>
        </Card>
      )}

      {/* ── Risk Assessment ── */}
      {report.risk_assessment ? (
        <RiskAssessmentSection assessment={report.risk_assessment} />
      ) : (
        <Card className="p-4 sm:p-5">
          <div className="flex items-center gap-3 text-gray-400 dark:text-gray-500">
            <Scale className="w-5 h-5" />
            <div>
              <p className="text-sm font-medium text-gray-500 dark:text-gray-400">Risk Assessment</p>
              <p className="text-xs">No risk assessment available</p>
            </div>
          </div>
        </Card>
      )}

      {/* ── Report footer ── */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 px-1">
        <p className="text-xs text-gray-400 dark:text-gray-500">
          Report ID: {report.id}
          <span className="mx-1.5">&middot;</span>
          Created: {formatDate(report.created_at)}
        </p>
        {onRefresh && (
          <Button
            variant="ghost"
            size="sm"
            onClick={onRefresh}
            leftIcon={<RefreshCw className="w-3.5 h-3.5" />}
          >
            Refresh report
          </Button>
        )}
      </div>
    </div>
  );
}
