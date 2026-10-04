import type { NextConfig } from "next";

const apiUrl = new URL(
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001",
);
const isLocalApi = ["127.0.0.1", "localhost"].includes(apiUrl.hostname);

const nextConfig: NextConfig = {
  images: {
    dangerouslyAllowLocalIP:
      process.env.NODE_ENV !== "production" && isLocalApi,
    remotePatterns: [
      {
        protocol: apiUrl.protocol === "https:" ? "https" : "http",
        hostname: apiUrl.hostname,
        port: apiUrl.port,
        pathname: "/drama-images/**",
      },
    ],
  },
};

export default nextConfig;
