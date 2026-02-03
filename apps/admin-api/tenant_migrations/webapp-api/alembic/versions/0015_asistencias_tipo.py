from alembic import op

revision = "0015_asistencias_tipo"
down_revision = "0014_checkin_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE asistencias
        ADD COLUMN IF NOT EXISTS tipo TEXT NOT NULL DEFAULT 'unknown';
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_asistencias_tipo ON asistencias(tipo);"
    )


def downgrade() -> None:
    return

