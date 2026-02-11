"""
Gym Template Assignment Routes
Authenticated endpoints for managing template assignments to gyms.
Requires gestion access (owner or profesor) for all operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, joinedload

from src.dependencies import (
    get_db_session as get_db,
    require_gestion_access,
)
from src.database.orm_models import PlantillaRutina, GimnasioPlantilla

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/gyms", tags=["gym-templates"])


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


def _safe_service(db: Session):
    """Lazily import GymTemplateService to avoid circular imports."""
    try:
        from src.services.gym_template_service import GymTemplateService
        return GymTemplateService(db)
    except ImportError:
        # Fallback: service not yet implemented
        return None


# ========== GYM TEMPLATE ASSIGNMENT ENDPOINTS ==========

@router.post("/{gym_id}/templates/assign", response_model=Dict[str, Any])
async def assign_template_to_gym(
    request: Request,
    gym_id: int,
    template_id: int = Query(..., description="Template ID to assign"),
    priority: int = Query(0, description="Priority (0 = highest)"),
    custom_config: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Assign a template to a specific gym."""
    try:
        user_id = _require_session_user_id(request)
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        assignment = service.assign_template_to_gym(
            gym_id=gym_id,
            template_id=template_id,
            assigned_by=user_id,
            priority=priority,
            custom_config=custom_config,
            notes=notes,
        )

        return {
            "success": True,
            "assignment": {
                "id": assignment.id,
                "gym_id": assignment.gimnasio_id,
                "template_id": assignment.plantilla_id,
                "priority": assignment.prioridad,
                "assigned_by": assignment.asignada_por,
                "fecha_asignacion": assignment.fecha_asignacion.isoformat(),
                "custom_config": assignment.configuracion_personalizada,
                "notes": assignment.notas,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error assigning template to gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{gym_id}/templates", response_model=Dict[str, Any])
async def get_gym_templates(
    gym_id: int,
    active_only: bool = Query(True, description="Only active assignments"),
    include_analytics: bool = Query(False, description="Include analytics data"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get all templates assigned to a gym."""
    try:
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        templates = service.get_gym_templates(
            gym_id=gym_id,
            active_only=active_only,
            include_analytics=include_analytics,
        )

        return {
            "success": True,
            "gym_id": gym_id,
            "templates": templates,
            "total": len(templates),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting templates for gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{gym_id}/templates/{assignment_id}", response_model=Dict[str, Any])
async def update_gym_template_assignment(
    request: Request,
    gym_id: int,
    assignment_id: int,
    updates: Dict[str, Any],
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Update a gym template assignment."""
    try:
        user_id = _require_session_user_id(request)
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        assignment = service.update_gym_template_assignment(
            assignment_id=assignment_id,
            updates=updates,
            updated_by=user_id,
        )

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {
            "success": True,
            "assignment": {
                "id": assignment.id,
                "gym_id": assignment.gimnasio_id,
                "template_id": assignment.plantilla_id,
                "priority": assignment.prioridad,
                "activa": assignment.activa,
                "custom_config": assignment.configuracion_personalizada,
                "notes": assignment.notas,
            },
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating gym template assignment {assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{gym_id}/templates/{assignment_id}", response_model=Dict[str, Any])
async def remove_template_from_gym(
    request: Request,
    gym_id: int,
    assignment_id: int,
    soft_delete: bool = Query(True, description="Soft delete (deactivate) instead of hard delete"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Remove a template assignment from a gym."""
    try:
        user_id = _require_session_user_id(request)
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        success = service.remove_template_from_gym(
            assignment_id=assignment_id,
            removed_by=user_id,
            soft_delete=soft_delete,
        )

        if not success:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {
            "success": True,
            "message": "Template assignment removed successfully",
            "soft_delete": soft_delete,
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removing template from gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== TEMPLATE DISCOVERY ENDPOINTS ==========

@router.get("/{gym_id}/templates/available", response_model=Dict[str, Any])
async def get_available_templates_for_gym(
    gym_id: int,
    category: Optional[str] = Query(None, description="Filter by category"),
    search_query: Optional[str] = Query(None, description="Search query"),
    limit: int = Query(50, ge=1, le=100, description="Limit results"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get templates available for assignment to a gym."""
    try:
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        templates = service.get_available_templates_for_gym(
            gym_id=gym_id,
            category=category,
            search_query=search_query,
        )

        return {
            "success": True,
            "gym_id": gym_id,
            "templates": templates[:limit],
            "total": len(templates),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting available templates for gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{gym_id}/templates/recommended", response_model=Dict[str, Any])
async def get_recommended_templates_for_gym(
    gym_id: int,
    limit: int = Query(10, ge=1, le=20, description="Number of recommendations"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get recommended templates for a gym based on usage patterns."""
    try:
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        templates = service.get_recommended_templates_for_gym(
            gym_id=gym_id,
            limit=limit,
        )

        return {
            "success": True,
            "gym_id": gym_id,
            "recommended_templates": templates,
            "total": len(templates),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting recommended templates for gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== BULK OPERATIONS ==========

@router.post("/{gym_id}/templates/bulk-assign", response_model=Dict[str, Any])
async def bulk_assign_templates_to_gym(
    request: Request,
    gym_id: int,
    template_ids: List[int],
    priority_start: int = Query(0, description="Starting priority"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Assign multiple templates to a gym."""
    try:
        if len(template_ids) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 templates per bulk operation")

        user_id = _require_session_user_id(request)
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        assignments = service.bulk_assign_templates_to_gym(
            gym_id=gym_id,
            template_ids=template_ids,
            assigned_by=user_id,
            priority_start=priority_start,
        )

        return {
            "success": True,
            "gym_id": gym_id,
            "assigned_count": len(assignments),
            "assignments": [
                {
                    "id": a.id,
                    "template_id": a.plantilla_id,
                    "priority": a.prioridad,
                }
                for a in assignments
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk assigning templates to gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{gym_id}/templates/bulk", response_model=Dict[str, Any])
async def bulk_remove_templates_from_gym(
    request: Request,
    gym_id: int,
    assignment_ids: List[int],
    soft_delete: bool = Query(True, description="Soft delete (deactivate) instead of hard delete"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Remove multiple template assignments from a gym."""
    try:
        if len(assignment_ids) > 20:
            raise HTTPException(status_code=400, detail="Maximum 20 assignments per bulk operation")

        user_id = _require_session_user_id(request)
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        removed_count = 0
        errors = []

        for assignment_id in assignment_ids:
            try:
                success = service.remove_template_from_gym(
                    assignment_id=assignment_id,
                    removed_by=user_id,
                    soft_delete=soft_delete,
                )
                if success:
                    removed_count += 1
            except Exception as inner_e:
                errors.append(f"Assignment {assignment_id}: {str(inner_e)}")

        return {
            "success": True,
            "gym_id": gym_id,
            "removed_count": removed_count,
            "requested_count": len(assignment_ids),
            "errors": errors,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error bulk removing templates from gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== ANALYTICS ENDPOINTS ==========

@router.get("/{gym_id}/templates/analytics", response_model=Dict[str, Any])
async def get_gym_template_analytics(
    gym_id: int,
    template_id: Optional[int] = Query(None, description="Specific template ID"),
    days: int = Query(30, ge=1, le=365, description="Days to analyze"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get template usage analytics for a gym."""
    try:
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        stats = service.get_gym_template_usage_stats(
            gym_id=gym_id,
            template_id=template_id,
            days=days,
        )

        return {
            "success": True,
            "gym_id": gym_id,
            "template_id": template_id,
            "days_analyzed": days,
            "analytics": stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting template analytics for gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{gym_id}/templates/popular", response_model=Dict[str, Any])
async def get_gym_popular_templates(
    gym_id: int,
    days: int = Query(30, ge=1, le=365, description="Days to analyze"),
    limit: int = Query(10, ge=1, le=20, description="Limit results"),
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get most popular templates for a gym."""
    try:
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        stats = service.get_gym_template_usage_stats(gym_id=gym_id, days=days)

        template_usage = stats.get("template_usage", {})
        template_ids = list(template_usage.keys())[:limit]

        if not template_ids:
            return {
                "success": True,
                "gym_id": gym_id,
                "popular_templates": [],
                "days_analyzed": days,
            }

        templates = db.query(PlantillaRutina).filter(
            PlantillaRutina.id.in_(template_ids)
        ).all()

        template_dict = {t.id: t for t in templates}
        popular_templates = []

        for tid, usage_count in sorted(
            template_usage.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:limit]:
            template = template_dict.get(tid)
            if template:
                popular_templates.append({
                    "template_id": tid,
                    "template_name": template.nombre,
                    "template_category": template.categoria,
                    "usage_count": usage_count,
                    "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
                    "dias_semana": template.dias_semana,
                })

        return {
            "success": True,
            "gym_id": gym_id,
            "popular_templates": popular_templates,
            "days_analyzed": days,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting popular templates for gym {gym_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


# ========== TEMPLATE CUSTOMIZATION ENDPOINTS ==========

@router.post("/{gym_id}/templates/{assignment_id}/customize", response_model=Dict[str, Any])
async def customize_gym_template(
    request: Request,
    gym_id: int,
    assignment_id: int,
    custom_config: Dict[str, Any],
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Apply custom configuration to a gym template assignment."""
    try:
        user_id = _require_session_user_id(request)
        service = _safe_service(db)
        if service is None:
            raise HTTPException(status_code=501, detail="GymTemplateService not available")

        assignment = service.update_gym_template_assignment(
            assignment_id=assignment_id,
            updates={
                "custom_config": custom_config,
                "notes": notes,
            },
            updated_by=user_id,
        )

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        return {
            "success": True,
            "assignment": {
                "id": assignment.id,
                "template_id": assignment.plantilla_id,
                "custom_config": assignment.configuracion_personalizada,
                "notes": assignment.notas,
                "customized_by": user_id,
                "customized_at": datetime.utcnow().isoformat(),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error customizing gym template {assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{gym_id}/templates/{assignment_id}/config", response_model=Dict[str, Any])
async def get_gym_template_config(
    gym_id: int,
    assignment_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_gestion_access),
):
    """Get template configuration for a gym assignment."""
    try:
        assignment = db.query(GimnasioPlantilla).filter(
            GimnasioPlantilla.id == assignment_id,
            GimnasioPlantilla.gimnasio_id == gym_id,
        ).options(
            joinedload(GimnasioPlantilla.plantilla)
        ).first()

        if not assignment:
            raise HTTPException(status_code=404, detail="Assignment not found")

        base_config = assignment.plantilla.configuracion
        custom_config = assignment.configuracion_personalizada or {}
        merged_config = {**base_config, **custom_config}

        return {
            "success": True,
            "assignment_id": assignment_id,
            "template_id": assignment.plantilla_id,
            "template_name": assignment.plantilla.nombre,
            "base_config": base_config,
            "custom_config": custom_config,
            "merged_config": merged_config,
            "has_customization": bool(custom_config),
            "notes": assignment.notas,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting gym template config {assignment_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
