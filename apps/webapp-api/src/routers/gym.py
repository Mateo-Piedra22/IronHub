import logging
import os
import json
import time
import hmac
import hashlib
import secrets
import base64
import zlib
import uuid
import threading
import urllib.parse
import tempfile
from datetime import datetime, timezone, date
from typing import Optional, List, Dict, Any

from starlette.background import BackgroundTask

from fastapi import APIRouter, Request, Depends, HTTPException, Body, UploadFile, File, status, Query
from fastapi.responses import JSONResponse, FileResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session


# Services
from src.dependencies import (
    require_gestion_access, 
    require_owner, 
    get_db,
    get_gym_config_service,
    get_clase_service,
    get_training_service,
    get_user_service,
    get_rm,
    get_current_active_user
)

from src.models.orm_models import (
    Rutina, Usuario, RutinaEjercicio, Ejercicio, Clase, ClaseBloque, ClaseBloqueItem
)

from src.database.tenant_connection import get_current_tenant, set_current_tenant, validate_tenant_name
from src.routine_manager import RoutineTemplateManager
from src.utils import get_gym_name, _resolve_logo_url, _resolve_existing_dir, get_webapp_base_url
from src.services.gym_config_service import GymConfigService
from src.services.clase_service import ClaseService
from src.services.training_service import TrainingService
from src.services.user_service import UserService
from src.services.b2_storage import simple_upload as b2_upload

router = APIRouter()
logger = logging.getLogger(__name__)


_MAX_PREVIEW_JSON_BYTES = int(os.environ.get("PREVIEW_MAX_JSON_BYTES", "300000"))  # ~300KB
_MAX_PREVIEW_B64_CHARS = int(os.environ.get("PREVIEW_MAX_B64_CHARS", "400000"))   # ~400KB chars
_MAX_PREVIEW_DECOMPRESSED_BYTES = int(os.environ.get("PREVIEW_MAX_DECOMPRESSED_BYTES", "1200000"))  # ~1.2MB


