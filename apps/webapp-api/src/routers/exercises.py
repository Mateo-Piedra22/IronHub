"""Exercises Router - Exercise management using GymService."""
import logging
import time
import os

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse

from src.dependencies import require_gestion_access, get_training_service
from src.services.training_service import TrainingService
from src.services.b2_storage import simple_upload as b2_upload, get_file_url
from src.utils import _get_tenant_from_request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/exercises/video")
async def api_upload_exercise_video(request: Request, file: UploadFile = File(...), _=Depends(require_gestion_access)):
    """Upload exercise video to cloud storage."""
    try:
        ctype = str(getattr(file, 'content_type', '') or '').lower()
        if not ctype.startswith("video/"):
            return JSONResponse({"ok": False, "error": "El archivo debe ser un video"}, status_code=400)
        
        data = await file.read()
        if not data:
            return JSONResponse({"ok": False, "error": "Archivo vacío"}, status_code=400)
        
        if len(data) > 50 * 1024 * 1024:
            return JSONResponse({"ok": False, "error": "El video es demasiado grande (max 50MB)"}, status_code=400)
        
        tenant = _get_tenant_from_request(request) or "common"
        ext = os.path.splitext(file.filename)[1] if file.filename else ".mp4"
        filename = f"exercise_{int(time.time())}_{os.urandom(4).hex()}{ext}"
        
        public_url = b2_upload(data, filename, ctype, subfolder=f"exercises/{tenant}")
        if not public_url:
            return JSONResponse({"ok": False, "error": "Error subiendo el video"}, status_code=500)
        
        return JSONResponse({"ok": True, "url": public_url, "mime": ctype})
    except Exception as e:
        logger.error(f"Error uploading exercise video: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/exercises")
async def api_list_exercises(
    request: Request, q: str = "", page: int = 1, page_size: int = 20,
    _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)
):
    """List exercises with pagination and search."""
    try:
        exercises = svc.obtener_ejercicios()
        search = q.strip().lower()
        
        if search:
            exercises = [e for e in exercises if search in (e.get('nombre', '') or '').lower() or search in (e.get('grupo_muscular', '') or '').lower()]
        
        total = len(exercises)
        offset = (max(1, page) - 1) * page_size
        items = exercises[offset:offset + page_size]
        
        # Ensure full CDN URLs
        for item in items:
            if item.get("video_url"):
                item["video_url"] = get_file_url(item["video_url"])
        
        return {"items": items, "total": total, "page": page}
    except Exception as e:
        logger.error(f"Error listing exercises: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post("/api/exercises")
async def api_create_exercise(request: Request, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Create a new exercise."""
    try:
        data = await request.json()
        nombre = str(data.get("nombre") or "").strip()
        if not nombre:
            return JSONResponse({"ok": False, "error": "Nombre requerido"}, status_code=400)
        
        new_id = svc.crear_ejercicio({
            'nombre': nombre,
            'grupo_muscular': str(data.get("grupo_muscular") or "").strip(),
            'video_url': data.get("video_url"),
            'video_mime': data.get("video_mime")
        })
        return {"ok": True, "id": new_id}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.put("/api/exercises/{eid}")
async def api_update_exercise(eid: int, request: Request, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Update an exercise."""
    try:
        data = await request.json()
        svc.actualizar_ejercicio(eid, data)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.delete("/api/exercises/{eid}")
async def api_delete_exercise(eid: int, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Delete an exercise."""
    try:
        svc.eliminar_ejercicio(eid)
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
