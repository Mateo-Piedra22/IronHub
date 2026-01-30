"""Admin Router - Owner management using AdminService."""

import logging
import os

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import require_owner, get_admin_service
from src.services.admin_service import AdminService

router = APIRouter()
logger = logging.getLogger(__name__)


# === Password Management ===


@router.post("/api/admin/cambiar_contrasena")
async def api_admin_cambiar_contrasena(
    request: Request,
    _=Depends(require_owner),
    svc: AdminService = Depends(get_admin_service),
):
    """Change owner password."""
    try:
        payload = await request.json()
        current = payload.get("current_password", "").strip()
        new = payload.get("new_password", "").strip()

        if not current or not new:
            raise HTTPException(400, "Contraseña actual y nueva requeridas")
        if len(new) < 6:
            raise HTTPException(400, "Mínimo 6 caracteres")

        result = svc.cambiar_contrasena_dueno(current, new)
        if not result.get("ok"):
            raise HTTPException(
                401 if "incorrect" in result.get("error", "") else 500,
                result.get("error"),
            )
        return {"ok": True, "message": "Contraseña actualizada"}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === User ID Renumbering ===


@router.post("/api/admin/renumerar_usuarios")
async def api_admin_renumerar_usuarios(
    request: Request,
    _=Depends(require_owner),
    svc: AdminService = Depends(get_admin_service),
):
    """Renumber user IDs starting from specified value."""
    try:
        payload = await request.json()
        start_id = int(payload.get("start_id", 1))
        if start_id < 1:
            raise HTTPException(400, "start_id debe ser >= 1")

        result = svc.renumerar_usuarios(start_id)
        return {
            "ok": result.get("ok", False),
            "message": result.get("message", ""),
            "changes": result.get("changes", 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Owner Security ===


@router.post("/api/admin/secure_owner")
async def api_admin_secure_owner(
    _=Depends(require_owner), svc: AdminService = Depends(get_admin_service)
):
    """Ensure owner exists and has bcrypt password."""
    result = svc.secure_owner()
    return result


# === System Reminders ===


@router.get("/api/admin/reminder")
async def api_admin_reminder(svc: AdminService = Depends(get_admin_service)):
    """Get system reminder."""
    env_msg = os.getenv("SYSTEM_REMINDER", "")
    if env_msg:
        return {"active": True, "message": env_msg}
    return svc.obtener_reminder()


@router.post("/api/admin/reminder")
async def api_admin_reminder_set(
    request: Request,
    _=Depends(require_owner),
    svc: AdminService = Depends(get_admin_service),
):
    """Set system reminder."""
    try:
        payload = await request.json()
        message = (payload.get("message") or "").strip()
        active = payload.get("active", bool(message))
        ok = svc.establecer_reminder(message, active)
        return {"ok": ok}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
