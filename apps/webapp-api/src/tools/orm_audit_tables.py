from __future__ import annotations

import re
from pathlib import Path


def _find_repo_root(start: Path) -> Path:
    for p in [start] + list(start.parents):
        if (p / "apps").is_dir():
            return p
    return start.parents[3]


def _extract_tables_from_sql(text: str) -> set[str]:
    out: set[str] = set()
    for pat in (
        r"CREATE TABLE\s+IF NOT EXISTS\s+([a-zA-Z0-9_]+)\s*\(",
        r"CREATE TABLE\s+([a-zA-Z0-9_]+)\s*\(",
    ):
        out |= set(re.findall(pat, text))
    return out


def _extract_tablenames_from_orm(text: str) -> set[str]:
    return set(re.findall(r'__tablename__\s*=\s*"([a-zA-Z0-9_]+)"', text))


def main() -> int:
    here = Path(__file__).resolve()
    root = _find_repo_root(here)
    webapp = (root / "apps" / "webapp-api").resolve()
    baseline = (webapp / "alembic" / "versions" / "0001_tenant_schema_baseline.py").read_text(
        encoding="utf-8"
    )
    orm = (webapp / "src" / "models" / "orm_models.py").read_text(encoding="utf-8")
    mig_tables: set[str] = set()
    for fp in sorted((webapp / "alembic" / "versions").glob("*.py")):
        mig_tables |= _extract_tables_from_sql(fp.read_text(encoding="utf-8"))
    baseline_tables = _extract_tables_from_sql(baseline)
    all_tables = baseline_tables | mig_tables
    orm_tables = _extract_tablenames_from_orm(orm)
    missing = sorted(all_tables - orm_tables)
    extra = sorted(orm_tables - all_tables)
    print(f"tables_in_migrations={len(all_tables)} orm_tables={len(orm_tables)}")
    print(f"missing={len(missing)} extra={len(extra)}")
    if missing:
        print("MISSING")
        for t in missing:
            print(t)
    if extra:
        print("EXTRA")
        for t in extra:
            print(t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

