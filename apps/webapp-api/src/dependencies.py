"""
Webapp API Dependencies
Self-contained FastAPI dependency injection for webapp-api
"""

import logging
import contextvars
from typing import Optional, Generator

from fastapi import Request, HTTPException, status, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

# Global ContextVar for Tenant
CURRENT_TENANT = contextvars.ContextVar("current_tenant", default=None)

# Import local modules
from src.database.connection import SessionLocal, AdminSessionLocal
from src.database.tenant_connection import get_tenant_session_factory
from src.services.user_service import UserService
from src.services.teacher_service import TeacherService
from src.services.payment_service import PaymentService
from src.services.auth_service import AuthService
from src.services.gym_service import GymService
from src.services.attendance_service import AttendanceService
from src.services.inscripciones_service import InscripcionesService
from src.services.profesor_service import ProfesorService
from src.services.whatsapp_service import WhatsAppService
from src.services.reports_service import ReportsService
from src.services.admin_service import AdminService


import os

def set_current_tenant(tenant: str):
    """Set the current tenant subdomain in context."""
    CURRENT_TENANT.set(tenant.strip().lower() if tenant else None)


def get_current_tenant() -> Optional[str]:
    """Get the current tenant subdomain from context."""
    try:
        return CURRENT_TENANT.get()
    except LookupError:
        return None

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
        set_current_tenant(tenant)
        return tenant
    return None


def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session for the current tenant.
    Uses CURRENT_TENANT context variable to determine which database to connect to.
    
    IMPORTANT: If tenant is set but cannot connect, raises an error instead of
    silently falling back to the wrong database.
    """
    tenant = get_current_tenant()
    
    if tenant:
        # Use tenant-specific session
        try:
            factory = get_tenant_session_factory(tenant)
            if factory:
                session = factory()
                try:
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
        yield session
    finally:
        session.close()


def get_user_service(session: Session = Depends(get_db_session)) -> UserService:
    """Get UserService instance with current session."""
    return UserService(session)


def get_teacher_service(session: Session = Depends(get_db_session)) -> TeacherService:
    """Get TeacherService instance with current session."""
    return TeacherService(session)


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


def get_gym_service(session: Session = Depends(get_db_session)) -> GymService:
    """Get GymService instance with current session."""
    return GymService(session)


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
    if not request.session.get("logged_in"):
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return RedirectResponse(url="/gestion/login", status_code=303)
    return True


async def require_owner(request: Request):
    """Require owner/admin access."""
    if not request.session.get("logged_in"):
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return RedirectResponse(url="/gestion/login", status_code=303)
    
    role = request.session.get("role", "").lower()
    if role not in ("dueño", "dueno", "owner", "admin", "administrador"):
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return RedirectResponse(url="/gestion", status_code=303)
    return True


async def require_admin(request: Request):
    """Alias for require_owner."""
    return await require_owner(request)


async def require_profesor(request: Request):
    """Require profesor or higher access."""
    if not request.session.get("logged_in"):
        if request.url.path.startswith("/api/"):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
        return RedirectResponse(url="/gestion/login", status_code=303)
    
    role = request.session.get("role", "").lower()
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
