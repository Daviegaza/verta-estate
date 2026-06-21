import type { Metadata } from 'next'

export const dynamic = 'force-dynamic';

export const metadata: Metadata = {
  title: 'Enterprise API | Vestra',
  description: 'Enterprise API access for banks, SACCOs, and insurers. API keys, webhooks, and usage analytics.',
}

export default function EnterpriseLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
