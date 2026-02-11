import logging
import os
import json
import time
import secrets
import base64
import zlib
import uuid
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from fastapi import (
    APIRouter,
    Request,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Response,
)
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session


# Services
from src.dependencies import (
    get_admin_db,
    get_claims,
    require_gestion_access,
    require_owner,
    require_sucursal_selected,
    get_db,
    get_gym_config_service,
    get_clase_service,
    get_training_service,
    require_feature,
    require_scope_gestion,
)

from src.models.orm_models import (
    Rutina,
    Usuario,
    RutinaEjercicio,
    Ejercicio,
    PlantillaRutina,
    GimnasioPlantilla,
)
from src.database.tenant_connection import (
    get_current_tenant,
    get_current_tenant_gym_id,
    _get_tenant_info_from_admin,
)
from src.database.raw_manager import RawPostgresManager
from src.utils import (
    get_gym_name,
    _resolve_logo_url,
)
from src.services.gym_config_service import GymConfigService
from src.services.clase_service import ClaseService
from src.services.training_service import TrainingService
from src.services.b2_storage import simple_upload as b2_upload
from src.services.feature_flags_service import FeatureFlagsService
from src.services.pdf_engine import PDFEngine
from src.services.template_validator import TemplateValidator

router = APIRouter()
logger = logging.getLogger(__name__)

ATTENDANCE_ALLOW_MULTIPLE_KEY = "attendance_allow_multiple_per_day"


class FeatureFlagsPayload(BaseModel):
    flags: Dict[str, Any]


