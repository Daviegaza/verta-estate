import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Property Market Kenya | Vestra',
  description: 'Browse properties for sale and rent across Kenya. AI-verified listings with trust scores, neighborhood insights, and M-Pesa-ready transactions.',
  openGraph: {
    title: 'Property Market Kenya | Vestra',
    description: 'Browse properties for sale and rent across Kenya with AI-verified trust scores.',
  },
}

export default function MarketLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
