import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";

export default function Loading() {
  return (
    <div className="shell section" aria-busy="true">
      <DramaGridSkeleton count={5} />
    </div>
  );
}
