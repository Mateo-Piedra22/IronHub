"""
IronHub Webapp API
FastAPI backend for tenant gym applications
Multi-tenant API for gym member features
"""

import os
import re
import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, Request, HTTPException, Form, Depends
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# STARTUP CONFIGURATION VALIDATION
# ============================================================================
# Log database configuration status (without exposing sensitive values)
_db_host = os.getenv("DB_HOST", "localhost")
_db_name = os.getenv("DB_NAME", "")
_db_user = os.getenv("DB_USER", "postgres")
_has_password = bool(os.getenv("DB_PASSWORD"))
_admin_db_host = os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost"))
_admin_db_name = os.getenv("ADMIN_DB_NAME", "")

logger.info("=" * 60)
logger.info("WEBAPP-API STARTUP - Database Configuration")
logger.info("=" * 60)
logger.info(f"DB_HOST: {_db_host}")
logger.info(f"DB_NAME: {_db_name or '(not set)'}")
logger.info(f"DB_USER: {_db_user}")
logger.info(f"DB_PASSWORD: {'***configured***' if _has_password else '(NOT SET)'}")
logger.info(f"ADMIN_DB_HOST: {_admin_db_host}")
logger.info(f"ADMIN_DB_NAME: {_admin_db_name or '(not set)'}")
logger.info(f"TENANT_BASE_DOMAIN: {os.getenv('TENANT_BASE_DOMAIN', 'ironhub.motiona.xyz')}")

if _db_host == "localhost" and not os.getenv("DEVELOPMENT_MODE"):
    logger.warning("⚠️  DB_HOST is 'localhost' but DEVELOPMENT_MODE not set!")
    logger.warning("⚠️  This may indicate missing production environment configuration.")

logger.info("=" * 60)

# Import core services
import sys
from pathlib import Path

# Add core to path
core_path = Path(__file__).parent.parent.parent.parent / "core"
sys.path.insert(0, str(core_path.parent))

try:
    from src.database.tenant_connection import (
        get_tenant_session_factory,
        set_current_tenant,
        get_current_tenant
    )
    from src.database import DatabaseManager
    from src.models import Usuario, Pago, Rutina
except ImportError as e:
    logger.warning(f"Could not import core modules: {e}")
    get_tenant_session_factory = None
    DatabaseManager = None

# Initialize FastAPI app
app = FastAPI(
    title="IronHub Webapp API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS for wildcard subdomains and base domain
base_domain = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz")
# Escape dots for regex
escaped_domain = base_domain.replace(".", r"\.")

# Build list of allowed origins for explicit matches + regex for subdomains
allowed_origins = [
    f"https://{base_domain}",
    f"https://www.{base_domain}",
    f"https://api.{base_domain}",
    f"https://admin.{base_domain}",
    f"https://admin-api.{base_domain}",
    "http://localhost:3000",
    "http://localhost:3001",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
]

# Add Vercel preview URLs if available
vercel_url = os.getenv("VERCEL_URL")
if vercel_url:
    allowed_origins.append(f"https://{vercel_url}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_origin_regex=rf"https://.*\.{escaped_domain}|https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session middleware
# Configure cookie domain for cross-subdomain session sharing
base_domain = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz")
is_dev = os.getenv("DEVELOPMENT_MODE", "False").lower() == "true"

# In production, share cookie across all subdomains to prevent session loss
# BUT disable explicit domain if in Vercel Preview (to avoid domain mismatch with .vercel.app)
vercel_env = os.getenv("VERCEL_ENV", "production") 
if not is_dev and vercel_env != "preview":
    cookie_domain = f".{base_domain}"
else:
    cookie_domain = None

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "webapp-session-secret"),
    https_only=not is_dev,
    same_site="lax",
    domain=cookie_domain,
)


# =====================================================
# TENANT CONTEXT MIDDLEWARE
# =====================================================
# This middleware extracts the tenant from the subdomain or X-Tenant header
# and sets it in the context for all database operations.

