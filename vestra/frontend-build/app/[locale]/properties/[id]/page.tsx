'use client';

import { useEffect, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Badge, Card, Spinner } from '@/components/ui/card';
import TrustScoreCard from '@/components/verify/TrustScoreCard';
import TrustScoreGauge from '@/components/verify/TrustScoreGauge';
import ShareButtons from '@/components/property/ShareButtons';
import VestimaWidget from '@/components/property/VestimaWidget';
import { useAuthStore } from '@/store/authStore';
import { useRecentlyViewed } from '@/hooks/useRecentlyViewed';
import api from '@/lib/api';
import type { Property, Verification } from '@/types';
import {
  formatCurrency, formatDate, getListingTypeLabel,
  getPropertyTypeLabel, getBadgeColor
} from '@/lib/utils';
import {
  MapPin, BedDouble, Bath, Maximize, Calendar, Eye,
  ShieldCheck, Heart, ChevronLeft, ChevronRight,
  Phone, MessageCircle, AlertCircle, CheckCircle2, Home,
  Zap, Droplets, Wifi, Car, Trees
} from 'lucide-react';

const AMENITY_ICONS: Record<string, React.ReactNode> = {
  Parking: <Car className="w-4 h-4" />,
  Garden: <Trees className="w-4 h-4" />,
  'Fibre Internet': <Wifi className="w-4 h-4" />,
  Borehole: <Droplets className="w-4 h-4" />,
  'Backup Generator': <Zap className="w-4 h-4" />,
};

