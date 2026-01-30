import argparse
import os
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.dialects import postgresql

from src.database.connection import AdminSessionLocal
from src.database.tenant_connection import _build_tenant_db_url
from src.models.orm_models import Base


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


def _type_sig(t) -> str:
    try:
        return str(t.compile(dialect=postgresql.dialect()))
    except Exception:
        return str(t)


def audit_db(url: str, *, strict: bool) -> list[str]:
    engine = create_engine(url, pool_pre_ping=True)
    insp = inspect(engine)
    db_tables = set(insp.get_table_names())
    errors: list[str] = []

    model_tables = list(Base.metadata.sorted_tables)
    model_table_names = {t.name for t in model_tables}

    missing_tables = sorted([t for t in model_table_names if t not in db_tables])
    if missing_tables:
        errors.append(f"Tablas faltantes: {', '.join(missing_tables)}")

    if strict:
        extra_tables = sorted([t for t in db_tables if t not in model_table_names and t != "alembic_version"])
        if extra_tables:
            errors.append(f"Tablas extra: {', '.join(extra_tables)}")

    for t in model_tables:
        if t.name not in db_tables:
            continue
        cols_db = {c["name"]: c for c in insp.get_columns(t.name)}
        cols_model = {c.name: c for c in t.columns}

        missing_cols = [c for c in cols_model.keys() if c not in cols_db]
        if missing_cols:
            errors.append(f"{t.name}: columnas faltantes: {', '.join(sorted(missing_cols))}")

        if strict:
            extra_cols = [c for c in cols_db.keys() if c not in cols_model]
            if extra_cols:
                errors.append(f"{t.name}: columnas extra: {', '.join(sorted(extra_cols))}")

        for name, mc in cols_model.items():
            dc = cols_db.get(name)
            if not dc:
                continue
            mt = _type_sig(mc.type)
            dt = _type_sig(dc.get("type"))
            if mt != dt:
                errors.append(f"{t.name}.{name}: tipo {dt} != {mt}")
            mn = bool(mc.nullable)
            dn = bool(dc.get("nullable"))
            if mn != dn:
                errors.append(f"{t.name}.{name}: nullable {dn} != {mn}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(prog="webapp-api-schema-audit")
    parser.add_argument("--tenant", type=str, default=None)
    parser.add_argument("--db-url", type=str, default=None)
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    strict = bool(args.strict)
    url = str(args.db_url or "").strip()
    if not url and args.tenant:
        ti = _load_tenant_from_admin(str(args.tenant))
        if not ti:
            raise SystemExit(f"Tenant no encontrado: {args.tenant}")
        url = _build_tenant_db_url(ti.db_name)

    if not url:
        env_url = os.getenv("DATABASE_URL") or ""
        if env_url:
            url = env_url
    if not url:
        raise SystemExit("Falta --db-url o --tenant (o DATABASE_URL).")

    errors = audit_db(url, strict=strict)
    if errors:
        raise SystemExit("Schema audit falló:\n" + "\n".join(errors))


if __name__ == "__main__":
    main()

