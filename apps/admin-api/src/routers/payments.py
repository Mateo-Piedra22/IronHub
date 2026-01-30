"""
IronHub Admin API - Payments Router
Restored functionality from deprecated/webapp/routers/payments.py

Includes:
- CRUD for Métodos de Pago
- CRUD for Tipos de Cuota (Subscription Plans)
- CRUD for Conceptos de Pago (Payment Concepts)
- Advanced payment registration with multiple concepts
- Payment statistics and reporting
"""

import logging
from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Payments"])


# ========== PYDANTIC MODELS ==========


class MetodoPagoCreate(BaseModel):
    nombre: str
    icono: Optional[str] = "💳"
    color: Optional[str] = "#3498db"
    comision: Optional[float] = 0.0
    activo: Optional[bool] = True
    descripcion: Optional[str] = None


class MetodoPagoUpdate(BaseModel):
    nombre: Optional[str] = None
    icono: Optional[str] = None
    color: Optional[str] = None
    comision: Optional[float] = None
    activo: Optional[bool] = None
    descripcion: Optional[str] = None


class TipoCuotaCreate(BaseModel):
    nombre: str
    precio: float = 0.0
    duracion_dias: int = 30
    activo: Optional[bool] = True
    descripcion: Optional[str] = None
    icono_path: Optional[str] = None


class TipoCuotaUpdate(BaseModel):
    nombre: Optional[str] = None
    precio: Optional[float] = None
    duracion_dias: Optional[int] = None
    activo: Optional[bool] = None
    descripcion: Optional[str] = None
    icono_path: Optional[str] = None


class ConceptoPagoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    precio_base: Optional[float] = 0.0
    tipo: Optional[str] = None
    activo: Optional[bool] = True


class ConceptoPagoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    precio_base: Optional[float] = None
    tipo: Optional[str] = None
    activo: Optional[bool] = None


class PagoConceptoItem(BaseModel):
    concepto_id: Optional[int] = None
    descripcion: Optional[str] = None
    cantidad: int = 1
    precio_unitario: float = 0.0


class PagoCreate(BaseModel):
    usuario_id: int
    monto: Optional[float] = None
    mes: Optional[int] = None
    año: Optional[int] = None
    metodo_pago_id: Optional[int] = None
    fecha_pago: Optional[str] = None
    conceptos: Optional[List[PagoConceptoItem]] = None


class PagoUpdate(BaseModel):
    usuario_id: Optional[int] = None
    monto: Optional[float] = None
    mes: Optional[int] = None
    año: Optional[int] = None
    metodo_pago_id: Optional[int] = None
    fecha_pago: Optional[str] = None
    conceptos: Optional[List[PagoConceptoItem]] = None


# ========== DEPENDENCY ==========


def get_db_session(request: Request):
    """Get database session from app state."""
    return getattr(request.app.state, "db_session", None)


def require_admin(request: Request):
    """Check admin authentication."""
    from src.main import require_admin as main_require_admin

    return main_require_admin(request)


def get_admin_service(request: Request):
    """Get admin service from main module."""
    from src.main import get_admin_service as main_get_service

    return main_get_service()


# ========== MÉTODOS DE PAGO ==========


