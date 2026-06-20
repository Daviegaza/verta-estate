/**
 * Role-specific theme configuration for VESTRA dashboards.
 * Every role has a unique color identity so dashboards feel distinct.
 */

export type RoleSlug = 'buyer' | 'seller' | 'landlord' | 'tenant' | 'agent' | 'admin';

export interface RoleTheme {
  slug: RoleSlug;
  label: string;
  icon: string;              // lucide icon name
  emoji: string;
  primary: string;           // Tailwind bg class e.g. 'bg-blue-600'
  primaryLight: string;
  primaryText: string;
  secondary: string;
  accent: string;
  gradient: string;          // bg gradient for hero banners
  gradientLight: string;
  badge: string;             // badge styling
  statIconBg: string;
  statIconColor: string;
  sidebarBg: string;
  sidebarHover: string;
  sidebarActive: string;
  borderColor: string;
  glowColor: string;         // for decorative glows
}

export const ROLE_THEMES: Record<RoleSlug, RoleTheme> = {
  buyer: {
    slug: 'buyer',
    label: 'Buyer',
    icon: 'Search',
    emoji: '🏠',
    primary: 'bg-blue-600',
    primaryLight: 'bg-blue-50',
    primaryText: 'text-blue-600',
    secondary: 'text-sky-500',
    accent: 'bg-indigo-500',
    gradient: 'from-blue-950 via-blue-900 to-indigo-950',
    gradientLight: 'from-blue-600 to-blue-700',
    badge: 'bg-blue-100 text-blue-700 border-blue-200',
    statIconBg: 'bg-blue-50',
    statIconColor: 'text-blue-600',
    sidebarBg: 'bg-blue-50/30',
    sidebarHover: 'hover:bg-blue-50',
    sidebarActive: 'bg-blue-100 text-blue-700 border-blue-200',
    borderColor: 'border-blue-100',
    glowColor: 'bg-blue-500/10',
  },
  seller: {
    slug: 'seller',
    label: 'Seller',
    icon: 'TrendingUp',
    emoji: '💰',
    primary: 'bg-emerald-600',
    primaryLight: 'bg-emerald-50',
    primaryText: 'text-emerald-600',
    secondary: 'text-teal-500',
    accent: 'bg-green-500',
    gradient: 'from-gray-950 via-emerald-950 to-gray-900',
    gradientLight: 'from-emerald-600 to-emerald-700',
    badge: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    statIconBg: 'bg-emerald-50',
    statIconColor: 'text-emerald-600',
    sidebarBg: 'bg-emerald-50/30',
    sidebarHover: 'hover:bg-emerald-50',
    sidebarActive: 'bg-emerald-100 text-emerald-700 border-emerald-200',
    borderColor: 'border-emerald-100',
    glowColor: 'bg-emerald-500/10',
  },
  landlord: {
    slug: 'landlord',
    label: 'Landlord',
    icon: 'Building2',
    emoji: '🏢',
    primary: 'bg-violet-600',
    primaryLight: 'bg-violet-50',
    primaryText: 'text-violet-600',
    secondary: 'text-purple-400',
    accent: 'bg-fuchsia-500',
    gradient: 'from-violet-950 via-purple-950 to-fuchsia-950',
    gradientLight: 'from-violet-600 to-purple-700',
    badge: 'bg-violet-100 text-violet-700 border-violet-200',
    statIconBg: 'bg-violet-50',
    statIconColor: 'text-violet-600',
    sidebarBg: 'bg-violet-50/30',
    sidebarHover: 'hover:bg-violet-50',
    sidebarActive: 'bg-violet-100 text-violet-700 border-violet-200',
    borderColor: 'border-violet-100',
    glowColor: 'bg-violet-500/10',
  },
  tenant: {
    slug: 'tenant',
    label: 'Tenant',
    icon: 'Home',
    emoji: '🏡',
    primary: 'bg-orange-600',
    primaryLight: 'bg-orange-50',
    primaryText: 'text-orange-600',
    secondary: 'text-amber-500',
    accent: 'bg-yellow-500',
    gradient: 'from-orange-950 via-amber-950 to-yellow-950',
    gradientLight: 'from-orange-600 to-amber-600',
    badge: 'bg-orange-100 text-orange-700 border-orange-200',
    statIconBg: 'bg-orange-50',
    statIconColor: 'text-orange-600',
    sidebarBg: 'bg-orange-50/30',
    sidebarHover: 'hover:bg-orange-50',
    sidebarActive: 'bg-orange-100 text-orange-700 border-orange-200',
    borderColor: 'border-orange-100',
    glowColor: 'bg-orange-500/10',
  },
  agent: {
    slug: 'agent',
    label: 'Agent',
    icon: 'Briefcase',
    emoji: '🕴️',
    primary: 'bg-cyan-600',
    primaryLight: 'bg-cyan-50',
    primaryText: 'text-cyan-600',
    secondary: 'text-teal-500',
    accent: 'bg-sky-500',
    gradient: 'from-slate-950 via-cyan-950 to-slate-900',
    gradientLight: 'from-cyan-600 to-teal-600',
    badge: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    statIconBg: 'bg-cyan-50',
    statIconColor: 'text-cyan-600',
    sidebarBg: 'bg-cyan-50/30',
    sidebarHover: 'hover:bg-cyan-50',
    sidebarActive: 'bg-cyan-100 text-cyan-700 border-cyan-200',
    borderColor: 'border-cyan-100',
    glowColor: 'bg-cyan-500/10',
  },
  admin: {
    slug: 'admin',
    label: 'Admin',
    icon: 'Shield',
    emoji: '⚙️',
    primary: 'bg-slate-800',
    primaryLight: 'bg-slate-50',
    primaryText: 'text-slate-700',
    secondary: 'text-gray-500',
    accent: 'bg-red-500',
    gradient: 'from-slate-950 via-gray-950 to-slate-900',
    gradientLight: 'from-slate-700 to-slate-800',
    badge: 'bg-slate-100 text-slate-700 border-slate-200',
    statIconBg: 'bg-slate-50',
    statIconColor: 'text-slate-600',
    sidebarBg: 'bg-slate-50/30',
    sidebarHover: 'hover:bg-slate-50',
    sidebarActive: 'bg-slate-200 text-slate-800 border-slate-300',
    borderColor: 'border-slate-100',
    glowColor: 'bg-slate-500/10',
  },
};

/** Get theme for a role, defaulting to buyer */
export function getRoleTheme(role?: string): RoleTheme {
  const slug = (role || 'buyer') as RoleSlug;
  return ROLE_THEMES[slug] || ROLE_THEMES.buyer;
}

/** Map backend role names to RoleSlug */
export function normalizeRole(role?: string): RoleSlug {
  if (!role) return 'buyer';
  if (role === 'super_admin') return 'admin';
  return (role as RoleSlug) || 'buyer';
}

/** Get the dashboard route for a given role */
export function getDashboardRoute(role?: string): string {
  const r = normalizeRole(role);
  if (r === 'admin') return '/admin';
  return `/dashboard/${r}`;
}
