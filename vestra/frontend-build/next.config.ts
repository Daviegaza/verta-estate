import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  // React Compiler — automatic memoization for free perf (Next.js 16 stable)
  reactCompiler: true,
  // Turbopack filesystem cache — faster dev restarts (beta, Next.js 16)
  experimental: {
    turbopackFileSystemCacheForDev: true,
  },
  images: {
    // Use unoptimized for data URIs and local images — faster
    unoptimized: process.env.NODE_ENV === 'development',
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
};

export default nextConfig;
