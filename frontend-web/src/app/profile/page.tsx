"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FormEvent, useState } from "react";
import Link from "next/link";
import {
  ArrowRight,
  Award,
  Clapperboard,
  Clock,
  Film,
  Heart,
  RotateCcw,
  Sparkles,
  Star,
  Users,
} from "lucide-react";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { StarRating } from "@/components/star-rating";
import { TasteDNAChart } from "@/components/taste-dna-chart";
import { PosterImage } from "@/components/poster-image";
import { getProfile, rateDrama, resetProfile, searchDramas } from "@/lib/api";
import type { WatchlistEntry } from "@/lib/types";
import { WRAPPED_FIRST_YEAR, defaultWrappedYear, wrappedSeasonYear } from "@/lib/wrapped";

function PreferenceList({
  title,
  icon: Icon,
  items,
  type = "actor",
}: {
  title: string;
  icon: typeof Users;
  items: [string, number][];
  type?: "actor" | "director" | "theme";
}) {
  return (
    <div className="preference-section">
      <div className="pref-header">
        <Icon size={16} />
        <h3>{title}</h3>
      </div>
      {items.length ? (
        <div className="pref-chips-grid">
          {items.slice(0, 8).map(([label, score], idx) => {
            const queryParam = type === "theme" ? label : label;
            return (
              <Link
                key={label}
                href={`/discover?q=${encodeURIComponent(queryParam)}`}
                className="pref-interactive-chip"
                title={`Find dramas with ${label}`}
              >
                <span className="pref-chip-rank">#{idx + 1}</span>
                <span className="pref-chip-label">{label}</span>
                <span className="pref-chip-score">{Math.round(score * 100)}%</span>
              </Link>
            );
          })}
        </div>
      ) : (
        <p className="muted text-note">
          Rate dramas featuring these creators to build this preference segment.
        </p>
      )}
    </div>
  );
}

/** A link to the fan's Wrapped: large from 1 December to 15 January, smaller ("so far") the rest of the year.
 *  Until the library has loaded it shows neutral text, so it doesn't flip from "finish 3 more" to the real count. */
function WrappedBanner({ entries, ready }: { entries: WatchlistEntry[]; ready: boolean }) {
  const season = wrappedSeasonYear();
  const year = season ?? defaultWrappedYear();
  if (year < WRAPPED_FIRST_YEAR) return null;
  const quiet = !season;

  if (!ready) {
    return (
      <Link className={quiet ? "wr-banner wr-banner-quiet" : "wr-banner"} href={`/wrapped/${year}`}>
        <div className="wr-banner-copy">
          <b>Your {year} Wrapped</b>
          <span>Your year in K-dramas, as a story you can share.</span>
        </div>
        <span className="wr-next">
          {quiet ? "Take a look" : "Open Wrapped"} <ArrowRight size={15} />
        </span>
      </Link>
    );
  }
  const finished = entries.filter(
    (entry) =>
      entry.status === "completed" &&
      entry.completed_at &&
      new Date(entry.completed_at).getUTCFullYear() === year,
  );
  const left = 3 - finished.length;

  return (
    <Link className={quiet ? "wr-banner wr-banner-quiet" : "wr-banner"} href={`/wrapped/${year}`}>
      {finished.length > 0 && (
        <div className="wr-banner-stack" aria-hidden="true">
          {finished.slice(0, 3).map((entry) => (
            <div className="wr-poster" key={entry.drama.drama_id ?? entry.drama.Title}>
              <PosterImage src={entry.drama.poster_thumbnail_url} alt="" sizes="46px" />
            </div>
          ))}
        </div>
      )}
      <div className="wr-banner-copy">
        <b>
          {quiet
            ? left > 0
              ? `Your ${year} Wrapped`
              : `Your ${year} Wrapped so far`
            : left > 0
              ? `Your ${year} Wrapped is almost ready`
              : `Your ${year} Wrapped is ready`}
        </b>
        <span>
          {left > 0
            ? `Finish ${left} more ${left === 1 ? "drama" : "dramas"} this year to unlock it.`
            : quiet
              ? `${finished.length} dramas finished this year. The full story arrives in December.`
              : `${finished.length} dramas, your top actor, and the trope you can't resist.`}
        </span>
      </div>
      <span className="wr-next">
        {quiet ? "Take a look" : "Open Wrapped"} <ArrowRight size={15} />
      </span>
    </Link>
  );
}

