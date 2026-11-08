// Daily rotation for the home page: a stable pick for the whole day that
// changes the next day, different per visitor, and no repeats until the pool
// has been cycled through.
import type { Drama } from "@/lib/types";

/** Days since 1970 in the visitor's local time zone. */
export function localDayNumber(now = Date.now()) {
  return Math.floor((now - new Date(now).getTimezoneOffset() * 60_000) / 86_400_000);
}

function hashSeed(text: string) {
  let hash = 2166136261;
  for (let index = 0; index < text.length; index += 1) {
    hash ^= text.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }
  return hash >>> 0;
}

// mulberry32: small deterministic PRNG, so a seed always gives the same order.
function seededRandom(seed: string) {
  let state = hashSeed(seed);
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = state;
    value = Math.imul(value ^ (value >>> 15), value | 1);
    value ^= value + Math.imul(value ^ (value >>> 7), value | 61);
    return ((value ^ (value >>> 14)) >>> 0) / 4294967296;
  };
}

function seededShuffle<T>(items: T[], seed: string) {
  const random = seededRandom(seed);
  const result = [...items];
  for (let index = result.length - 1; index > 0; index -= 1) {
    const swap = Math.floor(random() * (index + 1));
    [result[index], result[swap]] = [result[swap], result[index]];
  }
  return result;
}

/**
 * `count` items for `day`. The pool is shuffled once per seed (the visitor),
 * then each day takes the next slice, so tomorrow continues where today
 * stopped and nothing repeats until the whole pool has been shown.
 */
export function dailySlice<T>(pool: T[], count: number, seed: string, day: number) {
  if (count <= 0 || pool.length === 0) return [];
  if (pool.length <= count) return seededShuffle(pool, seed);
  const order = seededShuffle(pool, seed);
  const start = (day * count) % order.length;
  return Array.from({ length: count }, (_, offset) => order[(start + offset) % order.length]);
}

/** Keys that identify a drama by ID and by title+year (guest lists may lack IDs). */
export function libraryKeys(drama: Drama) {
  const keys = [`title:${drama.Title.trim().toLowerCase()}::${drama["Release Years"] ?? ""}`];
  if (drama.drama_id) keys.push(`id:${drama.drama_id}`);
  return keys;
}

/**
 * How many of the 5 home picks come from the visitor's personalised list,
 * based on how much they have saved or rated. The rest are discovery picks,
 * so even a settled taste keeps seeing something new.
 */
export function personalShare(activity: number) {
  if (activity >= 5) return 4;
  if (activity >= 1) return 3;
  return 0;
}
