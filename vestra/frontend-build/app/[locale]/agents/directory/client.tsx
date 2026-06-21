'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Card, Badge, StatCard } from '@/components/ui/card';
import {
  ShieldCheck, Search, MapPin, Star, Phone, Mail, ChevronRight,
  Filter, SlidersHorizontal, X, CheckCircle, Award, Users,
  ChevronDown, Grid3X3, List, UserCheck
} from 'lucide-react';

const AGENT_SPECIALTIES = [
  'All Specialties',
  'Residential Sales',
  'Commercial Leasing',
  'Land & Plots',
  'Rental Management',
  'Property Valuation',
  'Luxury Properties',
  'Student Housing',
];

const AGENTS = [
  {
    id: 1,
    name: 'James Mwangi',
    company: 'Prime Properties Ltd',
    location: 'Nairobi, Westlands',
    specialty: 'Residential Sales',
    rating: 4.9,
    reviewCount: 127,
    phone: '+254 712 345 678',
    email: 'james.mwangi@primepropertes.co.ke',
    verified: true,
    badge: 'platinum',
    listings: 34,
    yearsActive: 8,
    image: 'JM',
  },
  {
    id: 2,
    name: 'Sarah Odhiambo',
    company: 'Coast Realty Ltd',
    location: 'Mombasa, Nyali',
    specialty: 'Commercial Leasing',
    rating: 4.8,
    reviewCount: 94,
    phone: '+254 723 456 789',
    email: 'sarah@coastrealty.co.ke',
    verified: true,
    badge: 'gold',
    listings: 28,
    yearsActive: 6,
    image: 'SO',
  },
  {
    id: 3,
    name: 'David Kimani',
    company: 'Kimani Properties',
    location: 'Nairobi, Kilimani',
    specialty: 'Land & Plots',
    rating: 4.7,
    reviewCount: 82,
    phone: '+254 734 567 890',
    email: 'david@kimani-properties.co.ke',
    verified: true,
    badge: 'gold',
    listings: 45,
    yearsActive: 10,
    image: 'DK',
  },
  {
    id: 4,
    name: 'Grace Akinyi',
    company: 'Lakeside Realty',
    location: 'Kisumu, CBD',
    specialty: 'Rental Management',
    rating: 4.9,
    reviewCount: 156,
    phone: '+254 745 678 901',
    email: 'grace@lakesiderealty.co.ke',
    verified: true,
    badge: 'platinum',
    listings: 52,
    yearsActive: 7,
    image: 'GA',
  },
  {
    id: 5,
    name: 'Peter Kamau',
    company: 'Cityscape Realtors',
    location: 'Nairobi, Upper Hill',
    specialty: 'Luxury Properties',
    rating: 4.6,
    reviewCount: 63,
    phone: '+254 756 789 012',
    email: 'peter@cityscape.co.ke',
    verified: true,
    badge: 'silver',
    listings: 19,
    yearsActive: 5,
    image: 'PK',
  },
  {
    id: 6,
    name: 'Faith Wanjiku',
    company: 'Wanjiku Real Estate',
    location: 'Nakuru, CBD',
    specialty: 'Residential Sales',
    rating: 4.8,
    reviewCount: 108,
    phone: '+254 767 890 123',
    email: 'faith@wanjikurealestate.co.ke',
    verified: true,
    badge: 'gold',
    listings: 31,
    yearsActive: 9,
    image: 'FW',
  },
  {
    id: 7,
    name: 'Hassan Ali',
    company: 'Coastline Properties',
    location: 'Mombasa, Diani',
    specialty: 'Land & Plots',
    rating: 4.5,
    reviewCount: 47,
    phone: '+254 778 901 234',
    email: 'hassan@coastline.co.ke',
    verified: true,
    badge: 'bronze',
    listings: 15,
    yearsActive: 4,
    image: 'HA',
  },
  {
    id: 8,
    name: 'Mary Chebet',
    company: 'Highland Realty',
    location: 'Eldoret, CBD',
    specialty: 'Property Valuation',
    rating: 4.7,
    reviewCount: 71,
    phone: '+254 789 012 345',
    email: 'mary@highlandrealty.co.ke',
    verified: true,
    badge: 'silver',
    listings: 22,
    yearsActive: 6,
    image: 'MC',
  },
];