export default function ProfilePage() {
  const { user } = useAuth();
  const { ready, userId, sessionId, watchlistEntries, ratingEntries, saveRating } =
    useApp();
  const queryClient = useQueryClient();

  const [title, setTitle] = useState("");
  const [ratingScore, setRatingScore] = useState(9);
  const [message, setMessage] = useState("");

  const profile = useQuery({
    queryKey: ["profile", userId],
    queryFn: ({ signal }) => getProfile(userId, signal),
    enabled: ready && Boolean(userId),
    retry: false,
  });

  const rate = useMutation({
    mutationFn: async () => {
      if (!user) throw new Error("Sign in to save ratings to your account.");
      const result = await searchDramas({
        query: title.trim(),
        topN: 8,
        userId,
        sessionId,
      });
      const normalizedTitle = title.trim().toLocaleLowerCase();
      const drama =
        result.recommendations.find(
          (item) => item.Title.toLocaleLowerCase() === normalizedTitle,
        ) ?? result.recommendations[0];
      if (!drama?.drama_id)
        throw new Error("We could not find that drama. Try its exact title.");

      await saveRating(drama, Number(ratingScore));
      await rateDrama(userId, drama.Title, Number(ratingScore)).catch(() => undefined);
      return { message: `Rating saved: ${drama.Title} = ${ratingScore}/10` };
    },
    onSuccess: async (data) => {
      setMessage(data.message);
      setTitle("");
      await queryClient.invalidateQueries({ queryKey: ["profile", userId] });
      setTimeout(() => setMessage(""), 5000);
    },
    onError: (error) =>
      setMessage(error instanceof Error ? error.message : "Could not save rating"),
  });

  const reset = useMutation({
    mutationFn: () => resetProfile(userId),
    onSuccess: async (data) => {
      setMessage(data.message);
      await queryClient.invalidateQueries({ queryKey: ["profile", userId] });
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (title.trim()) rate.mutate();
  }

  const data = profile.data;
  // The API can send an empty list; keep the default then, so the card doesn't lose its name after loading.
  const apiPersonas = (Array.isArray(data?.persona) ? data.persona : [data?.persona]).filter(
    (persona): persona is string => typeof persona === "string" && persona.trim() !== "",
  );
  const personas = apiPersonas.length ? apiPersonas : ["K-Drama Explorer"];

  // Calculate watching statistics
  const completedCount = watchlistEntries.filter((e) => e.status === "completed").length;
  const watchingCount = watchlistEntries.filter((e) => e.status === "watching").length;
  const ratingsCount = ratingEntries.length;
  const avgRating =
    ratingsCount > 0
      ? (
          ratingEntries.reduce((acc, curr) => acc + curr.rating, 0) / ratingsCount
        ).toFixed(1)
      : null;

  // Estimated watch hours (completed dramas * ~16 eps * 1 hr + active watching partial)
  const estimatedHours = completedCount * 16 + watchingCount * 6;

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <span className="eyebrow">Personalized AI Profile</span>
          <h1 className="display">Your K-Drama Taste DNA</h1>
          <p>
            Every story you save, watch, or rate continuously trains SeoulMate&apos;s
            collaborative and semantic ranking weights to match your personal mood.
          </p>
        </div>
      </section>

      <div className="shell profile-layout">
        {/* Outside the main column so it can come first on phones (the sidebar moves up there). */}
        {user && <WrappedBanner entries={watchlistEntries} ready={ready} />}

        {/* Main Column */}
        <section className="profile-main-col">

          {/* Persona Hero Card */}
          <div className="profile-card persona-hero-card">
            <div className="persona-hero-content">
              <span className="eyebrow" style={{ color: "var(--lemon)" }}>
                Your Primary Persona
              </span>
              <h2>{personas[0]}</h2>
              <p>
                Dynamic taste category calculated from your ratings, watched tropes, and
                cast affinity.
              </p>
              <div className="persona-tags">
                {personas.map((p) => (
                  <span className="persona-tag" key={p}>
                    <Sparkles size={12} /> {p}
                  </span>
                ))}
              </div>
            </div>
            <div className="persona-aura" aria-hidden="true" />
          </div>

          {/* Taste DNA Visualizer */}
          <div className="profile-card taste-dna-card">
            <div className="card-header-flex">
              <div>
                <span className="eyebrow">Visual Analytics</span>
                <h2>Genre Affinity Radar</h2>
              </div>
            </div>

            {profile.isLoading ? (
              <div className="profile-loading">
                <span />
                <span />
                <span />
              </div>
            ) : profile.isError ? (
              <div className="error-banner" role="alert">
                {profile.error instanceof Error
                  ? profile.error.message
                  : "Profile data unavailable"}{" "}
                <button type="button" onClick={() => profile.refetch()}>
                  Try again
                </button>
              </div>
            ) : (
              <TasteDNAChart genres={data?.top_preferences.genres || []} />
            )}
          </div>

          {/* Creators & Themes */}
          <div className="profile-card">
            <h2>Affinity Breakdown</h2>
            <PreferenceList
              title="Favorite Actors & Stars"
              icon={Users}
              type="actor"
              items={data?.top_preferences.actors || []}
            />
            <PreferenceList
              title="Story Tropes & Themes"
              icon={Film}
              type="theme"
              items={data?.top_preferences.themes || []}
            />
            <PreferenceList
              title="Acclaimed Directors"
              icon={Clapperboard}
              type="director"
              items={data?.top_preferences.directors || []}
            />
          </div>
        </section>

        {/* Sidebar */}
        <aside className="profile-sidebar">
          {/* Marathon Statistics */}
          <div className="profile-card stat-summary-card">
            <h2>Marathon Stats</h2>
            <div className="stat-grid-modern">
              <div className="modern-stat-box">
                <Clock className="stat-icon" size={18} />
                <strong className="stat-val">{estimatedHours}h</strong>
                <span className="stat-desc">Est. Watch Time</span>
              </div>
              <div className="modern-stat-box">
                <Award className="stat-icon" size={18} />
                <strong className="stat-val">{completedCount}</strong>
                <span className="stat-desc">Completed</span>
              </div>
              <div className="modern-stat-box">
                <Star className="stat-icon" size={18} />
                <strong className="stat-val">{avgRating ?? "—"}</strong>
                <span className="stat-desc">Avg Score</span>
              </div>
              <div className="modern-stat-box">
                <Heart className="stat-icon" size={18} />
                <strong className="stat-val">{ratingsCount}</strong>
                <span className="stat-desc">Total Ratings</span>
              </div>
            </div>
          </div>

          {/* Interactive Teach SeoulMate Widget */}
          <div className="profile-card teach-widget-card">
            <span className="eyebrow">Fine-Tune Model</span>
            <h2>Teach SeoulMate</h2>
            {user ? (
              <form className="rate-form-modern" onSubmit={submit}>
                <label className="field-label" htmlFor="profile-drama">
                  Drama Title
                </label>
                <input
                  id="profile-drama"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder="e.g. Crash Landing on You"
                  required
                />

                <div className="star-rating-form-group">
                  <label className="field-label">Your Rating</label>
                  <StarRating
                    value={ratingScore}
                    onChange={(val) => setRatingScore(val)}
                  />
                </div>

                <button
                  className="primary-button"
                  type="submit"
                  disabled={rate.isPending}
                  style={{ width: "100%", marginTop: 8 }}
                >
                  {rate.isPending ? "Learning…" : "Submit Rating"}
                </button>
              </form>
            ) : (
              <div className="signin-prompt-box">
                <p className="muted">
                  Sign in to calibrate your personalized recommendation model and save
                  scores.
                </p>
                <Link
                  className="primary-button"
                  href="/auth/login"
                  style={{ display: "inline-block", textAlign: "center" }}
                >
                  Sign In
                </Link>
              </div>
            )}
            {message && (
              <p className="status-notice-message" role="status">
                {message}
              </p>
            )}
          </div>

          {/* Reset Action */}
          <div className="profile-card danger-zone-card">
            <h3>Reset Model Profile</h3>
            <p className="muted text-note">
              Clear all taste embeddings and start fresh from default cold-start weights.
            </p>
            <button
              className="danger-button"
              type="button"
              onClick={() => {
                if (
                  window.confirm(
                    "Reset everything SeoulMate has learned about your taste?",
                  )
                ) {
                  reset.mutate();
                }
              }}
              disabled={reset.isPending}
            >
              <RotateCcw size={14} style={{ display: "inline", marginRight: 6 }} />
              {reset.isPending ? "Resetting…" : "Reset Taste Profile"}
            </button>
          </div>
        </aside>
      </div>
    </>
  );
}
