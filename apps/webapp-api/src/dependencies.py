"""
Webapp API Dependencies
Self-contained FastAPI dependency injection for webapp-api
"""

import logging
import os
from typing import Optional, Generator

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


_schema_guard_lock = None
_schema_guard_done = set()
try:
    import threading
    _schema_guard_lock = threading.RLock()
except Exception:
    _schema_guard_lock = None


def _ensure_ejercicios_columns(session: Session, tenant: Optional[str]) -> None:
    try:
        auto_guard = str(os.getenv("AUTO_SCHEMA_GUARD", "")).strip().lower() in ("1", "true", "yes", "on")
        dev_mode = str(os.getenv("DEVELOPMENT_MODE", "")).strip().lower() in ("1", "true", "yes", "on")
        if not auto_guard and not dev_mode:
            return
    except Exception:
        return
    try:
        key = str(tenant or "__default__")
        if _schema_guard_lock is not None:
            with _schema_guard_lock:
                if key in _schema_guard_done:
                    return
        else:
            if key in _schema_guard_done:
                return
        session.execute(
            text("""
                ALTER TABLE ejercicios
                    ADD COLUMN IF NOT EXISTS objetivo VARCHAR(100) DEFAULT 'general',
                    ADD COLUMN IF NOT EXISTS equipamiento VARCHAR(100),
                    ADD COLUMN IF NOT EXISTS variantes TEXT;
            """)
        )

        try:
            session.commit()
        except Exception:
            session.rollback()
    except Exception:
        try:
            session.rollback()
        except Exception:
            pass
    finally:
        try:
            if _schema_guard_lock is not None:
                with _schema_guard_lock:
                    _schema_guard_done.add(str(tenant or "__default__"))
            else:
                _schema_guard_done.add(str(tenant or "__default__"))
        except Exception:
            pass

# Import tenant context functions from tenant_connection to avoid circular imports
# tenant_connection has the canonical CURRENT_TENANT contextvar
from src.database.tenant_connection import (
    get_tenant_session_factory,
    set_current_tenant,
    get_current_tenant,
    CURRENT_TENANT,
    validate_tenant_name
)

# Import local services
from src.database.connection import SessionLocal, AdminSessionLocal
from src.services.user_service import UserService

from src.services.payment_service import PaymentService
from src.services.auth_service import AuthService
from src.services.gym_config_service import GymConfigService
from src.services.clase_service import ClaseService
from src.services.training_service import TrainingService
from src.services.attendance_service import AttendanceService
from src.services.inscripciones_service import InscripcionesService
from src.services.profesor_service import ProfesorService
from src.services.whatsapp_service import WhatsAppService
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService
from src.services.whatsapp_settings_service import WhatsAppSettingsService
from src.services.reports_service import ReportsService
from src.services.admin_service import AdminService

async def ensure_tenant_context(request: Request) -> Optional[str]:
    """
    Dependency to extract and set tenant context from request.
    Useful for routers that don't go through main app middleware (if any).
    """
    host = request.headers.get("host", "")
    tenant = request.headers.get("x-tenant")
    
    # Try to extract from subdomain if not in header
    if not tenant and host:
        base_domain = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz")
        # Remove port
        host_clean = host.split(":")[0]
        if host_clean.endswith(f".{base_domain}"):
             candidate = host_clean.replace(f".{base_domain}", "")
             # Avoid 'www', 'api', 'admin' if they are reserved (optional, but good practice)
             if candidate not in ("www", "api", "admin", "admin-api"):
                 tenant = candidate

    if tenant:
        try:
            t = str(tenant).strip().lower()
        except Exception:
            t = ""

        try:
            ok, _err = validate_tenant_name(t)
        except Exception:
            ok = False

        if ok:
            set_current_tenant(t)
            return t
    return None


