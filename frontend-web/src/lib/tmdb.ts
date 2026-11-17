// Server-only: extra posters for a drama from TMDB (The Movie Database).
// tmdb-ids.json maps "Title|year" to a TMDB show id (scripts/match_tmdb.py).
// Images are loaded straight from TMDB's image servers; we never store them.
// The poster list is cached for a week (TMDB terms: no caching past 6 months).
import tmdbIds from "@/data/tmdb-ids.json";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import { firstYear } from "@/lib/drama";

const WEEK = 604_800;
const MAX_POSTERS = 12;
export const TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p";

export type TmdbPoster = { path: string; lang: string | null };
export type TmdbGallery = { tmdbId: number; posters: TmdbPoster[] };

type TmdbImage = {
  file_path: string;
  iso_639_1: string | null;
  aspect_ratio: number;
  vote_average: number;
  vote_count: number;
};

export function tmdbIdFor(title: string, aired?: string | null): number | undefined {
  return (tmdbIds as Record<string, number>)[`${title}|${firstYear(aired) ?? ""}`];
}

export async function getTmdbPosters(
  title: string,
  aired?: string | null,
): Promise<TmdbGallery | null> {
  const key = process.env.TMDB_API_KEY;
  const tmdbId = tmdbIdFor(title, aired);
  if (IS_MOCK_MODE || !key || !tmdbId) return null;

  try {
    const url =
      `https://api.themoviedb.org/3/tv/${tmdbId}/images` +
      `?include_image_language=ko,en,null&api_key=${encodeURIComponent(key)}`;
    const response = await fetch(url, { next: { revalidate: WEEK } });
    if (!response.ok) return null;
    const data = (await response.json()) as { posters?: TmdbImage[] };

    const posters = (data.posters ?? [])
      // Portrait posters only (TMDB posters are 2:3).
      .filter((p) => p.aspect_ratio > 0.6 && p.aspect_ratio < 0.75)
      .sort((a, b) => b.vote_average - a.vote_average || b.vote_count - a.vote_count)
      .slice(0, MAX_POSTERS)
      .map((p) => ({ path: p.file_path, lang: p.iso_639_1 }));

    // One poster is usually the same one we already show; a gallery needs two.
    return posters.length >= 2 ? { tmdbId, posters } : null;
  } catch {
    return null;
  }
}
