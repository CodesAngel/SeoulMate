"""add community posts, comments, and reactions schema with RLS

Revision ID: f2c84d1e9a73
Revises: e7b4d6a19c82
Create Date: 2026-10-06
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "f2c84d1e9a73"
down_revision: str | Sequence[str] | None = "e7b4d6a19c82"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. community_posts
    op.create_table(
        "community_posts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("drama_id", sa.BigInteger(), nullable=True),
        sa.Column("post_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("rating", sa.Numeric(precision=3, scale=1), nullable=True),
        sa.Column(
            "contains_spoilers",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "post_type IN ('discussion', 'review', 'recommendation')",
            name="ck_community_posts_post_type",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR (rating >= 1 AND rating <= 10)",
            name="ck_community_posts_rating_range",
        ),
        sa.CheckConstraint(
            "length(title) <= 120",
            name="ck_community_posts_title_len",
        ),
        sa.CheckConstraint(
            "length(body) <= 2000",
            name="ck_community_posts_body_len",
        ),
        sa.ForeignKeyConstraint(
            ["drama_id"],
            ["dramas.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_community_posts_created_at",
        "community_posts",
        ["created_at"],
    )
    op.create_index(
        "ix_community_posts_type_created",
        "community_posts",
        ["post_type", "created_at"],
    )
    op.create_index(
        "ix_community_posts_drama_id",
        "community_posts",
        ["drama_id"],
    )

    # 2. community_comments
    op.create_table(
        "community_comments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "contains_spoilers",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(body) <= 1000",
            name="ck_community_comments_body_len",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_community_comments_post_created",
        "community_comments",
        ["post_id", "created_at"],
    )

    # 3. community_reactions
    op.create_table(
        "community_reactions",
        sa.Column("post_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "reaction_type",
            sa.String(length=20),
            server_default=sa.text("'like'"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "reaction_type = 'like'",
            name="ck_community_reactions_type",
        ),
        sa.ForeignKeyConstraint(
            ["post_id"],
            ["community_posts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["profiles.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("post_id", "user_id", "reaction_type"),
        sa.UniqueConstraint("post_id", "user_id", "reaction_type", name="uq_community_reactions"),
    )

    op.create_index(
        "ix_community_reactions_post_id",
        "community_reactions",
        ["post_id"],
    )

    # Updated_at Triggers
    op.execute(
        """
        CREATE TRIGGER set_community_posts_updated_at
        BEFORE UPDATE ON public.community_posts
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

        CREATE TRIGGER set_community_comments_updated_at
        BEFORE UPDATE ON public.community_comments
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
        """
    )

    # Row Level Security
    op.execute(
        """
        -- Allow anonymous read on profiles display name & avatar
        GRANT SELECT (id, display_name, avatar_path, created_at, updated_at) ON TABLE public.profiles TO anon;
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies WHERE tablename = 'profiles' AND policyname = 'profiles_public_read'
            ) THEN
                CREATE POLICY profiles_public_read
                ON public.profiles FOR SELECT
                TO anon
                USING (true);
            END IF;
        END $$;

        -- community_posts RLS
        ALTER TABLE public.community_posts ENABLE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE public.community_posts FROM anon, authenticated;
        GRANT SELECT ON TABLE public.community_posts TO anon, authenticated;
        GRANT INSERT, UPDATE, DELETE ON TABLE public.community_posts TO authenticated;

        CREATE POLICY community_posts_public_read
        ON public.community_posts FOR SELECT
        TO anon, authenticated
        USING (true);

        CREATE POLICY community_posts_owner_insert
        ON public.community_posts FOR INSERT
        TO authenticated
        WITH CHECK ((SELECT auth.uid()) = user_id);

        CREATE POLICY community_posts_owner_update
        ON public.community_posts FOR UPDATE
        TO authenticated
        USING ((SELECT auth.uid()) = user_id)
        WITH CHECK ((SELECT auth.uid()) = user_id);

        CREATE POLICY community_posts_owner_delete
        ON public.community_posts FOR DELETE
        TO authenticated
        USING ((SELECT auth.uid()) = user_id);

        -- community_comments RLS
        ALTER TABLE public.community_comments ENABLE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE public.community_comments FROM anon, authenticated;
        GRANT SELECT ON TABLE public.community_comments TO anon, authenticated;
        GRANT INSERT, UPDATE, DELETE ON TABLE public.community_comments TO authenticated;

        CREATE POLICY community_comments_public_read
        ON public.community_comments FOR SELECT
        TO anon, authenticated
        USING (true);

        CREATE POLICY community_comments_owner_insert
        ON public.community_comments FOR INSERT
        TO authenticated
        WITH CHECK ((SELECT auth.uid()) = user_id);

        CREATE POLICY community_comments_owner_update
        ON public.community_comments FOR UPDATE
        TO authenticated
        USING ((SELECT auth.uid()) = user_id)
        WITH CHECK ((SELECT auth.uid()) = user_id);

        CREATE POLICY community_comments_owner_delete
        ON public.community_comments FOR DELETE
        TO authenticated
        USING ((SELECT auth.uid()) = user_id);

        -- community_reactions RLS
        ALTER TABLE public.community_reactions ENABLE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE public.community_reactions FROM anon, authenticated;
        GRANT SELECT ON TABLE public.community_reactions TO anon, authenticated;
        GRANT INSERT, DELETE ON TABLE public.community_reactions TO authenticated;

        CREATE POLICY community_reactions_public_read
        ON public.community_reactions FOR SELECT
        TO anon, authenticated
        USING (true);

        CREATE POLICY community_reactions_owner_insert
        ON public.community_reactions FOR INSERT
        TO authenticated
        WITH CHECK ((SELECT auth.uid()) = user_id);

        CREATE POLICY community_reactions_owner_delete
        ON public.community_reactions FOR DELETE
        TO authenticated
        USING ((SELECT auth.uid()) = user_id);
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DROP POLICY IF EXISTS community_reactions_owner_delete ON public.community_reactions;
        DROP POLICY IF EXISTS community_reactions_owner_insert ON public.community_reactions;
        DROP POLICY IF EXISTS community_reactions_public_read ON public.community_reactions;
        DROP POLICY IF EXISTS community_comments_owner_delete ON public.community_comments;
        DROP POLICY IF EXISTS community_comments_owner_update ON public.community_comments;
        DROP POLICY IF EXISTS community_comments_owner_insert ON public.community_comments;
        DROP POLICY IF EXISTS community_comments_public_read ON public.community_comments;
        DROP POLICY IF EXISTS community_posts_owner_delete ON public.community_posts;
        DROP POLICY IF EXISTS community_posts_owner_update ON public.community_posts;
        DROP POLICY IF EXISTS community_posts_owner_insert ON public.community_posts;
        DROP POLICY IF EXISTS community_posts_public_read ON public.community_posts;
        DROP POLICY IF EXISTS profiles_public_read ON public.profiles;

        DROP TRIGGER IF EXISTS set_community_comments_updated_at ON public.community_comments;
        DROP TRIGGER IF EXISTS set_community_posts_updated_at ON public.community_posts;
        """
    )

    op.drop_table("community_reactions")
    op.drop_table("community_comments")
    op.drop_table("community_posts")
