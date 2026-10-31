import type { Metadata } from "next";

export const SITE_NAME = "SeoulMate";

export const SITE_DESCRIPTION =
  "Thoughtful K-drama recommendations shaped by story, mood, and your taste.";

export const SITE_URL = new URL(
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
);

export const DEFAULT_OG_IMAGE = { url: "/og.png", width: 1200, height: 630 };

/**
 * Title, description, canonical and share tags for one page. Next.js replaces
 * (not merges) a parent's `openGraph`, so the default image is repeated here.
 */
export function pageMetadata({
  title,
  absoluteTitle = false,
  description,
  path,
}: {
  title: string;
  /** Skip the "— SeoulMate" suffix (for titles that already name the site). */
  absoluteTitle?: boolean;
  description: string;
  path: string;
}): Metadata {
  return {
    title: absoluteTitle ? { absolute: title } : title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "website",
      siteName: SITE_NAME,
      title,
      description,
      url: path,
      images: [DEFAULT_OG_IMAGE],
    },
    twitter: { card: "summary_large_image", title, description, images: [DEFAULT_OG_IMAGE.url] },
  };
}

// The canonical is cleared so these pages never inherit a parent's.
export const NO_INDEX: Metadata = {
  robots: { index: false, follow: true },
  alternates: { canonical: null },
};

export function absoluteUrl(path: string) {
  return new URL(path, SITE_URL).toString();
}

/** Trims long text to a meta-description length, breaking on a word. */
export function metaDescription(text: string | undefined, max = 155) {
  const clean = (text ?? "").replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  const cut = clean.slice(0, max - 1);
  return `${cut.slice(0, cut.lastIndexOf(" ") > 80 ? cut.lastIndexOf(" ") : cut.length)}…`;
}
