"""add authenticated avatar storage

Revision ID: e7b4d6a19c82
Revises: c4a91e2d6b70
Create Date: 2026-10-04
"""

from collections.abc import Sequence

from alembic import op


revision: str = "e7b4d6a19c82"
down_revision: str | Sequence[str] | None = "c4a91e2d6b70"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO storage.buckets (
            id, name, public, file_size_limit, allowed_mime_types
        )
        VALUES (
            'avatars',
            'avatars',
            true,
            2097152,
            ARRAY['image/jpeg', 'image/png', 'image/webp']
        )
        ON CONFLICT (id) DO UPDATE SET
            public = EXCLUDED.public,
            file_size_limit = EXCLUDED.file_size_limit,
            allowed_mime_types = EXCLUDED.allowed_mime_types;

        CREATE POLICY avatars_public_read
        ON storage.objects FOR SELECT
        TO public
        USING (bucket_id = 'avatars');

        CREATE POLICY avatars_owner_insert
        ON storage.objects FOR INSERT
        TO authenticated
        WITH CHECK (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
        );

        CREATE POLICY avatars_owner_update
        ON storage.objects FOR UPDATE
        TO authenticated
        USING (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
        )
        WITH CHECK (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
        );

        CREATE POLICY avatars_owner_delete
        ON storage.objects FOR DELETE
        TO authenticated
        USING (
            bucket_id = 'avatars'
            AND (storage.foldername(name))[1] = (SELECT auth.uid())::text
        );
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS avatars_owner_delete ON storage.objects")
    op.execute("DROP POLICY IF EXISTS avatars_owner_update ON storage.objects")
    op.execute("DROP POLICY IF EXISTS avatars_owner_insert ON storage.objects")
    op.execute("DROP POLICY IF EXISTS avatars_public_read ON storage.objects")
    op.execute(
        """
        DELETE FROM storage.buckets AS bucket
        WHERE bucket.id = 'avatars'
          AND NOT EXISTS (
              SELECT 1 FROM storage.objects AS object
              WHERE object.bucket_id = bucket.id
          )
        """
    )
