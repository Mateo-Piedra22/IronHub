from alembic import op

revision = "0006_changelog_targeting"
down_revision = "0005_support_enterprise"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.changelogs ADD COLUMN IF NOT EXISTS audience_roles JSONB NULL;")
    op.execute("ALTER TABLE public.changelogs ADD COLUMN IF NOT EXISTS audience_tenants JSONB NULL;")
    op.execute("ALTER TABLE public.changelogs ADD COLUMN IF NOT EXISTS audience_modules JSONB NULL;")
    op.execute("ALTER TABLE public.changelogs ADD COLUMN IF NOT EXISTS pinned BOOLEAN NOT NULL DEFAULT FALSE;")
    op.execute("ALTER TABLE public.changelogs ADD COLUMN IF NOT EXISTS min_app_version TEXT NULL;")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_changelogs_pinned_published_at_desc ON public.changelogs(pinned DESC, published_at DESC);"
    )


def downgrade() -> None:
    return

