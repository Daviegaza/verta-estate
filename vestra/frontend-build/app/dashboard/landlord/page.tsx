'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import {
  Building2, Users, TrendingUp, AlertCircle, Home,
  DollarSign, Phone, Calendar, Activity, ChevronRight, Plus
} from 'lucide-react';

interface RentalDashboard {
  total_units: number; occupied_units: number; vacancy_rate: number;
  total_tenants: number; expected_monthly_rent: number;
  collected_this_month: number; collection_rate: number;
  pending_maintenance: number; late_payments: number;
}

interface RentalUnit {
  id: number; name: string; unit_type: string; bedrooms: number;
  city: string; monthly_rent_kes: number; is_occupied: boolean;
  tenants: { id: number; name: string; phone: string; is_active: boolean }[];
}

export default function LandlordDashboardPage() {
  return (
    <AuthGuard requireAuth>
      <LandlordDashboardContent />
    </AuthGuard>
  );
}

function LandlordDashboardContent() {
  const { user } = useAuthStore();
  const [dashboard, setDashboard] = useState<RentalDashboard | null>(null);
  const [units, setUnits] = useState<RentalUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [collectingId, setCollectingId] = useState<number | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true);
    setError('');
    try {
      const [dashResp, unitsResp] = await Promise.all([
        api.client.get('/api/rentals/dashboard'),
        api.client.get('/api/rentals/units'),
      ]);
      setDashboard(dashResp.data);
      setUnits(unitsResp.data || []);
    } catch (err: any) {
      if (err?.response?.status === 402) {
        setError('A landlord subscription is required. Upgrade your plan to access rental management.');
      } else {
        setError('Failed to load dashboard. Please try again.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleCollectRent = async (tenantId: number) => {
    setCollectingId(tenantId);
    try {
      await api.client.post(`/api/rentals/rent/request-payment/${tenantId}`);
      alert('M-Pesa STK Push sent to tenant!');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to send payment request');
    } finally {
      setCollectingId(null);
    }
  };

  if (loading) return (
    <div className="min-h-screen bg-gray-50"><Navbar />
      <div className="flex justify-center py-32"><Spinner size="lg" /></div>
    </div>
  );

  if (error && !dashboard) return (
    <div className="min-h-screen bg-gray-50"><Navbar />
      <div className="max-w-2xl mx-auto px-4 py-32 text-center">
        <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-red-600 mb-4">{error}</p>
        {error.includes('subscription') ? (
          <Link href="/subscription"><Button>Upgrade Plan</Button></Link>
        ) : (
          <Button onClick={loadData}>Retry</Button>
        )}
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Landlord Dashboard</h1>
            <p className="text-gray-500 mt-1">Manage your rental portfolio</p>
          </div>
          <Link href="/properties/new">
            <Button><Plus className="w-4 h-4 mr-2" />Add Unit</Button>
          </Link>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          <StatItem icon={<Building2 className="w-5 h-5" />} label="Total Units" value={dashboard?.total_units ?? 0} color="blue" />
          <StatItem icon={<Users className="w-5 h-5" />} label="Occupied" value={`${dashboard?.occupied_units ?? 0}/${dashboard?.total_units ?? 0}`} color="emerald" />
          <StatItem icon={<DollarSign className="w-5 h-5" />} label="Collection Rate" value={`${dashboard?.collection_rate ?? 0}%`} color="amber" />
          <StatItem icon={<TrendingUp className="w-5 h-5" />} label="Collected (KES)" value={((dashboard?.collected_this_month ?? 0) / 1000).toFixed(0) + 'K'} color="green" />
        </div>

        {/* Units Table */}
        <Card className="mb-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4">Your Units</h2>
          {units.length === 0 ? (
            <div className="text-center py-12">
              <Home className="w-12 h-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500 mb-4">No rental units yet. Add your first unit to get started.</p>
              <Link href="/properties/new"><Button>Add Your First Unit</Button></Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-xs font-semibold text-gray-400 uppercase border-b">
                    <th className="pb-3">Unit</th>
                    <th className="pb-3">Tenant</th>
                    <th className="pb-3">Rent (KES)</th>
                    <th className="pb-3">Status</th>
                    <th className="pb-3 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100">
                  {units.map((unit) => (
                    <tr key={unit.id} className="hover:bg-gray-50">
                      <td className="py-3">
                        <p className="font-medium text-gray-900">{unit.name}</p>
                        <p className="text-xs text-gray-400">{unit.city} · {unit.bedrooms}br</p>
                      </td>
                      <td className="py-3">
                        {unit.tenants.length > 0 ? (
                          <div>
                            <p className="text-gray-900">{unit.tenants[0].name}</p>
                            <p className="text-xs text-gray-400">{unit.tenants[0].phone}</p>
                          </div>
                        ) : <span className="text-gray-400 text-xs">Vacant</span>}
                      </td>
                      <td className="py-3 font-medium">KES {(unit.monthly_rent_kes ?? 0).toLocaleString()}</td>
                      <td className="py-3">
                        <span className={`inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${
                          unit.is_occupied ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-500'
                        }`}>
                          {unit.is_occupied ? 'Occupied' : 'Vacant'}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        {unit.tenants.length > 0 && (
                          <Button
                            size="sm"
                            onClick={() => handleCollectRent(unit.tenants[0].id)}
                            loading={collectingId === unit.tenants[0].id}
                          >
                            <Phone className="w-3 h-3 mr-1" />Collect Rent
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Quick Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <DollarSign className="w-4 h-4" />Expected Monthly
            </div>
            <p className="text-2xl font-bold text-gray-900">
              KES {(dashboard?.expected_monthly_rent ?? 0).toLocaleString()}
            </p>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Activity className="w-4 h-4" />Pending Maintenance
            </div>
            <p className="text-2xl font-bold text-amber-600">{dashboard?.pending_maintenance ?? 0}</p>
          </Card>
          <Card className="p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Calendar className="w-4 h-4" />Late Payments
            </div>
            <p className="text-2xl font-bold text-red-600">{dashboard?.late_payments ?? 0}</p>
          </Card>
        </div>
      </div>
    </div>
  );
}

function StatItem({ icon, label, value, color }: {
  icon: React.ReactNode; label: string; value: string | number; color: string;
}) {
  const colors: Record<string, string> = {
    blue: 'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    amber: 'bg-amber-50 text-amber-600',
    green: 'bg-green-50 text-green-600',
  };
  return (
    <Card className="p-4">
      <div className="flex items-center gap-3">
        <div className={`p-2.5 rounded-xl ${colors[color] || colors.blue}`}>{icon}</div>
        <div>
          <p className="text-xs text-gray-500">{label}</p>
          <p className="text-xl font-bold text-gray-900">{value}</p>
        </div>
      </div>
    </Card>
  );
}
