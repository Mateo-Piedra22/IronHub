"""
Add explicit template type to plantillas_rutina to separate export templates
from other legacy/blueprint configurations.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_tpl_tipo"
down_revision = "0019_seed_excel_tpls"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "plantillas_rutina",
        sa.Column("tipo", sa.String(length=50), nullable=False, server_default="export_pdf"),
    )
    op.create_index("idx_plantillas_rutina_tipo", "plantillas_rutina", ["tipo"])

    conn = op.get_bind()
    conn.execute(
        sa.text(
            """
            UPDATE plantillas_rutina
            SET tipo = 'export_pdf'
            WHERE configuracion ? 'metadata'
              AND configuracion ? 'layout'
              AND configuracion ? 'pages'
              AND configuracion ? 'variables'
            """
        )
    )
    conn.execute(
        sa.text(
            """
            UPDATE plantillas_rutina
            SET tipo = 'workout_blueprint'
            WHERE NOT (
              configuracion ? 'metadata'
              AND configuracion ? 'layout'
              AND configuracion ? 'pages'
              AND configuracion ? 'variables'
            )
            """
        )
    )


def downgrade():
    op.drop_index("idx_plantillas_rutina_tipo", table_name="plantillas_rutina")
    op.drop_column("plantillas_rutina", "tipo")

