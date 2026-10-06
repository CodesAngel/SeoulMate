"use client";

import { useState } from "react";
import { Heart } from "lucide-react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/components/auth-provider";
import { likeCommunityPost, unlikeCommunityPost } from "@/lib/api";

interface ReactionButtonProps {
  postId: string;
  initialLiked: boolean;
  initialCount: number;
  onLikedChange?: (liked: boolean, count: number) => void;
  className?: string;
  size?: number;
}

export function ReactionButton({
  postId,
  initialLiked,
  initialCount,
  onLikedChange,
  className = "",
  size = 17,
}: ReactionButtonProps) {
  const { user, getAccessToken } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const [liked, setLiked] = useState(initialLiked);
  const [count, setCount] = useState(initialCount);
  const [pending, setPending] = useState(false);

  async function handleToggle(e: React.MouseEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (!user) {
      const returnUrl = encodeURIComponent(pathname || "/community");
      router.push(`/auth/login?returnUrl=${returnUrl}`);
      return;
    }

    if (pending) return;

    // Optimistic update
    const nextLiked = !liked;
    const nextCount = nextLiked ? count + 1 : Math.max(0, count - 1);
    const prevLiked = liked;
    const prevCount = count;

    setLiked(nextLiked);
    setCount(nextCount);
    onLikedChange?.(nextLiked, nextCount);
    setPending(true);

    try {
      const token = await getAccessToken();
      if (!token) throw new Error("No authentication token available");

      if (nextLiked) {
        const res = await likeCommunityPost(postId, token);
        setCount(res.like_count);
        onLikedChange?.(true, res.like_count);
      } else {
        const res = await unlikeCommunityPost(postId, token);
        setCount(res.like_count);
        onLikedChange?.(false, res.like_count);
      }
    } catch {
      // Rollback on failure
      setLiked(prevLiked);
      setCount(prevCount);
      onLikedChange?.(prevLiked, prevCount);
    } finally {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      className={`reaction-heart-button ${liked ? "active" : ""} ${className}`}
      onClick={handleToggle}
      disabled={pending}
      aria-label={liked ? `Unlike post (${count})` : `Like post (${count})`}
      aria-pressed={liked}
    >
      <Heart
        size={size}
        fill={liked ? "currentColor" : "none"}
        className="heart-icon"
      />
      <span className="reaction-count">{count}</span>
    </button>
  );
}
