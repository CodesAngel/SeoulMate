import Link from "next/link";
import { BrandMark } from "@/components/brand-mark";

export function SiteFooter() {
  return (
    <footer className="site-footer">
      <div className="shell footer-grid">
        <div>
          <BrandMark />
          <p>Your thoughtful guide to the next story you will love.</p>
        </div>
        <div className="footer-links">
          <Link href="/discover">Discover</Link>
          <Link href="/watchlist">My list</Link>
          <Link href="/profile">Taste profile</Link>
        </div>
        <p className="footer-note">Recommendations shaped by story, mood, and you.</p>
        <p className="footer-credit">
          <a href="https://www.themoviedb.org" target="_blank" rel="noopener noreferrer">
            {/* Official TMDB logo, unmodified (TMDB attribution rules). */}
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/tmdb-logo.svg" alt="TMDB" width={78} height={10} />
          </a>
          <span>This product uses the TMDB API but is not endorsed or certified by TMDB.</span>
        </p>
      </div>
    </footer>
  );
}
