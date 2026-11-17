import type { Metadata } from "next";
import { NO_INDEX } from "@/lib/site";

// Personal year-in-review pages: kept out of search results. Shared snapshot
// links still get their own preview image.
export const metadata: Metadata = { title: "Wrapped", ...NO_INDEX };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
