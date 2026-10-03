"use client";

import { useQuery } from "@tanstack/react-query";
import { RefreshCw, SearchX } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { FormEvent, useState } from "react";
import { useApp } from "@/components/app-provider";
import { DramaCard } from "@/components/drama-card";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { searchDramas } from "@/lib/api";

const genres = ["", "Romance", "Comedy", "Thriller", "Mystery", "Fantasy", "Historical", "Action", "Family", "Medical", "Law"];

export function DiscoverClient() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { ready, userId, sessionId } = useApp();
  const query = searchParams.get("q") || "recommend me something great";
  const genre = searchParams.get("genre") || "";
  const year = searchParams.get("year") || "";
  const minRating = searchParams.get("rating") || "";
  const sortBy = searchParams.get("sort") || "";
  const refresh = Number(searchParams.get("refresh") || 0);
  const [form, setForm] = useState({ genre, year, minRating, sortBy });

  const result = useQuery({
    queryKey: ["discover", query, genre, year, minRating, sortBy, refresh, userId],
    queryFn: ({ signal }) => searchDramas({ query, genre, year, minRating, sortBy, refresh, topN: 16, userId, sessionId }, signal),
    enabled: ready,
  });

  function applyFilters(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams({ q: query });
    if (form.genre) params.set("genre", form.genre);
    if (form.year) params.set("year", form.year);
    if (form.minRating) params.set("rating", form.minRating);
    if (form.sortBy) params.set("sort", form.sortBy);
    router.push(`/discover?${params}`);
  }

  function clearFilters() {
    setForm({ genre: "", year: "", minRating: "", sortBy: "" });
    router.push(`/discover?q=${encodeURIComponent(query)}`);
  }
  function refreshResults() {
    const params = new URLSearchParams(searchParams.toString());
    params.set("refresh", String(refresh + 1));
    router.push(`/discover?${params}`);
  }

  const dramas = result.data?.recommendations ?? [];
  const intent = result.data?.analysis?.intent?.replaceAll("_", " ");

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Smart discovery</span>
          <h1 className="display">Results for <span>“{query}”</span></h1>
          <p>Shape the results with a few useful filters, or describe your mood more naturally in the search bar above.</p>
        </div>
      </section>
      <div className="shell discover-layout">
        <aside className="filter-panel">
          <h2>Refine your match</h2>
          <form className="filter-form" onSubmit={applyFilters}>
            <div className="filter-group"><label htmlFor="genre">Genre</label><select id="genre" value={form.genre} onChange={(event) => setForm({ ...form, genre: event.target.value })}>{genres.map((item) => <option key={item} value={item}>{item || "Any genre"}</option>)}</select></div>
            <div className="filter-group"><label htmlFor="rating">Minimum rating</label><select id="rating" value={form.minRating} onChange={(event) => setForm({ ...form, minRating: event.target.value })}><option value="">Any rating</option><option value="7">7.0+</option><option value="8">8.0+</option><option value="8.5">8.5+</option><option value="9">9.0+</option></select></div>
            <div className="filter-group"><label htmlFor="year">Release year</label><input id="year" type="number" min="1990" max="2030" placeholder="e.g. 2024" value={form.year} onChange={(event) => setForm({ ...form, year: event.target.value })} /></div>
            <div className="filter-group"><label htmlFor="sort">Sort by</label><select id="sort" value={form.sortBy} onChange={(event) => setForm({ ...form, sortBy: event.target.value })}><option value="">Best match</option><option value="rating_value">Highest rated</option><option value="popularity">Most watched</option><option value="date_published">Newest</option></select></div>
            <div className="filter-actions"><button className="primary-button" type="submit">Apply filters</button><button className="secondary-button" type="button" onClick={clearFilters}>Clear</button></div>
          </form>
        </aside>
        <section className="discover-results">
          <div className="results-toolbar">
            <div><span className="eyebrow">{intent ? `Understood as ${intent}` : "Your matches"}</span><h2>{result.isLoading ? "Finding the right stories…" : `${dramas.length} dramas to explore`}</h2>{result.data?.query.expanded && <p>Expanded with: {result.data.query.expanded}</p>}</div>
            <button className="refresh-button" onClick={refreshResults}><RefreshCw size={15} /> Fresh mix</button>
          </div>
          {result.isError && <div className="error-banner">{result.error instanceof Error ? result.error.message : "Search failed"}</div>}
          {result.isLoading ? <DramaGridSkeleton count={8} /> : dramas.length ? (
            <div className="drama-grid">{dramas.map((drama, index) => <DramaCard key={`${drama.Title}-${index}`} drama={drama} position={index + 1} searchId={result.data?.search_id} priority={index < 4} />)}</div>
          ) : (
            <div className="empty-state"><SearchX size={36} /><h2>No close matches yet</h2><p>Try removing a filter or describing the feeling rather than a specific title.</p></div>
          )}
        </section>
      </div>
    </>
  );
}
