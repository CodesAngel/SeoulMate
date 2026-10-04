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
import { useAuth } from "@/components/auth-provider";
import {
  getMyRatings,
  getMyWatchlist,
  logInteraction,
  mergeMyWatchlist,
  removeMyWatchlistItem,
  saveMyRating,
  saveMyWatchlistItem,
} from "@/lib/api";
import type {
  Drama,
  RatingEntry,
  WatchlistEntry,
  WatchStatus,
} from "@/lib/types";

type AppContextValue = {
  ready: boolean;
  libraryError: string;
  userId: string;
  sessionId: string;
  watchlist: Drama[];
  watchlistEntries: WatchlistEntry[];
  ratingEntries: RatingEntry[];
  isSaved: (drama: Drama) => boolean;
  getWatchStatus: (drama: Drama) => WatchStatus | undefined;
  getRating: (drama: Drama) => number | undefined;
  toggleSaved: (drama: Drama) => void;
  setWatchStatus: (drama: Drama, status: WatchStatus) => void;
  saveRating: (drama: Drama, rating: number) => Promise<void>;
};

const AppContext = createContext<AppContextValue | null>(null);

function createId(prefix: string) {
  return `${prefix}_${crypto.randomUUID().replaceAll("-", "").slice(0, 16)}`;
}

function sameDrama(left: Drama, right: Drama) {
  if (left.drama_id && right.drama_id) return left.drama_id === right.drama_id;
  return `${left.Title}::${left["Release Years"] || ""}` === `${right.Title}::${right["Release Years"] || ""}`;
}

function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : "Your library could not be updated.";
}

