from alembic import op

revision = "0009_access_control_foundation"
down_revision = "0008_bulk_actions_framework"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.access_devices (
            id BIGSERIAL PRIMARY KEY,
            sucursal_id BIGINT NULL REFERENCES public.sucursales(id) ON DELETE SET NULL,
            name TEXT NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            device_public_id TEXT NOT NULL,
            token_hash TEXT NULL,
            pairing_code_hash TEXT NULL,
            pairing_expires_at TIMESTAMP WITHOUT TIME ZONE NULL,
            config JSONB NOT NULL DEFAULT '{}'::jsonb,
            last_seen_at TIMESTAMP WITHOUT TIME ZONE NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_access_devices_public_id ON public.access_devices(device_public_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_devices_sucursal_id ON public.access_devices(sucursal_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_devices_enabled ON public.access_devices(enabled)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.access_credentials (
            id BIGSERIAL PRIMARY KEY,
            usuario_id BIGINT NOT NULL REFERENCES public.usuarios(id) ON DELETE CASCADE,
            credential_type TEXT NOT NULL DEFAULT 'fob',
            credential_hash TEXT NOT NULL,
            label TEXT NULL,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_access_credentials_hash ON public.access_credentials(credential_hash)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_credentials_usuario_id ON public.access_credentials(usuario_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_credentials_active ON public.access_credentials(active)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.access_events (
            id BIGSERIAL PRIMARY KEY,
            sucursal_id BIGINT NULL REFERENCES public.sucursales(id) ON DELETE SET NULL,
            device_id BIGINT NULL REFERENCES public.access_devices(id) ON DELETE SET NULL,
            event_type TEXT NOT NULL,
            subject_usuario_id BIGINT NULL REFERENCES public.usuarios(id) ON DELETE SET NULL,
            credential_type TEXT NULL,
            credential_hint TEXT NULL,
            input_kind TEXT NULL,
            input_value_masked TEXT NULL,
            decision TEXT NOT NULL,
            reason TEXT NULL,
            unlock BOOLEAN NOT NULL DEFAULT FALSE,
            unlock_ms INTEGER NULL,
            meta JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_events_created_at_desc ON public.access_events(created_at DESC)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_events_device_id ON public.access_events(device_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_events_sucursal_id ON public.access_events(sucursal_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_access_events_subject_usuario_id ON public.access_events(subject_usuario_id)")


def downgrade() -> None:
    return

