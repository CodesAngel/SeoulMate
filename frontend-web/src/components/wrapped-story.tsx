"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  type MouseEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  Download,
  Link2,
  Lock,
  Play,
  Trash2,
  X,
} from "lucide-react";
import { useAuth } from "@/components/auth-provider";
import { PosterImage } from "@/components/poster-image";
import { WrappedShareCard } from "@/components/wrapped-share-card";
import { deleteMyWrappedShare, getMyWrapped, shareMyWrapped } from "@/lib/api";
import {
  firstAiredYear,
  hoursAsDays,
  type MyWrappedResponse,
  type WrappedDrama,
} from "@/lib/wrapped";

type Theme = "plum" | "rose" | "teal";
type Slide = { key: string; theme: Theme; body: ReactNode };

const CLOSE_HREF = "/profile";

// A slide mounts only when shown, so its posters are always on screen: load them now.
function Poster({ drama, sizes = "120px" }: { drama: WrappedDrama; sizes?: string }) {
  return (
    <div className="wr-poster">
      <PosterImage src={drama.poster_url} alt={drama.title} sizes={sizes} priority />
    </div>
  );
}

function Frame({
  year,
  theme = "plum",
  bars,
  children,
  footer,
  onClick,
}: {
  year: number;
  theme?: Theme;
  bars?: { count: number; index: number };
  children: ReactNode;
  footer?: ReactNode;
  onClick?: (event: MouseEvent<HTMLDivElement>) => void;
}) {
  return (
    <div className={`wr-story wr-theme-${theme}`} onClick={onClick}>
      <div className="wr-top">
        {bars && (
          <div
            className="wr-bars"
            style={{ gridTemplateColumns: `repeat(${bars.count}, 1fr)` }}
            aria-hidden="true"
          >
            {Array.from({ length: bars.count }, (_, i) => (
              <span key={i} className={i <= bars.index ? "done" : undefined} />
            ))}
          </div>
        )}
        <div className="wr-head">
          <span>
            <b>SeoulMate</b> Wrapped {year}
          </span>
          <Link className="wr-close" href={CLOSE_HREF} aria-label="Close Wrapped">
            <X size={15} />
          </Link>
        </div>
      </div>
      {children}
      {footer}
    </div>
  );
}

