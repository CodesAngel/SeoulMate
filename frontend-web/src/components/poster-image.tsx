"use client";

import Image from "next/image";
import { Clapperboard } from "lucide-react";
import { useState } from "react";
import { resolvePosterUrl } from "@/lib/api";

export function PosterImage({
  src,
  alt,
  priority = false,
  sizes = "(max-width: 640px) 44vw, (max-width: 1100px) 28vw, 220px",
}: {
  src?: string;
  alt: string;
  priority?: boolean;
  sizes?: string;
}) {
  const [failed, setFailed] = useState(false);
  const resolved = resolvePosterUrl(src);

  if (!resolved || failed) {
    return (
      <div className="poster-placeholder" role="img" aria-label={`${alt} poster unavailable`}>
        <Clapperboard size={30} />
        <span>Poster unavailable</span>
      </div>
    );
  }

  return (
    <Image
      src={resolved}
      alt={alt}
      fill
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      sizes={sizes}
      className="poster-img"
      onError={() => setFailed(true)}
    />
  );
}
