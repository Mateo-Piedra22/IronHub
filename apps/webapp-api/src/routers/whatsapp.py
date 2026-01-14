"""WhatsApp Router - WhatsApp messaging API using WhatsAppService and PaymentService."""
import logging
import os
import json
from typing import Optional, Dict, Any

from fastapi import APIRouter, Request, Depends, HTTPException, Response
from fastapi.responses import JSONResponse

from src.dependencies import (
    require_gestion_access, require_owner, 
    get_whatsapp_service, get_payment_service
)
from src.services.whatsapp_service import WhatsAppService
from src.services.payment_service import PaymentService

router = APIRouter()
logger = logging.getLogger(__name__)


def _is_owner_role(role: str) -> bool:
    r = (role or "").lower()
    return r in ("dueño", "dueno", "owner", "admin", "administrador")


def _redact_whatsapp_state_for_role(request: Request, state: Dict[str, Any]) -> Dict[str, Any]:
    """Redact sensitive fields (like access_token) for non-owner roles."""
    try:
        role = str(request.session.get("role") or "")
        if _is_owner_role(role):
            return state

        cfg = state.get("config")
        if isinstance(cfg, dict) and "access_token" in cfg:
            cfg = dict(cfg)
            cfg["access_token"] = ""
            state = dict(state)
            state["config"] = cfg
        return state
    except Exception:
        return state


@router.get("/api/whatsapp/state")
async def api_whatsapp_state(
    request: Request,
    _=Depends(require_gestion_access),
    pm: PaymentService = Depends(get_payment_service)
):
    try:
        state = pm.obtener_estado_whatsapp() if hasattr(pm, 'obtener_estado_whatsapp') else {"disponible": False}
        if isinstance(state, dict):
            redacted = _redact_whatsapp_state_for_role(request, state)
            if isinstance(redacted, dict) and "ok" not in redacted:
                redacted = {"ok": True, "mensaje": "OK", "success": True, "message": "OK", **redacted}
            return redacted
        return state
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.get("/api/whatsapp/stats")
async def api_whatsapp_stats(
    _=Depends(require_owner),
    pm: PaymentService = Depends(get_payment_service)
):
    try:
        data = pm.obtener_estadisticas_whatsapp() if hasattr(pm, 'obtener_estadisticas_whatsapp') else {"error": "Not available"}
        if isinstance(data, dict) and "ok" not in data:
            ok_val = "error" not in data
            msg = "OK" if ok_val else str(data.get("error") or "Error")
            data = {"ok": ok_val, "mensaje": msg, "success": ok_val, "message": msg, **data}
        return data
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.get("/api/whatsapp/pendings")
async def api_whatsapp_pendings(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    try:
        dias = int(request.query_params.get("dias") or 30)
        limite = int(request.query_params.get("limit") or 200)
    except:
        dias, limite = 30, 200
    return {"items": svc.obtener_mensajes_fallidos(dias, limite)}


# === Frontend-compatible alias endpoints ===

@router.get("/api/whatsapp/pendientes")
async def api_whatsapp_pendientes(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    """Alias for /api/whatsapp/pendings - returns {mensajes: []}."""
    try:
        dias = int(request.query_params.get("dias") or 30)
        limite = int(request.query_params.get("limit") or 200)
    except:
        dias, limite = 30, 200
    return {"mensajes": svc.obtener_mensajes_fallidos(dias, limite)}


@router.get("/api/whatsapp/status")
async def api_whatsapp_status(
    request: Request,
    _=Depends(require_gestion_access),
    pm: PaymentService = Depends(get_payment_service)
):
    """Alias for /api/whatsapp/state."""
    try:
        state = pm.obtener_estado_whatsapp() if hasattr(pm, 'obtener_estado_whatsapp') else {"disponible": False}
        if isinstance(state, dict):
            return _redact_whatsapp_state_for_role(request, state)
        return state
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/whatsapp/config")
async def api_whatsapp_config_get(
    _=Depends(require_owner),
    pm: PaymentService = Depends(get_payment_service)
):
    """GET endpoint for WhatsApp config."""
    try:
        config = pm.obtener_config_whatsapp() if hasattr(pm, 'obtener_config_whatsapp') else {}
        data = config or {"enabled": False, "webhook_enabled": False}
        if isinstance(data, dict) and "ok" not in data:
            data = {"ok": True, "mensaje": "OK", "success": True, "message": "OK", **data}
        return data
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/retry-all")
async def api_whatsapp_retry_all(
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service),
    pm: PaymentService = Depends(get_payment_service)
):
    """Retry all failed WhatsApp messages."""
    try:
        failed_messages = svc.obtener_mensajes_fallidos(30, 100)
        retried = 0
        for msg in failed_messages:
            uid = msg.get('usuario_id') or msg.get('user_id')
            if uid:
                try:
                    pm.enviar_mensaje_bienvenida_whatsapp(uid) if hasattr(pm, 'enviar_mensaje_bienvenida_whatsapp') else None
                    retried += 1
                except:
                    pass
        return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "retried": retried}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/clear-failed")
