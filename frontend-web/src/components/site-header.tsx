"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useEffect, useState } from "react";
import { Heart, Menu, Search, UserRound, X } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { useApp } from "@/components/app-provider";
import { useAuth } from "@/components/auth-provider";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import { ThemeToggle } from "@/components/theme-toggle";

const navItems = [
  { href: "/discover", label: "Discover" },
  { href: "/watchlist", label: "My list" },
  { href: "/profile", label: "Taste profile" },
  { href: "/fusion", label: "Watch Together" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { watchlist } = useApp();
  const { user, loading: authLoading } = useAuth();
  const [query, setQuery] = useState("");
  const [menuOpenedAt, setMenuOpenedAt] = useState<string | null>(null);
  const menuOpen = menuOpenedAt === pathname;

  useEffect(() => {
    if (!menuOpen) return;
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMenuOpenedAt(null);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [menuOpen]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    router.push(`/discover?q=${encodeURIComponent(value)}`);
    setMenuOpenedAt(null);
  }

  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Link href="/" className="header-brand">
          <BrandMark />
        </Link>
        {IS_MOCK_MODE && <span className="mock-mode-badge">Mock preview</span>}

        <nav className="desktop-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname === item.href || pathname.startsWith(`${item.href}/`) ? "active" : ""}
              aria-current={pathname === item.href || pathname.startsWith(`${item.href}/`) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
        </nav>

        <form className="header-search" onSubmit={submit} role="search">
          <Search size={17} aria-hidden="true" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search a mood, actor, or story"
            aria-label="Search dramas"
          />
          <kbd aria-hidden="true">↵</kbd>
        </form>

        <div className="header-actions">
          <ThemeToggle />
          <Link href="/watchlist" className="icon-button" aria-label="My list">
            <Heart size={19} />
            {watchlist.length > 0 && <span>{watchlist.length}</span>}
          </Link>
          <Link
            href={user ? "/account" : "/auth/login"}
            className="auth-link"
            aria-label={user ? `Account for ${user.email ?? "signed-in user"}` : "Sign in"}
          >
            <UserRound size={18} />
            <span>{authLoading ? "…" : user ? "Account" : "Sign in"}</span>
          </Link>
          <button
            type="button"
            className="mobile-menu-button"
            onClick={() => setMenuOpenedAt(menuOpen ? null : pathname)}
            aria-expanded={menuOpen}
            aria-controls="mobile-navigation"
            aria-label="Toggle navigation"
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="mobile-menu" id="mobile-navigation">
          <form className="mobile-search" onSubmit={submit} role="search">
            <Search size={18} />
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="What are you in the mood for?"
              aria-label="Search dramas"
            />
          </form>
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMenuOpenedAt(null)}
              aria-current={pathname === item.href || pathname.startsWith(`${item.href}/`) ? "page" : undefined}
            >
              {item.label}
            </Link>
          ))}
          <Link
            href={user ? "/account" : "/auth/login"}
            onClick={() => setMenuOpenedAt(null)}
          >
            {user ? "Account" : "Sign in"}
          </Link>
        </div>
      )}
    </header>
  );
}
