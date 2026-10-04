import type { Drama } from "@/lib/types";

export function dramaKey(drama: Drama) {
  return `${drama.image_id || drama.Title}::${drama["Release Years"] || ""}`;
}
