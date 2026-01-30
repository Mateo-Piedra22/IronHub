"""
Inscripciones Router - Class schedules, enrollments, and waitlist management
Uses InscripcionesService for all database operations.
"""

import logging
from fastapi import status

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import (
    require_gestion_access,
    require_owner,
    require_sucursal_selected,
    get_inscripciones_service,
    get_whatsapp_dispatch_service,
)
from src.services.inscripciones_service import InscripcionesService
from src.services.whatsapp_dispatch_service import WhatsAppDispatchService

router = APIRouter()
logger = logging.getLogger(__name__)


def _assert_profesor_horario_access(
    request: Request, svc: InscripcionesService, horario_id: int
) -> None:
    """If logged as profesor, ensure the horario belongs to that profesor."""
    role = str(request.session.get("role") or "").lower()
    if role != "profesor":
        return
    pid = request.session.get("gestion_profesor_id")
    if pid is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    hid_prof = svc._get_horario_profesor_id(int(horario_id))
    if hid_prof is None or int(hid_prof) != int(pid):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")


# === Clase Tipos ===


@router.get("/api/clases/tipos")
async def api_clase_tipos_list(
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """List all class types."""
    return {"tipos": svc.obtener_tipos()}


@router.post("/api/clases/tipos")
async def api_clase_tipo_create(
    request: Request,
    _=Depends(require_owner),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Create a class type."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        color = (payload.get("color") or "").strip() or None

        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")

        result = svc.crear_tipo(nombre, color)
        return result if result else {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating class type: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/clases/tipos/{tipo_id}")
async def api_clase_tipo_delete(
    tipo_id: int,
    _=Depends(require_owner),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Delete a class type (soft delete)."""
    try:
        svc.eliminar_tipo(tipo_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting class type: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Clase Horarios ===


@router.get("/api/clases/agenda")
async def api_clases_agenda(
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """List schedule entries across classes (calendar view)."""
    role = str(request.session.get("role") or "").lower()
    profesor_id = None
    if role == "profesor":
        pid = request.session.get("gestion_profesor_id")
        if pid is None:
            return {"agenda": []}
        profesor_id = int(pid)
    sucursal_id = request.session.get("sucursal_id")
    try:
        sucursal_id = int(sucursal_id) if sucursal_id is not None else None
    except Exception:
        sucursal_id = None
    return {"agenda": svc.obtener_agenda(profesor_id=profesor_id, sucursal_id=sucursal_id)}


@router.get("/api/clases/{clase_id}/horarios")
async def api_clase_horarios_list(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """List schedules for a class."""
    sucursal_id = request.session.get("sucursal_id")
    try:
        sucursal_id = int(sucursal_id) if sucursal_id is not None else None
    except Exception:
        sucursal_id = None
    horarios = svc.obtener_horarios(clase_id, sucursal_id=sucursal_id)
    role = str(request.session.get("role") or "").lower()
    if role == "profesor":
        pid = request.session.get("gestion_profesor_id")
        if pid is None:
            return {"horarios": []}
        horarios = [
            h for h in (horarios or []) if int(h.get("profesor_id") or 0) == int(pid)
        ]
    return {"horarios": horarios}


@router.post("/api/clases/{clase_id}/horarios")
async def api_clase_horario_create(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Create a class schedule."""
    try:
        payload = await request.json()
        dia = (payload.get("dia") or "").strip().lower()
        hora_inicio = payload.get("hora_inicio")
        hora_fin = payload.get("hora_fin")
        profesor_id = payload.get("profesor_id")
        cupo = payload.get("cupo") or 20

        if not dia or not hora_inicio or not hora_fin:
            raise HTTPException(
                status_code=400, detail="dia, hora_inicio y hora_fin son requeridos"
            )

        role = str(request.session.get("role") or "").lower()
        if role == "profesor":
            pid = request.session.get("gestion_profesor_id")
            if pid is None:
                raise HTTPException(status_code=403, detail="Forbidden")
            profesor_id = int(pid)

        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        result = svc.crear_horario(
            clase_id, dia, hora_inicio, hora_fin, profesor_id, int(cupo), sucursal_id=sucursal_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating schedule: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/clases/{clase_id}/horarios/{horario_id}")
async def api_clase_horario_update(
    clase_id: int,
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Update a class schedule."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        payload = await request.json()
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        result = svc.actualizar_horario(horario_id, clase_id, payload, sucursal_id=sucursal_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/clases/{clase_id}/horarios/{horario_id}")
async def api_clase_horario_delete(
    clase_id: int,
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Delete a class schedule."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        ok = svc.eliminar_horario(horario_id, clase_id, sucursal_id=sucursal_id)
        if not ok:
            raise HTTPException(status_code=404, detail="Horario no encontrado")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Inscripciones ===


@router.get("/api/horarios/{horario_id}/inscripciones")
async def api_inscripciones_list(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """List enrolled users for a schedule."""
    _assert_profesor_horario_access(request, svc, horario_id)
    return {"inscripciones": svc.obtener_inscripciones(horario_id)}


@router.post("/api/horarios/{horario_id}/inscripciones")
async def api_inscripcion_create(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Enroll a user in a class schedule."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        payload = await request.json()
        usuario_id = payload.get("usuario_id")

        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")

        result = svc.crear_inscripcion(horario_id, int(usuario_id))

        if result.get("error"):
            if result.get("forbidden"):
                raise HTTPException(status_code=403, detail=str(result.get("error") or "Forbidden"))
            if result.get("full"):
                raise HTTPException(
                    status_code=400, detail="Cupo lleno, agregar a lista de espera"
                )
            raise HTTPException(status_code=500, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating enrollment: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/horarios/{horario_id}/inscripciones/{usuario_id}")
async def api_inscripcion_delete(
    horario_id: int,
    usuario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Remove user from class schedule."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        svc.eliminar_inscripcion(horario_id, usuario_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting enrollment: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Lista de Espera ===


@router.get("/api/horarios/{horario_id}/lista-espera")
async def api_lista_espera_list(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Get waitlist for a schedule."""
    _assert_profesor_horario_access(request, svc, horario_id)
    return {"lista": svc.obtener_lista_espera(horario_id)}


@router.post("/api/horarios/{horario_id}/lista-espera")
async def api_lista_espera_add(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Add user to waitlist."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        payload = await request.json()
        usuario_id = payload.get("usuario_id")

        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")

        result = svc.agregar_lista_espera(horario_id, int(usuario_id))

        if result.get("error"):
            if result.get("forbidden"):
                raise HTTPException(status_code=403, detail=str(result.get("error") or "Forbidden"))
            raise HTTPException(status_code=500, detail=result["error"])

        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding to waitlist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/horarios/{horario_id}/lista-espera/{usuario_id}")
async def api_lista_espera_remove(
    horario_id: int,
    usuario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Remove user from waitlist."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        svc.eliminar_lista_espera(horario_id, usuario_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error removing from waitlist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/horarios/{horario_id}/lista-espera/notify")
async def api_lista_espera_notify(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
    wa: WhatsAppDispatchService = Depends(get_whatsapp_dispatch_service),
):
    """Notify next person in waitlist via WhatsApp."""
    try:
        _assert_profesor_horario_access(request, svc, horario_id)
        first = svc.obtener_primero_lista_espera(horario_id)

        if not first:
            return {"ok": False, "message": "Lista de espera vacía"}
        info = svc.obtener_horario_info(horario_id) or {}
        ok = wa.send_waitlist_promotion(
            int(first.get("usuario_id")),
            str(info.get("clase_nombre") or ""),
            str(info.get("dia") or ""),
            str(info.get("hora_inicio") or ""),
        )
        return {
            "ok": True,
            "notified_user": first.get("nombre"),
            "whatsapp_sent": bool(ok),
        }
    except Exception as e:
        logger.error(f"Error notifying waitlist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Clase Ejercicios ===


@router.get("/api/clases/{clase_id}/ejercicios")
async def api_clase_ejercicios_list(
    clase_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """List exercises linked to a class."""
    return {"ejercicios": svc.obtener_clase_ejercicios(clase_id)}


@router.put("/api/clases/{clase_id}/ejercicios")
async def api_clase_ejercicios_update(
    clase_id: int,
    request: Request,
    _=Depends(require_owner),
    svc: InscripcionesService = Depends(get_inscripciones_service),
):
    """Update exercises for a class (replaces all)."""
    try:
        payload = await request.json()
        ejercicio_ids = payload.get("ejercicio_ids") or []

        if not isinstance(ejercicio_ids, list):
            ejercicio_ids = []

        svc.actualizar_clase_ejercicios(clase_id, ejercicio_ids)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error updating class exercises: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
