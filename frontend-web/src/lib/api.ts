import type {
  Drama,
  InteractionType,
  ProfileResponse,
  RecommendationResponse,
  SearchFilters,
} from "@/lib/types";
import { z } from "zod";

const stringOrNumber = z.union([z.string(), z.number()]);
const dramaSchema = z
  .object({
    Title: z.string().min(1),
    Genre: z.string().optional(),
    Description: z.string().optional(),
    "Release Years": z.string().optional(),
    rating_value: stringOrNumber.optional(),
    episodes: stringOrNumber.optional(),
    Image: z.string().optional(),
    image_url: z.string().optional(),
    image_id: z.string().optional(),
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

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001"
).replace(/\/$/, "");

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

  return response.json() as Promise<T>;
}

export function resolvePosterUrl(value?: string): string | null {
  if (!value) return null;
  if (value.startsWith("/drama-images/")) return `${API_URL}${value}`;
  return null;
}

export async function searchDramas(filters: SearchFilters, signal?: AbortSignal) {
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
  const query = aired ? `?aired=${encodeURIComponent(aired)}` : "";
  const response = await apiRequest<{ drama: Drama }>(
    `/dramas/${encodeURIComponent(title)}${query}`,
    { signal },
  );
  dramaSchema.parse(response.drama);
  return response.drama;
}

export function getProfile(userId: string, signal?: AbortSignal) {
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
  return apiRequest<{ success: boolean; message: string }>(
    `/profile/${encodeURIComponent(userId)}`,
    { method: "DELETE", signal },
  );
}

export function logInteraction(input: {
  userId: string;
  sessionId: string;
  dramaTitle: string;
  type: InteractionType;
  position?: number;
  searchId?: string;
}) {
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
