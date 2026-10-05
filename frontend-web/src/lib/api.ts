import type {
  Drama,
  InteractionType,
  ProfileResponse,
  RecommendationResponse,
  SearchFilters,
  RatingEntry,
  WatchlistEntry,
  WatchStatus,
  AccountProfileResponse,
} from "@/lib/types";
import { z } from "zod";
import { IS_MOCK_MODE } from "@/lib/data-mode";
import * as mock from "@/lib/mock-data";

const stringOrNumber = z.union([z.string(), z.number()]);
const dramaSchema = z
  .object({
    Title: z.string().min(1),
    Genre: z.string().optional(),
    Description: z.string().optional(),
    "Release Years": z.string().optional(),
    drama_id: z.number().optional(),
    rating_value: stringOrNumber.optional(),
    episodes: stringOrNumber.optional(),
    Image: z.string().optional(),
    image_id: z.string().optional(),
    poster_original_path: z.string().optional(),
    poster_thumbnail_path: z.string().optional(),
    poster_original_url: z.string().url().optional(),
    poster_thumbnail_url: z.string().url().optional(),
    watchers: z.number().optional(),
  })
  .passthrough();
const recommendationSchema = z.object({
  query: z.object({
    Title: z.string(),
    expanded: z.string().optional(),
  }),
  recommendations: z.array(dramaSchema),
  search_id: z.string().optional(),
}).passthrough();
const watchStatusSchema = z.enum(["planned", "watching", "completed", "paused", "dropped"]);
const watchlistEntrySchema = z.object({
  drama: dramaSchema,
  status: watchStatusSchema,
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});
const ratingEntrySchema = z.object({
  drama: dramaSchema,
  rating: z.number().min(1).max(10),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
});
const accountProfileResponseSchema = z.object({
  profile: z.object({
    id: z.string().uuid(),
    display_name: z.string().nullable(),
    avatar_path: z.string().nullable(),
    avatar_url: z.string().url().nullable(),
    created_at: z.string(),
    updated_at: z.string(),
  }),
  statistics: z.object({
    saved_total: z.number().int().nonnegative(),
    active_total: z.number().int().nonnegative(),
    planned: z.number().int().nonnegative(),
    watching: z.number().int().nonnegative(),
    completed: z.number().int().nonnegative(),
    paused: z.number().int().nonnegative(),
    dropped: z.number().int().nonnegative(),
    ratings_total: z.number().int().nonnegative(),
    average_rating: z.number().nullable(),
  }),
});

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001"
).replace(/\/$/, "");
const SUPABASE_URL = (
  process.env.NEXT_PUBLIC_SUPABASE_URL ?? "http://127.0.0.1:54321"
).replace(/\/$/, "");
const POSTER_STORAGE_PREFIX = `${SUPABASE_URL}/storage/v1/object/public/drama-posters/`;

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly detail?: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function apiRequest<T>(
  path: string,
  init?: RequestInit,
  timeoutMs = 10_000,
): Promise<T> {
  const controller = new AbortController();
  const sourceSignal = init?.signal;
  const forwardAbort = () => controller.abort(sourceSignal?.reason);
  if (sourceSignal?.aborted) forwardAbort();
  else sourceSignal?.addEventListener("abort", forwardAbort, { once: true });
  const timeout = setTimeout(
    () => controller.abort(new DOMException("Request timed out", "TimeoutError")),
    timeoutMs,
  );

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...init?.headers,
      },
    });
  } catch (error) {
    if (controller.signal.aborted && !sourceSignal?.aborted) {
      throw new ApiError("The request timed out. Please try again.", 408);
    }
    throw error;
  } finally {
    clearTimeout(timeout);
    sourceSignal?.removeEventListener("abort", forwardAbort);
  }

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the status-based message for non-JSON errors.
    }
    throw new ApiError(message, response.status, message);
  }

  if (response.status === 204) return undefined as T;

  return response.json() as Promise<T>;
}

function bearerHeaders(accessToken: string) {
  return { Authorization: `Bearer ${accessToken}` };
}

export function resolvePosterUrl(value?: string): string | null {
  if (!value) return null;
  if (IS_MOCK_MODE && value.startsWith("/mock-posters/")) return value;
  return value.startsWith(POSTER_STORAGE_PREFIX) ? value : null;
}

export async function searchDramas(filters: SearchFilters, signal?: AbortSignal) {
  if (IS_MOCK_MODE) return mock.mockSearch(filters, signal);
  const params = new URLSearchParams({
    title: filters.query,
    top_n: String(filters.topN ?? 12),
  });

  if (filters.genre) params.set("genre", filters.genre);
  if (filters.year) params.set("year", filters.year);
  if (filters.minRating) params.set("rating_value", filters.minRating);
  if (filters.sortBy) params.set("sort_by", filters.sortBy);
  if (filters.sortOrder) params.set("sort_order", filters.sortOrder);
  if (filters.similarTo) params.set("similar_to", filters.similarTo);
  if (filters.refresh) params.set("refresh", String(filters.refresh));
  if (filters.userId) params.set("user_id", filters.userId);
  if (filters.sessionId) params.set("session_id", filters.sessionId);

  const response = await apiRequest<RecommendationResponse>(`/recommend?${params}`, { signal });
  recommendationSchema.parse(response);
  return response;
}

export async function getDrama(title: string, aired?: string, signal?: AbortSignal) {
  if (IS_MOCK_MODE) return mock.mockGetDrama(title, signal);
  const query = aired ? `?aired=${encodeURIComponent(aired)}` : "";
  const response = await apiRequest<{ drama: Drama }>(
    `/dramas/${encodeURIComponent(title)}${query}`,
    { signal },
  );
  dramaSchema.parse(response.drama);
  return response.drama;
}

