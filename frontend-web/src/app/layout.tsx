import type { Metadata } from "next";
import "./globals.css";
import { AppProvider } from "@/components/app-provider";
import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: {
    default: "SeoulMate — Find your next K-drama",
    template: "%s — SeoulMate",
  },
  description:
    "Thoughtful K-drama recommendations shaped by story, mood, and your taste.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppProvider>
          <SiteHeader />
          <main>{children}</main>
          <SiteFooter />
        </AppProvider>
      </body>
    </html>
  );
}
