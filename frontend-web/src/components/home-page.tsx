"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, HeartHandshake, Search, Sparkles, WandSparkles } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useApp } from "@/components/app-provider";
import { DramaCard } from "@/components/drama-card";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { PosterImage } from "@/components/poster-image";
import { CommunityTrendingSection } from "@/components/community-trending-section";
import { CommunityFromSection } from "@/components/community-from-section";
import { searchDramas } from "@/lib/api";
import { MOOD_LINKS, QUICK_PROMPTS } from "@/lib/constants";
import { dailySlice, libraryKeys, localDayNumber, personalShare } from "@/lib/daily-picks";
import { dramaHref, dramaKey } from "@/lib/drama";
import type { CommunityPost, Drama, TrendingCommunityPost } from "@/lib/types";

const moodIcons = [HeartHandshake, Sparkles, WandSparkles];

// The hero is the first thing every visitor sees, so it only features
// well-known, well-rated dramas and never adult titles.
const HERO_MIN_WATCHERS = 10_000;
const HERO_MIN_RATING = 7.5;

function isAdultTitle(drama: Drama) {
  return /\bmature\b/i.test(drama.Genre ?? "") || /nudity/i.test(drama.keywords ?? "");
}

function isHeroWorthy(drama: Drama) {
  return (
    (drama.watchers ?? 0) >= HERO_MIN_WATCHERS &&
    Number(drama.rating_value) >= HERO_MIN_RATING
  );
}

// Same search as "See more matches". ("…unforgettable" matched title words
// like "Memory" and "Un-" and pulled in obscure dramas.)
const HOME_PICKS_QUERY = "recommend me something great";
const HOME_PICK_COUNT = 5;
// Personalised picks rotate through this many of the visitor's top results.
const PERSONAL_POOL_SIZE = 20;

type LibrarySnapshot = { userId: string; keys: Set<string>; activity: number };

