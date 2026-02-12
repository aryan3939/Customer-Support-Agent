import type { NextConfig } from "next";

const nextConfig: NextConfig = {
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
