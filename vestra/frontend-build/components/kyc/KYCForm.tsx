'use client';

import { useState, useCallback, useRef } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import { Upload, Camera, Check, AlertCircle, FileText } from 'lucide-react';
import api from '@/lib/api';

interface KYCFormProps {
  onSubmitted: () => void;
  existingStatus?: string;
}

export function KYCForm({ onSubmitted, existingStatus }: KYCFormProps) {
  const [idType, setIdType] = useState('national_id');
  const [idNumber, setIdNumber] = useState('');
  const [idFront, setIdFront] = useState<File | null>(null);
  const [idBack, setIdBack] = useState<File | null>(null);
  const [selfie, setSelfie] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  const frontRef = useRef<HTMLInputElement>(null);
  const backRef = useRef<HTMLInputElement>(null);
  const selfieRef = useRef<HTMLInputElement>(null);

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
      setSuccess(true);
      onSubmitted();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to submit KYC. Please try again.');
    } finally {
      setSubmitting(false);
    }
  };

  if (success) {
    return (
      <Card className="p-6 bg-emerald-50 border-emerald-200 text-center">
        <Check className="w-12 h-12 text-emerald-500 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-emerald-800 mb-2">KYC Submitted!</h3>
        <p className="text-sm text-emerald-600">
          Your documents are under review. This usually takes 1-2 business days.
        </p>
      </Card>
    );
  }

  return (
    <Card className="p-6">
      <h2 className="text-xl font-bold text-gray-900 mb-6">Identity Verification (KYC)</h2>

      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-start gap-2">
          <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
          {error}
        </div>
      )}

      <div className="space-y-5">
        {/* ID Type */}
        <div>
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
        <Input
          label="ID Number"
          value={idNumber}
          onChange={(e) => setIdNumber(e.target.value)}
          placeholder="Enter your ID number"
          hint="Your ID number will be verified but never shared publicly"
        />

        {/* File Uploads */}
        <div className="grid gap-4 md:grid-cols-3">
          {/* ID Front */}
          <FileDropZone
            label="ID Front"
            file={idFront}
            onDrop={(e) => handleFileDrop(e, setIdFront)}
            onClick={() => frontRef.current?.click()}
            accept="image/*,application/pdf"
          />
          {/* ID Back */}
          <FileDropZone
            label="ID Back"
            file={idBack}
            onDrop={(e) => handleFileDrop(e, setIdBack)}
            onClick={() => backRef.current?.click()}
            accept="image/*,application/pdf"
          />
          {/* Selfie */}
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
        <input ref={frontRef} type="file" hidden accept="image/*,application/pdf"
          onChange={(e) => e.target.files?.[0] && setIdFront(e.target.files[0])} />
        <input ref={backRef} type="file" hidden accept="image/*,application/pdf"
          onChange={(e) => e.target.files?.[0] && setIdBack(e.target.files[0])} />
        <input ref={selfieRef} type="file" hidden accept="image/*"
          onChange={(e) => e.target.files?.[0] && setSelfie(e.target.files[0])} />

        {!['approved', 'reviewing', 'pending'].includes(existingStatus || '') && (
          <Button fullWidth size="lg" onClick={handleSubmit} loading={submitting}>
            <FileText className="w-4 h-4 mr-2" />
            Submit KYC for Review
          </Button>
        )}
      </div>
    </Card>
  );
}

// Local file drop zone component
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
          <Check className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
          <p className="text-xs font-medium text-emerald-700 truncate">{file.name}</p>
          <p className="text-xs text-emerald-500">{(file.size / 1024).toFixed(0)} KB</p>
        </div>
      ) : (
        <div>
          {icon || <Upload className="w-5 h-5 text-gray-400 mx-auto mb-1" />}
          <p className="text-xs font-medium text-gray-600">{label}</p>
          <p className="text-xs text-gray-400">Drop or click</p>
        </div>
      )}
    </div>
  );
}
