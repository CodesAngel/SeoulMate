import type { Metadata } from "next";
import { NO_INDEX } from "@/lib/site";

// Post editor: kept out of search results.
export const metadata: Metadata = { title: "New post", ...NO_INDEX };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
