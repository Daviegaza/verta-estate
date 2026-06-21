'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import Navbar from '@/components/layout/navbar';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/card';
import { Spinner } from '@/components/ui/card';
import {
  ShieldCheck, Bell, CheckCheck, Star, MessageCircle, Heart,
  TrendingUp, AlertCircle, Home, Building2, UserPlus, CreditCard,
  Clock, X, Filter, CheckCircle2, Settings, ChevronRight, Mail,
  Inbox, Archive
} from 'lucide-react';
import { formatRelativeTime } from '@/lib/utils';

// Notification types with their styling
const NOTIFICATION_ICONS: Record<string, { icon: React.ElementType; color: string }> = {
  verification: { icon: ShieldCheck, color: 'text-emerald-600 bg-emerald-50' },
  message: { icon: MessageCircle, color: 'text-blue-600 bg-blue-50' },
  listing: { icon: Building2, color: 'text-purple-600 bg-purple-50' },
  favorite: { icon: Heart, color: 'text-red-600 bg-red-50' },
  review: { icon: Star, color: 'text-amber-600 bg-amber-50' },
  payment: { icon: CreditCard, color: 'text-teal-600 bg-teal-50' },
  alert: { icon: AlertCircle, color: 'text-rose-600 bg-rose-50' },
  agent: { icon: UserPlus, color: 'text-indigo-600 bg-indigo-50' },
  property: { icon: Home, color: 'text-emerald-600 bg-emerald-50' },
  system: { icon: Bell, color: 'text-gray-600 bg-gray-50' },
};

const NOTIFICATION_TYPES = [
  { value: 'all', label: 'All' },
  { value: 'unread', label: 'Unread' },
  { value: 'verification', label: 'Verification' },
  { value: 'message', label: 'Messages' },
  { value: 'listing', label: 'Listings' },
  { value: 'payment', label: 'Payments' },
  { value: 'review', label: 'Reviews' },
  { value: 'alert', label: 'Alerts' },
  { value: 'system', label: 'System' },
];

