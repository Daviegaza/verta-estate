'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams, useRouter } from 'next/navigation';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import {
  ShieldCheck, Calendar, User, Clock, ArrowLeft, ArrowRight,
  Share2, MessageCircle, ExternalLink, Globe, Copy, CheckCircle2,
  ChevronRight, Heart, Bookmark
} from 'lucide-react';

// Placeholder blog data — in production this would come from a CMS API
const POSTS_DATA: Record<string, {
  title: string;
  excerpt: string;
  content: string[];
  author: string;
  role: string;
  date: string;
  readTime: string;
  category: string;
  categoryColor: string;
  gradient: string;
  related: string[];
}> = {
  'kenya-real-estate-market-trends-2026': {
    title: 'Kenya Real Estate Market Trends 2026: What Buyers and Sellers Need to Know',
    excerpt: 'Comprehensive analysis of Kenya real estate market in 2026, including price trends, emerging neighborhoods, and investment opportunities across Nairobi, Mombasa, and Kisumu.',
    content: [
      'The Kenya real estate market in 2026 presents a landscape of remarkable opportunity and careful consideration. After a period of adjustment following the post-pandemic boom, the market has stabilized with more realistic pricing and increased transparency, partly driven by technology platforms like Vestra that are making property verification accessible to everyday Kenyans.',
      'Average property prices in Nairobi have seen a moderate 5-8% increase year-on-year, with the most significant growth in emerging suburbs like Ruaka, Syokimau, and Kitengela. These areas offer more affordable options for first-time buyers while still providing good access to the city center via the expanding expressway network. In Mombasa, the coastal property market continues to attract both local and diaspora investors, with prices rising 6-10% in prime locations like Nyali and Diani.',
      'Kisumu is emerging as a surprise performer in 2026. With improved infrastructure and growing commercial activity in the Lake Region Economic Bloc, property values in Kisumu have appreciated by up to 12% in well-connected areas. This represents a significant opportunity for early investors who recognize the region growth potential.',
      'For buyers, the key trend is the increasing importance of property verification. With property fraud still affecting approximately 1 in 5 transactions in Kenya, buyers are increasingly using digital verification tools before committing to purchases. This shift is driving demand for verified listings and creating a premium for properties that have undergone professional verification.',
      'Sellers face a market where presentation and trustworthiness matter more than ever. Properties with verified title deeds, clear ownership history, and professional documentation are selling 40% faster than unverified ones. The premium for verified properties typically ranges from 5-15% above comparable unverified listings, making the investment in verification well worthwhile.',
    ],
    author: 'Kevin Ochieng',
    role: 'CEO & Co-Founder',
    date: 'June 15, 2026',
    readTime: '8 min read',
    category: 'Market Insights',
    categoryColor: 'bg-blue-50 text-blue-700 border-blue-200',
    gradient: 'from-blue-500 to-blue-700',
    related: ['first-time-home-buyer-guide-kenya', 'ai-property-verification-how-it-works'],
  },
  'how-to-verify-property-title-deed-kenya': {
    title: 'How to Verify a Property Title Deed in Kenya: Complete Guide 2026',
    excerpt: 'Step-by-step guide on verifying property title deeds in Kenya.',
    content: [
      'Verifying a property title deed is the single most important step in any property transaction in Kenya. With thousands of Kenyans falling victim to title deed fraud every year, understanding the verification process is essential for protecting your investment.',
      'The first step is to conduct a physical inspection of the original title deed. Look for security features including the watermark, serial numbers, and the Kenya government emblem. Genuine title deeds have distinct tactile features and printing quality that forgeries often fail to replicate. However, physical inspection alone is not sufficient — many modern forgeries are sophisticated enough to pass visual inspection.',
      'The second and most critical step is conducting an official search at the Ministry of Lands. This involves visiting the Ardhi House (Nairobi) or the relevant county lands office with the title deed details. An official search reveals the registered owner, any encumbrances (loans, caveats, or liens), and the property size and boundaries. The cost is approximately KES 500-1,000 and takes 2-5 working days.',
      'The third step is verifying the identity of the seller. Ask for their original national ID or passport and compare the details with the title deed. If the seller is a company, request their incorporation documents and director identification. Be wary of sellers who are reluctant to provide identification or who rush the transaction.',
      'Vestra AI verification service streamlines this entire process. By uploading your title deed and property documents, our AI cross-references the information with available land registry data, checks for document tampering, and generates a comprehensive Trust Report with a Trust Score. This can save you days of manual verification and catch inconsistencies that human inspection might miss.',
    ],
    author: 'Wanjiku Mwangi',
    role: 'CTO & Co-Founder',
    date: 'June 10, 2026',
    readTime: '12 min read',
    category: 'Property Guides',
    categoryColor: 'bg-emerald-50 text-emerald-700 border-emerald-200',
    gradient: 'from-emerald-500 to-emerald-700',
    related: ['ai-property-verification-how-it-works', 'first-time-home-buyer-guide-kenya'],
  },
  'ai-property-verification-how-it-works': {
    title: 'AI Property Verification: How Vestra Detects Fraud in Minutes',
    excerpt: 'Behind the scenes of Vestra AI verification technology.',
    content: [
      'Vestra AI verification technology represents a fundamental shift in how property fraud is detected in emerging markets. Our system combines three advanced AI technologies: computer vision, natural language processing (NLP), and anomaly detection algorithms, each playing a crucial role in the verification process.',
      'Computer Vision analyzes uploaded documents for signs of tampering or forgery. The system examines document structure, fonts, signatures, stamps, and security watermarks at a microscopic level. It can detect inconsistencies that would be invisible to the human eye, such as slight misalignments in official stamps, font inconsistencies, or digital manipulation artifacts.',
      'Natural Language Processing reads and interprets the text content of documents. It extracts key information such as property descriptions, owner names, title numbers, and legal encumbrances. The NLP engine cross-references this information across multiple documents to verify consistency. For example, it ensures the property description on a title deed matches the sale agreement and the listing description.',
      'The Anomaly Detection engine analyzes the complete property profile against Vestra database of verified properties. It checks for red flags such as duplicate listings, price anomalies (a property listed significantly below or above market value), suspicious agent patterns, and historical fraud indicators. This system learns continuously from new data, becoming more accurate over time.',
      'The entire process takes under 5 minutes and costs KES 500. The result is a comprehensive Trust Report with a Trust Score from 0-100, detailed findings on each verification check, and clear recommendations. For buyers, this means unprecedented visibility into property authenticity before committing funds.',
    ],
    author: 'Kevin Ochieng',
    role: 'CEO & Co-Founder',
    date: 'June 5, 2026',
    readTime: '10 min read',
    category: 'Technology',
    categoryColor: 'bg-purple-50 text-purple-700 border-purple-200',
    gradient: 'from-purple-500 to-purple-700',
    related: ['how-to-verify-property-title-deed-kenya', 'mpesa-real-estate-payments-kenya'],
  },
  'rental-property-management-tips-kenya': {
    title: 'Rental Property Management in Kenya: Tips for Landlords in 2026',
    excerpt: 'Essential tips for Kenyan landlords.',
    content: [
      'Managing rental properties in Kenya has evolved significantly. Modern landlords are leveraging technology to streamline operations, reduce vacancies, and maximize returns on their investments.',
      'Tenant screening remains the foundation of successful rental management. Beyond basic background checks, forward-thinking landlords are using digital platforms to verify tenant income, check rental history, and assess reliability. A thorough screening process dramatically reduces the risk of problematic tenants and costly evictions.',
      'Rent collection has been transformed by M-Pesa integration. Automated STK Push payments mean tenants can pay rent in seconds, and landlords receive instant notifications. Late payment rates drop by 60% when tenants can pay via mobile money. Vestra rental management platform automutes reminders, tracks payment history, and provides both parties with a transparent record.',
      'Maintenance management is often the most challenging aspect of being a landlord. A systematic approach with clear communication channels, documented procedures, and a network of reliable contractors is essential. Use digital tools to log maintenance requests, track response times, and maintain records for tax purposes.',
      'Understanding Kenya rental laws is non-negotiable. The Landlord and Tenant Act, rent control regulations, and county-specific bylaws all affect how you manage properties. Stay informed about your obligations regarding deposit handling, notice periods, eviction procedures, and habitability standards.',
    ],
    author: 'Grace Akinyi',
    role: 'Head of Operations',
    date: 'May 28, 2026',
    readTime: '7 min read',
    category: 'Landlord Tips',
    categoryColor: 'bg-amber-50 text-amber-700 border-amber-200',
    gradient: 'from-amber-500 to-amber-700',
    related: ['first-time-home-buyer-guide-kenya', 'kenya-real-estate-market-trends-2026'],
  },
  'first-time-home-buyer-guide-kenya': {
    title: 'First-Time Home Buyer Guide: Everything You Need to Know in Kenya',
    excerpt: 'A comprehensive guide for first-time home buyers in Kenya.',
    content: [
      'Buying your first home in Kenya is an exciting milestone, but it can also be overwhelming. This guide walks you through every step of the process, from financial preparation to final ownership.',
      'Start with your finances. Determine your budget by assessing your savings, income, and borrowing capacity. Most Kenyan banks offer mortgages covering 80-90% of the property value, with repayment periods of 5-20 years. The Kenya Mortgage Refinance Company (KMRC) offers competitive rates for first-time buyers. Factor in additional costs like stamp duty (2-4%), legal fees (1-2%), valuation fees (KES 5,000-15,000), and agent commissions.',
      'Choose your location carefully. Consider proximity to work, schools, healthcare, shopping, and public transport. Visit potential neighborhoods at different times of the day to assess traffic, noise levels, and security. Emerging areas often offer better value but may have infrastructure trade-offs.',
      'Property verification is non-negotiable. Always verify the title deed, conduct an official search at the Ministry of Lands, and consider using Vestra AI verification for an additional layer of protection. Never pay deposits without verified ownership. Fraudulent sellers often target first-time buyers precisely because they are less familiar with the verification process.',
      'Work with professionals. A qualified lawyer specializing in property law, a registered valuer, and a trusted real estate agent are essential partners. Vestra Verified Agents undergo background checks and are committed to ethical practices, giving first-time buyers added peace of mind.',
    ],
    author: 'Hassan Ali',
    role: 'Head of Product',
    date: 'May 20, 2026',
    readTime: '15 min read',
    category: 'Buyer Guides',
    categoryColor: 'bg-red-50 text-red-700 border-red-200',
    gradient: 'from-red-500 to-red-700',
    related: ['kenya-real-estate-market-trends-2026', 'how-to-verify-property-title-deed-kenya'],
  },
  'mpesa-real-estate-payments-kenya': {
    title: 'M-Pesa and Real Estate: How Digital Payments Are Transforming Property Transactions',
    excerpt: 'How M-Pesa integration is revolutionizing real estate payments in Kenya.',
    content: [
      'M-Pesa has transformed financial services in Kenya, and its impact on real estate is accelerating rapidly. From small rent payments to multi-million shilling property deposits, mobile money is reshaping how Kenyans transact in property markets.',
      'Rent collection has been the most visible change. Tenants can now pay rent via M-Pesa with a single tap, eliminating the need for cash transactions and physical receipt collection. Landlords appreciate the automatic record-keeping, instant confirmation, and reduced late payments. Vestra processes thousands of M-Pesa rental payments monthly, with 99.9% uptime.',
      'For property verification, M-Pesa integration means instant payment of verification fees. When you request a Vestra AI Trust Report, an STK Push is sent to your phone, you enter your PIN, and the verification process begins immediately. No bank queues, no card details to enter, no waiting for payment confirmation.',
      'Escrow services are being revolutionized by mobile money. Vestra Escrow holds transaction funds securely, releasing them only when all conditions are met. Buyers and sellers both benefit from the protection that a trusted intermediary provides, with the convenience of M-Pesa-based deposits and releases.',
      'The future of real estate payments in Kenya is undoubtedly mobile-first. As M-Pesa continues to evolve with features like M-Pesa Global for diaspora transactions and increased transaction limits, the real estate sector will benefit from even greater financial inclusion and transaction efficiency.',
    ],
    author: 'Wanjiku Mwangi',
    role: 'CTO & Co-Founder',
    date: 'May 15, 2026',
    readTime: '6 min read',
    category: 'Payments',
    categoryColor: 'bg-teal-50 text-teal-700 border-teal-200',
    gradient: 'from-teal-500 to-teal-700',
    related: ['ai-property-verification-how-it-works', 'rental-property-management-tips-kenya'],
  },
};

