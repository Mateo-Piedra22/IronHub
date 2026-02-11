"""
Gym Template Assignment Service
Servicio especializado para la gestión de asignación de plantillas a gimnasios
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_

from ..models.orm_models import (
    PlantillaRutina, GimnasioPlantilla, Gimnasio, 
    PlantillaAnalitica
)
from ..repositories.template_repository import TemplateRepository
from ..services.template_analytics import TemplateAnalyticsService

class GymTemplateService:
    """Servicio para gestión de plantillas específicas de gimnasios"""
    
    def __init__(self, db_session: Session):
        self.db = db_session
        self.template_repo = TemplateRepository(db_session)
        self.analytics_service = TemplateAnalyticsService(db_session)
    
    def assign_template_to_gym(
        self,
        gym_id: int,
        template_id: int,
        assigned_by: int,
        priority: int = 0,
        custom_config: Optional[Dict[str, Any]] = None,
        notes: Optional[str] = None
    ) -> Optional[GimnasioPlantilla]:
        """
        Asignar una plantilla a un gimnasio específico
        
        Args:
            gym_id: ID del gimnasio
            template_id: ID de la plantilla
            assigned_by: ID del usuario que asigna
            priority: Prioridad de la plantilla (0 = más alta)
            custom_config: Configuración personalizada para el gimnasio
            notes: Notas adicionales
            
        Returns:
            GimnasioPlantilla: Asignación creada
        """
        try:
            # Verificar que gimnasio y plantilla existen
            gym = self.db.query(Gimnasio).filter(Gimnasio.id == gym_id).first()
            if not gym:
                raise ValueError(f"Gimnasio {gym_id} no encontrado")
            
            template = self.db.query(PlantillaRutina).filter(
                PlantillaRutina.id == template_id,
                PlantillaRutina.activa == True,
                PlantillaRutina.tipo == "export_pdf",
            ).first()
            if not template:
                raise ValueError(f"Template {template_id} no encontrado/inactivo o no es de exportación")
            
            # Verificar si ya está asignada
            existing = self.db.query(GimnasioPlantilla).filter(
                and_(
                    GimnasioPlantilla.gimnasio_id == gym_id,
                    GimnasioPlantilla.plantilla_id == template_id
                )
            ).first()
            
            if existing:
                # Actualizar asignación existente
                existing.activa = True
                existing.prioridad = priority
                existing.configuracion_personalizada = custom_config
                existing.notas = notes
                existing.fecha_asignacion = datetime.utcnow()
                existing.asignada_por = assigned_by
                assignment = existing
            else:
                # Crear nueva asignación
                assignment = GimnasioPlantilla(
                    gimnasio_id=gym_id,
                    plantilla_id=template_id,
                    activa=True,
                    prioridad=priority,
                    configuracion_personalizada=custom_config,
                    asignada_por=assigned_by,
                    fecha_asignacion=datetime.utcnow(),
                    notas=notes
                )
                self.db.add(assignment)
            
            self.db.commit()
            
            # Registrar analytics
            self.analytics_service.track_assignment(
                template_id=template_id,
                gym_id=gym_id,
                user_id=assigned_by,
                assignment_data={
                    "priority": priority,
                    "has_custom_config": custom_config is not None,
                    "notes": notes
                }
            )
            
            return assignment
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_gym_templates(
        self,
        gym_id: int,
        active_only: bool = True,
        include_analytics: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Obtener plantillas asignadas a un gimnasio
        
        Args:
            gym_id: ID del gimnasio
            active_only: Solo plantillas activas
            include_analytics: Incluir datos de analytics
            
        Returns:
            List[Dict]: Lista de plantillas con sus datos
        """
        try:
            query = self.db.query(GimnasioPlantilla).filter(
                GimnasioPlantilla.gimnasio_id == gym_id
            )
            
            if active_only:
                query = query.filter(GimnasioPlantilla.activa == True)
            
            assignments = query.order_by(
                GimnasioPlantilla.prioridad.asc(),
                GimnasioPlantilla.fecha_asignacion.desc()
            ).options(
                joinedload(GimnasioPlantilla.plantilla),
                joinedload(GimnasioPlantilla.asignado_por_user)
            ).all()
            
            result = []
            for assignment in assignments:
                if not assignment.plantilla or getattr(assignment.plantilla, "tipo", "") != "export_pdf":
                    continue
                template_data = {
                    "assignment_id": assignment.id,
                    "template_id": assignment.plantilla_id,
                    "template_name": assignment.plantilla.nombre,
                    "template_description": assignment.plantilla.descripcion,
                    "template_category": assignment.plantilla.categoria,
                    "template_tags": assignment.plantilla.tags,
                    "dias_semana": assignment.plantilla.dias_semana,
                    "preview_url": assignment.plantilla.preview_url,
                    "uso_count": assignment.plantilla.uso_count,
                    "rating_promedio": float(assignment.plantilla.rating_promedio) if assignment.plantilla.rating_promedio else None,
                    "priority": assignment.prioridad,
                    "custom_config": assignment.configuracion_personalizada,
                    "notes": assignment.notas,
                    "assigned_by": assignment.asignada_por,
                    "assigned_by_name": assignment.asignado_por_user.nombre_completo if assignment.asignado_por_user else None,
                    "fecha_asignacion": assignment.fecha_asignacion.isoformat() if assignment.fecha_asignacion else None,
                    "fecha_ultima_uso": assignment.fecha_ultima_uso.isoformat() if assignment.fecha_ultima_uso else None,
                    "gym_usage_count": assignment.uso_count
                }
                
                if include_analytics:
                    analytics = self.analytics_service.get_template_analytics_for_gym(
                        assignment.plantilla_id, gym_id
                    )
                    template_data["analytics"] = analytics
                
                result.append(template_data)
            
            return result
            
        except Exception as e:
            raise e
    
    def update_gym_template_assignment(
        self,
        assignment_id: int,
        updates: Dict[str, Any],
        updated_by: int
    ) -> Optional[GimnasioPlantilla]:
        """
        Actualizar asignación de plantilla a gimnasio
        
        Args:
            assignment_id: ID de la asignación
            updates: Datos a actualizar
            updated_by: ID del usuario que actualiza
            
        Returns:
            GimnasioPlantilla: Asignación actualizada
        """
        try:
            assignment = self.db.query(GimnasioPlantilla).filter(
                GimnasioPlantilla.id == assignment_id
            ).first()
            
            if not assignment:
                raise ValueError(f"Asignación {assignment_id} no encontrada")
            
            # Actualizar campos permitidos
            if "priority" in updates:
                assignment.prioridad = updates["priority"]
            if "custom_config" in updates:
                assignment.configuracion_personalizada = updates["custom_config"]
            if "notes" in updates:
                assignment.notas = updates["notes"]
            if "activa" in updates:
                assignment.activa = updates["activa"]
            
            self.db.commit()
            
            # Registrar analytics
            self.analytics_service.track_assignment_update(
                template_id=assignment.plantilla_id,
                gym_id=assignment.gimnasio_id,
                user_id=updated_by,
                update_data=updates
            )
            
            return assignment
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def remove_template_from_gym(
        self,
        assignment_id: int,
        removed_by: int,
        soft_delete: bool = True
    ) -> bool:
        """
        Eliminar asignación de plantilla de gimnasio
        
        Args:
            assignment_id: ID de la asignación
            removed_by: ID del usuario que elimina
            soft_delete: Si es True, solo desactiva (borrado suave)
            
        Returns:
            bool: True si se eliminó correctamente
        """
        try:
            assignment = self.db.query(GimnasioPlantilla).filter(
                GimnasioPlantilla.id == assignment_id
            ).first()
            
            if not assignment:
                raise ValueError(f"Asignación {assignment_id} no encontrada")
            
            if soft_delete:
                assignment.activa = False
            else:
                self.db.delete(assignment)
            
            self.db.commit()
            
            # Registrar analytics
            self.analytics_service.track_assignment_removal(
                template_id=assignment.plantilla_id,
                gym_id=assignment.gimnasio_id,
                user_id=removed_by,
                soft_delete=soft_delete
            )
            
            return True
            
        except Exception as e:
            self.db.rollback()
            raise e
    
    def get_available_templates_for_gym(
        self,
        gym_id: int,
        category: Optional[str] = None,
        search_query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Obtener plantillas disponibles para asignar a un gimnasio
        
        Args:
            gym_id: ID del gimnasio
            category: Filtrar por categoría
            search_query: Búsqueda por nombre/descripción
            
        Returns:
            List[Dict]: Plantillas disponibles
        """
        try:
            # Obtener IDs de plantillas ya asignadas al gimnasio
            assigned_ids = self.db.query(GimnasioPlantilla.plantilla_id).filter(
                and_(
                    GimnasioPlantilla.gimnasio_id == gym_id,
                    GimnasioPlantilla.activa == True
                )
            ).subquery()
            
            # Query de plantillas públicas y activas no asignadas
            query = self.db.query(PlantillaRutina).filter(
                and_(
                    PlantillaRutina.activa == True,
                    PlantillaRutina.publica == True,
                    ~PlantillaRutina.id.in_(assigned_ids)
                )
            )
            
            # Aplicar filtros
            if category:
                query = query.filter(PlantillaRutina.categoria == category)
            
            if search_query:
                query = query.filter(
                    or_(
                        PlantillaRutina.nombre.ilike(f"%{search_query}%"),
                        PlantillaRutina.descripcion.ilike(f"%{search_query}%")
                    )
                )
            
            templates = query.order_by(
                PlantillaRutina.uso_count.desc(),
                PlantillaRutina.rating_promedio.desc()
            ).all()
            
            result = []
            for template in templates:
                result.append({
                    "id": template.id,
                    "nombre": template.nombre,
                    "descripcion": template.descripcion,
                    "categoria": template.categoria,
                    "dias_semana": template.dias_semana,
                    "tags": template.tags,
                    "preview_url": template.preview_url,
                    "uso_count": template.uso_count,
                    "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
                    "rating_count": template.rating_count,
                    "fecha_creacion": template.fecha_creacion.isoformat() if template.fecha_creacion else None
                })
            
            return result
            
        except Exception as e:
            raise e
    
    def get_gym_template_usage_stats(
        self,
        gym_id: int,
        template_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Obtener estadísticas de uso de plantillas en un gimnasio
        
        Args:
            gym_id: ID del gimnasio
            template_id: ID específico de plantilla (opcional)
            days: Días a considerar para estadísticas
            
        Returns:
            Dict: Estadísticas de uso
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            query = self.db.query(PlantillaAnalitica).filter(
                and_(
                    PlantillaAnalitica.gimnasio_id == gym_id,
                    PlantillaAnalitica.fecha_evento >= cutoff_date
                )
            )
            
            if template_id:
                query = query.filter(PlantillaAnalitica.plantilla_id == template_id)
            
            analytics = query.all()
            
            # Procesar estadísticas
            stats = {
                "total_events": len(analytics),
                "unique_templates": len(set(a.plantilla_id for a in analytics)),
                "unique_users": len(set(a.usuario_id for a in analytics if a.usuario_id)),
                "event_types": {},
                "daily_usage": {},
                "template_usage": {},
                "success_rate": 0
            }
            
            successful_events = 0
            for event in analytics:
                # Event types
                event_type = event.evento_tipo
                stats["event_types"][event_type] = stats["event_types"].get(event_type, 0) + 1
                
                # Daily usage
                date_key = event.fecha_evento.date().isoformat()
                stats["daily_usage"][date_key] = stats["daily_usage"].get(date_key, 0) + 1
                
                # Template usage
                template_key = event.plantilla_id
                stats["template_usage"][template_key] = stats["template_usage"].get(template_key, 0) + 1
                
                # Success rate
                if event.exitoso:
                    successful_events += 1
            
            stats["success_rate"] = (successful_events / len(analytics) * 100) if analytics else 0
            
            return stats
            
        except Exception as e:
            raise e
    
    def get_recommended_templates_for_gym(
        self,
        gym_id: int,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Obtener plantillas recomendadas para un gimnasio basadas en uso y preferencias
        
        Args:
            gym_id: ID del gimnasio
            limit: Límite de resultados
            
        Returns:
            List[Dict]: Plantillas recomendadas
        """
        try:
            # Obtener patrones de uso del gimnasio
            usage_stats = self.get_gym_template_usage_stats(gym_id, days=90)
            
            # Si no hay historial, recomendar las más populares
            if not usage_stats["template_usage"]:
                return self.get_available_templates_for_gym(
                    gym_id=gym_id
                )[:limit]
            
            # Obtener categorías más usadas
            most_used_templates = list(usage_stats["template_usage"].keys())[:5]
            
            # Obtener plantillas similares a las más usadas
            similar_templates = self.db.query(PlantillaRutina).filter(
                and_(
                    PlantillaRutina.activa == True,
                    PlantillaRutina.publica == True,
                    PlantillaRutina.categoria.in_(
                        self.db.query(PlantillaRutina.categoria).filter(
                            PlantillaRutina.id.in_(most_used_templates)
                        ).distinct().all()
                    )
                )
            ).order_by(
                PlantillaRutina.uso_count.desc(),
                PlantillaRutina.rating_promedio.desc()
            ).limit(limit * 2).all()
            
            # Filtrar las ya asignadas
            assigned_ids = self.db.query(GimnasioPlantilla.plantilla_id).filter(
                and_(
                    GimnasioPlantilla.gimnasio_id == gym_id,
                    GimnasioPlantilla.activa == True
                )
            ).subquery()
            
            recommended = []
            for template in similar_templates:
                if template.id not in assigned_ids and len(recommended) < limit:
                    recommended.append({
                        "id": template.id,
                        "nombre": template.nombre,
                        "descripcion": template.descripcion,
                        "categoria": template.categoria,
                        "dias_semana": template.dias_semana,
                        "tags": template.tags,
                        "preview_url": template.preview_url,
                        "uso_count": template.uso_count,
                        "rating_promedio": float(template.rating_promedio) if template.rating_promedio else None,
                        "rating_count": template.rating_count,
                        "recommendation_reason": self._get_recommendation_reason(template, usage_stats)
                    })
            
            return recommended
            
        except Exception as e:
            raise e
    
    def _get_recommendation_reason(
        self, 
        template: PlantillaRutina, 
        usage_stats: Dict[str, Any]
    ) -> str:
        """Generar razón de recomendación basada en estadísticas"""
        reasons = []
        
        if template.uso_count > 100:
            reasons.append("Muy popular")
        
        if template.rating_promedio and template.rating_promedio >= 4.5:
            reasons.append("Excelente rating")
        
        if template.categoria in [t.categoria for t in self.db.query(PlantillaRutina).filter(
            PlantillaRutina.id.in_(usage_stats["template_usage"].keys())
        ).all()]:
            reasons.append("Similar a tus favoritas")
        
        if not reasons:
            reasons.append("Recomendada para ti")
        
        return " • ".join(reasons)
    
    def bulk_assign_templates_to_gym(
        self,
        gym_id: int,
        template_ids: List[int],
        assigned_by: int,
        priority_start: int = 0
    ) -> List[GimnasioPlantilla]:
        """
        Asignar múltiples plantillas a un gimnasio
        
        Args:
            gym_id: ID del gimnasio
            template_ids: Lista de IDs de plantillas
            assigned_by: ID del usuario que asigna
            priority_start: Prioridad inicial
            
        Returns:
            List[GimnasioPlantilla]: Asignaciones creadas
        """
        assignments = []
        
        for i, template_id in enumerate(template_ids):
            try:
                assignment = self.assign_template_to_gym(
                    gym_id=gym_id,
                    template_id=template_id,
                    assigned_by=assigned_by,
                    priority=priority_start + i
                )
                assignments.append(assignment)
            except Exception as e:
                # Log error pero continuar con otras
                print(f"Error asignando template {template_id}: {e}")
        
        return assignments
