"""
Template API Routes
REST API endpoints for template management, preview, and analytics.
All mutating endpoints require gestion access (management panel login).
Read-only public template listing is available without auth.
"""

import logging
from pathlib import Path
from typing import Dict, List, Any, Optional

from fastapi import APIRouter, HTTPException, Depends, Query, Request, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from src.dependencies import (
    get_db_session as get_db,
    require_gestion_access,
    require_owner,
)
from src.services.template_service import TemplateService

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/templates", tags=["templates"])


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------

def _get_session_user_id(request: Request) -> Optional[int]:
    """Extract user_id from the session – returns None if absent."""
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
#  Pydantic models
# ---------------------------------------------------------------------------

class TemplateCreateRequest(BaseModel):
    """Request model for creating templates"""
    nombre: str = Field(..., description="Template name")
    configuracion: Dict[str, Any] = Field(..., description="Template configuration")
    descripcion: Optional[str] = Field(None, description="Template description")
    categoria: str = Field("general", description="Template category")
    dias_semana: Optional[int] = Field(None, description="Days per week")
    activa: bool = Field(True, description="Whether template is active")
    publica: bool = Field(False, description="Whether template is public")
    tags: List[str] = Field(default_factory=list, description="Template tags")


class TemplateUpdateRequest(BaseModel):
    """Request model for updating templates"""
    nombre: Optional[str] = Field(None, description="Template name")
    configuracion: Optional[Dict[str, Any]] = Field(None, description="Template configuration")
    descripcion: Optional[str] = Field(None, description="Template description")
    categoria: Optional[str] = Field(None, description="Template category")
    dias_semana: Optional[int] = Field(None, description="Days per week")
    activa: Optional[bool] = Field(None, description="Whether template is active")
    publica: Optional[bool] = Field(None, description="Whether template is public")
    tags: Optional[List[str]] = Field(None, description="Template tags")


class TemplatePreviewRequest(BaseModel):
    """Request model for template preview"""
    format: str = Field("pdf", description="Preview format (pdf, png, jpg)")
    quality: str = Field("medium", description="Preview quality (low, medium, high)")
    qr_mode: Optional[str] = Field("inline", description="QR code mode (inline, sheet, none)")
    show_watermark: bool = Field(False, description="Whether to show watermark")
    show_metadata: bool = Field(True, description="Whether to show metadata")
    page_number: Optional[int] = Field(None, description="Specific page number")
    multi_page: bool = Field(True, description="Whether to include all pages")


class TemplateValidationRequest(BaseModel):
    """Request model for template validation"""
    configuracion: Dict[str, Any] = Field(..., description="Template configuration to validate")


class BulkOperationRequest(BaseModel):
    """Request model for bulk operations"""
    template_ids: List[int] = Field(..., description="List of template IDs")
    data: Optional[Dict[str, Any]] = Field(None, description="Data for bulk update")


# ========== TEMPLATE CRUD ENDPOINTS ==========

