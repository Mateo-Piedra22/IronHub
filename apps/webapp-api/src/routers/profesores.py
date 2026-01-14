"""Profesores Router - Complete profesor management API using ProfesorService."""
import logging
import os
from datetime import datetime, date, timezone, timedelta

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import require_gestion_access, require_owner, get_profesor_service
from src.services.profesor_service import ProfesorService

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_app_timezone():
    tz_name = (
        os.getenv("APP_TIMEZONE")
        or os.getenv("TIMEZONE")
        or os.getenv("TZ")
        or "America/Argentina/Buenos_Aires"
    )
    if ZoneInfo is not None:
        try:
            return ZoneInfo(tz_name)
        except Exception:
            pass
    return timezone(timedelta(hours=-3))


def _today_local_date() -> date:
    tz = _get_app_timezone()
    return datetime.now(timezone.utc).astimezone(tz).date()


def _assert_profesor_access(request: Request, profesor_id: int) -> None:
    role = str(request.session.get("role") or "").lower()
    if role == "profesor":
        sid = request.session.get("gestion_profesor_id")
        if sid is None or int(sid) != int(profesor_id):
            raise HTTPException(status_code=403, detail="Forbidden")


# === Profesores CRUD ===

@router.get("/api/profesores")
async def api_profesores_list(request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """List all profesores."""
    try:
        role = str(request.session.get("role") or "").lower()
        if role == "profesor":
            pid = request.session.get("gestion_profesor_id")
            if pid is None:
                return {"profesores": []}
            prof = svc.obtener_profesor(int(pid))
            return {"profesores": [prof] if prof else []}
    except Exception:
        pass
    return {"profesores": svc.obtener_profesores()}


@router.post("/api/profesores")
async def api_profesores_create(request: Request, _=Depends(require_owner), svc: ProfesorService = Depends(get_profesor_service)):
    """Create a new profesor."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        result = svc.crear_profesor(nombre, (payload.get("email") or "").strip() or None, (payload.get("telefono") or "").strip() or None)
        return result if result else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error creating profesor")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/profesores/{profesor_id}")
async def api_profesor_get(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Get single profesor."""
    _assert_profesor_access(request, profesor_id)
    result = svc.obtener_profesor(profesor_id)
    if not result:
        raise HTTPException(status_code=404, detail="Profesor no encontrado")
    return result


@router.put("/api/profesores/{profesor_id}")
async def api_profesor_update(profesor_id: int, request: Request, _=Depends(require_owner), svc: ProfesorService = Depends(get_profesor_service)):
    """Update profesor details."""
    try:
        payload = await request.json()
        result = svc.actualizar_profesor(profesor_id, payload)
        return result if result else {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/profesores/{profesor_id}")
async def api_profesor_delete(profesor_id: int, _=Depends(require_owner), svc: ProfesorService = Depends(get_profesor_service)):
    """Delete a profesor."""
    try:
        svc.eliminar_profesor(profesor_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Sesiones ===

@router.get("/api/profesores/{profesor_id}/sesiones")
async def api_profesor_sesiones(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Get professor sessions."""
    _assert_profesor_access(request, profesor_id)
    return {"sesiones": svc.obtener_sesiones(profesor_id, request.query_params.get("desde"), request.query_params.get("hasta"))}


@router.post("/api/profesores/{profesor_id}/sesiones/start")
async def api_profesor_sesion_start(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Start a new session."""
    _assert_profesor_access(request, profesor_id)
    result = svc.iniciar_sesion(profesor_id)
    if result.get('error'):
        raise HTTPException(status_code=400, detail=result['error'])
    return result


@router.post("/api/profesores/{profesor_id}/sesiones/{sesion_id}/end")
async def api_profesor_sesion_end(profesor_id: int, sesion_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """End an active session."""
    _assert_profesor_access(request, profesor_id)
    result = svc.finalizar_sesion(profesor_id, sesion_id)
    if result.get('error'):
        raise HTTPException(status_code=404, detail=result['error'])
    return result


@router.delete("/api/sesiones/{sesion_id}")
async def api_sesion_delete(sesion_id: int, _=Depends(require_owner), svc: ProfesorService = Depends(get_profesor_service)):
    """Delete a session."""
    try:
        svc.eliminar_sesion(sesion_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Horarios ===

@router.get("/api/profesores/{profesor_id}/horarios")
async def api_profesor_horarios_list(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """List profesor availability schedules."""
    _assert_profesor_access(request, profesor_id)
    return {"horarios": svc.obtener_horarios(profesor_id)}


@router.post("/api/profesores/{profesor_id}/horarios")
async def api_profesor_horario_create(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Create availability schedule."""
    try:
        _assert_profesor_access(request, profesor_id)
        payload = await request.json()
        dia = (payload.get("dia") or "").strip().lower()
        hora_inicio = payload.get("hora_inicio")
        hora_fin = payload.get("hora_fin")
        if not dia or not hora_inicio or not hora_fin:
            raise HTTPException(status_code=400, detail="dia, hora_inicio y hora_fin son requeridos")
        result = svc.crear_horario(profesor_id, dia, hora_inicio, hora_fin, payload.get("disponible", True))
        return result if result else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/profesores/{profesor_id}/horarios/{horario_id}")
async def api_profesor_horario_update(profesor_id: int, horario_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Update availability schedule."""
    try:
        _assert_profesor_access(request, profesor_id)
        payload = await request.json()
        result = svc.actualizar_horario(profesor_id, horario_id, payload)
        return result if result else {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/profesores/{profesor_id}/horarios/{horario_id}")
async def api_profesor_horario_delete(profesor_id: int, horario_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Delete availability schedule."""
    try:
        _assert_profesor_access(request, profesor_id)
        svc.eliminar_horario(profesor_id, horario_id)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Config ===

@router.get("/api/profesores/{profesor_id}/config")
async def api_profesor_config_get(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Get profesor configuration."""
    try:
        _assert_profesor_access(request, profesor_id)
        return svc.obtener_config(profesor_id)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/profesores/{profesor_id}/config")
async def api_profesor_config_update(profesor_id: int, request: Request, _=Depends(require_owner), svc: ProfesorService = Depends(get_profesor_service)):
    """Update profesor configuration."""
    try:
        payload = await request.json()
        result = svc.actualizar_config(profesor_id, payload)
        if result.get('monto'):
            result['monto'] = float(result['monto'])
        return result
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# === Resumen ===

@router.get("/api/profesores/{profesor_id}/resumen/mensual")
async def api_profesor_resumen_mensual(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Get monthly summary of hours worked."""
    _assert_profesor_access(request, profesor_id)
    today = _today_local_date()
    mes = int(request.query_params.get("mes") or today.month)
    anio = int(request.query_params.get("anio") or today.year)
    return svc.resumen_mensual(profesor_id, mes, anio)


@router.get("/api/profesores/{profesor_id}/resumen/semanal")
async def api_profesor_resumen_semanal(profesor_id: int, request: Request, _=Depends(require_gestion_access), svc: ProfesorService = Depends(get_profesor_service)):
    """Get weekly summary of hours worked."""
    _assert_profesor_access(request, profesor_id)
    fecha = request.query_params.get("fecha")
    ref = datetime.strptime(fecha, "%Y-%m-%d").date() if fecha else _today_local_date()
    return svc.resumen_semanal(profesor_id, ref)
