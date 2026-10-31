import type { Metadata } from "next";
import { pageMetadata } from "@/lib/site";

export const metadata: Metadata = pageMetadata({
  title: "Discover K-dramas by mood, actor or story",
  description:
    "Search 2,130 Korean dramas in plain words: a mood, a trope, an actor or a drama you loved. SeoulMate finds the stories that match.",
  path: "/discover",
});

export default function Layout({ children }: { children: React.ReactNode }) {
  return children;
}
