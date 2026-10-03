export function DramaGridSkeleton({ count = 6 }: { count?: number }) {
  return (
    <div className="drama-grid" aria-label="Loading dramas">
      {Array.from({ length: count }).map((_, index) => (
        <div className="skeleton-card" key={index}>
          <div className="skeleton poster-skeleton" />
          <div className="skeleton line-skeleton" />
          <div className="skeleton short-skeleton" />
        </div>
      ))}
    </div>
  );
}