// Mock notifications
const MOCK_NOTIFICATIONS = [
  {
    id: 'n1',
    type: 'verification',
    title: 'Property Verification Complete',
    message: 'Your AI Trust Report for 2-bedroom apartment in Kilimani is ready. Trust Score: 92/100 — Low Risk.',
    timestamp: '2026-06-21T10:30:00',
    read: false,
    actionable: true,
    actionLabel: 'View Report',
    actionHref: '/verify',
  },
  {
    id: 'n2',
    type: 'message',
    title: 'New Message from James Mwangi',
    message: 'James Mwangi sent you a message about your property listing: "Is this property still available for viewing this weekend?"',
    timestamp: '2026-06-21T09:15:00',
    read: false,
    actionable: true,
    actionLabel: 'Reply',
    actionHref: '/messages',
  },
  {
    id: 'n3',
    type: 'listing',
    title: 'Your Listing is Live!',
    message: '3-bedroom house in Nyali, Mombasa is now live and visible to buyers. You have 3 inquiries waiting.',
    timestamp: '2026-06-20T16:45:00',
    read: false,
    actionable: true,
    actionLabel: 'View Listing',
    actionHref: '/properties/n3',
  },
  {
    id: 'n4',
    type: 'payment',
    title: 'Rent Payment Received',
    message: 'You received KES 35,000 rent payment for Apartment 4B, Westlands. Tenant: Mary Wanjiku.',
    timestamp: '2026-06-20T14:20:00',
    read: true,
    actionable: false,
  },
  {
    id: 'n5',
    type: 'review',
    title: 'New 5-Star Review',
    message: 'Sarah Odhiambo left you a 5-star review: "Excellent agent! Very professional and responsive. Highly recommended."',
    timestamp: '2026-06-20T11:00:00',
    read: true,
    actionable: true,
    actionLabel: 'View Review',
    actionHref: '/dashboard',
  },
  {
    id: 'n6',
    type: 'alert',
    title: 'Suspicious Activity Detected',
    message: 'Vestra AI detected a duplicate listing of your property in Kitengela. A fraudulent agent may be using your photos.',
    timestamp: '2026-06-19T22:30:00',
    read: false,
    actionable: true,
    actionLabel: 'Investigate',
    actionHref: '/verify',
  },
  {
    id: 'n7',
    type: 'agent',
    title: 'Agent Application Approved',
    message: 'Congratulations! Your Verified Agent application has been approved. Your badge is now active on all your listings.',
    timestamp: '2026-06-19T15:10:00',
    read: true,
    actionable: true,
    actionLabel: 'Go to Dashboard',
    actionHref: '/dashboard',
  },
  {
    id: 'n8',
    type: 'verification',
    title: 'Verification Expiring Soon',
    message: 'Your property verification for Plot 123, Ruiru will expire in 7 days. Renew to keep your Verified badge active.',
    timestamp: '2026-06-18T09:00:00',
    read: true,
    actionable: true,
    actionLabel: 'Renew Now',
    actionHref: '/verify',
  },
  {
    id: 'n9',
    type: 'system',
    title: 'Terms of Service Updated',
    message: 'We have updated our Terms of Service. Please review the changes by June 30, 2026 to continue using Vestra.',
    timestamp: '2026-06-17T12:00:00',
    read: true,
    actionable: true,
    actionLabel: 'Review Changes',
    actionHref: '/terms',
  },
  {
    id: 'n10',
    type: 'favorite',
    title: 'Property Saved: Karen Luxury Home',
    message: 'You saved "6-bedroom mansion in Karen, KES 45M" to your favorites. The price has dropped by KES 2,000,000.',
    timestamp: '2026-06-16T18:45:00',
    read: true,
    actionable: true,
    actionLabel: 'View Property',
    actionHref: '/properties/10',
  },
  {
    id: 'n11',
    type: 'payment',
    title: 'Subscription Renewed',
    message: 'Your Premium Agent subscription has been renewed. Next billing date: July 21, 2026. KES 2,500 charged.',
    timestamp: '2026-06-16T10:30:00',
    read: true,
    actionable: false,
  },
  {
    id: 'n12',
    type: 'message',
    title: 'New Inquiry from Buyer',
    message: 'A buyer is interested in your listing "2-bedroom apartment in Kilimani" and would like to schedule a viewing.',
    timestamp: '2026-06-15T14:00:00',
    read: true,
    actionable: true,
    actionLabel: 'Respond',
    actionHref: '/messages',
  },
];

