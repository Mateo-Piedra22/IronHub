import logging
import json
import secrets
import hashlib
from datetime import date, timedelta
from typing import Optional, Dict

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.checkin_ws_hub import checkin_ws_hub
from src.dependencies import (
    require_gestion_access,
    require_owner,
    get_attendance_service,
    require_feature,
    require_sucursal_selected,
    require_sucursal_selected_optional,
    require_scope_gestion,
)
from src.services.attendance_service import AttendanceService

router = APIRouter(
    dependencies=[
        Depends(require_feature("asistencias")),
        Depends(require_scope_gestion("asistencias:read")),
    ]
)
logger = logging.getLogger(__name__)

# --- API Check-in y Asistencias ---


@router.post("/api/checkin/validate")
async def api_checkin_validate(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Valida el token escaneado y registra asistencia si corresponde."""
    rid = getattr(getattr(request, "state", object()), "request_id", "-")
    try:
        data = await request.json()
        token = str(data.get("token", "")).strip()
        socio_id = request.session.get("checkin_user_id")

        logger.info(
            f"/api/checkin/validate: token=***{token[-4:] if token else ''} socio_id={socio_id} rid={rid}"
        )

        if not socio_id:
            return JSONResponse(
                {
                    "success": False,
                    "message": "Sesión de socio no encontrada",
                    "ok": False,
                    "mensaje": "Sesión de socio no encontrada",
                },
                status_code=401,
            )

        # Verify user is active
        is_active, reason = svc.verificar_usuario_activo(int(socio_id))
        if not is_active:
            return JSONResponse(
                {"success": False, "message": reason, "ok": False, "mensaje": reason},
                status_code=403,
            )

        # Validate token and register attendance
        ok, msg, asistencia_id, created = svc.validar_token_y_registrar(
            token, int(socio_id), int(sucursal_id), tipo="qr_gestion"
        )
        if ok and created and asistencia_id is not None:
            entry = svc.construir_checkin_entry_por_asistencia_id(int(asistencia_id))
            sid = entry.get("sucursal_id") if isinstance(entry, dict) else None
            if sid:
                await checkin_ws_hub.broadcast(int(sid), entry)

        logger.info(f"/api/checkin/validate: resultado ok={ok} msg='{msg}' rid={rid}")
        return JSONResponse(
            {"success": ok, "message": msg, "ok": ok, "mensaje": msg},
            status_code=200 if ok else 400,
        )
    except Exception as e:
        logger.exception(f"Error en /api/checkin/validate rid={rid}")
        return JSONResponse(
            {"success": False, "message": str(e), "ok": False, "mensaje": str(e)},
            status_code=500,
        )


# Alias endpoint for frontend compatibility (frontend calls /api/checkin instead of /api/checkin/validate)
@router.post("/api/checkin")
async def api_checkin(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Check-in by token - alias for /api/checkin/validate."""
    rid = getattr(getattr(request, "state", object()), "request_id", "-")
    try:
        data = await request.json()
        token = str(data.get("token", "")).strip()

        if not token:
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": "Token requerido",
                    "success": False,
                    "message": "Token requerido",
                },
                status_code=400,
            )

        socio_id = request.session.get("checkin_user_id") or request.session.get(
            "user_id"
        )
        if not socio_id:
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": "Debes iniciar sesión primero",
                    "success": False,
                    "message": "Debes iniciar sesión primero",
                },
                status_code=401,
            )

        is_active, reason = svc.verificar_usuario_activo(int(socio_id))
        if not is_active:
            return JSONResponse(
                {"ok": False, "mensaje": reason, "success": False, "message": reason},
                status_code=403,
            )

        ok, msg, asistencia_id, created = svc.validar_token_y_registrar(
            token, int(socio_id), int(sucursal_id), tipo="qr_gestion"
        )
        if ok:
            try:
                _enqueue_auto_unlock_for_sucursal(svc.db, int(sucursal_id), request_id=f"user_token:{token}", source="user_qr")
                svc.db.commit()
            except Exception:
                try:
                    svc.db.rollback()
                except Exception:
                    pass
        if ok and created and asistencia_id is not None:
            entry = svc.construir_checkin_entry_por_asistencia_id(int(asistencia_id))
            sid = entry.get("sucursal_id") if isinstance(entry, dict) else None
            if sid:
                await checkin_ws_hub.broadcast(int(sid), entry)

        sucursal_nombre = None
        try:
            row = svc.db.execute(
                text("SELECT nombre FROM sucursales WHERE id = :id LIMIT 1"),
                {"id": int(sucursal_id)},
            ).fetchone()
            if row and row[0]:
                sucursal_nombre = str(row[0])
        except Exception:
            sucursal_nombre = None

        return JSONResponse(
            {
                "ok": ok,
                "mensaje": msg,
                "success": ok,
                "message": msg,
                "sucursal_id": int(sucursal_id),
                "sucursal_nombre": sucursal_nombre,
            },
            status_code=200 if ok else 400,
        )
    except Exception as e:
        logger.exception(f"Error en /api/checkin rid={rid}")
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e)},
            status_code=500,
        )


