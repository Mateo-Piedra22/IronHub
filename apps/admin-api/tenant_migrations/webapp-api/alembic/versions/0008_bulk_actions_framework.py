from alembic import op

revision = "0008_bulk_actions_framework"
down_revision = "0007_optional_drop_legacy_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bulk_jobs (
            id SERIAL PRIMARY KEY,
            kind VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'draft',
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT CURRENT_TIMESTAMP NOT NULL,
            created_by_user_id INTEGER,
            created_by_role TEXT,
            source_filename TEXT,
            source_mime TEXT,
            source_size_bytes INTEGER,
            source_b2_key TEXT,
            rows_total INTEGER DEFAULT 0 NOT NULL,
            rows_valid INTEGER DEFAULT 0 NOT NULL,
            rows_invalid INTEGER DEFAULT 0 NOT NULL,
            applied_count INTEGER DEFAULT 0 NOT NULL,
            error_count INTEGER DEFAULT 0 NOT NULL,
            options JSONB,
            failure_reason TEXT
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS bulk_job_rows (
            id BIGSERIAL PRIMARY KEY,
            job_id INTEGER NOT NULL REFERENCES bulk_jobs(id) ON DELETE CASCADE,
            row_index INTEGER NOT NULL,
            data JSONB NOT NULL,
            errors JSONB,
            warnings JSONB,
            is_valid BOOLEAN DEFAULT 'true' NOT NULL,
            applied BOOLEAN DEFAULT 'false' NOT NULL,
            applied_at TIMESTAMP WITHOUT TIME ZONE,
            result JSONB,
            UNIQUE (job_id, row_index)
        );
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_bulk_jobs_kind_status ON bulk_jobs (kind, status);"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_bulk_job_rows_job_id ON bulk_job_rows (job_id);")


def downgrade() -> None:
    return

