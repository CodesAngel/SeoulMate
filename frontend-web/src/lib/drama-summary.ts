// A short, template-built "At a glance" text per drama, from SeoulMate's own
// fields (no LLM). It gives every drama page text that is not MyDramaList's
// synopsis. Ratings and watcher counts are left out: they are MDL's numbers.
import { firstYear } from "@/lib/drama";
import type { Drama } from "@/lib/types";

function list(value?: string, limit = 3) {
  return (value || "").split(",").map((item) => item.trim()).filter(Boolean).slice(0, limit);
}

/** "a", "a and b", "a, b and c" */
export function joinWords(items: string[]) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

/** Sentences about the drama itself (the "similar" sentence is built separately). */
export function dramaSummarySentences(drama: Drama): string[] {
  const sentences: string[] = [];
  const year = firstYear(drama["Release Years"]);
  const network = list(drama.Network, 1)[0];
  const episodes = Number(drama.episodes) || 0;

  let intro = `${drama.Title} is a Korean drama`;
  if (year) intro += ` from ${year}`;
  if (network) intro += ` that aired on ${network}`;
  if (episodes) intro += `, with ${episodes} episode${episodes === 1 ? "" : "s"}`;
  sentences.push(`${intro}.`);

  const genres = list(drama.Genre).map((genre) => genre.toLowerCase());
  if (genres.length > 1) sentences.push(`It mixes ${joinWords(genres)}.`);
  else if (genres.length === 1) sentences.push(`Its genre is ${genres[0]}.`);

  const cast = list(drama.Cast, 2);
  const director = list(drama.Director, 1)[0];
  if (cast.length && director) sentences.push(`It stars ${joinWords(cast)} and is directed by ${director}.`);
  else if (cast.length) sentences.push(`It stars ${joinWords(cast)}.`);
  else if (director) sentences.push(`It is directed by ${director}.`);

  const tags = list(drama.keywords);
  if (tags.length) sentences.push(`Its story tags include ${joinWords(tags)}.`);

  return sentences;
}

/** Plain-text version, for meta descriptions. */
export function dramaSummaryText(drama: Drama, similar: Drama[] = []) {
  const sentences = dramaSummarySentences(drama);
  const titles = similar.slice(0, 2).map((item) => item.Title);
  if (titles.length) sentences.push(`If you enjoyed it, try ${titles.join(" or ")}.`);
  return sentences.join(" ");
}
