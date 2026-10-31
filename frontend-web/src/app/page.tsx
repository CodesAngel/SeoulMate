import type { Metadata } from "next";
import { HOME_PICKS_QUERY, HomePage } from "@/components/home-page";
import { JsonLd } from "@/components/json-ld";
import { getHomeCommunityServer, getHomePicksServer } from "@/lib/catalog-server";
import { absoluteUrl, pageMetadata, SITE_DESCRIPTION, SITE_NAME } from "@/lib/site";

export const metadata: Metadata = pageMetadata({
  title: "SeoulMate — Find your next K-drama",
  absoluteTitle: true,
  description: SITE_DESCRIPTION,
  path: "/",
});

// Lets Google show a search box for the site in its results.
const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: SITE_NAME,
  url: absoluteUrl("/"),
  description: SITE_DESCRIPTION,
  potentialAction: {
    "@type": "SearchAction",
    target: { "@type": "EntryPoint", urlTemplate: absoluteUrl("/discover?q={search_term_string}") },
    "query-input": "required name=search_term_string",
  },
};

export default async function Page() {
  const [initialPicks, community] = await Promise.all([
    getHomePicksServer(HOME_PICKS_QUERY),
    getHomeCommunityServer(),
  ]);
  return (
    <>
      <JsonLd data={websiteJsonLd} />
      <HomePage
        initialPicks={initialPicks}
        initialTrending={community.trending}
        initialRecent={community.recent}
      />
    </>
  );
}
