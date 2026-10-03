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
      </div>
    </footer>
  );
}
