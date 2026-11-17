// Server-only: extra posters, the trailer and cast photos for a drama from TMDB
// (The Movie Database).
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
// One cast member as shown on the page. photo/character are null when TMDB has none.
export type TmdbCastMember = { name: string; character: string | null; photo: string | null };
// main: SeoulMate's own cast list (order and spelling kept) with TMDB photos added.
// more: the first of the rest of TMDB's cast (the catalog doesn't hold them);
// moreTotal counts all of them, for the button and the link to TMDB.
export type TmdbCast = {
  tmdbId: number;
  main: TmdbCastMember[];
  more: TmdbCastMember[];
  moreTotal: number;
};
export type TmdbMedia = {
  gallery: TmdbGallery | null;
  trailer: TmdbTrailer | null;
  cast: TmdbCast | null;
};

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

type TmdbCredit = {
  id: number;
  name: string;
  original_name?: string;
  profile_path: string | null;
  roles?: { character: string; episode_count: number }[];
};

const NONE: TmdbMedia = { gallery: null, trailer: null, cast: null };
const MAX_MORE_CAST = 30;

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

// ---- Cast pairing -------------------------------------------------------
// Our names come from MyDramaList ("Jeon Seok Ho"), TMDB's often differ in
// romanisation ("Jun Seok-ho"). Both sides are reduced to a rough sound key and
// compared only against TMDB's cast of the same drama, so namesakes in other
// dramas can't be mixed up. Tested on 50 random dramas: 86% of names paired.
const SOUND_RULES: [string, string][] = [
  ["eo", "u"], ["oo", "u"], ["ee", "i"], ["ou", "u"], ["wo", "u"], ["ae", "e"],
  ["k", "g"], ["ch", "j"], ["l", "r"], ["p", "b"], ["t", "d"], ["sh", "s"], ["y", ""],
];
const PAIR_THRESHOLD = 85;

function soundKey(name: string) {
  let key = name.toLowerCase().replace(/[^a-z]/g, "");
  for (const [from, to] of SOUND_RULES) key = key.split(from).join(to);
  return key;
}

function wordKey(name: string) {
  return name.split(/[\s-]+/).filter(Boolean).map(soundKey).sort().join("");
}

// Similarity 0-100 from the longest common subsequence (same as rapidfuzz's ratio).
function ratio(a: string, b: string) {
  if (!a || !b) return 0;
  const row = new Array<number>(b.length + 1).fill(0);
  for (let i = 1; i <= a.length; i++) {
    let prev = 0;
    for (let j = 1; j <= b.length; j++) {
      const keep = row[j];
      row[j] = a[i - 1] === b[j - 1] ? prev + 1 : Math.max(row[j], row[j - 1]);
      prev = keep;
    }
  }
  return (200 * row[b.length]) / (a.length + b.length);
}

function mainRole(credit: TmdbCredit) {
  const roles = [...(credit.roles ?? [])].sort((a, b) => b.episode_count - a.episode_count);
  return roles.find((r) => r.character?.trim())?.character.trim() || null;
}

function toMember(name: string, credit?: TmdbCredit): TmdbCastMember {
  return {
    name,
    character: credit ? mainRole(credit) : null,
    photo: credit?.profile_path ?? null,
  };
}

function pairCast(tmdbId: number, ours: string[], credits: TmdbCredit[]): TmdbCast | null {
  if (!credits.length) return null;
  const used = new Set<number>();
  const main = ours.map((name) => {
    let best: TmdbCredit | undefined;
    let bestScore = 0;
    for (const [index, credit] of credits.entries()) {
      if (used.has(credit.id)) continue;
      const score =
        Math.max(
          ratio(soundKey(name), soundKey(credit.name)),
          ratio(soundKey(name), soundKey(credit.original_name ?? "")),
          ratio(wordKey(name), wordKey(credit.name)) - 3,
        ) + (index < 12 ? 4 : 0); // TMDB lists main cast first
      if (score > bestScore) {
        best = credit;
        bestScore = score;
      }
    }
    if (!best || bestScore < PAIR_THRESHOLD) return toMember(name);
    used.add(best.id);
    return toMember(name, best);
  });
  // No cast in our catalog: show TMDB's first six instead.
  if (!main.length) {
    credits.slice(0, 6).forEach((credit) => used.add(credit.id));
    main.push(...credits.slice(0, 6).map((credit) => toMember(credit.name, credit)));
  }
  const rest = credits.filter((credit) => !used.has(credit.id));
  const more = rest.slice(0, MAX_MORE_CAST).map((credit) => toMember(credit.name, credit));
  return { tmdbId, main, more, moreTotal: rest.length };
}

export async function getTmdbMedia(
  title: string,
  aired?: string | null,
  castNames: string[] = [],
): Promise<TmdbMedia> {
  const key = process.env.TMDB_API_KEY;
  const tmdbId = tmdbIdFor(title, aired);
  if (IS_MOCK_MODE || !key || !tmdbId) return NONE;

  try {
    const url =
      `https://api.themoviedb.org/3/tv/${tmdbId}?append_to_response=images,videos,aggregate_credits` +
      `&include_image_language=ko,en,null&include_video_language=ko,en,null` +
      `&api_key=${encodeURIComponent(key)}`;
    const response = await fetch(url, { next: { revalidate: WEEK } });
    if (!response.ok) return NONE;
    const data = (await response.json()) as {
      images?: { posters?: TmdbImage[] };
      videos?: { results?: TmdbVideo[] };
      aggregate_credits?: { cast?: TmdbCredit[] };
    };

    const posters = pickPosters(data.images?.posters ?? []);
    return {
      // One poster is usually the same one we already show; a gallery needs two.
      gallery: posters.length >= 2 ? { tmdbId, posters } : null,
      trailer: pickTrailer(data.videos?.results ?? []),
      cast: pairCast(tmdbId, castNames, data.aggregate_credits?.cast ?? []),
    };
  } catch {
    return NONE;
  }
}
