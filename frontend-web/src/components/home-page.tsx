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
import { dramaKey } from "@/lib/drama";
import type { Drama } from "@/lib/types";

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

export const HOME_PICKS_QUERY = "recommend me something unforgettable";

export function HomePage({ initialPicks = [] }: { initialPicks?: Drama[] }) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const { ready, userId, sessionId } = useApp();
  const homeQuery = useQuery({
    queryKey: ["home-recommendations", userId],
    queryFn: ({ signal }) =>
      searchDramas(
        {
          query: HOME_PICKS_QUERY,
          topN: 10,
          userId,
          sessionId,
        },
        signal,
      ),
    enabled: ready,
    // Server-rendered, non-personalised picks (so crawlers see drama links)
    // until the visitor's own list loads.
    placeholderData: initialPicks.length
      ? { query: { Title: HOME_PICKS_QUERY }, recommendations: initialPicks }
      : undefined,
  });

  // The home page is the public front door: adult titles stay out of both the
  // hero and the top picks (they remain reachable through search).
  const dramas = (homeQuery.data?.recommendations ?? []).filter((drama) => !isAdultTitle(drama));
  // The hero waits for the real list: its daily pick uses the visitor's local
  // date, which the server does not know.
  const heroSource = homeQuery.isPlaceholderData ? [] : dramas;
  // "Tonight's match" rotates daily through the personalised top results:
  // the same drama all day (local time), a different one tomorrow. Popular,
  // well-rated picks come first; if none qualify, any result is used.
  const [localDay] = useState(() =>
    Math.floor((Date.now() - new Date().getTimezoneOffset() * 60_000) / 86_400_000),
  );
  const heroWorthy = heroSource.filter(isHeroWorthy);
  const heroPool = heroWorthy.length ? heroWorthy : heroSource;
  const feature = heroPool.length ? heroPool[localDay % heroPool.length] : undefined;
  const backdrop = heroPool.length > 1 ? heroPool[(localDay + 1) % heroPool.length] : undefined;

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

      <CommunityTrendingSection />

      <section className="section">
        <div className="shell">
          <div className="section-heading">
            <div><span className="eyebrow">Selected for you</span><h2 className="display">Start with these</h2></div>
            <Link className="text-link" href="/discover?q=recommend%20me%20something%20great">See more matches <ArrowRight size={17} /></Link>
          </div>
          {homeQuery.isLoading ? <DramaGridSkeleton count={5} /> : homeQuery.isError ? (
            <div className="error-banner" role="alert">The recommendation service is unavailable. <button type="button" onClick={() => homeQuery.refetch()}>Try again</button></div>
          ) : (
            <div className="drama-grid">
              {dramas.slice(0, 5).map((drama, index) => <DramaCard key={dramaKey(drama)} drama={drama} position={index + 1} />)}
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

      <CommunityFromSection />
    </>
  );
}