def _parse_bool(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    if v is None:
        return False
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip().lower()
    if not s:
        return False
    if s in ("1", "true", "yes", "y", "on"):
        return True
    if s in ("0", "false", "no", "n", "off"):
        return False
    return False


_MAX_PREVIEW_JSON_BYTES = int(
    os.environ.get("PREVIEW_MAX_JSON_BYTES", "300000")
)  # ~300KB
_MAX_PREVIEW_B64_CHARS = int(
    os.environ.get("PREVIEW_MAX_B64_CHARS", "400000")
)  # ~400KB chars
_MAX_PREVIEW_DECOMPRESSED_BYTES = int(
    os.environ.get("PREVIEW_MAX_DECOMPRESSED_BYTES", "1200000")
)  # ~1.2MB
_PREVIEW_SECRET_CACHE: Optional[str] = None


def _cleanup_file(path: str) -> None:
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _build_rutina_pdf_data(
    rutina_data: Dict[str, Any],
    user_override: Optional[str] = None,
    current_week: int = 1,
) -> Dict[str, Any]:
    try:
        usuario_nombre = str(user_override or rutina_data.get("usuario_nombre") or "").strip() or "Usuario"
    except Exception:
        usuario_nombre = "Usuario"

    dias_out: List[Dict[str, Any]] = []
    dias = rutina_data.get("dias") or []
    for d in dias:
        if not isinstance(d, dict):
            continue
        try:
            dnum = int(d.get("numero") or d.get("dayNumber") or d.get("dia") or 1)
        except Exception:
            dnum = 1
        ejercicios_out: List[Dict[str, Any]] = []
        for ex in (d.get("ejercicios") or []):
            if not isinstance(ex, dict):
                continue
            nombre = ex.get("nombre") or ex.get("ejercicio_nombre") or ex.get("nombre_ejercicio")
            if not nombre:
                nombre = "Ejercicio"
            ejercicios_out.append(
                {
                    "nombre": nombre,
                    "series": ex.get("series"),
                    "repeticiones": ex.get("repeticiones"),
                    "descanso": ex.get("descanso"),
                    "notas": ex.get("notas"),
                    "orden": ex.get("orden"),
                    "video_url": ex.get("video_url"),
                }
            )
        dias_out.append({"numero": dnum, "nombre": d.get("nombre") or f"Día {dnum}", "ejercicios": ejercicios_out})

    out: Dict[str, Any] = {
        "rutina_id": rutina_data.get("id"),
        "uuid_rutina": rutina_data.get("uuid_rutina"),
        "nombre_rutina": rutina_data.get("nombre_rutina") or rutina_data.get("nombre") or f"Rutina {rutina_data.get('id')}",
        "descripcion": rutina_data.get("descripcion") or "",
        "categoria": rutina_data.get("categoria") or "",
        "dias_semana": rutina_data.get("dias_semana") or (len(dias_out) if dias_out else 1),
        "usuario": {
            "id": rutina_data.get("usuario_id"),
            "nombre": usuario_nombre,
        },
        "usuario_nombre": usuario_nombre,
        "dias": dias_out,
        "current_week": int(current_week or 1),
    }
    try:
        out["gym_name"] = get_gym_name()
    except Exception:
        pass
    return out


def _select_template_config_for_rutina(
    db: Session,
    template_id: Optional[int],
    qr_mode: str,
) -> Dict[str, Any]:
    template: Optional[PlantillaRutina] = None

    if template_id is not None:
        template = db.query(PlantillaRutina).filter(PlantillaRutina.id == int(template_id)).first()
        if not template or not bool(getattr(template, "activa", True)):
            raise HTTPException(status_code=404, detail="Plantilla no encontrada")
        config = getattr(template, "configuracion", None) or {}
    else:
        gimnasio_id = get_current_tenant_gym_id()
        if not gimnasio_id:
            raise HTTPException(status_code=400, detail="No se pudo determinar el gimnasio del tenant")
        assignment = (
            db.query(GimnasioPlantilla)
            .filter(GimnasioPlantilla.gimnasio_id == int(gimnasio_id), GimnasioPlantilla.activa == True)
            .order_by(GimnasioPlantilla.prioridad.asc(), GimnasioPlantilla.fecha_asignacion.desc())
            .first()
        )
        if assignment and assignment.configuracion_personalizada:
            config = assignment.configuracion_personalizada
        elif assignment and assignment.plantilla:
            config = assignment.plantilla.configuracion
        else:
            template = (
                db.query(PlantillaRutina)
                .filter(PlantillaRutina.activa == True, PlantillaRutina.publica == True)
                .order_by(PlantillaRutina.uso_count.desc(), PlantillaRutina.id.asc())
                .first()
            )
            if not template:
                raise HTTPException(status_code=404, detail="No hay plantillas disponibles")
            config = getattr(template, "configuracion", None) or {}

    try:
        qr_norm = str(qr_mode or "auto").strip().lower()
    except Exception:
        qr_norm = "auto"
    if qr_norm == "auto":
        qr_norm = "inline"
    if qr_norm in ("separate_sheet", "sheet", "separate"):
        qr_norm = "separate"
    if qr_norm not in ("header", "footer", "inline", "separate", "none"):
        qr_norm = "inline"

    cfg = dict(config or {})
    qr_cfg = dict(cfg.get("qr_code") or {})
    if qr_norm == "none":
        qr_cfg["enabled"] = False
    else:
        qr_cfg.setdefault("enabled", True)
        qr_cfg.setdefault("data_source", "routine_uuid")
        qr_cfg["position"] = qr_norm
    cfg["qr_code"] = qr_cfg

    validator = TemplateValidator()
    validation = validator.validate_template(cfg)
    if not validation.is_valid:
        messages = [str(e.get("message") or "") for e in (validation.errors or []) if isinstance(e, dict)]
        raise HTTPException(status_code=500, detail="Plantilla inválida: " + "; ".join([m for m in messages if m]))

    return cfg


def _cleanup_files(*paths: str) -> None:
    for p in paths:
        try:
            _cleanup_file(p)
        except Exception:
            pass


def _sanitize_download_filename(
    filename: Optional[str], default_name: str, ext: str
) -> str:
    base = os.path.basename(filename) if filename else default_name
    if not base.lower().endswith(ext.lower()):
        base = f"{base}{ext}"
    base = (
        base[:150]
        .replace("\\", "_")
        .replace("/", "_")
        .replace(":", "_")
        .replace("*", "_")
        .replace("?", "_")
        .replace('"', "_")
        .replace("<", "_")
        .replace(">", "_")
        .replace("|", "_")
    )
    return base


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


def _normalize_rutina_export_params(
    weeks: int, qr_mode: str, sheet: Optional[str]
) -> tuple[int, str, Optional[str]]:
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


def _add_office_viewer_headers(res: Response) -> Response:
    res.headers["Access-Control-Allow-Origin"] = "*"
    res.headers["Access-Control-Allow-Methods"] = "GET,HEAD,OPTIONS"
    res.headers["Access-Control-Allow-Headers"] = "*"
    res.headers["Access-Control-Expose-Headers"] = (
        "Content-Disposition, Content-Length, Content-Type"
    )
    res.headers["Cache-Control"] = "public, max-age=60"
    return res


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
        part = dobj.decompress(
            compressed[i : i + chunk_size],
            max_length=max(0, _MAX_PREVIEW_DECOMPRESSED_BYTES - out_len),
        )
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


# --- API Configuración ---


@router.get("/api/gym/data")
async def api_gym_data(
    _=Depends(require_gestion_access),
    svc: GymConfigService = Depends(get_gym_config_service),
):
    """Get gym configuration using SQLAlchemy."""
    try:
        config = svc.obtener_configuracion_gimnasio()
        if config:
            # Frontend contract expects { nombre, logo_url }
            try:
                if isinstance(config, dict):
                    if "nombre" not in config:
                        config["nombre"] = config.get("gym_name") or config.get(
                            "nombre"
                        )
                    if "gym_name" not in config and config.get("nombre"):
                        config["gym_name"] = config.get("nombre")
                    if "gym_logo_url" not in config and config.get("logo_url"):
                        config["gym_logo_url"] = config.get("logo_url")
            except Exception:
                pass
            try:
                lu = config.get("logo_url") if isinstance(config, dict) else None
                if (
                    isinstance(lu, str)
                    and lu.strip()
                    and not lu.strip().startswith("http")
                    and not lu.strip().startswith("/")
                ):
                    from src.services.b2_storage import get_file_url

                    config["logo_url"] = get_file_url(lu.strip())
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


@router.get("/api/gym/feature-flags")
async def api_get_feature_flags(
    request: Request,
    _=Depends(require_gestion_access),
    db: Session = Depends(get_db),
    scope: str = "gym",
):
    try:
        sid = None
        try:
            if str(scope or "").strip().lower() in ("branch", "sucursal"):
                sid = request.session.get("sucursal_id")
        except Exception:
            sid = None
        flags = FeatureFlagsService(db).get_flags(sucursal_id=sid)
        return {"ok": True, "flags": flags}
    except Exception:
        return {"ok": True, "flags": {}}


@router.post("/api/gym/feature-flags")
async def api_set_feature_flags(
    payload: FeatureFlagsPayload,
    request: Request,
    _=Depends(require_owner),
    db: Session = Depends(get_db),
    scope: str = "gym",
):
    flags_in = payload.flags if isinstance(payload.flags, dict) else {}
    sid = None
    try:
        if str(scope or "").strip().lower() in ("branch", "sucursal"):
            sid = request.session.get("sucursal_id")
    except Exception:
        sid = None
    FeatureFlagsService(db).set_flags(flags_in, sucursal_id=sid)
    return {"ok": True, "flags": FeatureFlagsService(db).get_flags(sucursal_id=sid)}


@router.post("/api/gym/update")
async def api_gym_update(
    request: Request,
    _=Depends(require_owner),
    svc: GymConfigService = Depends(get_gym_config_service),
):
    """Update gym configuration using SQLAlchemy."""
    try:
        data = await request.json()
        name = str(data.get("gym_name", "")).strip()
        address = str(data.get("gym_address", "")).strip()

        if not name:
            return JSONResponse(
                {"ok": False, "error": "Nombre inválido"}, status_code=400
            )

        updates = {"gym_name": name}
        if address:
            updates["gym_address"] = address

        if svc.actualizar_configuracion_gimnasio(updates):
            return JSONResponse({"ok": True})
        return JSONResponse({"ok": False, "error": "Error guardando"}, status_code=500)
    except Exception as e:
        logger.error(f"Error updating gym: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/owner/gym/settings")
async def api_owner_gym_settings(
    _=Depends(require_owner),
    svc: GymConfigService = Depends(get_gym_config_service),
):
    try:
        cfg = svc.obtener_configuracion_gimnasio() or {}
        allow_multiple = _parse_bool(cfg.get(ATTENDANCE_ALLOW_MULTIPLE_KEY, False))
        return {"ok": True, "settings": {ATTENDANCE_ALLOW_MULTIPLE_KEY: allow_multiple}}
    except Exception as e:
        logger.error(f"Error getting owner gym settings: {e}")
        return JSONResponse(
            {"ok": False, "error": str(e), "settings": {}}, status_code=500
        )


@router.post("/api/owner/gym/settings")
async def api_owner_update_gym_settings(
    request: Request,
    _=Depends(require_owner),
    svc: GymConfigService = Depends(get_gym_config_service),
):
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="Invalid payload")
    if ATTENDANCE_ALLOW_MULTIPLE_KEY not in payload:
        raise HTTPException(
            status_code=400, detail=f"{ATTENDANCE_ALLOW_MULTIPLE_KEY} requerido"
        )
    allow_multiple = _parse_bool(payload.get(ATTENDANCE_ALLOW_MULTIPLE_KEY))
    ok = svc.actualizar_configuracion_gimnasio(
        {ATTENDANCE_ALLOW_MULTIPLE_KEY: allow_multiple}
    )
    if not ok:
        return JSONResponse({"ok": False, "error": "Error guardando"}, status_code=500)
    try:
        admin_params = {
            "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
            "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
            "database": os.getenv(
                "ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")
            ),
            "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
            "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
            "sslmode": os.getenv(
                "ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")
            ),
        }
        gym_id = get_current_tenant_gym_id()
        if gym_id:
            db = RawPostgresManager(connection_params=admin_params)
            with db.get_connection_context() as conn:
                cur = conn.cursor()
                cur.execute(
                    "INSERT INTO admin_audit (actor_username, action, gym_id, details) VALUES (%s, %s, %s, %s)",
                    (
                        f"owner:{request.session.get('user_id') or ''}",
                        "owner_set_attendance_policy",
                        int(gym_id),
                        json.dumps(
                            {"attendance_allow_multiple_per_day": bool(allow_multiple)},
                            ensure_ascii=False,
                        ),
                    ),
                )
                conn.commit()
    except Exception:
        pass
    return {"ok": True, "settings": {ATTENDANCE_ALLOW_MULTIPLE_KEY: allow_multiple}}


