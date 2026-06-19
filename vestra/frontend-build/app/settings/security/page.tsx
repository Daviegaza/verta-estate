'use client';

import { useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { Key, Shield, Smartphone, Lock, ArrowLeft, Clock } from 'lucide-react';

export default function SecuritySettingsPage() {
  return (
    <AuthGuard requireAuth>
      <SecurityContent />
    </AuthGuard>
  );
}

function SecurityContent() {
  const { logout } = useAuthStore();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [changingPassword, setChangingPassword] = useState(false);
  const [passwordMessage, setPasswordMessage] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [signingOut, setSigningOut] = useState(false);

  const validatePasswords = (): string | null => {
    if (!currentPassword) return 'Current password is required';
    if (!newPassword) return 'New password is required';
    if (newPassword.length < 8) return 'New password must be at least 8 characters';
    if (newPassword !== confirmPassword) return 'Passwords do not match';
    return null;
  };

  const handleChangePassword = async () => {
    const validationError = validatePasswords();
    if (validationError) {
      setPasswordError(validationError);
      setPasswordMessage('');
      return;
    }

    setChangingPassword(true);
    setPasswordMessage('');
    setPasswordError('');
    try {
      await api.changePassword(currentPassword, newPassword);
      setPasswordMessage('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err: any) {
      setPasswordError(err?.response?.data?.detail || 'Failed to change password');
    } finally {
      setChangingPassword(false);
    }
  };

  const handleSignOutAll = async () => {
    setSigningOut(true);
    try {
      await api.client.post('/api/auth/logout-all');
      logout();
      window.location.href = '/auth/login';
    } catch {
      setSigningOut(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        {/* Back Link */}
        <Link
          href="/settings"
          className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-emerald-600 transition-colors mb-8"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Settings
        </Link>

        {/* Page Header */}
        <div className="flex items-center gap-4 mb-10">
          <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <Shield className="w-7 h-7 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Security Settings</h1>
            <p className="text-sm text-gray-500 mt-1">
              Manage your password and account security
            </p>
          </div>
        </div>

        {/* Password Message */}
        {passwordMessage && (
          <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-sm text-emerald-700 flex items-center gap-2">
            <Key className="w-4 h-4 flex-shrink-0" />
            {passwordMessage}
          </div>
        )}

        {/* Password Error */}
        {passwordError && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2">
            <span className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-500">!</span>
            {passwordError}
          </div>
        )}

        {/* Change Password Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Key className="w-4 h-4 text-emerald-600" />
                Change Password
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              <Input
                label="Current Password"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                placeholder="Enter your current password"
                leftElement={<Lock className="w-4 h-4" />}
              />
              <Input
                label="New Password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                placeholder="At least 8 characters"
                leftElement={<Key className="w-4 h-4" />}
                hint="Use a strong, unique password with at least 8 characters"
              />
              <Input
                label="Confirm New Password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter your new password"
                leftElement={<Key className="w-4 h-4" />}
              />
              <div className="pt-2 flex justify-end">
                <Button
                  onClick={handleChangePassword}
                  loading={changingPassword}
                  size="lg"
                  className="gap-2"
                >
                  <Lock className="w-4 h-4" />
                  Update Password
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Two-Factor Authentication Card */}
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-emerald-600" />
                Two-Factor Authentication
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-gray-100 rounded-xl flex items-center justify-center flex-shrink-0">
                <Shield className="w-6 h-6 text-gray-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900 mb-1">Coming Soon</h3>
                <p className="text-sm text-gray-500 leading-relaxed">
                  Two-factor authentication adds an extra layer of security to your account.
                  Once enabled, you will need both your password and a one-time code from
                  your mobile device to sign in. We are working on bringing this feature
                  to you soon.
                </p>
                <div className="mt-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg text-xs font-medium text-amber-700">
                  <Clock className="w-3.5 h-3.5" />
                  Under development
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Session Management Card */}
        <Card>
          <CardHeader>
            <CardTitle>
              <span className="flex items-center gap-2">
                <Smartphone className="w-4 h-4 text-emerald-600" />
                Session Management
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-start gap-4">
              <div className="w-12 h-12 bg-red-50 rounded-xl flex items-center justify-center flex-shrink-0">
                <Shield className="w-6 h-6 text-red-400" />
              </div>
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-gray-900 mb-1">Sign Out All Devices</h3>
                <p className="text-sm text-gray-500 leading-relaxed mb-4">
                  If you suspect someone else has accessed your account, you can force a
                  sign out from all active sessions. You will be signed out of all devices
                  and redirected to the login page.
                </p>
                <Button
                  variant="danger"
                  size="md"
                  onClick={handleSignOutAll}
                  loading={signingOut}
                  className="gap-2"
                >
                  <Shield className="w-4 h-4" />
                  Sign Out All Devices
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