@router.get("/metodos_pago")
async def list_metodos_pago(
    request: Request, activos: bool = Query(True, description="Solo métodos activos")
):
    """List all payment methods."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                if activos:
                    cur.execute("""
                        SELECT id, nombre, icono, color, comision, activo, descripcion, fecha_creacion
                        FROM metodos_pago
                        WHERE activo = TRUE
                        ORDER BY nombre
                    """)
                else:
                    cur.execute("""
                        SELECT id, nombre, icono, color, comision, activo, descripcion, fecha_creacion
                        FROM metodos_pago
                        ORDER BY activo DESC, nombre
                    """)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nombre": r[1],
                        "icono": r[2],
                        "color": r[3],
                        "comision": float(r[4]) if r[4] else 0.0,
                        "activo": r[5],
                        "descripcion": r[6],
                        "fecha_creacion": str(r[7]) if r[7] else None,
                    }
                    for r in rows
                ]
    except Exception as e:
        logger.error(f"Error listing metodos_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/metodos_pago")
async def create_metodo_pago(request: Request, data: MetodoPagoCreate):
    """Create a new payment method."""
    require_admin(request)
    adm = get_admin_service(request)

    if not data.nombre or not data.nombre.strip():
        raise HTTPException(status_code=400, detail="'nombre' es obligatorio")

    if data.comision is not None and (data.comision < 0 or data.comision > 100):
        raise HTTPException(
            status_code=400, detail="'comision' debe estar entre 0 y 100"
        )

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO metodos_pago (nombre, icono, color, comision, activo, descripcion)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        data.nombre.strip(),
                        data.icono or "💳",
                        data.color or "#3498db",
                        data.comision or 0.0,
                        data.activo if data.activo is not None else True,
                        data.descripcion,
                    ),
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                adm.log_action("owner", "create_metodo_pago", None, data.nombre)
                return {"ok": True, "id": new_id}
    except Exception as e:
        logger.error(f"Error creating metodo_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/metodos_pago/{metodo_id}")
async def update_metodo_pago(request: Request, metodo_id: int, data: MetodoPagoUpdate):
    """Update an existing payment method."""
    require_admin(request)
    adm = get_admin_service(request)

    if data.comision is not None and (data.comision < 0 or data.comision > 100):
        raise HTTPException(
            status_code=400, detail="'comision' debe estar entre 0 y 100"
        )

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check exists
                cur.execute("SELECT id FROM metodos_pago WHERE id = %s", (metodo_id,))
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Método de pago no encontrado"
                    )

                # Build dynamic update
                updates = []
                values = []
                if data.nombre is not None:
                    updates.append("nombre = %s")
                    values.append(data.nombre.strip())
                if data.icono is not None:
                    updates.append("icono = %s")
                    values.append(data.icono)
                if data.color is not None:
                    updates.append("color = %s")
                    values.append(data.color)
                if data.comision is not None:
                    updates.append("comision = %s")
                    values.append(data.comision)
                if data.activo is not None:
                    updates.append("activo = %s")
                    values.append(data.activo)
                if data.descripcion is not None:
                    updates.append("descripcion = %s")
                    values.append(data.descripcion)

                if not updates:
                    return {"ok": True, "id": metodo_id}

                values.append(metodo_id)
                cur.execute(
                    f"UPDATE metodos_pago SET {', '.join(updates)} WHERE id = %s",
                    values,
                )
                conn.commit()
                adm.log_action("owner", "update_metodo_pago", None, str(metodo_id))
                return {"ok": True, "id": metodo_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating metodo_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/metodos_pago/{metodo_id}")
async def delete_metodo_pago(request: Request, metodo_id: int):
    """Delete a payment method."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM metodos_pago WHERE id = %s RETURNING id", (metodo_id,)
                )
                deleted = cur.fetchone()
                if not deleted:
                    raise HTTPException(
                        status_code=404, detail="Método de pago no encontrado"
                    )
                conn.commit()
                adm.log_action("owner", "delete_metodo_pago", None, str(metodo_id))
                return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting metodo_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== TIPOS DE CUOTA (PLANES) ==========


