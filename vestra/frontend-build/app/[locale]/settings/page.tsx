'use client';

import { useState, useEffect } from 'react';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Card, CardHeader, CardTitle, CardContent, Spinner } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import type { User } from '@/types';
import { User as UserIcon, Camera, Save, Mail, Phone, MapPin } from 'lucide-react';

export default function SettingsPage() {
  return (
    <AuthGuard requireAuth>
      <SettingsContent />
    </AuthGuard>
  );
}

interface ProfileForm {
  full_name: string;
  email: string;
  phone: string;
  location: string;
  bio: string;
}

function SettingsContent() {
  const [form, setForm] = useState<ProfileForm>({
    full_name: '',
    email: '',
    phone: '',
    location: '',
    bio: '',
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const loadProfile = async () => {
    setLoading(true);
    setError('');
    try {
      const user = await api.getMe();
      setForm({
        full_name: user.full_name || '',
        email: user.email || '',
        phone: user.phone || '',
        location: user.location || '',
        bio: (user as any).bio || '',
      });
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to load profile');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadProfile();
  }, []);

  const handleChange = (field: keyof ProfileForm) => (
    e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>
  ) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    setError('');
    try {
      await api.updateMe({
        full_name: form.full_name,
        phone: form.phone,
        location: form.location,
      } as Partial<User>);
      await useAuthStore.getState().refreshUser();
      setMessage('Profile updated successfully');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-32">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        {/* Page Header */}
        <div className="flex items-center gap-4 mb-10">
          <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
            <UserIcon className="w-7 h-7 text-emerald-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Account Settings</h1>
            <p className="text-sm text-gray-500 mt-1">
              Manage your personal information and account preferences
            </p>
          </div>
        </div>

        {/* Success Message */}
        {message && (
          <div className="mb-6 p-4 bg-emerald-50 border border-emerald-200 rounded-2xl text-sm text-emerald-700 flex items-center gap-2">
            <Save className="w-4 h-4 flex-shrink-0" />
            {message}
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-2xl text-sm text-red-700 flex items-start gap-2">
            <span className="w-4 h-4 flex-shrink-0 mt-0.5 text-red-500">!</span>
            {error}
          </div>
        )}

        {/* Profile Information Card */}
        <Card>
          <CardHeader>
            <CardTitle>Profile Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              {/* Avatar Section */}
              <div className="flex items-center gap-4 pb-5 border-b border-gray-100">
                <div className="relative">
                  <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                    <span className="text-emerald-700 font-bold text-xl">
                      {form.full_name?.[0]?.toUpperCase() || 'U'}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="absolute -bottom-1 -right-1 w-6 h-6 bg-emerald-600 rounded-full flex items-center justify-center shadow-sm hover:bg-emerald-700 transition-colors"
                    onClick={() => {}}
                  >
                    <Camera className="w-3 h-3 text-white" />
                  </button>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{form.full_name || 'User'}</p>
                  <p className="text-xs text-gray-400">{form.email}</p>
                </div>
              </div>

              {/* Full Name */}
              <Input
                label="Full Name"
                value={form.full_name}
                onChange={handleChange('full_name')}
                placeholder="Enter your full name"
                leftElement={<UserIcon className="w-4 h-4" />}
              />

              {/* Email (read-only) */}
              <Input
                label="Email Address"
                value={form.email}
                onChange={handleChange('email')}
                placeholder="Enter your email"
                leftElement={<Mail className="w-4 h-4" />}
                disabled
                hint="Email cannot be changed. Contact support for assistance."
              />

              {/* Phone */}
              <Input
                label="Phone Number"
                value={form.phone}
                onChange={handleChange('phone')}
                placeholder="254712345678"
                leftElement={<Phone className="w-4 h-4" />}
              />

              {/* Location */}
              <Input
                label="Location"
                value={form.location}
                onChange={handleChange('location')}
                placeholder="Nairobi, Kenya"
                leftElement={<MapPin className="w-4 h-4" />}
              />

              {/* Bio */}
              <div className="w-full">
                <label className="block text-sm font-medium text-gray-700 mb-1.5">
                  Bio
                </label>
                <textarea
                  value={form.bio}
                  onChange={handleChange('bio')}
                  placeholder="Tell us a little about yourself..."
                  rows={4}
                  className="block w-full rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-gray-900 placeholder:text-gray-400 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-transparent transition-all duration-200 resize-none"
                />
              </div>

              {/* Save Button */}
              <div className="pt-2 flex justify-end">
                <Button
                  onClick={handleSave}
                  loading={saving}
                  size="lg"
                  className="gap-2"
                >
                  <Save className="w-4 h-4" />
                  Save Changes
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
