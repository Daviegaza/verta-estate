'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import {
  Upload, Camera, CheckCircle, XCircle, Clock, AlertCircle, ArrowLeft, FileText, Shield
} from 'lucide-react';

export default function KYCSettingsPage() {
  return (
    <AuthGuard requireAuth>
      <KYCContent />
    </AuthGuard>
  );
}

interface KYCStatusData {
  status: string;
  rejection_reason?: string;
  submitted_at?: string;
  reviewed_at?: string;
  id_type?: string;
}

type KYCFormState = 'loading' | 'not_submitted' | 'pending' | 'approved' | 'rejected';

function KYCContent() {
  const [kycStatus, setKycStatus] = useState<KYCStatusData | null>(null);
  const [formState, setFormState] = useState<KYCFormState>('loading');
  const [idType, setIdType] = useState('national_id');
  const [idNumber, setIdNumber] = useState('');
  const [idFront, setIdFront] = useState<File | null>(null);
  const [idBack, setIdBack] = useState<File | null>(null);
  const [selfie, setSelfie] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const frontRef = useRef<HTMLInputElement>(null);
  const backRef = useRef<HTMLInputElement>(null);
  const selfieRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadKYCStatus();
  }, []);

  const loadKYCStatus = async () => {
    setError('');
    try {
      const res = await api.client.get('/api/kyc/status');
      const data: KYCStatusData = res.data;
      setKycStatus(data);

      if (data.status === 'approved') {
        setFormState('approved');
      } else if (data.status === 'pending' || data.status === 'reviewing') {
        setFormState('pending');
      } else if (data.status === 'rejected' || data.status === 'expired') {
        setFormState('rejected');
      } else {
        setFormState('not_submitted');
      }
    } catch {
      setFormState('not_submitted');
    }
  };

  const handleFileDrop = useCallback((e: React.DragEvent, setter: (f: File) => void) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && (file.type.startsWith('image/') || file.type === 'application/pdf')) {
      setter(file);
    }
  }, []);

  const handleSubmit = async () => {
    if (!idNumber.trim()) {
      setError('ID number is required');
      return;
    }
    if (!idFront && !selfie) {
      setError('At least an ID front image or selfie is required');
      return;
    }

    setSubmitting(true);
    setError('');
    setSuccess('');
    try {
      const form = new FormData();
      form.append('id_type', idType);
      form.append('id_number', idNumber);
      if (idFront) form.append('id_front', idFront);
      if (idBack) form.append('id_back', idBack);
      if (selfie) form.append('selfie', selfie);

      await api.client.post('/api/kyc/submit', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setSuccess('KYC documents submitted successfully! Your verification is now pending review.');
      await loadKYCStatus();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit KYC. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (formState === 'loading') {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-32">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  const renderKYCForm = () => (
    <Card>
      <CardHeader>
        <CardTitle>
          <span className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-emerald-600" />
            Identity Verification
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {/* Instructions */}
        <div className="mb-6 p-4 bg-blue-50 border border-blue-200 rounded-xl text-sm text-blue-700">
          <p className="font-medium mb-1">Required Documents:</p>
          <ul className="list-disc list-inside space-y-1 text-blue-600">
            <li>National ID (front and back) or Passport</li>
            <li>A clear selfie/portrait photo</li>
          </ul>
        </div>

        {/* ID Type Selector */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-2">ID Type</label>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
            {[
              { value: 'national_id', label: 'National ID' },
              { value: 'passport', label: 'Passport' },
              { value: 'alien_id', label: 'Alien ID' },
              { value: 'driving_license', label: "Driver's License" },
            ].map((opt) => (
              <button
                key={opt.value}
                type="button"
                onClick={() => setIdType(opt.value)}
                className={`px-3 py-2 rounded-lg border text-sm font-medium transition-colors ${
                  idType === opt.value
                    ? 'border-emerald-500 bg-emerald-50 text-emerald-700'
                    : 'border-gray-200 text-gray-600 hover:border-gray-300'
                }`}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </div>

        {/* ID Number */}
        <div className="mb-5">
          <label className="block text-sm font-medium text-gray-700 mb-1.5">ID Number</label>
          <input
            value={idNumber}
            onChange={(e) => setIdNumber(e.target.value)}
            placeholder="Enter your ID number"
            className="block w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-gray-900 placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200"
          />
          <p className="mt-1.5 text-xs text-gray-400">
            Your ID number will be verified but never shared publicly
          </p>
        </div>

        {/* Upload Zones */}
        <div className="grid gap-4 md:grid-cols-3 mb-6">
          <FileDropZone
            label="ID Front"
            file={idFront}
            onDrop={(e) => handleFileDrop(e, setIdFront)}
            onClick={() => frontRef.current?.click()}
            accept="image/*,application/pdf"
          />
          <FileDropZone
            label="ID Back"
            file={idBack}
            onDrop={(e) => handleFileDrop(e, setIdBack)}
            onClick={() => backRef.current?.click()}
            accept="image/*,application/pdf"
          />
          <FileDropZone
            label="Selfie"
            file={selfie}
            onDrop={(e) => handleFileDrop(e, setSelfie)}
            onClick={() => selfieRef.current?.click()}
            accept="image/*"
            icon={<Camera className="w-5 h-5" />}
          />
        </div>

        {/* Hidden file inputs */}
        <input
          ref={frontRef}
          type="file"
          hidden
          accept="image/*,application/pdf"
          onChange={(e) => e.target.files?.[0] && setIdFront(e.target.files[0])}
        />
        <input
          ref={backRef}
          type="file"
          hidden
          accept="image/*,application/pdf"
          onChange={(e) => e.target.files?.[0] && setIdBack(e.target.files[0])}
        />
        <input
          ref={selfieRef}
          type="file"
          hidden
          accept="image/*"
          onChange={(e) => e.target.files?.[0] && setSelfie(e.target.files[0])}
        />

        {/* Error */}
        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {/* Submit */}
        <Button fullWidth size="lg" onClick={handleSubmit} loading={submitting}>
          <Upload className="w-4 h-4 mr-2" />
          Submit KYC for Review
        </Button>
      </CardContent>
    </Card>
  );

  const renderPending = () => (
    <Card className="bg-amber-50 border-amber-200">
      <CardContent>
        <div className="flex items-start gap-4 py-2">
          <div className="w-14 h-14 bg-amber-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <Clock className="w-7 h-7 text-amber-600" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-amber-800 mb-2">Verification in Progress</h2>
            <p className="text-amber-700 text-sm leading-relaxed">
              Your KYC documents are being reviewed by our team. This process typically
              takes <strong>24-48 hours</strong>. You will be notified once the verification
              is complete.
            </p>
            {kycStatus?.submitted_at && (
              <p className="text-xs text-amber-600 mt-3">
                Submitted: {new Date(kycStatus.submitted_at).toLocaleDateString('en-KE', { dateStyle: 'long' })}
              </p>
            )}
            <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-200/50 rounded-lg text-xs font-medium text-amber-800">
              <Clock className="w-3.5 h-3.5" />
              Pending Review
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const renderApproved = () => (
    <Card className="bg-emerald-50 border-emerald-200">
      <CardContent>
        <div className="flex items-start gap-4 py-2">
          <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <CheckCircle className="w-7 h-7 text-emerald-600" />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-2">
              <h2 className="text-xl font-bold text-emerald-800">Identity Verified</h2>
              <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-600 text-white">
                <CheckCircle className="w-3 h-3" />
                Verified
              </span>
            </div>
            <p className="text-emerald-700 text-sm leading-relaxed">
              Your identity has been verified successfully. You now have access to all
              platform features.
            </p>
            {kycStatus?.id_type && (
              <p className="text-xs text-emerald-600 mt-3">
                ID Type: {kycStatus.id_type.replace('_', ' ').toUpperCase()}
              </p>
            )}
            {kycStatus?.reviewed_at && (
              <p className="text-xs text-emerald-600 mt-1">
                Reviewed: {new Date(kycStatus.reviewed_at).toLocaleDateString('en-KE', { dateStyle: 'long' })}
              </p>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );

  const renderRejected = () => (
    <Card className="bg-red-50 border-red-200">
      <CardContent>
        <div className="flex items-start gap-4 py-2">
          <div className="w-14 h-14 bg-red-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <XCircle className="w-7 h-7 text-red-600" />
          </div>
          <div className="flex-1">
            <h2 className="text-xl font-bold text-red-800 mb-2">Verification Rejected</h2>
            <p className="text-red-700 text-sm leading-relaxed mb-3">
              Your KYC verification was not approved. Please review the reason below and
              resubmit with corrected documents.
            </p>
            {kycStatus?.rejection_reason && (
              <div className="p-3 bg-red-100 border border-red-200 rounded-xl mb-4">
                <p className="text-xs font-medium text-red-800 mb-1">Rejection Reason:</p>
                <p className="text-sm text-red-700">{kycStatus.rejection_reason}</p>
              </div>
            )}
            {kycStatus?.reviewed_at && (
              <p className="text-xs text-red-600 mb-4">
                Reviewed: {new Date(kycStatus.reviewed_at).toLocaleDateString('en-KE', { dateStyle: 'long' })}
              </p>
            )}
            <Button
              variant="danger"
              size="md"
              onClick={() => setFormState('not_submitted')}
              className="gap-2"
            >
              <FileText className="w-4 h-4" />
              Resubmit KYC
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        {/* Back Link */}
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-emerald-600 transition-colors mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Settings
        </Link>

        {/* Page Header */}
        <div className="flex items-center gap-4 mb-10">
          <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <Shield className="w-7 h-7 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">KYC Verification</h1>
            <p className="text-sm text-gray-500 mt-1">
              Verify your identity to unlock all platform features
            </p>
          </div>
        </div>

        {/* Success Message */}
        {success && (
          <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-sm text-emerald-700 flex items-center gap-2">
            <CheckCircle className="w-4 h-4 flex-shrink-0" />
            {success}
          </div>
        )}

        {/* Error Message */}
        {error && formState !== 'not_submitted' && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {/* Status-based content */}
        {formState === 'approved' && renderApproved()}
        {formState === 'pending' && renderPending()}
        {formState === 'rejected' && renderRejected()}
        {formState === 'not_submitted' && renderKYCForm()}
      </div>
    </div>
  );
}

// ─── File Drop Zone ────────────────────────────────────────────────────────────

function FileDropZone({
  label, file, onDrop, onClick, accept, icon,
}: {
  label: string;
  file: File | null;
  onDrop: (e: React.DragEvent) => void;
  onClick: () => void;
  accept: string;
  icon?: React.ReactNode;
}) {
  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => e.preventDefault()}
      onClick={onClick}
      className={`border-2 border-dashed rounded-xl p-4 text-center cursor-pointer transition-colors ${
        file
          ? 'border-emerald-400 bg-emerald-50'
          : 'border-gray-300 hover:border-emerald-300 hover:bg-gray-50'
      }`}
    >
      {file ? (
        <div>
          <CheckCircle className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
          <p className="text-xs font-medium text-emerald-700 truncate">{file.name}</p>
          <p className="text-xs text-emerald-500">{(file.size / 1024).toFixed(0)} KB</p>
        </div>
      ) : (
        <div>
          {icon || <Upload className="w-5 h-5 text-gray-400 mx-auto mb-1" />}
          <p className="text-xs font-medium text-gray-600">{label}</p>
          <p className="text-xs text-gray-400">Drop or click to upload</p>
        </div>
      )}
    </div>
  );
}
