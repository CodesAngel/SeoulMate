"use client";

import Link from "next/link";
import { ArrowRight, Bookmark, BookmarkCheck, Star } from "lucide-react";
import { useApp } from "@/components/app-provider";
import { PosterImage } from "@/components/poster-image";
import { dramaHref, firstYear } from "@/lib/drama";
import type { RecommendationResponse } from "@/lib/types";

type MatchedDrama = NonNullable<RecommendationResponse["matched_drama"]>;

/** The drama a title search resolved to (issue #3), shown above "Dramas like X". */
export function TopMatchCard({ drama }: { drama: MatchedDrama }) {
  const { isSaved, toggleSaved } = useApp();
  const saved = isSaved(drama);
  const href = dramaHref(drama);
  const year = firstYear(drama["Release Years"]);
  const genres = (drama.Genre ?? "")
    .split(",")
    .map((genre) => genre.trim())
    .filter(Boolean)
    .slice(0, 4);
  const label = drama.match_type === "loose" ? "Closest title" : "Top match";

  return (
    <article className="top-match" aria-labelledby="top-match-title">
      <Link href={href} className="top-match-poster poster-frame" tabIndex={-1} aria-hidden="true">
        <PosterImage
          src={drama.poster_thumbnail_url ?? drama.Image}
          alt={`${drama.Title} poster`}
          sizes="(max-width: 640px) 34vw, 170px"
          priority
        />
      </Link>
      <div className="top-match-copy">
        <span className="eyebrow">{label}</span>
        <h2 id="top-match-title">
          <Link href={href}>{drama.Title}</Link>
        </h2>
        <p className="top-match-meta">
          {drama.rating_value ? (
            <span className="rating">
              <Star size={13} fill="currentColor" /> {drama.rating_value}
            </span>
          ) : null}
          {year && <span>{year}</span>}
          {drama.episodes ? <span>{drama.episodes} episodes</span> : null}
          {drama.Network && <span>{drama.Network}</span>}
        </p>
        {genres.length > 0 && (
          <ul className="top-match-genres">
            {genres.map((genre) => (
              <li key={genre}>{genre}</li>
            ))}
          </ul>
        )}
        {drama.Description && <p className="top-match-synopsis">{drama.Description}</p>}
        <div className="top-match-actions">
          <Link href={href} className="primary-button">
            View details <ArrowRight size={16} />
          </Link>
          <button
            type="button"
            className={`secondary-button ${saved ? "saved" : ""}`}
            onClick={() => toggleSaved(drama)}
            aria-pressed={saved}
          >
            {saved ? <BookmarkCheck size={16} /> : <Bookmark size={16} />}
            {saved ? "Saved" : "Save"}
          </button>
        </div>
      </div>
    </article>
  );
}
