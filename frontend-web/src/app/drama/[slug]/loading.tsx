import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";

export default function DramaLoading() {
  return (
    <div className="shell detail-shell" aria-busy="true">
      <DramaGridSkeleton count={4} />
    </div>
  );
}
