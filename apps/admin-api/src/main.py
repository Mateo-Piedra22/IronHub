"""
IronHub Admin API
FastAPI backend for admin panel - Self-contained deployment
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Form, Query, UploadFile, File
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local imports (self-contained)
from src.database.raw_manager import RawPostgresManager
from src.services.admin_service import AdminService
from src.routers.payments import router as payments_router
from src.secure_config import SecureConfig

# Initialize FastAPI app
app = FastAPI(
    title="IronHub Admin API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Include routers
app.include_router(payments_router)

# CORS
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
_origins = [o.strip() for o in (origins or []) if o and o.strip()]
_allow_all = (len(_origins) == 0)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins if not _allow_all else ["*"],
    allow_credentials=(not _allow_all),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("ADMIN_SESSION_SECRET", "admin-session-secret-change-me"),
    https_only=os.getenv("ENV", "production") == "production",
    same_site="lax",
    domain=f".{os.getenv('TENANT_BASE_DOMAIN', 'ironhub.motiona.xyz')}"  # Allow cookie sharing
)

# Service instance (lazy loaded)
_admin_service = None

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
        return JSONResponse({"ok": False, "error": "Credenciales incorrectas"}, status_code=401)
    
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
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...)
):
    """Change the admin owner password."""
    require_admin(request)
    adm = get_admin_service()
    
    # Verify current password
    if not adm.verificar_owner_password(current_password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    
    # Validate new password
    if len(new_password.strip()) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 8 caracteres")
    
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
    status: str = Query(None)
):
    """List all gyms with pagination and filtering."""
    require_admin(request)
    adm = get_admin_service()
    result = adm.listar_gimnasios_avanzado(page, page_size, q or None, status or None, "id", "DESC")
    # Map 'items' to 'gyms' to match frontend expectations
    return {
        "gyms": result.get("items", []),
        "total": result.get("total", 0),
        "page": result.get("page", 1),
        "page_size": result.get("page_size", 20)
    }


@app.get("/gyms/public")
async def list_public_gyms():
    """List active gyms for public display (landing page). No authentication required."""
    adm = get_admin_service()
    try:
        # Only return active gyms with limited info
        result = adm.listar_gimnasios_avanzado(1, 50, None, "active", "nombre", "ASC")
        items = result.get("items", [])
        
        # Return only public-safe fields
        public_gyms = []
        for gym in items:
            public_gyms.append({
                "id": gym.get("id"),
                "nombre": gym.get("nombre"),
                "subdominio": gym.get("subdominio"),
                "status": gym.get("status", "active"),
            })
        
        return {"items": public_gyms, "total": len(public_gyms)}
    except Exception as e:
        logger.error(f"Error fetching public gyms: {e}")
        return {"items": [], "total": 0}


@app.get("/gyms/summary")
async def list_gyms_with_summary(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    q: str = Query(None),
    status: str = Query(None)
):
    """List all gyms with subscription and payment summary."""
    require_admin(request)
    adm = get_admin_service()
    result = adm.listar_gimnasios_con_resumen(page, page_size, q or None, status or None, "id", "DESC")
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
        wa_timeout = float(whatsapp_send_timeout_seconds) if whatsapp_send_timeout_seconds not in (None, "") else None
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


@app.get("/gyms/{gym_id}")
async def get_gym(request: Request, gym_id: int):
    """Get a single gym by ID."""
    require_admin(request)
    adm = get_admin_service()
    
    gym = adm.obtener_gimnasio(gym_id)
    if not gym:
        raise HTTPException(status_code=404, detail="Gym not found")

    try:
        gym["wa_configured"] = bool((gym.get("whatsapp_phone_id") or "").strip()) and bool((gym.get("whatsapp_access_token") or "").strip())
    except Exception:
        pass

    try:
        tenant_cfg = adm.get_tenant_whatsapp_active_config_for_gym(int(gym_id))
        if tenant_cfg.get("ok"):
            gym["tenant_whatsapp_phone_id"] = str(tenant_cfg.get("phone_id") or "")
            gym["tenant_whatsapp_waba_id"] = str(tenant_cfg.get("waba_id") or "")
            gym["tenant_whatsapp_access_token_present"] = bool(tenant_cfg.get("access_token_present") is True)
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


@app.put("/gyms/{gym_id}")
async def update_gym(
    request: Request,
    gym_id: int,
    nombre: str = Form(None),
    subdominio: str = Form(None)
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
    reason: str = Form(None)
):
    """Set a gym's status (active, suspended, maintenance)."""
    require_admin(request)
    adm = get_admin_service()
    
    ok = adm.set_estado_gimnasio(gym_id, status, hard_suspend, suspended_until, reason)
    adm.log_action("owner", "set_gym_status", gym_id, f"{status}|{reason}")
    return {"ok": ok}


