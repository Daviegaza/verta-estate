'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/card';
import {
  ShieldCheck, Send, MapPin, Phone, Mail, Clock, MessageCircle,
  ChevronRight, CheckCircle2, AlertCircle, Building2
} from 'lucide-react';

const OFFICES = [
  {
    city: 'Nairobi',
    address: 'Bishop Magua Centre, Ngong Road',
    location: 'Upper Hill, Nairobi',
    phone: '+254 700 123 456',
    email: 'nairobi@vestra.co.ke',
    hours: 'Mon–Fri: 8:00 AM – 6:00 PM',
    isHeadquarters: true,
  },
  {
    city: 'Mombasa',
    address: 'Mombasa Trade Centre, Nkrumah Road',
    location: 'Mombasa CBD',
    phone: '+254 700 123 457',
    email: 'mombasa@vestra.co.ke',
    hours: 'Mon–Fri: 8:00 AM – 5:30 PM',
    isHeadquarters: false,
  },
  {
    city: 'Kisumu',
    address: 'Kisumu City Centre, Oginga Odinga Road',
    location: 'Kisumu CBD',
    phone: '+254 700 123 458',
    email: 'kisumu@vestra.co.ke',
    hours: 'Mon–Fri: 8:00 AM – 5:30 PM',
    isHeadquarters: false,
  },
];

const CONTACT_SUBJECTS = [
  'General Inquiry',
  'Property Verification Support',
  'Account Support',
  'Listing Assistance',
  'Payment Issue',
  'Agent Application',
  'Partnership Opportunity',
  'Report a Problem',
  'Media Inquiry',
  'Other',
];

