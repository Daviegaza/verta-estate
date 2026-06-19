'use client';

import Navbar from '@/components/layout/navbar';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Building2, Key, Webhook, Code, Zap, BookOpen, Shield, CheckCircle } from 'lucide-react';
import Link from 'next/link';

interface PricingTier {
  name: string;
  price: string;
  requests: string;
  endpoints: string;
  support: string;
  features: string[];
  highlighted?: boolean;
}

const PRICING_TIERS: PricingTier[] = [
  {
    name: 'Starter',
    price: 'KES 25,000',
    requests: '1,000 req/day',
    endpoints: 'Basic endpoints',
    support: 'Email support',
    features: [
      'Property search API',
      'Basic property details',
      'City-level filtering',
      '1,000 requests per day',
      'Email support within 48h',
      'API documentation access',
    ],
  },
  {
    name: 'Business',
    price: 'KES 75,000',
    requests: '10,000 req/day',
    endpoints: 'All endpoints',
    support: 'Priority support',
    highlighted: true,
    features: [
      'Everything in Starter',
      'AI trust scoring API',
      'Market data & analytics',
      'Webhook integration',
      '10,000 requests per day',
      'Priority support within 4h',
    ],
  },
  {
    name: 'Enterprise',
    price: 'KES 150,000',
    requests: 'Unlimited',
    endpoints: 'Full platform access',
    support: 'Dedicated support',
    features: [
      'Everything in Business',
      'Unlimited API requests',
      'Dedicated infrastructure',
      'Custom integration support',
      '99.9% SLA guarantee',
      'Dedicated account manager',
    ],
  },
];

const API_FEATURES = [
  {
    icon: <Building2 className="w-6 h-6" />,
    title: 'Property Search API',
    description: 'Full-text and structured search across thousands of verified properties. Filter by city, type, price range, bedrooms, and more with powerful query parameters.',
  },
  {
    icon: <Shield className="w-6 h-6" />,
    title: 'Verification API',
    description: 'AI-powered trust scoring and fraud detection. Verify property documents, ownership records, and market pricing with a single API call.',
  },
  {
    icon: <Zap className="w-6 h-6" />,
    title: 'Market Data API',
    description: 'City-level analytics on property prices, trends, and demand. Make data-driven decisions with real-time market intelligence from across Kenya.',
  },
  {
    icon: <Webhook className="w-6 h-6" />,
    title: 'Webhooks',
    description: 'Real-time event streaming for property updates, verification completions, and market changes. Integrate Vestra data directly into your workflows.',
  },
];

export default function EnterprisePage() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />

      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-12">
        {/* Hero */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-100 rounded-2xl mb-6">
            <Building2 className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Vestra Enterprise API
          </h1>
          <p className="text-lg text-gray-500 max-w-2xl mx-auto mb-8">
            Power your business with Africa&apos;s most trusted property data. Real-time property intelligence, AI verification, and market analytics — all through a simple REST API.
          </p>
          <Link href="/enterprise/keys">
            <Button size="xl" className="gap-2">
              <Key className="w-5 h-5" />
              Get API Keys
            </Button>
          </Link>
        </div>

        {/* Pricing Cards */}
        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Simple, Transparent Pricing</h2>
            <p className="text-gray-500">Choose the plan that fits your scale. All plans include documentation and support.</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {PRICING_TIERS.map((tier) => (
              <Card
                key={tier.name}
                className={`relative flex flex-col ${
                  tier.highlighted
                    ? 'ring-2 ring-emerald-400 shadow-lg scale-[1.02]'
                    : ''
                }`}
                padding="none"
              >
                {tier.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-emerald-600 text-white text-xs font-bold px-4 py-1 rounded-full whitespace-nowrap">
                    Most Popular
                  </div>
                )}

                <div className="p-6 flex-1">
                  <h3 className="text-xl font-bold text-gray-900 mb-1">{tier.name}</h3>
                  <div className="mb-4">
                    <span className="text-3xl font-bold text-gray-900">{tier.price}</span>
                    <span className="text-gray-400 text-sm">/month</span>
                  </div>
                  <div className="space-y-1.5 mb-4 text-sm text-gray-500">
                    <p>{tier.requests}</p>
                    <p>{tier.endpoints}</p>
                    <p>{tier.support}</p>
                  </div>

                  <ul className="space-y-3">
                    {tier.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm text-gray-700">
                        <CheckCircle className="w-4 h-4 text-emerald-500 flex-shrink-0 mt-0.5" />
                        {f}
                      </li>
                    ))}
                  </ul>
                </div>

                <div className="p-6 pt-0">
                  <Button
                    fullWidth
                    size="lg"
                    variant={tier.highlighted ? 'primary' : 'outline'}
                  >
                    Contact Sales
                  </Button>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* API Features */}
        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Everything You Need to Build</h2>
            <p className="text-gray-500">Comprehensive APIs for every property data use case.</p>
          </div>
          <div className="grid sm:grid-cols-2 gap-6">
            {API_FEATURES.map((feature) => (
              <Card key={feature.title} className="hover:shadow-md transition-shadow">
                <div className="flex items-start gap-4">
                  <div className="p-3 bg-emerald-50 rounded-xl flex-shrink-0">
                    <div className="text-emerald-600">{feature.icon}</div>
                  </div>
                  <div>
                    <h3 className="font-semibold text-gray-900 mb-1.5">{feature.title}</h3>
                    <p className="text-sm text-gray-500 leading-relaxed">{feature.description}</p>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>

        {/* Quick Start */}
        <div className="mb-20">
          <div className="text-center mb-10">
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Quick Start</h2>
            <p className="text-gray-500">Get started with a single API call. No SDK installation required.</p>
          </div>
          <Card className="overflow-hidden" padding="none">
            <div className="flex items-center gap-2 px-6 py-3 bg-gray-50 border-b border-gray-100">
              <Code className="w-4 h-4 text-gray-400" />
              <span className="text-xs font-medium text-gray-500">cURL Example</span>
            </div>
            <div className="p-6 bg-gray-900 overflow-x-auto">
              <pre className="text-sm font-mono leading-relaxed">
                <span className="text-emerald-400">curl</span>{' '}
                <span className="text-purple-300">-H</span>{' '}
                <span className="text-amber-300">&quot;Authorization: Bearer YOUR_API_KEY&quot;</span>{' '}
                <span className="text-gray-400">\</span>
                <br />
                <span className="text-emerald-400">  https://api.vestra.co.ke/api/properties?city=Nairobi</span>
              </pre>
            </div>
          </Card>
        </div>

        {/* Footer CTA */}
        <div className="text-center bg-gradient-to-br from-gray-900 via-emerald-950 to-gray-900 rounded-3xl p-12">
          <h2 className="text-3xl font-bold text-white mb-4">Ready to integrate?</h2>
          <p className="text-emerald-200/80 mb-8 max-w-lg mx-auto">
            Get your API keys and start building with Africa&apos;s most comprehensive property data platform.
          </p>
          <Link href="/enterprise/keys">
            <Button size="xl" className="bg-white text-emerald-700 hover:bg-emerald-50 gap-2">
              <Key className="w-5 h-5" />
              Get Your API Keys
            </Button>
          </Link>
        </div>
      </div>
    </div>
  );
}
