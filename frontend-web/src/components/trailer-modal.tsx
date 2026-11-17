"use client";

import { useEffect, useRef } from "react";
import { ExternalLink, Search, X } from "lucide-react";

interface TrailerModalProps {
  isOpen: boolean;
  onClose: () => void;
  dramaTitle: string;
  // YouTube id of the official trailer (from TMDB). Without it we can only
  // offer a YouTube search: YouTube no longer supports embedded searches.
  youtubeKey?: string;
}

export function TrailerModal({ isOpen, onClose, dramaTitle, youtubeKey }: TrailerModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (isOpen) {
      document.body.style.overflow = "hidden";
      window.addEventListener("keydown", handleKeyDown);
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const searchQuery = encodeURIComponent(`${dramaTitle} Korean drama official trailer`);
  const searchUrl = `https://www.youtube.com/results?search_query=${searchQuery}`;
  const embedUrl = youtubeKey
    ? `https://www.youtube-nocookie.com/embed/${encodeURIComponent(youtubeKey)}?autoplay=1&rel=0`
    : null;
  const externalUrl = `https://www.youtube.com/watch?v=${encodeURIComponent(youtubeKey ?? "")}`;

  return (
    <div
      className="trailer-modal-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      role="dialog"
      aria-modal="true"
      aria-label={`${dramaTitle} trailer`}
    >
      <div className="trailer-modal-container" ref={modalRef}>
        <div className="trailer-modal-header">
          <div>
            <span className="eyebrow" style={{ color: "var(--lemon)" }}>
              {youtubeKey ? "Official Preview" : "Trailer"}
            </span>
            <h3>{dramaTitle}</h3>
          </div>
          <div className="trailer-modal-actions">
            {youtubeKey && (
              <a
                href={externalUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="trailer-external-link"
                title="Open in YouTube"
              >
                <ExternalLink size={16} />
                <span>YouTube</span>
              </a>
            )}
            <button
              type="button"
              className="trailer-close-btn"
              onClick={onClose}
              aria-label="Close trailer modal"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        <div className="trailer-video-frame">
          {embedUrl ? (
            <iframe
              src={embedUrl}
              title={`${dramaTitle} official trailer`}
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowFullScreen
            />
          ) : (
            <div className="trailer-missing">
              <p>We don&apos;t have the official trailer for this drama yet.</p>
              <a href={searchUrl} target="_blank" rel="noopener noreferrer" className="trailer-search-link">
                <Search size={16} />
                <span>Search for it on YouTube</span>
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
