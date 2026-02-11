import argparse
import os
from dataclasses import dataclass
from typing import Iterable, Optional

from dotenv import load_dotenv

load_dotenv()

from sqlalchemy import text

from src.database.connection import AdminSessionLocal
from src.database.migration_runner import upgrade_head
from src.database.tenant_connection import _build_tenant_db_url


@dataclass(frozen=True)
class TenantInfo:
    subdominio: str
    db_name: str
    status: str


def _load_tenants_from_admin(*, include_inactive: bool) -> list[TenantInfo]:
    ses = AdminSessionLocal()
    try:
        rows = (
            ses.execute(
                text(
                    """
                    SELECT subdominio, db_name, status
                    FROM gyms
                    WHERE subdominio IS NOT NULL AND TRIM(subdominio) <> ''
                    """
                    + ("" if include_inactive else " AND COALESCE(status,'active') = 'active'")
                    + " ORDER BY id ASC"
                )
            )
            .mappings()
            .all()
        )
        out: list[TenantInfo] = []
        for r in rows or []:
            sub = str(r.get("subdominio") or "").strip().lower()
            dbn = str(r.get("db_name") or "").strip()
            st = str(r.get("status") or "active").strip().lower()
            if not sub or not dbn:
                continue
            out.append(TenantInfo(subdominio=sub, db_name=dbn, status=st))
        return out
    finally:
        ses.close()


def _iter_selected_tenants(
    *,
    tenant: Optional[str],
    include_inactive: bool,
) -> Iterable[TenantInfo]:
    tenants = _load_tenants_from_admin(include_inactive=include_inactive)
    if tenant:
        t = str(tenant).strip().lower()
        for x in tenants:
            if x.subdominio == t:
                return [x]
        return []
    return tenants


def migrate_tenant_db(
    *,
    db_name: str,
    lock_timeout_seconds: int = 120,
    verify_idempotent: bool = False,
) -> None:
    here = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    cfg_path = os.path.join(here, "alembic.ini")
    script_location = os.path.join(here, "alembic")
    url = _build_tenant_db_url(db_name)
    upgrade_head(
        sqlalchemy_url=url,
        cfg_path=cfg_path,
        script_location=script_location,
        lock_name=f"tenant:{db_name}",
        lock_timeout_seconds=int(lock_timeout_seconds),
        verify_revision=True,
        verify_idempotent=bool(verify_idempotent),
    )


def main() -> None:
    parser = argparse.ArgumentParser(prog="webapp-api-migrate")
    parser.add_argument("--tenant", type=str, default=None)
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument("--fail-fast", action="store_true")
    parser.add_argument("--lock-timeout-seconds", type=int, default=120)
    parser.add_argument("--verify-idempotent", action="store_true")
    args = parser.parse_args()

    selected = list(
        _iter_selected_tenants(
            tenant=args.tenant,
            include_inactive=bool(args.include_inactive),
        )
    )
    if args.tenant and not selected:
        raise SystemExit(f"Tenant no encontrado: {args.tenant}")

    ok = 0
    failed: list[str] = []
    for t in selected:
        try:
            migrate_tenant_db(
                db_name=t.db_name,
                lock_timeout_seconds=int(args.lock_timeout_seconds),
                verify_idempotent=bool(args.verify_idempotent),
            )
            ok += 1
        except Exception as e:
            failed.append(f"{t.subdominio} ({t.db_name}): {e}")
            if bool(args.fail_fast):
                break

    if failed:
        msg = "\n".join(failed)
        raise SystemExit(f"Migraciones fallidas ({len(failed)}/{len(selected)}):\n{msg}")


if __name__ == "__main__":
    main()
