'use client';

import { useEffect } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { ShieldCheck, ChevronRight } from 'lucide-react';

const SECTIONS = [
  {
    id: 'information-we-collect',
    title: 'Information We Collect',
    content: (
      <>
        <p className="mb-4">We collect information you provide directly to us, including:</p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li><strong>Account Information:</strong> Name, email address, phone number, and password when you create an account.</li>
          <li><strong>Profile Information:</strong> Profile photo, location, preferred language, and agent/broker credentials if applicable.</li>
          <li><strong>Property Information:</strong> Property details, images, documents, and location data you submit for listing or verification.</li>
          <li><strong>Transaction Information:</strong> Payment details, M-Pesa transaction IDs, escrow agreements, and rental contracts.</li>
          <li><strong>Communications:</strong> Messages sent through our platform, support inquiries, and feedback submissions.</li>
          <li><strong>Identity Documents:</strong> National ID, passport, or KRA PIN for verification purposes (with your consent).</li>
        </ul>
        <p className="text-gray-600">We also automatically collect certain technical information when you use our platform, including IP address, browser type, device information, and usage patterns.</p>
      </>
    ),
  },
  {
    id: 'how-we-use',
    title: 'How We Use Your Information',
    content: (
      <>
        <p className="mb-4">We use the information we collect to:</p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>Provide, maintain, and improve our property verification and listing services</li>
          <li>Process your transactions, including M-Pesa payments and escrow services</li>
          <li>Verify property ownership and detect fraudulent listings</li>
          <li>Calculate and display AI-powered Trust Scores</li>
          <li>Send you service updates, transaction confirmations, and support messages</li>
          <li>Respond to your comments, questions, and support requests</li>
          <li>Monitor and analyze usage trends to improve user experience</li>
          <li>Detect, prevent, and address fraud, abuse, and security incidents</li>
          <li>Comply with legal obligations under Kenyan law</li>
        </ul>
      </>
    ),
  },
  {
    id: 'information-sharing',
    title: 'Information Sharing and Disclosure',
    content: (
      <>
        <p className="mb-4">We may share your information in the following circumstances:</p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li><strong>With Your Consent:</strong> We share information when you explicitly authorize us to do so.</li>
          <li><strong>Service Providers:</strong> With trusted third-party services that help us operate (payment processors, cloud hosting, AI providers).</li>
          <li><strong>Property Verification:</strong> Relevant property information may be shared with government land registries and third-party verification services.</li>
          <li><strong>Legal Requirements:</strong> When required by law, court order, or government regulation in Kenya.</li>
          <li><strong>Business Transfers:</strong> In connection with a merger, acquisition, or sale of assets.</li>
          <li><strong>Fraud Prevention:</strong> With law enforcement and fraud prevention agencies to investigate and prevent fraudulent activity.</li>
        </ul>
        <p className="text-gray-600">We do not sell your personal information to third parties for their marketing purposes.</p>
      </>
    ),
  },
  {
    id: 'data-security',
    title: 'Data Security',
    content: (
      <>
        <p className="mb-4">We implement industry-standard security measures to protect your data:</p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li>End-to-end encryption for all data in transit (TLS 1.3)</li>
          <li>Encrypted storage for sensitive data at rest (AES-256)</li>
          <li>Regular security audits and penetration testing</li>
          <li>Strict access controls and authentication protocols</li>
          <li>24/7 monitoring for suspicious activity</li>
          <li>Secure M-Pesa integration with Safaricom certified APIs</li>
          <li>Token-based session management with automatic expiry</li>
        </ul>
        <p className="text-gray-600">While we take every precaution, no online platform can guarantee absolute security. We encourage users to enable two-factor authentication and use strong passwords.</p>
      </>
    ),
  },
  {
    id: 'data-retention',
    title: 'Data Retention',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          We retain your personal information for as long as your account is active or as needed to provide you with our services.
          If you close your account, we will delete or anonymize your personal data within 90 days, except where we are required
          by law to retain certain records (e.g., transaction records for tax and anti-fraud purposes, which we retain for 7 years
          as required by Kenyan law).
        </p>
      </>
    ),
  },
  {
    id: 'your-rights',
    title: 'Your Rights Under Data Protection Law',
    content: (
      <>
        <p className="mb-4">Under Kenya Data Protection Act, 2019, you have the following rights:</p>
        <ul className="list-disc pl-6 space-y-2 mb-4 text-gray-600">
          <li><strong>Right to Access:</strong> Request a copy of the personal data we hold about you.</li>
          <li><strong>Right to Rectification:</strong> Request correction of inaccurate or incomplete data.</li>
          <li><strong>Right to Deletion:</strong> Request deletion of your personal data, subject to legal retention requirements.</li>
          <li><strong>Right to Restrict Processing:</strong> Request that we limit how we use your data.</li>
          <li><strong>Right to Data Portability:</strong> Request transfer of your data to another service provider.</li>
          <li><strong>Right to Object:</strong> Object to processing of your data for marketing or legitimate interests.</li>
          <li><strong>Right to Withdraw Consent:</strong> Withdraw consent at any time where processing is based on consent.</li>
        </ul>
        <p className="text-gray-600">
          To exercise any of these rights, please contact our Data Protection Officer at dpo@vestra.co.ke.
          We will respond to your request within 30 days as required by law.
        </p>
      </>
    ),
  },
  {
    id: 'cookies',
    title: 'Cookies and Tracking',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          We use cookies and similar tracking technologies to enhance your experience on our platform.
          These include essential cookies required for platform functionality, analytics cookies to understand
          how you use our services, and preference cookies to remember your settings.
        </p>
        <p className="mb-4 text-gray-600">
          You can control cookie settings through your browser preferences. However, disabling certain cookies
          may affect the functionality of our platform. We do not use cookies for third-party advertising.
        </p>
      </>
    ),
  },
  {
    id: 'third-party',
    title: 'Third-Party Services',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Vestra integrates with several third-party services to provide our platform. These include Safaricom (M-Pesa),
          cloud infrastructure providers, AI model providers, and document verification services. Each third-party
          service has its own privacy policy governing data handling. We ensure all partners meet our security standards
          through contractual agreements and regular audits.
        </p>
      </>
    ),
  },
  {
    id: 'international-transfers',
    title: 'International Data Transfers',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          Your data may be processed on servers located outside Kenya. When we transfer data internationally,
          we ensure appropriate safeguards are in place, including Standard Contractual Clauses and compliance
          with the Kenya Data Protection Act requirements for cross-border data transfers. Our primary data
          centers are located in Africa and Europe.
        </p>
      </>
    ),
  },
  {
    id: 'changes',
    title: 'Changes to This Policy',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          We may update this Privacy Policy from time to time. We will notify you of material changes by posting
          the updated policy on our platform and, where appropriate, sending you an email notification.
          We encourage you to review this policy periodically. Continued use of Vestra after changes constitutes
          acceptance of the updated policy.
        </p>
        <p className="text-gray-600">Last updated: January 2026</p>
      </>
    ),
  },
  {
    id: 'contact-us',
    title: 'Contact Us',
    content: (
      <>
        <p className="mb-4 text-gray-600">
          If you have questions, concerns, or requests regarding this Privacy Policy or our data practices,
          please contact us:
        </p>
        <div className="bg-gray-50 rounded-2xl p-6 space-y-3">
          <p className="text-gray-700"><strong>Data Protection Officer:</strong> dpo@vestra.co.ke</p>
          <p className="text-gray-700"><strong>Email:</strong> privacy@vestra.co.ke</p>
          <p className="text-gray-700"><strong>Phone:</strong> +254 700 123 456</p>
          <p className="text-gray-700"><strong>Address:</strong> Vestra Technologies Ltd, Bishop Magua Centre, Ngong Road, Nairobi, Kenya</p>
        </div>
      </>
    ),
  },
];

export default function PrivacyPage() {
  useEffect(() => {
    document.title = 'Privacy Policy — Vestra';
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
              Privacy Policy
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-4 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              How Vestra collects, uses, and protects your personal information.
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
                At Vestra Technologies Ltd (&quot;Vestra,&quot; &quot;we,&quot; &quot;us,&quot; or &quot;our&quot;), we take your privacy seriously.
                This Privacy Policy explains how we collect, use, disclose, and safeguard your information when you use our
                AI-powered property trust platform and related services.
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
