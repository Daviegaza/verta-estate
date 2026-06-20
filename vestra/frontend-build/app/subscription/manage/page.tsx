'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import type { Payment } from '@/types';
import {
  CreditCard, CheckCircle, AlertCircle, Clock, ArrowLeft,
  Crown, Zap, Home, Star, Shield, XCircle
} from 'lucide-react';

interface SubscriptionData {
  subscription: {
    id: number;
    tier: string;
    status: string;
    price: number;
    currency: string;
    current_period_start: string;
    current_period_end: string;
    features: string[];
    auto_renew: boolean;
    trial_end?: string;
    cancelled_at?: string;
  } | null;
  listing_limit: number;
  listings_this_month?: number;
  role: string;
}

const TIER_BADGE: Record<string, 'default' | 'info' | 'success' | 'purple'> = {
  free: 'default',
  basic: 'info',
  pro: 'success',
  premium: 'purple',
};

const TIER_ICONS: Record<string, React.ReactNode> = {
  free: <Home className="w-5 h-5" />,
  basic: <Zap className="w-5 h-5" />,
  pro: <Star className="w-5 h-5" />,
  premium: <Crown className="w-5 h-5" />,
};

const TIER_ICON_BG: Record<string, string> = {
  free: 'bg-gray-100 text-gray-600',
  basic: 'bg-blue-100 text-blue-700',
  pro: 'bg-emerald-100 text-emerald-700',
  premium: 'bg-amber-100 text-amber-700',
};

const STATUS_ICONS: Record<string, React.ReactNode> = {
  active: <CheckCircle className="w-5 h-5 text-emerald-500" />,
  trialing: <Clock className="w-5 h-5 text-blue-500" />,
  past_due: <AlertCircle className="w-5 h-5 text-amber-500" />,
  cancelled: <XCircle className="w-5 h-5 text-gray-400" />,
  expired: <XCircle className="w-5 h-5 text-red-400" />,
};

const STATUS_BADGE: Record<string, 'success' | 'info' | 'warning' | 'default' | 'danger'> = {
  active: 'success',
  trialing: 'info',
  past_due: 'warning',
  cancelled: 'default',
  expired: 'danger',
};

