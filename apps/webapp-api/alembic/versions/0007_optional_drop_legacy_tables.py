from alembic import op

revision = "0007_optional_drop_legacy_tables"
down_revision = "0006_fix_fk_integer_types"
branch_labels = None
depends_on = None


def upgrade() -> None:
    tables = [
        "theme_schedules",
        "custom_themes",
        "theme_scheduling_config",
        "system_diagnostics",
        "maintenance_tasks",
        "acciones_masivas_pendientes",
    ]

    for t in tables:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{t}') IS NOT NULL THEN
                    IF EXISTS (SELECT 1 FROM {t} LIMIT 1) THEN
                        RAISE EXCEPTION 'No se puede eliminar %.%: la tabla tiene datos', 'public', '{t}';
                    END IF;
                END IF;
            END $$;
            """
        )

    for t in tables:
        op.execute(
            f"""
            DO $$
            BEGIN
                IF to_regclass('public.{t}') IS NOT NULL THEN
                    EXECUTE 'DROP TABLE IF EXISTS {t} CASCADE';
                END IF;
            END $$;
            """
        )
