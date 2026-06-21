'use client';

import { useState, useEffect } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import api from '@/lib/api';
import {
  Star,
  ShieldCheck,
  MapPin,
  Phone,
  Mail,
  Award,
  Home,
  Clock,
  CheckCircle,
  MessageSquare,
} from 'lucide-react';
import { formatCurrency, formatRelativeTime, getTrustScoreBg } from '@/lib/utils';

// ─── Types ─────────────────────────────────────────────────────────────────

interface AgentProfile {
  id: number;
  user_id: number;
  full_name: string;
  email: string;
  agency_name: string | null;
  license_number: string | null;
  years_experience: number;
  specialization: string[];
  badge_level: string | null;
  total_listings: number;
  successful_deals: number;
  rating: number;
  subscription_tier: string;
  location: string | null;
  avatar_url: string | null;
  bio: string | null;
  phone: string | null;
  created_at: string;
}

interface RecentListing {
  id: number;
  title: string;
  city: string;
  price: number;
  trust_score: number | null;
  images: string[];
  listing_type: string;
  property_type: string;
  created_at: string;
}

// ─── Badge colour map ──────────────────────────────────────────────────────

const BADGE_COLORS: Record<string, string> = {
  platinum: 'bg-gray-900 text-white',
  gold: 'bg-amber-500 text-white',
  silver: 'bg-gray-300 text-gray-700',
  bronze: 'bg-amber-700 text-white',
};

const TIER_COLORS: Record<string, string> = {
  premium: 'bg-purple-50 text-purple-700 border-purple-200',
  pro: 'bg-blue-50 text-blue-700 border-blue-200',
  basic: 'bg-gray-50 text-gray-600 border-gray-200',
};

// ─── Page ──────────────────────────────────────────────────────────────────

