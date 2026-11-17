// K-drama Wrapped: shared types and helpers. Every number comes from the
// backend's plain counts over the fan's list and ratings (no model).

export const WRAPPED_FIRST_YEAR = 2026;

export type WrappedDrama = {
  drama_id: number;
  title: string;
  aired: string | null;
  episodes: number | null;
  poster_url: string | null;
  poster_original_url: string | null;
};

export type WrappedStats = {
  year: number;
  required: number;
  finished: number;
  unlocked: boolean;
  display_name?: string | null;
  totals?: { dramas: number; episodes: number; hours: number };
  posters?: WrappedDrama[];
  top_actor?: {
    name: string;
    count: number;
    dramas: WrappedDrama[];
    tie_with: { name: string; count: number } | null;
    tie_broken_by: "ratings" | "popularity" | null;
  } | null;
  top_trope?: {
    name: string;
    count: number;
    others: { name: string; count: number }[];
  } | null;
  genres?: { name: string; count: number }[];
  fan_type?: { name: string; description: string };
  top_rated?: (WrappedDrama & { rating: number }) | null;
};

export type WrappedShareInfo = {
  id: string;
  year: number;
  show_name: boolean;
  created_at: string;
  updated_at: string;
};

export type MyWrappedResponse = WrappedStats & { share: WrappedShareInfo | null };

export type PublicWrappedResponse = { share: WrappedShareInfo; stats: WrappedStats };

/** Wrapped season: 1 December to 15 January (January shows the year before). */
export function wrappedSeasonYear(now = new Date()): number | null {
  const month = now.getMonth();
  if (month === 11) return now.getFullYear();
  if (month === 0 && now.getDate() <= 15) return now.getFullYear() - 1;
  return null;
}

/** The year /wrapped opens: last year until 15 January, else this year. */
export function defaultWrappedYear(now = new Date()): number {
  const season = wrappedSeasonYear(now);
  return Math.max(WRAPPED_FIRST_YEAR, season ?? now.getFullYear());
}

export function isWrappedYear(year: number, now = new Date()) {
  return Number.isInteger(year) && year >= WRAPPED_FIRST_YEAR && year <= now.getFullYear();
}

/** 448 hours -> "18 days and 16 hours". */
export function hoursAsDays(hours: number) {
  const days = Math.floor(hours / 24);
  const rest = hours % 24;
  if (!days) return `${hours} ${hours === 1 ? "hour" : "hours"}`;
  const dayText = `${days} ${days === 1 ? "day" : "days"}`;
  return rest ? `${dayText} and ${rest} ${rest === 1 ? "hour" : "hours"}` : dayText;
}

export function firstAiredYear(aired: string | null | undefined) {
  return aired?.match(/\d{4}/)?.[0] ?? "";
}

export function wrappedTitle(stats: Pick<WrappedStats, "display_name" | "year">) {
  return stats.display_name
    ? `${stats.display_name}'s ${stats.year} in K-dramas`
    : `My ${stats.year} in K-dramas`;
}
