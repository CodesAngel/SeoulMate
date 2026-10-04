import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";

export default function DiscoverLoading() {
  return (
    <div className="shell section" aria-busy="true">
      <DramaGridSkeleton count={8} />
    </div>
  );
}
