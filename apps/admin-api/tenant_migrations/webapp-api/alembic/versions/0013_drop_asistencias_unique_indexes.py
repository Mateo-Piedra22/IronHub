from alembic import op

revision = "0013_drop_asistencias_unique_indexes"
down_revision = "0012_access_commands"
branch_labels = None
depends_on = None


def upgrade() -> None:
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
    op.execute("DROP INDEX IF EXISTS uq_asistencias_usuario_fecha_global;")
    op.execute("DROP INDEX IF EXISTS uq_asistencias_usuario_fecha_sucursal;")
    op.execute("DROP INDEX IF EXISTS asistencias_usuario_id_fecha_key;")


def downgrade() -> None:
    return
