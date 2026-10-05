"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Bookmark,
  BookmarkCheck,
  Clapperboard,
  Film,
  Play,
  Share2,
  Sparkles,
  Star,
  Users,
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { DramaCard } from "@/components/drama-card";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { PosterImage } from "@/components/poster-image";
import { StarRating } from "@/components/star-rating";
import { TrailerModal } from "@/components/trailer-modal";
import { getDrama, searchDramas } from "@/lib/api";
import { dramaKey } from "@/lib/drama";
import type { WatchStatus } from "@/lib/types";

const WATCH_STATUS_OPTIONS: Array<{ value: WatchStatus; label: string }> = [
  { value: "planned", label: "Plan to watch" },
  { value: "watching", label: "Watching" },
  { value: "completed", label: "Completed" },
  { value: "paused", label: "On hold" },
  { value: "dropped", label: "Dropped" },
];

function list(value?: string, limit = 12) {
  return (value || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean)
    .slice(0, limit);
}

export function DramaDetail({ title, aired }: { title: string; aired?: string }) {
  const { user } = useAuth();
  const {
    ready,
    userId,
    sessionId,
    isSaved,
    toggleSaved,
    getWatchStatus,
    setWatchStatus,
    getRating,
    saveRating,
  } = useApp();

  const [ratingScore, setRatingScore] = useState<number | null>(null);
  const [message, setMessage] = useState("");
  const [trailerOpen, setTrailerOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  const dramaQuery = useQuery({
    queryKey: ["drama", title, aired],
    queryFn: ({ signal }) => getDrama(title, aired, signal),
  });

  const similarQuery = useQuery({
    queryKey: ["similar", title, userId],
    queryFn: ({ signal }) =>
      searchDramas(
        { query: `dramas like ${title}`, similarTo: title, topN: 5, userId, sessionId },
        signal,
      ),
    enabled: ready,
  });

  const drama = dramaQuery.data;
  const persistedRating = drama ? getRating(drama) : undefined;
  const currentRating = ratingScore ?? (persistedRating ?? 9);

  const ratingMutation = useMutation({
    mutationFn: async (score: number) => {
      if (!drama) throw new Error("Drama details are still loading.");
      await saveRating(drama, score);
    },
    onSuccess: (_, score) => {
      setRatingScore(score);
      setMessage(`Your ${score}/10 rating is saved to your account!`);
      setTimeout(() => setMessage(""), 4000);
    },
    onError: (error) =>
      setMessage(error instanceof Error ? error.message : "Could not save rating"),
  });

  function handleShare() {
    if (navigator.share) {
      void navigator
        .share({
          title: drama?.Title || "SeoulMate Drama",
          text: `Check out ${drama?.Title} on SeoulMate!`,
          url: window.location.href,
        })
        .catch(() => undefined);
    } else {
      void navigator.clipboard.writeText(window.location.href);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }

  if (dramaQuery.isLoading)
    return (
      <div className="shell detail-shell">
        <DramaGridSkeleton count={4} />
      </div>
    );

  if (dramaQuery.isError || !drama)
    return (
      <div className="shell section">
        <div className="empty-state">
          <h2>We could not find this drama</h2>
          <p>
            {dramaQuery.error instanceof Error
              ? dramaQuery.error.message
              : "Try searching for it again."}
          </p>
        </div>
      </div>
    );

  const saved = isSaved(drama);
  const watchStatus = getWatchStatus(drama);
  const genres = list(drama.Genre, 8);
  const actors = list(drama.Cast, 10);
  const directors = list(drama.Director, 4);
  const keywords = list(drama.keywords, 16);
  const posterUrl = drama.poster_original_url ?? drama.Image;

  return (
    <>
      {/* Ambient Cinematic Backdrop Glow */}
      <div className="detail-ambient-wrapper">
        <div
          className="detail-ambient-bg"
          style={{ backgroundImage: posterUrl ? `url(${posterUrl})` : undefined }}
          aria-hidden="true"
        />
        <div className="detail-ambient-gradient" aria-hidden="true" />

        <div className="shell detail-shell">
          <section className="detail-hero">
            <div className="detail-poster-wrap">
              <div className="detail-poster">
                <PosterImage
                  src={posterUrl}
                  alt={`${drama.Title} poster`}
                  priority
                  sizes="(max-width: 780px) 76vw, 340px"
                />
              </div>

              {/* Mobile Quick Action Strip */}
              <div className="detail-quick-strip">
                <button
                  type="button"
                  className="quick-strip-btn"
                  onClick={() => setTrailerOpen(true)}
                >
                  <Play size={16} fill="currentColor" />
                  <span>Preview</span>
                </button>
                <button
                  type="button"
                  className="quick-strip-btn"
                  onClick={handleShare}
                >
                  <Share2 size={16} />
                  <span>{copied ? "Copied!" : "Share"}</span>
                </button>
              </div>
            </div>

            <div className="detail-copy">
              <div className="detail-badge-row">
                <span className="eyebrow network-pill">{drama.Network || "Korean Drama"}</span>
                {drama.rating_value && Number(drama.rating_value) >= 8.5 && (
                  <span className="top-rated-badge">
                    <Sparkles size={12} /> Top Rated
                  </span>
                )}
              </div>

              <h1 className="display">{drama.Title}</h1>

              <div className="detail-meta">
                {drama.rating_value && (
                  <span className="meta-chip rating-chip">
                    <Star size={14} fill="currentColor" /> {drama.rating_value}
                    <small>/10</small>
                  </span>
                )}
                {drama.episodes && (
                  <span className="meta-chip">{drama.episodes} episodes</span>
                )}
                {drama["Release Years"] && (
                  <span className="meta-chip">{drama["Release Years"]}</span>
                )}
                {drama.watchers ? (
                  <span className="meta-chip">
                    <Users size={13} />{" "}
                    {Intl.NumberFormat("en", { notation: "compact" }).format(drama.watchers)}{" "}
                    fans
                  </span>
                ) : null}
              </div>

              <p className="detail-description">
                {drama.Description || "No synopsis is available yet."}
              </p>

              {/* Action Toolbar */}
              <div className="detail-actions">
                <button
                  className={`primary-button ${saved ? "saved-active" : ""}`}
                  onClick={() => toggleSaved(drama)}
                >
                  {saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
                  {saved ? "Saved to My List" : "Add to My List"}
                </button>

                <button
                  type="button"
                  className="secondary-button trailer-trigger-btn"
                  onClick={() => setTrailerOpen(true)}
                >
                  <Play size={17} fill="currentColor" />
                  Watch Trailer
                </button>

                {user && saved && (
                  <label className="status-control">
                    <span>Status</span>
                    <select
                      value={watchStatus ?? "planned"}
                      onChange={(event) =>
                        setWatchStatus(drama, event.target.value as WatchStatus)
                      }
                    >
                      {WATCH_STATUS_OPTIONS.map((option) => (
                        <option value={option.value} key={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </label>
                )}
              </div>

              {/* Interactive Star Rating */}
              <div className="rating-box-interactive">
                <div className="rating-box-header">
                  <strong>Your Personal Rating</strong>
                  {!user && (
                    <Link className="text-link" href="/auth/login">
                      Sign in to sync ratings
                    </Link>
                  )}
                </div>

                <StarRating
                  value={currentRating}
                  disabled={!user || ratingMutation.isPending}
                  onChange={(score) => {
                    if (user) {
                      ratingMutation.mutate(score);
                    } else {
                      setMessage("Sign in to save your ratings permanently.");
                    }
                  }}
                />

                {message && (
                  <span className="rating-status-message" role="status">
                    {message}
                  </span>
                )}
              </div>
            </div>
          </section>

          {/* Metadata & Tag Sections */}
          <section className="detail-columns">
            <div className="detail-col-main">
              <h2>Cast & Production</h2>
              <div className="detail-list">
                <div className="detail-row">
                  <strong>Genres</strong>
                  <div className="tag-list">
                    {genres.map((genre) => (
                      <Link
                        key={genre}
                        href={`/discover?genre=${encodeURIComponent(genre)}`}
                        className="tag tag-genre"
                        title={`Discover ${genre} dramas`}
                      >
                        {genre}
                      </Link>
                    ))}
                  </div>
                </div>

                <div className="detail-row">
                  <strong>Cast</strong>
                  <div className="tag-list">
                    {actors.length ? (
                      actors.map((actor) => (
                        <Link
                          key={actor}
                          href={`/discover?q=${encodeURIComponent(actor)}`}
                          className="tag tag-actor"
                          title={`Find dramas starring ${actor}`}
                        >
                          <Users size={12} />
                          <span>{actor}</span>
                        </Link>
                      ))
                    ) : (
                      <span className="muted">Not listed</span>
                    )}
                  </div>
                </div>

                {directors.length > 0 && (
                  <div className="detail-row">
                    <strong>Director</strong>
                    <div className="tag-list">
                      {directors.map((director) => (
                        <Link
                          key={director}
                          href={`/discover?q=${encodeURIComponent(director)}`}
                          className="tag tag-director"
                          title={`Find dramas directed by ${director}`}
                        >
                          <Clapperboard size={12} />
                          <span>{director}</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}

                {drama["Also Known As"] && (
                  <div className="detail-row">
                    <strong>Also known as</strong>
                    <span className="muted-text">{drama["Also Known As"]}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="detail-col-side">
              <h2>Story Tropes & Themes</h2>
              <p className="tropes-intro">
                Click any theme tag to explore matching Korean dramas:
              </p>
              <div className="tag-list">
                {keywords.length ? (
                  keywords.map((keyword) => (
                    <Link
                      key={keyword}
                      href={`/discover?q=${encodeURIComponent(keyword)}`}
                      className="tag tag-trope"
                      title={`Search for #${keyword} dramas`}
                    >
                      <Film size={11} />
                      <span>#{keyword}</span>
                    </Link>
                  ))
                ) : (
                  <span className="muted">No story tags available.</span>
                )}
              </div>
            </div>
          </section>
        </div>
      </div>

      {/* Similar Recommendations */}
      <section className="section alt">
        <div className="shell">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Keep the feeling</span>
              <h2 className="display">More like {drama.Title}</h2>
            </div>
          </div>
          {similarQuery.isLoading ? (
            <DramaGridSkeleton count={5} />
          ) : (
            <div className="drama-grid">
              {(similarQuery.data?.recommendations || []).map((item, index) => (
                <DramaCard
                  key={dramaKey(item)}
                  drama={item}
                  position={index + 1}
                />
              ))}
            </div>
          )}
        </div>
      </section>

      {/* Trailer Modal */}
      <TrailerModal
        isOpen={trailerOpen}
        onClose={() => setTrailerOpen(false)}
        dramaTitle={drama.Title}
      />
    </>
  );
}
