"""
IronHub Admin API
FastAPI backend for admin panel - Self-contained deployment
"""

import os
import logging
import time
import uuid
import re
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Form, Query, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
import psycopg2
import psycopg2.extras
from pydantic import BaseModel
from typing import Optional, List, Any, Dict

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local imports (self-contained)
from src.database.raw_manager import RawPostgresManager
from src.services.admin_service import AdminService
from src.routers.payments import router as payments_router
from src.routers.routine_templates import router as routine_templates_router
from src.routers.templates_v1 import router as templates_v1_router
from src.secure_config import SecureConfig
from src.security_utils import SecurityUtils


class GymBranchInput(BaseModel):
    name: str
    code: str
    address: Optional[str] = None
    timezone: Optional[str] = None


class GymCreateV2Input(BaseModel):
    nombre: str
    subdominio: Optional[str] = None
    owner_phone: Optional[str] = None
    owner_password: Optional[str] = None
    whatsapp_phone_id: Optional[str] = None
    whatsapp_access_token: Optional[str] = None
    whatsapp_business_account_id: Optional[str] = None
    whatsapp_verify_token: Optional[str] = None
    whatsapp_app_secret: Optional[str] = None
    whatsapp_nonblocking: Optional[bool] = False
    whatsapp_send_timeout_seconds: Optional[float] = None
    branches: Optional[List[GymBranchInput]] = None


class BulkBranchesInput(BaseModel):
    items: List[GymBranchInput]


class ProductionReadyInput(BaseModel):
    ready: bool

