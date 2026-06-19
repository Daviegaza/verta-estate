'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ShieldCheck, Eye, EyeOff, ArrowLeft } from 'lucide-react';

type Role = 'buyer' | 'seller' | 'agent' | 'landlord';

const ROLES: { value: Role; label: string; desc: string }[] = [
  { value: 'buyer', label: 'Buyer', desc: 'Looking to buy or rent property' },
  { value: 'seller', label: 'Seller', desc: 'Want to list and sell property' },
  { value: 'agent', label: 'Agent', desc: 'Real estate agent or broker' },
  { value: 'landlord', label: 'Landlord', desc: 'Own and manage rental property' },
];

export default function RegisterPage() {
  const router = useRouter();
  const { register, isLoading } = useAuthStore();
  const [showPass, setShowPass] = useState(false);
  const [error, setError] = useState('');
  const [form, setForm] = useState({
    full_name: '',
    email: '',
    phone: '',
    password: '',
    role: 'buyer' as Role,
  });

  const set = (key: string, value: string) => setForm((f) => ({ ...f, [key]: value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    if (form.password.length < 8) {
      setError('Password must be at least 8 characters');
      return;
    }
    try {
      const phone = form.phone ? (form.phone.startsWith('+') ? form.phone : '+254' + form.phone.replace(/^0/, '')) : undefined;
      await register({ ...form, phone });
      // Flag as new user so the onboarding wizard appears after redirect
      localStorage.setItem('vestra_show_onboarding', 'true');
      const params = new URLSearchParams(window.location.search);
      const redirect = params.get('redirect');
      router.push(redirect || '/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Registration failed. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Form */}
      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-8 lg:px-12">
        <div className="max-w-md w-full mx-auto">
          <Link href="/" className="inline-flex items-center gap-2 mb-8 group">
            <ArrowLeft className="w-4 h-4 text-gray-400 group-hover:text-gray-600" />
            <div className="w-8 h-8 bg-emerald-600 rounded-xl flex items-center justify-center ml-1">
              <span className="text-white font-bold text-sm">V</span>
            </div>
            <span className="font-bold text-xl text-gray-900">Vestra</span>
          </Link>

          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900">Create your account</h1>
            <p className="text-gray-500 mt-2">Join thousands of Kenyans trusting property with AI</p>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* Role selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">I am a...</label>
              <div className="grid grid-cols-2 gap-2">
                {ROLES.map((r) => (
                  <button
                    key={r.value}
                    type="button"
                    onClick={() => set('role', r.value)}
                    className={`text-left p-3 rounded-xl border-2 transition-all ${
                      form.role === r.value
                        ? 'border-emerald-500 bg-emerald-50'
                        : 'border-gray-200 hover:border-gray-300 bg-white'
                    }`}
                  >
                    <p className={`text-sm font-semibold ${form.role === r.value ? 'text-emerald-700' : 'text-gray-800'}`}>
                      {r.label}
                    </p>
                    <p className="text-xs text-gray-400 mt-0.5">{r.desc}</p>
                  </button>
                ))}
              </div>
            </div>

            <Input
              label="Full Name"
              value={form.full_name}
              onChange={(e) => set('full_name', e.target.value)}
              placeholder="John Kamau"
              required
            />
            <Input
              label="Email Address"
              type="email"
              value={form.email}
              onChange={(e) => set('email', e.target.value)}
              placeholder="john@example.com"
              required
            />
            <Input
              label="Phone Number (optional)"
              type="tel"
              value={form.phone}
              onChange={(e) => set('phone', e.target.value)}
              placeholder="0712 345 678"
              hint="Used for M-Pesa payments"
            />
            <Input
              label="Password"
              type={showPass ? 'text' : 'password'}
              value={form.password}
              onChange={(e) => set('password', e.target.value)}
              placeholder="Min 8 characters"
              required
              hint="At least 8 characters"
              rightElement={
                <button type="button" onClick={() => setShowPass(!showPass)} className="hover:text-gray-600">
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              }
            />

            <div className="flex items-start gap-2">
              <input type="checkbox" required className="mt-1 rounded border-gray-300 text-emerald-600" />
              <p className="text-xs text-gray-500">
                I agree to Vestra's{' '}
                <Link href="#" className="text-emerald-600 hover:underline">Terms of Service</Link>
                {' '}and{' '}
                <Link href="#" className="text-emerald-600 hover:underline">Privacy Policy</Link>
              </p>
            </div>

            <Button type="submit" fullWidth size="lg" loading={isLoading}>
              Create Account
            </Button>
          </form>

          <p className="mt-6 text-center text-sm text-gray-500">
            Already have an account?{' '}
            <Link href="/auth/login" className="text-emerald-600 hover:text-emerald-700 font-semibold">
              Sign in
            </Link>
          </p>
        </div>
      </div>

      {/* Branding */}
      <div className="hidden lg:flex flex-1 bg-gradient-to-br from-gray-900 to-emerald-900 text-white flex-col justify-center px-16">
        <div className="max-w-md">
          <ShieldCheck className="w-16 h-16 text-emerald-400 mb-8" />
          <h2 className="text-4xl font-bold mb-4">Join Africa's Property Revolution</h2>
          <p className="text-gray-300 text-lg leading-relaxed mb-8">
            Get AI-powered trust scores, verify any property instantly, and transact safely.
          </p>
          <div className="space-y-4">
            {['Free account forever', 'No hidden fees', 'M-Pesa native payments', 'AI-powered fraud protection'].map((item) => (
              <div key={item} className="flex items-center gap-3">
                <div className="w-5 h-5 bg-emerald-500 rounded-full flex items-center justify-center flex-shrink-0">
                  <span className="text-white text-xs">✓</span>
                </div>
                <span className="text-gray-200 text-sm">{item}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
