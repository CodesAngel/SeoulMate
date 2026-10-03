"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { Heart, Menu, Search, UserRound, X } from "lucide-react";
import { BrandMark } from "@/components/brand-mark";
import { useApp } from "@/components/app-provider";

const navItems = [
  { href: "/discover", label: "Discover" },
  { href: "/watchlist", label: "My list" },
  { href: "/profile", label: "Taste profile" },
];

export function SiteHeader() {
  const pathname = usePathname();
  const router = useRouter();
  const { watchlist } = useApp();
  const [query, setQuery] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = query.trim();
    if (!value) return;
    router.push(`/discover?q=${encodeURIComponent(value)}`);
    setMenuOpen(false);
  }

  return (
    <header className="site-header">
      <div className="shell header-inner">
        <Link href="/" className="header-brand">
          <BrandMark />
        </Link>

        <nav className="desktop-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className={pathname.startsWith(item.href) ? "active" : ""}
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
          <kbd>↵</kbd>
        </form>

        <div className="header-actions">
          <Link href="/watchlist" className="icon-button" aria-label="My list">
            <Heart size={19} />
            {watchlist.length > 0 && <span>{watchlist.length}</span>}
          </Link>
          <Link href="/profile" className="avatar-button" aria-label="Taste profile">
            <UserRound size={18} />
          </Link>
          <button
            className="mobile-menu-button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-expanded={menuOpen}
            aria-label="Toggle navigation"
          >
            {menuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {menuOpen && (
        <div className="mobile-menu">
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
            <Link key={item.href} href={item.href} onClick={() => setMenuOpen(false)}>
              {item.label}
            </Link>
          ))}
        </div>
      )}
    </header>
  );
}
