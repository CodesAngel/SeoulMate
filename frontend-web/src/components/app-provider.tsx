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
  const [userId, setUserId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [watchlist, setWatchlist] = useState<Drama[]>([]);

  useEffect(() => {
    let cancelled = false;
    const hydrateBrowserState = () => {
      if (cancelled) return;
      const storedUser = localStorage.getItem("seoulmate:user") || createId("viewer");
      localStorage.setItem("seoulmate:user", storedUser);
      setUserId(storedUser);
      setSessionId(createId("session"));

      try {
        const storedList = JSON.parse(
          localStorage.getItem("seoulmate:watchlist") || "[]",
        ) as Drama[];
        setWatchlist(Array.isArray(storedList) ? storedList : []);
      } catch {
        setWatchlist([]);
      }
      setReady(true);
    };

    queueMicrotask(hydrateBrowserState);
    return () => {
      cancelled = true;
    };
  }, []);

  const isSaved = useCallback(
    (drama: Drama) => watchlist.some((item) => dramaKey(item) === dramaKey(drama)),
    [watchlist],
  );

  const toggleSaved = useCallback(
    (drama: Drama) => {
      const removing = watchlist.some((item) => dramaKey(item) === dramaKey(drama));
      const next = removing
        ? watchlist.filter((item) => dramaKey(item) !== dramaKey(drama))
        : [drama, ...watchlist];
      setWatchlist(next);
      localStorage.setItem("seoulmate:watchlist", JSON.stringify(next));

      if (userId && sessionId) {
        void logInteraction({
          userId,
          sessionId,
          dramaTitle: drama.Title,
          type: removing ? "watchlist_remove" : "watchlist_add",
        }).catch(() => undefined);
      }
    },
    [sessionId, userId, watchlist],
  );

  const value = useMemo(
    () => ({ ready, userId, sessionId, watchlist, isSaved, toggleSaved }),
    [isSaved, ready, sessionId, toggleSaved, userId, watchlist],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AppContext.Provider value={value}>{children}</AppContext.Provider>
    </QueryClientProvider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
