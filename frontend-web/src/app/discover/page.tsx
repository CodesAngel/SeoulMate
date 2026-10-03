import { Suspense } from "react";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { DiscoverClient } from "@/components/discover-client";

export default function DiscoverPage() {
  return (
    <Suspense fallback={<div className="shell section"><DramaGridSkeleton count={8} /></div>}>
      <DiscoverClient />
    </Suspense>
  );
}
