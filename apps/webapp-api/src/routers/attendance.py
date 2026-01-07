import logging
import secrets
from datetime import datetime, date, timedelta
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from src.dependencies import require_gestion_access, require_owner, get_attendance_service
from src.services.attendance_service import AttendanceService

router = APIRouter()
logger = logging.getLogger(__name__)

# --- API Check-in y Asistencias ---

@router.post("/api/checkin/validate")
async def api_checkin_validate(
    request: Request,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Valida el token escaneado y registra asistencia si corresponde."""
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    try:
        data = await request.json()
        token = str(data.get("token", "")).strip()
        socio_id = request.session.get("checkin_user_id")
        
        logger.info(f"/api/checkin/validate: token=***{token[-4:] if token else ''} socio_id={socio_id} rid={rid}")
        
        if not socio_id:
            return JSONResponse({"success": False, "message": "Sesión de socio no encontrada"}, status_code=401)
        
        # Verify user is active
        is_active, reason = svc.verificar_usuario_activo(int(socio_id))
        if not is_active:
            return JSONResponse({"success": False, "message": reason}, status_code=403)
        
        # Validate token and register attendance
        ok, msg = svc.validar_token_y_registrar(token, int(socio_id))
        
        logger.info(f"/api/checkin/validate: resultado ok={ok} msg='{msg}' rid={rid}")
        return JSONResponse({"success": ok, "message": msg}, status_code=200 if ok else 400)
    except Exception as e:
        logger.exception(f"Error en /api/checkin/validate rid={rid}")
        return JSONResponse({"success": False, "message": str(e)}, status_code=500)


@router.get("/api/checkin/token_status")
async def api_checkin_token_status(
    request: Request,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Consulta el estado de un token: { exists, used, expired }."""
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    token = str(request.query_params.get("token", "")).strip()
    
    logger.info(f"/api/checkin/token_status: token=***{token[-4:] if token else ''} rid={rid}")
    
    if not token:
        return JSONResponse({"exists": False, "used": False, "expired": True}, status_code=200)
    
    try:
        status_info = svc.obtener_estado_token(token)
        logger.info(f"/api/checkin/token_status: result={status_info} rid={rid}")
        return JSONResponse({
            "exists": status_info.get('exists', False),
            "used": status_info.get('used', False),
            "expired": status_info.get('expired', True)
        }, status_code=200)
    except Exception as e:
        logger.exception(f"Error en /api/checkin/token_status rid={rid}")
        return JSONResponse({"exists": False, "used": False, "expired": True, "error": str(e)}, status_code=200)


@router.post("/api/checkin/create_token")
async def api_checkin_create_token(
    request: Request, 
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Create a check-in token for a user."""
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    payload = await request.json()
    usuario_id = int(payload.get("usuario_id") or 0)
    expires_minutes = int(payload.get("expires_minutes") or 5)
    
    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")
    
    try:
        token = svc.crear_checkin_token(usuario_id, expires_minutes)
        logger.info(f"/api/checkin/create_token: usuario_id={usuario_id} token=***{token[-4:]} expires={expires_minutes}m rid={rid}")
        return JSONResponse({"success": True, "token": token, "expires_minutes": expires_minutes}, status_code=200)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/api/asistencias/registrar")
async def api_asistencias_registrar(
    request: Request, 
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Register attendance for a user."""
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    payload = await request.json()
    usuario_id = int(payload.get("usuario_id") or 0)
    fecha_str = str(payload.get("fecha") or "").strip()
    
    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")
    
    fecha = None
    if fecha_str:
        try:
            parts = fecha_str.split("-")
            if len(parts) == 3:
                fecha = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            pass
    
    try:
        asistencia_id = svc.registrar_asistencia(usuario_id, fecha)
        logger.info(f"/api/asistencias/registrar: usuario_id={usuario_id} fecha={fecha} rid={rid}")
        return JSONResponse({"success": True, "asistencia_id": asistencia_id}, status_code=200)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.info(f"/api/asistencias/registrar: ya existía asistencia usuario_id={usuario_id} rid={rid}")
        return JSONResponse({"success": True, "message": str(e)}, status_code=200)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/asistencias/eliminar")
async def api_asistencias_eliminar(
    request: Request, 
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Delete attendance for a user."""
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    payload = await request.json()
    usuario_id = int(payload.get("usuario_id") or 0)
    fecha_str = str(payload.get("fecha") or "").strip()
    
    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")
    
    fecha: Optional[date] = None
    if fecha_str:
        try:
            parts = fecha_str.split("-")
            if len(parts) == 3:
                fecha = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            fecha = date.today()
    else:
        fecha = date.today()
    
    try:
        svc.eliminar_asistencia(usuario_id, fecha)
        logger.info(f"/api/asistencias/eliminar: usuario_id={usuario_id} fecha={fecha} rid={rid}")
        return JSONResponse({"success": True}, status_code=200)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/asistencia_30d")
async def api_asistencia_30d(
    request: Request, 
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Get daily attendance for the past 30 days."""
    try:
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        
        if start and end:
            data = svc.obtener_asistencias_por_rango(start, end)
        else:
            data = svc.obtener_asistencias_por_dia(30)
        
        series: Dict[str, int] = {}
        for d, c in data:
            series[str(d)] = int(c)
        
        # Fill in missing dates
        hoy = date.today()
        base: Dict[str, int] = {}
        for i in range(29, -1, -1):
            dia = hoy - timedelta(days=i)
            clave = dia.strftime("%Y-%m-%d")
            base[clave] = 0
        base.update(series)
        return dict(sorted(base.items()))
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/asistencia_por_hora_30d")
async def api_asistencia_por_hora_30d(
    request: Request, 
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Get hourly attendance distribution."""
    try:
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        data = svc.obtener_asistencias_por_hora(30, start, end)
        
        series: Dict[str, int] = {}
        for h, c in data:
            series[str(h)] = int(c)
        return series
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/asistencias_hoy_ids")
async def api_asistencias_hoy_ids(
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Get list of user IDs who attended today."""
    try:
        return svc.obtener_asistencias_hoy_ids()
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/asistencias_detalle")
async def api_asistencias_detalle(
    request: Request, 
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Listado de asistencias con nombre del usuario para un rango de fechas."""
    try:
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        q = request.query_params.get("q")
        limit = request.query_params.get("limit")
        offset = request.query_params.get("offset")
        
        lim = int(limit) if limit and limit.isdigit() else 500
        off = int(offset) if offset and offset.isdigit() else 0
        
        return svc.obtener_asistencias_detalle(start, end, q, lim, off)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
