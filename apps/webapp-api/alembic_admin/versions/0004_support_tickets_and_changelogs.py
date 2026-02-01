from alembic import op

revision = "0004_support_tickets_and_changelogs"
down_revision = "0003_admin_prod_ready_fix"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.support_tickets (
            id BIGSERIAL PRIMARY KEY,
            gym_id BIGINT NULL,
            tenant TEXT NOT NULL,
            user_id BIGINT NULL,
            user_role TEXT NULL,
            sucursal_id BIGINT NULL,
            subject TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'general',
            priority TEXT NOT NULL DEFAULT 'medium',
            status TEXT NOT NULL DEFAULT 'open',
            origin_url TEXT NULL,
            user_agent TEXT NULL,
            meta JSONB NULL,
            last_message_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            last_message_sender TEXT NULL,
            unread_by_admin BOOLEAN NOT NULL DEFAULT TRUE,
            unread_by_client BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_support_tickets_tenant_status ON public.support_tickets(tenant, status);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_support_tickets_status_priority ON public.support_tickets(status, priority);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_support_tickets_last_message_at_desc ON public.support_tickets(last_message_at DESC);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.support_ticket_messages (
            id BIGSERIAL PRIMARY KEY,
            ticket_id BIGINT NOT NULL REFERENCES public.support_tickets(id) ON DELETE CASCADE,
            sender_type TEXT NOT NULL,
            sender_id BIGINT NULL,
            content TEXT NOT NULL,
            attachments JSONB NULL,
            read_by_recipient BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_support_ticket_messages_ticket_created ON public.support_ticket_messages(ticket_id, created_at ASC);"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.changelogs (
            id BIGSERIAL PRIMARY KEY,
            version TEXT NOT NULL,
            title TEXT NOT NULL,
            body_markdown TEXT NOT NULL,
            change_type TEXT NOT NULL DEFAULT 'improvement',
            image_url TEXT NULL,
            is_published BOOLEAN NOT NULL DEFAULT FALSE,
            published_at TIMESTAMP WITHOUT TIME ZONE NULL,
            created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            created_by TEXT NULL,
            updated_by TEXT NULL
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_changelogs_published_at_desc ON public.changelogs(is_published, published_at DESC);"
    )
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_changelogs_version ON public.changelogs(version);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS public.changelog_reads (
            tenant TEXT NOT NULL,
            user_id BIGINT NOT NULL,
            user_role TEXT NOT NULL DEFAULT 'user',
            last_seen_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
            last_seen_changelog_id BIGINT NULL,
            PRIMARY KEY (tenant, user_id, user_role)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_changelog_reads_tenant_seen_at ON public.changelog_reads(tenant, last_seen_at DESC);"
    )


def downgrade() -> None:
    return
