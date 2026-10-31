import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { DramaDetail } from "@/components/drama-detail";
import { JsonLd } from "@/components/json-ld";
import { getDramaServer, getSimilarServer, resolveDramaSlug } from "@/lib/catalog-server";
import { dramaPath, firstYear } from "@/lib/drama";
import { absoluteUrl, DEFAULT_OG_IMAGE, metaDescription } from "@/lib/site";
import type { Drama } from "@/lib/types";

type Props = { params: Promise<{ slug: string }> };

function list(value?: string) {
  return (value || "").split(",").map((item) => item.trim()).filter(Boolean);
}

async function load(slug: string) {
  const entry = await resolveDramaSlug(slug).catch(() => undefined);
  if (!entry) notFound();
  const drama = await getDramaServer(entry.title, entry.aired);
  return { entry, drama, path: dramaPath(entry.title, entry.aired) };
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { slug } = await params;
  const { entry, drama, path } = await load(slug);
  const year = firstYear(entry.aired);
  const title = year ? `${entry.title} (${year})` : entry.title;
  const description =
    metaDescription(drama?.Description) ||
    `${entry.title}: cast, story themes and similar K-dramas on SeoulMate.`;
  const image = drama?.poster_thumbnail_url ?? drama?.poster_original_url;

  return {
    title,
    description,
    alternates: { canonical: path },
    openGraph: {
      type: "video.tv_show",
      title,
      description,
      url: path,
      images: [image ? { url: image, alt: `${entry.title} poster` } : DEFAULT_OG_IMAGE],
    },
    twitter: { card: "summary_large_image", title, description, images: [image ?? DEFAULT_OG_IMAGE.url] },
  };
}

function tvSeriesJsonLd(drama: Drama, url: string) {
  const year = firstYear(drama["Release Years"]);
  return {
    "@context": "https://schema.org",
    "@type": "TVSeries",
    name: drama.Title,
    url,
    ...(drama["Also Known As"] ? { alternateName: list(drama["Also Known As"]) } : {}),
    ...(drama.Description ? { description: drama.Description } : {}),
    ...(year ? { datePublished: year } : {}),
    ...(drama.Genre ? { genre: list(drama.Genre) } : {}),
    ...(drama.Cast
      ? { actor: list(drama.Cast).slice(0, 10).map((name) => ({ "@type": "Person", name })) }
      : {}),
    ...(drama.Director
      ? { director: list(drama.Director).map((name) => ({ "@type": "Person", name })) }
      : {}),
    ...(drama.episodes ? { numberOfEpisodes: Number(drama.episodes) || undefined } : {}),
    ...(drama.Network
      ? { productionCompany: { "@type": "Organization", name: drama.Network } }
      : {}),
    ...(drama.poster_original_url ? { image: drama.poster_original_url } : {}),
    countryOfOrigin: { "@type": "Country", name: "South Korea" },
    inLanguage: "ko",
  };
}

function breadcrumbJsonLd(title: string, url: string) {
  return {
    "@context": "https://schema.org",
    "@type": "BreadcrumbList",
    itemListElement: [
      { "@type": "ListItem", position: 1, name: "Home", item: absoluteUrl("/") },
      { "@type": "ListItem", position: 2, name: "Discover", item: absoluteUrl("/discover") },
      { "@type": "ListItem", position: 3, name: title, item: url },
    ],
  };
}

export default async function DramaPage({ params }: Props) {
  const { slug } = await params;
  const { entry, drama, path } = await load(slug);
  const similar = drama ? await getSimilarServer(entry.title) : [];
  const url = absoluteUrl(path);

  return (
    <>
      {drama && <JsonLd data={[tvSeriesJsonLd(drama, url), breadcrumbJsonLd(drama.Title, url)]} />}
      <DramaDetail
        title={entry.title}
        aired={drama?.["Release Years"] ?? entry.aired ?? undefined}
        initialDrama={drama ?? undefined}
        initialSimilar={similar}
      />
    </>
  );
}