def _try_set_tenant_from_request(request: Request) -> Optional[str]:

    session_tenant: Optional[str] = None
    try:
        session_tenant = str(request.session.get("tenant") or "").strip().lower() or None
    except Exception:
        session_tenant = None

    query_tenant: Optional[str] = None
    try:
        query_tenant = str(request.query_params.get("tenant") or "").strip().lower() or None
    except Exception:
        query_tenant = None

    header_tenant: Optional[str] = None
    try:
        header_tenant = str(request.headers.get("x-tenant") or "").strip().lower() or None
    except Exception:
        header_tenant = None

    tenant: Optional[str] = None
    if session_tenant:
        if query_tenant and query_tenant != session_tenant and request.url.path.startswith("/api/"):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        if header_tenant and header_tenant != session_tenant and request.url.path.startswith("/api/"):
            raise HTTPException(status_code=403, detail="Tenant mismatch")
        tenant = session_tenant
    else:
        tenant = query_tenant or header_tenant

    if not tenant:
        try:
            host = str(request.headers.get("host") or "").strip()
        except Exception:
            host = ""

        if host:
            base_domain = os.getenv("TENANT_BASE_DOMAIN", "ironhub.motiona.xyz").strip().lower()
            host_clean = host.split(":")[0].strip().lower()
            if base_domain and host_clean.endswith(f".{base_domain}"):
                candidate = host_clean.replace(f".{base_domain}", "").strip()
                if candidate and candidate not in ("www", "api", "admin", "admin-api"):
                    tenant = candidate

    if not tenant:
        return None

    try:
        ok, _err = validate_tenant_name(str(tenant))
    except Exception:
        ok = False

    if not ok:
        return None

    try:
        set_current_tenant(str(tenant).strip().lower())
    except Exception:
        return None
    return str(tenant).strip().lower()


def get_db_session(request: Request) -> Generator[Session, None, None]:
    """
    Get a database session for the current tenant.
    Uses CURRENT_TENANT context variable to determine which database to connect to.
    
    IMPORTANT: If tenant is set but cannot connect, raises an error instead of
    silently falling back to the wrong database.
    """
    if not get_current_tenant():
        _try_set_tenant_from_request(request)

    tenant = get_current_tenant()
    
    if tenant:
        # Use tenant-specific session
        try:
            factory = get_tenant_session_factory(tenant)
            if factory:
                session = factory()
                try:
                    _ensure_ejercicios_columns(session, tenant)
                    yield session
                finally:
                    session.close()
                return
            else:
                # Factory returned None - tenant lookup failed
                logger.error(f"Tenant session factory returned None for '{tenant}'")
                raise HTTPException(
                    status_code=503,
                    detail=f"Database connection unavailable for tenant '{tenant}'"
                )
        except HTTPException:
            raise  # Re-raise HTTP exceptions
        except Exception as e:
            logger.error(f"Failed to get tenant session for '{tenant}': {e}")
            # Check if this looks like a production environment without proper config
            db_host = os.getenv("DB_HOST", "localhost")
            if db_host == "localhost" and not os.getenv("DEVELOPMENT_MODE"):
                logger.critical(
                    f"PRODUCTION CONFIG ERROR: DB_HOST is 'localhost' but DEVELOPMENT_MODE not set. "
                    f"Ensure DB_HOST, DB_USER, DB_PASSWORD are configured for production."
                )
            raise HTTPException(
                status_code=503,
                detail=f"Database connection error: {str(e)}"
            )
    
    # No tenant context - use global database 
    # Also validate that we're not accidentally using localhost in production
    db_host = os.getenv("DB_HOST", "localhost")
    if db_host == "localhost" and not os.getenv("DEVELOPMENT_MODE"):
        logger.warning(
            f"No tenant context and DB_HOST is 'localhost'. "
            f"This may indicate missing environment configuration."
        )
    
    session = SessionLocal()
    try:
        _ensure_ejercicios_columns(session, None)
        yield session
    finally:
        session.close()


def get_user_service(session: Session = Depends(get_db_session)) -> UserService:
    """Get UserService instance with current session."""
    return UserService(session)





# Aliases for backwards compatibility with routers
get_db = get_db_session


def get_rm():
    """Get RoutineTemplateManager instance for PDF/Excel generation."""
    try:
        from src.routine_manager import RoutineTemplateManager
        return RoutineTemplateManager()
    except Exception:
        return None


def get_payment_service(session: Session = Depends(get_db_session)) -> PaymentService:
    """Get PaymentService instance with current session."""
    return PaymentService(session)


def get_auth_service(session: Session = Depends(get_db_session)) -> AuthService:
    """Get AuthService instance with current session."""
    return AuthService(session)


def get_gym_config_service(session: Session = Depends(get_db_session)) -> GymConfigService:
    """Get GymConfigService instance with current session."""
    return GymConfigService(session)

def get_clase_service(session: Session = Depends(get_db_session)) -> ClaseService:
    """Get ClaseService instance with current session."""
    return ClaseService(session)

def get_training_service(session: Session = Depends(get_db_session)) -> TrainingService:
    """Get TrainingService instance with current session."""
    return TrainingService(session)


