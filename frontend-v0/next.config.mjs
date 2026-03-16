/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_REVMAX_API_URL || 'http://127.0.0.1:8001';
    return [{ source: '/api/:path*', destination: `${api.replace(/\/$/, '')}/api/:path*` }];
  },
}

export default nextConfig
