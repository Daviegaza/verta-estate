'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import RoleBanner from '@/components/dashboard/RoleBanner';
import StatCardGrid, { type StatItem } from '@/components/dashboard/StatCardGrid';
import QuickActions, { type QuickAction } from '@/components/dashboard/QuickActions';
import ActivityFeed, { type ActivityItem } from '@/components/dashboard/ActivityFeed';
import { Card, Badge, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import {
  Building2, Users, DollarSign, TrendingUp, Home,
  Phone, AlertCircle, Plus, Wrench, Calendar, Activity,
  ArrowRight, Shield, BarChart3, CreditCard, Key,
  Search, Star, FileText, Zap, Bell, Layers, DoorOpen,
  Clock, Sparkles, Gauge, Building, Timer, Wallet,
  ChevronRight, MapPin, BedDouble, Bath, Ruler,
  ZapOff, UserCheck, Percent,
} from 'lucide-react';

interface RentalDashboard {
  total_units: number; occupied_units: number; vacant_units: number;
  vacancy_rate: number; total_tenants: number;
  expected_monthly_rent: number; collected_this_month: number;
  collection_rate: number; pending_maintenance: number;
  late_payments: number; late_fees_collected: number;
  buildings: BuildingSummary[];
  unit_types: Record<string, number>;
  utilities: { water: number; electricity: number; service_charge: number; total: number };
  efficiency: {
    hours_saved_per_month: number; automated_collections: number;
    auto_late_fees_kes: number; collection_boost_pct: string;
    maintenance_resolved: number; total_rent_managed_kes: number;
  };
}

interface BuildingSummary {
  name: string; total_units: number; occupied: number; vacant: number;
  occupancy_rate: number; units: UnitSummary[];
}

interface UnitSummary {
  id: number; name: string; unit_number?: string; unit_type: string;
  floor?: number; bedrooms: number; monthly_rent_kes: number;
  is_occupied: boolean; amenities: string[];
}

interface RentalUnit {
  id: number; building_name?: string; name: string; unit_number?: string;
  unit_type: string; bedrooms: number; bathrooms: number;
  floor?: number; size_sqft?: number; city: string; address: string;
  monthly_rent_kes: number; deposit_kes: number;
  water_kes: number; electricity_kes: number; service_charge_kes: number;
  total_monthly_kes: number; is_occupied: boolean; amenities: string[];
  tenants: { id: number; name: string; phone: string; is_active: boolean }[];
}

const UNIT_TYPE_LABELS: Record<string, string> = {
  bedsitter: 'Bedsitter', studio: 'Studio',
  '1br': '1 Bedroom', '2br': '2 Bedroom', '3br': '3 Bedroom',
  '4br': '4 Bedroom', penthouse: 'Penthouse',
  apartment: 'Apartment', house: 'House', other: 'Other',
};

const UNIT_TYPE_ICONS: Record<string, React.ReactNode> = {
  bedsitter: <DoorOpen className="w-4 h-4" />,
  studio: <Home className="w-4 h-4" />,
  '1br': <Building2 className="w-4 h-4" />,
  '2br': <Building2 className="w-4 h-4" />,
  '3br': <Building2 className="w-4 h-4" />,
  penthouse: <Star className="w-4 h-4" />,
};

export default function LandlordDashboardPage() {
  return (
    <AuthGuard requireAuth requireRoles={['landlord']}>
      <LandlordContent />
    </AuthGuard>
  );
}

function LandlordContent() {
  const { user } = useAuthStore();
  const [dashboard, setDashboard] = useState<RentalDashboard | null>(null);
  const [units, setUnits] = useState<RentalUnit[]>([]);
  const [loading, setLoading] = useState(true);
  const [collectingId, setCollectingId] = useState<number | null>(null);
  const [error, setError] = useState('');
  const [activeBuilding, setActiveBuilding] = useState<string | null>(null);

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    setLoading(true); setError('');
    try {
      const [dashResp, unitsResp] = await Promise.all([
        api.client.get('/api/rentals/dashboard').catch(() => ({ data: null })),
        api.client.get('/api/rentals/units').catch(() => ({ data: [] })),
      ]);
      setDashboard(dashResp.data);
      const unitList = unitsResp.data || [];
      setUnits(unitList);
      // Auto-select first building
      const buildings = dashResp.data?.buildings || [];
      if (buildings.length > 0 && !activeBuilding) {
        setActiveBuilding(buildings[0].name);
      }
    } catch {
      setError('Failed to load dashboard.');
    } finally {
      setLoading(false);
    }
  };

  const handleCollectRent = async (tenantId: number) => {
    setCollectingId(tenantId);
    try {
      await api.client.post(`/api/rentals/rent/request-payment/${tenantId}`);
      alert('M-Pesa STK Push sent to tenant! 📱');
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Failed to send payment request');
    } finally {
      setCollectingId(null);
    }
  };

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  if (error && !dashboard) return (
    <div className="text-center py-32">
      <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
      <p className="text-red-600 mb-4">{error}</p>
      <Button onClick={loadData}>Retry</Button>
    </div>
  );

  // Show onboarding if no units
  if (!dashboard || dashboard.total_units === 0) {
    return <OnboardingView />;
  }

  const d = dashboard;
  const buildings = d.buildings || [];
  const activeBldg = buildings.find(b => b.name === activeBuilding) || buildings[0];

  // ── Stats ──
  const stats: StatItem[] = [
    {
      label: 'Total Units',
      value: d.total_units,
      icon: <Building2 className="w-5 h-5" />,
      subtext: `${d.occupied_units} occupied · ${d.vacant_units} vacant`,
      trend: d.vacancy_rate > 20 ? { value: `${d.vacancy_rate}% vacant`, positive: false } : undefined,
    },
    {
      label: 'Collection Rate',
      value: `${d.collection_rate}%`,
      icon: <TrendingUp className="w-5 h-5" />,
      trend: d.collection_rate >= 90
        ? { value: 'Excellent', positive: true }
        : d.collection_rate >= 70
          ? { value: 'Average', positive: true }
          : { value: `${d.late_payments} late`, positive: false },
    },
    {
      label: 'Collected This Month',
      value: `KES ${(d.collected_this_month / 1000).toFixed(0)}K`,
      icon: <Wallet className="w-5 h-5" />,
      subtext: `of KES ${(d.expected_monthly_rent / 1000).toFixed(0)}K expected`,
    },
    {
      label: 'Active Tenants',
      value: d.total_tenants,
      icon: <Users className="w-5 h-5" />,
      subtext: d.pending_maintenance > 0 ? `${d.pending_maintenance} maintenance open` : 'All clear',
    },
  ];

  const actions: QuickAction[] = [
    {
      label: 'Add Unit',
      desc: 'Bedsitter, 1BR, 2BR, 3BR, Studio...',
      icon: <Plus className="w-4 h-4" />,
      href: '/properties/new',
      iconBg: 'bg-violet-600',
    },
    {
      label: 'View All Units',
      desc: `${d.total_units} units across ${buildings.length} building${buildings.length !== 1 ? 's' : ''}`,
      icon: <Building2 className="w-4 h-4" />,
      href: '/properties/my',
      iconBg: 'bg-purple-600',
    },
    {
      label: 'Manage Tenants',
      desc: `${d.total_tenants} active tenant${d.total_tenants !== 1 ? 's' : ''}`,
      icon: <Users className="w-4 h-4" />,
      href: '/dashboard/landlord/tenants',
      iconBg: 'bg-fuchsia-600',
    },
    {
      label: 'Maintenance',
      desc: d.pending_maintenance > 0 ? `${d.pending_maintenance} pending request${d.pending_maintenance !== 1 ? 's' : ''}` : 'No pending issues',
      icon: <Wrench className="w-4 h-4" />,
      href: '/dashboard/landlord/maintenance',
      iconBg: d.pending_maintenance > 0 ? 'bg-amber-600' : 'bg-emerald-600',
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <RoleBanner subtitle={`${d.total_units} units · ${buildings.length} building${buildings.length !== 1 ? 's' : ''} · KES ${(d.expected_monthly_rent / 1000).toFixed(0)}K/month portfolio`}>
        <Link href="/properties/new">
          <Button size="lg" className="bg-white text-violet-700 hover:bg-violet-50 gap-2 font-semibold shadow-lg">
            <Plus className="w-4 h-4" /> Add Unit
          </Button>
        </Link>
        {d.late_payments > 0 && (
          <Button
            size="lg"
            onClick={() => {
              units.filter(u => u.is_occupied).forEach(u => {
                u.tenants.forEach(t => handleCollectRent(t.id));
              });
            }}
            className="bg-white/10 border border-white/20 text-white hover:bg-white/20 gap-2"
          >
            <Zap className="w-4 h-4" /> Collect All Rent
          </Button>
        )}
      </RoleBanner>

      <StatCardGrid stats={stats} columns={4} />

      <div className="grid lg:grid-cols-3 gap-6">
        {/* ── Main Content ── */}
        <div className="lg:col-span-2 space-y-6">
          {/* Efficiency Banner */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-600 to-teal-600 text-white p-5">
            <div className="absolute top-0 right-0 w-40 h-40 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="relative z-10 flex items-center gap-4 flex-wrap">
              <div className="flex items-center gap-3 bg-white/15 rounded-xl px-4 py-3">
                <Clock className="w-6 h-6" />
                <div>
                  <p className="text-2xl font-bold">{d.efficiency?.hours_saved_per_month || 0}h</p>
                  <p className="text-xs text-emerald-100">Saved This Month</p>
                </div>
              </div>
              <div className="flex items-center gap-3 bg-white/15 rounded-xl px-4 py-3">
                <Zap className="w-6 h-6" />
                <div>
                  <p className="text-2xl font-bold">{d.efficiency?.automated_collections || 0}</p>
                  <p className="text-xs text-emerald-100">Auto-Collections</p>
                </div>
              </div>
              <div className="flex items-center gap-3 bg-white/15 rounded-xl px-4 py-3">
                <TrendingUp className="w-6 h-6" />
                <div>
                  <p className="text-2xl font-bold">{d.efficiency?.collection_boost_pct || '+5%'}</p>
                  <p className="text-xs text-emerald-100">Collection Boost</p>
                </div>
              </div>
              <div className="flex-1 text-right hidden lg:block">
                <p className="text-emerald-100 text-sm">Powered by Vestra AI</p>
                <p className="text-white font-semibold">Automated Rent Collection + Late Fees</p>
              </div>
            </div>
          </div>

          {/* Building Portfolio */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Building className="w-5 h-5 text-violet-600" />
                Building Portfolio
              </h2>
              <span className="text-sm text-gray-500">{buildings.length} building{buildings.length !== 1 ? 's' : ''}</span>
            </div>

            {/* Building Tabs */}
            <div className="flex gap-2 mb-4 overflow-x-auto pb-1">
              {buildings.map(bldg => (
                <button
                  key={bldg.name}
                  onClick={() => setActiveBuilding(bldg.name)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium whitespace-nowrap transition-all ${
                    activeBuilding === bldg.name
                      ? 'bg-violet-600 text-white shadow-lg shadow-violet-200'
                      : 'bg-white border border-gray-200 text-gray-600 hover:border-violet-200 hover:text-violet-700'
                  }`}
                >
                  <Building2 className="w-4 h-4" />
                  {bldg.name}
                  <span className={`text-xs px-1.5 py-0.5 rounded-full ${
                    activeBuilding === bldg.name ? 'bg-white/20' : 'bg-gray-100'
                  }`}>
                    {bldg.total_units}u · {bldg.occupancy_rate}%
                  </span>
                </button>
              ))}
            </div>

            {/* Active Building Units */}
            {activeBldg && (
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3 text-sm text-gray-500">
                    <span className="flex items-center gap-1"><Building2 className="w-3.5 h-3.5" />{activeBldg.total_units} units</span>
                    <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{activeBldg.occupied} occupied</span>
                    {activeBldg.vacant > 0 && (
                      <span className="flex items-center gap-1 text-amber-600 font-medium"><AlertCircle className="w-3.5 h-3.5" />{activeBldg.vacant} vacant</span>
                    )}
                  </div>
                  <span className="text-sm font-medium text-gray-900">{activeBldg.occupancy_rate}% occupied</span>
                </div>

                {/* Unit Cards Grid — Apartment Style */}
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {activeBldg.units.map(unit => {
                    const fullUnit = units.find(u => u.id === unit.id);
                    const floorLabel = unit.floor != null ? (unit.floor === 0 ? 'Ground' : `Floor ${unit.floor}`) : null;
                    return (
                      <div
                        key={unit.id}
                        className={`relative rounded-xl border-2 p-4 transition-all hover:shadow-md group ${
                          unit.is_occupied
                            ? 'border-violet-100 bg-white hover:border-violet-300'
                            : 'border-amber-200 bg-amber-50/30 hover:border-amber-400'
                        }`}
                      >
                        {/* Vacant badge */}
                        {!unit.is_occupied && (
                          <div className="absolute -top-2 -right-2 bg-amber-500 text-white text-xs font-bold px-2 py-0.5 rounded-full shadow">
                            VACANT
                          </div>
                        )}

                        {/* Unit Header */}
                        <div className="flex items-start justify-between mb-2">
                          <div>
                            <div className="flex items-center gap-1.5 mb-0.5">
                              <span className="text-lg font-bold text-gray-900">
                                {unit.unit_number || unit.name}
                              </span>
                              {unit.unit_type && (
                                <span className="text-xs text-gray-400 capitalize">{UNIT_TYPE_LABELS[unit.unit_type] || unit.unit_type}</span>
                              )}
                            </div>
                            {floorLabel && (
                              <p className="text-xs text-gray-400 flex items-center gap-1">
                                <Layers className="w-3 h-3" />{floorLabel}
                              </p>
                            )}
                          </div>
                          {unit.is_occupied && (
                            <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 animate-pulse" title="Occupied" />
                          )}
                        </div>

                        {/* Rent */}
                        <p className="text-lg font-bold text-violet-700 mb-2">
                          KES {unit.monthly_rent_kes.toLocaleString()}<span className="text-xs text-gray-400 font-normal">/mo</span>
                        </p>

                        {/* Features */}
                        <div className="flex items-center gap-3 text-xs text-gray-400 mb-3">
                          {unit.bedrooms > 0 && <span className="flex items-center gap-1"><BedDouble className="w-3 h-3" />{unit.bedrooms}br</span>}
                          {fullUnit?.bathrooms != null && fullUnit.bathrooms > 0 && <span className="flex items-center gap-1"><Bath className="w-3 h-3" />{fullUnit.bathrooms}ba</span>}
                          {fullUnit?.size_sqft != null && fullUnit.size_sqft > 0 && <span className="flex items-center gap-1"><Ruler className="w-3 h-3" />{fullUnit.size_sqft}sqft</span>}
                        </div>

                        {/* Amenities */}
                        {unit.amenities.length > 0 && (
                          <div className="flex flex-wrap gap-1 mb-3">
                            {unit.amenities.slice(0, 4).map(a => (
                              <span key={a} className="text-xs bg-gray-100 text-gray-600 px-1.5 py-0.5 rounded-md">{a}</span>
                            ))}
                          </div>
                        )}

                        {/* Tenants / Action */}
                        {fullUnit?.tenants && fullUnit.tenants.length > 0 ? (
                          <div className="flex items-center justify-between pt-2 border-t border-gray-100">
                            <div>
                              <p className="text-xs font-semibold text-gray-900">{fullUnit.tenants[0].name}</p>
                              <p className="text-xs text-gray-400">{fullUnit.tenants[0].phone}</p>
                            </div>
                            <Button
                              size="sm"
                              onClick={() => handleCollectRent(fullUnit.tenants[0].id)}
                              loading={collectingId === fullUnit.tenants[0].id}
                              className="gap-1 bg-violet-600 hover:bg-violet-500 text-xs"
                            >
                              <Phone className="w-3 h-3" />Collect
                            </Button>
                          </div>
                        ) : (
                          <div className="pt-2 border-t border-gray-100">
                            <Link href={`/dashboard/landlord/tenants`}>
                              <Button size="sm" variant="outline" className="w-full text-xs border-violet-200 text-violet-700 hover:bg-violet-50">
                                <Plus className="w-3 h-3" /> Add Tenant
                              </Button>
                            </Link>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}
          </div>

          {/* Unit Type Distribution + Quick Stats */}
          <div className="grid sm:grid-cols-2 gap-4">
            <Card padding="md">
              <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2 text-sm">
                <Layers className="w-4 h-4 text-violet-600" />
                Unit Types
              </h3>
              <div className="space-y-2">
                {Object.entries(d.unit_types || {}).sort(([,a], [,b]) => b - a).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 capitalize">{UNIT_TYPE_LABELS[type] || type}</span>
                    <div className="flex items-center gap-2">
                      <div className="w-24 bg-gray-100 rounded-full h-2">
                        <div
                          className="bg-violet-500 h-2 rounded-full"
                          style={{ width: `${(count / d.total_units) * 100}%` }}
                        />
                      </div>
                      <span className="text-sm font-semibold text-gray-900 w-6 text-right">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card padding="md">
              <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2 text-sm">
                <DollarSign className="w-4 h-4 text-violet-600" />
                Utility Breakdown
              </h3>
              {d.utilities && (
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-500">Rent</span>
                    <span className="font-semibold text-gray-900">KES {d.expected_monthly_rent.toLocaleString()}</span>
                  </div>
                  {d.utilities.water > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Water</span>
                      <span className="font-semibold text-blue-600">KES {d.utilities.water.toLocaleString()}</span>
                    </div>
                  )}
                  {d.utilities.electricity > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Electricity</span>
                      <span className="font-semibold text-amber-600">KES {d.utilities.electricity.toLocaleString()}</span>
                    </div>
                  )}
                  {d.utilities.service_charge > 0 && (
                    <div className="flex justify-between text-sm">
                      <span className="text-gray-500">Service Charge</span>
                      <span className="font-semibold text-gray-600">KES {d.utilities.service_charge.toLocaleString()}</span>
                    </div>
                  )}
                  <div className="border-t pt-2 flex justify-between text-sm font-bold">
                    <span className="text-gray-700">Total Portfolio</span>
                    <span className="text-violet-700">KES {(d.expected_monthly_rent + d.utilities.total).toLocaleString()}</span>
                  </div>
                </div>
              )}
            </Card>
          </div>
        </div>

        {/* ── Sidebar ── */}
        <div className="space-y-5">
          <QuickActions actions={actions} />

          {/* Why Use VESTRA */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600 via-purple-600 to-fuchsia-700 p-6 text-white">
            <div className="absolute top-0 right-0 w-32 h-32 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <Sparkles className="w-10 h-10 text-violet-200 mb-4 relative z-10" />
            <h3 className="font-bold text-lg mb-3 relative z-10">Why Landlords Choose Vestra</h3>
            <div className="space-y-2.5 mb-5 relative z-10">
              <div className="flex items-start gap-2 text-sm">
                <CheckIcon />
                <span>Automated M-Pesa rent collection — <strong>save {d.efficiency?.hours_saved_per_month || 0}h/month</strong></span>
              </div>
              <div className="flex items-start gap-2 text-sm">
                <CheckIcon />
                <span>Automatic late fees — <strong>KES {d.efficiency?.auto_late_fees_kes?.toLocaleString() || 0}</strong> collected</span>
              </div>
              <div className="flex items-start gap-2 text-sm">
                <CheckIcon />
                <span>Tenant management — contact, lease tracking, maintenance</span>
              </div>
              <div className="flex items-start gap-2 text-sm">
                <CheckIcon />
                <span>{d.efficiency?.collection_boost_pct || '+5%'} higher collection rate with auto-reminders</span>
              </div>
            </div>
          </div>

          {/* Recent Activity — late payments & maintenance alerts */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3">
              <h3 className="font-bold text-gray-900 flex items-center gap-2 text-sm">
                <Bell className="w-4 h-4 text-violet-600" />
                Alerts & Activity
              </h3>
            </div>
            <div className="divide-y divide-gray-50 px-5 pb-4">
              {d.late_payments > 0 && (
                <div className="flex items-center gap-3 py-3">
                  <div className="w-2 h-2 rounded-full bg-red-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{d.late_payments} late payment{d.late_payments !== 1 ? 's' : ''}</p>
                    <p className="text-xs text-gray-500">This month</p>
                  </div>
                  <Button size="sm" variant="outline" className="text-xs border-red-200 text-red-600 hover:bg-red-50">
                    Remind All
                  </Button>
                </div>
              )}
              {d.pending_maintenance > 0 && (
                <div className="flex items-center gap-3 py-3">
                  <div className="w-2 h-2 rounded-full bg-amber-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{d.pending_maintenance} maintenance request{d.pending_maintenance !== 1 ? 's' : ''}</p>
                    <p className="text-xs text-gray-500">Pending resolution</p>
                  </div>
                  <Link href="/dashboard/landlord/maintenance">
                    <Button size="sm" variant="outline" className="text-xs border-amber-200 text-amber-600 hover:bg-amber-50">
                      View
                    </Button>
                  </Link>
                </div>
              )}
              {d.vacant_units > 0 && (
                <div className="flex items-center gap-3 py-3">
                  <div className="w-2 h-2 rounded-full bg-blue-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900">{d.vacant_units} vacant unit{d.vacant_units !== 1 ? 's' : ''}</p>
                    <p className="text-xs text-gray-500">Lost KES {((d.expected_monthly_rent / (d.occupied_units || 1)) * d.vacant_units).toLocaleString()}/mo potential</p>
                  </div>
                  <Link href="/properties/new">
                    <Button size="sm" className="text-xs bg-violet-600 hover:bg-violet-500">List</Button>
                  </Link>
                </div>
              )}
              {d.late_payments === 0 && d.pending_maintenance === 0 && d.vacant_units === 0 && (
                <div className="text-center py-6">
                  <CheckIconGreen />
                  <p className="text-sm text-gray-500 mt-2">All units occupied & rent collected 🎉</p>
                </div>
              )}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ── Onboarding View (No Units Yet) ──────────────────────────────────────────

function OnboardingView() {
  return (
    <div className="space-y-8 animate-fade-in">
      <RoleBanner subtitle="Welcome to your landlord command center. Let's set up your portfolio." />

      <div className="max-w-4xl mx-auto">
        {/* Hero onboarding */}
        <div className="text-center mb-12">
          <div className="w-24 h-24 bg-violet-100 rounded-3xl flex items-center justify-center mx-auto mb-6 animate-float">
            <Building2 className="w-12 h-12 text-violet-600" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Your Rental Empire Starts Here</h2>
          <p className="text-gray-500 max-w-lg mx-auto mb-8 text-lg">
            Manage apartments, flats, bedsitters — collect rent automatically via M-Pesa, track tenants, handle maintenance. All in one place.
          </p>
          <Link href="/properties/new">
            <Button size="lg" className="gap-2 bg-violet-600 hover:bg-violet-500 text-lg px-8 py-6">
              <Plus className="w-5 h-5" /> Add Your First Unit
            </Button>
          </Link>
        </div>

        {/* Why VESTRA — Value Proposition Grid */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {[
            {
              icon: <Zap className="w-8 h-8" />,
              title: 'Auto Rent Collection',
              desc: 'M-Pesa STK Push sent to all tenants monthly. No more chasing payments. Collection rates up 95%.',
              color: 'bg-amber-50 text-amber-600',
            },
            {
              icon: <Clock className="w-8 h-8" />,
              title: 'Save Hours Every Month',
              desc: 'No manual receipts, no WhatsApp reminders, no Excel sheets. Save 15+ hours/month on admin.',
              color: 'bg-emerald-50 text-emerald-600',
            },
            {
              icon: <DollarSign className="w-8 h-8" />,
              title: 'Automatic Late Fees',
              desc: 'KES 100/day late fee applied automatically. Incentivize on-time payment without awkward conversations.',
              color: 'bg-red-50 text-red-600',
            },
            {
              icon: <Users className="w-8 h-8" />,
              title: 'Tenant Management',
              desc: 'Full tenant profiles, lease tracking, move-in/move-out dates, emergency contacts — all in one place.',
              color: 'bg-blue-50 text-blue-600',
            },
            {
              icon: <Wrench className="w-8 h-8" />,
              title: 'Maintenance Tracking',
              desc: 'Tenants report issues, you track resolution. No more forgotten repairs or WhatsApp confusion.',
              color: 'bg-purple-50 text-purple-600',
            },
            {
              icon: <BarChart3 className="w-8 h-8" />,
              title: 'Portfolio Analytics',
              desc: 'See occupancy rates, collection performance, vacancy losses, and unit-type breakdowns at a glance.',
              color: 'bg-teal-50 text-teal-600',
            },
          ].map(feature => (
            <Card key={feature.title} padding="md" className="hover:shadow-lg hover:-translate-y-1 transition-all text-center">
              <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-4 ${feature.color}`}>
                {feature.icon}
              </div>
              <h3 className="font-bold text-gray-900 mb-2">{feature.title}</h3>
              <p className="text-sm text-gray-500 leading-relaxed">{feature.desc}</p>
            </Card>
          ))}
        </div>

        {/* Supported Unit Types */}
        <div className="text-center mb-8">
          <h3 className="text-lg font-bold text-gray-900 mb-6">Manage Any Type of Rental</h3>
          <div className="flex flex-wrap justify-center gap-3">
            {[
              { type: 'Bedsitter', icon: <DoorOpen className="w-5 h-5" /> },
              { type: 'Studio', icon: <Home className="w-5 h-5" /> },
              { type: '1 Bedroom', icon: <Building2 className="w-5 h-5" /> },
              { type: '2 Bedroom', icon: <Building2 className="w-5 h-5" /> },
              { type: '3 Bedroom', icon: <Building2 className="w-5 h-5" /> },
              { type: 'Penthouse', icon: <Star className="w-5 h-5" /> },
              { type: 'Apartment Block', icon: <Building className="w-5 h-5" /> },
              { type: 'House', icon: <Home className="w-5 h-5" /> },
            ].map(item => (
              <div key={item.type} className="flex items-center gap-2 px-5 py-3 bg-white border-2 border-gray-100 rounded-2xl hover:border-violet-200 transition-colors">
                <span className="text-violet-500">{item.icon}</span>
                <span className="font-medium text-gray-700 text-sm">{item.type}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Small Helpers ───────────────────────────────────────────────────────────

function CheckIcon() {
  return (
    <svg className="w-4 h-4 text-violet-200 flex-shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
    </svg>
  );
}

function CheckIconGreen() {
  return (
    <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center mx-auto">
      <svg className="w-5 h-5 text-emerald-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M5 13l4 4L19 7" />
      </svg>
    </div>
  );
}
