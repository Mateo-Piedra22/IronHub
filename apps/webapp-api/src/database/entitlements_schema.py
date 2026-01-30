from sqlalchemy import text
from sqlalchemy.orm import Session


def ensure_entitlements_schema(db: Session) -> None:
    db.execute(
        text(
            "ALTER TABLE tipos_cuota ADD COLUMN IF NOT EXISTS all_sucursales BOOLEAN NOT NULL DEFAULT TRUE"
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tipo_cuota_sucursales (
                tipo_cuota_id INTEGER NOT NULL REFERENCES tipos_cuota(id) ON DELETE CASCADE,
                sucursal_id INTEGER NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                PRIMARY KEY (tipo_cuota_id, sucursal_id)
            )
            """
        )
    )
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS tipo_cuota_clases_permisos (
                id SERIAL PRIMARY KEY,
                tipo_cuota_id INTEGER NOT NULL REFERENCES tipos_cuota(id) ON DELETE CASCADE,
                sucursal_id INTEGER NULL REFERENCES sucursales(id) ON DELETE CASCADE,
                target_type VARCHAR(20) NOT NULL,
                target_id INTEGER NOT NULL,
                allow BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_tipo_cuota_clases_permiso ON tipo_cuota_clases_permisos(tipo_cuota_id, sucursal_id, target_type, target_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_tipo_cuota_clases_permiso_tipo_cuota ON tipo_cuota_clases_permisos(tipo_cuota_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_tipo_cuota_clases_permiso_sucursal ON tipo_cuota_clases_permisos(sucursal_id)"
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS usuario_accesos_sucursales (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                sucursal_id INTEGER NOT NULL REFERENCES sucursales(id) ON DELETE CASCADE,
                allow BOOLEAN NOT NULL,
                motivo TEXT NULL,
                starts_at TIMESTAMP WITHOUT TIME ZONE NULL,
                ends_at TIMESTAMP WITHOUT TIME ZONE NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_accesos_sucursales ON usuario_accesos_sucursales(usuario_id, sucursal_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_usuario_accesos_sucursales_usuario ON usuario_accesos_sucursales(usuario_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_usuario_accesos_sucursales_sucursal ON usuario_accesos_sucursales(sucursal_id)"
        )
    )

    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS usuario_permisos_clases (
                id SERIAL PRIMARY KEY,
                usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
                sucursal_id INTEGER NULL REFERENCES sucursales(id) ON DELETE CASCADE,
                target_type VARCHAR(20) NOT NULL,
                target_id INTEGER NOT NULL,
                allow BOOLEAN NOT NULL,
                motivo TEXT NULL,
                starts_at TIMESTAMP WITHOUT TIME ZONE NULL,
                ends_at TIMESTAMP WITHOUT TIME ZONE NULL,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_usuario_permisos_clases ON usuario_permisos_clases(usuario_id, sucursal_id, target_type, target_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_usuario_permisos_clases_usuario ON usuario_permisos_clases(usuario_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_usuario_permisos_clases_sucursal ON usuario_permisos_clases(sucursal_id)"
        )
    )

