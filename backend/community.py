"""Community discussions, reviews, recommendations, comments, and reactions."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from urllib.parse import quote
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import desc, func, or_, select
from sqlalchemy.orm import Session

from auth import AuthenticatedUser, optional_user, require_user
from database.models import (
    CommunityComment,
    CommunityPost,
    CommunityReaction,
    Drama,
    Profile,
)
from database.session import get_db
from database.settings import get_database_settings

PostType = Literal["discussion", "review", "recommendation"]

community_router = APIRouter(prefix="/community", tags=["Community"])


def _storage_url(object_key: str | None) -> str | None:
    if not object_key:
        return None
    base = get_database_settings().supabase_url.rstrip("/")
    encoded_key = quote(object_key, safe="/")
    return f"{base}/storage/v1/object/public/{encoded_key}"


def _clean_text(val: str) -> str:
    cleaned = " ".join(val.strip().split())
    if not cleaned:
        raise ValueError("Field cannot be empty")
    return cleaned


# ==========================================
# SCHEMAS
# ==========================================


class AuthorSummary(BaseModel):
    user_id: UUID
    display_name: str
    avatar_url: str | None = None


class DramaSummary(BaseModel):
    drama_id: int
    title: str
    poster_thumbnail_url: str | None = None
    rating_value: float | None = None
    year: str | None = None


class PostCreateRequest(BaseModel):
    post_type: PostType
    title: str = Field(min_length=1, max_length=120)
    body: str = Field(min_length=1, max_length=2000)
    drama_id: int | None = None
    rating: float | None = Field(default=None, ge=1, le=10)
    contains_spoilers: bool = False

    @field_validator("title", "body")
    @classmethod
    def validate_non_empty(cls, v: str) -> str:
        return _clean_text(v)


class PostUpdateRequest(BaseModel):
    post_type: PostType | None = None
    title: str | None = Field(default=None, min_length=1, max_length=120)
    body: str | None = Field(default=None, min_length=1, max_length=2000)
    drama_id: int | None = None
    rating: float | None = Field(default=None, ge=1, le=10)
    contains_spoilers: bool | None = None

    @field_validator("title", "body")
    @classmethod
    def validate_clean(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _clean_text(v)


class CommentCreateRequest(BaseModel):
    body: str = Field(min_length=1, max_length=1000)
    contains_spoilers: bool = False

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str) -> str:
        return _clean_text(v)


class CommentUpdateRequest(BaseModel):
    body: str | None = Field(default=None, min_length=1, max_length=1000)
    contains_spoilers: bool | None = None

    @field_validator("body")
    @classmethod
    def validate_body(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return _clean_text(v)


class CommunityCommentResponse(BaseModel):
    id: UUID
    post_id: UUID
    body: str
    contains_spoilers: bool
    created_at: datetime
    updated_at: datetime
    author: AuthorSummary
    is_author: bool = False


class CommunityPostResponse(BaseModel):
    id: UUID
    post_type: PostType
    title: str
    body: str
    rating: float | None = None
    contains_spoilers: bool
    created_at: datetime
    updated_at: datetime
    like_count: int
    comment_count: int
    author: AuthorSummary
    drama: DramaSummary | None = None
    is_liked_by_me: bool = False
    is_author: bool = False


class CommunityPostsListResponse(BaseModel):
    posts: list[CommunityPostResponse]
    total: int
    page: int
    has_more: bool


class TrendingPostItem(BaseModel):
    id: UUID
    title: str
    short_title: str
    post_type: PostType
    contains_spoilers: bool
    like_count: int
    comment_count: int
    drama_id: int | None = None
    drama_title: str | None = None
    drama_poster_thumbnail_url: str | None = None
    participant_avatars: list[str] = Field(default_factory=list)


# ==========================================
# HELPERS
# ==========================================


def calculate_trending_score(likes: int, comments: int, created_at: datetime) -> float:
    now = datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    age_seconds = max(0.0, (now - created_at).total_seconds())
    age_days = age_seconds / 86400.0
    recency_bonus = max(0.0, (7.0 - min(age_days, 7.0)) * 3.0)
    return float(likes + (comments * 2) + recency_bonus)


def serialize_author(profile: Profile | None, user_id: UUID) -> AuthorSummary:
    display_name = (
        profile.display_name if profile and profile.display_name else f"User {str(user_id)[:8]}"
    )
    avatar_url = _storage_url(profile.avatar_path) if profile else None
    return AuthorSummary(
        user_id=user_id,
        display_name=display_name,
        avatar_url=avatar_url,
    )


def serialize_drama(drama: Drama | None) -> DramaSummary | None:
    if not drama:
        return None
    thumb = _storage_url(drama.poster_thumbnail_key)
    year = drama.aired.split("-")[0].strip() if drama.aired else None
    return DramaSummary(
        drama_id=drama.id,
        title=drama.title,
        poster_thumbnail_url=thumb,
        rating_value=float(drama.rating_value) if drama.rating_value is not None else None,
        year=year,
    )


# ==========================================
# PUBLIC ENDPOINTS
# ==========================================


@community_router.get("/posts", response_model=CommunityPostsListResponse)
def list_community_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=50),
    post_type: PostType | None = Query(None),
    search: str | None = Query(None),
    drama_id: int | None = Query(None),
    sort: str = Query("trending", pattern="^(trending|recent)$"),
    user: AuthenticatedUser | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    """List community posts with filtering, search, and deterministic trending / recency sort."""
    stmt = select(CommunityPost)

    if post_type:
        stmt = stmt.where(CommunityPost.post_type == post_type)

    if drama_id:
        stmt = stmt.where(CommunityPost.drama_id == drama_id)

    if search:
        search_pattern = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                CommunityPost.title.ilike(search_pattern),
                CommunityPost.body.ilike(search_pattern),
            )
        )

    # Count total
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = db.scalar(count_stmt) or 0

    posts = db.scalars(stmt).all()

    # Pre-fetch counts and user reactions
    post_ids = [p.id for p in posts]
    likes_by_post: dict[UUID, int] = {}
    comments_by_post: dict[UUID, int] = {}
    my_likes: set[UUID] = set()

    if post_ids:
        like_counts = db.execute(
            select(CommunityReaction.post_id, func.count())
            .where(
                CommunityReaction.post_id.in_(post_ids),
                CommunityReaction.reaction_type == "like",
            )
            .group_by(CommunityReaction.post_id)
        ).all()
        for pid, cnt in like_counts:
            likes_by_post[pid] = cnt

        comment_counts = db.execute(
            select(CommunityComment.post_id, func.count())
            .where(CommunityComment.post_id.in_(post_ids))
            .group_by(CommunityComment.post_id)
        ).all()
        for pid, cnt in comment_counts:
            comments_by_post[pid] = cnt

        if user:
            liked_pids = db.scalars(
                select(CommunityReaction.post_id).where(
                    CommunityReaction.post_id.in_(post_ids),
                    CommunityReaction.user_id == user.id,
                    CommunityReaction.reaction_type == "like",
                )
            ).all()
            my_likes = set(liked_pids)

    # Sort
    if sort == "recent":
        sorted_posts = sorted(posts, key=lambda p: p.created_at, reverse=True)
    else:  # trending
        sorted_posts = sorted(
            posts,
            key=lambda p: calculate_trending_score(
                likes_by_post.get(p.id, 0),
                comments_by_post.get(p.id, 0),
                p.created_at,
            ),
            reverse=True,
        )

    # Pagination slice
    start = (page - 1) * limit
    paged_posts = sorted_posts[start : start + limit]
    has_more = (start + limit) < total

    result_items: list[CommunityPostResponse] = []
    for p in paged_posts:
        result_items.append(
            CommunityPostResponse(
                id=p.id,
                post_type=p.post_type,  # type: ignore[arg-type]
                title=p.title,
                body=p.body,
                rating=float(p.rating) if p.rating is not None else None,
                contains_spoilers=p.contains_spoilers,
                created_at=p.created_at,
                updated_at=p.updated_at,
                like_count=likes_by_post.get(p.id, 0),
                comment_count=comments_by_post.get(p.id, 0),
                author=serialize_author(p.author, p.user_id),
                drama=serialize_drama(p.drama),
                is_liked_by_me=p.id in my_likes,
                is_author=bool(user and user.id == p.user_id),
            )
        )

    return CommunityPostsListResponse(
        posts=result_items,
        total=total,
        page=page,
        has_more=has_more,
    )


@community_router.get("/trending", response_model=list[TrendingPostItem])
def get_homepage_trending(
    db: Session = Depends(get_db),
):
    """Get exactly four top trending community posts for the homepage."""
    posts = db.scalars(select(CommunityPost)).all()

    if not posts:
        return []

    post_ids = [p.id for p in posts]

    like_counts = db.execute(
        select(CommunityReaction.post_id, func.count())
        .where(
            CommunityReaction.post_id.in_(post_ids),
            CommunityReaction.reaction_type == "like",
        )
        .group_by(CommunityReaction.post_id)
    ).all()
    likes_map = {pid: cnt for pid, cnt in like_counts}

    comment_counts = db.execute(
        select(CommunityComment.post_id, func.count())
        .where(CommunityComment.post_id.in_(post_ids))
        .group_by(CommunityComment.post_id)
    ).all()
    comments_map = {pid: cnt for pid, cnt in comment_counts}

    # Fetch participant avatars for each post (up to 3 distinct avatars)
    participants_by_post: dict[UUID, list[str]] = {}
    if post_ids:
        commenter_rows = db.execute(
            select(CommunityComment.post_id, Profile.avatar_path)
            .join(Profile, Profile.id == CommunityComment.user_id, isouter=True)
            .where(CommunityComment.post_id.in_(post_ids))
            .order_by(desc(CommunityComment.created_at))
        ).all()
        for pid, av_path in commenter_rows:
            if pid not in participants_by_post:
                participants_by_post[pid] = []
            url = _storage_url(av_path)
            if url and url not in participants_by_post[pid] and len(participants_by_post[pid]) < 3:
                participants_by_post[pid].append(url)

    # Sort deterministic trending score
    ranked = sorted(
        posts,
        key=lambda p: calculate_trending_score(
            likes_map.get(p.id, 0),
            comments_map.get(p.id, 0),
            p.created_at,
        ),
        reverse=True,
    )

    top_four = ranked[:4]
    items: list[TrendingPostItem] = []
    for p in top_four:
        short_title = p.title[:45] + ("…" if len(p.title) > 45 else "")
        drama_thumb = _storage_url(p.drama.poster_thumbnail_key) if p.drama else None
        avatars = participants_by_post.get(p.id, [])
        if not avatars and p.author and p.author.avatar_path:
            author_av = _storage_url(p.author.avatar_path)
            if author_av:
                avatars.append(author_av)

        items.append(
            TrendingPostItem(
                id=p.id,
                title=p.title,
                short_title=short_title,
                post_type=p.post_type,  # type: ignore[arg-type]
                contains_spoilers=p.contains_spoilers,
                like_count=likes_map.get(p.id, 0),
                comment_count=comments_map.get(p.id, 0),
                drama_id=p.drama_id,
                drama_title=p.drama.title if p.drama else None,
                drama_poster_thumbnail_url=drama_thumb,
                participant_avatars=avatars,
            )
        )

    return items


@community_router.get("/posts/{post_id}", response_model=CommunityPostResponse)
def get_community_post(
    post_id: UUID,
    user: AuthenticatedUser | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    """Retrieve full details of a single post."""
    post = db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community post not found"
        )

    like_count = (
        db.scalar(
            select(func.count()).where(
                CommunityReaction.post_id == post_id,
                CommunityReaction.reaction_type == "like",
            )
        )
        or 0
    )

    comment_count = (
        db.scalar(select(func.count()).where(CommunityComment.post_id == post_id)) or 0
    )

    is_liked = False
    if user:
        is_liked = bool(
            db.scalar(
                select(CommunityReaction.post_id).where(
                    CommunityReaction.post_id == post_id,
                    CommunityReaction.user_id == user.id,
                    CommunityReaction.reaction_type == "like",
                )
            )
        )

    return CommunityPostResponse(
        id=post.id,
        post_type=post.post_type,  # type: ignore[arg-type]
        title=post.title,
        body=post.body,
        rating=float(post.rating) if post.rating is not None else None,
        contains_spoilers=post.contains_spoilers,
        created_at=post.created_at,
        updated_at=post.updated_at,
        like_count=like_count,
        comment_count=comment_count,
        author=serialize_author(post.author, post.user_id),
        drama=serialize_drama(post.drama),
        is_liked_by_me=is_liked,
        is_author=bool(user and user.id == post.user_id),
    )


@community_router.get(
    "/posts/{post_id}/comments", response_model=list[CommunityCommentResponse]
)
def list_post_comments(
    post_id: UUID,
    user: AuthenticatedUser | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    """List all comments for a post, ordered oldest-first."""
    comments = db.scalars(
        select(CommunityComment)
        .where(CommunityComment.post_id == post_id)
        .order_by(CommunityComment.created_at.asc())
    ).all()

    return [
        CommunityCommentResponse(
            id=c.id,
            post_id=c.post_id,
            body=c.body,
            contains_spoilers=c.contains_spoilers,
            created_at=c.created_at,
            updated_at=c.updated_at,
            author=serialize_author(c.author, c.user_id),
            is_author=bool(user and user.id == c.user_id),
        )
        for c in comments
    ]


# ==========================================
# AUTHENTICATED ENDPOINTS
# ==========================================


@community_router.post(
    "/posts", response_model=CommunityPostResponse, status_code=status.HTTP_201_CREATED
)
def create_community_post(
    payload: PostCreateRequest,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Publish a new community discussion, review, or recommendation."""
    # Validate drama if provided
    drama = None
    if payload.drama_id is not None:
        drama = db.scalar(select(Drama).where(Drama.id == payload.drama_id))
        if not drama:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drama with ID {payload.drama_id} does not exist",
            )

    post = CommunityPost(
        id=uuid.uuid4(),
        user_id=user.id,
        drama_id=payload.drama_id,
        post_type=payload.post_type,
        title=payload.title,
        body=payload.body,
        rating=Decimal(str(payload.rating)) if payload.rating is not None else None,
        contains_spoilers=payload.contains_spoilers,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    return CommunityPostResponse(
        id=post.id,
        post_type=post.post_type,  # type: ignore[arg-type]
        title=post.title,
        body=post.body,
        rating=float(post.rating) if post.rating is not None else None,
        contains_spoilers=post.contains_spoilers,
        created_at=post.created_at,
        updated_at=post.updated_at,
        like_count=0,
        comment_count=0,
        author=serialize_author(post.author, post.user_id),
        drama=serialize_drama(post.drama),
        is_liked_by_me=False,
        is_author=True,
    )


@community_router.patch("/posts/{post_id}", response_model=CommunityPostResponse)
def update_community_post(
    post_id: UUID,
    payload: PostUpdateRequest,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Update a post. Authors only."""
    post = db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community post not found"
        )

    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own posts",
        )

    if payload.post_type is not None:
        post.post_type = payload.post_type
    if payload.title is not None:
        post.title = payload.title
    if payload.body is not None:
        post.body = payload.body
    if payload.drama_id is not None:
        drama = db.scalar(select(Drama).where(Drama.id == payload.drama_id))
        if not drama:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Drama with ID {payload.drama_id} not found",
            )
        post.drama_id = payload.drama_id
    if payload.rating is not None:
        post.rating = Decimal(str(payload.rating))
    if payload.contains_spoilers is not None:
        post.contains_spoilers = payload.contains_spoilers

    db.commit()
    db.refresh(post)

    like_count = (
        db.scalar(
            select(func.count()).where(
                CommunityReaction.post_id == post_id,
                CommunityReaction.reaction_type == "like",
            )
        )
        or 0
    )
    comment_count = (
        db.scalar(select(func.count()).where(CommunityComment.post_id == post_id)) or 0
    )
    is_liked = bool(
        db.scalar(
            select(CommunityReaction.post_id).where(
                CommunityReaction.post_id == post_id,
                CommunityReaction.user_id == user.id,
                CommunityReaction.reaction_type == "like",
            )
        )
    )

    return CommunityPostResponse(
        id=post.id,
        post_type=post.post_type,  # type: ignore[arg-type]
        title=post.title,
        body=post.body,
        rating=float(post.rating) if post.rating is not None else None,
        contains_spoilers=post.contains_spoilers,
        created_at=post.created_at,
        updated_at=post.updated_at,
        like_count=like_count,
        comment_count=comment_count,
        author=serialize_author(post.author, post.user_id),
        drama=serialize_drama(post.drama),
        is_liked_by_me=is_liked,
        is_author=True,
    )


@community_router.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_community_post(
    post_id: UUID,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Delete a post. Authors only."""
    post = db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community post not found"
        )

    if post.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own posts",
        )

    db.delete(post)
    db.commit()
    return None


