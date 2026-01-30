from alembic import op

revision = "0001_admin_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limit_buckets (
            key TEXT PRIMARY KEY,
            count INTEGER NOT NULL,
            expires_at TIMESTAMPTZ NOT NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rate_limit_buckets_expires_at ON rate_limit_buckets(expires_at)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS whatsapp_onboarding_events (
            id BIGSERIAL PRIMARY KEY,
            subdominio TEXT NOT NULL,
            event_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            details JSONB,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_whatsapp_onboarding_events_subdominio_created "
        "ON whatsapp_onboarding_events(subdominio, created_at DESC)"
    )


def downgrade() -> None:
    return
