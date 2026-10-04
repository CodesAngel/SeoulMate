"use client";

import { BookmarkX } from "lucide-react";
import Link from "next/link";
import { useApp } from "@/components/app-provider";
import { DramaCard } from "@/components/drama-card";
import { DramaGridSkeleton } from "@/components/drama-grid-skeleton";
import { dramaKey } from "@/lib/drama";
import { useAuth } from "@/components/auth-provider";
import type { WatchStatus } from "@/lib/types";

const STATUS_OPTIONS: Array<{ value: WatchStatus; label: string }> = [
  { value: "planned", label: "Plan to watch" },
  { value: "watching", label: "Watching" },
  { value: "completed", label: "Completed" },
  { value: "paused", label: "On hold" },
  { value: "dropped", label: "Dropped" },
];

export default function WatchlistPage() {
  const { user } = useAuth();
  const { ready, libraryError, watchlistEntries, getRating, setWatchStatus } = useApp();
  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Saved for later</span><h1 className="display">My drama list</h1><p>{user ? "Your saved dramas, viewing progress, and ratings follow your SeoulMate account." : "Your guest list is saved in this browser. Sign in to sync it with your account."}</p>{!user && <Link className="text-link" href="/auth/login">Sign in to sync your list</Link>}</div></section>
      <section className="shell watchlist-grid">
        {libraryError && <div className="error-banner" role="alert">{libraryError}</div>}
        {!ready ? <DramaGridSkeleton count={5} /> : watchlistEntries.length ? <div className="drama-grid">{watchlistEntries.map((entry) => <div className="watchlist-card-wrap" key={dramaKey(entry.drama)}><DramaCard drama={entry.drama} />{user && <div className="watchlist-controls"><label><span>Viewing status</span><select value={entry.status} onChange={(event) => setWatchStatus(entry.drama, event.target.value as WatchStatus)}>{STATUS_OPTIONS.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select></label>{getRating(entry.drama) !== undefined && <span className="personal-rating">Your rating: <strong>{getRating(entry.drama)}/10</strong></span>}</div>}</div>)}</div> : (
          <div className="empty-state"><BookmarkX size={38} /><h2>Your list is waiting</h2><p>Save a drama from any recommendation card and it will appear here.</p><Link href="/discover" className="primary-button" style={{ display: "inline-block", marginTop: 18 }}>Discover dramas</Link></div>
        )}
      </section>
    </>
  );
}
