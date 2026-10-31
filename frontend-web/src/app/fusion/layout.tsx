import type { Metadata } from "next";
import { NO_INDEX } from "@/lib/site";

// Personal page: kept out of search results.
export const metadata: Metadata = { title: "Watch Together", ...NO_INDEX };

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
