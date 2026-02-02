from alembic import op

revision = "0014_checkin_idempotency"
down_revision = "0013_drop_asist_uq_idx"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS checkin_idempotency (
            key TEXT PRIMARY KEY,
            expires_at TIMESTAMP WITHOUT TIME ZONE NULL,
            usuario_id INTEGER NULL REFERENCES usuarios(id) ON DELETE SET NULL,
            route TEXT NOT NULL DEFAULT '',
            request_hash TEXT NULL,
            response_status INTEGER NULL,
            response_body JSONB NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkin_idempotency_expires_at ON checkin_idempotency(expires_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkin_idempotency_usuario_created_at_desc ON checkin_idempotency(usuario_id, created_at DESC);"
    )


def downgrade() -> None:
    return

