from sqlalchemy import text
from sqlalchemy.orm import Session


def ensure_clase_profesor_schema(db: Session) -> None:
    db.execute(
        text(
            """
            CREATE TABLE IF NOT EXISTS clase_profesor_asignaciones (
                id SERIAL PRIMARY KEY,
                clase_id INTEGER NOT NULL REFERENCES clases(id) ON DELETE CASCADE,
                profesor_id INTEGER NOT NULL REFERENCES profesores(id) ON DELETE CASCADE,
                activa BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
                UNIQUE (clase_id, profesor_id)
            )
            """
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_clase_profesor_asignaciones_profesor ON clase_profesor_asignaciones(profesor_id)"
        )
    )
    db.execute(
        text(
            "CREATE INDEX IF NOT EXISTS idx_clase_profesor_asignaciones_clase ON clase_profesor_asignaciones(clase_id)"
        )
    )

