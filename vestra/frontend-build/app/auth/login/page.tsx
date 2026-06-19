'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { Smartphone, ArrowLeft, ArrowRight, Check, ShieldCheck, Sparkles, Mail, Key, Eye, EyeOff, Copy, User } from 'lucide-react';

type Tab = 'phone' | 'email';
type Step = 'phone' | 'otp' | 'name' | 'email-form';

export default function LoginPage() {
  const router = useRouter();
  const { login, isLoading } = useAuthStore();
  const [tab, setTab] = useState<Tab>('phone');

  // ── Phone OTP state ──
  const [step, setStep] = useState<Step>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [fullName, setFullName] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [countdown, setCountdown] = useState(0);

  // ── Email state ──
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPass, setShowPass] = useState(false);

  // ── Demo accounts ──
  const [showDemo, setShowDemo] = useState(false);
  const [copied, setCopied] = useState('');

  const DEMO_ACCOUNTS = [
    { role: 'Admin', email: 'admin@vestra.co.ke', password: 'demo1234', color: 'bg-red-50 border-red-200 text-red-800' },
    { role: 'Agent', email: 'jane.muthoni@email.com', password: 'demo1234', color: 'bg-purple-50 border-purple-200 text-purple-800' },
    { role: 'Buyer', email: 'samuel.njoroge@email.com', password: 'demo1234', color: 'bg-blue-50 border-blue-200 text-blue-800' },
    { role: 'Seller', email: 'peter.omondi@email.com', password: 'demo1234', color: 'bg-amber-50 border-amber-200 text-amber-800' },
  ];

  useEffect(() => {
    if (countdown > 0) {
      const timer = setTimeout(() => setCountdown(c => c - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [countdown]);

  const normalizePhone = (input: string) => {
    let cleaned = input.replace(/[^0-9+]/g, '');
    if (cleaned.startsWith('+')) cleaned = cleaned.slice(1);
    if (cleaned.startsWith('0')) cleaned = '254' + cleaned.slice(1);
    if (cleaned.startsWith('7') && cleaned.length <= 9) cleaned = '254' + cleaned;
    return cleaned.slice(0, 12);
  };

  // ── Phone OTP handlers ──
  const handlePhoneSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (phone.length < 10) { setError('Enter a valid phone number'); return; }
    setLoading(true); setError('');
    try {
      await api.client.post('/api/auth/send-otp', { phone });
      setStep('otp'); setCountdown(60);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to send code. Try again.');
    } finally { setLoading(false); }
  };

  const handleOTPSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (code.length < 4) { setError('Enter the verification code'); return; }
    setLoading(true); setError('');
    try {
      const res = await api.client.post('/api/auth/verify-otp', { phone, code, full_name: fullName || undefined });
      localStorage.setItem('vestra_token', res.data.access_token);
      useAuthStore.setState({ user: res.data.user, token: res.data.access_token, isAuthenticated: true });
      const params = new URLSearchParams(window.location.search);
      if (res.data.is_new) {
        // Flag as new user so the onboarding wizard appears after redirect
        localStorage.setItem('vestra_show_onboarding', 'true');
        setStep('name');
      } else {
        router.push(params.get('redirect') || '/market');
      }
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid code. Try again.');
    } finally { setLoading(false); }
  };

  const handleNameSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const params = new URLSearchParams(window.location.search);
    router.push(params.get('redirect') || '/market');
  };

  // ── Email handlers ──
  const handleEmailLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    try {
      await login(email, password);
      const params = new URLSearchParams(window.location.search);
      router.push(params.get('redirect') || '/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid email or password');
    }
  };

  const fillDemo = (acc: typeof DEMO_ACCOUNTS[0]) => {
    setEmail(acc.email);
    setPassword(acc.password);
    setCopied(acc.role);
    setTimeout(() => setCopied(''), 1500);
  };

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Left — Form */}
      <div className="flex-1 flex flex-col justify-center py-12 px-4 sm:px-8 lg:px-12">
        <div className="max-w-md w-full mx-auto">
          <Link href="/" className="inline-flex items-center gap-2 mb-6 group">
            <ArrowLeft className="w-4 h-4 text-gray-400 group-hover:text-gray-600 transition-colors" />
            <div className="w-8 h-8 bg-emerald-600 rounded-xl flex items-center justify-center ml-1">
              <span className="text-white font-bold text-sm">V</span>
            </div>
            <span className="font-bold text-xl text-gray-900">Vestra</span>
          </Link>

          <h1 className="text-3xl font-bold text-gray-900 mb-1">Sign in</h1>
          <p className="text-gray-500 mb-8">Choose how you want to sign in</p>

          {/* ── Tabs ── */}
          <div className="flex bg-gray-100 rounded-2xl p-1 mb-6">
            <button
              onClick={() => { setTab('phone'); setError(''); setStep('phone'); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                tab === 'phone' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Smartphone className="w-4 h-4" />
              Phone
            </button>
            <button
              onClick={() => { setTab('email'); setError(''); }}
              className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                tab === 'email' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Mail className="w-4 h-4" />
              Email
            </button>
          </div>

          {error && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700 flex items-start gap-2">
              <span className="flex-shrink-0 mt-0.5">⚠</span>
              {error}
            </div>
          )}

          {/* ═══════════ PHONE TAB ═══════════ */}
          {tab === 'phone' && (
            <>
              {step === 'phone' && (
                <form onSubmit={handlePhoneSubmit} className="space-y-5">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1.5 block">Phone Number</label>
                    <div className="relative">
                      <Smartphone className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                      <input
                        type="tel"
                        value={phone}
                        onChange={(e) => { setPhone(normalizePhone(e.target.value)); setError(''); }}
                        placeholder="712 345 678"
                        className="w-full pl-12 pr-4 py-3.5 border border-gray-200 rounded-2xl text-base focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                        autoFocus
                      />
                    </div>
                    {phone && <p className="text-xs text-gray-400 mt-1.5">+{phone}</p>}
                  </div>
                  <Button type="submit" fullWidth size="lg" loading={loading}>
                    Send Code via WhatsApp <ArrowRight className="w-4 h-4" />
                  </Button>
                  <p className="text-center text-xs text-gray-400">No password needed — just your phone</p>
                </form>
              )}

              {step === 'otp' && (
                <form onSubmit={handleOTPSubmit} className="space-y-5">
                  <div>
                    <label className="text-sm font-medium text-gray-700 mb-1.5 block">Verification Code</label>
                    <input
                      type="text" inputMode="numeric" maxLength={6}
                      value={code}
                      onChange={(e) => { setCode(e.target.value.replace(/\D/g, '')); setError(''); }}
                      placeholder="000000"
                      className="w-full px-4 py-3.5 border border-gray-200 rounded-2xl text-2xl tracking-[0.5em] text-center font-bold focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 transition-all"
                      autoFocus
                    />
                    <p className="text-xs text-gray-400 mt-2 text-center">Sent to +{phone}</p>
                  </div>
                  <Button type="submit" fullWidth size="lg" loading={loading}>
                    Verify & Sign In <Check className="w-4 h-4" />
                  </Button>
                  <div className="text-center space-y-2">
                    <button type="button" onClick={() => { setStep('phone'); setError(''); }} className="text-sm text-gray-500 hover:text-gray-700">← Change number</button>
                    {countdown > 0 ? (
                      <p className="text-xs text-gray-400">Resend in {countdown}s</p>
                    ) : (
                      <button onClick={handlePhoneSubmit} className="text-xs text-emerald-600 hover:text-emerald-700 block mx-auto">Resend code</button>
                    )}
                  </div>
                </form>
              )}

              {step === 'name' && (
                <form onSubmit={handleNameSubmit} className="space-y-5">
                  <Input label="Your Name" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="e.g. Mary Wanjiku" autoFocus />
                  <Button type="submit" fullWidth size="lg">Start Browsing <Sparkles className="w-4 h-4" /></Button>
                  <button onClick={() => router.push('/market')} className="text-sm text-gray-500 hover:text-gray-700 block text-center w-full">Skip for now</button>
                </form>
              )}

              {step !== 'name' && (
                <div className="mt-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl flex items-start gap-3">
                  <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                  <p className="text-xs text-emerald-800">Fast login — no password needed. We'll send you a code via WhatsApp.</p>
                </div>
              )}
            </>
          )}

          {/* ═══════════ EMAIL TAB ═══════════ */}
          {tab === 'email' && (
            <form onSubmit={handleEmailLogin} className="space-y-5">
              <Input
                label="Email address"
                type="email"
                value={email}
                onChange={(e) => { setEmail(e.target.value); setError(''); }}
                placeholder="you@example.com"
                leftElement={<Mail className="w-4 h-4" />}
                autoFocus
              />
              <Input
                label="Password"
                type={showPass ? 'text' : 'password'}
                value={password}
                onChange={(e) => { setPassword(e.target.value); setError(''); }}
                placeholder="Enter your password"
                leftElement={<Key className="w-4 h-4" />}
                rightElement={
                  <button type="button" onClick={() => setShowPass(!showPass)} className="text-gray-400 hover:text-gray-600">
                    {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                }
              />
              <Button type="submit" fullWidth size="lg" loading={isLoading}>
                Sign In <ArrowRight className="w-4 h-4" />
              </Button>
              <p className="text-center text-xs text-gray-400">
                Secure login with your registered email and password
              </p>
            </form>
          )}
        </div>

        {/* ── Demo Credentials ── */}
        <div className="max-w-md w-full mx-auto mt-8">
          <button
            onClick={() => setShowDemo(!showDemo)}
            className="flex items-center gap-2 text-sm text-gray-400 hover:text-gray-600 transition-colors mx-auto"
          >
            <User className="w-4 h-4" />
            {showDemo ? 'Hide demo accounts' : 'Need a demo account?'}
          </button>

          {showDemo && (
            <div className="mt-3 space-y-2 animate-fade-in">
              <p className="text-xs text-gray-400 mb-2">Click any account to auto-fill. All passwords are <code className="bg-gray-100 px-1.5 py-0.5 rounded text-emerald-700 font-bold">demo1234</code></p>
              {DEMO_ACCOUNTS.map(acc => (
                <button
                  key={acc.role}
                  onClick={() => fillDemo(acc)}
                  className={`w-full text-left p-3 rounded-xl border text-sm flex items-center justify-between transition-all hover:shadow-sm ${acc.color}`}
                >
                  <div>
                    <span className="font-bold">{acc.role}</span>
                    <span className="ml-2 opacity-70">{acc.email}</span>
                  </div>
                  <span className="text-xs font-semibold flex items-center gap-1">
                    {copied === acc.role ? (
                      <><Check className="w-3 h-3" /> Filled</>
                    ) : (
                      <><Copy className="w-3 h-3" /> Use this</>
                    )}
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right — Brand panel */}
      <div className="hidden lg:flex flex-1 bg-gradient-to-br from-emerald-600 to-emerald-900 items-center justify-center p-12 relative overflow-hidden">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wNSI+PHBhdGggZD0iTTM2IDM2YzEuNjU3IDAgMy0xLjM0MyAzLTNzLTEuMzQzLTMtMy0zLTMgMS4zNDMtMyAzIDEuMzQzIDMgMyAzem0tMjQgMGMxLjY1NyAwIDMtMS4zNDMgMy0zcy0xLjM0My0zLTMtMy0zIDEuMzQzLTMgMyAxLjM0MyAzIDMgM3oiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-50" />
        <div className="relative z-10 text-center max-w-md">
          <div className="w-20 h-20 bg-white/20 backdrop-blur rounded-3xl flex items-center justify-center mx-auto mb-8">
            <ShieldCheck className="w-10 h-10 text-white" />
          </div>
          <h2 className="text-3xl font-bold text-white mb-4">Trust Every Property</h2>
          <p className="text-emerald-100 text-lg leading-relaxed">
            Browse verified properties across Kenya. Every listing has a Trust Score so you know exactly what you're getting.
          </p>
          <div className="mt-10 grid grid-cols-3 gap-4 text-center">
            {[
              { value: '50K+', label: 'Properties' },
              { value: '98%', label: 'Verified' },
              { value: '0', label: 'Hidden Fees' },
            ].map(stat => (
              <div key={stat.label}>
                <p className="text-2xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-emerald-200 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