@app.middleware("http")
async def tenant_context_middleware(request: Request, call_next):
    """
    Global middleware to extract and set tenant context for every request.
    This is CRITICAL for multi-tenant database routing.
    """
    tenant = None
    host = request.headers.get("host", "")
    base = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz")
    
    # Remove port if present
    host_clean = host.split(":")[0]
    
    # Enhanced logging for debugging tenant extraction
    x_tenant = request.headers.get("x-tenant")
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    
    # Log all sources for API routes (to diagnose issues)
    if request.url.path.startswith("/api/"):
        logger.info(f"TENANT DEBUG - Path: {request.url.path}")
        logger.info(f"TENANT DEBUG - Host: {host}, X-Tenant: {x_tenant}, Origin: {origin}")
    
    # 1. Try to extract from subdomain
    if host_clean.endswith(f".{base}"):
        subdomain = host_clean.replace(f".{base}", "")
        # Skip reserved subdomains
        if subdomain and subdomain not in ("www", "api", "admin", "admin-api"):
            tenant = subdomain
    
    # 2. Fallback to X-Tenant header (MOST IMPORTANT for cross-origin API calls)
    if not tenant and x_tenant:
        tenant = x_tenant.strip().lower()
        if request.url.path.startswith("/api/"):
            logger.info(f"TENANT DEBUG - Using X-Tenant header: {tenant}")
    
    # 3. Try to get from session (for gestion routes)
    if not tenant:
        try:
            # Session middleware runs before this, so session should be available
            session_tenant = request.session.get("tenant")
            if session_tenant:
                tenant = session_tenant
                if request.url.path.startswith("/api/"):
                    logger.info(f"TENANT DEBUG - Using session tenant: {tenant}")
        except Exception:
            pass
    
    # 4. Try to extract from Origin/Referer header (for cross-origin API calls)
    if not tenant and origin:
        import re
        match = re.search(rf"https?://([a-z0-9-]+)\.{re.escape(base)}", origin.lower())
        if match:
            candidate = match.group(1)
            if candidate not in ("www", "api", "admin", "admin-api"):
                tenant = candidate
                if request.url.path.startswith("/api/"):
                    logger.info(f"TENANT DEBUG - Using Origin extraction: {tenant}")
    
    # Set tenant context if found
    if tenant:
        set_current_tenant(tenant.strip().lower())
        if request.url.path.startswith("/api/"):
            logger.info(f"TENANT CONTEXT SET: {tenant} for {request.url.path}")
    else:
        # For API routes, log warning if no tenant found
        if request.url.path.startswith("/api/"):
            logger.warning(f"NO TENANT CONTEXT for API route: {request.url.path}")
    
    response = await call_next(request)
    return response


def extract_tenant_from_request(request: Request) -> str:
    """Extract tenant subdomain from request host"""
    host = request.headers.get("host", "")
    base = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz")
    
    # Remove port if present
    host = host.split(":")[0]
    
    # Check if it's a subdomain
    if host.endswith(f".{base}"):
        subdomain = host.replace(f".{base}", "")
        return subdomain if subdomain else None
    
    # Check X-Tenant header as fallback
    return request.headers.get("x-tenant")


def require_tenant(request: Request) -> str:
    """Middleware dependency to require tenant context"""
    tenant = extract_tenant_from_request(request)
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant not specified")
    
    set_current_tenant(tenant)
    return tenant


def get_user_from_session(request: Request) -> dict | None:
    """Get current user from session"""
    try:
        user_id = request.session.get("user_id")
        user_dni = request.session.get("user_dni")
        user_name = request.session.get("user_name")
        if user_id:
            return {"id": user_id, "dni": user_dni, "name": user_name}
    except Exception:
        pass
    return None


