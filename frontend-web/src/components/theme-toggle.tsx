"use client";

import { useEffect, useState } from "react";
import { Moon, Sun } from "lucide-react";

export function ThemeToggle() {
  const [theme, setTheme] = useState<"light" | "dark">("light");
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    // Check saved theme or system preference
    const saved = localStorage.getItem("seoulmate:theme") as "light" | "dark" | null;
    const initialTheme =
      saved ||
      (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");

    // eslint-disable-next-line react-hooks/set-state-in-effect
    setTheme(initialTheme);
    document.documentElement.setAttribute("data-theme", initialTheme);
    setMounted(true);
  }, []);

  function toggleTheme() {
    const nextTheme = theme === "light" ? "dark" : "light";
    setTheme(nextTheme);
    document.documentElement.setAttribute("data-theme", nextTheme);
    localStorage.setItem("seoulmate:theme", nextTheme);
  }

  if (!mounted) {
    return (
      <button
        type="button"
        className="icon-button theme-toggle-btn"
        aria-label="Toggle theme"
        disabled
      >
        <Moon size={18} />
      </button>
    );
  }

  return (
    <button
      type="button"
      className="icon-button theme-toggle-btn"
      onClick={toggleTheme}
      aria-label={`Switch to ${theme === "light" ? "Seoul Night (Dark Mode)" : "Day Paper (Light Mode)"}`}
      title={theme === "light" ? "Switch to Seoul Night (Dark Mode)" : "Switch to Day Paper (Light Mode)"}
    >
      {theme === "light" ? (
        <Moon size={18} className="theme-icon moon-icon" />
      ) : (
        <Sun size={18} className="theme-icon sun-icon" />
      )}
    </button>
  );
}