export default function PropertyDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { isAuthenticated, user, isHydrated } = useAuthStore();
  const { addView } = useRecentlyViewed();
  const propertyId = parseInt(params.id as string);

  const [property, setProperty] = useState<Property | null>(null);
  const [verifications, setVerifications] = useState<Verification[]>([]);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [activeImage, setActiveImage] = useState(0);
  const [saved, setSaved] = useState(false);
  const [showContact, setShowContact] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!propertyId || isNaN(propertyId)) { router.push('/market'); return; }
    loadData();
  }, [propertyId]);

  const loadData = async () => {
    setLoading(true);
    try {
      const [prop, vers] = await Promise.all([
        api.getProperty(propertyId),
        api.getPropertyVerifications(propertyId).catch(() => []),
      ]);
      setProperty(prop);
      setVerifications(vers);
      // Track in recently viewed (for retention)
      if (prop) {
        addView({
          id: prop.id,
          title: prop.title,
          city: prop.city,
          price: typeof prop.price === 'string' ? parseFloat(prop.price) : prop.price,
          currency: prop.currency,
        });
      }
    } catch {
      setError('Property not found.');
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyNow = async () => {
    if (!isHydrated) return;
    if (!isAuthenticated) { router.push('/auth/login?redirect=' + encodeURIComponent(window.location.pathname)); return; }
    setVerifying(true);
    try {
      const v = await api.runVerificationNow(propertyId);
      // Poll for result
      let attempts = 0;
      const poll = async () => {
        const updated = await api.getVerificationStatus(v.id);
        if (['approved', 'flagged', 'rejected'].includes(updated.status)) {
          setVerifications([updated, ...verifications]);
          await loadData();
          setVerifying(false);
        } else if (attempts < 15) {
          attempts++;
          setTimeout(poll, 3000);
        } else {
          setVerifying(false);
        }
      };
      setTimeout(poll, 3000);
    } catch {
      setVerifying(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center min-h-[60vh]">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  if (error || !property) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-2xl mx-auto px-4 py-32 text-center">
          <Home className="w-16 h-16 text-gray-200 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-800 mb-2">Property Not Found</h2>
          <p className="text-gray-500 mb-6">{error || 'This listing may have been removed.'}</p>
          <Link href="/market"><Button>Browse Properties</Button></Link>
        </div>
      </div>
    );
  }

  const latestVerification = verifications[0];
  const images = property.images?.length
    ? property.images
    : [`https://placehold.co/800x500/f0fdf4/059669?text=${encodeURIComponent(property.city)}`];

  const isOwner = user?.id === property.owner_id;

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      {/* Breadcrumb */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3 flex items-center gap-2 text-sm text-gray-500">
          <Link href="/" className="hover:text-gray-700">Home</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <Link href="/market" className="hover:text-gray-700">Properties</Link>
          <ChevronRight className="w-3.5 h-3.5" />
          <span className="text-gray-900 font-medium truncate">{property.title}</span>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="grid lg:grid-cols-3 gap-8">

          {/* Left — main content */}
          <div className="lg:col-span-2 space-y-6">

            {/* Image gallery */}
            <div className="relative bg-gray-900 rounded-2xl overflow-hidden">
              <img
                src={images[activeImage]}
                alt={property.title}
                className="w-full h-80 lg:h-[460px] object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).src =
                    `https://placehold.co/800x500/f0fdf4/059669?text=${encodeURIComponent(property.city)}`;
                }}
              />
              {/* Verified overlay */}
              {property.is_verified && (
                <div className={`absolute top-4 left-4 flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full border ${getBadgeColor(property.verification_badge)}`}>
                  <ShieldCheck className="w-3.5 h-3.5" />
                  Vestra Verified — {property.verification_badge?.toUpperCase()}
                </div>
              )}
              {/* Image nav */}
              {images.length > 1 && (
                <>
                  <button
                    onClick={() => setActiveImage((i) => Math.max(0, i - 1))}
                    className="absolute left-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-black/40 hover:bg-black/60 text-white rounded-full flex items-center justify-center"
                  >
                    <ChevronLeft className="w-5 h-5" />
                  </button>
                  <button
                    onClick={() => setActiveImage((i) => Math.min(images.length - 1, i + 1))}
                    className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-black/40 hover:bg-black/60 text-white rounded-full flex items-center justify-center"
                  >
                    <ChevronRight className="w-5 h-5" />
                  </button>
                  <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-1.5">
                    {images.map((_, i) => (
                      <button
                        key={i}
                        onClick={() => setActiveImage(i)}
                        className={`w-2 h-2 rounded-full transition-all ${i === activeImage ? 'bg-white w-5' : 'bg-white/50'}`}
                      />
                    ))}
                  </div>
                </>
              )}
              {/* Thumbnail strip */}
              {images.length > 1 && (
                <div className="flex gap-2 p-3 bg-black/20 backdrop-blur overflow-x-auto">
                  {images.map((img, i) => (
                    <img
                      key={i}
                      src={img}
                      alt=""
                      onClick={() => setActiveImage(i)}
                      className={`w-16 h-12 object-cover rounded-lg cursor-pointer flex-shrink-0 transition-all ${i === activeImage ? 'ring-2 ring-white' : 'opacity-60 hover:opacity-80'}`}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Title + basic info */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <div className="flex items-start justify-between gap-4 mb-4">
                <div className="flex-1">
                  <div className="flex flex-wrap gap-2 mb-3">
                    <Badge variant={property.listing_type === 'sale' ? 'info' : 'purple'}>
                      {getListingTypeLabel(property.listing_type)}
                    </Badge>
                    <Badge variant="default">{getPropertyTypeLabel(property.property_type)}</Badge>
                    {property.price_negotiable && <Badge variant="warning">Negotiable</Badge>}
                  </div>
                  <h1 className="text-2xl font-bold text-gray-900 mb-2">{property.title}</h1>
                  <div className="flex items-center gap-1.5 text-gray-500 text-sm">
                    <MapPin className="w-4 h-4 flex-shrink-0" />
                    <span>{property.address}, {property.city}, {property.county}</span>
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => setSaved(!saved)}
                    className={`p-2.5 rounded-xl border transition-all ${saved ? 'bg-red-50 border-red-300 text-red-500' : 'border-gray-200 text-gray-400 hover:text-red-400'}`}
                  >
                    <Heart className={`w-5 h-5 ${saved ? 'fill-red-400' : ''}`} />
                  </button>
                  <ShareButtons propertyId={property.id} title={property.title} />
                </div>
              </div>

              {/* Price */}
              <div className="flex items-end gap-3 mb-6 pb-6 border-b border-gray-100">
                <div>
                  <p className="text-3xl font-bold text-gray-900">
                    {formatCurrency(property.price, property.currency)}
                  </p>
                  {property.listing_type === 'rent' && (
                    <p className="text-sm text-gray-500">per month</p>
                  )}
                </div>
                {property.trust_score && (
                  <div className="ml-auto flex items-center gap-3">
                    <TrustScoreGauge score={property.trust_score} size={80} showLabel={false} />
                  </div>
                )}
              </div>

              {/* Key stats */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                {property.bedrooms && (
                  <div className="flex items-center gap-2.5 bg-gray-50 rounded-xl p-3">
                    <BedDouble className="w-5 h-5 text-gray-500" />
                    <div>
                      <p className="text-lg font-bold text-gray-900">{property.bedrooms}</p>
                      <p className="text-xs text-gray-500">Bedrooms</p>
                    </div>
                  </div>
                )}
                {property.bathrooms && (
                  <div className="flex items-center gap-2.5 bg-gray-50 rounded-xl p-3">
                    <Bath className="w-5 h-5 text-gray-500" />
                    <div>
                      <p className="text-lg font-bold text-gray-900">{property.bathrooms}</p>
                      <p className="text-xs text-gray-500">Bathrooms</p>
                    </div>
                  </div>
                )}
                {property.size_sqft && (
                  <div className="flex items-center gap-2.5 bg-gray-50 rounded-xl p-3">
                    <Maximize className="w-5 h-5 text-gray-500" />
                    <div>
                      <p className="text-lg font-bold text-gray-900">{property.size_sqft.toLocaleString()}</p>
                      <p className="text-xs text-gray-500">Sq Ft</p>
                    </div>
                  </div>
                )}
                {property.year_built && (
                  <div className="flex items-center gap-2.5 bg-gray-50 rounded-xl p-3">
                    <Calendar className="w-5 h-5 text-gray-500" />
                    <div>
                      <p className="text-lg font-bold text-gray-900">{property.year_built}</p>
                      <p className="text-xs text-gray-500">Year Built</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Description */}
            {property.description && (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-3">About this Property</h2>
                <p className="text-gray-600 leading-relaxed whitespace-pre-wrap">{property.description}</p>
              </div>
            )}

            {/* Amenities */}
            {property.amenities?.length > 0 && (
              <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">Amenities & Features</h2>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  {property.amenities.map((amenity) => (
                    <div key={amenity} className="flex items-center gap-2 text-sm text-gray-700">
                      <CheckCircle2 className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      {amenity}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* AI Verification Report */}
            {latestVerification && (
              <div>
                <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                  <ShieldCheck className="w-5 h-5 text-emerald-600" />
                  AI Verification Report
                </h2>
                <TrustScoreCard verification={latestVerification} />
              </div>
            )}

            {/* Property meta */}
            <div className="bg-white rounded-2xl border border-gray-100 shadow-sm p-6">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">Property Details</h2>
              <div className="grid grid-cols-2 gap-y-3 text-sm">
                {[
                  { label: 'Property ID', value: `#${property.id}` },
                  { label: 'Status', value: property.status },
                  { label: 'Listed', value: formatDate(property.created_at) },
                  { label: 'Views', value: `${property.views} views` },
                  { label: 'Country', value: property.country },
                  { label: 'Currency', value: property.currency },
                ].map(({ label, value }) => (
                  <div key={label}>
                    <p className="text-gray-400 text-xs uppercase tracking-wide mb-0.5">{label}</p>
                    <p className="font-medium text-gray-800 capitalize">{value}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Right — sidebar */}
          <div className="space-y-4">

            {/* Verify CTA */}
            {!property.is_verified && !latestVerification && (
              <div className="bg-white rounded-2xl border-2 border-amber-200 p-5">
                <div className="flex items-start gap-3 mb-4">
                  <AlertCircle className="w-5 h-5 text-amber-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-semibold text-gray-900">Not Yet Verified</h3>
                    <p className="text-sm text-gray-500 mt-1">
                      This property hasn't been verified. Get an AI trust report to confirm ownership and detect fraud.
                    </p>
                  </div>
                </div>
                <Button
                  fullWidth
                  onClick={handleVerifyNow}
                  loading={verifying}
                  leftIcon={<ShieldCheck className="w-4 h-4" />}
                >
                  {verifying ? 'Running AI Analysis...' : 'Verify This Property — Free Demo'}
                </Button>
                <Link href="/verify">
                  <Button fullWidth variant="outline" size="sm" className="mt-2">
                    Verify with M-Pesa (KES 500)
                  </Button>
                </Link>
              </div>
            )}

            {/* Verified badge */}
            {property.is_verified && (
              <div className="bg-emerald-50 border border-emerald-200 rounded-2xl p-5">
                <div className="flex items-center gap-3 mb-2">
                  <div className="w-10 h-10 bg-emerald-500 rounded-xl flex items-center justify-center">
                    <ShieldCheck className="w-5 h-5 text-white" />
                  </div>
                  <div>
                    <h3 className="font-semibold text-emerald-900">Vestra Verified</h3>
                    <p className="text-xs text-emerald-600 capitalize">{property.verification_badge} Status</p>
                  </div>
                </div>
                <p className="text-sm text-emerald-700">
                  This property has passed Vestra's AI verification. Ownership, documents, and pricing have been checked.
                </p>
              </div>
            )}

            {/* Contact card — gated behind sign-in for lead capture */}
            <Card>
              <h3 className="font-semibold text-gray-900 mb-3">Contact Owner / Agent</h3>
              {!isOwner ? (
                <>
                  {!isAuthenticated ? (
                    /* Sign-in gate — compelling CTA */
                    <div className="space-y-3">
                      <div className="bg-gradient-to-br from-emerald-50 to-blue-50 border border-emerald-200 rounded-xl p-4">
                        <div className="flex items-start gap-2.5 mb-2">
                          <ShieldCheck className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
                          <div>
                            <p className="font-semibold text-emerald-900 text-sm">Sign in to unlock full access</p>
                            <p className="text-xs text-emerald-700 mt-0.5">
                              Get contact details, save properties, receive price drop alerts, and AI-powered recommendations — all free.
                            </p>
                          </div>
                        </div>
                      </div>
                      <Link href={`/auth/login?redirect=${encodeURIComponent(window.location.pathname)}`}>
                        <Button fullWidth className="bg-emerald-600 hover:bg-emerald-700 text-white">
                          <Phone className="w-4 h-4 mr-2" />
                          Sign In to View Contact
                        </Button>
                      </Link>
                      <p className="text-[11px] text-gray-400 text-center">
                        No spam. Your data is protected. We never share your number.
                      </p>
                      <div className="flex gap-2 pt-1">
                        <Link href="/auth/register" className="flex-1">
                          <Button fullWidth variant="outline" size="sm">
                            Create Free Account
                          </Button>
                        </Link>
                      </div>
                    </div>
                  ) : !showContact ? (
                    <div className="space-y-3">
                      <Button fullWidth onClick={() => setShowContact(true)} className="bg-emerald-600 hover:bg-emerald-700 text-white">
                        <Phone className="w-4 h-4 mr-2" />
                        Reveal Contact Details
                      </Button>
                      <p className="text-xs text-gray-400 text-center">Your identity is protected when you contact sellers</p>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <div className="flex items-center gap-3 p-3 bg-emerald-50 rounded-xl">
                        <Phone className="w-5 h-5 text-emerald-600" />
                        <div>
                          <p className="text-xs text-gray-500">Phone</p>
                          <p className="text-sm font-semibold text-gray-900">+254 7XX XXX XXX</p>
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button fullWidth variant="outline" leftIcon={<MessageCircle className="w-4 h-4" />}>
                          Send Message
                        </Button>
                        <Button fullWidth className="bg-green-500 hover:bg-green-600 text-white">
                          WhatsApp
                        </Button>
                      </div>
                      {/* Save & Track */}
                      <div className="border-t border-gray-100 pt-3 mt-1">
                        <button
                          onClick={() => setSaved(!saved)}
                          className={`w-full flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all ${
                            saved
                              ? 'bg-red-50 text-red-600 border border-red-200'
                              : 'bg-gray-50 text-gray-600 border border-gray-200 hover:bg-gray-100'
                          }`}
                        >
                          <Heart className={`w-4 h-4 ${saved ? 'fill-red-400' : ''}`} />
                          {saved ? 'Saved — We\'ll alert you of changes' : 'Save Property & Get Price Alerts'}
                        </button>
                      </div>
                    </div>
                  )}
                </>
              ) : (
                <div className="space-y-2">
                  <p className="text-sm text-gray-500 mb-3">This is your listing</p>
                  <Link href={`/properties/edit/${property.id}`}>
                    <Button fullWidth variant="outline">Edit Listing</Button>
                  </Link>
                  <Button fullWidth onClick={handleVerifyNow} loading={verifying}>
                    <ShieldCheck className="w-4 h-4 mr-2" />
                    Run AI Verification
                  </Button>
                </div>
              )}
            </Card>

            {/* Vestima AI Price Estimate */}
            <VestimaWidget
              propertyId={property.id}
              submittedPrice={property.price}
              initialEstimate={(property as any).vestima_estimate ?? null}
            />

            {/* Safety tips */}
            <Card className="bg-blue-50 border-blue-200">
              <h3 className="font-semibold text-blue-900 mb-3">🔒 Vestra Safety Tips</h3>
              <ul className="space-y-2 text-sm text-blue-800">
                {[
                  'Always verify ownership before paying',
                  'Never send money before seeing the property',
                  'Use Vestra escrow for secure transactions',
                  'Check if agent has Vestra Verified badge',
                  'Report suspicious listings immediately',
                ].map((tip) => (
                  <li key={tip} className="flex items-start gap-2">
                    <span className="text-blue-500 flex-shrink-0 mt-0.5">•</span>
                    {tip}
                  </li>
                ))}
              </ul>
            </Card>

            {/* Share */}
            <Card padding="sm">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Eye className="w-4 h-4 text-gray-400" />
                  <span className="text-sm text-gray-500">{property.views} views</span>
                </div>
                <ShareButtons propertyId={property.id} title={property.title} />
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