def require_auth(request: Request) -> dict:
    """Require authenticated user"""
    user = get_user_from_session(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


# Routes
@app.get("/")
async def root():
    return {"name": "IronHub Webapp API", "version": "2.0.0", "status": "running"}


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.post("/auth/login")
async def login(
    request: Request,
    dni: str = Form(...),
    pin: str = Form(...),
    tenant: str = Depends(require_tenant)
):
    """Authenticate gym member with DNI and PIN"""
    try:
        # Get tenant database session
        SessionFactory = get_tenant_session_factory(tenant)
        if not SessionFactory:
            return JSONResponse({"ok": False, "error": "Gym not found"}, status_code=404)
        
        session = SessionFactory()
        try:
            # Find user by DNI
            user = session.query(Usuario).filter(Usuario.dni == dni).first()
            
            if not user:
                return JSONResponse({"ok": False, "error": "Usuario no encontrado"}, status_code=401)
            
            # Verify PIN
            stored_pin = getattr(user, 'pin', None) or getattr(user, 'password', None)
            if not stored_pin or stored_pin != pin:
                return JSONResponse({"ok": False, "error": "PIN incorrecto"}, status_code=401)
            
            # Set session
            request.session["user_id"] = user.id
            request.session["user_dni"] = user.dni
            request.session["user_name"] = user.nombre
            request.session["tenant"] = tenant
            
            return {"ok": True, "user": {"id": user.id, "name": user.nombre}}
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return JSONResponse({"ok": False, "error": "Error de autenticación"}, status_code=500)


@app.post("/auth/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    return {"ok": True}


@app.get("/me")
async def get_me(
    request: Request,
    tenant: str = Depends(require_tenant),
    user: dict = Depends(require_auth)
):
    """Get current user profile"""
    try:
        SessionFactory = get_tenant_session_factory(tenant)
        session = SessionFactory()
        try:
            db_user = session.query(Usuario).filter(Usuario.id == user["id"]).first()
            if not db_user:
                raise HTTPException(status_code=404, detail="User not found")
            
            return {
                "id": db_user.id,
                "name": db_user.nombre,
                "dni": db_user.dni,
                "email": getattr(db_user, 'email', None),
                "phone": getattr(db_user, 'telefono', None),
                "status": getattr(db_user, 'estado', 'active'),
                "plan": getattr(db_user, 'plan', None),
                "memberSince": str(getattr(db_user, 'fecha_alta', '')),
            }
        finally:
            session.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        raise HTTPException(status_code=500, detail="Error fetching user")


@app.get("/payments")
async def get_payments(
    request: Request,
    tenant: str = Depends(require_tenant),
    user: dict = Depends(require_auth)
):
    """Get user's payment history"""
    try:
        SessionFactory = get_tenant_session_factory(tenant)
        session = SessionFactory()
        try:
            payments = session.query(Pago).filter(
                Pago.usuario_id == user["id"]
            ).order_by(Pago.fecha.desc()).limit(50).all()
            
            return {
                "payments": [
                    {
                        "id": p.id,
                        "date": str(p.fecha),
                        "amount": float(p.monto),
                        "concept": getattr(p, 'concepto', 'Cuota'),
                        "method": getattr(p, 'metodo', 'Efectivo'),
                        "status": "paid"
                    }
                    for p in payments
                ]
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error fetching payments: {e}")
        raise HTTPException(status_code=500, detail="Error fetching payments")


@app.get("/attendance")
async def get_attendance(
    request: Request,
    tenant: str = Depends(require_tenant),
    user: dict = Depends(require_auth)
):
    """Get user's attendance history"""
    try:
        from src.models import Asistencia
        from sqlalchemy import func, extract
        from datetime import datetime, timedelta
        
        SessionFactory = get_tenant_session_factory(tenant)
        if not SessionFactory:
            return {"attendance": [], "stats": {"thisMonth": 0, "lastMonth": 0, "avgDuration": 0}}
        
        session = SessionFactory()
        try:
            # Get attendance records
            records = session.query(Asistencia).filter(
                Asistencia.usuario_id == user["id"]
            ).order_by(Asistencia.fecha.desc()).limit(50).all()
            
            # Calculate stats
            now = datetime.now()
            this_month = now.month
            this_year = now.year
            last_month = now.month - 1 if now.month > 1 else 12
            last_year = now.year if now.month > 1 else now.year - 1
            
            this_month_count = session.query(func.count(Asistencia.id)).filter(
                Asistencia.usuario_id == user["id"],
                extract('month', Asistencia.fecha) == this_month,
                extract('year', Asistencia.fecha) == this_year
            ).scalar() or 0
            
            last_month_count = session.query(func.count(Asistencia.id)).filter(
                Asistencia.usuario_id == user["id"],
                extract('month', Asistencia.fecha) == last_month,
                extract('year', Asistencia.fecha) == last_year
            ).scalar() or 0
            
            return {
                "attendance": [
                    {
                        "id": a.id,
                        "date": str(a.fecha),
                        "checkIn": str(getattr(a, 'hora_entrada', '') or ''),
                        "checkOut": str(getattr(a, 'hora_salida', '') or ''),
                        "duration": getattr(a, 'duracion_minutos', 60) or 60
                    }
                    for a in records
                ],
                "stats": {
                    "thisMonth": this_month_count,
                    "lastMonth": last_month_count,
                    "avgDuration": 60,
                    "streak": 0
                }
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error fetching attendance: {e}")
        raise HTTPException(status_code=500, detail="Error fetching attendance")


@app.get("/routines")
async def get_routines(
    request: Request,
    tenant: str = Depends(require_tenant),
    user: dict = Depends(require_auth)
):
    """Get user's assigned routines"""
    try:
        from src.models import RutinaEjercicio, Ejercicio
        from sqlalchemy.orm import joinedload
        
        SessionFactory = get_tenant_session_factory(tenant)
        if not SessionFactory:
            return {"routine": None}
        
        session = SessionFactory()
        try:
            # Get user's assigned routine
            db_user = session.query(Usuario).filter(Usuario.id == user["id"]).first()
            rutina_id = getattr(db_user, 'rutina_id', None)
            
            if not rutina_id:
                return {"routine": None}
            
            rutina = session.query(Rutina).filter(Rutina.id == rutina_id).first()
            if not rutina:
                return {"routine": None}
            
            # Get exercises grouped by day
            ejercicios_raw = session.query(RutinaEjercicio).filter(
                RutinaEjercicio.rutina_id == rutina_id
            ).order_by(RutinaEjercicio.dia, RutinaEjercicio.orden).all()
            
            # Group exercises by day
            days_map = {}
            for ej in ejercicios_raw:
                dia = getattr(ej, 'dia', 1) or 1
                if dia not in days_map:
                    days_map[dia] = []
                
                # Get exercise details
                ejercicio_id = getattr(ej, 'ejercicio_id', None)
                ejercicio_nombre = None
                if ejercicio_id:
                    ejercicio = session.query(Ejercicio).filter(Ejercicio.id == ejercicio_id).first()
                    if ejercicio:
                        ejercicio_nombre = ejercicio.nombre
                
                days_map[dia].append({
                    "id": ej.id,
                    "ejercicio_id": ejercicio_id,
                    "ejercicio_nombre": ejercicio_nombre or getattr(ej, 'nombre', 'Ejercicio'),
                    "series": getattr(ej, 'series', 3),
                    "repeticiones": str(getattr(ej, 'repeticiones', '10')),
                    "descanso": getattr(ej, 'descanso', 60),
                    "notas": getattr(ej, 'notas', None),
                    "orden": getattr(ej, 'orden', 0)
                })
            
            # Build days array
            days = []
            for dia_num in sorted(days_map.keys()):
                days.append({
                    "numero": dia_num,
                    "nombre": f"Día {dia_num}",
                    "ejercicios": days_map[dia_num]
                })
            
            return {
                "routine": {
                    "id": rutina.id,
                    "name": getattr(rutina, 'nombre', 'Rutina'),
                    "description": getattr(rutina, 'descripcion', None),
                    "days": days
                }
            }
        finally:
            session.close()
    except Exception as e:
        logger.error(f"Error fetching routines: {e}")
        raise HTTPException(status_code=500, detail="Error fetching routines")


@app.get("/gym/info")
async def get_gym_info(
    request: Request,
    tenant: str = Depends(require_tenant)
):
    """Get gym public information"""
    try:
        # TODO: Fetch gym info from admin database
        return {
            "name": tenant.replace("_", " ").title(),
            "subdomain": tenant,
            "logo": None,
            "theme": {}
        }
    except Exception as e:
        logger.error(f"Error fetching gym info: {e}")
        raise HTTPException(status_code=500, detail="Error fetching gym info")


# =====================================================
# Include Routers
# =====================================================

# Import all routers
from src.routers import users, gym, payments, whatsapp, attendance, exercises, auth
from src.routers import profesores, inscripciones
from src.routers import reports, admin

# Include routers
app.include_router(auth.router, tags=["Auth"])
app.include_router(users.router, tags=["Users"])
app.include_router(gym.router, tags=["Gym"])
app.include_router(payments.router, tags=["Payments"])
app.include_router(whatsapp.router, tags=["WhatsApp"])
app.include_router(attendance.router, tags=["Attendance"])
app.include_router(exercises.router, tags=["Exercises"])
app.include_router(profesores.router, tags=["Profesores"])
app.include_router(inscripciones.router, tags=["Inscripciones"])
app.include_router(reports.router, tags=["Reports"])
app.include_router(admin.router, tags=["Admin"])


