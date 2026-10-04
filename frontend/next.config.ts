import type { NextConfig } from "next";

// The browser only ever talks to this Next.js server. Requests to /api/* are
// forwarded to the FastAPI backend, so the backend address stays server-side
// and no CORS configuration is needed.
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

// Content Security Policy for production builds. Next.js hydrates pages with inline
// scripts, so 'unsafe-inline' is needed without per-request nonces; the policy still
// blocks framing (clickjacking), plugins, foreign form targets and connections to any
// origin other than this one (the API is reached through /api on the same origin).
const CSP = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const SECURITY_HEADERS = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
  // The dev server needs eval() for hot reloading, so the CSP is production-only
  ...(process.env.NODE_ENV === "production" ? [{ key: "Content-Security-Policy", value: CSP }] : []),
];

const nextConfig: NextConfig = {
  // Self-contained server for the Docker image (frontend/Dockerfile)
  output: "standalone",
  poweredByHeader: false,
  // Keep the dev-only Next.js badge away from the sidebar's backend status
  devIndicators: { position: "bottom-right" },
  async headers() {
    return [{ source: "/:path*", headers: SECURITY_HEADERS }];
  },
  async rewrites() {
    return [{ source: "/api/:path*", destination: `${BACKEND_URL}/:path*` }];
  },
  experimental: {
    // Answers from a local LLM (with verification and regeneration) can take minutes,
    // especially when the model is busy; the default proxy timeout is 30 s
    proxyTimeout: 600_000,
  },
};

export default nextConfig;
