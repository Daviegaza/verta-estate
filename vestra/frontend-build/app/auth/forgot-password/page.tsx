'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { ShieldCheck, Mail, ArrowLeft, CheckCircle2, AlertCircle } from 'lucide-react';
import api from '@/lib/api';

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.forgotPassword(email);
      setSent(true);
    } catch (err: any) {
      const message = err?.response?.data?.detail
        || err?.response?.data?.message
        || 'Something went wrong. Please try again later.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 text-2xl font-bold text-gray-900">
            <ShieldCheck className="w-8 h-8 text-emerald-600" />
            Vestra
          </Link>
        </div>

        {!sent ? (
          <Card className="p-8">
            <h1 className="text-xl font-bold text-gray-900 mb-2">Reset your password</h1>
            <p className="text-sm text-gray-500 mb-6">
              Enter your email address and we'll send you a link to reset your password.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <Input
                label="Email Address"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                leftElement={<Mail className="w-4 h-4" />}
              />

              {error && (
                <div className="flex items-start gap-2 p-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                  <AlertCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

              <Button type="submit" fullWidth loading={loading}>
                Send Reset Link
              </Button>
            </form>

            <div className="mt-6 text-center">
              <Link href="/auth/login" className="inline-flex items-center gap-1 text-sm text-emerald-600 hover:text-emerald-700 font-medium">
                <ArrowLeft className="w-3.5 h-3.5" />
                Back to login
              </Link>
            </div>
          </Card>
        ) : (
          <Card className="p-8 text-center">
            <CheckCircle2 className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
            <h1 className="text-xl font-bold text-gray-900 mb-2">Check your email</h1>
            <p className="text-sm text-gray-500 mb-6">
              If an account exists for {email}, we've sent a password reset link.
              Please check your inbox and spam folder.
            </p>
            <Link href="/auth/login">
              <Button variant="outline" fullWidth>Back to Login</Button>
            </Link>
          </Card>
        )}

        <p className="text-center text-xs text-gray-400 mt-6">
          Need help? Contact{' '}
          <a href="mailto:support@vestra.co.ke" className="text-emerald-600 hover:underline">
            support@vestra.co.ke
          </a>
        </p>
      </div>
    </div>
  );
}