@router.get("/tipos_cuota")
async def list_tipos_cuota(
    request: Request, activos: bool = Query(False, description="Solo tipos activos")
):
    """List all subscription types/plans."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                if activos:
                    cur.execute("""
                        SELECT id, nombre, precio, duracion_dias, activo, descripcion, icono_path
                        FROM tipos_cuota
                        WHERE activo = TRUE
                        ORDER BY precio, nombre
                    """)
                else:
                    cur.execute("""
                        SELECT id, nombre, precio, duracion_dias, activo, descripcion, icono_path
                        FROM tipos_cuota
                        ORDER BY activo DESC, precio, nombre
                    """)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nombre": r[1],
                        "precio": float(r[2]) if r[2] else 0.0,
                        "duracion_dias": r[3] or 30,
                        "activo": r[4],
                        "descripcion": r[5],
                        "icono_path": r[6],
                    }
                    for r in rows
                ]
    except Exception as e:
        logger.error(f"Error listing tipos_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/tipos_cuota/activos")
async def list_tipos_cuota_activos(request: Request):
    """List only active subscription types."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT id, nombre, precio, duracion_dias
                    FROM tipos_cuota
                    WHERE activo = TRUE
                    ORDER BY precio, nombre
                """)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nombre": r[1],
                        "precio": float(r[2]) if r[2] else 0.0,
                        "duracion_dias": r[3] or 30,
                    }
                    for r in rows
                ]
    except Exception as e:
        logger.error(f"Error listing tipos_cuota activos: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/tipos_cuota")
async def create_tipo_cuota(request: Request, data: TipoCuotaCreate):
    """Create a new subscription type/plan."""
    require_admin(request)
    adm = get_admin_service(request)

    if not data.nombre or not data.nombre.strip():
        raise HTTPException(status_code=400, detail="'nombre' es obligatorio")

    if data.precio is not None and data.precio < 0:
        raise HTTPException(status_code=400, detail="'precio' no puede ser negativo")

    if data.duracion_dias is not None and data.duracion_dias <= 0:
        raise HTTPException(
            status_code=400, detail="'duracion_dias' debe ser mayor a 0"
        )

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO tipos_cuota (nombre, precio, duracion_dias, activo, descripcion, icono_path)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        data.nombre.strip(),
                        data.precio or 0.0,
                        data.duracion_dias or 30,
                        data.activo if data.activo is not None else True,
                        data.descripcion,
                        data.icono_path,
                    ),
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                adm.log_action("owner", "create_tipo_cuota", None, data.nombre)
                return {"ok": True, "id": new_id}
    except Exception as e:
        logger.error(f"Error creating tipo_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/tipos_cuota/{tipo_id}")
async def update_tipo_cuota(request: Request, tipo_id: int, data: TipoCuotaUpdate):
    """Update an existing subscription type/plan."""
    require_admin(request)
    adm = get_admin_service(request)

    if data.precio is not None and data.precio < 0:
        raise HTTPException(status_code=400, detail="'precio' no puede ser negativo")

    if data.duracion_dias is not None and data.duracion_dias <= 0:
        raise HTTPException(
            status_code=400, detail="'duracion_dias' debe ser mayor a 0"
        )

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check exists
                cur.execute("SELECT id FROM tipos_cuota WHERE id = %s", (tipo_id,))
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Tipo de cuota no encontrado"
                    )

                # Build dynamic update
                updates = []
                values = []
                if data.nombre is not None:
                    updates.append("nombre = %s")
                    values.append(data.nombre.strip())
                if data.precio is not None:
                    updates.append("precio = %s")
                    values.append(data.precio)
                if data.duracion_dias is not None:
                    updates.append("duracion_dias = %s")
                    values.append(data.duracion_dias)
                if data.activo is not None:
                    updates.append("activo = %s")
                    values.append(data.activo)
                if data.descripcion is not None:
                    updates.append("descripcion = %s")
                    values.append(data.descripcion)
                if data.icono_path is not None:
                    updates.append("icono_path = %s")
                    values.append(data.icono_path)

                updates.append("fecha_modificacion = CURRENT_TIMESTAMP")

                if len(updates) <= 1:
                    return {"ok": True, "id": tipo_id}

                values.append(tipo_id)
                cur.execute(
                    f"UPDATE tipos_cuota SET {', '.join(updates)} WHERE id = %s", values
                )
                conn.commit()
                adm.log_action("owner", "update_tipo_cuota", None, str(tipo_id))
                return {"ok": True, "id": tipo_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating tipo_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/tipos_cuota/{tipo_id}")
async def delete_tipo_cuota(request: Request, tipo_id: int):
    """Delete a subscription type/plan."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM tipos_cuota WHERE id = %s RETURNING id", (tipo_id,)
                )
                deleted = cur.fetchone()
                if not deleted:
                    raise HTTPException(
                        status_code=404, detail="Tipo de cuota no encontrado"
                    )
                conn.commit()
                adm.log_action("owner", "delete_tipo_cuota", None, str(tipo_id))
                return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting tipo_cuota: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== CONCEPTOS DE PAGO ==========


