'use client';

import Link from 'next/link';
import { getRoleTheme, normalizeRole } from '@/lib/roleThemes';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';

interface RoleBannerProps {
  title?: string;
  subtitle?: string;
  children?: React.ReactNode;
}

export default function RoleBanner({ title, subtitle, children }: RoleBannerProps) {
  const { user } = useAuthStore();
  const role = normalizeRole(user?.role);
  const theme = getRoleTheme(role);
  const firstName = user?.full_name?.split(' ')[0] || 'there';
  const hour = new Date().getHours();
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening';

  return (
    <div className={cn('relative overflow-hidden rounded-3xl p-6 lg:p-8 mb-8 bg-gradient-to-br', theme.gradient)}>
      {/* Decorative elements */}
      <div className="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxnIGZpbGw9IiNmZmYiIGZpbGwtb3BhY2l0eT0iMC4wMyI+PHBhdGggZD0iTTM2IDE4YzEuNjU3IDAgMy0xLjM0MyAzLTNzLTEuMzQzLTMtMy0zLTMgMS4zNDMtMyAzIDEuMzQzIDMgMyAzem0tMjQgMGMxLjY1NyAwIDMtMS4zNDMgMy0zcy0xLjM0My0zLTMtMy0zIDEuMzQzLTMgMyAxLjM0MyAzIDMgM3oiLz48L2c+PC9nPjwvc3ZnPg==')] opacity-30" />
      <div className={cn('absolute top-10 right-10 w-72 h-72 rounded-full blur-3xl', theme.glowColor)} />
      <div className="absolute -bottom-20 -left-20 w-96 h-96 bg-white/5 rounded-full blur-3xl" />

      <div className="relative z-10 flex flex-col lg:flex-row lg:items-center lg:justify-between gap-6">
        <div>
          <div className="flex items-center gap-3 mb-3">
            <span className="text-3xl">{theme.emoji}</span>
            <span className={cn('inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border bg-white/10 border-white/20 text-white/90')}>
              <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
              {role === 'buyer' ? 'Property Seeker' :
               role === 'seller' ? 'Property Owner' :
               role === 'landlord' ? 'Property Manager' :
               role === 'tenant' ? 'Renter' :
               role === 'agent' ? 'Real Estate Agent' : 'Administrator'}
            </span>
          </div>
          <h1 className="text-2xl lg:text-3xl font-bold text-white mb-2">
            {greeting}, <span className="text-white/90">{firstName}</span> 👋
          </h1>
          <p className="text-white/70 text-base max-w-xl">
            {title || getDefaultSubtitle(role)}
          </p>
        </div>
        {children && (
          <div className="flex gap-3 flex-shrink-0">
            {children}
          </div>
        )}
      </div>
    </div>
  );
}

function getDefaultSubtitle(role: string): string {
  switch (role) {
    case 'buyer': return 'Find your perfect property with AI-powered search and verified listings.';
    case 'seller': return 'Track your listings, manage inquiries, and close deals faster.';
    case 'landlord': return 'Manage your rental portfolio, collect rent, and keep units full.';
    case 'tenant': return 'Your rental at a glance — pay rent, request maintenance, stay informed.';
    case 'agent': return 'Manage listings, track leads, and grow your real estate business.';
    case 'admin': return 'Full system control — users, properties, verifications, and more.';
    default: return 'Welcome to your Vestra dashboard.';
  }
}
