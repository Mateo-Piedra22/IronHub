"""
Tenant-aware database connection management for multi-tenant gym system.

This module provides per-tenant SQLAlchemy engine and session management,
allowing each gym (tenant) to have its own isolated database connection.

SECURITY FEATURES:
- Tenant name validation (alphanumeric + hyphen only)
- Status verification (suspended tenants blocked)
- Connection health checks with retry
- Proper error handling and logging
- Thread-safe caching
"""

import os
import re
import time
import logging
import threading
import contextvars
from typing import Dict, Any, Optional, Tuple
from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError, OperationalError

logger = logging.getLogger(__name__)
from pathlib import Path

from src.database.migration_runner import upgrade_head_with_connection

# ============================================================================
# CONFIGURATION
# ============================================================================

# Maximum number of cached tenant connections
MAX_TENANT_CACHE_SIZE = 50

# Connection pool settings per tenant
try:
    _IS_SERVERLESS = bool(
        os.getenv("VERCEL")
        or os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        or os.getenv("K_SERVICE")
    )
except Exception:
    _IS_SERVERLESS = False
try:
    POOL_SIZE_PER_TENANT = int(
        os.getenv("TENANT_DB_POOL_SIZE", "1" if _IS_SERVERLESS else "5")
    )
except Exception:
    POOL_SIZE_PER_TENANT = 1 if _IS_SERVERLESS else 5
try:
    MAX_OVERFLOW_PER_TENANT = int(
        os.getenv("TENANT_DB_MAX_OVERFLOW", "0" if _IS_SERVERLESS else "10")
    )
except Exception:
    MAX_OVERFLOW_PER_TENANT = 0 if _IS_SERVERLESS else 10
POOL_RECYCLE_SECONDS = 1800

# Connection retry settings
MAX_CONNECTION_RETRIES = 3
RETRY_DELAY_SECONDS = 1.0

# Subdomain/tenant name validation regex (alphanumeric, hyphens, 3-63 chars)
VALID_TENANT_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$|^[a-z0-9]{1,3}$")

# ============================================================================
# THREAD-SAFE CACHE
# ============================================================================

_tenant_engines: Dict[str, Engine] = {}
_tenant_session_factories: Dict[str, sessionmaker] = {}
_tenant_db_info: Dict[str, Dict[str, Any]] = {}  # Cache for tenant db_name and status
_tenant_lock = threading.RLock()
_tenant_last_access: Dict[str, float] = {}  # For LRU eviction
_tenant_migration_checked: Dict[str, float] = {}

# CANONICAL context variable for current tenant - ALL modules should import from here
CURRENT_TENANT = contextvars.ContextVar("current_tenant", default=None)


def set_current_tenant(tenant: str):
    """Set the current tenant subdomain in context."""
    CURRENT_TENANT.set(tenant.strip().lower() if tenant else None)


def get_current_tenant() -> Optional[str]:
    """Get the current tenant subdomain from context."""
    try:
        return CURRENT_TENANT.get()
    except LookupError:
        return None


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================


def validate_tenant_name(tenant: str) -> Tuple[bool, str]:
    """
    Validate that a tenant name is safe and properly formatted.

    Returns:
        Tuple of (is_valid: bool, error_message: str)
    """
    if not tenant:
        return False, "Tenant name cannot be empty"

    tenant = tenant.strip().lower()

    if len(tenant) < 1:
        return False, "Tenant name too short"

    if len(tenant) > 63:
        return False, "Tenant name too long (max 63 chars)"

    # Check for SQL injection attempts
    dangerous_chars = ["'", '"', ";", "--", "/*", "*/", "\\", "\x00"]
    for char in dangerous_chars:
        if char in tenant:
            return False, f"Invalid character in tenant name: {char}"

    # Must match subdomain pattern
    if not VALID_TENANT_PATTERN.match(tenant):
        return False, "Tenant name must be alphanumeric with optional hyphens"

    # Cannot be reserved names
    reserved = ["admin", "www", "api", "static", "assets", "test", "staging", "prod"]
    if tenant in reserved:
        return False, f"Tenant name '{tenant}' is reserved"

    return True, ""


def sanitize_db_name(db_name: str) -> str:
    """
    Sanitize a database name to prevent injection.
    Only allows alphanumeric, underscore, and hyphen.
    """
    if not db_name:
        return ""
    # Replace any non-alphanumeric/underscore/hyphen with underscore
    sanitized = re.sub(r"[^a-z0-9_-]", "_", db_name.lower().strip())
    # Ensure it starts with a letter or underscore
    if sanitized and sanitized[0].isdigit():
        sanitized = "_" + sanitized
    return sanitized[:63]  # PostgreSQL max identifier length


