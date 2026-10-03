"use client";

import { BookmarkX } from "lucide-react";
import Link from "next/link";
import { useApp } from "@/components/app-provider";
import { DramaCard } from "@/components/drama-card";

export default function WatchlistPage() {
  const { ready, watchlist } = useApp();
  return (
    <>
      <section className="page-hero"><div className="shell"><span className="eyebrow">Saved for later</span><h1 className="display">My drama list</h1><p>A quiet corner for every story that caught your attention. Your list is saved in this browser.</p></div></section>
      <section className="shell watchlist-grid">
        {ready && watchlist.length ? <div className="drama-grid">{watchlist.map((drama, index) => <DramaCard key={`${drama.Title}-${index}`} drama={drama} />)}</div> : (
          <div className="empty-state"><BookmarkX size={38} /><h2>Your list is waiting</h2><p>Save a drama from any recommendation card and it will appear here.</p><Link href="/discover" className="primary-button" style={{ display: "inline-block", marginTop: 18 }}>Discover dramas</Link></div>
        )}
      </section>
    </>
  );
}