function StarRating({ rating, size = 'sm' }: { rating: number; size?: 'sm' | 'md' }) {
  const sizeClass = size === 'sm' ? 'w-3.5 h-3.5' : 'w-5 h-5';
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: 5 }).map((_, i) => (
        <Star
          key={i}
          className={`${sizeClass} ${
            i < Math.floor(rating)
              ? 'text-amber-400 fill-amber-400'
              : i < rating
              ? 'text-amber-300 fill-amber-300'
              : 'text-gray-200 fill-gray-200'
          }`}
        />
      ))}
    </div>
  );
}

function BadgeIcon({ badge }: { badge: string }) {
  const colors: Record<string, string> = {
    platinum: 'text-purple-600',
    gold: 'text-yellow-600',
    silver: 'text-gray-500',
    bronze: 'text-orange-600',
  };
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-semibold ${colors[badge] || 'text-gray-500'}`}>
      <Award className="w-3.5 h-3.5" />
      {badge.charAt(0).toUpperCase() + badge.slice(1)}
    </span>
  );
}

export default function AgentsDirectoryPage() {
  useEffect(() => {
    document.title = 'Agents Directory — Vestra | Find Verified Agents in Kenya';
  }, []);

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedSpecialty, setSelectedSpecialty] = useState('All Specialties');
  const [showFilters, setShowFilters] = useState(false);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');

  const filteredAgents = AGENTS.filter((agent) => {
    const matchesSearch = searchQuery.trim()
      ? agent.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.company.toLowerCase().includes(searchQuery.toLowerCase()) ||
        agent.location.toLowerCase().includes(searchQuery.toLowerCase())
      : true;
    const matchesSpecialty = selectedSpecialty === 'All Specialties' || agent.specialty === selectedSpecialty;
    return matchesSearch && matchesSpecialty;
  });

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 text-white">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -right-20 w-72 h-72 bg-emerald-500/5 rounded-full blur-3xl animate-float" />
          <div className="absolute top-1/3 -left-20 w-96 h-96 bg-emerald-400/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-24 lg:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 rounded-full px-4 py-1.5 mb-6 animate-fade-in-down">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-emerald-300 text-sm font-medium">2,500+ Verified Agents</span>
            </div>
            <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6 animate-fade-in-up">
              Find a <span className="text-emerald-400">Verified Agent</span>
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-8 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Browse our directory of verified real estate agents across Kenya. Every agent has been vetted
              and approved to ensure you work with trusted professionals.
            </p>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <StatCard label="Verified Agents" value="2,500+" subtext="Across 47 counties" color="emerald" icon={<Users className="w-5 h-5" />} />
            <StatCard label="Properties Listed" value="50,000+" subtext="Sold & rented" color="blue" icon={<Building2Icon />} />
            <StatCard label="Avg Rating" value="4.8" subtext="From 10K+ reviews" color="amber" icon={<Star className="w-5 h-5" />} />
            <StatCard label="Closed Deals" value="15,000+" subtext="In 2026 alone" color="purple" icon={<CheckCircle className="w-5 h-5" />} />
          </div>
        </div>
      </section>

      {/* Search & Filter */}
      <div className="bg-white border-b border-gray-100 sticky top-16 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4">
          <div className="flex flex-col sm:flex-row gap-3">
            {/* Search */}
            <div className="flex-1 flex gap-2 bg-white border border-gray-200 rounded-xl p-2 focus-within:ring-2 focus-within:ring-emerald-500">
              <Search className="w-5 h-5 text-gray-400 ml-2 flex-shrink-0 self-center" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search by name, company, or location..."
                className="flex-1 bg-transparent text-gray-900 placeholder:text-gray-400 text-sm outline-none py-1"
              />
              {searchQuery && (
                <button onClick={() => setSearchQuery('')} className="p-1 text-gray-400 hover:text-gray-600">
                  <X className="w-4 h-4" />
                </button>
              )}
            </div>

            {/* View Toggle */}
            <div className="hidden sm:flex items-center bg-gray-100 rounded-xl p-1">
              <button
                onClick={() => setViewMode('grid')}
                className={`p-2 rounded-lg transition-colors ${viewMode === 'grid' ? 'bg-white shadow-sm text-emerald-600' : 'text-gray-400'}`}
              >
                <Grid3X3 className="w-4 h-4" />
              </button>
              <button
                onClick={() => setViewMode('list')}
                className={`p-2 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-white shadow-sm text-emerald-600' : 'text-gray-400'}`}
              >
                <List className="w-4 h-4" />
              </button>
            </div>

            {/* Filter Toggle */}
            <button
              onClick={() => setShowFilters(!showFilters)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-xl border text-sm font-medium transition-all ${
                showFilters || selectedSpecialty !== 'All Specialties'
                  ? 'bg-emerald-50 border-emerald-200 text-emerald-700'
                  : 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
              }`}
            >
              <SlidersHorizontal className="w-4 h-4" />
              Filters
              {selectedSpecialty !== 'All Specialties' && (
                <span className="w-5 h-5 bg-emerald-500 text-white text-xs rounded-full flex items-center justify-center">1</span>
              )}
            </button>
          </div>

          {/* Filter Panel */}
          {showFilters && (
            <div className="mt-4 p-4 bg-gray-50 rounded-2xl border border-gray-100 animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <span className="text-sm font-semibold text-gray-900">Specialty</span>
                {selectedSpecialty !== 'All Specialties' && (
                  <button
                    onClick={() => setSelectedSpecialty('All Specialties')}
                    className="text-xs text-emerald-600 hover:text-emerald-700"
                  >
                    Clear filter
                  </button>
                )}
              </div>
              <div className="flex flex-wrap gap-2">
                {AGENT_SPECIALTIES.map((specialty) => (
                  <button
                    key={specialty}
                    onClick={() => setSelectedSpecialty(specialty)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                      selectedSpecialty === specialty
                        ? 'bg-emerald-600 text-white'
                        : 'bg-white text-gray-600 border border-gray-200 hover:border-emerald-200 hover:text-emerald-600'
                    }`}
                  >
                    {specialty}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Agents */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <p className="text-sm text-gray-500">
            {filteredAgents.length} agent{filteredAgents.length !== 1 ? 's' : ''} found
          </p>
        </div>

        {filteredAgents.length > 0 ? (
          <div className={viewMode === 'grid'
            ? 'grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6'
            : 'space-y-4'
          }>
            {filteredAgents.map((agent) => (
              viewMode === 'grid' ? (
                <Card key={agent.id} className="p-6 hover:shadow-md transition-shadow">
                  {/* Header */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-14 h-14 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-2xl flex items-center justify-center shadow-sm">
                      <span className="text-white font-bold text-lg">{agent.image}</span>
                    </div>
                    <BadgeIcon badge={agent.badge} />
                  </div>

                  {/* Info */}
                  <h3 className="text-lg font-bold text-gray-900 mb-0.5">{agent.name}</h3>
                  <p className="text-sm text-gray-500 mb-2">{agent.company}</p>

                  <div className="flex items-center gap-1 mb-3">
                    <StarRating rating={agent.rating} />
                    <span className="text-sm font-semibold text-gray-700 ml-1">{agent.rating}</span>
                    <span className="text-xs text-gray-400">({agent.reviewCount})</span>
                  </div>

                  <div className="space-y-1.5 mb-4 text-sm">
                    <div className="flex items-center gap-2 text-gray-600">
                      <MapPin className="w-4 h-4 text-gray-400" />
                      {agent.location}
                    </div>
                    <div className="flex items-center gap-2 text-gray-600">
                      <CheckCircle className="w-4 h-4 text-emerald-500" />
                      {agent.specialty}
                    </div>
                    <div className="flex items-center gap-2 text-gray-600">
                      <Users className="w-4 h-4 text-gray-400" />
                      {agent.listings} listings
                    </div>
                  </div>

                  <div className="flex gap-2">
                    <Button variant="outline" size="sm" className="flex-1">
                      <Phone className="w-3.5 h-3.5" />
                      Call
                    </Button>
                    <Button variant="outline" size="sm" className="flex-1">
                      <Mail className="w-3.5 h-3.5" />
                      Email
                    </Button>
                  </div>
                </Card>
              ) : (
                <Card key={agent.id} className="p-5">
                  <div className="flex items-center gap-5">
                    <div className="w-14 h-14 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-2xl flex items-center justify-center flex-shrink-0">
                      <span className="text-white font-bold text-lg">{agent.image}</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <h3 className="text-lg font-bold text-gray-900">{agent.name}</h3>
                        <BadgeIcon badge={agent.badge} />
                        <div className="flex items-center gap-1">
                          <StarRating rating={agent.rating} />
                          <span className="text-sm font-semibold text-gray-700">{agent.rating}</span>
                          <span className="text-xs text-gray-400">({agent.reviewCount})</span>
                        </div>
                      </div>
                      <p className="text-sm text-gray-500">{agent.company} &middot; {agent.location} &middot; {agent.specialty}</p>
                    </div>
                    <div className="flex gap-2 flex-shrink-0">
                      <Button variant="outline" size="sm">
                        <Phone className="w-3.5 h-3.5" />
                      </Button>
                      <Button variant="outline" size="sm">
                        <Mail className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>
                </Card>
              )
            ))}
          </div>
        ) : (
          <div className="text-center py-16">
            <UserCheck className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No agents found</h3>
            <p className="text-gray-500 text-sm mb-6">
              Try adjusting your search or filter criteria.
            </p>
            <Button
              variant="outline"
              onClick={() => {
                setSearchQuery('');
                setSelectedSpecialty('All Specialties');
              }}
            >
              Clear Filters
            </Button>
          </div>
        )}
      </div>

      {/* CTA */}
      <section className="bg-gradient-to-br from-emerald-600 to-emerald-800 py-16">
        <div className="max-w-4xl mx-auto text-center px-4">
          <ShieldCheck className="w-12 h-12 text-white/80 mx-auto mb-4" />
          <h2 className="text-3xl font-bold text-white mb-3">Are You an Agent?</h2>
          <p className="text-emerald-100 text-lg mb-8 max-w-lg mx-auto">
            Get verified and join 2,500+ trusted real estate professionals using Vestra to grow their business.
          </p>
          <Link href="/auth/register?role=agent">
            <Button size="lg" className="bg-white text-emerald-700 hover:bg-emerald-50 font-semibold">
              Become a Verified Agent
            </Button>
          </Link>
        </div>
      </section>

      {/* Footer */}
      <footer className="bg-gray-950 text-gray-400 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="grid md:grid-cols-4 gap-8 mb-12">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <div className="w-8 h-8 bg-emerald-600 rounded-xl flex items-center justify-center">
                  <span className="text-white font-bold text-sm">V</span>
                </div>
                <span className="font-bold text-xl text-white">Vestra</span>
              </div>
              <p className="text-sm text-gray-500 leading-relaxed">
                Africa most trusted AI-powered property platform. Built in Kenya, for the world.
              </p>
            </div>
            {[
              { title: 'Platform', links: [
                { label: 'Browse Properties', href: '/market' },
                { label: 'Verify Property', href: '/verify' },
                { label: 'List Property', href: '/properties/new' },
                { label: 'AI Search', href: '/market?ai=1' },
              ]},
              { title: 'Company', links: [
                { label: 'About Us', href: '/about' },
                { label: 'Blog', href: '/blog' },
                { label: 'Contact', href: '/contact' },
                { label: 'FAQ', href: '/faq' },
              ]},
              { title: 'Support', links: [
                { label: 'Help Center', href: '/help' },
                { label: 'Privacy Policy', href: '/privacy' },
                { label: 'Terms of Service', href: '/terms' },
                { label: 'Agents Directory', href: '/agents/directory' },
              ]},
            ].map((col) => (
              <div key={col.title}>
                <h4 className="text-white font-semibold mb-4">{col.title}</h4>
                <ul className="space-y-2">
                  {col.links.map((link) => (
                    <li key={link.label}>
                      <Link href={link.href} className="text-sm text-gray-500 hover:text-white transition-colors">{link.label}</Link>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div className="border-t border-gray-800 pt-8 flex flex-col md:flex-row items-center justify-between gap-4">
            <p className="text-xs text-gray-600">&copy; 2026 Vestra Technologies Ltd. All rights reserved. Nairobi, Kenya.</p>
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-600" />
              <span className="text-xs text-gray-500">Secured and powered by AI</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

function Building2Icon() {
  return (
    <svg className="w-5 h-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="2" width="16" height="20" rx="2" ry="2" />
      <path d="M9 22v-4h6v4" />
      <path d="M8 6h.01" />
      <path d="M16 6h.01" />
      <path d="M8 10h.01" />
      <path d="M16 10h.01" />
      <path d="M8 14h.01" />
      <path d="M16 14h.01" />
    </svg>
  );
}
