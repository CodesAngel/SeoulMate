# Community system

SeoulMate includes a spoiler-safe K-drama community where visitors can read discussions, reviews, and recommendations, and signed-in members can share insights and join conversations. This is Phase 1 (the MVP). To try it locally, see [Test the community system](QUICKSTART.md#test-the-community-system-phase-1).

## Routes

| Route | Purpose | Access |
| --- | --- | --- |
| `/community` | Feed with Trending, Recent, Reviews, Recommendations tabs, search, and drama filtering | Public read |
| `/community/new` | Post composer for discussions, reviews (with 1–10 scores), and recommendations linked to dramas | Authenticated |
| `/community/[postId]` | Complete post detail, full markdown/body, associated drama links, reaction heart, and comments | Public read, authenticated comments |
| `/community/edit/[postId]` | Post editor for authors to update their title, body, spoiler flag, and review rating | Post author only |

## Homepage sections

- **Trending in the community**: four engagement-ranked posts placed after the statistics strip and before "Start with these", showing drama thumbnails, short titles, post type badges, spoiler tags, comment/like counts, and participant avatars.
- **From the community**: three recent community posts placed after the mood section, showing author avatars, relative post timestamps, drama poster banners, like buttons, comment links, and a "Join the conversation" CTA.

## Database and security

The schema is managed by the Alembic migration `backend/migrations/versions/f2c84d1e9a73_add_community_system.py`:

- `community_posts`: UUID primary key, `user_id` referencing `profiles(id)` (CASCADE), nullable `drama_id` referencing `dramas(id)` (SET NULL), post type (`discussion`, `review`, `recommendation`), title (max 120 chars), body (max 2,000 chars), rating (1.0–10.0), `contains_spoilers` boolean, timestamps with triggers.
- `community_comments`: UUID primary key, `post_id` (CASCADE), `user_id` (CASCADE), body (max 1,000 chars), `contains_spoilers` boolean, timestamps.
- `community_reactions`: `post_id` (CASCADE), `user_id` (CASCADE), `reaction_type` (`like`), unique constraint on `(post_id, user_id, reaction_type)`.
- Row Level Security (RLS) is enabled on all community tables: anonymous users have read-only access; authenticated members can only create content under their own identity, edit/delete their own posts and comments, and add/remove their own reactions.

## API endpoints

**Public:**

- `GET /community/posts`: list posts with cursor/page pagination, post-type filtering, search query, drama filter, and trending or recent sorting.
- `GET /community/posts/{post_id}`: one post with drama details, author profile, reaction counts, and author permissions.
- `GET /community/posts/{post_id}/comments`: comments, oldest first.
- `GET /community/trending`: the top 4 posts by trending score.

**Authenticated:**

- `POST /community/posts`: create a discussion, review, or recommendation (201 Created).
- `PATCH /community/posts/{post_id}`: edit the title, body, rating, or spoiler flag (author only).
- `DELETE /community/posts/{post_id}`: delete a post and cascade its reactions and comments (204 No Content, author only).
- `POST /community/posts/{post_id}/comments`: post a comment (201 Created).
- `PATCH /community/comments/{comment_id}`: edit a comment's body or spoiler flag (author only).
- `DELETE /community/comments/{comment_id}`: delete a comment (204 No Content, author only).
- `PUT /community/posts/{post_id}/like`: like a post (idempotent).
- `DELETE /community/posts/{post_id}/like`: remove the like.

## Trending formula

Trending is deterministic, with no ML model or background worker:

$$\text{Trending Score} = \text{Likes} + (\text{Comments} \times 2) + \text{Recency Bonus}$$

The recency bonus gives up to 21 points to posts active within the last 7 days: $\max(0, 7 - \text{age}_{\text{days}}) \times 3$.

## Spoilers

Any post or comment marked `contains_spoilers: true` starts masked behind a "Contains spoilers — Reveal" guard. Previews in the homepage sections, feed cards, search results, and page metadata never show unmasked spoiler text. Content is revealed only when the visitor clicks "Reveal".

## Mock mode

Run `.\scripts\run_web_frontend.ps1 -Mode mock` to use the community without PostgreSQL, Docker, or FastAPI. Mock mode provides 8+ community posts (including the 4 trending and 3 homepage items), multi-user comments, spoiler guards, and in-memory create, edit, delete and like actions that reset when the dev server restarts.

## Not in Phase 1

Left for later phases:

- Nested comment threads and replies
- Follows and direct messages
- Image or media uploads in posts
- Reactions other than "like"
- Real-time push notifications (WebSockets)
- Moderation dashboards
