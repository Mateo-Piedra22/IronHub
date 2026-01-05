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
from src.database.connection import SessionLocal
from src.database.tenant_connection import get_tenant_session_factory
from src.services.user_service import UserService
from src.services.teacher_service import TeacherService


def set_current_tenant(tenant: str):
    """Set the current tenant subdomain in context."""
    CURRENT_TENANT.set(tenant.strip().lower() if tenant else None)


def get_current_tenant() -> Optional[str]:
    """Get the current tenant subdomain from context."""
    try:
        return CURRENT_TENANT.get()
    except LookupError:
        return None


def get_db_session() -> Generator[Session, None, None]:
    """
    Get a database session for the current tenant.
    Uses CURRENT_TENANT context variable to determine which database to connect to.
    Falls back to global database if no tenant context is set.
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
        except Exception as e:
            logger.warning(f"Failed to get tenant session for '{tenant}': {e}")
    
    # Fallback to global database
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
