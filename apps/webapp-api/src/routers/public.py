import logging
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy import text
from src.database.connection import AdminSessionLocal
from pathlib import Path
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates

from src.dependencies import CURRENT_TENANT
from src.database.tenant_connection import get_tenant_session_factory
from src.database.tenant_connection import validate_tenant_name
from src.services.gym_config_service import GymConfigService
from src.services.feature_flags_service import FeatureFlagsService
from src.utils import (
    _resolve_theme_vars,
    _resolve_logo_url,
    get_gym_name,
    _resolve_existing_dir,
)

# Import preview helper from gym router
try:
    from src.routers.gym import _get_excel_preview_routine
except ImportError:

    def _get_excel_preview_routine(uuid_str: str):
        return None


# get_webapp_base_url implementation (self-contained)
def get_webapp_base_url():
    """Get the webapp base URL from environment variables."""
    return os.getenv("BASE_URL", os.getenv("VERCEL_URL", "http://localhost:8000"))


router = APIRouter()
logger = logging.getLogger(__name__)

templates_dir = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

_GYM_DATA_PUBLIC_CACHE: Dict[str, Dict[str, Any]] = {}
_GYM_DATA_PUBLIC_CACHE_TTL_S = 300
_ADMIN_STATUS_CACHE: Dict[str, Dict[str, Any]] = {}
_ADMIN_STATUS_CACHE_TTL_S = 30


def _extract_tenant_public(request: Request) -> str:
    tenant = ""
    try:
        tenant = str(CURRENT_TENANT.get() or "").strip().lower()
    except Exception:
        tenant = ""
    if not tenant:
        try:
            tenant = str(request.headers.get("x-tenant") or "").strip().lower()
        except Exception:
            tenant = ""
    if tenant:
        try:
            ok, _err = validate_tenant_name(tenant)
            if not ok:
                tenant = ""
        except Exception:
            tenant = ""
    return tenant


def _get_branding_for_tenant(tenant: str) -> Dict[str, Any]:
    cache_key = tenant or "__no_tenant__"
    now = int(time.time())
    cached = _GYM_DATA_PUBLIC_CACHE.get(cache_key)
    if cached and isinstance(cached, dict):
        try:
            if now - int(cached.get("ts") or 0) < _GYM_DATA_PUBLIC_CACHE_TTL_S:
                return cached.get("data") or {
                    "gym_name": "Gimnasio",
                    "logo_url": "/assets/logo.svg",
                }
        except Exception:
            pass

    gym_name = "Gimnasio"
    logo_url: Optional[str] = None
    if tenant:
        try:
            factory = get_tenant_session_factory(tenant)
            if factory:
                session = factory()
                try:
                    cfg = (
                        GymConfigService(session).obtener_configuracion_gimnasio() or {}
                    )
                    gym_name = str(cfg.get("gym_name") or cfg.get("nombre") or gym_name)
                    logo_url = (
                        cfg.get("logo_url")
                        or cfg.get("gym_logo_url")
                        or cfg.get("main_logo_url")
                    )
                finally:
                    session.close()
        except Exception:
            pass

    if logo_url:
        try:
            s = str(logo_url).strip()
            if s and not s.startswith("http") and not s.startswith("/"):
                from src.services.b2_storage import get_file_url

                logo_url = get_file_url(s)
            else:
                logo_url = s
        except Exception:
            logo_url = None

    if not logo_url:
        logo_url = _resolve_logo_url()
    if not gym_name:
        gym_name = get_gym_name("Gimnasio")

    payload = {"gym_name": gym_name, "logo_url": logo_url}
    _GYM_DATA_PUBLIC_CACHE[cache_key] = {"ts": now, "data": payload}
    return payload


def _get_sucursales_for_tenant(tenant: str) -> Dict[str, Any]:
    if not tenant:
        return {"items": [], "error": "no_tenant"}
    try:
        factory = get_tenant_session_factory(tenant)
        if not factory:
            return {"items": [], "error": "no_factory"}
        ses = factory()
        try:
            rows = (
                ses.execute(
                    text(
                        """
                        SELECT id, nombre, codigo, activa
                        FROM sucursales
                        WHERE activa = TRUE
                        ORDER BY id ASC
                        """
                    )
                )
                .mappings()
                .all()
            )
            items = [
                {
                    "id": int(r.get("id")),
                    "nombre": str(r.get("nombre") or ""),
                    "codigo": str(r.get("codigo") or ""),
                    "activa": bool(r.get("activa"))
                    if r.get("activa") is not None
                    else True,
                }
                for r in (rows or [])
                if r and r.get("id") is not None
            ]
            return {"items": items}
        finally:
            ses.close()
    except Exception:
        return {"items": [], "error": "query_failed"}


