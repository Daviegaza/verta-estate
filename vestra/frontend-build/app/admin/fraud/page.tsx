'use client';

import { useState, useEffect } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { Shield, AlertCircle, CheckCircle, XCircle, Search, Phone, Mail } from 'lucide-react';

export default function AdminFraudPage() {
  return <AuthGuard requireAuth requireAdmin><FraudContent /></AuthGuard>;
}

function FraudContent() {
  const [reports, setReports] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('pending');

  const loadReports = async () => {
    setLoading(true); setError('');
    try {
      const data = await api.getFraudReports(50, filter !== 'all' ? filter : undefined);
      setReports(data?.items || []);
    } catch {
      setError('Failed to load fraud reports');
    } finally { setLoading(false); }
  };

  useEffect(() => { loadReports(); }, [filter]);

  const handleReview = async (id: number, status: string) => {
    try {
      await api.reviewFraudReport(id, status);
      loadReports();
    } catch {}
  };

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Fraud Investigation</h1>
          <p className="text-sm text-gray-500 mt-1">{reports.length} reports to investigate</p>
        </div>
        <div className="flex gap-2">
          {['pending', 'investigating', 'confirmed', 'all'].map(f => (
            <button key={f} onClick={() => setFilter(f)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize ${
                filter === f ? 'bg-red-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>{f === 'false_report' ? 'Dismissed' : f}</button>
          ))}
        </div>
      </div>

      {reports.length === 0 ? (
        <Card className="p-12 text-center">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No fraud reports to review.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {reports.map((r: any) => (
            <Card key={r.id} className="p-4">
              <div className="flex items-start justify-between">
                <div className="space-y-2 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs text-gray-400">#{r.id}</span>
                    <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                      r.status === 'confirmed' ? 'bg-red-100 text-red-700' : 'bg-amber-100 text-amber-700'
                    } capitalize`}>{r.status}</span>
                  </div>
                  <p className="text-sm text-gray-900">{(r as any).description}</p>
                  <div className="flex items-center gap-4 text-xs text-gray-400">
                    {(r as any).reported_phone && <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{(r as any).reported_phone}</span>}
                    {(r as any).reported_email && <span className="flex items-center gap-1"><Mail className="w-3 h-3" />{(r as any).reported_email}</span>}
                    {(r as any).reported_title_deed && <span>Title Deed: {(r as any).reported_title_deed}</span>}
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => handleReview(r.id, 'confirmed')}
                    className="bg-red-600 hover:bg-red-700"><XCircle className="w-3 h-3 mr-1" />Confirm Fraud</Button>
                  <Button size="sm" variant="outline" onClick={() => handleReview(r.id, 'false_report')}>
                    <CheckCircle className="w-3 h-3 mr-1" />Dismiss</Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
