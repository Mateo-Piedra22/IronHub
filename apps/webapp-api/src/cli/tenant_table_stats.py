import argparse
import csv
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, text

from src.database.connection import AdminSessionLocal
from src.database.tenant_connection import _build_tenant_db_url


@dataclass(frozen=True)
class TenantInfo:
    subdominio: str
    db_name: str


def _load_tenant_from_admin(subdominio: str) -> Optional[TenantInfo]:
    ses = AdminSessionLocal()
    try:
        row = (
            ses.execute(
                text(
                    """
                    SELECT subdominio, db_name
                    FROM gyms
                    WHERE LOWER(TRIM(subdominio)) = LOWER(TRIM(:s))
                    LIMIT 1
                    """
                ),
                {"s": str(subdominio or "")},
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        sub = str(row.get("subdominio") or "").strip().lower()
        dbn = str(row.get("db_name") or "").strip()
        if not sub or not dbn:
            return None
        return TenantInfo(subdominio=sub, db_name=dbn)
    finally:
        ses.close()


def export_table_stats(url: str, out_csv: Path) -> None:
    engine = create_engine(url, pool_pre_ping=True)
    q = text(
        """
        SELECT
            n.nspname AS schema,
            c.relname AS table,
            COALESCE(s.n_live_tup, 0) AS n_live_tup,
            COALESCE(s.n_dead_tup, 0) AS n_dead_tup,
            pg_total_relation_size(c.oid) AS total_bytes,
            pg_relation_size(c.oid) AS table_bytes,
            pg_indexes_size(c.oid) AS index_bytes,
            s.last_vacuum,
            s.last_autovacuum,
            s.last_analyze,
            s.last_autoanalyze
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
        WHERE c.relkind = 'r'
          AND n.nspname = 'public'
          AND c.relname <> 'alembic_version'
        ORDER BY total_bytes DESC, c.relname ASC
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(q).mappings().all()

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "schema",
                "table",
                "n_live_tup",
                "n_dead_tup",
                "total_bytes",
                "table_bytes",
                "index_bytes",
                "last_vacuum",
                "last_autovacuum",
                "last_analyze",
                "last_autoanalyze",
            ]
        )
        for r in rows:
            w.writerow(
                [
                    r.get("schema"),
                    r.get("table"),
                    int(r.get("n_live_tup") or 0),
                    int(r.get("n_dead_tup") or 0),
                    int(r.get("total_bytes") or 0),
                    int(r.get("table_bytes") or 0),
                    int(r.get("index_bytes") or 0),
                    r.get("last_vacuum"),
                    r.get("last_autovacuum"),
                    r.get("last_analyze"),
                    r.get("last_autoanalyze"),
                ]
            )


def main() -> None:
    parser = argparse.ArgumentParser(prog="webapp-api-tenant-table-stats")
    parser.add_argument("--tenant", type=str, default=None)
    parser.add_argument("--db-url", type=str, default=None)
    parser.add_argument("--out", type=str, default=None)
    args = parser.parse_args()

    url = str(args.db_url or "").strip()
    tenant = str(args.tenant or "").strip()
    if not url and tenant:
        ti = _load_tenant_from_admin(tenant)
        if not ti:
            raise SystemExit(f"Tenant no encontrado: {tenant}")
        url = _build_tenant_db_url(ti.db_name)

    if not url:
        env_url = os.getenv("DATABASE_URL") or ""
        if env_url:
            url = env_url
    if not url:
        raise SystemExit("Falta --db-url o --tenant (o DATABASE_URL).")

    repo_root = Path(__file__).resolve().parents[3]
    out_csv = Path(args.out) if args.out else (repo_root / "docs" / "database" / "tenant-table-stats.csv")
    export_table_stats(url, out_csv)


if __name__ == "__main__":
    main()