# Initialize FastAPI app
app = FastAPI(
    title="IronHub Admin API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include routers
app.include_router(payments_router)
app.include_router(routine_templates_router)
app.include_router(templates_v1_router)

# CORS
origins_str = os.getenv("ALLOWED_ORIGINS", "")
origins = [o.strip() for o in origins_str.split(",") if o.strip()]
_origin_regex = os.getenv("ALLOWED_ORIGIN_REGEX", "")
vercel_url = str(os.getenv("VERCEL_URL") or "").strip()
if vercel_url:
    if not vercel_url.startswith("http://") and not vercel_url.startswith("https://"):
        vercel_url = f"https://{vercel_url}"
    origins.append(vercel_url)

if not origins and not _origin_regex:
    # Default behavior: Use regex to allow subdomains + localhost
    base_domain = (
        str(os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz") or "")
        .strip()
        .lstrip(".")
    )
    base_domain_escaped = re.escape(base_domain)
    _origin_regex = (
        rf"^https?://([a-z0-9-]+\.)?{base_domain_escaped}$"  # Any subdomain of base
        r"|^http://localhost(:\d+)?$"  # Localhost
        r"|^http://127\.0\.0\.1(:\d+)?$"  # IP Localhost
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins else [],
    allow_origin_regex=_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
_admin_secret = str(os.getenv("ADMIN_SESSION_SECRET") or "").strip()
_env = str(os.getenv("ENV") or "").strip().lower()
_is_prod = _env in ("prod", "production")
if _is_prod and (not _admin_secret or _admin_secret in ("admin-session-secret-change-me", "changeme", "password")):
    raise RuntimeError("ADMIN_SESSION_SECRET requerido y debe ser fuerte en producción")
if not _admin_secret:
    _admin_secret = "admin-session-secret-change-me"

app.add_middleware(
    SessionMiddleware,
    secret_key=_admin_secret,
    https_only=os.getenv("ENV", "production") == "production",
    same_site="lax",
    session_cookie=os.getenv("ADMIN_SESSION_COOKIE", "ironhub_admin_session"),
    domain=f".{os.getenv('TENANT_BASE_DOMAIN', 'ironhub.motiona.xyz')}",  # Allow cookie sharing
)

# Service instance (lazy loaded)
_admin_service = None
_public_metrics_cache = {"ts": 0.0, "value": None}


def get_admin_service() -> AdminService:
    """Get or initialize the AdminService singleton."""
    global _admin_service
    if _admin_service is not None:
        return _admin_service

    params = AdminService.resolve_admin_db_params()
    db = RawPostgresManager(connection_params=params)
    _admin_service = AdminService(db)
    return _admin_service


def is_logged_in(request: Request) -> bool:
    """Check if the request has a valid admin session."""
    try:
        return bool(request.session.get("admin_logged_in"))
    except Exception:
        return False


def require_admin(request: Request):
    """Require admin authentication. Check session or x-admin-secret header."""
    if is_logged_in(request):
        return
    secret = os.getenv("ADMIN_SECRET", "").strip()
    if secret and request.headers.get("x-admin-secret") == secret:
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


# ========== ROUTES ==========


@app.get("/")
async def root():
    """API info endpoint."""
    return {"name": "IronHub Admin API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


# ========== AUTH ROUTES ==========


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    """Admin login with password."""
    adm = get_admin_service()

    # Verify password
    ok = adm.verificar_owner_password(password)

    if not ok:
        # Check fallback passwords from env
        candidates = [
            os.getenv("ADMIN_INITIAL_PASSWORD", ""),
            os.getenv("ADMIN_SECRET", ""),
            os.getenv("DEV_PASSWORD", ""),
        ]
        if password in [c for c in candidates if c]:
            ok = True

    if not ok:
        return JSONResponse(
            {"ok": False, "error": "Credenciales incorrectas"}, status_code=401
        )

    request.session["admin_logged_in"] = True
    adm.log_action("owner", "login", None, None)
    return {"ok": True}


@app.post("/logout")
async def logout(request: Request):
    """Admin logout."""
    request.session.clear()
    return {"ok": True}


@app.get("/session")
async def check_session(request: Request):
    """Check if the current session is valid."""
    return {"logged_in": is_logged_in(request)}


@app.post("/admin/password")
async def change_admin_password(
    request: Request, current_password: str = Form(...), new_password: str = Form(...)
):
    """Change the admin owner password."""
    require_admin(request)
    adm = get_admin_service()

    # Verify current password
    if not adm.verificar_owner_password(current_password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")

    # Validate new password
    if len(new_password.strip()) < 8:
        raise HTTPException(
            status_code=400,
            detail="La nueva contraseña debe tener al menos 8 caracteres",
        )

    # Set new password
    success = adm.set_admin_owner_password(new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Error al actualizar la contraseña")

    adm.log_action("owner", "change_password", None, "Admin password changed")
    return {"ok": True}


# ========== GYM ROUTES ==========


@app.get("/gyms")
async def list_gyms(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query(None),
    status: str = Query(None),
    production_ready: Optional[bool] = Query(None),
):
    """List all gyms with pagination and filtering."""
    require_admin(request)
    adm = get_admin_service()
    result = adm.listar_gimnasios_avanzado(
        page, page_size, q or None, status or None, production_ready, "id", "DESC"
    )
    # Map 'items' to 'gyms' to match frontend expectations
    return {
        "gyms": result.get("items", []),
        "total": result.get("total", 0),
        "page": result.get("page", 1),
        "page_size": result.get("page_size", 20),
    }


@app.get("/gyms/public")
@app.get("/gyms/public")
async def list_public_gyms():
    """List active gyms for public display (landing page). No authentication required."""
    adm = get_admin_service()
    try:
        # Only return active gyms with limited info
        result = adm.listar_gimnasios_avanzado(1, 100, None, "active", None, "nombre", "ASC")
        items = result.get("items", []) or []

        # 3. Resolve base DB params once
        admin_params = AdminService.resolve_admin_db_params()
        base_pg_params = {
            "host": admin_params.get("host"),
            "port": admin_params.get("port"),
            "user": admin_params.get("user"),
            "password": admin_params.get("password"),
            "sslmode": admin_params.get("sslmode"),
            "connect_timeout": 3,
        }

        def _fetch_gym_branding(gym):
            gid = int(gym.get("id"))
            db_name = str(gym.get("db_name") or "").strip()
            # Default structure
            g_out = {
                "id": gid,
                "nombre": gym.get("nombre"),
                "subdominio": gym.get("subdominio"),
                "status": gym.get("status", "active"),
                "logo_url": None,
            }
            if not db_name:
                return g_out

            # Retry logic for branding (Cold Starts)
            for attempt in range(3):
                try:
                    pg_params = {
                        **base_pg_params,
                        "dbname": db_name,
                        "application_name": "landing_gyms_worker",
                        "connect_timeout": 3 if attempt == 0 else 5,
                    }
                    with psycopg2.connect(**pg_params) as t_conn:
                        with t_conn.cursor() as t_cur:
                            # Fetch branding config from Key-Value store
                            kv = {}
                            try:
                                t_cur.execute(
                                    "SELECT clave, valor FROM configuracion WHERE clave IN ('logo_url', 'gym_logo_url', 'nombre_publico')"
                                )
                                rows = t_cur.fetchall()
                                kv = {r[0]: r[1] for r in rows}
                            except Exception:
                                pass  # Table might not exist or be empty

                            logo_url = (
                                str(kv.get("logo_url") or kv.get("gym_logo_url") or "").strip()
                            )
                            nombre_publico = str(kv.get("nombre_publico") or "").strip()

                            if nombre_publico:
                                g_out["nombre"] = nombre_publico

                            # Simple B2/URL validation
                            if logo_url:
                                if not logo_url.startswith(
                                    "http"
                                ) and not logo_url.startswith("/"):
                                    # It's a B2 path, return as is
                                    pass
                                g_out["logo_url"] = logo_url

                            return g_out
                except Exception:
                    import time

                    time.sleep(0.5 * (attempt + 1))

            return g_out

        # Parallel Execution
        import concurrent.futures
        import asyncio

        loop = asyncio.get_event_loop()

        public_gyms = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [
                loop.run_in_executor(executor, _fetch_gym_branding, g) for g in items
            ]
            results = await asyncio.gather(*futures)
            public_gyms = list(results)

        return {"items": public_gyms, "total": len(public_gyms)}
    except Exception as e:
        logger.error(f"Error fetching public gyms: {e}")
        return {"items": [], "total": 0}


@app.get("/gyms/public/metrics")
async def get_public_metrics(ttl_seconds: int = Query(600, ge=60, le=3600)):
    adm = get_admin_service()
    now = time.time()
    cached = _public_metrics_cache.get("value")
    cached_ts = float(_public_metrics_cache.get("ts") or 0.0)

    # Check cache validity
    if cached and (now - cached_ts) < float(ttl_seconds):
        return cached

    try:
        # 1. Fetch all active gyms
        result = adm.listar_gimnasios_avanzado(1, 500, None, "active", None, "nombre", "ASC")
        gyms = result.get("items", []) or []

        # 2. Get paying gyms count (centralized query, fast)
        paying_count = 0
        try:
            with adm.db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT COUNT(DISTINCT gym_id) FROM gym_subscriptions WHERE status = 'active' AND next_due_date >= CURRENT_DATE"
                )
                paying_count = int((cur.fetchone() or [0])[0] or 0)
        except Exception:
            paying_count = 0

        # 3. Resolve base DB params once
        admin_params = AdminService.resolve_admin_db_params()
        base_pg_params = {
            "host": admin_params.get("host"),
            "port": admin_params.get("port"),
            "user": admin_params.get("user"),
            "password": admin_params.get("password"),
            "sslmode": admin_params.get("sslmode"),
            "connect_timeout": 3,  # Lower timeout for individual checks
        }

        # 4. Define helper for parallel execution
        def _fetch_gym_metrics(gym):
            gid = int(gym.get("id"))
            db_name = str(gym.get("db_name") or "").strip()
            sub = str(gym.get("subdominio") or "")

            if not db_name:
                return {
                    "id": gid,
                    "subdominio": sub,
                    "users_total": None,
                    "users_active": None,
                }

            # Retry policy for Cold Starts (Neon DB wakes up)
            # Default connect_timeout is short (3s), so we retry 3 times.
            last_err = None
            for attempt in range(3):
                try:
                    pg_params = {
                        **base_pg_params,
                        "dbname": db_name,
                        "application_name": "landing_metrics_worker",
                        # On attempt 0: 3s timeout. On attempt 1+: 5s timeout.
                        "connect_timeout": 3 if attempt == 0 else 5,
                    }

                    with psycopg2.connect(**pg_params) as t_conn:
                        with t_conn.cursor() as t_cur:
                            # SINGLE OPTIMIZED QUERY: Reduces DB round-trips by 50%
                            t_cur.execute("""
                                SELECT 
                                    COUNT(*) as total, 
                                    COUNT(*) FILTER (WHERE activo = TRUE) as activos 
                                FROM usuarios
                            """)
                            row = t_cur.fetchone() or (0, 0)
                            u_total = int(row[0] or 0)
                            u_active = int(row[1] or 0)

                            return {
                                "id": gid,
                                "subdominio": sub,
                                "users_total": u_total,
                                "users_active": u_active,
                            }
                except Exception as e:
                    import time  # Ensure locally available just in case, logic safe

                    last_err = e
                    # Wait briefly before retrying if it's a connection issue
                    time.sleep(0.5 * (attempt + 1))

            # If we get here, all retries failed
            logger.warning(
                f"Failed to fetch metrics for gym {gid} ({sub}) after 3 attempts: {last_err}"
            )
            return {
                "id": gid,
                "subdominio": sub,
                "users_total": None,
                "users_active": None,
            }

        # 5. execute in parallel using ThreadPoolExecutor
        import concurrent.futures
        import asyncio

        loop = asyncio.get_event_loop()
        gyms_metrics = []

        # We can use a reasonable number of workers, e.g., 20, to parallelize DB IO
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            # Wrap standard blocking calls in executor
            futures = [
                loop.run_in_executor(executor, _fetch_gym_metrics, g) for g in gyms
            ]
            # Gather results
            results = await asyncio.gather(*futures)
            gyms_metrics = list(results)

        # 6. Aggregate results
        total_users = 0
        total_active_users = 0

        for gm in gyms_metrics:
            ut = gm.get("users_total")
            ua = gm.get("users_active")
            if isinstance(ut, int):
                total_users += ut
            if isinstance(ua, int):
                total_active_users += ua

        value = {
            "ok": True,
            "generated_at": datetime.utcnow().isoformat(),
            "totals": {
                "active_gyms": int(len(gyms)),
                "paying_gyms": int(paying_count),
                "total_users": int(total_users),
                "total_active_users": int(total_active_users),
            },
            "gyms": gyms_metrics,
        }

        # Update cache
        _public_metrics_cache["ts"] = now
        _public_metrics_cache["value"] = value

        return value

    except Exception as e:
        logger.error(f"Error fetching public metrics: {e}")
        # If we have a stale cache, maybe return it? For now, return error structure
        return {"ok": False, "error": "error_fetching_public_metrics"}


@app.get("/gyms/summary")
async def list_gyms_with_summary(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query(None),
    status: str = Query(None),
    production_ready: Optional[bool] = Query(None),
):
    """List all gyms with subscription and payment summary."""
    require_admin(request)
    adm = get_admin_service()
    result = adm.listar_gimnasios_con_resumen(
        page, page_size, q or None, status or None, production_ready, "id", "DESC"
    )
    return result


@app.post("/gyms/batch/maintenance/clear")
async def batch_clear_maintenance(request: Request):
    """Disable maintenance mode for multiple gyms. Expects JSON {ids}."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ids = data.get("ids") or []
    try:
        ids = [int(x) for x in ids]
    except Exception:
        ids = []
    result = adm.batch_clear_maintenance(ids)
    try:
        adm.log_action("owner", "batch_clear_maintenance", None, f"count={len(ids)}")
    except Exception:
        pass
    return result


@app.post("/gyms")
async def create_gym(
    request: Request,
    nombre: str = Form(...),
    subdominio: str = Form(None),
    owner_phone: str = Form(None),
    whatsapp_phone_id: str = Form(None),
    whatsapp_access_token: str = Form(None),
    whatsapp_business_account_id: str = Form(None),
    whatsapp_verify_token: str = Form(None),
    whatsapp_app_secret: str = Form(None),
    whatsapp_nonblocking: bool = Form(False),
    whatsapp_send_timeout_seconds: str = Form(None),
):
    """Create a new gym with database provisioning."""
    require_admin(request)
    adm = get_admin_service()

    sub = (subdominio or "").strip().lower()
    if not sub:
        sub = adm.sugerir_subdominio_unico(nombre)

    try:
        wa_timeout = (
            float(whatsapp_send_timeout_seconds)
            if whatsapp_send_timeout_seconds not in (None, "")
            else None
        )
    except Exception:
        wa_timeout = None

    result = adm.crear_gimnasio(
        nombre,
        sub,
        whatsapp_phone_id=whatsapp_phone_id,
        whatsapp_access_token=whatsapp_access_token,
        owner_phone=owner_phone,
        whatsapp_business_account_id=whatsapp_business_account_id,
        whatsapp_verify_token=whatsapp_verify_token,
        whatsapp_app_secret=whatsapp_app_secret,
        whatsapp_nonblocking=bool(whatsapp_nonblocking),
        whatsapp_send_timeout_seconds=wa_timeout,
    )

    if "error" in result:
        return JSONResponse(result, status_code=400)

    adm.log_action("owner", "create_gym", result.get("id"), f"{nombre}|{sub}")
    return JSONResponse({**result, "ok": True}, status_code=201)


@app.post("/gyms/v2")
async def create_gym_v2(request: Request, payload: GymCreateV2Input):
    require_admin(request)
    adm = get_admin_service()

    nombre = str(payload.nombre or "").strip()
    if len(nombre) < 2:
        return JSONResponse({"ok": False, "error": "invalid_name"}, status_code=400)

    sub = str(payload.subdominio or "").strip().lower()
    if not sub:
        sub = adm.sugerir_subdominio_unico(nombre)

    branches = payload.branches or []
    create_default_branch = not bool(branches)

    result = adm.crear_gimnasio(
        nombre,
        sub,
        whatsapp_phone_id=payload.whatsapp_phone_id,
        whatsapp_access_token=payload.whatsapp_access_token,
        owner_phone=payload.owner_phone,
        whatsapp_business_account_id=payload.whatsapp_business_account_id,
        whatsapp_verify_token=payload.whatsapp_verify_token,
        whatsapp_app_secret=payload.whatsapp_app_secret,
        whatsapp_nonblocking=bool(payload.whatsapp_nonblocking or False),
        whatsapp_send_timeout_seconds=payload.whatsapp_send_timeout_seconds,
        create_default_branch=create_default_branch,
    )
    if "error" in result:
        return JSONResponse({**result, "ok": False}, status_code=400)

    gym_id = int(result.get("id") or 0)
    created_branches: List[Dict[str, Any]] = []
    bulk_res: Optional[Dict[str, Any]] = None
    if branches:
        st0 = adm.tenant_migration_status(gym_id)
        if st0.get("ok") and str(st0.get("status") or "") in (
            "uninitialized",
            "outdated",
        ):
            try:
                adm.provision_tenant_migrations(gym_id)
            except Exception:
                pass
        st1 = adm.tenant_migration_status(gym_id)
        if not st1.get("ok") or str(st1.get("status") or "") != "up_to_date":
            try:
                adm.eliminar_gimnasio(gym_id)
            except Exception:
                pass
            return JSONResponse(
                {"ok": False, "error": "tenant_migrations_failed", "gym_id": gym_id, "status": st1},
                status_code=500,
            )

        bulk_items = [b.model_dump() for b in branches]
        bulk_res = adm.bulk_crear_sucursales(gym_id, bulk_items)

        def _collect_ok(res_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
            out: List[Dict[str, Any]] = []
            if res_obj.get("ok") and isinstance(res_obj.get("results"), list):
                for r in res_obj.get("results") or []:
                    if isinstance(r, dict) and r.get("ok") and r.get("branch"):
                        out.append(r.get("branch"))
            return out

        created_branches = _collect_ok(bulk_res)

        failed_idx: List[int] = []
        merged_by_index: Dict[int, Dict[str, Any]] = {}
        if isinstance(bulk_res.get("results"), list):
            for r in bulk_res.get("results") or []:
                if isinstance(r, dict) and isinstance(r.get("index"), int):
                    merged_by_index[int(r["index"])] = r
                    if not bool(r.get("ok")):
                        failed_idx.append(int(r["index"]))

        if failed_idx:
            try:
                adm.provision_tenant_migrations(gym_id)
            except Exception:
                pass
            retry_pairs = [(i, bulk_items[i]) for i in failed_idx if 0 <= i < len(bulk_items)]
            retry_items = [p[1] for p in retry_pairs]
            if retry_items:
                retry_res = adm.bulk_crear_sucursales(gym_id, retry_items)
                if isinstance(retry_res.get("results"), list):
                    for pos, r in enumerate(retry_res.get("results") or []):
                        if not isinstance(r, dict):
                            continue
                        orig_index = retry_pairs[pos][0] if pos < len(retry_pairs) else None
                        if isinstance(orig_index, int):
                            merged_by_index[int(orig_index)] = {**r, "index": int(orig_index)}
                merged_results = [merged_by_index[i] for i in sorted(merged_by_index.keys())]
                bulk_res = {**bulk_res, "results": merged_results}
                created_branches = _collect_ok(bulk_res)

        if isinstance(bulk_res.get("results"), list):
            still_failed = [r for r in bulk_res.get("results") or [] if isinstance(r, dict) and not bool(r.get("ok"))]
            if still_failed:
                try:
                    adm.eliminar_gimnasio(gym_id)
                except Exception:
                    pass
                return JSONResponse(
                    {"ok": False, "error": "branches_create_failed", "gym_id": gym_id, "bulk_branches": bulk_res},
                    status_code=500,
                )

        result["bulk_branches"] = bulk_res

    owner_password = str(payload.owner_password or "").strip()
    owner_password_generated = False
    if not owner_password:
        owner_password = SecurityUtils.generate_secure_password(16)
        owner_password_generated = True

    if not adm.set_gym_owner_password(gym_id, owner_password):
        try:
            adm.eliminar_gimnasio(gym_id)
        except Exception:
            pass
        return JSONResponse(
            {"ok": False, "error": "owner_password_set_failed", "gym_id": gym_id},
            status_code=500,
        )

    tenant_domain = str(os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz") or "").strip().lstrip(".")
    tenant_url = f"https://{sub}.{tenant_domain}" if sub and tenant_domain else None

    try:
        adm.log_action("owner", "create_gym_v2", gym_id, f"{nombre}|{sub}")
    except Exception:
        pass

    resp: Dict[str, Any] = {
        "ok": True,
        "gym": {**result, "owner_password_hash": None},
        "tenant_url": tenant_url,
        "branches": created_branches,
        "owner_password_generated": bool(owner_password_generated),
        "owner_password_set": True,
    }
    if owner_password_generated:
        resp["owner_password"] = owner_password
    return JSONResponse(resp, status_code=201)


@app.get("/gyms/{gym_id}")
async def get_gym(request: Request, gym_id: int):
    """Get a single gym by ID."""
    require_admin(request)
    adm = get_admin_service()

    gym = adm.obtener_gimnasio(gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    try:
        phone_id = str((gym.get("whatsapp_phone_id") or "")).strip()
        gym["wa_configured"] = bool(phone_id)
    except Exception:
        pass

    try:
        tenant_cfg = adm.get_tenant_whatsapp_active_config_for_gym(int(gym_id))
        if tenant_cfg.get("ok"):
            gym["tenant_whatsapp_phone_id"] = str(tenant_cfg.get("phone_id") or "")
            gym["tenant_whatsapp_waba_id"] = str(tenant_cfg.get("waba_id") or "")
            gym["tenant_whatsapp_access_token_present"] = bool(
                tenant_cfg.get("access_token_present") is True
            )
            gym["tenant_wa_configured"] = bool(tenant_cfg.get("configured") is True)
            if not bool(gym.get("wa_configured")):
                gym["wa_configured"] = bool(gym.get("tenant_wa_configured"))
    except Exception:
        pass

    try:
        at_raw = gym.get("whatsapp_access_token")
        vt_raw = gym.get("whatsapp_verify_token")
        as_raw = gym.get("whatsapp_app_secret")
        if at_raw:
            gym["whatsapp_access_token"] = SecureConfig.decrypt_waba_secret(str(at_raw))
        if vt_raw:
            gym["whatsapp_verify_token"] = SecureConfig.decrypt_waba_secret(str(vt_raw))
        if as_raw:
            gym["whatsapp_app_secret"] = SecureConfig.decrypt_waba_secret(str(as_raw))
    except Exception:
        pass

    return gym


@app.get("/gyms/{gym_id}/details")
async def get_gym_details(request: Request, gym_id: int):
    """Alias for getting gym details (backwards compatible with admin-web)."""
    return await get_gym(request, gym_id)


@app.get("/gyms/{gym_id}/onboarding")
async def get_gym_onboarding(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()

    gym = adm.obtener_gimnasio(int(gym_id))
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    try:
        branches = adm.listar_sucursales(int(gym_id)) or []
    except Exception:
        branches = []
    active = 0
    for b in branches:
        try:
            st = str((b or {}).get("status") or "active").strip().lower()
            if st != "inactive":
                active += 1
        except Exception:
            active += 1

    owner_password_set = bool(str(gym.get("owner_password_hash") or "").strip())

    wa_configured = False
    try:
        wa_configured = bool(str(gym.get("whatsapp_phone_id") or "").strip())
    except Exception:
        wa_configured = False
    if not wa_configured:
        try:
            tenant_cfg = adm.get_tenant_whatsapp_active_config_for_gym(int(gym_id))
            wa_configured = bool(tenant_cfg.get("configured") is True)
        except Exception:
            pass

    base_domain = str(os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz") or "").strip().lstrip(".")
    sub = str(gym.get("subdominio") or "").strip().lower()
    tenant_url = f"https://{sub}.{base_domain}" if sub and base_domain else None

    return {
        "ok": True,
        "gym_id": int(gym_id),
        "subdominio": sub,
        "gym_status": str(gym.get("status") or ""),
        "tenant_url": tenant_url,
        "branches_total": int(len(branches)),
        "branches_active": int(active),
        "owner_password_set": bool(owner_password_set),
        "whatsapp_configured": bool(wa_configured),
        "production_ready": bool(gym.get("production_ready") is True),
        "production_ready_at": gym.get("production_ready_at"),
    }


@app.post("/gyms/{gym_id}/production-ready")
async def set_gym_production_ready(request: Request, gym_id: int, payload: ProductionReadyInput):
    require_admin(request)
    adm = get_admin_service()
    result = adm.set_gym_production_ready(int(gym_id), bool(payload.ready), by="admin")
    if not result.get("ok"):
        code = 404 if result.get("error") == "gym_not_found" else 400
        return JSONResponse(result, status_code=code)
    try:
        adm.log_action("owner", "set_production_ready", int(gym_id), f"ready={bool(payload.ready)}")
    except Exception:
        pass
    return result


@app.get("/gyms/{gym_id}/branches")
async def list_gym_branches(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    items = adm.listar_sucursales(int(gym_id))
    return {"ok": True, "items": items}


@app.post("/gyms/{gym_id}/branches")
async def create_gym_branch(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    name = data.get("name") or data.get("nombre")
    code = data.get("code") or data.get("codigo")
    address = data.get("address") or data.get("direccion")
    timezone = data.get("timezone")
    result = adm.crear_sucursal(
        int(gym_id),
        str(name or ""),
        str(code or ""),
        address=address,
        timezone=timezone,
    )
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    try:
        adm.log_action("owner", "create_branch", int(gym_id), f"{code}")
    except Exception:
        pass
    return result


@app.post("/gyms/{gym_id}/branches/bulk")
async def bulk_create_gym_branches(request: Request, gym_id: int, payload: BulkBranchesInput):
    require_admin(request)
    adm = get_admin_service()
    items = [it.model_dump() for it in (payload.items or [])]
    result = adm.bulk_crear_sucursales(int(gym_id), items)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    try:
        adm.log_action("owner", "bulk_create_branches", int(gym_id), f"count={len(items)}")
    except Exception:
        pass
    return result


@app.post("/gyms/{gym_id}/branches/sync")
async def sync_gym_branches(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.sync_sucursales(int(gym_id))
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    try:
        adm.log_action("owner", "sync_branches", int(gym_id), None)
    except Exception:
        pass
    return result


@app.put("/gyms/{gym_id}/branches/{branch_id}")
async def update_gym_branch(request: Request, gym_id: int, branch_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    result = adm.actualizar_sucursal(int(gym_id), int(branch_id), data or {})
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    try:
        adm.log_action("owner", "update_branch", int(gym_id), f"{branch_id}")
    except Exception:
        pass
    return result


@app.delete("/gyms/{gym_id}/branches/{branch_id}")
async def delete_gym_branch(request: Request, gym_id: int, branch_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.eliminar_sucursal(int(gym_id), int(branch_id))
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)
    try:
        adm.log_action("owner", "delete_branch", int(gym_id), f"{branch_id}")
    except Exception:
        pass
    return result


@app.put("/gyms/{gym_id}")
async def update_gym(
    request: Request,
    gym_id: int,
    nombre: str = Form(None),
    subdominio: str = Form(None),
):
    """Update a gym's basic info."""
    require_admin(request)
    adm = get_admin_service()

    result = adm.actualizar_gimnasio(gym_id, nombre, subdominio)
    if not result.get("ok"):
        return JSONResponse(result, status_code=400)

    adm.log_action("owner", "update_gym", gym_id, f"{nombre}|{subdominio}")
    return result


@app.delete("/gyms/{gym_id}")
async def delete_gym(request: Request, gym_id: int):
    """Delete a gym and its resources."""
    require_admin(request)
    adm = get_admin_service()

    ok = adm.eliminar_gimnasio(gym_id)
    adm.log_action("owner", "delete_gym", gym_id, None)
    return {"ok": ok}


@app.put("/gyms/{gym_id}/status")
async def set_gym_status(
    request: Request,
    gym_id: int,
    status: str = Form(...),
    hard_suspend: bool = Form(False),
    suspended_until: str = Form(None),
    reason: str = Form(None),
):
    """Set a gym's status (active, suspended, maintenance)."""
    require_admin(request)
    adm = get_admin_service()

    ok = adm.set_estado_gimnasio(gym_id, status, hard_suspend, suspended_until, reason)
    adm.log_action("owner", "set_gym_status", gym_id, f"{status}|{reason}")
    return {"ok": ok}


@app.post("/gyms/{gym_id}/owner-password")
async def set_gym_owner_password(
    request: Request, gym_id: int, new_password: str = Form(...)
):
    """Set the owner password for a specific gym."""
    require_admin(request)
    adm = get_admin_service()

    if len(new_password.strip()) < 6:
        raise HTTPException(
            status_code=400, detail="La contraseña debe tener al menos 6 caracteres"
        )

    success = adm.set_gym_owner_password(gym_id, new_password)
    if not success:
        raise HTTPException(status_code=500, detail="Error al actualizar la contraseña")

    adm.log_action("owner", "set_gym_owner_password", gym_id, "Password changed")
    return {"ok": True}


# ========== METRICS ROUTES ==========


@app.get("/metrics")
async def get_metrics(request: Request):
    """Get dashboard metrics."""
    require_admin(request)
    adm = get_admin_service()

    metrics = adm.obtener_metricas_agregadas()
    return metrics


@app.get("/metrics/warnings")
async def get_warnings(request: Request):
    """Get admin warnings (expirations, issues, etc.)."""
    require_admin(request)
    adm = get_admin_service()

    warnings = adm.obtener_warnings_admin()
    return {"warnings": warnings}


@app.get("/metrics/expirations")
async def get_expirations(request: Request, days: int = Query(30, ge=1, le=365)):
    """Get upcoming subscription expirations."""
    require_admin(request)
    adm = get_admin_service()

    expirations = adm.listar_proximos_vencimientos(days)
    # Normalize response fields for admin-web
    try:
        from datetime import date

        today = date.today()
        normalized = []
        for e in expirations:
            next_due = e.get("next_due_date")
            # psycopg2 may return date, datetime, or string
            if next_due is None:
                valid_until = None
                days_remaining = None
            else:
                try:
                    due_date = (
                        next_due.date() if hasattr(next_due, "date") else next_due
                    )
                    if isinstance(due_date, str):
                        from datetime import datetime

                        due_date = datetime.fromisoformat(due_date[:10]).date()
                    valid_until = str(due_date)
                    days_remaining = (due_date - today).days
                except Exception:
                    valid_until = str(next_due)
                    days_remaining = None
            normalized.append(
                {
                    "gym_id": e.get("gym_id"),
                    "nombre": e.get("nombre"),
                    "subdominio": e.get("subdominio"),
                    "valid_until": valid_until,
                    "days_remaining": days_remaining,
                }
            )
        expirations = normalized
    except Exception:
        pass
    return {"expirations": expirations}


@app.get("/admin/plans")
async def list_admin_plans(request: Request):
    """List all available gym subscription plans."""
    require_admin(request)
    adm = get_admin_service()
    plans = adm.listar_planes()
    return {"plans": plans}


@app.post("/gyms/{gym_id}/subscription")
async def assign_gym_subscription(
    request: Request,
    gym_id: int,
    plan_id: int = Form(...),
    start_date: str = Form(None),
    end_date: str = Form(None),
):
    """Manually assign a subscription to a gym (without payment)."""
    require_admin(request)
    adm = get_admin_service()

    ok = adm.asignar_suscripcion_manual(gym_id, plan_id, end_date, start_date)
    if not ok:
        raise HTTPException(status_code=400, detail="Error assigning subscription")

    adm.log_action("owner", "assign_subscription", gym_id, f"plan={plan_id}")
    return {"ok": True}


# ========== PAYMENTS ROUTES ==========


@app.get("/gyms/{gym_id}/payments")
async def list_gym_payments(request: Request, gym_id: int):
    """List all payments for a gym."""
    require_admin(request)
    adm = get_admin_service()

    payments = adm.listar_pagos(gym_id)
    return {"payments": payments}


@app.post("/gyms/{gym_id}/payments")
async def register_payment(
    request: Request,
    gym_id: int,
    plan: str = Form(None),
    plan_id: str = Form(None),
    amount: float = Form(...),
    currency: str = Form("ARS"),
    valid_until: str = Form(None),
    status: str = Form("paid"),
    notes: str = Form(None),
    provider: str = Form(None),
    external_reference: str = Form(None),
    idempotency_key: str = Form(None),
    apply_to_subscription: str = Form("true"),
    periods: str = Form("1"),
):
    """Register a payment for a gym."""
    require_admin(request)
    adm = get_admin_service()

    try:
        pid = (
            int(plan_id) if plan_id is not None and str(plan_id).strip() != "" else None
        )
    except Exception:
        pid = None
    try:
        per = int(periods) if periods is not None and str(periods).strip() != "" else 1
    except Exception:
        per = 1
    apply_flag = str(apply_to_subscription or "true").strip().lower() in (
        "true",
        "1",
        "yes",
        "y",
        "on",
    )

    ok = adm.registrar_pago(
        gym_id,
        plan,
        amount,
        currency,
        valid_until,
        status,
        notes,
        plan_id=pid,
        provider=provider,
        external_reference=external_reference,
        idempotency_key=idempotency_key,
        apply_to_subscription=apply_flag,
        periods=per,
    )
    if ok:
        adm.log_action("owner", "register_payment", gym_id, f"{amount} {currency}")
    return {"ok": ok}


@app.get("/payments/recent")
async def get_recent_payments(request: Request, limit: int = Query(10, ge=1, le=100)):
    """Get recent payments across all gyms."""
    require_admin(request)
    adm = get_admin_service()

    payments = adm.listar_pagos_recientes(limit)
    return {"payments": payments}


@app.get("/payments")
async def list_payments_advanced(
    request: Request,
    gym_id: int = Query(None),
    status: str = Query(None),
    q: str = Query(None),
    desde: str = Query(None),
    hasta: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    require_admin(request)
    adm = get_admin_service()
    return adm.listar_pagos_avanzado(
        gym_id=gym_id,
        status=status,
        q=q,
        desde=desde,
        hasta=hasta,
        page=page,
        page_size=page_size,
    )


@app.put("/gyms/{gym_id}/payments/{payment_id}")
async def update_gym_payment(request: Request, gym_id: int, payment_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    result = adm.actualizar_pago_gym(int(gym_id), int(payment_id), payload)
    if result.get("ok"):
        adm.log_action(
            "owner", "update_payment", int(gym_id), f"payment_id={payment_id}"
        )
    return result


@app.delete("/gyms/{gym_id}/payments/{payment_id}")
async def delete_gym_payment(request: Request, gym_id: int, payment_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.eliminar_pago_gym(int(gym_id), int(payment_id))
    if result.get("ok") and int(result.get("deleted") or 0) > 0:
        adm.log_action(
            "owner", "delete_payment", int(gym_id), f"payment_id={payment_id}"
        )
    return result


# ========== AUDIT ROUTES ==========


@app.get("/audit")
async def get_audit_summary(request: Request, days: int = Query(7, ge=1, le=90)):
    """Get audit summary for the last N days."""
    require_admin(request)
    adm = get_admin_service()

    summary = adm.resumen_auditoria(days)
    return summary


@app.get("/gyms/{gym_id}/audit")
async def get_gym_audit(
    request: Request, gym_id: int, limit: int = Query(50, ge=1, le=200)
):
    """Get audit log for a specific gym."""
    require_admin(request)
    adm = get_admin_service()

    audit = adm.obtener_auditoria_gym(gym_id, limit)
    return {"audit": audit}


# ========== BATCH OPERATIONS (used by admin-web) ==========


@app.post("/gyms/batch/provision")
async def batch_provision(request: Request):
    """Provision (or re-provision) multiple gyms. Expects JSON {ids: number[]}."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ids = data.get("ids") or []
    try:
        ids = [int(x) for x in ids]
    except Exception:
        ids = []
    result = adm.batch_provision(ids)
    try:
        adm.log_action("owner", "batch_provision", None, f"count={len(ids)}")
    except Exception:
        pass
    return result


@app.get("/gyms/{gym_id}/provision/status")
async def gym_provision_status(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    return adm.tenant_migration_status(int(gym_id))


@app.post("/gyms/{gym_id}/provision")
async def gym_provision(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.provision_tenant_migrations(int(gym_id))
    try:
        if result.get("ok"):
            adm.log_action("owner", "provision_tenant_migrations", int(gym_id), None)
        else:
            adm.log_action(
                "owner",
                "provision_tenant_migrations_failed",
                int(gym_id),
                str(result.get("error") or ""),
            )
    except Exception:
        pass
    return result


@app.post("/gyms/batch/suspend")
async def batch_suspend(request: Request):
    """Suspend multiple gyms. Expects JSON {ids, reason?, until?, hard?}."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ids = data.get("ids") or []
    reason = data.get("reason")
    until = data.get("until")
    hard = bool(data.get("hard") or False)
    try:
        ids = [int(x) for x in ids]
    except Exception:
        ids = []
    result = adm.batch_suspend(ids, reason=reason, until=until, hard=hard)
    try:
        adm.log_action("owner", "batch_suspend", None, f"count={len(ids)}")
    except Exception:
        pass
    return result


@app.post("/gyms/batch/reactivate")
async def batch_reactivate(request: Request):
    """Reactivate multiple gyms. Expects JSON {ids}."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ids = data.get("ids") or []
    try:
        ids = [int(x) for x in ids]
    except Exception:
        ids = []
    result = adm.batch_reactivate(ids)
    try:
        adm.log_action("owner", "batch_reactivate", None, f"count={len(ids)}")
    except Exception:
        pass
    return result


@app.post("/gyms/batch/remind")
async def batch_remind(request: Request):
    """Send reminder message to multiple gym owners. Expects JSON {ids, message}."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ids = data.get("ids") or []
    message = str(data.get("message") or "").strip()
    try:
        ids = [int(x) for x in ids]
    except Exception:
        ids = []
    if not message:
        return JSONResponse({"ok": False, "error": "message_required"}, status_code=400)
    result = adm.batch_send_owner_message(ids, message)
    try:
        adm.log_action("owner", "batch_remind", None, f"count={len(ids)}")
    except Exception:
        pass
    return result


@app.post("/gyms/batch/maintenance")
async def batch_maintenance(request: Request):
    """Enable maintenance mode for multiple gyms. Expects JSON {ids, message, until?}."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ids = data.get("ids") or []
    message = str(data.get("message") or "").strip() or None
    until = data.get("until")
    try:
        ids = [int(x) for x in ids]
    except Exception:
        ids = []
    if until:
        result = adm.batch_schedule_maintenance(ids, until, message)
    else:
        result = adm.batch_set_maintenance(ids, message)
    try:
        adm.log_action("owner", "batch_maintenance", None, f"count={len(ids)}")
    except Exception:
        pass
    return result


# ========== WHATSAPP CONFIG ROUTES (used by admin-web) ==========


@app.post("/gyms/{gym_id}/whatsapp")
async def update_gym_whatsapp(request: Request, gym_id: int):
    """Update WhatsApp configuration for a gym (admin-web expects this endpoint)."""
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    ok = adm.set_gym_whatsapp_config(
        gym_id,
        data.get("phone_id"),
        data.get("access_token"),
        data.get("business_account_id"),
        data.get("verify_token"),
        data.get("app_secret"),
        data.get("nonblocking"),
        data.get("send_timeout_seconds"),
    )
    if ok:
        try:
            adm.log_action("owner", "update_gym_whatsapp", gym_id, None)
        except Exception:
            pass
    return {"ok": bool(ok)}


@app.delete("/gyms/{gym_id}/whatsapp")
async def clear_gym_whatsapp(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    ok = adm.clear_gym_whatsapp_config(gym_id)
    if ok:
        try:
            adm.log_action("owner", "clear_gym_whatsapp", gym_id, None)
        except Exception:
            pass
    return {"ok": bool(ok)}


# ========== GYM REMINDER MESSAGE (used by admin-web) ==========


@app.get("/gyms/{gym_id}/reminder")
async def get_gym_reminder_message(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    msg = adm.get_gym_reminder_message(gym_id)
    return {"message": msg or ""}


@app.post("/gyms/{gym_id}/reminder")
async def set_gym_reminder_message(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    message = (data.get("message") or "").strip()
    result = adm.set_gym_reminder_message(gym_id, message)
    if result.get("ok"):
        try:
            adm.log_action("owner", "set_gym_reminder_message", gym_id, None)
        except Exception:
            pass
    return result


# ========== GYM ATTENDANCE POLICY (used by admin-web) ==========


@app.get("/gyms/{gym_id}/attendance-policy")
async def get_gym_attendance_policy(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    return adm.get_gym_attendance_policy(gym_id)


@app.post("/gyms/{gym_id}/attendance-policy")
async def set_gym_attendance_policy(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    raw = data.get("attendance_allow_multiple_per_day")
    if isinstance(raw, bool):
        allow = raw
    elif isinstance(raw, (int, float)):
        allow = bool(raw)
    else:
        s = str(raw or "").strip().lower()
        allow = s in ("1", "true", "yes", "y", "on")
    return adm.set_gym_attendance_policy(gym_id, allow)


@app.get("/gyms/{gym_id}/feature-flags")
async def get_gym_feature_flags(request: Request, gym_id: int, scope: str = "gym", branch_id: int = 0):
    require_admin(request)
    adm = get_admin_service()
    return adm.get_gym_feature_flags(int(gym_id), scope=scope, branch_id=int(branch_id) if branch_id else None)


@app.put("/gyms/{gym_id}/feature-flags")
async def set_gym_feature_flags(request: Request, gym_id: int, scope: str = "gym", branch_id: int = 0):
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    flags = data.get("flags") if isinstance(data, dict) else {}
    result = adm.set_gym_feature_flags(
        int(gym_id), flags, scope=scope, branch_id=int(branch_id) if branch_id else None
    )
    if not bool(result.get("ok")):
        return JSONResponse(result, status_code=400)
    return result


@app.get("/gyms/{gym_id}/tipos-cuota")
async def list_gym_tipos_cuota(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    return adm.list_gym_tipos_cuota(int(gym_id))


@app.get("/gyms/{gym_id}/tipos-clases")
async def list_gym_tipos_clases(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    return adm.list_gym_tipos_clases(int(gym_id))


@app.get("/gyms/{gym_id}/tipos-cuota/{tipo_cuota_id}/entitlements")
async def get_gym_tipo_cuota_entitlements(request: Request, gym_id: int, tipo_cuota_id: int):
    require_admin(request)
    adm = get_admin_service()
    return adm.get_gym_tipo_cuota_entitlements(int(gym_id), int(tipo_cuota_id))


@app.put("/gyms/{gym_id}/tipos-cuota/{tipo_cuota_id}/entitlements")
async def set_gym_tipo_cuota_entitlements(request: Request, gym_id: int, tipo_cuota_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        data = await request.json()
    except Exception:
        data = {}
    return adm.set_gym_tipo_cuota_entitlements(int(gym_id), int(tipo_cuota_id), data or {})


# ========== BRANDING ROUTES ==========


@app.get("/gyms/{gym_id}/branding")
async def get_gym_branding(request: Request, gym_id: int):
    """Get branding configuration for a gym."""
    require_admin(request)
    adm = get_admin_service()

    branding = adm.get_gym_branding(gym_id)
    return {"branding": branding}


@app.post("/gyms/{gym_id}/branding")
async def save_gym_branding(
    request: Request,
    gym_id: int,
    nombre_publico: str = Form(None),
    direccion: str = Form(None),
    logo_url: str = Form(None),
    color_primario: str = Form(None),
    color_secundario: str = Form(None),
    color_fondo: str = Form(None),
    color_texto: str = Form(None),
    portal_tagline: str = Form(None),
    footer_text: str = Form(None),
    show_powered_by: str = Form(None),
    support_whatsapp_enabled: str = Form(None),
    support_whatsapp: str = Form(None),
    support_email_enabled: str = Form(None),
    support_email: str = Form(None),
    support_url_enabled: str = Form(None),
    support_url: str = Form(None),
    portal_enable_checkin: str = Form(None),
    portal_enable_member: str = Form(None),
    portal_enable_staff: str = Form(None),
    portal_enable_owner: str = Form(None),
):
    """Save branding configuration for a gym."""
    require_admin(request)
    adm = get_admin_service()

    def _parse_bool(v: Any) -> Optional[bool]:
        if v is None:
            return None
        s = str(v).strip().lower()
        if s in ("1", "true", "yes", "y", "on"):
            return True
        if s in ("0", "false", "no", "n", "off"):
            return False
        return None

    branding = {}
    if nombre_publico is not None:
        branding["nombre_publico"] = nombre_publico
    if direccion is not None:
        branding["direccion"] = direccion
    if logo_url is not None:
        branding["logo_url"] = logo_url
    if color_primario is not None:
        branding["color_primario"] = color_primario
    if color_secundario is not None:
        branding["color_secundario"] = color_secundario
    if color_fondo is not None:
        branding["color_fondo"] = color_fondo
    if color_texto is not None:
        branding["color_texto"] = color_texto
    if portal_tagline is not None:
        branding["portal_tagline"] = portal_tagline
    if footer_text is not None:
        branding["footer_text"] = footer_text

    v_show_powered_by = _parse_bool(show_powered_by)
    if v_show_powered_by is not None:
        branding["show_powered_by"] = v_show_powered_by

    v_support_whatsapp_enabled = _parse_bool(support_whatsapp_enabled)
    if v_support_whatsapp_enabled is not None:
        branding["support_whatsapp_enabled"] = v_support_whatsapp_enabled
    if support_whatsapp is not None:
        branding["support_whatsapp"] = support_whatsapp

    v_support_email_enabled = _parse_bool(support_email_enabled)
    if v_support_email_enabled is not None:
        branding["support_email_enabled"] = v_support_email_enabled
    if support_email is not None:
        branding["support_email"] = support_email

    v_support_url_enabled = _parse_bool(support_url_enabled)
    if v_support_url_enabled is not None:
        branding["support_url_enabled"] = v_support_url_enabled
    if support_url is not None:
        branding["support_url"] = support_url

    v_portal_enable_checkin = _parse_bool(portal_enable_checkin)
    if v_portal_enable_checkin is not None:
        branding["portal_enable_checkin"] = v_portal_enable_checkin
    v_portal_enable_member = _parse_bool(portal_enable_member)
    if v_portal_enable_member is not None:
        branding["portal_enable_member"] = v_portal_enable_member
    v_portal_enable_staff = _parse_bool(portal_enable_staff)
    if v_portal_enable_staff is not None:
        branding["portal_enable_staff"] = v_portal_enable_staff
    v_portal_enable_owner = _parse_bool(portal_enable_owner)
    if v_portal_enable_owner is not None:
        branding["portal_enable_owner"] = v_portal_enable_owner

    result = adm.save_gym_branding(gym_id, branding)
    return result


@app.post("/gyms/{gym_id}/logo")
async def upload_gym_logo(request: Request, gym_id: int, file: UploadFile = File(...)):
    """Upload a logo image for a gym to B2 storage."""
    require_admin(request)
    adm = get_admin_service()

    # Validate file type
    allowed_types = [
        "image/png",
        "image/jpeg",
        "image/gif",
        "image/webp",
        "image/svg+xml",
    ]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}",
        )

    # Read file content
    content = await file.read()

    # Limit file size (5MB)
    max_size = 5 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")

    # Upload to B2
    result = adm.upload_gym_asset(
        gym_id, content, file.filename or "logo.png", file.content_type
    )

    if result.get("ok"):
        # Automatically save as logo_url in branding
        adm.save_gym_branding(gym_id, {"logo_url": result["url"]})

    return result


# ========== SUBDOMAIN ROUTES ==========


@app.get("/subdomain/check")
async def check_subdomain(request: Request, subdomain: str = Query(...)):
    """Check if a subdomain is available."""
    require_admin(request)
    adm = get_admin_service()

    available = adm.subdominio_disponible(subdomain)
    return {"subdomain": subdomain, "available": available}


@app.get("/subdomain/suggest")
async def suggest_subdomain(request: Request, name: str = Query(...)):
    """Suggest a unique subdomain based on a name."""
    require_admin(request)
    adm = get_admin_service()

    suggested = adm.sugerir_subdominio_unico(name)
    return {"suggested": suggested}


# ========== PLANS ROUTES ==========


@app.get("/plans")
async def list_plans(request: Request):
    """List all available plans."""
    require_admin(request)
    adm = get_admin_service()
    plans = adm.listar_planes()
    return {"plans": plans}


@app.post("/plans")
async def create_plan(
    request: Request,
    name: str = Form(...),
    amount: float = Form(...),
    currency: str = Form("ARS"),
    period_days: int = Form(30),
):
    """Create a new plan."""
    require_admin(request)
    adm = get_admin_service()

    result = adm.crear_plan(name, amount, currency, period_days)
    if result.get("ok"):
        adm.log_action(
            "owner", "create_plan", None, f"Plan: {name}, Amount: {amount} {currency}"
        )
    return result


@app.put("/plans/{plan_id}")
async def update_plan(
    request: Request,
    plan_id: int,
    name: str = Form(None),
    amount: str = Form(None),
    currency: str = Form(None),
    period_days: str = Form(None),
):
    """Update an existing plan."""
    require_admin(request)
    adm = get_admin_service()

    updates = {}
    if name:
        updates["name"] = name
    if amount:
        updates["amount"] = float(amount)
    if currency:
        updates["currency"] = currency
    if period_days:
        updates["period_days"] = int(period_days)

    result = adm.actualizar_plan(plan_id, updates)
    if result.get("ok"):
        adm.log_action("owner", "update_plan", None, f"Plan ID: {plan_id}")
    return result


@app.post("/plans/{plan_id}/toggle")
async def toggle_plan(request: Request, plan_id: int, active: str = Form(...)):
    """Toggle a plan's active status."""
    require_admin(request)
    adm = get_admin_service()

    is_active = active.lower() in ("true", "1", "yes")
    result = adm.toggle_plan(plan_id, is_active)
    if result.get("ok"):
        adm.log_action(
            "owner", "toggle_plan", None, f"Plan ID: {plan_id}, Active: {is_active}"
        )
    return result


@app.delete("/plans/{plan_id}")
async def delete_plan(request: Request, plan_id: int):
    """Delete a plan."""
    require_admin(request)
    adm = get_admin_service()

    result = adm.eliminar_plan(plan_id)
    if result.get("ok"):
        adm.log_action("owner", "delete_plan", None, f"Plan ID: {plan_id}")
    return result


# ========== SETTINGS ROUTES ==========


@app.get("/settings")
async def get_settings(request: Request):
    require_admin(request)
    adm = get_admin_service()
    return adm.obtener_settings()


@app.put("/settings")
async def put_settings(request: Request):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    result = adm.upsert_settings(payload, actor_username="owner")
    if result.get("ok"):
        adm.log_action(
            "owner", "update_settings", None, f"keys={','.join(payload.keys())}"
        )
    return result


# ========== SUBSCRIPTIONS ROUTES ==========


@app.get("/gyms/{gym_id}/subscription")
async def get_gym_subscription(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    return adm.obtener_suscripcion_gym(gym_id)


@app.put("/gyms/{gym_id}/subscription")
async def put_gym_subscription(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    plan_id = payload.get("plan_id")
    if plan_id is None:
        raise HTTPException(status_code=400, detail="plan_id requerido")
    result = adm.upsert_suscripcion_gym(
        int(gym_id),
        int(plan_id),
        start_date=payload.get("start_date"),
        next_due_date=payload.get("next_due_date"),
        status=payload.get("status") or "active",
    )
    if result.get("ok"):
        adm.log_action(
            "owner", "upsert_subscription", int(gym_id), f"plan_id={plan_id}"
        )
    return result


@app.post("/gyms/{gym_id}/subscription/renew")
async def renew_gym_subscription(
    request: Request,
    gym_id: int,
    periods: str = Form("1"),
):
    require_admin(request)
    adm = get_admin_service()
    try:
        per = int(periods) if periods is not None and str(periods).strip() != "" else 1
    except Exception:
        per = 1
    result = adm.renovar_suscripcion_gym(int(gym_id), periods=per)
    if result.get("ok"):
        adm.log_action("owner", "renew_subscription", int(gym_id), f"periods={per}")
    return result


@app.get("/subscriptions")
async def list_subscriptions(
    request: Request,
    q: str = Query(None),
    status: str = Query(None),
    due_before_days: int = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    require_admin(request)
    adm = get_admin_service()
    return adm.listar_suscripciones_avanzado(
        q=q,
        status=status,
        due_before_days=due_before_days,
        page=page,
        page_size=page_size,
    )


@app.post("/subscriptions/maintenance/run")
async def run_subscriptions_maintenance(
    request: Request,
    days: str = Form(None),
    grace_days: str = Form(None),
):
    require_admin(request)
    adm = get_admin_service()
    cfg = {}
    try:
        st = adm.obtener_settings()
        rows = (st or {}).get("settings") or []
        for r in rows:
            k = (r or {}).get("key")
            if k:
                cfg[str(k)] = (r or {}).get("value")
    except Exception:
        cfg = {}
    subs = cfg.get("subscriptions") or {}

    try:
        eff_days = int(days) if days is not None and str(days).strip() != "" else None
    except Exception:
        eff_days = None
    if eff_days is None:
        eff_days = int((subs or {}).get("reminder_days_before", 7) or 7)

    try:
        eff_grace = (
            int(grace_days)
            if grace_days is not None and str(grace_days).strip() != ""
            else None
        )
    except Exception:
        eff_grace = None
    if eff_grace is None:
        eff_grace = int((subs or {}).get("grace_days", 0) or 0)

    run_id = str(uuid.uuid4())
    result = adm.ejecutar_mantenimiento_suscripciones(
        reminder_days=eff_days, grace_days=eff_grace, run_id=run_id
    )
    if result.get("ok"):
        adm.log_action(
            "owner", "subscriptions_maintenance_run", None, f"run_id={run_id}"
        )
    return result


@app.get("/jobs/runs")
async def list_job_runs(
    request: Request, job_key: str = Query(...), limit: int = Query(25, ge=1, le=200)
):
    require_admin(request)
    adm = get_admin_service()
    return adm.listar_job_runs(job_key, limit=int(limit))


@app.get("/jobs/runs/{run_id}")
async def get_job_run(request: Request, run_id: str):
    require_admin(request)
    adm = get_admin_service()
    return adm.obtener_job_run(run_id)


# ========== CRON & AUTOMATION ROUTES ==========


@app.post("/cron/subscriptions/maintenance")
async def cron_subscriptions_maintenance(
    request: Request,
    token: str = Query(None),
    days: str = Query(None),
    grace_days: str = Query(None),
    run_id: str = Query(None),
):
    import os

    expected_token = os.getenv("CRON_TOKEN", "").strip()
    header_token = request.headers.get("x-cron-token", "")
    if not expected_token or (
        token != expected_token and header_token != expected_token
    ):
        raise HTTPException(status_code=403, detail="Invalid cron token")

    adm = get_admin_service()
    cfg = {}
    try:
        st = adm.obtener_settings()
        rows = (st or {}).get("settings") or []
        for r in rows:
            k = (r or {}).get("key")
            if k:
                cfg[str(k)] = (r or {}).get("value")
    except Exception:
        cfg = {}

    subs = cfg.get("subscriptions") or {}
    try:
        eff_days = int(days) if days is not None and str(days).strip() != "" else None
    except Exception:
        eff_days = None
    if eff_days is None:
        eff_days = int((subs or {}).get("reminder_days_before", 7) or 7)

    try:
        eff_grace = (
            int(grace_days)
            if grace_days is not None and str(grace_days).strip() != ""
            else None
        )
    except Exception:
        eff_grace = None
    if eff_grace is None:
        eff_grace = int((subs or {}).get("grace_days", 0) or 0)

    effective_run_id = (
        str(run_id).strip()
        if run_id is not None and str(run_id).strip() != ""
        else None
    )
    if effective_run_id is None:
        effective_run_id = f"subscriptions_maintenance:{date.today().isoformat()}:{int(eff_days)}:{int(eff_grace)}"

    result = adm.ejecutar_mantenimiento_suscripciones(
        reminder_days=eff_days, grace_days=eff_grace, run_id=effective_run_id
    )
    return result


@app.post("/cron/reminders")
async def cron_daily_reminders(
    request: Request, token: str = Query(None), days: str = Query(None)
):
    """Cron endpoint for daily subscription reminders. Requires CRON_TOKEN."""
    import os

    expected_token = os.getenv("CRON_TOKEN", "").strip()

    # Check token from query or header
    header_token = request.headers.get("x-cron-token", "")
    if not expected_token or (
        token != expected_token and header_token != expected_token
    ):
        raise HTTPException(status_code=403, detail="Invalid cron token")

    adm = get_admin_service()
    cfg = {}
    try:
        st = adm.obtener_settings()
        rows = (st or {}).get("settings") or []
        for r in rows:
            k = (r or {}).get("key")
            if k:
                cfg[str(k)] = (r or {}).get("value")
    except Exception:
        cfg = {}
    subs = cfg.get("subscriptions") or {}
    enabled = bool((subs or {}).get("reminders_enabled", True))
    try:
        eff_days = int(days) if days is not None and str(days).strip() != "" else None
    except Exception:
        eff_days = None
    if eff_days is None:
        eff_days = int((subs or {}).get("reminder_days_before", 7) or 7)
    if not enabled:
        return {"ok": True, "sent": 0, "disabled": True}
    result = adm.enviar_recordatorios_vencimiento(eff_days)
    return {"ok": True, "sent": result.get("sent", 0), "days": eff_days}


@app.post("/cron/tenants/provision")
async def cron_tenants_provision(
    request: Request,
    token: str = Query(None),
    limit: int = Query(25, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status: str = Query("active"),
    only_outdated: bool = Query(True),
    dry_run: bool = Query(False),
    max_seconds: int = Query(25, ge=5, le=55),
):
    import os
    import time as _time

    expected_token = os.getenv("CRON_TOKEN", "").strip()
    header_token = request.headers.get("x-cron-token", "")
    if not expected_token or (
        token != expected_token and header_token != expected_token
    ):
        raise HTTPException(status_code=403, detail="Invalid cron token")

    adm = get_admin_service()
    lst = adm.list_gym_ids_for_provision(limit=int(limit), offset=int(offset), status=str(status))
    if not lst.get("ok"):
        return {"ok": False, "error": "list_failed"}

    started = _time.monotonic()
    results = []
    processed = 0
    provisioned = 0
    skipped = 0
    failed = 0

    for item in lst.get("items") or []:
        if _time.monotonic() - started >= float(max_seconds):
            break
        gid = int((item or {}).get("id") or 0)
        if gid <= 0:
            continue
        processed += 1
        st = adm.tenant_migration_status(gid)
        if not st.get("ok"):
            failed += 1
            results.append({"gym_id": gid, "action": "status_failed", "status": st})
            continue

        s = str(st.get("status") or "")
        if only_outdated and s in ("up_to_date",):
            skipped += 1
            results.append({"gym_id": gid, "action": "skip_up_to_date", "status": st})
            continue

        if dry_run:
            results.append({"gym_id": gid, "action": "would_provision", "status": st})
            continue

        pr = adm.provision_tenant_migrations(gid)
        if pr.get("ok"):
            provisioned += 1
            results.append({"gym_id": gid, "action": "provisioned", "result": pr})
        else:
            failed += 1
            results.append({"gym_id": gid, "action": "provision_failed", "result": pr})

    return {
        "ok": True,
        "dry_run": bool(dry_run),
        "only_outdated": bool(only_outdated),
        "processed": processed,
        "provisioned": provisioned,
        "skipped": skipped,
        "failed": failed,
        "limit": int(limit),
        "offset": int(offset),
        "next_offset": int(offset) + int(processed),
        "results": results,
    }


@app.post("/gyms/batch/auto-suspend")
async def auto_suspend_overdue(request: Request, grace_days: str = Form(None)):
    """Automatically suspend gyms that are overdue by more than grace_days."""
    require_admin(request)
    adm = get_admin_service()

    cfg = {}
    try:
        st = adm.obtener_settings()
        rows = (st or {}).get("settings") or []
        for r in rows:
            k = (r or {}).get("key")
            if k:
                cfg[str(k)] = (r or {}).get("value")
    except Exception:
        cfg = {}
    subs = cfg.get("subscriptions") or {}
    enabled = bool((subs or {}).get("auto_suspend_enabled", True))
    try:
        eff_grace = (
            int(grace_days)
            if grace_days is not None and str(grace_days).strip() != ""
            else None
        )
    except Exception:
        eff_grace = None
    if eff_grace is None:
        eff_grace = int((subs or {}).get("grace_days", 0) or 0)
    if not enabled:
        return {"ok": True, "suspended": 0, "disabled": True}

    result = adm.auto_suspender_vencidos(eff_grace)
    if result.get("suspended"):
        adm.log_action(
            "owner",
            "auto_suspend_overdue",
            None,
            f"Suspended: {result.get('suspended')}, Grace: {eff_grace}",
        )
    return result


# ========== WHATSAPP ROUTES ==========


@app.post("/gyms/{gym_id}/whatsapp/test")
async def send_whatsapp_test(
    request: Request,
    gym_id: int,
    phone: str = Form(...),
    message: str = Form("Mensaje de prueba desde IronHub Admin"),
):
    """Send a test WhatsApp message using a gym's WhatsApp configuration."""
    require_admin(request)
    adm = get_admin_service()

    # Get gym info
    gym = adm.obtener_gimnasio(gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gimnasio no encontrado")

    phone_id = (gym.get("whatsapp_phone_id") or "").strip()
    access_token_enc = (gym.get("whatsapp_access_token") or "").strip()
    access_token = (
        SecureConfig.decrypt_waba_secret(access_token_enc) if access_token_enc else ""
    )

    if not phone_id or not access_token:
        return {"ok": False, "error": "WhatsApp no configurado para este gimnasio"}

    # Normalize phone number
    import re

    phone_clean = re.sub(r"[^\d]", "", phone)
    if not phone_clean.startswith("549"):
        if phone_clean.startswith("0"):
            phone_clean = "549" + phone_clean[1:]
        elif phone_clean.startswith("9"):
            phone_clean = "54" + phone_clean
        else:
            phone_clean = "549" + phone_clean

    # Send via WhatsApp API
    import httpx

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            api_version = (os.getenv("WHATSAPP_API_VERSION") or "v19.0").strip()
            url = f"https://graph.facebook.com/{api_version}/{phone_id}/messages"
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": phone_clean,
                "type": "text",
                "text": {"body": message},
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }
            response = await client.post(url, json=payload, headers=headers)

            if response.status_code == 200:
                adm.log_action(
                    "owner", "whatsapp_test", gym_id, f"Sent test to {phone_clean}"
                )
                return {"ok": True, "message": f"Mensaje enviado a {phone_clean}"}
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("error", {}).get("message", response.text)
                return {"ok": False, "error": error_msg}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/gyms/{gym_id}/whatsapp/onboarding-events")
async def gym_whatsapp_onboarding_events(
    request: Request,
    gym_id: int,
    limit: int = Query(30, ge=1, le=200),
):
    require_admin(request)
    adm = get_admin_service()
    result = adm.get_gym_whatsapp_onboarding_events(int(gym_id), int(limit))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/whatsapp/templates")
async def list_whatsapp_template_catalog(request: Request, active_only: bool = False):
    require_admin(request)
    adm = get_admin_service()
    return {
        "ok": True,
        "templates": adm.listar_whatsapp_template_catalog(
            active_only=bool(active_only)
        ),
    }


@app.put("/whatsapp/templates/{template_name}")
async def upsert_whatsapp_template_catalog(request: Request, template_name: str):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    result = adm.upsert_whatsapp_template_catalog(
        template_name, payload if isinstance(payload, dict) else {}
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return {"ok": True}


@app.delete("/whatsapp/templates/{template_name}")
async def delete_whatsapp_template_catalog(request: Request, template_name: str):
    require_admin(request)
    adm = get_admin_service()
    result = adm.delete_whatsapp_template_catalog(template_name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return {"ok": True}


@app.post("/whatsapp/templates/sync-defaults")
async def sync_whatsapp_template_defaults(request: Request, overwrite: bool = True):
    require_admin(request)
    adm = get_admin_service()
    result = adm.sync_whatsapp_template_defaults(overwrite=bool(overwrite))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.post("/whatsapp/templates/bump-version")
async def bump_whatsapp_template_version(
    request: Request, template_name: str = Form(None)
):
    require_admin(request)
    name = str(template_name or "").strip()
    if not name:
        try:
            payload = await request.json()
            name = str((payload or {}).get("template_name") or "").strip()
        except Exception:
            name = ""
    adm = get_admin_service()
    result = adm.bump_whatsapp_template_version(name)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/whatsapp/bindings")
async def list_whatsapp_bindings(request: Request):
    require_admin(request)
    adm = get_admin_service()
    return {"ok": True, "bindings": adm.list_whatsapp_template_bindings()}


@app.put("/whatsapp/bindings/{binding_key}")
async def upsert_whatsapp_binding(request: Request, binding_key: str):
    require_admin(request)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    tname = str((payload or {}).get("template_name") or "").strip()
    adm = get_admin_service()
    result = adm.upsert_whatsapp_template_binding(binding_key, tname)
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return {"ok": True}


@app.post("/whatsapp/bindings/sync-defaults")
async def sync_whatsapp_bindings_defaults(request: Request, overwrite: bool = True):
    require_admin(request)
    adm = get_admin_service()
    result = adm.sync_whatsapp_template_bindings_defaults(overwrite=bool(overwrite))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/whatsapp/actions/specs")
async def list_whatsapp_action_specs(request: Request):
    require_admin(request)
    adm = get_admin_service()
    return {"ok": True, "items": adm.list_whatsapp_action_specs()}


@app.get("/gyms/{gym_id}/whatsapp/actions")
async def get_gym_whatsapp_actions(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.get_gym_whatsapp_actions(int(gym_id))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.put("/gyms/{gym_id}/whatsapp/actions/{action_key}")
async def set_gym_whatsapp_action(request: Request, gym_id: int, action_key: str):
    require_admin(request)
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    enabled = bool((payload or {}).get("enabled") is True)
    template_name = str((payload or {}).get("template_name") or "").strip()
    adm = get_admin_service()
    result = adm.set_gym_whatsapp_action(
        int(gym_id), action_key, enabled, template_name
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return {"ok": True}


@app.post("/gyms/{gym_id}/whatsapp/provision-templates")
async def provision_whatsapp_templates_for_gym(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.provision_whatsapp_templates_to_gym(int(gym_id))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/gyms/{gym_id}/whatsapp/health")
async def gym_whatsapp_health(request: Request, gym_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.whatsapp_health_check_for_gym(int(gym_id))
    if not result.get("ok"):
        err = result.get("error")
        if not err:
            try:
                errs = result.get("errors") or []
                if isinstance(errs, list) and errs:
                    err = str(errs[0])
            except Exception:
                err = None
        return JSONResponse(
            {**result, "ok": False, "error": str(err or "Error")}, status_code=200
        )
    return JSONResponse(result, status_code=200)


@app.get("/support/tickets")
async def admin_list_support_tickets(
    request: Request,
    status: str = Query(None),
    priority: str = Query(None),
    tenant: str = Query(None),
    assignee: str = Query(None),
    q: str = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
):
    require_admin(request)
    adm = get_admin_service()
    return adm.list_support_tickets(
        status=status, priority=priority, tenant=tenant, assignee=assignee, q=q, page=page, page_size=page_size
    )


@app.get("/support/tickets/{ticket_id}")
async def admin_get_support_ticket(request: Request, ticket_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.get_support_ticket(int(ticket_id))
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail="Not found")
    return result


@app.patch("/support/tickets/{ticket_id}/status")
async def admin_update_support_ticket_status(request: Request, ticket_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    st = str((payload or {}).get("status") or "").strip()
    result = adm.update_support_ticket_status(int(ticket_id), st, by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.post("/support/tickets/{ticket_id}/reply")
async def admin_reply_support_ticket(request: Request, ticket_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    msg = str((payload or {}).get("message") or "").strip()
    attachments = (payload or {}).get("attachments")
    result = adm.reply_support_ticket_admin(
        int(ticket_id), msg, by="owner", attachments=attachments if isinstance(attachments, list) else []
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.post("/support/tickets/{ticket_id}/internal-note")
async def admin_internal_note_support_ticket(request: Request, ticket_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    msg = str((payload or {}).get("message") or "").strip()
    result = adm.internal_note_support_ticket(int(ticket_id), msg, by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.patch("/support/tickets/{ticket_id}")
async def admin_patch_support_ticket(request: Request, ticket_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    tags = payload.get("tags")
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]
    if tags is not None and not isinstance(tags, list):
        tags = None
    result = adm.update_support_ticket(
        int(ticket_id),
        status=str(payload.get("status")).strip() if payload.get("status") is not None else None,
        priority=str(payload.get("priority")).strip() if payload.get("priority") is not None else None,
        assigned_to=str(payload.get("assigned_to")).strip() if payload.get("assigned_to") is not None else None,
        tags=tags,
        by="owner",
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/support/ops/summary")
async def admin_support_ops_summary(request: Request):
    require_admin(request)
    adm = get_admin_service()
    return adm.support_ops_summary()


@app.post("/support/tickets/batch")
async def admin_batch_support_tickets(request: Request):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    ids = payload.get("ticket_ids") or payload.get("ids") or []
    data = payload.get("data") or payload.get("update") or {}
    if not isinstance(ids, list):
        ids = []
    if not isinstance(data, dict):
        data = {}
    result = adm.batch_update_support_tickets([int(x) for x in ids if str(x).isdigit()], data, by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/support/tenants/{tenant}/settings")
async def admin_get_support_tenant_settings(request: Request, tenant: str):
    require_admin(request)
    adm = get_admin_service()
    result = adm.get_support_tenant_settings(str(tenant))
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.put("/support/tenants/{tenant}/settings")
async def admin_set_support_tenant_settings(request: Request, tenant: str):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    result = adm.set_support_tenant_settings(str(tenant), payload, by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.get("/changelogs")
async def admin_list_changelogs(
    request: Request,
    include_drafts: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
):
    require_admin(request)
    adm = get_admin_service()
    return adm.list_changelogs_admin(include_drafts=bool(include_drafts), page=page, page_size=page_size)


@app.post("/changelogs")
async def admin_create_changelog(request: Request):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    result = adm.create_changelog(payload if isinstance(payload, dict) else {}, by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.put("/changelogs/{changelog_id}")
async def admin_update_changelog(request: Request, changelog_id: int):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    result = adm.update_changelog(int(changelog_id), payload if isinstance(payload, dict) else {}, by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=str(result.get("error") or "Error"))
    return result


@app.delete("/changelogs/{changelog_id}")
async def admin_delete_changelog(request: Request, changelog_id: int):
    require_admin(request)
    adm = get_admin_service()
    result = adm.delete_changelog(int(changelog_id), by="owner")
    if not result.get("ok"):
        raise HTTPException(status_code=404, detail="Not found")
    return result
