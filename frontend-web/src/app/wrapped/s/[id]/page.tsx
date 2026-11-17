import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { WrappedShareCard } from "@/components/wrapped-share-card";
import { getWrappedShare } from "@/lib/api";
import { NO_INDEX } from "@/lib/site";
import { wrappedTitle } from "@/lib/wrapped";

type Props = { params: Promise<{ id: string }> };

async function load(id: string) {
  const data = await getWrappedShare(id, { next: { revalidate: 3600 } }).catch(() => null);
  if (!data) notFound();
  return data;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { id } = await params;
  const { stats } = await load(id);
  const title = wrappedTitle(stats);
  const totals = stats.totals;
  const description = totals
    ? `${totals.dramas} dramas, ${totals.hours} hours${stats.fan_type ? `, ${stats.fan_type.name}` : ""}. SeoulMate Wrapped ${stats.year}.`
    : `SeoulMate Wrapped ${stats.year}.`;
  const image = { url: `/wrapped/s/${id}/card.png`, width: 1080, height: 1350, alt: title };
  return {
    title,
    description,
    ...NO_INDEX,
    openGraph: { type: "website", title, description, url: `/wrapped/s/${id}`, images: [image] },
    twitter: { card: "summary_large_image", title, description, images: [image.url] },
  };
}

export default async function WrappedSharePage({ params }: Props) {
  const { id } = await params;
  const { stats } = await load(id);

  return (
    <section className="wr-public shell">
      <div className="wr-public-card">
        <WrappedShareCard stats={stats} />
      </div>
      <div className="wr-public-copy">
        <span className="eyebrow eyebrow-accent">SeoulMate Wrapped {stats.year}</span>
        <h1 className="display">{wrappedTitle(stats)}</h1>
        {stats.fan_type && (
          <p>
            <strong>{stats.fan_type.name}.</strong> {stats.fan_type.description}
          </p>
        )}
        <p className="muted">
          Counted from the dramas finished and rated on SeoulMate, a K-drama recommender
          you can search by mood, actor or story.
        </p>
        <div className="wr-public-actions">
          <Link className="primary-button" href="/wrapped">
            Make your own Wrapped <ArrowRight size={16} />
          </Link>
          <Link className="secondary-button" href="/discover">
            Find your next drama
          </Link>
        </div>
      </div>
    </section>
  );
}
