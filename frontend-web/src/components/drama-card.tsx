"use client";

import Link from "next/link";
import { Bookmark, BookmarkCheck, Star } from "lucide-react";
import { useApp } from "@/components/app-provider";
import { PosterImage } from "@/components/poster-image";
import { logInteraction } from "@/lib/api";
import type { Drama } from "@/lib/types";

function firstGenre(value?: string) {
  return value?.split(",")[0]?.trim() || "K-drama";
}

export function DramaCard({
  drama,
  position,
  searchId,
  priority = false,
}: {
  drama: Drama;
  position?: number;
  searchId?: string;
  priority?: boolean;
}) {
  const { userId, sessionId, isSaved, toggleSaved } = useApp();
  const saved = isSaved(drama);
  const href = `/drama/${encodeURIComponent(drama.Title)}${
    drama["Release Years"]
      ? `?aired=${encodeURIComponent(drama["Release Years"] || "")}`
      : ""
  }`;

  function logClick() {
    if (!userId || !sessionId) return;
    void logInteraction({
      userId,
      sessionId,
      dramaTitle: drama.Title,
      type: "click",
      position,
      searchId,
    }).catch(() => undefined);
  }

  return (
    <article className="drama-card">
      <Link href={href} className="poster-frame" onClick={logClick}>
        <PosterImage src={drama.Image} alt={`${drama.Title} poster`} priority={priority} />
        <span className="genre-pill">{firstGenre(drama.Genre)}</span>
        <span className="card-gradient" />
      </Link>
      <button
        className={`save-button ${saved ? "saved" : ""}`}
        onClick={() => toggleSaved(drama)}
        aria-label={saved ? `Remove ${drama.Title} from my list` : `Add ${drama.Title} to my list`}
      >
        {saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
      </button>
      <div className="card-copy">
        <Link href={href} onClick={logClick}>
          <h3>{drama.Title}</h3>
        </Link>
        <div className="card-meta">
          <span className="rating"><Star size={14} fill="currentColor" /> {drama.rating_value || "New"}</span>
          <span>{drama.episodes ? `${drama.episodes} eps` : drama.Network || "Series"}</span>
        </div>
      </div>
    </article>
  );
}
