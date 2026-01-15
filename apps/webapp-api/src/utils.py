import sys
import os
import re
import logging
import threading
import contextvars
from pathlib import Path
from typing import Dict, List, Any, Optional
import urllib.parse
import psycopg2
import psycopg2.extras
from psycopg2 import sql

from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse

# Import dependencies - simplified for standalone API
try:
    from src.dependencies import CURRENT_TENANT, get_db_session
except ImportError:
    CURRENT_TENANT = None
    get_db_session = None

# Helper class to wrap database session with obtener_configuracion method
class _DatabaseWrapper:
    def __init__(self, session):
        self._session = session
    
    def obtener_configuracion(self, clave: str, timeout_ms: int = 1000) -> Optional[str]:
        """Get configuration value from configuracion table."""
        try:
            from sqlalchemy import text
            result = self._session.execute(
                text("SELECT valor FROM configuracion WHERE clave = :clave LIMIT 1"),
                {"clave": clave}
            )
            row = result.fetchone()
            if row:
                return str(row[0])
        except Exception:
            pass
        return None

def get_db():
    """Get database wrapper with configuration access."""
    try:
        from src.database.connection import SessionLocal
        session = SessionLocal()
        return _DatabaseWrapper(session)
    except Exception:
        return None

def get_admin_db():
    """Get admin database connection for cross-tenant operations."""
    try:
        # Try to import and return the admin service
        from src.dependencies import get_admin_db as deps_get_admin_db
        return deps_get_admin_db()
    except ImportError:
        pass
    # Fallback: try to create a direct admin connection
    try:
        import os
        admin_url = os.getenv("ADMIN_DATABASE_URL")
        if admin_url:
            # Create a simple wrapper for admin DB
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            engine = create_engine(admin_url)
            Session = sessionmaker(bind=engine)
            return _DatabaseWrapper(Session())
    except Exception:
        pass
    return None

DatabaseManager = None


def read_theme_vars(path: Path) -> Dict[str, str]:
    return {}

logger = logging.getLogger(__name__)

# Global cache for tenant DBs
_tenant_dbs: Dict[str, DatabaseManager] = {}
_tenant_lock = threading.RLock()

def _circuit_guard_json(db: Optional[DatabaseManager], endpoint: str = "") -> Optional[JSONResponse]:
    if db is None:
        return JSONResponse({"error": "DB no disponible"}, status_code=503)
    try:
        if hasattr(db, "is_circuit_open") and callable(getattr(db, "is_circuit_open")):
            if db.is_circuit_open():  # type: ignore
                state = {}
                try:
                    if hasattr(db, "get_circuit_state") and callable(getattr(db, "get_circuit_state")):
                        state = db.get_circuit_state()  # type: ignore
                except Exception:
                    state = {"open": True}
                try:
                    logger.warning(f"{endpoint or '[endpoint]'}: circuito abierto -> 503; state={state}")
                except Exception:
                    pass
                return JSONResponse({
                    "error": "Servicio temporalmente no disponible",
                    "circuit": state,
                }, status_code=503)
    except Exception as e:
        try:
            logger.exception(f"{endpoint or '[endpoint]'}: error comprobando circuito: {e}")
        except Exception:
            pass
    return None

def _compute_base_dir() -> Path:
    """Determina la carpeta base desde la cual resolver recursos."""
    try:
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            meipass = getattr(sys, "_MEIPASS", None)
            if meipass:
                return Path(meipass)
            return exe_dir
    except Exception:
        pass
    # Desarrollo: carpeta del proyecto
    try:
        # webapp/utils.py está en webapp/, subimos a apps/
        return Path(__file__).resolve().parent.parent
    except Exception:
        return Path('.')

BASE_DIR = _compute_base_dir()


def resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource, works for both development and PyInstaller.
    In Vercel/serverless environments, falls back to the current working directory.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base = getattr(sys, '_MEIPASS', None)
        if base:
            return str(Path(base) / relative_path)
    except Exception:
        pass
    
    try:
        # Frozen executable
        if getattr(sys, 'frozen', False):
            base = Path(sys.executable).parent
            return str(base / relative_path)
    except Exception:
        pass
    
    # Development: relative to the src/ directory
    try:
        # utils.py is in src/, so go up one level to get to webapp-api root
        src_dir = Path(__file__).resolve().parent
        api_root = src_dir.parent
        result = api_root / relative_path
        if result.exists():
            return str(result)

        # Monorepo layout: check repo root (IronHub/) for shared assets
        repo_root = api_root.parent.parent
        result2 = repo_root / relative_path
        if result2.exists():
            return str(result2)
    except Exception:
        pass
    
    # Fallback: current working directory
    return str(Path.cwd() / relative_path)


def get_webapp_base_url() -> str:
    """
    Get the base URL for the webapp.
    Reads from environment variables with sensible defaults.
    """
    # Try various environment variables
    candidates = [
        os.getenv("WEBAPP_BASE_URL"),
        os.getenv("NEXT_PUBLIC_API_URL"),
        os.getenv("VERCEL_URL"),
        os.getenv("VERCEL_BRANCH_URL"),
        os.getenv("VERCEL_PROJECT_PRODUCTION_URL"),
    ]
    
    for url in candidates:
        if url and url.strip():
            url = url.strip()
            # Ensure it has a protocol
            if not url.startswith("http://") and not url.startswith("https://"):
                url = f"https://{url}"
            return url.rstrip("/")
    
    # Default fallback
    return "http://127.0.0.1:8000"

def _resolve_existing_dir(*parts: str) -> Path:
    candidates = []
    try:
        if parts and parts[0] == "webapp":
            try:
                local = Path(__file__).resolve().parent.joinpath(*parts[1:])
                candidates.append(local)
            except Exception:
                pass
    except Exception:
        pass
    try:
        candidates.append(BASE_DIR.joinpath(*parts))
    except Exception:
        pass
    try:
        exe_dir = Path(sys.executable).resolve().parent
        candidates.append(exe_dir.joinpath(*parts))
    except Exception:
        pass
    try:
        # Attempt to find repo root
        repo_root = Path(__file__).resolve().parent.parent.parent
        candidates.append(repo_root.joinpath(*parts))
    except Exception:
        pass
    try:
        proj_root = Path(__file__).resolve().parent.parent
        candidates.append(proj_root.joinpath(*parts))
    except Exception:
        pass
    for c in candidates:
        try:
            if c.exists():
                return c
        except Exception:
            continue
    return candidates[0] if candidates else Path(*parts)

# Define static_dir as it is used in theme resolution
static_dir = _resolve_existing_dir("webapp", "static")

def _get_theme_from_db() -> Dict[str, str]:
    out: Dict[str, str] = {}
    db = get_db()
    if db is None:
        return out
    keys = [
        ("theme_primary", "--primary"),
        ("theme_secondary", "--secondary"),
        ("theme_accent", "--accent"),
        ("theme_bg", "--bg"),
        ("theme_card", "--card"),
        ("theme_text", "--text"),
        ("theme_muted", "--muted"),
        ("theme_border", "--border"),
        ("font_base", "--font-base"),
        ("font_heading", "--font-heading"),
    ]
    for cfg_key, css_var in keys:
        try:
            val = db.obtener_configuracion(cfg_key)  # type: ignore
        except Exception:
            val = None
        v = str(val or "").strip()
        if v:
            out[css_var] = v
    return out

def _resolve_theme_vars() -> Dict[str, str]:
    base = read_theme_vars(static_dir / "style.css")
    dbv = _get_theme_from_db()
    return {**base, **dbv}

