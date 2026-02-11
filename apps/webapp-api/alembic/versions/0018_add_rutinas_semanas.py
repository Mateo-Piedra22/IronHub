"""
Add semanas to rutinas.
"""

from alembic import op
import sqlalchemy as sa

revision = "0018_add_rutinas_semanas"
down_revision = "0017_seed_default_templates"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("rutinas") as batch_op:
        batch_op.add_column(sa.Column("semanas", sa.Integer(), server_default="4"))
    op.create_index("idx_rutinas_semanas", "rutinas", ["semanas"])


def downgrade():
    op.drop_index("idx_rutinas_semanas", table_name="rutinas")
    with op.batch_alter_table("rutinas") as batch_op:
        batch_op.drop_column("semanas")

