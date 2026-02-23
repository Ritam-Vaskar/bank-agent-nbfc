/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Remove build-time env embedding - use runtime process.env instead
  async rewrites() {
    // Remove localhost rewrite - use API route handlers for proxying
    return [];
  },
};

export default nextConfig;
