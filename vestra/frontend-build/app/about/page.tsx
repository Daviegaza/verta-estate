'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/card';
import { ShieldCheck, Users, Building2, Target, Heart, Award, ArrowRight, MapPin, Quote, ChevronRight } from 'lucide-react';

const STATS = [
  { value: '2024', label: 'Founded' },
  { value: '50K+', label: 'Properties Listed' },
  { value: '98%', label: 'Verification Accuracy' },
  { value: '10K+', label: 'Trusted Users' },
  { value: '47', label: 'Counties Covered' },
  { value: '24/7', label: 'AI Support' },
];

const VALUES = [
  {
    icon: ShieldCheck,
    title: 'Trust First',
    description: 'Every transaction on Vestra is backed by rigorous verification. We never compromise on trust.',
    color: 'text-emerald-600 bg-emerald-50',
  },
  {
    icon: Target,
    title: 'Radical Transparency',
    description: 'No hidden fees, no fake listings, no fine print. What you see is exactly what you get.',
    color: 'text-blue-600 bg-blue-50',
  },
  {
    icon: Heart,
    title: 'Built for Kenya',
    description: 'From M-Pesa to Swahili support, every feature is designed for the Kenyan market.',
    color: 'text-red-600 bg-red-50',
  },
  {
    icon: Users,
    title: 'Community First',
    description: 'We empower local agents, landlords, and buyers with tools that level the playing field.',
    color: 'text-purple-600 bg-purple-50',
  },
  {
    icon: Award,
    title: 'Excellence',
    description: 'Our AI-driven verification sets the gold standard for property trust in emerging markets.',
    color: 'text-amber-600 bg-amber-50',
  },
  {
    icon: Building2,
    title: 'Innovation',
    description: 'Continuous improvement through AI, blockchain-ready architecture, and user feedback.',
    color: 'text-teal-600 bg-teal-50',
  },
];

const TIMELINE = [
  { year: '2024 Q1', title: 'The Idea', description: 'Founders identify property fraud as Kenya\'s biggest real estate problem after losing KES 500K to a fake listing.' },
  { year: '2024 Q2', title: 'MVP Launch', description: 'Vestra launches with AI verification for Nairobi properties. 500 users in first month.' },
  { year: '2024 Q3', title: 'M-Pesa Integration', description: 'STK Push payments go live. Verification time drops from 24hrs to 5 minutes.' },
  { year: '2024 Q4', title: '50K Properties', description: 'Scale to 47 counties. 50K+ properties listed. 98% verification accuracy achieved.' },
  { year: '2025 Q1', title: 'Agent Network', description: 'Verified Agent program launches. 500+ agents onboarded across Kenya.' },
  { year: '2025 Q2', title: 'Rental Management', description: 'End-to-end rental platform: listings, payments, tenant management, maintenance.' },
  { year: '2025 Q3', title: 'Enterprise API', description: 'Enterprise-grade API for banks, developers, and large property portfolios.' },
  { year: '2026', title: 'Africa Expansion', description: 'Vestra begins expansion into Nigeria, Ghana, and South Africa.' },
];

const TEAM_MEMBERS = [
  { name: 'Kevin Ochieng', role: 'CEO & Co-Founder', initials: 'KO' },
  { name: 'Wanjiku Mwangi', role: 'CTO & Co-Founder', initials: 'WM' },
  { name: 'Hassan Ali', role: 'Head of Product', initials: 'HA' },
  { name: 'Grace Akinyi', role: 'Head of Operations', initials: 'GA' },
];