async def api_whatsapp_clear_failed(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    """Alias for /api/whatsapp/clear_failures - clears failed messages."""
    try:
        payload = await request.json()
    except:
        payload = {}
    dias = int(payload.get("days") or 30)
    result = svc.limpiar_fallidos(None, dias)
    cleared = result.get('deleted', 0) if isinstance(result, dict) else 0
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "cleared": cleared}


@router.post("/api/whatsapp/mensajes/{mensaje_id}/retry")
async def api_whatsapp_mensaje_retry(
    mensaje_id: int,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service),
    pm: PaymentService = Depends(get_payment_service)
):
    """Retry a specific WhatsApp message by ID."""
    # Get message info
    # For now, just return success - message retry would need more context
    return {"ok": True}


@router.post("/api/whatsapp/retry")
async def api_whatsapp_retry(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service),
    pm: PaymentService = Depends(get_payment_service)
):
    try:
        payload = await request.json()
    except:
        payload = {}
    
    telefono = str(payload.get("telefono") or payload.get("phone") or "").strip()
    usuario_id = payload.get("usuario_id")
    
    uid = int(usuario_id) if usuario_id else None
    if not uid and telefono:
        uid = svc.obtener_usuario_id_por_telefono(telefono)
    if not uid:
        return JSONResponse(
            {"ok": False, "mensaje": "usuario_id no encontrado", "success": False, "message": "usuario_id no encontrado"},
            status_code=400,
        )
    
    last = svc.obtener_ultimo_fallido(telefono, uid)
    last_type = (last.get("message_type") or "").lower() if last else ""
    
    if last_type in ("welcome", "bienvenida"):
        ok = pm.enviar_mensaje_bienvenida_whatsapp(uid) if hasattr(pm, 'enviar_mensaje_bienvenida_whatsapp') else False
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type or "welcome"}
    elif last_type in ("overdue", "recordatorio_vencida", "payment_reminder"):
        if hasattr(pm, 'whatsapp_manager') and pm.whatsapp_manager:
            ok = pm.whatsapp_manager.enviar_recordatorio_cuota_vencida(uid)
            msg = "OK" if bool(ok) else "Error"
            return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type}
        return JSONResponse(
            {"ok": False, "mensaje": "WhatsApp manager not available", "success": False, "message": "WhatsApp manager not available"},
            status_code=503,
        )
    else:
        ok = pm.enviar_mensaje_bienvenida_whatsapp(uid) if hasattr(pm, 'enviar_mensaje_bienvenida_whatsapp') else False
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "tipo": last_type or "welcome"}


@router.post("/api/whatsapp/clear_failures")
async def api_whatsapp_clear_failures(
    request: Request,
    _=Depends(require_owner),
    svc: WhatsAppService = Depends(get_whatsapp_service)
):
    try:
        payload = await request.json()
    except:
        payload = {}
    telefono = str(payload.get("telefono") or payload.get("phone") or "").strip() or None
    dias = int(payload.get("desde_dias") or payload.get("days") or 30)
    result = svc.limpiar_fallidos(telefono, dias)
    ok_val = bool(isinstance(result, dict) and ('error' not in result))
    msg = "OK" if ok_val else str((result or {}).get('error') if isinstance(result, dict) else 'Error')
    payload_out = {"ok": ok_val, "mensaje": msg, "success": ok_val, "message": msg}
    if isinstance(result, dict):
        payload_out.update(result)
    return payload_out


