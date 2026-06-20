'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import type { Payout } from '@/types';
import { ArrowLeft, DollarSign, CreditCard, TrendingUp } from 'lucide-react';

export default function CommissionsPage() {
  return (
    <AuthGuard requireAuth requireRoles={['agent']}>
      <CommissionsContent />
    </AuthGuard>
  );
}

function CommissionsContent() {
  const [payouts, setPayouts] = useState<Payout[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyPayouts()
      .then(r => setPayouts(Array.isArray(r.items) ? r.items : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const completed = payouts.filter(p => p.status === 'completed').reduce((s, p) => s + p.amount_kes, 0);
  const pending = payouts.filter(p => p.status === 'pending' || p.status === 'processing').reduce((s, p) => s + p.amount_kes, 0);

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/agent" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Commissions & Payouts</h1>
          <p className="text-sm text-gray-500">Your earnings at a glance</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4">
        <Card padding="md" className="text-center">
          <DollarSign className="w-8 h-8 text-emerald-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">KES {completed.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Total Earned</p>
        </Card>
        <Card padding="md" className="text-center">
          <CreditCard className="w-8 h-8 text-amber-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-amber-600">KES {pending.toLocaleString()}</p>
          <p className="text-xs text-gray-500">Pending Payout</p>
        </Card>
        <Card padding="md" className="text-center">
          <TrendingUp className="w-8 h-8 text-cyan-600 mx-auto mb-2" />
          <p className="text-2xl font-bold text-gray-900">{payouts.filter(p => p.status === 'completed').length}</p>
          <p className="text-xs text-gray-500">Payouts Received</p>
        </Card>
      </div>

      {payouts.length === 0 ? (
        <Card className="text-center py-20">
          <DollarSign className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No payouts yet</h2>
          <p className="text-gray-500 text-sm mb-6">Commissions from verified listings and deals will appear here.</p>
          <Link href="/wallet"><Button className="bg-cyan-600 hover:bg-cyan-500">Request Payout</Button></Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {payouts.map(payout => (
            <Card key={payout.id} padding="md">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-semibold text-gray-900">KES {payout.amount_kes.toLocaleString()}</p>
                  <p className="text-xs text-gray-500 capitalize">{payout.payout_type || 'Commission'} · {new Date(payout.created_at).toLocaleDateString()}</p>
                </div>
                <Badge variant={
                  payout.status === 'completed' ? 'success' :
                  payout.status === 'failed' ? 'danger' : 'warning'
                } className="text-xs capitalize">
                  {payout.status}
                </Badge>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
