'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { ArrowLeft, Wrench, CheckCircle, Clock } from 'lucide-react';

export default function LandlordMaintenancePage() {
  return (
    <AuthGuard requireAuth requireRoles={['landlord']}>
      <MaintenanceContent />
    </AuthGuard>
  );
}

function MaintenanceContent() {
  const [requests, setRequests] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.client.get('/api/rentals/maintenance')
      .then(r => setRequests(Array.isArray(r.data) ? r.data : (r.data?.items || [])))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleResolve = async (id: number) => {
    try {
      await api.client.put(`/api/rentals/maintenance/${id}/resolve`);
      setRequests(prev => prev.map(r => r.id === id ? { ...r, status: 'resolved' } : r));
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed');
    }
  };

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  const pending = requests.filter(r => r.status !== 'resolved');

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/landlord" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Maintenance Requests</h1>
          <p className="text-sm text-gray-500">{pending.length} pending · {requests.length} total</p>
        </div>
      </div>

      {requests.length === 0 ? (
        <Card className="text-center py-20">
          <Wrench className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No maintenance requests</h2>
          <p className="text-gray-500 text-sm">All clear — no issues reported by tenants.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {requests.map(req => (
            <Card key={req.id} padding="md" className={req.status === 'pending' ? 'border-l-4 border-l-amber-500' : ''}>
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900 capitalize">{req.issue || req.title}</h3>
                    <Badge variant={
                      req.status === 'resolved' ? 'success' :
                      req.status === 'in_progress' ? 'info' : 'warning'
                    } className="text-xs capitalize">
                      {(req.status || 'pending').replace(/_/g, ' ')}
                    </Badge>
                  </div>
                  <p className="text-sm text-gray-600 mb-2">{req.description}</p>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    {req.tenant_name && <span>Tenant: {req.tenant_name}</span>}
                    {req.unit_name && <span>Unit: {req.unit_name}</span>}
                    <span>{new Date(req.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                {req.status !== 'resolved' && (
                  <Button
                    size="sm"
                    onClick={() => handleResolve(req.id)}
                    className="bg-emerald-600 hover:bg-emerald-500 flex-shrink-0"
                  >
                    <CheckCircle className="w-3 h-3 mr-1" />Resolve
                  </Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
