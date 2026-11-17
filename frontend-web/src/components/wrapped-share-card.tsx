import { PosterImage } from "@/components/poster-image";
import { SITE_URL } from "@/lib/site";
import { type WrappedStats, wrappedTitle } from "@/lib/wrapped";

/** The share card as HTML (same layout as the downloadable image in lib/wrapped-card.tsx). */
export function WrappedShareCard({ stats }: { stats: WrappedStats }) {
  const totals = stats.totals ?? { dramas: 0, episodes: 0, hours: 0 };
  const topGenres = (stats.genres ?? []).slice(0, 3).map((genre) => genre.name).join(" · ");
  const top = stats.top_rated;

  return (
    <div className="wr-card">
      <div className="wr-card-head">
        <p>SeoulMate Wrapped {stats.year}</p>
        <h3>{wrappedTitle(stats)}</h3>
      </div>
      <div className="wr-card-stats">
        <div><b>{totals.dramas}</b><span>dramas</span></div>
        <div><b>{totals.episodes}</b><span>episodes</span></div>
        <div><b>{totals.hours}</b><span>hours</span></div>
      </div>
      <div className="wr-card-body">
        <dl>
          {stats.fan_type && (
            <div><dt>Fan type</dt><dd>{stats.fan_type.name}</dd></div>
          )}
          {stats.top_actor && (
            <div><dt>Top actor</dt><dd>{stats.top_actor.name} · {stats.top_actor.count}</dd></div>
          )}
          {stats.top_trope && (
            <div><dt>Top trope</dt><dd>{stats.top_trope.name}</dd></div>
          )}
          {topGenres && (
            <div><dt>Top genres</dt><dd>{topGenres}</dd></div>
          )}
        </dl>
        {top && (
          <div className="wr-card-top">
            <div className="wr-poster">
              <PosterImage src={top.poster_url} alt={top.title} sizes="110px" />
            </div>
            <span>#1 {top.title}</span>
          </div>
        )}
      </div>
      <div className="wr-card-foot">
        <span>{SITE_URL.host}/wrapped</span>
        <span>Made with SeoulMate</span>
      </div>
    </div>
  );
}
