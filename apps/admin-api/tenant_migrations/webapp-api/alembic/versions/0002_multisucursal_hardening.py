from alembic import op

revision = "0002_multisucursal_hardening"
down_revision = "0001_tenant_schema_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkin_station_tokens (
            id BIGSERIAL PRIMARY KEY,
            gym_id BIGINT NOT NULL DEFAULT 0,
            sucursal_id BIGINT NULL REFERENCES sucursales(id) ON DELETE SET NULL,
            token VARCHAR(64) NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
            used_by BIGINT NULL,
            used_at TIMESTAMP WITHOUT TIME ZONE NULL
        );
        """
    )
    op.execute(
        "ALTER TABLE IF EXISTS checkin_station_tokens ADD COLUMN IF NOT EXISTS sucursal_id BIGINT NULL;"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_checkin_station_tokens_sucursal_id'
            ) THEN
                BEGIN
                    EXECUTE 'ALTER TABLE checkin_station_tokens ADD CONSTRAINT fk_checkin_station_tokens_sucursal_id FOREIGN KEY (sucursal_id) REFERENCES sucursales(id) ON DELETE SET NULL';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_checkin_station_tokens_token ON checkin_station_tokens(token);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkin_station_tokens_sucursal_expires ON checkin_station_tokens(sucursal_id, expires_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkin_station_tokens_expires_at ON checkin_station_tokens(expires_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkin_station_tokens_sucursal_active ON checkin_station_tokens(sucursal_id, created_at) WHERE used_by IS NULL;"
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'asistencias_usuario_id_fecha_key'
            ) THEN
                EXECUTE 'ALTER TABLE asistencias DROP CONSTRAINT asistencias_usuario_id_fecha_key';
            END IF;
        END $$;
        """
    )
    op.execute("DROP INDEX IF EXISTS asistencias_usuario_id_fecha_key;")

    op.execute(
        """
        DELETE FROM asistencias a
        USING asistencias b
        WHERE a.id < b.id
          AND a.usuario_id = b.usuario_id
          AND a.fecha = b.fecha
          AND (
            (a.sucursal_id IS NULL AND b.sucursal_id IS NULL)
            OR (a.sucursal_id IS NOT NULL AND b.sucursal_id IS NOT NULL AND a.sucursal_id = b.sucursal_id)
          );
        """
    )

    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_asistencias_usuario_fecha_global ON asistencias(usuario_id, fecha) WHERE sucursal_id IS NULL;"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_asistencias_usuario_fecha_sucursal ON asistencias(usuario_id, fecha, sucursal_id) WHERE sucursal_id IS NOT NULL;"
    )


def downgrade() -> None:
    return
