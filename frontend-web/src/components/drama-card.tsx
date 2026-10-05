"use client";

import Link from "next/link";
import {
  Bookmark,
  BookmarkCheck,
  CheckCircle2,
  Eye,
  Play,
  Sparkles,
  Star,
} from "lucide-react";
import { MouseEvent, useState } from "react";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { PosterImage } from "@/components/poster-image";
import { logInteraction } from "@/lib/api";
import type { Drama, WatchStatus } from "@/lib/types";

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
  const { user } = useAuth();
  const { userId, sessionId, isSaved, toggleSaved, getWatchStatus, setWatchStatus } =
    useApp();
  const [hovered, setHovered] = useState(false);

  const saved = isSaved(drama);
  const status = getWatchStatus(drama);

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

  function handleQuickStatus(
    e: MouseEvent<HTMLButtonElement>,
    targetStatus: WatchStatus,
  ) {
    e.preventDefault();
    e.stopPropagation();

    if (!user) {
      toggleSaved(drama);
      return;
    }

    if (saved && status === targetStatus) {
      toggleSaved(drama);
    } else {
      setWatchStatus(drama, targetStatus);
    }
  }

  const isHighlyRated =
    drama.rating_value && Number(drama.rating_value) >= 8.6;

  return (
    <article
      className="drama-card group"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      <div className="poster-frame">
        <Link href={href} className="poster-link-wrap" onClick={logClick}>
          <PosterImage
            src={drama.poster_thumbnail_url ?? drama.Image}
            alt={`${drama.Title} poster`}
            priority={priority}
          />
          <span className="genre-pill">{firstGenre(drama.Genre)}</span>
          <span className="card-gradient" />
        </Link>

        {/* High Rating / AI Match Badge */}
        {isHighlyRated && (
          <span className="card-ai-badge" title="High Community & AI Match Score">
            <Sparkles size={11} /> Top Pick
          </span>
        )}

        {/* Floating Save Button */}
        <button
          type="button"
          className={`save-button ${saved ? "saved" : ""}`}
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            toggleSaved(drama);
          }}
          aria-label={
            saved
              ? `Remove ${drama.Title} from my list`
              : `Add ${drama.Title} to my list`
          }
        >
          {saved ? <BookmarkCheck size={18} /> : <Bookmark size={18} />}
        </button>

        {/* Quick-Action Status Bar on Hover */}
        <div
          className={`card-quick-actions ${hovered ? "active" : ""}`}
          aria-hidden={!hovered}
        >
          <button
            type="button"
            className={`quick-status-btn ${status === "watching" ? "active" : ""}`}
            onClick={(e) => handleQuickStatus(e, "watching")}
            title="Mark as Watching"
          >
            <Play size={13} fill="currentColor" />
            <span>Watching</span>
          </button>
          <button
            type="button"
            className={`quick-status-btn ${status === "planned" ? "active" : ""}`}
            onClick={(e) => handleQuickStatus(e, "planned")}
            title="Mark as Plan to Watch"
          >
            <Eye size={13} />
            <span>Plan</span>
          </button>
          <button
            type="button"
            className={`quick-status-btn ${status === "completed" ? "active" : ""}`}
            onClick={(e) => handleQuickStatus(e, "completed")}
            title="Mark as Completed"
          >
            <CheckCircle2 size={13} />
            <span>Done</span>
          </button>
        </div>
      </div>

      <div className="card-copy">
        <Link href={href} onClick={logClick} className="card-title-link">
          <h3 title={drama.Title}>{drama.Title}</h3>
        </Link>
        <div className="card-meta">
          <span className="rating">
            <Star size={13} fill="currentColor" /> {drama.rating_value || "New"}
          </span>
          <span className="card-sub-info">
            {drama.episodes ? `${drama.episodes} eps` : drama.Network || "Series"}
          </span>
        </div>
      </div>
    </article>
  );
}
