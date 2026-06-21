'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Card, Badge } from '@/components/ui/card';
import {
  ShieldCheck, Search, ChevronRight, HelpCircle, MessageCircle,
  BookOpen, UserCheck, CreditCard, Building2, FileText, Settings,
  ArrowRight, ExternalLink, LifeBuoy, FileQuestion, Phone
} from 'lucide-react';

const HELP_CATEGORIES = [
  {
    title: 'Getting Started',
    icon: BookOpen,
    description: 'New to Vestra? Start here to learn the basics.',
    color: 'text-emerald-600 bg-emerald-50',
    articles: [
      'Creating your Vestra account',
      'Completing your profile',
      'Navigating the dashboard',
      'Setting up M-Pesa payments',
      'Understanding Trust Scores',
    ],
  },
  {
    title: 'Property Listings',
    icon: Building2,
    description: 'Everything about listing and managing properties.',
    color: 'text-blue-600 bg-blue-50',
    articles: [
      'How to list a property',
      'Adding photos and documents',
      'Premium listing features',
      'Managing your listings',
      'Responding to inquiries',
    ],
  },
  {
    title: 'AI Verification',
    icon: ShieldCheck,
    description: 'How our AI verification works and how to use it.',
    color: 'text-purple-600 bg-purple-50',
    articles: [
      'What is AI verification?',
      'Uploading documents for verification',
      'Understanding your Trust Report',
      'Verification pricing and packages',
      'Disputing a Trust Score',
    ],
  },
  {
    title: 'Rentals',
    icon: CreditCard,
    description: 'Manage rental properties and payments.',
    color: 'text-amber-600 bg-amber-50',
    articles: [
      'Listing a rental property',
      'Collecting rent via M-Pesa',
      'Tenant management tools',
      'Maintenance request handling',
      'Lease agreement templates',
    ],
  },
  {
    title: 'Account & Billing',
    icon: Settings,
    description: 'Manage your account settings and subscription.',
    color: 'text-red-600 bg-red-50',
    articles: [
      'Account settings overview',
      'Subscription plans and pricing',
      'Payment history and invoices',
      'Cancelling your subscription',
      'Changing your payment method',
    ],
  },
  {
    title: 'Agent Resources',
    icon: UserCheck,
    description: 'Tools and guides for real estate agents.',
    color: 'text-teal-600 bg-teal-50',
    articles: [
      'Becoming a Verified Agent',
      'Agent dashboard guide',
      'Client management tips',
      'Agent analytics and reports',
      'Marketing your listings',
    ],
  },
  {
    title: 'Safety & Trust',
    icon: LifeBuoy,
    description: 'Stay safe on Vestra. Recognize and avoid scams.',
    color: 'text-rose-600 bg-rose-50',
    articles: [
      'Common property scams in Kenya',
      'How Vestra protects you',
      'Reporting suspicious activity',
      'Secure payment practices',
      'Verified badge meaning',
    ],
  },
  {
    title: 'Legal & Policies',
    icon: FileText,
    description: 'Terms, privacy, and legal information.',
    color: 'text-gray-600 bg-gray-50',
    articles: [
      'Terms of Service',
      'Privacy Policy',
      'Refund Policy',
      'Cookie Policy',
      'Community Guidelines',
    ],
  },
];

const QUICK_LINKS = [
  { label: 'FAQ', href: '/faq', icon: FileQuestion },
  { label: 'Contact Support', href: '/contact', icon: Phone },
  { label: 'Community Forum', href: '#', icon: MessageCircle },
];

