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

// Home "discovery" pool: well-known, well-rated dramas the home page rotates
// through daily, so visitors with little history still see something new.
const DISCOVERY_MIN_RATING = 8;
const DISCOVERY_MIN_WATCHERS = 15_000;
const DISCOVERY_SIZE = 150;
// The catalog stores genres without MyDramaList's order, so the card's genre
// pill (the first genre) uses this order: headline genres first, broad ones
// ("Drama", "Life") last, anything unlisted in between.
const GENRE_ORDER = [
  "Romance", "Comedy", "Thriller", "Mystery", "Action", "Fantasy", "Historical",
  "Horror", "Crime", "Medical", "Law", "Melodrama", "Sci-Fi", "Supernatural", "Youth",
];
const BROAD_GENRES = ["Drama", "Life"];
function genreRank(name: string) {
  const headline = GENRE_ORDER.indexOf(name);
  if (headline >= 0) return headline;
  return BROAD_GENRES.includes(name) ? 1000 : 500;
}

type DiscoveryRow = {
  id: number;
  title: string;
  aired: string | null;
  rating_value: number | null;
  episodes: number | null;
  watchers: number | null;
  publisher: string | null;
  poster_original_key: string | null;
  poster_thumbnail_key: string | null;
  genres: { name: string }[];
  keywords: { name: string }[];
};

/**
 * Popular, well-rated dramas straight from the catalog (not the search API,
 * whose generic home query leans on title words). Adult titles are removed
 * here. Cached for a day; empty on error so the page still renders.
 */
export const getHomeDiscoveryServer = cache(async (): Promise<Drama[]> => {
  if (IS_MOCK_MODE) return MOCK_DRAMAS;
  const base = (process.env.NEXT_PUBLIC_SUPABASE_URL ?? "").replace(/\/$/, "");
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY ?? "";
  const posterUrl = (objectKey: string | null) =>
    objectKey
      ? `${base}/storage/v1/object/public/drama-posters/${objectKey.split("/").map(encodeURIComponent).join("/")}`
      : undefined;
  try {
    const url =
      `${base}/rest/v1/dramas?select=id,title,aired,rating_value,episodes,watchers,publisher,` +
      `poster_original_key,poster_thumbnail_key,genres(name),keywords(name)` +
      `&rating_value=gte.${DISCOVERY_MIN_RATING}&watchers=gte.${DISCOVERY_MIN_WATCHERS}` +
      // Extra rows leave room for the adult filter below.
      `&order=watchers.desc&limit=${DISCOVERY_SIZE + 50}`;
    const response = await fetch(url, {
      ...CACHE,
      headers: { apikey: key, Authorization: `Bearer ${key}` },
    });
    if (!response.ok) return [];
    const rows = (await response.json()) as DiscoveryRow[];
    return rows
      .filter(
        (row) =>
          !row.genres.some((genre) => genre.name === "Mature") &&
          !row.keywords.some((keyword) => /nudity/i.test(keyword.name)),
      )
      .slice(0, DISCOVERY_SIZE)
      .map((row) => {
        const genres = row.genres
          .map((genre) => genre.name)
          .sort((a, b) => genreRank(a) - genreRank(b));
        const thumbnail = posterUrl(row.poster_thumbnail_key);
        return {
          drama_id: row.id,
          Title: row.title,
          Genre: genres.join(", "),
          Network: row.publisher ?? undefined,
          "Release Years": row.aired ?? undefined,
          rating_value: row.rating_value ?? undefined,
          episodes: row.episodes ?? undefined,
          watchers: row.watchers ?? undefined,
          poster_thumbnail_url: thumbnail,
          poster_original_url: posterUrl(row.poster_original_key),
          Image: thumbnail,
        } satisfies Drama;
      });
  } catch {
    return [];
  }
});
