'use client';

import { useState, useEffect, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Spinner } from '@/components/ui/card';
import api from '@/lib/api';
import { useAuthStore } from '@/store/authStore';
import {
  Check, Zap, Shield, Crown, Building2, Star, Users,
  Briefcase, Home, ArrowRight, Phone, Sparkles, AlertCircle
} from 'lucide-react';

interface Plan {
  tier: string;
  price: number;
  features: string[];
  max_listings: number;
  badge: string | null;
}

interface PlansData {
  role: string;
  current_tier: string;
  current_status: string;
  requires_subscription: boolean;
  trial_days: number;
  plans: Plan[];
}

const TIER_ICONS: Record<string, React.ReactNode> = {
  free: <Home className="w-6 h-6" /> as React.ReactNode,
  basic: <Zap className="w-6 h-6" /> as React.ReactNode,
  pro: <Star className="w-6 h-6" /> as React.ReactNode,
  premium: <Crown className="w-6 h-6" /> as React.ReactNode,
};

const TIER_COLORS: Record<string, string> = {
  free: 'border-gray-200 bg-white',
  basic: 'border-emerald-200 bg-white',
  pro: 'border-blue-200 bg-gradient-to-b from-white to-blue-50/30',
  premium: 'border-amber-200 bg-gradient-to-b from-white to-amber-50/30',
};

const TIER_BUTTON: Record<string, string> = {
  free: 'bg-gray-900 hover:bg-gray-800 text-white',
  basic: 'bg-emerald-600 hover:bg-emerald-700 text-white',
  pro: 'bg-blue-600 hover:bg-blue-700 text-white',
  premium: 'bg-amber-500 hover:bg-amber-600 text-white',
};

export default function SubscriptionPage() {
  return (
    <AuthGuard requireAuth>
      <SubscriptionContent />
    </AuthGuard>
  );
}

