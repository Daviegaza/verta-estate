'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { ChevronRight, Home } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BreadcrumbItem {
  label: string
  href?: string
  icon?: React.ReactNode
}

interface BreadcrumbProps {
  items?: BreadcrumbItem[]
  /** Auto-generate from pathname */
  auto?: boolean
  /** Custom label map for path segments */
  labels?: Record<string, string>
  className?: string
  homeHref?: string
}

const DEFAULT_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  market: 'Market',
  properties: 'Properties',
  admin: 'Admin',
  settings: 'Settings',
  profile: 'Profile',
  messages: 'Messages',
  notifications: 'Notifications',
  favorites: 'Favorites',
  wallet: 'Wallet',
  subscriptions: 'Subscriptions',
  agents: 'Agents',
  enterprise: 'Enterprise',
  'kyc': 'KYC Verification',
  security: 'Security',
  help: 'Help',
  about: 'About',
  contact: 'Contact',
  blog: 'Blog',
  faq: 'FAQ',
  terms: 'Terms',
  privacy: 'Privacy',
  verify: 'Verify Property',
  new: 'New',
  edit: 'Edit',
  compare: 'Compare',
  reports: 'Reports',
  disputes: 'Disputes',
  escrow: 'Escrow',
  rentals: 'Rentals',
  tenants: 'Tenants',
  maintenance: 'Maintenance',
  'trust-safety': 'Trust & Safety',
  'title-chain': 'Title Chain',
  payouts: 'Payouts',
  coupons: 'Coupons',
  referrals: 'Referrals',
  monitoring: 'Monitoring',
  'forgot-password': 'Forgot Password',
  register: 'Register',
  login: 'Login',
}

export default function Breadcrumb({
  items,
  auto = true,
  labels = {},
  className,
  homeHref = '/',
}: BreadcrumbProps) {
  const pathname = usePathname()
  const mergedLabels = { ...DEFAULT_LABELS, ...labels }

  // Auto-generate breadcrumbs from pathname
  let crumbs: BreadcrumbItem[] = []

  if (items) {
    crumbs = items
  } else if (auto) {
    const segments = pathname.split('/').filter(Boolean)

    // Remove locale prefix (en, sw)
    const isLocale = segments[0]?.length === 2
    const pathSegments = isLocale ? segments.slice(1) : segments

    crumbs = pathSegments.map((segment, index) => {
      const path = '/' + (isLocale ? segments[0] + '/' : '') + pathSegments.slice(0, index + 1).join('/')
      const label = mergedLabels[segment] || segment
        .replace(/-/g, ' ')
        .replace(/\b\w/g, (c) => c.toUpperCase())

      return {
        label,
        href: index < pathSegments.length - 1 ? path : undefined,
      }
    })
  }

  if (crumbs.length === 0) return null

  return (
    <nav
      aria-label="Breadcrumb"
      className={cn(
        'flex items-center gap-1.5 text-sm py-3 px-1 overflow-x-auto scrollbar-none',
        'animate-fade-in-up',
        className,
      )}
    >
      {/* Home link */}
      <Link
        href={homeHref}
        className="flex items-center gap-1 text-gray-400 hover:text-emerald-500
          dark:text-gray-500 dark:hover:text-emerald-400 transition-colors duration-200 shrink-0"
        aria-label="Home"
      >
        <Home className="w-3.5 h-3.5" />
      </Link>

      {crumbs.map((crumb, index) => (
        <div key={crumb.label} className="flex items-center gap-1.5 shrink-0">
          <ChevronRight className="w-3.5 h-3.5 text-gray-300 dark:text-gray-600" />

          {crumb.href ? (
            <Link
              href={crumb.href}
              className="text-gray-400 hover:text-emerald-500 dark:text-gray-500
                dark:hover:text-emerald-400 transition-colors duration-200
                whitespace-nowrap max-w-[150px] truncate"
            >
              {crumb.icon && <span className="mr-1 inline-flex align-middle">{crumb.icon}</span>}
              {crumb.label}
            </Link>
          ) : (
            <span className="text-gray-900 dark:text-gray-100 font-medium
              whitespace-nowrap max-w-[150px] truncate"
            >
              {crumb.icon && <span className="mr-1 inline-flex align-middle">{crumb.icon}</span>}
              {crumb.label}
            </span>
          )}
        </div>
      ))}
    </nav>
  )
}