def _get_admin_tenant_status(tenant: str) -> Dict[str, Any]:
    key = str(tenant or "").strip().lower() or "__no_tenant__"
    now = int(time.time())
    cached = _ADMIN_STATUS_CACHE.get(key)
    if cached and isinstance(cached, dict):
        try:
            if now - int(cached.get("ts") or 0) < _ADMIN_STATUS_CACHE_TTL_S:
                return cached.get("data") or {}
        except Exception:
            pass

    data: Dict[str, Any] = {}
    if tenant:
        try:
            ses = AdminSessionLocal()
            try:
                row = (
                    ses.execute(
                        text(
                            "SELECT status, suspended_until, suspended_reason "
                            "FROM gyms WHERE subdominio = :t LIMIT 1"
                        ),
                        {"t": str(tenant).strip().lower()},
                    )
                    .mappings()
                    .first()
                )
                if row:
                    data = dict(row)
            finally:
                ses.close()
        except Exception:
            data = {}

    _ADMIN_STATUS_CACHE[key] = {"ts": now, "data": data}
    return data


@router.get("/public")
async def index(request: Request):
    """Root endpoint - returns JSON with gym info. Frontend handles the UI."""
    return JSONResponse(
        {
            "ok": True,
            "gym_name": get_gym_name("Gimnasio"),
            "logo_url": _resolve_logo_url(),
            "message": "IronHub Gym API",
        }
    )


@router.get("/gym/data")
async def gym_data_public(request: Request):
    tenant = _extract_tenant_public(request)
    payload = _get_branding_for_tenant(tenant)
    resp = JSONResponse(payload)
    resp.headers["Cache-Control"] = (
        "public, max-age=60, s-maxage=300, stale-while-revalidate=600"
    )
    resp.headers["Vary"] = "X-Tenant, Origin"
    return resp


@router.get("/api/bootstrap")
async def api_bootstrap(request: Request, context: str = "auto"):
    tenant = _extract_tenant_public(request)
    branding = _get_branding_for_tenant(tenant)

    try:
        ctx = str(context or "auto").strip().lower()
    except Exception:
        ctx = "auto"

    user_id = request.session.get("user_id")
    role = request.session.get("role")
    logged_in = request.session.get("logged_in", False)
    gestion_prof_user_id = request.session.get("gestion_profesor_user_id")

    session_payload: Dict[str, Any] = {"authenticated": False, "user": None}
    try:
        if user_id and ctx in ("auto", "usuario", "user"):
            nombre = request.session.get("usuario_nombre", "")
            try:
                rol_out = str(role or "user").strip().lower() or "user"
            except Exception:
                rol_out = "user"
            if rol_out in ("dueño", "dueno"):
                rol_out = "owner"
            if rol_out in ("cliente", "socio", "member", "usuario", "usuarios"):
                rol_out = "user"
            if rol_out not in ("owner", "admin", "profesor", "user"):
                rol_out = "user"
            session_payload = {
                "authenticated": True,
                "user": {
                    "id": int(user_id),
                    "nombre": nombre,
                    "rol": rol_out,
                    "dni": None,
                },
            }
        elif gestion_prof_user_id is not None and ctx in ("auto", "gestion"):
            session_payload = {
                "authenticated": True,
                "user": {
                    "id": int(gestion_prof_user_id),
                    "nombre": request.session.get("usuario_nombre", "") or "Profesor",
                    "rol": "profesor",
                    "dni": None,
                },
            }
        else:
            try:
                role_norm = str(role or "").strip().lower()
            except Exception:
                role_norm = ""
            if (
                logged_in
                and role_norm in ("owner", "dueño", "dueno")
                and ctx in ("auto", "gestion")
            ):
                session_payload = {
                    "authenticated": True,
                    "user": {"id": 0, "nombre": "Dueño", "rol": "owner", "dni": None},
                }
    except Exception:
        session_payload = {"authenticated": False, "user": None}

    flags: Dict[str, Any] = {"tenant": tenant or None}
    try:
        admin_row = _get_admin_tenant_status(tenant) if tenant else {}
        st = str((admin_row.get("status") or "")).strip().lower()
        until = admin_row.get("suspended_until")
        msg = admin_row.get("suspended_reason")

        suspended = st in ("suspended", "suspension")
        maintenance = st == "maintenance"

        until_s = ""
        try:
            until_s = (
                until.isoformat()
                if hasattr(until, "isoformat") and until
                else (str(until or ""))
            )
        except Exception:
            until_s = str(until or "")

        flags.update(
            {
                "suspended": bool(suspended),
                "reason": str(msg or "") if suspended else "",
                "until": until_s if suspended else "",
                "maintenance": bool(maintenance),
                "maintenance_message": str(msg or "") if maintenance else "",
            }
        )
    except Exception:
        flags.update({"suspended": False, "maintenance": False})

    current_sucursal_id = request.session.get("sucursal_id")
    try:
        current_sucursal_id = (
            int(current_sucursal_id) if current_sucursal_id is not None else None
        )
    except Exception:
        current_sucursal_id = None

    try:
        if tenant:
            factory = get_tenant_session_factory(tenant)
            if factory:
                ses = factory()
                try:
                    ff = FeatureFlagsService(ses).get_flags(sucursal_id=current_sucursal_id)
                    if isinstance(ff, dict) and isinstance(ff.get("modules"), dict):
                        flags["modules"] = ff.get("modules")
                finally:
                    ses.close()
    except Exception:
        pass

    sucursales_info = _get_sucursales_for_tenant(tenant) if tenant else {"items": []}
    sucursales = sucursales_info.get("items") or []

    try:
        if current_sucursal_id is not None:
            active_ids = set()
            for s in sucursales or []:
                try:
                    sid = int((s or {}).get("id"))
                except Exception:
                    continue
                if bool((s or {}).get("activa")):
                    active_ids.add(sid)
            if active_ids and int(current_sucursal_id) not in active_ids:
                request.session.pop("sucursal_id", None)
                current_sucursal_id = None
    except Exception:
        pass

    try:
        if isinstance(session_payload.get("user"), dict):
            session_payload["user"]["sucursal_id"] = current_sucursal_id
    except Exception:
        pass

    branch_required = bool(session_payload.get("authenticated")) and (not current_sucursal_id) and bool(sucursales)

    payload = {
        "tenant": tenant or None,
        "gym": branding,
        "session": session_payload,
        "sucursales": sucursales,
        "sucursal_actual_id": current_sucursal_id,
        "branch_required": branch_required,
        "flags": flags,
    }
    resp = JSONResponse(payload)
    resp.headers["Cache-Control"] = "private, max-age=5"
    resp.headers["Vary"] = "Cookie, X-Tenant, Origin"
    return resp


