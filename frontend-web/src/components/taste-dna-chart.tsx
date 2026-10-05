"use client";

import { useMemo } from "react";

interface TasteDNAChartProps {
  genres: [string, number][];
}

const PALETTE = [
  "#e95f4d", // Coral
  "#f5cd62", // Lemon Gold
  "#acbda6", // Sage Green
  "#4d9de0", // Sky Blue
  "#e15554", // Crimson
  "#9b5de5", // Violet
  "#00bbf9", // Cyan
  "#f15bb5", // Pink
];

export function TasteDNAChart({ genres }: TasteDNAChartProps) {
  const topGenres = useMemo(() => genres.slice(0, 6), [genres]);

  if (!topGenres.length) {
    return (
      <div className="taste-dna-empty">
        <p className="muted">Rate at least 3 dramas to unlock your Taste DNA visualization!</p>
      </div>
    );
  }

  // Calculate radar polygon points
  const size = 260;
  const center = size / 2;
  const radius = center - 35;
  const numPoints = topGenres.length;

  const points = topGenres.map(([, score], i) => {
    const angle = (Math.PI * 2 * i) / numPoints - Math.PI / 2;
    const r = radius * Math.max(0.2, Math.min(1, score));
    const x = center + r * Math.cos(angle);
    const y = center + r * Math.sin(angle);
    return { x, y, labelX: center + (radius + 22) * Math.cos(angle), labelY: center + (radius + 22) * Math.sin(angle) };
  });

  const polygonPath = points.map((p) => `${p.x},${p.y}`).join(" ");

  // Concentric background grid circles
  const gridLevels = [0.33, 0.66, 1];

  return (
    <div className="taste-dna-wrapper">
      <div className="taste-dna-radar">
        <svg viewBox={`0 0 ${size} ${size}`} className="radar-svg">
          {/* Background web rings */}
          {gridLevels.map((lvl) => (
            <circle
              key={lvl}
              cx={center}
              cy={center}
              r={radius * lvl}
              fill="none"
              stroke="var(--line)"
              strokeDasharray={lvl < 1 ? "4 4" : undefined}
              strokeWidth="1"
            />
          ))}

          {/* Web spokes */}
          {points.map((p, i) => (
            <line
              key={i}
              x1={center}
              y1={center}
              x2={center + radius * Math.cos((Math.PI * 2 * i) / numPoints - Math.PI / 2)}
              y2={center + radius * Math.sin((Math.PI * 2 * i) / numPoints - Math.PI / 2)}
              stroke="var(--line)"
              strokeWidth="1"
            />
          ))}

          {/* Radar area polygon */}
          <polygon
            points={polygonPath}
            className="radar-polygon"
          />

          {/* Radar vertices */}
          {points.map((p, i) => (
            <circle
              key={i}
              cx={p.x}
              cy={p.y}
              r="4.5"
              fill={PALETTE[i % PALETTE.length]}
              stroke="#fff"
              strokeWidth="1.5"
            />
          ))}

          {/* Axis Labels */}
          {topGenres.map(([name], i) => {
            const p = points[i];
            return (
              <text
                key={name}
                x={p.labelX}
                y={p.labelY}
                textAnchor="middle"
                dominantBaseline="central"
                className="radar-text"
              >
                {name}
              </text>
            );
          })}
        </svg>
      </div>

      {/* Breakdown Bar List */}
      <div className="taste-dna-bars">
        {topGenres.map(([name, score], idx) => {
          const pct = Math.round(score * 100);
          const color = PALETTE[idx % PALETTE.length];
          return (
            <div className="dna-bar-row" key={name}>
              <div className="dna-bar-info">
                <span className="dna-dot" style={{ backgroundColor: color }} />
                <span className="dna-genre-name">{name}</span>
                <strong className="dna-genre-pct">{pct}%</strong>
              </div>
              <div className="dna-bar-track">
                <div
                  className="dna-bar-fill"
                  style={{ width: `${Math.max(6, pct)}%`, backgroundColor: color }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
