import hashlib
import os
import time
from contextlib import contextmanager
from typing import Optional

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text


def _lock_key(name: str) -> int:
    s = str(name or "").strip().lower()
    d = hashlib.blake2b(s.encode("utf-8"), digest_size=8).digest()
    n = int.from_bytes(d, "big", signed=False)
    return int(n % (2**63 - 1))


@contextmanager
def _advisory_lock(conn, *, name: str, timeout_seconds: int) -> None:
    key = _lock_key(name)
    deadline = time.time() + float(max(1, int(timeout_seconds)))
    while True:
        got = conn.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()
        if bool(got):
            break
        if time.time() >= deadline:
            raise TimeoutError(f"Timeout esperando advisory lock (key={key})")
        time.sleep(0.5)
    try:
        yield
    finally:
        try:
            conn.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
        except Exception:
            pass


def _alembic_cfg(*, sqlalchemy_url: str, cfg_path: str, script_location: str) -> Config:
    cfg = Config(cfg_path)
    cfg.set_main_option("script_location", script_location)
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url)
    return cfg


def _get_head_revision(cfg: Config) -> Optional[str]:
    try:
        script = ScriptDirectory.from_config(cfg)
        return script.get_current_head()
    except Exception:
        return None


def upgrade_head(
    *,
    sqlalchemy_url: str,
    cfg_path: str,
    script_location: str,
    lock_name: str,
    lock_timeout_seconds: int = 120,
    verify_revision: bool = True,
    verify_idempotent: bool = False,
) -> None:
    url = str(sqlalchemy_url or "").strip()
    if not url:
        raise ValueError("sqlalchemy_url vacío")

    cfg = _alembic_cfg(
        sqlalchemy_url=url,
        cfg_path=str(cfg_path),
        script_location=str(script_location),
    )

    head = _get_head_revision(cfg) if verify_revision else None
    engine = create_engine(url, pool_pre_ping=True)

    old_env = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        with engine.connect() as conn:
            with _advisory_lock(
                conn,
                name=str(lock_name),
                timeout_seconds=int(lock_timeout_seconds),
            ):
                cfg.attributes["connection"] = conn
                command.upgrade(cfg, "head")
                if verify_idempotent:
                    command.upgrade(cfg, "head")
                if verify_revision and head:
                    row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
                    current = str(row[0]) if row and row[0] is not None else ""
                    if current != str(head):
                        raise RuntimeError(f"alembic_version={current} != head={head}")
    finally:
        if old_env is None:
            os.environ.pop("DATABASE_URL", None)
        else:
            os.environ["DATABASE_URL"] = old_env


def upgrade_head_with_connection(
    *,
    connection,
    sqlalchemy_url: str,
    cfg_path: str,
    script_location: str,
    lock_name: str,
    lock_timeout_seconds: int = 120,
    verify_revision: bool = True,
    verify_idempotent: bool = False,
) -> None:
    url = str(sqlalchemy_url or "").strip()
    if not url:
        raise ValueError("sqlalchemy_url vacío")

    cfg = _alembic_cfg(
        sqlalchemy_url=url,
        cfg_path=str(cfg_path),
        script_location=str(script_location),
    )
    head = _get_head_revision(cfg) if verify_revision else None

    old_env = os.environ.get("DATABASE_URL")
    os.environ["DATABASE_URL"] = url
    try:
        with _advisory_lock(
            connection,
            name=str(lock_name),
            timeout_seconds=int(lock_timeout_seconds),
        ):
            cfg.attributes["connection"] = connection
            command.upgrade(cfg, "head")
            if verify_idempotent:
                command.upgrade(cfg, "head")
            if verify_revision and head:
                row = connection.execute(
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
