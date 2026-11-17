// Server-only: extra posters and the trailer for a drama from TMDB (The Movie Database).
// tmdb-ids.json maps "Title|year" to a TMDB show id (scripts/match_tmdb.py).
// Images load straight from TMDB's image servers and trailers from YouTube;
// we never store them. The TMDB answer is cached for a week
// (TMDB terms: no caching past 6 months).
import tmdbIds from "@/data/tmdb-ids.json";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import { firstYear } from "@/lib/drama";

const WEEK = 604_800;
const MAX_POSTERS = 12;

export type TmdbPoster = { path: string; lang: string | null };
export type TmdbGallery = { tmdbId: number; posters: TmdbPoster[] };
export type TmdbTrailer = { youtubeKey: string; name: string };
export type TmdbMedia = { gallery: TmdbGallery | null; trailer: TmdbTrailer | null };

type TmdbImage = {
  file_path: string;
  iso_639_1: string | null;
  aspect_ratio: number;
  vote_average: number;
  vote_count: number;
};

type TmdbVideo = {
  key: string;
  name: string;
  site: string;
  type: string;
  official: boolean;
  iso_639_1: string | null;
  published_at: string;
};

const NONE: TmdbMedia = { gallery: null, trailer: null };

export function tmdbIdFor(title: string, aired?: string | null): number | undefined {
  return (tmdbIds as Record<string, number>)[`${title}|${firstYear(aired) ?? ""}`];
}

function pickPosters(images: TmdbImage[]): TmdbPoster[] {
  return images
    .filter((p) => p.aspect_ratio > 0.6 && p.aspect_ratio < 0.75) // portrait (2:3) only
    .sort((a, b) => b.vote_average - a.vote_average || b.vote_count - a.vote_count)
    .slice(0, MAX_POSTERS)
    .map((p) => ({ path: p.file_path, lang: p.iso_639_1 }));
}

// Best YouTube trailer: Trailer before Teaser, official first, English
// (usually subtitled) before Korean, then the earliest (the main trailer).
function pickTrailer(videos: TmdbVideo[]): TmdbTrailer | null {
  const typeRank = (v: TmdbVideo) => (v.type === "Trailer" ? 0 : v.type === "Teaser" ? 1 : 9);
  const langRank = (v: TmdbVideo) => (v.iso_639_1 === "en" ? 0 : v.iso_639_1 === "ko" ? 1 : 2);
  const best = videos
    .filter((v) => v.site === "YouTube" && typeRank(v) < 9 && v.key)
    .sort(
      (a, b) =>
        typeRank(a) - typeRank(b) ||
        Number(b.official) - Number(a.official) ||
        langRank(a) - langRank(b) ||
        a.published_at.localeCompare(b.published_at),
    )[0];
  return best ? { youtubeKey: best.key, name: best.name } : null;
}

export async function getTmdbMedia(title: string, aired?: string | null): Promise<TmdbMedia> {
  const key = process.env.TMDB_API_KEY;
  const tmdbId = tmdbIdFor(title, aired);
  if (IS_MOCK_MODE || !key || !tmdbId) return NONE;

  try {
    const url =
      `https://api.themoviedb.org/3/tv/${tmdbId}?append_to_response=images,videos` +
      `&include_image_language=ko,en,null&include_video_language=ko,en,null` +
      `&api_key=${encodeURIComponent(key)}`;
    const response = await fetch(url, { next: { revalidate: WEEK } });
    if (!response.ok) return NONE;
    const data = (await response.json()) as {
      images?: { posters?: TmdbImage[] };
      videos?: { results?: TmdbVideo[] };
    };

    const posters = pickPosters(data.images?.posters ?? []);
    return {
      // One poster is usually the same one we already show; a gallery needs two.
      gallery: posters.length >= 2 ? { tmdbId, posters } : null,
      trailer: pickTrailer(data.videos?.results ?? []),
    };
  } catch {
    return NONE;
  }
}