export default function HelpPage() {
  useEffect(() => {
    document.title = 'Help Center — Vestra | Support & Guides';
  }, []);

  const [searchQuery, setSearchQuery] = useState('');

  const filteredCategories = searchQuery.trim()
    ? HELP_CATEGORIES.map((cat) => ({
        ...cat,
        articles: cat.articles.filter(
          (article) =>
            article.toLowerCase().includes(searchQuery.toLowerCase()) ||
            cat.title.toLowerCase().includes(searchQuery.toLowerCase())
        ),
      })).filter((cat) => cat.articles.length > 0)
    : HELP_CATEGORIES;

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
          <div className="max-w-3xl mx-auto text-center">
            <div className="inline-flex items-center gap-2 bg-emerald-500/20 border border-emerald-500/30 rounded-full px-4 py-1.5 mb-6 animate-fade-in-down">
              <span className="w-2 h-2 bg-emerald-400 rounded-full animate-pulse" />
              <span className="text-emerald-300 text-sm font-medium">We are here to help</span>
            </div>
            <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6 animate-fade-in-up">
              Help Center
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-8 max-w-2xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Find answers to common questions, browse our guides, or get in touch with our support team.
            </p>
            {/* Search */}
            <div className="max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              <div className="flex gap-2 bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-2">
                <Search className="w-5 h-5 text-gray-400 ml-2 flex-shrink-0 self-center" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search help articles..."
                  className="flex-1 bg-transparent text-white placeholder:text-gray-400 text-sm outline-none py-2"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Quick Links */}
      <div className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
          <div className="flex flex-wrap justify-center gap-4">
            {QUICK_LINKS.map((link) => {
              const Icon = link.icon;
              return (
                <Link
                  key={link.label}
                  href={link.href}
                  className="flex items-center gap-2 px-5 py-3 bg-white rounded-xl border border-gray-100 text-sm font-medium text-gray-700 hover:border-emerald-200 hover:text-emerald-700 hover:shadow-sm transition-all"
                >
                  <Icon className="w-4 h-4" />
                  {link.label}
                  <ChevronRight className="w-4 h-4" />
                </Link>
              );
            })}
          </div>
        </div>
      </div>

      {/* Help Categories */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        {searchQuery.trim() && (
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Search Results</h2>
            <p className="text-gray-500">
              {filteredCategories.reduce((acc, cat) => acc + cat.articles.length, 0)} articles found
            </p>
          </div>
        )}

        <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
          {filteredCategories.map((category) => {
            const Icon = category.icon;
            return (
              <Card key={category.title} className="p-6 hover:shadow-md transition-shadow">
                <div className={`inline-flex p-3 rounded-xl mb-4 ${category.color}`}>
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="text-lg font-semibold text-gray-900 mb-1">{category.title}</h3>
                <p className="text-sm text-gray-500 mb-4">{category.description}</p>
                <ul className="space-y-2 mb-4">
                  {category.articles.map((article) => (
                    <li key={article}>
                      <Link
                        href="/faq"
                        className="flex items-center gap-2 text-sm text-gray-600 hover:text-emerald-600 transition-colors group"
                      >
                        <ChevronRight className="w-3 h-3 text-gray-300 group-hover:text-emerald-500 flex-shrink-0" />
                        {article}
                      </Link>
                    </li>
                  ))}
                </ul>
              </Card>
            );
          })}
        </div>

        {filteredCategories.length === 0 && (
          <div className="text-center py-16">
            <HelpCircle className="w-16 h-16 text-gray-200 mx-auto mb-4" />
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No results found</h3>
            <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
              We could not find any articles matching your search. Try different keywords or contact our support team.
            </p>
            <Link href="/contact">
              <Button>
                <MessageCircle className="w-4 h-4" />
                Contact Support
              </Button>
            </Link>
          </div>
        )}
      </div>

      {/* Still Need Help */}
      <section className="bg-gradient-to-br from-emerald-600 to-emerald-800 py-16">
        <div className="max-w-4xl mx-auto text-center px-4">
          <LifeBuoy className="w-12 h-12 text-white/80 mx-auto mb-4" />
          <h2 className="text-3xl font-bold text-white mb-3">Still Need Help?</h2>
          <p className="text-emerald-100 text-lg mb-8 max-w-lg mx-auto">
            Our support team is available Monday to Friday, 8 AM to 6 PM. We typically respond within 24 hours.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/contact">
              <Button size="lg" className="bg-white text-emerald-700 hover:bg-emerald-50 font-semibold">
                <MessageCircle className="w-4 h-4" />
                Contact Support
              </Button>
            </Link>
            <Link href="/faq">
              <Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10">
                <FileQuestion className="w-4 h-4" />
                Browse FAQ
              </Button>
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
