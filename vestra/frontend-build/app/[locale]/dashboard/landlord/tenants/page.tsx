'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import {
  ArrowLeft, Users, Phone, Calendar, Home, DollarSign,
  Plus, UserPlus, Mail, IdCard, Search, Wrench,
  CreditCard, Building2, CheckCircle, X, AlertCircle,
} from 'lucide-react';

export default function LandlordTenantsPage() {
  return (
    <AuthGuard requireAuth requireRoles={['landlord']}>
      <TenantsContent />
    </AuthGuard>
  );
}

function TenantsContent() {
  const [units, setUnits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [collectingId, setCollectingId] = useState<number | null>(null);
  const [showAddTenant, setShowAddTenant] = useState(false);
  const [selectedUnitId, setSelectedUnitId] = useState<number | null>(null);

  // Add tenant form
  const [newTenant, setNewTenant] = useState({ full_name: '', phone: '', email: '', national_id: '', rent_due_day: '1' });
  const [adding, setAdding] = useState(false);
  const [addSuccess, setAddSuccess] = useState(false);

  useEffect(() => {
    api.client.get('/api/rentals/units')
      .then(r => setUnits(r.data || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleCollectRent = async (tenantId: number) => {
    setCollectingId(tenantId);
    try {
      await api.client.post(`/api/rentals/rent/request-payment/${tenantId}`);
      alert('M-Pesa STK Push sent to tenant! 📱');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed');
    } finally {
      setCollectingId(null);
    }
  };

  const handleAddTenant = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUnitId || !newTenant.full_name || !newTenant.phone) {
      alert('Fill in at least name and phone number');
      return;
    }
    setAdding(true);
    try {
      await api.client.post('/api/rentals/tenants', null, {
        params: {
          unit_id: selectedUnitId,
          full_name: newTenant.full_name,
          phone: newTenant.phone,
          email: newTenant.email || undefined,
          national_id: newTenant.national_id || undefined,
          rent_due_day: parseInt(newTenant.rent_due_day) || 1,
        },
      });
      setAddSuccess(true);
      setNewTenant({ full_name: '', phone: '', email: '', national_id: '', rent_due_day: '1' });
      // Refresh units
      const r = await api.client.get('/api/rentals/units');
      setUnits(r.data || []);
      setTimeout(() => { setAddSuccess(false); setShowAddTenant(false); }, 2000);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to add tenant');
    } finally {
      setAdding(false);
    }
  };

  const allTenants = units.flatMap(u =>
    (u.tenants || []).map((t: any) => ({ ...t, unit: u }))
  );

  const vacantUnits = units.filter(u => !u.is_occupied);

  if (loading) return <div className="flex justify-center py-32"><Spinner size="lg" /></div>;

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link href="/dashboard/landlord" className="p-2 hover:bg-gray-100 rounded-xl">
            <ArrowLeft className="w-5 h-5 text-gray-500" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Tenants</h1>
            <p className="text-sm text-gray-500">{allTenants.length} tenant{allTenants.length !== 1 ? 's' : ''} · {units.length} units</p>
          </div>
        </div>
        <Button onClick={() => setShowAddTenant(true)} className="gap-2 bg-violet-600 hover:bg-violet-500">
          <UserPlus className="w-4 h-4" /> Add Tenant
        </Button>
      </div>

      {/* Add Tenant Form */}
      {showAddTenant && (
        <Card padding="md" className="border-2 border-violet-200 bg-violet-50/30">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-bold text-gray-900 flex items-center gap-2">
              <UserPlus className="w-5 h-5 text-violet-600" /> Add New Tenant
            </h3>
            <button onClick={() => setShowAddTenant(false)} className="p-1 hover:bg-gray-100 rounded-lg">
              <X className="w-5 h-5 text-gray-400" />
            </button>
          </div>

          {addSuccess ? (
            <div className="bg-emerald-100 rounded-xl p-4 flex items-center gap-3">
              <CheckCircle className="w-6 h-6 text-emerald-600" />
              <div>
                <p className="font-semibold text-emerald-800">Tenant Added!</p>
                <p className="text-sm text-emerald-600">They can now log in and see their rental.</p>
              </div>
            </div>
          ) : (
            <form onSubmit={handleAddTenant} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">Select Unit *</label>
                <select
                  value={selectedUnitId || ''}
                  onChange={e => setSelectedUnitId(Number(e.target.value))}
                  className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-violet-500"
                  required
                >
                  <option value="">Choose a unit...</option>
                  {vacantUnits.map(u => (
                    <option key={u.id} value={u.id}>
                      {u.name} — {u.unit_type} · {u.city} · KES {u.monthly_rent_kes?.toLocaleString()}/mo
                    </option>
                  ))}
                  {units.filter(u => u.is_occupied).map(u => (
                    <option key={u.id} value={u.id} disabled>
                      {u.name} — OCCUPIED
                    </option>
                  ))}
                </select>
                {vacantUnits.length === 0 && (
                  <p className="text-xs text-amber-600 mt-1">All units are occupied. Free up a unit first.</p>
                )}
              </div>

              <div className="grid sm:grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Full Name *</label>
                  <input
                    type="text"
                    value={newTenant.full_name}
                    onChange={e => setNewTenant({ ...newTenant, full_name: e.target.value })}
                    placeholder="Jane Muthoni"
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Phone Number *</label>
                  <input
                    type="tel"
                    value={newTenant.phone}
                    onChange={e => setNewTenant({ ...newTenant, phone: e.target.value })}
                    placeholder="0712345678"
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-violet-500"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
                  <input
                    type="email"
                    value={newTenant.email}
                    onChange={e => setNewTenant({ ...newTenant, email: e.target.value })}
                    placeholder="jane@email.com"
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-violet-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Rent Due Day</label>
                  <input
                    type="number"
                    min="1"
                    max="28"
                    value={newTenant.rent_due_day}
                    onChange={e => setNewTenant({ ...newTenant, rent_due_day: e.target.value })}
                    className="w-full px-3 py-2.5 rounded-xl border border-gray-200 text-sm focus:ring-2 focus:ring-violet-500"
                  />
                </div>
              </div>

              <div className="flex gap-3">
                <Button type="submit" loading={adding} className="gap-2 bg-violet-600 hover:bg-violet-500 flex-1">
                  <UserPlus className="w-4 h-4" /> Add Tenant
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowAddTenant(false)}>
                  Cancel
                </Button>
              </div>
            </form>
          )}
        </Card>
      )}

      {/* Tenant List */}
      {allTenants.length === 0 ? (
        <Card className="text-center py-20">
          <Users className="w-14 h-14 text-gray-200 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-700 mb-2">No Tenants Yet</h2>
          <p className="text-gray-500 text-sm mb-6">
            Add tenants to your vacant units. They'll automatically see their rental when they log in.
          </p>
          <Button onClick={() => setShowAddTenant(true)} className="bg-violet-600 hover:bg-violet-500 gap-2">
            <UserPlus className="w-4 h-4" /> Add Your First Tenant
          </Button>
        </Card>
      ) : (
        <div className="space-y-3">
          {allTenants.map((t: any) => (
            <Card key={`${t.unit.id}-${t.id}`} padding="md" className="hover:shadow-md transition-all">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-violet-100 rounded-full flex items-center justify-center">
                    <span className="text-violet-700 font-bold text-lg">{t.name?.[0]?.toUpperCase()}</span>
                  </div>
                  <div>
                    <div className="flex items-center gap-2 mb-0.5">
                      <p className="font-semibold text-gray-900">{t.name}</p>
                      <Badge variant={t.is_active ? 'success' : 'default'} className="text-xs">
                        {t.is_active ? 'Active' : 'Inactive'}
                      </Badge>
                    </div>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="flex items-center gap-1"><Phone className="w-3 h-3" />{t.phone}</span>
                      <span className="flex items-center gap-1"><Home className="w-3 h-3" />{t.unit.name}</span>
                      <span className="flex items-center gap-1"><DollarSign className="w-3 h-3" />KES {t.unit.monthly_rent_kes?.toLocaleString()}/mo</span>
                    </div>
                  </div>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    onClick={() => handleCollectRent(t.id)}
                    loading={collectingId === t.id}
                    className="bg-violet-600 hover:bg-violet-500 text-xs gap-1"
                  >
                    <Phone className="w-3 h-3" /> Collect Rent
                  </Button>
                  <Link href={`/messages?user=${t.id}`}>
                    <Button size="sm" variant="outline" className="text-xs gap-1">
                      Message
                    </Button>
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
