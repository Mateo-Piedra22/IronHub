from alembic import op

revision = "0010_access_events_nonce"
down_revision = "0009_access_control_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE IF EXISTS public.access_events
        ADD COLUMN IF NOT EXISTS event_nonce_hash TEXT NULL
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_access_events_nonce
        ON public.access_events(device_id, event_nonce_hash)
        WHERE event_nonce_hash IS NOT NULL
        """
    )


def downgrade() -> None:
    return

