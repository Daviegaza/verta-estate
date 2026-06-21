'use client';

import { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import type { Property } from '@/types';
import { formatCurrency } from '@/lib/utils';
import { ArrowLeft, Users, Eye, Phone, MessageSquare, Filter } from 'lucide-react';

export default function AgentLeadsPage() {
  return (
    <AuthGuard requireAuth requireRoles={['agent']}>
      <LeadsContent />
    </AuthGuard>
  );
}

function LeadsContent() {
  const [properties, setProperties] = useState<Property[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getMyProperties()
      .then(p => setProperties(Array.isArray(p) ? p : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const leadsData = useMemo(() =>
    properties
      .filter(p => (p.inquiries || 0) > 0)
      .sort((a, b) => (b.inquiries || 0) - (a.inquiries || 0)),
    [properties]
  );
  const totalLeads = useMemo(() => properties.reduce((sum, p) => sum + (p.inquiries || 0), 0), [properties]);

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center gap-3">
        <Link href="/dashboard/agent" className="p-2 hover:bg-gray-100 rounded-xl">
          <ArrowLeft className="w-5 h-5 text-gray-500" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Lead Pipeline</h1>
          <p className="text-sm text-gray-500">{totalLeads} total leads · {leadsData.length} listings with activity</p>
        </div>
      </div>

      {/* Pipeline stages summary */}
      <div className="grid grid-cols-4 gap-4">
        {[
          { stage: 'New', count: totalLeads, pct: 100, color: 'bg-blue-50 text-blue-700 border-blue-200' },
          { stage: 'Contacted', count: Math.round(totalLeads * 0.6), pct: 60, color: 'bg-amber-50 text-amber-700 border-amber-200' },
          { stage: 'Viewing', count: Math.round(totalLeads * 0.3), pct: 30, color: 'bg-purple-50 text-purple-700 border-purple-200' },
          { stage: 'Closed', count: Math.round(totalLeads * 0.1), pct: 10, color: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
        ].map(s => (
          <Card key={s.stage} padding="md" className={`text-center border ${s.color}`}>
            <p className="text-2xl font-bold">{s.count}</p>
            <p className="text-xs font-medium opacity-70">{s.stage}</p>
            <div className="w-full bg-gray-200 rounded-full h-1 mt-2">
              <div className="bg-current h-1 rounded-full opacity-30" style={{ width: `${s.pct}%` }} />
            </div>
          </Card>
        ))}
      </div>

      {leadsData.length === 0 ? (
        <Card className="text-center py-20">
          <Users className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No leads yet</h2>
          <p className="text-gray-500 text-sm mb-6">Add listings to start attracting leads. Verified listings get 5x more inquiries.</p>
          <Link href="/properties/new"><Button className="bg-cyan-600 hover:bg-cyan-500">Add Listing</Button></Link>
        </Card>
      ) : (
        <div className="space-y-3">
          {leadsData.map(prop => (
            <Card key={prop.id} padding="md">
              <div className="flex items-center justify-between">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h3 className="font-semibold text-gray-900 truncate">{prop.title}</h3>
                    <Badge variant="info" className="text-xs">{prop.city}</Badge>
                  </div>
                  <p className="text-sm font-bold text-cyan-600">{formatCurrency(prop.price, prop.currency)}</p>
                  <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                    <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5" />{prop.views || 0} views</span>
                    <span className="flex items-center gap-1 font-semibold text-cyan-600"><Users className="w-3.5 h-3.5" />{prop.inquiries || 0} leads</span>
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0 ml-4">
                  <Button size="sm" variant="outline" className="gap-1"><Phone className="w-3 h-3" />Contact</Button>
                  <Link href={`/properties/${prop.id}`}>
                    <Button size="sm" variant="ghost">View</Button>
                  </Link>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