def _normalize_public_url(url: str) -> str:
    try:
        if not url:
            return url
        
        # If it's a B2/CDN file key (e.g. "some-file.jpg" or "path/to/file.mp4")
        # and NOT a full URL (http/https), we might want to prepend the CDN domain
        # IF we know it's an asset.
        # However, some URLs might be local ("/assets/...") or external.
        
        # Check if it's likely a B2 key (no protocol, no starting slash)
        # But wait, `logo.svg` is local. `assets/logo.svg` is local.
        # B2 keys usually don't start with slash.
        # Let's look for B2 bucket context.
        # If we have a CDN_CUSTOM_DOMAIN env var, we can construct the URL.
        
        bucket = os.getenv("B2_BUCKET_NAME", "").strip()
        media_prefix = os.getenv("B2_MEDIA_PREFIX", "assets").strip().strip("/") or "assets"

        base = os.getenv("B2_PUBLIC_BASE_URL", "https://f005.backblazeb2.com").strip().rstrip("/")
        if base and not (base.startswith("http://") or base.startswith("https://")):
            base = f"https://{base.lstrip('/')}"
        if base.endswith("/file"):
            base = base[:-5]
        # Never use a custom domain here (old CDN). Force Backblaze host.
        if base and "backblazeb2.com" not in base.lower():
            ep = (os.getenv("B2_ENDPOINT_URL", "") or "").strip().lower()
            ep = ep.replace("https://", "").replace("http://", "")
            m = re.search(r"-(\d{3})\.backblazeb2\.com", ep)
            if m:
                base = f"https://f{m.group(1)}.backblazeb2.com"
            else:
                base = "https://f000.backblazeb2.com"

        # Local/static
        if url.startswith("/"):
            return url

        # Full URL
        if url.startswith("http://") or url.startswith("https://"):
            try:
                parsed = urllib.parse.urlparse(url)
                path = parsed.path or ""
                marker = f"/file/{bucket}/" if bucket else "/file/"
                if bucket and marker in path:
                    key = path.split(marker, 1)[1].lstrip("/")
                    if key and ".." not in key:
                        return f"{base}/file/{bucket}/{key}"
            except Exception:
                pass
            return url

        # Key stored in DB
        try:
            p = str(url).lstrip("/")
            if bucket and p and ".." not in p and p.startswith(f"{media_prefix}/"):
                return f"{base}/file/{bucket}/{p}"
        except Exception:
            pass

        return url
    except Exception:
        return url

def _resolve_logo_url() -> str:
    # Primero intentar obtener URL desde gym_config; luego desde configuracion
    try:
        db = get_db()
        if db is not None:
            # Prioridad: gym_config
            if hasattr(db, 'obtener_configuracion_gimnasio'):
                try:
                    cfg = db.obtener_configuracion_gimnasio()  # type: ignore
                except Exception:
                    cfg = {}
                if isinstance(cfg, dict):
                    # En gym_config la clave se almacena como 'logo_url'
                    u1 = str(cfg.get('logo_url') or '').strip()
                    if u1:
                        return _normalize_public_url(u1)
            # Fallback: tabla configuracion
            if hasattr(db, 'obtener_configuracion'):
                try:
                    url = db.obtener_configuracion('gym_logo_url')  # type: ignore
                except Exception:
                    url = None
                if isinstance(url, str) and url.strip():
                    return _normalize_public_url(url.strip())
    except Exception:
        pass
    # Fallback a assets locales
    candidates = [
        _resolve_existing_dir("assets") / "gym_logo.png",
        _resolve_existing_dir("assets") / "logo.svg",
        _resolve_existing_dir("webapp", "assets") / "logo.svg",
    ]
    for p in candidates:
        try:
            if p.exists():
                return "/assets/" + p.name
        except Exception:
            continue
    return "/assets/logo.svg"

def get_gym_name(default: str = "Gimnasio") -> str:
    # Wrapper around DB config
    try:
        db = get_db()
        if db and hasattr(db, 'obtener_configuracion'):
             n = db.obtener_configuracion('gym_name')
             if n: return str(n)
    except Exception:
        pass
    return default

