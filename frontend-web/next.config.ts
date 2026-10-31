import type { NextConfig } from "next";

const supabaseUrl = new URL(
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321",
);
const isLocalSupabase = ["127.0.0.1", "localhost"].includes(
  supabaseUrl.hostname,
);

// Basic security headers. No full Content-Security-Policy yet: the site loads
// Supabase, the API, YouTube and Vercel scripts, and a wrong policy breaks it.
const securityHeaders = [
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Content-Security-Policy", value: "frame-ancestors 'none'" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
];

const nextConfig: NextConfig = {
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  images: {
    // 75 is the default for cards; 90 keeps large hero posters sharp.
    qualities: [75, 90],
    dangerouslyAllowLocalIP:
      process.env.NODE_ENV !== "production" && isLocalSupabase,
    remotePatterns: [
      {
        protocol: supabaseUrl.protocol === "https:" ? "https" : "http",
        hostname: supabaseUrl.hostname,
        port: supabaseUrl.port,
        pathname: "/storage/v1/object/public/drama-posters/**",
      },
      {
        protocol: supabaseUrl.protocol === "https:" ? "https" : "http",
        hostname: supabaseUrl.hostname,
        port: supabaseUrl.port,
        pathname: "/storage/v1/object/public/avatars/**",
      },
    ],
  },
};

export default nextConfig;
