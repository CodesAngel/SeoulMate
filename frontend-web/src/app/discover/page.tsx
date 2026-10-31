import { Suspense } from "react";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { DEFAULT_DISCOVER_QUERY, DiscoverClient } from "@/components/discover-client";
import { getDiscoverDefaultServer } from "@/lib/catalog-server";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

// Reading searchParams renders this route per request, so the heading, form
// and (for the plain /discover page) the results are in the server HTML.
export default async function DiscoverPage({ searchParams }: Props) {
  const params = await searchParams;
  const isDefault = !Object.keys(params).length;
  const initialResults = isDefault ? await getDiscoverDefaultServer(DEFAULT_DISCOVER_QUERY) : [];

  return (
    <Suspense fallback={<div className="shell section"><DramaGridSkeleton count={8} /></div>}>
      <DiscoverClient initialResults={initialResults} />
    </Suspense>
  );
}
