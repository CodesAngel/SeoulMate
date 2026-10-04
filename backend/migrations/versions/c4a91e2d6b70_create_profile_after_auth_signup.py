"""create a public profile after an auth signup

Revision ID: c4a91e2d6b70
Revises: 8c1f2a7b9d34
Create Date: 2026-10-04
"""

from collections.abc import Sequence

from alembic import op


revision: str = "c4a91e2d6b70"
down_revision: str | Sequence[str] | None = "8c1f2a7b9d34"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION public.handle_new_auth_user()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = ''
        AS $$
        BEGIN
            INSERT INTO public.profiles (id, display_name)
            VALUES (
                NEW.id,
                COALESCE(
                    NULLIF(NEW.raw_user_meta_data ->> 'display_name', ''),
                    NULLIF(split_part(NEW.email, '@', 1), '')
                )
            )
            ON CONFLICT (id) DO NOTHING;
            RETURN NEW;
        END;
        $$;

        REVOKE ALL ON FUNCTION public.handle_new_auth_user() FROM PUBLIC;

        CREATE TRIGGER on_auth_user_created
        AFTER INSERT ON auth.users
        FOR EACH ROW EXECUTE FUNCTION public.handle_new_auth_user();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users")
    op.execute("DROP FUNCTION IF EXISTS public.handle_new_auth_user()")
