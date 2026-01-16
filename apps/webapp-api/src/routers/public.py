import logging
import os
import time
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
from pathlib import Path
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse, Response, FileResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timezone
import os

from src.dependencies import get_admin_db, CURRENT_TENANT
from src.database.tenant_connection import get_tenant_session_factory
from src.services.gym_config_service import GymConfigService
from src.utils import (
    _is_tenant_suspended, _get_tenant_suspension_info,
    _resolve_theme_vars, _resolve_logo_url, get_gym_name, validate_tenant_name,
    _resolve_existing_dir
)
from src.services.b2_storage import get_file_url
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

@router.get("/public")
async def index(request: Request):
    """Root endpoint - returns JSON with gym info. Frontend handles the UI."""
    return JSONResponse({
        "ok": True,
        "gym_name": get_gym_name("Gimnasio"),
        "logo_url": _resolve_logo_url(),
        "message": "IronHub Gym API"
    })

@router.get("/gym/data")
async def gym_data_public(request: Request):
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

    cache_key = tenant or "__no_tenant__"
    now = int(time.time())
    cached = _GYM_DATA_PUBLIC_CACHE.get(cache_key)
    if cached and isinstance(cached, dict):
        try:
            if now - int(cached.get("ts") or 0) < _GYM_DATA_PUBLIC_CACHE_TTL_S:
                return JSONResponse(cached.get("data") or {"gym_name": "Gimnasio", "logo_url": "/assets/logo.svg"})
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
                    cfg = GymConfigService(session).obtener_configuracion_gimnasio() or {}
                    gym_name = str(cfg.get("gym_name") or cfg.get("nombre") or gym_name)
                    logo_url = cfg.get("logo_url") or cfg.get("gym_logo_url") or cfg.get("main_logo_url")
                finally:
                    session.close()
        except Exception:
            pass

    if logo_url:
        try:
            s = str(logo_url).strip()
            if s and not s.startswith("http") and not s.startswith("/"):
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
    return JSONResponse(payload)

@router.get("/checkin")
async def checkin_page(request: Request):
    """Check-in page - returns JSON. Frontend handles the UI."""
    return JSONResponse({
        "ok": True,
        "gym_name": get_gym_name("Gimnasio"),
        "logo_url": _resolve_logo_url(),
        "message": "Check-in endpoint"
    })

@router.get("/theme.css")
async def theme_css():
    tv = _resolve_theme_vars()
    lines = []
    lines.append(":root {")
    for k, v in tv.items():
        lines.append(f"  {k}: {v};")
    lines.append("}")
    lines.append("body { font-family: var(--font-base, Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji'); }")
    lines.append("h1,h2,h3,h4,h5,h6 { font-family: var(--font-heading, var(--font-base, Inter, system-ui, -apple-system, Segoe UI, Roboto, Ubuntu, Cantarell, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji')); }")
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
            v = (os.getenv("VERCEL_URL") or os.getenv("VERCEL_BRANCH_URL") or os.getenv("VERCEL_PROJECT_PRODUCTION_URL") or "").strip()
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
        import subprocess
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
        sub = CURRENT_TENANT.get() or ""
    except Exception:
        sub = ""
    adm = get_admin_db()
    if adm is None:
        return JSONResponse({"active": False})
    try:
        with adm.db.get_connection_context() as conn:  # type: ignore
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT status, suspended_until, suspended_reason FROM gyms WHERE subdominio = %s", (str(sub).strip().lower(),))
            row = cur.fetchone() or {}
            st = str((row.get("status") or "")).lower()
            active = (st == "maintenance")
            until = row.get("suspended_until")
            msg = row.get("suspended_reason")
            try:
                from src.database.connection import SessionLocal
                from src.services.gym_service import GymService
                tenant_session = SessionLocal()
                try:
                    svc = GymService(tenant_session)
                    config = svc.obtener_configuracion_gimnasio()
                    act = config.get("maintenance_modal_active")
                    if str(act or "").strip().lower() in ("1", "true", "yes", "on") and not active:
                        active = True
                        try:
                            m2 = config.get("maintenance_modal_message")
                            if m2:
                                msg = m2
                        except Exception:
                            pass
                        try:
                            u2 = config.get("maintenance_modal_until")
                            if u2:
                                until = u2
                        except Exception:
                            pass
                finally:
                    tenant_session.close()
            except Exception:
                pass
            active_now = False
            if active:
                try:
                    if until:
                        dt = until if hasattr(until, "tzinfo") else datetime.fromisoformat(str(until))
                        now = datetime.utcnow().replace(tzinfo=timezone.utc)
                        active_now = bool(dt <= now)
                    else:
                        active_now = True
                except Exception:
                    active_now = True
            try:
                u = until.isoformat() if hasattr(until, "isoformat") and until else (str(until or ""))
            except Exception:
                u = str(until or "")
            return JSONResponse({"active": bool(active), "active_now": bool(active_now), "until": u, "message": str(msg or "")})
    except Exception:
        return JSONResponse({"active": False})

@router.get("/maintenance_status")
async def api_maintenance_status_alias(request: Request):
    return await api_maintenance_status(request)

@router.get("/api/suspension_status")
async def api_suspension_status(request: Request):
    try:
        sub = CURRENT_TENANT.get() or ""
        if not sub:
            return JSONResponse({"suspended": False})
        sus = bool(_is_tenant_suspended(sub))
        info = _get_tenant_suspension_info(sub) if sus else None
        payload: Dict[str, Any] = {"suspended": sus}
        if info:
            payload.update({"reason": info.get("reason"), "until": info.get("until"), "hard": info.get("hard")})
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
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)

    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in ("1", "true", "yes") or os.getenv("ENV", "").lower() in ("dev", "development")
    allow_public = os.getenv("ALLOW_PUBLIC_ROUTINE_QR", "").lower() in ("1", "true", "yes")
    if not (dev_mode or allow_public):
        sess_uid = request.session.get("user_id") or request.session.get("checkin_user_id")
        if not sess_uid:
            msg = "Unauthorized"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=401)

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
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=404)
    
    if not bool(rutina.get("activa", True)):
        msg = "Rutina inactiva"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)
    
    return JSONResponse({"ok": True, "rutina": rutina})