export default function AboutPage() {
  useEffect(() => {
    document.title = 'About Us — Vestra | AI-Powered Property Trust Platform | Kenya';
  }, []);

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-gray-950 via-gray-900 to-emerald-950 text-white">
        <div className="absolute inset-0 overflow-hidden pointer-events-none">
          <div className="absolute -top-20 -right-20 w-72 h-72 bg-emerald-500/5 rounded-full blur-3xl animate-float" />
          <div className="absolute top-1/3 -left-20 w-96 h-96 bg-emerald-400/5 rounded-full blur-3xl animate-float" style={{ animationDelay: '2s' }} />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-24 lg:py-32">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 rounded-full px-4 py-1.5 mb-6 animate-fade-in-down">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-emerald-300 text-sm font-medium">Our Story</span>
            </div>
            <h1 className="text-5xl lg:text-7xl font-bold leading-tight mb-6 animate-fade-in-up">
              Building Trust in
              <span className="text-emerald-400"> African Real Estate</span>
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-8 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Vestra was born from a painful personal experience with property fraud. Today, we are on a mission
              to make every property transaction in Africa transparent, secure, and trustworthy.
            </p>
            <div className="flex flex-wrap gap-4 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              <Link href="/market">
                <Button size="lg" className="bg-emerald-500 hover:bg-emerald-400 gap-2">
                  Explore Properties
                  <ArrowRight className="w-5 h-5" />
                </Button>
              </Link>
              <Link href="/contact">
                <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10 gap-2">
                  Get in Touch
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Mission & Vision */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <div className="grid md:grid-cols-2 gap-12 items-center">
          <div>
            <Badge variant="success" className="mb-4">Our Mission</Badge>
            <h2 className="text-4xl font-bold text-gray-900 mb-6">Making Property Trustworthy for Every African</h2>
            <p className="text-gray-600 leading-relaxed mb-4">
              Property fraud costs Kenyans billions of shillings every year. Fake listings, forged title deeds,
              and phantom agents are everyday realities in our market. Vestra exists to change that.
            </p>
            <p className="text-gray-600 leading-relaxed mb-4">
              Our AI-powered platform verifies every property, agent, and transaction — giving buyers and
              tenants the confidence they deserve. We believe access to trusted property information is not
              a luxury, it is a right.
            </p>
            <p className="text-gray-600 leading-relaxed">
              From M-Pesa integration to Swahili language support, every feature is built specifically for
              the Kenyan and broader African market.
            </p>
          </div>
          <div className="bg-gradient-to-br from-emerald-500 to-emerald-800 rounded-3xl p-10 text-white">
            <div className="mb-6">
              <div className="w-14 h-14 bg-white/20 rounded-2xl flex items-center justify-center mb-4">
                <Target className="w-7 h-7" />
              </div>
              <h3 className="text-2xl font-bold mb-3">Our Vision</h3>
              <p className="text-emerald-100 leading-relaxed">
                A Africa where every property transaction is transparent, every listing is verified,
                and every user — whether buyer, seller, agent, or landlord — can participate with
                complete confidence and trust.
              </p>
            </div>
            <div className="border-t border-white/20 pt-6 mt-6">
              <div className="flex items-center gap-4 mb-3">
                <MapPin className="w-5 h-5 text-emerald-300" />
                <span className="text-sm text-emerald-100">Headquarters: Nairobi, Kenya</span>
              </div>
              <div className="flex items-center gap-4">
                <Users className="w-5 h-5 text-emerald-300" />
                <span className="text-sm text-emerald-100">Serving 47 counties across Kenya</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="bg-gray-50 border-y border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold text-gray-900 mb-2">Vestra by the Numbers</h2>
            <p className="text-gray-500">Our impact across Kenya since day one</p>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-6 stagger-fade-in">
            {STATS.map((stat) => (
              <div key={stat.label} className="text-center bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md transition-shadow">
                <p className="text-3xl font-bold text-emerald-600">{stat.value}</p>
                <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Values */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <div className="text-center mb-16">
          <Badge variant="info" className="mb-4">Our Values</Badge>
          <h2 className="text-4xl font-bold text-gray-900 mb-4">What Drives Us</h2>
          <p className="text-gray-500 max-w-2xl mx-auto">Core principles that guide every decision we make at Vestra</p>
        </div>
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-fade-in">
          {VALUES.map((value) => (
            <div key={value.title} className="bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200">
              <div className={"inline-flex p-3 rounded-xl mb-4 " + value.color}>
                <value.icon className="w-6 h-6" />
              </div>
              <h3 className="text-lg font-semibold text-gray-900 mb-2">{value.title}</h3>
              <p className="text-gray-500 text-sm leading-relaxed">{value.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Timeline */}
      <section className="bg-gray-50 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6">
          <div className="text-center mb-16">
            <Badge variant="warning" className="mb-4">Our Journey</Badge>
            <h2 className="text-4xl font-bold text-gray-900 mb-4">The Vestra Timeline</h2>
            <p className="text-gray-500 max-w-2xl mx-auto">From a painful personal loss to Africa trusted property platform</p>
          </div>
          <div className="relative">
            {/* Timeline line */}
            <div className="absolute left-8 md:left-1/2 top-0 bottom-0 w-0.5 bg-emerald-200 -translate-x-1/2 hidden md:block" />
            <div className="space-y-12">
              {TIMELINE.map((item, index) => (
                <div key={item.year} className={`relative flex flex-col md:flex-row gap-6 md:gap-12 items-start ${index % 2 === 0 ? 'md:flex-row' : 'md:flex-row-reverse'}`}>
                  {/* Timeline dot */}
                  <div className="absolute left-8 md:left-1/2 w-4 h-4 bg-emerald-600 rounded-full border-4 border-emerald-100 -translate-x-1/2 mt-1.5 hidden md:block z-10" />
                  {/* Mobile dot */}
                  <div className="flex md:hidden items-center gap-4">
                    <div className="w-4 h-4 bg-emerald-600 rounded-full border-4 border-emerald-100 flex-shrink-0" />
                  </div>
                  {/* Content */}
                  <div className={`flex-1 ${index % 2 === 0 ? 'md:text-right md:pr-12' : 'md:text-left md:pl-12'}`}>
                    <span className="inline-block text-sm font-bold text-emerald-600 bg-emerald-50 px-3 py-1 rounded-full mb-2">
                      {item.year}
                    </span>
                    <h3 className="text-xl font-bold text-gray-900 mb-2">{item.title}</h3>
                    <p className="text-gray-600 leading-relaxed">{item.description}</p>
                  </div>
                  {/* Spacer for alternating layout */}
                  <div className="hidden md:block flex-1" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Team */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-24">
        <div className="text-center mb-16">
          <Badge className="mb-4">Leadership</Badge>
          <h2 className="text-4xl font-bold text-gray-900 mb-4">Meet Our Team</h2>
          <p className="text-gray-500 max-w-2xl mx-auto">The people building Africa most trusted property platform</p>
        </div>
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-6 stagger-fade-in">
          {TEAM_MEMBERS.map((member) => (
            <div key={member.name} className="bg-white rounded-2xl border border-gray-100 p-8 text-center hover:shadow-md hover:-translate-y-1 transition-all duration-200">
              <div className="w-20 h-20 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-lg">
                <span className="text-white font-bold text-2xl">{member.initials}</span>
              </div>
              <h3 className="text-lg font-semibold text-gray-900">{member.name}</h3>
              <p className="text-sm text-gray-500 mt-1">{member.role}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section className="relative overflow-hidden bg-gradient-to-br from-emerald-600 to-emerald-800 py-20">
        <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZGVmcz48cGF0dGVybiBpZD0iZ3JpZCIgd2lkdGg9IjYwIiBoZWlnaHQ9IjYwIiBwYXR0ZXJuVW5pdHM9InVzZXJTcGFjZU9uVXNlIj48cGF0aCBkPSJNIDYwIDAgTCAwIDAgMCA2MCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ3aGl0ZSIgc3Ryb2tlLW9wYWNpdHk9IjAuMSIgc3Ryb2tlLXdpZHRoPSIxIi8+PC9wYXR0ZXJuPjwvZGVmcz48cmVjdCB3aWR0aD0iMTAwJSIgaGVpZ2h0PSIxMDAlIiBmaWxsPSJ1cmwoI2dyaWQpIi8+PC9zdmc+')] opacity-10" />
        <div className="relative max-w-4xl mx-auto text-center px-4">
          <h2 className="text-4xl font-bold text-white mb-4">Join Us in Building Trust</h2>
          <p className="text-emerald-100 text-lg mb-8">
            Whether you are buying, selling, or investing — Vestra is your trusted partner in African real estate.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/auth/register">
              <Button size="lg" className="bg-white text-emerald-700 hover:bg-emerald-50 font-semibold">Get Started Free</Button>
            </Link>
            <Link href="/contact">
              <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10">Contact Us</Button>
            </Link>
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
