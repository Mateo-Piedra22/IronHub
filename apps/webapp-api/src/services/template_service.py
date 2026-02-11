"""
Template Service

This module provides business logic for template management,
including template operations, versioning, validation, and analytics.
"""

from typing import List, Optional, Dict, Any, Tuple, BinaryIO
from datetime import datetime, timedelta
import json
import logging
import base64
import os
from pathlib import Path

from sqlalchemy.orm import joinedload
from sqlalchemy import desc, func

from ..repositories.template_repository import TemplateRepository
from ..models.orm_models import (
    PlantillaRutina, PlantillaRutinaVersion, GimnasioPlantilla,
    PlantillaAnalitica, Usuario
)
from ..services.template_validator import TemplateValidator, ValidationResult
from ..services.pdf_engine import PDFEngine
from ..services.variable_resolver import VariableResolver, VariableContext
from ..services.exercise_table_builder import ExerciseTableBuilder, TableConfig, TableFormat
from ..services.qr_code_manager import QRCodeManager, QRConfig, QRContext
from ..services.preview_engine import PreviewEngine, PreviewConfig, PreviewFormat, PreviewQuality
from ..services.template_analytics import TemplateAnalyticsService

logger = logging.getLogger(__name__)


class TemplateService:
    """Service for template business logic"""
    
    def __init__(self, db_session):
        self.db = db_session
        self.repository = TemplateRepository(db_session)
        
        # Initialize validator with error handling
        try:
            self.validator = TemplateValidator()
        except Exception as e:
            logger.error(f"Failed to initialize TemplateValidator: {e}")
            self.validator = None
        
        # Initialize Phase 2 components with error handling
        try:
            self.pdf_engine = PDFEngine()
        except Exception as e:
            logger.warning(f"Failed to initialize PDFEngine: {e}")
            self.pdf_engine = None
        
        try:
            self.variable_resolver = VariableResolver()
        except Exception as e:
            logger.warning(f"Failed to initialize VariableResolver: {e}")
            self.variable_resolver = None
        
        try:
            self.exercise_builder = ExerciseTableBuilder()
        except Exception as e:
            logger.warning(f"Failed to initialize ExerciseTableBuilder: {e}")
            self.exercise_builder = None
        
        try:
            self.qr_manager = QRCodeManager()
        except Exception as e:
            logger.warning(f"Failed to initialize QRCodeManager: {e}")
            self.qr_manager = None
        
        try:
            self.preview_engine = PreviewEngine()
        except Exception as e:
            logger.warning(f"Failed to initialize PreviewEngine: {e}")
            self.preview_engine = None
        
        # Initialize analytics service with error handling
        try:
            self.analytics_service = TemplateAnalyticsService(db_session)
        except Exception as e:
            logger.warning(f"Failed to initialize TemplateAnalyticsService: {e}")
            self.analytics_service = None
    
    # === Template Management ===
    
    def create_template(
        self,
        nombre: str,
        configuracion: Dict[str, Any],
        descripcion: Optional[str] = None,
        categoria: str = "general",
        dias_semana: Optional[int] = None,
        creada_por: Optional[int] = None,
        tags: Optional[List[str]] = None,
        publica: bool = False,
        generate_preview: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create a new template with validation and preview generation"""
        try:
            # Validate template configuration if validator is available
            if self.validator:
                validation_result = self.validator.validate_template(configuracion)
                if not validation_result.is_valid:
                    error_messages = [error["message"] for error in validation_result.errors]
                    return None, f"Template validation failed: {'; '.join(error_messages)}"
            else:
                logger.warning("TemplateValidator not available, skipping validation")
            
            # Create template
            template, error = self.repository.create_template(
                nombre=nombre,
                configuracion=configuracion,
                descripcion=descripcion,
                categoria=categoria,
                dias_semana=dias_semana,
                creada_por=creada_por,
                tags=tags,
                publica=publica
            )
            
            if not template:
                return None, error
            
            # Generate preview if requested and preview engine is available
            preview_url = None
            if generate_preview and self.preview_engine:
                try:
                    preview_url = self._generate_template_preview(template)
                except Exception as e:
                    logger.warning(f"Failed to generate preview for template {template.id}: {e}")
            
            # Update template with preview URL
            if preview_url:
                self.repository.update_template(
                    template.id,
                    {"preview_url": preview_url}
                )
            
            # Return template data
            return self._template_to_dict(template, include_versions=False), None
            
        except Exception as e:
            logger.error(f"Error creating template: {e}")
            return None, f"Internal error: {str(e)}"
    
    def get_template(self, template_id: int, include_versions: bool = False) -> Optional[Dict[str, Any]]:
        """Get template by ID"""
        try:
            template = self.repository.get_template(template_id)
            if not template:
                return None
            
            return self._template_to_dict(template, include_versions)
            
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    def update_template(
        self,
        template_id: int,
        updates: Dict[str, Any],
        creada_por: Optional[int] = None,
        cambios_descripcion: Optional[str] = None,
        generate_preview: bool = True
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Update template with validation and preview generation"""
        try:
            # Validate new configuration if provided
            if "configuracion" in updates:
                validation_result = self.validator.validate_template(updates["configuracion"])
                if not validation_result.is_valid:
                    error_messages = [error["message"] for error in validation_result.errors]
                    return None, f"Template validation failed: {'; '.join(error_messages)}"
            
            # Update template
            template, error = self.repository.update_template(
                template_id=template_id,
                updates=updates,
                creada_por=creada_por,
                cambios_descripcion=cambios_descripcion
            )
            
            if not template:
                return None, error
            
            # Generate new preview if requested
            preview_url = None
            if generate_preview and self.pdf_engine:
                try:
                    preview_url = self._generate_template_preview(template)
                except Exception as e:
                    logger.warning(f"Failed to generate preview for template {template.id}: {e}")
            
            # Update template with preview URL
            if preview_url:
                self.repository.update_template(
                    template.id,
                    {"preview_url": preview_url}
                )
            
            return self._template_to_dict(template, include_versions=False), None
            
        except Exception as e:
            logger.error(f"Error updating template {template_id}: {e}")
            return None, f"Internal error: {str(e)}"
    
    def delete_template(self, template_id: int) -> Tuple[bool, Optional[str]]:
        """Delete template (soft delete)"""
        try:
            return self.repository.delete_template(template_id)
        except Exception as e:
            logger.error(f"Error deleting template {template_id}: {e}")
            return False, f"Internal error: {str(e)}"
    
    def get_templates(
        self,
        query: Optional[str] = None,
        categoria: Optional[str] = None,
        activa: Optional[bool] = None,
        publica: Optional[bool] = None,
        sort_by: str = "fecha_creacion",
        sort_order: str = "desc",
        limit: int = 50,
        offset: int = 0,
        gym_id: Optional[int] = None,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Get templates with filtering and pagination"""
        try:
            return self.search_templates(
                query=query,
                categoria=categoria,
                dias_semana=None,
                publica=publica,
                creada_por=user_id,
                tags=None,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )
        except Exception as e:
            logger.error(f"Error getting templates: {e}")
            return {"templates": [], "total": 0, "limit": limit, "offset": offset, "has_more": False}
    
    def get_template_by_id(self, template_id: int, user_id: Optional[int] = None) -> Optional[PlantillaRutina]:
        """Get template by ID with access control"""
        try:
            template = self.repository.get_template(template_id)
            if not template:
                return None
            
            # Check access permissions if user_id provided
            if user_id and not self._check_template_access(template, user_id):
                return None
            
            return template
        except Exception as e:
            logger.error(f"Error getting template {template_id}: {e}")
            return None
    
    def _check_template_access(self, template: PlantillaRutina, user_id: int) -> bool:
        """Check if user has access to template"""
        # User can access if:
        # 1. They created the template
        # 2. Template is public
        # 3. Template is assigned to their gym
        if template.creada_por == user_id or template.publica:
            return True
        
        # Check gym assignment
        # This would require getting user's gym ID - simplified for now
        return True  # Simplified - implement proper gym checking
    
    # === Template Search and Discovery ===
    
    def search_templates(
        self,
        query: Optional[str] = None,
        categoria: Optional[str] = None,
        dias_semana: Optional[int] = None,
        publica: Optional[bool] = None,
        creada_por: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "fecha_creacion",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Search templates with filters and pagination"""
        try:
            templates = self.repository.search_templates(
                query=query,
                categoria=categoria,
                dias_semana=dias_semana,
                publica=publica,
                creada_por=creada_por,
                tags=tags,
                limit=limit,
                offset=offset,
                sort_by=sort_by,
                sort_order=sort_order
            )
            
            # Get total count for pagination
            total_count = len(templates)
            
            return {
                "templates": [self._template_to_dict(t, include_versions=False) for t in templates],
                "total": total_count,
                "limit": limit,
                "offset": offset,
                "has_more": offset + limit < total_count
            }
            
        except Exception as e:
            logger.error(f"Error searching templates: {e}")
            return {"templates": [], "total": 0, "limit": limit, "offset": offset, "has_more": False}
    
    def get_templates_for_gym(
        self,
        gimnasio_id: int,
        include_public: bool = True,
        include_analytics: bool = False
    ) -> List[Dict[str, Any]]:
        """Get templates available to a specific gym"""
        try:
            templates = self.repository.get_templates_by_gym(
                gimnasio_id=gimnasio_id,
                activa=True,
                include_public=include_public
            )
            
            result = []
            for template in templates:
                template_dict = self._template_to_dict(template, include_versions=False)
                
                # Add analytics if requested
                if include_analytics:
                    analytics = self.repository.get_template_analytics(template.id)
                    template_dict["analytics"] = analytics
                
                result.append(template_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting templates for gym {gimnasio_id}: {e}")
            return []
    
    # === Template Version Management ===
    
    
    def compare_template_versions(
        self,
        template_id: int,
        version1: str,
        version2: str
    ) -> Optional[Dict[str, Any]]:
        """Compare two versions of a template"""
        try:
            v1 = self.repository.get_template_version(template_id, version1)
            v2 = self.repository.get_template_version(template_id, version2)
            
            if not v1 or not v2:
                return None
            
            # Simple comparison - in production you might want more sophisticated diff
            return {
                "template_id": template_id,
                "version1": {
                    "version": v1.version,
                    "configuracion": v1.configuracion,
                    "fecha_creacion": v1.fecha_creacion.isoformat(),
                    "cambios_descripcion": v1.cambios_descripcion
                },
                "version2": {
                    "version": v2.version,
                    "configuracion": v2.configuracion,
                    "fecha_creacion": v2.fecha_creacion.isoformat(),
                    "cambios_descripcion": v2.cambios_descripcion
                },
                "identical": v1.configuracion == v2.configuracion
            }
            
        except Exception as e:
            logger.error(f"Error comparing versions for template {template_id}: {e}")
            return None
    
    # === Gym Template Management ===
    
    
    
    def get_gym_template_assignments(self, gimnasio_id: int) -> List[Dict[str, Any]]:
        """Get all template assignments for a gym"""
        try:
            assignments = self.db.query(GimnasioPlantilla).options(
                joinedload(GimnasioPlantilla.plantilla),
                joinedload(GimnasioPlantilla.asignador)
            ).filter(
                GimnasioPlantilla.gimnasio_id == gimnasio_id
            ).order_by(desc(GimnasioPlantilla.prioridad)).all()
            
            return [self._assignment_to_dict(a) for a in assignments]
            
        except Exception as e:
            logger.error(f"Error getting assignments for gym {gimnasio_id}: {e}")
            return []
    
    # === Template Preview and Export ===
    
    def generate_template_preview(
        self,
        template_id: int,
        sample_data: Optional[Dict[str, Any]] = None,
        format: str = "pdf",
        quality: str = "medium",
        page_number: int = 1
    ) -> Tuple[Optional[str], Optional[str]]:
        """Generate preview for template"""
        try:
            template = self.repository.get_template(template_id)
            if not template:
                return None, "Template not found"
            
            # Configure preview
            preview_format = PreviewFormat(format.lower())
            preview_quality = PreviewQuality(quality.lower())
            
            config = PreviewConfig(
                format=preview_format,
                quality=preview_quality,
                page_number=page_number,
                use_cache=True,
                generate_sample_data=sample_data is None
            )
            
            # Generate preview
            result = self.preview_engine.generate_preview(
                template_config=template.configuracion,
                config=config,
                custom_data=sample_data
            )
            
            if not result.success:
                return None, result.error_message
            
            # Save preview to file if PDF
            if result.format == PreviewFormat.PDF:
                preview_path = f"previews/template_{template_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
                os.makedirs("previews", exist_ok=True)
                
                with open(preview_path, "wb") as f:
                    f.write(result.data)
                
                preview_url = f"/{preview_path}"
            else:
                preview_url = f"data:{result.format.value};base64,{base64.b64encode(result.data).decode()}"
            
            # Log preview generation
            self.repository._log_analytics(
                template_id=template_id,
                evento_tipo="preview",
                exitoso=True,
                datos_evento={
                    "format": format,
                    "quality": quality,
                    "page_number": page_number,
                    "generation_time": result.generation_time,
                    "cache_hit": result.cache_hit
                }
            )
            
            return preview_url, None
            
        except Exception as e:
            logger.error(f"Error generating preview for template {template_id}: {e}")
            
            # Log failed preview
            self.repository._log_analytics(
                template_id=template_id,
                evento_tipo="preview",
                exitoso=False,
                error_message=str(e)
            )
            
            return None, f"Internal error: {str(e)}"
    
    
    
    # === Analytics and Metrics ===
    
    
    def get_popular_templates(
        self,
        limit: int = 10,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get most popular templates"""
        try:
            popular = self.repository.get_popular_templates(limit, fecha_inicio, fecha_fin)
            return [
                {
                    **self._template_to_dict(template, include_versions=False),
                    "usage_count": usage_count
                }
                for template, usage_count in popular
            ]
        except Exception as e:
            logger.error(f"Error getting popular templates: {e}")
            return []
    
    def get_template_statistics(self) -> Dict[str, Any]:
        """Get overall template statistics"""
        try:
            # Get basic counts
            total_templates = self.db.query(PlantillaRutina).filter(
                PlantillaRutina.activa == True
            ).count()
            
            public_templates = self.db.query(PlantillaRutina).filter(
                PlantillaRutina.activa == True,
                PlantillaRutina.publica == True
            ).count()
            
            # Get categories distribution
            categories = self.db.query(
                PlantillaRutina.categoria,
                func.count(PlantillaRutina.id).label("count")
            ).filter(
                PlantillaRutina.activa == True
            ).group_by(PlantillaRutina.categoria).all()
            
            # Get recent activity
            recent_activity = self.db.query(PlantillaAnalitica).filter(
                PlantillaAnalitica.fecha_evento >= datetime.utcnow() - timedelta(days=7)
            ).count()
            
            return {
                "total_templates": total_templates,
                "public_templates": public_templates,
                "private_templates": total_templates - public_templates,
                "categories": [{"name": cat, "count": count} for cat, count in categories],
                "recent_activity_7_days": recent_activity,
                "last_updated": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting template statistics: {e}")
            return {}
    
    # === Utility Methods ===
    
    def _template_to_dict(self, template: PlantillaRutina, include_versions: bool = False) -> Dict[str, Any]:
        """Convert template to dictionary"""
        result = {
            "id": template.id,
            "nombre": template.nombre,
            "descripcion": template.descripcion,
            "configuracion": template.configuracion,
            "categoria": template.categoria,
            "dias_semana": template.dias_semana,
            "activa": template.activa,
            "publica": template.publica,
            "creada_por": template.creada_por,
            "fecha_creacion": template.fecha_creacion.isoformat() if template.fecha_creacion else None,
            "fecha_actualizacion": template.fecha_actualizacion.isoformat() if template.fecha_actualizacion else None,
            "version_actual": template.version_actual,
            "tags": template.tags or [],
            "preview_url": template.preview_url,
            "uso_count": template.uso_count,
            "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
            "rating_count": template.rating_count
        }
        
        # Include creator info
        if template.creador:
            result["creador"] = {
                "id": template.creador.id,
                "nombre": template.creador.nombre
            }
        
        # Include versions if requested
        if include_versions:
            result["versiones"] = [self._version_to_dict(v) for v in template.versiones]
        
        return result
    
    def _version_to_dict(self, version: PlantillaRutinaVersion) -> Dict[str, Any]:
        """Convert template version to dictionary"""
        return {
            "id": version.id,
            "plantilla_id": version.plantilla_id,
            "version": version.version,
            "configuracion": version.configuracion,
            "cambios_descripcion": version.cambios_descripcion,
            "creada_por": version.creada_por,
            "fecha_creacion": version.fecha_creacion.isoformat() if version.fecha_creacion else None,
            "es_actual": version.es_actual,
            "creador": {
                "id": version.creador.id,
                "nombre": version.creador.nombre
            } if version.creador else None
        }
    
    def _assignment_to_dict(self, assignment: GimnasioPlantilla) -> Dict[str, Any]:
        """Convert gym assignment to dictionary"""
        return {
            "id": assignment.id,
            "gimnasio_id": assignment.gimnasio_id,
            "plantilla_id": assignment.plantilla_id,
            "activa": assignment.activa,
            "prioridad": assignment.prioridad,
            "configuracion_personalizada": assignment.configuracion_personalizada,
            "asignada_por": assignment.asignada_por,
            "fecha_asignacion": assignment.fecha_asignacion.isoformat() if assignment.fecha_asignacion else None,
            "fecha_ultima_uso": assignment.fecha_ultima_uso.isoformat() if assignment.fecha_ultima_uso else None,
            "uso_count": assignment.uso_count,
            "notas": assignment.notas,
            "plantilla": self._template_to_dict(assignment.plantilla, include_versions=False) if assignment.plantilla else None,
            "asignador": {
                "id": assignment.asignador.id,
                "nombre": assignment.asignador.nombre
            } if assignment.asignador else None
        }
    
    def _generate_template_preview(
        self,
        template: PlantillaRutina,
        sample_data: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate preview for template"""
        try:
            # Configure preview
            config = PreviewConfig(
                format=PreviewFormat.PDF,
                quality=PreviewQuality.MEDIUM,
                use_cache=True,
                generate_sample_data=sample_data is None
            )
            
            # Generate preview
            result = self.preview_engine.generate_preview(
                template_config=template.configuracion,
                config=config,
                custom_data=sample_data
            )
            
            if not result.success:
                logger.warning(f"Preview generation failed: {result.error_message}")
                return ""
            
            # Save preview to file
            preview_path = f"previews/template_{template.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
            os.makedirs("previews", exist_ok=True)
            
            with open(preview_path, "wb") as f:
                f.write(result.data)
            
            return f"/{preview_path}"
            
        except Exception as e:
            logger.warning(f"Failed to generate preview for template {template.id}: {e}")
            return ""
    
    def validate_template_config(self, configuracion: Dict[str, Any]) -> ValidationResult:
        """Validate template configuration"""
        if not self.validator:
            # Return a basic validation result if validator is not available
            return ValidationResult(
                is_valid=True,
                errors=[],
                warnings=[],
                info=[],
                performance_score=50.0,
                security_score=50.0
            )
        
        return self.validator.validate_template(configuracion)
    
    def get_template_categories(self) -> List[str]:
        """Get all available template categories"""
        return self.repository.get_template_categories()
    
    def get_template_tags(self) -> List[str]:
        """Get all available template tags"""
        return self.repository.get_template_tags()
    
    # === Analytics Methods ===
    
    def get_template_analytics(self, template_id: int, days: int = 30) -> Dict[str, Any]:
        """Get analytics for a specific template"""
        if not self.analytics_service:
            logger.warning("TemplateAnalyticsService not available")
            return {"error": "Analytics service not available"}
        
        try:
            return self.analytics_service.get_template_analytics(template_id, days)
        except Exception as e:
            logger.error(f"Error getting analytics for template {template_id}: {e}")
            return {"error": str(e)}
    
    def get_analytics_dashboard(self, gimnasio_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """Get analytics dashboard data"""
        if not self.analytics_service:
            logger.warning("TemplateAnalyticsService not available")
            return {"error": "Analytics service not available"}
        
        try:
            return self.analytics_service.get_analytics_dashboard(gimnasio_id, days)
        except Exception as e:
            logger.error(f"Error getting analytics dashboard: {e}")
            return {"error": str(e)}
    
    # === Additional API Methods ===
    
    def generate_template_preview_bytes(
        self,
        template_id: int,
        sample_data: Optional[Dict[str, Any]] = None,
        format: str = "pdf",
        quality: str = "medium",
        page_number: int = 1
    ) -> Optional[bytes]:
        """Generate template preview as bytes"""
        try:
            template = self.repository.get_template(template_id)
            if not template:
                return None
            
            # Configure preview
            preview_format = PreviewFormat(format.lower())
            preview_quality = PreviewQuality(quality.lower())
            
            config = PreviewConfig(
                format=preview_format,
                quality=preview_quality,
                page_number=page_number,
                use_cache=True,
                generate_sample_data=sample_data is None
            )
            
            # Generate preview
            result = self.preview_engine.generate_preview(
                template_config=template.configuracion,
                config=config,
                custom_data=sample_data
            )
            
            if result.success and result.format in [PreviewFormat.PDF, PreviewFormat.IMAGE, PreviewFormat.THUMBNAIL]:
                return result.data
            
            return None
            
        except Exception as e:
            logger.error(f"Error generating preview bytes for template {template_id}: {e}")
            return None
    
    def get_template_versions(self, template_id: int) -> List[Dict[str, Any]]:
        """Get all versions of a template"""
        try:
            versions = self.repository.get_template_versions(template_id)
            return [self._version_to_dict(version) for version in versions]
        except Exception as e:
            logger.error(f"Error getting template versions for {template_id}: {e}")
            return []
    
    def create_template_version(
        self,
        template_id: int,
        configuracion: Dict[str, Any],
        version: str,
        descripcion: Optional[str] = None,
        creada_por: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Create a new version of a template"""
        try:
            # Validate configuration
            validation_result = self.validator.validate_template(configuracion)
            if not validation_result.is_valid:
                error_messages = [error["message"] for error in validation_result.errors]
                return None, f"Template validation failed: {'; '.join(error_messages)}"
            
            # Create version
            version_obj, error = self.repository.create_template_version(
                template_id=template_id,
                configuracion=configuracion,
                version=version,
                descripcion=descripcion,
                creada_por=creada_por
            )
            
            if not version_obj:
                return None, error
            
            return self._version_to_dict(version_obj), None
            
        except Exception as e:
            logger.error(f"Error creating template version: {e}")
            return None, f"Internal error: {str(e)}"
    
    def restore_template_version(
        self,
        template_id: int,
        version: str,
        restaurado_por: Optional[int] = None
    ) -> Tuple[bool, Optional[str]]:
        """Restore template to a specific version"""
        try:
            return self.repository.restore_template_version(
                template_id=template_id,
                version=version,
                restaurado_por=restaurado_por
            )
        except Exception as e:
            logger.error(f"Error restoring template version: {e}")
            return False, f"Internal error: {str(e)}"
    
    def import_template(
        self,
        template_data: Dict[str, Any],
        creada_por: Optional[int] = None,
        overwrite: bool = False
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Import template from data"""
        try:
            # Validate template data
            validation_result = self.validator.validate_template(template_data.get("configuracion", {}))
            if not validation_result.is_valid:
                error_messages = [error["message"] for error in validation_result.errors]
                return None, f"Template validation failed: {'; '.join(error_messages)}"
            
            # Check if template already exists
            existing_template = None
            if "id" in template_data:
                existing_template = self.repository.get_template(template_data["id"])
            
            if existing_template and not overwrite:
                return None, "Template already exists. Use overwrite parameter to replace."
            
            # Create or update template
            if existing_template and overwrite:
                template, error = self.repository.update_template(
                    template_id=existing_template.id,
                    updates={
                        "nombre": template_data.get("nombre", existing_template.nombre),
                        "configuracion": template_data.get("configuracion", existing_template.configuracion),
                        "descripcion": template_data.get("descripcion"),
                        "categoria": template_data.get("categoria", existing_template.categoria),
                        "dias_semana": template_data.get("dias_semana"),
                        "tags": template_data.get("tags", []),
                        "publica": template_data.get("publica", existing_template.publica)
                    },
                    creada_por=creada_por,
                    cambios_descripcion="Imported template"
                )
            else:
                template, error = self.repository.create_template(
                    nombre=template_data.get("nombre", "Imported Template"),
                    configuracion=template_data.get("configuracion", {}),
                    descripcion=template_data.get("descripcion"),
                    categoria=template_data.get("categoria", "general"),
                    dias_semana=template_data.get("dias_semana"),
                    creada_por=creada_por,
                    tags=template_data.get("tags", []),
                    publica=template_data.get("publica", False),
                    generate_preview=False
                )
            
            if not template:
                return None, error
            
            return self._template_to_dict(template, include_versions=False), None
            
        except Exception as e:
            logger.error(f"Error importing template: {e}")
            return None, f"Internal error: {str(e)}"
    
    def export_template(
        self,
        template_id: int,
        include_analytics: bool = False,
        include_versions: bool = False
    ) -> Dict[str, Any]:
        """Export template data"""
        try:
            template = self.repository.get_template(template_id)
            if not template:
                return {}
            
            export_data = {
                "id": template.id,
                "nombre": template.nombre,
                "descripcion": template.descripcion,
                "categoria": template.categoria,
                "dias_semana": template.dias_semana,
                "configuracion": template.configuracion,
                "tags": template.tags,
                "publica": template.publica,
                "creada_por": template.creada_por,
                "fecha_creacion": template.fecha_creacion.isoformat() if template.fecha_creacion else None,
                "version_actual": template.version_actual
            }
            
            # Include versions if requested
            if include_versions:
                versions = self.repository.get_template_versions(template_id)
                export_data["versions"] = [self._version_to_dict(version) for version in versions]
            
            # Include analytics if requested
            if include_analytics:
                analytics = self.get_template_analytics(template_id)
                export_data["analytics"] = analytics
            
            return export_data
            
        except Exception as e:
            logger.error(f"Error exporting template {template_id}: {e}")
            return {}
    
    def assign_template_to_gym(
        self,
        gimnasio_id: int,
        template_id: int,
        prioridad: int = 0,
        asignada_por: Optional[int] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Assign template to gym"""
        try:
            assignment, error = self.repository.assign_template_to_gym(
                gimnasio_id=gimnasio_id,
                template_id=template_id,
                prioridad=prioridad,
                asignada_por=asignada_por
            )
            
            if not assignment:
                return None, error
            
            return self._assignment_to_dict(assignment), None
            
        except Exception as e:
            logger.error(f"Error assigning template to gym: {e}")
            return None, f"Internal error: {str(e)}"
    
    def remove_template_from_gym(self, assignment_id: int) -> Tuple[bool, Optional[str]]:
        """Remove template assignment from gym"""
        try:
            return self.repository.remove_template_from_gym(assignment_id)
        except Exception as e:
            logger.error(f"Error removing template assignment: {e}")
            return False, f"Internal error: {str(e)}"
    
    # === Helper Methods ===
    
    def _version_to_dict(self, version) -> Dict[str, Any]:
        """Convert version object to dictionary"""
        return {
            "id": version.id,
            "plantilla_id": version.plantilla_id,
            "version": version.version,
            "configuracion": version.configuracion,
            "descripcion": version.descripcion,
            "creada_por": version.creada_por,
            "fecha_creacion": version.fecha_creacion.isoformat() if version.fecha_creacion else None,
            "es_actual": version.es_actual,
            "creador": {
                "id": version.creador.id,
                "nombre": version.creador.nombre
            } if version.creador else None
        }
    
    def _assignment_to_dict(self, assignment) -> Dict[str, Any]:
        """Convert assignment object to dictionary"""
        return {
            "id": assignment.id,
            "gimnasio_id": assignment.gimnasio_id,
            "plantilla_id": assignment.plantilla_id,
            "activa": assignment.activa,
            "prioridad": assignment.prioridad,
            "asignada_por": assignment.asignada_por,
            "fecha_asignacion": assignment.fecha_asignacion.isoformat() if assignment.fecha_asignacion else None,
            "uso_count": assignment.uso_count,
            "gimnasio": {
                "id": assignment.gimnasio.id,
                "nombre": assignment.gimnasio.nombre
            } if assignment.gimnasio else None,
            "asignador": {
                "id": assignment.asignador.id,
                "nombre": assignment.asignador.nombre
            } if assignment.asignador else None
        }


# Export main class
__all__ = ["TemplateService"]
