import base64
import gzip
import os
import sys
import hashlib
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from .tenant_migrations_bundle import EMBEDDED_FILES


def _materialize_embedded_webapp_api_path() -> Path:
    root = Path(tempfile.gettempdir()).resolve() / "tenant_migrations"
    webapp_api = (root / "webapp-api").resolve()
    cfg_path = webapp_api / "alembic.ini"
    script_location = webapp_api / "alembic"
    if cfg_path.exists() and script_location.exists():
        return webapp_api

    root.mkdir(parents=True, exist_ok=True)
    for rel, b64 in EMBEDDED_FILES.items():
        out_path = (root / rel).resolve()
        if out_path.exists():
            continue
        data = gzip.decompress(base64.b64decode(b64))
        out_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = out_path.with_name(out_path.name + ".tmp")
        tmp_path.write_bytes(data)
        tmp_path.replace(out_path)
    return webapp_api


def expected_tenant_head() -> Optional[str]:
    webapp_api = _resolve_webapp_api_path()
    cfg_path = (webapp_api / "alembic.ini").resolve()
    script_location = (webapp_api / "alembic").resolve()
    if not cfg_path.exists() or not script_location.exists():
        webapp_api = _materialize_embedded_webapp_api_path()
        cfg_path = (webapp_api / "alembic.ini").resolve()
        script_location = (webapp_api / "alembic").resolve()
    if not cfg_path.exists() or not script_location.exists():
        return None

    cfg = Config(str(cfg_path))
    cfg.set_main_option("script_location", str(script_location))
    try:
        return ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        return None


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for p in [here] + list(here.parents):
        if (p / "apps").is_dir():
            return p
    return here.parents[2]


def _build_db_url(
    *,
    user: str,
    password: str,
    host: str,
    port: str,
    db_name: str,
    sslmode: Optional[str],
) -> str:
    url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db_name}"
    sm = (sslmode or "").strip()
    if sm:
        url += f"?sslmode={sm}"
    return url


def _resolve_webapp_api_path() -> Path:
    env_root = (os.getenv("TENANT_MIGRATIONS_ROOT") or "").strip()
    if env_root:
        candidates: list[Path] = []
        try:
            raw = Path(env_root)
            if raw.is_absolute():
                candidates.append(raw)
            else:
                candidates.append(Path.cwd() / raw)
                candidates.append(Path(__file__).resolve().parents[1] / raw)
        except Exception:
            candidates = []
        for c in candidates:
            try:
                p = c.resolve()
            except Exception:
                p = c
            if p.exists():
                return p

    root = _repo_root()
    p = (root / "apps" / "webapp-api").resolve()
    if p.exists():
        return p

    bundled = (Path(__file__).resolve().parents[1] / "tenant_migrations" / "webapp-api").resolve()
    if bundled.exists():
        return bundled

    return _materialize_embedded_webapp_api_path()


def _lock_key(name: str) -> int:
    s = str(name or "").strip().lower()
    d = hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest()
    n = int.from_bytes(d, "big", signed=False)
    return int(n % (2**63 - 1))


@contextmanager
def _advisory_lock(conn, *, name: str, timeout_seconds: int) -> None:
    key = _lock_key(name)
    deadline = time.time() + float(max(1, int(timeout_seconds)))
    lock_conn = conn.execution_options(isolation_level="AUTOCOMMIT")
    while True:
        got = lock_conn.execute(
            text("SELECT pg_try_advisory_lock(:k)"), {"k": key}
        ).scalar()
        if bool(got):
            break
        if time.time() >= deadline:
            raise TimeoutError(f"Timeout esperando advisory lock (key={key})")
        time.sleep(0.5)
    try:
        yield
    finally:
        try:
            lock_conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
        except Exception:
            pass


def migrate_tenant_db(
    *,
    user: str,
    password: str,
    host: str,
    port: str,
    db_name: str,
    sslmode: Optional[str] = None,
) -> None:
    webapp_api = _resolve_webapp_api_path()
    cfg_path = (webapp_api / "alembic.ini").resolve()
    script_location = (webapp_api / "alembic").resolve()

    if not cfg_path.exists() or not script_location.exists():
        webapp_api = _materialize_embedded_webapp_api_path()
        cfg_path = (webapp_api / "alembic.ini").resolve()
        script_location = (webapp_api / "alembic").resolve()
        if not cfg_path.exists() or not script_location.exists():
            raise FileNotFoundError(
                f"No se encontró Alembic tenant. Esperado: {cfg_path} y {script_location}"
            )

    added_path = False
    if str(webapp_api) not in sys.path:
        sys.path.insert(0, str(webapp_api))
        added_path = True

    sqlalchemy_url = _build_db_url(
        user=str(user),
        password=str(password),
        host=str(host),
        port=str(port),
        db_name=str(db_name),
        sslmode=sslmode,
    )

    cfg = Config(str(cfg_path)) if cfg_path.exists() else Config()
    cfg.set_main_option("script_location", str(script_location))
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)

    head = None
    try:
        head = ScriptDirectory.from_config(cfg).get_current_head()
    except Exception:
        head = None

    engine = create_engine(sqlalchemy_url, pool_pre_ping=True)
    old_env = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = sqlalchemy_url
    try:
        with engine.connect() as conn:
            with _advisory_lock(conn, name=f"tenant:{db_name}", timeout_seconds=300):
                try:
                    conn.commit()
                except Exception:
                    pass
                cfg.attributes["connection"] = conn
                command.upgrade(cfg, "head")
                try:
                    conn.commit()
                except Exception:
                    pass
                if head:
                    row = conn.execute(
                        text("SELECT version_num FROM alembic_version")
                    ).fetchone()
                    current = str(row[0]) if row and row[0] is not None else ""
                    if current != str(head):
                        raise RuntimeError(f"alembic_version={current} != head={head}")
    finally:
        if old_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_env
        if added_path:
            try:
                sys.path.remove(str(webapp_api))
            except ValueError:
                pass
