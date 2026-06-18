'use client';

import { Shield, Clock, CheckCircle, XCircle, AlertTriangle, RefreshCw } from 'lucide-react';

interface KYCStatusProps {
  status: string;
  rejectionReason?: string;
  submittedAt?: string;
  reviewedAt?: string;
  idType?: string;
}

export function KYCStatus({ status, rejectionReason, submittedAt, reviewedAt, idType }: KYCStatusProps) {
  const config = STATUS_CONFIG[status] || STATUS_CONFIG.not_submitted;

  return (
    <div className={`rounded-2xl border p-6 ${config.bgClass}`}>
      <div className="flex items-start gap-4">
        <div className={`p-3 rounded-xl ${config.iconBg}`}>
          {config.icon}
        </div>
        <div className="flex-1">
          <h3 className={`text-lg font-bold ${config.textClass}`}>{config.label}</h3>
          <p className="text-sm text-gray-500 mt-1">{config.description}</p>

          {idType && (
            <p className="text-xs text-gray-400 mt-2">
              ID Type: {idType.replace('_', ' ').toUpperCase()}
            </p>
          )}

          {submittedAt && (
            <p className="text-xs text-gray-400 mt-1">
              Submitted: {new Date(submittedAt).toLocaleDateString('en-KE', { dateStyle: 'long' })}
            </p>
          )}

          {reviewedAt && (
            <p className="text-xs text-gray-400 mt-1">
              Reviewed: {new Date(reviewedAt).toLocaleDateString('en-KE', { dateStyle: 'long' })}
            </p>
          )}

          {rejectionReason && (
            <div className="mt-3 p-3 bg-red-50 border border-red-100 rounded-lg">
              <p className="text-xs font-medium text-red-700">Rejection Reason:</p>
              <p className="text-sm text-red-600 mt-1">{rejectionReason}</p>
            </div>
          )}
        </div>

        {/* Badge */}
        <div className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase ${config.badgeClass}`}>
          {status.replace('_', ' ')}
        </div>
      </div>
    </div>
  );
}

const STATUS_CONFIG: Record<string, {
  label: string;
  description: string;
  icon: React.ReactNode;
  bgClass: string;
  iconBg: string;
  textClass: string;
  badgeClass: string;
}> = {
  approved: {
    label: 'KYC Verified',
    description: 'Your identity has been verified. You can now access all platform features.',
    icon: <CheckCircle className="w-6 h-6 text-emerald-600" />,
    bgClass: 'bg-emerald-50 border-emerald-200',
    iconBg: 'bg-emerald-100',
    textClass: 'text-emerald-800',
    badgeClass: 'bg-emerald-600 text-white',
  },
  reviewing: {
    label: 'Under Review',
    description: 'Our team is reviewing your documents. This usually takes 1-2 business days.',
    icon: <Clock className="w-6 h-6 text-blue-600" />,
    bgClass: 'bg-blue-50 border-blue-200',
    iconBg: 'bg-blue-100',
    textClass: 'text-blue-800',
    badgeClass: 'bg-blue-600 text-white',
  },
  pending: {
    label: 'Awaiting Review',
    description: 'Your documents have been submitted and are in the review queue.',
    icon: <Clock className="w-6 h-6 text-amber-600" />,
    bgClass: 'bg-amber-50 border-amber-200',
    iconBg: 'bg-amber-100',
    textClass: 'text-amber-800',
    badgeClass: 'bg-amber-500 text-white',
  },
  rejected: {
    label: 'KYC Rejected',
    description: 'Your verification was not approved. Please review the reason and resubmit.',
    icon: <XCircle className="w-6 h-6 text-red-600" />,
    bgClass: 'bg-red-50 border-red-200',
    iconBg: 'bg-red-100',
    textClass: 'text-red-800',
    badgeClass: 'bg-red-600 text-white',
  },
  expired: {
    label: 'KYC Expired',
    description: 'Your verification has expired. Annual re-verification is required.',
    icon: <RefreshCw className="w-6 h-6 text-orange-600" />,
    bgClass: 'bg-orange-50 border-orange-200',
    iconBg: 'bg-orange-100',
    textClass: 'text-orange-800',
    badgeClass: 'bg-orange-500 text-white',
  },
  not_submitted: {
    label: 'Not Verified',
    description: 'Complete KYC verification to unlock all platform features and build trust.',
    icon: <Shield className="w-6 h-6 text-gray-400" />,
    bgClass: 'bg-gray-50 border-gray-200',
    iconBg: 'bg-gray-100',
    textClass: 'text-gray-700',
    badgeClass: 'bg-gray-400 text-white',
  },
};
