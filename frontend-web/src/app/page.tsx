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

const quickPrompts = ["Healing romance", "Smart crime thriller", "Found family", "Fantasy with heart"];

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
              {quickPrompts.map((prompt) => (
                <Link key={prompt} href={`/discover?q=${encodeURIComponent(prompt)}`}>{prompt}</Link>
              ))}
            </div>
          </div>
          <div className="hero-art" aria-hidden={!feature}>
            <div className="hero-poster-back">
              <PosterImage src={dramas[1]?.Image} alt={dramas[1]?.Title || "Featured drama"} priority />
            </div>
            <div className="hero-poster-main">
              <PosterImage src={feature?.Image} alt={feature?.Title || "Featured drama"} priority />
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
          <div className="trust-item"><span className="trust-number">87%</span><div><strong>Search accuracy</strong><span>Tested against real requests</span></div></div>
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
            <div className="error-banner">The recommendation service is unavailable. Start the FastAPI backend on port 8001 and refresh.</div>
          ) : (
            <div className="drama-grid">
              {dramas.slice(0, 5).map((drama, index) => <DramaCard key={`${drama.Title}-${index}`} drama={drama} position={index + 1} priority={index < 3} />)}
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
            <Link href="/discover?q=warm%20healing%20romance" className="mood-card">
              <HeartHandshake size={30} /><div><h3>Soft landing</h3><p>Comforting romance, kind people, and places that feel like home.</p></div><span className="arrow-disc"><ArrowRight size={18} /></span>
            </Link>
            <Link href="/discover?q=clever%20mystery%20thriller" className="mood-card">
              <Sparkles size={30} /><div><h3>Keep me guessing</h3><p>Sharp mysteries and thrillers with something to say.</p></div><span className="arrow-disc"><ArrowRight size={18} /></span>
            </Link>
            <Link href="/discover?q=fantasy%20romance%20found%20family" className="mood-card">
              <WandSparkles size={30} /><div><h3>Leave reality</h3><p>Magic, fate, chosen families, and impossible love.</p></div><span className="arrow-disc"><ArrowRight size={18} /></span>
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