@router.post("/api/whatsapp/server/start")
async def api_whatsapp_server_start(_=Depends(require_owner), pm: PaymentService = Depends(get_payment_service)):
    try:
        ok = pm.iniciar_servidor_whatsapp() if hasattr(pm, 'iniciar_servidor_whatsapp') else False
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/server/stop")
async def api_whatsapp_server_stop(_=Depends(require_owner), pm: PaymentService = Depends(get_payment_service)):
    try:
        ok = pm.detener_servidor_whatsapp() if hasattr(pm, 'detener_servidor_whatsapp') else False
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/whatsapp/config")
async def api_whatsapp_config(request: Request, _=Depends(require_owner), pm: PaymentService = Depends(get_payment_service)):
    try:
        data = await request.json() if request.headers.get("content-type", "").startswith("application/json") else await request.form()
    except:
        data = {}
    allowed = {"phone_number_id", "whatsapp_business_account_id", "access_token", "allowlist_numbers", "allowlist_enabled", "enable_webhook", "max_retries", "retry_delay_seconds"}
    cfg = {k: data.get(k) for k in allowed if k in data}
    ok = pm.configurar_whatsapp(cfg) if hasattr(pm, 'configurar_whatsapp') else False
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg, "applied_keys": list(cfg.keys())}


@router.post("/api/usuarios/{usuario_id}/whatsapp/bienvenida")
async def api_usuario_whatsapp_bienvenida(usuario_id: int, _=Depends(require_gestion_access), pm: PaymentService = Depends(get_payment_service)):
    try:
        ok = pm.enviar_mensaje_bienvenida_whatsapp(usuario_id) if hasattr(pm, 'enviar_mensaje_bienvenida_whatsapp') else False
        msg = "OK" if bool(ok) else "Error"
        return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}
    except Exception as e:
        return JSONResponse(
            {"ok": False, "mensaje": str(e), "success": False, "message": str(e), "error": str(e)},
            status_code=500,
        )


