import type { Metadata } from "next";
import { pageMetadata, SITE_NAME } from "@/lib/site";

const title = "K-drama community: reviews, theories and recommendations";

export const metadata: Metadata = {
  ...pageMetadata({
    title,
    description:
      "Spoiler-safe K-drama discussions: reviews, fan theories, recommendations and watch-along posts from the SeoulMate community.",
    path: "/community",
  }),
  // A plain string title here would drop the root "%s — SeoulMate" template
  // for every page under /community, so restate it.
  title: { absolute: `${title} — ${SITE_NAME}`, template: `%s — ${SITE_NAME}` },
};

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
