"""
Inscripciones Router - Class schedules, enrollments, and waitlist management
Uses InscripcionesService for all database operations.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from src.dependencies import require_gestion_access, get_inscripciones_service
from src.services.inscripciones_service import InscripcionesService

router = APIRouter()
logger = logging.getLogger(__name__)


# === Clase Tipos ===

@router.get("/api/clases/tipos")
async def api_clase_tipos_list(
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """List all class types."""
    return {"tipos": svc.obtener_tipos()}


@router.post("/api/clases/tipos")
async def api_clase_tipo_create(
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
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
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Delete a class type (soft delete)."""
    try:
        svc.eliminar_tipo(tipo_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting class type: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Clase Horarios ===

@router.get("/api/clases/{clase_id}/horarios")
async def api_clase_horarios_list(
    clase_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """List schedules for a class."""
    return {"horarios": svc.obtener_horarios(clase_id)}


@router.post("/api/clases/{clase_id}/horarios")
async def api_clase_horario_create(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
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
            raise HTTPException(status_code=400, detail="dia, hora_inicio y hora_fin son requeridos")
        
        result = svc.crear_horario(clase_id, dia, hora_inicio, hora_fin, profesor_id, int(cupo))
        return result if result else {"ok": True}
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
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Update a class schedule."""
    try:
        payload = await request.json()
        result = svc.actualizar_horario(horario_id, clase_id, payload)
        return result if result else {"ok": True}
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/clases/{clase_id}/horarios/{horario_id}")
async def api_clase_horario_delete(
    clase_id: int,
    horario_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Delete a class schedule."""
    try:
        svc.eliminar_horario(horario_id, clase_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting schedule: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Inscripciones ===

@router.get("/api/horarios/{horario_id}/inscripciones")
async def api_inscripciones_list(
    horario_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """List enrolled users for a schedule."""
    return {"inscripciones": svc.obtener_inscripciones(horario_id)}


@router.post("/api/horarios/{horario_id}/inscripciones")
async def api_inscripcion_create(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Enroll a user in a class schedule."""
    try:
        payload = await request.json()
        usuario_id = payload.get("usuario_id")
        
        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")
        
        result = svc.crear_inscripcion(horario_id, int(usuario_id))
        
        if result.get('error'):
            if result.get('full'):
                raise HTTPException(status_code=400, detail="Cupo lleno, agregar a lista de espera")
            raise HTTPException(status_code=500, detail=result['error'])
        
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
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Remove user from class schedule."""
    try:
        svc.eliminar_inscripcion(horario_id, usuario_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error deleting enrollment: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Lista de Espera ===

@router.get("/api/horarios/{horario_id}/lista-espera")
async def api_lista_espera_list(
    horario_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Get waitlist for a schedule."""
    return {"lista": svc.obtener_lista_espera(horario_id)}


@router.post("/api/horarios/{horario_id}/lista-espera")
async def api_lista_espera_add(
    horario_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Add user to waitlist."""
    try:
        payload = await request.json()
        usuario_id = payload.get("usuario_id")
        
        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")
        
        result = svc.agregar_lista_espera(horario_id, int(usuario_id))
        
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
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
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Remove user from waitlist."""
    try:
        svc.eliminar_lista_espera(horario_id, usuario_id)
        return {"ok": True}
    except Exception as e:
        logger.error(f"Error removing from waitlist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/horarios/{horario_id}/lista-espera/notify")
async def api_lista_espera_notify(
    horario_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """Notify next person in waitlist via WhatsApp."""
    try:
        first = svc.obtener_primero_lista_espera(horario_id)
        
        if not first:
            return {"ok": False, "message": "Lista de espera vacía"}
        
        # WhatsApp notification would be handled separately
        return {
            "ok": True,
            "notified_user": first.get('nombre'),
            "whatsapp_sent": False  # Simplified - actual WhatsApp integration would be here
        }
    except Exception as e:
        logger.error(f"Error notifying waitlist: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# === Clase Ejercicios ===

@router.get("/api/clases/{clase_id}/ejercicios")
async def api_clase_ejercicios_list(
    clase_id: int,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
):
    """List exercises linked to a class."""
    return {"ejercicios": svc.obtener_clase_ejercicios(clase_id)}


@router.put("/api/clases/{clase_id}/ejercicios")
async def api_clase_ejercicios_update(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: InscripcionesService = Depends(get_inscripciones_service)
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
