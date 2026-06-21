'use client';

import { useState } from 'react';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/card';
import TrustScoreCard from '@/components/verify/TrustScoreCard';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { Verification } from '@/types';
import {
  ShieldCheck, Upload, FileText, AlertCircle,
  CheckCircle2, Clock, Smartphone, ChevronRight
} from 'lucide-react';
import Link from 'next/link';

type Step = 'input' | 'upload' | 'payment' | 'processing' | 'result';

export default function VerifyPage() {
  const { isAuthenticated } = useAuthStore();
  const [step, setStep] = useState<Step>('input');
  const [propertyId, setPropertyId] = useState<number | null>(null);
  const [propertyIdInput, setPropertyIdInput] = useState('');
  const [phone, setPhone] = useState('');
  const [verification, setVerification] = useState<Verification | null>(null);
  const [paymentId, setPaymentId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadedDocs, setUploadedDocs] = useState<string[]>([]);
  const [uploadProgress, setUploadProgress] = useState(0);

  const handlePropertySubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const id = parseInt(propertyIdInput);
    if (!id || isNaN(id)) { setError('Please enter a valid property ID'); return; }
    try {
      await api.getProperty(id);
      setPropertyId(id);
      setStep('upload');
      setError('');
    } catch {
      setError('Property not found. Please check the ID and try again.');
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || !propertyId) return;
    const file = e.target.files[0];
    setLoading(true);
    try {
      await api.uploadDocument(propertyId, 'title_deed', file, setUploadProgress);
      setUploadedDocs((prev) => [...prev, file.name]);
      setError('');
    } catch {
      setError('Upload failed. Please try again.');
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  const handlePayment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!propertyId) return;
    setLoading(true);
    setError('');
    try {
      const result = await api.requestVerification(propertyId, phone);
      setPaymentId(result.payment_id);
      setStep('processing');
      pollForResult(result.payment_id);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Payment initiation failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleRunNow = async () => {
    if (!propertyId) return;
    setStep('processing');
    setLoading(true);
    try {
      const result = await api.runVerificationNow(propertyId);
      await pollVerification(result.id);
    } catch (err: any) {
      setError('Verification failed. Please try again.');
      setStep('payment');
    } finally {
      setLoading(false);
    }
  };

  const pollForResult = (pId: number) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      attempts++;
      try {
        const payment = await api.getPaymentStatus(pId);
        if (payment.status === 'completed') {
          clearInterval(interval);
          await handleRunNow();
        } else if (payment.status === 'failed' || attempts > 30) {
          clearInterval(interval);
          setError('Payment failed or timed out. Please try again.');
          setStep('payment');
        }
      } catch { clearInterval(interval); }
    }, 3000);
  };

  const pollVerification = async (vId: number) => {
    let attempts = 0;
    const poll = async () => {
      try {
        const v = await api.getVerificationStatus(vId);
        if (['approved', 'flagged', 'rejected'].includes(v.status)) {
          setVerification(v);
          setStep('result');
        } else if (attempts < 20) {
          attempts++;
          setTimeout(poll, 3000);
        }
      } catch { console.error('Poll error'); }
    };
    setTimeout(poll, 2000);
  };

  const STEPS = [
    { key: 'input', label: 'Property', icon: <FileText className="w-4 h-4" /> },
    { key: 'upload', label: 'Documents', icon: <Upload className="w-4 h-4" /> },
    { key: 'payment', label: 'Payment', icon: <Smartphone className="w-4 h-4" /> },
    { key: 'result', label: 'Report', icon: <ShieldCheck className="w-4 h-4" /> },
  ];
  const stepOrder = ['input', 'upload', 'payment', 'processing', 'result'];
  const currentStepIndex = stepOrder.indexOf(step);

  if (!isAuthenticated) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-lg mx-auto px-4 py-32 text-center">
          <ShieldCheck className="w-16 h-16 text-emerald-500 mx-auto mb-6" />
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Verify a Property</h1>
          <p className="text-gray-500 mb-8">Create a free account to get instant AI-powered property trust reports.</p>
          <div className="flex gap-3 justify-center">
            <Link href="/auth/register"><Button size="lg">Create Free Account</Button></Link>
            <Link href="/auth/login"><Button size="lg" variant="outline">Sign In</Button></Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-2xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-14 h-14 bg-emerald-100 rounded-2xl mb-4">
            <ShieldCheck className="w-7 h-7 text-emerald-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Property Verification</h1>
          <p className="text-gray-500 mt-2">Get an AI Trust Report in under 5 minutes — KES 500</p>
        </div>

        {/* Step indicator */}
        {step !== 'processing' && step !== 'result' && (
          <div className="flex items-center justify-center mb-10 overflow-x-auto pb-2">
            {STEPS.map((s, i) => {
              const sIdx = stepOrder.indexOf(s.key);
              const isActive = s.key === step;
              const isDone = currentStepIndex > sIdx;
              return (
                <div key={s.key} className="flex items-center flex-shrink-0">
                  <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition-all shadow-sm ${
                    isActive ? 'bg-emerald-600 text-white shadow-emerald-200' :
                    isDone ? 'bg-emerald-100 text-emerald-800' :
                    'bg-gray-200 text-gray-700'
                  }`}>
                    {isDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : s.icon}
                    {s.label}
                  </div>
                  {i < STEPS.length - 1 && <ChevronRight className="w-3.5 h-3.5 text-gray-400 mx-0.5" />}
                </div>
              );
            })}
          </div>
        )}

        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl flex items-center gap-3 text-sm text-red-700">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            {error}
          </div>
        )}

        {/* Step: Enter property ID */}
        {step === 'input' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Enter Property ID</h2>
            <p className="text-gray-500 text-sm mb-6">Enter the Vestra Property ID from the listing you want to verify.</p>
            <form onSubmit={handlePropertySubmit} className="space-y-4">
              <Input
                label="Property ID"
                value={propertyIdInput}
                onChange={(e) => setPropertyIdInput(e.target.value)}
                placeholder="e.g. 1042"
                type="number"
                required
              />
              <Button type="submit" fullWidth size="lg">
                Find Property <ChevronRight className="w-4 h-4" />
              </Button>
            </form>
            <div className="mt-6 p-4 bg-blue-50 border border-blue-100 rounded-xl text-sm text-blue-700">
              <strong>Tip:</strong> You can find the Property ID on any listing page — it appears as &ldquo;Property #ID&rdquo; near the title.
            </div>
          </div>
        )}

        {/* Step: Upload documents */}
        {step === 'upload' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Upload Documents</h2>
            <p className="text-gray-500 text-sm mb-6">
              Upload any available documents (title deed, agreement, etc.). More documents = higher accuracy.
            </p>

            <div className="border-2 border-dashed border-gray-300 rounded-2xl p-8 text-center hover:border-emerald-400 transition-colors bg-gray-50">
              <Upload className="w-10 h-10 text-gray-400 mx-auto mb-3" />
              <p className="text-gray-700 font-medium mb-1">Drag & drop or click to upload</p>
              <p className="text-xs text-gray-500 mb-4">PDF, JPG, PNG — Max 10MB</p>
              <label className="cursor-pointer">
                <span className="bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-medium px-4 py-2 rounded-xl transition-colors">
                  {loading ? 'Uploading...' : 'Choose File'}
                </span>
                <input type="file" className="hidden" onChange={handleFileUpload} accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" disabled={loading} />
              </label>
              {uploadProgress > 0 && uploadProgress < 100 && (
                <div className="mt-4">
                  <div className="bg-gray-100 rounded-full h-2">
                    <div className="bg-emerald-500 h-2 rounded-full transition-all" style={{ width: `${uploadProgress}%` }} />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">{uploadProgress}%</p>
                </div>
              )}
            </div>

            {uploadedDocs.length > 0 && (
              <div className="mt-4 space-y-2">
                {uploadedDocs.map((doc, i) => (
                  <div key={i} className="flex items-center gap-2 p-3 bg-emerald-50 border border-emerald-200 rounded-xl">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                    <span className="text-sm text-emerald-800 truncate">{doc}</span>
                  </div>
                ))}
              </div>
            )}

            <div className="mt-6 flex gap-3">
              <Button variant="outline" fullWidth onClick={() => setStep('input')}>Back</Button>
              <Button fullWidth onClick={() => setStep('payment')}>
                Continue {uploadedDocs.length > 0 ? `(${uploadedDocs.length} docs)` : '(skip)'}
              </Button>
            </div>
          </div>
        )}

        {/* Step: Payment */}
        {step === 'payment' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
            <h2 className="text-xl font-semibold text-gray-900 mb-2">Pay & Run Verification</h2>
            <div className="bg-gray-50 rounded-xl p-4 mb-6">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-600">AI Property Trust Report</span>
                <span className="font-bold text-gray-900">KES 500</span>
              </div>
              <div className="flex justify-between items-center mt-2">
                <span className="text-xs text-gray-400">Property ID: #{propertyId}</span>
                <span className="text-xs text-emerald-600">One-time fee</span>
              </div>
            </div>
            <form onSubmit={handlePayment} className="space-y-4">
              <Input
                label="M-Pesa Phone Number"
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                placeholder="0712 345 678"
                required
                hint="You'll receive an STK Push on this number"
                leftElement={<Smartphone className="w-4 h-4" />}
              />
              <Button type="submit" fullWidth size="lg" loading={loading}>
                Pay KES 500 via M-Pesa
              </Button>
            </form>
            <div className="mt-4 text-center">
              <button onClick={handleRunNow} className="text-sm text-emerald-600 hover:text-emerald-700 underline font-medium">
                Skip payment — run demo verification
              </button>
            </div>
            <div className="flex gap-3 mt-4">
              <Button variant="outline" fullWidth onClick={() => setStep('upload')}>Back</Button>
            </div>
          </div>
        )}

        {/* Step: Processing */}
        {step === 'processing' && (
          <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-12 text-center">
            <div className="relative w-20 h-20 mx-auto mb-6">
              <div className="w-20 h-20 rounded-full border-4 border-emerald-100 flex items-center justify-center">
                <ShieldCheck className="w-10 h-10 text-emerald-500" />
              </div>
              <div className="absolute inset-0 rounded-full border-4 border-transparent border-t-emerald-500 animate-spin" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">AI is Analyzing the Property</h2>
            <p className="text-gray-500 text-sm mb-4">
              Our AI is checking ownership records, document authenticity, pricing, and fraud signals...
            </p>
            <div className="space-y-2 text-left max-w-xs mx-auto">
              {['Checking title deed...', 'Analyzing market price...', 'Detecting fraud signals...', 'Calculating Trust Score...'].map((item, i) => (
                <div key={i} className="flex items-center gap-2 text-sm text-gray-400">
                  <Clock className="w-3.5 h-3.5 text-emerald-500" />
                  {item}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Step: Result */}
        {step === 'result' && verification && (
          <div className="space-y-4">
            <TrustScoreCard verification={verification} />
            <div className="flex gap-3">
              <Button variant="outline" fullWidth onClick={() => { setStep('input'); setPropertyId(null); setVerification(null); setUploadedDocs([]); setPropertyIdInput(''); }}>
                Verify Another Property
              </Button>
              <Link href="/dashboard" className="flex-1">
                <Button fullWidth>View Dashboard</Button>
              </Link>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