def _get_password() -> str:
    # 1. Intentar obtener desde tabla usuarios (Donde AdminService actualiza la contraseña)
    # PRIORIDAD: Esto es lo que usa el login normal. Si hay algo aquí, úsalo.
    try:
        db = get_db()
        # Si get_db falla (ej: sin tenant context), esto lanzará excepción y pasamos al siguiente bloque.
        if db and hasattr(db, '_session'):
            from sqlalchemy import text
            # Buscar usuario con rol dueño/admin/owner
            result = db._session.execute(
                text("SELECT pin FROM usuarios WHERE rol IN ('dueno', 'owner', 'admin') AND activo = true ORDER BY id LIMIT 1")
            )
            row = result.fetchone()
            if row and row[0]:
                val = str(row[0]).strip()
                if val:
                    # PRECAUCIÓN: Si la base de datos tiene texto plano (ej: '123456'), devolvemos eso.
                    # El verificador (_verify_owner_password) manejará si es hash o no.
                    return val
    except Exception:
        pass

    # 2. Leer desde la base de datos (Legacy configuracion)
    try:
        db = get_db()
        if db and hasattr(db, 'obtener_configuracion'):
            pwd = db.obtener_configuracion('owner_password', timeout_ms=700)  # type: ignore
            if isinstance(pwd, str) and pwd.strip():
                return pwd.strip()
    except Exception:
        pass

    # 3. Fallback: leer desde Admin DB usando CURRENT_TENANT
    try:
        tenant = None
        try:
            tenant = CURRENT_TENANT.get()
        except Exception:
            pass
            
        # Si no hay tenant en contexto, intentar adivinar por entorno (para dev local)
        if not tenant:
            tenant = os.getenv("DEFAULT_TENANT", "testingiron") # Un default razonable para dev

        if tenant:
            adm = get_admin_db()
            if adm is not None:
                # get_admin_db retorna un generador, necesitamos la sesión
                session_gen = adm
                session = next(session_gen)
                try:
                    from sqlalchemy import text
                    result = session.execute(
                        text("SELECT owner_password_hash FROM gyms WHERE subdominio = :sub"),
                        {'sub': list([str(tenant).strip().lower()])} # Param as list to be safe or simple dict
                    )
                    # Use simple params actually
                    result = session.execute(
                        text("SELECT owner_password_hash FROM gyms WHERE subdominio = :sub"),
                        {'sub': str(tenant).strip().lower()}
                    )
                    row = result.fetchone()
                    if row and row[0]:
                         val = str(row[0]).strip()
                         if val:
                             return val
                finally:
                    session.close()
    except Exception:
        pass
        
    # 4. Fallback: variables de entorno
    try:
        env_pwd = (os.getenv("WEBAPP_OWNER_PASSWORD", "") or os.getenv("OWNER_PASSWORD", "")).strip()
    except Exception:
        env_pwd = ""
    if env_pwd:
        return env_pwd
        
def _verify_owner_password(password: str) -> bool:
    """
    Verify owner password against stored hash or environment variable.
    Supports bcrypt hashes and plaintext fallback.
    """
    import os
    import logging
    logger = logging.getLogger(__name__)
    
    if not password:
        return False
    
    # Get stored password from various sources
    stored = None
    try:
        stored = _get_password()
    except Exception:
        pass
    
    # Fallback to env vars
    env_pwd = (os.getenv("WEBAPP_OWNER_PASSWORD", "") or os.getenv("OWNER_PASSWORD", "")).strip()
    
    candidates = []
    if stored:
        candidates.append(stored)
    if env_pwd:
        candidates.append(env_pwd)
    if not candidates:
        candidates.append("admin")  # Default fallback for dev
    
    import bcrypt
    for secret in candidates:
        try:
            secret = str(secret).strip()
            # Bcrypt hash verification
            if secret.startswith('$2'):
                if bcrypt.checkpw(password.encode('utf-8'), secret.encode('utf-8')):
                    return True
            # Plaintext comparison
            elif secret == password:
                return True
        except Exception as e:
            logger.debug(f"Password check failed: {e}")
            continue
    
    return False

def _get_password() -> str:
    """DEPRECATED: Unused."""
    return ""

