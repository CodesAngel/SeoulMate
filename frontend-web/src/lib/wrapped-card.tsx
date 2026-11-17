import { ImageResponse } from "next/og";
import { SITE_URL } from "@/lib/site";
import { type WrappedStats, wrappedTitle } from "@/lib/wrapped";

// The Wrapped share image (1080 × 1350, 4:5), used for "Save image" and as the
// public snapshot page's og:image. Satori renders it: flexbox only, every
// element with more than one child needs display: flex.
export const CARD_SIZE = { width: 1080, height: 1350 };

const INK = "#151827";
const SOFT = "#5b6070";
const LINE = "#eee8f5";

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", marginBottom: 34 }}>
      <div style={{ display: "flex", fontSize: 24, fontWeight: 700, letterSpacing: 3, color: SOFT }}>
        {label.toUpperCase()}
      </div>
      <div style={{ display: "flex", fontSize: 40, fontWeight: 700, marginTop: 6, lineHeight: 1.2 }}>
        {value}
      </div>
    </div>
  );
}

function Stat({ value, label, last = false }: { value: number; label: string; last?: boolean }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        flex: 1,
        padding: "34px 0",
        borderRight: last ? "none" : `2px solid ${LINE}`,
      }}
    >
      <div style={{ display: "flex", fontSize: 84, fontWeight: 700, lineHeight: 1 }}>
        {value.toLocaleString("en")}
      </div>
      <div style={{ display: "flex", fontSize: 28, color: SOFT, marginTop: 10 }}>{label}</div>
    </div>
  );
}

export function wrappedCardImage(stats: WrappedStats, init?: ResponseInit) {
  const totals = stats.totals ?? { dramas: 0, episodes: 0, hours: 0 };
  const topGenres = (stats.genres ?? []).slice(0, 3).map((genre) => genre.name).join(" · ");
  const top = stats.top_rated;
  const poster = top?.poster_original_url ?? top?.poster_url;
  const host = SITE_URL.host;

  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          background: "#fffcf8",
          color: INK,
        }}
      >
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            background: "linear-gradient(135deg, #2D1738 0%, #4a1f45 70%, #6b1c43 100%)",
            color: "#ffffff",
            padding: "56px 64px 52px",
          }}
        >
          <div style={{ display: "flex", fontSize: 28, fontWeight: 700, letterSpacing: 6, color: "#f3a8c6" }}>
            {`SEOULMATE WRAPPED ${stats.year}`}
          </div>
          <div style={{ display: "flex", fontSize: 64, marginTop: 14, lineHeight: 1.1 }}>
            {wrappedTitle(stats)}
          </div>
        </div>

        <div style={{ display: "flex", borderBottom: `2px solid ${LINE}` }}>
          <Stat value={totals.dramas} label="dramas" />
          <Stat value={totals.episodes} label="episodes" />
          <Stat value={totals.hours} label="hours" last />
        </div>

        <div style={{ display: "flex", flex: 1, alignItems: "center", padding: "0 64px" }}>
          <div style={{ display: "flex", flexDirection: "column", flex: 1, paddingRight: 40 }}>
            {stats.fan_type && <Fact label="Fan type" value={stats.fan_type.name} />}
            {stats.top_actor && (
              <Fact label="Top actor" value={`${stats.top_actor.name} · ${stats.top_actor.count}`} />
            )}
            {stats.top_trope && <Fact label="Top trope" value={stats.top_trope.name} />}
            {topGenres && <Fact label="Top genres" value={topGenres} />}
          </div>
          {top && (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", width: 340 }}>
              {poster ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={poster}
                  alt=""
                  width={340}
                  height={510}
                  style={{ borderRadius: 18, objectFit: "cover" }}
                />
              ) : (
                <div style={{ display: "flex", width: 340, height: 510, borderRadius: 18, background: LINE }} />
              )}
              <div
                style={{
                  display: "flex",
                  fontSize: 28,
                  color: SOFT,
                  marginTop: 16,
                  textAlign: "center",
                  justifyContent: "center",
                }}
              >
                {`#1 ${top.title}`}
              </div>
            </div>
          )}
        </div>

        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            padding: "26px 64px",
            fontSize: 26,
            color: SOFT,
            borderTop: `2px solid ${LINE}`,
          }}
        >
          <div style={{ display: "flex" }}>{`${host}/wrapped`}</div>
          <div style={{ display: "flex" }}>Made with SeoulMate</div>
        </div>
      </div>
    ),
    { ...CARD_SIZE, ...init },
  );
}
