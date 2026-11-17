"""add episode progress, completion time and Wrapped share snapshots

Revision ID: b5e8a2c47d19
Revises: f2c84d1e9a73
Create Date: 2026-11-17
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "b5e8a2c47d19"
down_revision: str | Sequence[str] | None = "f2c84d1e9a73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Episode tracker progress (was browser-only) and the time a drama was finished.
    op.add_column(
        "watchlist_items",
        sa.Column("episodes_watched", sa.SmallInteger(), nullable=True),
    )
    op.add_column(
        "watchlist_items",
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_watchlist_items_episodes_watched",
        "watchlist_items",
        "episodes_watched IS NULL OR episodes_watched >= 0",
    )
    # Best guess for rows finished before this column existed.
    op.execute(
        "UPDATE public.watchlist_items SET completed_at = updated_at "
        "WHERE status = 'completed' AND completed_at IS NULL"
    )

    # Public Wrapped snapshots: the numbers only, never the live list.
    op.create_table(
        "wrapped_shares",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("year", sa.SmallInteger(), nullable=False),
        sa.Column(
            "show_name",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("stats_json", postgresql.JSONB(), nullable=False),
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
        sa.ForeignKeyConstraint(["user_id"], ["auth.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "year", name="uq_wrapped_shares_user_year"),
    )
    op.execute(
        """
        CREATE TRIGGER set_wrapped_shares_updated_at
        BEFORE UPDATE ON public.wrapped_shares
        FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

        -- Only the backend (database owner) reads and writes snapshots;
        -- the public REST API gets no access at all.
        ALTER TABLE public.wrapped_shares ENABLE ROW LEVEL SECURITY;
        REVOKE ALL ON TABLE public.wrapped_shares FROM anon, authenticated;
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS set_wrapped_shares_updated_at ON public.wrapped_shares"
    )
    op.drop_table("wrapped_shares")
    op.drop_constraint(
        "ck_watchlist_items_episodes_watched", "watchlist_items", type_="check"
    )
    op.drop_column("watchlist_items", "completed_at")
    op.drop_column("watchlist_items", "episodes_watched")