@app.post("/gyms/{gym_id}/owner-password")
async def set_gym_owner_password(
    request: Request,
    gym_id: int,
    new_password: str = Form(...)
):
    """Set the owner password for a specific gym."""
    require_admin(request)
    adm = get_admin_service()
    
    if len(new_password.strip()) < 6:
        raise HTTPException(status_code=400, detail="La contraseña debe tener al menos 6 caracteres")
    
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
                    due_date = next_due.date() if hasattr(next_due, "date") else next_due
                    if isinstance(due_date, str):
                        from datetime import datetime
                        due_date = datetime.fromisoformat(due_date[:10]).date()
                    valid_until = str(due_date)
                    days_remaining = (due_date - today).days
                except Exception:
                    valid_until = str(next_due)
                    days_remaining = None
            normalized.append({
                "gym_id": e.get("gym_id"),
                "nombre": e.get("nombre"),
                "subdominio": e.get("subdominio"),
                "valid_until": valid_until,
                "days_remaining": days_remaining,
            })
        expirations = normalized
    except Exception:
        pass
    return {"expirations": expirations}


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
    amount: float = Form(...),
    currency: str = Form("ARS"),
    valid_until: str = Form(None),
    status: str = Form("paid"),
    notes: str = Form(None)
):
    """Register a payment for a gym."""
    require_admin(request)
    adm = get_admin_service()
    
    ok = adm.registrar_pago(gym_id, plan, amount, currency, valid_until, status, notes)
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


# ========== AUDIT ROUTES ==========

@app.get("/audit")
async def get_audit_summary(request: Request, days: int = Query(7, ge=1, le=90)):
    """Get audit summary for the last N days."""
    require_admin(request)
    adm = get_admin_service()
    
    summary = adm.resumen_auditoria(days)
    return summary


@app.get("/gyms/{gym_id}/audit")
async def get_gym_audit(request: Request, gym_id: int, limit: int = Query(50, ge=1, le=200)):
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
    color_texto: str = Form(None)
):
    """Save branding configuration for a gym."""
    require_admin(request)
    adm = get_admin_service()
    
    branding = {}
    if nombre_publico is not None: branding["nombre_publico"] = nombre_publico
    if direccion is not None: branding["direccion"] = direccion
    if logo_url is not None: branding["logo_url"] = logo_url
    if color_primario is not None: branding["color_primario"] = color_primario
    if color_secundario is not None: branding["color_secundario"] = color_secundario
    if color_fondo is not None: branding["color_fondo"] = color_fondo
    if color_texto is not None: branding["color_texto"] = color_texto
    
    result = adm.save_gym_branding(gym_id, branding)
    return result


@app.post("/gyms/{gym_id}/logo")
async def upload_gym_logo(
    request: Request,
    gym_id: int,
    file: UploadFile = File(...)
):
    """Upload a logo image for a gym to B2 storage."""
    require_admin(request)
    adm = get_admin_service()
    
    # Validate file type
    allowed_types = ["image/png", "image/jpeg", "image/gif", "image/webp", "image/svg+xml"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail=f"Invalid file type. Allowed: {', '.join(allowed_types)}")
    
    # Read file content
    content = await file.read()
    
    # Limit file size (5MB)
    max_size = 5 * 1024 * 1024
    if len(content) > max_size:
        raise HTTPException(status_code=400, detail="File too large. Max 5MB.")
    
    # Upload to B2
    result = adm.upload_gym_asset(gym_id, content, file.filename or "logo.png", file.content_type)
    
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
    period_days: int = Form(30)
):
    """Create a new plan."""
    require_admin(request)
    adm = get_admin_service()
    
    result = adm.crear_plan(name, amount, currency, period_days)
    if result.get("ok"):
        adm.log_action("owner", "create_plan", None, f"Plan: {name}, Amount: {amount} {currency}")
    return result


