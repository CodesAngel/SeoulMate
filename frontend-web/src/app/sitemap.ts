import type { MetadataRoute } from "next";
import { getCommunityPosts } from "@/lib/api";
import { getCatalog } from "@/lib/catalog-server";
import { absoluteUrl } from "@/lib/site";

// Rebuilt at most once a day; the catalog changes only with a data release.
export const revalidate = 86400;

const COMMUNITY_PAGES = 5;
const COMMUNITY_PAGE_SIZE = 50;

async function communityEntries(): Promise<MetadataRoute.Sitemap> {
  const entries: MetadataRoute.Sitemap = [];
  for (let page = 1; page <= COMMUNITY_PAGES; page += 1) {
    const response = await getCommunityPosts({ page, limit: COMMUNITY_PAGE_SIZE, sort: "recent" }).catch(
      () => null,
    );
    if (!response) break;
    for (const post of response.posts) {
      entries.push({
        url: absoluteUrl(`/community/${post.id}`),
        lastModified: post.updated_at,
        changeFrequency: "weekly",
        priority: 0.4,
      });
    }
    if (!response.has_more) break;
  }
  return entries;
}

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [catalog, community] = await Promise.all([
    getCatalog().catch(() => []),
    communityEntries(),
  ]);

  return [
    { url: absoluteUrl("/"), changeFrequency: "daily", priority: 1 },
    { url: absoluteUrl("/discover"), changeFrequency: "weekly", priority: 0.8 },
    { url: absoluteUrl("/community"), changeFrequency: "daily", priority: 0.7 },
    ...catalog.map((entry) => ({
      url: absoluteUrl(`/drama/${entry.slug}`),
      ...(entry.updatedAt ? { lastModified: entry.updatedAt } : {}),
      changeFrequency: "monthly" as const,
      priority: 0.6,
    })),
    ...community,
  ];
}
