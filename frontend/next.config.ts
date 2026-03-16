import type { NextConfig } from "next";
import { config } from "dotenv";
import { resolve } from "path";

// Load the root .env file (one level up from /frontend)
config({ path: resolve(__dirname, "..", ".env") });

const nextConfig: NextConfig = {
  // Expose root .env vars to the browser via process.env
  // This avoids needing a separate .env.local in the frontend
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.SUPABASE_URL || "",
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.SUPABASE_ANON_KEY || "",
  },

  // Proxy API calls to FastAPI backend
  async rewrites() {
    return {
      // beforeFiles ensures rewrites run BEFORE Next.js tries to match routes
      beforeFiles: [
        {
          source: "/api/:path*",
          // Use 127.0.0.1 instead of localhost — on Windows, localhost can
          // resolve to IPv6 ::1 which fails if the backend only listens on IPv4
          destination: "http://127.0.0.1:8000/api/:path*",
        },
      ],
      afterFiles: [],
      fallback: [],
    };
  },
};

export default nextConfig;
