import type { NextConfig } from "next";

// In local dev: loads vars from the root .env file (one level up from /frontend)
// On Vercel: env vars are set in the dashboard, no file needed
try {
  const { config } = require("dotenv");
  const { resolve } = require("path");
  config({ path: resolve(__dirname, "..", ".env") });
} catch {
  // dotenv not available or .env not found — fine on Vercel
}

const nextConfig: NextConfig = {
  // Expose env vars to the browser:
  // - Locally: reads SUPABASE_URL from root .env
  // - Vercel: reads NEXT_PUBLIC_SUPABASE_URL from dashboard
  env: {
    NEXT_PUBLIC_SUPABASE_URL:
      process.env.NEXT_PUBLIC_SUPABASE_URL ||
      process.env.SUPABASE_URL ||
      "",
    NEXT_PUBLIC_SUPABASE_ANON_KEY:
      process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ||
      process.env.SUPABASE_ANON_KEY ||
      "",
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || 
      "http://127.0.0.1:8000",
  },

  // Proxy API calls to FastAPI backend (local dev only)
  async rewrites() {
    const backendUrl =
      process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

    return {
      beforeFiles: [
        {
          source: "/api/:path*",
          destination: `${backendUrl}/api/:path*`,
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
