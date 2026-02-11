"""
Template Repository

This module provides data access layer for template management,
including CRUD operations, versioning, and analytics.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import and_, or_, desc, asc, func, text
from sqlalchemy.exc import SQLAlchemyError

from ..models.orm_models import (
    PlantillaRutina, PlantillaRutinaVersion, GimnasioPlantilla,
    PlantillaAnalitica, PlantillaMercado, Usuario
)
from ..services.template_validator import TemplateValidator, ValidationResult


class TemplateRepository:
    """Repository for template management operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.validator = TemplateValidator()
    
    # === Template CRUD Operations ===
    
    def create_template(
        self,
        nombre: str,
        configuracion: Dict[str, Any],
        descripcion: Optional[str] = None,
        categoria: str = "general",
        dias_semana: Optional[int] = None,
        creada_por: Optional[int] = None,
        tags: Optional[List[str]] = None,
        publica: bool = False
    ) -> Tuple[Optional[PlantillaRutina], Optional[str]]:
        """Create a new template"""
        try:
            # Validate template configuration
            validation_result = self.validator.validate_template(configuracion)
            if not validation_result.is_valid:
                error_messages = [error["message"] for error in validation_result.errors]
                return None, f"Template validation failed: {'; '.join(error_messages)}"
            
            # Create template
            template = PlantillaRutina(
                nombre=nombre,
                descripcion=descripcion,
                configuracion=configuracion,
                categoria=categoria,
                dias_semana=dias_semana,
                creada_por=creada_por,
                publica=publica,
                tags=tags or [],
                version_actual="1.0.0"
            )
            
            self.db.add(template)
            self.db.flush()  # Get the ID
            
            # Create initial version
            initial_version = PlantillaRutinaVersion(
                plantilla_id=template.id,
                version="1.0.0",
                configuracion=configuracion,
                cambios_descripcion="Initial version",
                creada_por=creada_por,
                es_actual=True
            )
            
            self.db.add(initial_version)
            self.db.commit()
            
            # Log creation event
            self._log_analytics(template.id, evento_tipo="create", exitoso=True)
            
            return template, None
            
        except SQLAlchemyError as e:
            self.db.rollback()
            return None, f"Database error: {str(e)}"
    
    def get_template(self, template_id: int) -> Optional[PlantillaRutina]:
        """Get template by ID with relationships"""
        try:
            return self.db.query(PlantillaRutina).options(
                joinedload(PlantillaRutina.creador),
                joinedload(PlantillaRutina.versiones),
                joinedload(PlantillaRutina.gimnasio_asignaciones),
                joinedload(PlantillaRutina.mercado)
            ).filter(PlantillaRutina.id == template_id).first()
        except SQLAlchemyError:
            return None
    
    def update_template(
        self,
        template_id: int,
        updates: Dict[str, Any],
        creada_por: Optional[int] = None,
        cambios_descripcion: Optional[str] = None
    ) -> Tuple[Optional[PlantillaRutina], Optional[str]]:
        """Update template and create new version"""
        try:
            template = self.get_template(template_id)
            if not template:
                return None, "Template not found"
            
            # Validate new configuration if provided
            if "configuracion" in updates:
                validation_result = self.validator.validate_template(updates["configuracion"])
                if not validation_result.is_valid:
                    error_messages = [error["message"] for error in validation_result.errors]
                    return None, f"Template validation failed: {'; '.join(error_messages)}"
            
            # Update template fields
            for field, value in updates.items():
                if field != "configuracion" and hasattr(template, field):
                    setattr(template, field, value)
            
            template.fecha_actualizacion = datetime.utcnow()
            
            # Create new version if configuration changed
            if "configuracion" in updates:
                new_version = self._increment_version(template.version_actual)
                
                # Mark previous versions as not current
                self.db.query(PlantillaRutinaVersion).filter(
                    PlantillaRutinaVersion.plantilla_id == template_id,
                    PlantillaRutinaVersion.es_actual == True
                ).update({"es_actual": False})
                
                # Create new version
                version = PlantillaRutinaVersion(
                    plantilla_id=template_id,
                    version=new_version,
                    configuracion=updates["configuracion"],
                    cambios_descripcion=cambios_descripcion or "Updated configuration",
                    creada_por=creada_por,
                    es_actual=True
                )
                
                template.version_actual = new_version
                self.db.add(version)
            
            self.db.commit()
            
            # Log update event
            self._log_analytics(template_id, evento_tipo="edit", exitoso=True)
            
            return template, None
            
        except SQLAlchemyError as e:
            self.db.rollback()
            return None, f"Database error: {str(e)}"
    
    def delete_template(self, template_id: int) -> Tuple[bool, Optional[str]]:
        """Delete template (soft delete by setting activa=False)"""
        try:
            template = self.db.query(PlantillaRutina).filter(
                PlantillaRutina.id == template_id
            ).first()
            
            if not template:
                return False, "Template not found"
            
            template.activa = False
            self.db.commit()
            
            # Log deletion event
            self._log_analytics(template_id, evento_tipo="delete", exitoso=True)
            
            return True, None
            
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f"Database error: {str(e)}"
    
    # === Template Search and Filtering ===
    
    def search_templates(
        self,
        query: Optional[str] = None,
        categoria: Optional[str] = None,
        dias_semana: Optional[int] = None,
        publica: Optional[bool] = None,
        activa: bool = True,
        creada_por: Optional[int] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        sort_by: str = "fecha_creacion",
        sort_order: str = "desc"
    ) -> List[PlantillaRutina]:
        """Search templates with filters"""
        try:
            q = self.db.query(PlantillaRutina).options(
                joinedload(PlantillaRutina.creador)
            )
            
            # Apply filters
            if query:
                q = q.filter(
                    or_(
                        PlantillaRutina.nombre.ilike(f"%{query}%"),
                        PlantillaRutina.descripcion.ilike(f"%{query}%")
                    )
                )
            
            if categoria:
                q = q.filter(PlantillaRutina.categoria == categoria)
            
            if dias_semana:
                q = q.filter(PlantillaRutina.dias_semana == dias_semana)
            
            if publica is not None:
                q = q.filter(PlantillaRutina.publica == publica)
            
            if activa is not None:
                q = q.filter(PlantillaRutina.activa == activa)
            
            if creada_por:
                q = q.filter(PlantillaRutina.creada_por == creada_por)
            
            if tags:
                # Filter templates that have any of the specified tags
                q = q.filter(PlantillaRutina.tags.overlap(tags))
            
            # Apply sorting
            sort_column = getattr(PlantillaRutina, sort_by, PlantillaRutina.fecha_creacion)
            if sort_order.lower() == "desc":
                q = q.order_by(desc(sort_column))
            else:
                q = q.order_by(asc(sort_column))
            
            # Apply pagination
            return q.offset(offset).limit(limit).all()
            
        except SQLAlchemyError:
            return []
    
    def get_templates_by_gym(
        self,
        gimnasio_id: int,
        activa: bool = True,
        include_public: bool = True
    ) -> List[PlantillaRutina]:
        """Get templates available to a specific gym"""
        try:
            q = self.db.query(PlantillaRutina).options(
                joinedload(PlantillaRutina.creador)
            ).join(
                GimnasioPlantilla,
                PlantillaRutina.id == GimnasioPlantilla.plantilla_id
            ).filter(
                GimnasioPlantilla.gimnasio_id == gimnasio_id,
                GimnasioPlantilla.activa == activa
            )
            
            if include_public:
                q = q.union(
                    self.db.query(PlantillaRutina).options(
                        joinedload(PlantillaRutina.creador)
                    ).filter(
                        PlantillaRutina.publica == True,
                        PlantillaRutina.activa == True
                    )
                )
            
            return q.order_by(GimnasioPlantilla.prioridad.desc()).all()
            
        except SQLAlchemyError:
            return []
    
    # === Template Version Management ===
    
    def get_template_versions(self, template_id: int) -> List[PlantillaRutinaVersion]:
        """Get all versions of a template"""
        try:
            return self.db.query(PlantillaRutinaVersion).options(
                joinedload(PlantillaRutinaVersion.creador)
            ).filter(
                PlantillaRutinaVersion.plantilla_id == template_id
            ).order_by(desc(PlantillaRutinaVersion.fecha_creacion)).all()
        except SQLAlchemyError:
            return []
    
    def get_template_version(self, template_id: int, version: str) -> Optional[PlantillaRutinaVersion]:
        """Get specific version of a template"""
        try:
            return self.db.query(PlantillaRutinaVersion).options(
                joinedload(PlantillaRutinaVersion.creador)
            ).filter(
                PlantillaRutinaVersion.plantilla_id == template_id,
                PlantillaRutinaVersion.version == version
            ).first()
        except SQLAlchemyError:
            return None
    
    def restore_template_version(self, template_id: int, version: str) -> Tuple[bool, Optional[str]]:
        """Restore template to a specific version"""
        try:
            template = self.get_template(template_id)
            if not template:
                return False, "Template not found"
            
            version_obj = self.get_template_version(template_id, version)
            if not version_obj:
                return False, "Version not found"
            
            # Mark current version as not current
            self.db.query(PlantillaRutinaVersion).filter(
                PlantillaRutinaVersion.plantilla_id == template_id,
                PlantillaRutinaVersion.es_actual == True
            ).update({"es_actual": False})
            
            # Create new version based on old one
            new_version = self._increment_version(template.version_actual)
            
            restored_version = PlantillaRutinaVersion(
                plantilla_id=template_id,
                version=new_version,
                configuracion=version_obj.configuracion,
                cambios_descripcion=f"Restored from version {version}",
                es_actual=True
            )
            
            template.version_actual = new_version
            template.configuracion = version_obj.configuracion
            template.fecha_actualizacion = datetime.utcnow()
            
            self.db.add(restored_version)
            self.db.commit()
            
            return True, None
            
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f"Database error: {str(e)}"
    
    # === Gym Template Assignment ===
    
    def assign_template_to_gym(
        self,
        gimnasio_id: int,
        plantilla_id: int,
        prioridad: int = 0,
        configuracion_personalizada: Optional[Dict[str, Any]] = None,
        asignada_por: Optional[int] = None,
        notas: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """Assign template to gym"""
        try:
            # Check if assignment already exists
            existing = self.db.query(GimnasioPlantilla).filter(
                GimnasioPlantilla.gimnasio_id == gimnasio_id,
                GimnasioPlantilla.plantilla_id == plantilla_id
            ).first()
            
            if existing:
                # Update existing assignment
                existing.prioridad = prioridad
                existing.configuracion_personalizada = configuracion_personalizada
                existing.asignada_por = asignada_por
                existing.notas = notas
                existing.fecha_asignacion = datetime.utcnow()
            else:
                # Create new assignment
                assignment = GimnasioPlantilla(
                    gimnasio_id=gimnasio_id,
                    plantilla_id=plantilla_id,
                    prioridad=prioridad,
                    configuracion_personalizada=configuracion_personalizada,
                    asignada_por=asignada_por,
                    notas=notas
                )
                self.db.add(assignment)
            
            self.db.commit()
            return True, None
            
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f"Database error: {str(e)}"
    
    def remove_template_from_gym(self, gimnasio_id: int, plantilla_id: int) -> Tuple[bool, Optional[str]]:
        """Remove template assignment from gym"""
        try:
            assignment = self.db.query(GimnasioPlantilla).filter(
                GimnasioPlantilla.gimnasio_id == gimnasio_id,
                GimnasioPlantilla.plantilla_id == plantilla_id
            ).first()
            
            if not assignment:
                return False, "Assignment not found"
            
            self.db.delete(assignment)
            self.db.commit()
            return True, None
            
        except SQLAlchemyError as e:
            self.db.rollback()
            return False, f"Database error: {str(e)}"
    
    # === Analytics and Metrics ===
    
    def get_template_analytics(
        self,
        template_id: int,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get analytics for a template"""
        try:
            if not fecha_inicio:
                fecha_inicio = datetime.utcnow() - timedelta(days=30)
            if not fecha_fin:
                fecha_fin = datetime.utcnow()
            
            analytics = self.db.query(PlantillaAnalitica).filter(
                PlantillaAnalitica.plantilla_id == template_id,
                PlantillaAnalitica.fecha_evento >= fecha_inicio,
                PlantillaAnalitica.fecha_evento <= fecha_fin
            ).all()
            
            # Calculate metrics
            total_events = len(analytics)
            successful_events = sum(1 for a in analytics if a.exitoso)
            avg_render_time = sum(a.tiempo_render_ms or 0 for a in analytics) / total_events if total_events > 0 else 0
            
            events_by_type = {}
            for a in analytics:
                events_by_type[a.evento_tipo] = events_by_type.get(a.evento_tipo, 0) + 1
            
            return {
                "total_events": total_events,
                "successful_events": successful_events,
                "success_rate": (successful_events / total_events * 100) if total_events > 0 else 0,
                "avg_render_time_ms": avg_render_time,
                "events_by_type": events_by_type,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin
            }
            
        except SQLAlchemyError:
            return {}
    
    def get_popular_templates(
        self,
        limit: int = 10,
        fecha_inicio: Optional[datetime] = None,
        fecha_fin: Optional[datetime] = None
    ) -> List[Tuple[PlantillaRutina, int]]:
        """Get most popular templates by usage"""
        try:
            if not fecha_inicio:
                fecha_inicio = datetime.utcnow() - timedelta(days=30)
            if not fecha_fin:
                fecha_fin = datetime.utcnow()
            
            popular = self.db.query(
                PlantillaRutina,
                func.count(PlantillaAnalitica.id).label("usage_count")
            ).join(
                PlantillaAnalitica,
                PlantillaRutina.id == PlantillaAnalitica.plantilla_id
            ).filter(
                PlantillaAnalitica.fecha_evento >= fecha_inicio,
                PlantillaAnalitica.fecha_evento <= fecha_fin,
                PlantillaAnalitica.evento_tipo.in_(["view", "export", "create"])
            ).group_by(
                PlantillaRutina.id
            ).order_by(
                desc("usage_count")
            ).limit(limit).all()
            
            return [(template, usage_count) for template, usage_count in popular]
            
        except SQLAlchemyError:
            return []
    
    # === Utility Methods ===
    
    def _increment_version(self, current_version: str) -> str:
        """Increment version number (semantic versioning)"""
        try:
            parts = current_version.split(".")
            if len(parts) != 3:
                return "1.0.1"
            
            major, minor, patch = map(int, parts)
            patch += 1
            return f"{major}.{minor}.{patch}"
        except:
            return "1.0.1"
    
    def _log_analytics(
        self,
        template_id: int,
        evento_tipo: str,
        exitoso: bool = True,
        gimnasio_id: Optional[int] = None,
        usuario_id: Optional[int] = None,
        datos_evento: Optional[Dict[str, Any]] = None,
        tiempo_render_ms: Optional[int] = None,
        error_message: Optional[str] = None
    ):
        """Log template analytics event"""
        try:
            analytics = PlantillaAnalitica(
                plantilla_id=template_id,
                gimnasio_id=gimnasio_id,
                usuario_id=usuario_id,
                evento_tipo=evento_tipo,
                datos_evento=datos_evento,
                tiempo_render_ms=tiempo_render_ms,
                exitoso=exitoso,
                error_message=error_message
            )
            self.db.add(analytics)
            self.db.commit()
        except SQLAlchemyError:
            # Don't fail the main operation if analytics logging fails
            pass
    
    def validate_template(self, configuracion: Dict[str, Any]) -> ValidationResult:
        """Validate template configuration"""
        return self.validator.validate_template(configuracion)
    
    def get_template_categories(self) -> List[str]:
        """Get all available template categories"""
        try:
            categories = self.db.query(PlantillaRutina.categoria).distinct().all()
            return [cat[0] for cat in categories if cat[0]]
        except SQLAlchemyError:
            return []
    
    def get_template_tags(self) -> List[str]:
        """Get all available template tags"""
        try:
            # This is a simplified approach - in production you might want to use
            # PostgreSQL's unnest function for better performance
            templates = self.db.query(PlantillaRutina.tags).filter(
                PlantillaRutina.tags.isnot(None)
            ).all()
            
            all_tags = set()
            for (tags,) in templates:
                if tags:
                    all_tags.update(tags)
            
            return sorted(list(all_tags))
        except SQLAlchemyError:
            return []


# Export main class
__all__ = ["TemplateRepository"]
