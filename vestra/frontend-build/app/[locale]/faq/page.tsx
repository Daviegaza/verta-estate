'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/card';
import { Search, ChevronDown, Plus, ShieldCheck, HelpCircle, MessageCircle, ChevronRight } from 'lucide-react';

const FAQ_CATEGORIES = [
  {
    id: 'general',
    label: 'General',
    icon: HelpCircle,
    color: 'text-emerald-600 bg-emerald-50',
  },
  {
    id: 'buyers',
    label: 'Buyers',
    icon: ShieldCheck,
    color: 'text-blue-600 bg-blue-50',
  },
  {
    id: 'sellers',
    label: 'Sellers & Landlords',
    icon: Plus,
    color: 'text-purple-600 bg-purple-50',
  },
  {
    id: 'agents',
    label: 'Agents',
    icon: MessageCircle,
    color: 'text-amber-600 bg-amber-50',
  },
  {
    id: 'rentals',
    label: 'Rentals',
    icon: ShieldCheck,
    color: 'text-red-600 bg-red-50',
  },
  {
    id: 'payments',
    label: 'Payments',
    icon: Search,
    color: 'text-teal-600 bg-teal-50',
  },
];

const FAQ_ITEMS: Record<string, { question: string; answer: string }[]> = {
  general: [
    {
      question: 'What is Vestra?',
      answer: 'Vestra is Kenya\'s AI-powered property trust platform. We help buyers, sellers, landlords, and agents verify properties, detect fraud, and transact with confidence. Our platform uses artificial intelligence to analyze property documents, detect fake listings, and provide a Trust Score for every property.',
    },
    {
      question: 'Is Vestra free to use?',
      answer: 'Browsing properties and basic searches are free. Premium features like AI property verification (KES 500 per report), advanced analytics, and enhanced listings have associated fees. Creating an account is always free.',
    },
    {
      question: 'How does Vestra detect fraud?',
      answer: 'Our AI analyzes property documents, cross-references with government land registry data (where available), checks for duplicate listings, and runs multiple algorithms to detect inconsistencies in property information. The system flags suspicious patterns and assigns a Trust Score that indicates the likelihood of fraud.',
    },
    {
      question: 'Which countries does Vestra operate in?',
      answer: 'Vestra is currently available across all 47 counties in Kenya. We are actively expanding to Nigeria, Ghana, and South Africa in 2026.',
    },
  ],
  buyers: [
    {
      question: 'How do I search for properties?',
      answer: 'You can use our natural language AI search bar — just type what you\'re looking for, like "2-bedroom apartment in Westlands under KES 40,000." You can also browse by location, property type, price range, and other filters on our market page.',
    },
    {
      question: 'What is a Trust Score?',
      answer: 'A Trust Score is our AI\'s assessment of a property\'s legitimacy, scored from 0-100. Scores above 80 indicate high trustworthiness, 60-80 suggest some caution needed, and below 60 indicates significant risk. The score is based on document analysis, ownership verification, price comparison, and historical data.',
    },
    {
      question: 'Can I verify a property before buying?',
      answer: 'Absolutely. Use our Verify Property feature — upload the property documents (title deed, sale agreement, etc.), pay a KES 500 fee via M-Pesa, and receive a comprehensive AI Trust Report within minutes.',
    },
    {
      question: 'How do I contact an agent or seller?',
      answer: 'Each property listing has a "Contact Agent" or "Inquire" button. You can message them directly through our platform. Your communication is tracked and recorded for your safety.',
    },
  ],
  sellers: [
    {
      question: 'How do I list a property on Vestra?',
      answer: 'Create an account, go to your dashboard, and click "List Property." Fill in the property details, upload photos and documents, set your price, and submit. Your listing will be reviewed and verified before going live.',
    },
    {
      question: 'How much does it cost to list a property?',
      answer: 'Basic property listings are free. We offer premium listing packages with enhanced visibility, AI verification badges, and featured placement starting from KES 1,500 per month.',
    },
    {
      question: 'Will my property be verified?',
      answer: 'All listings undergo AI verification. Properties that pass verification receive a "Verified" badge, which significantly increases buyer trust and typically results in faster sales at better prices.',
    },
    {
      question: 'How do I receive payments?',
      answer: 'Sellers can receive payments via M-Pesa, bank transfer, or escrow services through Vestra. For high-value transactions, we recommend using our escrow service for added protection.',
    },
  ],
  agents: [
    {
      question: 'How do I become a Verified Agent?',
      answer: 'Apply through your dashboard by submitting your agent credentials, including your estate agency license, practicing certificate, and identification documents. Our team reviews and verifies your qualifications within 48 hours.',
    },
    {
      question: 'What are the benefits of being verified?',
      answer: 'Verified Agents get a special badge on their profile, higher visibility in search results, featured listings, access to exclusive analytics, and priority support. Verified Agents close deals 3x faster on average.',
    },
    {
      question: 'Is there a cost for agents?',
      answer: 'Agent registration and verification are free. We offer premium subscription tiers (KES 2,500/month for Professional, KES 5,000/month for Enterprise) with additional features like bulk listing management, advanced analytics, and priority placement.',
    },
    {
      question: 'Can I manage multiple clients through Vestra?',
      answer: 'Yes! Our agent dashboard is designed for portfolio management. You can manage listings for multiple clients, track inquiries, monitor Trust Scores, and generate performance reports — all from one interface.',
    },
  ],
  rentals: [
    {
      question: 'How do I list a rental property?',
      answer: 'Select "For Rent" as your listing type when creating a property listing. Include rent amount, deposit required, lease terms, and availability date. You can also specify furnished/unfurnished and utility arrangements.',
    },
    {
      question: 'How does rental payment work?',
      answer: 'Tenants can pay rent via M-Pesa STK Push directly through the platform. Landlords receive automatic payment confirmations and can track payment history. Late payment reminders are automated.',
    },
    {
      question: 'What tenant management tools are available?',
      answer: 'Landlords can manage tenant profiles, track rent payments, log maintenance requests, store lease agreements, and communicate with tenants — all from the Vestra dashboard. Automated reminders help reduce late payments.',
    },
    {
      question: 'What happens if a tenant stops paying?',
      answer: 'Vestra provides a structured communication and escalation process. Our platform documents all payment history and communication, which can be used as evidence if legal action becomes necessary. We also offer optional rent guarantee insurance.',
    },
  ],
  payments: [
    {
      question: 'What payment methods does Vestra accept?',
      answer: 'We accept M-Pesa (STK Push and Buy Goods), bank transfers, and credit/debit cards. For large transactions, we recommend using our escrow service.',
    },
    {
      question: 'How does M-Pesa integration work?',
      answer: 'When you choose to pay with M-Pesa, an STK Push is sent to your registered M-Pesa phone number. Simply enter your PIN to authorize the payment. The transaction is confirmed in real-time.',
    },
    {
      question: 'Is my payment information secure?',
      answer: 'Yes. We use PCI-compliant payment processing. M-Pesa transactions are processed directly through Safaricom\'s secure APIs. We never store your M-Pesa PIN or full payment credentials.',
    },
    {
      question: 'Can I get a refund?',
      answer: 'Refund policies vary by service. AI verification fees are non-refundable once the report is generated. Escrow payments are refundable according to the escrow agreement terms. Premium listing fees may be prorated if you cancel early.',
    },
    {
      question: 'What is Vestra Escrow?',
      answer: 'Vestra Escrow is a secure payment service that holds funds until both buyer and seller fulfill their obligations. The buyer deposits funds, the seller transfers ownership, and once both sides confirm satisfaction, the funds are released. This protects both parties from fraud.',
    },
  ],
};

