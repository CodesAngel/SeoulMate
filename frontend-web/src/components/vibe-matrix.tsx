"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Sliders, Sparkles, Wand2 } from "lucide-react";

interface VibeMatrixProps {
  onApplyVibe: (vibeQuery: string) => void;
  defaultExpanded?: boolean;
}

const PRESETS = [
  {
    label: "💖 Pure Rom-Com Fluff",
    tone: 90,
    tension: 10,
    pacing: 30,
    setting: 15,
  },
  {
    label: "🗡️ Dark Revenge Thriller",
    tone: 10,
    tension: 95,
    pacing: 90,
    setting: 20,
  },
  {
    label: "☕ Cozy Rainy Day Slice-of-Life",
    tone: 85,
    tension: 15,
    pacing: 10,
    setting: 10,
  },
  {
    label: "👑 Royal Palace Intrigue",
    tone: 40,
    tension: 75,
    pacing: 65,
    setting: 55,
  },
  {
    label: "✨ Supernatural Urban Fantasy",
    tone: 60,
    tension: 50,
    pacing: 75,
    setting: 90,
  },
];

export function VibeMatrix({ onApplyVibe, defaultExpanded = false }: VibeMatrixProps) {
  const [expanded, setExpanded] = useState(defaultExpanded);

  // Sliders range 0 - 100
  const [tone, setTone] = useState(70); // 0 = Tearjerker, 100 = Heartwarming
  const [tension, setTension] = useState(25); // 0 = Fluffy Romance, 100 = Dark Revenge
  const [pacing, setPacing] = useState(40); // 0 = Slow-Burn, 100 = High-Stakes Action
  const [setting, setSetting] = useState(20); // 0 = Modern Urban, 50 = Historical Palace, 100 = Supernatural Fantasy

  // Synthesize natural language prompt for SeoulMate's bi-encoder
  const synthesizedPrompt = useMemo(() => {
    const parts: string[] = [];

    // 1. Tone
    if (tone <= 30) parts.push("heartbreaking tearjerker melodrama");
    else if (tone >= 70) parts.push("heartwarming feel-good comfort");
    else parts.push("emotionally balanced poignant");

    // 2. Tension / Genre style
    if (tension <= 30) parts.push("fluffy sweet romantic comedy");
    else if (tension >= 70) parts.push("dark gritty revenge thriller");
    else parts.push("romantic suspense with tension");

    // 3. Pacing
    if (pacing <= 30) parts.push("slow-burn slice of life");
    else if (pacing >= 70) parts.push("high-stakes fast-paced action");
    else parts.push("engaging compelling pacing");

    // 4. Setting
    if (setting <= 30) parts.push("modern city workplace");
    else if (setting >= 75) parts.push("supernatural fantasy realm");
    else parts.push("historical sageuk royal palace");

    return parts.join(", ");
  }, [tone, tension, pacing, setting]);

  function applyPreset(p: typeof PRESETS[0]) {
    setTone(p.tone);
    setTension(p.tension);
    setPacing(p.pacing);
    setSetting(p.setting);
  }

  function handleApply() {
    onApplyVibe(synthesizedPrompt);
  }

  return (
    <div className={`vibe-matrix-card ${expanded ? "expanded" : ""}`}>
      <div className="vibe-matrix-header" onClick={() => setExpanded(!expanded)}>
        <div className="vibe-header-left">
          <div className="vibe-icon-badge">
            <Sliders size={16} />
          </div>
          <div>
            <div className="vibe-title-row">
              <span className="eyebrow" style={{ color: "var(--coral)" }}>AI Vibe Tuner</span>
              <span className="vibe-pill-active">Interactive</span>
            </div>
            <h3>Tune Your Story Atmosphere</h3>
          </div>
        </div>
        <button
          type="button"
          className="vibe-toggle-btn"
          aria-expanded={expanded}
          aria-label="Toggle Vibe Matrix controls"
        >
          <ChevronDown
            size={18}
            style={{ transform: expanded ? "rotate(180deg)" : "rotate(0deg)", transition: "transform 200ms ease" }}
          />
        </button>
      </div>

      {expanded && (
        <div className="vibe-matrix-body">
          {/* Quick Presets */}
          <div className="vibe-presets-row">
            <span className="preset-label">Instant Mood:</span>
            <div className="preset-chips">
              {PRESETS.map((p) => (
                <button
                  key={p.label}
                  type="button"
                  className="preset-chip"
                  onClick={() => applyPreset(p)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          </div>

          {/* 4 Interactive Sliders */}
          <div className="vibe-sliders-grid">
            {/* Slider 1: Emotional Tone */}
            <div className="vibe-slider-group">
              <div className="slider-label-row">
                <span className="slider-end-left">😭 Tearjerker</span>
                <strong className="slider-param-name">Emotional Tone</strong>
                <span className="slider-end-right">💖 Heartwarming</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={tone}
                onChange={(e) => setTone(Number(e.target.value))}
                className="vibe-range-input"
              />
            </div>

            {/* Slider 2: Romance vs Dark Revenge */}
            <div className="vibe-slider-group">
              <div className="slider-label-row">
                <span className="slider-end-left">🌸 Fluffy Rom-Com</span>
                <strong className="slider-param-name">Theme & Romance</strong>
                <span className="slider-end-right">🗡️ Dark Revenge</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={tension}
                onChange={(e) => setTension(Number(e.target.value))}
                className="vibe-range-input"
              />
            </div>

            {/* Slider 3: Pacing */}
            <div className="vibe-slider-group">
              <div className="slider-label-row">
                <span className="slider-end-left">☕ Slow-Burn Slice</span>
                <strong className="slider-param-name">Pacing & Energy</strong>
                <span className="slider-end-right">⚡ High-Stakes Action</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={pacing}
                onChange={(e) => setPacing(Number(e.target.value))}
                className="vibe-range-input"
              />
            </div>

            {/* Slider 4: Setting */}
            <div className="vibe-slider-group">
              <div className="slider-label-row">
                <span className="slider-end-left">🏙️ Modern City</span>
                <strong className="slider-param-name">World Setting</strong>
                <span className="slider-end-right">✨ Supernatural</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={setting}
                onChange={(e) => setSetting(Number(e.target.value))}
                className="vibe-range-input"
              />
            </div>
          </div>

          {/* Live Synthesizer Output Bar */}
          <div className="vibe-footer-bar">
            <div className="vibe-prompt-preview">
              <Sparkles size={15} className="vibe-sparkle" />
              <div>
                <span className="synthesized-label">Synthesized Search Vibe:</span>
                <p className="synthesized-text">&ldquo;{synthesizedPrompt}&rdquo;</p>
              </div>
            </div>
            <button
              type="button"
              className="primary-button vibe-submit-btn"
              onClick={handleApply}
            >
              <Wand2 size={15} />
              <span>Apply Vibe Search</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
