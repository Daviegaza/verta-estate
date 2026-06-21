'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import AuthGuard from '@/components/layout/AuthGuard';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/authStore';
import api from '@/lib/api';
import { KENYA_CITIES, KENYA_COUNTIES, AMENITIES_OPTIONS } from '@/lib/utils';
import { Building2, MapPin, DollarSign, Home, CheckCircle2, ArrowLeft } from 'lucide-react';
import Link from 'next/link';

const PROPERTY_TYPES = ['residential', 'commercial', 'land', 'industrial', 'agricultural', 'student_housing', 'short_stay'];
const LISTING_TYPES = ['sale', 'rent', 'lease'];

export default function NewPropertyPage() {
  return (
    <AuthGuard requireAuth requireRoles={['seller', 'agent', 'landlord', 'admin', 'super_admin']}>
      <NewPropertyContent />
    </AuthGuard>
  );
}

function NewPropertyContent() {
  const router = useRouter();
  const { isAuthenticated, isHydrated } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState(1);
  const [selectedAmenities, setSelectedAmenities] = useState<string[]>([]);

  const [form, setForm] = useState({
    title: '', description: '', property_type: 'residential',
    listing_type: 'sale', address: '', city: 'Nairobi',
    county: 'Nairobi', price: '', currency: 'KES',
    price_negotiable: false, bedrooms: '', bathrooms: '',
    size_sqft: '', year_built: '',
  });

  const set = (k: string, v: string | boolean) => setForm((f) => ({ ...f, [k]: v }));

  const toggleAmenity = (a: string) =>
    setSelectedAmenities((prev) => prev.includes(a) ? prev.filter((x) => x !== a) : [...prev, a]);

  const handleSubmit = async () => {
    if (!isAuthenticated) { router.push('/auth/login'); return; }
    setLoading(true);
    setError('');
    try {
      const prop = await api.createProperty({
        title: form.title,
        description: form.description,
        property_type: form.property_type as any,
        listing_type: form.listing_type as any,
        address: form.address,
        city: form.city,
        county: form.county,
        price: parseFloat(form.price),
        currency: form.currency,
        price_negotiable: form.price_negotiable,
        bedrooms: form.bedrooms ? parseInt(form.bedrooms) : undefined,
        bathrooms: form.bathrooms ? parseInt(form.bathrooms) : undefined,
        size_sqft: form.size_sqft ? parseFloat(form.size_sqft) : undefined,
        year_built: form.year_built ? parseInt(form.year_built) : undefined,
        amenities: selectedAmenities,
      });
      router.push('/dashboard');
    } catch (err: any) {
      setError(err?.response?.data?.detail || 'Failed to create listing. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const STEPS = ['Basic Info', 'Location', 'Details & Price', 'Amenities'];

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-2xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center gap-3 mb-8">
          <Link href="/dashboard" className="p-2 hover:bg-gray-100 rounded-xl transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-600" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">New Property Listing</h1>
            <p className="text-gray-500 text-sm">Fill in the details below to list your property</p>
          </div>
        </div>

        {/* Step indicator */}
        <div className="flex items-center mb-8">
          {STEPS.map((label, i) => {
            const stepNum = i + 1;
            const isActive = step === stepNum;
            const isDone = step > stepNum;
            return (
              <div key={label} className="flex items-center flex-1 last:flex-none">
                <div className={`flex items-center gap-2 text-xs font-medium ${isActive ? 'text-emerald-700' : isDone ? 'text-emerald-600' : 'text-gray-400'}`}>
                  <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 ${
                    isActive ? 'bg-emerald-600 text-white' : isDone ? 'bg-emerald-100 text-emerald-700' : 'bg-gray-100 text-gray-400'
                  }`}>
                    {isDone ? '✓' : stepNum}
                  </div>
                  <span className="hidden sm:block">{label}</span>
                </div>
                {i < STEPS.length - 1 && <div className="flex-1 h-px bg-gray-200 mx-2" />}
              </div>
            );
          })}
        </div>

        {error && (
          <div className="mb-5 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">{error}</div>
        )}

        <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-8">
          {/* Step 1 - Basic Info */}
          {step === 1 && (
            <div className="space-y-5">
              <div className="flex items-center gap-2 mb-2">
                <Building2 className="w-5 h-5 text-emerald-600" />
                <h2 className="font-semibold text-gray-900">Basic Information</h2>
              </div>
              <Input label="Property Title" value={form.title} onChange={(e) => set('title', e.target.value)} placeholder="e.g. Modern 3BR Apartment in Westlands" required />
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Description</label>
                <textarea
                  value={form.description}
                  onChange={(e) => set('description', e.target.value)}
                  rows={4}
                  placeholder="Describe the property, its features, neighborhood, security..."
                  className="w-full border border-gray-200 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 resize-none"
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Property Type <span className="text-red-500">*</span></label>
                  <select value={form.property_type} onChange={(e) => set('property_type', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white capitalize">
                    {PROPERTY_TYPES.map((t) => <option key={t} value={t}>{t.replace(/_/g, ' ')}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">Listing Type <span className="text-red-500">*</span></label>
                  <select value={form.listing_type} onChange={(e) => set('listing_type', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white capitalize">
                    {LISTING_TYPES.map((t) => <option key={t} value={t}>For {t.charAt(0).toUpperCase() + t.slice(1)}</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 2 - Location */}
          {step === 2 && (
            <div className="space-y-5">
              <div className="flex items-center gap-2 mb-2">
                <MapPin className="w-5 h-5 text-emerald-600" />
                <h2 className="font-semibold text-gray-900">Location Details</h2>
              </div>
              <Input label="Street Address" value={form.address} onChange={(e) => set('address', e.target.value)} placeholder="e.g. Waiyaki Way, Westlands" required />
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">City <span className="text-red-500">*</span></label>
                  <select value={form.city} onChange={(e) => set('city', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white">
                    {KENYA_CITIES.map((c) => <option key={c}>{c}</option>)}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">County <span className="text-red-500">*</span></label>
                  <select value={form.county} onChange={(e) => set('county', e.target.value)} className="w-full border border-gray-200 rounded-xl px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 bg-white">
                    {KENYA_COUNTIES.map((c) => <option key={c}>{c}</option>)}
                  </select>
                </div>
              </div>
            </div>
          )}

          {/* Step 3 - Details & Price */}
          {step === 3 && (
            <div className="space-y-5">
              <div className="flex items-center gap-2 mb-2">
                <DollarSign className="w-5 h-5 text-emerald-600" />
                <h2 className="font-semibold text-gray-900">Details & Pricing</h2>
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
          )}

          {/* Step 4 - Amenities */}
          {step === 4 && (
            <div>
              <div className="flex items-center gap-2 mb-4">
                <Home className="w-5 h-5 text-emerald-600" />
                <h2 className="font-semibold text-gray-900">Amenities</h2>
              </div>
              <p className="text-sm text-gray-500 mb-5">Select all amenities available at this property</p>
              <div className="grid grid-cols-2 gap-2">
                {AMENITIES_OPTIONS.map((a) => {
                  const selected = selectedAmenities.includes(a);
                  return (
                    <button key={a} type="button" onClick={() => toggleAmenity(a)}
                      className={`flex items-center gap-2 p-3 rounded-xl border text-sm font-medium text-left transition-all ${
                        selected ? 'bg-emerald-50 border-emerald-400 text-emerald-800' : 'border-gray-200 text-gray-600 hover:border-gray-400'
                      }`}>
                      {selected && <CheckCircle2 className="w-4 h-4 text-emerald-600 flex-shrink-0" />}
                      {!selected && <div className="w-4 h-4 rounded-full border-2 border-gray-300 flex-shrink-0" />}
                      {a}
                    </button>
                  );
                })}
              </div>
              {selectedAmenities.length > 0 && (
                <p className="text-xs text-emerald-600 mt-3 font-medium">{selectedAmenities.length} amenities selected</p>
              )}
            </div>
          )}

          {/* Navigation */}
          <div className="flex gap-3 mt-8 pt-6 border-t border-gray-100">
            {step > 1 && (
              <Button variant="outline" onClick={() => setStep((s) => s - 1)}>Back</Button>
            )}
            {step < 4 ? (
              <Button fullWidth onClick={() => setStep((s) => s + 1)}
                disabled={step === 1 && (!form.title || !form.property_type) || step === 2 && (!form.address || !form.city) || step === 3 && !form.price}>
                Continue
              </Button>
            ) : (
              <Button fullWidth loading={loading} onClick={handleSubmit}>
                Publish Listing
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
