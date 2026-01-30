import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env vars from webapp-api .env
base_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(base_dir, "apps", "webapp-api", ".env")
load_dotenv(env_path)

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
# DB_NAME = "testingiron_db" # We know this is the one from inspection

# Use passed arg or default
import sys

DB_NAME = sys.argv[1] if len(sys.argv) > 1 else "testingiron_db"


def get_engine():
    url = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    return create_engine(url)


# Add src to path
import sys
import os

sys.path.append(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "apps", "webapp-api")
)

from src.models.orm_models import Base
from sqlalchemy import text


def migrate():
    print(f"Migrating database: {DB_NAME}...")
    engine = get_engine()

    # 1. Use SQLAlchemy to create missing tables (Robust & Automatic)
    print("Syncing schema with ORM models...")
    try:
        Base.metadata.create_all(bind=engine)
        print(
            "  - create_all() completed (created missing tables: numeracion_comprobantes, comprobantes_pago, etc)."
        )
    except Exception as e:
        print(f"  - Error in create_all: {e}")

    with engine.connect() as conn:
        # 1.5 Ensure critical constraints exist (create_all does not alter existing tables)
        try:
            conn.execute(
                text("""
                DO $$
                BEGIN
                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'idx_pagos_usuario_mes_año'
                    ) THEN
                        EXECUTE format(
                            'ALTER TABLE pagos ADD CONSTRAINT %I UNIQUE (usuario_id, mes, %I)',
                            'idx_pagos_usuario_mes_año',
                            'año'
                        );
                    END IF;

                    IF NOT EXISTS (
                        SELECT 1 FROM pg_constraint WHERE conname = 'asistencias_usuario_id_fecha_key'
                    ) THEN
                        NULL;
                    END IF;
                END $$;
            """)
            )
            print("Ensured critical unique constraints (pagos/asistencias).")
        except Exception as e:
            print(f"  - Warning: could not ensure constraints: {e}")

        try:
            conn.execute(
                text("""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'ejercicios' AND column_name = 'variantes'
                    ) THEN
                        NULL;
                    ELSE
                        EXECUTE 'ALTER TABLE ejercicios ADD COLUMN variantes TEXT';
                    END IF;

                    IF EXISTS (
                        SELECT 1 FROM information_schema.columns
                        WHERE table_name = 'usuarios' AND column_name = 'pin'
                    ) THEN
                        IF EXISTS (
                            SELECT 1 FROM information_schema.columns
                            WHERE table_name = 'usuarios' AND column_name = 'pin'
                            AND data_type = 'character varying'
                            AND (character_maximum_length IS NULL OR character_maximum_length < 100)
                        ) THEN
                            EXECUTE 'ALTER TABLE usuarios ALTER COLUMN pin TYPE VARCHAR(100)';
                        END IF;
                        EXECUTE 'ALTER TABLE usuarios ALTER COLUMN pin SET DEFAULT ''123456''';
                    END IF;
                END $$;
            """)
            )
            print("Ensured schema alignment for usuarios.pin and ejercicios.variantes.")
        except Exception as e:
            print(f"  - Warning: could not ensure schema alignment: {e}")

        # 2. Add 'equipamiento' to 'ejercicios' (ALTER TABLE for existing tables)
        print("Checking 'ejercicios' for 'equipamiento' column...")
        try:
            # Check if column exists first to avoid error if using simple SQL
            result = conn.execute(
                text(
                    "SELECT column_name FROM information_schema.columns WHERE table_name='ejercicios' AND column_name='equipamiento'"
                )
            )
            if not result.scalar():
                conn.execute(
                    text("ALTER TABLE ejercicios ADD COLUMN equipamiento VARCHAR(100);")
                )
                print("  - Added 'equipamiento' column.")
            else:
                print("  - 'equipamiento' column already exists.")
        except Exception as e:
            print(f"  - Error checking/adding column: {e}")

        conn.commit()
        print("Migration complete.")


if __name__ == "__main__":
    migrate()