@router.get("/", response_model=Dict[str, Any])
async def get_templates(
    query: Optional[str] = Query(None, description="Search query"),
    categoria: Optional[str] = Query(None, description="Filter by category"),
    activa: Optional[bool] = Query(None, description="Filter by active status"),
    publica: Optional[bool] = Query(None, description="Filter by public status"),
    sort_by: str = Query("fecha_creacion", description="Sort field"),
    sort_order: str = Query("desc", description="Sort order (asc, desc)"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    gym_id: Optional[int] = Query(None, description="Gym ID for filtering"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get templates with filtering and pagination."""
    try:
        # Sanitise sort_order
        if sort_order not in ("asc", "desc"):
            sort_order = "desc"

        template_service = TemplateService(db)
        result = template_service.get_templates(
            query=query,
            categoria=categoria,
            activa=activa,
            publica=publica,
            sort_by=sort_by,
            sort_order=sort_order,
            limit=limit,
            offset=offset,
            gym_id=gym_id,
        )

        return {
            "success": True,
            "templates": result["templates"],
            "total": result["total"],
            "has_more": result["has_more"],
            "offset": result["offset"],
            "limit": result["limit"],
        }

    except Exception as e:
        logger.error(f"Error getting templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}", response_model=Dict[str, Any])
async def get_template(
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get template by ID."""
    try:
        template_service = TemplateService(db)
        template = template_service.get_template_by_id(template_id)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        template_dict = template_service._template_to_dict(template, include_versions=False)
        analytics = template_service.get_template_analytics(template_id)

        return {
            "success": True,
            "template": template_dict,
            "analytics": analytics,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/", response_model=Dict[str, Any])
async def create_template(
    request: Request,
    body: TemplateCreateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Create a new template."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        template = template_service.create_template(
            nombre=body.nombre,
            configuracion=body.configuracion,
            descripcion=body.descripcion,
            categoria=body.categoria,
            dias_semana=body.dias_semana,
            activa=body.activa,
            publica=body.publica,
            tags=body.tags,
            creada_por=user_id,
        )

        return {
            "success": True,
            "template": {
                "id": template.id,
                "nombre": template.nombre,
                "descripcion": template.descripcion,
                "categoria": template.categoria,
                "dias_semana": template.dias_semana,
                "activa": template.activa,
                "publica": template.publica,
                "creada_por": template.creada_por,
                "version_actual": template.version_actual,
                "tags": template.tags,
                "uso_count": template.uso_count,
                "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
                "rating_count": template.rating_count,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating template: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{template_id}", response_model=Dict[str, Any])
async def update_template(
    request: Request,
    template_id: int,
    body: TemplateUpdateRequest,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Update template."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)

        updates = {k: v for k, v in body.dict(exclude_unset=True).items()}
        template = template_service.update_template(template_id, updates, user_id)

        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "success": True,
            "template": {
                "id": template.id,
                "nombre": template.nombre,
                "descripcion": template.descripcion,
                "categoria": template.categoria,
                "dias_semana": template.dias_semana,
                "activa": template.activa,
                "publica": template.publica,
                "version_actual": template.version_actual,
                "tags": template.tags,
                "uso_count": template.uso_count,
                "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
                "rating_count": template.rating_count,
            },
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
    """Delete template – Owner only."""
    try:
        _require_session_user_id(request)
        template_service = TemplateService(db)
        success = template_service.delete_template(template_id)

        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        return {"success": True, "message": "Template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{template_id}/duplicate", response_model=Dict[str, Any])
async def duplicate_template(
    request: Request,
    template_id: int,
    nuevo_nombre: Optional[str] = Query(None, description="New name for duplicate"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Duplicate template."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        duplicate = template_service.duplicate_template(template_id, nuevo_nombre, user_id)

        if not duplicate:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "success": True,
            "template": {
                "id": duplicate.id,
                "nombre": duplicate.nombre,
                "descripcion": duplicate.descripcion,
                "categoria": duplicate.categoria,
                "dias_semana": duplicate.dias_semana,
                "activa": duplicate.activa,
                "publica": duplicate.publica,
                "version_actual": duplicate.version_actual,
                "tags": duplicate.tags,
                "uso_count": duplicate.uso_count,
                "rating_promedio": float(duplicate.rating_promedio) if duplicate.rating_promedio else None,
                "rating_count": duplicate.rating_count,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error duplicating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== CATEGORIES ENDPOINTS ==========

@router.get("/categories/list", response_model=Dict[str, Any])
async def get_template_categories(
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get all template categories."""
    try:
        template_service = TemplateService(db)
        categories = template_service.get_template_categories()
        return {"success": True, "categories": categories}
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== ANALYTICS ENDPOINTS ==========

@router.get("/{template_id}/analytics", response_model=Dict[str, Any])
async def get_template_analytics(
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get template analytics."""
    try:
        template_service = TemplateService(db)

        template = template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        analytics = template_service.get_template_analytics(template_id)

        if not analytics:
            return {
                "success": True,
                "analytics": {
                    "template_id": template_id,
                    "usos_totales": 0,
                    "usuarios_unicos": 0,
                    "uso_ultimo_mes": 0,
                    "rating_promedio": 0.0,
                    "evaluaciones": 0,
                    "tendencias": [],
                    "popularidad": {"posicion": 0, "total_plantillas": 0},
                },
            }

        return {"success": True, "analytics": analytics}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting analytics for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats/overview", response_model=Dict[str, Any])
async def get_template_stats(
    time_range: str = Query("30d", description="Time range (7d, 30d, 90d, 1y, all)"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get overall template statistics."""
    try:
        template_service = TemplateService(db)
        stats = template_service.get_template_stats(time_range)
        return {"success": True, "stats": stats}
    except Exception as e:
        logger.error(f"Error getting template stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== PREVIEW ENDPOINTS ==========

@router.post("/{template_id}/preview", response_model=Dict[str, Any])
async def get_template_preview(
    template_id: int,
    body: TemplatePreviewRequest,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Generate template preview."""
    try:
        template_service = TemplateService(db)

        template = template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        preview_url = template_service.generate_template_preview(
            template_id,
            body.dict(),
        )

        if not preview_url:
            raise HTTPException(status_code=500, detail="Failed to generate preview")

        return {
            "success": True,
            "preview_url": preview_url,
            "format": body.format,
            "quality": body.quality,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generating preview for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== VALIDATION ENDPOINTS ==========

@router.post("/validate", response_model=Dict[str, Any])
async def validate_template_config(
    body: TemplateValidationRequest,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Validate template configuration."""
    try:
        template_service = TemplateService(db)
        validation = template_service.validate_template_config(body.configuracion)
        return {"success": True, "validation": validation}
    except Exception as e:
        logger.error(f"Error validating template config: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== BULK OPERATIONS ENDPOINTS ==========

@router.put("/bulk", response_model=Dict[str, Any])
async def bulk_update_templates(
    request: Request,
    body: BulkOperationRequest,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Bulk update templates."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        updated = template_service.bulk_update_templates(
            body.template_ids,
            body.data or {},
            user_id,
        )

        return {
            "success": True,
            "updated": updated,
            "total_requested": len(body.template_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/bulk", response_model=Dict[str, Any])
async def bulk_delete_templates(
    request: Request,
    body: BulkOperationRequest,
    db: Session = Depends(get_db),
    _=Depends(require_owner),
):
    """Bulk delete templates – Owner only."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        deleted = template_service.bulk_delete_templates(
            body.template_ids,
            user_id,
        )

        return {
            "success": True,
            "deleted": deleted,
            "total_requested": len(body.template_ids),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in bulk delete: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== FAVORITES ENDPOINTS ==========

@router.post("/{template_id}/favorite", response_model=Dict[str, Any])
async def toggle_template_favorite(
    request: Request,
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Toggle template favorite status."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        is_favorite = template_service.toggle_template_favorite(template_id, user_id)

        return {
            "success": True,
            "favorite": is_favorite,
            "template_id": template_id,
        }

    except Exception as e:
        logger.error(f"Error toggling favorite for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/favorites/list", response_model=Dict[str, Any])
async def get_template_favorites(
    request: Request,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get user's favorite templates."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        templates = template_service.get_template_favorites(user_id)

        return {
            "success": True,
            "templates": [
                {
                    "id": t.id,
                    "nombre": t.nombre,
                    "descripcion": t.descripcion,
                    "categoria": t.categoria,
                    "dias_semana": t.dias_semana,
                    "activa": t.activa,
                    "publica": t.publica,
                    "fecha_creacion": t.fecha_creacion.isoformat() if t.fecha_creacion else None,
                    "version_actual": t.version_actual,
                    "tags": t.tags or [],
                    "uso_count": t.uso_count,
                    "rating_promedio": float(t.rating_promedio) if t.rating_promedio else None,
                    "rating_count": t.rating_count,
                }
                for t in templates
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting favorites: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== RATING ENDPOINTS ==========

@router.post("/{template_id}/rating", response_model=Dict[str, Any])
async def rate_template(
    request: Request,
    template_id: int,
    rating: int = Query(..., ge=1, le=5, description="Rating from 1 to 5"),
    comment: Optional[str] = Query(None, description="Optional comment"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Rate template."""
    try:
        user_id = _require_session_user_id(request)
        template_service = TemplateService(db)
        success = template_service.rate_template(template_id, user_id, rating, comment)

        if not success:
            raise HTTPException(status_code=404, detail="Template not found")

        template = template_service.get_template_by_id(template_id)

        return {
            "success": True,
            "rating": rating,
            "template_id": template_id,
            "new_average": float(template.rating_promedio) if template and template.rating_promedio else None,
            "total_ratings": template.rating_count if template else 0,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rating template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{template_id}/ratings", response_model=Dict[str, Any])
async def get_template_ratings(
    template_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get template ratings."""
    try:
        template_service = TemplateService(db)

        template = template_service.get_template_by_id(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")

        return {
            "success": True,
            "ratings": [],
            "average": float(template.rating_promedio) if template.rating_promedio else None,
            "total_ratings": template.rating_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting ratings for template {template_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== EXPORT/IMPORT ENDPOINTS ==========

@router.get("/export", response_model=Dict[str, Any])
async def export_templates(
    template_ids: Optional[str] = Query(None, description="Comma-separated template IDs"),
    format: str = Query("json", description="Export format"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Export templates."""
    try:
        template_service = TemplateService(db)

        ids = None
        if template_ids:
            ids = [int(tid.strip()) for tid in template_ids.split(",") if tid.strip().isdigit()]

        export_path = template_service.export_templates(ids, format)

        if not export_path:
            raise HTTPException(status_code=500, detail="Failed to export templates")

        return {
            "success": True,
            "download_url": f"/api/templates/download/{Path(export_path).name}",
            "format": format,
            "template_count": len(ids) if ids else "all",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exporting templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/import", response_model=Dict[str, Any])
async def import_templates(
    request: Request,
    file: UploadFile = File(..., description="Template file to import"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Import templates from file."""
    try:
        _require_session_user_id(request)
        return {
            "success": True,
            "imported": 0,
            "errors": ["Import functionality not yet implemented"],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error importing templates: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
