import logging
import os
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, List, Dict, Any

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from fastapi import APIRouter, Request, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy import select, or_, text

from src.dependencies import (
    get_payment_service,
    require_gestion_access,
    get_whatsapp_dispatch_service,
    require_owner,
    get_audit_service,
    require_feature,
    require_sucursal_selected,
    require_sucursal_selected_optional,
    get_membership_service,
    require_scope_gestion,
)
from src.services.payment_service import PaymentService
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService
from src.services.audit_service import AuditService
from src.services.membership_service import MembershipService
from src.database.orm_models import Usuario

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_public_base_url(request: Request) -> str:
    try:
        xf_proto = (
            (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
        )
        xf_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
        host = xf_host or (request.headers.get("host") or "").split(",")[0].strip()
        proto = xf_proto or (request.url.scheme if hasattr(request, "url") else "")
        if host and proto:
            return f"{proto}://{host}".rstrip("/")
    except Exception:
        pass
    try:
        return str(request.base_url).rstrip("/")
    except Exception:
        return os.environ.get("API_BASE_URL", "https://api.ironhub.motiona.xyz").rstrip(
            "/"
        )


def _now_local_naive() -> datetime:
    tz_name = (
        os.getenv("APP_TIMEZONE")
        or os.getenv("TIMEZONE")
        or os.getenv("TZ")
        or "America/Argentina/Buenos_Aires"
    )
    if ZoneInfo is not None:
        try:
            tz = ZoneInfo(tz_name)
            return datetime.now(timezone.utc).astimezone(tz).replace(tzinfo=None)
        except Exception:
            pass
    return (
        datetime.now(timezone.utc)
        .astimezone(timezone(timedelta(hours=-3)))
        .replace(tzinfo=None)
    )


# --- Config Endpoints (for webapp-web frontend compatibility) ---


@router.get("/api/config/tipos-cuota", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_tipos_cuota(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get subscription types. Returns {tipos: []}."""
    try:
        tipos = svc.obtener_tipos_cuota(solo_activos=True)
        return {"tipos": tipos}
    except Exception as e:
        logger.error(f"Error obteniendo tipos_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/config/metodos-pago", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_metodos_pago(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get payment methods. Returns {metodos: []}."""
    try:
        metodos = svc.obtener_metodos_pago(solo_activos=True)
        return {"metodos": metodos}
    except Exception as e:
        logger.error(f"Error obteniendo metodos_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/config/conceptos", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_conceptos(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get payment concepts. Returns {conceptos: []}."""
    try:
        conceptos = svc.obtener_conceptos_pago(solo_activos=True)
        return {"conceptos": conceptos}
    except Exception as e:
        logger.error(f"Error obteniendo conceptos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- CRUD for /api/config/tipos-cuota ---


@router.post("/api/config/tipos-cuota", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_tipos_cuota_create(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Create subscription type."""
    payload = await request.json()
    try:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' es obligatorio")
        data = {
            "nombre": nombre,
            "precio": float(payload.get("precio") or 0),
            "duracion_dias": int(payload.get("duracion_dias") or 30),
            "activo": True,
        }
        new_id = svc.crear_tipo_cuota(data)
        return {"ok": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/config/tipos-cuota/{tipo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_tipos_cuota_update(
    tipo_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update subscription type."""
    payload = await request.json()
    try:
        updated = svc.actualizar_tipo_cuota(tipo_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Tipo de cuota no encontrado")
        return {"ok": True, "id": tipo_id}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/config/tipos-cuota/{tipo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_tipos_cuota_delete(
    tipo_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Delete subscription type."""
    try:
        deleted = svc.eliminar_tipo_cuota(tipo_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Tipo de cuota no encontrado")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/config/tipos-cuota/{tipo_id}/toggle", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_tipos_cuota_toggle(
    tipo_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Toggle subscription type active status."""
    try:
        tipo = svc.obtener_tipo_cuota(tipo_id)
        if not tipo:
            raise HTTPException(status_code=404, detail="Tipo de cuota no encontrado")
        new_status = not tipo.activo
        svc.actualizar_tipo_cuota(tipo_id, {"activo": new_status})
        return {"ok": True, "activo": new_status}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# --- CRUD for /api/config/metodos-pago ---


@router.post("/api/config/metodos-pago", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_metodos_pago_create(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Create payment method."""
    payload = await request.json()
    try:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' es obligatorio")
        data = {"nombre": nombre, "activo": True, "comision": 0}
        new_id = svc.crear_metodo_pago(data)
        return {"ok": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/config/metodos-pago/{metodo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_metodos_pago_update(
    metodo_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update payment method."""
    payload = await request.json()
    try:
        updated = svc.actualizar_metodo_pago(metodo_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Método de pago no encontrado")
        return {"ok": True, "id": metodo_id}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/config/metodos-pago/{metodo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_metodos_pago_delete(
    metodo_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Delete payment method."""
    try:
        deleted = svc.eliminar_metodo_pago(metodo_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Método de pago no encontrado")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/config/metodos-pago/{metodo_id}/toggle", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_metodos_pago_toggle(
    metodo_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Toggle payment method active status."""
    try:
        metodo = svc.obtener_metodo_pago(metodo_id)
        if not metodo:
            raise HTTPException(status_code=404, detail="Método de pago no encontrado")
        new_status = not metodo.activo
        svc.actualizar_metodo_pago(metodo_id, {"activo": new_status})
        return {"ok": True, "activo": new_status}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# --- CRUD for /api/config/conceptos ---


@router.post("/api/config/conceptos", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_conceptos_create(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Create payment concept."""
    payload = await request.json()
    try:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' es obligatorio")
        data = {"nombre": nombre, "activo": True}
        new_id = svc.crear_concepto_pago(data)
        return {"ok": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/config/conceptos/{concepto_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_conceptos_update(
    concepto_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update payment concept."""
    payload = await request.json()
    try:
        updated = svc.actualizar_concepto_pago(concepto_id, payload)
        if not updated:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")
        return {"ok": True, "id": concepto_id}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/config/conceptos/{concepto_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_conceptos_delete(
    concepto_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Delete payment concept."""
    try:
        deleted = svc.eliminar_concepto_pago(concepto_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/config/conceptos/{concepto_id}/toggle", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_conceptos_toggle(
    concepto_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Toggle payment concept active status."""
    try:
        concepto = svc.obtener_concepto_pago(concepto_id)
        if not concepto:
            raise HTTPException(status_code=404, detail="Concepto no encontrado")
        new_status = not concepto.activo
        svc.actualizar_concepto_pago(concepto_id, {"activo": new_status})
        return {"ok": True, "activo": new_status}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Config Recibos Endpoints (frontend-compatible aliases) ---


@router.get("/api/config/recibos", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_recibos_get(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get receipt numbering configuration (frontend-compatible alias)."""
    try:
        cfg = svc.get_receipt_numbering_config()
        return cfg
    except Exception as e:
        logger.error(f"Error obteniendo config recibos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/config/recibos", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_recibos_put(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update receipt numbering configuration (frontend-compatible alias)."""
    try:
        payload = await request.json()
        ok = svc.save_receipt_numbering_config(payload)
        if ok:
            return {"ok": True}
        return JSONResponse(
            {"error": "No se pudo guardar la configuración"}, status_code=400
        )
    except Exception as e:
        logger.error(f"Error guardando config recibos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/config/recibos/next-number", dependencies=[Depends(require_feature("configuracion"))])
async def api_config_recibos_next_number(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get next receipt number (frontend-compatible alias)."""
    try:
        numero = svc.get_next_receipt_number()
        return {"numero": str(numero)}
    except Exception as e:
        logger.error(f"Error obteniendo numero proximo: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- API Metadatos de pago ---


@router.get("/api/metodos_pago", dependencies=[Depends(require_feature("configuracion"))])
async def api_metodos_pago(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get all active payment methods using SQLAlchemy."""
    try:
        return svc.obtener_metodos_pago(solo_activos=True)
    except Exception as e:
        logger.error(f"Error obteniendo metodos_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/metodos_pago", dependencies=[Depends(require_feature("configuracion"))])
async def api_metodos_pago_create(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Create a new payment method using SQLAlchemy."""
    payload = await request.json()
    try:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' es obligatorio")

        comision_raw = payload.get("comision")
        comision = float(comision_raw) if comision_raw is not None else 0.0
        if comision < 0 or comision > 100:
            raise HTTPException(
                status_code=400, detail="'comision' debe estar entre 0 y 100"
            )

        data = {
            "nombre": nombre,
            "icono": payload.get("icono"),
            "color": (payload.get("color") or "#3498db").strip() or "#3498db",
            "comision": comision,
            "activo": bool(payload.get("activo", True)),
            "descripcion": payload.get("descripcion"),
        }
        new_id = svc.crear_metodo_pago(data)
        return {"ok": True, "id": int(new_id)}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando metodo_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/pagos/defaults/{usuario_id}", dependencies=[Depends(require_feature("pagos"))])
async def api_pagos_defaults(
    usuario_id: int,
    _scope=Depends(require_scope_gestion("pagos:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """
    Get default payment values for a user (Auto-Quota).
    Used to pre-fill the payment form.
    """
    try:
        defaults = svc.obtener_datos_cuota_usuario(usuario_id)
        if defaults:
            return defaults
        # Return empty defaults if no config found (not 404, just no defaults)
        return {"nombre": None, "precio": 0, "concepto_id": None}
    except Exception as e:
        logger.error(f"Error getting payment defaults for {usuario_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/metodos_pago/{metodo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_metodos_pago_update(
    metodo_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update a payment method using SQLAlchemy."""
    payload = await request.json()
    try:
        existing = svc.obtener_metodo_pago(int(metodo_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Método de pago no encontrado")

        data = {}
        if "nombre" in payload:
            data["nombre"] = (
                payload.get("nombre") or existing.nombre or ""
            ).strip() or existing.nombre
        if "icono" in payload:
            data["icono"] = payload.get("icono")
        if "color" in payload:
            data["color"] = (
                payload.get("color") or existing.color or "#3498db"
            ).strip()
        if "comision" in payload and payload.get("comision") is not None:
            comision = float(payload.get("comision"))
            if comision < 0 or comision > 100:
                raise HTTPException(
                    status_code=400, detail="'comision' debe estar entre 0 y 100"
                )
            data["comision"] = comision
        if "activo" in payload:
            data["activo"] = bool(payload.get("activo"))
        if "descripcion" in payload:
            data["descripcion"] = payload.get("descripcion")

        updated = svc.actualizar_metodo_pago(int(metodo_id), data)
        if not updated:
            raise HTTPException(
                status_code=404, detail="No se pudo actualizar el método de pago"
            )
        return {"ok": True, "id": int(metodo_id)}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando metodo_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/metodos_pago/{metodo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_metodos_pago_delete(
    metodo_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Delete a payment method using SQLAlchemy."""
    try:
        deleted = svc.eliminar_metodo_pago(int(metodo_id))
        if not deleted:
            raise HTTPException(
                status_code=404, detail="No se pudo eliminar el método de pago"
            )
        return {"ok": True}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando metodo_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Tipos de Cuota (Planes) ---


@router.get("/api/tipos_cuota_activos", dependencies=[Depends(require_feature("configuracion"))])
async def api_tipos_cuota_activos(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get active subscription types sorted by price using SQLAlchemy."""
    try:
        return svc.obtener_tipos_cuota_activos()
    except Exception as e:
        logger.error(f"Error obteniendo tipos_cuota_activos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/tipos_cuota_catalogo", dependencies=[Depends(require_feature("configuracion"))])
async def api_tipos_cuota_catalogo(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get all subscription types (catalog) using SQLAlchemy."""
    try:
        tipos = svc.obtener_tipos_cuota(solo_activos=False)
        # Sort: active first, then by price, then by name
        tipos = sorted(
            tipos,
            key=lambda t: (
                0 if t.get("activo", True) else 1,
                t.get("precio", 0),
                t.get("nombre", ""),
            ),
        )
        return tipos
    except Exception as e:
        logger.error(f"Error obteniendo tipos_cuota_catalogo: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/tipos_cuota", dependencies=[Depends(require_feature("configuracion"))])
async def api_tipos_cuota_create(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Create a subscription type using SQLAlchemy."""
    payload = await request.json()
    try:
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' es obligatorio")

        precio_raw = payload.get("precio")
        precio = float(precio_raw) if precio_raw is not None else 0.0
        if precio < 0:
            raise HTTPException(
                status_code=400, detail="'precio' no puede ser negativo"
            )

        duracion_raw = payload.get("duracion_dias")
        duracion_dias = int(duracion_raw) if duracion_raw is not None else 30
        if duracion_dias <= 0:
            raise HTTPException(status_code=400, detail="'duracion_dias' debe ser > 0")

        data = {
            "nombre": nombre,
            "precio": precio,
            "duracion_dias": duracion_dias,
            "activo": bool(payload.get("activo", True)),
            "descripcion": payload.get("descripcion"),
            "icono_path": payload.get("icono_path"),
        }
        new_id = svc.crear_tipo_cuota(data)
        return {"ok": True, "id": new_id}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando tipo_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/tipos_cuota/{tipo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_tipos_cuota_update(
    tipo_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update a subscription type using SQLAlchemy."""
    payload = await request.json()
    try:
        existing = svc.obtener_tipo_cuota(int(tipo_id))
        if not existing:
            raise HTTPException(status_code=404, detail="Tipo de cuota no encontrado")

        data = {}
        if "nombre" in payload:
            data["nombre"] = (
                payload.get("nombre") or existing.nombre or ""
            ).strip() or existing.nombre
        if "precio" in payload and payload.get("precio") is not None:
            precio = float(payload.get("precio"))
            if precio < 0:
                raise HTTPException(
                    status_code=400, detail="'precio' no puede ser negativo"
                )
            data["precio"] = precio
        if "duracion_dias" in payload and payload.get("duracion_dias") is not None:
            duracion = int(payload.get("duracion_dias"))
            if duracion <= 0:
                raise HTTPException(
                    status_code=400, detail="'duracion_dias' debe ser > 0"
                )
            data["duracion_dias"] = duracion
        if "activo" in payload:
            data["activo"] = bool(payload.get("activo"))
        if "descripcion" in payload:
            data["descripcion"] = payload.get("descripcion")
        if "icono_path" in payload:
            data["icono_path"] = payload.get("icono_path")

        updated = svc.actualizar_tipo_cuota(int(tipo_id), data)
        if not updated:
            raise HTTPException(
                status_code=500, detail="No se pudo actualizar el tipo de cuota"
            )
        return {"ok": True, "id": int(tipo_id)}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando tipo_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/tipos_cuota/{tipo_id}", dependencies=[Depends(require_feature("configuracion"))])
async def api_tipos_cuota_delete(
    tipo_id: int,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Delete a subscription type using SQLAlchemy."""
    try:
        deleted = svc.eliminar_tipo_cuota(int(tipo_id))
        if not deleted:
            raise HTTPException(
                status_code=404, detail="No se pudo eliminar el tipo de cuota"
            )
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando tipo_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Pagos y Recibos ---


@router.get("/api/pagos", dependencies=[Depends(require_feature("pagos"))])
async def api_pagos_list(
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:read")),
    sucursal_id: Optional[int] = Depends(require_sucursal_selected_optional),
    svc: PaymentService = Depends(get_payment_service),
    ms: MembershipService = Depends(get_membership_service),
):
    """List payments with optional filters. Returns {pagos: [], total}."""
    try:
        # AuthZ:
        # - Gestion sessions can query arbitrary users via usuario_id.
        # - Member sessions can only query their own payments.
        try:
            role = str(request.session.get("role") or "").strip().lower()
        except Exception:
            role = ""
        is_gestion = (
            bool(request.session.get("logged_in"))
            or bool(request.session.get("gestion_profesor_user_id"))
            or role
            in (
                "dueño",
                "dueno",
                "owner",
                "admin",
                "administrador",
                "profesor",
                "empleado",
                "recepcionista",
                "staff",
            )
        )
        if is_gestion and sucursal_id is None:
            raise HTTPException(status_code=428, detail="Sucursal requerida")
        if is_gestion and role in ("profesor", "empleado", "recepcionista", "staff"):
            staff_uid = request.session.get("gestion_profesor_user_id") or request.session.get("user_id")
            if not staff_uid:
                raise HTTPException(status_code=401, detail="Unauthorized")
            row = svc.db.execute(
                text("SELECT scopes FROM staff_permissions WHERE usuario_id = :uid"),
                {"uid": int(staff_uid)},
            ).scalar()
            scopes: List[str] = []
            try:
                if row:
                    scopes = list(row)
            except Exception:
                scopes = []
            if ("pagos:read" not in scopes) and ("pagos:*" not in scopes):
                raise HTTPException(status_code=403, detail="Forbidden")
        session_user_id = request.session.get("user_id")
        if (not is_gestion) and (session_user_id is None):
            raise HTTPException(status_code=401, detail="Unauthorized")

        desde = request.query_params.get("desde")
        hasta = request.query_params.get("hasta")
        usuario_id = request.query_params.get("usuario_id")
        metodo_id = request.query_params.get("metodo_id")
        limit_q = request.query_params.get("limit")
        offset_q = request.query_params.get("offset")
        page_q = request.query_params.get("page")

        limit = int(limit_q) if (limit_q and str(limit_q).isdigit()) else 50
        limit = max(1, min(limit, 100))
        offset = 0
        if offset_q and str(offset_q).isdigit():
            offset = int(offset_q)
        elif page_q and str(page_q).isdigit():
            page_n = max(1, int(page_q))
            offset = (page_n - 1) * limit
        offset = max(0, offset)

        uid_filter: Optional[int] = None
        if not is_gestion:
            uid_filter = int(session_user_id)
            if sucursal_id is not None:
                allowed, reason = ms.check_access(int(uid_filter), int(sucursal_id))
            else:
                allowed, reason = ms.check_access_any(int(uid_filter))
            if allowed is False:
                raise HTTPException(status_code=403, detail=reason or "Forbidden")
        elif usuario_id and str(usuario_id).isdigit():
            uid_filter = int(usuario_id)
            try:
                role = str(request.session.get("role") or "").strip().lower()
            except Exception:
                role = ""
            if role not in ("dueño", "dueno", "owner", "admin", "administrador"):
                allowed, reason = ms.check_access(int(uid_filter), int(sucursal_id or 0))
                if allowed is False:
                    raise HTTPException(status_code=403, detail=reason or "Forbidden")

        mid_filter: Optional[int] = None
        if metodo_id and str(metodo_id).isdigit():
            mid_filter = int(metodo_id)

        suc_filter: Optional[int] = None
        if is_gestion:
            try:
                suc_filter = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                suc_filter = None

        out = svc.obtener_pagos_por_fecha_paginados(
            start=desde,
            end=hasta,
            usuario_id=uid_filter,
            metodo_id=mid_filter,
            sucursal_id=suc_filter,
            limit=limit,
            offset=offset,
        )
        items = list(out.get("items") or [])
        total = int(out.get("total") or 0)

        pagos_out = []
        for r in items:
            pagos_out.append(
                {
                    "id": r.get("id"),
                    "usuario_id": r.get("usuario_id"),
                    "usuario_nombre": r.get("usuario_nombre"),
                    "monto": r.get("monto") or 0,
                    "fecha": r.get("fecha_pago"),
                    "mes": r.get("mes"),
                    "anio": r.get("anio"),
                    "sucursal_id": r.get("sucursal_id"),
                    "sucursal_nombre": r.get("sucursal_nombre"),
                    "metodo_pago_id": r.get("metodo_pago_id"),
                    "metodo_pago_nombre": r.get("metodo_pago"),
                    "recibo_numero": r.get("recibo_numero"),
                    "estado": r.get("estado"),
                    "tipo_cuota_nombre": r.get("tipo_cuota"),
                }
            )

        return {"pagos": pagos_out, "total": total}
    except Exception as e:
        logger.error(f"Error obteniendo pagos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/pagos_detalle", dependencies=[Depends(require_feature("pagos"))])
async def api_pagos_detalle(
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get payments with optional date range and search filter using SQLAlchemy."""
    try:
        start = request.query_params.get("start")
        end = request.query_params.get("end")
        q = request.query_params.get("q")
        limit_q = request.query_params.get("limit")
        offset_q = request.query_params.get("offset")

        limit = int(limit_q) if (limit_q and str(limit_q).isdigit()) else 50
        offset = int(offset_q) if (offset_q and str(offset_q).isdigit()) else 0

        if start and isinstance(start, str) and start.strip() == "":
            start = None
        if end and isinstance(end, str) and end.strip() == "":
            end = None

        rows = svc.obtener_pagos_por_fecha(start, end)
        items = rows

        # Apply search filter
        if q and isinstance(q, str) and q.strip() != "":
            ql = q.lower()

            def _match(r: Dict[str, Any]) -> bool:
                try:
                    nombre = str(
                        r.get("usuario_nombre") or r.get("nombre") or ""
                    ).lower()
                    dni = str(r.get("dni") or "").lower()
                    metodo = str(r.get("metodo_pago") or r.get("metodo") or "").lower()
                    concepto = str(
                        r.get("concepto_pago") or r.get("concepto") or ""
                    ).lower()
                    return (
                        (ql in nombre)
                        or (ql in dni)
                        or (ql in metodo)
                        or (ql in concepto)
                    )
                except Exception:
                    return False

            items = [r for r in rows if _match(r)]

        total = len(items)
        sliced = items[offset : offset + limit]
        return {"count": total, "items": sliced}
    except Exception as e:
        logger.error(f"Error obteniendo pagos_detalle: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/pagos/{pago_id}", dependencies=[Depends(require_feature("pagos"))])
async def api_pago_resumen(
    pago_id: int,
    _scope=Depends(require_scope_gestion("pagos:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get payment summary with user and details using SQLAlchemy."""
    try:
        resumen = svc.obtener_pago_resumen(int(pago_id))
        if not resumen:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        # Extract detalles and format response
        detalles = resumen.pop("detalles", [])
        total_detalles = resumen.pop("total_detalles", 0)

        return {"pago": resumen, "detalles": detalles, "total_detalles": total_detalles}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo pago resumen: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put(
    "/api/pagos/{pago_id}",
    dependencies=[Depends(require_feature("pagos")), Depends(require_feature("pagos:update"))],
)
async def api_pago_update(
    pago_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """
    Update a payment with differential calculation for user expiration.

    This endpoint implements differential calculation:
    - Calculates delta between old and new item durations
    - Adjusts user's fecha_proximo_vencimiento by delta
    - Updates pago's tipo_cuota (historical record)
    - Does NOT change user's tipo_cuota (profile preference)
    """
    try:
        payload = await request.json()

        # Extract items from payload
        items = payload.get("items") or payload.get("conceptos") or []
        if not items:
            raise HTTPException(status_code=400, detail="Se requiere al menos un item")

        # Normalize items format
        nuevo_items = []
        for item in items:
            nuevo_items.append(
                {
                    "descripcion": item.get("descripcion", ""),
                    "cantidad": float(item.get("cantidad", 1) or 1),
                    "precio_unitario": float(
                        item.get("precio_unitario") or item.get("precio") or 0
                    ),
                    "concepto_id": item.get("concepto_id"),
                }
            )

        # Optional: explicit tipo_cuota override
        tipo_cuota_override = payload.get("tipo_cuota_nombre") or payload.get(
            "tipo_cuota"
        )

        # Call service method with differential calculation
        result = svc.actualizar_pago_con_diferencial(
            pago_id=int(pago_id),
            nuevo_items=nuevo_items,
            nuevo_tipo_cuota_nombre=tipo_cuota_override,
        )

        return {
            "ok": True,
            "mensaje": "Pago actualizado correctamente",
            "success": True,
            "message": "Payment updated successfully",
            **result,
        }
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando pago {pago_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/pagos/preview", dependencies=[Depends(require_feature("pagos"))])
async def api_pago_preview(
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:write")),
    _=Depends(require_gestion_access),
):
    """Generate PDF receipt preview (stateless)."""
    try:
        body = await request.json()

        from types import SimpleNamespace

        # Mock objects for PDFGenerator
        u_data = body.get("usuario", {})
        usuario = SimpleNamespace(
            id=u_data.get("id", 0),
            nombre=u_data.get("nombre", "Vista Previa"),
            dni=u_data.get("dni", ""),
            tipo_cuota=u_data.get("tipo_cuota", ""),
            email=u_data.get("email", ""),
            telefono=u_data.get("telefono", ""),
            # Add other fields if needed by generator access
            estado="activo",
            fecha_alta=None,
        )

        p_data = body.get("pago", {})
        now_local = _now_local_naive()
        pago = SimpleNamespace(
            id=0,
            usuario_id=usuario.id,
            monto=float(p_data.get("monto", 0)),
            fecha_pago=now_local,
            mes=int(p_data.get("mes", now_local.month)),
            año=int(p_data.get("anio", now_local.year)),
            metodo_pago_id=p_data.get("metodo_pago_id"),
            metodo_pago_nombre=p_data.get("metodo_pago_nombre"),
        )

        detalles_override = body.get("detalles", [])
        totales = body.get("totales", {})
        branding = body.get("branding", {})

        try:
            from apps.core.pdf_generator import PDFGenerator
        except ImportError:
            from src.pdf_generator import PDFGenerator

        pdfg = PDFGenerator(branding_config=branding)

        filepath = pdfg.generar_recibo(
            pago=pago,
            usuario=usuario,
            numero_comprobante="PREVIEW",
            detalles_override=detalles_override,
            totales=totales,
            observaciones=body.get("observaciones"),
            emitido_por=body.get("emitido_por"),
            titulo="VISTA PREVIA",
            metodo_pago=pago.metodo_pago_nombre,
            mostrar_logo=body.get("mostrar_logo", True),
            mostrar_metodo=body.get("mostrar_metodo", True),
            mostrar_dni=body.get("mostrar_dni", True),
            tipo_cuota=body.get("tipo_cuota_override"),
            periodo=body.get("periodo_override"),
        )

        return FileResponse(
            filepath, media_type="application/pdf", filename="preview.pdf"
        )

    except Exception as e:
        logger.error(f"Error previewing receipt: {e}")
        import traceback

        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/pagos/{pago_id}/recibo/preview", dependencies=[Depends(require_feature("pagos"))])
async def api_pago_recibo_preview(
    pago_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:read")),
    svc: PaymentService = Depends(get_payment_service),
):
    try:
        pago = svc.obtener_pago(int(pago_id))
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        # Permission check: Admin/Profesor OR the Payment Owner
        role = str(request.session.get("role") or "").strip().lower()
        is_admin = role in (
            "dueño",
            "dueno",
            "owner",
            "admin",
            "administrador",
            "profesor",
        )

        current_user_id = request.session.get("user_id")

        if not is_admin:
            # check if owner
            if not current_user_id:
                raise HTTPException(status_code=401, detail="Unauthorized")
            if int(current_user_id) != int(pago.usuario_id):
                raise HTTPException(status_code=403, detail="Forbidden")

        usuario = svc.obtener_usuario_por_id(int(pago.usuario_id))
        if not usuario:
            raise HTTPException(
                status_code=404, detail="Usuario del pago no encontrado"
            )

        try:
            detalles = svc.obtener_detalles_pago(int(pago_id))
        except Exception:
            detalles = []

        subtotal = 0.0
        try:
            subtotal = (
                sum(float(d.subtotal or 0.0) for d in (detalles or []))
                if detalles
                else float(pago.monto or 0.0)
            )
        except Exception:
            subtotal = float(pago.monto or 0.0)

        try:
            totales = svc.calcular_total_con_comision(subtotal, pago.metodo_pago_id)
        except Exception:
            totales = {"subtotal": subtotal, "comision": 0.0, "total": subtotal}

        metodo_nombre = None
        try:
            if pago.metodo_pago_id:
                m = svc.obtener_metodo_pago(int(pago.metodo_pago_id))
                metodo_nombre = getattr(m, "nombre", None) if m else None
        except Exception:
            metodo_nombre = None

        qp = request.query_params

        def _qp_bool(val, default: bool) -> bool:
            try:
                if val is None:
                    return default
                s = str(val).strip().lower()
            except Exception:
                return default
            if s in ("1", "true", "yes", "on"):
                return True
            if s in ("0", "false", "no", "off"):
                return False
            return default

        mostrar_logo = _qp_bool(qp.get("mostrar_logo"), True)
        mostrar_metodo = _qp_bool(qp.get("mostrar_metodo"), True)
        mostrar_dni = _qp_bool(qp.get("mostrar_dni"), True)

        gym_nombre = None
        gym_direccion = None
        gym_logo_url = None
        try:
            from src.services.gym_config_service import GymConfigService

            cfg = GymConfigService(svc.db).obtener_configuracion_gimnasio() or {}
            gym_nombre = cfg.get("gym_name") or cfg.get("nombre")
            gym_direccion = cfg.get("gym_address") or cfg.get("direccion")
            gym_logo_url = cfg.get("logo_url") or cfg.get("gym_logo_url")
        except Exception:
            gym_nombre = None
            gym_direccion = None
            gym_logo_url = None

        try:
            if (
                gym_logo_url
                and not str(gym_logo_url).startswith("http")
                and not str(gym_logo_url).startswith("/")
            ):
                from src.services.b2_storage import get_file_url

                gym_logo_url = get_file_url(str(gym_logo_url))
        except Exception:
            pass

        if not gym_logo_url:
            try:
                from src.utils import _resolve_logo_url

                gym_logo_url = _resolve_logo_url()
            except Exception:
                gym_logo_url = None

        if not gym_nombre:
            try:
                from src.utils import get_gym_name

                gym_nombre = get_gym_name("Gimnasio")
            except Exception:
                gym_nombre = "Gimnasio"

        numero = None
        try:
            comp_existing = svc.obtener_comprobante_por_pago(int(pago_id))
            if comp_existing:
                numero = comp_existing.get("numero_comprobante")
        except Exception:
            numero = None

        if not numero:
            try:
                numero = svc.get_next_receipt_number()
            except Exception:
                numero = None

        emitido_por = None
        try:
            prof_uid = request.session.get("gestion_profesor_user_id")
            prof_id = request.session.get("gestion_profesor_id")
            emitido_por = svc.obtener_profesor_nombre(
                profesor_user_id=int(prof_uid) if prof_uid else None,
                profesor_id=int(prof_id) if prof_id else None,
            )
        except Exception:
            emitido_por = None

        fecha_disp = None
        try:
            dt = getattr(pago, "fecha_pago", None)
            if dt:
                try:
                    fecha_disp = dt.strftime("%d/%m/%Y")
                except Exception:
                    fecha_disp = str(dt)
        except Exception:
            fecha_disp = None
        if not fecha_disp:
            try:
                fecha_disp = _now_local_naive().strftime("%d/%m/%Y")
            except Exception:
                fecha_disp = ""

        items = []
        for d in detalles or []:
            try:
                items.append(
                    {
                        "descripcion": getattr(d, "descripcion", None) or "Pago",
                        "cantidad": float(getattr(d, "cantidad", 1) or 1),
                        "precio": float(getattr(d, "precio_unitario", 0.0) or 0.0),
                    }
                )
            except Exception:
                continue

        if not items:
            try:
                items = [
                    {
                        "descripcion": "Pago",
                        "cantidad": 1,
                        "precio": float(pago.monto or 0.0),
                    }
                ]
            except Exception:
                items = [{"descripcion": "Pago", "cantidad": 1, "precio": 0.0}]

        observaciones = None
        try:
            observaciones = getattr(pago, "notas", None)
        except Exception:
            observaciones = None

        return {
            "numero": numero,
            "titulo": "RECIBO",
            "fecha": fecha_disp,
            "gym_nombre": gym_nombre,
            "gym_direccion": gym_direccion,
            "logo_url": gym_logo_url,
            "usuario_nombre": getattr(usuario, "nombre", None) or "Usuario",
            "usuario_dni": getattr(usuario, "dni", None),
            "metodo_pago": metodo_nombre,
            "items": items,
            "subtotal": float(totales.get("subtotal", subtotal) or 0.0),
            "total": float(totales.get("total", subtotal) or 0.0),
            "observaciones": observaciones,
            "emitido_por": emitido_por,
            "mostrar_logo": bool(mostrar_logo),
            "mostrar_metodo": bool(mostrar_metodo),
            "mostrar_dni": bool(mostrar_dni),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating recibo preview: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/pagos/{pago_id}/recibo/pdf", dependencies=[Depends(require_feature("pagos"))])
async def api_pago_recibo_pdf_alias(
    pago_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:read")),
    svc: PaymentService = Depends(get_payment_service),
):
    try:
        pago = svc.obtener_pago(int(pago_id))
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        role = str(request.session.get("role") or "").strip().lower()
        is_admin = role in (
            "dueño",
            "dueno",
            "owner",
            "admin",
            "administrador",
            "profesor",
        )
        current_user_id = request.session.get("user_id")
        if not is_admin:
            if not current_user_id:
                raise HTTPException(status_code=401, detail="Unauthorized")
            if int(current_user_id) != int(pago.usuario_id):
                raise HTTPException(status_code=403, detail="Forbidden")

        pdf_url = (
            _get_public_base_url(request) + f"/api/pagos/{int(pago_id)}/recibo.pdf"
        )
        return {"pdf_url": pdf_url}
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/pagos/{pago_id}/recibo.pdf", dependencies=[Depends(require_feature("pagos"))])
async def api_pago_recibo_pdf(
    pago_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:read")),
    svc: PaymentService = Depends(get_payment_service),
):
    """Generate PDF receipt for a payment using SQLAlchemy."""
    try:
        pago = svc.obtener_pago(int(pago_id))
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")

        role = str(request.session.get("role") or "").strip().lower()
        is_admin = role in (
            "dueño",
            "dueno",
            "owner",
            "admin",
            "administrador",
            "profesor",
        )
        current_user_id = request.session.get("user_id")
        if not is_admin:
            if not current_user_id:
                raise HTTPException(status_code=401, detail="Unauthorized")
            if int(current_user_id) != int(pago.usuario_id):
                raise HTTPException(status_code=403, detail="Forbidden")

        usuario = svc.obtener_usuario_por_id(int(pago.usuario_id))
        if not usuario:
            raise HTTPException(
                status_code=404, detail="Usuario del pago no encontrado"
            )

        try:
            detalles = svc.obtener_detalles_pago(int(pago_id))
        except Exception:
            detalles = []
        subtotal = 0.0
        try:
            subtotal = (
                sum(float(d.subtotal or 0.0) for d in (detalles or []))
                if detalles
                else float(pago.monto or 0.0)
            )
        except Exception:
            subtotal = float(pago.monto or 0.0)
        metodo_id = pago.metodo_pago_id
        try:
            totales = svc.calcular_total_con_comision(subtotal, metodo_id)
        except Exception:
            totales = {"subtotal": subtotal, "comision": 0.0, "total": subtotal}

        qp = request.query_params
        preview_mode = False
        try:
            qpv = qp.get("preview")
            preview_mode = (
                True if (qpv and str(qpv).lower() in ("1", "true", "yes")) else False
            )
        except Exception:
            preview_mode = False
        numero_override = None
        try:
            nraw = qp.get("numero")
            numero_override = (
                (str(nraw).strip() or None) if (nraw is not None) else None
            )
        except Exception:
            numero_override = None

        obs_text = None
        try:
            oraw = qp.get("observaciones")
            obs_text = (str(oraw).strip() or None) if (oraw is not None) else None
        except Exception:
            obs_text = None
        emitido_por = None
        try:
            eraw = qp.get("emitido_por")
            emitido_por = (str(eraw).strip() or None) if (eraw is not None) else None
        except Exception:
            emitido_por = None
        try:
            if not emitido_por:
                prof_uid = request.session.get("gestion_profesor_user_id")
                prof_id = request.session.get("gestion_profesor_id")
                emitido_por = svc.obtener_profesor_nombre(
                    profesor_user_id=int(prof_uid) if prof_uid else None,
                    profesor_id=int(prof_id) if prof_id else None,
                )
        except Exception:
            pass

        def _qp_bool(val):
            try:
                s = str(val).strip().lower()
            except Exception:
                return None
            if s in ("1", "true", "yes", "on"):
                return True
            if s in ("0", "false", "no", "off"):
                return False
            return None

        titulo = None
        try:
            titulo = (
                (str(qp.get("titulo")).strip() or None)
                if (qp.get("titulo") is not None)
                else None
            )
        except Exception:
            titulo = None
        gym_name_override = None
        gym_address_override = None
        try:
            gym_name_override = (
                (str(qp.get("gym_name")).strip() or None)
                if (qp.get("gym_name") is not None)
                else None
            )
        except Exception:
            gym_name_override = None
        try:
            gym_address_override = (
                (str(qp.get("gym_address")).strip() or None)
                if (qp.get("gym_address") is not None)
                else None
            )
        except Exception:
            gym_address_override = None

        fecha_emision_disp = None
        try:
            fraw = qp.get("fecha")
            if fraw is not None:
                s = str(fraw).strip()
                try:
                    if "/" in s:
                        dt = datetime.strptime(s, "%d/%m/%Y")
                    else:
                        dt = datetime.strptime(s, "%Y-%m-%d")
                    fecha_emision_disp = dt.strftime("%d/%m/%Y")
                except Exception:
                    fecha_emision_disp = s or None
        except Exception:
            fecha_emision_disp = None

        metodo_override = None
        try:
            metodo_override = (
                (str(qp.get("metodo")).strip() or None)
                if (qp.get("metodo") is not None)
                else None
            )
        except Exception:
            metodo_override = None

        tipo_cuota_override = None
        try:
            tipo_cuota_override = (
                (str(qp.get("tipo_cuota")).strip() or None)
                if (qp.get("tipo_cuota") is not None)
                else None
            )
        except Exception:
            tipo_cuota_override = None
        periodo_override = None
        try:
            periodo_override = (
                (str(qp.get("periodo")).strip() or None)
                if (qp.get("periodo") is not None)
                else None
            )
        except Exception:
            periodo_override = None

        usuario_nombre_override = None
        usuario_dni_override = None
        try:
            usuario_nombre_override = (
                (str(qp.get("usuario_nombre")).strip() or None)
                if (qp.get("usuario_nombre") is not None)
                else None
            )
        except Exception:
            usuario_nombre_override = None
        try:
            usuario_dni_override = (
                (str(qp.get("usuario_dni")).strip() or None)
                if (qp.get("usuario_dni") is not None)
                else None
            )
        except Exception:
            usuario_dni_override = None

        mostrar_logo = _qp_bool(qp.get("mostrar_logo"))
        mostrar_metodo = _qp_bool(qp.get("mostrar_metodo"))
        mostrar_dni = _qp_bool(qp.get("mostrar_dni"))

        detalles_override = None
        try:
            iraw = qp.get("items")
            if iraw is not None:
                obj = json.loads(str(iraw))
                if isinstance(obj, list):
                    detalles_override = obj
        except Exception:
            detalles_override = None

        try:
            sub_o = qp.get("subtotal")
            com_o = qp.get("comision")
            tot_o = qp.get("total")
            if sub_o is not None or com_o is not None or tot_o is not None:
                s = (
                    float(sub_o)
                    if (sub_o is not None and str(sub_o).strip() != "")
                    else float(totales.get("subtotal", 0.0))
                )
                c = (
                    float(com_o)
                    if (com_o is not None and str(com_o).strip() != "")
                    else float(totales.get("comision", 0.0))
                )
                t = (
                    float(tot_o)
                    if (tot_o is not None and str(tot_o).strip() != "")
                    else float(totales.get("total", s + c))
                )
                totales = {"subtotal": s, "comision": c, "total": t}
        except Exception:
            pass

        numero_comprobante = None
        comprobante_id = None
        try:
            comp_existing = svc.obtener_comprobante_por_pago(int(pago_id))
            if comp_existing:
                comprobante_id = comp_existing.get("id")
                numero_comprobante = comp_existing.get("numero_comprobante")
        except Exception:
            numero_comprobante = None

        if preview_mode:
            if numero_override:
                numero_comprobante = numero_override
        else:
            try:
                if not numero_comprobante:
                    comprobante_id = svc.crear_comprobante(
                        tipo_comprobante="recibo",
                        pago_id=int(pago_id),
                        usuario_id=int(pago.usuario_id),
                        monto_total=float(pago.monto or 0.0),
                        emitido_por=emitido_por,
                    )
                    if comprobante_id:
                        comp = svc.obtener_comprobante(int(comprobante_id))
                        if comp:
                            numero_comprobante = comp.get("numero_comprobante")
                if numero_override:
                    numero_comprobante = numero_override
            except Exception:
                numero_comprobante = None

        try:
            from apps.core.pdf_generator import PDFGenerator
        except ImportError:
            # If apps.core is not in path directly, assume it is available via sys.path from dependencies
            from src.pdf_generator import PDFGenerator

        logo_url = None
        gym_name_cfg = None
        gym_addr_cfg = None
        try:
            from src.services.gym_config_service import GymConfigService

            cfg = GymConfigService(svc.db).obtener_configuracion_gimnasio() or {}
            logo_url = cfg.get("logo_url") or cfg.get("gym_logo_url")
            gym_name_cfg = cfg.get("gym_name") or cfg.get("nombre")
            gym_addr_cfg = cfg.get("gym_address") or cfg.get("direccion")
        except Exception:
            logo_url = None
            gym_name_cfg = None
            gym_addr_cfg = None

        sucursal_nombre = None
        sucursal_codigo = None
        sucursal_direccion = None
        try:
            if getattr(pago, "sucursal_id", None) is not None:
                row = svc.db.execute(
                    text(
                        "SELECT nombre, codigo, direccion FROM sucursales WHERE id = :id LIMIT 1"
                    ),
                    {"id": int(pago.sucursal_id)},
                ).fetchone()
                if row:
                    sucursal_nombre = str(row[0] or "") if row[0] is not None else None
                    sucursal_codigo = str(row[1] or "") if row[1] is not None else None
                    sucursal_direccion = str(row[2] or "") if row[2] is not None else None
        except Exception:
            sucursal_nombre = None
            sucursal_codigo = None
            sucursal_direccion = None
        if not logo_url:
            try:
                from src.utils import _resolve_logo_url

                logo_url = _resolve_logo_url()
            except Exception:
                logo_url = None

        try:
            if (
                logo_url
                and not str(logo_url).startswith("http")
                and not str(logo_url).startswith("/")
            ):
                from src.services.b2_storage import get_file_url

                logo_url = get_file_url(str(logo_url))
        except Exception:
            pass

        branding_cfg = {
            "gym_name": gym_name_cfg,
            "gym_address": gym_addr_cfg,
            "logo_url": logo_url,
        }
        if not gym_name_override:
            try:
                if sucursal_nombre and gym_name_cfg:
                    gym_name_override = f"{gym_name_cfg} - {sucursal_nombre}"
                elif sucursal_nombre:
                    gym_name_override = str(sucursal_nombre)
            except Exception:
                pass
        if not gym_address_override:
            try:
                base_addr = sucursal_direccion or gym_addr_cfg
                if base_addr and sucursal_codigo:
                    gym_address_override = f"{base_addr} ({sucursal_codigo})"
                else:
                    gym_address_override = base_addr
            except Exception:
                pass
        pdfg = PDFGenerator(branding_config=branding_cfg)
        filepath = pdfg.generar_recibo(
            pago,
            usuario,
            numero_comprobante,
            detalles=detalles,
            totales=totales,
            observaciones=obs_text,
            emitido_por=emitido_por,
            titulo=titulo,
            gym_name=gym_name_override,
            gym_address=gym_address_override,
            fecha_emision=fecha_emision_disp,
            metodo_pago=metodo_override,
            usuario_nombre=usuario_nombre_override,
            usuario_dni=usuario_dni_override,
            detalles_override=detalles_override,
            mostrar_logo=mostrar_logo,
            mostrar_metodo=mostrar_metodo,
            mostrar_dni=mostrar_dni,
            tipo_cuota=tipo_cuota_override,
            periodo=periodo_override,
        )

        try:
            if comprobante_id is not None and filepath:
                svc.actualizar_comprobante_pdf(int(comprobante_id), str(filepath))
        except Exception:
            pass

        filename = os.path.basename(filepath)
        resp = FileResponse(filepath, media_type="application/pdf")
        try:
            resp.headers["Content-Disposition"] = f'inline; filename="{filename}"'
        except Exception:
            pass
        return resp
    except HTTPException:
        raise
    except Exception as e:
        import traceback

        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/recibos/numero-proximo")
async def api_recibos_numero_proximo(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get next receipt number using SQLAlchemy."""
    try:
        numero = svc.get_next_receipt_number()
        return {"numero": str(numero)}
    except Exception as e:
        logger.error(f"Error obteniendo numero proximo: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/recibos/config")
async def api_recibos_config_get(
    _scope=Depends(require_scope_gestion("configuracion:read")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get receipt numbering configuration using SQLAlchemy."""
    try:
        cfg = svc.get_receipt_numbering_config()
        return cfg
    except Exception as e:
        logger.error(f"Error obteniendo config: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/recibos/config")
async def api_recibos_config_put(
    request: Request,
    _scope=Depends(require_scope_gestion("configuracion:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update receipt numbering configuration using SQLAlchemy."""
    try:
        payload = await request.json()
        ok = svc.save_receipt_numbering_config(payload)
        if ok:
            return {"ok": True}
        return JSONResponse(
            {"error": "No se pudo guardar la configuración"}, status_code=400
        )
    except Exception as e:
        logger.error(f"Error guardando config: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/api/pagos",
    dependencies=[Depends(require_feature("pagos")), Depends(require_feature("pagos:create"))],
)
async def api_pagos_create(
    request: Request,
    background_tasks: BackgroundTasks,
    _scope=Depends(require_scope_gestion("pagos:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service),
    sucursal_id: int = Depends(require_sucursal_selected),
):
    """Create a payment using SQLAlchemy - supports both simple and multi-concept."""
    payload = await request.json()
    try:
        usuario_id_raw = payload.get("usuario_id")
        monto_raw = payload.get("monto")
        mes_raw = payload.get("mes")
        año_raw = payload.get("año")
        metodo_pago_id = payload.get("metodo_pago_id")
        conceptos_raw = payload.get("conceptos")
        if not isinstance(conceptos_raw, list) or len(conceptos_raw) == 0:
            alt = payload.get("conceptos_raw")
            if isinstance(alt, list):
                conceptos_raw = alt
            else:
                conceptos_raw = []
        fecha_pago_raw = payload.get("fecha_pago")

        if usuario_id_raw is None:
            raise HTTPException(status_code=400, detail="'usuario_id' es obligatorio")
        try:
            usuario_id = int(usuario_id_raw)
            metodo_pago_id_int = (
                int(metodo_pago_id) if metodo_pago_id is not None else None
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Tipos inválidos en payload")

        idempotency_key = ""
        try:
            idempotency_key = (
                str(request.headers.get("Idempotency-Key") or "").strip()
                or str(payload.get("idempotency_key") or "").strip()
            )
        except Exception:
            idempotency_key = ""
        if idempotency_key:
            try:
                existing_pid = svc.db.execute(
                    text(
                        "SELECT pago_id FROM pagos_idempotency WHERE key = :k LIMIT 1"
                    ),
                    {"k": idempotency_key},
                ).scalar()
                if existing_pid:
                    return {
                        "ok": True,
                        "id": int(existing_pid),
                        "idempotent": True,
                    }
            except Exception:
                pass

        was_active_before = None
        try:
            u = svc.db.get(Usuario, int(usuario_id))
            was_active_before = bool(getattr(u, "activo", False)) if u else None
        except Exception:
            was_active_before = None

        # Multi-concept payment
        if isinstance(conceptos_raw, list) and len(conceptos_raw) > 0:
            conceptos: list[dict] = []
            for c in conceptos_raw:
                cid_raw = c.get("concepto_id")
                cid_val = None
                try:
                    if cid_raw is not None and str(cid_raw).strip() != "":
                        cid_val = int(cid_raw)
                except Exception:
                    cid_val = None
                descripcion = c.get("descripcion")
                try:
                    cantidad = int(c.get("cantidad") or 1)
                    precio_unitario = float(c.get("precio_unitario") or 0.0)
                except Exception:
                    raise HTTPException(
                        status_code=400, detail="Conceptos inválidos en payload"
                    )
                if cantidad <= 0 or precio_unitario < 0:
                    raise HTTPException(
                        status_code=400, detail="Cantidad/precio inválidos en conceptos"
                    )
                if cid_val is None and (
                    not descripcion or str(descripcion).strip() == ""
                ):
                    raise HTTPException(
                        status_code=400,
                        detail="Cada ítem debe tener 'concepto_id' o 'descripcion'",
                    )
                conceptos.append(
                    {
                        "concepto_id": cid_val,
                        "descripcion": descripcion,
                        "cantidad": cantidad,
                        "precio_unitario": precio_unitario,
                    }
                )

            fecha_dt = None
            try:
                if fecha_pago_raw:
                    fecha_dt = datetime.fromisoformat(str(fecha_pago_raw))
                elif mes_raw is not None and año_raw is not None:
                    mes_i = int(mes_raw)
                    año_i = int(año_raw)
                    fecha_dt = datetime(int(año_i), int(mes_i), 1)
            except Exception:
                raise HTTPException(status_code=400, detail="fecha_pago inválida")

            try:
                tipo_cuota_id_int = None
                try:
                    tci_raw = payload.get("tipo_cuota_id")
                    if tci_raw is not None and str(tci_raw).strip() != "":
                        tipo_cuota_id_int = int(tci_raw)
                except Exception:
                    tipo_cuota_id_int = None
                pago_id = svc.registrar_pago_avanzado(
                    usuario_id=usuario_id,
                    metodo_pago_id=metodo_pago_id_int,
                    conceptos=conceptos,
                    fecha_pago=fecha_dt,
                    sucursal_id=int(sucursal_id),
                    tipo_cuota_id=tipo_cuota_id_int,
                    idempotency_key=idempotency_key or None,
                )
            except PermissionError as pe:
                raise HTTPException(status_code=403, detail=str(pe))
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            try:
                total = sum(
                    float(x.get("cantidad") or 0) * float(x.get("precio_unitario") or 0)
                    for x in conceptos
                )
                dt = fecha_dt or datetime.now()
                mes_env = int(dt.month)
                anio_env = int(dt.year)
                if background_tasks is not None:
                    background_tasks.add_task(
                        wa.send_payment_confirmation,
                        int(usuario_id),
                        float(total),
                        mes_env,
                        anio_env,
                        int(sucursal_id),
                        f"payment:{int(pago_id)}",
                    )
                    if was_active_before is False:
                        background_tasks.add_task(
                            wa.send_membership_reactivated,
                            int(usuario_id),
                            int(sucursal_id),
                        )
                else:
                    wa.send_payment_confirmation(
                        int(usuario_id),
                        float(total),
                        mes_env,
                        anio_env,
                        int(sucursal_id),
                        f"payment:{int(pago_id)}",
                    )
                    if was_active_before is False:
                        wa.send_membership_reactivated(
                            int(usuario_id), int(sucursal_id)
                        )
            except Exception:
                pass
            return {"ok": True, "id": int(pago_id)}

        # Simple payment
        if monto_raw is None or mes_raw is None or año_raw is None:
            raise HTTPException(
                status_code=400,
                detail="'monto', 'mes' y 'año' son obligatorios cuando no hay 'conceptos'",
            )
        try:
            monto = float(monto_raw)
            mes = int(mes_raw)
            año = int(año_raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Tipos inválidos en payload")
        if not (1 <= mes <= 12):
            raise HTTPException(status_code=400, detail="'mes' debe estar entre 1 y 12")
        if monto <= 0:
            raise HTTPException(status_code=400, detail="'monto' debe ser mayor a 0")

        try:
            tipo_cuota_id_int = None
            try:
                tci_raw = payload.get("tipo_cuota_id")
                if tci_raw is not None and str(tci_raw).strip() != "":
                    tipo_cuota_id_int = int(tci_raw)
            except Exception:
                tipo_cuota_id_int = None
            pago_id = svc.registrar_pago(
                usuario_id,
                monto,
                mes,
                año,
                metodo_pago_id_int,
                sucursal_id=int(sucursal_id),
                tipo_cuota_id=tipo_cuota_id_int,
                idempotency_key=idempotency_key or None,
            )
        except PermissionError as pe:
            raise HTTPException(status_code=403, detail=str(pe))
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

        try:
            if background_tasks is not None:
                background_tasks.add_task(
                    wa.send_payment_confirmation,
                    int(usuario_id),
                    float(monto),
                    int(mes),
                    int(año),
                    int(sucursal_id),
                    f"payment:{int(pago_id)}",
                )
                if was_active_before is False:
                    background_tasks.add_task(
                        wa.send_membership_reactivated,
                        int(usuario_id),
                        int(sucursal_id),
                    )
            else:
                wa.send_payment_confirmation(
                    int(usuario_id),
                    float(monto),
                    int(mes),
                    int(año),
                    int(sucursal_id),
                    f"payment:{int(pago_id)}",
                )
                if was_active_before is False:
                    wa.send_membership_reactivated(
                        int(usuario_id), int(sucursal_id)
                    )
        except Exception:
            pass

        return {"ok": True, "id": int(pago_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/pagos/{pago_id}/update_raw", dependencies=[Depends(require_feature("pagos"))])
async def api_pagos_update(
    pago_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Update a payment using SQLAlchemy - supports both simple and multi-concept."""
    payload = await request.json()
    try:
        usuario_id_raw = payload.get("usuario_id")
        monto_raw = payload.get("monto")
        fecha_raw = payload.get("fecha_pago")
        mes_raw = payload.get("mes")
        año_raw = payload.get("año")
        metodo_pago_id = payload.get("metodo_pago_id")
        conceptos_raw = payload.get("conceptos")

        advanced_conceptos = isinstance(conceptos_raw, list) and len(conceptos_raw) > 0
        if usuario_id_raw is None or (monto_raw is None and not advanced_conceptos):
            raise HTTPException(
                status_code=400,
                detail="'usuario_id' es obligatorio y 'monto' cuando no hay 'conceptos'",
            )
        try:
            usuario_id = int(usuario_id_raw)
            monto = float(monto_raw) if monto_raw is not None else None
            metodo_pago_id_int = (
                int(metodo_pago_id) if metodo_pago_id is not None else None
            )
        except Exception:
            raise HTTPException(status_code=400, detail="Tipos inválidos en payload")

        # Parse date
        fecha_dt = None
        if fecha_raw is not None:
            try:
                if isinstance(fecha_raw, str):
                    fecha_dt = datetime.fromisoformat(fecha_raw)
                else:
                    raise ValueError("fecha_pago debe ser string ISO")
            except Exception:
                raise HTTPException(
                    status_code=400,
                    detail="'fecha_pago' inválida, use ISO 8601 (YYYY-MM-DD)",
                )
        else:
            if mes_raw is not None and año_raw is not None:
                try:
                    mes = int(mes_raw)
                    año = int(año_raw)
                    if not (1 <= mes <= 12):
                        raise HTTPException(
                            status_code=400, detail="'mes' debe estar entre 1 y 12"
                        )
                    fecha_dt = datetime(año, mes, 1)
                except HTTPException:
                    raise
                except Exception:
                    raise HTTPException(status_code=400, detail="'mes'/'año' inválidos")
            else:
                try:
                    existing = svc.obtener_pago(pago_id)
                    if existing and getattr(existing, "fecha_pago", None):
                        fecha_dt = (
                            existing.fecha_pago
                            if not isinstance(existing.fecha_pago, str)
                            else datetime.fromisoformat(existing.fecha_pago)
                        )
                    else:
                        fecha_dt = _now_local_naive()
                except Exception:
                    fecha_dt = _now_local_naive()

        if mes_raw is not None and año_raw is not None:
            try:
                mes = int(mes_raw)
                año = int(año_raw)
            except Exception:
                mes = fecha_dt.month
                año = fecha_dt.year
        else:
            mes = fecha_dt.month
            año = fecha_dt.year

        # Multi-concept update
        if advanced_conceptos:
            conceptos: list[dict] = []
            try:
                for c in conceptos_raw:
                    cid_raw = c.get("concepto_id")
                    try:
                        cid_val = int(cid_raw) if cid_raw is not None else None
                    except Exception:
                        cid_val = None
                    descripcion = c.get("descripcion")
                    try:
                        cantidad = int(c.get("cantidad") or 1)
                        precio_unitario = float(c.get("precio_unitario") or 0.0)
                    except Exception:
                        raise HTTPException(
                            status_code=400, detail="Conceptos inválidos en payload"
                        )
                    if cantidad <= 0 or precio_unitario < 0:
                        raise HTTPException(
                            status_code=400,
                            detail="Cantidad/precio inválidos en conceptos",
                        )
                    if cid_val is None and (
                        not descripcion or str(descripcion).strip() == ""
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail="Cada ítem debe tener 'concepto_id' o 'descripcion'",
                        )
                    conceptos.append(
                        {
                            "concepto_id": cid_val,
                            "descripcion": descripcion,
                            "cantidad": cantidad,
                            "precio_unitario": precio_unitario,
                        }
                    )
            except HTTPException:
                raise
            except Exception:
                raise HTTPException(status_code=400, detail="'conceptos' inválidos")

            try:
                svc.modificar_pago_avanzado(
                    int(pago_id), usuario_id, metodo_pago_id_int, conceptos, fecha_dt
                )
            except ValueError as ve:
                raise HTTPException(status_code=400, detail=str(ve))
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))
            return {"ok": True, "id": int(pago_id)}

        # Simple update
        if monto is None or float(monto) <= 0:
            raise HTTPException(status_code=400, detail="'monto' debe ser mayor a 0")

        data = {
            "usuario_id": usuario_id,
            "monto": float(monto),
            "mes": mes,
            "año": año,
            "fecha_pago": fecha_dt,
            "metodo_pago_id": metodo_pago_id_int,
        }
        try:
            svc.modificar_pago(int(pago_id), data)
        except ValueError as ve:
            raise HTTPException(status_code=400, detail=str(ve))
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        return {"ok": True, "id": int(pago_id)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/api/pagos/{pago_id}",
    dependencies=[Depends(require_feature("pagos")), Depends(require_feature("pagos:delete"))],
)
async def api_pagos_delete(
    pago_id: int,
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:write")),
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
    audit_service: AuditService = Depends(get_audit_service),
):
    """Delete a payment using SQLAlchemy."""
    try:
        # Get payment info before deletion for audit log
        pago_before = svc.obtener_pago(int(pago_id))
        old_values = None
        if pago_before:
            old_values = {
                "id": pago_before.id,
                "usuario_id": pago_before.usuario_id,
                "monto": float(pago_before.monto or 0),
                "fecha_pago": str(pago_before.fecha_pago)
                if pago_before.fecha_pago
                else None,
                "metodo_pago_id": pago_before.metodo_pago_id,
            }

        svc.eliminar_pago(int(pago_id))

        # Log the deletion
        audit_service.log_from_request(
            request=request,
            action=AuditService.ACTION_PAYMENT_DELETE,
            table_name="pagos",
            record_id=pago_id,
            old_values=old_values,
        )

        return {"ok": True}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Error eliminando pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/usuario_pagos")
async def api_usuario_pagos(
    request: Request,
    _=Depends(require_gestion_access),
    svc: PaymentService = Depends(get_payment_service),
):
    """Get user payments list with search and pagination using SQLAlchemy."""
    try:
        usuario_id = request.query_params.get("usuario_id")
        q = request.query_params.get("q")
        limit = request.query_params.get("limit")
        offset = request.query_params.get("offset")

        if not usuario_id:
            return []

        lim = int(limit) if limit and limit.isdigit() else 50
        off = int(offset) if offset and offset.isdigit() else 0

        # Get payments for user
        pagos = svc.obtener_historial_pagos(int(usuario_id), limit=lim + off)

        # Apply offset
        pagos = pagos[off : off + lim]

        # Get user for tipo_cuota
        usuario = svc.obtener_usuario_por_id(int(usuario_id))
        tipo_cuota = usuario.tipo_cuota if usuario else ""

        # Filter by search query if provided
        rows = []
        for p in pagos:
            if q:
                if not (q.lower() in (tipo_cuota or "").lower()):
                    continue
            rows.append(
                {
                    "fecha": p.fecha_pago.date().isoformat() if p.fecha_pago else None,
                    "monto": float(p.monto or 0),
                    "tipo_cuota": tipo_cuota or "",
                }
            )
        return rows
    except Exception as e:
        logger.error(f"Error obteniendo usuario_pagos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/pagos/recalcular-estado", dependencies=[Depends(require_feature("pagos"))])
async def api_pagos_recalcular_estado(
    request: Request,
    _scope=Depends(require_scope_gestion("pagos:write")),
    _=Depends(require_owner),
    svc: PaymentService = Depends(get_payment_service),
):
    try:
        try:
            payload = await request.json()
        except Exception:
            payload = {}

        usuario_id = payload.get("usuario_id")
        limit = payload.get("limit")
        modo = str(payload.get("mode") or "candidatos").strip().lower()

        try:
            lim = int(limit) if limit is not None else 300
        except Exception:
            lim = 300
        if lim <= 0:
            lim = 300

        if usuario_id is not None and str(usuario_id).strip() != "":
            try:
                uid = int(usuario_id)
            except Exception:
                raise HTTPException(status_code=400, detail="usuario_id inválido")
            res = svc._recalcular_estado_usuario(uid)
            return {"ok": True, "processed": 1, "result": res}

        hoy = svc._today_local_date()
        stmt = select(Usuario.id).where(Usuario.rol == "socio")
        if modo == "overdue_only":
            stmt = stmt.where(
                Usuario.activo == True,
                Usuario.fecha_proximo_vencimiento != None,
                Usuario.fecha_proximo_vencimiento < hoy,
            )
        else:
            stmt = stmt.where(
                Usuario.activo == True,
                or_(
                    Usuario.fecha_proximo_vencimiento == None,
                    Usuario.fecha_proximo_vencimiento < hoy,
                    Usuario.cuotas_vencidas == None,
                ),
            )

        ids = list(
            svc.db.execute(stmt.order_by(Usuario.id.asc()).limit(lim)).scalars().all()
        )
        processed = 0
        desactivados = 0
        for uid in ids:
            try:
                out = svc._recalcular_estado_usuario(int(uid))
                processed += 1
                if out.get("desactivado"):
                    desactivados += 1
            except Exception:
                continue

        return {
            "ok": True,
            "processed": processed,
            "desactivados": desactivados,
            "limit": lim,
            "mode": modo,
        }
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
