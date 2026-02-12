import os
from typing import Any, Dict, Optional

from fastapi import APIRouter, Request, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import sessionmaker

from src.database.raw_manager import RawPostgresManager
from src.services.admin_service import AdminService
from src.template_system.template_service import TemplateService

router = APIRouter(prefix="/api/v1/templates", tags=["TemplatesV1"])

_admin_service = None


def get_admin_service() -> AdminService:
    global _admin_service
    if _admin_service is not None:
        return _admin_service
    params = AdminService.resolve_admin_db_params()
    db = RawPostgresManager(connection_params=params)
    _admin_service = AdminService(db)
    return _admin_service


def require_admin(request: Request):
    try:
        if request.session.get("admin_logged_in"):
            return
    except Exception:
        pass
    secret = os.getenv("ADMIN_SECRET", "").strip()
    if secret and request.headers.get("x-admin-secret") == secret:
        return
    raise HTTPException(status_code=401, detail="Unauthorized")


def require_gym_id(request: Request) -> int:
    raw = (request.headers.get("x-gym-id") or "").strip()
    if not raw:
        raise HTTPException(status_code=400, detail="x-gym-id requerido")
    try:
        gid = int(raw)
    except Exception:
        raise HTTPException(status_code=400, detail="x-gym-id inválido")
    if gid <= 0:
        raise HTTPException(status_code=400, detail="x-gym-id inválido")
    return gid


def with_tenant_service(gym_id: int) -> TemplateService:
    adm = get_admin_service()
    eng = adm._get_tenant_engine_for_gym(int(gym_id))
    if not eng:
        raise HTTPException(status_code=400, detail="tenant_db_unavailable")
    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False)
    db = SessionLocal()
    return TemplateService(db)


