import type { MetadataRoute } from "next";
import { absoluteUrl } from "@/lib/site";

// AI crawlers are welcome too: being cited by AI search is a goal.
export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: "*",
      allow: "/",
      disallow: [
        "/account",
        "/watchlist",
        "/profile",
        "/fusion",
        "/auth/",
        "/community/new",
        "/community/edit/",
      ],
    },
    sitemap: absoluteUrl("/sitemap.xml"),
  };
}
