'use client';

import { useState, useEffect } from 'react';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { CheckCircle, AlertCircle, Shield, ChevronDown, Users } from 'lucide-react';

export default function AdminDisputesPage() {
  return <AuthGuard requireAuth requireAdmin><DisputesContent /></AuthGuard>;
}

function DisputesContent() {
  const [disputes, setDisputes] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const loadDisputes = async () => {
    setLoading(true);
    try {
      const res = await api.client.get('/api/admin/disputes?limit=50');
      setDisputes(res.data?.items || res.data || []);
    } catch {
      setError('Failed to load disputes');
    } finally { setLoading(false); }
  };

  useEffect(() => { loadDisputes(); }, []);

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="p-6 max-w-7xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Dispute Management</h1>
        <p className="text-sm text-gray-500 mt-1">Review and resolve user disputes</p>
      </div>

      {error && <div className="mb-4 p-3 bg-red-50 rounded-lg text-sm text-red-700"><AlertCircle className="w-4 h-4 inline mr-2" />{error}</div>}

      {disputes.length === 0 ? (
        <Card className="p-12 text-center">
          <Shield className="w-12 h-12 text-gray-300 mx-auto mb-3" />
          <p className="text-gray-500">No active disputes.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {disputes.map((d: any) => (
            <Card key={d.id} className="p-4">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-mono text-xs text-gray-400">#{d.id}</span>
                    <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 capitalize">
                      {d.status || 'open'}
                    </span>
                    <span className="text-xs text-gray-400">{(d as any).category}</span>
                  </div>
                  <p className="text-sm text-gray-900">{(d as any).description}</p>
                </div>
                <Button size="sm" variant="outline">Review</Button>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