@router.get("/checkin")
async def checkin_page(request: Request):
    """Check-in page - returns JSON. Frontend handles the UI."""
    return JSONResponse(
        {
            "ok": True,
            "gym_name": get_gym_name("Gimnasio"),
            "logo_url": _resolve_logo_url(),
            "message": "Check-in endpoint",
        }
    )


@router.get("/theme.css")
async def theme_css():
    tv = _resolve_theme_vars()
    lines = []
    lines.append(":root {")
    for k, v in tv.items():
        lines.append(f"  {k}: {v};")
    lines.append("}")
    lines.append(
        "body { font-family: var(--font-base, Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'); }"
    )
    lines.append(
        "h1,h2,h3,h4,h5,h6 { font-family: var(--font-heading, var(--font-base, Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji')); }"
    )
    return Response("\n".join(lines), media_type="text/css")


@router.get("/healthz")
async def healthz():
    try:
        details = {
            "status": "ok",
            "time": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        }
        try:
            from src.database.connection import SessionLocal

            session = SessionLocal()
            try:
                session.execute("SELECT 1")  # Simple connectivity check
                details["db"] = "ok"
            finally:
                session.close()
        except Exception:
            details["db"] = "error"
        return JSONResponse(details)
    except Exception:
        return JSONResponse({"status": "ok"})


@router.get("/webapp/base_url")
async def webapp_base_url():
    try:
        url = get_webapp_base_url()
        return JSONResponse({"base_url": url})
    except Exception:
        try:
            v = (
                os.getenv("VERCEL_URL")
                or os.getenv("VERCEL_BRANCH_URL")
                or os.getenv("VERCEL_PROJECT_PRODUCTION_URL")
                or ""
            ).strip()
            if v:
                if v.startswith("http://") or v.startswith("https://"):
                    return JSONResponse({"base_url": v})
                return JSONResponse({"base_url": f"https://{v}"})
        except Exception:
            pass
        return JSONResponse({"base_url": "http://127.0.0.1:8000/"})


@router.get("/favicon.png")
async def favicon_png():
    p = _resolve_existing_dir("assets") / "web-icon.png"
    if p.exists():
        return FileResponse(str(p))
    p2 = _resolve_existing_dir("assets") / "gym_logo.png"
    if p2.exists():
        return FileResponse(str(p2))
    return Response(status_code=404)