def _cleanup_file(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _cleanup_files(*paths: str) -> None:
    for p in paths:
        try:
            _cleanup_file(p)
        except Exception:
            pass


def _sanitize_download_filename(filename: Optional[str], default_name: str, ext: str) -> str:
    base = os.path.basename(filename) if filename else default_name
    if not base.lower().endswith(ext.lower()):
        base = f"{base}{ext}"
    base = base[:150].replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    return base


def _get_public_base_url(request: Request) -> str:
    try:
        xf_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
        xf_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
        host = xf_host or (request.headers.get("host") or "").split(",")[0].strip()
        proto = xf_proto or (request.url.scheme if hasattr(request, "url") else "")
        if host and proto:
            return f"{proto}://{host}".rstrip('/')
    except Exception:
        pass
    try:
        return str(request.base_url).rstrip('/')
    except Exception:
        return os.environ.get('API_BASE_URL', 'https://api.ironhub.motiona.xyz').rstrip('/')


def _normalize_rutina_export_params(weeks: int, qr_mode: str, sheet: Optional[str]) -> tuple[int, str, Optional[str]]:
    try:
        weeks_n = int(weeks)
    except Exception:
        weeks_n = 1
    weeks_n = max(1, min(weeks_n, 4))

    qr = str(qr_mode or "inline").strip().lower()
    if qr == "auto":
        qr = "sheet"
    if qr not in ("inline", "sheet", "none"):
        qr = "sheet"

    sh = None
    try:
        sh = (str(sheet).strip()[:64]) if sheet else None
    except Exception:
        sh = None
    return weeks_n, qr, sh


def _safe_decompress_url_payload(b64_data: str) -> str:
    if not isinstance(b64_data, str):
        raise ValueError("Invalid data")
    if len(b64_data) > _MAX_PREVIEW_B64_CHARS:
        raise ValueError("Payload too large")

    compressed = base64.urlsafe_b64decode(b64_data)
    dobj = zlib.decompressobj()
    out_parts: list[bytes] = []
    out_len = 0
    chunk_size = 64 * 1024
    for i in range(0, len(compressed), chunk_size):
        part = dobj.decompress(compressed[i:i + chunk_size], max_length=max(0, _MAX_PREVIEW_DECOMPRESSED_BYTES - out_len))
        if part:
            out_parts.append(part)
            out_len += len(part)
            if out_len > _MAX_PREVIEW_DECOMPRESSED_BYTES:
                raise ValueError("Decompressed payload too large")
    tail = dobj.flush()
    if tail:
        out_len += len(tail)
        if out_len > _MAX_PREVIEW_DECOMPRESSED_BYTES:
            raise ValueError("Decompressed payload too large")
        out_parts.append(tail)

    return b"".join(out_parts).decode("utf-8")

def _sign_excel_view(rutina_id: int, weeks: int, filename: str, ts: int, qr_mode: str = "sheet", sheet: str | None = None) -> str:
    """Generate HMAC signature for Excel view URL."""
    try:
        qr = str(qr_mode or "inline").strip().lower()
        if qr == "auto":
            qr = "sheet"
        if qr not in ("inline", "sheet", "none"):
            qr = "sheet"
    except Exception:
        qr = "sheet"
    try:
        sh = (str(sheet).strip()[:64]) if (sheet is not None and str(sheet).strip()) else ""
    except Exception:
        sh = ""
    try:
        tenant = str(get_current_tenant() or "").strip().lower()
    except Exception:
        tenant = ""
    try:
        base = f"{tenant}|{int(rutina_id)}|{int(weeks)}|{filename}|{int(ts)}|{qr}|{sh}".encode("utf-8")
    except Exception:
        base = f"{tenant}|{rutina_id}|{weeks}|{filename}|{ts}|{qr}|{sh}".encode("utf-8")
    secret = _get_preview_secret().encode("utf-8")
    return hmac.new(secret, base, hashlib.sha256).hexdigest()

# --- API Configuración ---

@router.get("/api/gym/data")
async def api_gym_data(
    _=Depends(require_gestion_access),

    svc: GymConfigService = Depends(get_gym_config_service)
):
    """Get gym configuration using SQLAlchemy."""
    try:
        config = svc.obtener_configuracion_gimnasio()
        if config:
            # Frontend contract expects { nombre, logo_url }
            try:
                if isinstance(config, dict):
                    if 'nombre' not in config:
                        config['nombre'] = config.get('gym_name') or config.get('nombre')
                    if 'gym_name' not in config and config.get('nombre'):
                        config['gym_name'] = config.get('nombre')
                    if 'gym_logo_url' not in config and config.get('logo_url'):
                        config['gym_logo_url'] = config.get('logo_url')
            except Exception:
                pass
            try:
                lu = config.get('logo_url') if isinstance(config, dict) else None
                if isinstance(lu, str) and lu.strip() and not lu.strip().startswith("http") and not lu.strip().startswith("/"):
                    from src.services.b2_storage import get_file_url
                    config['logo_url'] = get_file_url(lu.strip())
            except Exception:
                pass
            return config
        # Fallback to simple dict using utils
        return {
            "gym_name": get_gym_name(),
            "nombre": get_gym_name(),
            "logo_url": _resolve_logo_url(),
            "gym_logo_url": _resolve_logo_url(),
        }
    except Exception as e:
        logger.error(f"Error getting gym data: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/gym/update")
async def api_gym_update(
    request: Request, 
    _=Depends(require_owner),

    svc: GymConfigService = Depends(get_gym_config_service)
):
    """Update gym configuration using SQLAlchemy."""
    try:
        data = await request.json()
        name = str(data.get("gym_name", "")).strip()
        address = str(data.get("gym_address", "")).strip()
        
        if not name:
            return JSONResponse({"ok": False, "error": "Nombre inválido"}, status_code=400)
        
        updates = {"gym_name": name}
        if address:
            updates["gym_address"] = address
        
        if svc.actualizar_configuracion_gimnasio(updates):
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": "Error guardando"}, status_code=500)
    except Exception as e:
        logger.error(f"Error updating gym: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@router.post("/api/gym/logo")
async def api_gym_logo(
    request: Request, 
    file: UploadFile = File(...), 
    _=Depends(require_gestion_access),

    svc: GymConfigService = Depends(get_gym_config_service)
):
    """Upload gym logo using SQLAlchemy for storage."""
    try:
        ctype = str(getattr(file, 'content_type', '') or '').lower()
        if ctype not in ("image/png", "image/svg+xml", "image/jpeg", "image/jpg"):
            return JSONResponse({"ok": False, "error": "Formato no soportado. Use PNG, JPG o SVG"}, status_code=400)
            
        data = await file.read()
        if not data:
             return JSONResponse({"ok": False, "error": "Archivo vacío"}, status_code=400)
             
        public_url = None
        
        # 1. Try Cloud Storage (B2 + Cloudflare)
        try:
            from src.utils import _get_tenant_from_request
            tenant = _get_tenant_from_request(request) or "common"
            
            ext = ".png"
            if "svg" in ctype: ext = ".svg"
            elif "jpeg" in ctype or "jpg" in ctype: ext = ".jpg"
            
            filename = f"gym_logo_{int(time.time())}{ext}"
            uploaded_url = b2_upload(data, filename, ctype, subfolder=f"logos/{tenant}")
            if uploaded_url:
                public_url = uploaded_url
        except Exception as e:
            logger.error(f"Error uploading logo to cloud storage: {e}")

        # 2. Fallback to Local Storage if cloud failed
        if not public_url:
            return JSONResponse({"ok": False, "error": "Error subiendo logo"}, status_code=500)
        

        if public_url:
            svc.actualizar_logo_url(public_url)
                 
        return JSONResponse({"ok": True, "logo_url": public_url})
    except Exception as e:
        logger.error(f"Error uploading gym logo: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@router.get("/api/gym/subscription")
async def api_gym_subscription(request: Request, _=Depends(require_gestion_access)):
    from src.utils import _get_multi_tenant_mode, _get_tenant_from_request
    from src.dependencies import get_admin_db
    
    if not _get_multi_tenant_mode():
        return {"active": True, "plan": "pro", "gym_name": get_gym_name()}
        
    # Multi-tenant logic
    sub = _get_tenant_from_request(request)
    if not sub:
        return {"active": False, "error": "no_tenant"}
        
    adm = get_admin_db()
    if adm is None:
        # Fail open or closed? Legacy failed open usually for safety if admin db down
        return {"active": True, "plan": "pro", "source": "fallback"}
        
    try:
        # Assuming admin_db has a way to get subscription by subdomain or we need gym_id
        # We don't have gym_id easily here without querying admin DB for the tenant
        # But wait, we can query gyms table in admin db by subdomain
        with adm.db.get_connection_context() as conn: # type: ignore
             cur = conn.cursor()
             cur.execute("SELECT id, plan, active FROM gyms WHERE subdominio = %s", (sub,))
             row = cur.fetchone()
             if row:
                 return {
                     "active": bool(row[2]), 
                     "plan": str(row[1]),
                     "gym_id": int(row[0])
                 }
    except Exception:
        pass
        
    return {"active": True, "plan": "pro", "source": "default"}

# --- Helpers for Routine Export / Preview ---

def _get_preview_secret() -> str:
    try:
        env = os.getenv("WEBAPP_PREVIEW_SECRET", "").strip()
        if env:
            return env
    except Exception:
        pass
    for k in ("SESSION_SECRET", "SECRET_KEY", "VERCEL_GITHUB_COMMIT_SHA"):
        try:
            v = os.getenv(k, "").strip()
            if v:
                return v
        except Exception:
            continue
    return "preview-secret"

def _sign_excel_view(rutina_id: int, weeks: int, filename: str, ts: int, qr_mode: str = "auto", sheet: str | None = None) -> str:
    try:
        qr = str(qr_mode or "inline").strip().lower()
        if qr in ("auto", "real", "preview"):
            qr = "sheet"
        if qr not in ("inline", "sheet", "none"):
            qr = "sheet"
    except Exception:
        qr = "sheet"
    try:
        sh = (str(sheet).strip()[:64]) if (sheet is not None and str(sheet).strip()) else ""
    except Exception:
        sh = ""
    try:
        tenant = str(get_current_tenant() or "").strip().lower()
    except Exception:
        tenant = ""
    try:
        base = f"{tenant}|{int(rutina_id)}|{int(weeks)}|{filename}|{int(ts)}|{qr}|{sh}".encode("utf-8")
    except Exception:
        base = f"{tenant}|{rutina_id}|{weeks}|{filename}|{ts}|{qr}|{sh}".encode("utf-8")
    secret = _get_preview_secret().encode("utf-8")
    return hmac.new(secret, base, hashlib.sha256).hexdigest()

def _sign_excel_view_draft(payload_id: str, weeks: int, filename: str, ts: int, qr_mode: str = "auto", sheet: str | None = None) -> str:
    try:
        pid = str(payload_id)
    except Exception:
        pid = payload_id
    try:
        qr = str(qr_mode or "inline").strip().lower()
        if qr in ("auto", "real", "preview"):
            qr = "sheet"
        if qr not in ("inline", "sheet", "none"):
            qr = "sheet"
    except Exception:
        qr = "sheet"
    try:
        sh = (str(sheet).strip()[:64]) if (sheet is not None and str(sheet).strip()) else ""
    except Exception:
        sh = ""
    try:
        base = f"{pid}|{int(weeks)}|{filename}|{int(ts)}|{qr}|{sh}".encode("utf-8")
    except Exception:
        base = f"{pid}|{weeks}|{filename}|{ts}|{qr}|{sh}".encode("utf-8")
    secret = _get_preview_secret().encode("utf-8")
    return hmac.new(secret, base, hashlib.sha256).hexdigest()

def _sign_excel_view_draft_data(data: str, weeks: int, filename: str, ts: int, qr_mode: str = "auto", sheet: str | None = None) -> str:
    try:
        d = str(data)
    except Exception:
        d = data
    try:
        qr = str(qr_mode or "inline").strip().lower()
        if qr in ("auto", "real", "preview"):
            qr = "sheet"
        if qr not in ("inline", "sheet", "none"):
            qr = "sheet"
    except Exception:
        qr = "sheet"
    try:
        sh = (str(sheet).strip()[:64]) if (sheet is not None and str(sheet).strip()) else ""
    except Exception:
        sh = ""
    try:
        base = f"{d}|{int(weeks)}|{filename}|{int(ts)}|{qr}|{sh}".encode("utf-8")
    except Exception:
        base = f"{d}|{weeks}|{filename}|{ts}|{qr}|{sh}".encode("utf-8")
    secret = _get_preview_secret().encode("utf-8")
    return hmac.new(secret, base, hashlib.sha256).hexdigest()

def _sanitize_filename_component(val: Any, max_len: int = 64) -> str:
    try:
        s = str(val or "").strip()
    except Exception:
        s = ""
    if not s:
        return ""
    try:
        s = s.replace(" ", "_")
        for ch in ("\\", "/", ":", "*", "?", '"', "<", ">", "|"):
            s = s.replace(ch, "_")
        while "__" in s:
            s = s.replace("__", "_")
        return s[:max_len]
    except Exception:
        return s[:max_len]

def _dias_segment(dias: Any) -> str:
    try:
        d = int(dias)
    except Exception:
        d = 1
    try:
        d = max(1, min(d, 5))
    except Exception:
        d = 1
    return f"{d}-dias"

def _build_excel_export_filename(nombre_rutina: str, dias: Any, usuario_nombre: str) -> str:
    try:
        date_str = datetime.now().strftime("%d-%m-%Y")
    except Exception:
        date_str = ""
    nr = _sanitize_filename_component(nombre_rutina or "rutina", max_len=60) or "rutina"
    seg_d = _dias_segment(dias)
    user_seg = _sanitize_filename_component(usuario_nombre or "", max_len=60)
    parts = ["rutina", nr, seg_d]
    if user_seg:
        parts.append(user_seg)
    if date_str:
        parts.append(date_str)
    base = "_".join([p for p in parts if p])
    base = base[:150]
    return f"{base}.xlsx"

def _encode_preview_payload(payload: Dict[str, Any]) -> str:
    try:
        compact: Dict[str, Any] = {
            "n": payload.get("nombre_rutina"),
            "d": payload.get("descripcion"),
            "ds": payload.get("dias_semana"),
            "c": payload.get("categoria"),
            "ui": ((payload.get("usuario_id") if payload.get("usuario_id") is not None else (payload.get("usuario") or {}).get("id"))),
            "un": (payload.get("usuario_nombre_override") if (payload.get("usuario_nombre_override") not in (None, "")) else ((payload.get("usuario") or {}).get("nombre"))),
            "ud": (payload.get("usuario_dni") if payload.get("usuario_dni") is not None else (payload.get("usuario") or {}).get("dni")),
            "ut": (payload.get("usuario_telefono") if payload.get("usuario_telefono") is not None else (payload.get("usuario") or {}).get("telefono")),
            "e": [
                [
                    int(x.get("ejercicio_id")),
                    int(x.get("dia_semana", 1)),
                    x.get("series"),
                    x.get("repeticiones"),
                    int(x.get("orden", 1)),
                    ((x.get("nombre_ejercicio")) or ((x.get("ejercicio") or {}).get("nombre") if isinstance(x.get("ejercicio"), dict) else None) or None),
                ]
                for x in (payload.get("ejercicios") or [])
            ],
        }
        raw = json.dumps(compact, separators=(",", ":")).encode("utf-8")
        comp = zlib.compress(raw, level=6)
        return base64.urlsafe_b64encode(comp).decode("ascii")
    except Exception:
        try:
            return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
        except Exception:
            return ""

def _decode_preview_payload(data: str) -> Optional[Dict[str, Any]]:
    try:
        comp = base64.urlsafe_b64decode(str(data))
        try:
            raw = zlib.decompress(comp)
        except Exception:
            raw = comp
        obj = json.loads(raw.decode("utf-8"))
        if not isinstance(obj, dict):
            return None
        if "e" in obj and isinstance(obj.get("e"), list):
            ejercicios = []
            for arr in (obj.get("e") or []):
                try:
                    item = {
                        "ejercicio_id": int(arr[0]),
                        "dia_semana": int(arr[1]),
                        "series": arr[2],
                        "repeticiones": arr[3],
                        "orden": int(arr[4]),
                    }
                    try:
                        if len(arr) > 5 and arr[5] not in (None, ""):
                            item["nombre_ejercicio"] = str(arr[5])
                            item["nombre_actual"] = item["nombre_ejercicio"]
                    except Exception:
                        pass
                    ejercicios.append(item)
                except Exception:
                    continue
            ui = obj.get("ui")
            try:
                ui_int = int(ui) if ui is not None else None
            except Exception:
                ui_int = None
            return {
                "nombre_rutina": obj.get("n"),
                "descripcion": obj.get("d"),
                "dias_semana": obj.get("ds"),
                "categoria": obj.get("c"),
                "usuario_id": ui_int,
                "usuario_nombre_override": obj.get("un"),
                "usuario_dni": obj.get("ud"),
                "usuario_telefono": obj.get("ut"),
                "usuario": {
                    "id": ui_int,
                    "nombre": obj.get("un"),
                    "dni": obj.get("ud"),
                    "telefono": obj.get("ut"),
                },
                "ejercicios": ejercicios,
            }
        return obj
    except Exception:
        return None

_excel_preview_drafts_lock = threading.RLock()
_excel_preview_drafts: Dict[str, Dict[str, Any]] = {}

def _clean_preview_drafts() -> None:
    try:
        now = int(time.time())
        to_del = []
        with _excel_preview_drafts_lock:
            for k, v in list(_excel_preview_drafts.items()):
                exp = int(v.get("expires_at", 0) or 0)
                if exp and now > exp:
                    to_del.append(k)
            for k in to_del:
                _excel_preview_drafts.pop(k, None)
    except Exception:
        pass

def _save_excel_preview_draft(payload: Dict[str, Any]) -> str:
    try:
        raw_len = len(json.dumps(payload, ensure_ascii=False))
        if raw_len > 500_000:
            raise ValueError("Payload demasiado grande para previsualización")
    except Exception:
        pass
    pid = secrets.token_urlsafe(18)
    now = int(time.time())
    entry = {
        "payload": payload,
        "created_at": now,
        "expires_at": now + 600,
    }
    with _excel_preview_drafts_lock:
        _excel_preview_drafts[pid] = entry
        _clean_preview_drafts()
    return pid

def _get_excel_preview_draft(pid: str) -> Optional[Dict[str, Any]]:
    try:
        with _excel_preview_drafts_lock:
            entry = _excel_preview_drafts.get(str(pid))
            if not entry:
                return None
            exp = int(entry.get("expires_at", 0) or 0)
            now = int(time.time())
            if exp and now > exp:
                _excel_preview_drafts.pop(str(pid), None)
                return None
            return entry.get("payload")
    except Exception:
        return None

_excel_preview_routines_lock = threading.RLock()
_excel_preview_routines: Dict[str, Dict[str, Any]] = {}

def _clean_preview_routines() -> None:
    try:
        now = int(time.time())
        to_del = []
        with _excel_preview_routines_lock:
            for k, v in list(_excel_preview_routines.items()):
                exp = int(v.get("expires_at", 0) or 0)
                if exp and now > exp:
                    to_del.append(k)
            for k in to_del:
                _excel_preview_routines.pop(k, None)
    except Exception:
        pass

def _save_excel_preview_routine(uuid_str: str, rutina_dict: Dict[str, Any]) -> None:
    if not uuid_str:
        return
    now = int(time.time())
    entry = {
        "rutina": rutina_dict,
        "created_at": now,
        "expires_at": now + 600,
    }
    with _excel_preview_routines_lock:
        _excel_preview_routines[str(uuid_str)] = entry
        _clean_preview_routines()

def _get_excel_preview_routine(uuid_str: str) -> Optional[Dict[str, Any]]:
    try:
        with _excel_preview_routines_lock:
            entry = _excel_preview_routines.get(str(uuid_str))
            if not entry:
                return None
            exp = int(entry.get("expires_at", 0) or 0)
            now = int(time.time())
            if exp and now > exp:
                _excel_preview_routines.pop(str(uuid_str), None)
                return None
            return entry.get("rutina")
    except Exception:
        return None

_ejercicios_catalog_lock = threading.RLock()
_ejercicios_catalog_cache: Dict[str, Any] = {"ts": 0, "by_id": {}, "by_name": {}}

def _load_ejercicios_catalog(force: bool = False) -> Dict[str, Any]:
    try:
        now = int(time.time())
        with _ejercicios_catalog_lock:
            ts = int(_ejercicios_catalog_cache.get("ts", 0) or 0)
            if (not force) and ts and (now - ts) < 300:
                return _ejercicios_catalog_cache
            by_id: Dict[int, Dict[str, Any]] = {}
            by_name: Dict[str, Dict[str, Any]] = {}
            rows = None
            try:
                from src.database.connection import SessionLocal
                from src.services.training_service import TrainingService
                session = SessionLocal()
                try:
                    svc = TrainingService(session)
                    rows = svc.obtener_ejercicios_catalog()
                finally:
                    session.close()
            except Exception:
                rows = None
            if rows:
                for r in rows:
                    try:
                        eid = int(r.get('id') or 0)
                    except Exception:
                        eid = 0
                    name = (r.get('nombre') or '').strip().lower()
                    info = {
                        'video_url': r.get('video_url'),
                        'video_mime': r.get('video_mime'),
                    }
                    if eid:
                        by_id[eid] = info
                    if name:
                        by_name[name] = info
            else:
                try:
                    p = Path(__file__).resolve().parent.parent / 'ejercicios.json'
                    if p.exists():
                        data = json.loads(p.read_text(encoding='utf-8'))
                        for it in (data or []):
                            try:
                                eid = int(it.get('id') or 0)
                            except Exception:
                                eid = 0
                            name = (it.get('nombre') or '').strip().lower()
                            info = {
                                'video_url': it.get('video_url'),
                                'video_mime': it.get('video_mime'),
                            }
                            if eid:
                                by_id[eid] = info
                            if name:
                                by_name[name] = info
                except Exception:
                    pass
            _ejercicios_catalog_cache = {"ts": now, "by_id": by_id, "by_name": by_name}
            return _ejercicios_catalog_cache
    except Exception:
        return {"ts": 0, "by_id": {}, "by_name": {}}

def _lookup_video_info(ejercicio_id: Any, nombre: Optional[str]) -> Dict[str, Any]:
    try:
        cat = _load_ejercicios_catalog()
        info = None
        if ejercicio_id is not None:
            try:
                info = cat.get('by_id', {}).get(int(ejercicio_id))
            except Exception:
                info = None
        if (not info) and nombre:
            try:
                info = cat.get('by_name', {}).get(str(nombre).strip().lower())
            except Exception:
                info = None
        return info or {'video_url': None, 'video_mime': None}
    except Exception:
        return {'video_url': None, 'video_mime': None}

def _build_exercises_by_day(rutina: Any) -> Dict[int, list]:
    try:
        grupos: Dict[int, list] = {}
        ejercicios = getattr(rutina, "ejercicios", []) or []
        for r in ejercicios:
            try:
                if isinstance(r, dict):
                    rid_val = getattr(rutina, "id", None)
                    rid = int(rid_val) if rid_val is not None else 0
                    r_obj = RutinaEjercicio(
                        id=r.get("id"),
                        rutina_id=int(r.get("rutina_id") or rid or 0),
                        ejercicio_id=int(r.get("ejercicio_id") or 0),
                        dia_semana=int(r.get("dia_semana") or 1),
                        series=r.get("series"),
                        repeticiones=r.get("repeticiones"),
                        orden=int(r.get("orden") or 0),
                        ejercicio=None
                    )
                    ej = r.get("ejercicio")
                    try:
                        if isinstance(ej, dict):
                            r_obj.ejercicio = Ejercicio(
                                id=int(ej.get("id") or r_obj.ejercicio_id or 0),
                                nombre=str(ej.get("nombre") or ""),
                                grupo_muscular=ej.get("grupo_muscular"),
                                descripcion=ej.get("descripcion")
                            )
                        elif ej is not None:
                            r_obj.ejercicio = ej  # type: ignore
                        else:
                            r_obj.ejercicio = Ejercicio(id=int(r_obj.ejercicio_id or 0))
                    except Exception:
                        r_obj.ejercicio = None
                    nombre_actual = r.get("nombre_ejercicio")
                    if not nombre_actual:
                        nombre_nested = getattr(r_obj.ejercicio, "nombre", None) if r_obj.ejercicio is not None else None
                        if nombre_nested:
                            nombre_actual = nombre_nested
                        else:
                            eid = r_obj.ejercicio_id
                            nombre_actual = f"Ejercicio {eid}" if eid else "Ejercicio"
                    try:
                        setattr(r_obj, "nombre_ejercicio", nombre_actual)
                    except Exception:
                        pass
                    r = r_obj
                else:
                    nombre_actual = getattr(r, "nombre_ejercicio", None)
                    if not nombre_actual:
                        nombre_nested = getattr(getattr(r, "ejercicio", None), "nombre", None)
                        if nombre_nested:
                            try:
                                setattr(r, "nombre_ejercicio", nombre_nested)
                            except Exception:
                                pass
                        else:
                            eid = getattr(r, "ejercicio_id", None)
                            try:
                                setattr(r, "nombre_ejercicio", f"Ejercicio {eid}" if eid is not None else "Ejercicio")
                            except Exception:
                                pass
            except Exception:
                pass
            dia = getattr(r, "dia_semana", None) if not isinstance(r, dict) else r.get("dia_semana")
            if dia is None:
                continue
            try:
                grupos.setdefault(int(dia), []).append(r)
            except Exception:
                continue
        for dia, arr in grupos.items():
            try:
                arr.sort(key=lambda e: (int(getattr(e, "orden", 0) or 0), str(getattr(e, "nombre_ejercicio", "") or "")))
            except Exception:
                pass
        return grupos
    except Exception:
        return {}

def _build_rutina_from_draft(payload: Dict[str, Any]) -> tuple:
    # Simplified version for brevity but functional based on read code
    u_raw = payload.get("usuario") or {}
    try:
        u_nombre = (
            (u_raw.get("nombre") or u_raw.get("Nombre"))
            or (payload.get("usuario_nombre") or payload.get("nombre_usuario"))
            or (payload.get("usuario_nombre_override") or None)
        )
        u_nombre = (u_nombre or "").strip()
    except Exception:
        u_nombre = ""
    
    u_id = None
    try:
        u_id_raw = payload.get("usuario_id") or u_raw.get("id")
        u_id = int(u_id_raw) if u_id_raw is not None else None
    except Exception:
        u_id = None

    if (not u_nombre) and (u_id is not None):
        try:
            from src.dependencies import get_user_service
            from src.database.connection import SessionLocal
            session = SessionLocal()
            try:
                svc = get_user_service(session)
                u_obj = svc.get_user(int(u_id))
                if u_obj:
                    u_nombre = (getattr(u_obj, "nombre", "") or "").strip() or u_nombre
            finally:
                session.close()
        except Exception:
            pass
    
    if not u_nombre and u_id is None:
        u_nombre = "Plantilla"
    
    usuario = Usuario(nombre=u_nombre)
    try:
        if u_id:
            usuario.id = u_id
    except Exception:
        pass
    
    r_raw = payload.get("rutina") or payload
    rutina = Rutina(
        nombre_rutina=(r_raw.get("nombre_rutina") or r_raw.get("nombre") or "Rutina"),
        descripcion=r_raw.get("descripcion"),
        dias_semana=int(r_raw.get("dias_semana") or 1),
        categoria=(r_raw.get("categoria") or "general")
    )
    
    # Add uuid
    try:
        ruuid = (r_raw.get("uuid_rutina") or r_raw.get("uuid") or payload.get("uuid_rutina"))
        if not ruuid:
            ruuid = str(uuid.uuid4())
        setattr(rutina, "uuid_rutina", ruuid)
        setattr(rutina, "uuid", ruuid)
    except Exception:
        pass

    ejercicios: list = []
    day_counts: Dict[int, int] = {}
    items = payload.get("ejercicios") or []
    # Logic for parsing items (simplified)
    if isinstance(items, list):
        for idx, it in enumerate(items):
            try:
                dia = int(it.get("dia_semana") or it.get("dia") or 1)
                re = RutinaEjercicio(
                    rutina_id=0,
                    ejercicio_id=int(it.get("ejercicio_id") or 0),
                    dia_semana=dia,
                    series=str(it.get("series") or ""),
                    repeticiones=str(it.get("repeticiones") or ""),
                    orden=int(it.get("orden") or idx + 1)
                )
                nombre_e = it.get("nombre_ejercicio") or it.get("nombre")
                if nombre_e:
                    setattr(re, "nombre_ejercicio", nombre_e)
                else:
                    day_counts[dia] = day_counts.get(dia, 0) + 1
                    setattr(re, "nombre_ejercicio", f"Ejercicio {day_counts[dia]}")
                ejercicios.append(re)
            except Exception:
                continue
    
    try:
        rutina.ejercicios = ejercicios
    except Exception:
        pass
        
    ejercicios_por_dia = _build_exercises_by_day(rutina)
    return rutina, usuario, ejercicios_por_dia

# --- API Configuración ---

@router.get("/api/gym_data")
async def api_gym_data_legacy(
    _=Depends(require_gestion_access),

    svc: GymConfigService = Depends(get_gym_config_service)
):
    """Legacy gym data endpoint using SQLAlchemy."""
    try:
        config = svc.obtener_configuracion_gimnasio()
        return config if config else {}
    except Exception as e:
        logger.error(f"Error getting gym data: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.put("/api/gym_update")
async def api_gym_update_legacy(
    request: Request, 
    _=Depends(require_gestion_access),

    svc: GymConfigService = Depends(get_gym_config_service)
):
    """Legacy gym update endpoint using SQLAlchemy."""
    try:
        payload = await request.json()
        if svc.actualizar_configuracion_gimnasio(payload):
            return {"ok": True}
        return JSONResponse({"error": "No se pudo guardar"}, status_code=400)
    except Exception as e:
        logger.error(f"Error updating gym: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/gym_logo")
async def api_gym_logo_legacy(
    request: Request,
    file: UploadFile = File(...), 
    _=Depends(require_gestion_access),

    svc: GymConfigService = Depends(get_gym_config_service)
):
    """Legacy gym logo upload endpoint using SQLAlchemy."""
    try:
        ctype = str(getattr(file, 'content_type', '') or '').lower()
        allowed = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/svg+xml": ".svg",
        }
        if ctype not in allowed:
            return JSONResponse({"ok": False, "error": "Formato no soportado. Use PNG, JPG o SVG"}, status_code=400)

        content = await file.read()
        if not content:
            return JSONResponse({"ok": False, "error": "Archivo vacío"}, status_code=400)
        max_bytes = int(os.environ.get("MAX_LOGO_BYTES", "5000000"))
        if len(content) > max_bytes:
            return JSONResponse({"ok": False, "error": "Logo demasiado grande"}, status_code=400)

        ext = allowed.get(ctype, ".png")
        filename = f"gym_logo_{int(time.time())}{ext}"

        try:
            tenant = _get_tenant_from_request(request)
        except Exception:
            tenant = None
        if not tenant:
            tenant = "common"

        uploaded_url = b2_upload(content, filename, ctype, subfolder=f"logos/{tenant}")
        if not uploaded_url:
            return JSONResponse({"ok": False, "error": "Error subiendo logo"}, status_code=500)

        svc.actualizar_configuracion('gym_logo_url', uploaded_url)
        return {"ok": True, "url": uploaded_url}
    except Exception as e:
        logger.error(f"Error uploading gym logo: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# --- API Clases ---

@router.get("/api/clases")
async def api_clases(
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Get all classes using SQLAlchemy."""
    try:
        clases = svc.obtener_clases()
        return {"clases": clases}
    except Exception as e:
        logger.error(f"Error getting clases: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/clases")
async def api_clases_create(
    request: Request, 
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Create a class using SQLAlchemy."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        descripcion = (payload.get("descripcion") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        
        new_id = svc.crear_clase({
            'nombre': nombre,
            'descripcion': descripcion,
            'activo': True
        })
        
        if new_id:
            return {"ok": True, "id": int(new_id)}
        msg = "No se pudo crear"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get("/api/clases/{clase_id}")
async def api_clase_get(
    clase_id: int,
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Get a single clase by ID."""
    try:
        clase = svc.obtener_clase(clase_id)
        if not clase:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        return clase
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put("/api/clases/{clase_id}")
async def api_clase_update(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Update a clase."""
    try:
        payload = await request.json()
        success = svc.actualizar_clase(clase_id, payload)
        if success:
            clase = svc.obtener_clase(clase_id)
            return clase or {"ok": True}
        return JSONResponse({"error": "No se pudo actualizar"}, status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete("/api/clases/{clase_id}")
async def api_clase_delete(
    clase_id: int,
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Delete a clase."""
    try:
        success = svc.eliminar_clase(clase_id)
        if success:
            return {"ok": True}
        return JSONResponse({"error": "No se pudo eliminar"}, status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- API Bloques ---


@router.get("/api/clases/{clase_id}/bloques")
async def api_clase_bloques_list(
    clase_id: int, 
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Get workout blocks for a class using SQLAlchemy."""
    try:
        return svc.obtener_clase_bloques(clase_id)
    except Exception as e:
        logger.error(f"Error listing bloques: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/api/clases/{clase_id}/bloques/{bloque_id}")
async def api_clase_bloque_items(
    clase_id: int, 
    bloque_id: int, 
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Get items in a workout block using SQLAlchemy."""
    try:
        items = svc.obtener_bloque_items(clase_id, bloque_id)
        if items is None:
            raise HTTPException(status_code=404, detail="Bloque no encontrado")
        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bloque items: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.post("/api/clases/{clase_id}/bloques")
async def api_clase_bloque_create(
    clase_id: int, 
    request: Request, 
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Create a workout block with items using SQLAlchemy."""
    payload = await request.json()
    try:
        nombre = (payload.get("nombre") or "").strip()
        items = payload.get("items") or []
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' es obligatorio")
        if not isinstance(items, list):
            items = []
        
        # Convert items format
        formatted_items = []
        for idx, it in enumerate(items):
            try:
                eid = int(it.get("ejercicio_id") or it.get("id") or 0)
            except Exception:
                eid = 0
            if eid <= 0:
                continue
            formatted_items.append({
                'ejercicio_id': eid,
                'orden': int(it.get("orden") or idx),
                'series': int(it.get("series") or 0),
                'repeticiones': str(it.get("repeticiones") or ""),
                'descanso_segundos': int(it.get("descanso_segundos") or 0),
                'notas': str(it.get("notas") or "")
            })
        
        bloque_id = svc.crear_clase_bloque(clase_id, nombre, formatted_items)
        if bloque_id:
            return {"ok": True, "id": bloque_id}
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bloque: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.put("/api/clases/{clase_id}/bloques/{bloque_id}")
async def api_clase_bloque_update(
    clase_id: int, 
    bloque_id: int, 
    request: Request, 
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Update a workout block using SQLAlchemy."""
    payload = await request.json()
    try:
        items = payload.get("items") or []
        nombre_raw = payload.get("nombre")
        nombre = (nombre_raw or "").strip() if isinstance(nombre_raw, str) else "Bloque"
        if not isinstance(items, list):
            items = []
        
        # Check if bloque exists
        existing = svc.obtener_bloque_items(clase_id, bloque_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Bloque no encontrado")
        
        # Convert items format
        formatted_items = []
        for idx, it in enumerate(items):
            try:
                eid = int(it.get("ejercicio_id") or it.get("id") or 0)
            except Exception:
                eid = 0
            if eid <= 0:
                continue
            formatted_items.append({
                'ejercicio_id': eid,
                'orden': int(it.get("orden") or idx),
                'series': int(it.get("series") or 0),
                'repeticiones': str(it.get("repeticiones") or ""),
                'descanso_segundos': int(it.get("descanso_segundos") or 0),
                'notas': str(it.get("notas") or "")
            })
        
        if svc.actualizar_clase_bloque(bloque_id, nombre, formatted_items):
            return {"ok": True}
        return JSONResponse({"error": "No se pudo actualizar"}, status_code=500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bloque: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

@router.delete("/api/clases/{clase_id}/bloques/{bloque_id}")
async def api_clase_bloque_delete(
    clase_id: int, 
    bloque_id: int, 
    _=Depends(require_gestion_access),

    svc: ClaseService = Depends(get_clase_service)
):
    """Delete a workout block using SQLAlchemy."""
    try:
        # Check if bloque exists
        existing = svc.obtener_bloque_items(clase_id, bloque_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Bloque no encontrado")
        
        if svc.eliminar_clase_bloque(bloque_id):
            return {"ok": True}
        return JSONResponse({"error": "No se pudo eliminar"}, status_code=500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting bloque: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

# --- API Ejercicios ---

@router.get("/api/ejercicios")
async def api_ejercicios_list(
    request: Request,
    _=Depends(require_gestion_access),

    svc: TrainingService = Depends(get_training_service)
):
    """Get all exercises using SQLAlchemy with optional filters."""
    try:
        search = request.query_params.get("search")
        grupo = request.query_params.get("grupo")
        objetivo = request.query_params.get("objetivo")

        limit_q = request.query_params.get("limit")
        offset_q = request.query_params.get("offset")
        if limit_q is not None or offset_q is not None:
            try:
                limit_n = int(limit_q) if limit_q is not None else 50
            except Exception:
                limit_n = 50
            try:
                offset_n = int(offset_q) if offset_q is not None else 0
            except Exception:
                offset_n = 0
            limit_n = max(1, min(limit_n, 500))
            offset_n = max(0, offset_n)

            out = svc.obtener_ejercicios_paginados(search=str(search or ""), grupo=grupo, objetivo=objetivo, limit=limit_n, offset=offset_n)
            return {"ejercicios": list(out.get('items') or []), "total": int(out.get('total') or 0), "limit": limit_n, "offset": offset_n}

        return {"ejercicios": svc.obtener_ejercicios(search=search, grupo=grupo, objetivo=objetivo)}
    except Exception as e:
        logger.error(f"Error listing ejercicios: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.post("/api/ejercicios")
async def api_ejercicios_create(
    request: Request, 
    _=Depends(require_gestion_access),

    svc: TrainingService = Depends(get_training_service)
):
    """Create an exercise using SQLAlchemy."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        
        new_id = svc.crear_ejercicio({
            'nombre': nombre,
            'grupo_muscular': (payload.get("grupo_muscular") or "").strip(),
            'objetivo': (payload.get("objetivo") or "general"),
            'equipamiento': (payload.get("equipamiento") or "").strip() or None,
            'variantes': (payload.get("variantes") or "").strip() or None,
            'descripcion': (payload.get("descripcion") or "").strip() or None,
            'video_url': payload.get("video_url"),
            'video_mime': payload.get("video_mime")
        })
        
        if new_id:
            return {"ok": True, "id": int(new_id)}
        msg = "No se pudo crear"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ejercicio: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.put("/api/ejercicios/{ejercicio_id}")
async def api_ejercicios_update(
    ejercicio_id: int, 
    request: Request, 
    _=Depends(require_gestion_access),

    svc: TrainingService = Depends(get_training_service)
):
    """Update an exercise using SQLAlchemy."""
    try:
        payload = await request.json()
        if svc.actualizar_ejercicio(ejercicio_id, payload):
            return {"ok": True}
        msg = "No se pudo actualizar"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except Exception as e:
        logger.error(f"Error updating ejercicio: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.delete("/api/ejercicios/{ejercicio_id}")
async def api_ejercicios_delete(
    ejercicio_id: int, 
    _=Depends(require_gestion_access),

    svc: TrainingService = Depends(get_training_service)
):
    """Delete an exercise using SQLAlchemy."""
    try:
        if svc.eliminar_ejercicio(ejercicio_id):
            return {"ok": True}
        msg = "No se pudo eliminar"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except Exception as e:
        logger.error(f"Error deleting ejercicio: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

# --- API Rutinas ---

@router.get("/api/rutinas")
async def api_rutinas_list(
    request: Request,
    usuario_id: Optional[int] = None,
    search: str = "",
    plantillas: Optional[bool] = None,
    es_plantilla: Optional[bool] = None, # Alias for plantillas
    include_exercises: bool = False,

    svc: TrainingService = Depends(get_training_service)
):
    """Get routines using SQLAlchemy. Includes exercises when filtering by user."""
    try:
        # AuthZ:
        # - Gestion sessions can list any rutinas (incl templates).
        # - Member sessions can only list their own rutinas.
        try:
            role = str(request.session.get('role') or '').strip().lower()
        except Exception:
            role = ""

        logged_in = bool(request.session.get('logged_in'))
        gestion_prof_user_id = request.session.get('gestion_profesor_user_id')
        session_user_id = request.session.get('user_id')

        is_gestion = bool(logged_in) or bool(gestion_prof_user_id) or role in (
            'dueño', 'dueno', 'owner', 'admin', 'administrador', 'profesor'
        )

        if (not is_gestion) and (session_user_id is None):
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not is_gestion:
            usuario_id = int(session_user_id)
            plantillas = False
            es_plantilla = False
            include_exercises = True

        is_template_req = plantillas if plantillas is not None else es_plantilla
        rutinas = svc.obtener_rutinas(
            usuario_id,
            include_exercises=include_exercises,
            search=search,
            solo_plantillas=is_template_req,
        )
        return {"rutinas": rutinas}
    except Exception as e:
        logger.error(f"Error listing rutinas: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.post("/api/rutinas")
async def api_rutinas_create(
    request: Request, 
    _=Depends(require_gestion_access),

    svc: TrainingService = Depends(get_training_service)
):
    """Create a routine using SQLAlchemy."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or payload.get("nombre_rutina") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")
        
        new_id = svc.crear_rutina({
            'nombre_rutina': nombre,
            'descripcion': payload.get("descripcion"),
            'usuario_id': payload.get("usuario_id"),
            'dias_semana': payload.get("dias_semana") or 1,
            'categoria': payload.get("categoria") or "general",
            'activa': True
        })
        
        if new_id:
            # Handle exercises 
            # 1. Try from 'dias' (UnifiedRutinaEditor format)
            dias = payload.get("dias")
            ok_assign = True
            if dias and isinstance(dias, list):
                exercises_flat = []
                for dia in dias:
                    d_num = int(dia.get("numero") or dia.get("dayNumber") or 1)
                    for ex in (dia.get("ejercicios") or []):
                        ex_copy = ex.copy()
                        ex_copy["dia_semana"] = d_num
                        exercises_flat.append(ex_copy)
                if exercises_flat:
                    ok_assign = bool(svc.asignar_ejercicios_rutina(new_id, exercises_flat))
            # 2. Try from 'ejercicios' (Duplicate format or flat API usage)
            elif payload.get("ejercicios") and isinstance(payload.get("ejercicios"), list):
                ok_assign = bool(svc.asignar_ejercicios_rutina(new_id, payload.get("ejercicios")))

            if not ok_assign:
                try:
                    svc.eliminar_rutina(int(new_id))
                except Exception:
                    pass
                msg = "Ejercicios inválidos"
                return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
            
            return {"ok": True, "id": int(new_id)}
        msg = "No se pudo crear"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except HTTPException:
        raise
    except PermissionError as e:
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)
    except Exception as e:
        logger.error(f"Error creating rutina: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.get("/api/rutinas/{rutina_id}/export/pdf")
async def api_rutina_export_pdf(rutina_id: int, weeks: int = 1, filename: Optional[str] = None, qr_mode: str = "auto", sheet: Optional[str] = None, tenant: Optional[str] = None, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Export routine as PDF using RoutineTemplateManager."""
    rm = get_rm()
    if rm is None:
        raise HTTPException(status_code=503, detail="RoutineTemplateManager no disponible")
    try:
        try:
            t = str(tenant or "").strip().lower()
        except Exception:
            t = ""
        if t:
            try:
                ok_t, _err = validate_tenant_name(t)
                if ok_t:
                    set_current_tenant(t)
            except Exception:
                pass

        weeks_n, qr_norm, sheet_norm = _normalize_rutina_export_params(weeks, qr_mode, sheet)
        rutina_data = svc.obtener_rutina_completa(rutina_id)
        if not rutina_data:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")
        
        # Build Rutina object for RoutineTemplateManager
        rutina = Rutina(
            id=rutina_data['id'],
            nombre_rutina=rutina_data['nombre_rutina'],
            descripcion=rutina_data.get('descripcion'),
            categoria=rutina_data.get('categoria'),
            uuid_rutina=rutina_data.get('uuid_rutina')
        )
        rutina.ejercicios = rutina_data.get('ejercicios', [])
        
        # Build Usuario object
        usuario = Usuario(nombre=rutina_data.get('usuario_nombre') or 'Usuario')
        
        ejercicios_por_dia = _build_exercises_by_day(rutina_data)

        tmp_xlsx_fd, tmp_xlsx = tempfile.mkstemp(prefix=f"rutina_{rutina_id}_", suffix=".xlsx")
        try:
            os.close(tmp_xlsx_fd)
        except Exception:
            pass
        tmp_pdf_fd, tmp_pdf = tempfile.mkstemp(prefix=f"rutina_{rutina_id}_", suffix=".pdf")
        try:
            os.close(tmp_pdf_fd)
        except Exception:
            pass

        xlsx_path = rm.generate_routine_excel(
            rutina,
            usuario,
            ejercicios_por_dia,
            output_path=tmp_xlsx,
            weeks=weeks_n,
            qr_mode=qr_norm,
            sheet=sheet_norm,
        )
        pdf_path = rm.convert_excel_to_pdf(xlsx_path, pdf_path=tmp_pdf)

        pdf_filename = _sanitize_download_filename(filename, f"rutina_{rutina_id}", ".pdf")
        return FileResponse(
            pdf_path,
            media_type="application/pdf",
            filename=pdf_filename,
            background=BackgroundTask(_cleanup_files, str(pdf_path), str(xlsx_path))
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error exporting PDF")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/rutinas/{rutina_id}")
async def api_rutina_get(rutina_id: int, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Get a single routine with all exercises."""
    try:
        rutina = svc.obtener_rutina_completa(rutina_id)
        if not rutina:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")
        return rutina
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rutina: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.put("/api/rutinas/{rutina_id}")
async def api_rutina_update(rutina_id: int, request: Request, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Update a routine."""
    try:
        if not svc.obtener_rutina_completa(rutina_id):
            raise HTTPException(status_code=404, detail="Rutina no encontrada")

        payload = await request.json()
        
        # Transform dias to exercises list if present
        dias = payload.get("dias")
        if dias and isinstance(dias, list) and "ejercicios" not in payload:
            exercises_flat = []
            for dia in dias:
                d_num = dia.get("numero") or dia.get("dayNumber") or 1
                for ex in (dia.get("ejercicios") or []):
                    ex["dia_semana"] = d_num
                    exercises_flat.append(ex)
            payload["ejercicios"] = exercises_flat
            
        success = svc.actualizar_rutina(rutina_id, payload)
        if success:
            return {"ok": True}
        if "ejercicios" in (payload or {}):
            msg = "Ejercicios inválidos"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
        msg = "No se pudo actualizar"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except Exception as e:
        logger.error(f"Error updating rutina: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.delete("/api/rutinas/{rutina_id}")
async def api_rutina_delete(rutina_id: int, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Delete a routine."""
    try:
        if svc.eliminar_rutina(rutina_id):
            return {"ok": True}
        msg = "No se pudo eliminar"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except Exception as e:
        logger.error(f"Error deleting rutina: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
@router.put("/api/rutinas/{rutina_id}/toggle-activa")
async def api_rutina_toggle_activa(rutina_id: int, _=Depends(require_gestion_access), svc: TrainingService = Depends(get_training_service)):
    """Toggle activa status of a routine. If activating, deactivates other rutinas for the same user."""
    try:
        rutina = svc.obtener_rutina_completa(rutina_id)
        if not rutina:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")
        
        new_status = not rutina.get('activa', False)
        
        # If activating this rutina and it has a user, deactivate others first
        if new_status and rutina.get('usuario_id'):
            svc.desactivar_rutinas_usuario(rutina['usuario_id'], except_rutina_id=rutina_id)
        
        success = svc.actualizar_rutina(rutina_id, {'activa': new_status})
        if success:
            return {"ok": True, "activa": new_status}
        msg = "No se pudo actualizar"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling rutina activa: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.post("/api/rutinas/{rutina_id}/assign")
async def api_rutina_assign(
    rutina_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    svc: TrainingService = Depends(get_training_service)
):
    """Assign a routine (plantation) to a user, creating a copy for that user."""
    try:
        payload = await request.json()
        usuario_id = payload.get("usuario_id")
        
        rutina_origen = svc.obtener_rutina_completa(rutina_id)
        if not rutina_origen:
             raise HTTPException(status_code=404, detail="Rutina origen no encontrada")
             
        # Clone
        new_data = {
            'nombre_rutina': rutina_origen['nombre_rutina'],
            'descripcion': rutina_origen['descripcion'],
            'usuario_id': usuario_id,
            'dias_semana': rutina_origen['dias_semana'],
            'categoria': rutina_origen['categoria'],
            'activa': True
        }
        new_id = svc.crear_rutina(new_data)
        if new_id:
            # Clone exercises
            exs = rutina_origen.get('ejercicios', [])
            ok_assign = bool(svc.asignar_ejercicios_rutina(new_id, exs))
            if not ok_assign:
                try:
                    svc.eliminar_rutina(int(new_id))
                except Exception:
                    pass
                msg = "Ejercicios inválidos"
                return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)
            return {"ok": True, "id": new_id}
            
        msg = "No se pudo asignar"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)
    except HTTPException:
        raise
    except PermissionError as e:
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)
    except Exception as e:
        logger.error(f"Error assigning rutina: {e}")
        msg = str(e)
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=500)

@router.get("/api/rutinas/{rutina_id}/export/excel")
async def api_rutina_export_excel(
    rutina_id: int,
    weeks: int = 1,
    qr_mode: str = "sheet",
    sheet: Optional[str] = None,
    tenant: Optional[str] = None,
    user_override: Optional[str] = None,
    filename: Optional[str] = None,
    _=Depends(require_gestion_access),
    svc: TrainingService = Depends(get_training_service),
    rm: RoutineTemplateManager = Depends(get_rm)
):
    """Export a routine as Excel."""
    try:
        if rm is None:
            raise HTTPException(status_code=503, detail="RoutineTemplateManager no disponible")

        try:
            t = str(tenant or "").strip().lower()
        except Exception:
            t = ""
        if t:
            try:
                ok_t, _err = validate_tenant_name(t)
                if ok_t:
                    set_current_tenant(t)
            except Exception:
                pass

        weeks_n, qr_norm, sheet_norm = _normalize_rutina_export_params(weeks, qr_mode, sheet)
        rutina_data = svc.obtener_rutina_completa(rutina_id)
        if not rutina_data:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")
        
        # Build Rutina object
        rutina = Rutina(
            id=rutina_data['id'],
            nombre_rutina=rutina_data.get('nombre_rutina') or rutina_data.get('nombre', ''),
            descripcion=rutina_data.get('descripcion'),
            dias_semana=rutina_data.get('dias_semana', 1),
            uuid_rutina=rutina_data.get('uuid_rutina')
        )
        
        # Build Usuario object
        user_name = user_override or rutina_data.get('usuario_nombre') or 'Usuario'
        usuario = Usuario(nombre=user_name)
        
        ejercicios_por_dia = _build_exercises_by_day(rutina_data)

        tmp_xlsx_fd, tmp_xlsx = tempfile.mkstemp(prefix=f"rutina_{rutina_id}_", suffix=".xlsx")
        try:
            os.close(tmp_xlsx_fd)
        except Exception:
            pass
        xlsx_path = rm.generate_routine_excel(
            rutina,
            usuario,
            ejercicios_por_dia,
            output_path=tmp_xlsx,
            weeks=weeks_n,
            qr_mode=qr_norm,
            sheet=sheet_norm,
        )
        excel_filename = _sanitize_download_filename(filename, f"rutina_{rutina_id}", ".xlsx")
        return FileResponse(
            xlsx_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=excel_filename,
            background=BackgroundTask(_cleanup_file, str(xlsx_path))
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error exporting Excel")
        raise HTTPException(status_code=500, detail=str(e))

# --- Excel Preview Signed URL Endpoints ---
# These endpoints enable Excel preview in Office Online Viewer without needing cloud storage

@router.get("/api/rutinas/{rutina_id}/export/excel_view_url")
async def api_rutina_excel_view_url(
    rutina_id: int,
    request: Request,
    weeks: int = 1,
    filename: Optional[str] = None,
    qr_mode: str = "sheet",
    sheet: Optional[str] = None,
    tenant: Optional[str] = None,
    _=Depends(require_gestion_access),
    svc: TrainingService = Depends(get_training_service),
):
    """Generate a signed URL for Excel preview in Office Online Viewer.
    
    This endpoint requires authentication and returns a signed URL that can be
    used with Office Online Viewer. The signed URL points to the public
    excel_view.xlsx endpoint which verifies the signature before serving.
    """
    try:
        if not tenant:
            try:
                tenant = str(get_current_tenant() or "").strip().lower()
            except Exception:
                tenant = None
        if not tenant:
            try:
                tenant = str(request.session.get("tenant") or "").strip().lower()
            except Exception:
                tenant = None
        if not tenant:
            try:
                tenant = str(request.headers.get("x-tenant") or "").strip().lower()
            except Exception:
                tenant = None

        if tenant:
            try:
                ok_t, _err = validate_tenant_name(tenant)
                if not ok_t:
                    tenant = None
            except Exception:
                tenant = None

        if not tenant:
            raise HTTPException(status_code=400, detail="Tenant requerido para previsualización")

        try:
            set_current_tenant(str(tenant))
        except Exception:
            pass

        # Get rutina data to build filename
        rutina_data = svc.obtener_rutina_completa(rutina_id)
        if not rutina_data:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")
        
        # Build filename
        if not filename:
            nombre_rutina = rutina_data.get('nombre_rutina') or rutina_data.get('nombre', f'rutina_{rutina_id}')
            usuario_nombre = rutina_data.get('usuario_nombre', '')
            dias = rutina_data.get('dias_semana', 1)
            parts = ['rutina', nombre_rutina, f'{dias}-dias']
            if usuario_nombre:
                parts.append(usuario_nombre)
            filename = '_'.join(parts) + '.xlsx'
        
        # Sanitize filename
        base_name = os.path.basename(filename)
        if not base_name.lower().endswith('.xlsx'):
            base_name = f"{base_name}.xlsx"
        base_name = base_name[:150].replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        # Normalize params
        weeks = max(1, min(int(weeks), 4))
        qr_mode = str(qr_mode or "sheet").strip().lower()
        if qr_mode == "auto":
            qr_mode = "sheet"
        if qr_mode not in ("inline", "sheet", "none"):
            qr_mode = "sheet"
        sheet_norm = (str(sheet).strip()[:64]) if sheet else None
        
        # Generate signature
        ts = int(time.time())
        sig = _sign_excel_view(rutina_id, weeks, base_name, ts, qr_mode=qr_mode, sheet=sheet_norm)
        
        base_url = _get_public_base_url(request)
        
        # Build signed URL with .xlsx extension for Office compatibility
        params = {
            "tenant": tenant,
            "weeks": str(weeks),
            "filename": base_name,
            "qr_mode": qr_mode,
            "sheet": sheet_norm or "",
            "ts": str(ts),
            "sig": sig,
        }
        qs = urllib.parse.urlencode(params, safe="")
        full_url = f"{base_url}/api/rutinas/{rutina_id}/export/excel_view.xlsx?{qs}"
        
        return JSONResponse({"url": full_url})
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error generating Excel view URL")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/rutinas/{rutina_id}/export/excel_view.xlsx")
async def api_rutina_excel_view(
    rutina_id: int,
    request: Request,
    tenant: Optional[str] = None,
    weeks: int = 1,
    filename: Optional[str] = None,
    qr_mode: str = "sheet",
    sheet: Optional[str] = None,
    ts: int = 0,
    sig: Optional[str] = None,
):
    """Public endpoint that serves Excel file after verifying signature.
    
    This endpoint does NOT require authentication - instead it verifies
    the HMAC signature generated by excel_view_url. This allows Office Online
    Viewer to fetch the file directly.
    """
    # Tenant context for multi-tenant DB routing
    try:
        t = str(tenant or "").strip().lower()
    except Exception:
        t = ""
    if t:
        try:
            ok_t, _err = validate_tenant_name(t)
            if ok_t:
                set_current_tenant(t)
            else:
                raise HTTPException(status_code=400, detail="Tenant inválido")
        except HTTPException:
            raise
        except Exception:
            raise HTTPException(status_code=400, detail="Tenant inválido")
    else:
        raise HTTPException(status_code=400, detail="Tenant requerido")

    # Validate signature exists
    if not sig:
        raise HTTPException(status_code=403, detail="Firma requerida")
    
    # Normalize params
    weeks = max(1, min(int(weeks), 4))
    qr_mode = str(qr_mode or "sheet").strip().lower()
    if qr_mode == "auto":
        qr_mode = "sheet"
    if qr_mode not in ("inline", "sheet", "none"):
        qr_mode = "sheet"
    sheet_norm = (str(sheet).strip()[:64]) if sheet else None
    
    # Sanitize filename
    base_name = os.path.basename(filename) if filename else f"rutina_{rutina_id}.xlsx"
    if not base_name.lower().endswith('.xlsx'):
        base_name = f"{base_name}.xlsx"
    base_name = base_name[:150].replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
    
    # Verify timestamp (10 minute window)
    try:
        now = int(time.time())
        if abs(now - int(ts)) > 600:
            raise HTTPException(status_code=403, detail="Link de previsualización expirado")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=403, detail="Timestamp inválido")
    
    # Verify signature
    expected = _sign_excel_view(rutina_id, weeks, base_name, int(ts), qr_mode=qr_mode, sheet=sheet_norm)
    if not hmac.compare_digest(expected, str(sig)):
        raise HTTPException(status_code=403, detail="Firma inválida")
    
    db_gen = None
    session = None
    try:
        db_gen = get_db()
        session = next(db_gen)
        svc = TrainingService(session)
        user_svc = UserService(session)
        rm = RoutineTemplateManager()

        rutina_data = svc.obtener_rutina_completa(rutina_id)
        if not rutina_data:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")

        rutina = Rutina(
            id=rutina_data['id'],
            nombre_rutina=rutina_data.get('nombre_rutina') or rutina_data.get('nombre', ''),
            descripcion=rutina_data.get('descripcion'),
            dias_semana=rutina_data.get('dias_semana', 1),
            uuid_rutina=rutina_data.get('uuid_rutina')
        )

        usuario = None
        if rutina_data.get('usuario_id'):
            usuario = user_svc.get_user(rutina_data['usuario_id'])

        if not usuario:
            user_name = rutina_data.get('usuario_nombre') or 'Usuario'
            usuario = Usuario(nombre=user_name)

        ejercicios_por_dia = _build_exercises_by_day(rutina_data)

        tmp_fd, tmp_path = tempfile.mkstemp(prefix=f"rutina_view_{rutina_id}_", suffix=".xlsx")
        try:
            os.close(tmp_fd)
        except Exception:
            pass

        xlsx_path = rm.generate_routine_excel(
            rutina,
            usuario,
            ejercicios_por_dia,
            output_path=tmp_path,
            weeks=weeks,
            qr_mode=qr_mode,
            sheet=sheet_norm,
        )

        response = FileResponse(
            xlsx_path,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=base_name,
            background=BackgroundTask(_cleanup_file, str(xlsx_path))
        )
        response.headers["Content-Disposition"] = f'inline; filename="{base_name}"'
        response.headers["Cache-Control"] = "private, max-age=60"
        return response
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error generating Excel for preview")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        try:
            if session is not None:
                session.close()
        except Exception:
            pass
        try:
            if db_gen is not None:
                db_gen.close()
        except Exception:
            pass

@router.post("/api/rutinas/export/draft_url")
async def sign_draft_url(
    request: Request,
    _=Depends(require_gestion_access),
    svc: GymConfigService = Depends(get_gym_config_service)
):
    """
    Generate signed URL for draft preview using compressed data in URL.
    Payload: { "rutina": ..., "usuario": ..., "ejercicios": ... }
    """
    try:
        data = await request.json()
        
        # Compress and encode
        json_str = json.dumps(data)
        if len(json_str.encode('utf-8')) > _MAX_PREVIEW_JSON_BYTES:
            raise HTTPException(status_code=413, detail="Payload demasiado grande")
        compressed = zlib.compress(json_str.encode('utf-8'))
        b64_data = base64.urlsafe_b64encode(compressed).decode('utf-8')
        if len(b64_data) > _MAX_PREVIEW_B64_CHARS:
            raise HTTPException(status_code=413, detail="Payload demasiado grande")
        
        ts = int(time.time())
        rnd = secrets.token_hex(4)
        filename = f"draft_{ts}_{rnd}.xlsx"
        
        # Sign
        secret = _get_preview_secret()
        to_sign = f"draft:{b64_data}:{ts}:{filename}:{secret}"
        sig = hmac.new(secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest()
        
        base_url = _get_public_base_url(request)
        url = f"{base_url}/api/public/rutinas/render_draft.xlsx?ts={ts}&data={b64_data}&sig={sig}&filename={filename}"
        
        return JSONResponse({"url": url})
        
    except Exception as e:
        logger.exception("Error signing draft")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/public/rutinas/render_draft.xlsx")
async def render_draft_excel(
    ts: int,
    data: str,
    sig: str,
    filename: Optional[str] = None,
    rm: RoutineTemplateManager = Depends(get_rm)
):
    """
    Public endpoint to render draft excel from URL data.
    """
    try:
        # Verify timestamp
        now = int(time.time())
        if abs(now - ts) > 600: # 10 min
             raise HTTPException(status_code=403, detail="Expired")
             
        # Verify sig
        secret = _get_preview_secret()
        fname = filename or ""
        to_sign = f"draft:{data}:{ts}:{fname}:{secret}"
        expected = hmac.new(secret.encode(), to_sign.encode(), hashlib.sha256).hexdigest()
        
        if not hmac.compare_digest(expected, sig):
             raise HTTPException(status_code=403, detail="Invalid signature")
             
        # Decode (with size limits)
        try:
            json_str = _safe_decompress_url_payload(data)
            if len(json_str.encode('utf-8')) > _MAX_PREVIEW_DECOMPRESSED_BYTES:
                raise HTTPException(status_code=413, detail="Payload demasiado grande")
            payload = json.loads(json_str)
        except Exception:
             raise HTTPException(status_code=400, detail="Corrupt data")

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Payload inválido")
             
        # Build Objects
        rutina_info = payload.get('rutina', {})
        usuario_info = payload.get('usuario', {})
        ejercicios_list = payload.get('ejercicios', [])
        if not isinstance(ejercicios_list, list):
            ejercicios_list = []
        
        rutina = Rutina(
            nombre_rutina=rutina_info.get('nombre', 'Borrador'),
            descripcion=rutina_info.get('descripcion', ''),
            dias_semana=int(rutina_info.get('dias_semana', 1) or 1),
            categoria=rutina_info.get('categoria', 'general')
        )
        
        usuario = Usuario(
            nombre=usuario_info.get('nombre', 'Usuario')
        )
        
        exercises_by_day: Dict[int, List[RutinaEjercicio]] = {}
        # Cap to prevent abuse; generator itself clamps, but we avoid building huge objects
        for ej in ejercicios_list[:200]:
            dia = int(ej.get('dia', 1))
            if dia not in exercises_by_day:
                exercises_by_day[dia] = []

            if len(exercises_by_day[dia]) >= 20:
                continue
            
            # Create Ejercicio obj
            ej_base = Ejercicio(
                nombre=ej.get('nombre_ejercicio', 'Ejercicio'),
                video_url=ej.get('video_url'),
                descripcion=ej.get('descripcion')
            )
            
            re = RutinaEjercicio(
                dia_semana=dia,
                orden=int(ej.get('orden', 0)),
                series=(int(ej.get('series') or 0) if str(ej.get('series') or '').strip().isdigit() else 0),
                repeticiones=str(ej.get('repeticiones', '')),
                ejercicio=ej_base
            )
            exercises_by_day[dia].append(re)
            
        # Extract config from payload
        qr_mode = str(payload.get('qr_mode', 'inline') or 'inline').strip().lower()
        if qr_mode not in ('inline', 'sheet', 'none'):
            qr_mode = 'inline'
        sheet_name = payload.get('sheet') or payload.get('sheet_name') or None
        try:
            sheet_name = (str(sheet_name).strip()[:64]) if sheet_name else None
        except Exception:
            sheet_name = None
        try:
            weeks = int(payload.get('weeks', 1))
        except Exception:
            weeks = 1
        weeks = max(1, min(weeks, 4))

        # Generate to temp
        tmp_fd, tmp_path = tempfile.mkstemp(prefix=f"draft_{ts}_", suffix=".xlsx")
        try:
            os.close(tmp_fd)
        except Exception:
            pass

        xlsx_path = rm.generate_routine_excel(
            rutina,
            usuario,
            exercises_by_day,
            output_path=tmp_path,
            weeks=weeks,
            qr_mode=qr_mode,
            sheet=sheet_name,
        )
        
        base_name = os.path.basename(filename) if filename else f"draft_{ts}.xlsx"
        if not base_name.lower().endswith('.xlsx'):
            base_name = f"{base_name}.xlsx"
        base_name = base_name[:150].replace('\\', '_').replace('/', '_').replace(':', '_').replace('*', '_').replace('?', '_').replace('"', '_').replace('<', '_').replace('>', '_').replace('|', '_')
        
        res = FileResponse(
             xlsx_path,
             media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
             filename=base_name,
             background=BackgroundTask(_cleanup_file, str(xlsx_path))
        )
        res.headers["Content-Disposition"] = f'inline; filename="{base_name}"'
        return res
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Error rendering draft")
        raise HTTPException(status_code=500, detail="Server Error")

@router.get("/api/maintenance_status")
async def api_maintenance_status():
    return {"maintenance": False}

@router.get("/api/suspension_status")
async def api_suspension_status():
    return {"suspended": False}

# --- QR Access Endpoints ---

@router.post("/api/rutinas/verify_qr")
async def api_verify_routine_qr(
    request: Request,
    payload: Dict[str, str],
    svc: TrainingService = Depends(get_training_service)
):
    """
    Validate a Routine QR code UUID and return the full routine details.
    This grants ephemeral access to the routine content.
    """
    import os
    from sqlalchemy import select

    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in ("1", "true", "yes") or os.getenv("ENV", "").lower() in ("dev", "development")
    allow_public = os.getenv("ALLOW_PUBLIC_ROUTINE_QR", "").lower() in ("1", "true", "yes")
    if not (dev_mode or allow_public):
        uid = request.session.get("user_id") or request.session.get("checkin_user_id")
        if not uid:
            msg = "Unauthorized"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=401)

    uuid_val = (payload.get("uuid") or "").strip()
    if not uuid_val:
        msg = "UUID requerido"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=400)

    rutina = svc.obtener_rutina_por_uuid(uuid_val)
    if not rutina:
        msg = "Rutina no encontrada"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=404)

    if not bool(rutina.get("activa", True)):
        msg = "Rutina inactiva"
        return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)

    rid = int(rutina.get("id") or 0)
    usuario_id_rut = rutina.get("usuario_id")
    try:
        usuario_id_rut = int(usuario_id_rut) if usuario_id_rut is not None else None
    except Exception:
        usuario_id_rut = None

    if usuario_id_rut is not None and rid:
        try:
            from src.models.orm_models import Rutina as RutinaModel
            active_ids = list(svc.db.scalars(select(RutinaModel.id).where(RutinaModel.usuario_id == int(usuario_id_rut), RutinaModel.activa.is_(True))).all())
            active_ids = [int(x) for x in (active_ids or []) if x is not None]
            if len(active_ids) != 1 or int(active_ids[0]) != int(rid):
                msg = "QR no corresponde a la rutina activa"
                return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)
        except Exception:
            msg = "Validación de rutina falló"
            return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)

    sess_uid = request.session.get("user_id") or request.session.get("checkin_user_id")
    if sess_uid is not None and usuario_id_rut is not None:
        try:
            if int(sess_uid) != int(usuario_id_rut):
                msg = "QR no corresponde a tu rutina"
                return JSONResponse({"ok": False, "mensaje": msg, "error": msg, "success": False, "message": msg}, status_code=403)
        except Exception:
            pass

    try:
        request.session["qr_access_rutina_id"] = rid
        request.session["qr_access_until"] = int(time.time()) + 24 * 60 * 60
    except Exception:
        pass

    return {
        "ok": True,
        "rutina": rutina,
        "access_granted": True,
        "expires_in_seconds": 86400
    }

@router.get("/api/rutinas/qr_scan/{uuid_val}")
async def api_handle_qr_scan_redirect(
    uuid_val: str
):
    """
    Generic endpoint for generic QR Code Scanners.
    Redirects to the WebApp Dashboard with a specific action parameter.
    """
    try:
        base_url = get_webapp_base_url()
    except Exception:
        base_url = "https://ironhub.motiona.xyz"
        
    redirect_url = f"{str(base_url).rstrip('/')}/usuario?action=scan&uuid={uuid_val}"
    return RedirectResponse(url=redirect_url)