export function getProfile(userId: string, signal?: AbortSignal) {
  if (IS_MOCK_MODE) return mock.mockGetProfile(userId, signal);
  return apiRequest<ProfileResponse>(`/profile/${encodeURIComponent(userId)}`, {
    signal,
  });
}

export function rateDrama(
  userId: string,
  dramaTitle: string,
  rating: number,
  signal?: AbortSignal,
) {
  if (IS_MOCK_MODE) return mock.mockRateLegacy();
  const params = new URLSearchParams({
    drama_title: dramaTitle,
    rating: String(rating),
  });
  return apiRequest<{ success: boolean; message: string }>(
    `/profile/${encodeURIComponent(userId)}/rate?${params}`,
    { method: "POST", signal },
  );
}

export function resetProfile(userId: string, signal?: AbortSignal) {
  if (IS_MOCK_MODE) return mock.mockResetProfile();
  return apiRequest<{ success: boolean; message: string }>(
    `/profile/${encodeURIComponent(userId)}`,
    { method: "DELETE", signal },
  );
}

export async function getMyAccountProfile(
  accessToken: string,
  signal?: AbortSignal,
): Promise<AccountProfileResponse> {
  if (IS_MOCK_MODE) return mock.mockGetAccount(signal);
  const response = await apiRequest<AccountProfileResponse>("/me/profile", {
    headers: bearerHeaders(accessToken),
    signal,
  });
  return accountProfileResponseSchema.parse(response);
}

export async function updateMyAccountProfile(
  accessToken: string,
  update: { display_name?: string; avatar_path?: string | null },
): Promise<AccountProfileResponse> {
  if (IS_MOCK_MODE) return mock.mockUpdateAccount(update);
  const response = await apiRequest<AccountProfileResponse>("/me/profile", {
    method: "PATCH",
    headers: bearerHeaders(accessToken),
    body: JSON.stringify(update),
  });
  return accountProfileResponseSchema.parse(response);
}

export function deleteMyAccount(accessToken: string) {
  if (IS_MOCK_MODE) return mock.mockDeleteAccount();
  return apiRequest<void>("/me/account", {
    method: "DELETE",
    headers: bearerHeaders(accessToken),
  });
}

export async function getMyWatchlist(accessToken: string, signal?: AbortSignal) {
  if (IS_MOCK_MODE) return mock.mockGetWatchlist(signal);
  const response = await apiRequest<{ items: WatchlistEntry[] }>("/me/watchlist", {
    headers: bearerHeaders(accessToken),
    signal,
  });
  return { items: z.array(watchlistEntrySchema).parse(response.items) };
}

export async function mergeMyWatchlist(
  accessToken: string,
  items: Array<{ drama_id: number; status: WatchStatus }>,
) {
  if (IS_MOCK_MODE) return mock.mockMergeWatchlist(items);
  const response = await apiRequest<{ items: WatchlistEntry[] }>("/me/watchlist/merge", {
    method: "POST",
    headers: bearerHeaders(accessToken),
    body: JSON.stringify({ items }),
  });
  return { items: z.array(watchlistEntrySchema).parse(response.items) };
}

export async function saveMyWatchlistItem(
  accessToken: string,
  dramaId: number,
  status: WatchStatus,
) {
  if (IS_MOCK_MODE) return mock.mockSaveWatchlistItem(dramaId, status);
  const response = await apiRequest<{ item: WatchlistEntry }>(`/me/watchlist/${dramaId}`, {
    method: "PUT",
    headers: bearerHeaders(accessToken),
    body: JSON.stringify({ status }),
  });
  return { item: watchlistEntrySchema.parse(response.item) };
}

export function removeMyWatchlistItem(accessToken: string, dramaId: number) {
  if (IS_MOCK_MODE) return mock.mockRemoveWatchlistItem(dramaId);
  return apiRequest<void>(`/me/watchlist/${dramaId}`, {
    method: "DELETE",
    headers: bearerHeaders(accessToken),
  });
}

export async function getMyRatings(accessToken: string, signal?: AbortSignal) {
  if (IS_MOCK_MODE) return mock.mockGetRatings(signal);
  const response = await apiRequest<{ items: RatingEntry[] }>("/me/ratings", {
    headers: bearerHeaders(accessToken),
    signal,
  });
  return { items: z.array(ratingEntrySchema).parse(response.items) };
}

export async function saveMyRating(
  accessToken: string,
  dramaId: number,
  rating: number,
) {
  if (IS_MOCK_MODE) return mock.mockSaveRating(dramaId, rating);
  const response = await apiRequest<{
    item: RatingEntry;
    watchlist_item: WatchlistEntry;
  }>(`/me/ratings/${dramaId}`, {
    method: "PUT",
    headers: bearerHeaders(accessToken),
    body: JSON.stringify({ rating }),
  });
  return {
    item: ratingEntrySchema.parse(response.item),
    watchlist_item: watchlistEntrySchema.parse(response.watchlist_item),
  };
}

export function logInteraction(input: {
  userId: string;
  sessionId: string;
  dramaTitle: string;
  type: InteractionType;
  position?: number;
  searchId?: string;
}) {
  if (IS_MOCK_MODE) return Promise.resolve({ status: "mocked" });
  return apiRequest<{ status: string }>("/analytics/interaction", {
    method: "POST",
    keepalive: true,
    body: JSON.stringify({
      user_id: input.userId,
      session_id: input.sessionId,
      search_id: input.searchId,
      drama_title: input.dramaTitle,
      interaction_type: input.type,
      position: input.position,
    }),
  });
}
