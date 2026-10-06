"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  Compass,
  Flame,
  MessageSquarePlus,
  RefreshCw,
  Search,
  Sparkles,
  Star,
  ThumbsUp,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { deleteCommunityPost, getCommunityPosts } from "@/lib/api";
import type { PostType } from "@/lib/types";
import { CommunityPostCard } from "@/components/community-post-card";
import { CommunitySkeleton } from "@/components/community-skeleton";

const TABS = [
  { id: "trending", label: "Trending", icon: Flame },
  { id: "recent", label: "Recent", icon: Compass },
  { id: "review", label: "Reviews", icon: Star },
  { id: "recommendation", label: "Recommendations", icon: ThumbsUp },
] as const;

export default function CommunityPage() {
  const searchParams = useSearchParams();
  const initialSearch = searchParams.get("q") || "";
  const initialTab = searchParams.get("tab") || "trending";

  const { user, getAccessToken } = useAuth();
  const [activeTab, setActiveTab] = useState<string>(initialTab);
  const [searchInput, setSearchInput] = useState(initialSearch);
  const [searchQuery, setSearchQuery] = useState(initialSearch);
  const [page, setPage] = useState(1);

  // Map activeTab to filters
  const sortParam: "trending" | "recent" = activeTab === "recent" ? "recent" : "trending";
  const postTypeParam: PostType | undefined =
    activeTab === "review"
      ? "review"
      : activeTab === "recommendation"
      ? "recommendation"
      : undefined;

  const {
    data,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: [
      "community-feed",
      activeTab,
      searchQuery,
      page,
      user?.id,
    ],
    queryFn: async ({ signal }) => {
      const token = user ? await getAccessToken() : null;
      return getCommunityPosts(
        {
          page,
          limit: 10,
          post_type: postTypeParam,
          search: searchQuery || undefined,
          sort: sortParam,
        },
        token,
        signal,
      );
    },
    staleTime: 1000 * 60 * 2,
  });

  function handleSearchSubmit(e: React.FormEvent) {
    e.preventDefault();
    setPage(1);
    setSearchQuery(searchInput.trim());
  }

  function handleTabChange(tabId: string) {
    setActiveTab(tabId);
    setPage(1);
  }

  async function handleDeletePost(postId: string) {
    if (!user) return;
    const token = await getAccessToken();
    if (!token) return;
    await deleteCommunityPost(postId, token);
    refetch();
  }

  const posts = data?.posts || [];
  const hasMore = data?.has_more;

  return (
    <main className="shell community-page-container">
      {/* Header Banner */}
      <section className="community-header-panel">
        <div className="community-header-content">
          <span className="eyebrow community-eyebrow">
            K-Drama Community
          </span>
          <h1 className="display community-page-title">
            SeoulMate Community
          </h1>
          <p className="community-page-desc">
            A kinder, spoiler-safe space for K-drama fans to discuss theories, share
            honest reviews, and recommend hidden gems.
          </p>
        </div>

        <div className="community-header-actions">
          <Link
            href="/community/new"
            className="primary-button create-discussion-btn"
          >
            <MessageSquarePlus size={18} />
            <span>Start a discussion</span>
          </Link>
        </div>
      </section>

      {/* Search & Tabs Toolbar */}
      <div className="community-toolbar">
        {/* Search input */}
        <form className="community-search-bar" onSubmit={handleSearchSubmit}>
          <Search size={18} className="search-icon" />
          <input
            type="search"
            placeholder="Search discussions, reviews, or dramas…"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            aria-label="Search community content"
          />
          <button type="submit" className="ghost-button search-submit-btn">
            Search
          </button>
        </form>

        {/* Filter Tabs */}
        <div className="community-filter-tabs" role="tablist">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isSelected = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                type="button"
                role="tab"
                aria-selected={isSelected}
                className={`community-tab-btn ${isSelected ? "active" : ""}`}
                onClick={() => handleTabChange(tab.id)}
              >
                <Icon size={15} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Main Feed Content */}
      <div className="community-feed-layout">
        {isLoading ? (
          <CommunitySkeleton count={4} />
        ) : isError ? (
          <div className="error-banner community-error-card" role="alert">
            <p>{error instanceof Error ? error.message : "Failed to load community discussions"}</p>
            <button
              type="button"
              className="ghost-button retry-btn"
              onClick={() => refetch()}
            >
              <RefreshCw size={14} className={isFetching ? "spinning" : ""} />
              <span>Try again</span>
            </button>
          </div>
        ) : posts.length === 0 ? (
          <div className="empty-state community-empty-card">
            <Sparkles size={36} className="empty-state-icon" />
            <h2>No discussions found</h2>
            <p>
              {searchQuery
                ? `No posts matched “${searchQuery}”. Try a broader search term.`
                : "Be the very first member to kick off a discussion in this topic!"}
            </p>
            <Link href="/community/new" className="primary-button">
              <MessageSquarePlus size={16} />
              <span>Create the first post</span>
            </Link>
          </div>
        ) : (
          <div className="community-posts-list">
            {posts.map((post) => (
              <CommunityPostCard
                key={post.id}
                post={post}
                onDelete={handleDeletePost}
              />
            ))}

            {/* Load More Button */}
            {hasMore && (
              <div className="load-more-container">
                <button
                  type="button"
                  className="ghost-button load-more-btn"
                  onClick={() => setPage((p) => p + 1)}
                  disabled={isFetching}
                >
                  <RefreshCw size={15} className={isFetching ? "spinning" : ""} />
                  <span>{isFetching ? "Loading more…" : "Load more discussions"}</span>
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </main>
  );
}
