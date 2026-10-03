import { DramaDetail } from "@/components/drama-detail";

export default async function DramaPage({
  params,
  searchParams,
}: {
  params: Promise<{ slug: string }>;
  searchParams: Promise<{ aired?: string }>;
}) {
  const { slug } = await params;
  const { aired } = await searchParams;
  return <DramaDetail title={decodeURIComponent(slug)} aired={aired} />;
}
