"use client";

import { useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { ArrowRight, Flame, MessageSquare, ShieldCheck, ShieldAlert, Heart, ChevronLeft, ChevronRight } from "lucide-react";
import { getCommunityTrending } from "@/lib/api";
import { PosterImage } from "@/components/poster-image";

export function CommunityTrendingSection() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const { data: trendingPosts, isLoading, isError } = useQuery({
    queryKey: ["community-trending"],
    queryFn: ({ signal }) => getCommunityTrending(signal),
    staleTime: 1000 * 60 * 3,
  });

  if (isError) {
    // Fail gracefully: don't break the homepage recommendations if community endpoint fails
    return null;
  }

  function handleScroll(direction: "left" | "right") {
    if (!scrollRef.current) return;
    const scrollAmount = 300;
    scrollRef.current.scrollBy({
      left: direction === "left" ? -scrollAmount : scrollAmount,
      behavior: "smooth",
    });
  }

  return (
    <section className="section community-trending-section" aria-labelledby="trending-community-title">
      <div className="shell">
        <div className="section-heading trending-heading-row">
          <div className="trending-title-wrap">
            <span className="trending-fire-icon" aria-hidden="true">
              🔥
            </span>
            <h2 id="trending-community-title" className="display trending-section-title">
              Trending in the community
            </h2>
          </div>
          <div className="trending-header-actions">
            <div className="trending-scroll-controls" aria-label="Scroll trending items">
              <button
                type="button"
                className="trending-scroll-btn"
                onClick={() => handleScroll("left")}
                aria-label="Scroll discussions left"
              >
                <ChevronLeft size={16} />
              </button>
              <button
                type="button"
                className="trending-scroll-btn"
                onClick={() => handleScroll("right")}
                aria-label="Scroll discussions right"
              >
                <ChevronRight size={16} />
              </button>
            </div>
            <Link href="/community" className="text-link see-all-link">
              <span>See all discussions</span>
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>

        {isLoading ? (
          <div className="trending-grid" ref={scrollRef}>
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="trending-card-skeleton" />
            ))}
          </div>
        ) : (
          <div
            className="trending-grid"
            ref={scrollRef}
            tabIndex={0}
            role="region"
            aria-label="Trending community discussions"
          >
            {trendingPosts?.map((post) => {
              const postTypeLabel =
                post.post_type === "recommendation"
                  ? "Recommendation"
                  : post.post_type === "review"
                  ? "Review"
                  : "Discussion";

              return (
                <Link
                  key={post.id}
                  href={`/community/${post.id}`}
                  className="trending-card"
                  title={post.title}
                >
                  <div className="trending-card-thumb">
                    {post.drama_poster_thumbnail_url ? (
                      <PosterImage
                        src={post.drama_poster_thumbnail_url}
                        alt={post.drama_title || post.title}
                      />
                    ) : (
                      <div className="trending-card-thumb-fallback">
                        <Flame size={20} />
                      </div>
                    )}
                  </div>

                  <div className="trending-card-content">
                    <h3 className="trending-card-title">{post.short_title || post.title}</h3>

                    <div className="trending-card-badges">
                      {!post.contains_spoilers ? (
                        <span className="spoiler-safe-badge">
                          <ShieldCheck size={11} />
                          <span>Spoiler-safe</span>
                        </span>
                      ) : (
                        <span className="spoiler-warning-badge">
                          <ShieldAlert size={11} />
                          <span>Spoiler</span>
                        </span>
                      )}
                      <span className={`post-type-chip post-type-${post.post_type}`}>{postTypeLabel}</span>
                    </div>

                    <div className="trending-card-footer">
                      {/* Participant Avatars */}
                      <div className="trending-avatar-stack">
                        {post.participant_avatars?.slice(0, 3).map((av, idx) => (
                          <div
                            key={idx}
                            className="participant-avatar-dot"
                            style={{ zIndex: 3 - idx }}
                          >
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img src={av} alt="Participant" />
                          </div>
                        ))}
                      </div>

                      {/* Stats */}
                      <div className="trending-stats-row">
                        {post.like_count > 0 && (
                          <span className="trending-stat" title={`${post.like_count} likes`}>
                            <Heart size={13} fill="currentColor" />
                            <span>{post.like_count >= 1000 ? `${(post.like_count / 1000).toFixed(1)}K` : post.like_count}</span>
                          </span>
                        )}
                        <span className="trending-stat" title={`${post.comment_count} comments`}>
                          <MessageSquare size={13} />
                          <span>{post.comment_count >= 1000 ? `${(post.comment_count / 1000).toFixed(1)}K` : post.comment_count}</span>
                        </span>
                      </div>
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}