export function AppProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading, getAccessToken } = useAuth();
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
  const [storageReady, setStorageReady] = useState(false);
  const [accountReady, setAccountReady] = useState(false);
  const [anonymousUserId, setAnonymousUserId] = useState("");
  const [sessionId, setSessionId] = useState("");
  const [guestWatchlist, setGuestWatchlist] = useState<Drama[]>([]);
  const [accountWatchlist, setAccountWatchlist] = useState<WatchlistEntry[]>([]);
  const [ratingEntries, setRatingEntries] = useState<RatingEntry[]>([]);
  const [libraryError, setLibraryError] = useState("");
  const [notice, setNotice] = useState("");

  useEffect(() => {
    const storedUser = localStorage.getItem("seoulmate:user") || createId("viewer");
    const storedSession = sessionStorage.getItem("seoulmate:session") || createId("session");
    localStorage.setItem("seoulmate:user", storedUser);
    sessionStorage.setItem("seoulmate:session", storedSession);
    // Browser storage is intentionally hydrated after SSR.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setAnonymousUserId(storedUser);
    setSessionId(storedSession);

    try {
      const storedList = JSON.parse(localStorage.getItem("seoulmate:watchlist") || "[]") as Drama[];
      setGuestWatchlist(Array.isArray(storedList) ? storedList : []);
    } catch {
      setGuestWatchlist([]);
    }
    setStorageReady(true);
  }, []);

  useEffect(() => {
    if (storageReady) {
      localStorage.setItem("seoulmate:watchlist", JSON.stringify(guestWatchlist));
    }
  }, [guestWatchlist, storageReady]);

  useEffect(() => {
    if (!storageReady || authLoading) return;
    let active = true;
    const controller = new AbortController();

    if (!user) {
      // Account rows stay private after logout; signed-out visitors see only guest saves.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setAccountWatchlist([]);
      setRatingEntries([]);
      setLibraryError("");
      setAccountReady(true);
      return () => controller.abort();
    }

    setAccountReady(false);
    setLibraryError("");
    void (async () => {
      try {
        const accessToken = await getAccessToken();
        if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
        const guestItems = guestWatchlist.flatMap((drama) =>
          drama.drama_id ? [{ drama_id: drama.drama_id, status: "planned" as const }] : [],
        );
        const [watchlistResponse, ratingsResponse] = await Promise.all([
          guestItems.length
            ? mergeMyWatchlist(accessToken, guestItems)
            : getMyWatchlist(accessToken, controller.signal),
          getMyRatings(accessToken, controller.signal),
        ]);
        if (!active) return;
        setAccountWatchlist(watchlistResponse.items);
        setRatingEntries(ratingsResponse.items);
        if (guestItems.length) {
          setGuestWatchlist([]);
          setNotice(`${guestItems.length} saved ${guestItems.length === 1 ? "drama was" : "dramas were"} added to your account`);
        }
      } catch (error) {
        if (!active || controller.signal.aborted) return;
        const message = errorMessage(error);
        setLibraryError(message);
        setNotice(message);
      } finally {
        if (active) setAccountReady(true);
      }
    })();

    return () => {
      active = false;
      controller.abort();
    };
  }, [authLoading, getAccessToken, guestWatchlist, storageReady, user]);

  useEffect(() => {
    if (!notice) return;
    const timeout = setTimeout(() => setNotice(""), 3200);
    return () => clearTimeout(timeout);
  }, [notice]);

  const userId = user?.id ?? anonymousUserId;
  const watchlistEntries = useMemo<WatchlistEntry[]>(
    () => user ? accountWatchlist : guestWatchlist.map((drama) => ({ drama, status: "planned" })),
    [accountWatchlist, guestWatchlist, user],
  );
  const watchlist = useMemo(
    () => watchlistEntries.map((entry) => entry.drama),
    [watchlistEntries],
  );
  const ready = storageReady && !authLoading && (!user || accountReady);

  const isSaved = useCallback(
    (drama: Drama) => watchlist.some((item) => sameDrama(item, drama)),
    [watchlist],
  );

  const getWatchStatus = useCallback(
    (drama: Drama) => watchlistEntries.find((entry) => sameDrama(entry.drama, drama))?.status,
    [watchlistEntries],
  );

  const getRating = useCallback(
    (drama: Drama) => ratingEntries.find((entry) => sameDrama(entry.drama, drama))?.rating,
    [ratingEntries],
  );

  const toggleSaved = useCallback(
    (drama: Drama) => {
      const removing = isSaved(drama);
      if (!user) {
        setGuestWatchlist((current) =>
          removing
            ? current.filter((item) => !sameDrama(item, drama))
            : [drama, ...current],
        );
        setNotice(removing ? "Removed from your list" : "Saved in this browser");
      } else if (!drama.drama_id) {
        setNotice("This drama is missing its catalog ID.");
        return;
      } else {
        const previous = accountWatchlist;
        setAccountWatchlist((current) =>
          removing
            ? current.filter((entry) => !sameDrama(entry.drama, drama))
            : [{ drama, status: "planned" }, ...current],
        );
        setNotice(removing ? "Removed from your account" : "Saved to your account");
        void (async () => {
          try {
            const accessToken = await getAccessToken();
            if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
            if (removing) {
              await removeMyWatchlistItem(accessToken, drama.drama_id!);
            } else {
              const response = await saveMyWatchlistItem(accessToken, drama.drama_id!, "planned");
              setAccountWatchlist((current) => [
                response.item,
                ...current.filter((entry) => !sameDrama(entry.drama, drama)),
              ]);
            }
          } catch (error) {
            setAccountWatchlist(previous);
            setNotice(errorMessage(error));
          }
        })();
      }

      if (userId && sessionId) {
        void logInteraction({
          userId,
          sessionId,
          dramaTitle: drama.Title,
          type: removing ? "watchlist_remove" : "watchlist_add",
        }).catch(() => undefined);
      }
    },
    [accountWatchlist, getAccessToken, isSaved, sessionId, user, userId],
  );

  const setWatchStatus = useCallback(
    (drama: Drama, status: WatchStatus) => {
      if (!user || !drama.drama_id) {
        setNotice("Sign in to track your viewing status.");
        return;
      }
      const previous = accountWatchlist;
      setAccountWatchlist((current) => [
        { drama, status },
        ...current.filter((entry) => !sameDrama(entry.drama, drama)),
      ]);
      void (async () => {
        try {
          const accessToken = await getAccessToken();
          if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
          const response = await saveMyWatchlistItem(accessToken, drama.drama_id!, status);
          setAccountWatchlist((current) => [
            response.item,
            ...current.filter((entry) => !sameDrama(entry.drama, drama)),
          ]);
          setNotice(`Marked ${status}`);
        } catch (error) {
          setAccountWatchlist(previous);
          setNotice(errorMessage(error));
        }
      })();
    },
    [accountWatchlist, getAccessToken, user],
  );

  const saveRating = useCallback(
    async (drama: Drama, rating: number) => {
      if (!user || !drama.drama_id) throw new Error("Sign in to save ratings.");
      const accessToken = await getAccessToken();
      if (!accessToken) throw new Error("Your session has expired. Please sign in again.");
      const response = await saveMyRating(accessToken, drama.drama_id, rating);
      setRatingEntries((current) => [
        response.item,
        ...current.filter((entry) => !sameDrama(entry.drama, drama)),
      ]);
      setAccountWatchlist((current) => [
        response.watchlist_item,
        ...current.filter((entry) => !sameDrama(entry.drama, drama)),
      ]);
      setNotice(`Rated ${rating}/10 and marked completed`);
    },
    [getAccessToken, user],
  );

  const value = useMemo(
    () => ({
      ready,
      libraryError,
      userId,
      sessionId,
      watchlist,
      watchlistEntries,
      ratingEntries,
      isSaved,
      getWatchStatus,
      getRating,
      toggleSaved,
      setWatchStatus,
      saveRating,
    }),
    [
      getRating,
      getWatchStatus,
      isSaved,
      libraryError,
      ratingEntries,
      ready,
      saveRating,
      sessionId,
      setWatchStatus,
      toggleSaved,
      userId,
      watchlist,
      watchlistEntries,
    ],
  );

  return (
    <QueryClientProvider client={queryClient}>
      <AppContext.Provider value={value}>
        {children}
        {notice && <div className="app-toast" role="status" aria-live="polite">{notice}</div>}
      </AppContext.Provider>
    </QueryClientProvider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) throw new Error("useApp must be used inside AppProvider");
  return context;
}
