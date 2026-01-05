"""
IronHub Admin API
FastAPI backend for admin panel - Self-contained deployment
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Form, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Local imports (self-contained)
from src.database.raw_manager import RawPostgresManager
from src.services.admin_service import AdminService

# Initialize FastAPI app
app = FastAPI(
    title="IronHub Admin API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
origins = os.getenv("ALLOWED_ORIGINS", "").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins if origins[0] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("ADMIN_SESSION_SECRET", "admin-session-secret-change-me"),
    https_only=os.getenv("ENV", "production") == "production",
    same_site="lax",
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
    return result


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


@app.post("/gyms")
async def create_gym(
    request: Request,
    nombre: str = Form(...),
    subdominio: str = Form(None),
    owner_phone: str = Form(None),
):
    """Create a new gym with database provisioning."""
    require_admin(request)
    adm = get_admin_service()
    
    sub = (subdominio or "").strip().lower()
    if not sub:
        sub = adm.sugerir_subdominio_unico(nombre)
    
    result = adm.crear_gimnasio(nombre, sub, owner_phone=owner_phone)
    
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
    
    return gym


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
