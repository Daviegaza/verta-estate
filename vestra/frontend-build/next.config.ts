import type { NextConfig } from "next";
import createNextIntlPlugin from "next-intl/plugin";

const isProd = process.env.NODE_ENV === 'production';

const withNextIntl = createNextIntlPlugin("./i18n/request.ts");

let nextConfig: NextConfig = {
  output: 'standalone',
  // React Compiler — ONLY in production. In dev it uses Babel and makes
  // hot reload painfully slow (Next.js 16 docs warn about this).
  reactCompiler: isProd,
  // Turbopack filesystem cache — faster dev restarts
  experimental: {
    turbopackFileSystemCacheForDev: !isProd,
  },
  images: {
    remotePatterns: [
      { protocol: 'https', hostname: 'vestra.co.ke' },
      { protocol: 'https', hostname: '*.vestra.co.ke' },
      { protocol: 'https', hostname: 'images.unsplash.com' },
      { protocol: 'https', hostname: 'res.cloudinary.com' },
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: '*.fly.dev' },
    ],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },

  // ── Security Headers ──────────────────────────────────────────────────────────
  async headers() {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const imageDomains = [
      'https://vestra.co.ke',
      'https://*.vestra.co.ke',
      'https://images.unsplash.com',
      'https://res.cloudinary.com',
      'http://localhost',
      'https://*.fly.dev',
    ];

    const csp = [
      `default-src 'self'`,
      `script-src 'self' 'unsafe-eval' 'unsafe-inline'`,
      `style-src 'self' 'unsafe-inline'`,
      `img-src 'self' data: blob: ${imageDomains.join(' ')}`,
      `font-src 'self' data:`,
      `connect-src 'self' ${apiUrl}`,
      `frame-ancestors 'none'`,
      `base-uri 'self'`,
      `form-action 'self'`,
    ].join('; ');

    return [
      {
        source: '/:path*',
        headers: [
          { key: 'Content-Security-Policy', value: csp },
          {
            key: 'Strict-Transport-Security',
            value: 'max-age=31536000; includeSubDomains',
          },
          { key: 'X-Frame-Options', value: 'DENY' },
          { key: 'X-Content-Type-Options', value: 'nosniff' },
          {
            key: 'Referrer-Policy',
            value: 'strict-origin-when-cross-origin',
          },
          {
            key: 'Permissions-Policy',
            value:
              'camera=(), microphone=(), geolocation=self, payment=self',
          },
        ],
      },
    ];
  },
};

export default withNextIntl(nextConfig);
