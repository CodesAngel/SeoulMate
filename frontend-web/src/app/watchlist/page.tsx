"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Bookmark,
  BookmarkX,
  CheckCircle2,
  Clock,
  Columns,
  Eye,
  LayoutGrid,
  PauseCircle,
  Play,
  Star,
  Trash2,
} from "lucide-react";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { DramaCard } from "@/components/drama-card";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { EpisodeTracker } from "@/components/episode-tracker";
import { PosterImage } from "@/components/poster-image";
import { dramaKey } from "@/lib/drama";
import type { WatchStatus, WatchlistEntry } from "@/lib/types";

const STATUS_CONFIG: Record<
  WatchStatus,
  { label: string; icon: typeof Eye; color: string }
> = {
  planned: { label: "Plan to watch", icon: Bookmark, color: "var(--lemon)" },
  watching: { label: "Watching", icon: Play, color: "var(--coral)" },
  completed: { label: "Completed", icon: CheckCircle2, color: "#48bb78" },
  paused: { label: "On hold", icon: PauseCircle, color: "#ecc94b" },
  dropped: { label: "Dropped", icon: Clock, color: "#a0aec0" },
};

const STATUS_LIST: WatchStatus[] = ["planned", "watching", "completed", "paused", "dropped"];

export default function WatchlistPage() {
  const { user } = useAuth();
  const {
    ready,
    libraryError,
    watchlistEntries,
    getRating,
    setWatchStatus,
    toggleSaved,
  } = useApp();

  const [viewMode, setViewMode] = useState<"grid" | "kanban">("kanban");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const entriesByStatus: Record<WatchStatus, WatchlistEntry[]> = {
    planned: [],
    watching: [],
    completed: [],
    paused: [],
    dropped: [],
  };

  for (const entry of watchlistEntries) {
    if (entriesByStatus[entry.status]) {
      entriesByStatus[entry.status].push(entry);
    } else {
      entriesByStatus.planned.push(entry);
    }
  }

  const filteredEntries =
    filterStatus === "all"
      ? watchlistEntries
      : watchlistEntries.filter((entry) => entry.status === filterStatus);

  return (
    <>
      <section className="page-hero">
        <div className="shell">
          <div className="watchlist-hero-flex">
            <div>
              <span className="eyebrow">Personal Library</span>
              <h1 className="display">My Drama Collection</h1>
              <p>
                {user
                  ? "Track what you're watching, plan upcoming shows, and log ratings synchronized to your account."
                  : "Your guest list is stored in this browser. Sign in to sync across devices and record personal stats."}
              </p>
              {!user && (
                <Link className="text-link" href="/auth/login">
                  Sign in to sync your library
                </Link>
              )}
            </div>

            {/* View Mode Toggle */}
            <div className="watchlist-view-controls">
              <div className="view-toggle-group">
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === "kanban" ? "active" : ""}`}
                  onClick={() => setViewMode("kanban")}
                  title="Kanban Board View"
                >
                  <Columns size={16} />
                  <span>Board View</span>
                </button>
                <button
                  type="button"
                  className={`view-toggle-btn ${viewMode === "grid" ? "active" : ""}`}
                  onClick={() => setViewMode("grid")}
                  title="Grid Poster View"
                >
                  <LayoutGrid size={16} />
                  <span>Grid View</span>
                </button>
              </div>
            </div>
          </div>

          {/* Quick Filter Badges for Grid View */}
          {viewMode === "grid" && watchlistEntries.length > 0 && (
            <div className="watchlist-filter-bar">
              <button
                type="button"
                className={`filter-pill ${filterStatus === "all" ? "active" : ""}`}
                onClick={() => setFilterStatus("all")}
              >
                All ({watchlistEntries.length})
              </button>
              {STATUS_LIST.map((st) => (
                <button
                  key={st}
                  type="button"
                  className={`filter-pill ${filterStatus === st ? "active" : ""}`}
                  onClick={() => setFilterStatus(st)}
                >
                  {STATUS_CONFIG[st].label} ({entriesByStatus[st].length})
                </button>
              ))}
            </div>
          )}
        </div>
      </section>

      <section className="shell watchlist-main-section">
        {libraryError && (
          <div className="error-banner" role="alert">
            {libraryError}
          </div>
        )}

        {!ready ? (
          <DramaGridSkeleton count={5} />
        ) : watchlistEntries.length === 0 ? (
          <div className="empty-state">
            <BookmarkX size={44} />
            <h2>Your watchlist is waiting</h2>
            <p>
              Discover captivating stories, heartwarming rom-coms, or dark thrillers and
              save them with one click.
            </p>
            <Link
              href="/discover"
              className="primary-button"
              style={{ display: "inline-block", marginTop: 20 }}
            >
              Explore Korean Dramas
            </Link>
          </div>
        ) : viewMode === "kanban" ? (
          /* Kanban Board View */
          <div className="kanban-board">
            {(
              [
                { id: "watching", label: "Currently Watching", icon: Play },
                { id: "planned", label: "Plan to Watch", icon: Bookmark },
                { id: "completed", label: "Completed", icon: CheckCircle2 },
                { id: "paused", label: "On Hold & Dropped", icon: PauseCircle },
              ] as const
            ).map((col) => {
              const colEntries =
                col.id === "paused"
                  ? [...entriesByStatus.paused, ...entriesByStatus.dropped]
                  : entriesByStatus[col.id];

              return (
                <div className={`kanban-column kanban-${col.id}`} key={col.id}>
                  <div className="kanban-column-header">
                    <div className="kanban-header-title">
                      <col.icon size={16} />
                      <h3>{col.label}</h3>
                    </div>
                    <span className="kanban-count">{colEntries.length}</span>
                  </div>

                  <div className="kanban-card-list">
                    {colEntries.length === 0 ? (
                      <div className="kanban-empty-drop">
                        <span>No dramas here yet</span>
                      </div>
                    ) : (
                      colEntries.map((entry) => (
                        <KanbanCard
                          key={dramaKey(entry.drama)}
                          entry={entry}
                          userLoggedIn={Boolean(user)}
                          onStatusChange={(newStatus) =>
                            setWatchStatus(entry.drama, newStatus)
                          }
                          onRemove={() => toggleSaved(entry.drama)}
                          rating={getRating(entry.drama)}
                        />
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Grid View */
          <div className="drama-grid">
            {filteredEntries.map((entry) => (
              <div className="watchlist-card-wrap" key={dramaKey(entry.drama)}>
                <DramaCard drama={entry.drama} />
                <div className="watchlist-controls">
                  {user && (
                    <label>
                      <span>Viewing status</span>
                      <select
                        value={entry.status}
                        onChange={(e) =>
                          setWatchStatus(entry.drama, e.target.value as WatchStatus)
                        }
                      >
                        {STATUS_LIST.map((st) => (
                          <option value={st} key={st}>
                            {STATUS_CONFIG[st].label}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}

                  {getRating(entry.drama) !== undefined && (
                    <span className="personal-rating">
                      Your rating: <strong>{getRating(entry.drama)}/10</strong>
                    </span>
                  )}

                  {entry.status === "watching" && (
                    <EpisodeTracker
                      drama={entry.drama}
                      onComplete={() => setWatchStatus(entry.drama, "completed")}
                    />
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}

function KanbanCard({
  entry,
  userLoggedIn,
  onStatusChange,
  onRemove,
  rating,
}: {
  entry: WatchlistEntry;
  userLoggedIn: boolean;
  onStatusChange: (status: WatchStatus) => void;
  onRemove: () => void;
  rating?: number;
}) {
  const { drama, status } = entry;
  const href = `/drama/${encodeURIComponent(drama.Title)}${
    drama["Release Years"]
      ? `?aired=${encodeURIComponent(drama["Release Years"] || "")}`
      : ""
  }`;

  return (
    <article className="kanban-card">
      <div className="kanban-card-inner">
        <Link
          href={href}
          className="kanban-thumbnail"
          style={{
            position: "relative",
            display: "block",
            width: 58,
            height: 87,
            flexShrink: 0,
            overflow: "hidden",
          }}
        >
          <PosterImage
            src={drama.poster_thumbnail_url ?? drama.Image}
            alt={drama.Title}
          />
        </Link>
        <div className="kanban-info">
          <Link href={href}>
            <h4 title={drama.Title}>{drama.Title}</h4>
          </Link>
          <div className="kanban-meta-row">
            <span className="kanban-meta-item">
              <Star size={12} fill="currentColor" /> {drama.rating_value || "—"}
            </span>
            {drama.episodes && (
              <span className="kanban-meta-item">{drama.episodes} eps</span>
            )}
          </div>
          {rating !== undefined && (
            <div className="kanban-user-rating">
              <span>My Score: </span>
              <strong>{rating}/10</strong>
            </div>
          )}
        </div>
      </div>

      {/* Episode Progress for Watching dramas */}
      {status === "watching" && (
        <div className="kanban-tracker-wrap">
          <EpisodeTracker
            drama={drama}
            onComplete={() => onStatusChange("completed")}
          />
        </div>
      )}

      {/* Status Mover Footer */}
      <div className="kanban-card-footer">
        {userLoggedIn ? (
          <select
            className="kanban-status-select"
            value={status}
            onChange={(e) => onStatusChange(e.target.value as WatchStatus)}
          >
            {STATUS_LIST.map((st) => (
              <option value={st} key={st}>
                Move: {STATUS_CONFIG[st].label}
              </option>
            ))}
          </select>
        ) : (
          <span className="muted" style={{ fontSize: "0.72rem" }}>
            Guest mode
          </span>
        )}
        <button
          type="button"
          className="kanban-remove-btn"
          onClick={onRemove}
          title="Remove from watchlist"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </article>
  );
}
