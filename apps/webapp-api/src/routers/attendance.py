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


# Alias endpoint for frontend compatibility (frontend calls /api/checkin instead of /api/checkin/validate)
@router.post("/api/checkin")
async def api_checkin(
    request: Request,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Check-in by token - alias for /api/checkin/validate."""
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    try:
        data = await request.json()
        token = str(data.get("token", "")).strip()
        
        if not token:
            return JSONResponse({"ok": False, "mensaje": "Token requerido"}, status_code=400)
        
        # Validate token and register attendance
        ok, msg = svc.validar_token_y_registrar_sin_sesion(token)
        
        return JSONResponse({
            "ok": ok,
            "usuario_nombre": msg if ok else None,
            "mensaje": msg if not ok else "Asistencia registrada"
        }, status_code=200 if ok else 400)
    except Exception as e:
        logger.exception(f"Error en /api/checkin rid={rid}")
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)


@router.post("/api/checkin/dni")
async def api_checkin_by_dni(
    request: Request,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Check-in by DNI with optional PIN verification.
    
    PIN requirement is controlled by CHECKIN_REQUIRE_PIN env var:
    - "true" or "1": PIN is required (more secure)
    - "false" or "0" (default): PIN is optional (faster access)
    """
    import os
    rid = getattr(getattr(request, 'state', object()), 'request_id', '-')
    
    # Configuration switch for PIN requirement
    require_pin = os.getenv("CHECKIN_REQUIRE_PIN", "false").lower() in ("true", "1", "yes")
    
    try:
        data = await request.json()
        dni = str(data.get("dni", "")).strip()
        pin = str(data.get("pin", "")).strip() if require_pin else None
        
        if not dni:
            return JSONResponse({"ok": False, "mensaje": "DNI requerido"}, status_code=400)
        
        if require_pin and not pin:
            return JSONResponse({"ok": False, "mensaje": "PIN requerido", "require_pin": True}, status_code=400)
        
        # Check-in with or without PIN verification
        if require_pin:
            ok, msg = svc.registrar_asistencia_por_dni_y_pin(dni, pin)
        else:
            ok, msg = svc.registrar_asistencia_por_dni(dni)
        
        return JSONResponse({
            "ok": ok,
            "usuario_nombre": msg if ok else None,
            "mensaje": msg if not ok else "Asistencia registrada"
        }, status_code=200 if ok else 400)
    except Exception as e:
        logger.exception(f"Error en /api/checkin/dni rid={rid}")
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)


# Endpoint to check if PIN is required (for frontend to know)
@router.get("/api/checkin/config")
async def api_checkin_config():
    """Returns check-in configuration for the frontend."""
    import os
    require_pin = os.getenv("CHECKIN_REQUIRE_PIN", "false").lower() in ("true", "1", "yes")
    return {"require_pin": require_pin}


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


