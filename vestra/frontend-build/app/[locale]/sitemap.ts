import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'https://vestra.co.ke'
  const now = new Date()

  return [
    // ── Core Pages ──
    { url: baseUrl, lastModified: now, changeFrequency: 'daily', priority: 1 },
    { url: `${baseUrl}/market`, lastModified: now, changeFrequency: 'hourly', priority: 1 },
    { url: `${baseUrl}/verify`, lastModified: now, changeFrequency: 'daily', priority: 0.9 },

    // ── Auth Pages ──
    { url: `${baseUrl}/auth/login`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${baseUrl}/auth/register`, lastModified: now, changeFrequency: 'monthly', priority: 0.7 },
    { url: `${baseUrl}/auth/forgot-password`, lastModified: now, changeFrequency: 'monthly', priority: 0.3 },

    // ── Dashboard Pages ──
    { url: `${baseUrl}/dashboard`, lastModified: now, changeFrequency: 'weekly', priority: 0.8 },
    { url: `${baseUrl}/dashboard/buyer`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${baseUrl}/dashboard/seller`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${baseUrl}/dashboard/landlord`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${baseUrl}/dashboard/tenant`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${baseUrl}/dashboard/agent`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },

    // ── Property Pages ──
    { url: `${baseUrl}/properties/new`, lastModified: now, changeFrequency: 'weekly', priority: 0.6 },
    { url: `${baseUrl}/properties/my`, lastModified: now, changeFrequency: 'weekly', priority: 0.6 },
    { url: `${baseUrl}/properties/compare`, lastModified: now, changeFrequency: 'daily', priority: 0.7 },

    // ── Agent Directory ──
    { url: `${baseUrl}/agents`, lastModified: now, changeFrequency: 'daily', priority: 0.8 },
    { url: `${baseUrl}/agents/directory`, lastModified: now, changeFrequency: 'daily', priority: 0.7 },

    // ── Enterprise ──
    { url: `${baseUrl}/enterprise`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${baseUrl}/enterprise/keys`, lastModified: now, changeFrequency: 'weekly', priority: 0.5 },

    // ── Subscriptions ──
    { url: `${baseUrl}/subscription`, lastModified: now, changeFrequency: 'weekly', priority: 0.7 },
    { url: `${baseUrl}/subscription/manage`, lastModified: now, changeFrequency: 'weekly', priority: 0.5 },

    // ── User Pages ──
    { url: `${baseUrl}/settings`, lastModified: now, changeFrequency: 'monthly', priority: 0.4 },
    { url: `${baseUrl}/settings/security`, lastModified: now, changeFrequency: 'monthly', priority: 0.4 },
    { url: `${baseUrl}/settings/kyc`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${baseUrl}/messages`, lastModified: now, changeFrequency: 'hourly', priority: 0.7 },
    { url: `${baseUrl}/notifications`, lastModified: now, changeFrequency: 'hourly', priority: 0.6 },
    { url: `${baseUrl}/wallet`, lastModified: now, changeFrequency: 'daily', priority: 0.6 },
    { url: `${baseUrl}/account`, lastModified: now, changeFrequency: 'monthly', priority: 0.4 },

    // ── Content Pages (NEW in v4.0.0) ──
    { url: `${baseUrl}/about`, lastModified: now, changeFrequency: 'monthly', priority: 0.6 },
    { url: `${baseUrl}/privacy`, lastModified: now, changeFrequency: 'yearly', priority: 0.3 },
    { url: `${baseUrl}/terms`, lastModified: now, changeFrequency: 'yearly', priority: 0.3 },
    { url: `${baseUrl}/faq`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${baseUrl}/contact`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },
    { url: `${baseUrl}/blog`, lastModified: now, changeFrequency: 'weekly', priority: 0.6 },
    { url: `${baseUrl}/help`, lastModified: now, changeFrequency: 'monthly', priority: 0.5 },

    // ── Admin Pages (not indexed, but listed for completeness) ──
    { url: `${baseUrl}/admin`, lastModified: now, changeFrequency: 'daily', priority: 0.1 },
  ]
}
