import { ImageResponse } from "next/og";

// The default share image (1200×630) for pages without their own poster.
// Built once at build time.
export const dynamic = "force-static";

export function GET() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "0 96px",
          background: "linear-gradient(135deg, #2D1738 0%, #4a1f45 60%, #C63C6D 140%)",
          color: "#FFFCF8",
        }}
      >
        <div style={{ display: "flex", fontSize: 40, letterSpacing: 6, color: "#d9b8e8" }}>
          STORIES MATCHED TO YOUR MOOD
        </div>
        <div style={{ display: "flex", fontSize: 120, fontWeight: 700, marginTop: 24 }}>
          Seoul<span style={{ color: "#f07aa3" }}>Mate</span>
        </div>
        <div style={{ display: "flex", fontSize: 46, marginTop: 24, maxWidth: 900, lineHeight: 1.3 }}>
          Find your next K-drama by mood, actor or story.
        </div>
        <div style={{ display: "flex", fontSize: 32, marginTop: 48, color: "#d9b8e8" }}>
          2,130 Korean dramas · natural-language search
        </div>
      </div>
    ),
    { width: 1200, height: 630 },
  );
}
