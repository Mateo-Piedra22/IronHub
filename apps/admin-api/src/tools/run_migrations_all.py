import os
import sys
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import quote_plus

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text

_here = Path(__file__).resolve()
_admin_api_root = _here.parents[2]
if str(_admin_api_root) not in sys.path:
    sys.path.insert(0, str(_admin_api_root))

from src.tenant_migrations import expected_tenant_head, migrate_tenant_db


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "apps").is_dir():
            return p
    return here.parents[3]


def _load_env_file(path: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        if not path.exists():
            return out
        for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip()
            if not k:
                continue
            if len(v) >= 2 and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
                v = v[1:-1]
            out[k] = v
    except Exception:
        return out
    return out


def _load_env() -> Dict[str, str]:
    root = _repo_root()
    files = [
        root / ".env",
        root / "apps" / "admin-api" / ".env",
        root / "apps" / "webapp-api" / ".env",
    ]
    merged: Dict[str, str] = {}
    for f in files:
        merged.update(_load_env_file(f))
    for k, v in os.environ.items():
        if k and v is not None:
            merged[k] = str(v)
    return merged


def _build_admin_sqlalchemy_url(env: Dict[str, str]) -> str:
    url = (env.get("ADMIN_DATABASE_URL") or env.get("DATABASE_URL") or "").strip()
    if url:
        return url
    host = (env.get("ADMIN_DB_HOST") or "").strip()
    port = (env.get("ADMIN_DB_PORT") or "5432").strip()
    db = (env.get("ADMIN_DB_NAME") or "ironhub_admin").strip()
    user = (env.get("ADMIN_DB_USER") or "").strip()
    password = env.get("ADMIN_DB_PASSWORD") or ""
    sslmode = (env.get("ADMIN_DB_SSLMODE") or "").strip()
    if not host or not user:
        raise RuntimeError("Faltan ADMIN_DB_HOST o ADMIN_DB_USER en .env")
    pw = quote_plus(password)
    base = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}"
    if sslmode:
        base += f"?sslmode={quote_plus(sslmode)}"
    return base


def _build_tenant_params(env: Dict[str, str]) -> Dict[str, str]:
    host = (env.get("TENANT_DB_HOST") or env.get("ADMIN_DB_HOST") or "").strip()
    port = (env.get("TENANT_DB_PORT") or env.get("ADMIN_DB_PORT") or "5432").strip()
    user = (env.get("TENANT_DB_USER") or env.get("ADMIN_DB_USER") or "").strip()
    password = env.get("TENANT_DB_PASSWORD")
    if password is None:
        password = env.get("ADMIN_DB_PASSWORD") or ""
    sslmode = (env.get("TENANT_DB_SSLMODE") or env.get("ADMIN_DB_SSLMODE") or "").strip()
    if not host or not user:
        raise RuntimeError("Faltan TENANT_DB_HOST o TENANT_DB_USER en .env")
    return {"host": host, "port": port, "user": user, "password": password, "sslmode": sslmode}


def _run_admin_alembic(env: Dict[str, str]) -> None:
    root = _repo_root()
    ini = (root / "apps" / "webapp-api" / "alembic_admin.ini").resolve()
    script_location = (root / "apps" / "webapp-api" / "alembic_admin").resolve()
    if not ini.exists() or not script_location.exists():
        raise RuntimeError("No se encontró alembic_admin en apps/webapp-api")
    cfg = Config(str(ini))
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", _build_admin_sqlalchemy_url(env))
    command.upgrade(cfg, "head")


def _fetch_gyms(admin_url: str) -> List[Tuple[int, str, str]]:
    eng = create_engine(admin_url, pool_pre_ping=True)
    with eng.connect() as conn:
        rows = conn.execute(text("SELECT id, db_name, subdominio FROM gyms ORDER BY id ASC")).fetchall()
    out: List[Tuple[int, str, str]] = []
    for r in rows:
        try:
            out.append((int(r[0]), str(r[1]), str(r[2])))
        except Exception:
            continue
    return out


def _tenant_current_version(tenant_params: Dict[str, str], db_name: str) -> Optional[str]:
    host = tenant_params["host"]
    port = tenant_params["port"]
    user = tenant_params["user"]
    pw = quote_plus(tenant_params["password"])
    sslmode = tenant_params.get("sslmode") or ""
    url = f"postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db_name}"
    if sslmode:
        url += f"?sslmode={quote_plus(sslmode)}"
    eng = create_engine(url, pool_pre_ping=True)
    with eng.connect() as conn:
        reg_ver = conn.execute(text("SELECT to_regclass('alembic_version')")).scalar()
        reg_suc = conn.execute(text("SELECT to_regclass('sucursales')")).scalar()
        if not reg_ver or not reg_suc:
            return None
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        return str(row[0]) if row and row[0] is not None else None


def main() -> int:
    env = _load_env()
    admin_url = _build_admin_sqlalchemy_url(env)
    tenant_params = _build_tenant_params(env)

    print("== Migraciones admin (alembic_admin) ==")
    _run_admin_alembic(env)
    print("OK: admin head aplicado")

    head = expected_tenant_head()
    print("== Migraciones tenants (alembic tenant) ==")
    if not head:
        print("ERROR: no se pudo resolver tenant head")
        return 2

    gyms = _fetch_gyms(admin_url)
    ok = 0
    skipped = 0
    failed = 0
    for gym_id, db_name, subdom in gyms:
        label = f"[{gym_id}:{subdom}]"
        try:
            current = _tenant_current_version(tenant_params, db_name)
        except Exception as e:
            msg = str(e).lower()
            if ("does not exist" in msg and "database" in msg) or ("invalidcatalogname" in msg):
                print(f"{label} db_missing")
                skipped += 1
                continue
            print(f"{label} status_error")
            failed += 1
            continue

        if current == head:
            skipped += 1
            continue

        try:
            migrate_tenant_db(
                user=tenant_params["user"],
                password=tenant_params["password"],
                host=tenant_params["host"],
                port=tenant_params["port"],
                db_name=db_name,
                sslmode=tenant_params.get("sslmode") or None,
            )
            ok += 1
            print(f"{label} migrated")
        except Exception as e:
            failed += 1
            print(f"{label} failed: {type(e).__name__}: {e}")
            traceback.print_exc()

    print(f"Resumen: migrated={ok} skipped={skipped} failed={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
