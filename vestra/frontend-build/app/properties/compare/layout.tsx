import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Compare Properties | Vestra',
  description: 'Compare up to 4 properties side-by-side on Vestra. Analyze price, size, bedrooms, bathrooms, amenities, trust scores, and more to find your ideal property in Kenya.',
  robots: { index: false, follow: true },
  openGraph: {
    title: 'Compare Properties | Vestra',
    description: 'Compare properties side-by-side on Vestra. Make informed decisions with AI-verified trust scores.',
  },
}

export default function CompareLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