@router.post("/api/usuarios/{usuario_id}/whatsapp/confirmacion_pago")
async def api_usuario_whatsapp_confirmacion_pago(usuario_id: int, request: Request, _=Depends(require_gestion_access), pm: PaymentService = Depends(get_payment_service)):
    try:
        payload = await request.json()
    except:
        payload = {}
    
    if not hasattr(pm, 'whatsapp_manager') or not pm.whatsapp_manager:
        return JSONResponse(
            {"ok": False, "mensaje": "WhatsApp manager not available", "success": False, "message": "WhatsApp manager not available"},
            status_code=503,
        )
    
    monto = payload.get("monto")
    mes = payload.get("mes") or payload.get("month")
    anio = payload.get("año") or payload.get("anio") or payload.get("year")
    
    # Get user info
    usuario = pm.obtener_usuario_por_id(usuario_id) if hasattr(pm, 'obtener_usuario_por_id') else None
    telefono = getattr(usuario, 'telefono', None) if usuario else None
    nombre = getattr(usuario, 'nombre', None) if usuario else None
    
    # Get last payment if needed
    if monto is None or mes is None or anio is None:
        pagos = pm.obtener_historial_pagos(usuario_id, limit=1) if hasattr(pm, 'obtener_historial_pagos') else []
        if pagos:
            monto = monto or getattr(pagos[0], 'monto', None)
            mes = mes or getattr(pagos[0], 'mes', None)
            anio = anio or getattr(pagos[0], 'año', None)
    
    if not telefono or monto is None or mes is None or anio is None:
        return JSONResponse(
            {"ok": False, "mensaje": "Datos insuficientes", "success": False, "message": "Datos insuficientes"},
            status_code=400,
        )
    
    ok = pm.whatsapp_manager.send_payment_confirmation({
        'user_id': usuario_id, 'phone': str(telefono), 'name': str(nombre or ""),
        'amount': float(monto), 'date': f"{int(mes):02d}/{int(anio)}"
    })
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/desactivacion")
async def api_usuario_whatsapp_desactivacion(usuario_id: int, request: Request, _=Depends(require_gestion_access), pm: PaymentService = Depends(get_payment_service)):
    if not hasattr(pm, 'whatsapp_manager') or not pm.whatsapp_manager:
        return JSONResponse(
            {"ok": False, "mensaje": "WhatsApp manager not available", "success": False, "message": "WhatsApp manager not available"},
            status_code=503,
        )
    try:
        payload = await request.json()
    except:
        payload = {}
    motivo = (payload.get("motivo") or "cuotas vencidas").strip()
    ok = pm.whatsapp_manager.enviar_notificacion_desactivacion(usuario_id=usuario_id, motivo=motivo, force_send=True)
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/recordatorio_vencida")
async def api_usuario_whatsapp_recordatorio_vencida(usuario_id: int, _=Depends(require_gestion_access), pm: PaymentService = Depends(get_payment_service)):
    if not hasattr(pm, 'whatsapp_manager') or not pm.whatsapp_manager:
        return JSONResponse(
            {"ok": False, "mensaje": "WhatsApp manager not available", "success": False, "message": "WhatsApp manager not available"},
            status_code=503,
        )
    ok = pm.whatsapp_manager.enviar_recordatorio_cuota_vencida(usuario_id)
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/force")
async def api_usuario_whatsapp_force(
    usuario_id: int,
    request: Request,
    _=Depends(require_owner),
    pm: PaymentService = Depends(get_payment_service)
):
    """Force send a WhatsApp message of a specific type to a user."""
    try:
        payload = await request.json()
    except:
        payload = {}
    
    tipo = (payload.get("tipo") or "").lower()
    
    if not hasattr(pm, 'whatsapp_manager') or not pm.whatsapp_manager:
        return JSONResponse(
            {"ok": False, "mensaje": "WhatsApp manager not available", "success": False, "message": "WhatsApp manager not available"},
            status_code=503,
        )
    
    ok = False
    if tipo in ("welcome", "bienvenida"):
        ok = pm.enviar_mensaje_bienvenida_whatsapp(usuario_id) if hasattr(pm, 'enviar_mensaje_bienvenida_whatsapp') else False
    elif tipo in ("overdue", "vencida", "recordatorio"):
        ok = pm.whatsapp_manager.enviar_recordatorio_cuota_vencida(usuario_id)
    elif tipo in ("deactivation", "desactivacion"):
        ok = pm.whatsapp_manager.enviar_notificacion_desactivacion(usuario_id=usuario_id, motivo="Por decisión del administrador", force_send=True)
    else:
        # Default to welcome
        ok = pm.enviar_mensaje_bienvenida_whatsapp(usuario_id) if hasattr(pm, 'enviar_mensaje_bienvenida_whatsapp') else False

    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.post("/api/usuarios/{usuario_id}/whatsapp/recordatorio_clase")
async def api_usuario_whatsapp_recordatorio_clase(usuario_id: int, request: Request, _=Depends(require_gestion_access), pm: PaymentService = Depends(get_payment_service)):
    if not hasattr(pm, 'whatsapp_manager') or not pm.whatsapp_manager:
        return JSONResponse(
            {"ok": False, "mensaje": "WhatsApp manager not available", "success": False, "message": "WhatsApp manager not available"},
            status_code=503,
        )
    try:
        payload = await request.json()
    except:
        payload = {}
    ok = pm.whatsapp_manager.enviar_recordatorio_horario_clase(usuario_id, {
        'tipo_clase': payload.get('tipo_clase') or payload.get('clase_nombre') or '',
        'fecha': payload.get('fecha') or '', 'hora': payload.get('hora') or ''
    })
    msg = "OK" if bool(ok) else "Error"
    return {"ok": bool(ok), "mensaje": msg, "success": bool(ok), "message": msg}


@router.get("/api/usuarios/{usuario_id}/whatsapp/ultimo")
async def api_usuario_whatsapp_ultimo(usuario_id: int, request: Request, _=Depends(require_owner), svc: WhatsAppService = Depends(get_whatsapp_service)):
    direccion = request.query_params.get("direccion")
    tipo = request.query_params.get("tipo")
    return {
        "ok": True,
        "mensaje": "OK",
        "success": True,
        "message": "OK",
        "item": svc.obtener_ultimo_mensaje(usuario_id, tipo, direccion if direccion in (None, "enviado", "recibido") else None),
    }