@router.get("/api/owner/gym/billing")
async def api_owner_gym_billing(_=Depends(require_owner)):
    tenant = get_current_tenant() or ""
    info = _get_tenant_info_from_admin(tenant.strip().lower())
    if not info or not info.get("gym_id"):
        raise HTTPException(status_code=404, detail="Gym not found")

    admin_params = {
        "host": os.getenv("ADMIN_DB_HOST", os.getenv("DB_HOST", "localhost")),
        "port": int(os.getenv("ADMIN_DB_PORT", os.getenv("DB_PORT", 5432))),
        "database": os.getenv("ADMIN_DB_NAME", os.getenv("DB_NAME", "ironhub_admin")),
        "user": os.getenv("ADMIN_DB_USER", os.getenv("DB_USER", "postgres")),
        "password": os.getenv("ADMIN_DB_PASSWORD", os.getenv("DB_PASSWORD", "")),
        "sslmode": os.getenv("ADMIN_DB_SSLMODE", os.getenv("DB_SSLMODE", "require")),
    }

    gym_id = int(info["gym_id"])
    db = RawPostgresManager(connection_params=admin_params)
    with db.get_connection_context() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT
                gs.id,
                gs.plan_id,
                gs.start_date,
                gs.next_due_date,
                gs.status,
                gs.created_at,
                p.name AS plan_name,
                p.amount AS plan_amount,
                p.currency AS plan_currency,
                p.period_days AS plan_period_days,
                p.active AS plan_active
            FROM gym_subscriptions gs
            JOIN plans p ON p.id = gs.plan_id
            WHERE gs.gym_id = %s
            ORDER BY gs.id DESC
            LIMIT 1
            """,
            (gym_id,),
        )
        srow = cur.fetchone()
        subscription = None
        if srow:
            subscription = {
                "id": srow[0],
                "plan_id": srow[1],
                "start_date": srow[2].isoformat() if srow[2] else None,
                "next_due_date": srow[3].isoformat() if srow[3] else None,
                "status": srow[4],
                "created_at": srow[5].isoformat() if srow[5] else None,
                "plan": {
                    "id": srow[1],
                    "name": srow[6],
                    "amount": float(srow[7] or 0),
                    "currency": srow[8],
                    "period_days": int(srow[9] or 0),
                    "active": bool(srow[10]),
                },
            }

        cur.execute(
            """
            SELECT id, plan, plan_id, amount, currency, paid_at, valid_until, status, notes, provider, external_reference
            FROM gym_payments
            WHERE gym_id = %s
            ORDER BY paid_at DESC
            LIMIT 20
            """,
            (gym_id,),
        )
        payments = []
        for r in cur.fetchall() or []:
            payments.append(
                {
                    "id": r[0],
                    "plan": r[1],
                    "plan_id": r[2],
                    "amount": float(r[3] or 0),
                    "currency": r[4],
                    "paid_at": r[5].isoformat() if r[5] else None,
                    "valid_until": r[6].isoformat() if r[6] else None,
                    "status": r[7],
                    "notes": r[8],
                    "provider": r[9],
                    "external_reference": r[10],
                }
            )

    return {
        "ok": True,
        "gym": {
            "gym_id": gym_id,
            "tenant": tenant,
            "nombre": info.get("nombre"),
            "status": info.get("status"),
            "suspended_reason": info.get("suspended_reason"),
            "suspended_until": info.get("suspended_until").isoformat()
            if info.get("suspended_until")
            else None,
        },
        "subscription": subscription,
        "payments": payments,
    }


@router.post("/api/gym/logo")
async def api_gym_logo(
    request: Request,
    file: UploadFile = File(...),
    _=Depends(require_gestion_access),
    svc: GymConfigService = Depends(get_gym_config_service),
):
    """Upload gym logo using SQLAlchemy for storage."""
    try:
        ctype = str(getattr(file, "content_type", "") or "").lower()
        if ctype not in ("image/png", "image/svg+xml", "image/jpeg", "image/jpg"):
            return JSONResponse(
                {"ok": False, "error": "Formato no soportado. Use PNG, JPG o SVG"},
                status_code=400,
            )

        data = await file.read()
        if not data:
            return JSONResponse(
                {"ok": False, "error": "Archivo vacío"}, status_code=400
            )

        public_url = None

        # 1. Try Cloud Storage (B2 + Cloudflare)
        try:
            from src.utils import _get_tenant_from_request

            tenant = _get_tenant_from_request(request) or "common"

            ext = ".png"
            if "svg" in ctype:
                ext = ".svg"
            elif "jpeg" in ctype or "jpg" in ctype:
                ext = ".jpg"

            filename = f"gym_logo_{int(time.time())}{ext}"
            uploaded_url = b2_upload(data, filename, ctype, subfolder=f"logos/{tenant}")
            if uploaded_url:
                public_url = uploaded_url
        except Exception as e:
            logger.error(f"Error uploading logo to cloud storage: {e}")

        # 2. Fallback to Local Storage if cloud failed
        if not public_url:
            return JSONResponse(
                {"ok": False, "error": "Error subiendo logo"}, status_code=500
            )

        if public_url:
            svc.actualizar_logo_url(public_url)

        return JSONResponse({"ok": True, "logo_url": public_url})
    except Exception as e:
        logger.error(f"Error uploading gym logo: {e}")
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/api/gym/subscription")
async def api_gym_subscription(
    request: Request,
    _=Depends(require_gestion_access),
    svc: GymConfigService = Depends(get_gym_config_service),
):
    """Get real gym subscription status from Admin DB."""
    try:
        status = svc.get_subscription_status()
        if not status:
            # Fallback for error or no data
            return {"active": True, "plan": "free", "status": "fallback"}

        # Normalize for frontend
        is_active = status.get("status") == "active"
        return {
            "active": is_active,
            "plan": status.get("plan"),
            "valid_until": status.get("valid_until"),
            "days_remaining": status.get("days_remaining"),
            "status": status.get("status"),
        }
    except Exception as e:
        logger.error(f"Error getting subscription: {e}")
        return {"active": True, "plan": "unknown", "error": str(e)}


# --- Helpers for Routine Export / Preview ---


def _get_preview_secret() -> str:
    global _PREVIEW_SECRET_CACHE
    try:
        cached = str(_PREVIEW_SECRET_CACHE or "").strip()
    except Exception:
        cached = ""
    if cached:
        return cached

    candidates = []
    for k in ("WEBAPP_PREVIEW_SECRET", "SESSION_SECRET", "SECRET_KEY"):
        try:
            v = os.getenv(k, "").strip()
            if v:
                candidates.append(v)
        except Exception:
            continue

    if candidates:
        _PREVIEW_SECRET_CACHE = candidates[0]
        return _PREVIEW_SECRET_CACHE

    is_prod = False
    try:
        if (
            os.getenv("VERCEL")
            or os.getenv("VERCEL_URL")
            or os.getenv("NODE_ENV") == "production"
        ):
            is_prod = True
    except Exception:
        is_prod = False
    try:
        if os.getenv("DEVELOPMENT_MODE", "").lower() in ("1", "true", "yes"):
            is_prod = False
    except Exception:
        pass

    if is_prod:
        raise RuntimeError(
            "Preview secret no configurado (WEBAPP_PREVIEW_SECRET/SESSION_SECRET/SECRET_KEY)"
        )

    _PREVIEW_SECRET_CACHE = secrets.token_hex(32)
    return _PREVIEW_SECRET_CACHE

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


def _encode_preview_payload(payload: Dict[str, Any]) -> str:
    try:
        compact: Dict[str, Any] = {
            "n": payload.get("nombre_rutina"),
            "d": payload.get("descripcion"),
            "ds": payload.get("dias_semana"),
            "c": payload.get("categoria"),
            "ui": (
                payload.get("usuario_id")
                if payload.get("usuario_id") is not None
                else (payload.get("usuario") or {}).get("id")
            ),
            "un": (
                payload.get("usuario_nombre_override")
                if (payload.get("usuario_nombre_override") not in (None, ""))
                else ((payload.get("usuario") or {}).get("nombre"))
            ),
            "ud": (
                payload.get("usuario_dni")
                if payload.get("usuario_dni") is not None
                else (payload.get("usuario") or {}).get("dni")
            ),
            "ut": (
                payload.get("usuario_telefono")
                if payload.get("usuario_telefono") is not None
                else (payload.get("usuario") or {}).get("telefono")
            ),
            "e": [
                [
                    int(x.get("ejercicio_id")),
                    int(x.get("dia_semana", 1)),
                    x.get("series"),
                    x.get("repeticiones"),
                    int(x.get("orden", 1)),
                    (
                        (x.get("nombre_ejercicio"))
                        or (
                            (x.get("ejercicio") or {}).get("nombre")
                            if isinstance(x.get("ejercicio"), dict)
                            else None
                        )
                        or None
                    ),
                ]
                for x in (payload.get("ejercicios") or [])
            ],
        }
        raw = json.dumps(compact, separators=(",", ":")).encode("utf-8")
        comp = zlib.compress(raw, level=6)
        return base64.urlsafe_b64encode(comp).decode("ascii")
    except Exception:
        try:
            return base64.urlsafe_b64encode(
                json.dumps(payload, separators=(",", ":")).encode("utf-8")
            ).decode("ascii")
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
            for arr in obj.get("e") or []:
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
        global _ejercicios_catalog_cache
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
                        eid = int(r.get("id") or 0)
                    except Exception:
                        eid = 0
                    name = (r.get("nombre") or "").strip().lower()
                    info = {
                        "video_url": r.get("video_url"),
                        "video_mime": r.get("video_mime"),
                    }
                    if eid:
                        by_id[eid] = info
                    if name:
                        by_name[name] = info
            else:
                try:
                    p = Path(__file__).resolve().parent.parent / "ejercicios.json"
                    if p.exists():
                        data = json.loads(p.read_text(encoding="utf-8"))
                        for it in data or []:
                            try:
                                eid = int(it.get("id") or 0)
                            except Exception:
                                eid = 0
                            name = (it.get("nombre") or "").strip().lower()
                            info = {
                                "video_url": it.get("video_url"),
                                "video_mime": it.get("video_mime"),
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
                info = cat.get("by_id", {}).get(int(ejercicio_id))
            except Exception:
                info = None
        if (not info) and nombre:
            try:
                info = cat.get("by_name", {}).get(str(nombre).strip().lower())
            except Exception:
                info = None
        return info or {"video_url": None, "video_mime": None}
    except Exception:
        return {"video_url": None, "video_mime": None}


def _build_exercises_by_day(rutina: Any) -> Dict[int, list]:
    try:
        grupos: Dict[int, list] = {}
        ejercicios = []
        if isinstance(rutina, dict):
            ejercicios = rutina.get("ejercicios") or []
            if not ejercicios:
                dias = rutina.get("dias") or []
                flat: list[dict] = []
                for d in dias or []:
                    try:
                        dnum = int(
                            d.get("numero") or d.get("dayNumber") or d.get("dia") or 1
                        )
                    except Exception:
                        dnum = 1
                    for ex in d.get("ejercicios") or []:
                        if not isinstance(ex, dict):
                            continue
                        flat.append(
                            {
                                "id": ex.get("id"),
                                "rutina_id": rutina.get("id"),
                                "ejercicio_id": ex.get("ejercicio_id")
                                or ex.get("id_ejercicio"),
                                "dia_semana": ex.get("dia_semana")
                                or ex.get("dia")
                                or dnum,
                                "series": ex.get("series"),
                                "repeticiones": ex.get("repeticiones"),
                                "orden": ex.get("orden"),
                                "nombre_ejercicio": ex.get("nombre_ejercicio")
                                or ex.get("ejercicio_nombre")
                                or ex.get("nombre"),
                                "ejercicio": ex.get("ejercicio"),
                            }
                        )
                ejercicios = flat
        else:
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
                        ejercicio=None,
                    )
                    ej = r.get("ejercicio")
                    try:
                        if isinstance(ej, dict):
                            r_obj.ejercicio = Ejercicio(
                                id=int(ej.get("id") or r_obj.ejercicio_id or 0),
                                nombre=str(ej.get("nombre") or ""),
                                grupo_muscular=ej.get("grupo_muscular"),
                                descripcion=ej.get("descripcion"),
                            )
                        elif ej is not None:
                            r_obj.ejercicio = ej  # type: ignore
                        else:
                            r_obj.ejercicio = Ejercicio(id=int(r_obj.ejercicio_id or 0))
                    except Exception:
                        r_obj.ejercicio = None
                    nombre_actual = (
                        r.get("nombre_ejercicio")
                        or r.get("ejercicio_nombre")
                        or r.get("nombre")
                    )
                    if not nombre_actual:
                        nombre_nested = (
                            getattr(r_obj.ejercicio, "nombre", None)
                            if r_obj.ejercicio is not None
                            else None
                        )
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
                        nombre_nested = getattr(
                            getattr(r, "ejercicio", None), "nombre", None
                        )
                        if nombre_nested:
                            try:
                                setattr(r, "nombre_ejercicio", nombre_nested)
                            except Exception:
                                pass
                        else:
                            eid = getattr(r, "ejercicio_id", None)
                            try:
                                setattr(
                                    r,
                                    "nombre_ejercicio",
                                    f"Ejercicio {eid}"
                                    if eid is not None
                                    else "Ejercicio",
                                )
                            except Exception:
                                pass
            except Exception:
                pass
            dia = (
                getattr(r, "dia_semana", None)
                if not isinstance(r, dict)
                else r.get("dia_semana")
            )
            if dia is None:
                continue
            try:
                grupos.setdefault(int(dia), []).append(r)
            except Exception:
                continue
        for dia, arr in grupos.items():
            try:
                arr.sort(
                    key=lambda e: (
                        int(getattr(e, "orden", 0) or 0),
                        str(getattr(e, "nombre_ejercicio", "") or ""),
                    )
                )
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
        categoria=(r_raw.get("categoria") or "general"),
    )

    # Add uuid
    try:
        ruuid = (
            r_raw.get("uuid_rutina") or r_raw.get("uuid") or payload.get("uuid_rutina")
        )
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
                    orden=int(it.get("orden") or idx + 1),
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
    svc: GymConfigService = Depends(get_gym_config_service),
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
    svc: GymConfigService = Depends(get_gym_config_service),
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
    svc: GymConfigService = Depends(get_gym_config_service),
):
    """Legacy gym logo upload endpoint using SQLAlchemy."""
    try:
        ctype = str(getattr(file, "content_type", "") or "").lower()
        allowed = {
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/svg+xml": ".svg",
        }
        if ctype not in allowed:
            return JSONResponse(
                {"ok": False, "error": "Formato no soportado. Use PNG, JPG o SVG"},
                status_code=400,
            )

        content = await file.read()
        if not content:
            return JSONResponse(
                {"ok": False, "error": "Archivo vacío"}, status_code=400
            )
        max_bytes = int(os.environ.get("MAX_LOGO_BYTES", "5000000"))
        if len(content) > max_bytes:
            return JSONResponse(
                {"ok": False, "error": "Logo demasiado grande"}, status_code=400
            )

        ext = allowed.get(ctype, ".png")
        filename = f"gym_logo_{int(time.time())}{ext}"

        try:
            from src.utils import _get_tenant_from_request

            tenant = _get_tenant_from_request(request)
        except Exception:
            tenant = None
        if not tenant:
            tenant = "common"

        uploaded_url = b2_upload(content, filename, ctype, subfolder=f"logos/{tenant}")
        if not uploaded_url:
            return JSONResponse(
                {"ok": False, "error": "Error subiendo logo"}, status_code=500
            )

        svc.actualizar_configuracion("gym_logo_url", uploaded_url)
        return {"ok": True, "url": uploaded_url}
    except Exception as e:
        logger.error(f"Error uploading gym logo: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


# --- API Clases ---


@router.get(
    "/api/clases",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:read")),
    ],
)
async def api_clases(
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
):
    """Get all classes using SQLAlchemy."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        clases = svc.obtener_clases(sucursal_id=sucursal_id)
        return {"clases": clases}
    except Exception as e:
        logger.error(f"Error getting clases: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.post(
    "/api/clases",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:write")),
    ],
)
async def api_clases_create(
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
):
    """Create a class using SQLAlchemy."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        descripcion = (payload.get("descripcion") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")

        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        shared = False
        try:
            if "shared" in payload:
                shared = bool(payload.get("shared"))
        except Exception:
            shared = False
        sucursal_for_new = None if shared else sucursal_id

        new_id = svc.crear_clase(
            {"nombre": nombre, "descripcion": descripcion, "activo": True, "sucursal_id": sucursal_for_new}
        )

        if new_id:
            return {"ok": True, "id": int(new_id)}
        msg = "No se pudo crear"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/api/clases/{clase_id}",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:read")),
    ],
)
async def api_clase_get(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
):
    """Get a single clase by ID."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        clase = svc.obtener_clase(clase_id, sucursal_id=sucursal_id)
        if not clase:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        return clase
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put(
    "/api/clases/{clase_id}",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:write")),
    ],
)
async def api_clase_update(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
):
    """Update a clase."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        existing = svc.obtener_clase(clase_id, sucursal_id=sucursal_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        payload = await request.json()
        success = svc.actualizar_clase(clase_id, payload)
        if success:
            clase = svc.obtener_clase(clase_id, sucursal_id=sucursal_id)
            return clase or {"ok": True}
        return JSONResponse({"error": "No se pudo actualizar"}, status_code=400)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating clase: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/api/clases/{clase_id}",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:write")),
    ],
)
async def api_clase_delete(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
):
    """Delete a clase."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        existing = svc.obtener_clase(clase_id, sucursal_id=sucursal_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
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