function SubscriptionContent() {
  const router = useRouter();
  const { user } = useAuthStore();
  const [plansData, setPlansData] = useState<PlansData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [subscribing, setSubscribing] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [checkoutId, setCheckoutId] = useState('');

  const roleLabel = {
    seller: 'Seller',
    agent: 'Agent',
    landlord: 'Landlord',
    buyer: 'Buyer',
    admin: 'Admin',
    super_admin: 'Admin',
  }[user?.role as string] || user?.role || '';

  const loadPlans = async () => {
    try {
      const data = await api.client.get('/api/subscriptions/plans');
      setPlansData(data.data);
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Failed to load plans');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPlans();
  }, []);

  const validatePhone = (phone: string): boolean => {
    return /^254\d{9}$/.test(phone);
  };

  const handleSubscribe = async (tier: string, price: number) => {
    if (!phoneNumber || !validatePhone(phoneNumber)) {
      setError('Please enter a valid M-Pesa phone number (e.g., 254712345678) — must start with 254 and be 12 digits');
      return;
    }

    if (tier === 'free') {
      try {
        setSubscribing(tier);
        await api.client.post(`/api/subscriptions/subscribe?tier=free&phone_number=${encodeURIComponent(phoneNumber)}`);
        setMessage('Free plan activated!');
        setTimeout(() => loadPlans(), 1000);
      } catch (err: any) {
        setError(err?.response?.data?.message || 'Failed to activate');
      } finally {
        setSubscribing(null);
      }
      return;
    }

    try {
      setSubscribing(tier);
      setError('');
      setMessage('');
      const res = await api.client.post(
        `/api/subscriptions/subscribe?tier=${tier}&phone_number=${encodeURIComponent(phoneNumber)}`
      );
      setMessage(`M-Pesa STK Push sent to ${phoneNumber}. Enter your PIN to complete payment.`);
      setCheckoutId(res.data.checkout_request_id || '');
    } catch (err: any) {
      setError(err?.response?.data?.message || 'Payment failed. Try again.');
    } finally {
      setSubscribing(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-32"><Spinner size="lg" /></div>
      </div>
    );
  }

  if (!plansData) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-2xl mx-auto px-4 py-32 text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-600">{error || 'Could not load plans'}</p>
          <Button onClick={loadPlans} variant="outline" className="mt-4">Retry</Button>
        </div>
      </div>
    );
  }

  const isBuyer = user?.role === 'buyer';

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            {isBuyer ? "You're Free Forever! 🎉" : `Choose Your ${roleLabel} Plan`}
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto">
            {isBuyer
              ? 'Vestra is completely free for buyers. Search, verify, and invest with confidence — no subscription needed.'
              : plansData.requires_subscription
                ? `As a ${roleLabel.toLowerCase()}, choose a plan that fits your needs. All plans include a ${plansData.trial_days}-day free trial.`
                : 'Manage your subscription.'}
          </p>
        </div>

        {/* Current Status */}
        {plansData.current_tier !== 'free' && (
          <div className="max-w-md mx-auto mb-10 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-center">
            <p className="text-sm text-emerald-700">
              Current plan: <strong className="capitalize">{plansData.current_tier}</strong>
              {' '}— Status: <strong className="capitalize">{plansData.current_status}</strong>
            </p>
          </div>
        )}

        {/* M-Pesa Phone Input (show for paid plans) */}
        {!isBuyer && (
          <div className="max-w-md mx-auto mb-10">
            <Input
              label="M-Pesa Phone Number"
              value={phoneNumber}
              onChange={(e) => setPhoneNumber(e.target.value)}
              placeholder="254712345678"
              hint="We'll send an STK Push to this number for payment"
              leftElement={<Phone className="w-4 h-4" />}
            />
          </div>
        )}

        {/* Message / Error */}
        {message && (
          <div className="max-w-md mx-auto mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-sm text-emerald-700 flex items-start gap-2">
            <Sparkles className="w-4 h-4 flex-shrink-0 mt-0.5" />
            {message}
          </div>
        )}
        {error && (
          <div className="max-w-md mx-auto mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2">
            <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            {error}
          </div>
        )}

        {/* Plans Grid */}
        {isBuyer ? (
          <div className="max-w-lg mx-auto">
            <Card className="text-center p-8 border-2 border-emerald-200 bg-gradient-to-b from-white to-emerald-50/30">
              <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-4">
                <Sparkles className="w-8 h-8 text-emerald-600" />
              </div>
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Free Forever</h2>
              <p className="text-gray-500 mb-6">All features included for buyers at no cost.</p>
              <ul className="space-y-3 text-left max-w-xs mx-auto mb-8">
                {[
                  'Unlimited property search',
                  'AI-powered natural language search',
                  'Full AI verification reports (KES 500 each)',
                  'Save favorite properties',
                  'WhatsApp search & alerts',
                  'PWA app for iOS & Android',
                ].map((f) => (
                  <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                    <Check className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                    {f}
                  </li>
                ))}
              </ul>
              <Button size="lg" onClick={() => router.push('/market')} className="gap-2">
                Start Browsing Properties <ArrowRight className="w-4 h-4" />
              </Button>
            </Card>
          </div>
        ) : (
          <div className={`grid gap-6 ${plansData.plans.length === 4 ? 'grid-cols-1 md:grid-cols-2 lg:grid-cols-4' : 'grid-cols-1 md:grid-cols-3 max-w-4xl mx-auto'}`}>
            {plansData.plans.map((plan) => {
              const isCurrentPlan = plan.tier === plansData.current_tier;
              const icon = TIER_ICONS[plan.tier] || <Zap className="w-6 h-6" />;

              return (
                <Card
                  key={plan.tier}
                  className={`relative flex flex-col ${TIER_COLORS[plan.tier]} ${
                    plan.tier === 'premium' ? 'ring-2 ring-amber-400 shadow-lg scale-[1.02]' : ''
                  } ${isCurrentPlan ? 'ring-2 ring-emerald-400' : ''}`}
                  padding="none"
                >
                  {isCurrentPlan && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-4 py-1 rounded-full">
                      Current Plan
                    </div>
                  )}
                  {plan.tier === 'premium' && !isCurrentPlan && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-amber-500 text-white text-xs font-bold px-4 py-1 rounded-full">
                      Best Value
                    </div>
                  )}

                  <div className="p-6 flex-1">
                    <div className="flex items-center gap-3 mb-4">
                      <div className={`p-2.5 rounded-xl ${
                        plan.tier === 'premium' ? 'bg-amber-100 text-amber-700' :
                        plan.tier === 'pro' ? 'bg-blue-100 text-blue-700' :
                        plan.tier === 'basic' ? 'bg-emerald-100 text-emerald-700' :
                        'bg-gray-100 text-gray-700'
                      }`}>
                        {icon}
                      </div>
                      <div>
                        <h3 className="font-bold text-lg text-gray-900 capitalize">{plan.tier}</h3>
                        {plan.badge && (
                          <span className="text-xs text-gray-500 capitalize">{plan.badge} badge</span>
                        )}
                      </div>
                    </div>

                    <div className="mb-4">
                      <span className="text-3xl font-bold text-gray-900">
                        KES {plan.price.toLocaleString()}
                      </span>
                      <span className="text-gray-400 text-sm">/month</span>
                    </div>

                    <p className="text-xs text-gray-500 mb-4">
                      Up to {plan.max_listings} active listings
                    </p>

                    <ul className="space-y-2 mb-6">
                      {plan.features.map((f) => (
                        <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                          <Check className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                          {f}
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-6 pt-0">
                    <Button
                      fullWidth
                      size="lg"
                      className={TIER_BUTTON[plan.tier]}
                      onClick={() => handleSubscribe(plan.tier, plan.price)}
                      loading={subscribing === plan.tier}
                      disabled={isCurrentPlan || subscribing !== null}
                    >
                      {isCurrentPlan ? 'Current Plan' :
                       plan.price === 0 ? 'Get Started Free' :
                       `Subscribe — KES ${plan.price.toLocaleString()}`}
                    </Button>
                  </div>
                </Card>
              );
            })}
          </div>
        )}

        {/* Cancel / Manage */}
        {plansData.current_tier !== 'free' && !isBuyer && (
          <div className="text-center mt-10">
            <button
              onClick={async () => {
                try {
                  await api.client.post('/api/subscriptions/cancel');
                  setMessage('Subscription cancelled. Access continues until end of billing period.');
                  setTimeout(() => loadPlans(), 1000);
                } catch (err: any) {
                  setError(err?.response?.data?.message || 'Failed to cancel');
                }
              }}
              className="text-sm text-gray-400 hover:text-red-500 transition-colors"
            >
              Cancel auto-renewal
            </button>
          </div>
        )}

        {/* Guarantee */}
        <div className="text-center mt-16 pb-8">
          <div className="inline-flex items-center gap-2 text-sm text-gray-400">
            <Shield className="w-4 h-4" />
            7-day free trial on all plans. Cancel anytime. No questions asked.
          </div>
        </div>
      </div>
    </div>
  );
}
