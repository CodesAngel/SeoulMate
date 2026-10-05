"use client";

import { useState } from "react";
import { Star } from "lucide-react";

interface StarRatingProps {
  value: number;
  onChange: (score: number) => void;
  disabled?: boolean;
}

const SCORE_LABELS: Record<number, string> = {
  10: "Masterpiece (10/10)",
  9.5: "Incredible (9.5/10)",
  9: "Amazing (9/10)",
  8.5: "Great (8.5/10)",
  8: "Very Good (8/10)",
  7.5: "Good (7.5/10)",
  7: "Enjoyable (7/10)",
  6.5: "Decent (6.5/10)",
  6: "Fair (6/10)",
  5: "Mediocre (5/10)",
  4: "Disappointing (4/10)",
  3: "Bad (3/10)",
  2: "Very Bad (2/10)",
  1: "Terrible (1/10)",
};

export function StarRating({ value, onChange, disabled = false }: StarRatingProps) {
  const [hoverScore, setHoverScore] = useState<number | null>(null);

  const activeScore = hoverScore !== null ? hoverScore : value;
  const currentLabel =
    SCORE_LABELS[activeScore] || `${activeScore}/10`;

  return (
    <div className="interactive-rating-container" onMouseLeave={() => setHoverScore(null)}>
      <div className="star-rating-row" role="radiogroup" aria-label="Rating out of 10">
        {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].map((starNum) => {
          const isFilled = activeScore >= starNum;
          const isHalf = activeScore >= starNum - 0.5 && !isFilled;

          return (
            <button
              key={starNum}
              type="button"
              disabled={disabled}
              className={`star-button ${isFilled ? "filled" : ""} ${isHalf ? "half" : ""}`}
              onMouseEnter={() => setHoverScore(starNum)}
              onClick={() => onChange(starNum)}
              aria-label={`Rate ${starNum} out of 10`}
              aria-checked={value === starNum}
              role="radio"
            >
              <Star
                size={22}
                className="star-icon"
                fill={isFilled ? "currentColor" : isHalf ? "url(#halfGrad)" : "none"}
              />
            </button>
          );
        })}
      </div>
      <div className="rating-score-badge">
        <span className="rating-score-num">{activeScore.toFixed(1)}</span>
        <span className="rating-score-text">{currentLabel}</span>
      </div>

      <svg width="0" height="0" className="hidden-svg">
        <defs>
          <linearGradient id="halfGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="50%" stopColor="currentColor" />
            <stop offset="50%" stopColor="transparent" stopOpacity="1" />
          </linearGradient>
        </defs>
      </svg>
    </div>
  );
}