def _filter_existing_columns(conn, schema: str, table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Filtra las claves del diccionario 'data' preservando solo aquellas que
    coinciden con columnas existentes en la tabla indicada.
    """
    try:
        cur = conn.cursor()
        # Consulta segura de columnas en information_schema
        cur.execute(
            """
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s
            """,
            (schema, table)
        )
        rows = cur.fetchall() or []
        valid_cols = {r[0] for r in rows}
        return {k: v for k, v in data.items() if k in valid_cols}
    except Exception:
        return {}

def _apply_change_idempotent(conn, schema: str, table: str, operation: str, keys: Dict[str, Any], data: Dict[str, Any], where: List = None) -> bool:
    try:
        cur = conn.cursor()
        if operation.upper() == "UPDATE":
            filtered_data = _filter_existing_columns(conn, schema, table, data)
            if not filtered_data:
                return False
            
            set_clause = sql.SQL(", ").join([
                sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k))
                for k in filtered_data.keys()
            ])
            
            where_clause = sql.SQL(" AND ").join([
                sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(f"w_{k}"))
                for k in keys.keys()
            ])
            
            query = sql.SQL("UPDATE {}.{} SET {} WHERE {}").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                set_clause,
                where_clause
            )
            
            params = filtered_data.copy()
            for k, v in keys.items():
                params[f"w_{k}"] = v
                
            cur.execute(query, params)
            return cur.rowcount > 0

        elif operation.upper() == "DELETE":
            where_clause = sql.SQL(" AND ").join([
                sql.SQL("{} = {}").format(sql.Identifier(k), sql.Placeholder(k))
                for k in keys.keys()
            ])
            query = sql.SQL("DELETE FROM {}.{} WHERE {}").format(
                sql.Identifier(schema),
                sql.Identifier(table),
                where_clause
            )
            cur.execute(query, keys)
            return cur.rowcount > 0
            
        return False
    except Exception as e:
        logger.error(f"_apply_change_idempotent error: {e}")
        return False

# --- Multi-tenant Helpers ---

def _get_multi_tenant_mode() -> bool:
    try:
        v = os.getenv("MULTI_TENANT_MODE", "false").strip().lower()
        return v in ("1", "true", "yes", "on")
    except Exception:
        return False

def _get_request_host(request: Request) -> str:
    try:
        h = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
        h = h.strip()
        if h:
            return h.split(":")[0].strip().lower()
        try:
            return (request.url.hostname or "").strip().lower()
        except Exception:
            return ""
    except Exception:
        return ""

def _extract_tenant_from_host(host: str) -> Optional[str]:
    try:
        base = os.getenv("TENANT_BASE_DOMAIN", "gymms-motiona.xyz").strip().lower().lstrip(".")
    except Exception:
        base = "gymms-motiona.xyz"
    h = (host or "").strip().lower()
    if not h:
        return None
    if "localhost" in h or h.endswith(".localhost"):
        return None
    def _extract_with_base(hh: str, bb: str) -> Optional[str]:
        if not bb or not hh.endswith(bb):
            return None
        try:
            pref = hh[: max(0, len(hh) - len(bb))].rstrip(".")
        except Exception:
            pref = ""
        if not pref:
            return None
        try:
            s = pref.split(".")[0].strip()
        except Exception:
            s = pref
        if not s:
            return None
        try:
            if s.lower() == "www":
                return None
        except Exception:
            pass
        return s
    sub = _extract_with_base(h, base)
    if sub:
        return sub
    try:
        v = (os.getenv("VERCEL_URL") or os.getenv("VERCEL_BRANCH_URL") or os.getenv("VERCEL_PROJECT_PRODUCTION_URL") or "").strip()
        if v:
            import urllib.parse as _up
            try:
                u = _up.urlparse(v if (v.startswith("http://") or v.startswith("https://")) else ("https://" + v))
                vb = (u.hostname or "").strip().lower()
            except Exception:
                vb = v.split("/")[0].strip().lower()
            if vb:
                sub = _extract_with_base(h, vb)
                if sub:
                    return sub
    except Exception:
        pass
    return None

def _get_tenant_from_request(request: Request) -> Optional[str]:
    """Helper para extraer el tenant directamente del request."""
    host = _get_request_host(request)
    return _extract_tenant_from_host(host)

def _resolve_base_db_params() -> Dict[str, Any]:
    host = os.getenv("DB_HOST", "localhost").strip()
    try:
        port = int(os.getenv("DB_PORT", 5432))
    except Exception:
        port = 5432
    user = os.getenv("DB_USER", "postgres").strip()
    password = os.getenv("DB_PASSWORD", "")
    sslmode = os.getenv("DB_SSLMODE", "prefer").strip()
    try:
        connect_timeout = int(os.getenv("DB_CONNECT_TIMEOUT", 10))
    except Exception:
        connect_timeout = 10
    application_name = os.getenv("DB_APPLICATION_NAME", "gym_management_system").strip()
    database = os.getenv("DB_NAME", "gimnasio").strip()
    try:
        h = host.lower()
        if ("neon.tech" in h) or ("neon" in h):
            if not sslmode or sslmode.lower() in ("disable", "prefer"):
                sslmode = "require"
    except Exception:
        pass
    params: Dict[str, Any] = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "password": password,
        "sslmode": sslmode,
        "connect_timeout": connect_timeout,
        "application_name": application_name,
    }
    return params

def _get_db_for_tenant(tenant: str) -> Optional[DatabaseManager]:
    """
    Get a database manager for the specified tenant.
    Note: This returns the legacy DatabaseManager for backward compatibility.
    For SQLAlchemy sessions, use get_tenant_session_factory from tenant_connection.
    """
    t = (tenant or "").strip().lower()
    if not t:
        return None
    
    # First, try to get the tenant's db_name from admin
    with _tenant_lock:
        dm = _tenant_dbs.get(t)
        if dm is not None:
            return dm
        
        # Use the new tenant connection module to get db_name
        try:
            from src.database.tenant_connection import _get_tenant_db_name
            db_name = _get_tenant_db_name(t)
        except ImportError:
            db_name = None
        
        if not db_name:
            # Fallback to old method
            base = _resolve_base_db_params()
            adm = get_admin_db()
            if adm is not None:
                try:
                    with adm.db.get_connection_context() as conn:  # type: ignore
                        cur = conn.cursor()
                        cur.execute("SELECT db_name FROM gyms WHERE subdominio = %s", (t,))
                        row = cur.fetchone()
                        if row:
                            db_name = str(row[0] or "").strip()
                except Exception:
                    db_name = None
        
        if not db_name:
            return None
        
        base = _resolve_base_db_params()
        base["database"] = db_name
        
        try:
            dm = DatabaseManager(connection_params=base)  # type: ignore
        except Exception:
            return None
        
        try:
            with dm.get_connection_context() as conn:  # type: ignore
                cur = conn.cursor()
                cur.execute("SELECT 1")
                _ = cur.fetchone()
        except Exception:
            return None
        
        _tenant_dbs[t] = dm
        return dm

def _is_tenant_suspended(tenant: str) -> bool:
    adm = get_admin_db()
    if adm is None:
        return False
    try:
        return bool(adm.is_gym_suspended(tenant))  # type: ignore
    except Exception:
        return False

def _get_tenant_suspension_info(tenant: str) -> Optional[Dict[str, Any]]:
    adm = get_admin_db()
    if adm is None:
        return None
    try:
        with adm.db.get_connection_context() as conn:  # type: ignore
            cur = conn.cursor()
            cur.execute(
                "SELECT hard_suspend, suspended_until, suspended_reason FROM gyms WHERE subdominio = %s",
                (tenant.strip().lower(),),
            )
            row = cur.fetchone()
            if not row:
                return None
            hard, until, reason = row[0], row[1], row[2]
            try:
                u = until.isoformat() if hasattr(until, "isoformat") and until else (str(until or ""))
            except Exception:
                u = str(until or "")
            return {"hard": bool(hard), "until": u, "reason": str(reason or "")}
    except Exception:
        return None

def _get_session_secret() -> str:
    # 1) Prefer an explicit, stable secret via environment
    try:
        env = os.getenv("WEBAPP_SECRET_KEY", "").strip()
        if env:
            return env
    except Exception:
        pass

    # 2) In serverless environments (e.g., Vercel) the filesystem is ephemeral.
    try:
        if os.getenv("VERCEL") or os.getenv("VERCEL_ENV"):
            base = (os.getenv("WHATSAPP_APP_SECRET", "") + "|" + os.getenv("WHATSAPP_VERIFY_TOKEN", "")).strip()
            if base:
                import hashlib
                return hashlib.sha256(base.encode("utf-8")).hexdigest()
    except Exception:
        pass
    
    # 3) Non-serverless: try to read/persist in config/config.json for stability
    try:
        # Try to find config path
        base_dir = _resolve_existing_dir("config")
        cfg_path = base_dir / "config.json"
        
        cfg = {}
        if cfg_path.exists():
            import json as _json
            try:
                with open(cfg_path, "r", encoding="utf-8") as f:
                    cfg = _json.load(f) or {}
                if not isinstance(cfg, dict):
                    cfg = {}
            except Exception:
                cfg = {}
        secret = str(cfg.get("webapp_session_secret") or cfg.get("session_secret") or "").strip()
        if not secret:
            import secrets as _secrets
            secret = _secrets.token_urlsafe(32)
            cfg["webapp_session_secret"] = secret
            try:
                if not base_dir.exists():
                    os.makedirs(base_dir, exist_ok=True)
                with open(cfg_path, "w", encoding="utf-8") as f:
                    _json.dump(cfg, f, ensure_ascii=False, indent=2)
            except Exception:
                pass
        return secret
    except Exception:
        pass
    
    # 4) Absolute last resort: ephemeral secret
    import secrets as _secrets
    return _secrets.token_urlsafe(32)


# --- JWT and Usuario Helpers (ported from legacy server.py lines 5613-5656) ---

def _get_usuario_id_by_dni(dni: str) -> Optional[int]:
    """
    Get usuario ID by DNI from the database.
    Returns None if not found or on error.
    """
    try:
        d = str(dni or "").strip()
    except Exception:
        d = str(dni)
    if not d:
        return None
    db = get_db()
    if db is None:
        return None
    try:
        with db.get_connection_context() as conn:  # type: ignore
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)  # type: ignore
            cur.execute("SELECT id FROM usuarios WHERE dni = %s LIMIT 1", (d,))
            row = cur.fetchone()
            if row and ("id" in row):
                try:
                    val = int(row["id"] or 0)
                    return val if val > 0 else None
                except Exception:
                    pass
    except Exception:
        try:
            logger.exception("Error buscando usuario por DNI")
        except Exception:
            pass
    return None


def _issue_usuario_jwt(usuario_id: int) -> Optional[str]:
    """
    Issue a JWT token for a usuario session.
    Token is valid for 24 hours (86400 seconds).
    Uses HMAC-SHA256 with the session secret.
    """
    try:
        import json
        import base64
        import time
        import hmac
        import hashlib
        
        hdr = {"alg": "HS256", "typ": "JWT"}
        now = int(time.time())
        pl = {"sub": int(usuario_id), "role": "user", "iat": now, "exp": now + 86400}
        hdr_b = json.dumps(hdr, separators=(",", ":")).encode("utf-8")
        pl_b = json.dumps(pl, separators=(",", ":")).encode("utf-8")
        h_b64 = base64.urlsafe_b64encode(hdr_b).rstrip(b"=").decode("utf-8")
        p_b64 = base64.urlsafe_b64encode(pl_b).rstrip(b"=").decode("utf-8")
        signing_input = f"{h_b64}.{p_b64}".encode("utf-8")
        secret = _get_session_secret().encode("utf-8")
        sig = hmac.new(secret, signing_input, hashlib.sha256).digest()
        s_b64 = base64.urlsafe_b64encode(sig).rstrip(b"=").decode("utf-8")
        return f"{h_b64}.{p_b64}.{s_b64}"
    except Exception:
        return None


def _get_usuario_nombre(usuario_id: int) -> Optional[str]:
    """
    Get the nombre (name) for a usuario by ID.
    Returns None if not found or on error.
    """
    db = get_db()
    if db is None:
        return None
    try:
        u = db.obtener_usuario_por_id(int(usuario_id))  # type: ignore
        if u is not None:
            nombre = getattr(u, 'nombre', None) or (u.get('nombre') if isinstance(u, dict) else None) or ""
            return nombre if nombre else None
    except Exception:
        pass
    return None