@router.get("")
async def list_templates(
    request: Request,
    query: Optional[str] = None,
    categoria: Optional[str] = None,
    activa: Optional[bool] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        out = service.search_templates(
            {
                "query": query,
                "categoria": categoria,
                "activa": activa,
                "sort_by": sort_by,
                "sort_order": sort_order,
                "limit": limit,
                "offset": offset,
            }
        )
        return JSONResponse(out)
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/categories")
async def get_categories(request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        cats = service.repository.get_template_categories()
        return JSONResponse({"success": True, "categories": cats})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/tags")
async def get_tags(request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        tags = service.repository.get_template_tags()
        return JSONResponse({"success": True, "tags": tags})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.post("/preview")
async def preview_template_config(
    request: Request,
    format: str = Query("pdf"),
    quality: str = Query("medium"),
    page_number: int = Query(1, ge=1),
):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid payload")
        configuracion = payload.get("configuracion")
        if configuracion is None and isinstance(payload.get("template_config"), dict):
            configuracion = payload.get("template_config")
        if configuracion is None and "metadata" in payload and "layout" in payload:
            configuracion = payload
        if not isinstance(configuracion, dict):
            raise HTTPException(status_code=400, detail="configuracion requerida")
        sample_data = payload.get("sample_data")
        if not isinstance(sample_data, dict):
            sample_data = None
        url, err = service.generate_template_preview(
            configuracion,
            format=format,
            quality=quality,
            page_number=page_number,
            sample_data=sample_data,
        )
        if not url:
            raise HTTPException(status_code=400, detail=err or "preview_failed")
        return JSONResponse({"success": True, "preview_url": url, "format": format, "quality": quality, "page_number": page_number})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/{template_id}")
async def get_template(template_id: int, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        tpl = service.get_template(int(template_id))
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        return JSONResponse({"success": True, "template": tpl})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.post("")
async def create_template(request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid payload")
        tpl, err = service.create_template(payload, creada_por=None)
        if not tpl:
            raise HTTPException(status_code=400, detail=err or "create_failed")
        service.generate_and_store_thumbnail(int(tpl["id"]))
        tpl2 = service.get_template(int(tpl["id"])) or tpl
        return JSONResponse({"success": True, "template": tpl2})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.put("/{template_id}")
async def update_template(template_id: int, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid payload")
        tpl, err = service.update_template(int(template_id), payload, creada_por=None)
        if not tpl:
            raise HTTPException(status_code=400, detail=err or "update_failed")
        service.generate_and_store_thumbnail(int(template_id))
        tpl2 = service.get_template(int(template_id)) or tpl
        return JSONResponse({"success": True, "template": tpl2})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.delete("/{template_id}")
async def delete_template(template_id: int, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        ok, err = service.delete_template(int(template_id))
        if not ok:
            raise HTTPException(status_code=400, detail=err or "delete_failed")
        return JSONResponse({"success": True})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.post("/{template_id}/preview")
async def preview_template(
    template_id: int,
    request: Request,
    format: str = Query("pdf"),
    quality: str = Query("medium"),
    page_number: int = Query(1, ge=1),
):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        tpl = service.repository.get_template(int(template_id))
        if not tpl:
            raise HTTPException(status_code=404, detail="Template not found")
        sample_data = None
        try:
            body = await request.json()
            if isinstance(body, dict):
                sample_data = body
        except Exception:
            sample_data = None
        url, err = service.generate_template_preview(tpl.configuracion, format=format, quality=quality, page_number=page_number, sample_data=sample_data)
        if not url:
            raise HTTPException(status_code=400, detail=err or "preview_failed")
        return JSONResponse({"success": True, "preview_url": url, "format": format, "quality": quality, "page_number": page_number})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.post("/validate")
async def validate_template(request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid payload")
        res = service.validate_template_config(payload)
        return JSONResponse(
            {
                "success": True,
                "validation": {
                    "is_valid": res.is_valid,
                    "errors": res.errors,
                    "warnings": res.warnings,
                    "info": res.info,
                    "performance_score": res.performance_score,
                    "security_score": res.security_score,
                },
            }
        )
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/{template_id}/versions")
async def list_versions(template_id: int, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        versions = service.get_template_versions(int(template_id))
        return JSONResponse({"success": True, "versions": versions, "total": len(versions)})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.post("/{template_id}/versions")
async def create_version(template_id: int, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        payload = await request.json()
        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="Invalid payload")
        version = str(payload.get("version") or "").strip() or "1.0.0"
        configuracion = payload.get("configuracion")
        if not isinstance(configuracion, dict):
            raise HTTPException(status_code=400, detail="configuracion requerida")
        desc = payload.get("descripcion")
        v, err = service.create_template_version(int(template_id), version=version, configuracion=configuracion, descripcion=str(desc) if desc else None, creada_por=None)
        if not v:
            raise HTTPException(status_code=400, detail=err or "create_version_failed")
        service.generate_and_store_thumbnail(int(template_id))
        return JSONResponse({"success": True, "version": v})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.post("/{template_id}/versions/{version}/restore")
async def restore_version(template_id: int, version: str, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        ok, err = service.restore_template_version(int(template_id), version=str(version))
        if not ok:
            raise HTTPException(status_code=400, detail=err or "restore_failed")
        service.generate_and_store_thumbnail(int(template_id))
        return JSONResponse({"success": True, "message": f"Template restored to version {version}"})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/{template_id}/analytics")
async def template_analytics(template_id: int, request: Request, days: int = Query(30, ge=1, le=365)):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        analytics = service.get_template_analytics(int(template_id), days=int(days))
        return JSONResponse({"success": True, "analytics": analytics, "period_days": int(days)})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/analytics/dashboard")
async def analytics_dashboard(request: Request, days: int = Query(30, ge=1, le=365)):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        dash = service.get_analytics_dashboard(days=int(days))
        return JSONResponse({"success": True, "dashboard": dash, "period_days": int(days)})
    finally:
        try:
            service.db.close()
        except Exception:
            pass


@router.get("/{template_id}/export")
async def export_template(template_id: int, request: Request):
    require_admin(request)
    gym_id = require_gym_id(request)
    service = with_tenant_service(gym_id)
    try:
        out, err = service.export_template(int(template_id))
        if not out:
            raise HTTPException(status_code=404, detail=err or "not_found")
        return JSONResponse({"success": True, "export_data": out})
    finally:
        try:
            service.db.close()
        except Exception:
            pass
