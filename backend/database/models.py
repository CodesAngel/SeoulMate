import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Identity,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Drama(Base):
    __tablename__ = "dramas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    source_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    catalog_index: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    alternate_names: Mapped[list[str]] = mapped_column(
        ARRAY(Text), nullable=False, server_default="{}"
    )
    description: Mapped[str | None] = mapped_column(Text)
    image_id: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    poster_original_key: Mapped[str | None] = mapped_column(Text)
    poster_thumbnail_key: Mapped[str | None] = mapped_column(Text)
    publisher: Mapped[str | None] = mapped_column(Text)
    rating_value: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    rating_count: Mapped[int | None] = mapped_column(Integer)
    episodes: Mapped[int | None] = mapped_column(Integer)
    aired: Mapped[str | None] = mapped_column(Text)
    duration: Mapped[str | None] = mapped_column(Text)
    watchers: Mapped[int | None] = mapped_column(BigInteger)
    source_hash: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Genre(Base):
    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)


class DramaGenre(Base):
    __tablename__ = "drama_genres"

    drama_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dramas.id", ondelete="CASCADE"), primary_key=True
    )
    genre_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("genres.id", ondelete="CASCADE"), primary_key=True
    )


class Person(Base):
    __tablename__ = "people"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class DramaCredit(Base):
    __tablename__ = "drama_credits"
    __table_args__ = (
        CheckConstraint(
            "role IN ('actor', 'director', 'screenwriter')",
            name="ck_drama_credits_role",
        ),
    )

    drama_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dramas.id", ondelete="CASCADE"), primary_key=True
    )
    person_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("people.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(20), primary_key=True)
    billing_order: Mapped[int | None] = mapped_column(SmallInteger)


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)


class DramaKeyword(Base):
    __tablename__ = "drama_keywords"

    drama_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dramas.id", ondelete="CASCADE"), primary_key=True
    )
    keyword_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("keywords.id", ondelete="CASCADE"), primary_key=True
    )


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    display_name: Mapped[str | None] = mapped_column(String(100))
    avatar_path: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        CheckConstraint(
            "status IN ('planned', 'watching', 'completed', 'paused', 'dropped')",
            name="ck_watchlist_items_status",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drama_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dramas.id", ondelete="CASCADE"), primary_key=True
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="planned"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Rating(Base):
    __tablename__ = "ratings"
    __table_args__ = (
        CheckConstraint("rating >= 1 AND rating <= 10", name="ck_ratings_range"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    drama_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("dramas.id", ondelete="CASCADE"), primary_key=True
    )
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 1), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class UserPreference(Base):
    __tablename__ = "user_preferences"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "category", "preference_key", name="uq_user_preference"
        ),
        CheckConstraint("score >= 0 AND score <= 1", name="ck_user_preferences_score"),
    )

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    preference_key: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class SearchEvent(Base):
    __tablename__ = "search_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), index=True)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    filters: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    intent: Mapped[dict] = mapped_column(JSONB, nullable=False, server_default="{}")
    result_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class RecommendationEvent(Base):
    __tablename__ = "recommendation_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), index=True)
    query: Mapped[str | None] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(String(100), nullable=False)
    catalog_version: Mapped[str] = mapped_column(String(100), nullable=False)
    result_drama_ids: Mapped[list[int]] = mapped_column(
        ARRAY(BigInteger), nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("auth.users.id", ondelete="SET NULL"),
        index=True,
    )
    session_id: Mapped[str | None] = mapped_column(String(128), index=True)
    drama_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("dramas.id", ondelete="SET NULL"), index=True
    )
    search_event_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("search_events.id", ondelete="SET NULL")
    )
    action: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    position: Mapped[int | None] = mapped_column(Integer)
    metadata_json: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class CommunityPost(Base):
    __tablename__ = "community_posts"
    __table_args__ = (
        CheckConstraint(
            "post_type IN ('discussion', 'review', 'recommendation')",
            name="ck_community_posts_post_type",
        ),
        CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 10)",
            name="ck_community_posts_rating_range",
        ),
        CheckConstraint("length(title) <= 120", name="ck_community_posts_title_len"),
        CheckConstraint("length(body) <= 2000", name="ck_community_posts_body_len"),
        Index("ix_community_posts_type_created", "post_type", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    drama_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("dramas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    post_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    contains_spoilers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    author: Mapped["Profile"] = relationship("Profile", lazy="joined", foreign_keys=[user_id])
    drama: Mapped["Drama | None"] = relationship("Drama", lazy="joined", foreign_keys=[drama_id])
    comments: Mapped[list["CommunityComment"]] = relationship(
        "CommunityComment", back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )
    reactions: Mapped[list["CommunityReaction"]] = relationship(
        "CommunityReaction", back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )


class CommunityComment(Base):
    __tablename__ = "community_comments"
    __table_args__ = (
        CheckConstraint("length(body) <= 1000", name="ck_community_comments_body_len"),
        Index("ix_community_comments_post_created", "post_id", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        default=uuid.uuid4,
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    contains_spoilers: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    post: Mapped["CommunityPost"] = relationship("CommunityPost", back_populates="comments")
    author: Mapped["Profile"] = relationship("Profile", lazy="joined", foreign_keys=[user_id])


class CommunityReaction(Base):
    __tablename__ = "community_reactions"
    __table_args__ = (
        CheckConstraint("reaction_type = 'like'", name="ck_community_reactions_type"),
        UniqueConstraint("post_id", "user_id", "reaction_type", name="uq_community_reactions"),
        Index("ix_community_reactions_post_id", "post_id"),
    )

    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("community_posts.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profiles.id", ondelete="CASCADE"),
        primary_key=True,
    )
    reaction_type: Mapped[str] = mapped_column(
        String(20), primary_key=True, server_default="like"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    post: Mapped["CommunityPost"] = relationship("CommunityPost", back_populates="reactions")
    user: Mapped["Profile"] = relationship("Profile", lazy="joined", foreign_keys=[user_id])

