import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Verified Property Agents Kenya | Vestra',
  description: 'Find verified real estate agents and agencies across Kenya. Compare agent ratings, reviews, successful deals, and license verification — all AI-powered.',
  openGraph: {
    title: 'Verified Property Agents Kenya | Vestra',
    description: 'Find verified real estate agents across Kenya with AI-powered trust scores and license verification.',
  },
}

export default function AgentsLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
