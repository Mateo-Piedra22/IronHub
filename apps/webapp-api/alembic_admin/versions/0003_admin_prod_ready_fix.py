from alembic import op

revision = "0003_admin_prod_ready_fix"
down_revision = "0002_admin_production_ready"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE IF EXISTS public.gyms ADD COLUMN IF NOT EXISTS production_ready BOOLEAN NOT NULL DEFAULT false;")
    op.execute("ALTER TABLE IF EXISTS public.gyms ADD COLUMN IF NOT EXISTS production_ready_at TIMESTAMP WITHOUT TIME ZONE NULL;")
    op.execute("ALTER TABLE IF EXISTS public.gyms ADD COLUMN IF NOT EXISTS production_ready_by TEXT NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_gyms_production_ready ON public.gyms(production_ready);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_gyms_production_ready_at ON public.gyms(production_ready_at DESC);")


def downgrade() -> None:
    return

