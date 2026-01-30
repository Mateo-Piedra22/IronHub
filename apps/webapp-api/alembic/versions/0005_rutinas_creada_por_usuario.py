from alembic import op

revision = "0005_rutinas_creada_por_usuario"
down_revision = "0004_usuario_sucursal_registro"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        "ALTER TABLE IF EXISTS rutinas ADD COLUMN IF NOT EXISTS creada_por_usuario_id BIGINT NULL;"
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'fk_rutinas_creada_por_usuario_id'
            ) THEN
                BEGIN
                    EXECUTE 'ALTER TABLE rutinas ADD CONSTRAINT fk_rutinas_creada_por_usuario_id FOREIGN KEY (creada_por_usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL';
                EXCEPTION WHEN others THEN
                    NULL;
                END;
            END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_rutinas_creada_por_usuario_id ON rutinas(creada_por_usuario_id);"
    )


def downgrade() -> None:
    return

