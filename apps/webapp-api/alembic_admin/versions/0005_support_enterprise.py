from alembic import op

revision = "0005_support_enterprise"
down_revision = "0004_support_tickets_and_changelogs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS assigned_to TEXT NULL;")
    op.execute("ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS tags JSONB NULL;")
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS first_response_due_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS next_response_due_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS first_response_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS closed_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS last_admin_read_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )
    op.execute(
        "ALTER TABLE public.support_tickets ADD COLUMN IF NOT EXISTS last_client_read_at TIMESTAMP WITHOUT TIME ZONE NULL;"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_support_tickets_next_response_due_at ON public.support_tickets(next_response_due_at);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_support_tickets_assigned_to ON public.support_tickets(assigned_to);"
    )


def downgrade() -> None:
    return

