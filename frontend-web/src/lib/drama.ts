import type { Drama } from "@/lib/types";

export function dramaKey(drama: Drama) {
  return `${drama.image_id || drama.Title}::${drama["Release Years"] || ""}`;
}

// Same rule as slug_part() in scripts/import_catalog.py.
export function slugify(value: string) {
  const ascii = value.normalize("NFKD").replace(/[^\x00-\x7F]/g, "");
  return ascii.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "drama";
}

/** First year in an aired range such as "Dec 14, 2019 - Feb 16, 2020". */
export function firstYear(aired?: string | null) {
  return aired?.match(/\b(?:19|20)\d{2}\b/)?.[0];
}

/** "crash-landing-on-you-2019"; the year keeps remakes with the same title apart. */
export function dramaSlug(title: string, aired?: string | null) {
  const year = firstYear(aired);
  return year ? `${slugify(title)}-${year}` : slugify(title);
}

export function dramaPath(title: string, aired?: string | null) {
  return `/drama/${dramaSlug(title, aired)}`;
}

export function dramaHref(drama: Drama) {
  return dramaPath(drama.Title, drama["Release Years"]);
}