@community_router.post(
    "/posts/{post_id}/comments",
    response_model=CommunityCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    post_id: UUID,
    payload: CommentCreateRequest,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Add a comment to a community post."""
    post = db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community post not found"
        )

    comment = CommunityComment(
        id=uuid.uuid4(),
        post_id=post_id,
        user_id=user.id,
        body=payload.body,
        contains_spoilers=payload.contains_spoilers,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    return CommunityCommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        body=comment.body,
        contains_spoilers=comment.contains_spoilers,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=serialize_author(comment.author, comment.user_id),
        is_author=True,
    )


@community_router.patch(
    "/comments/{comment_id}", response_model=CommunityCommentResponse
)
def update_comment(
    comment_id: UUID,
    payload: CommentUpdateRequest,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Edit an existing comment. Authors only."""
    comment = db.scalar(select(CommunityComment).where(CommunityComment.id == comment_id))
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only edit your own comments",
        )

    if payload.body is not None:
        comment.body = payload.body
    if payload.contains_spoilers is not None:
        comment.contains_spoilers = payload.contains_spoilers

    db.commit()
    db.refresh(comment)

    return CommunityCommentResponse(
        id=comment.id,
        post_id=comment.post_id,
        body=comment.body,
        contains_spoilers=comment.contains_spoilers,
        created_at=comment.created_at,
        updated_at=comment.updated_at,
        author=serialize_author(comment.author, comment.user_id),
        is_author=True,
    )


