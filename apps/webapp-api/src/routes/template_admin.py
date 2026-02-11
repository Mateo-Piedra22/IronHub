"""
Template Admin API Routes (v1)
Authenticated endpoints for template management, preview, analytics, and versioning.
Requires gestion access (owner or profesor) for all operations.
"""

import io
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import (
    APIRouter, HTTPException, Depends, Query, Request,
    UploadFile, File, BackgroundTasks,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.dependencies import (
    get_db_session as get_db,
    require_gestion_access,
    require_owner,
)
from src.services.template_service import TemplateService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/templates", tags=["templates"])


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_session_user_id(request: Request) -> Optional[int]:
    """Extract user_id from session – returns None if absent."""
    uid = request.session.get("user_id")
    if uid is None:
        return None
    try:
        return int(uid)
    except (ValueError, TypeError):
        return None


def _require_session_user_id(request: Request) -> int:
    """Extract user_id or raise 401."""
    uid = _get_session_user_id(request)
    if uid is None:
        raise HTTPException(status_code=401, detail="Unauthorized")
    return uid


# ---------------------------------------------------------------------------
#  Template CRUD
# ---------------------------------------------------------------------------

@router.post("/", response_model=Dict[str, Any])
async def create_template(
    request: Request,
    template_data: Dict[str, Any],
    generate_preview: bool = Query(True, description="Generate preview after creation"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Create a new template with validation and optional preview generation."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        nombre = template_data.get("nombre")
        configuracion = template_data.get("configuracion", {})
        descripcion = template_data.get("descripcion")
        categoria = template_data.get("categoria", "general")
        dias_semana = template_data.get("dias_semana")
        tags = template_data.get("tags", [])
        publica = template_data.get("publica", False)

        template, error = service.create_template(
            nombre=nombre,
            configuracion=configuracion,
            descripcion=descripcion,
            categoria=categoria,
            dias_semana=dias_semana,
            creada_por=user_id,
            tags=tags,
            publica=publica,
            generate_preview=generate_preview,
        )

        if not template:
            raise HTTPException(status_code=400, detail=error or "Validation failed")

        logger.info(f"Template '{nombre}' created by user {user_id}")

        return {
            "success": True,
            "template": template,
            "message": "Template created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: int,
    include_versions: bool = Query(False, description="Include version history"),
    include_analytics: bool = Query(False, description="Include analytics data"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get template by ID with optional additional data."""
    try:
        service = TemplateService(db)
        template = service.get_template(template_id=template_id, include_versions=include_versions)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        if include_analytics:
            analytics = service.get_template_analytics(template_id)
            template["analytics"] = analytics

        return {"success": True, "template": template}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{template_id}", response_model=Dict[str, Any])
async def update_template(
    request: Request,
    template_id: int,
    template_data: Dict[str, Any],
    generate_preview: bool = Query(True, description="Generate preview after update"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Update template with validation, versioning, and preview generation."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        allowed_fields = {
            "nombre", "configuracion", "descripcion",
            "categoria", "dias_semana", "tags", "publica",
        }
        updates = {k: v for k, v in template_data.items() if k in allowed_fields}

        template, error = service.update_template(
            template_id=template_id,
            updates=updates,
            creada_por=user_id,
            cambios_descripcion=template_data.get("cambios_descripcion"),
            generate_preview=generate_preview,
        )

        if not template:
            raise HTTPException(status_code=400, detail=error or "Update failed")

        logger.info(f"Template {template_id} updated by user {user_id}")

        return {
            "success": True,
            "template": template,
            "message": "Template updated successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{template_id}", response_model=Dict[str, Any])
async def delete_template(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """Delete template (soft delete) – Owner only."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        success, error = service.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=400, detail=error or "Delete failed")

        logger.info(f"Template {template_id} deleted by user {user_id}")
        return {"success": True, "message": "Template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Search & Discovery
# ---------------------------------------------------------------------------

@router.get("/", response_model=Dict[str, Any])
async def search_templates(
    query: Optional[str] = Query(None, description="Search query"),
    categoria: Optional[str] = Query(None, description="Filter by category"),
    dias_semana: Optional[int] = Query(None, description="Filter by days per week"),
    publica: Optional[bool] = Query(None, description="Filter by public status"),
    creada_por: Optional[int] = Query(None, description="Filter by creator"),
    tags: Optional[List[str]] = Query(None, description="Filter by tags"),
    limit: int = Query(50, ge=1, le=100, description="Results per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
    sort_by: str = Query("fecha_creacion", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Search templates with advanced filters and pagination."""
    try:
        # Sanitise sort_order
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        service = TemplateService(db)
        result = service.search_templates(
            query=query,
            categoria=categoria,
            dias_semana=dias_semana,
            publica=publica,
            creada_por=creada_por,
            tags=tags,
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            sort_order=sort_order,
        )

        return {
            "success": True,
            "templates": result.get("templates", []),
            "total": result.get("total", 0),
            "limit": result.get("limit", limit),
            "offset": result.get("offset", offset),
            "has_more": result.get("has_more", False),
        }

    except Exception as e:
        logger.error(f"Error searching templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/categories", response_model=Dict[str, Any])
async def get_template_categories(
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get all available template categories."""
    try:
        service = TemplateService(db)
        return {"success": True, "categories": service.get_template_categories()}
    except Exception as e:
        logger.error(f"Error getting template categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/tags", response_model=Dict[str, Any])
async def get_template_tags(
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get all available template tags."""
    try:
        service = TemplateService(db)
        return {"success": True, "tags": service.get_template_tags()}
    except Exception as e:
        logger.error(f"Error getting template tags: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Preview Generation
# ---------------------------------------------------------------------------

@router.post("/{template_id}/preview", response_model=Dict[str, Any])
async def generate_template_preview(
    template_id: int,
    format: str = Query("pdf", description="Preview format (pdf|image|thumbnail|html|json)"),
    quality: str = Query("medium", description="Preview quality (low|medium|high|ultra)"),
    page_number: int = Query(1, ge=1, description="Page number for multi-page previews"),
    sample_data: Optional[Dict[str, Any]] = None,
    background: bool = Query(False, description="Generate in background"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Generate template preview in various formats."""
    try:
        # Validate enums
        if format not in ("pdf", "image", "thumbnail", "html", "json"):
            raise HTTPException(status_code=400, detail="Invalid format")
        if quality not in ("low", "medium", "high", "ultra"):
            raise HTTPException(status_code=400, detail="Invalid quality")

        service = TemplateService(db)

        if background:
            background_tasks = BackgroundTasks()
            background_tasks.add_task(
                service.generate_template_preview,
                template_id=template_id,
                sample_data=sample_data,
                format=format,
                quality=quality,
                page_number=page_number,
            )
            return {
                "success": True,
                "message": "Preview generation started in background",
                "preview_url": None,
            }
        else:
            preview_url, error = service.generate_template_preview(
                template_id=template_id,
                sample_data=sample_data,
                format=format,
                quality=quality,
                page_number=page_number,
            )

            if error:
                raise HTTPException(status_code=400, detail=error)

            return {
                "success": True,
                "preview_url": preview_url,
                "format": format,
                "quality": quality,
                "page_number": page_number,
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}/preview/stream")
async def stream_template_preview(
    template_id: int,
    format: str = Query("pdf", description="Stream format (pdf|image|thumbnail)"),
    quality: str = Query("medium", description="Stream quality"),
    page_number: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Stream template preview directly."""
    try:
        if format not in ("pdf", "image", "thumbnail"):
            raise HTTPException(status_code=400, detail="Invalid format")

        service = TemplateService(db)

        preview_bytes = service.generate_template_preview_bytes(
            template_id=template_id,
            format=format,
            quality=quality,
            page_number=page_number,
        )

        if not preview_bytes:
            raise HTTPException(status_code=400, detail="Failed to generate preview")

        media_types = {
            "pdf": "application/pdf",
            "image": "image/png",
            "thumbnail": "image/png",
        }
        media_type = media_types.get(format, "application/octet-stream")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        ext = "pdf" if format == "pdf" else "png"
        filename = f"template_{template_id}_preview_{timestamp}.{ext}"

        return StreamingResponse(
            io.BytesIO(preview_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error streaming preview for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Validation
# ---------------------------------------------------------------------------

@router.post("/validate", response_model=Dict[str, Any])
async def validate_template_config(
    configuracion: Dict[str, Any],
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Validate template configuration without creating the template."""
    try:
        service = TemplateService(db)
        validation_result = service.validate_template_config(configuracion)

        return {
            "success": True,
            "validation": {
                "is_valid": validation_result.is_valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings,
                "performance_score": getattr(validation_result, "performance_score", None),
                "security_score": getattr(validation_result, "security_score", None),
            },
        }

    except Exception as e:
        logger.error(f"Error validating template config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Version Management
# ---------------------------------------------------------------------------

@router.get("/{template_id}/versions", response_model=Dict[str, Any])
async def get_template_versions(
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get version history for a template."""
    try:
        service = TemplateService(db)
        versions = service.get_template_versions(template_id)
        return {"success": True, "versions": versions, "total": len(versions)}
    except Exception as e:
        logger.error(f"Error getting versions for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{template_id}/versions", response_model=Dict[str, Any])
async def create_template_version(
    request: Request,
    template_id: int,
    version_data: Dict[str, Any],
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Create a new version of a template."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        version, error = service.create_template_version(
            template_id=template_id,
            configuracion=version_data.get("configuracion", {}),
            version=version_data.get("version"),
            descripcion=version_data.get("descripcion"),
            creada_por=user_id,
        )

        if not version:
            raise HTTPException(status_code=400, detail=error or "Version creation failed")

        return {
            "success": True,
            "version": version,
            "message": "Template version created successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating version for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{template_id}/versions/{version}/restore", response_model=Dict[str, Any])
async def restore_template_version(
    request: Request,
    template_id: int,
    version: str,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Restore a template to a specific version."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        success, error = service.restore_template_version(
            template_id=template_id,
            version=version,
            restaurado_por=user_id,
        )

        if not success:
            raise HTTPException(status_code=400, detail=error or "Restore failed")

        return {"success": True, "message": f"Template restored to version {version}"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error restoring template {template_id} to version {version}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Analytics
# ---------------------------------------------------------------------------

@router.get("/{template_id}/analytics", response_model=Dict[str, Any])
async def get_template_analytics(
    template_id: int,
    days: int = Query(30, ge=1, le=365, description="Analytics period in days"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get analytics data for a template."""
    try:
        service = TemplateService(db)
        analytics = service.get_template_analytics(template_id=template_id, days=days)
        return {"success": True, "analytics": analytics, "period_days": days}
    except Exception as e:
        logger.error(f"Error getting analytics for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analytics/dashboard", response_model=Dict[str, Any])
async def get_analytics_dashboard(
    gimnasio_id: Optional[int] = Query(None, description="Filter by gym"),
    days: int = Query(30, ge=1, le=365, description="Analytics period in days"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get comprehensive analytics dashboard data."""
    try:
        service = TemplateService(db)
        dashboard_data = service.get_analytics_dashboard(gimnasio_id=gimnasio_id, days=days)
        return {
            "success": True,
            "dashboard": dashboard_data,
            "period_days": days,
            "gimnasio_id": gimnasio_id,
        }
    except Exception as e:
        logger.error(f"Error getting analytics dashboard: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Import / Export
# ---------------------------------------------------------------------------

@router.post("/import", response_model=Dict[str, Any])
async def import_template(
    request: Request,
    file: UploadFile = File(...),
    validate_only: bool = Query(False, description="Only validate, don't import"),
    overwrite: bool = Query(False, description="Overwrite existing templates"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Import template from JSON file."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        content = await file.read()

        if not file.filename or not file.filename.endswith(".json"):
            raise HTTPException(status_code=400, detail="Only JSON files are supported")

        try:
            template_data = json.loads(content.decode("utf-8"))
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid JSON file")

        if validate_only:
            validation_result = service.validate_template_config(
                template_data.get("configuracion", {})
            )
            return {
                "success": True,
                "validated": True,
                "validation": {
                    "is_valid": validation_result.is_valid,
                    "errors": validation_result.errors,
                    "warnings": validation_result.warnings,
                },
            }
        else:
            template, error = service.import_template(
                template_data=template_data,
                creada_por=user_id,
                overwrite=overwrite,
            )

            if not template:
                raise HTTPException(status_code=400, detail=error or "Import failed")

            return {
                "success": True,
                "template": template,
                "message": "Template imported successfully",
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing template: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}/export", response_model=Dict[str, Any])
async def export_template(
    template_id: int,
    include_analytics: bool = Query(False, description="Include analytics data"),
    include_versions: bool = Query(False, description="Include version history"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Export template with optional additional data."""
    try:
        service = TemplateService(db)

        export_data = service.export_template(
            template_id=template_id,
            include_analytics=include_analytics,
            include_versions=include_versions,
        )

        return {
            "success": True,
            "export_data": export_data,
            "filename": f"template_{template_id}_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        }

    except Exception as e:
        logger.error(f"Error exporting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ---------------------------------------------------------------------------
#  Gym Assignment (admin-level)
# ---------------------------------------------------------------------------

@router.get("/gym/{gimnasio_id}", response_model=Dict[str, Any])
async def get_templates_for_gym(
    gimnasio_id: int,
    include_public: bool = Query(True, description="Include public templates"),
    include_analytics: bool = Query(False, description="Include analytics"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get templates available to a specific gym."""
    try:
        service = TemplateService(db)
        templates = service.get_templates_for_gym(
            gimnasio_id=gimnasio_id,
            include_public=include_public,
            include_analytics=include_analytics,
        )
        return {"success": True, "templates": templates, "gimnasio_id": gimnasio_id}
    except Exception as e:
        logger.error(f"Error getting templates for gym {gimnasio_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/gym/{gimnasio_id}/assign", response_model=Dict[str, Any])
async def assign_template_to_gym(
    request: Request,
    gimnasio_id: int,
    assignment_data: Dict[str, Any],
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Assign a template to a gym."""
    try:
        user_id = _require_session_user_id(request)
        service = TemplateService(db)

        assignment, error = service.assign_template_to_gym(
            gimnasio_id=gimnasio_id,
            template_id=assignment_data.get("template_id"),
            prioridad=assignment_data.get("prioridad", 0),
            asignada_por=user_id,
        )

        if not assignment:
            raise HTTPException(status_code=400, detail=error or "Assignment failed")

        return {
            "success": True,
            "assignment": assignment,
            "message": "Template assigned to gym successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning template to gym {gimnasio_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/gym/{gimnasio_id}/assign/{assignment_id}", response_model=Dict[str, Any])
async def remove_template_from_gym(
    gimnasio_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Remove template assignment from gym."""
    try:
        service = TemplateService(db)

        success, error = service.remove_template_from_gym(assignment_id)

        if not success:
            raise HTTPException(status_code=400, detail=error or "Removal failed")

        return {"success": True, "message": "Template removed from gym successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing template assignment {assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
