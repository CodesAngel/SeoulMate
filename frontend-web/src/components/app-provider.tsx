"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { logInteraction } from "@/lib/api";
import type { Drama } from "@/lib/types";
import { useAuth } from "@/components/auth-provider";

type AppContextValue = {
  ready: boolean;
  userId: string;
  sessionId: string;
  watchlist: Drama[];
  isSaved: (drama: Drama) => boolean;
  toggleSaved: (drama: Drama) => void;
};

const AppContext = createContext<AppContextValue | null>(null);

function createId(prefix: string) {
  return `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 16)}`;
}

function dramaKey(drama: Drama) {
  return `${drama.Title}::${drama["Release Years"] || ""}`;
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const { user } = useAuth();
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 1000 * 60 * 5,
            retry: 1,
            refetchOnWindowFocus: false,
          },
        },
      }),
  );
  const [ready, setReady] = useState(false);
  const [anonymousUserId, setAnonymousUserId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [watchlist, setWatchlist] = useState<Drama[]>([]);
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const storedUser = localStorage.getItem("seoulmate:user") || createId("viewer");
    const storedSession =
      sessionStorage.getItem("seoulmate:session") || createId("session");
    localStorage.setItem("seoulmate:user", storedUser);
    sessionStorage.setItem("seoulmate:session", storedSession);
    // This effect intentionally hydrates state from browser-only storage after SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAnonymousUserId(storedUser);
    setSessionId(storedSession);

    try {
      const storedList = JSON.parse(
        localStorage.getItem("seoulmate:watchlist") || "[]",
      ) as Drama[];
      setWatchlist(Array.isArray(storedList) ? storedList : []);
    } catch {
      setWatchlist([]);
    }
    setReady(true);
  }, []);

  const userId = user?.id ?? anonymousUserId;

  useEffect(() => {
    if (ready) {
      localStorage.setItem("seoulmate:watchlist", JSON.stringify(watchlist));
    }
  }, [ready, watchlist]);

  useEffect(() => {
    if (!notice) return;
    const timeout = setTimeout(() => setNotice(""), 2800);
    return () => clearTimeout(timeout);
  }, [notice]);

  const isSaved = useCallback(
    (drama: Drama) => watchlist.some((item) => dramaKey(item) === dramaKey(drama)),
    [watchlist],
  );

  const toggleSaved = useCallback(
    (drama: Drama) => {
      const removing = isSaved(drama);
      setWatchlist((current) =>
        current.some((item) => dramaKey(item) === dramaKey(drama))
          ? current.filter((item) => dramaKey(item) !== dramaKey(drama))
          : [drama, ...current],
      );
      setNotice(removing ? "Removed from your list" : "Saved to your list");

      if (userId && sessionId) {
        void logInteraction({
          userId,
          sessionId,
          dramaTitle: drama.Title,
          type: removing ? "watchlist_remove" : "watchlist_add",
        }).catch(() => undefined);
      }
    },
    [isSaved, sessionId, userId],
  );

  const value = useMemo(
    () => ({ ready, userId, sessionId, watchlist, isSaved, toggleSaved }),
    [isSaved, ready, sessionId, toggleSaved, userId, watchlist],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AppContext.Provider value={value}>
        {children}
        {notice && (
          <div className="app-toast" role="status" aria-live="polite">
            {notice}
          </div>
        )}
      </AppContext.Provider>
    </QueryClientProvider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
