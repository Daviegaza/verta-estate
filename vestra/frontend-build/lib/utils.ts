import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function setCookie(name: string, value: string, days = 365) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${encodeURIComponent(name)}=${encodeURIComponent(value)}; expires=${expires}; path=/; SameSite=Lax`;
}

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(amount: number, currency = 'KES'): string {
  if (currency === 'KES') {
    return `KES ${amount.toLocaleString('en-KE')}`;
  }
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
  }).format(amount);
}

export function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-KE', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

export function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 7) return formatDate(dateString);
  if (days > 0) return `${days}d ago`;
  if (hours > 0) return `${hours}h ago`;
  if (minutes > 0) return `${minutes}m ago`;
  return 'just now';
}

export function getTrustScoreColor(score: number): string {
  if (score >= 80) return 'text-emerald-600';
  if (score >= 60) return 'text-amber-600';
  return 'text-red-600';
}

export function getTrustScoreBg(score: number): string {
  if (score >= 80) return 'bg-emerald-50 border-emerald-200';
  if (score >= 60) return 'bg-amber-50 border-amber-200';
  return 'bg-red-50 border-red-200';
}

export function getBadgeColor(badge?: string): string {
  switch (badge) {
    case 'platinum': return 'bg-purple-100 text-purple-800 border-purple-300';
    case 'gold': return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    case 'silver': return 'bg-gray-100 text-gray-700 border-gray-300';
    case 'bronze': return 'bg-orange-100 text-orange-800 border-orange-300';
    default: return 'bg-gray-100 text-gray-500 border-gray-200';
  }
}

export function getPropertyTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    residential: 'Residential',
    commercial: 'Commercial',
    land: 'Land',
    industrial: 'Industrial',
    agricultural: 'Agricultural',
    student_housing: 'Student Housing',
    short_stay: 'Short Stay',
  };
  return labels[type] || type;
}

export function getListingTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    sale: 'For Sale',
    rent: 'For Rent',
    lease: 'For Lease',
  };
  return labels[type] || type;
}

export function truncateText(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength).trim() + '...';
}

export const KENYA_CITIES = [
  'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Eldoret',
  'Thika', 'Kitengela', 'Rongai', 'Karen', 'Westlands',
  'Kiambu', 'Machakos', 'Meru', 'Nyeri', 'Ruiru',
  'Ngong', 'Athi River', 'Limuru', 'Kikuyu', 'Kahawa',
];

export const KENYA_COUNTIES = [
  'Nairobi', 'Mombasa', 'Kisumu', 'Nakuru', 'Uasin Gishu',
  'Kiambu', 'Machakos', 'Kajiado', 'Meru', 'Nyeri',
  'Murang\'a', 'Kirinyaga', 'Laikipia', 'Nyandarua', 'Embu',
];

export const AMENITIES_OPTIONS = [
  'Parking', 'Security', 'CCTV', 'Electric Fence', 'Borehole',
  'Swimming Pool', 'Gym', 'Balcony', 'Garden', 'Backup Generator',
  'Solar Power', 'Fibre Internet', 'Lift/Elevator', 'Servant Quarter',
  'Paved Road', 'Water Tank', 'Guard', 'Intercom', 'Air Conditioning',
];