export default function AgentProfilePage() {
  const params = useParams();
  const agentId = params?.id as string;

  const [agent, setAgent] = useState<AgentProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [recentListings, setRecentListings] = useState<RecentListing[]>([]);
  const [listingsLoading, setListingsLoading] = useState(false);

  // ── Data fetching ──────────────────────────────────────────────────────

  const loadRecentListings = async (userId: number) => {
    setListingsLoading(true);
    try {
      const res = await api.client.get('/api/properties', {
        params: { owner_id: userId, limit: 6 },
      });
      setRecentListings(res.data.items || []);
    } catch (err) {
      console.error('Failed to load listings:', err);
    } finally {
      setListingsLoading(false);
    }
  };

  const loadAgent = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.client.get('/api/admin/users', {
        params: { role: 'agent', limit: 100 },
      });
      const agents: AgentProfile[] = res.data.items || [];
      const found = agents.find((a) => a.user_id === Number(agentId));
      if (found) {
        setAgent(found);
        loadRecentListings(found.user_id);
      } else {
        setAgent(null);
      }
    } catch (err: unknown) {
      console.error('Failed to load agent:', err);
      const axiosErr = err as { response?: { data?: { message?: string } }; message?: string };
      setError(
        axiosErr?.response?.data?.message ||
          axiosErr?.message ||
          'Failed to load agent profile',
      );
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (agentId) {
      loadAgent();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [agentId]);

  // ── Derived values ─────────────────────────────────────────────────────

  const initials = agent?.full_name
    ? agent.full_name
        .split(' ')
        .map((n) => n[0])
        .join('')
        .slice(0, 2)
        .toUpperCase()
    : 'AG';

  const memberSinceYear = agent ? new Date(agent.created_at).getFullYear() : null;

  const renderStars = (rating: number) => {
    const stars: React.ReactNode[] = [];
    const full = Math.floor(rating);
    const hasHalf = rating - full >= 0.5;
    for (let i = 0; i < 5; i++) {
      if (i < full) {
        stars.push(
          <Star key={i} className="w-4 h-4 text-amber-400 fill-amber-400" />,
        );
      } else if (i === full && hasHalf) {
        stars.push(
          <Star key={i} className="w-4 h-4 text-amber-400 fill-amber-200" />,
        );
      } else {
        stars.push(
          <Star key={i} className="w-4 h-4 text-gray-200" />,
        );
      }
    }
    return stars;
  };

  // ── Loading state ──────────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="flex justify-center items-center py-40">
          <Spinner size="lg" />
        </div>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────────────

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
          <div className="text-center py-20">
            <ShieldCheck className="w-16 h-16 text-red-300 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              Something went wrong
            </h3>
            <p className="text-gray-400 mb-6">{error}</p>
            <Button onClick={loadAgent}>Try Again</Button>
          </div>
        </div>
      </div>
    );
  }

  // ── Not-found state ────────────────────────────────────────────────────

  if (!agent) {
    return (
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
          <div className="text-center py-20">
            <MapPin className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">
              Agent not found
            </h3>
            <p className="text-gray-400 mb-6">
              The agent you&rsquo;re looking for doesn&rsquo;t exist or has been
              removed.
            </p>
            <Link href="/agents">
              <Button variant="outline">Browse All Agents</Button>
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // ── Main content ───────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        {/* ── Breadcrumb ─────────────────────────────────────────────── */}
        <div className="flex items-center gap-2 text-sm text-gray-400 mb-8">
          <Link href="/agents" className="hover:text-emerald-600 transition-colors">
            Agents
          </Link>
          <span>/</span>
          <span className="text-gray-600 truncate">{agent.full_name}</span>
        </div>

        {/* ── Header card ────────────────────────────────────────────── */}
        <Card className="mb-8">
          <div className="flex flex-col sm:flex-row items-start gap-6">
            {/* Avatar */}
            <div className="w-20 h-20 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
              {agent.avatar_url ? (
                <img
                  src={agent.avatar_url}
                  alt={agent.full_name}
                  className="w-full h-full rounded-2xl object-cover"
                />
              ) : (
                <span className="text-emerald-700 font-bold text-2xl">
                  {initials}
                </span>
              )}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-3 mb-2">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-900">
                  {agent.full_name}
                </h1>
                {agent.badge_level && (
                  <span
                    className={`inline-block text-xs px-2.5 py-0.5 rounded-full font-medium ${
                      BADGE_COLORS[agent.badge_level] ||
                      'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {agent.badge_level.toUpperCase()} VERIFIED
                  </span>
                )}
              </div>

              <p className="text-lg text-gray-500 mb-3">
                {agent.agency_name || 'Independent Agent'}
              </p>

              <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500">
                <div className="flex items-center gap-1.5">
                  <Award className="w-4 h-4 text-amber-500" />
                  <span>{agent.years_experience} years experience</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <Clock className="w-4 h-4 text-gray-400" />
                  <span>Member since {memberSinceYear}</span>
                </div>
                <Badge
                  variant={
                    (
                      {
                        premium: 'purple',
                        pro: 'info',
                        basic: 'default',
                      } as Record<string, 'purple' | 'info' | 'default'>
                    )[agent.subscription_tier] || 'default'
                  }
                >
                  {agent.subscription_tier.charAt(0).toUpperCase() +
                    agent.subscription_tier.slice(1)}{' '}
                  Tier
                </Badge>
              </div>

              {/* Bio */}
              {agent.bio && (
                <p className="text-gray-600 mt-4 leading-relaxed max-w-3xl">
                  {agent.bio}
                </p>
              )}
            </div>
          </div>
        </Card>

        {/* ── Stats row ──────────────────────────────────────────────── */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
          <Card padding="sm" className="text-center">
            <div className="flex items-center justify-center gap-1 mb-1">
              {renderStars(agent.rating)}
            </div>
            <p className="text-2xl font-bold text-gray-900">
              {agent.rating.toFixed(1)}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">Rating</p>
          </Card>

          <Card padding="sm" className="text-center">
            <Home className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-900">
              {agent.total_listings}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">Total Listings</p>
          </Card>

          <Card padding="sm" className="text-center">
            <CheckCircle className="w-5 h-5 text-emerald-500 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-900">
              {agent.successful_deals}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">Successful Deals</p>
          </Card>

          <Card padding="sm" className="text-center">
            <MapPin className="w-5 h-5 text-blue-500 mx-auto mb-1" />
            <p className="text-2xl font-bold text-gray-900 truncate">
              {agent.location || 'Kenya'}
            </p>
            <p className="text-xs text-gray-400 mt-0.5">Location</p>
          </Card>
        </div>

        {/* ── Two-column layout ──────────────────────────────────────── */}
        <div className="grid lg:grid-cols-3 gap-8 mb-8">
          {/* Left column — Specializations + License */}
          <div className="lg:col-span-1 space-y-6">
            {/* Specializations */}
            <Card>
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Specializations
              </h2>
              {agent.specialization.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {agent.specialization.map((s) => (
                    <span
                      key={s}
                      className="inline-block text-sm bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full capitalize border border-emerald-200"
                    >
                      {s.replace(/_/g, ' ')}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-gray-400">
                  No specializations listed
                </p>
              )}
            </Card>

            {/* License & Verification */}
            <Card>
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                <ShieldCheck className="w-5 h-5 text-emerald-500" />
                License &amp; Verification
              </h2>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">EARB License</span>
                  <span className="text-sm font-medium text-gray-900">
                    {agent.license_number || (
                      <span className="text-gray-400">Not provided</span>
                    )}
                  </span>
                </div>
                <div className="border-t border-gray-100 pt-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    <span className="text-sm text-gray-600">
                      {agent.badge_level
                        ? `${agent.badge_level.charAt(0).toUpperCase() + agent.badge_level.slice(1)}-verified agent`
                        : 'Identity verified'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 mt-2">
                    <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                    <span className="text-sm text-gray-600">
                      Email confirmed
                    </span>
                  </div>
                  {agent.phone && (
                    <div className="flex items-center gap-2 mt-2">
                      <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0" />
                      <span className="text-sm text-gray-600">
                        Phone verified
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* Right column — Recent Listings */}
          <div className="lg:col-span-2">
            <Card>
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-lg font-semibold text-gray-900">
                  Recent Listings
                </h2>
                <span className="text-xs text-gray-400">
                  {recentListings.length} property
                  {recentListings.length !== 1 ? 'ies' : 'y'}
                </span>
              </div>

              {listingsLoading ? (
                <div className="flex justify-center py-12">
                  <Spinner size="md" />
                </div>
              ) : recentListings.length === 0 ? (
                <div className="text-center py-12">
                  <Home className="w-12 h-12 text-gray-200 mx-auto mb-3" />
                  <p className="text-gray-400 text-sm">
                    No listings from this agent yet
                  </p>
                </div>
              ) : (
                <div className="grid sm:grid-cols-2 gap-4">
                  {recentListings.map((listing) => (
                    <Link key={listing.id} href={`/properties/${listing.id}`}>
                      <div className="group border border-gray-100 rounded-2xl overflow-hidden hover:shadow-md transition-all duration-200 hover:-translate-y-0.5 bg-white">
                        {/* Image */}
                        <div className="h-36 bg-gray-100 relative overflow-hidden">
                          {listing.images && listing.images.length > 0 ? (
                            <img
                              src={listing.images[0]}
                              alt={listing.title}
                              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            />
                          ) : (
                            <div className="flex items-center justify-center h-full">
                              <Home className="w-8 h-8 text-gray-300" />
                            </div>
                          )}
                          {/* Trust score badge */}
                          {listing.trust_score != null && (
                            <span
                              className={`absolute top-2 right-2 text-xs font-medium px-2 py-0.5 rounded-full border ${getTrustScoreBg(listing.trust_score)}`}
                            >
                              Trust {listing.trust_score}
                            </span>
                          )}
                        </div>

                        {/* Details */}
                        <div className="p-3">
                          <p className="font-semibold text-gray-900 text-sm truncate group-hover:text-emerald-600 transition-colors">
                            {listing.title}
                          </p>
                          <div className="flex items-center gap-1 text-xs text-gray-400 mt-1">
                            <MapPin className="w-3 h-3" />
                            <span>{listing.city}</span>
                          </div>
                          <p className="text-emerald-600 font-bold text-sm mt-1.5">
                            {formatCurrency(listing.price)}
                          </p>
                          <p className="text-xs text-gray-400 mt-1">
                            {formatRelativeTime(listing.created_at)}
                          </p>
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </Card>
          </div>
        </div>

        {/* ── Contact section ─────────────────────────────────────────── */}
        <Card>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-gray-900 mb-1">
                Get in Touch
              </h2>
              <p className="text-sm text-gray-500">
                Interested in working with {agent.full_name.split(' ')[0]}?
                Send a message or give them a call.
              </p>
            </div>
            <div className="flex items-center gap-3">
              {agent.phone && (
                <a href={`tel:${agent.phone}`}>
                  <Button
                    variant="outline"
                    leftIcon={<Phone className="w-4 h-4" />}
                  >
                    {agent.phone}
                  </Button>
                </a>
              )}
              <a href={`mailto:${agent.email}`}>
                <Button
                  variant="outline"
                  leftIcon={<Mail className="w-4 h-4" />}
                >
                  Email
                </Button>
              </a>
              <Link href={`/messages?agent=${agent.user_id}`}>
                <Button leftIcon={<MessageSquare className="w-4 h-4" />}>
                  Send Message
                </Button>
              </Link>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
