'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Shield, Eye, EyeOff, ArrowRight, AlertTriangle } from 'lucide-react';

export default function AdminLoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState('admin@vestra.co.ke');
  const [password, setPassword] = useState('demo1234');
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      // Call backend login directly (bypass store to get role immediately)
      const data = await api.login(email, password);

      // Check admin role BEFORE anything else
      if (data.user.role !== 'admin' && data.user.role !== 'super_admin') {
        setError('Access denied. Admin credentials required.');
        setLoading(false);
        return;
      }

      // Store token and user IMMEDIATELY
      localStorage.setItem('vestra_token', data.access_token);
      useAuthStore.setState({
        user: data.user,
        token: data.access_token,
        isAuthenticated: true,
      });

      // Navigate instantly — no delay needed
      router.replace('/admin');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Invalid credentials');
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <div className="w-16 h-16 bg-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-emerald-900/30">
            <Shield className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-2xl font-bold text-white">Vestra Admin</h1>
          <p className="text-gray-400 text-sm mt-1">Secure control panel</p>
        </div>

        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 shadow-2xl">
          {error && (
            <div className="mb-5 p-4 bg-red-900/30 border border-red-800 rounded-xl flex items-start gap-3 text-sm text-red-300">
              <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="text-sm font-medium text-gray-300 mb-1.5 block">Admin Email</label>
              <input type="email" value={email} onChange={e => setEmail(e.target.value)}
                className="w-full px-4 py-3 bg-gray-800 border border-gray-700 rounded-xl text-white placeholder:text-gray-500 focus:outline-none focus:ring-2 focus:ring-emerald-500" required />
            </div>

            <div>
              <label className="text-sm font-medium text-gray-300 mb-1.5 block">Password</label>
              <div className="relative">
                <input type={showPass ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)}
                  className="w-full px-4 py-3 pr-12 bg-gray-800 border border-gray-700 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500" required />
                <button type="button" onClick={() => setShowPass(!showPass)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <Button type="submit" fullWidth size="lg" loading={loading} className="bg-emerald-600 hover:bg-emerald-500">
              Sign In to Admin <ArrowRight className="w-4 h-4" />
            </Button>
          </form>

          <div className="mt-5 pt-4 border-t border-gray-800 text-center">
            <p className="text-xs text-gray-500">Authorized personnel only. All access is logged and monitored.</p>
          </div>
        </div>

        <div className="text-center mt-6">
          <a href="/" className="text-xs text-gray-500 hover:text-gray-300">← Back to Vestra</a>
        </div>
      </div>
    </div>
  );
}