@router.get("/favicon.ico")
async def favicon_ico():
    p = _resolve_existing_dir("assets") / "gym_logo.ico"
    if p.exists():
        return FileResponse(str(p))
    return Response(status_code=204)


@router.get("/api/system/libreoffice")
async def api_system_libreoffice(request: Request):
    try:
        import shutil

        path = shutil.which("soffice") or shutil.which("soffice.exe")
        if not path:
            return JSONResponse({"available": False})
        # Optional: check version
        return JSONResponse({"available": True, "path": path})
    except Exception:
        return JSONResponse({"available": False})


@router.get("/api/theme")
async def api_theme_get():
    tv = _resolve_theme_vars()
    return JSONResponse(tv)


@router.get("/api/maintenance_status")
async def api_maintenance_status(request: Request):
    try:
        sub = str(CURRENT_TENANT.get() or "").strip().lower()
    except Exception:
        sub = ""
    if not sub:
        return JSONResponse({"active": False})

    try:
        row = _get_admin_tenant_status(sub) or {}
        st = str((row.get("status") or "")).strip().lower()
        active = st == "maintenance"
        until = row.get("suspended_until")
        msg = row.get("suspended_reason")
        active_now = False
        if active:
            try:
                if until:
                    dt = (
                        until
                        if hasattr(until, "tzinfo")
                        else datetime.fromisoformat(str(until))
                    )
                    now = datetime.utcnow().replace(tzinfo=timezone.utc)
                    active_now = bool(dt <= now)
                else:
                    active_now = True
            except Exception:
                active_now = True
        try:
            u = (
                until.isoformat()
                if hasattr(until, "isoformat") and until
                else (str(until or ""))
            )
        except Exception:
            u = str(until or "")
        return JSONResponse(
            {
                "active": bool(active),
                "active_now": bool(active_now),
                "until": u,
                "message": str(msg or ""),
            }
        )
    except Exception:
        return JSONResponse({"active": False})


@router.get("/maintenance_status")
async def api_maintenance_status_alias(request: Request):
    return await api_maintenance_status(request)


@router.get("/api/suspension_status")
async def api_suspension_status(request: Request):
    try:
        sub = str(CURRENT_TENANT.get() or "").strip().lower()
        if not sub:
            return JSONResponse({"suspended": False})
        row = _get_admin_tenant_status(sub) or {}
        st = str((row.get("status") or "")).strip().lower()
        sus = st in ("suspended", "suspension")
        until = row.get("suspended_until")
        msg = row.get("suspended_reason")
        try:
            u = (
                until.isoformat()
                if hasattr(until, "isoformat") and until
                else (str(until or ""))
            )
        except Exception:
            u = str(until or "")
        payload: Dict[str, Any] = {"suspended": bool(sus)}
        if sus:
            payload.update({"reason": str(msg or ""), "until": u, "hard": False})
        return JSONResponse(payload)
    except Exception:
        return JSONResponse({"suspended": False})


@router.get("/suspension_status")
async def api_suspension_status_alias(request: Request):
    return await api_suspension_status(request)


@router.get("/api/rutinas/qr_scan/{uuid_rutina}")
async def api_rutina_qr_scan(uuid_rutina: str, request: Request):
    """Valida UUID y retorna JSON con la rutina completa y ejercicios."""
    uid = str(uuid_rutina or "").strip()
    if not uid or len(uid) < 8:
        msg = "UUID inválido"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=400,
        )

    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    ) or os.getenv("ENV", "").lower() in ("dev", "development")
    allow_public = os.getenv("ALLOW_PUBLIC_ROUTINE_QR", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not (dev_mode or allow_public):
        sess_uid = request.session.get("user_id") or request.session.get(
            "checkin_user_id"
        )
        if not sess_uid:
            msg = "Unauthorized"
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": msg,
                    "error": msg,
                    "success": False,
                    "message": msg,
                },
                status_code=401,
            )

    rutina = None
    try:
        from src.database.connection import SessionLocal
        from src.services.training_service import TrainingService

        session = SessionLocal()
        try:
            svc = TrainingService(session)
            rutina = svc.obtener_rutina_por_uuid(uid)
        finally:
            session.close()
    except Exception as e:
        import logging

        logging.error(f"Error in qr_scan: {e}")
        rutina = None

    if rutina is None:
        # Fallback to ephemeral preview if available
        try:
            rutina = _get_excel_preview_routine(uid)
        except Exception:
            rutina = None

    if not rutina:
        msg = "Rutina no encontrada"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=404,
        )

    if not bool(rutina.get("activa", True)):
        msg = "Rutina inactiva"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=403,
        )

    return JSONResponse({"ok": True, "rutina": rutina})
