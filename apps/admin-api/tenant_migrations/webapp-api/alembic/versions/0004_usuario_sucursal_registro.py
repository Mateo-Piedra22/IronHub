from alembic import op

revision = "0004_usuario_sucursal_registro"
down_revision = "0003_pagos_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE IF EXISTS usuarios ADD COLUMN IF NOT EXISTS sucursal_registro_id BIGINT NULL;"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_usuarios_sucursal_registro_id'
            ) THEN
                BEGIN
                    EXECUTE 'ALTER TABLE usuarios ADD CONSTRAINT fk_usuarios_sucursal_registro_id FOREIGN KEY (sucursal_registro_id) REFERENCES sucursales(id) ON DELETE SET NULL';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_usuarios_sucursal_registro_id ON usuarios(sucursal_registro_id);"
    )


def downgrade() -> None:
    return
