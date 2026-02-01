from alembic import op

revision = "0007_support_tenant_settings"
down_revision = "0006_changelog_targeting"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.support_tenant_settings (
            tenant TEXT PRIMARY KEY,
            timezone TEXT NULL,
            sla_seconds JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_by TEXT NULL
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_support_tenant_settings_tenant ON public.support_tenant_settings(tenant);")


def downgrade() -> None:
    return

