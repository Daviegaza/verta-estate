'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { Card, Badge, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/toaster';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { AdminStats } from '@/types';
import { formatCurrency } from '@/lib/utils';
import {
  Users, Building2, ShieldCheck, DollarSign, Clock, AlertTriangle,
  BarChart3, Settings, Activity, Search, Trash2, Ban, UserCheck,
  RefreshCw, Home, MapPin, Filter, X, Check, Eye, Shield, FileText,
  CreditCard, ChevronDown, ChevronRight, LogOut, Smartphone, Key,
  ArrowUpRight, ArrowDownRight,
} from 'lucide-react';
import dynamic from 'next/dynamic';

const OverviewCharts = dynamic(() => import('./OverviewCharts'), {
  ssr: false,
  loading: () => <div className="h-64 bg-gray-50 rounded-2xl animate-pulse" />,
});

type Tab = 'overview' | 'users' | 'properties' | 'payments' | 'verifications' | 'kyc' | 'fraud' | 'audit';

function getTabFromURL(): Tab {
  if (typeof window === 'undefined') return 'overview';
  const p = new URLSearchParams(window.location.search);
  return (p.get('tab') as Tab) || 'overview';
}

export default function AdminPage() {
  return <AdminContent />;
}

function AdminContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const toast = useToast();

  // Derive active tab from URL on every render
  const [activeTab, setActiveTab] = useState<Tab>(getTabFromURL());

  // Sync tab with URL changes (from sidebar clicks using router.push)
  useEffect(() => {
    const handleRouteChange = () => {
      const tab = getTabFromURL();
      setActiveTab(tab);
    };
    window.addEventListener('popstate', handleRouteChange);
    // Custom event for sidebar clicks that use router.push
    window.addEventListener('admin-tab-change', handleRouteChange);
    return () => {
      window.removeEventListener('popstate', handleRouteChange);
      window.removeEventListener('admin-tab-change', handleRouteChange);
    };
  }, []);

  // Navigate to tab — updates URL and triggers re-render
  const navigateToTab = (tab: Tab) => {
    setActiveTab(tab);
    window.history.pushState({}, '', `/admin?tab=${tab}`);
    window.dispatchEvent(new Event('admin-tab-change'));
  };

  // ── Stats ──
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [loading, setLoading] = useState(true);

  // ── Users ──
  const [users, setUsers] = useState<any[]>([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [userSearch, setUserSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [userPage, setUserPage] = useState(0);

  // ── Properties ──
  const [properties, setProperties] = useState<any[]>([]);
  const [propsTotal, setPropsTotal] = useState(0);
  const [propStatus, setPropStatus] = useState('');

  // ── Payments ──
  const [payments, setPayments] = useState<any[]>([]);
  const [paymentsTotal, setPaymentsTotal] = useState(0);
  const [paymentStatus, setPaymentStatus] = useState('');

  // ── Verifications ──
  const [pendingRevs, setPendingRevs] = useState<any[]>([]);

  // ── KYC ──
  const [kycItems, setKycItems] = useState<any[]>([]);
  const [kycTotal, setKycTotal] = useState(0);

  // ── Fraud ──
  const [fraudItems, setFraudItems] = useState<any[]>([]);

  // ── Audit ──
  const [auditItems, setAuditItems] = useState<any[]>([]);
  const [auditTotal, setAuditTotal] = useState(0);

  // ── Confirm ──
  const [confirm, setConfirm] = useState<{ title: string; msg: string; action: () => void; danger?: boolean } | null>(null);

  const exec = async (fn: () => Promise<any>, ok: string) => {
    try { await fn(); toast.success(ok); } catch (e: any) { toast.error('Failed', e?.response?.data?.detail || e?.message); }
  };

  const loadStats = useCallback(async () => {
    try { setStats(await api.getAdminStats()); } catch {}
    finally { setLoading(false); }
  }, []);

  const loadUsers = useCallback(async () => {
    try { const d = await api.getAllUsers(userPage * 20, 20, roleFilter || undefined, userSearch || undefined); setUsers(d.items); setUsersTotal(d.total); } catch {}
  }, [userPage, roleFilter, userSearch]);

  const loadProperties = useCallback(async () => {
    try { const d = await api.getAdminProperties(0, 50, propStatus || undefined); setProperties(d.items); setPropsTotal(d.total); } catch {}
  }, [propStatus]);

  const loadPayments = useCallback(async () => {
    try { const d = await api.getAdminPayments(0, 50, paymentStatus || undefined); setPayments(d.items); setPaymentsTotal(d.total); } catch {}
  }, [paymentStatus]);

  const loadPendingRevs = useCallback(async () => {
    try { setPendingRevs(await api.getPendingVerifications(20)); } catch {}
  }, []);

  const loadKYC = useCallback(async () => {
    try { const d = await api.getPendingKYC(20); setKycItems(d.items); setKycTotal(d.total); } catch {}
  }, []);

  const loadFraud = useCallback(async () => {
    try { const d = await api.getFraudReports(50); setFraudItems(d.items); } catch {}
  }, []);

  const loadAudit = useCallback(async () => {
    try { const d = await api.getAuditLogs(0, 100); setAuditItems(d.items); setAuditTotal(d.total); } catch {}
  }, []);

  useEffect(() => { loadStats(); }, [loadStats]);
  useEffect(() => { if (activeTab === 'users') loadUsers(); }, [activeTab, loadUsers]);
  useEffect(() => { if (activeTab === 'properties') loadProperties(); }, [activeTab, loadProperties]);
  useEffect(() => { if (activeTab === 'payments') loadPayments(); }, [activeTab, loadPayments]);
  useEffect(() => { if (activeTab === 'verifications') loadPendingRevs(); }, [activeTab, loadPendingRevs]);
  useEffect(() => { if (activeTab === 'kyc') loadKYC(); }, [activeTab, loadKYC]);
  useEffect(() => { if (activeTab === 'fraud') loadFraud(); }, [activeTab, loadFraud]);
  useEffect(() => { if (activeTab === 'audit') loadAudit(); }, [activeTab, loadAudit]);

  if (loading && !stats) return <div className="min-h-screen bg-gray-50 flex items-center justify-center gap-3"><Spinner size="lg" /><span className="text-gray-500">Loading admin panel...</span></div>;

  const tabs: { key: Tab; label: string; icon: React.ReactNode; count?: number; color?: string }[] = [
    { key: 'overview', label: 'Overview', icon: <BarChart3 className="w-4 h-4" /> },
    { key: 'users', label: 'Users', icon: <Users className="w-4 h-4" />, count: stats?.total_users },
    { key: 'properties', label: 'Properties', icon: <Building2 className="w-4 h-4" />, count: stats?.total_properties },
    { key: 'payments', label: 'Payments', icon: <CreditCard className="w-4 h-4" /> },
    { key: 'verifications', label: 'Reviews', icon: <ShieldCheck className="w-4 h-4" />, count: stats?.pending_verifications, color: stats?.pending_verifications ? 'red' : undefined },
    { key: 'kyc', label: 'KYC', icon: <FileText className="w-4 h-4" /> },
    { key: 'fraud', label: 'Fraud', icon: <AlertTriangle className="w-4 h-4" /> },
    { key: 'audit', label: 'Audit Log', icon: <Activity className="w-4 h-4" /> },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gray-900 rounded-xl flex items-center justify-center shrink-0"><Settings className="w-5 h-5 text-white" /></div>
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-gray-900">Admin Panel</h1>
              <p className="text-gray-500 text-xs">Full system control</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="success"><Activity className="w-3 h-3" /> Live</Badge>
            <button onClick={loadStats} className="p-2 hover:bg-gray-100 rounded-lg" title="Refresh"><RefreshCw className="w-4 h-4 text-gray-500" /></button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-5 bg-gray-100 p-1 rounded-xl overflow-x-auto">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => navigateToTab(tab.key)}
              className={`flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2 rounded-lg text-xs sm:text-sm font-medium whitespace-nowrap transition-all ${
                activeTab === tab.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}>
              {tab.icon}
              <span className="hidden sm:inline">{tab.label}</span>
              {tab.count !== undefined && tab.count > 0 && (
                <span className={`text-xs px-1.5 py-0.5 rounded-full ${tab.color === 'red' ? 'bg-red-500 text-white' : 'bg-gray-700 text-white'}`}>{tab.count}</span>
              )}
            </button>
          ))}
        </div>

        {/* ═══════════ OVERVIEW ═══════════ */}
        {activeTab === 'overview' && stats && (
          <div className="space-y-5 animate-fade-in">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {[
                { l: 'Total Users', v: stats.total_users.toLocaleString(), i: <Users className="w-5 h-5" />, c: 'blue' },
                { l: 'Properties', v: stats.total_properties.toLocaleString(), i: <Building2 className="w-5 h-5" />, c: 'emerald' },
                { l: 'Revenue', v: `KES ${(stats.total_revenue/1000).toFixed(0)}K`, i: <DollarSign className="w-5 h-5" />, c: 'amber' },
                { l: 'Pending Reviews', v: stats.pending_verifications, i: <Clock className="w-5 h-5" />, c: stats.pending_verifications > 0 ? 'red' : 'emerald' },
              ].map(s => (
                <Card key={s.l} padding="sm">
                  <div className="flex items-center gap-3">
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${s.c === 'blue' ? 'bg-blue-50 text-blue-600' : s.c === 'emerald' ? 'bg-emerald-50 text-emerald-600' : s.c === 'amber' ? 'bg-amber-50 text-amber-600' : 'bg-red-50 text-red-600'}`}>{s.i}</div>
                    <div><p className="text-xs text-gray-500">{s.l}</p><p className="text-xl font-bold text-gray-900">{s.v}</p></div>
                  </div>
                </Card>
              ))}
            </div>

            <OverviewCharts charts={stats.charts} />
          </div>
        )}

        {/* ═══════════ USERS ═══════════ */}
        {activeTab === 'users' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1"><Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" /><input type="text" placeholder="Search users..." value={userSearch} onChange={e => { setUserSearch(e.target.value); setUserPage(0); }} className="w-full pl-9 pr-4 py-2 rounded-xl border border-gray-200 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500" /></div>
              <select value={roleFilter} onChange={e => { setRoleFilter(e.target.value); setUserPage(0); }} className="px-3 py-2 rounded-xl border border-gray-200 text-sm bg-white"><option value="">All Roles</option>{['buyer','seller','agent','landlord','admin','super_admin'].map(r=><option key={r} value={r}>{r.replace('_',' ')}</option>)}</select>
            </div>
            <Card padding="none" className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-sm">
                <thead><tr className="border-b bg-gray-50">{['#','Name','Email','Role','Status','Joined','Actions'].map(h=><th key={h} className="text-left text-xs font-semibold text-gray-500 px-3 py-3 uppercase">{h}</th>)}</tr></thead>
                <tbody>
                  {users.map(u => (
                    <tr key={u.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="px-3 py-2.5 text-xs text-gray-400">#{u.id}</td>
                      <td className="px-3 py-2.5"><div className="flex items-center gap-2"><div className="w-7 h-7 bg-emerald-100 rounded-full flex items-center justify-center text-emerald-700 text-xs font-semibold">{u.full_name?.[0]}</div><span className="font-medium text-gray-900">{u.full_name}</span></div></td>
                      <td className="px-3 py-2.5 text-xs text-gray-500">{u.email}</td>
                      <td className="px-3 py-2.5"><Badge variant={u.role==='admin'||u.role==='super_admin'?'danger':'default'} className="text-xs capitalize">{u.role?.replace('_',' ')}</Badge></td>
                      <td className="px-3 py-2.5"><Badge variant={u.is_active?'success':'danger'} className="text-xs">{u.is_active?'Active':'Banned'}</Badge></td>
                      <td className="px-3 py-2.5 text-xs text-gray-400">{new Date(u.created_at).toLocaleDateString()}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex gap-1">
                          <select value={u.role} onChange={e => exec(() => api.changeUserRole(u.id, e.target.value).then(loadUsers), `Role changed to ${e.target.value}`)} className="text-xs border rounded-lg px-1.5 py-1 bg-white">
                            {['buyer','seller','agent','landlord','admin'].map(r=><option key={r} value={r}>{r}</option>)}
                          </select>
                          <button onClick={() => exec(() => api.toggleUserActive(u.id).then(loadUsers), `User ${u.is_active?'banned':'unbanned'}`)} className={`text-xs px-2 py-1 rounded-lg ${u.is_active?'bg-red-50 text-red-600 hover:bg-red-100':'bg-emerald-50 text-emerald-600 hover:bg-emerald-100'}`} title={u.is_active?'Ban':'Unban'}>{u.is_active?<Ban className="w-3.5 h-3.5"/>:<UserCheck className="w-3.5 h-3.5"/>}</button>
                          <button onClick={() => setConfirm({title:'Delete User',msg:`Delete ${u.full_name} and ALL their data? This cannot be undone.`,action:()=>exec(()=>api.deleteUser(u.id).then(loadUsers),'User deleted'),danger:true})} className="text-xs px-2 py-1 rounded-lg bg-red-50 text-red-600 hover:bg-red-100"><Trash2 className="w-3.5 h-3.5"/></button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {users.length===0 && <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">No users found</td></tr>}
                </tbody>
              </table>
              <div className="flex items-center justify-between px-4 py-3 border-t text-sm">
                <span className="text-gray-500">{usersTotal} total</span>
                <div className="flex gap-2">
                  <button disabled={userPage===0} onClick={()=>setUserPage(p=>p-1)} className="px-3 py-1 rounded-lg border text-xs disabled:opacity-30">Prev</button>
                  <button disabled={(userPage+1)*20>=usersTotal} onClick={()=>setUserPage(p=>p+1)} className="px-3 py-1 rounded-lg border text-xs disabled:opacity-30">Next</button>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* ═══════════ PROPERTIES ═══════════ */}
        {activeTab === 'properties' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <select value={propStatus} onChange={e=>setPropStatus(e.target.value)} className="px-3 py-2 rounded-xl border border-gray-200 text-sm bg-white">
                <option value="">All Statuses</option>
                {['draft','pending_review','active','suspended','sold','rented'].map(s=><option key={s} value={s}>{s.replace('_',' ')}</option>)}
              </select>
              <span className="text-sm text-gray-500">{propsTotal} properties</span>
            </div>
            <Card padding="none" className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-sm">
                <thead><tr className="border-b bg-gray-50">{['#','Property','Price','Status','Trust','Owner','Actions'].map(h=><th key={h} className="text-left text-xs font-semibold text-gray-500 px-3 py-3 uppercase">{h}</th>)}</tr></thead>
                <tbody>
                  {properties.map(p => (
                    <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="px-3 py-2.5 text-xs text-gray-400">#{p.id}</td>
                      <td className="px-3 py-2.5"><div className="flex items-center gap-2"><Home className="w-4 h-4 text-gray-400"/><div><p className="font-medium text-gray-900 truncate max-w-[180px]">{p.title}</p><p className="text-xs text-gray-400 flex items-center gap-1"><MapPin className="w-3 h-3"/>{p.city}</p></div></div></td>
                      <td className="px-3 py-2.5 font-medium">{formatCurrency(p.price)}</td>
                      <td className="px-3 py-2.5"><Badge variant={p.status==='active'?'success':p.status==='pending_review'?'warning':p.status==='suspended'?'danger':'default'} className="text-xs capitalize">{p.status?.replace('_',' ')}</Badge></td>
                      <td className="px-3 py-2.5">{p.trust_score ? <span className={`font-medium text-sm ${p.trust_score>=75?'text-emerald-600':p.trust_score>=50?'text-amber-600':'text-red-600'}`}>{p.trust_score}%</span> : <span className="text-xs text-gray-400">N/A</span>}</td>
                      <td className="px-3 py-2.5 text-xs text-gray-500">{p.owner?.full_name || 'N/A'}</td>
                      <td className="px-3 py-2.5">
                        <div className="flex gap-1">
                          <select value={p.status} onChange={e=>exec(()=>api.setPropertyStatus(p.id,e.target.value).then(loadProperties),`Status: ${e.target.value}`)} className="text-xs border rounded-lg px-1.5 py-1 bg-white">
                            {['active','pending_review','suspended','sold','rented'].map(s=><option key={s} value={s}>{s.replace('_',' ')}</option>)}
                          </select>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {properties.length===0 && <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">No properties found</td></tr>}
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* ═══════════ PAYMENTS ═══════════ */}
        {activeTab === 'payments' && (
          <div className="space-y-4 animate-fade-in">
            <div className="flex items-center gap-3">
              <select value={paymentStatus} onChange={e=>setPaymentStatus(e.target.value)} className="px-3 py-2 rounded-xl border border-gray-200 text-sm bg-white">
                <option value="">All Statuses</option>
                {['pending','processing','completed','failed','refunded'].map(s=><option key={s} value={s}>{s}</option>)}
              </select>
              <span className="text-sm text-gray-500">{paymentsTotal} payments</span>
            </div>
            <Card padding="none" className="overflow-x-auto">
              <table className="w-full min-w-[700px] text-sm">
                <thead><tr className="border-b bg-gray-50">{['#','Amount','Purpose','Method','Status','Receipt','Date','Actions'].map(h=><th key={h} className="text-left text-xs font-semibold text-gray-500 px-3 py-3 uppercase">{h}</th>)}</tr></thead>
                <tbody>
                  {payments.map(p => (
                    <tr key={p.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="px-3 py-2.5 text-xs text-gray-400">#{p.id}</td>
                      <td className="px-3 py-2.5 font-bold text-gray-900">KES {p.amount?.toLocaleString()}</td>
                      <td className="px-3 py-2.5 text-xs capitalize">{p.purpose?.replace(/_/g,' ')}</td>
                      <td className="px-3 py-2.5 text-xs uppercase text-gray-500">{p.method}</td>
                      <td className="px-3 py-2.5"><Badge variant={p.status==='completed'?'success':p.status==='failed'?'danger':p.status==='refunded'?'purple':p.status==='processing'?'warning':'default'} className="text-xs">{p.status}</Badge></td>
                      <td className="px-3 py-2.5 text-xs font-mono text-gray-500">{p.mpesa_receipt || '—'}</td>
                      <td className="px-3 py-2.5 text-xs text-gray-400">{p.created_at ? new Date(p.created_at).toLocaleDateString() : '—'}</td>
                      <td className="px-3 py-2.5">
                        {p.status === 'completed' && (
                          <button onClick={()=>setConfirm({title:'Refund Payment',msg:`Refund KES ${p.amount?.toLocaleString()} to user #${p.user_id}?`,action:()=>exec(()=>api.refundPayment(p.id).then(loadPayments),'Payment refunded'),danger:true})} className="text-xs px-2 py-1 rounded-lg bg-amber-50 text-amber-700 hover:bg-amber-100">Refund</button>
                        )}
                      </td>
                    </tr>
                  ))}
                  {payments.length===0 && <tr><td colSpan={8} className="px-4 py-12 text-center text-gray-400">No payments found</td></tr>}
                </tbody>
              </table>
            </Card>
          </div>
        )}

        {/* ═══════════ VERIFICATIONS ═══════════ */}
        {activeTab === 'verifications' && (
          <div className="space-y-4 animate-fade-in">
            <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
              {pendingRevs.map(v => (
                <Card key={v.id} padding="sm" className={`border-l-4 ${v.ai_recommendation==='reject'?'border-l-red-500':v.ai_recommendation==='approve'?'border-l-emerald-500':'border-l-amber-500'}`}>
                  <div className="flex items-start justify-between mb-2"><div><p className="text-xs text-gray-400">Verification #{v.id}</p><p className="text-sm font-semibold">Property #{v.property_id}</p></div><Badge variant={v.status==='flagged'?'danger':'default'} className="text-xs">{v.status}</Badge></div>
                  <div className="grid grid-cols-2 gap-2 mb-2 text-xs">
                    <div><span className="text-gray-400">Fraud:</span> <span className={`font-semibold ${v.fraud_risk_score>30?'text-red-600':'text-emerald-600'}`}>{v.fraud_risk_score}%</span></div>
                    <div><span className="text-gray-400">Trust:</span> <span className={`font-semibold ${v.trust_score>=75?'text-emerald-600':v.trust_score>=50?'text-amber-600':'text-red-600'}`}>{v.trust_score}%</span></div>
                    <div><span className="text-gray-400">AI:</span> <span className="font-semibold capitalize">{v.ai_recommendation}</span></div>
                  </div>
                  {v.ai_summary && <p className="text-xs text-gray-500 mb-3 line-clamp-2">{v.ai_summary}</p>}
                  <div className="flex gap-2">
                    <button onClick={()=>exec(async()=>{await api.reviewVerification(v.id,'approved');loadPendingRevs();loadStats();},'Approved')} className="flex-1 flex items-center justify-center gap-1 text-xs bg-emerald-50 text-emerald-700 px-2 py-1.5 rounded-lg hover:bg-emerald-100"><Check className="w-3 h-3"/>Approve</button>
                    <button onClick={()=>exec(async()=>{await api.reviewVerification(v.id,'flagged');loadPendingRevs();loadStats();},'Flagged')} className="flex-1 flex items-center justify-center gap-1 text-xs bg-amber-50 text-amber-700 px-2 py-1.5 rounded-lg hover:bg-amber-100">Flag</button>
                    <button onClick={()=>exec(async()=>{await api.reviewVerification(v.id,'rejected');loadPendingRevs();loadStats();},'Rejected')} className="flex-1 flex items-center justify-center gap-1 text-xs bg-red-50 text-red-700 px-2 py-1.5 rounded-lg hover:bg-red-100"><X className="w-3 h-3"/>Reject</button>
                  </div>
                </Card>
              ))}
              {pendingRevs.length===0 && <div className="col-span-full text-center py-12 text-gray-400"><ShieldCheck className="w-12 h-12 mx-auto mb-3 text-emerald-300"/><p>All clear — no pending verifications.</p></div>}
            </div>
          </div>
        )}

        {/* ═══════════ KYC ═══════════ */}
        {activeTab === 'kyc' && (
          <div className="space-y-4 animate-fade-in">
            <p className="text-sm text-gray-500">{kycTotal} pending KYC submissions</p>
            <div className="grid md:grid-cols-2 gap-4">
              {kycItems.map(k => (
                <Card key={k.id} padding="sm">
                  <div className="flex items-start justify-between mb-3"><div><p className="text-xs text-gray-400">KYC #{k.id} — User #{k.user_id}</p><p className="text-sm font-semibold capitalize">{k.id_type?.replace('_',' ')}: {k.id_number}</p></div><Badge variant="warning" className="text-xs">{k.status}</Badge></div>
                  {k.id_front_url && <p className="text-xs text-gray-500 mb-3">ID Document uploaded</p>}
                  <div className="flex gap-2">
                    <button onClick={()=>exec(async()=>{await api.reviewKYC(k.id,'approved');loadKYC();},'KYC Approved')} className="flex-1 text-xs bg-emerald-50 text-emerald-700 px-2 py-1.5 rounded-lg hover:bg-emerald-100"><Check className="w-3 h-3 inline"/>Approve</button>
                    <button onClick={()=>exec(async()=>{await api.reviewKYC(k.id,'rejected','Does not meet requirements');loadKYC();},'KYC Rejected')} className="flex-1 text-xs bg-red-50 text-red-700 px-2 py-1.5 rounded-lg hover:bg-red-100"><X className="w-3 h-3 inline"/>Reject</button>
                  </div>
                </Card>
              ))}
              {kycItems.length===0 && <div className="col-span-full text-center py-12 text-gray-400"><FileText className="w-12 h-12 mx-auto mb-3 text-gray-300"/><p>No pending KYC submissions.</p></div>}
            </div>
          </div>
        )}

        {/* ═══════════ FRAUD ═══════════ */}
        {activeTab === 'fraud' && (
          <div className="space-y-4 animate-fade-in">
            <div className="grid gap-4">
              {fraudItems.map(r => (
                <Card key={r.id} padding="sm" className={`border-l-4 ${r.status==='confirmed'?'border-l-red-500':r.status==='false_report'?'border-l-emerald-500':'border-l-amber-500'}`}>
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-2">
                    <div><p className="text-sm font-semibold">Report #{r.id} by User #{r.reporter_id}</p><p className="text-xs text-gray-500">{new Date(r.created_at).toLocaleString()}</p></div>
                    <Badge variant={r.status==='confirmed'?'danger':r.status==='false_report'?'success':'warning'} className="text-xs">{r.status}</Badge>
                  </div>
                  <p className="text-sm text-gray-700 mb-2">{r.description}</p>
                  <div className="flex flex-wrap gap-2 text-xs text-gray-500 mb-3">
                    {r.reported_phone && <span>📱 {r.reported_phone}</span>}
                    {r.reported_email && <span>📧 {r.reported_email}</span>}
                    {r.reported_name && <span>👤 {r.reported_name}</span>}
                    {r.reported_title_deed && <span>📜 Title: {r.reported_title_deed}</span>}
                  </div>
                  {r.status === 'pending' && (
                    <div className="flex gap-2">
                      <button onClick={()=>exec(async()=>{await api.reviewFraudReport(r.id,'confirmed');loadFraud();},'Fraud confirmed')} className="text-xs bg-red-50 text-red-700 px-2 py-1.5 rounded-lg hover:bg-red-100">Confirm Fraud</button>
                      <button onClick={()=>exec(async()=>{await api.reviewFraudReport(r.id,'false_report');loadFraud();},'Marked as false')} className="text-xs bg-emerald-50 text-emerald-700 px-2 py-1.5 rounded-lg hover:bg-emerald-100">False Report</button>
                    </div>
                  )}
                  {r.review_notes && <p className="text-xs text-gray-400 mt-2">Notes: {r.review_notes}</p>}
                </Card>
              ))}
              {fraudItems.length===0 && <div className="text-center py-12 text-gray-400"><Shield className="w-12 h-12 mx-auto mb-3 text-emerald-300"/><p>No fraud reports.</p></div>}
            </div>
          </div>
        )}

        {/* ═══════════ AUDIT LOG ═══════════ */}
        {activeTab === 'audit' && (
          <div className="space-y-4 animate-fade-in">
            <p className="text-sm text-gray-500">{auditTotal} audit entries</p>
            <Card padding="none" className="overflow-x-auto">
              <table className="w-full min-w-[600px] text-sm">
                <thead><tr className="border-b bg-gray-50">{['ID','User','Action','Resource','Details','IP','Time'].map(h=><th key={h} className="text-left text-xs font-semibold text-gray-500 px-3 py-3 uppercase">{h}</th>)}</tr></thead>
                <tbody>
                  {auditItems.map(l => (
                    <tr key={l.id} className="border-b border-gray-50 hover:bg-gray-50/50">
                      <td className="px-3 py-2 text-xs text-gray-400">#{l.id}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{l.user_id || 'system'}</td>
                      <td className="px-3 py-2 text-xs font-medium text-gray-700">{l.action}</td>
                      <td className="px-3 py-2 text-xs text-gray-500">{l.resource_type}#{l.resource_id}</td>
                      <td className="px-3 py-2 text-xs text-gray-400 max-w-[200px] truncate">{typeof l.details==='object'?JSON.stringify(l.details).slice(0,80):l.details}</td>
                      <td className="px-3 py-2 text-xs font-mono text-gray-400">{l.ip_address}</td>
                      <td className="px-3 py-2 text-xs text-gray-400">{l.created_at ? new Date(l.created_at).toLocaleString() : '—'}</td>
                    </tr>
                  ))}
                  {auditItems.length===0 && <tr><td colSpan={7} className="px-4 py-12 text-center text-gray-400">No audit logs.</td></tr>}
                </tbody>
              </table>
            </Card>
          </div>
        )}
      </div>

      {/* Confirm Dialog */}
      <ConfirmDialog
        open={!!confirm}
        title={confirm?.title || ''}
        message={confirm?.msg || ''}
        confirmLabel={confirm?.danger ? 'Delete' : 'Confirm'}
        danger={confirm?.danger}
        onConfirm={() => { confirm?.action(); setConfirm(null); }}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}

// ── Confirm Dialog ────────────────────────────────────────────────────────

function ConfirmDialog({
  open, title, message, confirmLabel, danger, onConfirm, onCancel,
}: {
  open: boolean; title: string; message: string;
  confirmLabel?: string; danger?: boolean;
  onConfirm: () => void; onCancel: () => void;
}) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/40 backdrop-blur-sm" onClick={onCancel} />
      <div className="relative bg-white rounded-2xl shadow-xl p-6 max-w-md w-full mx-4">
        <h3 className="text-lg font-bold text-gray-900 mb-2">{title}</h3>
        <p className="text-gray-600 text-sm mb-6">{message}</p>
        <div className="flex gap-3 justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-sm font-medium text-gray-700 bg-gray-100 rounded-xl hover:bg-gray-200">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            className={`px-4 py-2 text-sm font-medium text-white rounded-xl ${
              danger ? 'bg-red-600 hover:bg-red-700' : 'bg-emerald-600 hover:bg-emerald-700'
            }`}
          >
            {confirmLabel || 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}
