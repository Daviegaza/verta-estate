'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { ShieldCheck } from 'lucide-react';

const SECTIONS = [
  {
    id: 'acceptance',
    title: 'Acceptance of Terms',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          By accessing or using Vestra (&quot;the Platform&quot;), you agree to be bound by these Terms of Service (&quot;Terms&quot;).
          If you do not agree to these Terms, please do not use the Platform. These Terms constitute a legally binding
          agreement between you (&quot;User&quot; or &quot;you&quot;) and Vestra Technologies Ltd (&quot;Vestra,&quot; &quot;we,&quot; or &quot;us&quot;).
        </p>
        <p className="text-gray-600">
          We reserve the right to update these Terms at any time. Continued use of the Platform after changes
          constitutes acceptance of the updated Terms. We will notify users of material changes via email or
          platform notification at least 14 days before they take effect.
        </p>
      </>
    ),
  },
  {
    id: 'accounts',
    title: 'Account Registration and Responsibilities',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          To access certain features of the Platform, you must register for an account. You agree to:
        </p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>Provide accurate, current, and complete registration information</li>
          <li>Maintain and promptly update your account information</li>
          <li>Keep your password secure and confidential</li>
          <li>Notify us immediately of any unauthorized use of your account</li>
          <li>Not create multiple accounts or use automated means to create accounts</li>
          <li>Be at least 18 years old or have parental consent</li>
        </ul>
        <p className="text-gray-600">
          You are fully responsible for all activities that occur under your account. Vestra reserves the right
          to suspend or terminate accounts that violate these Terms or engage in fraudulent activity.
        </p>
      </>
    ),
  },
  {
    id: 'listings',
    title: 'Property Listings and Verification',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Users may list properties for sale, rent, or lease on the Platform. By listing a property, you represent and warrant that:
        </p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>You have the legal right to list the property (as owner or authorized agent)</li>
          <li>All information provided about the property is accurate and not misleading</li>
          <li>Images and documents are authentic and not altered to misrepresent the property</li>
          <li>The property is not subject to any undisclosed legal disputes or encumbrances</li>
          <li>You will respond to inquiries in a timely and professional manner</li>
        </ul>
        <p className="mb-4 text-gray-600">
          Vestra uses AI-powered verification to assess property listings. However, we do not guarantee the
          accuracy, completeness, or legality of any listing. Users should conduct their own due diligence
          before entering into any property transaction.
        </p>
        <p className="text-gray-600">
          Vestra reserves the right to remove any listing that violates these Terms or appears fraudulent.
        </p>
      </>
    ),
  },
  {
    id: 'payments',
    title: 'Payments and Fees',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Vestra offers various paid services, including property verification, premium listings, and escrow services.
          By using paid services, you agree to:
        </p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>Pay all fees and charges associated with your selected services</li>
          <li>Provide valid payment information (M-Pesa, bank transfer, or other accepted methods)</li>
          <li>Authorize Vestra to charge applicable fees via your chosen payment method</li>
          <li>Pay all applicable taxes, including VAT where required</li>
        </ul>
        <p className="mb-4 text-gray-600">
          All fees are displayed in Kenyan Shillings (KES) unless otherwise stated. Fees are non-refundable
          except as expressly stated in our Refund Policy. We reserve the right to change our fees with
          30 days notice.
        </p>
        <p className="text-gray-600">
          Escrow payments are held in accordance with our Escrow Agreement and released only when specified
          conditions are met by all parties.
        </p>
      </>
    ),
  },
  {
    id: 'verification-service',
    title: 'AI Verification Service',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Vestra AI verification service provides an automated Trust Score for properties based on available
          data and documents. Important limitations:
        </p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>Trust Scores are AI-generated estimates and do not constitute professional advice</li>
          <li>Verification is based on documents and data you provide — we cannot verify what we cannot see</li>
          <li>Vestra does not perform physical property inspections unless explicitly stated</li>
          <li>Verification results should not be your sole basis for property decisions</li>
          <li>We recommend consulting with qualified professionals (lawyers, surveyors, valuers) for major transactions</li>
        </ul>
      </>
    ),
  },
  {
    id: 'prohibited-conduct',
    title: 'Prohibited Conduct',
    content: (
      <>
        <p className="mb-4 text-gray-600">You agree not to engage in any of the following prohibited activities:</p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>Posting fake, misleading, or fraudulent property listings</li>
          <li>Impersonating another person or entity</li>
          <li>Attempting to manipulate or game the AI Trust Score system</li>
          <li>Uploading malicious code, viruses, or harmful content</li>
          <li>Scraping, crawling, or using automated tools to access the Platform without permission</li>
          <li>Interfering with the security or functionality of the Platform</li>
          <li>Using the Platform for any illegal purpose or in violation of Kenyan law</li>
          <li>Harassing, threatening, or abusing other users</li>
          <li>Posting discriminatory or offensive content</li>
        </ul>
      </>
    ),
  },
  {
    id: 'intellectual-property',
    title: 'Intellectual Property',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          The Vestra platform, including its design, logo, trademarks, AI models, and software, is the
          intellectual property of Vestra Technologies Ltd. You may not reproduce, distribute, modify, or
          create derivative works without our express written permission.
        </p>
        <p className="text-gray-600">
          By listing a property, you grant Vestra a non-exclusive, royalty-free license to display your
          content on the Platform. You retain ownership of your content.
        </p>
      </>
    ),
  },
  {
    id: 'disclaimers',
    title: 'Disclaimers and Limitation of Liability',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          The Platform is provided &quot;as is&quot; and &quot;as available&quot; without warranties of any kind,
          either express or implied. Vestra does not guarantee that:
        </p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>The Platform will be uninterrupted, timely, or error-free</li>
          <li>Verification results are 100% accurate or complete</li>
          <li>Any property transaction will be successfully completed</li>
          <li>Third-party services integrated with the Platform will perform as expected</li>
        </ul>
        <p className="text-gray-600">
          To the maximum extent permitted by law, Vestra shall not be liable for any indirect, incidental,
          special, consequential, or punitive damages arising from your use of the Platform. Our total
          liability shall not exceed the fees you have paid to Vestra in the 12 months preceding the claim.
        </p>
      </>
    ),
  },
  {
    id: 'dispute-resolution',
    title: 'Dispute Resolution',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Any disputes arising from these Terms or your use of the Platform shall be resolved as follows:
        </p>
        <ol className="list-decimal pl-6 space-y-2 mb-4 text-gray-600">
          <li><strong>Informal Resolution:</strong> Parties will attempt to resolve disputes informally through good-faith negotiations.</li>
          <li><strong>Mediation:</strong> If informal resolution fails, disputes will be referred to mediation at the Nairobi Centre for International Arbitration (NCIA).</li>
          <li><strong>Jurisdiction:</strong> Any legal proceedings shall be brought exclusively in the courts of Nairobi, Kenya.</li>
          <li><strong>Governing Law:</strong> These Terms are governed by the laws of the Republic of Kenya.</li>
        </ol>
        <p className="text-gray-600">
          For disputes involving less than KES 50,000, we offer an internal dispute resolution process.
          Please contact support@vestra.co.ke to initiate this process.
        </p>
      </>
    ),
  },
  {
    id: 'termination',
    title: 'Termination',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Either party may terminate these Terms at any time. Vestra may suspend or terminate your account
          immediately if you violate these Terms or engage in fraudulent, abusive, or illegal activity.
        </p>
        <p className="text-gray-600">
          Upon termination, your right to use the Platform ceases immediately. Sections regarding payments,
          intellectual property, disclaimers, and dispute resolution shall survive termination.
        </p>
      </>
    ),
  },
  {
    id: 'contact',
    title: 'Contact Information',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          For questions about these Terms, please contact us:
        </p>
        <div className="bg-gray-50 rounded-2xl p-6 space-y-3">
          <p className="text-gray-700"><strong>Email:</strong> legal@vestra.co.ke</p>
          <p className="text-gray-700"><strong>Phone:</strong> +254 700 123 456</p>
          <p className="text-gray-700"><strong>Address:</strong> Vestra Technologies Ltd, Bishop Magua Centre, Ngong Road, Nairobi, Kenya</p>
        </div>
      </>
    ),
  },
];

