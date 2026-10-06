"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, Film, MessageSquare, Send, ShieldAlert, Star, ThumbsUp } from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { getCommunityPost, updateCommunityPost, searchDramas } from "@/lib/api";
import type { Drama, PostType } from "@/lib/types";
import { StarRating } from "@/components/star-rating";

const POST_TYPES: Array<{ id: PostType; label: string; icon: typeof MessageSquare }> = [
  { id: "discussion", label: "Discussion", icon: MessageSquare },
  { id: "review", label: "Review", icon: Star },
  { id: "recommendation", label: "Recommendation", icon: ThumbsUp },
];

export default function EditPostPage({
  params,
}: {
  params: Promise<{ postId: string }>;
}) {
  const resolvedParams = use(params);
  const postId = resolvedParams.postId;

  const router = useRouter();
  const { user, getAccessToken } = useAuth();

  const [isLoading, setIsLoading] = useState(true);
  const [postType, setPostType] = useState<PostType>("discussion");
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [containsSpoilers, setContainsSpoilers] = useState(false);
  const [rating, setRating] = useState<number | null>(null);

  // Drama Search / Selection
  const [selectedDrama, setSelectedDrama] = useState<Drama | null>(null);
  const [dramaSearch, setDramaSearch] = useState("");
  const [searchResults, setSearchResults] = useState<Drama[]>([]);

  // Submission state
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadPost() {
      try {
        const token = user ? await getAccessToken() : null;
        const post = await getCommunityPost(postId, token);
        setPostType(post.post_type);
        setTitle(post.title);
        setBody(post.body);
        setContainsSpoilers(post.contains_spoilers);
        setRating(post.rating);
        if (post.drama) {
          setSelectedDrama({
            drama_id: post.drama.drama_id,
            Title: post.drama.title,
            poster_thumbnail_url: post.drama.poster_thumbnail_url ?? undefined,
          });
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load post");
      } finally {
        setIsLoading(false);
      }
    }
    loadPost();
  }, [postId, user, getAccessToken]);

  async function handleDramaSearch(term: string) {
    setDramaSearch(term);
    if (!term.trim()) {
      setSearchResults([]);
      return;
    }
    try {
      const res = await searchDramas({ query: term, topN: 5 });
      setSearchResults(res.recommendations);
    } catch {
      setSearchResults([]);
    }
  }

  function handleSelectDrama(drama: Drama) {
    setSelectedDrama(drama);
    setDramaSearch("");
    setSearchResults([]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (!user) {
      router.push(`/auth?returnUrl=${encodeURIComponent(`/community/edit/${postId}`)}`);
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

      await updateCommunityPost(
        postId,
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

      router.push(`/community/${postId}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update post");
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <main className="shell community-composer-container">
        <p className="muted">Loading post details…</p>
      </main>
    );
  }

  return (
    <main className="shell community-composer-container">
      <div className="composer-back-row">
        <Link href={`/community/${postId}`} className="text-link back-link">
          <ArrowLeft size={16} />
          <span>Back to Post</span>
        </Link>
      </div>

      <div className="composer-card-box">
        <div className="composer-card-header">
          <h1 className="display composer-title">Edit Discussion</h1>
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
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              maxLength={120}
              required
            />
          </div>

          {/* Associated Drama Selector */}
          <div className="form-field-group">
            <label className="field-label">Associated Drama</label>
            {selectedDrama ? (
              <div className="selected-drama-chip">
                <Film size={16} className="film-icon" />
                <span className="selected-drama-name">{selectedDrama.Title}</span>
                <button
                  type="button"
                  className="remove-drama-btn"
                  onClick={() => setSelectedDrama(null)}
                >
                  ✕
                </button>
              </div>
            ) : (
              <div className="drama-search-combobox">
                <input
                  type="text"
                  className="text-input"
                  placeholder="Search a K-drama to link…"
                  value={dramaSearch}
                  onChange={(e) => handleDramaSearch(e.target.value)}
                />
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
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            )}
          </div>

          {/* Review Rating */}
          {postType === "review" && (
            <div className="form-field-group rating-field-box">
              <label className="field-label">Review Rating (1–10)</label>
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
              </div>
            </label>
          </div>

          {/* Actions */}
          <div className="composer-button-row">
            <Link href={`/community/${postId}`} className="ghost-button cancel-btn">
              Cancel
            </Link>
            <button
              type="submit"
              className="primary-button publish-btn"
              disabled={isSubmitting || !title.trim() || !body.trim()}
            >
              <Send size={16} />
              <span>{isSubmitting ? "Saving…" : "Save Changes"}</span>
            </button>
          </div>
        </form>
      </div>
    </main>
  );
}
