import os
from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable, CreateIndex, AddConstraint


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "apps").is_dir() and (p / "package.json").exists():
            return p
    return here.parents[1]


def _normalize_create_table(sql: str) -> str:
    s = sql.strip().rstrip(";")
    if s.upper().startswith("CREATE TABLE "):
        s = "CREATE TABLE IF NOT EXISTS " + s[len("CREATE TABLE ") :]
    return s + ";"


def _normalize_create_index(sql: str) -> str:
    s = sql.strip().rstrip(";")
    up = s.upper()
    if up.startswith("CREATE UNIQUE INDEX "):
        s = "CREATE UNIQUE INDEX IF NOT EXISTS " + s[len("CREATE UNIQUE INDEX ") :]
    elif up.startswith("CREATE INDEX "):
        s = "CREATE INDEX IF NOT EXISTS " + s[len("CREATE INDEX ") :]
    return s + ";"


def main() -> None:
    root = _repo_root()
    webapp_api = root / "apps" / "webapp-api"

    os.chdir(str(webapp_api))
    import sys

    sys.path.insert(0, str(webapp_api))

    from src.models.orm_models import Base

    dialect = postgresql.dialect()
    stmts: list[str] = []

    stmts.append(
        """
        DO $$
        BEGIN
            BEGIN
                CREATE EXTENSION IF NOT EXISTS pg_trgm;
            EXCEPTION
                WHEN insufficient_privilege THEN
                    NULL;
            END;
        END $$;
        """.strip()
    )

    for table in Base.metadata.sorted_tables:
        stmts.append(_normalize_create_table(str(CreateTable(table).compile(dialect=dialect))))

    for table in Base.metadata.sorted_tables:
        for idx in sorted(table.indexes, key=lambda x: x.name or ""):
            stmts.append(_normalize_create_index(str(CreateIndex(idx).compile(dialect=dialect))))

    extra_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_usuarios_telefono ON usuarios(telefono)",
        "CREATE INDEX IF NOT EXISTS idx_usuarios_fecha_proximo_vencimiento ON usuarios(fecha_proximo_vencimiento)",
        "CREATE INDEX IF NOT EXISTS idx_pagos_fecha_pago ON pagos(fecha_pago)",
        "CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado)",
        "CREATE INDEX IF NOT EXISTS idx_ejercicios_nombre ON ejercicios(nombre)",
        "CREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_id ON rutina_ejercicios(rutina_id)",
        "CREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_ejercicio_id ON rutina_ejercicios(ejercicio_id)",
        "CREATE INDEX IF NOT EXISTS idx_comprobantes_pago_pago_id ON comprobantes_pago(pago_id)",
        "CREATE INDEX IF NOT EXISTS idx_comprobantes_pago_numero ON comprobantes_pago(numero_comprobante)",
        "CREATE INDEX IF NOT EXISTS idx_checkin_pending_usuario_id ON checkin_pending(usuario_id)",
        "CREATE INDEX IF NOT EXISTS idx_checkin_pending_expires_at ON checkin_pending(expires_at)",
        "CREATE INDEX IF NOT EXISTS idx_rutina_ejercicios_rutina_dia_orden ON rutina_ejercicios (rutina_id, dia_semana, orden)",
        "CREATE INDEX IF NOT EXISTS idx_comprobantes_pago_emitido_pago_fecha_desc ON comprobantes_pago (pago_id, fecha_creacion DESC) WHERE estado = 'emitido'",
        "CREATE INDEX IF NOT EXISTS idx_pagos_metodo_fecha_desc ON pagos (metodo_pago_id, fecha_pago DESC)",
    ]
    stmts.extend([s.strip().rstrip(';') + ';' for s in extra_indexes])

    trgm_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_usuarios_nombre_trgm ON usuarios USING gin (lower(nombre) gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS idx_rutinas_nombre_trgm ON rutinas USING gin (lower(nombre_rutina) gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS idx_ejercicios_nombre_trgm ON ejercicios USING gin (lower(nombre) gin_trgm_ops)",
    ]
    for stmt in trgm_indexes:
        esc = stmt.strip().rstrip(";").replace("'", "''")
        stmts.append(
            (
                "DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm') "
                f"THEN EXECUTE '{esc}'; END IF; END $$;"
            )
        )

    stmts.extend(
        [
            "ALTER TABLE IF EXISTS ejercicios ADD COLUMN IF NOT EXISTS variantes TEXT;",
            "ALTER TABLE IF EXISTS sucursales ADD COLUMN IF NOT EXISTS station_key VARCHAR(64);",
            "ALTER TABLE IF EXISTS usuarios ALTER COLUMN pin TYPE VARCHAR(100);",
            "ALTER TABLE IF EXISTS usuarios ALTER COLUMN pin SET DEFAULT '123456';",
        ]
    )

    for table in Base.metadata.sorted_tables:
        for c in table.constraints:
            if getattr(c, "use_alter", False) and getattr(c, "name", None):
                stmts.append(str(AddConstraint(c).compile(dialect=dialect)).strip().rstrip(";") + ";")

    stmts.append(
        """
        INSERT INTO sucursales (nombre, codigo)
        SELECT 'Sucursal Principal', 'principal'
        WHERE NOT EXISTS (SELECT 1 FROM sucursales);
        """.strip()
    )

    stmts.append(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'asistencias' AND column_name = 'sucursal_id'
            ) THEN
                UPDATE asistencias
                SET sucursal_id = (SELECT id FROM sucursales ORDER BY id ASC LIMIT 1)
                WHERE sucursal_id IS NULL;
            END IF;
        END $$;
        """.strip()
    )
    stmts.append(
        """
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'checkin_pending' AND column_name = 'sucursal_id'
            ) THEN
                UPDATE checkin_pending
                SET sucursal_id = (SELECT id FROM sucursales ORDER BY id ASC LIMIT 1)
                WHERE sucursal_id IS NULL;
            END IF;
        END $$;
        """.strip()
    )

    out_path = webapp_api / "alembic" / "versions" / "0001_tenant_schema_baseline.py"
    body = "\n\n".join([f'    op.execute("""\\n{s}\\n    """)' for s in stmts])

    content = f"""from alembic import op

revision = "0001_tenant_schema_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
{body}


def downgrade() -> None:
    return
"""
    out_path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
