'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/card';
import { ShieldCheck, Calendar, User, Clock, ArrowRight, ChevronRight, Search } from 'lucide-react';

const POSTS = [
  {
    slug: 'kenya-real-estate-market-trends-2026',
    title: 'Kenya Real Estate Market Trends 2026: What Buyers and Sellers Need to Know',
    excerpt: 'Comprehensive analysis of Kenya real estate market in 2026, including price trends, emerging neighborhoods, and investment opportunities across Nairobi, Mombasa, and Kisumu.',
    author: 'Kevin Ochieng',
    role: 'CEO & Co-Founder',
    date: 'June 15, 2026',
    readTime: '8 min read',
    category: 'Market Insights',
    color: 'bg-blue-50 text-blue-700 border-blue-200',
    imageColor: 'from-blue-400 to-blue-600',
    gradient: 'from-blue-500 to-blue-700',
  },
  {
    slug: 'how-to-verify-property-title-deed-kenya',
    title: 'How to Verify a Property Title Deed in Kenya: Complete Guide 2026',
    excerpt: 'Step-by-step guide on verifying property title deeds in Kenya. Learn how to check ownership, encumbrances, and avoid fraud using both traditional and AI-powered methods.',
    author: 'Wanjiku Mwangi',
    role: 'CTO & Co-Founder',
    date: 'June 10, 2026',
    readTime: '12 min read',
    category: 'Property Guides',
    color: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    imageColor: 'from-emerald-400 to-emerald-600',
    gradient: 'from-emerald-500 to-emerald-700',
  },
  {
    slug: 'ai-property-verification-how-it-works',
    title: 'AI Property Verification: How Vestra Detects Fraud in Minutes',
    excerpt: 'Behind the scenes of Vestra AI verification technology. Learn how machine learning, computer vision, and natural language processing work together to protect property buyers.',
    author: 'Kevin Ochieng',
    role: 'CEO & Co-Founder',
    date: 'June 5, 2026',
    readTime: '10 min read',
    category: 'Technology',
    color: 'bg-purple-50 text-purple-700 border-purple-200',
    imageColor: 'from-purple-400 to-purple-600',
    gradient: 'from-purple-500 to-purple-700',
  },
  {
    slug: 'rental-property-management-tips-kenya',
    title: 'Rental Property Management in Kenya: Tips for Landlords in 2026',
    excerpt: 'Essential tips for Kenyan landlords covering tenant screening, rent collection via M-Pesa, maintenance tracking, and legal requirements for residential rentals.',
    author: 'Grace Akinyi',
    role: 'Head of Operations',
    date: 'May 28, 2026',
    readTime: '7 min read',
    category: 'Landlord Tips',
    color: 'bg-amber-50 text-amber-700 border-amber-200',
    imageColor: 'from-amber-400 to-amber-600',
    gradient: 'from-amber-500 to-amber-700',
  },
  {
    slug: 'first-time-home-buyer-guide-kenya',
    title: 'First-Time Home Buyer Guide: Everything You Need to Know in Kenya',
    excerpt: 'A comprehensive guide for first-time home buyers in Kenya covering budget planning, mortgage options, property search, legal processes, and common pitfalls to avoid.',
    author: 'Hassan Ali',
    role: 'Head of Product',
    date: 'May 20, 2026',
    readTime: '15 min read',
    category: 'Buyer Guides',
    color: 'bg-red-50 text-red-700 border-red-200',
    imageColor: 'from-red-400 to-red-600',
    gradient: 'from-red-500 to-red-700',
  },
  {
    slug: 'mpesa-real-estate-payments-kenya',
    title: 'M-Pesa and Real Estate: How Digital Payments Are Transforming Property Transactions',
    excerpt: 'How M-Pesa integration is revolutionizing real estate payments in Kenya from deposits and rent to full property purchases. Security, convenience, and the future of property finance.',
    author: 'Wanjiku Mwangi',
    role: 'CTO & Co-Founder',
    date: 'May 15, 2026',
    readTime: '6 min read',
    category: 'Payments',
    color: 'bg-teal-50 text-teal-700 border-teal-200',
    imageColor: 'from-teal-400 to-teal-600',
    gradient: 'from-teal-500 to-teal-700',
  },
];