def get_attendance_service(session: Session = Depends(get_db_session)) -> AttendanceService:
    """Get AttendanceService instance with current session."""
    return AttendanceService(session)


def get_inscripciones_service(session: Session = Depends(get_db_session)) -> InscripcionesService:
    """Get InscripcionesService instance with current session."""
    return InscripcionesService(session)


def get_profesor_service(session: Session = Depends(get_db_session)) -> ProfesorService:
    """Get ProfesorService instance with current session."""
    return ProfesorService(session)


def get_whatsapp_service(session: Session = Depends(get_db_session)) -> WhatsAppService:
    """Get WhatsAppService instance with current session."""
    return WhatsAppService(session)

def get_whatsapp_dispatch_service(session: Session = Depends(get_db_session)) -> WhatsAppDispatchService:
    return WhatsAppDispatchService(session)

def get_whatsapp_settings_service(session: Session = Depends(get_db_session)) -> WhatsAppSettingsService:
    return WhatsAppSettingsService(session)


def get_reports_service(session: Session = Depends(get_db_session)) -> ReportsService:
    """Get ReportsService instance with current session."""
    return ReportsService(session)


def get_admin_service(session: Session = Depends(get_db_session)) -> AdminService:
    """Get AdminService instance with current session."""
    return AdminService(session)


# Alias for backwards compatibility with routers
def get_pm(session: Session = Depends(get_db_session)) -> PaymentService:
    """Get PaymentService - alias for payments router backward compatibility."""
    return PaymentService(session)


def get_admin_db() -> Generator[Session, None, None]:
    """
    Get admin database session (always uses global/admin database).
    Used by public router for tenant-independent operations.
    """
    session = AdminSessionLocal()
    try:
        yield session
    finally:
        session.close()


# --- Security Dependencies ---

async def require_gestion_access(request: Request):
    """Require gestion (management) panel access - owner or profesor."""
    try:
        if request.session.get("logged_in"):
            return True
    except Exception:
        pass

    # Fallback: allow based on role for sessions that were created by /api/auth/login
    try:
        role = str(request.session.get("role") or "").strip().lower()
    except Exception:
        role = ""

    if role in ("dueño", "dueno", "owner", "admin", "administrador"):
        return True

    if role == "profesor":
        # A profesor session may store either user_id (generic login) or gestion_profesor_user_id (gestion login)
        try:
            if request.session.get("gestion_profesor_user_id") or request.session.get("user_id"):
                return True
        except Exception:
            pass

    if request.url.path.startswith("/api/"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
    return RedirectResponse(url="/gestion/login", status_code=303)


async def require_owner(request: Request):
    """Require owner/admin access."""
    if not request.session.get("logged_in"):
        logger.warning(f"AUTH FAILED: Not logged in. Session keys: {list(request.session.keys())}")
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return RedirectResponse(url="/gestion/login", status_code=303)
    
    role = request.session.get("role", "").lower()
    if role not in ("dueño", "dueno", "owner", "admin", "administrador"):
        logger.warning(f"AUTH FAILED: Invalid role {role}")
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return RedirectResponse(url="/gestion", status_code=303)
    return True


async def require_admin(request: Request):
    """Alias for require_owner."""
    return await require_owner(request)


async def require_profesor(request: Request):
    """Require profesor or higher access."""
    try:
        role = str(request.session.get("role") or "").strip().lower()
    except Exception:
        role = ""

    # Either logged_in (gestion login) OR role-based session (generic login)
    try:
        logged_in = bool(request.session.get("logged_in"))
    except Exception:
        logged_in = False

    if not logged_in and role not in ("profesor", "dueño", "dueno", "owner", "admin", "administrador"):
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return RedirectResponse(url="/gestion/login", status_code=303)
    
    if role not in ("profesor", "dueño", "dueno", "owner", "admin", "administrador"):
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return RedirectResponse(url="/gestion", status_code=303)
    return True


async def require_user_auth(request: Request):
    """Require user (member) authentication from usuario panel."""
    user_id = request.session.get("user_id")
    if not user_id:
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return RedirectResponse(url="/usuario/login", status_code=303)
    return user_id

async def get_current_active_user(
    request: Request,
    user_service: UserService = Depends(get_user_service)
):
    """
    Get current active user from session or raise 401.
    Used by gym router for member-specific actions.
    """
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authenticated user required"
        )
    
    user = user_service.get_user_by_id(user_id)
    if not user:
        # Invalid session data
        request.session.clear()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
        
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
        
    return user
