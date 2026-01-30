from alembic import op

revision = "0003_pagos_idempotency"
down_revision = "0002_multisucursal_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS pagos_idempotency (
            key TEXT PRIMARY KEY,
            pago_id BIGINT NOT NULL REFERENCES pagos(id) ON DELETE CASCADE,
            usuario_id BIGINT NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            mes INTEGER NOT NULL,
            año INTEGER NOT NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_pagos_idempotency_usuario_created_at_desc ON pagos_idempotency(usuario_id, created_at DESC);"
    )


def downgrade() -> None:
    return
