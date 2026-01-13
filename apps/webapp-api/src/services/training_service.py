"""
Training Service - SQLAlchemy ORM Implementation

Handles exercises (Ejercicio) and routines (Rutina).
Replaces legacy GymService training management methods.
"""
import logging
from typing import List, Dict, Any, Optional

from sqlalchemy import select, or_, func
from sqlalchemy.orm import Session, joinedload

from src.services.base import BaseService
from src.database.orm_models import (
    Ejercicio, Rutina, RutinaEjercicio
)

logger = logging.getLogger(__name__)

class TrainingService(BaseService):
    """Service for exercises, routines, and training plans."""

    def __init__(self, db: Session):
        super().__init__(db)

    # =========================================================================
    # EJERCICIOS (Exercises)
    # =========================================================================

    def obtener_ejercicios_catalog(self) -> List[Dict[str, Any]]:
        """Get minimal exercises catalog for routine building."""
        try:
            ejercicios = self.db.scalars(select(Ejercicio).order_by(Ejercicio.nombre)).all()
            return [
                {
                    'id': e.id,
                    'nombre': e.nombre,
                    'video_url': e.video_url if hasattr(e, 'video_url') else None,
                    'grupo_muscular': e.grupo_muscular if hasattr(e, 'grupo_muscular') else None
                }
                for e in ejercicios
            ]
        except Exception as e:
            logger.error(f"Error getting ejercicios catalog: {e}")
            return []

    def obtener_ejercicios(self, search: str = None, grupo: str = None, objetivo: str = None) -> List[Dict[str, Any]]:
        """Get all exercises with optional filters."""
        try:
            stmt = select(Ejercicio)
            
            if search and search.strip():
                term = f"%{search.strip().lower()}%"
                stmt = stmt.where(or_(
                    func.lower(Ejercicio.nombre).like(term),
                    # Check if descripcion exists on model
                    func.lower(getattr(Ejercicio, 'descripcion', '')).like(term)
                ))
            
            if grupo and grupo.strip():
                if hasattr(Ejercicio, 'grupo_muscular'):
                    stmt = stmt.where(func.lower(Ejercicio.grupo_muscular) == grupo.strip().lower())
            
            if objetivo and objetivo.strip():
                if hasattr(Ejercicio, 'objetivo'):
                    stmt = stmt.where(func.lower(Ejercicio.objetivo) == objetivo.strip().lower())

            stmt = stmt.order_by(Ejercicio.nombre)
            
            ejercicios = self.db.scalars(stmt).all()
            
            return [
                {
                    'id': e.id,
                    'nombre': e.nombre,
                    'descripcion': getattr(e, 'descripcion', None),
                    'grupo_muscular': getattr(e, 'grupo_muscular', None),
                    'objetivo': getattr(e, 'objetivo', None),
                    'video_url': getattr(e, 'video_url', None)
                }
                for e in ejercicios
            ]
        except Exception as e:
            logger.error(f"Error scanning ejercicios: {e}")
            return []
            
    def crear_ejercicio(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new exercise."""
        try:
            ejercicio = Ejercicio(
                nombre=data.get('nombre', ''),
                grupo_muscular=data.get('grupo_muscular'),
                video_url=data.get('video_url'),
                video_mime=data.get('video_mime')
            )
            # Add description if model has it
            if hasattr(Ejercicio, 'descripcion'):
                ejercicio.descripcion = data.get('descripcion')
                
            self.db.add(ejercicio)
            self.db.commit()
            if ejercicio.id:
                 return ejercicio.id
            return None
        except Exception as e:
            logger.error(f"Error creating ejercicio: {e}")
            self.db.rollback()
            return None

    def actualizar_ejercicio(self, ejercicio_id: int, data: Dict[str, Any]) -> bool:
        """Update an exercise."""
        try:
            ejercicio = self.db.get(Ejercicio, ejercicio_id)
            if not ejercicio:
                return False
                
            if 'nombre' in data: ejercicio.nombre = data['nombre']
            if 'grupo_muscular' in data: ejercicio.grupo_muscular = data['grupo_muscular']
            if 'video_url' in data: ejercicio.video_url = data['video_url']
            if 'video_mime' in data: ejercicio.video_mime = data['video_mime']
            if 'descripcion' in data and hasattr(ejercicio, 'descripcion'): 
                ejercicio.descripcion = data['descripcion']
                
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating ejercicio {ejercicio_id}: {e}")
            self.db.rollback()
            return False

    def eliminar_ejercicio(self, ejercicio_id: int) -> bool:
        """Delete an exercise."""
        try:
            ejercicio = self.db.get(Ejercicio, ejercicio_id)
            if not ejercicio:
                return False
            self.db.delete(ejercicio)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting ejercicio {ejercicio_id}: {e}")
            self.db.rollback()
            return False

    # =========================================================================
    # RUTINAS (Routines)
    # =========================================================================

    def obtener_rutinas(self, usuario_id: Optional[int] = None, include_exercises: bool = False) -> List[Dict[str, Any]]:
        """Get routines, optionally filtered by user."""
        try:
            stmt = select(Rutina)
            if usuario_id is not None:
                stmt = stmt.where(Rutina.usuario_id == usuario_id)
            # If requesting templates (usuario_id is None in some contexts, but let's assume filtering logic is outside or passed here)
            
            stmt = stmt.order_by(Rutina.nombre_rutina)
            rutinas = self.db.scalars(stmt).all()
            
            results = []
            for r in rutinas:
                rout_dict = {
                    'id': r.id,
                    'nombre_rutina': r.nombre_rutina,
                    'descripcion': r.descripcion,
                    'usuario_id': r.usuario_id,
                    'dias_semana': r.dias_semana,
                    'categoria': r.categoria,
                    'activa': r.activa,
                    'uuid_rutina': getattr(r, 'uuid_rutina', None)
                }
                
                if include_exercises:
                    # Fetch exercises for this routine
                    # Careful with N+1 query problem if list is long. 
                    # For list endpoints usually lightweight data is improved.
                    # But if requested:
                    exs = self.db.scalars(
                        select(RutinaEjercicio)
                        .options(joinedload(RutinaEjercicio.ejercicio))
                        .where(RutinaEjercicio.rutina_id == r.id)
                        .order_by(RutinaEjercicio.dia_semana, RutinaEjercicio.orden)
                    ).all()
                    
                    rout_dict['ejercicios'] = [
                        {
                            'id': re.id,
                            'ejercicio_id': re.ejercicio_id,
                            'nombre_ejercicio': re.ejercicio.nombre if re.ejercicio else None,
                            'dia_semana': re.dia_semana,
                            'series': re.series,
                            'repeticiones': re.repeticiones,
                            'orden': re.orden
                        }
                        for re in exs
                    ]
                
                results.append(rout_dict)
            return results
        except Exception as e:
            logger.error(f"Error listing rutinas: {e}")
            return []

    def crear_rutina(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new routine."""
        try:
            rutina = Rutina(
                nombre_rutina=data['nombre_rutina'],
                usuario_id=data.get('usuario_id'),
                descripcion=data.get('descripcion'),
                dias_semana=data.get('dias_semana'),
                categoria=data.get('categoria', 'general'),
                activa=data.get('activa', True)
            )
            # Add uuid if model supports it
            if hasattr(Rutina, 'uuid_rutina'):
                 import uuid
                 rutina.uuid_rutina = str(uuid.uuid4())
                 
            self.db.add(rutina)
            self.db.commit()
            return rutina.id
        except Exception as e:
            logger.error(f"Error creating rutina: {e}")
            self.db.rollback()
            return None

    def obtener_rutina_completa(self, rutina_id: int) -> Optional[Dict[str, Any]]:
        """Get full details of a routine including exercises (Alias for obtener_rutina_detalle)."""
        return self.obtener_rutina_detalle(rutina_id)

    def obtener_rutina_detalle(self, rutina_id: int) -> Optional[Dict[str, Any]]:
        """Get full details of a routine including exercises."""
        try:
            rutina = self.db.get(Rutina, rutina_id)
            if not rutina:
                return None
            return self._build_rutina_detail(rutina)
        except Exception as e:
            logger.error(f"Error getting rutina detail: {e}")
            return None

    def obtener_rutina_por_uuid(self, uuid_str: str) -> Optional[Dict[str, Any]]:
        """Get full details of a routine by UUID."""
        try:
            stmt = select(Rutina).where(Rutina.uuid_rutina == uuid_str)
            rutina = self.db.scalars(stmt).first()
            if not rutina:
                return None
            return self._build_rutina_detail(rutina)
        except Exception as e:
            logger.error(f"Error getting rutina by uuid {uuid_str}: {e}")
            return None

    def _build_rutina_detail(self, rutina: Rutina) -> Dict[str, Any]:
        """Helper to build routine detail dict from ORM object."""
        ejercicios = self.db.scalars(
            select(RutinaEjercicio)
            .options(joinedload(RutinaEjercicio.ejercicio))
            .where(RutinaEjercicio.rutina_id == rutina.id)
            .order_by(RutinaEjercicio.dia_semana, RutinaEjercicio.orden)
        ).all()

        # Get user name if exists
        usuario_nombre = None
        if rutina.usuario_id:
            if hasattr(rutina, 'usuario') and rutina.usuario: # type: ignore
                 usuario_nombre = rutina.usuario.nombre
            
        return {
            'id': rutina.id,
            'nombre_rutina': rutina.nombre_rutina,
            'descripcion': rutina.descripcion,
            'usuario_id': rutina.usuario_id,
            'usuario_nombre': usuario_nombre,
            'categoria': rutina.categoria,
            'dias_semana': rutina.dias_semana,
            'activa': rutina.activa,
            'uuid_rutina': getattr(rutina, 'uuid_rutina', None),
            'ejercicios': [
                {
                    'id': re.id,
                    'ejercicio_id': re.ejercicio_id,
                    'nombre': re.ejercicio.nombre if re.ejercicio else None,
                    'nombre_ejercicio': getattr(re, 'nombre_ejercicio', None) or (re.ejercicio.nombre if re.ejercicio else None),
                    'grupo_muscular': re.ejercicio.grupo_muscular if re.ejercicio else None,
                    'series': re.series,
                    'repeticiones': re.repeticiones,
                    'dia_semana': re.dia_semana,
                    'orden': re.orden,
                    'video_url': re.ejercicio.video_url if re.ejercicio else None
                }
                for re in ejercicios
            ]
        }

    def actualizar_rutina(self, rutina_id: int, data: Dict[str, Any]) -> bool:
        """Update a routine."""
        try:
            rutina = self.db.get(Rutina, rutina_id)
            if not rutina:
                return False

            if 'nombre_rutina' in data: rutina.nombre_rutina = data['nombre_rutina']
            if 'descripcion' in data: rutina.descripcion = data['descripcion']
            if 'categoria' in data: rutina.categoria = data['categoria']
            if 'dias_semana' in data: rutina.dias_semana = data['dias_semana']
            if 'activa' in data: rutina.activa = data['activa']
            
            # If exercises are included in update, handle them
            if 'ejercicios' in data and isinstance(data['ejercicios'], list):
                self.asignar_ejercicios_rutina(rutina_id, data['ejercicios'])
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating rutina {rutina_id}: {e}")
            self.db.rollback()
            return False

    def eliminar_rutina(self, rutina_id: int) -> bool:
        """Delete a routine."""
        try:
            rutina = self.db.get(Rutina, rutina_id)
            if not rutina:
                return False
            self.db.delete(rutina)
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting rutina {rutina_id}: {e}")
            self.db.rollback()
            return False

    def desactivar_rutinas_usuario(self, usuario_id: int, except_rutina_id: int = None) -> bool:
        """Deactivate all routines for a user except one."""
        try:
            stmt = select(Rutina).where(Rutina.usuario_id == usuario_id)
            if except_rutina_id:
                stmt = stmt.where(Rutina.id != except_rutina_id)
            
            rutinas = self.db.scalars(stmt).all()
            for r in rutinas:
                r.activa = False
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error deactivating user routines: {e}")
            self.db.rollback()
            return False

    def asignar_ejercicios_rutina(self, rutina_id: int, ejercicios: List[Dict[str, Any]]) -> bool:
        """Assign exercises to a routine."""
        try:
            rutina = self.db.get(Rutina, rutina_id)
            if not rutina:
                return False

            # Clear existing exercises
            self.db.query(RutinaEjercicio).filter(RutinaEjercicio.rutina_id == rutina_id).delete()

            for ex_data in ejercicios:
                assignment = RutinaEjercicio(
                    rutina_id=rutina_id,
                    ejercicio_id=int(ex_data['ejercicio_id']),
                    dia_semana=int(ex_data.get('dia_semana') or 1),
                    series=int(ex_data.get('series') or 0),
                    repeticiones=str(ex_data.get('repeticiones', '')),
                    orden=int(ex_data.get('orden', 0))
                )
                self.db.add(assignment)
            
            self.db.commit()
            return True
        except Exception as e:
            logger.error(f"Error assigning exercises to routine {rutina_id}: {e}")
            self.db.rollback()
            return False
