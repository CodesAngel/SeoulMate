"use client";

import { useEffect, useState } from "react";
import { Check, Minus, Plus } from "lucide-react";
import type { Drama } from "@/lib/types";

interface EpisodeTrackerProps {
  drama: Drama;
  onComplete?: () => void;
}

export function EpisodeTracker({ drama, onComplete }: EpisodeTrackerProps) {
  const totalEpisodes = drama.episodes ? parseInt(String(drama.episodes), 10) : null;
  const storageKey = `seoulmate:ep:${drama.drama_id ?? drama.Title}`;

  const [currentEp, setCurrentEp] = useState<number>(0);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);
      if (saved !== null) {
        // Hydrate browser-only progress after the server render.
        // eslint-disable-next-line react-hooks/set-state-in-effect
        setCurrentEp(parseInt(saved, 10) || 0);
      }
    } catch {
      // Ignore localStorage errors
    }
  }, [storageKey]);

  function updateEp(newVal: number) {
    const clamped = Math.max(0, totalEpisodes ? Math.min(newVal, totalEpisodes) : newVal);
    setCurrentEp(clamped);
    try {
      localStorage.setItem(storageKey, String(clamped));
    } catch {
      // Ignore localStorage errors
    }

    if (totalEpisodes && clamped === totalEpisodes && onComplete) {
      onComplete();
    }
  }

  const progressPercent = totalEpisodes ? Math.min(100, Math.round((currentEp / totalEpisodes) * 100)) : null;

  return (
    <div className="episode-tracker">
      <div className="episode-tracker-header">
        <span className="ep-label">Episode Progress</span>
        <span className="ep-count">
          <strong>{currentEp}</strong> {totalEpisodes ? `/ ${totalEpisodes}` : "eps watched"}
        </span>
      </div>

      {progressPercent !== null && (
        <div className="ep-progress-bar">
          <div className="ep-progress-fill" style={{ width: `${progressPercent}%` }} />
        </div>
      )}

      <div className="ep-buttons">
        <button
          type="button"
          className="ep-btn"
          onClick={() => updateEp(currentEp - 1)}
          disabled={currentEp <= 0}
          aria-label="Decrease episode count"
        >
          <Minus size={13} />
        </button>
        <button
          type="button"
          className="ep-btn ep-btn-plus"
          onClick={() => updateEp(currentEp + 1)}
          disabled={Boolean(totalEpisodes && currentEp >= totalEpisodes)}
          aria-label="Increase episode count"
        >
          <Plus size={13} />
          <span>Next Ep</span>
        </button>
        {totalEpisodes && currentEp === totalEpisodes && (
          <span className="ep-completed-tag">
            <Check size={12} /> Finished
          </span>
        )}
      </div>
    </div>
  );
}
