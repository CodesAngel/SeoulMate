"use client";

import Image from "next/image";
import Link from "next/link";
import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import type { TmdbCast, TmdbCastMember } from "@/lib/tmdb";

const IMG = "https://image.tmdb.org/t/p/w185";

function initials(name: string) {
  return name
    .split(/[\s-]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((word) => word[0]?.toUpperCase())
    .join("");
}

// Photo from TMDB's servers (unoptimized: Vercel never stores a copy).
// Missing or broken photos fall back to the actor's initials.
function CastPhoto({ member, size, className }: { member: TmdbCastMember; size: number; className: string }) {
  const [failed, setFailed] = useState(false);
  return (
    <span className={className} aria-hidden="true">
      {member.photo && !failed ? (
        <Image
          src={`${IMG}${member.photo}`}
          alt=""
          width={size}
          height={Math.round(size * 1.5)}
          loading="lazy"
          unoptimized
          onError={() => setFailed(true)}
        />
      ) : (
        <span className="cast-initials">{initials(member.name)}</span>
      )}
    </span>
  );
}

export function CastSection({
  cast,
  catalogNames,
}: {
  cast: TmdbCast;
  // Names that exist in SeoulMate's catalog; only these link to a search.
  catalogNames: string[];
}) {
  const [showAll, setShowAll] = useState(false);
  const linkable = new Set(catalogNames);

  return (
    <section className="detail-cast" aria-labelledby="cast-heading">
      <div className="cast-head">
        <h2 id="cast-heading">Cast</h2>
        <a className="tmdb-credit" href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer">
          <span>Photos from</span>
          {/* Official TMDB logo, unmodified (TMDB attribution rules). */}
          <Image src="/tmdb-logo.svg" alt="TMDB" width={78} height={10} unoptimized style={{ width: "auto", height: 10 }} />
        </a>
      </div>

      <div className="cast-row">
        {cast.main.map((member) => {
          const body = (
            <>
              <CastPhoto member={member} size={185} className="cast-photo" />
              <span className="cast-name">{member.name}</span>
              {member.character && <span className="cast-char">as {member.character}</span>}
            </>
          );
          return linkable.has(member.name) ? (
            <Link
              key={member.name}
              href={`/discover?q=${encodeURIComponent(member.name)}`}
              className="cast-card"
              title={`Find dramas starring ${member.name}`}
            >
              {body}
            </Link>
          ) : (
            <div key={member.name} className="cast-card">
              {body}
            </div>
          );
        })}
      </div>

      {cast.more.length > 0 && (
        <>
          <button
            type="button"
            className="cast-more"
            onClick={() => setShowAll((open) => !open)}
            aria-expanded={showAll}
            aria-controls="cast-full"
          >
            {showAll ? (
              <>
                Show less <ChevronUp size={15} />
              </>
            ) : (
              <>
                Full cast · {cast.moreTotal} more <ChevronDown size={15} />
              </>
            )}
          </button>
          {showAll && (
            <div className="cast-full" id="cast-full">
              <ul>
                {cast.more.map((member, index) => (
                  <li key={`${member.name}-${index}`} className="cast-full-row">
                    <CastPhoto member={member} size={92} className="cast-full-photo" />
                    <span>
                      <b>{member.name}</b>
                      {member.character && <small>{member.character}</small>}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="cast-full-note">
                {cast.moreTotal > cast.more.length
                  ? `Showing ${cast.more.length} of ${cast.moreTotal}. `
                  : "From TMDB. "}
                <a
                  href={`https://www.themoviedb.org/tv/${cast.tmdbId}/cast`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {cast.moreTotal > cast.more.length ? "See the full cast on TMDB" : "View on TMDB"}
                </a>
              </p>
            </div>
          )}
        </>
      )}
    </section>
  );
}
