import os

from src.database.migration_runner import upgrade_head


def main() -> None:
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg_path = os.path.join(here, "alembic_admin.ini")
    script_location = os.path.join(here, "alembic_admin")
    url = os.getenv("ADMIN_DATABASE_URL") or os.getenv("DATABASE_URL") or ""
    if not url:
        raise SystemExit("Falta ADMIN_DATABASE_URL (o DATABASE_URL) para migrar admin DB.")
    upgrade_head(
        sqlalchemy_url=str(url),
        cfg_path=cfg_path,
        script_location=script_location,
        lock_name="admin-db",
        lock_timeout_seconds=300,
        verify_revision=False,
        verify_idempotent=False,
    )


if __name__ == "__main__":
    main()
