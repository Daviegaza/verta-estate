'use client';

import { useEffect, useState } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, LoadingScreen } from '@/components/ui/card';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { KENYA_CITIES, KENYA_COUNTIES } from '@/lib/utils';
import type { Property } from '@/types';
import { ArrowLeft, Save } from 'lucide-react';

const PROPERTY_TYPES = ['residential', 'commercial', 'land', 'industrial', 'agricultural', 'student_housing', 'short_stay'];
const LISTING_TYPES = ['sale', 'rent', 'lease'];

export default function EditPropertyPage() {
  return (
    <AuthGuard requireAuth>
      <EditPropertyContent />
    </AuthGuard>
  );
}

function EditPropertyContent() {
  const router = useRouter();
  const params = useParams();
  const propertyId = parseInt(params.id as string);
  const { isAuthenticated, isHydrated } = useAuthStore();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const [form, setForm] = useState({
    title: '', description: '', property_type: 'residential',
    listing_type: 'sale', address: '', city: 'Nairobi',
    county: 'Nairobi', price: '', currency: 'KES',
    price_negotiable: false, bedrooms: '', bathrooms: '',
    size_sqft: '', year_built: '',
  });

  useEffect(() => {
    if (!isHydrated) return;
    if (!isAuthenticated) { router.push('/auth/login'); return; }
    loadProperty();
  }, [isHydrated, isAuthenticated, propertyId]);

  const loadProperty = async () => {
    try {
      const prop: Property = await api.getProperty(propertyId);
      setForm({
        title: prop.title || '',
        description: prop.description || '',
        property_type: prop.property_type || 'residential',
        listing_type: prop.listing_type || 'sale',
        address: prop.address || '',
        city: prop.city || 'Nairobi',
        county: prop.county || 'Nairobi',
        price: prop.price ? String(prop.price) : '',
        currency: prop.currency || 'KES',
        price_negotiable: prop.price_negotiable || false,
        bedrooms: prop.bedrooms ? String(prop.bedrooms) : '',
        bathrooms: prop.bathrooms ? String(prop.bathrooms) : '',
        size_sqft: prop.size_sqft ? String(prop.size_sqft) : '',
        year_built: prop.year_built ? String(prop.year_built) : '',
      });
    } catch (err: any) {
      setError('Failed to load property. It may not exist or you may not have permission.');
    } finally {
      setLoading(false);
    }
  };

  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const handleSave = async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await api.updateProperty(propertyId, {
        title: form.title,
        description: form.description,
        property_type: form.property_type as any,
        listing_type: form.listing_type as any,
        address: form.address,
        city: form.city,
        county: form.county,
        price: form.price ? parseFloat(form.price) : undefined,
        currency: form.currency,
        price_negotiable: form.price_negotiable,
        bedrooms: form.bedrooms ? parseInt(form.bedrooms) : undefined,
        bathrooms: form.bathrooms ? parseInt(form.bathrooms) : undefined,
        size_sqft: form.size_sqft ? parseFloat(form.size_sqft) : undefined,
        year_built: form.year_built ? parseInt(form.year_built) : undefined,
      });
      setSuccess('Property updated successfully!');
      setTimeout(() => router.push(`/properties/${propertyId}`), 1500);
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to update property. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingScreen message="Loading property..." />;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Link href={`/properties/${propertyId}`} className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Edit Property</h1>
            <p className="text-gray-500 text-sm">Update your property listing details</p>
          </div>
        </div>

        {error && (
          <div className="mb-5 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
        )}
        {success && (
          <div className="mb-5 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-sm text-emerald-700">{success}</div>
        )}

        <Card className="p-8">
          <div className="space-y-5">
            <Input label="Property Title" value={form.title} onChange={(e) => set('title', e.target.value)} placeholder="e.g. Modern 3BR Apartment in Westlands" required />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
              <textarea
                value={form.description}
                onChange={(e) => set('description', e.target.value)}
                rows={4}
                placeholder="Describe the property..."
                className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Property Type</label>
                <select value={form.property_type} onChange={(e) => set('property_type', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white capitalize">
                  {PROPERTY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Listing Type</label>
                <select value={form.listing_type} onChange={(e) => set('listing_type', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white capitalize">
                  {LISTING_TYPES.map((t) => <option key={t} value={t}>For {t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                </select>
              </div>
            </div>

            <Input label="Street Address" value={form.address} onChange={(e) => set('address', e.target.value)} placeholder="e.g. Waiyaki Way, Westlands" required />

            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">City</label>
                <select value={form.city} onChange={(e) => set('city', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white">
                  {KENYA_CITIES.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">County</label>
                <select value={form.county} onChange={(e) => set('county', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white">
                  {KENYA_COUNTIES.map((c) => <option key={c}>{c}</option>)}
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input label="Price (KES)" type="number" value={form.price} onChange={(e) => set('price', e.target.value)} placeholder="e.g. 5000000" required />
              <div className="flex items-end">
                <label className="flex items-center gap-2 cursor-pointer pb-2">
                  <input type="checkbox" checked={form.price_negotiable} onChange={(e) => set('price_negotiable', e.target.checked)} className="rounded border-gray-300 text-emerald-600" />
                  <span className="text-sm text-gray-600">Price Negotiable</span>
                </label>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <Input label="Bedrooms" type="number" value={form.bedrooms} onChange={(e) => set('bedrooms', e.target.value)} placeholder="e.g. 3" />
              <Input label="Bathrooms" type="number" value={form.bathrooms} onChange={(e) => set('bathrooms', e.target.value)} placeholder="e.g. 2" />
              <Input label="Size (sqft)" type="number" value={form.size_sqft} onChange={(e) => set('size_sqft', e.target.value)} placeholder="e.g. 1200" />
              <Input label="Year Built" type="number" value={form.year_built} onChange={(e) => set('year_built', e.target.value)} placeholder="e.g. 2020" />
            </div>
          </div>

          <div className="flex gap-3 mt-8 pt-6 border-t border-gray-100">
            <Link href={`/properties/${propertyId}`}>
              <Button variant="outline">Cancel</Button>
            </Link>
            <Button fullWidth loading={saving} onClick={handleSave} leftIcon={<Save className="w-4 h-4" />}>
              Save Changes
            </Button>
          </div>
        </Card>
      </div>
    </div>
  );
}
