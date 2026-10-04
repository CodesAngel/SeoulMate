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
import { searchDramas } from "@/lib/api";
import { MOOD_LINKS, QUICK_PROMPTS } from "@/lib/constants";
import { dramaKey } from "@/lib/drama";

const moodIcons = [HeartHandshake, Sparkles, WandSparkles];

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const { ready, userId, sessionId } = useApp();
  const homeQuery = useQuery({
    queryKey: ["home-recommendations", userId],
    queryFn: ({ signal }) =>
      searchDramas(
        {
          query: "recommend me something unforgettable",
          topN: 10,
          userId,
          sessionId,
        },
        signal,
      ),
    enabled: ready,
  });

  const dramas = homeQuery.data?.recommendations ?? [];
  const feature = dramas[0];

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
              <PosterImage src={dramas[1]?.poster_thumbnail_url ?? dramas[1]?.Image} alt={dramas[1]?.Title || "Featured drama"} />
            </div>
            <div className="hero-poster-main">
              <PosterImage src={feature?.poster_thumbnail_url ?? feature?.Image} alt={feature?.Title || "Featured drama"} priority />
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
          <div className="trust-item"><span className="trust-number">2,081</span><div><strong>Stories to discover</strong><span>Across every mood and genre</span></div></div>
          <div className="trust-item"><span className="trust-number">87.05%</span><div><strong>Search accuracy</strong><span>Tested against real requests</span></div></div>
          <div className="trust-item"><span className="trust-number">You</span><div><strong>At the center</strong><span>Recommendations learn your taste</span></div></div>
        </div>
      </section>

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
    </>
  );
}
