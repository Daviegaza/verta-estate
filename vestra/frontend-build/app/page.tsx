'use client';

import Link from 'next/link';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import {
  ShieldCheck, Search, TrendingUp, Users, CheckCircle,
  ArrowRight, Star, MapPin, Zap, Building2, Lock, Smartphone
} from 'lucide-react';

const STATS = [
  { value: '50K+', label: 'Properties Listed' },
  { value: '98%', label: 'Verified Listings' },
  { value: 'KES 0', label: 'Hidden Fees' },
  { value: '24/7', label: 'AI Support' },
];

const FEATURES = [
  {
    icon: 'shield',
    title: 'AI Property Verification',
    description: 'Every property gets a Trust Score from our AI. Know before you buy — ownership, documents, price fairness.',
    color: 'text-emerald-600 bg-emerald-50',
  },
  {
    icon: 'search',
    title: 'Natural Language Search',
    description: 'Just type "2-bedroom in Karen under KES 50k" and our AI finds the perfect match instantly.',
    color: 'text-blue-600 bg-blue-50',
  },
  {
    icon: 'lock',
    title: 'Fraud Detection',
    description: 'Advanced AI detects fake listings, duplicate properties, suspicious agents before you lose money.',
    color: 'text-purple-600 bg-purple-50',
  },
  {
    icon: 'trend',
    title: 'Smart Valuation',
    description: 'Instant AI-powered property valuation. Know the market price, rental yield, and growth forecast.',
    color: 'text-amber-600 bg-amber-50',
  },
  {
    icon: 'zap',
    title: 'M-Pesa Integration',
    description: 'Pay for verifications, deposits, and rent using M-Pesa — the way Kenya moves money.',
    color: 'text-red-600 bg-red-50',
  },
  {
    icon: 'building',
    title: 'Property Management',
    description: 'Manage tenants, collect rent, track maintenance — all in one platform built for Kenyan landlords.',
    color: 'text-teal-600 bg-teal-50',
  },
];

const TESTIMONIALS = [
  { name: 'James Mwangi', role: 'Property Buyer, Nairobi', text: 'I was about to buy a plot in Kitengela that turned out to be fraudulent. Vestra flagged it with 91% risk score. Saved me KES 2.5 million.', rating: 5 },
  { name: 'Sarah Odhiambo', role: 'Landlord, Mombasa', text: 'Managing 12 rental units used to be chaotic. With Vestra, I collect rent via M-Pesa, track everything, and have not had a bad tenant since.', rating: 5 },
  { name: 'David Kimani', role: 'Real Estate Agent, Nairobi', text: 'My Vestra Verified badge has increased my client trust massively. I close deals 3x faster now because buyers trust my listings.', rating: 5 },
];

const HOW_IT_WORKS = [
  { step: '01', title: 'Enter Property', desc: 'Input the property address or listing you want to verify.' },
  { step: '02', title: 'Upload Documents', desc: 'Upload title deed, sale agreement, or any available documents.' },
  { step: '03', title: 'Pay via M-Pesa', desc: 'Pay KES 500 verification fee via M-Pesa STK Push instantly.' },
  { step: '04', title: 'Get Trust Report', desc: 'Receive detailed AI analysis with Trust Score, flags, and recommendation.' },
];

const POPULAR_SEARCHES = [
  '2 bedroom in Westlands under 50k',
  'Apartments in Kilimani',
  'Land for sale in Karen',
  'Houses in Mombasa',
  'Studio in Nairobi under 20k',
];