export function HomePage({
  discoveryPool = [],
  initialTrending,
  initialRecent,
}: {
  discoveryPool?: Drama[];
  initialTrending?: TrendingCommunityPost[];
  initialRecent?: CommunityPost[];
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const { ready, userId, sessionId, watchlist, ratingEntries } = useApp();

  // What the visitor has saved or rated, captured once when their library has
  // loaded. A snapshot (not live state) so saving a drama from these cards
  // doesn't make it vanish from the page.
  const [library, setLibrary] = useState<LibrarySnapshot | null>(null);
  if (ready && library?.userId !== userId) {
    const known = [...watchlist, ...ratingEntries.map((entry) => entry.drama)];
    setLibrary({
      userId,
      keys: new Set(known.flatMap(libraryKeys)),
      activity: new Set(known.map((drama) => libraryKeys(drama)[0])).size,
    });
  }
  const personalCount = library ? personalShare(library.activity) : 0;

  const personalQuery = useQuery({
    queryKey: ["home-recommendations", userId],
    queryFn: ({ signal }) =>
      searchDramas(
        {
          query: HOME_PICKS_QUERY,
          topN: PERSONAL_POOL_SIZE + 10,
          userId,
          sessionId,
        },
        signal,
      ),
    // A visitor with no history gets discovery picks only, so the
    // personalised search is skipped entirely.
    enabled: ready && library !== null && personalCount > 0,
  });

  // The rotation day: the same picks all day (local time), new ones tomorrow.
  const [localDay] = useState(() => localDayNumber());

  // The home page is the public front door: adult titles stay out of both the
  // hero and the picks (they remain reachable through search). Dramas the
  // visitor already saved or rated are skipped too.
  const isFresh = (drama: Drama) =>
    !isAdultTitle(drama) && !libraryKeys(drama).some((key) => library?.keys.has(key));
  const personalPool = (personalQuery.data?.recommendations ?? [])
    .filter(isFresh)
    .slice(0, PERSONAL_POOL_SIZE);
  // If the personalised search fails, discovery picks fill every slot.
  const personalPicks = personalQuery.isError
    ? []
    : dailySlice(personalPool, personalCount, `${userId}|personal`, localDay);
  const pickedKeys = new Set(personalPicks.flatMap(libraryKeys));
  const freshDiscovery = discoveryPool.filter(
    (drama) => isFresh(drama) && !libraryKeys(drama).some((key) => pickedKeys.has(key)),
  );
  const discoveryPicks = dailySlice(
    freshDiscovery,
    HOME_PICK_COUNT - personalPicks.length,
    `${userId}|discovery`,
    localDay,
  );
  const picks = [...personalPicks, ...discoveryPicks];
  const picksLoading = !library || (personalCount > 0 && personalQuery.isPending);

  // "Tonight's match" also rotates daily: from the visitor's own well-known,
  // well-rated matches once they have a taste, otherwise from the discovery
  // pool. It never repeats one of the cards below.
  const shownKeys = new Set(picks.flatMap(libraryKeys));
  const notShown = (drama: Drama) => !libraryKeys(drama).some((key) => shownKeys.has(key));
  const personalHeroes = personalPool.filter((drama) => isHeroWorthy(drama) && notShown(drama));
  const heroPool = personalHeroes.length
    ? personalHeroes
    : freshDiscovery.filter((drama) => isHeroWorthy(drama) && notShown(drama));
  const [feature, backdrop] = picksLoading
    ? []
    : dailySlice(heroPool, 2, `${userId}|hero`, localDay);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (value) router.push(`/discover?q=${encodeURIComponent(value)}`);
  }

  return (
    <>
      <section className="hero">
        <div className="shell hero-panel">
          <div className="hero-copy">
            <span className="eyebrow">Stories matched to your mood</span>
            <h1 className="display">Your next <em>obsession</em> is one search away.</h1>
            <p>
              Tell SeoulMate what you want to feel, who you want to watch, or the story you cannot stop thinking about.
            </p>
            <form className="hero-search" onSubmit={submit}>
              <Search size={21} />
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Try “a funny fantasy with found family”"
                aria-label="Describe your next drama"
              />
              <button type="submit">Find my drama</button>
            </form>
            <div className="prompt-row">
              {QUICK_PROMPTS.map((prompt) => (
                <Link key={prompt} href={`/discover?q=${encodeURIComponent(prompt)}`}>{prompt}</Link>
              ))}
            </div>
          </div>
          <div className="hero-art" aria-hidden={!feature}>
            <div className="hero-poster-back">
              <PosterImage src={backdrop?.poster_thumbnail_url ?? backdrop?.Image} alt={backdrop?.Title || "Featured drama"} sizes="(max-width: 950px) 50vw, 360px" />
            </div>
            <div className="hero-poster-main">
              {/* The hero poster is far larger than a card, so it uses the original
                  image instead of the 480px thumbnail. */}
              <PosterImage
                src={feature?.poster_original_url ?? feature?.poster_thumbnail_url ?? feature?.Image}
                alt={feature?.Title || "Featured drama"}
                priority
                sizes="(max-width: 950px) 60vw, 420px"
                quality={90}
              />
            </div>
            {feature && (
              <div className="hero-feature-label">
                <span>Tonight&apos;s match</span>
                <h2>{feature.Title}</h2>
              </div>
            )}
          </div>
        </div>
        <div className="shell trust-strip">
          <div className="trust-item"><span className="trust-number">2,130</span><div><strong>Stories to discover</strong><span>Across every mood and genre</span></div></div>
          <div className="trust-item"><span className="trust-number">89.10%</span><div><strong>Search accuracy</strong><span>Tested against real requests</span></div></div>
          <div className="trust-item"><span className="trust-number">You</span><div><strong>At the center</strong><span>Recommendations learn your taste</span></div></div>
        </div>
      </section>

      <CommunityTrendingSection initialData={initialTrending} />

      <section className="section">
        <div className="shell">
          <div className="section-heading">
            <div><span className="eyebrow">Selected for you</span><h2 className="display">Start with these</h2></div>
            <Link className="text-link" href="/discover?q=recommend%20me%20something%20great">See more matches <ArrowRight size={17} /></Link>
          </div>
          {/* The picks depend on the visitor (their history and the day), so
              none are rendered on the server (they would visibly swap).
              Crawlers without JavaScript get discovery picks as plain links. */}
          {discoveryPool.length > 0 && (
            <noscript>
              <ul className="drama-grid">
                {discoveryPool.slice(0, HOME_PICK_COUNT).map((drama) => (
                  <li key={dramaKey(drama)}><a href={dramaHref(drama)}>{drama.Title}</a></li>
                ))}
              </ul>
            </noscript>
          )}
          {picksLoading ? <DramaGridSkeleton count={HOME_PICK_COUNT} /> : picks.length === 0 ? (
            <div className="error-banner" role="alert">The recommendation service is unavailable. <button type="button" onClick={() => { void personalQuery.refetch(); router.refresh(); }}>Try again</button></div>
          ) : (
            <div className="drama-grid">
              {picks.map((drama, index) => <DramaCard key={dramaKey(drama)} drama={drama} position={index + 1} />)}
            </div>
          )}
        </div>
      </section>

      <section className="section alt">
        <div className="shell">
          <div className="section-heading">
            <div><span className="eyebrow">Choose a feeling</span><h2 className="display">Where should the story take you?</h2></div>
            <p>Search in natural language. SeoulMate understands genre, mood, setting, relationships, actors, and story themes together.</p>
          </div>
          <div className="mood-grid">
            {MOOD_LINKS.map((mood, index) => {
              const Icon = moodIcons[index];
              return (
                <Link href={mood.href} className="mood-card" key={mood.href}>
                  <Icon size={30} /><div><h3>{mood.title}</h3><p>{mood.description}</p></div><span className="arrow-disc"><ArrowRight size={18} /></span>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      <CommunityFromSection initialData={initialRecent} />
    </>
  );
}
