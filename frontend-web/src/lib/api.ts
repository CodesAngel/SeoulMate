import type {
  Drama,
  InteractionType,
  ProfileResponse,
  RecommendationResponse,
  SearchFilters,
} from "@/lib/types";
import { z } from "zod";

const dramaIdentitySchema = z.object({ Title: z.string().min(1) });
const recommendationIdentitySchema = z.object({
  recommendations: z.array(dramaIdentitySchema),
});

export const API_URL = (
  process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8001"
).replace(/\/$/, "");

async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });

  if (!response.ok) {
    let message = `Request failed (${response.status})`;
    try {
      const body = (await response.json()) as { detail?: string };
      if (body.detail) message = body.detail;
    } catch {
      // Keep the status-based message for non-JSON errors.
    }
    throw new Error(message);
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
  recommendationIdentitySchema.parse(response);
  return response;
}

export async function getDrama(title: string, aired?: string) {
  const query = aired ? `?aired=${encodeURIComponent(aired)}` : "";
  const response = await apiRequest<{ drama: Drama }>(
    `/dramas/${encodeURIComponent(title)}${query}`,
  );
  dramaIdentitySchema.parse(response.drama);
  return response.drama;
}

export function getProfile(userId: string) {
  return apiRequest<ProfileResponse>(`/profile/${encodeURIComponent(userId)}`);
}

export function rateDrama(userId: string, dramaTitle: string, rating: number) {
  const params = new URLSearchParams({
    drama_title: dramaTitle,
    rating: String(rating),
  });
  return apiRequest<{ success: boolean; message: string }>(
    `/profile/${encodeURIComponent(userId)}/rate?${params}`,
    { method: "POST" },
  );
}

export function resetProfile(userId: string) {
  return apiRequest<{ success: boolean; message: string }>(
    `/profile/${encodeURIComponent(userId)}`,
    { method: "DELETE" },
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
