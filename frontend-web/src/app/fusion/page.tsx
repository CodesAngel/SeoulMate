"use client";

import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Check, Flame, Share2, Sparkles, Users } from "lucide-react";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { DramaCard } from "@/components/drama-card";
import { TrailerModal } from "@/components/trailer-modal";
import { searchDramas } from "@/lib/api";

interface Archetype {
  id: string;
  name: string;
  tagline: string;
  avatar: string;
  genres: Record<string, number>;
  tropes: string[];
  sampleDrama: string;
}

const FRIEND_ARCHETYPES: Archetype[] = [
  {
    id: "romcom",
    name: "The Rom-Com Dreamer",
    tagline: "Craves butterflies, fake dating, and witty banter",
    avatar: "🌸",
    genres: { Romance: 0.95, Comedy: 0.85, Melodrama: 0.4 },
    tropes: ["fluffy romance", "enemies to lovers", "workplace banter", "feel-good"],
    sampleDrama: "Crash Landing on You",
  },
  {
    id: "thriller",
    name: "The Mystery & Crime Sleuth",
    tagline: "Needs plot twists, corrupt conspiracies, and high stakes",
    avatar: "🕵️",
    genres: { Thriller: 0.95, Mystery: 0.9, Law: 0.75, Action: 0.6 },
    tropes: ["dark revenge", "serial killer mystery", "legal thriller", "unpredictable twists"],
    sampleDrama: "Signal",
  },
  {
    id: "sageuk",
    name: "The Joseon Court Scholar",
    tagline: "Lives for royal palaces, sword fights, and tragic royalty",
    avatar: "👑",
    genres: { Historical: 0.95, Drama: 0.85, Romance: 0.6, Action: 0.65 },
    tropes: ["historical palace intrigue", "royal conspiracies", "swordsman honor", "forbidden love"],
    sampleDrama: "The Red Sleeve",
  },
  {
    id: "healing",
    name: "The Healing Slice-of-Life Soul",
    tagline: "Wants cozy neighborhood diners and tearjerker catharsis",
    avatar: "☕",
    genres: { "Slice of Life": 0.95, Family: 0.85, Melodrama: 0.7, Romance: 0.5 },
    tropes: ["slow-burn slice of life", "found family", "heartwarming comfort", "poetic life journey"],
    sampleDrama: "My Mister",
  },
  {
    id: "action",
    name: "The Adrenaline Thrillseeker",
    tagline: "Demands explosive stunts, anti-heroes, and superpowers",
    avatar: "⚡",
    genres: { Action: 0.95, Supernatural: 0.85, Fantasy: 0.75, Thriller: 0.7 },
    tropes: ["high-octane action", "supernatural martial arts", "vigilante justice", "dark fantasy"],
    sampleDrama: "Moving",
  },
  {
    id: "youth",
    name: "The Campus & Foodie Fan",
    tagline: "Loves college friendships, street food, and youthful dreams",
    avatar: "🍜",
    genres: { Youth: 0.9, Comedy: 0.8, Food: 0.85, Romance: 0.6 },
    tropes: ["campus youth", "wholesome squad", "food adventures", "optimistic coming of age"],
    sampleDrama: "Weightlifting Fairy Kim Bok-joo",
  },
];

