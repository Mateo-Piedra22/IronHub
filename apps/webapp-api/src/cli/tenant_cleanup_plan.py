import argparse
import csv
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from sqlalchemy import create_engine, text

from src.database.connection import AdminSessionLocal
from src.database.tenant_connection import _build_tenant_db_url


def _load_tenant_db_url(tenant: str) -> Optional[str]:
    ses = AdminSessionLocal()
    try:
        row = (
            ses.execute(
                text(
                    """
                    SELECT db_name
                    FROM gyms
                    WHERE LOWER(TRIM(subdominio)) = LOWER(TRIM(:s))
                    LIMIT 1
                    """
                ),
                {"s": str(tenant or "")},
            )
            .mappings()
            .first()
        )
        if not row:
            return None
        dbn = str(row.get("db_name") or "").strip()
        if not dbn:
            return None
        return _build_tenant_db_url(dbn)
    finally:
        ses.close()


def _read_csv(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8") as f:
        r = csv.DictReader(f)
        return [dict(row) for row in r]


def _table_has_rows(conn, table: str) -> bool:
    try:
        q = text(f'SELECT 1 FROM "{table}" LIMIT 1')
        return conn.execute(q).first() is not None
    except Exception:
        return True


def main() -> None:
    parser = argparse.ArgumentParser(prog="webapp-api-tenant-cleanup-plan")
    parser.add_argument("--tenant", type=str, default=None)
    parser.add_argument("--db-url", type=str, default=None)
    parser.add_argument("--audit-csv", type=str, default=None)
    parser.add_argument("--out-md", type=str, default=None)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[3]
    audit_csv = Path(args.audit_csv) if args.audit_csv else (repo_root / "docs" / "database" / "tenant-schema-audit.csv")
    if not audit_csv.exists():
        raise SystemExit(f"No existe audit csv: {audit_csv}")

    url = str(args.db_url or "").strip()
    tenant = str(args.tenant or "").strip()
    if not url and tenant:
        url = _load_tenant_db_url(tenant) or ""
    if not url:
        url = str(os.getenv("DATABASE_URL") or "").strip()
    if not url:
        raise SystemExit("Falta --db-url o --tenant (o DATABASE_URL).")

    out_md = Path(args.out_md) if args.out_md else (repo_root / "docs" / "database" / "tenant-cleanup-heavy.md")

    audit_rows = _read_csv(audit_csv)
    drop_candidates: List[Tuple[str, str]] = []
    with create_engine(url, pool_pre_ping=True).connect() as conn:
        for r in audit_rows:
            table = str(r.get("tabla") or "").strip()
            if not table:
                continue
            refs_sql = str(r.get("referencias_sql_(tabla_literal)") or "").strip()
            refs_model = str(r.get("referencias_modelo_(class)") or "").strip()
            rec = str(r.get("recomendacion") or "").strip().lower()
            if rec != "revisar":
                continue
            if refs_sql or refs_model:
                continue
            if _table_has_rows(conn, table):
                continue
            drop_candidates.append((table, str(r.get("orm_class") or "").strip()))

    out_md.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Plan pesado de limpieza (tenant)")
    lines.append("")
    lines.append("Este reporte cruza:")
    lines.append("- `tenant-schema-audit.csv` (referencias por código)")
    lines.append("- DB tenant actual (detección de tablas vacías por `SELECT 1 LIMIT 1`)")
    lines.append("")
    lines.append("## Candidatas a DROP seguro (sin referencias + vacías)")
    lines.append("")
    if not drop_candidates:
        lines.append("- (ninguna)")
    else:
        for t, cls in sorted(drop_candidates):
            lines.append(f"- {t} ({cls})")
    lines.append("")
    lines.append("## Siguiente paso")
    lines.append("")
    lines.append("- Crear una migración Alembic opcional que dropee estas tablas solo si existe el flag de entorno y están vacías.")

    out_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
