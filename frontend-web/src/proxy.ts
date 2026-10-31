import { NextResponse, type NextRequest } from "next/server";
import { updateSession } from "@/lib/supabase/proxy";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import { dramaPath } from "@/lib/drama";

// Old drama links used the raw title (/drama/Crash%20Landing%20on%20You?aired=...).
// Send them permanently to the slug URL (/drama/crash-landing-on-you-2019).
function legacyDramaRedirect(request: NextRequest) {
  const { pathname, searchParams } = request.nextUrl;
  if (!pathname.startsWith("/drama/")) return null;
  let title: string;
  try {
    title = decodeURIComponent(pathname.slice("/drama/".length));
  } catch {
    return null;
  }
  const aired = searchParams.get("aired");
  if (/^[a-z0-9-]+$/.test(title) && !aired) return null;
  const url = request.nextUrl.clone();
  url.pathname = dramaPath(title, aired);
  url.search = "";
  return NextResponse.redirect(url, 308);
}

export async function proxy(request: NextRequest) {
  const redirect = legacyDramaRedirect(request);
  if (redirect) return redirect;
  if (IS_MOCK_MODE) return NextResponse.next();
  return updateSession(request);
}

export const config = {
  matcher: [
    "/((?!_next/static|_next/image|favicon.ico|.*\\.(?:svg|png|jpg|jpeg|gif|webp)$).*)",
  ],
};