const ALL_SLUGS = Object.keys(POSTS_DATA);

export default function BlogPostPage() {
  const params = useParams();
  const router = useRouter();
  const slug = params?.slug as string;
  const [copied, setCopied] = useState(false);

  const post = POSTS_DATA[slug];

  useEffect(() => {
    if (post) {
      document.title = `${post.title} — Vestra Blog`;
    }
  }, [post]);

  // Loading state
  if (!post) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="flex items-center justify-center py-32">
          <div className="text-center">
            <Spinner size="lg" />
            <p className="text-gray-500 mt-4">Loading post...</p>
          </div>
        </div>
      </div>
    );
  }

  // Error state: post not found
  if (!slug || !POSTS_DATA[slug]) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="max-w-lg mx-auto px-4 py-32 text-center">
          <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <span className="text-3xl">404</span>
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-3">Post Not Found</h1>
          <p className="text-gray-500 mb-8">
            The blog post you are looking for could not be found. It may have been removed or the URL may be incorrect.
          </p>
          <Link href="/blog">
            <Button variant="outline">
              <ArrowLeft className="w-4 h-4" />
              Back to Blog
            </Button>
          </Link>
        </div>
      </div>
    );
  }

  const copyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const relatedPosts = post.related
    .filter((s) => POSTS_DATA[s])
    .map((s) => POSTS_DATA[s]);

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Back link */}
      <div className="bg-gray-50 border-b border-gray-100">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4">
          <Link
            href="/blog"
            className="inline-flex items-center gap-1.5 text-sm text-gray-500 hover:text-emerald-600 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Blog
          </Link>
        </div>
      </div>

      <article className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        {/* Header */}
        <header className="mb-10">
          <Badge className={post.categoryColor + ' mb-4'}>{post.category}</Badge>
          <h1 className="text-4xl lg:text-5xl font-bold text-gray-900 leading-tight mb-6">
            {post.title}
          </h1>
          <p className="text-xl text-gray-500 leading-relaxed mb-6">
            {post.excerpt}
          </p>
          <div className="flex flex-wrap items-center gap-6 text-sm text-gray-500 pb-6 border-b border-gray-100">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-xl flex items-center justify-center">
                <span className="text-white font-bold text-sm">
                  {post.author.split(' ').map((n) => n[0]).join('')}
                </span>
              </div>
              <div>
                <p className="font-medium text-gray-900">{post.author}</p>
                <p className="text-xs text-gray-400">{post.role}</p>
              </div>
            </div>
            <span className="flex items-center gap-1.5">
              <Calendar className="w-4 h-4" />
              {post.date}
            </span>
            <span className="flex items-center gap-1.5">
              <Clock className="w-4 h-4" />
              {post.readTime}
            </span>
          </div>
        </header>

        {/* Content */}
        <div className="prose prose-gray max-w-none">
          {post.content.map((paragraph, index) => (
            <p key={index} className="text-gray-700 leading-relaxed mb-6 text-lg">
              {paragraph}
            </p>
          ))}
        </div>

        {/* Share & Actions */}
        <div className="mt-12 pt-8 border-t border-gray-100">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-gray-500">Share this article:</span>
              <button className="p-2 rounded-xl hover:bg-blue-50 text-blue-500 transition-colors" aria-label="Share on Twitter/X">
                <ExternalLink className="w-5 h-5" />
              </button>
              <button className="p-2 rounded-xl hover:bg-blue-50 text-blue-700 transition-colors" aria-label="Share on Facebook">
                <Globe className="w-5 h-5" />
              </button>
              <button className="p-2 rounded-xl hover:bg-blue-50 text-blue-600 transition-colors" aria-label="Share on LinkedIn">
                <Share2 className="w-5 h-5" />
              </button>
              <button
                onClick={copyLink}
                className="p-2 rounded-xl hover:bg-gray-100 text-gray-500 transition-colors relative"
                aria-label="Copy link"
              >
                {copied ? <CheckCircle2 className="w-5 h-5 text-emerald-500" /> : <Copy className="w-5 h-5" />}
              </button>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="ghost" size="sm">
                <Heart className="w-4 h-4" />
                Like
              </Button>
              <Button variant="ghost" size="sm">
                <Bookmark className="w-4 h-4" />
                Save
              </Button>
            </div>
          </div>
        </div>

        {/* Author Card */}
        <div className="mt-12 bg-gray-50 rounded-3xl p-8 border border-gray-100">
          <div className="flex items-start gap-4">
            <div className="w-16 h-16 bg-gradient-to-br from-emerald-400 to-emerald-600 rounded-2xl flex items-center justify-center flex-shrink-0">
              <span className="text-white font-bold text-xl">
                {post.author.split(' ').map((n) => n[0]).join('')}
              </span>
            </div>
            <div>
              <h3 className="text-lg font-bold text-gray-900">{post.author}</h3>
              <p className="text-sm text-gray-500 mb-2">{post.role}</p>
              <p className="text-sm text-gray-600 leading-relaxed">
                {post.author} is a key member of the Vestra team, dedicated to making property transactions in Kenya
                more transparent, secure, and trustworthy through innovative technology and deep market expertise.
              </p>
            </div>
          </div>
        </div>

        {/* Related Posts */}
        {relatedPosts.length > 0 && (
          <div className="mt-16">
            <h2 className="text-2xl font-bold text-gray-900 mb-6">Related Articles</h2>
            <div className="grid md:grid-cols-2 gap-6">
              {relatedPosts.map((related) => (
                <Link
                  key={related.title}
                  href={`/blog/${ALL_SLUGS.find((s) => POSTS_DATA[s] === related)}`}
                  className="group bg-white rounded-2xl border border-gray-100 p-6 hover:shadow-md hover:-translate-y-0.5 transition-all duration-200"
                >
                  <Badge className={related.categoryColor + ' mb-3'}>{related.category}</Badge>
                  <h3 className="font-bold text-gray-900 mb-2 group-hover:text-emerald-700 transition-colors">
                    {related.title}
                  </h3>
                  <p className="text-sm text-gray-500 line-clamp-2">{related.excerpt}</p>
                </Link>
              ))}
            </div>
          </div>
        )}
      </article>

      {/* CTA */}
      <section className="bg-gray-50 py-16">
        <div className="max-w-3xl mx-auto text-center px-4">
          <h2 className="text-3xl font-bold text-gray-900 mb-3">Ready to Experience Vestra?</h2>
          <p className="text-gray-500 mb-8">
            Join thousands of Kenyans using Vestra to buy, sell, and rent property with confidence.
          </p>
          <div className="flex gap-4 justify-center flex-wrap">
            <Link href="/auth/register">
              <Button size="lg">Get Started Free</Button>
            </Link>
            <Link href="/market">
              <Button size="lg" variant="outline">Browse Properties</Button>
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