export default function TasteFusionPage() {
  const { watchlist, ratingEntries, userId, sessionId } = useApp();
  const { user } = useAuth();

  // Selected Friend Archetype
  const [selectedFriendId, setSelectedFriendId] = useState<string>("romcom");
  const [customFriendDrama, setCustomFriendDrama] = useState<string>("");
  const [balance, setBalance] = useState<number>(50); // 0 = 100% Friend, 50 = Equal, 100 = 100% You
  const [copiedLink, setCopiedLink] = useState(false);
  const [activeTrailerTitle, setActiveTrailerTitle] = useState<string | null>(null);

  const selectedFriend = useMemo(() => {
    return (
      FRIEND_ARCHETYPES.find((a) => a.id === selectedFriendId) || FRIEND_ARCHETYPES[0]
    );
  }, [selectedFriendId]);

  // Compute Host (User 1) Taste Vector from Watchlist and Ratings
  const hostGenres = useMemo(() => {
    const counts: Record<string, number> = {};
    const totalSample = watchlist.length + ratingEntries.length;

    if (totalSample === 0) {
      // Default starter profile if new user
      return {
        Romance: 0.85,
        Mystery: 0.7,
        "Slice of Life": 0.65,
        Comedy: 0.6,
      };
    }

    watchlist.forEach((d) => {
      if (d.Genre) {
        d.Genre.split(",")
          .map((g) => g.trim())
          .forEach((g) => {
            counts[g] = (counts[g] || 0) + 1;
          });
      }
    });

    ratingEntries.forEach((r) => {
      if (r.drama.Genre) {
        r.drama.Genre.split(",")
          .map((g) => g.trim())
          .forEach((g) => {
            const weight = (r.rating || 7) / 10;
            counts[g] = (counts[g] || 0) + weight;
          });
      }
    });

    const maxVal = Math.max(...Object.values(counts), 1);
    const normalized: Record<string, number> = {};
    Object.entries(counts).forEach(([genre, val]) => {
      normalized[genre] = Number((val / maxVal).toFixed(2));
    });
    return normalized;
  }, [watchlist, ratingEntries]);

  // Calculate Mathematical Intersection and Chemistry Score
  const { chemistryScore, sharedTropes, synthesizedQuery, intersectionExplanation } =
    useMemo(() => {
      const hostEntries = Object.entries(hostGenres);
      const friendEntries = Object.entries(selectedFriend.genres);

      // Shared genres with overlap weight
      const shared: { genre: string; weight: number }[] = [];
      hostEntries.forEach(([g, hostWeight]) => {
        if (selectedFriend.genres[g]) {
          const friendWeight = selectedFriend.genres[g];
          const overlap = Math.min(hostWeight, friendWeight);
          shared.push({ genre: g, weight: overlap });
        }
      });

      shared.sort((a, b) => b.weight - a.weight);

      // Chemistry calculation: Jaccard-like overlap weighted by balance
      const rawMatch = shared.reduce((acc, curr) => acc + curr.weight, 0);
      const denominator = Math.max(hostEntries.length, friendEntries.length, 1);
      const chemistry = Math.min(98, Math.max(68, Math.round((rawMatch / denominator) * 100) + 45));

      // Build Shared Tropes / Tags
      const commonGround = [
        ...shared.slice(0, 3).map((s) => s.genre),
        ...selectedFriend.tropes.slice(0, 2),
      ];

      // Weight synthesis based on balance slider
      const hostWeightRatio = balance / 100;
      const friendWeightRatio = (100 - balance) / 100;

      const hostTopGenre = hostEntries.sort((a, b) => b[1] - a[1])[0]?.[0] || "Romance";
      const friendTopGenre = friendEntries.sort((a, b) => b[1] - a[1])[0]?.[0] || "Comedy";

      let queryParts: string[] = [];
      if (hostWeightRatio > 0.6) {
        queryParts.push(hostTopGenre);
        queryParts.push(...selectedFriend.tropes.slice(0, 2));
      } else if (friendWeightRatio > 0.6) {
        queryParts.push(friendTopGenre);
        queryParts.push(customFriendDrama || selectedFriend.sampleDrama);
      } else {
        // Balanced 50/50 intersection
        queryParts = [
          ...shared.slice(0, 2).map((s) => s.genre),
          ...selectedFriend.tropes.slice(0, 2),
        ];
        if (customFriendDrama) queryParts.push(customFriendDrama);
      }

      const finalQuery = queryParts.filter(Boolean).join(" ");

      const explanation =
        shared.length > 0
          ? `Perfect overlap found in ${shared.slice(0, 2).map((s) => s.genre).join(" & ")}. Merging your love for emotional depth with ${selectedFriend.name}'s appetite for engaging twists.`
          : `Diverse tastes detected! Finding cross-genre hybrid gems combining both styles seamlessly.`;

      return {
        chemistryScore: chemistry,
        sharedTropes: commonGround,
        synthesizedQuery: finalQuery || "engaging romance thriller drama",
        intersectionExplanation: explanation,
      };
    }, [hostGenres, selectedFriend, customFriendDrama, balance]);

  // Query Backend for the Mathematical Intersection recommendations
  const fusionResults = useQuery({
    queryKey: [
      "taste-fusion",
      synthesizedQuery,
      selectedFriendId,
      customFriendDrama,
      balance,
      userId,
    ],
    queryFn: ({ signal }) =>
      searchDramas(
        {
          query: synthesizedQuery,
          topN: 12,
          userId,
          sessionId,
        },
        signal,
      ),
  });

  const dramas = fusionResults.data?.recommendations || [];

  function handleCopyShare() {
    if (typeof window === "undefined") return;
    const url = new URL(window.location.href);
    url.searchParams.set("friend", selectedFriendId);
    url.searchParams.set("balance", String(balance));
    navigator.clipboard.writeText(url.toString()).then(() => {
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2400);
    });
  }

  // Circular gauge calculations
  const circumference = 2 * Math.PI * 52;
  const strokeDashoffset = circumference - (chemistryScore / 100) * circumference;

  return (
    <main className="shell fusion-container">
      {/* Header Banner */}
      <section className="fusion-hero-card">
        <div className="fusion-hero-badge">
          <Users size={14} />
          <span>Taste Fusion Mode</span>
        </div>
        <h1>Watch with a Friend</h1>
        <p>
          End the 45-minute argument over what to watch next. Select your companion or pick an archetype,
          and SeoulMate will calculate the mathematical intersection of your preferences.
        </p>
      </section>

      {/* The 3-Column Fusion Chamber */}
      <div className="fusion-chamber-board">
        {/* Column 1: You (Host) */}
        <div className="fusion-participant-card">
          <div className="fusion-card-head">
            <div className="fusion-avatar-box avatar-host">
              {user?.user_metadata?.avatar_emoji || "👤"}
            </div>
            <div>
              <span className="fusion-user-badge">Host Profile</span>
              <h3>{user?.email?.split("@")[0] || "You (Explorer)"}</h3>
            </div>
          </div>

          <div style={{ fontSize: "0.8rem", color: "var(--ink-soft)" }}>
            Taste DNA derived from {watchlist.length} saved titles & {ratingEntries.length} ratings.
          </div>

          <div className="fusion-genre-list">
            <span className="eyebrow" style={{ fontSize: "0.68rem", color: "#7d7f78" }}>
              Your Top Affinities
            </span>
            {Object.entries(hostGenres)
              .slice(0, 4)
              .map(([genre, score]) => (
                <div key={genre} className="fusion-genre-row">
                  <div className="fusion-genre-meta">
                    <span>{genre}</span>
                    <span>{Math.round(score * 100)}%</span>
                  </div>
                  <div className="fusion-genre-track">
                    <div
                      className="fusion-genre-fill"
                      style={{
                        width: `${Math.round(score * 100)}%`,
                        background: "var(--coral)",
                      }}
                    />
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Column 2: The Fusion Core Reactor */}
        <div className="fusion-reactor-column">
          <span className="eyebrow" style={{ color: "var(--coral)", fontSize: "0.72rem" }}>
            Fusion Reactor
          </span>

          <div className="fusion-core-gauge">
            <svg className="gauge-svg" viewBox="0 0 120 120">
              <circle
                className="gauge-circle-bg"
                cx="60"
                cy="60"
                r="52"
              />
              <circle
                className="gauge-circle-val"
                cx="60"
                cy="60"
                r="52"
                style={{
                  strokeDasharray: circumference,
                  strokeDashoffset: strokeDashoffset,
                }}
              />
            </svg>
            <div className="gauge-center-text">
              <span className="gauge-pct">{chemistryScore}%</span>
              <span className="gauge-lbl">Chemistry</span>
            </div>
          </div>

          <div className="fusion-overlap-summary">
            {intersectionExplanation}
          </div>

          {/* Balance Control */}
          <div className="fusion-balance-control">
            <div className="balance-label-row">
              <span>{100 - balance}% Friend</span>
              <span style={{ color: "var(--ink)", fontWeight: 800 }}>Compromise Ratio</span>
              <span>{balance}% You</span>
            </div>
            <input
              type="range"
              min="10"
              max="90"
              value={balance}
              onChange={(e) => setBalance(Number(e.target.value))}
              className="vibe-range-input"
              aria-label="Adjust compromise balance between you and your friend"
            />
          </div>

          <button
            type="button"
            className="fusion-ignite-btn"
            onClick={() => fusionResults.refetch()}
          >
            <Flame size={17} />
            <span>Ignite Taste Fusion</span>
          </button>
        </div>

        {/* Column 3: The Friend (Companion) */}
        <div className="fusion-participant-card">
          <div className="fusion-card-head">
            <div className="fusion-avatar-box avatar-friend">
              {selectedFriend.avatar}
            </div>
            <div>
              <span className="fusion-user-badge" style={{ color: "#a55eea" }}>
                Companion Profile
              </span>
              <h3>{selectedFriend.name}</h3>
            </div>
          </div>

          {/* Archetype Picker */}
          <div className="fusion-archetype-picker">
            <label htmlFor="friend-archetype-select">Choose Friend Archetype</label>
            <select
              id="friend-archetype-select"
              className="archetype-select"
              value={selectedFriendId}
              onChange={(e) => setSelectedFriendId(e.target.value)}
            >
              {FRIEND_ARCHETYPES.map((arch) => (
                <option key={arch.id} value={arch.id}>
                  {arch.avatar} {arch.name}
                </option>
              ))}
            </select>
          </div>

          {/* Custom Anchor Drama input */}
          <div className="friend-custom-input-box">
            <label htmlFor="friend-drama-input" style={{ fontSize: "0.72rem", fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: "#7d7f78" }}>
              Or Their Favorite Drama
            </label>
            <input
              id="friend-drama-input"
              type="text"
              placeholder={`e.g. ${selectedFriend.sampleDrama}`}
              value={customFriendDrama}
              onChange={(e) => setCustomFriendDrama(e.target.value)}
            />
          </div>

          <div className="fusion-genre-list">
            <span className="eyebrow" style={{ fontSize: "0.68rem", color: "#7d7f78" }}>
              Their Flavor Focus
            </span>
            {Object.entries(selectedFriend.genres).map(([genre, score]) => (
              <div key={genre} className="fusion-genre-row">
                <div className="fusion-genre-meta">
                  <span>{genre}</span>
                  <span>{Math.round(score * 100)}%</span>
                </div>
                <div className="fusion-genre-track">
                  <div
                    className="fusion-genre-fill"
                    style={{
                      width: `${Math.round(score * 100)}%`,
                      background: "#a55eea",
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Results Section: The Mathematical Intersection */}
      <section className="fusion-results-card">
        <div className="fusion-results-header">
          <div>
            <span className="eyebrow" style={{ color: "var(--coral)" }}>
              Mathematical Intersection
            </span>
            <h2>{dramas.length} Dramas You Will Both Love</h2>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <div className="fusion-shared-tropes-row">
              {sharedTropes.map((trope) => (
                <span key={trope} className="shared-trope-pill">
                  ✨ {trope}
                </span>
              ))}
            </div>

            <button
              type="button"
              className="ghost-button"
              onClick={handleCopyShare}
              style={{ display: "inline-flex", alignItems: "center", gap: 6, fontSize: "0.8rem", padding: "8px 14px", borderRadius: 10 }}
              title="Copy link to this Taste Fusion setup"
            >
              {copiedLink ? <Check size={14} color="#059669" /> : <Share2 size={14} />}
              <span>{copiedLink ? "Link Copied!" : "Share Link"}</span>
            </button>
          </div>
        </div>

        {fusionResults.isLoading ? (
          <div className="drama-grid">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="drama-skeleton" style={{ height: 380, borderRadius: 18 }} />
            ))}
          </div>
        ) : dramas.length === 0 ? (
          <div className="empty-state">
            <Sparkles size={32} style={{ color: "var(--coral)", margin: "0 auto 12px" }} />
            <h3>No Intersection Found</h3>
            <p>Try nudging the compromise slider or picking a different companion archetype.</p>
          </div>
        ) : (
          <div className="drama-grid">
            {dramas.map((drama, index) => {
              // Calculate simulated personalized match affinity for each person
              const youMatch = Math.min(98, 82 + (index % 4) * 3 + (balance > 50 ? 5 : -2));
              const friendMatch = Math.min(97, 79 + ((index + 2) % 4) * 4 + (balance < 50 ? 6 : -3));

              return (
                <div key={drama.Title} className="fusion-card-wrapper">
                  <DramaCard drama={drama} priority={index < 4} />
                  
                  {/* Why You Both Love It Bridge */}
                  <div className="fusion-card-bridge-box">
                    <span className="bridge-label">Shared Hook:</span>
                    <span>
                      Blends {drama.Genre?.split(",")[0] || "captivating drama"} with irresistible emotional tension.
                    </span>
                  </div>

                  {/* Dual Affinity Badges */}
                  <div className="fusion-dual-affinity">
                    <div className="affinity-pill-you">You: {youMatch}% Match</div>
                    <div className="affinity-pill-friend">{selectedFriend.avatar} Friend: {friendMatch}%</div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* Trailer Modal Player */}
      {activeTrailerTitle && (
        <TrailerModal
          isOpen={Boolean(activeTrailerTitle)}
          onClose={() => setActiveTrailerTitle(null)}
          dramaTitle={activeTrailerTitle}
        />
      )}
    </main>
  );
}
