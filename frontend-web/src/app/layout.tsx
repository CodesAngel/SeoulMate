import type { Metadata, Viewport } from "next";
import "./globals.css";
import { AppProvider } from "@/components/app-provider";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { AuthProvider } from "@/components/auth-provider";
import { SITE_DESCRIPTION, SITE_NAME, SITE_URL } from "@/lib/site";

const defaultTitle = "SeoulMate — Find your next K-drama";

// No canonical here: child routes would inherit it. Each page sets its own.
export const metadata: Metadata = {
  metadataBase: SITE_URL,
  title: {
    default: defaultTitle,
    template: `%s — ${SITE_NAME}`,
  },
  description: SITE_DESCRIPTION,
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: defaultTitle,
    description: SITE_DESCRIPTION,
    images: [{ url: "/og.png", width: 1200, height: 630, alt: defaultTitle }],
  },
  twitter: {
    card: "summary_large_image",
    title: defaultTitle,
    description: SITE_DESCRIPTION,
    images: ["/og.png"],
  },
  // No `robots` here: indexing is the default, and a site-wide "index" tag
  // would contradict the "noindex" that Next.js adds to 404 pages.
  ...(process.env.GOOGLE_SITE_VERIFICATION
    ? { verification: { google: process.env.GOOGLE_SITE_VERIFICATION } }
    : {}),
};

export const viewport: Viewport = {
  themeColor: "#FFFCF8",
  colorScheme: "light",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">Skip to content</a>
        <AuthProvider>
          <AppProvider>
            <SiteHeader />
            <main id="main-content">{children}</main>
            <SiteFooter />
          </AppProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
