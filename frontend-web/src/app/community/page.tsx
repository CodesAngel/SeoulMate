import { CommunityClient } from "@/components/community-client";
import { getCommunityPosts } from "@/lib/api";

type Props = { searchParams: Promise<Record<string, string | string[] | undefined>> };

// Reading searchParams renders this route per request, so the header and
// (for the default view) the first page of posts are in the server HTML.
export default async function CommunityPage({ searchParams }: Props) {
  const params = await searchParams;
  const isDefault = !params.q && !params.tab && !params.drama_id;
  const initialPosts = isDefault
    ? await getCommunityPosts({ page: 1, limit: 10, sort: "trending" }, null, undefined, {
        next: { revalidate: 600 },
      }).catch(() => undefined)
    : undefined;

  return <CommunityClient initialPosts={initialPosts} />;
}
