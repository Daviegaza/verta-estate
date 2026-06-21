'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import {
  User, ShieldCheck, Building2, Home, Briefcase, ArrowRight,
  Check, Star, Smartphone, Settings, LogOut, Sparkles, ChevronRight
} from 'lucide-react';

export default function AccountPage() {
  return (
    <AuthGuard requireAuth>
      <AccountContent />
    </AuthGuard>
  );
}

function AccountContent() {
  const router = useRouter();
  const { user, logout } = useAuthStore();
  const [upgradingTo, setUpgradingTo] = useState<string | null>(null);
  const [message, setMessage] = useState('');

  const isBuyer = user?.role === 'buyer';

  const handleUpgrade = async (role: string) => {
    setUpgradingTo(role);
    setMessage('');
    try {
      const res = await api.client.post(`/api/auth/upgrade-role?role=${role}`);
      // Update user in store
      useAuthStore.setState({ user: res.data.user });
      setMessage(`You're now a ${role}! Your dashboard is ready.`);
    } catch (err: any) {
      setMessage(err?.response?.data?.detail || 'Something went wrong');
    } finally {
      setUpgradingTo(null);
    }
  };

  const roleLabels: Record<string, { icon: React.ReactNode; title: string; desc: string; benefits: string[] }> = {
    seller: {
      icon: <Home className="w-8 h-8" />,
      title: 'Become a Seller',
      desc: 'List properties for sale or rent. Get AI trust scores, reach thousands of buyers.',
      benefits: ['List properties for sale or rent', 'AI trust score on every listing', 'Buyer inquiries via WhatsApp & chat', 'First 3 listings free'],
    },
    agent: {
      icon: <Briefcase className="w-8 h-8" />,
      title: 'Become an Agent',
      desc: 'Build your reputation. Get verified, earn badges, manage clients, close more deals.',
      benefits: ['Vestra Verified Agent badge', 'Agent profile page with reviews', 'Client management tools', 'Priority in agent directory', 'Lead generation tools'],
    },
    landlord: {
      icon: <Building2 className="w-8 h-8" />,
      title: 'Become a Landlord',
      desc: 'Manage your rental units. Collect rent via M-Pesa, screen tenants, track maintenance.',
      benefits: ['Rental unit management', 'M-Pesa rent collection', 'Tenant screening reports', 'Maintenance request tracking', 'First 2 units free'],
    },
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-2xl mx-auto px-4 py-12">
        {/* Header */}
        <div className="flex items-center gap-4 mb-10">
          <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <User className="w-8 h-8 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{user?.full_name || 'My Account'}</h1>
            <p className="text-sm text-gray-500 flex items-center gap-1.5 mt-1">
              <Smartphone className="w-3.5 h-3.5" />
              {user?.phone || user?.email}
            </p>
            <span className="inline-block mt-1.5 text-xs bg-emerald-50 text-emerald-700 px-2.5 py-0.5 rounded-full capitalize font-medium">
              {user?.role?.replace('_', ' ')}
            </span>
          </div>
        </div>

        {message && (
          <div className={`mb-6 p-4 rounded-2xl text-sm font-medium ${
            message.includes('now') ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {message}
          </div>
        )}

        {/* Roles — always show, highlight current */}
        <div className="mb-8">
          <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-emerald-600" />
            What would you like to do?
          </h2>

          <div className="space-y-3">
            {Object.entries(roleLabels).map(([role, info]) => {
              const isCurrent = user?.role === role;
              const isUpgrading = upgradingTo === role;

              return (
                <Card
                  key={role}
                  className={`relative overflow-hidden transition-all ${
                    isCurrent
                      ? 'ring-2 ring-emerald-400 bg-emerald-50/50'
                      : 'hover:shadow-md'
                  }`}
                >
                  {isCurrent && (
                    <div className="absolute top-3 right-3 bg-emerald-600 text-white text-xs font-bold px-3 py-1 rounded-full flex items-center gap-1">
                      <Check className="w-3 h-3" />
                      Current
                    </div>
                  )}

                  <div className="flex items-start gap-4">
                    <div className={`p-3 rounded-xl flex-shrink-0 ${
                      isCurrent ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-600'
                    }`}>
                      {info.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h3 className="font-bold text-gray-900 text-lg">{info.title}</h3>
                      <p className="text-sm text-gray-500 mt-1">{info.desc}</p>
                      <ul className="mt-3 space-y-1.5">
                        {info.benefits.map(b => (
                          <li key={b} className="flex items-start gap-2 text-xs text-gray-600">
                            <Check className="w-3.5 h-3.5 text-emerald-500 flex-shrink-0 mt-0.5" />
                            {b}
                          </li>
                        ))}
                      </ul>
                    </div>
                  </div>

                  {!isCurrent && (
                    <div className="mt-4 pt-4 border-t border-gray-100 flex justify-end">
                      <Button
                        size="sm"
                        onClick={() => handleUpgrade(role)}
                        loading={isUpgrading}
                        className="gap-1.5"
                      >
                        {role === 'seller' && 'Start Selling'}
                        {role === 'agent' && 'Become an Agent'}
                        {role === 'landlord' && 'Manage Rentals'}
                        <ChevronRight className="w-4 h-4" />
                      </Button>
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        </div>

        {/* Bottom actions */}
        <div className="space-y-2 pt-4 border-t border-gray-100">
          {!isBuyer && (
            <Link href="/dashboard" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-gray-100 transition-colors">
              <Star className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-700">Go to Dashboard</span>
              <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
            </Link>
          )}
          <Link href="/messages" className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-gray-100 transition-colors">
            <Star className="w-5 h-5 text-gray-400" />
            <span className="text-sm text-gray-700">Messages</span>
            <ChevronRight className="w-4 h-4 text-gray-400 ml-auto" />
          </Link>
          <button
            onClick={() => { logout(); router.push('/'); }}
            className="flex items-center gap-3 px-4 py-3 rounded-xl hover:bg-red-50 transition-colors w-full text-left"
          >
            <LogOut className="w-5 h-5 text-red-400" />
            <span className="text-sm text-red-600">Sign Out</span>
          </button>
        </div>
      </div>
    </div>
  );
}
