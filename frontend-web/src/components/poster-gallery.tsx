"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, X } from "lucide-react";
import type { TmdbGallery } from "@/lib/tmdb";

const IMG = "https://image.tmdb.org/t/p";
const LANG: Record<string, string> = { ko: "Korean", en: "English" };

// Extra posters from TMDB, loaded straight from TMDB's image servers.
// unoptimized: Vercel never fetches or stores a copy.
export function PosterGallery({ gallery, title }: { gallery: TmdbGallery; title: string }) {
  const { posters, tmdbId } = gallery;
  const [open, setOpen] = useState<number | null>(null);

  const close = useCallback(() => setOpen(null), []);
  const step = useCallback(
    (delta: number) =>
      setOpen((i) => (i === null ? i : (i + delta + posters.length) % posters.length)),
    [posters.length],
  );

  useEffect(() => {
    if (open === null) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") close();
      if (e.key === "ArrowRight") step(1);
      if (e.key === "ArrowLeft") step(-1);
    }
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", onKey);
    };
  }, [open, close, step]);

  const current = open === null ? null : posters[open];

  return (
    <section className="poster-gallery shell" aria-labelledby="poster-gallery-title">
      <div className="poster-gallery-head">
        <h2 id="poster-gallery-title" className="display">Posters</h2>
        <a
          className="tmdb-credit"
          href={`https://www.themoviedb.org/tv/${tmdbId}/images/posters`}
          target="_blank"
          rel="noopener noreferrer"
        >
          <span>Posters from</span>
          {/* Official TMDB logo, unmodified (TMDB attribution rules). */}
          <Image src="/tmdb-logo.svg" alt="TMDB" width={78} height={10} unoptimized />
        </a>
      </div>

      <div className="poster-gallery-row">
        {posters.map((poster, index) => (
          <button
            key={poster.path}
            type="button"
            className="poster-gallery-item"
            onClick={() => setOpen(index)}
            aria-label={`Open poster ${index + 1} of ${posters.length}`}
          >
            <Image
              src={`${IMG}/w342${poster.path}`}
              alt={`${title} poster ${index + 1}`}
              width={342}
              height={513}
              loading="lazy"
              unoptimized
            />
            {poster.lang && LANG[poster.lang] && (
              <span className="poster-gallery-lang">{LANG[poster.lang]}</span>
            )}
          </button>
        ))}
      </div>

      {current && open !== null && (
        <div
          className="poster-viewer"
          role="dialog"
          aria-modal="true"
          aria-label={`${title} poster ${open + 1} of ${posters.length}`}
          onClick={close}
        >
          <button type="button" className="poster-viewer-close" onClick={close} aria-label="Close">
            <X size={22} />
          </button>
          <button
            type="button"
            className="poster-viewer-nav prev"
            onClick={(e) => {
              e.stopPropagation();
              step(-1);
            }}
            aria-label="Previous poster"
          >
            <ChevronLeft size={26} />
          </button>
          <figure onClick={(e) => e.stopPropagation()}>
            <Image
              key={current.path}
              src={`${IMG}/w780${current.path}`}
              alt={`${title} poster ${open + 1}`}
              width={780}
              height={1170}
              unoptimized
            />
            <figcaption>
              {open + 1} / {posters.length}
            </figcaption>
          </figure>
          <button
            type="button"
            className="poster-viewer-nav next"
            onClick={(e) => {
              e.stopPropagation();
              step(1);
            }}
            aria-label="Next poster"
          >
            <ChevronRight size={26} />
          </button>
        </div>
      )}
    </section>
  );
}
