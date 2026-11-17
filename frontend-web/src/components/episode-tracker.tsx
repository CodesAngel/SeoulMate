"use client";

import { useEffect, useRef, useState } from "react";
import { Check, Minus, Plus } from "lucide-react";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import type { Drama } from "@/lib/types";

interface EpisodeTrackerProps {
  drama: Drama;
  onComplete?: () => void;
}

const SAVE_DELAY_MS = 600;

function sameDrama(left: Drama, right: Drama) {
  if (left.drama_id && right.drama_id) return left.drama_id === right.drama_id;
  return left.Title === right.Title && left["Release Years"] === right["Release Years"];
}

function readStored(key: string): number | null {
  try {
    const saved = localStorage.getItem(key);
    return saved === null ? null : parseInt(saved, 10) || 0;
  } catch {
    return null;
  }
}

/**
 * Episode progress. Signed-in fans with the drama in their list save to their
 * account (it counts toward Wrapped); guests keep it in this browser. Progress
 * saved in the browser before accounts stored it is copied over once.
 */
export function EpisodeTracker({ drama, onComplete }: EpisodeTrackerProps) {
  const { user } = useAuth();
  const { watchlistEntries, saveEpisodeProgress } = useApp();
  const totalEpisodes = drama.episodes ? parseInt(String(drama.episodes), 10) : null;
  const storageKey = `seoulmate:ep:${drama.drama_id ?? drama.Title}`;

  const entry = user ? watchlistEntries.find((item) => sameDrama(item.drama, drama)) : undefined;
  const accountMode = Boolean(user && entry && drama.drama_id);
  const serverValue = entry?.episodes_watched ?? null;

  const [currentEp, setCurrentEp] = useState<number>(0);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pendingSave = useRef<(() => void) | null>(null);
  const migrated = useRef(false);

  useEffect(() => {
    if (saveTimer.current) return; // a local change is still waiting to be saved
    let value: number;
    if (!accountMode) {
      value = readStored(storageKey) ?? 0;
    } else {
      const stored = readStored(storageKey);
      if (serverValue === null && stored && !migrated.current) {
        // Browser-only progress from before: move it into the account.
        migrated.current = true;
        value = stored;
        void saveEpisodeProgress(drama, stored).then((saved) => {
          if (!saved) return;
          try {
            localStorage.removeItem(storageKey);
          } catch {
            // Ignore localStorage errors
          }
        });
      } else {
        value = serverValue ?? 0;
      }
    }
    // Hydrate progress (browser or account) after the server render.
    setCurrentEp(value);
  }, [accountMode, drama, saveEpisodeProgress, serverValue, storageKey]);

  // Leaving the page (or the card) saves a change that is still waiting.
  useEffect(
    () => () => {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = null;
      pendingSave.current?.();
      pendingSave.current = null;
    },
    [],
  );

  function updateEp(newVal: number) {
    const clamped = Math.max(0, totalEpisodes ? Math.min(newVal, totalEpisodes) : newVal);
    setCurrentEp(clamped);

    if (accountMode) {
      if (saveTimer.current) clearTimeout(saveTimer.current);
      const save = () => void saveEpisodeProgress(drama, clamped);
      pendingSave.current = save;
      saveTimer.current = setTimeout(() => {
        saveTimer.current = null;
        pendingSave.current = null;
        save();
      }, SAVE_DELAY_MS);
    } else {
      try {
        localStorage.setItem(storageKey, String(clamped));
      } catch {
        // Ignore localStorage errors
      }
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
