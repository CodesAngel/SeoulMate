import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    // The trusted FastAPI service serves posters from 127.0.0.1 in local development.
    dangerouslyAllowLocalIP: true,
    remotePatterns: [
      { protocol: "http", hostname: "127.0.0.1", port: "8001" },
      { protocol: "http", hostname: "localhost", port: "8001" },
    ],
  },
};

export default nextConfig;
