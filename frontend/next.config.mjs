/** @type {import('next').NextConfig} */

// API_PROXY_TARGET must be set to the backend Railway URL in production.
// Example: https://helper-backend-production.up.railway.app
const apiTarget =
  process.env.API_PROXY_TARGET ||
  (process.env.NODE_ENV === "production"
    ? (() => {
        console.warn(
          "[next.config] WARNING: API_PROXY_TARGET is not set. " +
            "Set it to your backend Railway URL, e.g. " +
            "https://helper-backend-production.up.railway.app"
        );
        return "http://127.0.0.1:8000";
      })()
    : "http://127.0.0.1:8000");

const nextConfig = {
  reactStrictMode: true,

  // Required for Railway: Next.js must listen on $PORT (injected at runtime).
  // 'standalone' bundles only what's needed and respects the PORT env var.
  output: "standalone",

  async rewrites() {
    return [
      // Proxy all /api/* requests to the backend, stripping the /api prefix.
      // /api/meetings/start  →  https://backend/meetings/start
      // /api/health/stt      →  https://backend/health/stt
      {
        source: "/api/:path*",
        destination: `${apiTarget}/:path*`,
      },
    ];
  },

  async headers() {
    return [
      {
        // Allow Telegram WebApp to embed the app inside an iframe.
        source: "/(.*)",
        headers: [
          { key: "X-Frame-Options", value: "ALLOWALL" },
          { key: "Content-Security-Policy", value: "frame-ancestors *" },
        ],
      },
    ];
  },
};

export default nextConfig;
