"use client";

import Link from "next/link";
import { MessageSquare, MoreHorizontal, ShieldAlert, ShieldCheck, Star, Trash2, Edit3, Film } from "lucide-react";
import { useState } from "react";
import type { CommunityPost } from "@/lib/types";
import { ReactionButton } from "@/components/reaction-button";
import { SpoilerContent } from "@/components/spoiler-content";
import { PosterImage } from "@/components/poster-image";

interface CommunityPostCardProps {
  post: CommunityPost;
  onDelete?: (postId: string) => Promise<void>;
}

function formatRelativeTime(dateStr: string): string {
  try {
    const diffMs = Date.now() - new Date(dateStr).getTime();
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);

    if (diffDay > 0) return `${diffDay}d ago`;
    if (diffHour > 0) return `${diffHour}h ago`;
    if (diffMin > 0) return `${diffMin}m ago`;
    return "just now";
  } catch {
    return "recently";
  }
}

export function CommunityPostCard({ post, onDelete }: CommunityPostCardProps) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const exactTime = new Date(post.created_at).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });

  const typeLabel =
    post.post_type === "review"
      ? "Review"
      : post.post_type === "recommendation"
      ? "Recommendation"
      : "Discussion";

  async function handleDelete() {
    if (!onDelete) return;
    setIsDeleting(true);
    try {
      await onDelete(post.id);
    } catch {
      setIsDeleting(false);
      setConfirmDelete(false);
    }
  }

  return (
    <article className="community-post-card" aria-labelledby={`post-title-${post.id}`}>
      {/* Header */}
      <div className="post-card-top-row">
        <div className="post-card-author-group">
          <div className="post-author-avatar">
            {post.author.avatar_url ? (
              /* eslint-disable-next-line @next/next/no-img-element */
              <img src={post.author.avatar_url} alt={post.author.display_name} />
            ) : (
              <div className="post-avatar-fallback">
                {post.author.display_name.slice(0, 1).toUpperCase()}
              </div>
            )}
          </div>
          <div className="post-author-meta">
            <strong className="post-author-name">{post.author.display_name}</strong>
            <time
              className="post-timestamp"
              dateTime={post.created_at}
              title={exactTime}
            >
              {formatRelativeTime(post.created_at)}
            </time>
          </div>
        </div>

        <div className="post-card-chips">
          <span className={`post-type-pill type-${post.post_type}`}>
            {typeLabel}
          </span>

          {post.rating !== null && post.rating !== undefined && (
            <span className="post-rating-pill" title={`Rating: ${post.rating}/10`}>
              <Star size={12} fill="currentColor" />
              <span>{post.rating}</span>
            </span>
          )}

          {!post.contains_spoilers ? (
            <span className="spoiler-safe-badge" title="No spoilers">
              <ShieldCheck size={12} />
              <span>Spoiler-safe</span>
            </span>
          ) : (
            <span className="spoiler-warning-badge" title="Contains spoilers">
              <ShieldAlert size={12} />
              <span>Spoiler</span>
            </span>
          )}

          {post.is_author && (
            <div className="post-owner-menu-container">
              <button
                type="button"
                className="icon-button post-menu-btn"
                onClick={() => setMenuOpen(!menuOpen)}
                aria-label="Author actions"
                aria-expanded={menuOpen}
              >
                <MoreHorizontal size={17} />
              </button>
              {menuOpen && (
                <div className="post-menu-dropdown" role="menu">
                  <Link
                    href={`/community/edit/${post.id}`}
                    className="post-menu-item"
                    role="menuitem"
                  >
                    <Edit3 size={14} />
                    <span>Edit post</span>
                  </Link>
                  <button
                    type="button"
                    className="post-menu-item delete"
                    onClick={() => {
                      setMenuOpen(false);
                      setConfirmDelete(true);
                    }}
                    role="menuitem"
                  >
                    <Trash2 size={14} />
                    <span>Delete post</span>
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Delete Confirmation Modal / Inline warning */}
      {confirmDelete && (
        <div className="inline-confirm-box" role="alert">
          <p>Are you sure you want to delete this post? This cannot be undone.</p>
          <div className="inline-confirm-actions">
            <button
              type="button"
              className="danger-button confirm-delete-btn"
              onClick={handleDelete}
              disabled={isDeleting}
            >
              {isDeleting ? "Deleting…" : "Yes, delete"}
            </button>
            <button
              type="button"
              className="ghost-button"
              onClick={() => setConfirmDelete(false)}
              disabled={isDeleting}
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Title */}
      <h2 id={`post-title-${post.id}`} className="post-card-title">
        <Link href={`/community/${post.id}`} className="post-title-link">
          {post.title}
        </Link>
      </h2>

      {/* Body */}
      <div className="post-card-body-snippet">
        <SpoilerContent isSpoiler={post.contains_spoilers} previewOnly>
          <Link href={`/community/${post.id}`} className="post-body-link">
            <p className="post-snippet-text">{post.body}</p>
          </Link>
        </SpoilerContent>
      </div>

      {/* Associated Drama Chip / Card */}
      {post.drama && (
        <div className="post-drama-reference">
          <Link
            href={`/drama/${encodeURIComponent(post.drama.title)}`}
            className="drama-reference-link"
            title={`View ${post.drama.title} details`}
          >
            <div className="drama-reference-poster">
              {post.drama.poster_thumbnail_url ? (
                <PosterImage
                  src={post.drama.poster_thumbnail_url}
                  alt={post.drama.title}
                />
              ) : (
                <Film size={16} />
              )}
            </div>
            <div className="drama-reference-info">
              <span className="drama-ref-label">Associated Drama</span>
              <strong className="drama-ref-title">{post.drama.title}</strong>
              {post.drama.rating_value && (
                <span className="drama-ref-rating">
                  ★ {post.drama.rating_value}
                  {post.drama.year ? ` • ${post.drama.year}` : ""}
                </span>
              )}
            </div>
          </Link>
        </div>
      )}

      {/* Bottom Action Bar */}
      <div className="post-card-action-bar">
        <ReactionButton
          postId={post.id}
          initialLiked={Boolean(post.is_liked_by_me)}
          initialCount={post.like_count}
        />

        <Link
          href={`/community/${post.id}#comments`}
          className="post-action-comment-link"
          aria-label={`${post.comment_count} comments`}
        >
          <MessageSquare size={16} />
          <span>{post.comment_count} {post.comment_count === 1 ? "comment" : "comments"}</span>
        </Link>
      </div>
    </article>
  );
}