function formatKES(amount: number): string {
  return `KES ${amount.toLocaleString('en-KE')}`;
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-KE', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

function getPurposeLabel(purpose: string): string {
  return purpose
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export default function ManageSubscriptionPage() {
  return (
    <AuthGuard requireAuth>
      <ManageSubscriptionContent />
    </AuthGuard>
  );
}

function ManageSubscriptionContent() {
  const router = useRouter();
  const [subData, setSubData] = useState<SubscriptionData | null>(null);
  const [billingHistory, setBillingHistory] = useState<Payment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState('');
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [fetchingBilling, setFetchingBilling] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setError('');
      const [sub, payments] = await Promise.all([
        api.getMySubscription(),
        api.getMyPayments(),
      ]);
      setSubData(sub);

      const billing = (payments || [])
        .filter((p) => p.purpose === 'subscription')
        .slice(0, 5);
      setBillingHistory(billing);
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to load subscription details');
    } finally {
      setLoading(false);
      setFetchingBilling(false);
    }
  };

  const handleCancelSubscription = async () => {
    try {
      setActionLoading(true);
      setActionMessage('');
      await api.cancelSubscription();
      setActionMessage('Subscription cancelled. Access continues until the end of your billing period.');
      setShowCancelModal(false);
      setTimeout(() => loadData(), 1500);
    } catch (err: any) {
      setActionMessage(err?.response?.data?.message || 'Failed to cancel subscription');
    } finally {
      setActionLoading(false);
    }
  };

  const isCancelled = subData?.subscription?.status === 'cancelled' || subData?.subscription?.status === 'expired';

  // Loading state
  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-32"><Spinner size="lg" /></div>
      </div>
    );
  }

  // Error state with no data
  if (error && !subData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-2xl mx-auto px-4 py-32 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600 text-sm mb-4">{error}</p>
          <Button onClick={loadData} variant="outline">Retry</Button>
        </div>
      </div>
    );
  }

  const subscription = subData?.subscription;
  const listingLimit = subData?.listing_limit ?? 0;
  const listingsUsed = subData?.listings_this_month ?? 0;
  const listingPct = listingLimit > 0 ? Math.round((listingsUsed / listingLimit) * 100) : 0;

  // No subscription state
  if (!subscription) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-2xl mx-auto px-4 sm:px-6 py-12">
          <Link href="/subscription" className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-emerald-600 transition-colors mb-6">
            <ArrowLeft className="w-4 h-4" />
            Back to Plans
          </Link>

          <Card className="text-center py-24 border-2 border-dashed border-gray-200 bg-white/50">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <CreditCard className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No active subscription</h3>
            <p className="text-gray-400 text-sm mb-6 max-w-sm mx-auto">
              Choose a plan that fits your needs and unlock premium features.
            </p>
            <Link href="/subscription">
              <Button size="lg">View Plans</Button>
            </Link>
          </Card>
        </div>
      </div>
    );
  }

  const tier = subscription.tier;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        {/* Back link */}
        <Link
          href="/subscription"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-emerald-600 transition-colors mb-6"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Plans
        </Link>

        {/* Action message */}
        {actionMessage && (
          <div className={`mb-6 p-4 border rounded-2xl text-sm flex items-start gap-2 ${
            actionMessage.includes('Failed') || actionMessage.includes('failed')
              ? 'bg-red-50 border-red-200 text-red-700'
              : 'bg-emerald-50 border-emerald-200 text-emerald-700'
          }`}>
            {actionMessage.includes('Failed') || actionMessage.includes('failed')
              ? <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
              : <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            }
            {actionMessage}
          </div>
        )}

        {/* Error banner (when data exists but there's an error) */}
        {error && subData && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        <div className="grid lg:grid-cols-3 gap-6">
          {/* Main — Current Plan */}
          <div className="lg:col-span-2 space-y-6">
            {/* Current Plan Card */}
            <Card padding="lg">
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-bold text-gray-900">Current Plan</h2>
                <Badge variant={TIER_BADGE[tier] || 'default'} className="capitalize">
                  {tier}
                </Badge>
              </div>

              <div className="flex items-start gap-4 mb-6">
                <div className={`p-3 rounded-2xl ${TIER_ICON_BG[tier] || 'bg-gray-100 text-gray-600'}`}>
                  {TIER_ICONS[tier] || <Shield className="w-5 h-5" />}
                </div>
                <div>
                  <h3 className="text-xl font-bold text-gray-900 capitalize">{tier} Plan</h3>
                  <p className="text-2xl font-bold text-gray-900 mt-1">
                    {formatKES(subscription.price)}
                    <span className="text-sm font-normal text-gray-400">/month</span>
                  </p>
                </div>
              </div>

              {/* Status & Dates */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-1">Status</p>
                  <div className="flex items-center gap-2">
                    {STATUS_ICONS[subscription.status] || <AlertCircle className="w-5 h-5 text-gray-400" />}
                    <span className="font-semibold text-gray-900 capitalize">{subscription.status}</span>
                    <Badge variant={STATUS_BADGE[subscription.status] || 'default'} className="capitalize">
                      {subscription.status}
                    </Badge>
                  </div>
                </div>
                <div className="p-4 bg-gray-50 rounded-xl">
                  <p className="text-xs text-gray-500 font-medium uppercase tracking-wider mb-1">Renewal Date</p>
                  <p className="font-semibold text-gray-900">
                    {formatDate(subscription.current_period_end)}
                  </p>
                  <p className="text-xs text-gray-400 mt-0.5">
                    Auto-renew: {subscription.auto_renew ? 'On' : 'Off'}
                  </p>
                </div>
              </div>

              {/* Features */}
              <div className="mb-6">
                <h4 className="text-sm font-semibold text-gray-700 mb-3">Plan Features</h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {(subscription.features || []).length > 0 ? (
                    subscription.features.map((feature, idx) => (
                      <div key={idx} className="flex items-start gap-2 text-sm text-gray-600">
                        <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        {feature}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-400 col-span-2">No features listed</p>
                  )}
                </div>
              </div>

              {/* Listing limit usage */}
              <div className="p-5 bg-gradient-to-b from-white to-emerald-50/30 border border-emerald-100 rounded-2xl">
                <div className="flex items-center justify-between mb-2">
                  <p className="text-sm font-semibold text-gray-700">Listing Usage</p>
                  <p className="text-sm text-gray-500">
                    <span className="font-bold text-gray-900">{listingsUsed}</span>
                    {' '}of{' '}
                    <span className="font-bold text-gray-900">{listingLimit}</span>
                    {' '}listings used this month
                  </p>
                </div>
                <div className="w-full h-2.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${
                      listingPct >= 80 ? 'bg-red-500' : listingPct >= 60 ? 'bg-amber-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, listingPct)}%` }}
                  />
                </div>
                {listingPct >= 80 && (
                  <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
                    <AlertCircle className="w-3.5 h-3.5" />
                    You are nearing your listing limit. Upgrade to increase your limit.
                  </p>
                )}
              </div>
            </Card>

            {/* Billing History */}
            <Card padding="lg">
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <CreditCard className="w-5 h-5 text-gray-400" />
                Billing History
              </h3>

              {fetchingBilling ? (
                <div className="flex justify-center py-8"><Spinner size="md" /></div>
              ) : billingHistory.length === 0 ? (
                <div className="text-center py-8 bg-gray-50 rounded-xl">
                  <CreditCard className="w-8 h-8 text-gray-300 mx-auto mb-2" />
                  <p className="text-sm text-gray-400">No subscription payments yet</p>
                </div>
              ) : (
                <div className="divide-y divide-gray-50">
                  {billingHistory.map((payment) => (
                    <div key={payment.id} className="flex items-center justify-between py-3 first:pt-0 last:pb-0">
                      <div className="min-w-0">
                        <p className="text-sm font-semibold text-gray-800">
                          {getPurposeLabel(payment.purpose)}
                        </p>
                        <p className="text-xs text-gray-400">{formatDate(payment.created_at)}</p>
                      </div>
                      <div className="text-right flex-shrink-0 ml-3">
                        <p className="text-sm font-bold text-gray-900">
                          {formatKES(payment.amount)}
                        </p>
                        <Badge variant={
                          payment.status === 'completed' ? 'success' :
                          payment.status === 'failed' ? 'danger' :
                          payment.status === 'refunded' ? 'default' :
                          'warning'
                        }>
                          {payment.status}
                        </Badge>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* Sidebar — Actions */}
          <div className="space-y-5">
            <Card padding="lg">
              <h3 className="font-bold text-gray-900 mb-4 flex items-center gap-2">
                <Shield className="w-4 h-4 text-emerald-600" />
                Manage Plan
              </h3>
              <div className="space-y-3">
                <Link href="/subscription">
                  <Button fullWidth variant="primary" size="md" leftIcon={<Zap className="w-3.5 h-3.5" />}>
                    Change Plan
                  </Button>
                </Link>

                {isCancelled ? (
                  <Link href="/subscription">
                    <Button fullWidth variant="outline" size="md" leftIcon={<Star className="w-3.5 h-3.5" />}>
                      Reactivate Subscription
                    </Button>
                  </Link>
                ) : (
                  <Button
                    fullWidth
                    variant="danger"
                    size="md"
                    onClick={() => setShowCancelModal(true)}
                    disabled={actionLoading}
                  >
                    Cancel Subscription
                  </Button>
                )}
              </div>
            </Card>

            {/* Plan Info */}
            <Card padding="lg">
              <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
                <Clock className="w-4 h-4 text-gray-400" />
                Plan Details
              </h3>
              <div className="space-y-3 text-sm">
                <div className="flex justify-between">
                  <span className="text-gray-500">Plan</span>
                  <span className="font-semibold text-gray-900 capitalize">{tier}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Price</span>
                  <span className="font-semibold text-gray-900">{formatKES(subscription.price)}/mo</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Auto-renew</span>
                  <span className={`font-semibold ${subscription.auto_renew ? 'text-emerald-600' : 'text-gray-400'}`}>
                    {subscription.auto_renew ? 'On' : 'Off'}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Listing Limit</span>
                  <span className="font-semibold text-gray-900">{listingLimit}/month</span>
                </div>
              </div>
            </Card>
          </div>
        </div>
      </div>

      {/* Cancel Confirmation Modal */}
      {showCancelModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 animate-in fade-in zoom-in duration-200">
            <div className="w-14 h-14 bg-red-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
              <AlertCircle className="w-7 h-7 text-red-600" />
            </div>
            <h3 className="text-xl font-bold text-gray-900 text-center mb-2">Cancel Subscription?</h3>
            <p className="text-sm text-gray-500 text-center mb-6">
              Your access will continue until the end of the current billing period ({formatDate(subscription.current_period_end)}). After that, your account will be downgraded to the Free plan.
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                fullWidth
                onClick={() => setShowCancelModal(false)}
                disabled={actionLoading}
              >
                Keep Plan
              </Button>
              <Button
                variant="danger"
                fullWidth
                onClick={handleCancelSubscription}
                loading={actionLoading}
              >
                Confirm Cancel
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