function AccordionItem({ question, answer, isOpen, onToggle }: { question: string; answer: string; isOpen: boolean; onToggle: () => void }) {
  return (
    <div className="border border-gray-100 rounded-xl overflow-hidden transition-all duration-200 hover:border-gray-200">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between px-6 py-4 text-left bg-white hover:bg-gray-50 transition-colors"
      >
        <span className="text-sm font-medium text-gray-900 pr-4">{question}</span>
        <ChevronDown
          className={`w-5 h-5 text-gray-400 flex-shrink-0 transition-transform duration-200 ${
            isOpen ? 'rotate-180' : ''
          }`}
        />
      </button>
      <div
        className={`overflow-hidden transition-all duration-300 ${
          isOpen ? 'max-h-96 opacity-100' : 'max-h-0 opacity-0'
        }`}
      >
        <div className="px-6 pb-4">
          <p className="text-sm text-gray-600 leading-relaxed">{answer}</p>
        </div>
      </div>
    </div>
  );
}

export default function FAQPage() {
  useEffect(() => {
    document.title = 'FAQ — Vestra | Frequently Asked Questions';
  }, []);

  const [activeCategory, setActiveCategory] = useState('general');
  const [searchQuery, setSearchQuery] = useState('');
  const [openItems, setOpenItems] = useState<Record<string, boolean>>({});

  const allQuestions = Object.values(FAQ_ITEMS).flat();
  const currentQuestions = FAQ_ITEMS[activeCategory] || [];

  const filteredQuestions = searchQuery.trim()
    ? allQuestions.filter(
        (item) =>
          item.question.toLowerCase().includes(searchQuery.toLowerCase()) ||
          item.answer.toLowerCase().includes(searchQuery.toLowerCase())
      )
    : currentQuestions;

  const toggleItem = (question: string) => {
    setOpenItems((prev) => ({ ...prev, [question]: !prev[question] }));
  };

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
            <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6 animate-fade-in-up">
              Frequently Asked Questions
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-8 max-w-2xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Everything you need to know about Vestra. Can&apos;t find what you&apos;re looking for? Reach out to our support team.
            </p>

            {/* Search */}
            <div className="max-w-xl mx-auto animate-fade-in-up" style={{ animationDelay: '0.3s' }}>
              <div className="flex gap-2 bg-white/10 backdrop-blur border border-white/20 rounded-2xl p-2">
                <Search className="w-5 h-5 text-gray-400 ml-2 flex-shrink-0 self-center" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search frequently asked questions..."
                  className="flex-1 bg-transparent text-white placeholder:text-gray-400 text-sm outline-none py-2"
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Content */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        {!searchQuery.trim() && (
          <>
            {/* Category Pills */}
            <div className="flex flex-wrap gap-3 mb-12 justify-center">
              {FAQ_CATEGORIES.map((cat) => {
                const Icon = cat.icon;
                const isActive = activeCategory === cat.id;
                return (
                  <button
                    key={cat.id}
                    onClick={() => setActiveCategory(cat.id)}
                    className={`inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 border ${
                      isActive
                        ? 'bg-emerald-50 border-emerald-200 text-emerald-700 shadow-sm'
                        : 'bg-white border-gray-100 text-gray-600 hover:border-gray-200 hover:text-gray-900'
                    }`}
                  >
                    <Icon className={`w-4 h-4 ${isActive ? 'text-emerald-600' : 'text-gray-400'}`} />
                    {cat.label}
                  </button>
                );
              })}
            </div>

            {/* Category Title */}
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-gray-900">
                {FAQ_CATEGORIES.find((c) => c.id === activeCategory)?.label || 'General'}
              </h2>
              <p className="text-gray-500 text-sm mt-1">
                {FAQ_ITEMS[activeCategory]?.length || 0} questions
              </p>
            </div>
          </>
        )}

        {searchQuery.trim() && (
          <div className="text-center mb-8">
            <h2 className="text-2xl font-bold text-gray-900">Search Results</h2>
            <p className="text-gray-500 text-sm mt-1">
              {filteredQuestions.length} result{filteredQuestions.length !== 1 ? 's' : ''} for &quot;{searchQuery}&quot;
            </p>
          </div>
        )}

        {/* Accordion */}
        <div className="max-w-3xl mx-auto space-y-3">
          {filteredQuestions.length > 0 ? (
            filteredQuestions.map((item) => (
              <AccordionItem
                key={item.question}
                question={item.question}
                answer={item.answer}
                isOpen={!!openItems[item.question]}
                onToggle={() => toggleItem(item.question)}
              />
            ))
          ) : (
            <div className="text-center py-16">
              <HelpCircle className="w-16 h-16 text-gray-200 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">No results found</h3>
              <p className="text-gray-500 text-sm mb-6">
                Try a different search term or browse the categories above.
              </p>
              <Button
                variant="outline"
                onClick={() => {
                  setSearchQuery('');
                  setActiveCategory('general');
                }}
              >
                Clear Search
              </Button>
            </div>
          )}
        </div>

        {/* Still have questions? */}
        <div className="max-w-3xl mx-auto mt-16 bg-gray-50 rounded-3xl p-10 text-center border border-gray-100">
          <HelpCircle className="w-12 h-12 text-emerald-500 mx-auto mb-4" />
          <h3 className="text-xl font-bold text-gray-900 mb-2">Still have questions?</h3>
          <p className="text-gray-500 text-sm mb-6 max-w-md mx-auto">
            Cannot find the answer you are looking for? Our support team is here to help.
          </p>
          <div className="flex gap-4 justify-center">
            <Link href="/contact">
              <Button>
                <MessageCircle className="w-4 h-4" />
                Contact Us
              </Button>
            </Link>
            <Link href="/help">
              <Button variant="outline">
                Help Center
              </Button>
            </Link>
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