@router.get(
    "/api/clases/{clase_id}/bloques",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:read")),
    ],
)
async def api_clase_bloques_list(
    clase_id: int,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
):
    """Get workout blocks for a class using SQLAlchemy."""
    try:
        return svc.obtener_clase_bloques(clase_id)
    except Exception as e:
        logger.error(f"Error listing bloques: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.get(
    "/api/clases/{clase_id}/bloques/{bloque_id}",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:read")),
    ],
)
async def api_clase_bloque_items(
    clase_id: int,
    bloque_id: int,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
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


@router.post(
    "/api/clases/{clase_id}/bloques",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:write")),
    ],
)
async def api_clase_bloque_create(
    clase_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
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
            formatted_items.append(
                {
                    "ejercicio_id": eid,
                    "orden": int(it.get("orden") or idx),
                    "series": int(it.get("series") or 0),
                    "repeticiones": str(it.get("repeticiones") or ""),
                    "descanso_segundos": int(it.get("descanso_segundos") or 0),
                    "notas": str(it.get("notas") or ""),
                }
            )

        bloque_id = svc.crear_clase_bloque(clase_id, nombre, formatted_items)
        if bloque_id:
            return {"ok": True, "id": bloque_id}
        raise HTTPException(status_code=404, detail="Clase no encontrada")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating bloque: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.put(
    "/api/clases/{clase_id}/bloques/{bloque_id}",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:write")),
    ],
)
async def api_clase_bloque_update(
    clase_id: int,
    bloque_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
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
            formatted_items.append(
                {
                    "ejercicio_id": eid,
                    "orden": int(it.get("orden") or idx),
                    "series": int(it.get("series") or 0),
                    "repeticiones": str(it.get("repeticiones") or ""),
                    "descanso_segundos": int(it.get("descanso_segundos") or 0),
                    "notas": str(it.get("notas") or ""),
                }
            )

        if svc.actualizar_clase_bloque(bloque_id, nombre, formatted_items):
            return {"ok": True}
        return JSONResponse({"error": "No se pudo actualizar"}, status_code=500)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating bloque: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)


