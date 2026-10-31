import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";

export default function Loading() {
  return (
    <div className="shell section route-loading" aria-busy="true">
      <DramaGridSkeleton count={5} />
    </div>
  );
}
