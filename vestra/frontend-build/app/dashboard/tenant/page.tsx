'use client';

import { useEffect, useState, useCallback, useRef } from 'react';
import Link from 'next/link';
import AuthGuard from '@/components/layout/AuthGuard';
import RoleBanner from '@/components/dashboard/RoleBanner';
import StatCardGrid, { type StatItem } from '@/components/dashboard/StatCardGrid';
import QuickActions, { type QuickAction } from '@/components/dashboard/QuickActions';
import { Card, Badge, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import {
  Home, CreditCard, Calendar, Wrench, Phone,
  FileText, Bell, DollarSign, Key, Shield,
  Star, MessageSquare, AlertCircle, Plus,
  Clock, CheckCircle, XCircle, ArrowRight, Zap, Search,
  Smartphone, Download, Timer, TrendingUp, Heart,
  MapPin, BedDouble, Bath, Receipt, Sparkles,
} from 'lucide-react';

interface TenantRental {
  id: number; tenant_id: number;
  unit_name: string; unit_type: string; city: string; bedrooms: number;
  monthly_rent_kes: number; deposit_kes: number;
  lease_start: string; lease_end: string; days_remaining: number;
  landlord_name: string; landlord_phone: string; landlord_email?: string;
  payment_status: string;
  water_kes?: number; electricity_kes?: number; service_charge_kes?: number;
}

export default function TenantDashboardPage() {
  return (
    <AuthGuard requireAuth requireRoles={['tenant']}>
      <TenantContent />
    </AuthGuard>
  );
}

function TenantContent() {
  const { user } = useAuthStore();
  const [rental, setRental] = useState<TenantRental | null>(null);
  const [payments, setPayments] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [paying, setPaying] = useState(false);
  const [paymentSent, setPaymentSent] = useState(false);
  const [checkingPayment, setCheckingPayment] = useState(false);
  const [paymentConfirmed, setPaymentConfirmed] = useState(false);
  const [paymentTimeout, setPaymentTimeout] = useState(false);
  const [lastReceipt, setLastReceipt] = useState<any>(null);
  const pollCount = useRef(0);

  useEffect(() => { loadData(); }, []);

  // ── Auto-poll for payment confirmation (max 20 attempts = 60 seconds) ──
  useEffect(() => {
    if (!paymentSent || paymentConfirmed) return;
    pollCount.current = 0;
    setPaymentTimeout(false);
    const interval = setInterval(async () => {
      pollCount.current += 1;
      if (pollCount.current > 20) {
        clearInterval(interval);
        setPaymentSent(false);
        setPaymentTimeout(true);
        return;
      }
      setCheckingPayment(true);
      try {
        const res = await api.client.get('/api/payments/my');
        const allPayments = res.data || [];
        const recentRent = allPayments.find((p: any) =>
          (p.purpose === 'rent' || (p.description || '').toLowerCase().includes('rent')) &&
          p.status === 'completed' &&
          new Date(p.created_at).getTime() > Date.now() - 60000 // last 1 minute
        );
        if (recentRent) {
          setPaymentConfirmed(true);
          setPaymentSent(false);
          setLastReceipt({
            id: recentRent.id,
            receipt_number: `RCP-${String(recentRent.id).padStart(6, '0')}`,
            amount: recentRent.amount,
            date: recentRent.created_at,
            mpesa_ref: recentRent.mpesa_receipt_number || '',
          });
          loadData(); // Refresh all data
        }
      } catch {} finally {
        setCheckingPayment(false);
      }
    }, 3000); // Check every 3 seconds
    return () => clearInterval(interval);
  }, [paymentSent, paymentConfirmed]);

  const loadData = async () => {
    setLoading(true); setError('');
    try {
      const [rentalResp, paymentResp] = await Promise.all([
        api.client.get('/api/rentals/my-rental').catch(() => ({ data: null })),
        api.client.get('/api/payments/my').catch(() => ({ data: [] })),
      ]);
      setRental(rentalResp.data);
      setPayments(Array.isArray(paymentResp.data) ? paymentResp.data : []);
    } catch {
      setError('Unable to load rental information.');
    } finally {
      setLoading(false);
    }
  };

  // ── ONE-CLICK PAY RENT ──
  const handlePayRent = useCallback(async () => {
    if (!rental || !user?.phone) {
      alert('Please add your phone number in settings first.');
      return;
    }
    setPaying(true);
    try {
      const totalDue = rental.monthly_rent_kes + (rental.water_kes || 0) + (rental.electricity_kes || 0) + (rental.service_charge_kes || 0);
      const res = await api.client.post('/api/payments/mpesa/initiate', {
        phone_number: user.phone,
        amount: totalDue,
        purpose: 'rent',
        reference_id: rental.id,
      });
      setPaymentSent(true);
      setPaymentConfirmed(false);
    } catch (err: any) {
      alert(err?.response?.data?.detail || 'Payment failed. Please try again.');
    } finally {
      setPaying(false);
    }
  }, [rental, user]);

  if (loading) return (
    <div className="flex justify-center py-32"><Spinner size="lg" /></div>
  );

  if (error && !rental) return (
    <div className="text-center py-32">
      <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
      <p className="text-red-600 mb-4">{error}</p>
      <Button onClick={loadData}>Retry</Button>
    </div>
  );

  // ── No Rental — Onboarding ──
  if (!rental) return <NoRentalView />;

  const totalDue = rental.monthly_rent_kes + (rental.water_kes || 0) + (rental.electricity_kes || 0) + (rental.service_charge_kes || 0);
  const leaseEnd = rental.lease_end ? new Date(rental.lease_end) : null;
  const daysLeft = leaseEnd ? Math.ceil((leaseEnd.getTime() - Date.now()) / (1000 * 60 * 60 * 24)) : 0;

  const stats: StatItem[] = [
    {
      label: 'Monthly Rent',
      value: `KES ${totalDue.toLocaleString()}`,
      icon: <DollarSign className="w-5 h-5" />,
      subtext: paymentConfirmed ? '✅ Paid this month' : paymentSent ? '⏳ Waiting for M-Pesa...' : 'Ready to pay',
    },
    {
      label: 'Lease Remaining',
      value: `${daysLeft} days`,
      icon: <Calendar className="w-5 h-5" />,
      trend: daysLeft > 90 ? { value: 'Secure', positive: true } :
             daysLeft > 30 ? { value: 'Mid-term', positive: true } :
             { value: 'Expiring soon', positive: false },
    },
    {
      label: 'Receipts',
      value: payments.filter(p => p.status === 'completed').length,
      icon: <Receipt className="w-5 h-5" />,
      subtext: 'Digital records',
    },
    {
      label: 'Landlord',
      value: rental.landlord_name || 'N/A',
      icon: <Phone className="w-5 h-5" />,
      subtext: rental.landlord_phone || 'Contact via messages',
    },
  ];

  const actions: QuickAction[] = [
    {
      label: 'Find Next Home',
      desc: 'Browse rental listings',
      icon: <Search className="w-4 h-4" />,
      href: '/dashboard/tenant/discover',
      iconBg: 'bg-orange-600',
    },
    {
      label: 'My Receipts',
      desc: `${payments.filter(p => p.status === 'completed').length} digital receipts`,
      icon: <FileText className="w-4 h-4" />,
      href: '/dashboard/tenant/receipts',
      iconBg: 'bg-emerald-600',
    },
    {
      label: 'Request Maintenance',
      desc: 'Report an issue',
      icon: <Wrench className="w-4 h-4" />,
      href: '/dashboard/tenant/maintenance',
      iconBg: 'bg-amber-600',
    },
    {
      label: 'Message Landlord',
      desc: rental.landlord_phone || 'Send a message',
      icon: <MessageSquare className="w-4 h-4" />,
      href: '/messages',
      iconBg: 'bg-blue-600',
    },
  ];

  return (
    <div className="space-y-6 animate-fade-in">
      <RoleBanner subtitle={`${rental.unit_name} — ${rental.city}`}>
        {/* PAY RENT BUTTON — ONE CLICK */}
        {!paymentConfirmed ? (
          <Button
            size="lg"
            onClick={handlePayRent}
            loading={paying}
            className="bg-white text-orange-700 hover:bg-orange-50 gap-2 font-semibold shadow-lg"
          >
            {paying ? (
              <><Smartphone className="w-4 h-4 animate-pulse" /> Sending STK Push...</>
            ) : paymentSent ? (
              <><Timer className="w-4 h-4 animate-spin" /> Check Your Phone</>
            ) : (
              <><CreditCard className="w-4 h-4" /> Pay KES {totalDue.toLocaleString()}</>
            )}
          </Button>
        ) : (
          <div className="bg-white/15 backdrop-blur border border-white/20 rounded-xl px-4 py-2 flex items-center gap-3">
            <CheckCircle className="w-5 h-5 text-emerald-300" />
            <div>
              <p className="text-white font-semibold text-sm">Paid ✓</p>
              <p className="text-white/70 text-xs">Receipt #{lastReceipt?.receipt_number}</p>
            </div>
            <Link href="/dashboard/tenant/receipts">
              <Button size="sm" className="bg-white text-emerald-700 hover:bg-emerald-50 text-xs">
                <Download className="w-3 h-3" /> Receipt
              </Button>
            </Link>
          </div>
        )}
      </RoleBanner>

      {/* Payment Status Banner */}
      {paymentSent && !paymentConfirmed && !paymentTimeout && (
        <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl p-6 text-center animate-pulse">
          <Smartphone className="w-12 h-12 text-amber-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-amber-800 mb-2">Check Your Phone 📱</h3>
          <p className="text-amber-700 mb-1">M-Pesa STK Push sent to <strong>{user?.phone}</strong></p>
          <p className="text-amber-600 text-sm">Enter your M-Pesa PIN to complete payment. This page will auto-update.</p>
          {checkingPayment && (
            <div className="flex items-center justify-center gap-2 mt-4 text-amber-500">
              <Spinner size="sm" />
              <span className="text-sm">Waiting for payment confirmation...</span>
            </div>
          )}
        </div>
      )}

      {/* Payment Timeout Banner */}
      {paymentTimeout && (
        <div className="bg-red-50 border-2 border-red-200 rounded-2xl p-6 text-center">
          <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-3" />
          <h3 className="text-lg font-bold text-red-800 mb-2">Payment Timed Out</h3>
          <p className="text-red-700 mb-4">We didn't receive a payment confirmation after 60 seconds. The STK Push may have expired.</p>
          <Button
            onClick={() => setPaymentTimeout(false)}
            className="bg-red-600 hover:bg-red-500 text-white"
          >
            Try Again
          </Button>
        </div>
      )}

      {/* Payment Confirmed Banner */}
      {paymentConfirmed && lastReceipt && (
        <div className="bg-emerald-50 border-2 border-emerald-200 rounded-2xl p-6 animate-scale-in">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-emerald-500 rounded-2xl flex items-center justify-center">
              <CheckCircle className="w-8 h-8 text-white" />
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-bold text-emerald-800">Payment Successful! 🎉</h3>
              <p className="text-emerald-700">KES {lastReceipt.amount?.toLocaleString()} received. Receipt auto-generated.</p>
              <div className="flex gap-2 mt-2">
                <Link href="/dashboard/tenant/receipts">
                  <Button size="sm" className="bg-emerald-600 hover:bg-emerald-500 text-xs gap-1">
                    <Download className="w-3 h-3" /> View Receipt
                  </Button>
                </Link>
                <Button
                  size="sm"
                  variant="outline"
                  className="text-xs border-emerald-200 text-emerald-700"
                  onClick={() => setPaymentConfirmed(false)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      <StatCardGrid stats={stats} columns={4} />

      <div className="grid lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 space-y-6">
          {/* Rental Details + Lease Info */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Home className="w-5 h-5 text-orange-600" /> Your Home
              </h2>
              <Badge variant={paymentConfirmed ? 'success' : 'warning'}>
                {paymentConfirmed ? 'Rent Paid ✓' : 'Payment Pending'}
              </Badge>
            </div>
            <div className="px-5 pb-5 grid sm:grid-cols-2 gap-3">
              <DetailBox bg="bg-orange-50" label="Property" value={rental.unit_name} sub={`${rental.city} · ${rental.bedrooms}br · ${rental.unit_type}`} />
              <DetailBox bg="bg-amber-50" label="Monthly Rent" value={`KES ${rental.monthly_rent_kes.toLocaleString()}`} sub={`Due on the ${new Date().getDate()}th`} />
              <DetailBox bg="bg-blue-50" label="Lease Period" value={`${new Date(rental.lease_start).toLocaleDateString()} — ${new Date(rental.lease_end).toLocaleDateString()}`} sub={`${daysLeft} days remaining`} />
              <DetailBox bg="bg-emerald-50" label="Landlord" value={rental.landlord_name} sub={rental.landlord_phone || 'Contact via messages'} />
            </div>

            {/* Utility breakdown if applicable */}
            {(rental.water_kes || rental.electricity_kes || rental.service_charge_kes) && (
              <div className="px-5 pb-5 border-t pt-4">
                <h3 className="text-sm font-semibold text-gray-700 mb-2">Bill Breakdown</h3>
                <div className="space-y-1.5 text-sm">
                  <div className="flex justify-between"><span className="text-gray-500">Rent</span><span className="font-semibold">KES {rental.monthly_rent_kes.toLocaleString()}</span></div>
                  {rental.water_kes ? <div className="flex justify-between"><span className="text-gray-500">Water</span><span className="text-blue-600">KES {rental.water_kes.toLocaleString()}</span></div> : null}
                  {rental.electricity_kes ? <div className="flex justify-between"><span className="text-gray-500">Electricity</span><span className="text-amber-600">KES {rental.electricity_kes.toLocaleString()}</span></div> : null}
                  {rental.service_charge_kes ? <div className="flex justify-between"><span className="text-gray-500">Service Charge</span><span className="text-gray-600">KES {rental.service_charge_kes.toLocaleString()}</span></div> : null}
                  <div className="flex justify-between border-t pt-1.5 font-bold"><span className="text-gray-700">Total Due</span><span className="text-orange-600">KES {totalDue.toLocaleString()}</span></div>
                </div>
              </div>
            )}
          </Card>

          {/* Payment History Timeline */}
          <Card padding="none">
            <div className="px-5 pt-4 pb-3 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Receipt className="w-5 h-5 text-orange-600" /> Payment History
              </h2>
              <Link href="/dashboard/tenant/receipts">
                <Button size="sm" variant="ghost" className="text-xs text-orange-600 gap-1">
                  All Receipts <ArrowRight className="w-3 h-3" />
                </Button>
              </Link>
            </div>
            {payments.length === 0 ? (
              <div className="text-center py-10">
                <Receipt className="w-10 h-10 text-gray-200 mx-auto mb-3" />
                <p className="text-sm text-gray-500">No payments yet. Pay your first rent!</p>
              </div>
            ) : (
              <div className="px-5 pb-4">
                {/* Timeline */}
                <div className="relative">
                  {payments.slice(0, 8).map((p, i) => (
                    <div key={p.id} className="flex gap-3 pb-4 last:pb-0">
                      {/* Timeline line */}
                      <div className="flex flex-col items-center">
                        <div className={`w-3 h-3 rounded-full border-2 flex-shrink-0 ${
                          p.status === 'completed' ? 'bg-emerald-500 border-emerald-500' :
                          p.status === 'failed' ? 'bg-red-500 border-red-500' :
                          'bg-amber-500 border-amber-500'
                        }`} />
                        {i < payments.slice(0, 8).length - 1 && (
                          <div className="w-0.5 flex-1 bg-gray-200 mt-1" />
                        )}
                      </div>
                      <div className="flex-1 min-w-0 pb-2">
                        <div className="flex items-center justify-between">
                          <p className="text-sm font-semibold text-gray-900">
                            KES {p.amount?.toLocaleString()}
                          </p>
                          <Badge variant={p.status === 'completed' ? 'success' : p.status === 'failed' ? 'danger' : 'warning'} className="text-xs">
                            {p.status}
                          </Badge>
                        </div>
                        <p className="text-xs text-gray-500">
                          {new Date(p.created_at).toLocaleDateString('en-KE', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' })}
                        </p>
                        {p.mpesa_receipt_number && (
                          <p className="text-xs text-gray-400 font-mono mt-0.5">M-Pesa: {p.mpesa_receipt_number}</p>
                        )}
                        {p.status === 'completed' && (
                          <Link href="/dashboard/tenant/receipts" className="text-xs text-orange-600 hover:underline mt-0.5 inline-block">
                            View Receipt →
                          </Link>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-5">
          {/* ONE-CLICK PAY CARD */}
          <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-orange-600 via-orange-500 to-amber-600 p-6 text-white">
            <div className="absolute top-0 right-0 w-40 h-40 bg-white/5 rounded-full -translate-y-1/2 translate-x-1/2" />
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-4">
                <Smartphone className="w-10 h-10 text-orange-200" />
                {paymentConfirmed && <CheckCircle className="w-6 h-6 text-emerald-200" />}
              </div>
              {!paymentConfirmed ? (
                <>
                  <h3 className="font-bold text-lg mb-2">Pay Rent Now</h3>
                  <p className="text-orange-100 text-sm mb-2">
                    Total due: <strong className="text-white text-lg">KES {totalDue.toLocaleString()}</strong>
                  </p>
                  <p className="text-orange-100 text-xs mb-5 leading-relaxed">
                    One click sends M-Pesa STK Push to your phone. Enter PIN to pay. Receipt auto-generated.
                  </p>
                  <Button
                    onClick={handlePayRent}
                    loading={paying || paymentSent}
                    className="bg-white text-orange-700 hover:bg-orange-50 w-full font-semibold"
                    size="lg"
                  >
                    {paying ? 'Sending...' : paymentSent ? 'Check Your Phone 📱' : `Pay KES ${totalDue.toLocaleString()}`}
                  </Button>
                </>
              ) : (
                <>
                  <h3 className="font-bold text-lg mb-2">All Paid Up! 🎉</h3>
                  <p className="text-orange-100 text-sm mb-5">
                    Receipt <strong className="text-white">{lastReceipt?.receipt_number}</strong> is ready.
                  </p>
                  <Link href="/dashboard/tenant/receipts">
                    <Button className="bg-white text-orange-700 hover:bg-orange-50 w-full font-semibold">
                      <Download className="w-4 h-4" /> Download Receipt
                    </Button>
                  </Link>
                </>
              )}
            </div>
          </div>

          <QuickActions actions={actions} />

          {/* How It Works — Free Tenant Tools */}
          <Card padding="md">
            <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2 text-sm">
              <Sparkles className="w-4 h-4 text-orange-600" />
              Your Free Tenant Tools
            </h3>
            <div className="space-y-3">
              {[
                { icon: <Smartphone className="w-4 h-4" />, text: 'One-click M-Pesa rent payment' },
                { icon: <Receipt className="w-4 h-4" />, text: 'Digital receipts stored forever' },
                { icon: <Wrench className="w-4 h-4" />, text: 'Maintenance request tracking' },
                { icon: <Search className="w-4 h-4" />, text: 'Find your next rental home' },
                { icon: <MessageSquare className="w-4 h-4" />, text: 'Direct messaging with landlord' },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3 text-sm">
                  <div className="w-8 h-8 bg-orange-50 rounded-lg flex items-center justify-center text-orange-600">
                    {item.icon}
                  </div>
                  <span className="text-gray-600">{item.text}</span>
                </div>
              ))}
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

// ── No Rental View — Helpful Onboarding ──────────────────────────────────

function NoRentalView() {
  return (
    <div className="space-y-8 animate-fade-in">
      <RoleBanner subtitle="Welcome to your free tenant portal. Let's find your next home." />

      <div className="max-w-4xl mx-auto">
        <div className="text-center mb-12">
          <div className="w-24 h-24 bg-orange-100 rounded-3xl flex items-center justify-center mx-auto mb-6 animate-float">
            <Home className="w-12 h-12 text-orange-600" />
          </div>
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Your Free Tenant Portal</h2>
          <p className="text-gray-500 max-w-lg mx-auto mb-8 text-lg">
            Your landlord adds you to their system, and you get everything for free — pay rent, get receipts, request maintenance, find your next home.
          </p>

          <div className="grid md:grid-cols-3 gap-4 mb-8">
            {[
              { icon: <Search className="w-6 h-6" />, title: 'Find Rentals', desc: 'Browse verified rental listings across Kenya' },
              { icon: <CreditCard className="w-6 h-6" />, title: 'Pay via M-Pesa', desc: 'One-click STK Push, auto-receipt' },
              { icon: <Shield className="w-6 h-6" />, title: '100% Free', desc: 'No subscription, no fees for tenants' },
            ].map((f, i) => (
              <Card key={i} padding="md" className="text-center hover:shadow-lg transition-all">
                <div className="w-12 h-12 bg-orange-100 rounded-xl flex items-center justify-center mx-auto mb-3 text-orange-600">
                  {f.icon}
                </div>
                <h3 className="font-bold text-gray-900 mb-1">{f.title}</h3>
                <p className="text-xs text-gray-500">{f.desc}</p>
              </Card>
            ))}
          </div>

          <div className="flex gap-3 justify-center">
            <Link href="/dashboard/tenant/discover">
              <Button size="lg" className="gap-2 bg-orange-600 hover:bg-orange-500">
                <Search className="w-4 h-4" /> Find a Home
              </Button>
            </Link>
            <Link href="/market">
              <Button size="lg" variant="outline" className="gap-2">
                Browse Market
              </Button>
            </Link>
          </div>
        </div>

        <div className="bg-gradient-to-r from-orange-50 to-amber-50 rounded-2xl p-8 text-center">
          <h3 className="text-xl font-bold text-gray-900 mb-4">How It Works</h3>
          <div className="grid md:grid-cols-4 gap-4">
            {[
              { step: '1', title: 'Landlord Adds You', desc: 'Your landlord adds you to their unit with your phone number' },
              { step: '2', title: 'See Your Rental', desc: 'Log in and see your rental, lease, and payment info' },
              { step: '3', title: 'Pay via M-Pesa', desc: 'One click sends STK Push. Enter PIN. Done.' },
              { step: '4', title: 'Get Receipt', desc: 'Receipt auto-generated and stored forever' },
            ].map(s => (
              <div key={s.step} className="text-center">
                <div className="w-10 h-10 bg-orange-600 rounded-xl flex items-center justify-center text-white font-bold mx-auto mb-3">{s.step}</div>
                <h4 className="font-semibold text-gray-900 mb-1">{s.title}</h4>
                <p className="text-xs text-gray-500">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── Detail Box Helper ──────────────────────────────────────────────────────

function DetailBox({ bg, label, value, sub }: { bg: string; label: string; value: string; sub: string }) {
  return (
    <div className={`${bg} rounded-xl p-4`}>
      <p className="text-xs text-gray-500 mb-1">{label}</p>
      <p className="font-semibold text-gray-900">{value}</p>
      <p className="text-xs text-gray-500 mt-0.5">{sub}</p>
    </div>
  );
}