@community_router.delete(
    "/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT
)
def delete_comment(
    comment_id: UUID,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Delete a comment. Authors only."""
    comment = db.scalar(select(CommunityComment).where(CommunityComment.id == comment_id))
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Comment not found"
        )

    if comment.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only delete your own comments",
        )

    db.delete(comment)
    db.commit()
    return None


@community_router.put("/posts/{post_id}/like")
def like_post(
    post_id: UUID,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Like a community post (idempotent)."""
    post = db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community post not found"
        )

    reaction = db.scalar(
        select(CommunityReaction).where(
            CommunityReaction.post_id == post_id,
            CommunityReaction.user_id == user.id,
            CommunityReaction.reaction_type == "like",
        )
    )

    if not reaction:
        reaction = CommunityReaction(
            post_id=post_id,
            user_id=user.id,
            reaction_type="like",
        )
        db.add(reaction)
        db.commit()

    like_count = (
        db.scalar(
            select(func.count()).where(
                CommunityReaction.post_id == post_id,
                CommunityReaction.reaction_type == "like",
            )
        )
        or 0
    )

    return {"success": True, "liked": True, "like_count": like_count}


@community_router.delete("/posts/{post_id}/like")
def unlike_post(
    post_id: UUID,
    user: AuthenticatedUser = Depends(require_user),
    db: Session = Depends(get_db),
):
    """Remove like from a community post (idempotent)."""
    post = db.scalar(select(CommunityPost).where(CommunityPost.id == post_id))
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Community post not found"
        )

    reaction = db.scalar(
        select(CommunityReaction).where(
            CommunityReaction.post_id == post_id,
            CommunityReaction.user_id == user.id,
            CommunityReaction.reaction_type == "like",
        )
    )

    if reaction:
        db.delete(reaction)
        db.commit()

    like_count = (
        db.scalar(
            select(func.count()).where(
                CommunityReaction.post_id == post_id,
                CommunityReaction.reaction_type == "like",
            )
        )
        or 0
    )

    return {"success": True, "liked": False, "like_count": like_count}