export default function TermsPage() {
  useEffect(() => {
    document.title = 'Terms of Service — Vestra';
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
            <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6 animate-fade-in-up">
              Terms of Service
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-4 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              The terms governing your use of the Vestra platform and services.
            </p>
            <p className="text-sm text-gray-400 animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              Last updated: January 2026
            </p>
          </div>
        </div>
      </section>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="flex flex-col lg:flex-row gap-12">
          {/* Table of Contents - Sidebar */}
          <aside className="lg:w-72 flex-shrink-0">
            <div className="lg:sticky lg:top-24 bg-gray-50 rounded-2xl p-6 border border-gray-100">
              <h3 className="text-sm font-semibold text-gray-900 uppercase tracking-wider mb-4">On this page</h3>
              <nav className="space-y-1">
                {SECTIONS.map((section) => (
                  <a
                    key={section.id}
                    href={`#${section.id}`}
                    className="block text-sm text-gray-600 hover:text-emerald-600 hover:bg-emerald-50 px-3 py-2 rounded-lg transition-colors"
                  >
                    {section.title}
                  </a>
                ))}
              </nav>
            </div>
          </aside>

          {/* Main Content */}
          <div className="flex-1 min-w-0 max-w-3xl">
            <div className="prose prose-gray max-w-none">
              <p className="text-lg text-gray-600 leading-relaxed mb-12">
                Welcome to Vestra. These Terms of Service outline the rules and regulations for the use of
                Vestra&apos;s AI-powered property trust platform. By accessing this platform, you accept these
                Terms in full. Do not continue to use Vestra if you do not agree with any of these Terms.
              </p>

              <div className="space-y-16">
                {SECTIONS.map((section) => (
                  <section key={section.id} id={section.id}>
                    <h2 className="text-2xl font-bold text-gray-900 mb-4">{section.title}</h2>
                    {section.content}
                  </section>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

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
