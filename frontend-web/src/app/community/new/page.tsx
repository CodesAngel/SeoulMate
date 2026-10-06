"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Film, MessageSquare, Send, ShieldAlert, Star, ThumbsUp } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { useApp } from "@/components/app-provider";
import { createCommunityPost, searchDramas } from "@/lib/api";
import type { Drama, PostType } from "@/lib/types";
import { StarRating } from "@/components/star-rating";

const POST_TYPES: Array<{ id: PostType; label: string; desc: string; icon: typeof MessageSquare }> = [
  {
    id: "discussion",
    label: "Discussion",
    desc: "Theories, character debates, and questions",
    icon: MessageSquare,
  },
  {
    id: "review",
    label: "Review",
    desc: "Your honest thoughts with an optional 1–10 score",
    icon: Star,
  },
  {
    id: "recommendation",
    label: "Recommendation",
    desc: "Highlight hidden gems and curated watchlists",
    icon: ThumbsUp,
  },
];

export default function NewPostPage() {
  const router = useRouter();
  const { user, getAccessToken } = useAuth();
  const { ratingEntries } = useApp();

  const [postType, setPostType] = useState<PostType>("discussion");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [containsSpoilers, setContainsSpoilers] = useState(false);
  const [rating, setRating] = useState<number | null>(null);

  // Drama Search / Selection
  const [dramaSearch, setDramaSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Drama[]>([]);
  const [selectedDrama, setSelectedDrama] = useState<Drama | null>(null);
  const [isSearchingDrama, setIsSearchingDrama] = useState(false);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  async function handleDramaSearch(term: string) {
    setDramaSearch(term);
    if (!term.trim()) {
      setSearchResults([]);
      return;
    }
    setIsSearchingDrama(true);
    try {
      const res = await searchDramas({ query: term, topN: 5 });
      setSearchResults(res.recommendations);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearchingDrama(false);
    }
  }

  function handleSelectDrama(drama: Drama) {
    setSelectedDrama(drama);
    setDramaSearch("");
    setSearchResults([]);

    // Check if user already rated this drama
    const existingRating = ratingEntries.find(
      (r) =>
        (r.drama.drama_id && r.drama.drama_id === drama.drama_id) ||
        r.drama.Title.toLowerCase() === drama.Title.toLowerCase(),
    );
    if (existingRating && rating === null) {
      setRating(existingRating.rating);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!user) {
      router.push(`/auth?returnUrl=${encodeURIComponent("/community/new")}`);
      return;
    }

    if (!title.trim() || !body.trim()) {
      setError("Please fill out both the title and body.");
      return;
    }

    setIsSubmitting(true);

    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Authentication required");

      const created = await createCommunityPost(
        {
          post_type: postType,
          title: title.trim(),
          body: body.trim(),
          drama_id: selectedDrama?.drama_id ?? null,
          rating: postType === "review" ? rating : null,
          contains_spoilers: containsSpoilers,
        },
        token,
      );

      router.push(`/community/${created.id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to publish post");
      setIsSubmitting(false);
    }
  }

  if (!user) {
    return (
      <main className="shell community-composer-container">
        <div className="signin-prompt-card">
          <h2>Sign in to start a discussion</h2>
          <p>You need to be signed in to create discussions, post reviews, and share recommendations.</p>
          <Link
            href={`/auth?returnUrl=${encodeURIComponent("/community/new")}`}
            className="primary-button"
          >
            Sign in now
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="shell community-composer-container">
      {/* Back Link */}
      <div className="composer-back-row">
        <Link href="/community" className="text-link back-link">
          <ArrowLeft size={16} />
          <span>Back to Community</span>
        </Link>
      </div>

      <div className="composer-card-box">
        <div className="composer-card-header">
          <h1 className="display composer-title">Start a Discussion</h1>
          <p className="composer-subtitle">
            Share your theories, honest reviews, or recommendations with the SeoulMate community.
          </p>
        </div>

        {error && (
          <div className="error-banner" role="alert">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="community-create-form">
          {/* Post Type Selector */}
          <div className="form-field-group">
            <label className="field-label">Post Type</label>
            <div className="post-type-selector-grid">
              {POST_TYPES.map((t) => {
                const Icon = t.icon;
                const active = postType === t.id;
                return (
                  <button
                    key={t.id}
                    type="button"
                    className={`post-type-select-card ${active ? "active" : ""}`}
                    onClick={() => setPostType(t.id)}
                  >
                    <div className="type-card-head">
                      <Icon size={18} />
                      <strong>{t.label}</strong>
                    </div>
                    <p>{t.desc}</p>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Title */}
          <div className="form-field-group">
            <div className="field-label-row">
              <label htmlFor="post-title-input" className="field-label">
                Title
              </label>
              <span className="char-count">{title.length}/120</span>
            </div>
            <input
              id="post-title-input"
              type="text"
              className="text-input"
              placeholder="e.g. What did you think of the final scene?"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={120}
              required
            />
          </div>

          {/* Associated Drama Selector */}
          <div className="form-field-group">
            <label className="field-label">
              Associated Drama <span className="muted">(Optional)</span>
            </label>

            {selectedDrama ? (
              <div className="selected-drama-chip">
                <Film size={16} className="film-icon" />
                <span className="selected-drama-name">{selectedDrama.Title}</span>
                <button
                  type="button"
                  className="remove-drama-btn"
                  onClick={() => setSelectedDrama(null)}
                  aria-label="Remove associated drama"
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="drama-search-combobox">
                <input
                  type="text"
                  className="text-input"
                  placeholder="Search a K-drama to link (e.g. Crash Landing on You)…"
                  value={dramaSearch}
                  onChange={(e) => handleDramaSearch(e.target.value)}
                />
                {isSearchingDrama && (
                  <p className="field-hint" style={{ marginTop: 4 }}>Searching catalog...</p>
                )}
                {searchResults.length > 0 && (
                  <ul className="drama-search-dropdown-menu" role="listbox">
                    {searchResults.map((d) => (
                      <li
                        key={d.drama_id || d.Title}
                        className="drama-search-option"
                        onClick={() => handleSelectDrama(d)}
                        role="option"
                        aria-selected={false}
                      >
                        <strong>{d.Title}</strong>
                        {d["Release Years"] && <span className="muted"> ({d["Release Years"]})</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* Review Rating (if Review type) */}
          {postType === "review" && (
            <div className="form-field-group rating-field-box">
              <label className="field-label">Your Review Rating (1–10)</label>
              <div style={{ marginTop: 6 }}>
                <StarRating
                  value={rating || 0}
                  onChange={(val) => setRating(val)}
                />
              </div>
            </div>
          )}

          {/* Body */}
          <div className="form-field-group">
            <div className="field-label-row">
              <label htmlFor="post-body-input" className="field-label">
                Content
              </label>
              <span className="char-count">{body.length}/2000</span>
            </div>
            <textarea
              id="post-body-input"
              className="text-area-input"
              placeholder="Write your thoughts, analysis, or review here…"
              value={body}
              onChange={(e) => setBody(e.target.value)}
              maxLength={2000}
              rows={8}
              required
            />
          </div>

          {/* Spoiler Checkbox */}
          <div className="form-field-group spoiler-checkbox-group">
            <label className="spoiler-checkbox-label">
              <input
                type="checkbox"
                checked={containsSpoilers}
                onChange={(e) => setContainsSpoilers(e.target.checked)}
              />
              <ShieldAlert size={16} className="spoiler-icon" />
              <div>
                <strong>Mark as containing spoilers</strong>
                <p className="muted" style={{ margin: "2px 0 0", fontSize: "0.8rem" }}>
                  Hides the content behind a reveal shield to protect viewers who haven&apos;t finished the show.
                </p>
              </div>
            </label>
          </div>

          {/* Actions */}
          <div className="composer-button-row">
            <Link href="/community" className="ghost-button cancel-btn">
              Cancel
            </Link>
            <button
              type="submit"
              className="primary-button publish-btn"
              disabled={isSubmitting || !title.trim() || !body.trim()}
            >
              <Send size={16} />
              <span>{isSubmitting ? "Publishing…" : "Publish Post"}</span>
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
