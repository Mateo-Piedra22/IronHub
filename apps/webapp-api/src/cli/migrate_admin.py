import os

from dotenv import load_dotenv

load_dotenv()

from src.database.connection import get_admin_database_url
from src.database.migration_runner import upgrade_head


def main() -> None:
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg_path = os.path.join(here, "alembic_admin.ini")
    script_location = os.path.join(here, "alembic_admin")
    url = get_admin_database_url()
    if not url:
        raise SystemExit("Falta configuración de DB admin (ADMIN_DB_HOST/ADMIN_DB_NAME o ADMIN_DATABASE_URL).")
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
