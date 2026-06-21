'use client';

import { useState, useEffect } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import type { KYCVerification } from '@/types';
import { CheckCircle, XCircle, AlertCircle, Clock, Shield, Search, ChevronDown } from 'lucide-react';

export default function AdminKYCPage() {
  return (
    <AuthGuard requireAuth requireAdmin>
      <AdminKYCPageContent />
    </AuthGuard>
  );
}

function AdminKYCPageContent() {
  const [kycItems, setKycItems] = useState<KYCVerification[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [selectedKYC, setSelectedKYC] = useState<KYCVerification | null>(null);
  const [reviewStatus, setReviewStatus] = useState<'approved' | 'rejected' | null>(null);
  const [rejectionReason, setRejectionReason] = useState('');
  const [reviewing, setReviewing] = useState(false);
  const [filter, setFilter] = useState('pending');
  const [message, setMessage] = useState('');

  const loadKYCPending = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await api.getPendingKYC(50);
      if (data && data.items) {
        setKycItems(data.items.filter((item: KYCVerification) => {
          if (filter === 'all') return true;
          return item.status === filter;
        }));
        setTotal(data.total || 0);
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load KYC queue');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadKYCPending();
  }, [filter]);

  const handleReview = async (kycId: number, status: 'approved' | 'rejected') => {
    setReviewing(true);
    setMessage('');
    try {
      await api.reviewKYC(
        kycId,
        status,
        status === 'rejected' ? rejectionReason : undefined
      );
      setMessage(`KYC #${kycId} ${status}`);
      setSelectedKYC(null);
      setReviewStatus(null);
      setRejectionReason('');
      loadKYCPending();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to review KYC');
    } finally {
      setReviewing(false);
    }
  };

  const statusBadge = (status: string) => {
    const config: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
      pending: { color: 'bg-amber-100 text-amber-700', icon: <Clock className="w-3 h-3" />, label: 'Pending' },
      reviewing: { color: 'bg-blue-100 text-blue-700', icon: <Shield className="w-3 h-3" />, label: 'Reviewing' },
      approved: { color: 'bg-emerald-100 text-emerald-700', icon: <CheckCircle className="w-3 h-3" />, label: 'Approved' },
      rejected: { color: 'bg-red-100 text-red-700', icon: <XCircle className="w-3 h-3" />, label: 'Rejected' },
    };
    const c = config[status] || config.pending;
    return (
      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${c.color}`}>
        {c.icon}
        {c.label}
      </span>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-32">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">KYC Review Queue</h1>
          <p className="text-sm text-gray-500 mt-1">
            {total} pending verification(s) requiring review
          </p>
        </div>
        <div className="flex gap-2">
          {['pending', 'reviewing', 'approved', 'rejected', 'all'].map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition-colors ${
                filter === f
                  ? 'bg-emerald-600 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {f}
            </button>
          ))}
          <Button onClick={loadKYCPending} variant="outline" size="sm">
            Refresh
          </Button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700 flex items-center gap-2">
          <CheckCircle className="w-4 h-4" />
          {message}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center gap-2">
          <AlertCircle className="w-4 h-4" />
          {error}
        </div>
      )}

      {/* Empty state */}
      {kycItems.length === 0 && !loading && (
        <Card className="p-12 text-center">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-gray-700 mb-2">No KYC submissions</h3>
          <p className="text-sm text-gray-500">
            {filter === 'pending' ? 'All KYC submissions have been reviewed.' : 'No KYC records found.'}
          </p>
        </Card>
      )}

      {/* KYC Table */}
      {kycItems.length > 0 && (
        <div className="bg-white rounded-2xl border border-gray-200 overflow-hidden">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase">
                <th className="px-6 py-3">KYC ID</th>
                <th className="px-6 py-3">User ID</th>
                <th className="px-6 py-3">ID Type</th>
                <th className="px-6 py-3">ID Number</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Submitted</th>
                <th className="px-6 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {kycItems.map((kyc) => (
                <>
                  <tr
                    key={kyc.id}
                    className={`text-sm hover:bg-gray-50 cursor-pointer transition-colors ${
                      selectedKYC?.id === kyc.id ? 'bg-emerald-50' : ''
                    }`}
                    onClick={() => {
                      setSelectedKYC(selectedKYC?.id === kyc.id ? null : kyc);
                      setReviewStatus(null);
                      setRejectionReason('');
                    }}
                  >
                    <td className="px-6 py-3 font-mono text-xs">#{kyc.id}</td>
                    <td className="px-6 py-3">User #{kyc.user_id}</td>
                    <td className="px-6 py-3 capitalize">{kyc.id_type?.replace('_', ' ')}</td>
                    <td className="px-6 py-3 font-mono text-xs">{kyc.id_number}</td>
                    <td className="px-6 py-3">{statusBadge(kyc.status)}</td>
                    <td className="px-6 py-3 text-xs text-gray-400">
                      {kyc.created_at ? new Date(kyc.created_at).toLocaleDateString() : '-'}
                    </td>
                    <td className="px-6 py-3">
                      <ChevronDown className={`w-4 h-4 text-gray-400 transition-transform ${
                        selectedKYC?.id === kyc.id ? 'rotate-180' : ''
                      }`} />
                    </td>
                  </tr>

                  {/* Expanded Review Panel */}
                  {selectedKYC?.id === kyc.id && (
                    <tr key={`review-${kyc.id}`}>
                      <td colSpan={7} className="px-6 py-4 bg-gray-50">
                        <div className="flex items-start gap-6">
                          <div className="flex-1">
                            <h4 className="font-semibold text-gray-900 mb-2">Review KYC #{kyc.id}</h4>

                            {!reviewStatus ? (
                              <div className="flex gap-3">
                                <Button
                                  onClick={() => setReviewStatus('approved')}
                                  className="bg-emerald-600 hover:bg-emerald-700"
                                  size="sm"
                                >
                                  <CheckCircle className="w-4 h-4 mr-1" />
                                  Approve
                                </Button>
                                <Button
                                  onClick={() => setReviewStatus('rejected')}
                                  variant="outline"
                                  className="border-red-300 text-red-600 hover:bg-red-50"
                                  size="sm"
                                >
                                  <XCircle className="w-4 h-4 mr-1" />
                                  Reject
                                </Button>
                              </div>
                            ) : (
                              <div className="space-y-3">
                                {reviewStatus === 'rejected' && (
                                  <div>
                                    <label className="block text-sm font-medium text-gray-700 mb-1">
                                      Rejection Reason
                                    </label>
                                    <textarea
                                      value={rejectionReason}
                                      onChange={(e) => setRejectionReason(e.target.value)}
                                      className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                                      rows={3}
                                      placeholder="Explain why this KYC was rejected..."
                                    />
                                  </div>
                                )}
                                <div className="flex gap-3">
                                  <Button
                                    onClick={() => handleReview(kyc.id, reviewStatus)}
                                    loading={reviewing}
                                    size="sm"
                                    className={reviewStatus === 'approved' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-red-600 hover:bg-red-700'}
                                  >
                                    Confirm {reviewStatus === 'approved' ? 'Approval' : 'Rejection'}
                                  </Button>
                                  <Button
                                    onClick={() => { setReviewStatus(null); setRejectionReason(''); }}
                                    variant="ghost"
                                    size="sm"
                                    disabled={reviewing}
                                  >
                                    Cancel
                                  </Button>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
