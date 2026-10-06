"use client";

import { use, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  Edit3,
  Film,
  MessageSquare,
  ShieldAlert,
  ShieldCheck,
  Star,
  Trash2,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { deleteCommunityPost, getCommunityComments, getCommunityPost } from "@/lib/api";
import { CommunityComments } from "@/components/community-comments";
import { PosterImage } from "@/components/poster-image";
import { ReactionButton } from "@/components/reaction-button";
import { SpoilerContent } from "@/components/spoiler-content";

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

export default function PostDetailPage({
  params,
}: {
  params: Promise<{ postId: string }>;
}) {
  const resolvedParams = use(params);
  const postId = resolvedParams.postId;

  const router = useRouter();
  const { user, getAccessToken } = useAuth();
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  // Fetch post details
  const postQuery = useQuery({
    queryKey: ["community-post", postId, user?.id],
    queryFn: async ({ signal }) => {
      const token = user ? await getAccessToken() : null;
      return getCommunityPost(postId, token, signal);
    },
  });

  // Fetch comments
  const commentsQuery = useQuery({
    queryKey: ["community-comments", postId, user?.id],
    queryFn: async ({ signal }) => {
      const token = user ? await getAccessToken() : null;
      return getCommunityComments(postId, token, signal);
    },
  });

  async function handleDelete() {
    if (!user) return;
    setIsDeleting(true);
    try {
      const token = await getAccessToken();
      if (!token) throw new Error("Authentication required");
      await deleteCommunityPost(postId, token);
      router.push("/community");
    } catch (err) {
      alert(err instanceof Error ? err.message : "Failed to delete post");
      setIsDeleting(false);
      setConfirmDelete(false);
    }
  }

  if (postQuery.isLoading) {
    return (
      <main className="shell community-detail-container">
        <div className="composer-back-row">
          <Link href="/community" className="text-link back-link">
            <ArrowLeft size={16} />
            <span>Back to Community</span>
          </Link>
        </div>
        <div className="community-card-skeleton-full" style={{ marginTop: 24 }} />
      </main>
    );
  }

  if (postQuery.isError || !postQuery.data) {
    return (
      <main className="shell community-detail-container">
        <div className="composer-back-row">
          <Link href="/community" className="text-link back-link">
            <ArrowLeft size={16} />
            <span>Back to Community</span>
          </Link>
        </div>
        <div className="error-banner" style={{ marginTop: 24 }} role="alert">
          <p>
            {postQuery.error instanceof Error
              ? postQuery.error.message
              : "Discussion not found"}
          </p>
          <Link href="/community" className="primary-button" style={{ marginTop: 12 }}>
            Return to Community
          </Link>
        </div>
      </main>
    );
  }

  const post = postQuery.data;
  const isAuthor = post.is_author;
  const exactDate = new Date(post.created_at).toLocaleString(undefined, {
    dateStyle: "full",
    timeStyle: "short",
  });

  const typeLabel =
    post.post_type === "review"
      ? "Review"
      : post.post_type === "recommendation"
      ? "Recommendation"
      : "Discussion";

  return (
    <main className="shell community-detail-container">
      {/* Back button */}
      <div className="composer-back-row">
        <Link href="/community" className="text-link back-link">
          <ArrowLeft size={16} />
          <span>Back to Community</span>
        </Link>
      </div>

      <article className="community-detail-card">
        {/* Author & Meta Row */}
        <div className="detail-header-row">
          <div className="detail-author-box">
            <div className="detail-author-avatar">
              {post.author.avatar_url ? (
                /* eslint-disable-next-line @next/next/no-img-element */
                <img src={post.author.avatar_url} alt={post.author.display_name} />
              ) : (
                post.author.display_name.slice(0, 1).toUpperCase()
              )}
            </div>
            <div>
              <strong className="detail-author-name">{post.author.display_name}</strong>
              <div className="detail-date-row">
                <time
                  className="detail-relative-time"
                  dateTime={post.created_at}
                  title={exactDate}
                >
                  {formatRelativeTime(post.created_at)}
                </time>
                <span className="dot-divider">•</span>
                <span className="detail-exact-time muted">{exactDate}</span>
              </div>
            </div>
          </div>

          {/* Badges & Actions */}
          <div className="detail-meta-actions">
            <span className={`post-type-pill type-${post.post_type}`}>
              {typeLabel}
            </span>

            {post.rating !== null && post.rating !== undefined && (
              <span className="post-rating-pill" title={`Rating: ${post.rating}/10`}>
                <Star size={13} fill="currentColor" />
                <span>{post.rating} / 10</span>
              </span>
            )}

            {!post.contains_spoilers ? (
              <span className="spoiler-safe-badge">
                <ShieldCheck size={12} />
                <span>Spoiler-safe</span>
              </span>
            ) : (
              <span className="spoiler-warning-badge">
                <ShieldAlert size={12} />
                <span>Contains spoilers</span>
              </span>
            )}

            {isAuthor && (
              <div className="detail-author-controls">
                <Link
                  href={`/community/edit/${post.id}`}
                  className="ghost-button edit-post-btn"
                  title="Edit this post"
                >
                  <Edit3 size={14} />
                  <span>Edit</span>
                </Link>
                <button
                  type="button"
                  className="danger-button delete-post-btn"
                  onClick={() => setConfirmDelete(true)}
                  title="Delete this post"
                >
                  <Trash2 size={14} />
                  <span>Delete</span>
                </button>
              </div>
            )}
          </div>
        </div>

        {/* Delete Confirmation Alert */}
        {confirmDelete && (
          <div className="inline-confirm-box detail-confirm" role="alert">
            <p>Are you sure you want to delete this discussion? All comments will also be deleted.</p>
            <div className="inline-confirm-actions">
              <button
                type="button"
                className="danger-button confirm-delete-btn"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? "Deleting…" : "Yes, delete discussion"}
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
        <h1 className="display detail-post-title">{post.title}</h1>

        {/* Associated Drama Banner if present */}
        {post.drama && (
          <div className="detail-drama-banner">
            <Link
              href={`/drama/${encodeURIComponent(post.drama.title)}`}
              className="detail-drama-banner-link"
              title={`View ${post.drama.title}`}
            >
              <div className="detail-drama-thumb">
                {post.drama.poster_thumbnail_url ? (
                  <PosterImage
                    src={post.drama.poster_thumbnail_url}
                    alt={post.drama.title}
                  />
                ) : (
                  <Film size={20} />
                )}
              </div>
              <div className="detail-drama-info">
                <span className="eyebrow" style={{ color: "var(--coral)", fontSize: "0.68rem" }}>
                  Discussing Drama
                </span>
                <strong className="detail-drama-title">{post.drama.title}</strong>
                {post.drama.rating_value && (
                  <span className="detail-drama-score">
                    ★ {post.drama.rating_value}
                    {post.drama.year ? ` (${post.drama.year})` : ""}
                  </span>
                )}
              </div>
            </Link>
          </div>
        )}

        {/* Post Body (with Spoiler protection) */}
        <div className="detail-post-body">
          <SpoilerContent isSpoiler={post.contains_spoilers}>
            <div className="detail-post-text">
              {post.body.split("\n\n").map((paragraph, idx) => (
                <p key={idx}>{paragraph}</p>
              ))}
            </div>
          </SpoilerContent>
        </div>

        {/* Action bar */}
        <div className="detail-action-bar">
          <ReactionButton
            postId={post.id}
            initialLiked={Boolean(post.is_liked_by_me)}
            initialCount={post.like_count}
            size={18}
          />

          <a href="#comments" className="feed-comment-link detail-comment-count">
            <MessageSquare size={17} />
            <span>{post.comment_count} comments</span>
          </a>
        </div>
      </article>

      {/* Comments Section */}
      <CommunityComments
        postId={post.id}
        comments={commentsQuery.data || []}
        isLoading={commentsQuery.isLoading}
        onRefresh={() => {
          postQuery.refetch();
          commentsQuery.refetch();
        }}
      />
    </main>
  );
}
