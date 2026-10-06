"use client";

import { useState } from "react";
import { Eye, EyeOff, ShieldAlert } from "lucide-react";

interface SpoilerContentProps {
  children: React.ReactNode;
  isSpoiler: boolean;
  className?: string;
  previewOnly?: boolean;
}

export function SpoilerContent({
  children,
  isSpoiler,
  className = "",
  previewOnly = false,
}: SpoilerContentProps) {
  const [revealed, setRevealed] = useState(false);

  if (!isSpoiler) {
    return <div className={className}>{children}</div>;
  }

  // In preview mode (e.g. feed list, homepage), never reveal spoiler text
  if (previewOnly) {
    return (
      <div className={`spoiler-preview-guard ${className}`}>
        <span className="spoiler-tag">
          <ShieldAlert size={13} />
          <span>Contains spoilers</span>
        </span>
        <p className="spoiler-preview-notice muted">
          Content hidden to protect your viewing experience. View discussion to reveal.
        </p>
      </div>
    );
  }

  if (!revealed) {
    return (
      <div className={`spoiler-guard-box ${className}`}>
        <div className="spoiler-guard-inner">
          <div className="spoiler-guard-meta">
            <ShieldAlert size={16} className="spoiler-guard-icon" />
            <span>Contains spoilers</span>
          </div>
          <button
            type="button"
            className="ghost-button spoiler-reveal-button"
            onClick={() => setRevealed(true)}
            aria-label="Reveal spoiler content"
          >
            <Eye size={14} />
            <span>Reveal</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className={`spoiler-revealed-wrapper ${className}`}>
      <div className="spoiler-revealed-bar">
        <span className="spoiler-revealed-badge">Spoiler revealed</span>
        <button
          type="button"
          className="spoiler-hide-button"
          onClick={() => setRevealed(false)}
          aria-label="Hide spoiler content"
        >
          <EyeOff size={13} />
          <span>Hide</span>
        </button>
      </div>
      <div className="spoiler-revealed-body">{children}</div>
    </div>
  );
}
