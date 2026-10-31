// Server-only catalog helpers for SEO: slug lookup, sitemap entries and
// server-rendered drama pages. Results are cached by Next.js for a day.
import { cache } from "react";
import { getCommunityTrending, getDrama, getHomepageCommunity, searchDramas } from "@/lib/api";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import { dramaSlug, slugify } from "@/lib/drama";
import { MOCK_DRAMAS } from "@/lib/mock-data";
import type { Drama } from "@/lib/types";

const DAY = 86_400;
const CACHE: RequestInit = { next: { revalidate: DAY } };
// Supabase returns at most 1,000 rows per request.
const PAGE_SIZE = 1000;

export type CatalogEntry = {
  slug: string;
  title: string;
  aired: string | null;
  updatedAt: string | null;
};

type CatalogRow = {
  id: number;
  title: string;
  aired: string | null;
  updated_at: string | null;
};

async function fetchCatalogRows(): Promise<CatalogRow[]> {
  if (IS_MOCK_MODE) {
    return MOCK_DRAMAS.map((drama, index) => ({
      id: index,
      title: drama.Title,
      aired: drama["Release Years"] ?? null,
      updated_at: null,
    }));
  }

  const base = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";
  const rows: CatalogRow[] = [];
  for (let offset = 0; ; offset += PAGE_SIZE) {
    const url =
      `${base}/rest/v1/dramas?select=id,title,aired,updated_at` +
      `&order=id&limit=${PAGE_SIZE}&offset=${offset}`;
    const response = await fetch(url, {
      ...CACHE,
      headers: { apikey: key, Authorization: `Bearer ${key}` },
    });
    if (!response.ok) throw new Error(`Catalog request failed (${response.status})`);
    const page = (await response.json()) as CatalogRow[];
    rows.push(...page);
    if (page.length < PAGE_SIZE) return rows;
  }
}

/** Every drama with its URL slug. Title+year collisions get -2, -3 in id order. */
export const getCatalog = cache(async (): Promise<CatalogEntry[]> => {
  const seen = new Map<string, number>();
  return (await fetchCatalogRows()).map((row) => {
    let slug = dramaSlug(row.title, row.aired);
    const count = (seen.get(slug) ?? 0) + 1;
    seen.set(slug, count);
    if (count > 1) slug = `${slug}-${count}`;
    return {
      slug,
      title: row.title,
      aired: row.aired,
      updatedAt: row.updated_at,
    };
  });
});

/**
 * Finds the drama for a URL slug. A slug without the year (community posts
 * link that way when they have no date) matches if exactly one title fits.
 */
export async function resolveDramaSlug(slug: string): Promise<CatalogEntry | undefined> {
  const catalog = await getCatalog();
  const exact = catalog.find((entry) => entry.slug === slug);
  if (exact) return exact;
  const byTitle = catalog.filter((entry) => slugify(entry.title) === slug);
  return byTitle.length === 1 ? byTitle[0] : undefined;
}

export const getDramaServer = cache(
  async (title: string, aired?: string | null): Promise<Drama | null> => {
    try {
      return await getDrama(title, aired ?? undefined, undefined, CACHE);
    } catch {
      // The API matches `aired` exactly; fall back to the title alone.
      if (!aired) return null;
      return getDrama(title, undefined, undefined, CACHE).catch(() => null);
    }
  },
);

/** Non-personalised "More like" list, so the server HTML has drama links. */
export const getSimilarServer = cache(async (title: string): Promise<Drama[]> => {
  try {
    const response = await searchDramas(
      { query: `dramas like ${title}`, similarTo: title, topN: 5 },
      undefined,
      CACHE,
    );
    return response.recommendations;
  } catch {
    return [];
  }
});

/** Default /discover results (no query or filters), for the server HTML. */
export async function getDiscoverDefaultServer(query: string): Promise<Drama[]> {
  try {
    const response = await searchDramas({ query, topN: 16 }, undefined, CACHE);
    return response.recommendations;
  } catch {
    return [];
  }
}

/**
 * Home page community lists, so the first paint already has their final
 * height. `undefined` on error lets the browser fetch them instead.
 */
export async function getHomeCommunityServer() {
  const init: RequestInit = { next: { revalidate: 600 } };
  const [trending, recent] = await Promise.all([
    getCommunityTrending(undefined, init).catch(() => undefined),
    getHomepageCommunity(undefined, init).catch(() => undefined),
  ]);
  return { trending, recent };
}

/** Non-personalised home picks; shown until the visitor's own list loads. */
export async function getHomePicksServer(query: string): Promise<Drama[]> {
  try {
    const response = await searchDramas({ query, topN: 10 }, undefined, CACHE);
    return response.recommendations;
  } catch {
    return [];
  }
}
