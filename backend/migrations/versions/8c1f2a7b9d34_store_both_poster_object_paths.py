"""Store both poster object paths.

Revision ID: 8c1f2a7b9d34
Revises: 0039fdbaddf3
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = "8c1f2a7b9d34"
down_revision: str | Sequence[str] | None = "0039fdbaddf3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("dramas", "poster_key", new_column_name="poster_original_key")
    op.add_column("dramas", sa.Column("poster_thumbnail_key", sa.Text(), nullable=True))
    op.execute(
        """
        UPDATE dramas
        SET poster_original_key = 'dramas/' || id || '/original.jpg',
            poster_thumbnail_key = 'dramas/' || id || '/thumbnail.webp'
        """
    )


def downgrade() -> None:
    op.drop_column("dramas", "poster_thumbnail_key")
    op.alter_column(
        "dramas", "poster_original_key", new_column_name="poster_key"
    )
