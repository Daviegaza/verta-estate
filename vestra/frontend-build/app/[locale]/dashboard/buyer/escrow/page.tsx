'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { ArrowLeft, Shield, DollarSign, Calendar } from 'lucide-react';

export default function EscrowPage() {
  return (
    <AuthGuard requireAuth requireRoles={['buyer']}>
      <EscrowContent />
    </AuthGuard>
  );
}

function EscrowContent() {
  const [escrows, setEscrows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyEscrows()
      .then(r => setEscrows(Array.isArray(r.items) ? r.items : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/buyer" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">My Escrows</h1>
          <p className="text-sm text-gray-500">Protected transactions</p>
        </div>
      </div>

      {escrows.length === 0 ? (
        <Card className="text-center py-20">
          <Shield className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No escrow transactions</h2>
          <p className="text-gray-500 text-sm">Escrow protects your money when buying property.</p>
        </Card>
      ) : (
        <div className="space-y-3">
          {escrows.map(escrow => (
            <Card key={escrow.id} padding="md">
              <div className="flex items-center justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900">Property #{escrow.property_id}</h3>
                    <Badge variant={
                      escrow.status === 'completed' ? 'success' :
                      escrow.status === 'disputed' ? 'danger' :
                      escrow.status === 'cancelled' ? 'default' : 'info'
                    } className="text-xs capitalize">
                      {escrow.status.replace(/_/g, ' ')}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />KES {escrow.amount_kes?.toLocaleString()}</span>
                    <span className="flex items-center gap-1"><Calendar className="w-3 h-3" />{new Date(escrow.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
                <Link href={`/properties/${escrow.property_id}`}>
                  <Button size="sm" variant="outline">View Property</Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