function ShareSlide({
  data,
  onReplay,
}: {
  data: MyWrappedResponse;
  onReplay: () => void;
}) {
  const { getAccessToken } = useAuth();
  const queryClient = useQueryClient();
  const [showName, setShowName] = useState(data.share?.show_name ?? true);
  const [busy, setBusy] = useState<"" | "image" | "link" | "delete">("");
  const [status, setStatus] = useState("");
  const [shareUrl, setShareUrl] = useState(
    data.share ? `/wrapped/s/${data.share.id}` : "",
  );

  const preview = useMemo(
    () => ({ ...data, display_name: showName ? data.display_name : null }),
    [data, showName],
  );

  async function token() {
    const accessToken = await getAccessToken();
    if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
    return accessToken;
  }

  async function saveImage() {
    setBusy("image");
    setStatus("");
    try {
      const response = await fetch(`/wrapped/${data.year}/card.png`, {
        headers: { Authorization: `Bearer ${await token()}` },
      });
      if (!response.ok) throw new Error("The image could not be made. Please try again.");
      const url = URL.createObjectURL(await response.blob());
      const link = document.createElement("a");
      link.href = url;
      link.download = `seoulmate-wrapped-${data.year}.png`;
      link.click();
      setTimeout(() => URL.revokeObjectURL(url), 10_000);
      setStatus("Image saved.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The image could not be saved.");
    } finally {
      setBusy("");
    }
  }

  async function copyLink() {
    setBusy("link");
    setStatus("");
    try {
      // Saves (or refreshes) the public snapshot; the link stays the same.
      const { share } = await shareMyWrapped(await token(), data.year, showName);
      const path = `/wrapped/s/${share.id}`;
      setShareUrl(path);
      const full = `${window.location.origin}${path}`;
      try {
        await navigator.clipboard.writeText(full);
        setStatus("Link copied. Anyone with it sees these numbers only.");
      } catch {
        setStatus("Link ready below. Copy it from there.");
      }
      await queryClient.invalidateQueries({ queryKey: ["wrapped", data.year] });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The link could not be made.");
    } finally {
      setBusy("");
    }
  }

  async function removeLink() {
    if (!window.confirm("Remove your public Wrapped link? People who open it will see a 'not found' page.")) {
      return;
    }
    setBusy("delete");
    setStatus("");
    try {
      await deleteMyWrappedShare(await token(), data.year);
      setShareUrl("");
      setStatus("Public link removed.");
      await queryClient.invalidateQueries({ queryKey: ["wrapped", data.year] });
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "The link could not be removed.");
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="wr-body wr-body-share">
      <p className="wr-eyebrow">Share your year</p>
      <WrappedShareCard stats={preview} />
      {data.display_name && (
        <label className="wr-check">
          <input
            type="checkbox"
            checked={showName}
            onChange={(event) => setShowName(event.target.checked)}
          />
          Show my name ({data.display_name}) on the card
        </label>
      )}
      <div className="wr-share">
        <button type="button" className="wr-btn wr-btn-main" onClick={saveImage} disabled={Boolean(busy)}>
          <Download size={15} /> {busy === "image" ? "Making image…" : "Save image"}
        </button>
        <button type="button" className="wr-btn" onClick={copyLink} disabled={Boolean(busy)}>
          <Link2 size={15} /> {busy === "link" ? "Saving…" : shareUrl ? "Update link" : "Copy link"}
        </button>
        <button type="button" className="wr-btn wr-btn-wide" onClick={onReplay}>
          <Play size={12} /> Watch again
        </button>
      </div>
      {status && (
        <p className="wr-status" role="status">
          {status}
        </p>
      )}
      {shareUrl && (
        <p className="wr-link-row">
          <Link href={shareUrl} target="_blank">
            Open your public page
          </Link>
          <button type="button" onClick={removeLink} disabled={Boolean(busy)}>
            <Trash2 size={13} /> Remove link
          </button>
        </p>
      )}
    </div>
  );
}

