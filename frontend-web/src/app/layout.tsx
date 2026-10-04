import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppProvider } from "@/components/app-provider";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

const siteUrl = new URL(
  process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
);
const description =
  "Thoughtful K-drama recommendations shaped by story, mood, and your taste.";

export const metadata: Metadata = {
  metadataBase: siteUrl,
  title: {
    default: "SeoulMate — Find your next K-drama",
    template: "%s — SeoulMate",
  },
  description,
  alternates: { canonical: "/" },
  openGraph: {
    type: "website",
    siteName: "SeoulMate",
    title: "SeoulMate — Find your next K-drama",
    description,
    url: "/",
  },
  twitter: {
    card: "summary",
    title: "SeoulMate — Find your next K-drama",
    description,
  },
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  themeColor: "#f6f2ea",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <AppProvider>
          <SiteHeader />
          <main id="main-content">{children}</main>
          <SiteFooter />
        </AppProvider>
      </body>
    </html>
  );
}
