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
from src.services.b2_storage import delete_file, extract_file_key, get_file_url
from src.database.orm_models import (
    Ejercicio, Rutina, RutinaEjercicio, Usuario
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
                    'video_url': (get_file_url(e.video_url) if (hasattr(e, 'video_url') and getattr(e, 'video_url', None)) else None),
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
                filters = [func.lower(Ejercicio.nombre).like(term)]
                if hasattr(Ejercicio, 'descripcion'):
                    filters.append(func.lower(Ejercicio.descripcion).like(term))
                stmt = stmt.where(or_(*filters))
            
            if grupo and grupo.strip():
                if hasattr(Ejercicio, 'grupo_muscular'):
                    stmt = stmt.where(func.lower(Ejercicio.grupo_muscular) == grupo.strip().lower())
            
            if objetivo and objetivo.strip():
                if hasattr(Ejercicio, 'objetivo'):
                    stmt = stmt.where(func.lower(Ejercicio.objetivo) == objetivo.strip().lower())

            stmt = stmt.order_by(Ejercicio.nombre)
            
            ejercicios = self.db.scalars(stmt).all()
            
            out = []
            for e in ejercicios:
                v = getattr(e, 'video_url', None)
                try:
                    if v:
                        v = get_file_url(v)
                except Exception:
                    pass
                out.append(
                    {
                        'id': e.id,
                        'nombre': e.nombre,
                        'descripcion': getattr(e, 'descripcion', None),
                        'grupo_muscular': getattr(e, 'grupo_muscular', None),
                        'objetivo': getattr(e, 'objetivo', None),
                        'video_url': v,
                    }
                )
            return out
        except Exception as e:
            logger.error(f"Error scanning ejercicios: {e}")
            return []

    def obtener_ejercicios_paginados(
        self,
        *,
        search: str = "",
        grupo: str = None,
        objetivo: str = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Dict[str, Any]:
        """Get exercises with pagination (items + total)."""
        try:
            term = str(search or "").strip().lower()

            stmt = select(Ejercicio)
            count_stmt = select(func.count()).select_from(Ejercicio)

            search_filters = []
            if term:
                like = f"%{term}%"
                search_filters.append(func.lower(Ejercicio.nombre).like(like))
                if hasattr(Ejercicio, 'grupo_muscular'):
                    search_filters.append(func.lower(Ejercicio.grupo_muscular).like(like))
                if hasattr(Ejercicio, 'descripcion'):
                    search_filters.append(func.lower(Ejercicio.descripcion).like(like))

            if search_filters:
                stmt = stmt.where(or_(*search_filters))
                count_stmt = count_stmt.where(or_(*search_filters))

            if grupo and str(grupo).strip() and hasattr(Ejercicio, 'grupo_muscular'):
                stmt = stmt.where(func.lower(Ejercicio.grupo_muscular) == str(grupo).strip().lower())
                count_stmt = count_stmt.where(func.lower(Ejercicio.grupo_muscular) == str(grupo).strip().lower())
            if objetivo and str(objetivo).strip() and hasattr(Ejercicio, 'objetivo'):
                stmt = stmt.where(func.lower(Ejercicio.objetivo) == str(objetivo).strip().lower())
                count_stmt = count_stmt.where(func.lower(Ejercicio.objetivo) == str(objetivo).strip().lower())

            total = int(self.db.scalar(count_stmt) or 0)

            stmt = stmt.order_by(Ejercicio.nombre).limit(int(limit or 20)).offset(int(offset or 0))
            ejercicios = self.db.scalars(stmt).all()

            items = []
            for e in ejercicios:
                v = getattr(e, 'video_url', None)
                try:
                    if v:
                        v = get_file_url(v)
                except Exception:
                    pass
                items.append(
                    {
                        'id': e.id,
                        'nombre': e.nombre,
                        'descripcion': getattr(e, 'descripcion', None),
                        'grupo_muscular': getattr(e, 'grupo_muscular', None),
                        'objetivo': getattr(e, 'objetivo', None),
                        'video_url': v,
                        'video_mime': getattr(e, 'video_mime', None),
                    }
                )

            return {'items': items, 'total': total}
        except Exception as e:
            logger.error(f"Error paginating ejercicios: {e}")
            return {'items': [], 'total': 0}
            
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
                
            old_video_url = getattr(ejercicio, 'video_url', None)

            if 'nombre' in data: ejercicio.nombre = data['nombre']
            if 'grupo_muscular' in data: ejercicio.grupo_muscular = data['grupo_muscular']
            if 'video_url' in data: ejercicio.video_url = data['video_url']
            if 'video_mime' in data: ejercicio.video_mime = data['video_mime']
            if 'descripcion' in data and hasattr(ejercicio, 'descripcion'): 
                ejercicio.descripcion = data['descripcion']
                
            self.db.commit()

            # Best-effort cleanup of old video if it was replaced/removed
            try:
                if 'video_url' in data:
                    new_video_url = getattr(ejercicio, 'video_url', None)
                    if old_video_url and old_video_url != new_video_url:
                        old_key = extract_file_key(old_video_url)
                        if old_key:
                            delete_file(old_key)
            except Exception:
                pass

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

            old_video_url = getattr(ejercicio, 'video_url', None)
            self.db.delete(ejercicio)
            self.db.commit()

            # Best-effort cleanup of video in B2
            try:
                if old_video_url:
                    old_key = extract_file_key(old_video_url)
                    if old_key:
                        delete_file(old_key)
            except Exception:
                pass

            return True
        except Exception as e:
            logger.error(f"Error deleting ejercicio {ejercicio_id}: {e}")
            self.db.rollback()
            return False

    # =========================================================================
    # RUTINAS (Routines)
    # =========================================================================

    def obtener_rutinas(
        self,
        usuario_id: Optional[int] = None,
        include_exercises: bool = False,
        search: str = None,
        solo_plantillas: Optional[bool] = None,
        limit: Optional[int] = None,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get routines, optionally filtered by user."""
        try:
            stmt = select(Rutina)
            if usuario_id is not None:
                stmt = stmt.where(Rutina.usuario_id == usuario_id)

            if solo_plantillas is not None:
                if bool(solo_plantillas):
                    stmt = stmt.where(Rutina.usuario_id.is_(None))
                else:
                    stmt = stmt.where(Rutina.usuario_id.is_not(None))

            if search and str(search).strip():
                like = f"%{str(search).strip().lower()}%"
                stmt = stmt.where(func.lower(Rutina.nombre_rutina).like(like))
            
            stmt = stmt.order_by(Rutina.nombre_rutina)

            if limit is not None:
                stmt = stmt.limit(int(limit or 0))
            if offset:
                stmt = stmt.offset(int(offset or 0))

            rutinas = self.db.scalars(stmt).all()
            
            results = []

            ejercicios_by_rutina: Dict[int, List[Dict[str, Any]]] = {}
            if include_exercises and rutinas:
                rutina_ids = [int(r.id) for r in rutinas if getattr(r, 'id', None) is not None]
                if rutina_ids:
                    exs_all = self.db.scalars(
                        select(RutinaEjercicio)
                        .options(joinedload(RutinaEjercicio.ejercicio))
                        .where(RutinaEjercicio.rutina_id.in_(rutina_ids))
                        .order_by(RutinaEjercicio.rutina_id, RutinaEjercicio.dia_semana, RutinaEjercicio.orden)
                    ).all()
                    for re in exs_all:
                        rid = int(re.rutina_id)
                        ejercicios_by_rutina.setdefault(rid, []).append(
                            {
                                'id': re.id,
                                'ejercicio_id': re.ejercicio_id,
                                'nombre_ejercicio': re.ejercicio.nombre if re.ejercicio else None,
                                'dia_semana': re.dia_semana,
                                'series': re.series,
                                'repeticiones': re.repeticiones,
                                'orden': re.orden,
                            }
                        )

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
                    rout_dict['ejercicios'] = ejercicios_by_rutina.get(int(r.id), [])
                
                results.append(rout_dict)
            return results
        except Exception as e:
            logger.error(f"Error listing rutinas: {e}")
            return []

    def crear_rutina(self, data: Dict[str, Any]) -> Optional[int]:
        """Create a new routine."""
        try:
            usuario_id = data.get('usuario_id')
            if usuario_id is not None:
                usuario = self.db.get(Usuario, int(usuario_id))
                if not usuario or not bool(getattr(usuario, 'activo', False)):
                    raise PermissionError("El usuario está inactivo: no se puede crear una rutina")

            try:
                dias_semana = int(data.get('dias_semana') or 1)
            except Exception:
                dias_semana = 1
            dias_semana = max(1, dias_semana)

            nombre = str(data.get('nombre_rutina') or '').strip()
            if not nombre:
                return None

            rutina = Rutina(
                nombre_rutina=nombre,
                usuario_id=usuario_id,
                descripcion=data.get('descripcion'),
                dias_semana=dias_semana,
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
            
        ejercicios_out = []
        for re in ejercicios:
            video_url = re.ejercicio.video_url if re.ejercicio else None
            try:
                if video_url:
                    video_url = get_file_url(video_url)
            except Exception:
                pass
            ejercicios_out.append(
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
                    'video_url': video_url,
                }
            )

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
            'ejercicios': ejercicios_out
        }

    def actualizar_rutina(self, rutina_id: int, data: Dict[str, Any]) -> bool:
        """Update a routine."""
        try:
            rutina = self.db.get(Rutina, rutina_id)
            if not rutina:
                return False

            if 'nombre_rutina' not in data and 'nombre' in data:
                data['nombre_rutina'] = data.get('nombre')

            if 'nombre_rutina' in data: rutina.nombre_rutina = data['nombre_rutina']
            if 'descripcion' in data: rutina.descripcion = data['descripcion']
            if 'categoria' in data: rutina.categoria = data['categoria']
            if 'dias_semana' in data: rutina.dias_semana = data['dias_semana']
            if 'activa' in data: rutina.activa = data['activa']
            
            # If exercises are included in update, handle them
            if 'ejercicios' in data and isinstance(data['ejercicios'], list):
                ok = self.asignar_ejercicios_rutina(rutina_id, data['ejercicios'], commit=False)
                if not ok:
                    self.db.rollback()
                    return False
            
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

            try:
                self.db.query(RutinaEjercicio).filter(RutinaEjercicio.rutina_id == rutina_id).delete()
            except Exception:
                pass
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

    def asignar_ejercicios_rutina(self, rutina_id: int, ejercicios: List[Dict[str, Any]], commit: bool = True) -> bool:
        """Assign exercises to a routine."""
        try:
            rutina = self.db.get(Rutina, rutina_id)
            if not rutina:
                return False

            try:
                ejercicio_ids = [int(ex.get('ejercicio_id')) for ex in ejercicios if ex.get('ejercicio_id') is not None]
            except Exception:
                ejercicio_ids = []
            if ejercicio_ids:
                existing = set(self.db.scalars(select(Ejercicio.id).where(Ejercicio.id.in_(ejercicio_ids))).all())
                missing = [eid for eid in ejercicio_ids if eid not in existing]
                if missing:
                    return False

            # Clear existing exercises
            self.db.query(RutinaEjercicio).filter(RutinaEjercicio.rutina_id == rutina_id).delete()

            for ex_data in ejercicios:
                try:
                    dia_semana = int(ex_data.get('dia_semana') or 1)
                except Exception:
                    dia_semana = 1
                dia_semana = max(1, dia_semana)
                try:
                    if getattr(rutina, 'dias_semana', None):
                        dia_semana = min(dia_semana, int(rutina.dias_semana or dia_semana))
                except Exception:
                    pass

                try:
                    series = int(ex_data.get('series') or 0)
                except Exception:
                    series = 0
                series = max(0, series)
                try:
                    orden = int(ex_data.get('orden', 0) or 0)
                except Exception:
                    orden = 0
                orden = max(0, orden)

                assignment = RutinaEjercicio(
                    rutina_id=rutina_id,
                    ejercicio_id=int(ex_data['ejercicio_id']),
                    dia_semana=dia_semana,
                    series=series,
                    repeticiones=str(ex_data.get('repeticiones', '')),
                    orden=orden,
                )
                self.db.add(assignment)
            
            if commit:
                self.db.commit()
            else:
                self.db.flush()
            return True
        except Exception as e:
            logger.error(f"Error assigning exercises to routine {rutina_id}: {e}")
            if commit:
                self.db.rollback()
            return False
