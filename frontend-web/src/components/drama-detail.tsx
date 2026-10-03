"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { Bookmark, BookmarkCheck, Star, Users } from "lucide-react";
import { useState } from "react";
import { useApp } from "@/components/app-provider";
import { DramaCard } from "@/components/drama-card";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { PosterImage } from "@/components/poster-image";
import { getDrama, rateDrama, searchDramas } from "@/lib/api";

function list(value?: string, limit = 10) {
  return (value || "").split(",").map((item) => item.trim()).filter(Boolean).slice(0, limit);
}

export function DramaDetail({ title, aired }: { title: string; aired?: string }) {
  const { ready, userId, sessionId, isSaved, toggleSaved } = useApp();
  const [rating, setRating] = useState("9");
  const [message, setMessage] = useState("");
  const dramaQuery = useQuery({ queryKey: ["drama", title, aired], queryFn: () => getDrama(title, aired) });
  const similarQuery = useQuery({
    queryKey: ["similar", title, userId],
    queryFn: ({ signal }) => searchDramas({ query: `dramas like ${title}`, similarTo: title, topN: 5, userId, sessionId }, signal),
    enabled: ready,
  });
  const ratingMutation = useMutation({
    mutationFn: () => rateDrama(userId, title, Number(rating)),
    onSuccess: (data) => setMessage(data.message),
    onError: (error) => setMessage(error instanceof Error ? error.message : "Could not save rating"),
  });

  if (dramaQuery.isLoading) return <div className="shell detail-shell"><DramaGridSkeleton count={4} /></div>;
  if (dramaQuery.isError || !dramaQuery.data) return <div className="shell section"><div className="empty-state"><h2>We could not find this drama</h2><p>{dramaQuery.error instanceof Error ? dramaQuery.error.message : "Try searching for it again."}</p></div></div>;

  const drama = dramaQuery.data;
  const saved = isSaved(drama);
  const genres = list(drama.Genre, 6);
  const keywords = list(drama.keywords, 12);

  return (
    <>
      <div className="shell detail-shell">
        <section className="detail-hero">
          <div className="detail-poster"><PosterImage src={drama.Image} alt={`${drama.Title} poster`} priority sizes="(max-width: 780px) 76vw, 340px" /></div>
          <div className="detail-copy">
            <span className="eyebrow">{drama.Network || "Korean drama"}</span>
            <h1 className="display">{drama.Title}</h1>
            <div className="detail-meta">
              {drama.rating_value && <span className="meta-chip"><Star size={13} fill="currentColor" /> {drama.rating_value}/10</span>}
              {drama.episodes && <span className="meta-chip">{drama.episodes} episodes</span>}
              {drama["Release Years"] && <span className="meta-chip">{drama["Release Years"]}</span>}
              {drama.watchers ? <span className="meta-chip"><Users size={13} /> {Intl.NumberFormat("en", { notation: "compact" }).format(drama.watchers)} watchers</span> : null}
            </div>
            <p className="detail-description">{drama.Description || "No synopsis is available yet."}</p>
            <div className="detail-actions">
              <button className="primary-button" onClick={() => toggleSaved(drama)}>{saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}{saved ? "Saved to my list" : "Add to my list"}</button>
            </div>
            <div className="rating-box">
              <strong>Already watched it?</strong>
              <select value={rating} onChange={(event) => setRating(event.target.value)} aria-label="Your rating">{[10,9.5,9,8.5,8,7.5,7,6,5].map((score) => <option value={score} key={score}>{score}/10</option>)}</select>
              <button className="secondary-button" onClick={() => ratingMutation.mutate()} disabled={!userId || ratingMutation.isPending}>{ratingMutation.isPending ? "Saving…" : "Save rating"}</button>
              {message && <span className="muted" role="status">{message}</span>}
            </div>
          </div>
        </section>
        <section className="detail-columns">
          <div>
            <h2>Story notes</h2>
            <div className="detail-list">
              <div className="detail-row"><strong>Genres</strong><div className="tag-list">{genres.map((genre) => <span className="tag" key={genre}>{genre}</span>)}</div></div>
              <div className="detail-row"><strong>Cast</strong><span>{drama.Cast || "Not listed"}</span></div>
              <div className="detail-row"><strong>Director</strong><span>{drama.Director || "Not listed"}</span></div>
              {drama["Also Known As"] && <div className="detail-row"><strong>Also known as</strong><span>{drama["Also Known As"]}</span></div>}
            </div>
          </div>
          <div><h2>What you will find</h2><div className="tag-list">{keywords.length ? keywords.map((keyword) => <span className="tag" key={keyword}>{keyword}</span>) : <span className="muted">No story tags available.</span>}</div></div>
        </section>
      </div>
      <section className="section alt">
        <div className="shell">
          <div className="section-heading"><div><span className="eyebrow">Keep the feeling</span><h2 className="display">More like {drama.Title}</h2></div></div>
          {similarQuery.isLoading ? <DramaGridSkeleton count={5} /> : (
            <div className="drama-grid">{(similarQuery.data?.recommendations || []).map((item, index) => <DramaCard key={`${item.Title}-${index}`} drama={item} position={index + 1} />)}</div>
          )}
        </div>
      </section>
    </>
  );
}
