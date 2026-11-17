import { API_URL } from "@/lib/api";
import { isWrappedYear, type MyWrappedResponse } from "@/lib/wrapped";
import { wrappedCardImage } from "@/lib/wrapped-card";

// The signed-in fan's own share image ("Save image"). The browser sends its
// access token; the numbers come straight from the API, so nobody can render
// a card with made-up text.
export async function GET(
  request: Request,
  { params }: { params: Promise<{ year: string }> },
) {
  const year = Number((await params).year);
  if (!isWrappedYear(year)) return new Response("Not found", { status: 404 });

  const authorization = request.headers.get("authorization");
  if (!authorization?.startsWith("Bearer ")) {
    return new Response("Sign in first", { status: 401 });
  }

  const response = await fetch(`${API_URL}/me/wrapped?year=${year}`, {
    headers: { Authorization: authorization },
    cache: "no-store",
  });
  if (!response.ok) return new Response("Could not load Wrapped", { status: response.status });
  const stats = (await response.json()) as MyWrappedResponse;
  if (!stats.unlocked) return new Response("Wrapped is still locked", { status: 400 });

  return wrappedCardImage(stats, { headers: { "Cache-Control": "private, no-store" } });
}