export default function ContactPage() {
  useEffect(() => {
    document.title = 'Contact Us — Vestra | Get in Touch';
  }, []);

  const [formData, setFormData] = useState({
    name: '',
    email: '',
    subject: '',
    message: '',
  });
  const [formErrors, setFormErrors] = useState<Record<string, string>>({});
  const [submitted, setSubmitted] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const validate = () => {
    const errors: Record<string, string> = {};
    if (!formData.name.trim()) errors.name = 'Name is required';
    if (!formData.email.trim()) errors.email = 'Email is required';
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) errors.email = 'Please enter a valid email';
    if (!formData.subject) errors.subject = 'Please select a subject';
    if (!formData.message.trim()) errors.message = 'Message is required';
    else if (formData.message.trim().length < 10) errors.message = 'Message must be at least 10 characters';
    return errors;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const errors = validate();
    setFormErrors(errors);
    if (Object.keys(errors).length > 0) return;

    setIsSubmitting(true);
    // Simulate API call
    await new Promise((resolve) => setTimeout(resolve, 1500));
    setIsSubmitting(false);
    setSubmitted(true);
  };

  if (submitted) {
    return (
      <div className="min-h-screen bg-white">
        <Navbar />
        <div className="max-w-lg mx-auto px-4 py-32 text-center">
          <div className="w-16 h-16 bg-emerald-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <CheckCircle2 className="w-8 h-8 text-emerald-600" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-3">Message Sent!</h1>
          <p className="text-gray-500 mb-8">
            Thank you for reaching out. Our team will get back to you within 24 hours.
          </p>
          <Link href="/">
            <Button variant="outline">Back to Home</Button>
          </Link>
        </div>
      </div>
    );
  }

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
            <h1 className="text-5xl lg:text-6xl font-bold leading-tight mb-6 animate-fade-in-up">
              Get in Touch
            </h1>
            <p className="text-xl text-gray-300 leading-relaxed mb-4 max-w-2xl animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
              Have a question, feedback, or need help? We would love to hear from you. Our team typically responds within 24 hours.
            </p>
          </div>
        </div>
      </section>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-16">
        <div className="grid lg:grid-cols-3 gap-12">
          {/* Contact Form */}
          <div className="lg:col-span-2">
            <Card className="p-8">
              <h2 className="text-2xl font-bold text-gray-900 mb-6">Send Us a Message</h2>
              <form onSubmit={handleSubmit} className="space-y-5">
                <div className="grid sm:grid-cols-2 gap-5">
                  <Input
                    label="Full Name"
                    placeholder="John Kamau"
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    error={formErrors.name}
                    required
                  />
                  <Input
                    label="Email Address"
                    type="email"
                    placeholder="john@example.com"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    error={formErrors.email}
                    required
                  />
                </div>

                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Subject <span className="text-red-500 ml-1">*</span>
                  </label>
                  <select
                    value={formData.subject}
                    onChange={(e) => setFormData({ ...formData, subject: e.target.value })}
                    className={`block w-full rounded-xl border ${
                      formErrors.subject ? 'border-red-400' : 'border-gray-200'
                    } bg-white px-4 py-2.5 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all duration-200`}
                  >
                    <option value="">Select a subject</option>
                    {CONTACT_SUBJECTS.map((s) => (
                      <option key={s} value={s}>{s}</option>
                    ))}
                  </select>
                  {formErrors.subject && (
                    <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">{formErrors.subject}</p>
                  )}
                </div>

                <div className="w-full">
                  <label className="block text-sm font-medium text-gray-700 mb-1.5">
                    Message <span className="text-red-500 ml-1">*</span>
                  </label>
                  <textarea
                    value={formData.message}
                    onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                    rows={5}
                    placeholder="Tell us how we can help you..."
                    className={`block w-full rounded-xl border ${
                      formErrors.message ? 'border-red-400' : 'border-gray-200'
                    } bg-white px-4 py-2.5 text-sm text-gray-900 placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all duration-200 resize-none`}
                  />
                  {formErrors.message && (
                    <p className="mt-1.5 text-xs text-red-500 flex items-center gap-1">{formErrors.message}</p>
                  )}
                </div>

                <Button type="submit" loading={isSubmitting} className="w-full sm:w-auto">
                  <Send className="w-4 h-4" />
                  {isSubmitting ? 'Sending...' : 'Send Message'}
                </Button>
              </form>
            </Card>
          </div>

          {/* Contact Info */}
          <div className="space-y-6">
            {/* Quick Contacts */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Quick Contact</h3>
              <div className="space-y-4">
                <a href="tel:+254700123456" className="flex items-center gap-3 text-sm text-gray-600 hover:text-emerald-600 transition-colors">
                  <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Phone className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Phone</p>
                    <p>+254 700 123 456</p>
                  </div>
                </a>
                <a href="mailto:support@vestra.co.ke" className="flex items-center gap-3 text-sm text-gray-600 hover:text-emerald-600 transition-colors">
                  <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Mail className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Email</p>
                    <p>support@vestra.co.ke</p>
                  </div>
                </a>
                <div className="flex items-center gap-3 text-sm text-gray-600">
                  <div className="w-10 h-10 bg-emerald-50 rounded-xl flex items-center justify-center flex-shrink-0">
                    <Clock className="w-5 h-5 text-emerald-600" />
                  </div>
                  <div>
                    <p className="font-medium text-gray-900">Hours</p>
                    <p>Mon–Fri: 8 AM – 6 PM</p>
                  </div>
                </div>
              </div>
            </Card>

            {/* Other Help Options */}
            <Card className="p-6">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Other Help Options</h3>
              <div className="space-y-3">
                <Link
                  href="/faq"
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <MessageCircle className="w-5 h-5 text-gray-400" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">Visit FAQ</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500" />
                </Link>
                <Link
                  href="/help"
                  className="flex items-center justify-between p-3 rounded-xl hover:bg-gray-50 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    <Building2 className="w-5 h-5 text-gray-400" />
                    <span className="text-sm text-gray-700 group-hover:text-gray-900">Help Center</span>
                  </div>
                  <ChevronRight className="w-4 h-4 text-gray-300 group-hover:text-gray-500" />
                </Link>
              </div>
            </Card>
          </div>
        </div>

        {/* Office Locations */}
        <div className="mt-20">
          <div className="text-center mb-12">
            <Badge variant="success" className="mb-4">Our Offices</Badge>
            <h2 className="text-3xl font-bold text-gray-900 mb-3">Visit Us in Person</h2>
            <p className="text-gray-500">We have offices across Kenya to serve you better</p>
          </div>
          <div className="grid md:grid-cols-3 gap-6 stagger-fade-in">
            {OFFICES.map((office) => (
              <Card key={office.city} className="p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 bg-emerald-50 rounded-2xl flex items-center justify-center">
                    <MapPin className="w-6 h-6 text-emerald-600" />
                  </div>
                  {office.isHeadquarters && (
                    <Badge variant="success">Headquarters</Badge>
                  )}
                </div>
                <h3 className="text-xl font-bold text-gray-900 mb-1">{office.city}</h3>
                <p className="text-sm text-gray-500 mb-4">{office.address}</p>
                <div className="space-y-2 text-sm">
                  <div className="flex items-center gap-2 text-gray-600">
                    <Phone className="w-4 h-4 text-gray-400" />
                    {office.phone}
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <Mail className="w-4 h-4 text-gray-400" />
                    {office.email}
                  </div>
                  <div className="flex items-center gap-2 text-gray-600">
                    <Clock className="w-4 h-4 text-gray-400" />
                    {office.hours}
                  </div>
                </div>
              </Card>
            ))}
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