export default function HomePage() {
  const router = useRouter();
  const [aiQuery, setAiQuery] = useState('');
  const [isFocused, setIsFocused] = useState(false);

  const suggestions = aiQuery.trim()
    ? POPULAR_SEARCHES.filter((s) =>
        s.toLowerCase().includes(aiQuery.toLowerCase())
      )
    : POPULAR_SEARCHES;

  const handleAiSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (aiQuery.trim()) {
      router.push('/market?q=' + encodeURIComponent(aiQuery) + '&ai=1');
    }
  };

  const selectSuggestion = (suggestion: string) => {
    setAiQuery(suggestion);
    setIsFocused(false);
    router.push('/market?q=' + encodeURIComponent(suggestion) + '&ai=1');
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 text-white">
        {/* Floating background decorations */}
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -right-20 w-72 h-72 bg-emerald-500/5 rounded-full blur-3xl animate-float" />
          <div className="absolute top-1/3 -left-20 w-96 h-96 bg-emerald-400/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
          <div className="absolute bottom-10 right-1/4 w-48 h-48 bg-emerald-300/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '4s' }} />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-24 lg:py-32">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 rounded-full px-4 py-1.5 mb-6 animate-fade-in-down">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-emerald-300 text-sm font-medium">Africa Number 1 Trusted Property Platform</span>
            </div>
            <h1 className="text-5xl lg:text-7xl font-bold leading-tight mb-6 animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
              Trust Every
              <span className="text-emerald-400"> Property.</span>
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-10 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Stop losing money to fake listings and property fraud. Vestra AI verifies ownership,
              detects scams, and gives every property a Trust Score before you pay a single shilling.
            </p>
            <form onSubmit={handleAiSearch} className="mb-8 animate-fade-in-up relative" style={{ animationDelay: '0.3s' }}>
              <div className="flex gap-2 bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-2">
                <Search className="w-5 h-5 text-gray-400 ml-2 flex-shrink-0 self-center" />
                <input
                  type="text"
                  value={aiQuery}
                  onChange={(e) => setAiQuery(e.target.value)}
                  onFocus={() => setIsFocused(true)}
                  onBlur={() => setTimeout(() => setIsFocused(false), 200)}
                  placeholder="Try: 2 bedroom apartment in Westlands under KES 40,000..."
                  className="flex-1 bg-transparent text-white placeholder:text-gray-400 text-sm outline-none py-2"
                />
                <button
                  type="submit"
                  className="bg-emerald-500 hover:bg-emerald-400 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors flex-shrink-0"
                >
                  Search with AI
                </button>
              </div>

              {/* Search suggestions dropdown */}
              {isFocused && suggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-700 overflow-hidden z-50 animate-scale-in">
                  {!aiQuery.trim() && (
                    <div className="px-4 pt-3 pb-1 text-xs text-gray-400 font-medium uppercase tracking-wider">
                      Popular searches
                    </div>
                  )}
                  <div className="py-1">
                    {suggestions.map((suggestion) => (
                      <button
                        key={suggestion}
                        type="button"
                        onMouseDown={() => selectSuggestion(suggestion)}
                        className="w-full text-left px-4 py-2.5 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                      >
                        <Search className="w-4 h-4 text-gray-300 flex-shrink-0" />
                        <span className="text-sm text-gray-700 dark:text-gray-300">{suggestion}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </form>
            <div className="flex flex-wrap gap-4 animate-fade-in-up" style={{ animationDelay: '0.4s' }}>
              <Link href="/market">
                <Button size="lg" className="bg-emerald-500 hover:bg-emerald-400 gap-2">
                  Browse Properties
                  <ArrowRight className="w-5 h-5" />
                </Button>
              </Link>
              <Link href="/verify">
                <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10 hover:text-white gap-2">
                  <ShieldCheck className="w-5 h-5" />
                  Verify a Property
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-8 stagger-fade-in">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-4xl font-bold text-gray-900"><span className="count-up">{stat.value}</span></p>
                <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Why Kenyans Trust Vestra</h2>
          <p className="text-xl text-gray-500 max-w-2xl mx-auto">Built for Kenya. Designed for Africa. Ready for the world.</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-fade-in">
          {FEATURES.map((feature) => {
            const IconComponent = {
              shield: ShieldCheck,
              search: Search,
              lock: Lock,
              trend: TrendingUp,
              zap: Zap,
              building: Building2,
            }[feature.icon] || ShieldCheck;
            return (
              <div key={feature.title} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
                <div className={"inline-flex p-3 rounded-xl mb-4 " + feature.color}>
                  <IconComponent className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">{feature.title}</h3>
                <p className="text-gray-500 text-sm leading-relaxed">{feature.description}</p>
              </div>
            );
          })}
        </div>
      </section>

      {/* How it works */}
      <section className="bg-gray-50 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">How Vestra Verify Works</h2>
            <p className="text-gray-500">Get a full property trust report in under 5 minutes</p>
          </div>
          <div className="grid md:grid-cols-4 gap-6 stagger-fade-in">
            {HOW_IT_WORKS.map((item) => (
              <div key={item.step} className="bg-white rounded-2xl border border-gray-100 p-6">
                <div className="w-12 h-12 bg-emerald-600 rounded-xl flex items-center justify-center mb-4">
                  <span className="text-white font-bold text-sm">{item.step}</span>
                </div>
                <h3 className="font-semibold text-gray-900 mb-2">{item.title}</h3>
                <p className="text-sm text-gray-500">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <div className="text-center mb-16">
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Trusted by Kenyans</h2>
          <p className="text-gray-500">Real people. Real properties. Real peace of mind.</p>
        </div>
        <div className="grid md:grid-cols-3 gap-6 stagger-fade-in">
          {TESTIMONIALS.map((t) => (
            <div key={t.name} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
              <div className="flex gap-1 mb-4">
                {Array.from({ length: t.rating }).map((_, i) => (
                  <Star key={i} className="w-4 h-4 text-amber-400 fill-amber-400" />
                ))}
              </div>
              <p className="text-gray-700 text-sm leading-relaxed mb-6">"{t.text}"</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-emerald-100 rounded-full flex items-center justify-center">
                  <span className="text-emerald-700 font-semibold">{t.name[0]}</span>
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">{t.name}</p>
                  <p className="text-xs text-gray-500">{t.role}</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-600 to-emerald-800 py-20">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZ3JpZCIgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDYwIDAgTCAwIDAgMCA2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-10" />
        <div className="relative max-w-4xl mx-auto text-center px-4">
          <h2 className="text-4xl font-bold text-white mb-4">Ready to Trust Every Property?</h2>
          <p className="text-emerald-100 text-lg mb-8">Join 50,000+ Kenyans using Vestra to buy, sell, and rent with confidence.</p>
          <div className="flex gap-4 justify-center">
            <Link href="/auth/register"><Button size="lg" className="bg-white text-emerald-700 hover:bg-emerald-50 font-semibold">Get Started Free</Button></Link>
            <Link href="/verify"><Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10">Verify Property</Button></Link>
          </div>
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
                { label: 'About Us', href: '/#about' },
                { label: 'Agents', href: '/agents' },
                { label: 'Enterprise API', href: '/enterprise' },
                { label: 'Dashboard', href: '/dashboard' },
              ]},
              { title: 'Support', links: [
                { label: 'Help Center', href: '/#faq' },
                { label: 'Contact Us', href: 'mailto:support@vestra.co.ke' },
                { label: 'Privacy Policy', href: '/#privacy' },
                { label: 'Terms of Service', href: '/#terms' },
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