@router.get("/conceptos_pago")
async def list_conceptos_pago(
    request: Request, activos: bool = Query(True, description="Solo conceptos activos")
):
    """List all payment concepts."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                if activos:
                    cur.execute("""
                        SELECT id, nombre, descripcion, precio_base, tipo, activo
                        FROM conceptos_pago
                        WHERE activo = TRUE
                        ORDER BY nombre
                    """)
                else:
                    cur.execute("""
                        SELECT id, nombre, descripcion, precio_base, tipo, activo
                        FROM conceptos_pago
                        ORDER BY activo DESC, nombre
                    """)
                rows = cur.fetchall()
                return [
                    {
                        "id": r[0],
                        "nombre": r[1],
                        "descripcion": r[2],
                        "precio_base": float(r[3]) if r[3] else 0.0,
                        "tipo": r[4],
                        "activo": r[5],
                    }
                    for r in rows
                ]
    except Exception as e:
        logger.error(f"Error listing conceptos_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/conceptos_pago")
async def create_concepto_pago(request: Request, data: ConceptoPagoCreate):
    """Create a new payment concept."""
    require_admin(request)
    adm = get_admin_service(request)

    if not data.nombre or not data.nombre.strip():
        raise HTTPException(status_code=400, detail="'nombre' es obligatorio")

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO conceptos_pago (nombre, descripcion, precio_base, tipo, activo)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        data.nombre.strip(),
                        data.descripcion,
                        data.precio_base or 0.0,
                        data.tipo,
                        data.activo if data.activo is not None else True,
                    ),
                )
                new_id = cur.fetchone()[0]
                conn.commit()
                adm.log_action("owner", "create_concepto_pago", None, data.nombre)
                return {"ok": True, "id": new_id}
    except Exception as e:
        logger.error(f"Error creating concepto_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/conceptos_pago/{concepto_id}")
async def update_concepto_pago(
    request: Request, concepto_id: int, data: ConceptoPagoUpdate
):
    """Update an existing payment concept."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check exists
                cur.execute(
                    "SELECT id FROM conceptos_pago WHERE id = %s", (concepto_id,)
                )
                if not cur.fetchone():
                    raise HTTPException(
                        status_code=404, detail="Concepto de pago no encontrado"
                    )

                # Build dynamic update
                updates = []
                values = []
                if data.nombre is not None:
                    updates.append("nombre = %s")
                    values.append(data.nombre.strip())
                if data.descripcion is not None:
                    updates.append("descripcion = %s")
                    values.append(data.descripcion)
                if data.precio_base is not None:
                    updates.append("precio_base = %s")
                    values.append(data.precio_base)
                if data.tipo is not None:
                    updates.append("tipo = %s")
                    values.append(data.tipo)
                if data.activo is not None:
                    updates.append("activo = %s")
                    values.append(data.activo)

                if not updates:
                    return {"ok": True, "id": concepto_id}

                values.append(concepto_id)
                cur.execute(
                    f"UPDATE conceptos_pago SET {', '.join(updates)} WHERE id = %s",
                    values,
                )
                conn.commit()
                adm.log_action("owner", "update_concepto_pago", None, str(concepto_id))
                return {"ok": True, "id": concepto_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating concepto_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/conceptos_pago/{concepto_id}")
async def delete_concepto_pago(request: Request, concepto_id: int):
    """Delete a payment concept."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM conceptos_pago WHERE id = %s RETURNING id",
                    (concepto_id,),
                )
                deleted = cur.fetchone()
                if not deleted:
                    raise HTTPException(
                        status_code=404, detail="Concepto de pago no encontrado"
                    )
                conn.commit()
                adm.log_action("owner", "delete_concepto_pago", None, str(concepto_id))
                return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting concepto_pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== PAGOS AVANZADOS ==========


@router.get("/pagos/{pago_id}")
async def get_pago_detalle(request: Request, pago_id: int):
    """Get payment details with concepts."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Get payment basic info
                cur.execute(
                    """
                    SELECT p.id, p.usuario_id, p.monto, p.mes, p.año, p.fecha_pago, p.metodo_pago_id,
                           u.nombre AS usuario_nombre, u.dni,
                           m.nombre AS metodo_nombre
                    FROM pagos p
                    LEFT JOIN usuarios u ON u.id = p.usuario_id
                    LEFT JOIN metodos_pago m ON m.id = p.metodo_pago_id
                    WHERE p.id = %s
                """,
                    (pago_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Pago no encontrado")

                pago = {
                    "id": row[0],
                    "usuario_id": row[1],
                    "monto": float(row[2]) if row[2] else 0.0,
                    "mes": row[3],
                    "año": row[4],
                    "fecha_pago": str(row[5]) if row[5] else None,
                    "metodo_pago_id": row[6],
                    "usuario_nombre": row[7],
                    "dni": row[8],
                    "metodo_nombre": row[9],
                }

                # Get payment details
                cur.execute(
                    """
                    SELECT pd.id, pd.concepto_id, pd.descripcion, pd.cantidad, pd.precio_unitario, pd.subtotal,
                           cp.nombre AS concepto_nombre
                    FROM pago_detalles pd
                    LEFT JOIN conceptos_pago cp ON cp.id = pd.concepto_id
                    WHERE pd.pago_id = %s
                """,
                    (pago_id,),
                )
                detalles = [
                    {
                        "id": r[0],
                        "concepto_id": r[1],
                        "descripcion": r[2],
                        "cantidad": r[3] or 1,
                        "precio_unitario": float(r[4]) if r[4] else 0.0,
                        "subtotal": float(r[5]) if r[5] else 0.0,
                        "concepto_nombre": r[6],
                    }
                    for r in cur.fetchall()
                ]

                total_detalles = (
                    sum(d["subtotal"] for d in detalles)
                    if detalles
                    else float(pago["monto"])
                )

                return {
                    "pago": pago,
                    "detalles": detalles,
                    "total_detalles": total_detalles,
                }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting pago detalle: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/pagos")
async def create_pago(request: Request, data: PagoCreate):
    """Create a new payment with optional concepts."""
    require_admin(request)
    adm = get_admin_service(request)

    if data.conceptos and len(data.conceptos) > 0:
        # Advanced payment with concepts
        return await _create_pago_avanzado(adm, data)
    else:
        # Simple payment
        return await _create_pago_simple(adm, data)


async def _create_pago_simple(adm, data: PagoCreate):
    """Create a simple payment without concepts."""
    if data.monto is None or data.monto <= 0:
        raise HTTPException(status_code=400, detail="'monto' debe ser mayor a 0")

    if data.mes is None or not (1 <= data.mes <= 12):
        raise HTTPException(status_code=400, detail="'mes' debe estar entre 1 y 12")

    if data.año is None:
        data.año = datetime.now().year

    try:
        fecha_pago = datetime.now()
        if data.fecha_pago:
            try:
                fecha_pago = datetime.fromisoformat(data.fecha_pago)
            except:
                pass

        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO pagos (usuario_id, monto, mes, año, fecha_pago, metodo_pago_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        data.usuario_id,
                        data.monto,
                        data.mes,
                        data.año,
                        fecha_pago,
                        data.metodo_pago_id,
                    ),
                )
                new_id = cur.fetchone()[0]

                # Update user expiration date
                _actualizar_vencimiento_usuario(cur, data.usuario_id, fecha_pago.date())

                conn.commit()
                adm.log_action(
                    "owner",
                    "create_pago",
                    None,
                    f"usuario:{data.usuario_id} monto:{data.monto}",
                )
                return {"ok": True, "id": new_id}
    except Exception as e:
        logger.error(f"Error creating pago simple: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


async def _create_pago_avanzado(adm, data: PagoCreate):
    """Create an advanced payment with multiple concepts."""
    # Validate concepts
    total = 0.0
    for c in data.conceptos:
        if c.cantidad <= 0:
            raise HTTPException(status_code=400, detail="Cantidad debe ser mayor a 0")
        if c.precio_unitario < 0:
            raise HTTPException(
                status_code=400, detail="Precio unitario no puede ser negativo"
            )
        if c.concepto_id is None and (not c.descripcion or not c.descripcion.strip()):
            raise HTTPException(
                status_code=400, detail="Cada ítem debe tener concepto_id o descripcion"
            )
        total += c.cantidad * c.precio_unitario

    try:
        fecha_pago = datetime.now()
        if data.fecha_pago:
            try:
                fecha_pago = datetime.fromisoformat(data.fecha_pago)
            except:
                pass

        mes = data.mes or fecha_pago.month
        año = data.año or fecha_pago.year

        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Create main payment record
                cur.execute(
                    """
                    INSERT INTO pagos (usuario_id, monto, mes, año, fecha_pago, metodo_pago_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id
                """,
                    (
                        data.usuario_id,
                        total,
                        mes,
                        año,
                        fecha_pago,
                        data.metodo_pago_id,
                    ),
                )
                pago_id = cur.fetchone()[0]

                # Create payment details
                for c in data.conceptos:
                    subtotal = c.cantidad * c.precio_unitario
                    cur.execute(
                        """
                        INSERT INTO pago_detalles (pago_id, concepto_id, descripcion, cantidad, precio_unitario, subtotal)
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                        (
                            pago_id,
                            c.concepto_id,
                            c.descripcion,
                            c.cantidad,
                            c.precio_unitario,
                            subtotal,
                        ),
                    )

                # Update user expiration date
                _actualizar_vencimiento_usuario(cur, data.usuario_id, fecha_pago.date())

                conn.commit()
                adm.log_action(
                    "owner",
                    "create_pago_avanzado",
                    None,
                    f"usuario:{data.usuario_id} total:{total}",
                )
                return {"ok": True, "id": pago_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating pago avanzado: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


def _actualizar_vencimiento_usuario(cur, usuario_id: int, fecha_pago: date):
    """Update user's next expiration date after payment."""
    try:
        # Get user's subscription type duration
        cur.execute(
            """
            SELECT u.tipo_cuota, tc.duracion_dias
            FROM usuarios u
            LEFT JOIN tipos_cuota tc ON tc.nombre = u.tipo_cuota
            WHERE u.id = %s
        """,
            (usuario_id,),
        )
        row = cur.fetchone()

        duracion = 30  # Default
        if row and row[1]:
            duracion = row[1]

        nueva_fecha = fecha_pago + timedelta(days=duracion)

        cur.execute(
            """
            UPDATE usuarios
            SET fecha_proximo_vencimiento = %s,
                cuotas_vencidas = 0,
                ultimo_pago = %s
            WHERE id = %s
        """,
            (nueva_fecha, fecha_pago, usuario_id),
        )
    except Exception as e:
        logger.warning(f"Could not update user expiration: {e}")


@router.put("/pagos/{pago_id}")
async def update_pago(request: Request, pago_id: int, data: PagoUpdate):
    """Update an existing payment."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Check exists
                cur.execute("SELECT id FROM pagos WHERE id = %s", (pago_id,))
                if not cur.fetchone():
                    raise HTTPException(status_code=404, detail="Pago no encontrado")

                # Build dynamic update
                updates = []
                values = []
                if data.usuario_id is not None:
                    updates.append("usuario_id = %s")
                    values.append(data.usuario_id)
                if data.monto is not None:
                    updates.append("monto = %s")
                    values.append(data.monto)
                if data.mes is not None:
                    updates.append("mes = %s")
                    values.append(data.mes)
                if data.año is not None:
                    updates.append("año = %s")
                    values.append(data.año)
                if data.metodo_pago_id is not None:
                    updates.append("metodo_pago_id = %s")
                    values.append(data.metodo_pago_id)
                if data.fecha_pago is not None:
                    try:
                        fecha = datetime.fromisoformat(data.fecha_pago)
                        updates.append("fecha_pago = %s")
                        values.append(fecha)
                    except:
                        pass

                if not updates:
                    return {"ok": True, "id": pago_id}

                values.append(pago_id)
                cur.execute(
                    f"UPDATE pagos SET {', '.join(updates)} WHERE id = %s", values
                )

                # Handle concepts update if provided
                if data.conceptos is not None and len(data.conceptos) > 0:
                    # Delete existing details
                    cur.execute(
                        "DELETE FROM pago_detalles WHERE pago_id = %s", (pago_id,)
                    )

                    # Insert new details
                    total = 0.0
                    for c in data.conceptos:
                        subtotal = c.cantidad * c.precio_unitario
                        total += subtotal
                        cur.execute(
                            """
                            INSERT INTO pago_detalles (pago_id, concepto_id, descripcion, cantidad, precio_unitario, subtotal)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                            (
                                pago_id,
                                c.concepto_id,
                                c.descripcion,
                                c.cantidad,
                                c.precio_unitario,
                                subtotal,
                            ),
                        )

                    # Update total amount
                    cur.execute(
                        "UPDATE pagos SET monto = %s WHERE id = %s", (total, pago_id)
                    )

                conn.commit()
                adm.log_action("owner", "update_pago", None, str(pago_id))
                return {"ok": True, "id": pago_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/pagos/{pago_id}")
async def delete_pago(request: Request, pago_id: int):
    """Delete a payment and its details."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Delete details first (cascade should handle this, but be explicit)
                cur.execute("DELETE FROM pago_detalles WHERE pago_id = %s", (pago_id,))

                # Delete main payment
                cur.execute("DELETE FROM pagos WHERE id = %s RETURNING id", (pago_id,))
                deleted = cur.fetchone()
                if not deleted:
                    raise HTTPException(status_code=404, detail="Pago no encontrado")

                conn.commit()
                adm.log_action("owner", "delete_pago", None, str(pago_id))
                return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting pago: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== ESTADÍSTICAS ==========


@router.get("/pagos/estadisticas")
async def get_estadisticas_pagos(
    request: Request, año: int = Query(None, description="Año para estadísticas")
):
    """Get payment statistics for a year."""
    require_admin(request)
    adm = get_admin_service(request)

    if año is None:
        año = datetime.now().year

    try:
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                # Overall stats
                cur.execute(
                    """
                    SELECT 
                        COUNT(id),
                        COALESCE(SUM(monto), 0),
                        COALESCE(AVG(monto), 0),
                        COALESCE(MIN(monto), 0),
                        COALESCE(MAX(monto), 0)
                    FROM pagos
                    WHERE EXTRACT(YEAR FROM fecha_pago) = %s
                """,
                    (año,),
                )
                row = cur.fetchone()

                stats = {
                    "año": año,
                    "total_pagos": row[0],
                    "total_recaudado": float(row[1]),
                    "promedio_pago": float(row[2]),
                    "pago_minimo": float(row[3]),
                    "pago_maximo": float(row[4]),
                    "por_mes": {},
                }

                # Per month stats
                cur.execute(
                    """
                    SELECT 
                        EXTRACT(MONTH FROM fecha_pago) AS mes,
                        COUNT(id),
                        COALESCE(SUM(monto), 0)
                    FROM pagos
                    WHERE EXTRACT(YEAR FROM fecha_pago) = %s
                    GROUP BY mes
                    ORDER BY mes
                """,
                    (año,),
                )

                for r in cur.fetchall():
                    stats["por_mes"][int(r[0])] = {
                        "cantidad": r[1],
                        "total": float(r[2]),
                    }

                # Per payment method
                cur.execute(
                    """
                    SELECT 
                        COALESCE(m.nombre, 'Sin método') AS metodo,
                        COUNT(p.id),
                        COALESCE(SUM(p.monto), 0)
                    FROM pagos p
                    LEFT JOIN metodos_pago m ON m.id = p.metodo_pago_id
                    WHERE EXTRACT(YEAR FROM p.fecha_pago) = %s
                    GROUP BY m.nombre
                    ORDER BY SUM(p.monto) DESC
                """,
                    (año,),
                )

                stats["por_metodo"] = [
                    {"metodo": r[0], "cantidad": r[1], "total": float(r[2])}
                    for r in cur.fetchall()
                ]

                return stats
    except Exception as e:
        logger.error(f"Error getting estadisticas: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ========== RECIBO PDF ==========


@router.get("/pagos/{pago_id}/recibo.pdf")
async def get_recibo_pdf(request: Request, pago_id: int):
    """Generate and return a PDF receipt for a payment."""
    require_admin(request)
    adm = get_admin_service(request)

    try:
        # Check if PDF generation is available
        from src.services.pdf_generator import PDFGenerator

        if not PDFGenerator.is_available():
            raise HTTPException(
                status_code=503,
                detail="Generación de PDF no disponible. Instale reportlab.",
            )

        # Get payment info
        with adm.db.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT p.id, p.usuario_id, p.monto, p.mes, p.año, p.fecha_pago, p.metodo_pago_id,
                           u.nombre AS usuario_nombre, u.dni, u.tipo_cuota,
                           m.nombre AS metodo_nombre
                    FROM pagos p
                    LEFT JOIN usuarios u ON u.id = p.usuario_id
                    LEFT JOIN metodos_pago m ON m.id = p.metodo_pago_id
                    WHERE p.id = %s
                """,
                    (pago_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Pago no encontrado")

                pago_info = {
                    "id": row[0],
                    "usuario_id": row[1],
                    "monto": float(row[2]) if row[2] else 0.0,
                    "mes": row[3] or 1,
                    "año": row[4] or datetime.now().year,
                    "fecha_pago": row[5],
                    "usuario_nombre": row[7],
                    "dni": row[8],
                    "tipo_cuota": row[9],
                    "metodo_nombre": row[10],
                }

                # Get payment details if any
                cur.execute(
                    """
                    SELECT pd.id, pd.concepto_id, pd.descripcion, pd.cantidad, 
                           pd.precio_unitario, pd.subtotal, cp.nombre AS concepto_nombre
                    FROM pago_detalles pd
                    LEFT JOIN conceptos_pago cp ON cp.id = pd.concepto_id
                    WHERE pd.pago_id = %s
                """,
                    (pago_id,),
                )
                detalles = [
                    {
                        "descripcion": r[2] or r[6] or "Concepto",
                        "concepto_nombre": r[6],
                        "cantidad": r[3] or 1,
                        "precio_unitario": float(r[4]) if r[4] else 0.0,
                        "subtotal": float(r[5]) if r[5] else 0.0,
                    }
                    for r in cur.fetchall()
                ]

        # Generate PDF
        pdf_gen = PDFGenerator(gym_name="IronHub")

        fecha_pago = pago_info["fecha_pago"]
        if isinstance(fecha_pago, str):
            try:
                fecha_pago = datetime.fromisoformat(fecha_pago)
            except:
                fecha_pago = datetime.now()

        filepath = pdf_gen.generar_recibo(
            pago_id=pago_info["id"],
            usuario_nombre=pago_info["usuario_nombre"],
            usuario_dni=pago_info["dni"],
            monto=pago_info["monto"],
            mes=pago_info["mes"],
            año=pago_info["año"],
            fecha_pago=fecha_pago,
            metodo_pago=pago_info["metodo_nombre"],
            tipo_cuota=pago_info["tipo_cuota"],
            detalles=detalles if detalles else None,
        )

        # Return the PDF file
        from fastapi.responses import FileResponse
        import os

        filename = os.path.basename(filepath)
        return FileResponse(
            filepath,
            media_type="application/pdf",
            filename=filename,
            headers={"Content-Disposition": f'inline; filename="{filename}"'},
        )

    except HTTPException:
        raise
    except ImportError as e:
        logger.error(f"PDF generation not available: {e}")
        raise HTTPException(status_code=503, detail="Módulo PDF no disponible")
    except Exception as e:
        logger.error(f"Error generating recibo PDF: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
