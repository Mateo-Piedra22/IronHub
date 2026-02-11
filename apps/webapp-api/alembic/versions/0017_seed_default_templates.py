"""
Seed: Default routine templates for the Dynamic Routine Engine.
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

revision = "0017_seed_default_templates"
down_revision = "0016_add_dynamic_template_system"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()

    template_config = {
        "metadata": {
            "name": "Plantilla Clásica",
            "version": "1.0.0",
            "description": "Plantilla pública por defecto para exportar rutinas en PDF",
            "author": "system",
            "category": "general",
            "difficulty": "beginner",
            "tags": ["classic", "system"],
            "estimated_duration": 45,
        },
        "layout": {
            "page_size": "A4",
            "orientation": "portrait",
            "margins": {"top": 20, "bottom": 20, "left": 20, "right": 20},
        },
        "pages": [
            {
                "name": "Rutina",
                "sections": [
                    {
                        "type": "header",
                        "content": {
                            "title": "{{gym_name}}",
                            "subtitle": "{{nombre_rutina}} - {{usuario_nombre}}",
                        },
                    },
                    {"type": "spacing", "content": {"height": 8}},
                    {"type": "exercise_table", "content": {}},
                    {"type": "spacing", "content": {"height": 12}},
                    {"type": "qr_code", "content": {"size": 90}},
                ],
            }
        ],
        "variables": {
            "gym_name": {"type": "string", "default": "Gimnasio", "required": False},
            "nombre_rutina": {"type": "string", "default": "Rutina", "required": False},
            "usuario_nombre": {"type": "string", "default": "Usuario", "required": False},
        },
        "qr_code": {"enabled": True, "position": "inline", "data_source": "routine_uuid"},
        "styling": {
            "fonts": {
                "title": {"family": "Helvetica-Bold", "size": 18, "color": "#000000"},
                "body": {"family": "Helvetica", "size": 10, "color": "#111827"},
            },
            "colors": {"primary": "#111827", "accent": "#3B82F6"},
        },
    }

    cfg_json = json.dumps(template_config, ensure_ascii=False)

    existing = conn.execute(
        sa.text(
            """
            SELECT id FROM plantillas_rutina
            WHERE activa = true AND publica = true
            ORDER BY id ASC
            LIMIT 1
            """
        )
    ).scalar()
    if existing:
        return

    template_id = conn.execute(
        sa.text(
            """
            INSERT INTO plantillas_rutina
              (nombre, descripcion, configuracion, categoria, dias_semana, activa, publica, version_actual, tags, uso_count, rating_count)
            VALUES
              (:nombre, :descripcion, CAST(:cfg AS JSONB), :categoria, :dias_semana, true, true, :version_actual, :tags, 0, 0)
            RETURNING id
            """
        ),
        {
            "nombre": "Plantilla Clásica",
            "descripcion": "Plantilla pública por defecto (sistema)",
            "cfg": cfg_json,
            "categoria": "general",
            "dias_semana": None,
            "version_actual": "1.0.0",
            "tags": ["classic", "system"],
        },
    ).scalar()

    if template_id:
        conn.execute(
            sa.text(
                """
                INSERT INTO plantillas_rutina_versiones
                  (plantilla_id, version, configuracion, cambios_descripcion, creada_por, es_actual)
                VALUES
                  (:pid, :version, CAST(:cfg AS JSONB), :desc, NULL, true)
                """
            ),
            {
                "pid": int(template_id),
                "version": "1.0.0",
                "cfg": cfg_json,
                "desc": "Versión inicial (seed)",
            },
        )


def downgrade():
    conn = op.get_bind()
    row = conn.execute(
        sa.text("SELECT id FROM plantillas_rutina WHERE nombre = :n AND publica = true LIMIT 1"),
        {"n": "Plantilla Clásica"},
    ).scalar()
    if not row:
        return
    conn.execute(
        sa.text("DELETE FROM plantillas_rutina_versiones WHERE plantilla_id = :pid"),
        {"pid": int(row)},
    )
    conn.execute(
        sa.text("DELETE FROM plantillas_rutina WHERE id = :pid"),
        {"pid": int(row)},
    )