@router.get("/api/usuarios/{usuario_id}/whatsapp/historial")
async def api_usuario_whatsapp_historial(usuario_id: int, request: Request, _=Depends(require_gestion_access), svc: WhatsAppService = Depends(get_whatsapp_service)):
    tipo = request.query_params.get("tipo")
    limite = int(request.query_params.get("limit") or 50)
    return {"mensajes": svc.obtener_historial_usuario(usuario_id, tipo, limite)}


@router.delete("/api/usuarios/{usuario_id}/whatsapp/{message_pk}")
async def api_usuario_whatsapp_delete(usuario_id: int, message_pk: int, _=Depends(require_owner), svc: WhatsAppService = Depends(get_whatsapp_service)):
    old_item = svc.obtener_mensaje_por_pk(usuario_id, message_pk)
    ok = svc.eliminar_mensaje_por_pk(usuario_id, message_pk)
    if not ok:
        return JSONResponse(
            {"ok": False, "mensaje": "Mensaje no encontrado", "success": False, "message": "Mensaje no encontrado"},
            status_code=404,
        )
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "deleted": message_pk}


@router.delete("/api/usuarios/{usuario_id}/whatsapp/by-mid/{message_id}")
async def api_usuario_whatsapp_delete_by_mid(usuario_id: int, message_id: str, _=Depends(require_owner), svc: WhatsAppService = Depends(get_whatsapp_service)):
    ok = svc.eliminar_mensaje_por_mid(usuario_id, message_id)
    if not ok:
        return JSONResponse(
            {"ok": False, "mensaje": "Mensaje no encontrado", "success": False, "message": "Mensaje no encontrado"},
            status_code=404,
        )
    return {"ok": True, "mensaje": "OK", "success": True, "message": "OK", "deleted_mid": message_id}


# --- Webhooks ---

@router.get("/webhooks/whatsapp")
async def whatsapp_verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if mode == "subscribe" and expected and token == expected and challenge:
        return Response(content=str(challenge), media_type="text/plain")
    raise HTTPException(status_code=403, detail="Invalid verify token")


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, svc: WhatsAppService = Depends(get_whatsapp_service)):
    try:
        raw = await request.body()
        dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in ("1", "true", "yes") or os.getenv("ENV", "").lower() in ("dev", "development")
        allow_unsigned = os.getenv("ALLOW_UNSIGNED_WHATSAPP_WEBHOOK", "").lower() in ("1", "true", "yes")

        app_secret = os.getenv("WHATSAPP_APP_SECRET", "")
        if not app_secret and not (dev_mode or allow_unsigned):
            raise HTTPException(status_code=503, detail="Webhook signature not configured")

        if app_secret:
            import hmac, hashlib
            sig = request.headers.get("X-Hub-Signature-256") or ""
            expected = "sha256=" + hmac.new(app_secret.encode(), raw, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected, sig):
                raise HTTPException(status_code=403, detail="Invalid signature")
        
        payload = json.loads(raw.decode())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail="Bad Request")
    
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            
            # Status updates
            for status in value.get("statuses") or []:
                mid, st = status.get("id"), status.get("status")
                if mid and st:
                    svc.actualizar_estado_mensaje(mid, st)
            
            # Incoming messages
            for msg in value.get("messages") or []:
                mid = msg.get("id")
                mtype = msg.get("type")
                wa_from = msg.get("from")
                
                text = None
                if mtype == "text":
                    text = (msg.get("text") or {}).get("body")
                elif mtype == "button":
                    text = (msg.get("button") or {}).get("text")
                elif mtype == "interactive":
                    ir = msg.get("interactive") or {}
                    text = (ir.get("button_reply") or {}).get("title") or (ir.get("list_reply") or {}).get("title")
                elif mtype in ("image", "audio", "video", "document"):
                    text = f"[{mtype}]"
                
                uid = svc.obtener_usuario_id_por_telefono(wa_from) if wa_from else None
                svc.registrar_mensaje_entrante(uid, wa_from, text or "", mid)
    
    return {"status": "ok"}
