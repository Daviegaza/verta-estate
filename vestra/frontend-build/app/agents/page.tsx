'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Card, Spinner, Badge } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import api from '@/lib/api';
import { KENYA_CITIES } from '@/lib/utils';
import { Search, ShieldCheck, Star, MapPin, Phone, Mail, Award } from 'lucide-react';

interface Agent {
  id: number;
  user_id: number;
  full_name: string;
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
}

const BADGE_COLORS: Record<string, string> = {
  platinum: 'bg-gray-900 text-white',
  gold: 'bg-amber-500 text-white',
  silver: 'bg-gray-300 text-gray-700',
  bronze: 'bg-amber-700 text-white',
};

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [city, setCity] = useState('');

  const loadAgents = async () => {
    try {
      const res = await api.client.get('/api/admin/users', {
        params: { role: 'agent', limit: 100 },
      });
      setAgents(res.data.items || []);
    } catch (err) {
      console.error('Failed to load agents:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAgents();
  }, []);

  const filtered = agents.filter((a) => {
    const matchesSearch = !search ||
      a.full_name.toLowerCase().includes(search.toLowerCase()) ||
      (a.agency_name || '').toLowerCase().includes(search.toLowerCase());
    const matchesCity = !city || (a.location || '').toLowerCase().includes(city.toLowerCase());
    return matchesSearch && matchesCity;
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Verified Real Estate Agents</h1>
          <p className="text-gray-500 max-w-2xl mx-auto">
            Work with trusted, verified agents across Kenya. Every agent with a badge has been vetted by VESTRA.
          </p>
        </div>

        {/* Search & Filter */}
        <div className="flex gap-3 mb-8 max-w-2xl mx-auto">
          <div className="flex-1">
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search agents by name or agency..."
              leftElement={<Search className="w-4 h-4" />}
            />
          </div>
          <select
            value={city}
            onChange={(e) => setCity(e.target.value)}
            className="border border-gray-200 rounded-xl px-3 py-2 text-sm bg-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
          >
            <option value="">All Cities</option>
            {KENYA_CITIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>

        {/* Results */}
        {loading ? (
          <div className="flex justify-center py-20"><Spinner size="lg" /></div>
        ) : filtered.length === 0 ? (
          <div className="text-center py-20">
            <ShieldCheck className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-gray-700 mb-2">No agents found</h3>
            <p className="text-gray-400">Try adjusting your search or check back later</p>
          </div>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filtered.map((agent) => (
              <Card key={agent.user_id} className="hover:shadow-md transition-shadow">
                <div className="flex items-start gap-4 mb-4">
                  <div className="w-14 h-14 bg-emerald-100 rounded-2xl flex items-center justify-center flex-shrink-0">
                    <span className="text-emerald-700 font-bold text-xl">
                      {agent.full_name.split(' ').map(n => n[0]).join('').slice(0, 2).toUpperCase()}
                    </span>
                  </div>
                  <div className="min-w-0">
                    <h3 className="font-semibold text-gray-900 truncate">{agent.full_name}</h3>
                    <p className="text-sm text-gray-500 truncate">{agent.agency_name || 'Independent Agent'}</p>
                    {agent.badge_level && (
                      <span className={`inline-block text-xs px-2 py-0.5 rounded-full mt-1 ${BADGE_COLORS[agent.badge_level] || 'bg-gray-100 text-gray-600'}`}>
                        {agent.badge_level.toUpperCase()} VERIFIED
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3 mb-4 text-sm">
                  <div className="flex items-center gap-1.5 text-gray-600">
                    <Award className="w-4 h-4 text-amber-500" />
                    <span>{agent.years_experience} yrs exp</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-gray-600">
                    <Star className="w-4 h-4 text-amber-400 fill-amber-400" />
                    <span>{agent.rating.toFixed(1)} rating</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-gray-600">
                    <ShieldCheck className="w-4 h-4 text-emerald-500" />
                    <span>{agent.successful_deals} deals</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-gray-600">
                    <MapPin className="w-4 h-4 text-blue-500" />
                    <span className="truncate">{agent.location || 'Kenya'}</span>
                  </div>
                </div>

                {agent.specialization.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mb-4">
                    {agent.specialization.slice(0, 3).map((s) => (
                      <span key={s} className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
                        {s.replace(/_/g, ' ')}
                      </span>
                    ))}
                  </div>
                )}

                <div className="flex gap-2">
                  <Link href={`/messages?agent=${agent.user_id}`} className="flex-1">
                    <Button size="sm" variant="outline" fullWidth leftIcon={<Mail className="w-3.5 h-3.5" />}>
                      Contact
                    </Button>
                  </Link>
                </div>
              </Card>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