# ============================================================================
# ADMIN DATABASE LOOKUP
# ============================================================================


def _get_tenant_info_from_admin(tenant: str) -> Optional[Dict[str, Any]]:
    """
    Look up tenant information from the admin database.

    Returns dict with:
        - db_name: str
        - status: str (active, suspended, maintenance)
        - suspended_reason: str | None
        - suspended_until: datetime | None
    """
    if not tenant:
        return None

    tenant = tenant.strip().lower()

    # Check cache first (with 60s TTL)
    with _tenant_lock:
        cached = _tenant_db_info.get(tenant)
        if cached and (time.time() - cached.get("_cached_at", 0)) < 60:
            return cached

    try:
        from src.database.raw_manager import RawPostgresManager

        admin_params = {
            "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
            "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
            "database": os.getenv(
                "ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")
            ),
            "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
            "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            "sslmode": os.getenv(
                "ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")
            ),
        }

        db = RawPostgresManager(connection_params=admin_params)
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, db_name, status, suspended_reason, suspended_until, nombre
                FROM gyms 
                WHERE subdominio = %s
            """,
                (tenant,),
            )
            row = cur.fetchone()

            if row:
                info = {
                    "gym_id": int(row[0]) if row[0] else None,
                    "db_name": str(row[1]).strip() if row[1] else None,
                    "status": str(row[2]).strip() if row[2] else "active",
                    "suspended_reason": str(row[3]) if row[3] else None,
                    "suspended_until": row[4],
                    "nombre": str(row[5]) if row[5] else tenant,
                    "_cached_at": time.time(),
                }

                # Cache the result
                with _tenant_lock:
                    _tenant_db_info[tenant] = info

                return info

    except Exception as e:
        logger.warning(f"Failed to get tenant info from admin for '{tenant}': {e}")

    return None


def _get_tenant_db_name(tenant: str) -> Optional[str]:
    """Look up the database name for a tenant from the admin database."""
    info = _get_tenant_info_from_admin(tenant)
    if info and info.get("db_name"):
        return info["db_name"]

    # Fallback: construct db_name from tenant subdomain
    suffix = os.getenv("TENANT_DB_SUFFIX", "_db")
    return f"{tenant}{suffix}"


def get_tenant_gym_id(tenant: str) -> Optional[int]:
    """Look up the gym_id for a tenant from the admin database."""
    info = _get_tenant_info_from_admin(tenant)
    if info and info.get("gym_id"):
        return info["gym_id"]
    return None


def get_current_tenant_gym_id() -> Optional[int]:
    """Get the gym_id for the current tenant from context."""
    tenant = get_current_tenant()
    if not tenant:
        return None
    return get_tenant_gym_id(tenant)


def is_tenant_active(tenant: str) -> Tuple[bool, str]:
    """
    Check if a tenant is active and can be connected to.

    Returns:
        Tuple of (is_active: bool, reason: str)
    """
    info = _get_tenant_info_from_admin(tenant)

    if not info:
        return False, "Tenant not found"

    status = info.get("status", "active").lower()

    if status == "active":
        return True, ""

    if status == "suspended":
        reason = info.get("suspended_reason") or "Cuenta suspendida"
        until = info.get("suspended_until")
        if until and isinstance(until, datetime):
            reason += f" (hasta {until.strftime('%d/%m/%Y')})"
        return False, reason

    if status == "maintenance":
        return False, "Gimnasio en mantenimiento"

    return False, f"Estado desconocido: {status}"


# ============================================================================
# CONNECTION URL BUILDING
# ============================================================================


def _build_tenant_db_url(db_name: str) -> str:
    """Build a database URL for a specific tenant database."""
    # Sanitize db_name to prevent injection
    safe_db_name = sanitize_db_name(db_name)
    if not safe_db_name:
        raise ValueError("Invalid database name")

    user = os.getenv("DB_USER", "postgres")
    password = os.getenv("DB_PASSWORD", "")
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    sslmode = os.getenv("DB_SSLMODE", "")

    # URL encode password to handle special characters
    from urllib.parse import quote_plus

    safe_password = quote_plus(password) if password else ""

    auth = f"{user}:{safe_password}" if safe_password else user
    base_url = f"postgresql+psycopg2://{auth}@{host}:{port}/{safe_db_name}"

    if sslmode:
        base_url += f"?sslmode={sslmode}"

    return base_url


# ============================================================================
# ENGINE & SESSION MANAGEMENT
# ============================================================================


def _evict_lru_tenant():
    """Evict least recently used tenant from cache if over limit."""
    with _tenant_lock:
        if len(_tenant_engines) <= MAX_TENANT_CACHE_SIZE:
            return

        # Find LRU tenant
        if not _tenant_last_access:
            return

        lru_tenant = min(_tenant_last_access, key=_tenant_last_access.get)

        # Evict
        logger.info(f"Evicting LRU tenant from cache: {lru_tenant}")
        clear_tenant_cache(lru_tenant)


def get_tenant_engine(tenant: str, verify_status: bool = True) -> Optional[Engine]:
    """
    Get or create a SQLAlchemy engine for the specified tenant.

    Args:
        tenant: The tenant subdomain
        verify_status: If True, verify tenant is active before connecting

    Returns:
        SQLAlchemy Engine or None if tenant invalid/suspended
    """
    if not tenant:
        return None

    tenant = tenant.strip().lower()

    # Validate tenant name
    is_valid, error = validate_tenant_name(tenant)
    if not is_valid:
        logger.warning(f"Invalid tenant name '{tenant}': {error}")
        return None

    # Verify tenant is active
    if verify_status:
        is_active, reason = is_tenant_active(tenant)
        if not is_active:
            logger.warning(f"Tenant '{tenant}' is not active: {reason}")
            return None

    should_auto_migrate = str(os.getenv("AUTO_MIGRATE_TENANT", "true")).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    auto_migrate_required = str(
        os.getenv("AUTO_MIGRATE_TENANT_REQUIRED", "true")
    ).strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )
    try:
        auto_migrate_check_ttl = int(os.getenv("AUTO_MIGRATE_TENANT_CHECK_TTL_SECONDS", "300"))
    except Exception:
        auto_migrate_check_ttl = 300

    engine = None
    db_name = None
    db_url = None

    with _tenant_lock:
        # Update last access time
        _tenant_last_access[tenant] = time.time()

        # Return cached engine if exists
        if tenant in _tenant_engines:
            engine = _tenant_engines[tenant]
            # Quick health check
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                db_name = _get_tenant_db_name(tenant)
                try:
                    db_url = _build_tenant_db_url(db_name) if db_name else None
                except Exception:
                    db_url = None
            except Exception as e:
                logger.warning(
                    f"Cached engine for '{tenant}' unhealthy, recreating: {e}"
                )
                try:
                    engine.dispose()
                except Exception:
                    pass
                try:
                    del _tenant_engines[tenant]
                except Exception:
                    pass
                if tenant in _tenant_session_factories:
                    try:
                        del _tenant_session_factories[tenant]
                    except Exception:
                        pass
                engine = None
        if engine is None:
            _evict_lru_tenant()

            db_name = _get_tenant_db_name(tenant)
            if not db_name:
                logger.error(f"Could not determine db_name for tenant: {tenant}")
                return None

            try:
                db_url = _build_tenant_db_url(db_name)
            except ValueError as e:
                logger.error(f"Invalid db_name for tenant '{tenant}': {e}")
                return None

            last_error = None
            for attempt in range(MAX_CONNECTION_RETRIES):
                try:
                    engine = create_engine(
                        db_url,
                        pool_pre_ping=True,
                        pool_size=POOL_SIZE_PER_TENANT,
                        max_overflow=MAX_OVERFLOW_PER_TENANT,
                        pool_recycle=POOL_RECYCLE_SECONDS,
                        connect_args={
                            "options": "-c timezone=America/Argentina/Buenos_Aires",
                            "connect_timeout": 10,
                        },
                    )

                    with engine.connect() as conn:
                        conn.execute(text("SELECT 1"))

                    _tenant_engines[tenant] = engine
                    logger.info(f"Created engine for tenant: {tenant} -> {db_name}")
                    break

                except (OperationalError, SQLAlchemyError) as e:
                    last_error = e
                    logger.warning(
                        f"Connection attempt {attempt + 1}/{MAX_CONNECTION_RETRIES} failed for tenant '{tenant}': {e}"
                    )
                    if attempt < MAX_CONNECTION_RETRIES - 1:
                        time.sleep(RETRY_DELAY_SECONDS * (attempt + 1))

            if engine is None:
                logger.error(
                    f"Failed to create engine for tenant '{tenant}' after {MAX_CONNECTION_RETRIES} attempts: {last_error}"
                )
                return None

    if not should_auto_migrate:
        return engine

    try:
        now_ts = time.time()
        with _tenant_lock:
            last = float(_tenant_migration_checked.get(tenant) or 0.0)
        if (now_ts - last) < float(max(10, auto_migrate_check_ttl)):
            return engine

        root = Path(__file__).resolve().parents[2]
        cfg_path = str((root / "alembic.ini").resolve())
        script_location = str((root / "alembic").resolve())
        with engine.connect() as conn:
            upgrade_head_with_connection(
                connection=conn,
                sqlalchemy_url=str(db_url or ""),
                cfg_path=cfg_path,
                script_location=script_location,
                lock_name=f"tenant:{db_name or tenant}",
                lock_timeout_seconds=300,
                verify_revision=True,
                verify_idempotent=False,
            )
        with _tenant_lock:
            _tenant_migration_checked[tenant] = now_ts
        return engine
    except Exception as e:
        logger.error(f"Auto-migrate tenant failed for '{tenant}': {e}")
        if auto_migrate_required:
            try:
                with _tenant_lock:
                    if tenant in _tenant_engines:
                        try:
                            _tenant_engines[tenant].dispose()
                        except Exception:
                            pass
                        del _tenant_engines[tenant]
                    if tenant in _tenant_session_factories:
                        del _tenant_session_factories[tenant]
            except Exception:
                pass
            return None
        return engine


def get_tenant_session_factory(tenant: str) -> Optional[sessionmaker]:
    """Get or create a session factory for the specified tenant."""
    if not tenant:
        return None

    tenant = tenant.strip().lower()

    with _tenant_lock:
        # Return cached factory if exists and engine is valid
        if tenant in _tenant_session_factories:
            # Verify the underlying engine is still valid
            if tenant in _tenant_engines:
                return _tenant_session_factories[tenant]

        # Get or create engine
        engine = get_tenant_engine(tenant)
        if not engine:
            return None

        # Create session factory
        factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        _tenant_session_factories[tenant] = factory
        return factory


def get_current_tenant_session() -> Optional[Session]:
    """Get a session for the current tenant (from context variable)."""
    try:
        tenant = CURRENT_TENANT.get()
    except LookupError:
        tenant = None

    if not tenant:
        logger.warning("No current tenant set, cannot create session")
        return None

    factory = get_tenant_session_factory(tenant)
    if not factory:
        return None

    return factory()


@contextmanager
def tenant_session_scope(tenant: str = None):
    """
    Context manager for tenant database sessions with auto-cleanup.

    Usage:
        with tenant_session_scope('gym_subdomain') as session:
            user = session.query(Usuario).first()
    """
    if tenant is None:
        try:
            tenant = CURRENT_TENANT.get()
        except LookupError:
            tenant = None

    if not tenant:
        raise ValueError("No tenant specified and no CURRENT_TENANT context var set")

    factory = get_tenant_session_factory(tenant)
    if not factory:
        raise RuntimeError(f"Could not create session factory for tenant: {tenant}")

    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ============================================================================
# CACHE MANAGEMENT
# ============================================================================


def clear_tenant_cache(tenant: str = None):
    """Clear cached engines/sessions for a specific tenant or all tenants."""
    with _tenant_lock:
        if tenant:
            tenant = tenant.strip().lower()
            if tenant in _tenant_session_factories:
                del _tenant_session_factories[tenant]
            if tenant in _tenant_engines:
                try:
                    _tenant_engines[tenant].dispose()
                except Exception:
                    pass
                del _tenant_engines[tenant]
            if tenant in _tenant_db_info:
                del _tenant_db_info[tenant]
            if tenant in _tenant_last_access:
                del _tenant_last_access[tenant]
        else:
            # Clear all
            _tenant_session_factories.clear()

            for engine in _tenant_engines.values():
                try:
                    engine.dispose()
                except Exception:
                    pass
            _tenant_engines.clear()
            _tenant_db_info.clear()
            _tenant_last_access.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get statistics about the tenant connection cache."""
    with _tenant_lock:
        return {
            "cached_engines": len(_tenant_engines),
            "cached_sessions": len(_tenant_session_factories),
            "cached_info": len(_tenant_db_info),
            "tenants": list(_tenant_engines.keys()),
            "max_cache_size": MAX_TENANT_CACHE_SIZE,
        }


def invalidate_tenant_info(tenant: str):
    """Invalidate cached tenant info (e.g., after status change)."""
    with _tenant_lock:
        if tenant in _tenant_db_info:
            del _tenant_db_info[tenant]
