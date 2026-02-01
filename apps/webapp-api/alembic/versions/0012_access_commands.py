from alembic import op

revision = "0012_access_commands"
down_revision = "0011_access_ev_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.access_commands (
            id BIGSERIAL PRIMARY KEY,
            device_id BIGINT NOT NULL REFERENCES public.access_devices(id) ON DELETE CASCADE,
            command_type TEXT NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            status TEXT NOT NULL DEFAULT 'pending',
            request_id TEXT NULL,
            actor_usuario_id BIGINT NULL REFERENCES public.usuarios(id) ON DELETE SET NULL,
            expires_at TIMESTAMP WITHOUT TIME ZONE NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            claimed_at TIMESTAMP WITHOUT TIME ZONE NULL,
            acked_at TIMESTAMP WITHOUT TIME ZONE NULL,
            result JSONB NOT NULL DEFAULT '{}'::jsonb
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_access_commands_device_status_created_at
        ON public.access_commands(device_id, status, created_at DESC)
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_access_commands_device_request_id
        ON public.access_commands(device_id, request_id)
        WHERE request_id IS NOT NULL
        """
    )


def downgrade() -> None:
    return

