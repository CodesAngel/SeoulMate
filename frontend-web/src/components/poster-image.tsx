"use client";

import Image from "next/image";
import { Clapperboard } from "lucide-react";
import { useState } from "react";
import { resolvePosterUrl } from "@/lib/api";

/**
 * "optimized": served through Vercel's image optimizer (smaller, cached).
 * "direct": the optimizer refused the image (e.g. 402 once the plan's monthly
 *   image allowance is used up), so the same file is loaded straight from
 *   Supabase Storage. The WebP thumbnails there are already small.
 * "failed": both attempts failed; show the placeholder.
 */
type Attempt = "optimized" | "direct" | "failed";

export function PosterImage({
  src,
  alt,
  priority = false,
  sizes = "(max-width: 640px) 44vw, (max-width: 1100px) 28vw, 220px",
  quality,
}: {
  src?: string | null;
  alt: string;
  priority?: boolean;
  sizes?: string;
  /** Must be listed in `images.qualities` in next.config.ts. */
  quality?: number;
}) {
  const resolved = resolvePosterUrl(src);
  const [attempt, setAttempt] = useState<Attempt>("optimized");
  const [attemptFor, setAttemptFor] = useState(resolved);

  // A reused card can receive a different poster: start again with the optimizer.
  if (attemptFor !== resolved) {
    setAttemptFor(resolved);
    setAttempt("optimized");
  }

  if (!resolved || attempt === "failed") {
    return (
      <div className="poster-placeholder" role="img" aria-label={`${alt} poster unavailable`}>
        <Clapperboard size={30} />
        <span>Poster unavailable</span>
      </div>
    );
  }

  return (
    <Image
      key={attempt}
      src={resolved}
      alt={alt}
      fill
      unoptimized={attempt === "direct"}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      sizes={sizes}
      quality={quality}
      className="poster-img"
      onError={() => setAttempt((current) => (current === "optimized" ? "direct" : "failed"))}
    />
  );
}
