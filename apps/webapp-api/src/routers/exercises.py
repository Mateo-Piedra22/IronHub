"""Exercises Router - Exercise management using GymService."""
import logging
import time
import os
import re

from fastapi import APIRouter, Request, Depends, UploadFile, File
from fastapi.responses import JSONResponse

from src.dependencies import require_gestion_access, get_training_service
from src.services.training_service import TrainingService
from src.services.b2_storage import simple_upload as b2_upload, get_file_url
from src.utils import _get_tenant_from_request

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/exercises/video")
async def api_upload_exercise_video(
    request: Request,
    file: UploadFile = File(...),
    name: str = "",
    _=Depends(require_gestion_access)
):
    """Upload exercise video to cloud storage."""
    try:
        ctype = str(getattr(file, 'content_type', '') or '').lower()
        allowed = {
            "video/mp4": ".mp4",
            "video/webm": ".webm",
            "video/quicktime": ".mov",
        }
        if ctype not in allowed:
            msg = "Formato de video no soportado. Use MP4, WEBM o MOV"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
        
        data = await file.read()
        if not data:
            msg = "Archivo vacío"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
        
        max_bytes = int(os.environ.get("MAX_EXERCISE_VIDEO_BYTES", str(50 * 1024 * 1024)))
        if len(data) > max_bytes:
            msg = "El video es demasiado grande"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
        
        tenant = _get_tenant_from_request(request) or "common"
        ext = allowed.get(ctype, ".mp4")

        hint = str(name or '').strip()
        if hint:
            hint = hint.replace(" ", "_")
            hint = re.sub(r"[^A-Za-z0-9._-]", "_", hint)
            hint = hint.strip("_")[:80] or f"ejercicio_{int(time.time())}"
            filename = f"{hint}{ext}"
        else:
            orig = str(getattr(file, 'filename', '') or '').strip()
            orig_base = os.path.basename(orig) if orig else ''
            if orig_base:
                stem = os.path.splitext(orig_base)[0] or f"ejercicio_{int(time.time())}"
                stem = stem.replace(" ", "_")
                stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem)
                stem = stem.strip("_")[:80] or f"ejercicio_{int(time.time())}"
                filename = f"{stem}{ext}"
            else:
                filename = f"ejercicio_{int(time.time())}{ext}"
        
        public_url = b2_upload(data, filename, ctype, subfolder=f"exercises/{tenant}")
        if not public_url:
            msg = "Error subiendo el video"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
        
        return JSONResponse({"ok": True, "url": public_url, "mime": ctype})
    except Exception as e:
        logger.error(f"Error uploading exercise video: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)


@router.get("/api/exercises")
async def api_list_exercises(
    request: Request, q: str = "", page: int = 1, page_size: int = 20,
    grupo: str = "", objetivo: str = "",
    _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)
):
    """List exercises with pagination and search."""
    try:
        page_n = max(1, int(page or 1))
        page_size_n = max(1, int(page_size or 20))
        offset = (page_n - 1) * page_size_n

        out = svc.obtener_ejercicios_paginados(
            search=str(q or ""),
            grupo=(str(grupo).strip() if str(grupo or "").strip() else None),
            objetivo=(str(objetivo).strip() if str(objetivo or "").strip() else None),
            limit=page_size_n,
            offset=offset,
        )
        items = list(out.get('items') or [])
        total = int(out.get('total') or 0)
        
        # Ensure full CDN URLs
        for item in items:
            if item.get("video_url"):
                item["video_url"] = get_file_url(item["video_url"])
        
        return {"items": items, "total": total, "page": page_n}
    except Exception as e:
        logger.error(f"Error listing exercises: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)


@router.post("/api/exercises")
async def api_create_exercise(request: Request, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Create a new exercise."""
    try:
        data = await request.json()
        nombre = str(data.get("nombre") or "").strip()
        if not nombre:
            msg = "Nombre requerido"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
        
        new_id = svc.crear_ejercicio({
            'nombre': nombre,
            'grupo_muscular': str(data.get("grupo_muscular") or "").strip(),
            'video_url': data.get("video_url"),
            'video_mime': data.get("video_mime")
        })
        if not new_id:
            msg = "No se pudo crear"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
        return {"ok": True, "id": int(new_id)}
    except Exception as e:
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)


@router.put("/api/exercises/{eid}")
async def api_update_exercise(eid: int, request: Request, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Update an exercise."""
    try:
        data = await request.json()
        ok = bool(svc.actualizar_ejercicio(eid, data))
        if not ok:
            msg = "Ejercicio no encontrado"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=404)
        return {"ok": True}
    except Exception as e:
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)


@router.delete("/api/exercises/{eid}")
async def api_delete_exercise(eid: int, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Delete an exercise."""
    try:
        ok = bool(svc.eliminar_ejercicio(eid))
        if not ok:
            msg = "Ejercicio no encontrado"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=404)
        return {"ok": True}
    except Exception as e:
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