@router.get("/api/checkin/verify")
async def api_checkin_verify(
    request: Request, svc: AttendanceService = Depends(get_attendance_service)
):
    token = str(request.query_params.get("token", "")).strip()
    if not token:
        return JSONResponse(
            {"verified": False, "success": False, "expired": True, "exists": False},
            status_code=400,
        )

    try:
        status_info = svc.obtener_estado_token(token)
        verified = bool(status_info.get("used"))
        return {
            "verified": verified,
            "success": verified,
            "expired": bool(status_info.get("expired")),
            "exists": bool(status_info.get("exists")),
        }
    except Exception as e:
        logger.exception("Error en /api/checkin/verify")
        return JSONResponse(
            {
                "verified": False,
                "success": False,
                "expired": True,
                "exists": False,
                "error": str(e),
            },
            status_code=200,
        )


@router.post("/api/checkin/dni")
async def api_checkin_by_dni(
    request: Request, svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Check-in by DNI with optional PIN verification.

    PIN requirement is controlled by CHECKIN_REQUIRE_PIN env var:
    - "true" or "1": PIN is required (more secure)
    - "false" or "0" (default): PIN is optional (faster access)
    """
    import os

    rid = getattr(getattr(request, "state", object()), "request_id", "-")

    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    ) or os.getenv("ENV", "").lower() in ("dev", "development")
    rp_raw = os.getenv("CHECKIN_REQUIRE_PIN")
    if rp_raw is None or str(rp_raw).strip() == "":
        require_pin = not dev_mode
    else:
        require_pin = str(rp_raw).lower() in ("true", "1", "yes")

    try:
        data = await request.json()
        dni = str(data.get("dni", "")).strip()
        pin = str(data.get("pin", "")).strip() if require_pin else None
        idempotency_key = str(
            request.headers.get("Idempotency-Key") or data.get("idempotency_key") or ""
        ).strip()

        if not dni:
            return JSONResponse(
                {"ok": False, "mensaje": "DNI requerido"}, status_code=400
            )

        if require_pin and not pin:
            return JSONResponse(
                {"ok": False, "mensaje": "PIN requerido", "require_pin": True},
                status_code=400,
            )

        if idempotency_key:
            rh = hashlib.sha256(
                f"dni:{dni}|require_pin:{bool(require_pin)}|pin:{pin or ''}".encode(
                    "utf-8"
                )
            ).hexdigest()
            cached = svc.idempotency_get_response(idempotency_key, request_hash=rh)
            if cached and not cached.get("pending"):
                return JSONResponse(
                    cached.get("body") or {},
                    status_code=int(cached.get("status_code") or 200),
                )
            if cached and cached.get("pending"):
                return JSONResponse(
                    {
                        "ok": False,
                        "mensaje": "Solicitud en progreso, reintentar",
                        "retry_after_ms": 250,
                    },
                    status_code=409,
                )
            svc.idempotency_reserve(
                idempotency_key,
                usuario_id=None,
                route="/api/checkin/dni",
                request_hash=rh,
                ttl_seconds=60,
            )

        # Check-in with or without PIN verification
        if require_pin:
            ok, msg, asistencia_id, created = svc.registrar_asistencia_por_dni_y_pin(
                dni, pin, request.session.get("sucursal_id"), tipo="dni_pin"
            )
        else:
            ok, msg, asistencia_id, created = svc.registrar_asistencia_por_dni(
                dni, request.session.get("sucursal_id"), tipo="dni_pin"
            )
        entry = (
            svc.construir_checkin_entry_por_asistencia_id(int(asistencia_id))
            if ok and asistencia_id is not None
            else None
        )
        if ok:
            sid = request.session.get("sucursal_id")
            try:
                sid = int(sid) if sid is not None else None
            except Exception:
                sid = None
            if sid is None and isinstance(entry, dict):
                sid = entry.get("sucursal_id")
            if sid:
                try:
                    _enqueue_auto_unlock_for_sucursal(svc.db, int(sid), request_id=f"dni:{dni}", source="dni_checkin")
                    svc.db.commit()
                except Exception:
                    try:
                        svc.db.rollback()
                    except Exception:
                        pass
        if ok and created and asistencia_id is not None and isinstance(entry, dict):
            sid = entry.get("sucursal_id")
            if sid:
                await checkin_ws_hub.broadcast(int(sid), entry)

        payload = {
            "ok": ok,
            "usuario_nombre": msg if ok else None,
            "mensaje": msg if not ok else "Asistencia registrada",
        }
        status_code = 200 if ok else 400
        if idempotency_key:
            svc.idempotency_store_response(
                idempotency_key, status_code=status_code, body=payload
            )
        return JSONResponse(payload, status_code=status_code)
    except Exception as e:
        logger.exception(f"Error en /api/checkin/dni rid={rid}")
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)


# Endpoint to check if PIN is required (for frontend to know)
@router.get("/api/checkin/config")
async def api_checkin_config():
    """Returns check-in configuration for the frontend."""
    import os

    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    ) or os.getenv("ENV", "").lower() in ("dev", "development")
    rp_raw = os.getenv("CHECKIN_REQUIRE_PIN")
    if rp_raw is None or str(rp_raw).strip() == "":
        require_pin = not dev_mode
    else:
        require_pin = str(rp_raw).lower() in ("true", "1", "yes")
    return {"require_pin": require_pin}


@router.get("/api/checkin/token_status")
async def api_checkin_token_status(
    request: Request, svc: AttendanceService = Depends(get_attendance_service)
):
    """Consulta el estado de un token: { exists, used, expired }."""
    rid = getattr(getattr(request, "state", object()), "request_id", "-")
    token = str(request.query_params.get("token", "")).strip()

    logger.info(
        f"/api/checkin/token_status: token=***{token[-4:] if token else ''} rid={rid}"
    )

    if not token:
        return JSONResponse(
            {"exists": False, "used": False, "expired": True}, status_code=200
        )

    try:
        status_info = svc.obtener_estado_token(token)
        logger.info(f"/api/checkin/token_status: result={status_info} rid={rid}")
        return JSONResponse(
            {
                "exists": status_info.get("exists", False),
                "used": status_info.get("used", False),
                "expired": status_info.get("expired", True),
            },
            status_code=200,
        )
    except Exception as e:
        logger.exception(f"Error en /api/checkin/token_status rid={rid}")
        return JSONResponse(
            {"exists": False, "used": False, "expired": True, "error": str(e)},
            status_code=200,
        )


@router.post("/api/checkin/create_token")
async def api_checkin_create_token(
    request: Request,
    _scope=Depends(require_scope_gestion("asistencias:write")),
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Create a check-in token for a user."""
    rid = getattr(getattr(request, "state", object()), "request_id", "-")
    payload = await request.json()
    usuario_id = int(payload.get("usuario_id") or 0)
    expires_minutes = int(payload.get("expires_minutes") or 5)

    if not usuario_id:
        raise HTTPException(status_code=400, detail="usuario_id es requerido")

    try:
        token = svc.crear_checkin_token(
            usuario_id, expires_minutes, request.session.get("sucursal_id")
        )
        logger.info(
            f"/api/checkin/create_token: usuario_id={usuario_id} token=***{token[-4:]} expires={expires_minutes}m rid={rid}"
        )
        return JSONResponse(
            {
                "ok": True,
                "mensaje": "OK",
                "success": True,
                "message": "OK",
                "token": token,
                "expires_minutes": expires_minutes,
            },
            status_code=200,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/asistencias")
async def api_asistencias_list(
    request: Request,
    sucursal_id: Optional[int] = Depends(require_sucursal_selected_optional),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """List attendance records with optional filters. Returns {asistencias: [], total}."""
    try:
        logged_in = bool(request.session.get("logged_in"))
        session_user_id = request.session.get("user_id")
        if (not logged_in) and (session_user_id is None):
            raise HTTPException(status_code=401, detail="Unauthorized")

        usuario_id = request.query_params.get("usuario_id")
        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        q = request.query_params.get("q")
        limit_q = request.query_params.get("limit")
        offset_q = request.query_params.get("offset")
        page_q = request.query_params.get("page")

        limit = int(limit_q) if (limit_q and str(limit_q).isdigit()) else 50
        limit = max(1, min(limit, 200))
        offset = 0
        if offset_q and str(offset_q).isdigit():
            offset = int(offset_q)
        elif page_q and str(page_q).isdigit():
            page_n = max(1, int(page_q))
            offset = (page_n - 1) * limit
        offset = max(0, offset)

        if (not logged_in) and (session_user_id is not None):
            usuario_id = str(int(session_user_id))

        uid_filter = (
            int(usuario_id) if (usuario_id and str(usuario_id).isdigit()) else None
        )
        if bool(logged_in) and sucursal_id is None:
            raise HTTPException(status_code=428, detail="Sucursal requerida")
        suc_filter = int(sucursal_id) if (bool(logged_in) and sucursal_id is not None) else None
        out = svc.obtener_asistencias_detalle_paginadas(
            usuario_id=uid_filter,
            start=desde,
            end=hasta,
            q=q,
            sucursal_id=suc_filter,
            limit=limit,
            offset=offset,
        )
        return JSONResponse(
            {
                "asistencias": list(out.get("items") or []),
                "total": int(out.get("total") or 0),
            },
            status_code=200,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, private",
                "Pragma": "no-cache",
                "Expires": "0",
                "Vary": "Cookie, X-Tenant, Origin",
            },
        )
    except Exception as e:
        logger.error(f"Error listing asistencias: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/usuario_asistencias")
async def api_usuario_asistencias(
    request: Request,
    sucursal_id: Optional[int] = Depends(require_sucursal_selected_optional),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Get attendance records for a specific user. Returns {asistencias: []}."""
    try:
        logged_in = bool(request.session.get("logged_in"))
        session_user_id = request.session.get("user_id")
        if (not logged_in) and (session_user_id is None):
            raise HTTPException(status_code=401, detail="Unauthorized")

        usuario_id = request.query_params.get("usuario_id")
        limit_q = request.query_params.get("limit")

        if (not logged_in) and (session_user_id is not None):
            usuario_id = str(int(session_user_id))
        if bool(logged_in) and sucursal_id is None:
            raise HTTPException(status_code=428, detail="Sucursal requerida")

        if not usuario_id or not str(usuario_id).isdigit():
            raise HTTPException(status_code=400, detail="usuario_id requerido")

        limit = int(limit_q) if (limit_q and str(limit_q).isdigit()) else 50
        limit = max(1, min(limit, 200))
        offset_q = request.query_params.get("offset")
        page_q = request.query_params.get("page")
        offset = 0
        if offset_q and str(offset_q).isdigit():
            offset = int(offset_q)
        elif page_q and str(page_q).isdigit():
            page_n = max(1, int(page_q))
            offset = (page_n - 1) * limit
        offset = max(0, offset)

        out = svc.obtener_asistencias_detalle_paginadas(
            usuario_id=int(usuario_id),
            start=None,
            end=None,
            q=None,
            sucursal_id=int(sucursal_id),
            limit=limit,
            offset=offset,
        )
        return {
            "asistencias": list(out.get("items") or []),
            "total": int(out.get("total") or 0),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting usuario asistencias: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/asistencias/registrar")
async def api_asistencias_registrar(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    _scope=Depends(require_scope_gestion("asistencias:write")),
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Register attendance for a user."""
    rid = getattr(getattr(request, "state", object()), "request_id", "-")
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
        asistencia_id, created = svc.registrar_asistencia_con_resultado(
            usuario_id, fecha, int(sucursal_id), tipo="manual_gestion"
        )
        logger.info(
            f"/api/asistencias/registrar: usuario_id={usuario_id} fecha={fecha} rid={rid}"
        )
        if created and asistencia_id is not None:
            entry = svc.construir_checkin_entry_por_asistencia_id(int(asistencia_id))
            sid = entry.get("sucursal_id") if isinstance(entry, dict) else None
            if sid:
                await checkin_ws_hub.broadcast(int(sid), entry)
        return JSONResponse(
            {
                "ok": True,
                "mensaje": "OK",
                "success": True,
                "message": "OK",
                "asistencia_id": asistencia_id,
            },
            status_code=200,
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        logger.info(
            f"/api/asistencias/registrar: ya existía asistencia usuario_id={usuario_id} rid={rid}"
        )
        return JSONResponse(
            {
                "ok": True,
                "mensaje": str(e),
                "success": True,
                "message": str(e),
            },
            status_code=200,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/api/asistencias/eliminar")
async def api_asistencias_eliminar(
    request: Request,
    _scope=Depends(require_scope_gestion("asistencias:write")),
    _=Depends(require_gestion_access),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Delete attendance for a user."""
    rid = getattr(getattr(request, "state", object()), "request_id", "-")
    payload = await request.json()
    asistencia_id = payload.get("asistencia_id")
    try:
        asistencia_id = (
            int(asistencia_id)
            if asistencia_id is not None and str(asistencia_id).strip() != ""
            else None
        )
    except Exception:
        asistencia_id = None

    usuario_id = int(payload.get("usuario_id") or 0)
    fecha_str = str(payload.get("fecha") or "").strip()

    if asistencia_id is None and (not usuario_id):
        raise HTTPException(
            status_code=400, detail="usuario_id o asistencia_id es requerido"
        )

    fecha: Optional[date] = None
    if fecha_str:
        try:
            parts = fecha_str.split("-")
            if len(parts) == 3:
                fecha = date(int(parts[0]), int(parts[1]), int(parts[2]))
        except Exception:
            fecha = None
    else:
        fecha = None

    try:
        ok = svc.eliminar_asistencia(
            usuario_id=usuario_id if usuario_id else None,
            fecha=fecha,
            asistencia_id=asistencia_id,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Asistencia no encontrada")
        logger.info(
            f"/api/asistencias/eliminar: usuario_id={usuario_id} asistencia_id={asistencia_id} fecha={fecha} rid={rid}"
        )
        return JSONResponse(
            {"ok": True, "mensaje": "OK", "success": True, "message": "OK"},
            status_code=200,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, private",
                "Pragma": "no-cache",
                "Expires": "0",
                "Vary": "Cookie, X-Tenant, Origin",
            },
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/asistencia_30d")
async def api_asistencia_30d(
    request: Request,
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service),
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
        hoy = svc._today_local_date()
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
    svc: AttendanceService = Depends(get_attendance_service),
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
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Get list of user IDs who attended today."""
    try:
        logged_in = bool(request.session.get("logged_in"))
        session_user_id = request.session.get("user_id")
        if logged_in:
            return svc.obtener_asistencias_hoy_ids(int(sucursal_id))
        if session_user_id is None:
            raise HTTPException(status_code=401, detail="Unauthorized")
        ids = svc.obtener_asistencias_hoy_ids(int(sucursal_id))
        try:
            return (
                [int(session_user_id)]
                if int(session_user_id) in set(int(x) for x in ids)
                else []
            )
        except Exception:
            return []
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/asistencias_detalle")
async def api_asistencias_detalle(
    request: Request,
    sucursal_id: int = Depends(require_sucursal_selected),
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service),
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

        return svc.obtener_asistencias_detalle(start, end, q, int(sucursal_id), lim, off)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== Station QR Check-in (Public Endpoints) ==========


@router.get("/api/checkin/station/info/{station_key}")
async def api_station_info(
    station_key: str, svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Get station info (public - no auth required).
    Used by the station display page to validate key and get gym info.
    """
    try:
        sucursal_id = svc.validar_station_key(station_key)
        if not sucursal_id:
            return JSONResponse(
                {"valid": False, "error": "Station key inválida"}, status_code=404
            )

        try:
            row = svc.db.execute(
                text("SELECT nombre, codigo FROM sucursales WHERE id = :id LIMIT 1"),
                {"id": int(sucursal_id)},
            ).fetchone()
        except Exception:
            row = None
        sucursal_nombre = row[0] if row and row[0] else "Sucursal"
        sucursal_codigo = row[1] if row and row[1] else None

        return {
            "valid": True,
            "gym_id": None,
            "gym_name": sucursal_nombre,
            "branch_id": int(sucursal_id),
            "branch_name": sucursal_nombre,
            "branch_code": sucursal_codigo,
            "logo_url": None,  # Column doesn't exist in admin DB gyms table
        }
    except Exception as e:
        logger.error(f"Error getting station info: {e}")
        return JSONResponse({"valid": False, "error": str(e)}, status_code=500)


@router.get("/api/checkin/station/token/{station_key}")
async def api_station_token(
    station_key: str, svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Get current active station token (public - no auth required).
    Used by station display to show QR code.
    """
    try:
        sucursal_id = svc.validar_station_key(station_key)
        if not sucursal_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)
        token_data = svc.obtener_station_token_activo(int(sucursal_id))
        return token_data
    except Exception as e:
        logger.error(f"Error getting station token: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/checkin/station/regenerate/{station_key}")
async def api_station_regenerate(
    station_key: str, svc: AttendanceService = Depends(get_attendance_service)
):
    """Legacy alias of /api/checkin/station/token (public)."""
    try:
        sucursal_id = svc.validar_station_key(station_key)
        if not sucursal_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)
        return svc.obtener_station_token_activo(int(sucursal_id))
    except Exception as e:
        logger.error(f"Error regenerating station token: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/checkin/station/recent/{station_key}")
async def api_station_recent(
    station_key: str, svc: AttendanceService = Depends(get_attendance_service)
):
    """
    Get recent check-ins for station display (public - no auth required).
    """
    try:
        sucursal_id = svc.validar_station_key(station_key)
        if not sucursal_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)
        recent = svc.obtener_station_checkins_recientes(int(sucursal_id), limit=5)
        stats = svc.obtener_station_stats(int(sucursal_id))

        return {"checkins": recent, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting recent check-ins: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/checkin/station/updates/{station_key}")
async def api_station_updates(
    station_key: str,
    svc: AttendanceService = Depends(get_attendance_service),
    since_id: int = 0,
    limit: int = 20,
):
    try:
        sucursal_id = svc.validar_station_key(station_key)
        if not sucursal_id:
            return JSONResponse({"error": "Station key inválida"}, status_code=404)

        items = svc.obtener_station_checkins_desde(
            int(sucursal_id), since_id=int(since_id or 0), limit=int(limit or 20)
        )
        last_id = int(since_id or 0)
        for it in items:
            try:
                last_id = max(last_id, int(it.get("id") or 0))
            except Exception:
                pass

        stats = svc.obtener_station_stats(int(sucursal_id))
        return {"checkins": items, "last_id": last_id, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting station updates: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


def _enqueue_auto_unlock_for_sucursal(db: Session, sucursal_id: int, *, request_id: str, source: str) -> None:
    rid = str(request_id or "").strip()[:80]
    if not rid:
        return
    src = str(source or "").strip()[:40] or "checkin"
    row = db.execute(
        text(
            """
            SELECT id, config
            FROM access_devices
            WHERE sucursal_id = :sid AND enabled = TRUE
            ORDER BY id ASC
            """
        ),
        {"sid": int(sucursal_id)},
    ).mappings().all()
    target_id = None
    unlock_ms = 2500
    for r in row:
        cfg = r.get("config") if isinstance(r.get("config"), dict) else {}
        if not bool(cfg.get("allow_remote_unlock")):
            continue
        if not bool(cfg.get("station_auto_unlock")):
            continue
        try:
            unlock_ms = int(cfg.get("station_unlock_ms") or cfg.get("unlock_ms") or 2500)
        except Exception:
            unlock_ms = 2500
        unlock_ms = max(250, min(unlock_ms, 15000))
        target_id = int(r.get("id") or 0)
        break
    if not target_id:
        return
    payload = {"unlock_ms": unlock_ms, "source": src}
    db.execute(
        text(
            """
            INSERT INTO access_commands(device_id, command_type, payload, status, request_id, actor_usuario_id, expires_at, created_at)
            VALUES (:did, 'unlock', CAST(:p AS JSONB), 'pending', :rid, NULL, NOW() + INTERVAL '15 seconds', NOW())
            ON CONFLICT (device_id, request_id) DO NOTHING
            """
        ),
        {"did": int(target_id), "rid": rid, "p": json.dumps(payload, ensure_ascii=False)},
    )


@router.post("/api/checkin/station/scan")
async def api_station_scan(
    request: Request, svc: AttendanceService = Depends(get_attendance_service)
):
    """
    User scans station QR to register attendance.
    Requires user to be authenticated (session with checkin_user_id or user_id).
    """
    try:
        data = await request.json()
        token = str(data.get("token", "")).strip()
        idempotency_key = str(
            request.headers.get("Idempotency-Key") or data.get("idempotency_key") or ""
        ).strip()

        if not token:
            return JSONResponse(
                {"ok": False, "mensaje": "Token requerido"}, status_code=400
            )

        # Get user ID from session
        usuario_id = request.session.get("checkin_user_id") or request.session.get(
            "user_id"
        )
        if not usuario_id:
            return JSONResponse(
                {"ok": False, "mensaje": "Debes iniciar sesión primero"},
                status_code=401,
            )

        if idempotency_key:
            rh = hashlib.sha256(
                f"user:{int(usuario_id)}|token:{token}".encode("utf-8")
            ).hexdigest()
            cached = svc.idempotency_get_response(idempotency_key, request_hash=rh)
            if cached and not cached.get("pending"):
                return JSONResponse(
                    cached.get("body") or {},
                    status_code=int(cached.get("status_code") or 200),
                )
            if cached and cached.get("pending"):
                return JSONResponse(
                    {
                        "ok": False,
                        "mensaje": "Solicitud en progreso, reintentar",
                        "retry_after_ms": 250,
                    },
                    status_code=409,
                )
            svc.idempotency_reserve(
                idempotency_key,
                usuario_id=int(usuario_id),
                route="/api/checkin/qr",
                request_hash=rh,
                ttl_seconds=60,
            )

        # Validate and register
        ok, msg, user_data = svc.validar_station_scan(token, int(usuario_id))
        if ok and isinstance(user_data, dict):
            asistencia_id = user_data.get("asistencia_id")
            created = bool(user_data.get("created"))
            if created and asistencia_id is not None:
                entry = svc.construir_checkin_entry_por_asistencia_id(int(asistencia_id))
                sid = entry.get("sucursal_id") if isinstance(entry, dict) else None
                if sid:
                    await checkin_ws_hub.broadcast(int(sid), entry)
            sid = user_data.get("branch_id") or user_data.get("sucursal_id")
            try:
                sid = int(sid) if sid is not None else None
            except Exception:
                sid = None
            if sid:
                try:
                    _enqueue_auto_unlock_for_sucursal(svc.db, int(sid), request_id=f"station:{token}", source="station_qr")
                    svc.db.commit()
                except Exception:
                    try:
                        svc.db.rollback()
                    except Exception:
                        pass

        payload = {"ok": ok, "mensaje": msg, "usuario": user_data}
        status_code = 200 if ok else 400
        if idempotency_key:
            svc.idempotency_store_response(
                idempotency_key, status_code=status_code, body=payload
            )
        return JSONResponse(payload, status_code=status_code)
    except Exception as e:
        logger.error(f"Error in station scan: {e}")
        return JSONResponse({"ok": False, "mensaje": str(e)}, status_code=500)


@router.post("/api/checkin/qr")
async def api_checkin_qr_alias(
    request: Request, svc: AttendanceService = Depends(get_attendance_service)
):
    """Backwards-compatible alias for station QR scan (legacy endpoint)."""
    return await api_station_scan(request, svc)


# Admin endpoint to generate/get station key
@router.get("/api/gestion/station-key")
async def api_get_station_key(
    request: Request,
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Get or generate station key for the current sucursal (requires owner auth)."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        if not sucursal_id:
            sucursal_id = svc._get_default_sucursal_id()
        if not sucursal_id:
            return JSONResponse({"error": "Sucursal no encontrada"}, status_code=400)

        station_key = svc.generar_station_key(int(sucursal_id))

        # Build the station URL using the current tenant subdomain
        # For cross-origin calls, use the Origin header to determine the frontend URL
        origin = request.headers.get("origin", "")
        if origin:
            station_url = f"{origin}/station/{station_key}"
        else:
            host = request.headers.get("host", "")
            protocol = (
                "https"
                if request.headers.get("x-forwarded-proto") == "https"
                else "http"
            )
            station_url = f"{protocol}://{host}/station/{station_key}"

        return {
            "station_key": station_key,
            "station_url": station_url,
            "sucursal_id": int(sucursal_id),
        }
    except Exception as e:
        logger.error(f"Error getting station key: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/gestion/station-key/regenerate")
async def api_regenerate_station_key(
    request: Request,
    _=Depends(require_owner),
    svc: AttendanceService = Depends(get_attendance_service),
):
    """Regenerate station key (invalidates old URL)."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        if not sucursal_id:
            sucursal_id = svc._get_default_sucursal_id()
        if not sucursal_id:
            return JSONResponse({"error": "Sucursal no encontrada"}, status_code=400)

        new_key = secrets.token_urlsafe(16)
        try:
            svc.db.execute(
                text("UPDATE sucursales SET station_key = :k WHERE id = :id"),
                {"k": new_key, "id": int(sucursal_id)},
            )
            svc.db.commit()
        except Exception:
            try:
                svc.db.rollback()
            except Exception:
                pass
            return JSONResponse(
                {"error": "No se pudo regenerar la station key"}, status_code=500
            )

        # Build the station URL
        origin = request.headers.get("origin", "")
        if origin:
            station_url = f"{origin}/station/{new_key}"
        else:
            host = request.headers.get("host", "")
            protocol = (
                "https"
                if request.headers.get("x-forwarded-proto") == "https"
                else "http"
            )
            station_url = f"{protocol}://{host}/station/{new_key}"

        return {
            "station_key": new_key,
            "station_url": station_url,
            "sucursal_id": int(sucursal_id),
        }
    except Exception as e:
        logger.error(f"Error regenerating station key: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
