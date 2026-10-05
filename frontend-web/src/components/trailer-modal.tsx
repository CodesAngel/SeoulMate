"use client";

import { useEffect, useRef } from "react";
import { ExternalLink, X } from "lucide-react";

interface TrailerModalProps {
  isOpen: boolean;
  onClose: () => void;
  dramaTitle: string;
}

export function TrailerModal({ isOpen, onClose, dramaTitle }: TrailerModalProps) {
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
  const embedUrl = `https://www.youtube-nocookie.com/embed?listType=search&list=${searchQuery}&autoplay=1`;
  const externalUrl = `https://www.youtube.com/results?search_query=${searchQuery}`;

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
            <span className="eyebrow" style={{ color: "var(--lemon)" }}>Official Preview</span>
            <h3>{dramaTitle}</h3>
          </div>
          <div className="trailer-modal-actions">
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
          <iframe
            src={embedUrl}
            title={`${dramaTitle} official trailer`}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
            allowFullScreen
          />
        </div>
      </div>
    </div>
  );
}