const CATEGORIES = [...new Set(POSTS.map((p) => p.category))];

export default function BlogPage() {
  useEffect(() => {
    document.title = 'Blog — Vestra | Real Estate Insights & Guides';
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
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-24 lg:py-28">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 rounded-full px-4 py-1.5 mb-6 animate-fade-in-down">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-emerald-300 text-sm font-medium">Insights & Guides</span>
            </div>
            <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6 animate-fade-in-up">
              Vestra Blog
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-4 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Expert insights, guides, and analysis on Kenya real estate market, property verification,
              and smart investing. Written by the team behind Vestra.
            </p>
          </div>
        </div>
      </section>

      {/* Categories */}
      <div className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex flex-wrap gap-2">
            <Badge variant="success" className="px-4 py-1.5">All Posts</Badge>
            {CATEGORIES.map((cat) => (
              <Badge key={cat} variant="default" className="px-4 py-1.5 cursor-pointer hover:bg-gray-200 transition-colors">
                {cat}
              </Badge>
            ))}
          </div>
        </div>
      </div>

      {/* Featured Post */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <Link
          href={`/blog/${POSTS[0].slug}`}
          className="group block relative overflow-hidden rounded-3xl bg-gradient-to-br from-gray-900 via-gray-800 to-gray-950 text-white mb-12 hover:shadow-xl transition-all duration-300"
        >
          <div className="absolute inset-0 bg-gradient-to-tr from-emerald-900/40 to-transparent" />
          <div className="relative p-8 md:p-12 lg:p-16">
            <Badge className={POSTS[0].color + ' mb-4'}>{POSTS[0].category}</Badge>
            <h2 className="text-3xl md:text-4xl font-bold mb-4 leading-tight group-hover:text-emerald-300 transition-colors">
              {POSTS[0].title}
            </h2>
            <p className="text-gray-300 text-lg leading-relaxed max-w-2xl mb-6">
              {POSTS[0].excerpt}
            </p>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-400 mb-6">
              <span className="flex items-center gap-1.5">
                <User className="w-4 h-4" />
                {POSTS[0].author}
              </span>
              <span className="flex items-center gap-1.5">
                <Calendar className="w-4 h-4" />
                {POSTS[0].date}
              </span>
              <span className="flex items-center gap-1.5">
                <Clock className="w-4 h-4" />
                {POSTS[0].readTime}
              </span>
            </div>
            <span className="inline-flex items-center gap-2 text-emerald-400 font-medium group-hover:gap-3 transition-all">
              Read Article
              <ArrowRight className="w-4 h-4" />
            </span>
          </div>
        </Link>

        {/* Post Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6 stagger-fade-in">
          {POSTS.slice(1).map((post) => (
            <Link
              key={post.slug}
              href={`/blog/${post.slug}`}
              className="group bg-white rounded-2xl border border-gray-100 overflow-hidden hover:shadow-lg hover:-translate-y-1 transition-all duration-200"
            >
              {/* Image placeholder */}
              <div className={`h-48 bg-gradient-to-br ${post.gradient} relative overflow-hidden`}>
                <div className="absolute inset-0 bg-black/10" />
                <div className="absolute bottom-4 left-4">
                  <Badge className={post.color}>{post.category}</Badge>
                </div>
              </div>
              <div className="p-6">
                <h3 className="font-bold text-gray-900 mb-2 line-clamp-2 group-hover:text-emerald-700 transition-colors">
                  {post.title}
                </h3>
                <p className="text-sm text-gray-500 leading-relaxed mb-4 line-clamp-3">
                  {post.excerpt}
                </p>
                <div className="flex items-center justify-between text-xs text-gray-400">
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-3.5 h-3.5" />
                    {post.date}
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5" />
                    {post.readTime}
                  </div>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Newsletter CTA */}
      <section className="bg-gray-50 py-16">
        <div className="max-w-3xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">Stay Updated</h2>
          <p className="text-gray-500 mb-8">
            Get the latest real estate insights, guides, and market analysis delivered to your inbox.
          </p>
          <div className="flex gap-3 max-w-md mx-auto">
            <input
              type="email"
              placeholder="Enter your email"
              className="flex-1 rounded-xl border border-gray-200 bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <Button>Subscribe</Button>
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