function buildSlides(data: MyWrappedResponse, replay: () => void): Slide[] {
  const totals = data.totals!;
  const slides: Slide[] = [];
  const mosaic = data.posters ?? [];
  // Repeat posters so a short year still fills the tilted wall.
  const wall = mosaic.length
    ? Array.from({ length: 18 }, (_, i) => mosaic[i % mosaic.length])
    : [];

  slides.push({
    key: "totals",
    theme: "plum",
    body: (
      <div className="wr-body wr-body-totals">
        <div className="wr-mosaic" aria-hidden="true">
          {wall.map((drama, i) => (
            <Poster key={`${drama.drama_id}-${i}`} drama={drama} sizes="80px" />
          ))}
        </div>
        <div className="wr-stats">
          <p className="wr-eyebrow">Your {data.year} in K-dramas</p>
          <div className="wr-stat"><b>{totals.dramas}</b><span>{totals.dramas === 1 ? "drama" : "dramas"} finished</span></div>
          <div className="wr-stat"><b>{totals.episodes}</b><span>episodes</span></div>
          <div className="wr-stat"><b>{totals.hours}</b><span>hours</span></div>
          <p className="wr-text">
            That&apos;s <b>{hoursAsDays(totals.hours)}</b> of K-dramas.
          </p>
        </div>
      </div>
    ),
  });

  const actor = data.top_actor;
  if (actor) {
    slides.push({
      key: "actor",
      theme: "plum",
      body: (
        <div className="wr-body">
          <p className="wr-eyebrow">Your most-watched actor</p>
          <h2 className="wr-big">{actor.name}</h2>
          <p className="wr-text">
            {actor.count === 1 ? (
              <>A lead in <b>one of your dramas</b> this year.</>
            ) : (
              <>A lead in <b>{actor.count} of your dramas</b> this year.</>
            )}
          </p>
          <div className="wr-posters">
            {actor.dramas.slice(0, 3).map((drama) => (
              <Poster key={drama.drama_id} drama={drama} sizes="110px" />
            ))}
          </div>
          <p className="wr-text wr-small">
            {actor.dramas.map((drama) => drama.title).join(" · ")}
            {actor.tie_with && (
              <>
                <br />
                Tied with {actor.tie_with.name} ({actor.tie_with.count});{" "}
                {actor.tie_broken_by === "ratings"
                  ? "your ratings broke the tie."
                  : "the more-watched dramas broke the tie."}
              </>
            )}
          </p>
        </div>
      ),
    });
  }

  const trope = data.top_trope;
  if (trope) {
    slides.push({
      key: "trope",
      theme: "rose",
      body: (
        <div className="wr-body">
          <p className="wr-eyebrow">Your favourite trope</p>
          <p className="wr-lead">You can&apos;t resist…</p>
          <h2 className="wr-big"><em>{trope.name}</em></h2>
          <p className="wr-text">
            It&apos;s in <b>{trope.count} of your {totals.dramas} dramas</b>, more than any other
            story tag once very common ones are weighed down.
          </p>
          {trope.others.length > 0 && (
            <>
              <p className="wr-eyebrow wr-eyebrow-soft">You also loved</p>
              <div className="wr-chips">
                {trope.others.map((other) => (
                  <span key={other.name}>{other.name} · {other.count}</span>
                ))}
              </div>
            </>
          )}
        </div>
      ),
    });
  }

  const genres = data.genres ?? [];
  if (genres.length) {
    const max = genres[0].count;
    slides.push({
      key: "genres",
      theme: "teal",
      body: (
        <div className="wr-body">
          <p className="wr-eyebrow">Your genre mix</p>
          <div className="wr-genres">
            {genres.map((genre) => (
              <div className="wr-g" key={genre.name}>
                <span>{genre.name}</span>
                <i style={{ width: `${Math.max(8, Math.round((genre.count / max) * 100))}%` }} />
                <em>{genre.count}</em>
              </div>
            ))}
          </div>
          {data.fan_type && (
            <div className="wr-type">
              <span>Your fan type</span>
              <b>{data.fan_type.name}</b>
              <span>{data.fan_type.description}</span>
            </div>
          )}
        </div>
      ),
    });
  }

  const top = data.top_rated;
  if (top) {
    const year = firstAiredYear(top.aired);
    slides.push({
      key: "top",
      theme: "plum",
      body: (
        <div className="wr-body">
          <p className="wr-eyebrow">Your top-rated drama</p>
          <div className="wr-top1">
            <Poster drama={top} sizes="160px" />
            <div>
              <div className="wr-score">
                {top.rating % 1 ? top.rating.toFixed(1) : top.rating}
                <small>/10</small>
              </div>
              <p className="wr-text">your rating</p>
            </div>
          </div>
          <h2 className="wr-big wr-big-sm">{top.title}</h2>
          <p className="wr-text">
            {[year, top.episodes ? `${top.episodes} episodes` : ""].filter(Boolean).join(" · ")}
            {" · "}the highest score you gave this year.
          </p>
        </div>
      ),
    });
  }

  slides.push({
    key: "share",
    theme: "rose",
    body: <ShareSlide data={data} onReplay={replay} />,
  });
  return slides;
}

