import type { Metadata } from "next";
import { NO_INDEX } from "@/lib/site";

// Sign-in pages: kept out of search results.
export const metadata: Metadata = { title: "Sign in", ...NO_INDEX };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
