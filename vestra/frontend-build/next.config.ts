import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === 'production';

const nextConfig: NextConfig = {
  output: 'standalone',
  // React Compiler — ONLY in production. In dev it uses Babel and makes
  // hot reload painfully slow (Next.js 16 docs warn about this).
  reactCompiler: isProd,
  // Turbopack filesystem cache — faster dev restarts
  experimental: {
    turbopackFileSystemCacheForDev: !isProd,
  },
  images: {
    unoptimized: true,  // Always fast — skip image optimization in dev AND prod
    remotePatterns: [
      { protocol: 'https', hostname: 'vestra.co.ke' },
      { protocol: 'https', hostname: '*.vestra.co.ke' },
      { protocol: 'https', hostname: 'images.unsplash.com' },
      { protocol: 'https', hostname: 'res.cloudinary.com' },
      { protocol: 'http', hostname: 'localhost' },
      { protocol: 'https', hostname: '*.fly.dev' },
    ],
  },
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{member}}',
    },
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
