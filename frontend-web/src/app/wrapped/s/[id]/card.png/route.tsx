import { getWrappedShare } from "@/lib/api";
import { wrappedCardImage } from "@/lib/wrapped-card";

// Public share image for a saved snapshot (also the page's og:image).
export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const data = await getWrappedShare(id, { next: { revalidate: 3600 } }).catch(() => null);
  if (!data) return new Response("Not found", { status: 404 });
  return wrappedCardImage(data.stats, {
    headers: { "Cache-Control": "public, max-age=3600, s-maxage=3600" },
  });
}
