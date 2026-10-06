"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, Bookmark, MessageSquare, MoreHorizontal } from "lucide-react";
import { getHomepageCommunity } from "@/lib/api";
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

export function CommunityFromSection() {
  const { data: posts, isLoading, isError } = useQuery({
    queryKey: ["homepage-community-feed"],
    queryFn: ({ signal }) => getHomepageCommunity(signal),
    staleTime: 1000 * 60 * 3,
  });

  if (isError) {
    // Fail gracefully: homepage continues working
    return null;
  }

  return (
    <section className="section community-from-section" aria-labelledby="from-community-title">
      <div className="shell">
        <div className="section-heading from-community-header">
          <div>
            <h2 id="from-community-title" className="display from-community-heading">
              From the community
            </h2>
            <p className="from-community-subtitle">
              Real fans. Real thoughts. A kinder, spoiler-safe space to share your love for K-dramas.
            </p>
          </div>
          <Link href="/community" className="primary-button join-conversation-btn">
            <span>Join the conversation</span>
            <ArrowRight size={17} />
          </Link>
        </div>

        {isLoading ? (
          <div className="community-cards-grid">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="community-card-skeleton" />
            ))}
          </div>
        ) : (
          <div className="community-cards-grid">
            {posts?.map((post) => (
              <article key={post.id} className="community-feed-card">
                {/* Author row */}
                <div className="feed-card-header">
                  <div className="feed-author-info">
                    <div className="feed-author-avatar">
                      {post.author.avatar_url ? (
                        /* eslint-disable-next-line @next/next/no-img-element */
                        <img src={post.author.avatar_url} alt={post.author.display_name} />
                      ) : (
                        <div className="author-avatar-fallback">
                          {post.author.display_name.slice(0, 1).toUpperCase()}
                        </div>
                      )}
                    </div>
                    <div>
                      <strong className="feed-author-name">{post.author.display_name}</strong>
                      <span className="feed-post-time">
                        {formatRelativeTime(post.created_at)}
                      </span>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="feed-more-btn"
                    aria-label="Post options"
                  >
                    <MoreHorizontal size={18} />
                  </button>
                </div>

                {/* Post body */}
                <div className="feed-card-body">
                  <SpoilerContent isSpoiler={post.contains_spoilers} previewOnly>
                    <Link href={`/community/${post.id}`} className="feed-card-text-link">
                      <p className="feed-post-text">{post.body}</p>
                    </Link>
                  </SpoilerContent>
                </div>

                {/* Drama Banner / Image */}
                {post.drama && (
                  <Link href={`/community/${post.id}`} className="feed-card-media-banner">
                    <div className="feed-media-container">
                      <PosterImage
                        src={post.drama.poster_thumbnail_url}
                        alt={post.drama.title}
                      />
                    </div>
                  </Link>
                )}

                {/* Footer Actions */}
                <div className="feed-card-footer">
                  <div className="feed-actions-left">
                    <ReactionButton
                      postId={post.id}
                      initialLiked={Boolean(post.is_liked_by_me)}
                      initialCount={post.like_count}
                    />

                    <Link
                      href={`/community/${post.id}#comments`}
                      className="feed-comment-link"
                      aria-label={`${post.comment_count} comments`}
                    >
                      <MessageSquare size={17} />
                      <span>{post.comment_count}</span>
                    </Link>
                  </div>

                  <button
                    type="button"
                    className="feed-bookmark-btn"
                    aria-label="Save discussion"
                  >
                    <Bookmark size={17} />
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  );
}
