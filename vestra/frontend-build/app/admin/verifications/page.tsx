'use client';

import { useState, useEffect } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { CheckCircle, XCircle, AlertCircle, Clock, Shield, Search, Filter, ChevronDown, Eye } from 'lucide-react';

interface PendingVerification {
  id: number; property_id: number | null;
  fraud_risk_score: number | null; trust_score: number | null;
  ai_recommendation: string | null; status: string;
  created_at: string;
}

export default function AdminVerificationsPage() {
  return <AuthGuard requireAuth requireAdmin><VerificationsContent /></AuthGuard>;
}

function VerificationsContent() {
  const [verifications, setVerifications] = useState<PendingVerification[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('pending');
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [reviewing, setReviewing] = useState(false);
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState('');

  useEffect(() => { loadData(); }, [filter]);

  const loadData = async () => {
    setLoading(true); setError('');
    try {
      const data = await api.getPendingVerifications(50);
      if (Array.isArray(data)) {
        setVerifications(data.filter((v: PendingVerification) =>
          filter === 'all' ? true : v.status === filter
        ));
      }
    } catch (err: any) {
      setError('Failed to load verifications');
    } finally { setLoading(false); }
  };

  const handleReview = async (id: number, status: string) => {
    setReviewing(true);
    try {
      await api.reviewVerification(id, status, notes);
      setMessage(`Verification #${id} ${status}`);
      setExpandedId(null); setNotes('');
      loadData();
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Review failed');
    } finally { setReviewing(false); }
  };

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Verification Review Queue</h1>
          <p className="text-sm text-gray-500 mt-1">{verifications.length} items awaiting review</p>
        </div>
        <div className="flex gap-2">
          {['pending', 'flagged', 'approved', 'rejected', 'all'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize ${
                filter === f ? 'bg-emerald-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>{f}</button>
          ))}
        </div>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700"><AlertCircle className="w-4 h-4 inline mr-2" />{error}</div>}
      {message && <div className="mb-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-sm text-emerald-700"><CheckCircle className="w-4 h-4 inline mr-2" />{message}</div>}

      {verifications.length === 0 ? (
        <Card className="p-12 text-center">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No verifications to review.</p>
        </Card>
      ) : (
        <div className="bg-white rounded-2xl border overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs font-semibold text-gray-500 uppercase">
                <th className="px-6 py-3">ID</th>
                <th className="px-6 py-3">Property</th>
                <th className="px-6 py-3">Trust Score</th>
                <th className="px-6 py-3">Fraud Risk</th>
                <th className="px-6 py-3">AI Says</th>
                <th className="px-6 py-3">Status</th>
                <th className="px-6 py-3">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {verifications.map(v => (
                <>
                  <tr key={v.id} className={`hover:bg-gray-50 cursor-pointer ${expandedId === v.id ? 'bg-emerald-50' : ''}`}
                    onClick={() => setExpandedId(expandedId === v.id ? null : v.id)}>
                    <td className="px-6 py-3 font-mono text-xs">#{v.id}</td>
                    <td className="px-6 py-3">{v.property_id ? `#${v.property_id}` : 'N/A'}</td>
                    <td className="px-6 py-3 font-medium">{v.trust_score?.toFixed(0) ?? '-'}/100</td>
                    <td className="px-6 py-3"><span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      (v.fraud_risk_score ?? 0) > 50 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'
                    }`}>{v.fraud_risk_score?.toFixed(0) ?? '-'}/100</span></td>
                    <td className="px-6 py-3 capitalize">{v.ai_recommendation || '-'}</td>
                    <td className="px-6 py-3 capitalize">{v.status}</td>
                    <td className="px-6 py-3"><ChevronDown className={`w-4 h-4 text-gray-400 ${expandedId === v.id ? 'rotate-180' : ''}`} /></td>
                  </tr>
                  {expandedId === v.id && (
                    <tr><td colSpan={7} className="px-6 py-4 bg-gray-50">
                      <div className="flex gap-4">
                        <textarea value={notes} onChange={e => setNotes(e.target.value)}
                          className="flex-1 px-3 py-2 border rounded-lg text-sm" rows={2} placeholder="Review notes..." />
                        <div className="flex flex-col gap-2">
                          <Button size="sm" onClick={() => handleReview(v.id, 'approved')}
                            className="bg-emerald-600 hover:bg-emerald-700" loading={reviewing}>
                            <CheckCircle className="w-3 h-3 mr-1" />Approve
                          </Button>
                          <Button size="sm" onClick={() => handleReview(v.id, 'flagged')}
                            variant="outline" className="border-amber-300 text-amber-600" loading={reviewing}>
                            <AlertCircle className="w-3 h-3 mr-1" />Flag
                          </Button>
                          <Button size="sm" onClick={() => handleReview(v.id, 'rejected')}
                            variant="outline" className="border-red-300 text-red-600" loading={reviewing}>
                            <XCircle className="w-3 h-3 mr-1" />Reject
                          </Button>
                        </div>
                      </div>
                    </td></tr>
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