@router.delete(
    "/api/clases/{clase_id}/bloques/{bloque_id}",
    dependencies=[
        Depends(require_feature("clases")),
        Depends(require_scope_gestion("clases:write")),
    ],
)
async def api_clase_bloque_delete(
    clase_id: int,
    bloque_id: int,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: ClaseService = Depends(get_clase_service),
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


@router.get("/api/ejercicios", dependencies=[Depends(require_feature("ejercicios"))])
async def api_ejercicios_list(
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Get all exercises using SQLAlchemy with optional filters."""
    try:
        search = request.query_params.get("search")
        grupo = request.query_params.get("grupo")
        objetivo = request.query_params.get("objetivo")

        limit_q = request.query_params.get("limit")
        offset_q = request.query_params.get("offset")
        if limit_q is not None or offset_q is not None:
            sucursal_id = request.session.get("sucursal_id")
            try:
                sucursal_id = int(sucursal_id) if sucursal_id is not None else None
            except Exception:
                sucursal_id = None
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

            out = svc.obtener_ejercicios_paginados(
                search=str(search or ""),
                grupo=grupo,
                objetivo=objetivo,
                sucursal_id=sucursal_id,
                limit=limit_n,
                offset=offset_n,
            )
            return {
                "ejercicios": list(out.get("items") or []),
                "total": int(out.get("total") or 0),
                "limit": limit_n,
                "offset": offset_n,
            }

        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        return {
            "ejercicios": svc.obtener_ejercicios(
                search=search, grupo=grupo, objetivo=objetivo, sucursal_id=sucursal_id
            )
        }
    except Exception as e:
        logger.error(f"Error listing ejercicios: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post("/api/ejercicios", dependencies=[Depends(require_feature("ejercicios"))])
async def api_ejercicios_create(
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Create an exercise using SQLAlchemy."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")

        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        shared = True
        try:
            if "shared" in payload:
                shared = bool(payload.get("shared"))
        except Exception:
            shared = True
        sucursal_for_new = None if shared else sucursal_id

        new_id = svc.crear_ejercicio(
            {
                "nombre": nombre,
                "grupo_muscular": (payload.get("grupo_muscular") or "").strip(),
                "objetivo": (payload.get("objetivo") or "general"),
                "equipamiento": (payload.get("equipamiento") or "").strip() or None,
                "variantes": (payload.get("variantes") or "").strip() or None,
                "descripcion": (payload.get("descripcion") or "").strip() or None,
                "video_url": payload.get("video_url"),
                "video_mime": payload.get("video_mime"),
                "sucursal_id": sucursal_for_new,
            }
        )

        if new_id:
            return {"ok": True, "id": int(new_id)}
        msg = "No se pudo crear"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating ejercicio: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put("/api/ejercicios/{ejercicio_id}", dependencies=[Depends(require_feature("ejercicios"))])
async def api_ejercicios_update(
    ejercicio_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Update an exercise using SQLAlchemy."""
    try:
        payload = await request.json()
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        if svc.actualizar_ejercicio(ejercicio_id, payload, sucursal_id=sucursal_id):
            return {"ok": True}
        msg = "No se pudo actualizar"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except Exception as e:
        logger.error(f"Error updating ejercicio: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.delete("/api/ejercicios/{ejercicio_id}", dependencies=[Depends(require_feature("ejercicios"))])
async def api_ejercicios_delete(
    ejercicio_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Delete an exercise using SQLAlchemy."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        if svc.eliminar_ejercicio(ejercicio_id, sucursal_id=sucursal_id):
            return {"ok": True}
        msg = "No se pudo eliminar"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except Exception as e:
        logger.error(f"Error deleting ejercicio: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


# --- API Rutinas ---


@router.get(
    "/api/rutinas",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:read")),
    ],
)
async def api_rutinas_list(
    request: Request,
    usuario_id: Optional[int] = None,
    search: str = "",
    plantillas: Optional[bool] = None,
    es_plantilla: Optional[bool] = None,  # Alias for plantillas
    include_exercises: bool = False,
    limit: int = 50,
    offset: int = 0,
    page: Optional[int] = None,
    svc: TrainingService = Depends(get_training_service),
):
    """Get routines using SQLAlchemy. Includes exercises when filtering by user."""
    try:
        # AuthZ:
        # - Gestion sessions can list any rutinas (incl templates).
        # - Member sessions can only list their own rutinas.
        try:
            role = str(request.session.get("role") or "").strip().lower()
        except Exception:
            role = ""

        logged_in = bool(request.session.get("logged_in"))
        gestion_prof_user_id = request.session.get("gestion_profesor_user_id")
        session_user_id = request.session.get("user_id")

        is_gestion = (
            bool(logged_in)
            or bool(gestion_prof_user_id)
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

        if (not is_gestion) and (session_user_id is None):
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not is_gestion:
            usuario_id = int(session_user_id)
            plantillas = False
            es_plantilla = False
            include_exercises = True

        try:
            lim = max(1, min(int(limit or 50), 100))
        except Exception:
            lim = 50
        try:
            off = max(0, int(offset or 0))
        except Exception:
            off = 0
        if off <= 0 and page is not None:
            try:
                p = int(page)
                if p > 0:
                    off = (p - 1) * lim
            except Exception:
                pass

        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None

        is_template_req = plantillas if plantillas is not None else es_plantilla
        out = svc.obtener_rutinas_paginadas(
            usuario_id=usuario_id,
            include_exercises=include_exercises,
            search=search,
            solo_plantillas=is_template_req,
            sucursal_id=sucursal_id,
            limit=lim,
            offset=off,
        )
        return {
            "rutinas": list(out.get("items") or []),
            "total": int(out.get("total") or 0),
        }
    except Exception as e:
        logger.error(f"Error listing rutinas: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post(
    "/api/rutinas",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:write")),
    ],
)
async def api_rutinas_create(
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Create a routine using SQLAlchemy."""
    try:
        payload = await request.json()
        nombre = (payload.get("nombre") or payload.get("nombre_rutina") or "").strip()
        if not nombre:
            raise HTTPException(status_code=400, detail="Nombre requerido")

        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        usuario_id = payload.get("usuario_id")
        shared = True if usuario_id is None else False
        try:
            if "shared" in payload:
                shared = bool(payload.get("shared"))
        except Exception:
            shared = True if usuario_id is None else False
        sucursal_for_new = None if shared else sucursal_id
        creada_por_usuario_id = request.session.get("user_id")
        try:
            creada_por_usuario_id = (
                int(creada_por_usuario_id)
                if creada_por_usuario_id is not None
                else None
            )
        except Exception:
            creada_por_usuario_id = None

        new_id = svc.crear_rutina(
            {
                "nombre_rutina": nombre,
                "descripcion": payload.get("descripcion"),
                "usuario_id": usuario_id,
                "dias_semana": payload.get("dias_semana") or 1,
                "semanas": payload.get("semanas") or 4,
                "categoria": payload.get("categoria") or "general",
                "activa": True,
                "sucursal_id": sucursal_for_new,
                "creada_por_usuario_id": creada_por_usuario_id,
                "plantilla_id": payload.get("plantilla_id"),
            }
        )

        if new_id:
            # Handle exercises
            # 1. Try from 'dias' (UnifiedRutinaEditor format)
            dias = payload.get("dias")
            ok_assign = True
            if dias and isinstance(dias, list):
                exercises_flat = []
                for dia in dias:
                    d_num = int(dia.get("numero") or dia.get("dayNumber") or 1)
                    for ex in dia.get("ejercicios") or []:
                        ex_copy = ex.copy()
                        ex_copy["dia_semana"] = d_num
                        exercises_flat.append(ex_copy)
                if exercises_flat:
                    ok_assign = bool(
                        svc.asignar_ejercicios_rutina(
                            new_id, exercises_flat, sucursal_id=sucursal_id
                        )
                    )
            # 2. Try from 'ejercicios' (Duplicate format or flat API usage)
            elif payload.get("ejercicios") and isinstance(
                payload.get("ejercicios"), list
            ):
                ok_assign = bool(
                    svc.asignar_ejercicios_rutina(
                        new_id, payload.get("ejercicios"), sucursal_id=sucursal_id
                    )
                )

            if not ok_assign:
                try:
                    svc.eliminar_rutina(int(new_id), sucursal_id=sucursal_id)
                except Exception:
                    pass
                msg = "Ejercicios inválidos"
                return JSONResponse(
                    {
                        "ok": False,
                        "mensaje": msg,
                        "error": msg,
                        "success": False,
                        "message": msg,
                    },
                    status_code=400,
                )

            return {"ok": True, "id": int(new_id)}
        msg = "No se pudo crear"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except HTTPException:
        raise
    except PermissionError as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=403,
        )
    except Exception as e:
        logger.error(f"Error creating rutina: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.get(
    "/api/rutinas/{rutina_id}/export/pdf",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:read")),
    ],
)
async def api_rutina_export_pdf(
    rutina_id: int,
    weeks: int = 1,
    filename: Optional[str] = None,
    template_id: Optional[int] = None,
    qr_mode: str = "auto",
    sheet: Optional[str] = None,
    tenant: Optional[str] = None,
    user_override: Optional[str] = None,
    _=Depends(require_gestion_access),
    svc: TrainingService = Depends(get_training_service),
    db: Session = Depends(get_db),
):
    """Export routine as PDF using the dynamic template system."""
    try:
        rutina_data = svc.obtener_rutina_completa(rutina_id)
        if not rutina_data:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")

        if not (rutina_data.get("ejercicios") or []) and not any((d.get("ejercicios") or []) for d in (rutina_data.get("dias") or []) if isinstance(d, dict)):
            raise HTTPException(
                status_code=400, detail="La rutina no contiene ejercicios"
            )

        pdf_filename = _sanitize_download_filename(
            filename, f"rutina_{rutina_id}", ".pdf"
        )
        try:
            semanas_total = int(rutina_data.get("semanas") or 4)
        except Exception:
            semanas_total = 4
        semanas_total = max(1, min(semanas_total, 12))
        try:
            current_week = int(weeks or 1)
        except Exception:
            current_week = 1
        current_week = max(1, min(current_week, semanas_total))
        data = _build_rutina_pdf_data(
            rutina_data, user_override=user_override, current_week=current_week
        )
        effective_template_id = template_id
        if effective_template_id is None:
            try:
                rid_tpl = rutina_data.get("plantilla_id")
                effective_template_id = int(rid_tpl) if rid_tpl is not None else None
            except Exception:
                effective_template_id = None
        template_config = _select_template_config_for_rutina(db, template_id=effective_template_id, qr_mode=qr_mode)

        engine = PDFEngine()
        pdf_bytes = engine.generate_pdf(template_config=template_config, data=data, output_path=None)
        if not isinstance(pdf_bytes, (bytes, bytearray)):
            raise HTTPException(status_code=500, detail="Error generando PDF")

        headers = {"Content-Disposition": f'attachment; filename="{pdf_filename}"'}
        return Response(content=bytes(pdf_bytes), media_type="application/pdf", headers=headers)
    except HTTPException:
        raise
    except Exception as e:
        logging.exception("Error exporting PDF")
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/api/rutinas/{rutina_id}",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:read")),
    ],
)
async def api_rutina_get(
    rutina_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Get a single routine with all exercises."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        rutina = svc.obtener_rutina_detalle(rutina_id, sucursal_id=sucursal_id)
        if not rutina:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")
        return rutina
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rutina: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put(
    "/api/rutinas/{rutina_id}",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:write")),
    ],
)
async def api_rutina_update(
    rutina_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Update a routine."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        if not svc.obtener_rutina_detalle(rutina_id, sucursal_id=sucursal_id):
            raise HTTPException(status_code=404, detail="Rutina no encontrada")

        payload = await request.json()

        # Transform dias to exercises list if present
        dias = payload.get("dias")
        if dias and isinstance(dias, list) and "ejercicios" not in payload:
            exercises_flat = []
            for dia in dias:
                d_num = dia.get("numero") or dia.get("dayNumber") or 1
                for ex in dia.get("ejercicios") or []:
                    ex["dia_semana"] = d_num
                    exercises_flat.append(ex)
            payload["ejercicios"] = exercises_flat

        success = svc.actualizar_rutina(rutina_id, payload, sucursal_id=sucursal_id)
        if success:
            return {"ok": True}
        if "ejercicios" in (payload or {}):
            msg = "Ejercicios inválidos"
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": msg,
                    "error": msg,
                    "success": False,
                    "message": msg,
                },
                status_code=400,
            )
        msg = "No se pudo actualizar"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except Exception as e:
        logger.error(f"Error updating rutina: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.delete(
    "/api/rutinas/{rutina_id}",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:write")),
    ],
)
async def api_rutina_delete(
    rutina_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Delete a routine."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        if svc.eliminar_rutina(rutina_id, sucursal_id=sucursal_id):
            return {"ok": True}
        msg = "No se pudo eliminar"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except Exception as e:
        logger.error(f"Error deleting rutina: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.put(
    "/api/rutinas/{rutina_id}/toggle-activa",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:write")),
    ],
)
async def api_rutina_toggle_activa(
    rutina_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Toggle activa status of a routine. If activating, deactivates other rutinas for the same user."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        rutina = svc.obtener_rutina_detalle(rutina_id, sucursal_id=sucursal_id)
        if not rutina:
            raise HTTPException(status_code=404, detail="Rutina no encontrada")

        new_status = not rutina.get("activa", False)

        # If activating this rutina and it has a user, deactivate others first
        if new_status and rutina.get("usuario_id"):
            svc.desactivar_rutinas_usuario(
                rutina["usuario_id"], except_rutina_id=rutina_id
            )

        success = svc.actualizar_rutina(
            rutina_id, {"activa": new_status}, sucursal_id=sucursal_id
        )
        if success:
            return {"ok": True, "activa": new_status}
        msg = "No se pudo actualizar"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggling rutina activa: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


@router.post(
    "/api/rutinas/{rutina_id}/assign",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:write")),
    ],
)
async def api_rutina_assign(
    rutina_id: int,
    request: Request,
    _=Depends(require_gestion_access),
    __=Depends(require_sucursal_selected),
    svc: TrainingService = Depends(get_training_service),
):
    """Assign a routine (plantation) to a user, creating a copy for that user."""
    try:
        sucursal_id = request.session.get("sucursal_id")
        try:
            sucursal_id = int(sucursal_id) if sucursal_id is not None else None
        except Exception:
            sucursal_id = None
        payload = await request.json()
        usuario_id = payload.get("usuario_id")
        try:
            usuario_id = int(usuario_id)
        except Exception:
            usuario_id = None
        if not usuario_id:
            raise HTTPException(status_code=400, detail="usuario_id requerido")

        rutina_origen = svc.obtener_rutina_detalle(rutina_id, sucursal_id=sucursal_id)
        if not rutina_origen:
            raise HTTPException(status_code=404, detail="Rutina origen no encontrada")

        # Clone
        new_data = {
            "nombre_rutina": rutina_origen["nombre_rutina"],
            "descripcion": rutina_origen["descripcion"],
            "usuario_id": usuario_id,
            "dias_semana": rutina_origen["dias_semana"],
            "semanas": rutina_origen.get("semanas") or 4,
            "categoria": rutina_origen["categoria"],
            "activa": True,
            "sucursal_id": sucursal_id,
            "plantilla_id": rutina_origen.get("plantilla_id"),
        }
        new_id = svc.crear_rutina(new_data)
        if new_id:
            # Clone exercises
            exs = rutina_origen.get("ejercicios", [])
            ok_assign = bool(
                svc.asignar_ejercicios_rutina(new_id, exs, sucursal_id=sucursal_id)
            )
            if not ok_assign:
                try:
                    svc.eliminar_rutina(int(new_id), sucursal_id=sucursal_id)
                except Exception:
                    pass
                msg = "Ejercicios inválidos"
                return JSONResponse(
                    {
                        "ok": False,
                        "mensaje": msg,
                        "error": msg,
                        "success": False,
                        "message": msg,
                    },
                    status_code=400,
                )
            return {"ok": True, "id": new_id}

        msg = "No se pudo asignar"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )
    except HTTPException:
        raise
    except PermissionError as e:
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=403,
        )
    except Exception as e:
        logger.error(f"Error assigning rutina: {e}")
        msg = str(e)
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=500,
        )


 


@router.get("/api/maintenance_status")
async def api_maintenance_status(request: Request, db: Session = Depends(get_admin_db)):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    row = db.execute(
        text(
            "SELECT status, suspended_reason, suspended_until FROM gyms WHERE LOWER(subdominio) = :t LIMIT 1"
        ),
        {"t": tenant},
    ).mappings().first()
    if not row:
        return {"maintenance": False}
    is_maintenance = str(row.get("status") or "").strip().lower() == "maintenance"
    until = row.get("suspended_until")
    if is_maintenance and until is not None:
        try:
            if hasattr(until, "timestamp") and until <= datetime.utcnow():
                is_maintenance = False
        except Exception:
            pass
    msg = str(row.get("suspended_reason") or "").strip() if is_maintenance else ""
    return {
        "maintenance": bool(is_maintenance),
        "message": msg or None,
        "until": until.isoformat() if hasattr(until, "isoformat") else None,
    }


@router.get("/api/suspension_status")
async def api_suspension_status(request: Request, db: Session = Depends(get_admin_db)):
    claims = get_claims(request)
    tenant = str(claims.get("tenant") or "").strip().lower()
    if not tenant:
        raise HTTPException(status_code=400, detail="Tenant inválido")
    row = db.execute(
        text(
            "SELECT status, suspended_reason, suspended_until, hard_suspend FROM gyms WHERE LOWER(subdominio) = :t LIMIT 1"
        ),
        {"t": tenant},
    ).mappings().first()
    if not row:
        return {"suspended": False}
    status = str(row.get("status") or "").strip().lower()
    is_suspended = status == "suspended"
    until = row.get("suspended_until")
    if is_suspended and until is not None:
        try:
            if hasattr(until, "timestamp") and until <= datetime.utcnow():
                is_suspended = False
        except Exception:
            pass
    msg = str(row.get("suspended_reason") or "").strip() if is_suspended else ""
    hard = bool(row.get("hard_suspend")) if is_suspended else False
    return {
        "suspended": bool(is_suspended),
        "reason": msg or None,
        "until": until.isoformat() if hasattr(until, "isoformat") else None,
        "hard": bool(hard),
    }


# --- QR Access Endpoints ---


@router.post(
    "/api/rutinas/verify_qr",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:read")),
    ],
)
async def api_verify_routine_qr(
    request: Request,
    payload: Dict[str, str],
    svc: TrainingService = Depends(get_training_service),
):
    """
    Validate a Routine QR code UUID and return the full routine details.
    This grants ephemeral access to the routine content.
    """
    import os
    from sqlalchemy import select, or_

    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    ) or os.getenv("ENV", "").lower() in ("dev", "development")
    allow_public = os.getenv("ALLOW_PUBLIC_ROUTINE_QR", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not (dev_mode or allow_public):
        uid = request.session.get("user_id") or request.session.get("checkin_user_id")
        if not uid:
            msg = "Unauthorized"
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": msg,
                    "error": msg,
                    "success": False,
                    "message": msg,
                },
                status_code=401,
            )

    uuid_val = (payload.get("uuid") or "").strip()
    if not uuid_val:
        msg = "UUID requerido"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=400,
        )

    sucursal_id = request.session.get("sucursal_id")
    try:
        sucursal_id = int(sucursal_id) if sucursal_id is not None else None
    except Exception:
        sucursal_id = None

    rutina = svc.obtener_rutina_por_uuid(uuid_val, sucursal_id=sucursal_id)
    if not rutina:
        msg = "Rutina no encontrada"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=404,
        )

    if not bool(rutina.get("activa", True)):
        msg = "Rutina inactiva"
        return JSONResponse(
            {
                "ok": False,
                "mensaje": msg,
                "error": msg,
                "success": False,
                "message": msg,
            },
            status_code=403,
        )

    rid = int(rutina.get("id") or 0)
    usuario_id_rut = rutina.get("usuario_id")
    try:
        usuario_id_rut = int(usuario_id_rut) if usuario_id_rut is not None else None
    except Exception:
        usuario_id_rut = None

    if usuario_id_rut is not None and rid:
        try:
            from src.models.orm_models import Rutina as RutinaModel

            conds = [
                RutinaModel.usuario_id == int(usuario_id_rut),
                RutinaModel.activa.is_(True),
            ]
            if sucursal_id is not None and hasattr(RutinaModel, "sucursal_id"):
                try:
                    sid = int(sucursal_id)
                except Exception:
                    sid = None
                if sid is not None and sid > 0:
                    conds.append(
                        or_(RutinaModel.sucursal_id.is_(None), RutinaModel.sucursal_id == sid)
                    )

            active_ids = list(
                svc.db.scalars(
                    select(RutinaModel.id).where(*conds)
                ).all()
            )
            active_ids = [int(x) for x in (active_ids or []) if x is not None]
            if len(active_ids) != 1 or int(active_ids[0]) != int(rid):
                msg = "QR no corresponde a la rutina activa"
                return JSONResponse(
                    {
                        "ok": False,
                        "mensaje": msg,
                        "error": msg,
                        "success": False,
                        "message": msg,
                    },
                    status_code=403,
                )
        except Exception:
            msg = "Validación de rutina falló"
            return JSONResponse(
                {
                    "ok": False,
                    "mensaje": msg,
                    "error": msg,
                    "success": False,
                    "message": msg,
                },
                status_code=403,
            )

    sess_uid = request.session.get("user_id") or request.session.get("checkin_user_id")
    if sess_uid is not None and usuario_id_rut is not None:
        try:
            if int(sess_uid) != int(usuario_id_rut):
                msg = "QR no corresponde a tu rutina"
                return JSONResponse(
                    {
                        "ok": False,
                        "mensaje": msg,
                        "error": msg,
                        "success": False,
                        "message": msg,
                    },
                    status_code=403,
                )
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
        "expires_in_seconds": 86400,
    }


@router.get(
    "/api/rutinas/qr_scan/{uuid_val}",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:read")),
    ],
)
async def api_rutina_qr_scan(
    uuid_val: str,
    request: Request,
    tenant: Optional[str] = None,
    svc: TrainingService = Depends(get_training_service),
):
    dev_mode = os.getenv("DEVELOPMENT_MODE", "").lower() in (
        "1",
        "true",
        "yes",
    ) or os.getenv("ENV", "").lower() in ("dev", "development")
    allow_public = os.getenv("ALLOW_PUBLIC_ROUTINE_QR", "").lower() in (
        "1",
        "true",
        "yes",
    )
    if not (dev_mode or allow_public):
        uid = request.session.get("user_id") or request.session.get("checkin_user_id")
        if not uid:
            return HTMLResponse(
                "<h3>Acceso requerido</h3><p>Iniciá sesión para ver la rutina.</p>",
                status_code=401,
            )

    sucursal_id = request.session.get("sucursal_id")
    try:
        sucursal_id = int(sucursal_id) if sucursal_id is not None else None
    except Exception:
        sucursal_id = None
    rutina = svc.obtener_rutina_por_uuid(str(uuid_val or "").strip(), sucursal_id=sucursal_id)
    if not rutina:
        return HTMLResponse("<h3>Rutina no encontrada</h3>", status_code=404)

    if not bool(rutina.get("activa", True)):
        return HTMLResponse("<h3>Rutina inactiva</h3>", status_code=403)

    dias = rutina.get("dias") or []
    nombre = str(rutina.get("nombre_rutina") or rutina.get("nombre") or "Rutina")
    usuario_nombre = str(rutina.get("usuario_nombre") or "").strip()

    def _esc(s: str) -> str:
        return (
            (s or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    parts = [
        "<!doctype html><html lang='es'><head><meta charset='utf-8'/>",
        "<meta name='viewport' content='width=device-width, initial-scale=1'/>",
        f"<title>{_esc(nombre)}</title>",
        "<style>body{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;margin:0;padding:18px;background:#0b1220;color:#e5e7eb}h1{font-size:18px;margin:0 0 8px}h2{font-size:14px;margin:16px 0 8px;color:#93c5fd}.card{background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:14px}a{color:#93c5fd;text-decoration:none}a:hover{text-decoration:underline}.ex{display:flex;gap:10px;justify-content:space-between;border-top:1px solid rgba(255,255,255,.08);padding:10px 0}.ex:first-child{border-top:0}.muted{color:#9ca3af;font-size:12px}</style>",
        "</head><body><div class='card'>",
        f"<h1>{_esc(nombre)}</h1>",
    ]
    if usuario_nombre:
        parts.append(f"<div class='muted'>{_esc(usuario_nombre)}</div>")
    if not isinstance(dias, list) or len(dias) == 0:
        parts.append("<p class='muted'>Sin ejercicios.</p>")
    else:
        for d in dias:
            try:
                dnum = int(d.get("numero") or d.get("dayNumber") or 0)
            except Exception:
                dnum = 0
            parts.append(f"<h2>Día {dnum or ''}</h2>")
            parts.append("<div>")
            for ex in d.get("ejercicios") or []:
                if not isinstance(ex, dict):
                    continue
                ex_name = str(
                    ex.get("ejercicio_nombre")
                    or ex.get("nombre_ejercicio")
                    or ex.get("nombre")
                    or "Ejercicio"
                )
                series = str(ex.get("series") or "")
                reps = str(ex.get("repeticiones") or "")
                video = ex.get("video_url")
                left = _esc(ex_name)
                if video:
                    left = f"<a href='{_esc(str(video))}' target='_blank' rel='noopener noreferrer'>{left}</a>"
                right = " ".join(
                    [
                        p
                        for p in [
                            ("Ser: " + _esc(series)) if series else "",
                            ("Rep: " + _esc(reps)) if reps else "",
                        ]
                        if p
                    ]
                ).strip()
                parts.append(
                    f"<div class='ex'><div>{left}</div><div class='muted'>{right}</div></div>"
                )
            parts.append("</div>")
    parts.append("</div></body></html>")
    return HTMLResponse("".join(parts), status_code=200)


@router.get(
    "/api/rutinas/preview/qr_scan/{uuid_val}",
    dependencies=[
        Depends(require_feature("rutinas")),
        Depends(require_scope_gestion("rutinas:read")),
    ],
)
async def api_rutina_qr_scan_preview(
    uuid_val: str,
    request: Request,
    tenant: Optional[str] = None,
    svc: TrainingService = Depends(get_training_service),
):
    return await api_rutina_qr_scan(
        uuid_val=uuid_val, request=request, tenant=tenant, svc=svc
    )
