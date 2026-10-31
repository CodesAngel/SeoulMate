import type { Metadata } from "next";
import { cache } from "react";
import { JsonLd } from "@/components/json-ld";
import { getCommunityPost } from "@/lib/api";
import { absoluteUrl, metaDescription, pageMetadata } from "@/lib/site";
import type { CommunityPost } from "@/lib/types";

type Props = { params: Promise<{ postId: string }> };

// cache(): metadata and the layout share one request.
const loadPost = cache(
  (postId: string): Promise<CommunityPost | null> => getCommunityPost(postId).catch(() => null),
);

function postDescription(post: CommunityPost) {
  // Never put spoilers into search snippets.
  if (post.contains_spoilers) {
    return post.drama
      ? `A spoiler-marked discussion about ${post.drama.title} in the SeoulMate community.`
      : "A spoiler-marked K-drama discussion in the SeoulMate community.";
  }
  return metaDescription(post.body);
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const { postId } = await params;
  const post = await loadPost(postId);
  if (!post) return { title: "Community post" };
  return pageMetadata({
    title: post.title,
    description: postDescription(post),
    path: `/community/${postId}`,
  });
}

export default async function Layout({ children, params }: Props & { children: React.ReactNode }) {
  const { postId } = await params;
  const post = await loadPost(postId);
  const jsonLd = post && {
    "@context": "https://schema.org",
    "@type": "DiscussionForumPosting",
    headline: post.title,
    url: absoluteUrl(`/community/${postId}`),
    datePublished: post.created_at,
    dateModified: post.updated_at,
    author: { "@type": "Person", name: post.author.display_name || "SeoulMate member" },
    ...(post.contains_spoilers ? {} : { text: post.body }),
    interactionStatistic: [
      { "@type": "InteractionCounter", interactionType: "https://schema.org/LikeAction", userInteractionCount: post.like_count },
      { "@type": "InteractionCounter", interactionType: "https://schema.org/CommentAction", userInteractionCount: post.comment_count },
    ],
  };
  return (
    <>
      {jsonLd && <JsonLd data={jsonLd} />}
      {children}
    </>
  );
}
