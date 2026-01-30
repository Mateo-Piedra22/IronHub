import argparse
import os

from src.database.tenant_connection import _build_tenant_db_url
from src.database.migration_runner import upgrade_head


def main() -> None:
    parser = argparse.ArgumentParser(prog="webapp-api-migrate-verify")
    parser.add_argument("--db-name", type=str, default=None)
    parser.add_argument("--db-url", type=str, default=None)
    args = parser.parse_args()

    url = str(args.db_url or "").strip()
    lock_name = ""
    if not url and args.db_name:
        url = _build_tenant_db_url(str(args.db_name))
        lock_name = f"tenant:{args.db_name}"
    if not url:
        raise SystemExit("Falta --db-url o --db-name.")
    if not lock_name:
        try:
            from sqlalchemy.engine import make_url

            u = make_url(url)
            lock_name = f"tenant:{u.database or 'unknown'}"
        except Exception:
            lock_name = "tenant:unknown"

    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg_path = os.path.join(here, "alembic.ini")
    script_location = os.path.join(here, "alembic")
    upgrade_head(
        sqlalchemy_url=url,
        cfg_path=cfg_path,
        script_location=script_location,
        lock_name=lock_name,
        lock_timeout_seconds=300,
        verify_revision=True,
        verify_idempotent=True,
    )


if __name__ == "__main__":
    main()