@router.get("/api/asistencias")
async def api_asistencias_list(
    request: Request,
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """List attendance records with optional filters. Returns {asistencias: [], total}."""
    try:
        usuario_id = request.query_params.get("usuario_id")
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        limit_q = request.query_params.get("limit")
        
        limit = int(limit_q) if (limit_q and str(limit_q).isdigit()) else 50
        
        # Get attendance records
        records = svc.obtener_asistencias_detalle(start=desde, end=hasta)
        
        # Filter by usuario_id if provided
        if usuario_id and str(usuario_id).isdigit():
            uid = int(usuario_id)
            records = [r for r in records if r.get("usuario_id") == uid]
        
        total = len(records)
        sliced = records[:limit] if limit else records
        return {"asistencias": sliced, "total": total}
    except Exception as e:
        logger.error(f"Error listing asistencias: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/usuario_asistencias")
async def api_usuario_asistencias(
    request: Request,
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Get attendance records for a specific user. Returns {asistencias: []}."""
    try:
        usuario_id = request.query_params.get("usuario_id")
        limit_q = request.query_params.get("limit")
        
        if not usuario_id or not str(usuario_id).isdigit():
            raise HTTPException(status_code=400, detail="usuario_id requerido")
        
        limit = int(limit_q) if (limit_q and str(limit_q).isdigit()) else 50
        
        # Get all attendance and filter by user
        records = svc.obtener_asistencias_detalle(start=None, end=None)
        user_records = [r for r in records if r.get("usuario_id") == int(usuario_id)]
        
        sliced = user_records[:limit] if limit else user_records
        return {"asistencias": sliced}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usuario asistencias: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


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


# ========== Station QR Check-in (Public Endpoints) ==========

@router.get("/api/checkin/station/info/{station_key}")
async def api_station_info(
    station_key: str,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Get station info (public - no auth required).
    Used by the station display page to validate key and get gym info.
    """
    try:
        gym_id = svc.validar_station_key(station_key)
        if not gym_id:
            return JSONResponse({"valid": False, "error": "Station key inválida"}, status_code=404)
        
        # Get gym name from admin DB gyms table
        import os
        from src.database.raw_manager import RawPostgresManager
        admin_params = {
            "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
            "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
            "database": os.getenv("ADMIN_DB_NAME", "ironhub_admin"),
            "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
            "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
        }
        
        db = RawPostgresManager(connection_params=admin_params)
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT nombre, logo_url FROM gyms WHERE id = %s LIMIT 1", (gym_id,))
            row = cur.fetchone()
            gym_name = row[0] if row else "Gimnasio"
            logo_url = row[1] if row and len(row) > 1 else None
        
        return {
            "valid": True,
            "gym_id": gym_id,
            "gym_name": gym_name,
            "logo_url": logo_url
        }
    except Exception as e:
        logger.error(f"Error getting station info: {e}")
        return JSONResponse({"valid": False, "error": str(e)}, status_code=500)


@router.get("/api/checkin/station/token/{station_key}")
async def api_station_token(
    station_key: str,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Get current active station token (public - no auth required).
    Used by station display to show QR code.
    """
    try:
        gym_id = svc.validar_station_key(station_key)
        if not gym_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)
        
        token_data = svc.obtener_station_token_activo(gym_id)
        return token_data
    except Exception as e:
        logger.error(f"Error getting station token: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/checkin/station/regenerate/{station_key}")
async def api_station_regenerate(
    station_key: str,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Force regenerate station token (public - used after each check-in)."""
    try:
        gym_id = svc.validar_station_key(station_key)
        if not gym_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)
        
        token_data = svc.crear_station_token(gym_id)
        return token_data
    except Exception as e:
        logger.error(f"Error regenerating station token: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/checkin/station/recent/{station_key}")
async def api_station_recent(
    station_key: str,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Get recent check-ins for station display (public - no auth required).
    """
    try:
        gym_id = svc.validar_station_key(station_key)
        if not gym_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)
        
        recent = svc.obtener_station_checkins_recientes(gym_id, limit=5)
        stats = svc.obtener_station_stats(gym_id)
        
        return {
            "checkins": recent,
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Error getting recent check-ins: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/checkin/station/scan")
async def api_station_scan(
    request: Request,
    svc: AttendanceService = Depends(get_attendance_service)
):
    """
    User scans station QR to register attendance.
    Requires user to be authenticated (session with checkin_user_id or user_id).
    """
    try:
        data = await request.json()
        token = str(data.get("token", "")).strip()
        
        if not token:
            return JSONResponse({"ok": False, "mensaje": "Token requerido"}, status_code=400)
        
        # Get user ID from session
        usuario_id = request.session.get("checkin_user_id") or request.session.get("user_id")
        if not usuario_id:
            return JSONResponse({"ok": False, "mensaje": "Debes iniciar sesión primero"}, status_code=401)
        
        # Validate and register
        ok, msg, user_data = svc.validar_station_scan(token, int(usuario_id))
        
        return JSONResponse({
            "ok": ok,
            "mensaje": msg,
            "usuario": user_data
        }, status_code=200 if ok else 400)
    except Exception as e:
        logger.error(f"Error in station scan: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)


# Admin endpoint to generate/get station key
@router.get("/api/gestion/station-key")
async def api_get_station_key(
    request: Request,
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Get or generate station key for the current gym (requires owner auth)."""
    try:
        # Try to get gym_id from session first
        gym_id = request.session.get("gym_id")
        
        # If not in session, look up from admin DB using tenant subdomain
        if not gym_id:
            from src.database.tenant_connection import get_current_tenant_gym_id
            gym_id = get_current_tenant_gym_id()
        
        if not gym_id:
            return JSONResponse({"error": "Gym ID no encontrado - asegúrate de que el gym está registrado"}, status_code=400)
        
        station_key = svc.generar_station_key(int(gym_id))
        
        # Build the station URL using the current tenant subdomain
        # For cross-origin calls, use the Origin header to determine the frontend URL
        origin = request.headers.get("origin", "")
        if origin:
            station_url = f"{origin}/station/{station_key}"
        else:
            host = request.headers.get("host", "")
            protocol = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
            station_url = f"{protocol}://{host}/station/{station_key}"
        
        return {
            "station_key": station_key,
            "station_url": station_url
        }
    except Exception as e:
        logger.error(f"Error getting station key: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/gestion/station-key/regenerate") 
async def api_regenerate_station_key(
    request: Request,
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service)
):
    """Regenerate station key (invalidates old URL)."""
    try:
        # Try to get gym_id from session first
        gym_id = request.session.get("gym_id")
        
        # If not in session, look up from admin DB using tenant subdomain
        if not gym_id:
            from src.database.tenant_connection import get_current_tenant_gym_id
            gym_id = get_current_tenant_gym_id()
        
        if not gym_id:
            return JSONResponse({"error": "Gym ID no encontrado - asegúrate de que el gym está registrado"}, status_code=400)
        
        import secrets as sec
        import os
        new_key = sec.token_urlsafe(16)
        
        # Update station key in admin DB gyms table
        from src.database.raw_manager import RawPostgresManager
        admin_params = {
            "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
            "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
            "database": os.getenv("ADMIN_DB_NAME", "ironhub_admin"),
            "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
            "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
        }
        
        db = RawPostgresManager(connection_params=admin_params)
        with db.get_connection_context() as conn:
            cur = conn.cursor()
            cur.execute("UPDATE gyms SET station_key = %s WHERE id = %s", (new_key, gym_id))
            conn.commit()
        
        # Build the station URL
        origin = request.headers.get("origin", "")
        if origin:
            station_url = f"{origin}/station/{new_key}"
        else:
            host = request.headers.get("host", "")
            protocol = "https" if request.headers.get("x-forwarded-proto") == "https" else "http"
            station_url = f"{protocol}://{host}/station/{new_key}"
        
        return {
            "station_key": new_key,
            "station_url": station_url
        }
    except Exception as e:
        logger.error(f"Error regenerating station key: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