function Unlocked({ data }: { data: MyWrappedResponse }) {
  const router = useRouter();
  const [index, setIndex] = useState(0);
  const replay = useCallback(() => setIndex(0), []);
  const slides = useMemo(() => buildSlides(data, replay), [data, replay]);
  const last = slides.length - 1;
  const current = Math.min(index, last);
  const slide = slides[current];

  const go = useCallback(
    (step: number) => setIndex((i) => Math.max(0, Math.min(last, Math.min(i, last) + step))),
    [last],
  );

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      const target = event.target as HTMLElement | null;
      if (target?.closest("input, textarea, select")) return;
      if (event.key === "ArrowRight") go(1);
      else if (event.key === "ArrowLeft") go(-1);
      else if (event.key === "Escape") router.push(CLOSE_HREF);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [go, router]);

  // Tap the left third to go back, anywhere else to go on (like stories).
  function onStoryClick(event: MouseEvent<HTMLDivElement>) {
    const target = event.target as HTMLElement;
    if (target.closest("a, button, input, label")) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const back = event.clientX < rect.left + rect.width * 0.3;
    // The share slide has no "next"; its left side still goes back (phones have no arrows).
    if (current === last && !back) return;
    go(back ? -1 : 1);
  }

  return (
    <div className="wr-page">
      <button
        type="button"
        className="wr-arrow"
        onClick={() => go(-1)}
        disabled={current === 0}
        aria-label="Previous slide"
      >
        <ChevronLeft size={20} />
      </button>

      <div className="wr-stage">
        <Frame
          year={data.year}
          theme={slide.theme}
          bars={{ count: slides.length, index: current }}
          onClick={onStoryClick}
          footer={
            current < last ? (
              <div className="wr-foot">
                <span>Tap to continue</span>
                <button type="button" className="wr-next" onClick={() => go(1)}>
                  Next <ArrowRight size={15} />
                </button>
              </div>
            ) : null
          }
        >
          <div className="wr-slide" key={slide.key} aria-live="polite">
            {slide.body}
          </div>
        </Frame>
        <p className="wr-help">Click the card or press → to go on. ← goes back. Esc closes.</p>
      </div>

      <button
        type="button"
        className="wr-arrow"
        onClick={() => go(1)}
        disabled={current === last}
        aria-label="Next slide"
      >
        <ChevronRight size={20} />
      </button>
    </div>
  );
}

function Message({
  year,
  icon,
  title,
  children,
}: {
  year: number;
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="wr-page">
      <div className="wr-stage">
        <Frame year={year}>
          <div className="wr-body wr-lock">
            {icon && <div className="wr-lock-icon">{icon}</div>}
            <p className="wr-eyebrow">Wrapped {year}</p>
            <h1 className="wr-big wr-big-sm">{title}</h1>
            {children}
          </div>
        </Frame>
      </div>
    </div>
  );
}

export function WrappedStory({ year }: { year: number }) {
  const { user, loading, getAccessToken } = useAuth();
  const query = useQuery({
    queryKey: ["wrapped", year, user?.id],
    enabled: Boolean(user),
    retry: false,
    queryFn: async ({ signal }) => {
      const accessToken = await getAccessToken();
      if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
      return getMyWrapped(accessToken, year, signal);
    },
  });

  if (loading || (user && query.isPending)) {
    return (
      <Message year={year} title="Counting your year…">
        <div className="wr-loading" aria-hidden="true"><span /><span /><span /></div>
      </Message>
    );
  }

  if (!user) {
    return (
      <Message year={year} icon={<Lock size={24} />} title="Sign in to see your Wrapped.">
        <p className="wr-text">
          Wrapped is counted from the dramas you finish and rate in your account.
        </p>
        <Link
          className="wr-next wr-cta"
          href={`/auth/login?returnUrl=${encodeURIComponent(`/wrapped/${year}`)}`}
        >
          Sign in <ArrowRight size={15} />
        </Link>
      </Message>
    );
  }

  if (query.isError || !query.data) {
    return (
      <Message year={year} title="Your Wrapped didn't load.">
        <p className="wr-text">
          {query.error instanceof Error ? query.error.message : "Please try again."}
        </p>
        <button type="button" className="wr-next wr-cta" onClick={() => query.refetch()}>
          Try again
        </button>
      </Message>
    );
  }

  const data = query.data;
  if (!data.unlocked) {
    const percent = Math.min(100, Math.round((data.finished / data.required) * 100));
    return (
      <Message
        year={year}
        icon={<Lock size={24} />}
        title={`Your Wrapped unlocks after ${data.required} finished dramas.`}
      >
        <p className="wr-text">
          You&apos;ve finished <b>{data.finished}</b> in {year}.
        </p>
        <div className="wr-meter" role="progressbar" aria-valuenow={data.finished} aria-valuemin={0} aria-valuemax={data.required}>
          <span style={{ width: `${percent}%` }} />
        </div>
        <p className="wr-text wr-small">
          Mark dramas as <b>Completed</b> in My list. Only dramas finished in {year} count.
        </p>
        <Link className="wr-next wr-cta" href="/watchlist">
          Open My list <ArrowRight size={15} />
        </Link>
      </Message>
    );
  }

  return <Unlocked data={data} />;
}
