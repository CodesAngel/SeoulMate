"use client";

export function CommunitySkeleton({ count = 4 }: { count?: number }) {
  return (
    <div className="community-feed-skeleton-list" aria-busy="true" aria-label="Loading community posts">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="community-card-skeleton-full">
          <div className="skeleton-line-author" />
          <div className="skeleton-line-title" />
          <div className="skeleton-line-body" />
          <div className="skeleton-line-body short" />
          <div className="skeleton-line-footer" />
        </div>
      ))}
    </div>
  );
}