@app.put("/plans/{plan_id}")
async def update_plan(
    request: Request,
    plan_id: int,
    name: str = Form(None),
    amount: str = Form(None),
    currency: str = Form(None),
    period_days: str = Form(None)
):
    """Update an existing plan."""
    require_admin(request)
    adm = get_admin_service()
    
    updates = {}
    if name: updates["name"] = name
    if amount: updates["amount"] = float(amount)
    if currency: updates["currency"] = currency
    if period_days: updates["period_days"] = int(period_days)
    
    result = adm.actualizar_plan(plan_id, updates)
    if result.get("ok"):
        adm.log_action("owner", "update_plan", None, f"Plan ID: {plan_id}")
    return result


@app.post("/plans/{plan_id}/toggle")
async def toggle_plan(
    request: Request,
    plan_id: int,
    active: str = Form(...)
):
    """Toggle a plan's active status."""
    require_admin(request)
    adm = get_admin_service()
    
    is_active = active.lower() in ("true", "1", "yes")
    result = adm.toggle_plan(plan_id, is_active)
    if result.get("ok"):
        adm.log_action("owner", "toggle_plan", None, f"Plan ID: {plan_id}, Active: {is_active}")
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


# ========== CRON & AUTOMATION ROUTES ==========

@app.post("/cron/reminders")
async def cron_daily_reminders(request: Request, token: str = Query(None), days: int = Query(7)):
    """Cron endpoint for daily subscription reminders. Requires CRON_TOKEN."""
    import os
    expected_token = os.getenv("CRON_TOKEN", "").strip()
    
    # Check token from query or header
    header_token = request.headers.get("x-cron-token", "")
    if not expected_token or (token != expected_token and header_token != expected_token):
        raise HTTPException(status_code=403, detail="Invalid cron token")
    
    adm = get_admin_service()
    result = adm.enviar_recordatorios_vencimiento(days)
    return {"ok": True, "sent": result.get("sent", 0)}


@app.post("/gyms/batch/auto-suspend")
async def auto_suspend_overdue(
    request: Request,
    grace_days: int = Form(0)
):
    """Automatically suspend gyms that are overdue by more than grace_days."""
    require_admin(request)
    adm = get_admin_service()
    
    result = adm.auto_suspender_vencidos(grace_days)
    if result.get("suspended"):
        adm.log_action("owner", "auto_suspend_overdue", None, f"Suspended: {result.get('suspended')}, Grace: {grace_days}")
    return result


# ========== WHATSAPP ROUTES ==========

@app.post("/gyms/{gym_id}/whatsapp/test")
async def send_whatsapp_test(
    request: Request,
    gym_id: int,
    phone: str = Form(...),
    message: str = Form("Mensaje de prueba desde IronHub Admin")
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
    access_token = SecureConfig.decrypt_waba_secret(access_token_enc) if access_token_enc else ""
    
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
                "text": {"body": message}
            }
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            response = await client.post(url, json=payload, headers=headers)
            
            if response.status_code == 200:
                adm.log_action("owner", "whatsapp_test", gym_id, f"Sent test to {phone_clean}")
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
    return {"ok": True, "templates": adm.listar_whatsapp_template_catalog(active_only=bool(active_only))}


@app.put("/whatsapp/templates/{template_name}")
async def upsert_whatsapp_template_catalog(request: Request, template_name: str):
    require_admin(request)
    adm = get_admin_service()
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    result = adm.upsert_whatsapp_template_catalog(template_name, payload if isinstance(payload, dict) else {})
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
async def bump_whatsapp_template_version(request: Request, template_name: str = Form(None)):
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
    result = adm.set_gym_whatsapp_action(int(gym_id), action_key, enabled, template_name)
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
        return JSONResponse({**result, "ok": False, "error": str(err or "Error")}, status_code=200)
    return JSONResponse(result, status_code=200)

