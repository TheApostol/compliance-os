/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Proxy all /api/v1/* and /docs/* requests to the backend.
  // BACKEND_URL is a server-side env var (set in Vercel → Settings → Environment Variables).
  // It is NOT NEXT_PUBLIC_ — the browser never sees it; Next.js uses it at request time.
  // Local default: http://localhost:8000
  async rewrites() {
    const backend = process.env.BACKEND_URL || 'http://localhost:8000'
    return [
      { source: '/api/v1/:path*', destination: `${backend}/api/v1/:path*` },
      { source: '/docs',          destination: `${backend}/docs` },
      { source: '/redoc',         destination: `${backend}/redoc` },
    ]
  },
}

module.exports = nextConfig