export default function NotificationsPage() {
  useEffect(() => {
    document.title = 'Notifications — Vestra';
  }, []);

  const [filter, setFilter] = useState('all');
  const [isLoading, setIsLoading] = useState(true);

  // Simulate loading
  useEffect(() => {
    const timer = setTimeout(() => setIsLoading(false), 800);
    return () => clearTimeout(timer);
  }, []);

  const filteredNotifications = MOCK_NOTIFICATIONS.filter((n) => {
    if (filter === 'unread') return !n.read;
    if (filter === 'all') return true;
    return n.type === filter;
  });

  const unreadCount = MOCK_NOTIFICATIONS.filter((n) => !n.read).length;
  const markAllAsRead = () => {
    // In production: API call to mark all as read
    console.log('Mark all as read');
  };

  return (
    <div className="min-h-screen bg-white">
      <Navbar />

      {/* Page Header */}
      <div className="bg-white border-b border-gray-100">
        <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center gap-3 mb-1">
                <h1 className="text-3xl font-bold text-gray-900">Notifications</h1>
                {unreadCount > 0 && (
                  <Badge variant="danger" className="text-sm px-3 py-0.5">
                    {unreadCount} new
                  </Badge>
                )}
              </div>
              <p className="text-gray-500 text-sm">Stay updated on your properties, messages, and activity.</p>
            </div>
            <div className="flex items-center gap-2">
              {unreadCount > 0 && (
                <Button variant="outline" size="sm" onClick={markAllAsRead}>
                  <CheckCheck className="w-4 h-4" />
                  Mark All Read
                </Button>
              )}
              <Link href="/settings/notifications">
                <Button variant="ghost" size="sm">
                  <Settings className="w-4 h-4" />
                  Preferences
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="bg-gray-50 border-b border-gray-100 overflow-x-auto">
        <div className="max-w-5xl mx-auto px-4 sm:px-6">
          <div className="flex gap-1 py-3">
            {NOTIFICATION_TYPES.map((type) => (
              <button
                key={type.value}
                onClick={() => setFilter(type.value)}
                className={`whitespace-nowrap px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                  filter === type.value
                    ? 'bg-emerald-600 text-white'
                    : 'text-gray-600 hover:bg-white hover:text-gray-900'
                }`}
              >
                {type.label}
                {type.value === 'unread' && unreadCount > 0 && (
                  <span className="ml-1.5 w-4 h-4 bg-red-500 text-white text-[10px] rounded-full inline-flex items-center justify-center">
                    {unreadCount}
                  </span>
                )}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Notifications List */}
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-center">
              <Spinner size="lg" />
              <p className="text-gray-500 text-sm mt-4">Loading notifications...</p>
            </div>
          </div>
        ) : filteredNotifications.length > 0 ? (
          <div className="space-y-2">
            {filteredNotifications.map((notification) => {
              const typeInfo = NOTIFICATION_ICONS[notification.type] || NOTIFICATION_ICONS.system;
              const IconComponent = typeInfo.icon;

              return (
                <div
                  key={notification.id}
                  className={`group rounded-2xl border p-5 transition-all duration-200 hover:shadow-sm ${
                    notification.read
                      ? 'bg-white border-gray-100'
                      : 'bg-emerald-50/40 border-emerald-200/60'
                  }`}
                >
                  <div className="flex gap-4">
                    {/* Icon */}
                    <div className={`flex-shrink-0 w-11 h-11 rounded-xl flex items-center justify-center ${typeInfo.color}`}>
                      <IconComponent className="w-5 h-5" />
                    </div>

                    {/* Content */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <h3 className={`text-sm ${notification.read ? 'font-medium text-gray-900' : 'font-semibold text-gray-900'}`}>
                              {notification.title}
                            </h3>
                            {!notification.read && (
                              <span className="w-2 h-2 bg-emerald-500 rounded-full flex-shrink-0" />
                            )}
                          </div>
                          <p className="text-sm text-gray-600 mt-1 leading-relaxed">
                            {notification.message}
                          </p>
                        </div>
                        <span className="text-xs text-gray-400 whitespace-nowrap flex-shrink-0 mt-0.5">
                          {formatRelativeTime(notification.timestamp)}
                        </span>
                      </div>

                      {/* Actions */}
                      {notification.actionable && (
                        <div className="mt-3 flex items-center gap-2">
                          <Link href={notification.actionHref || '#'}>
                            <Button size="sm" variant="outline" className="text-xs">
                              {notification.actionLabel || 'View Details'}
                              <ChevronRight className="w-3 h-3" />
                            </Button>
                          </Link>
                          <button className="p-1.5 text-gray-300 hover:text-gray-500 transition-colors opacity-0 group-hover:opacity-100">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-gray-100 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <Bell className="w-8 h-8 text-gray-300" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">No notifications yet</h3>
            <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
              {filter === 'unread'
                ? 'You have no unread notifications. Check back later for updates.'
                : 'You will see notifications here when there is activity on your properties, messages, and account.'}
            </p>
            {filter !== 'all' && (
              <Button variant="outline" size="sm" onClick={() => setFilter('all')}>
                View All Notifications
              </Button>
            )}
          </div>
        )}

        {/* Empty state for error */}
        {!isLoading && filteredNotifications.length === 0 && filter !== 'unread' && (
          <div className="text-center py-20">
            <div className="w-16 h-16 bg-red-50 rounded-2xl flex items-center justify-center mx-auto mb-6">
              <AlertCircle className="w-8 h-8 text-red-300" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Could not load notifications</h3>
            <p className="text-gray-500 text-sm mb-6 max-w-sm mx-auto">
              There was a problem loading your notifications. Please try again.
            </p>
            <Button onClick={() => window.location.reload()}>
              Try Again
            </Button>
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-gray-950 text-gray-400 py-16 mt-8">
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
