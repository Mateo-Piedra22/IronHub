from alembic import op

revision = "0011_access_ev_idx"
down_revision = "0010_access_events_nonce"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_events_device_created_at_desc
        ON public.access_events(device_id, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_events_subject_created_at_desc
        ON public.access_events(subject_usuario_id, created_at DESC)
        """
    )


def downgrade() -> None:
    return

