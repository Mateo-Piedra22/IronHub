from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


RE_TABLE = re.compile(r'__tablename__\s*=\s*"([^"]+)"')
RE_CLASS = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
RE_CREATE_TABLE = re.compile(r"op\.create_table\(\s*'([^']+)'")
RE_DROP_TABLE = re.compile(r"op\.drop_table\(\s*'([^']+)'")


@dataclass(frozen=True)
class TableInfo:
    table: str
    orm_class: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return path.read_text(encoding="latin-1", errors="ignore")


def parse_orm_tables(orm_models_path: Path) -> Dict[str, TableInfo]:
    text = _read_text(orm_models_path)
    tables: Dict[str, TableInfo] = {}

    lines = text.splitlines()
    current_class: Optional[str] = None
    for line in lines:
        m_cls = RE_CLASS.match(line)
        if m_cls:
            current_class = m_cls.group(1)
            continue
        m_tab = RE_TABLE.search(line)
        if m_tab and current_class:
            table = m_tab.group(1)
            tables[table] = TableInfo(table=table, orm_class=current_class)
            current_class = None

    return tables


def parse_migrations(alembic_versions_dir: Path) -> Dict[str, Dict[str, List[str]]]:
    out: Dict[str, Dict[str, List[str]]] = {}
    for p in sorted(alembic_versions_dir.glob("*.py")):
        txt = _read_text(p)
        creates = RE_CREATE_TABLE.findall(txt)
        drops = RE_DROP_TABLE.findall(txt)
        for t in creates:
            out.setdefault(t, {}).setdefault("created_in", []).append(p.name)
        for t in drops:
            out.setdefault(t, {}).setdefault("dropped_in", []).append(p.name)
    return out


def scan_usage(
    roots: Sequence[Path],
    needles: Sequence[str],
    *,
    file_globs: Sequence[str] = ("**/*.py",),
) -> Dict[str, List[str]]:
    usage: Dict[str, List[str]] = {n: [] for n in needles}
    for root in roots:
        for g in file_globs:
            for p in root.glob(g):
                if not p.is_file():
                    continue
                txt = _read_text(p)
                for n in needles:
                    if n in txt:
                        usage[n].append(str(p))
    return usage


def _categorize(table: str) -> Tuple[str, str]:
    consolidate = {
        "usuario_sucursales",
        "usuario_accesos_sucursales",
        "membership_sucursales",
        "tipo_cuota_sucursales",
        "gym_config",
        "configuracion",
    }
    if table in consolidate:
        return ("consolidar", "Solapamiento conocido de fuentes de verdad")
    return ("mantener", "")


def _short_paths(paths: Iterable[str], base: Path) -> str:
    out: List[str] = []
    for p in paths:
        try:
            out.append(str(Path(p).resolve().relative_to(base.resolve())))
        except Exception:
            out.append(p)
    out = sorted(set(out))
    if len(out) > 12:
        out = out[:12] + ["(más...)"]
    return ";".join(out)


def write_csv(
    repo_root: Path,
    out_path: Path,
    *,
    orm_models_path: Path,
    alembic_versions_dir: Path,
) -> None:
    orm_tables = parse_orm_tables(orm_models_path)
    migrations = parse_migrations(alembic_versions_dir)

    tables = sorted(set(orm_tables.keys()) | set(migrations.keys()))
    orm_needles = [f'__tablename__ = "{t}"' for t in tables]
    sql_needles = tables
    model_needles = [orm_tables[t].orm_class for t in tables if t in orm_tables]

    router_root = repo_root / "apps" / "webapp-api" / "src" / "routers"
    services_root = repo_root / "apps" / "webapp-api" / "src" / "services"
    db_root = repo_root / "apps" / "webapp-api" / "src" / "database"

    usage_sql = scan_usage([router_root, services_root, db_root], sql_needles)
    usage_models = scan_usage([router_root, services_root, db_root], model_needles)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(
            [
                "tabla",
                "orm_class",
                "created_in_migrations",
                "dropped_in_migrations",
                "referencias_sql_(tabla_literal)",
                "referencias_modelo_(class)",
                "recomendacion",
                "nota",
            ]
        )
        for t in tables:
            orm_cls = orm_tables.get(t).orm_class if t in orm_tables else ""
            mig = migrations.get(t, {})
            created_in = ",".join(sorted(set(mig.get("created_in", []))))
            dropped_in = ",".join(sorted(set(mig.get("dropped_in", []))))
            refs_sql = _short_paths(usage_sql.get(t, []), repo_root)
            refs_model = _short_paths(usage_models.get(orm_cls, []), repo_root) if orm_cls else ""
            rec, note = _categorize(t)
            w.writerow([t, orm_cls, created_in, dropped_in, refs_sql, refs_model, rec, note])


def main(argv: Optional[Sequence[str]] = None) -> int:
    repo_root = Path(__file__).resolve().parents[4]
    out_path = repo_root / "docs" / "database" / "tenant-schema-audit.csv"
    orm_models_path = repo_root / "apps" / "webapp-api" / "src" / "models" / "orm_models.py"
    alembic_versions_dir = repo_root / "apps" / "webapp-api" / "alembic" / "versions"
    write_csv(
        repo_root,
        out_path,
        orm_models_path=orm_models_path,
        alembic_versions_dir=alembic_versions_dir,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
